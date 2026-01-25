"""
User management endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user, UserResponse


router = APIRouter()


class UserUpdate(BaseModel):
    name: str | None = None
    

class UsageStats(BaseModel):
    scans_used: int
    scans_limit: int
    redlines_used: int


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
