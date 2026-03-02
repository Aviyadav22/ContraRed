"""
Team management endpoints.
Allows org admins to list, update roles, and remove team members.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.dependencies import require_admin
from app.models.audit_log import log_audit_event


router = APIRouter()


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    last_login: Optional[str] = None
    is_active: bool


class ChangeRoleRequest(BaseModel):
    role: str  # analyst, admin


@router.get("/members", response_model=List[TeamMemberResponse])
async def list_members(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users in the current organization. Requires ADMIN role."""
    if not current_user.organization_id:
        return []

    result = await db.execute(
        select(User).where(User.organization_id == current_user.organization_id)
    )
    members = result.scalars().all()

    return [
        TeamMemberResponse(
            id=str(m.id),
            email=m.email,
            name=m.name,
            role=m.role.value,
            last_login=m.last_login.isoformat() if m.last_login else None,
            is_active=m.is_active,
        )
        for m in members
    ]


@router.put("/members/{user_id}/role", response_model=TeamMemberResponse)
async def change_role(
    user_id: UUID,
    body: ChangeRoleRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Change a team member's role. Requires ADMIN role."""
    # Validate target role
    allowed_roles = {"analyst", "admin"}
    if body.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role must be one of: {', '.join(allowed_roles)}"
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
async def remove_member(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove a user from the organization. Requires ADMIN role."""
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
