"""
User management endpoints.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.document import Document, DocumentStatus, UsageLog, UsageAction
from app.api.v1.endpoints.auth import get_current_user, UserResponse
from app.api.dependencies import require_permission
from app.core.config import settings

logger = logging.getLogger(__name__)


router = APIRouter()


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)


class UsageStats(BaseModel):
    scans_used: int
    scans_limit: int
    redlines_used: int


class DashboardStats(BaseModel):
    documents_analyzed: int
    total_risks_detected: int
    redlines_applied: int
    red_risks: int
    yellow_risks: int
    green_risks: int


@router.get("/me/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's usage statistics."""
    # Get usage for current month
    first_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0)
    
    result = await db.execute(
        select(func.count(UsageLog.id))
        .where(UsageLog.user_id == current_user.id)
        .where(UsageLog.action == UsageAction.SCAN)
        .where(UsageLog.created_at >= first_of_month)
    )
    scans_used = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(UsageLog.id))
        .where(UsageLog.user_id == current_user.id)
        .where(UsageLog.action == UsageAction.REDLINE)
        .where(UsageLog.created_at >= first_of_month)
    )
    redlines_used = result.scalar() or 0
    
    # Determine limit based on tier (all 5 tiers)
    tier_limits = {
        "free": settings.FREE_TIER_SCANS,
        "starter": settings.STARTER_TIER_SCANS,
        "pro": settings.PRO_TIER_SCANS,
        "business": settings.BUSINESS_TIER_SCANS,
        "enterprise": settings.ENTERPRISE_INCLUDED_SCANS,
    }
    scans_limit = tier_limits.get(current_user.subscription_tier.value, settings.FREE_TIER_SCANS)
    
    return UsageStats(
        scans_used=scans_used,
        scans_limit=scans_limit,
        redlines_used=redlines_used,
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile."""
    if updates.name:
        current_user.name = updates.name

    await db.commit()
    await db.refresh(current_user)

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        subscription_tier=current_user.subscription_tier.value,
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
    )


@router.get("/me/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's dashboard statistics."""
    # Documents analyzed
    doc_count = await db.execute(
        select(func.count(Document.id))
        .where(Document.user_id == current_user.id)
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    documents_analyzed = doc_count.scalar() or 0

    # Total risks
    risk_sum = await db.execute(
        select(func.coalesce(func.sum(Document.total_risks), 0))
        .where(Document.user_id == current_user.id)
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    total_risks = risk_sum.scalar() or 0

    # Risk breakdown from JSONB
    docs_result = await db.execute(
        select(Document.risk_summary)
        .where(Document.user_id == current_user.id)
        .where(Document.status == DocumentStatus.COMPLETED)
        .where(Document.risk_summary.isnot(None))
    )
    summaries = docs_result.scalars().all()
    red = sum(s.get("red", 0) for s in summaries if s)
    yellow = sum(s.get("yellow", 0) for s in summaries if s)
    green = sum(s.get("green", 0) for s in summaries if s)

    # Redlines applied
    redline_count = await db.execute(
        select(func.count(UsageLog.id))
        .where(UsageLog.user_id == current_user.id)
        .where(UsageLog.action == UsageAction.REDLINE)
    )
    redlines_applied = redline_count.scalar() or 0

    return DashboardStats(
        documents_analyzed=documents_analyzed,
        total_risks_detected=total_risks,
        redlines_applied=redlines_applied,
        red_risks=red,
        yellow_risks=yellow,
        green_risks=green,
    )


@router.get("/org/stats", response_model=DashboardStats)
async def get_org_stats(
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db)
):
    """Get organization-wide dashboard statistics."""
    if not current_user.organization_id:
        return DashboardStats(
            documents_analyzed=0, total_risks_detected=0, redlines_applied=0,
            red_risks=0, yellow_risks=0, green_risks=0,
        )

    # Use subquery to avoid N+1 (no separate fetch of user_ids list)
    user_ids_subq = select(User.id).where(
        User.organization_id == current_user.organization_id
    ).scalar_subquery()

    # Documents analyzed
    doc_count = await db.execute(
        select(func.count(Document.id))
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    documents_analyzed = doc_count.scalar() or 0

    # Total risks
    risk_sum = await db.execute(
        select(func.coalesce(func.sum(Document.total_risks), 0))
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    total_risks = risk_sum.scalar() or 0

    # Risk breakdown
    docs_result = await db.execute(
        select(Document.risk_summary)
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.status == DocumentStatus.COMPLETED)
        .where(Document.risk_summary.isnot(None))
    )
    summaries = docs_result.scalars().all()
    red = sum(s.get("red", 0) for s in summaries if s)
    yellow = sum(s.get("yellow", 0) for s in summaries if s)
    green = sum(s.get("green", 0) for s in summaries if s)

    # Redlines applied
    redline_count = await db.execute(
        select(func.count(UsageLog.id))
        .where(UsageLog.user_id.in_(user_ids_subq))
        .where(UsageLog.action == UsageAction.REDLINE)
    )
    redlines_applied = redline_count.scalar() or 0

    return DashboardStats(
        documents_analyzed=documents_analyzed,
        total_risks_detected=total_risks,
        redlines_applied=redlines_applied,
        red_risks=red,
        yellow_risks=yellow,
        green_risks=green,
    )


@router.delete("/me")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete current user's account (GDPR compliance).

    Performs a soft delete: anonymizes PII and deactivates the account.
    The user record is retained for audit trail integrity.
    """
    logger.info("Account deletion requested for user id=%s", str(current_user.id)[:8])

    # Soft delete — anonymize PII and deactivate
    current_user.email = f"deleted_{current_user.id}@deleted.local"
    current_user.name = "Deleted User"
    current_user.is_active = False

    await db.commit()

    return {"message": "Account deleted successfully"}
