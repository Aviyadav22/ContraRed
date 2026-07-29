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
            granted = await self._check_consent(request, user_uuid, purpose_code)
            if granted is None:
                logger.error(
                    "Consent enforcement unavailable for %s %s; blocking protected processing",
                    request.method,
                    path,
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "consent_check_unavailable",
                        "detail": "Consent could not be verified. Please try again.",
                    },
                )
            if not granted:
                missing_purposes.append(purpose_code)

        if missing_purposes:
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

    async def _check_consent(
        self,
        request: Request,
        user_id,
        purpose_code: str,
    ) -> Optional[bool]:
        """Check consent using the application's configured session factory.

        Production falls back to ``AsyncSessionLocal``. Tests and alternate
        deployments can inject the same session factory used by request
        dependencies through ``app.state.consent_session_factory`` so consent
        checks never silently query a different database.
        """
        try:
            from app.services.consent_service import consent_service
            from app.db.session import AsyncSessionLocal

            session_factory = getattr(
                request.app.state,
                "consent_session_factory",
                AsyncSessionLocal,
            )
            async with session_factory() as session:
                return await consent_service.check_consent(session, user_id, purpose_code)
        except Exception as e:
            # Protected processing must not proceed when consent cannot be verified.
            logger.error("Consent check failed: %s", e)
            return None
