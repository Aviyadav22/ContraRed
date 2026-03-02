"""
User management endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.document import Document, DocumentStatus, UsageLog, UsageAction
from app.api.v1.endpoints.auth import get_current_user, UserResponse
from app.api.dependencies import require_admin
from app.core.config import settings


router = APIRouter()


class UserUpdate(BaseModel):
    name: str | None = None


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
    from app.models.document import UsageLog, UsageAction
    from sqlalchemy import func
    from datetime import datetime
    
    # Get usage for current month
    first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    
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
    
    # Determine limit based on tier
    from app.core.config import settings
    if current_user.subscription_tier.value == "free":
        scans_limit = settings.FREE_TIER_SCANS
    elif current_user.subscription_tier.value == "pro":
        scans_limit = settings.PRO_TIER_SCANS
    else:
        scans_limit = settings.ENTERPRISE_INCLUDED_SCANS
    
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
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get organization-wide dashboard statistics. Requires ADMIN role."""
    if not current_user.organization_id:
        return DashboardStats(
            documents_analyzed=0, total_risks_detected=0, redlines_applied=0,
            red_risks=0, yellow_risks=0, green_risks=0,
        )

    # Get all user IDs in the org
    org_users = await db.execute(
        select(User.id).where(User.organization_id == current_user.organization_id)
    )
    user_ids = [uid for uid in org_users.scalars().all()]

    if not user_ids:
        return DashboardStats(
            documents_analyzed=0, total_risks_detected=0, redlines_applied=0,
            red_risks=0, yellow_risks=0, green_risks=0,
        )

    # Documents analyzed
    doc_count = await db.execute(
        select(func.count(Document.id))
        .where(Document.user_id.in_(user_ids))
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    documents_analyzed = doc_count.scalar() or 0

    # Total risks
    risk_sum = await db.execute(
        select(func.coalesce(func.sum(Document.total_risks), 0))
        .where(Document.user_id.in_(user_ids))
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    total_risks = risk_sum.scalar() or 0

    # Risk breakdown
    docs_result = await db.execute(
        select(Document.risk_summary)
        .where(Document.user_id.in_(user_ids))
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
        .where(UsageLog.user_id.in_(user_ids))
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
