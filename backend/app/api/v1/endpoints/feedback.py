"""
Rule Feedback API - Lawyers can mark false positives/negatives per rule.

Phase 5: Continuous learning through user feedback.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, cast, Float

from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.feedback import RuleFeedback
from app.models.playbook import Playbook

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    playbook_rule_id: UUID
    document_id: Optional[UUID] = None
    feedback_type: str = Field(..., pattern="^(false_positive|false_negative|correct|needs_improvement)$")
    clause_text: Optional[str] = None
    user_comment: Optional[str] = None
    suggested_risk_level: Optional[str] = Field(None, pattern="^(RED|YELLOW|GREEN)$")


class FeedbackResponse(BaseModel):
    id: UUID
    feedback_type: str
    clause_text: Optional[str]
    user_comment: Optional[str]
    suggested_risk_level: Optional[str]
    created_at: datetime


class FeedbackListResponse(BaseModel):
    items: List[FeedbackResponse]
    total: int


class RuleEffectivenessResponse(BaseModel):
    rule_id: UUID
    clause_type: str
    total_feedback: int
    false_positives: int
    false_negatives: int
    correct_count: int
    false_positive_rate: float
    needs_review: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on a rule match (false positive, false negative, etc.)."""
    entry = RuleFeedback(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        playbook_rule_id=feedback.playbook_rule_id,
        document_id=feedback.document_id,
        feedback_type=feedback.feedback_type,
        clause_text=feedback.clause_text,
        user_comment=feedback.user_comment,
        suggested_risk_level=feedback.suggested_risk_level,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return FeedbackResponse(
        id=entry.id,
        feedback_type=entry.feedback_type,
        clause_text=entry.clause_text,
        user_comment=entry.user_comment,
        suggested_risk_level=entry.suggested_risk_level,
        created_at=entry.created_at,
    )


@router.get("/", response_model=FeedbackListResponse)
async def list_feedback(
    playbook_rule_id: Optional[UUID] = None,
    feedback_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List feedback for the current organization with pagination."""
    base_filter = RuleFeedback.organization_id == current_user.organization_id

    # Build filter conditions
    filters = [base_filter]
    if playbook_rule_id:
        filters.append(RuleFeedback.playbook_rule_id == playbook_rule_id)
    if feedback_type:
        filters.append(RuleFeedback.feedback_type == feedback_type)

    # Total count
    count_query = select(func.count(RuleFeedback.id)).where(*filters)
    total = (await db.execute(count_query)).scalar() or 0

    # Paginated results
    query = (
        select(RuleFeedback)
        .where(*filters)
        .order_by(RuleFeedback.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    return FeedbackListResponse(
        items=[
            FeedbackResponse(
                id=row.id,
                feedback_type=row.feedback_type,
                clause_text=row.clause_text,
                user_comment=row.user_comment,
                suggested_risk_level=row.suggested_risk_level,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
    )


@router.get("/stats", response_model=List[RuleEffectivenessResponse])
async def get_rule_effectiveness(
    needs_review_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get rule effectiveness stats using ORM aggregation."""
    from app.models.playbook import PlaybookRule

    try:
        # Subquery: playbook IDs belonging to user's org
        org_playbook_ids = (
            select(Playbook.id)
            .where(Playbook.organization_id == current_user.organization_id)
        ).scalar_subquery()

        # Aggregate feedback per rule
        false_positives_col = func.count(
            case((RuleFeedback.feedback_type == "false_positive", 1))
        )
        false_negatives_col = func.count(
            case((RuleFeedback.feedback_type == "false_negative", 1))
        )
        correct_count_col = func.count(
            case((RuleFeedback.feedback_type == "correct", 1))
        )
        total_feedback_col = func.count(RuleFeedback.id)

        query = (
            select(
                RuleFeedback.playbook_rule_id.label("rule_id"),
                PlaybookRule.clause_type.label("clause_type"),
                total_feedback_col.label("total_feedback"),
                false_positives_col.label("false_positives"),
                false_negatives_col.label("false_negatives"),
                correct_count_col.label("correct_count"),
            )
            .join(PlaybookRule, PlaybookRule.id == RuleFeedback.playbook_rule_id)
            .where(PlaybookRule.playbook_id.in_(org_playbook_ids))
            .group_by(RuleFeedback.playbook_rule_id, PlaybookRule.clause_type)
        )

        result = await db.execute(query)
        rows = result.all()

        results = []
        for row in rows:
            total = row.total_feedback or 0
            fp = row.false_positives or 0
            fp_rate = fp / total if total > 0 else 0.0
            needs_review = fp_rate > 0.3 and total >= 3

            if needs_review_only and not needs_review:
                continue

            results.append(RuleEffectivenessResponse(
                rule_id=row.rule_id,
                clause_type=row.clause_type,
                total_feedback=total,
                false_positives=fp,
                false_negatives=row.false_negatives or 0,
                correct_count=row.correct_count or 0,
                false_positive_rate=round(fp_rate, 4),
                needs_review=needs_review,
            ))

        return results
    except Exception as e:
        logger.error("Failed to fetch feedback stats: %s", e, exc_info=True)
        return []
