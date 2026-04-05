"""
Consent Enforcement Middleware — blocks requests to protected endpoints
when the user has not granted the required consent purpose.

Declarative path-to-purpose mapping makes it easy to add new protected
routes. Uses Redis cache (when available) for O(1) consent checks.

Returns 403 with a machine-readable error when consent is missing,
enabling the frontend to show the appropriate consent prompt.
"""

import logging
import re
from typing import Dict, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Declarative mapping: URL path patterns → required consent purpose codes.
# If ANY listed purpose is not granted, the request is blocked.
CONSENT_REQUIREMENTS: Dict[str, List[str]] = {
    # AI-powered document analysis
    r"/api/v1/documents/analyze": ["contract_analysis"],
    r"/api/v1/documents/clause-analyze": ["contract_analysis"],
    r"/api/v1/documents/batch": ["contract_analysis"],
    # AI-powered contract drafting
    r"/api/v1/drafting/": ["ai_drafting"],
    # AI review agent
    r"/api/v1/agent/": ["contract_analysis"],
    # Billing endpoints
    r"/api/v1/billing/": ["billing"],
    # SSO endpoints
    r"/api/v1/sso/": ["sso_integration"],
}

# Paths that should never be blocked by consent checks
EXEMPT_PATHS = frozenset({
    "/health", "/health/db", "/health/deep",
    "/docs", "/openapi.json", "/redoc",
    "/api/v1/auth/",
    "/api/v1/consent/",
    "/api/v1/rights/",
    "/api/v1/grievances/",
})

# Compile patterns once at import time
_COMPILED_REQUIREMENTS = [
    (re.compile(pattern), purposes)
    for pattern, purposes in CONSENT_REQUIREMENTS.items()
]


class ConsentEnforcementMiddleware(BaseHTTPMiddleware):
    """Enforce consent requirements on protected API endpoints.

    Runs after TenantContextMiddleware (needs user_id from request.state).
    Checks consent grants via the consent service, using Redis cache.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.rstrip("/")

        # Skip exempt paths
        for exempt in EXEMPT_PATHS:
            if path.startswith(exempt.rstrip("/")):
                return await call_next(request)

        # Skip non-API paths and safe methods on some paths
        if not path.startswith("/api/v1/"):
            return await call_next(request)

        # Only enforce on state-changing methods and POST (which is how analysis works)
        # GET requests for listing/viewing are generally allowed
        if request.method in ("GET", "HEAD", "OPTIONS") and not self._is_processing_endpoint(path):
            return await call_next(request)

        # Find required purposes for this path
        required_purposes = self._match_purposes(path)
        if not required_purposes:
            return await call_next(request)

        # Get user ID from request state (set by TenantContextMiddleware)
        user_id = getattr(request.state, "tenant_user_id", None)
        if not user_id:
            # No authenticated user — let the auth dependency handle 401
            return await call_next(request)

        # Check consent for each required purpose
        import uuid
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except (ValueError, TypeError):
            return await call_next(request)

        missing_purposes = []
        for purpose_code in required_purposes:
            granted = await self._check_consent(user_uuid, purpose_code)
            if not granted:
                missing_purposes.append(purpose_code)

        if missing_purposes:
            # Auto-grant for existing users who registered before consent system
            # (they have no consent record at all — implied consent from prior usage)
            has_any_record = await self._has_any_consent_record(user_uuid)
            if not has_any_record:
                await self._auto_grant_existing_user(user_uuid, missing_purposes)
                return await call_next(request)
            logger.info(
                "Consent enforcement: blocked %s %s for user %s — missing: %s",
                request.method, path, user_id, missing_purposes,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "consent_required",
                    "detail": "This action requires your consent for the following purposes.",
                    "required_purposes": missing_purposes,
                    "consent_url": "/settings/privacy",
                    "api_grant_url": "/api/v1/consent/grant",
                },
            )

        return await call_next(request)

    def _match_purposes(self, path: str) -> List[str]:
        """Match a request path against consent requirements."""
        for pattern, purposes in _COMPILED_REQUIREMENTS:
            if pattern.search(path):
                return purposes
        return []

    def _is_processing_endpoint(self, path: str) -> bool:
        """Check if this is a data-processing endpoint that needs consent even for GET."""
        # Analysis/drafting endpoints always need consent
        processing_patterns = ["/documents/analyze", "/drafting/", "/agent/"]
        return any(p in path for p in processing_patterns)

    async def _check_consent(self, user_id, purpose_code: str) -> bool:
        """Check consent via service (which uses Redis cache internally)."""
        try:
            from app.services.consent_service import consent_service
            from app.db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                return await consent_service.check_consent(session, user_id, purpose_code)
        except Exception as e:
            # Fail open: if consent check fails, allow the request
            logger.error("Consent check failed (allowing request): %s", e)
            return True

    async def _has_any_consent_record(self, user_id) -> bool:
        """Check if user has ANY consent record (new vs legacy user)."""
        try:
            from app.db.session import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM consent_records WHERE subject_id = :uid"),
                    {"uid": user_id},
                )
                count = result.scalar() or 0
                logger.debug("Consent record count for %s: %d", user_id, count)
                return count > 0
        except Exception as e:
            logger.error("Consent record check failed: %s", e)
            return False  # If check fails, try auto-grant anyway

    async def _auto_grant_existing_user(self, user_id, purpose_codes: list):
        """Auto-grant consent for a legacy user who registered before consent system."""
        try:
            from app.db.session import AsyncSessionLocal
            from sqlalchemy import text, select
            from app.models.consent import (
                ConsentPurpose, ConsentRecord, ConsentPurposeGrant,
                ConsentEvent, ConsentStatus,
            )
            from datetime import datetime, timezone
            import uuid as uuid_mod

            now = datetime.now(timezone.utc)

            async with AsyncSessionLocal() as session:
                # Create consent record directly (bypass service to avoid flush/commit issues)
                record = ConsentRecord(
                    subject_id=user_id,
                    status=ConsentStatus.ACTIVE.value,
                    collection_method="auto_migration",
                    expression_method="implied",
                    consent_metadata={"reason": "legacy_user_auto_migration"},
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
                await session.flush()

                # Get all active purposes
                result = await session.execute(
                    select(ConsentPurpose).where(ConsentPurpose.is_active == True)
                )
                purposes = result.scalars().all()

                # Grant each purpose
                for purpose in purposes:
                    grant = ConsentPurposeGrant(
                        consent_record_id=record.id,
                        purpose_id=purpose.id,
                        purpose_code=purpose.purpose_code,
                        granted=True,
                        granted_at=now,
                        created_at=now,
                    )
                    session.add(grant)

                await session.commit()

            logger.info("Auto-granted consent for legacy user %s (%d purposes)", user_id, len(purposes))
        except Exception as e:
            logger.error("Auto-grant consent failed for %s: %s", user_id, e, exc_info=True)
