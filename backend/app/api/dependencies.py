"""
RBAC permission dependencies for FastAPI.

Role hierarchy: ANALYST (+ legacy USER) < ADMIN < SUPER_ADMIN

Usage:
    current_user: User = Depends(require_role(UserRole.ADMIN))
"""

from fastapi import Depends, HTTPException, status
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user


# Role hierarchy levels
ROLE_HIERARCHY = {
    UserRole.USER: 0,        # Legacy — same level as ANALYST
    UserRole.ANALYST: 0,
    UserRole.ADMIN: 1,
    UserRole.SUPER_ADMIN: 2,
}


def require_role(minimum_role: UserRole):
    """Dependency factory: require minimum role level."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role.value} role or higher",
            )
        return current_user
    return _check


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Shortcut dependency: require ADMIN or higher."""
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    if user_level < ROLE_HIERARCHY[UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
