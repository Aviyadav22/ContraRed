"""
Tenant-aware database session dependency.

Usage in endpoints:
    db: AsyncSession = Depends(get_tenant_db)

This dependency chains get_db + get_current_user and sets PostgreSQL
session variables for Row-Level Security enforcement.
"""

import logging
from typing import AsyncGenerator

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User, UserRole
from app.middleware.tenant_context import set_tenant_context

logger = logging.getLogger(__name__)

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def _get_current_user_for_tenant(
    request: Request,
    token: str = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Lazy-load get_current_user to avoid circular import."""
    from app.api.v1.endpoints.auth import get_current_user
    return await get_current_user(request=request, token=token, db=db)


async def get_tenant_db(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user_for_tenant),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a tenant-scoped database session.

    Sets PostgreSQL session variables so RLS policies automatically
    filter rows to the current user's organization.
    """
    is_super = current_user.role in (UserRole.SUPER_ADMIN,)
    await set_tenant_context(
        db=db,
        user_id=str(current_user.id),
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        is_super_admin=is_super,
    )
    yield db
