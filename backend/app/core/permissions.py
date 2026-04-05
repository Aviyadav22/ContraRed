"""
Granular RBAC Permission System for ContraRed.

5-tier role hierarchy:
    VIEWER (0) < REVIEWER (1) < MANAGER (2) < ADMIN (3) < SUPER_ADMIN (4)

Legacy mapping:
    USER   -> VIEWER  (level 0)
    ANALYST -> REVIEWER (level 1)

Each role is assigned a set of granular permissions (20+).
`require_permission("document.write")` is a FastAPI dependency that checks
whether the current user's role grants the requested permission.
"""

from __future__ import annotations

import logging
from typing import Set, Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.db.session import get_db

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role hierarchy levels
# ---------------------------------------------------------------------------
ROLE_HIERARCHY: Dict[UserRole, int] = {
    # Legacy roles (backward compat)
    UserRole.USER: 0,
    UserRole.ANALYST: 1,
    # New 5-tier roles
    UserRole.VIEWER: 0,
    UserRole.REVIEWER: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
    UserRole.SUPER_ADMIN: 4,
}

# ---------------------------------------------------------------------------
# Granular permission definitions
# ---------------------------------------------------------------------------
# fmt: off
PERMISSIONS = {
    # Documents
    "document.read",
    "document.write",
    "document.delete",
    "document.export",

    # Playbooks
    "playbook.read",
    "playbook.write",
    "playbook.admin",       # Manage org-wide playbooks

    # Clauses & Templates
    "clause.read",
    "clause.write",
    "template.read",
    "template.write",

    # Team
    "team.read",
    "team.manage",          # Invite / remove members

    # Users
    "user.invite",
    "user.manage",          # Promote / demote / deactivate

    # Billing
    "billing.read",
    "billing.manage",

    # Analytics
    "analytics.read",
    "analytics.export",

    # Audit
    "audit.read",

    # Settings & SSO
    "settings.read",
    "settings.manage",
    "sso.manage",

    # Org-level
    "org.manage",

    # API keys
    "api_keys.manage",
}
# fmt: on

# ---------------------------------------------------------------------------
# Role -> Permission mapping
# ---------------------------------------------------------------------------
_VIEWER_PERMS: Set[str] = {
    "document.read",
    "playbook.read",
    "clause.read",
    "template.read",
    "analytics.read",
    "team.read",
    "settings.read",
}

_REVIEWER_PERMS: Set[str] = _VIEWER_PERMS | {
    "document.write",
    "document.export",
    "playbook.write",
    "clause.write",
    "template.write",
}

_MANAGER_PERMS: Set[str] = _REVIEWER_PERMS | {
    "document.delete",
    "playbook.admin",
    "team.manage",
    "user.invite",
    "analytics.export",
    "audit.read",
}

_ADMIN_PERMS: Set[str] = _MANAGER_PERMS | {
    "user.manage",
    "billing.read",
    "billing.manage",
    "settings.manage",
    "sso.manage",
    "org.manage",
    "api_keys.manage",
}

_SUPER_ADMIN_PERMS: Set[str] = PERMISSIONS.copy()  # All permissions

ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    # Legacy roles map to their modern equivalents
    UserRole.USER: _VIEWER_PERMS,
    UserRole.ANALYST: _REVIEWER_PERMS,
    # New 5-tier roles
    UserRole.VIEWER: _VIEWER_PERMS,
    UserRole.REVIEWER: _REVIEWER_PERMS,
    UserRole.MANAGER: _MANAGER_PERMS,
    UserRole.ADMIN: _ADMIN_PERMS,
    UserRole.SUPER_ADMIN: _SUPER_ADMIN_PERMS,
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def get_role_level(role: UserRole) -> int:
    """Return the numeric hierarchy level for a role."""
    return ROLE_HIERARCHY.get(role, 0)


def role_has_permission(role: UserRole, permission: str) -> bool:
    """Check if a role grants a specific permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms


def get_permissions_for_role(role: UserRole) -> Set[str]:
    """Return all permissions granted to a role."""
    return ROLE_PERMISSIONS.get(role, set()).copy()


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
def require_permission(permission: str):
    """
    FastAPI dependency factory: require a specific granular permission.

    Usage:
        @router.post("/documents")
        async def create_doc(user: User = Depends(require_permission("document.write"))):
            ...
    """
    if permission not in PERMISSIONS:
        logger.warning(f"Unknown permission requested: {permission}")

    async def _check(current_user: User = Depends(_get_current_user_lazy)) -> User:
        if not role_has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission}'",
            )
        return current_user

    return _check


def require_role(minimum_role: UserRole):
    """
    FastAPI dependency factory: require minimum role level.

    Backward-compatible with the old `require_role` in dependencies.py.
    """
    required_level = get_role_level(minimum_role)

    async def _check(current_user: User = Depends(_get_current_user_lazy)) -> User:
        user_level = get_role_level(current_user.role)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role.value} role or higher",
            )
        return current_user

    return _check


def require_any_permission(*permissions: str):
    """
    FastAPI dependency factory: require at least ONE of the listed permissions.

    Usage:
        @router.get("/reports")
        async def reports(user: User = Depends(require_any_permission("analytics.read", "audit.read"))):
            ...
    """
    async def _check(current_user: User = Depends(_get_current_user_lazy)) -> User:
        user_perms = get_permissions_for_role(current_user.role)
        if not user_perms.intersection(permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires one of {list(permissions)}",
            )
        return current_user

    return _check


# ---------------------------------------------------------------------------
# Lazy import to avoid circular dependency with auth.py
# ---------------------------------------------------------------------------
async def _get_current_user_lazy(
    request: Request,
    token: str = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Lazy-load get_current_user to break circular import with auth.py.

    Mirrors the same dependency signature and delegates at call-time.
    """
    from app.api.v1.endpoints.auth import get_current_user
    return await get_current_user(request=request, token=token, db=db)
