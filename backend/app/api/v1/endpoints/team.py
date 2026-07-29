"""
Team management endpoints.
Allows org admins to list, update roles, and remove team members.
"""

from typing import List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.dependencies import require_permission
from app.models.audit_log import log_audit_event
from app.api.v1.endpoints.auth import limiter
from app.api.v1.endpoints.billing import require_tier


router = APIRouter()


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    last_login: Optional[str] = None
    is_active: bool


class TeamListResponse(BaseModel):
    items: List[TeamMemberResponse]
    total: int


class ChangeRoleRequest(BaseModel):
    role: Literal["analyst", "admin"]


@router.get("/members", response_model=TeamListResponse)
async def list_members(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("team.read")),
    db: AsyncSession = Depends(get_db)
):
    """List all users in the current organization with pagination."""
    if not current_user.organization_id:
        return TeamListResponse(items=[], total=0)

    # Total count
    count_result = await db.execute(
        select(func.count(User.id)).where(User.organization_id == current_user.organization_id)
    )
    total = count_result.scalar() or 0

    # Paginated results
    result = await db.execute(
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .offset(offset)
        .limit(limit)
    )
    members = result.scalars().all()

    return TeamListResponse(
        items=[
            TeamMemberResponse(
                id=str(m.id),
                email=m.email,
                name=m.name,
                role=m.role.value,
                last_login=m.last_login.isoformat() if m.last_login else None,
                is_active=m.is_active,
            )
            for m in members
        ],
        total=total,
    )


@router.put("/members/{user_id}/role", response_model=TeamMemberResponse)
@limiter.limit("10/minute")
async def change_role(
    user_id: UUID,
    body: ChangeRoleRequest,
    request: Request,
    current_user: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db),
    _tier=Depends(require_tier("pro")),
):
    """Change a team member's role."""
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=403,
            detail="Organization membership is required to manage a team.",
        )
    # Find target user
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Must be in same org
    if target_user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Cannot modify users outside your organization")

    # Cannot change own role
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    old_role = target_user.role.value
    target_user.role = UserRole(body.role)

    # Audit log
    await log_audit_event(
        db, user=current_user, action="role_changed", resource_type="user",
        resource_name=target_user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details=f'{{"old_role": "{old_role}", "new_role": "{body.role}", "target_user_id": "{user_id}"}}',
    )

    await db.commit()
    await db.refresh(target_user)

    return TeamMemberResponse(
        id=str(target_user.id),
        email=target_user.email,
        name=target_user.name,
        role=target_user.role.value,
        last_login=target_user.last_login.isoformat() if target_user.last_login else None,
        is_active=target_user.is_active,
    )


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def remove_member(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("team.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Remove a user from the organization."""
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=403,
            detail="Organization membership is required to manage a team.",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Cannot modify users outside your organization")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the organization")

    # Remove from org (don't delete the user account)
    target_user.organization_id = None

    # Audit log
    await log_audit_event(
        db, user=current_user, action="member_removed", resource_type="user",
        resource_name=target_user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await db.commit()
