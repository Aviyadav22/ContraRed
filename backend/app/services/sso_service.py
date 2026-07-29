"""
SSO Service — WorkOS-based SAML/OIDC brokering.

Supports Azure AD, Okta, Google Workspace, and any SAML 2.0 IdP via WorkOS.
Gracefully degrades when WORKOS_API_KEY is not configured (returns helpful errors).

Flow:
    1. GET /sso/authorize?org_id=X  -> redirect URL to IdP
    2. POST /sso/callback           -> verify code, create/link user, issue JWT
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.organization import Organization
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WorkOS availability check (graceful degradation like Redis)
# ---------------------------------------------------------------------------
_workos_client = None
_workos_available = False

try:
    import workos
    if getattr(settings, "WORKOS_API_KEY", "") and getattr(settings, "WORKOS_CLIENT_ID", ""):
        _workos_client = workos.WorkOSClient(
            api_key=settings.WORKOS_API_KEY,
            client_id=settings.WORKOS_CLIENT_ID,
        )
        _workos_available = True
        logger.info("WorkOS SSO client initialized successfully")
    else:
        logger.info("WorkOS credentials not configured — SSO features disabled")
except ImportError:
    logger.info("workos-python package not installed — SSO features disabled")
except Exception as e:
    logger.warning("WorkOS initialization failed: %s", e)


def is_sso_available() -> bool:
    """Check if SSO is available (WorkOS configured)."""
    return _workos_available


# ---------------------------------------------------------------------------
# Core SSO functions
# ---------------------------------------------------------------------------

async def get_authorization_url(
    org_id: uuid.UUID,
    db: AsyncSession,
    redirect_uri: str,
    state: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generate an SSO authorization URL for the given organization.

    Args:
        org_id: Organization UUID
        db: Database session
        redirect_uri: Where WorkOS should redirect after IdP auth
        state: Optional opaque state string for CSRF protection

    Returns:
        (authorization_url, state) — caller should redirect the user

    Raises:
        ValueError: If SSO not available or org not configured for SSO
    """
    if not _workos_available or not _workos_client:
        raise ValueError(
            "SSO is not configured. Set WORKOS_API_KEY and WORKOS_CLIENT_ID."
        )

    # Fetch org
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise ValueError(f"Organization {org_id} not found")

    if not org.sso_enabled:
        raise ValueError(f"SSO is not enabled for organization '{org.name}'")

    # Determine the WorkOS connection/organization identifier
    workos_org_id = org.workos_org_id
    if not workos_org_id:
        raise ValueError(
            f"Organization '{org.name}' has SSO enabled but no WorkOS organization ID configured. "
            "An admin must complete SSO setup in the dashboard."
        )

    # Generate authorization URL via WorkOS
    try:
        generated_state = state or str(uuid.uuid4())
        authorization_url = _workos_client.sso.get_authorization_url(
            organization_id=workos_org_id,
            redirect_uri=redirect_uri,
            state=generated_state,
        )
        logger.info("SSO authorization URL generated for org %s", org.name)
        return authorization_url, generated_state
    except Exception as e:
        logger.error("WorkOS authorization URL generation failed: %s", e, exc_info=True)
        raise ValueError(f"Failed to generate SSO login URL: {e}")


async def handle_sso_callback(
    code: str,
    db: AsyncSession,
) -> Tuple[User, Organization, bool]:
    """
    Handle the SSO callback from WorkOS.

    Verifies the authorization code, retrieves the user profile from the IdP,
    and either links to an existing user or creates a new one.

    Args:
        code: Authorization code from WorkOS callback
        db: Database session

    Returns:
        (user, organization, is_new_user)

    Raises:
        ValueError: On verification failure or configuration issues
    """
    if not _workos_available or not _workos_client:
        raise ValueError("SSO is not configured")

    # Exchange code for profile
    try:
        profile_and_token = _workos_client.sso.get_profile_and_token(code)
        profile = profile_and_token.profile
    except Exception as e:
        logger.error("WorkOS SSO callback verification failed: %s", e, exc_info=True)
        raise ValueError(f"SSO verification failed: {e}")

    # Extract profile data
    email = profile.email
    name = getattr(profile, "first_name", "") or ""
    last_name = getattr(profile, "last_name", "") or ""
    full_name = f"{name} {last_name}".strip() or email.split("@")[0]
    idp_id = profile.id  # WorkOS profile ID
    workos_org_id = getattr(profile, "organization_id", None)

    # Find the organization by WorkOS org ID
    org = None
    if workos_org_id:
        result = await db.execute(
            select(Organization).where(Organization.workos_org_id == workos_org_id)
        )
        org = result.scalar_one_or_none()

    # Fallback: try to find org by email domain
    if not org and email:
        domain = email.split("@")[-1].lower()
        result = await db.execute(
            select(Organization).where(Organization.domain == domain)
        )
        org = result.scalar_one_or_none()

    if not org:
        raise ValueError(
            "No matching organization found for this SSO login. "
            "Contact your administrator to configure SSO."
        )

    if not org.sso_enabled:
        raise ValueError(f"SSO is not enabled for organization '{org.name}'")

    # Find or create user
    is_new_user = False
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user:
        # Link SSO provider ID if not already set
        if not user.sso_provider_id:
            user.sso_provider_id = idp_id

        # Guard against silent org reassignment
        if user.organization_id and user.organization_id != org.id:
            logger.warning("SSO login attempted for user %s who belongs to different org", user.id)
            raise ValueError("User already belongs to a different organization. Contact support to transfer accounts.")

        # Activate user if inactive
        if not user.is_active:
            user.is_active = True

        user.is_verified = True  # SSO users are inherently verified
    else:
        # Create new user from SSO
        is_new_user = True
        user = User(
            email=email,
            name=full_name,
            password_hash=None,  # SSO users don't have passwords
            role=UserRole.REVIEWER,  # Default role for SSO-provisioned users
            organization_id=org.id,
            sso_provider_id=idp_id,
            is_active=True,
            is_verified=True,
        )
        db.add(user)

    await db.flush()

    logger.info(
        "SSO %s user %s for org %s",
        "created" if is_new_user else "authenticated", email, org.name,
    )

    return user, org, is_new_user


async def get_org_sso_status(org_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    Get the SSO configuration status for an organization.

    Returns a dict with SSO status info (safe for API response).
    """
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise ValueError(f"Organization {org_id} not found")

    return {
        "sso_enabled": org.sso_enabled,
        "sso_provider": org.sso_provider,
        "workos_configured": bool(org.workos_org_id),
        "sso_available": _workos_available,
        "entra_tenant_id": org.entra_tenant_id,
    }


async def enable_sso_for_org(
    org_id: uuid.UUID,
    workos_org_id: str,
    sso_provider: str,
    db: AsyncSession,
) -> Organization:
    """
    Enable SSO for an organization.

    Args:
        org_id: Organization UUID
        workos_org_id: The WorkOS organization ID from the WorkOS dashboard
        sso_provider: Provider name ("azure_ad", "okta", "google")
        db: Database session
    """
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise ValueError(f"Organization {org_id} not found")

    org.sso_enabled = True
    org.workos_org_id = workos_org_id
    org.sso_provider = sso_provider
    await db.flush()

    logger.info("SSO enabled for org %s (provider: %s)", org.name, sso_provider)
    return org


async def disable_sso_for_org(org_id: uuid.UUID, db: AsyncSession) -> Organization:
    """Disable SSO for an organization."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise ValueError(f"Organization {org_id} not found")

    org.sso_enabled = False
    # Keep workos_org_id for potential re-enable
    await db.flush()

    logger.info("SSO disabled for org %s", org.name)
    return org
