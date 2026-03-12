"""
RBAC permission dependencies for FastAPI.

5-tier role hierarchy:
    VIEWER (+ legacy USER) < REVIEWER (+ legacy ANALYST) < MANAGER < ADMIN < SUPER_ADMIN

This module re-exports the new granular permission system from
`app.core.permissions` for backward compatibility, and adds convenience
shortcuts used across the codebase.

Usage (new — preferred):
    current_user: User = Depends(require_permission("document.write"))

Usage (legacy — still works):
    current_user: User = Depends(require_role(UserRole.ADMIN))
    current_user: User = Depends(require_admin)
"""

from fastapi import Depends, HTTPException, status

from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user

# Re-export the new permission system for backward compatibility
from app.core.permissions import (  # noqa: F401
    ROLE_HIERARCHY,
    ROLE_PERMISSIONS,
    PERMISSIONS,
    get_role_level,
    role_has_permission,
    get_permissions_for_role,
    require_permission,
    require_role,
    require_any_permission,
)


# ---------------------------------------------------------------------------
# Convenience shortcuts (backward compat)
# ---------------------------------------------------------------------------

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Shortcut dependency: require ADMIN or higher."""
    user_level = get_role_level(current_user.role)
    if user_level < get_role_level(UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_manager(current_user: User = Depends(get_current_user)) -> User:
    """Shortcut dependency: require MANAGER or higher."""
    user_level = get_role_level(current_user.role)
    if user_level < get_role_level(UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required",
        )
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Shortcut dependency: require SUPER_ADMIN."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user
