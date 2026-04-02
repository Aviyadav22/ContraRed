"""
SSO Endpoints — SAML/OIDC authentication via WorkOS.

Endpoints:
    GET  /sso/authorize   — Redirect user to their IdP login
    POST /sso/callback    — Handle IdP callback, issue JWT
    GET  /sso/status      — Check SSO config for an organization
    POST /sso/enable      — Enable SSO for an organization (admin only)
    POST /sso/disable     — Disable SSO for an organization (admin only)
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.audit_log import log_audit_event
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.permissions import require_permission
from app.services import sso_service
from app.services.token_service import get_token_blacklist
from app.api.v1.endpoints.auth import limiter, get_current_user
from app.api.v1.endpoints.billing import require_tier

logger = logging.getLogger(__name__)

ALLOWED_REDIRECT_ORIGINS = [
    "https://contrared-dashboard.netlify.app",
    "https://contrared-addin.netlify.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "https://localhost:3000",
    "https://localhost:5173",
]


def _validate_redirect_uri(uri: str) -> bool:
    """Validate redirect URI against allowlist to prevent open redirect."""
    if not uri:
        return True  # Will use default callback
    from urllib.parse import urlparse
    parsed = urlparse(uri)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return origin in ALLOWED_REDIRECT_ORIGINS or origin in settings.CORS_ORIGINS

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SSOAuthorizeRequest(BaseModel):
    org_id: str = Field(..., description="Organization UUID")
    redirect_uri: Optional[str] = Field(None, description="Post-login redirect URI")


class SSOCallbackRequest(BaseModel):
    code: str = Field(..., description="Authorization code from WorkOS")
    state: str = Field(..., description="CSRF state parameter")
    state_sig: Optional[str] = Field(None, description="HMAC signature of state parameter")


class SSOStatusResponse(BaseModel):
    sso_enabled: bool
    sso_provider: Optional[str] = None
    workos_configured: bool
    sso_available: bool
    entra_tenant_id: Optional[str] = None


class SSOEnableRequest(BaseModel):
    org_id: str = Field(..., description="Organization UUID")
    workos_org_id: str = Field(..., description="WorkOS organization ID")
    sso_provider: str = Field(..., description="Provider: azure_ad, okta, google")


class SSODisableRequest(BaseModel):
    org_id: str = Field(..., description="Organization UUID")


class SSOLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    is_new_user: bool


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _sign_state(state: str) -> str:
    """Create an HMAC signature for SSO CSRF state parameter."""
    return hmac_mod.new(
        settings.SECRET_KEY.encode(), state.encode(), hashlib.sha256
    ).hexdigest()[:16]


def _verify_state_signature(state: str, signature: str) -> bool:
    """Verify the HMAC signature of the SSO CSRF state parameter."""
    expected = _sign_state(state)
    return hmac_mod.compare_digest(expected, signature)


def _get_client_ip(request: Request) -> Optional[str]:
    """Get real client IP, only trusting X-Forwarded-For from known proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and request.client:
        trusted_hosts = [h.strip() for h in settings.TRUSTED_PROXY_HOSTS.split(",") if h.strip()]
        if request.client.host in trusted_hosts:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/authorize")
@limiter.limit("10/minute")
async def sso_authorize(
    request: Request,
    org_id: str = Query(..., description="Organization UUID"),
    redirect_uri: Optional[str] = Query(None, description="Post-login redirect URI"),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate SSO login — redirects the user to their organization's IdP.

    The client calls this endpoint; the response is a redirect to the IdP.
    After authentication, the IdP redirects back to /sso/callback.
    """
    if redirect_uri and not _validate_redirect_uri(redirect_uri):
        raise HTTPException(status_code=400, detail="Invalid redirect URI")

    if not sso_service.is_sso_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO is not configured on this server. Contact your administrator.",
        )

    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID format",
        )

    # Default redirect URI (the callback endpoint on this server)
    callback_uri = redirect_uri or str(request.url_for("sso_callback"))

    # Generate CSRF state token
    state = secrets.token_urlsafe(32)

    try:
        authorization_url, returned_state = await sso_service.get_authorization_url(
            org_id=org_uuid,
            db=db,
            redirect_uri=callback_uri,
            state=state,
        )
    except ValueError as e:
        logger.error("SSO authorization failed for org %s: %s", org_id, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO authorization failed",
        )

    # Sign the state so callback can verify it server-side (prevents CSRF)
    state_signature = _sign_state(returned_state)
    return {
        "authorization_url": authorization_url,
        "state": returned_state,
        "state_sig": state_signature,
    }


@router.post("/callback", response_model=SSOLoginResponse)
@limiter.limit("10/minute")
async def sso_callback(
    request: Request,
    data: SSOCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle the SSO callback from WorkOS.

    Verifies the authorization code, creates/links the user, and returns
    JWT access + refresh tokens.
    """
    if not sso_service.is_sso_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO is not configured",
        )

    # Validate CSRF state parameter with server-side signature verification
    if not data.state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing CSRF state parameter",
        )

    # Verify state signature from body, cookie, or header
    state_sig = data.state_sig or request.cookies.get("sso_state_sig") or request.headers.get("X-SSO-State-Sig", "")
    if not state_sig or not _verify_state_signature(data.state, state_sig):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSRF state — possible replay or forgery",
        )

    try:
        user, org, is_new_user = await sso_service.handle_sso_callback(
            code=data.code,
            db=db,
        )
    except ValueError as e:
        logger.error("SSO callback failed: %s", e)
        await log_audit_event(
            db, user=None, action="sso_login_failed", resource_type="auth",
            resource_name="sso_callback", status="failure",
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            details=str(e),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SSO authentication failed",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    # Audit log
    await log_audit_event(
        db, user=user,
        action="sso_login_success" if not is_new_user else "sso_user_created",
        resource_type="auth",
        resource_name=user.email,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    # Session & IP tracking (same as password login)
    client_ip = _get_client_ip(request)
    try:
        blacklist = await get_token_blacklist()
        await blacklist.record_login_ip(str(user.id), client_ip)
    except Exception:
        pass  # Redis may be unavailable

    # Issue JWT tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "org_id": str(user.organization_id) if user.organization_id else None,
        "auth_method": "sso",
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Register session
    try:
        td = decode_token(access_token)
        if td and td.jti:
            await blacklist.register_session(str(user.id), td.jti)
    except Exception:
        pass

    return SSOLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=is_new_user,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "organization_id": str(user.organization_id) if user.organization_id else None,
        },
    )


@router.get("/status", response_model=SSOStatusResponse)
async def sso_status(
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SSO configuration status for an organization."""
    # Verify user belongs to the queried org (or is super_admin)
    if str(current_user.organization_id) != org_id and current_user.role.value != "super_admin":
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID format",
        )

    try:
        status_data = await sso_service.get_org_sso_status(org_uuid, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return SSOStatusResponse(**status_data)


@router.post("/enable")
async def sso_enable(
    request: Request,
    data: SSOEnableRequest,
    current_user: User = Depends(require_permission("sso.manage")),
    db: AsyncSession = Depends(get_db),
    _tier=Depends(require_tier("business")),
):
    """Enable SSO for an organization (requires sso.manage permission)."""
    try:
        org_uuid = uuid.UUID(data.org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID format",
        )

    # Verify user belongs to this org (or is super admin)
    if (
        current_user.organization_id != org_uuid
        and current_user.role.value != "super_admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage SSO for your own organization",
        )

    if data.sso_provider not in ("azure_ad", "okta", "google"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid SSO provider. Must be: azure_ad, okta, google",
        )

    try:
        org = await sso_service.enable_sso_for_org(
            org_id=org_uuid,
            workos_org_id=data.workos_org_id,
            sso_provider=data.sso_provider,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await log_audit_event(
        db, user=current_user, action="sso_enabled", resource_type="organization",
        resource_name=org.name,
        ip_address=_get_client_ip(request),
        details=f"provider={data.sso_provider}",
    )
    await db.commit()

    return {"message": f"SSO enabled for {org.name}", "provider": data.sso_provider}


@router.post("/disable")
async def sso_disable(
    request: Request,
    data: SSODisableRequest,
    current_user: User = Depends(require_permission("sso.manage")),
    db: AsyncSession = Depends(get_db),
    _tier=Depends(require_tier("business")),
):
    """Disable SSO for an organization (requires sso.manage permission)."""
    try:
        org_uuid = uuid.UUID(data.org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID format",
        )

    if (
        current_user.organization_id != org_uuid
        and current_user.role.value != "super_admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage SSO for your own organization",
        )

    try:
        org = await sso_service.disable_sso_for_org(org_uuid, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await log_audit_event(
        db, user=current_user, action="sso_disabled", resource_type="organization",
        resource_name=org.name,
        ip_address=_get_client_ip(request),
    )
    await db.commit()

    return {"message": f"SSO disabled for {org.name}"}
