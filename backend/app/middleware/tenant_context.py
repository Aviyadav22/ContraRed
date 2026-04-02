"""
Tenant Context Middleware — sets PostgreSQL session variables for Row-Level Security.

Three-layer multi-tenancy:
  1. PostgreSQL RLS policies use session variables (app.current_org_id, app.current_user_id)
  2. This middleware extracts tenant info from JWT and sets PG session vars
  3. The get_tenant_db dependency also sets these vars for explicit RLS

The middleware runs on every request that has a valid JWT token.
If no token is present (public endpoints), RLS variables are not set,
and the DB connection uses default restrictive policies.
"""

import logging
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Paths that never carry a JWT — skip parsing to avoid overhead
_PUBLIC_PATHS = frozenset({
    "/health", "/health/db", "/health/deep", "/docs", "/openapi.json", "/redoc",
})


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Set PostgreSQL session variables from JWT for RLS enforcement.

    Lightweight JWT claim extraction (no DB lookup, no full auth).
    The real auth validation happens in the endpoint dependency —
    this middleware only sets PG session vars so that RLS policies
    activate on *every* query, not just those using ``get_tenant_db``.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip public/health endpoints
        path = request.url.path.rstrip("/")
        if path in _PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Extract JWT from Authorization header (lightweight — no DB call)
        user_id: Optional[str] = None
        org_id: Optional[str] = None
        is_super_admin = False

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]
            try:
                from app.core.security import decode_token
                token_data = decode_token(raw_token)
                if token_data:
                    user_id = token_data.user_id
                    org_id = token_data.organization_id
                    is_super_admin = token_data.role == "super_admin"
            except Exception:
                # If JWT is invalid, let the auth dependency handle the 401.
                pass

        # Fallback: try HttpOnly cookie if no Bearer token
        if not user_id:
            cookie_token = request.cookies.get("access_token")
            if cookie_token:
                try:
                    from app.core.security import decode_token
                    token_data = decode_token(cookie_token)
                    if token_data:
                        user_id = token_data.user_id
                        org_id = token_data.organization_id
                        is_super_admin = token_data.role == "super_admin"
                except Exception:
                    pass

        # Store in request state so downstream code can access without re-parsing
        request.state.tenant_user_id = user_id
        request.state.tenant_org_id = org_id
        request.state.tenant_is_super_admin = is_super_admin

        response = await call_next(request)
        return response


async def set_tenant_context(
    db,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    is_super_admin: bool = False,
):
    """
    Set PostgreSQL session variables for RLS policies.

    Called from the get_db dependency or directly in endpoints.
    Sets:
      - app.current_user_id
      - app.current_org_id
      - app.is_super_admin

    These variables are used by RLS policies created in migration 010.
    """
    try:
        if user_id:
            await db.execute(
                text("SELECT set_config('app.current_user_id', :val, true)"),
                {"val": str(user_id)},
            )
        if organization_id:
            await db.execute(
                text("SELECT set_config('app.current_org_id', :val, true)"),
                {"val": str(organization_id)},
            )
        if is_super_admin:
            await db.execute(
                text("SELECT set_config('app.is_super_admin', 'true', true)"),
            )
    except Exception as e:
        logger.error("Failed to set tenant context, aborting request: %s", e)
        raise


async def clear_tenant_context(db):
    """Clear PostgreSQL session variables (for connection recycling).

    Only reset the specific variables we set, not ALL session config,
    to avoid interfering with connection pool settings or other state.
    """
    try:
        await db.execute(text(
            "SELECT set_config('app.current_user_id', '', true), "
            "set_config('app.current_org_id', '', true), "
            "set_config('app.is_super_admin', 'false', true)"
        ))
    except Exception:
        pass
