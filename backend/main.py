"""
ContraRed Backend - AI Contract Redlining API

Main application entry point.
"""

import logging
import re
import time
import traceback
import uuid

# ---------------------------------------------------------------------------
# Sensitive Data Log Filter — must be installed BEFORE any logger is used
# ---------------------------------------------------------------------------

class SensitiveDataFilter(logging.Filter):
    """Redact PII and secrets from log records before they reach any handler.

    Patterns redacted:
    - Email addresses
    - JWT tokens (Bearer + raw eyJ... tokens)
    - Long base64 strings that may be API keys or secrets
    - Fragments that look like contract text (long quoted strings)
    """

    _EMAIL_RE = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    _BEARER_RE = re.compile(r'Bearer\s+[A-Za-z0-9\-_\.]+', re.IGNORECASE)
    _JWT_RE = re.compile(r'eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+')
    _API_KEY_RE = re.compile(r'(?:key|token|secret|password)[\s=:]+\S{16,}', re.IGNORECASE)
    # Quoted strings > 200 chars likely contain contract text
    _LONG_QUOTE_RE = re.compile(r'"[^"]{200,}"')

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact(a) if isinstance(a, str) else a for a in record.args)
        return True

    def _redact(self, text: str) -> str:
        text = self._EMAIL_RE.sub('[EMAIL_REDACTED]', text)
        text = self._BEARER_RE.sub('Bearer [TOKEN_REDACTED]', text)
        text = self._JWT_RE.sub('[JWT_REDACTED]', text)
        text = self._API_KEY_RE.sub('[SECRET_REDACTED]', text)
        text = self._LONG_QUOTE_RE.sub('"[CONTRACT_TEXT_REDACTED]"', text)
        return text


# Install the filter on the root logger so ALL loggers inherit it
_sensitive_filter = SensitiveDataFilter()
import os as _os
_log_level = getattr(logging, _os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(
    level=_log_level,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","function":"%(funcName)s","message":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logging.getLogger().addFilter(_sensitive_filter)

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import init_db

APP_VERSION = "1.4.0"

logger = logging.getLogger("contrared")


# =============================================================================
# Security Headers Middleware (CSP + HSTS + frame/content protection)
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses (SOC2 / OWASP)."""

    # Content-Security-Policy — restrictive default, allow inline styles for
    # Swagger UI when DEBUG is on.  In production docs are disabled anyway.
    _CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"  # Modern best practice: disable legacy XSS auditor
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Content-Security-Policy"] = self._CSP
        # Prevent browsers from MIME-sniffing the response away from the declared content-type
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        return response


# =============================================================================
# Request Logging Middleware
# =============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests for audit trail."""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response: Response = await call_next(request)
        duration = time.time() - start

        request_id = getattr(request.state, "request_id", "-")

        # Skip health check logs to reduce noise
        if not request.url.path.startswith("/health"):
            logger.info(
                "method=%s path=%s status=%d duration=%.3fs ip=%s request_id=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration,
                request.client.host if request.client else "unknown",
                request_id,
            )
        return response


# =============================================================================
# Global Exception Handler — strips PII from error responses
# =============================================================================

def _strip_pii_from_detail(detail: str) -> str:
    """Remove potential PII from error detail strings before sending to client."""
    # Remove email addresses
    detail = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED]', detail)
    # Remove things that look like tokens/keys
    detail = re.sub(r'eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', '[REDACTED]', detail)
    # Truncate very long messages (might contain contract text)
    if len(detail) > 500:
        detail = detail[:500] + "... [truncated]"
    return detail


# =============================================================================
# Application Setup
# =============================================================================

# ---------------------------------------------------------------------------
# Sentry integration (Phase 2.5) — optional, degrades gracefully
# ---------------------------------------------------------------------------
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        def _before_send(event, hint):
            """Strip PII from Sentry events before sending."""
            # Remove request body (may contain contract text)
            if "request" in event and "data" in event["request"]:
                event["request"]["data"] = "[REDACTED]"
            # Remove email from user context
            if "user" in event and "email" in event["user"]:
                event["user"]["email"] = "[REDACTED]"
            return event

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            before_send=_before_send,
            send_default_pii=False,
        )
        logger.info("Sentry initialized (env=%s)", settings.SENTRY_ENVIRONMENT)
    except ImportError:
        logger.info("sentry-sdk not installed — error monitoring disabled")
    except Exception as e:
        logger.warning("Sentry init failed: %s — error monitoring disabled", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Security: refuse to start with default SECRET_KEY in production
    if not settings.DEBUG and settings.SECRET_KEY == "your-secret-key-change-in-production":
        logger.critical("FATAL: SECRET_KEY is set to the default value in a non-DEBUG environment. "
                        "Set a strong SECRET_KEY environment variable before starting.")
        raise RuntimeError("Insecure SECRET_KEY — set SECRET_KEY env var before starting in production")
    # Startup - non-fatal DB init (app stays healthy even if DB is temporarily unreachable)
    try:
        await init_db()
    except Exception as e:
        logger.error("DB init failed on startup: %s. App will still start.", e)

    # Startup - connect token blacklist (non-fatal)
    try:
        from app.services.token_service import get_token_blacklist
        await get_token_blacklist()
    except Exception as e:
        logger.warning("Token blacklist init failed: %s — revocation disabled", e)

    # Startup - seed default playbooks if missing (non-fatal)
    try:
        from app.services.seed_defaults import seed_default_playbooks
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            n = await seed_default_playbooks(session)
            if n:
                logger.info("Seeded %d default playbook(s)", n)
    except Exception as e:
        logger.warning("Default playbook seeding failed: %s — app continues", e)

    # Startup - seed DPDP consent purposes and privacy policy (non-fatal)
    try:
        from app.services.seed_consent_defaults import seed_all_consent_defaults
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await seed_all_consent_defaults(session)
    except Exception as e:
        logger.warning("Consent defaults seeding failed: %s — app continues", e)

    yield

    # Shutdown
    from app.services.cache_service import shutdown_cache
    from app.services.token_service import shutdown_token_blacklist
    await shutdown_cache()
    await shutdown_token_blacklist()


app = FastAPI(
    title="ContraRed API",
    description="AI-powered contract redlining and review platform",
    version=APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Global exception handler — catch unhandled errors, strip PII from response
# ---------------------------------------------------------------------------

def _is_client_cancellation(exc: BaseException) -> bool:
    """True if this exception (or any cause in its chain) is a request cancellation.

    CancelledError propagates up when the client disconnects mid-request or an
    upstream proxy times out — typical on Render cold-starts where asyncpg's
    connect handshake is still in flight. SQLAlchemy wraps it as __cause__/__context__,
    so we walk the chain.
    """
    import asyncio as _a
    seen = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        if isinstance(cur, _a.CancelledError):
            return True
        seen.add(id(cur))
        cur = cur.__cause__ or cur.__context__
    return False


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions.

    - Logs the full traceback server-side (through the SensitiveDataFilter).
    - Returns a generic error to the client with PII stripped.
    - Adds CORS headers so browsers don't block the error response.
    """
    # Client disconnect / upstream cancellation: not a bug, don't spam error logs or return 500
    if _is_client_cancellation(exc):
        logger.warning(
            "Request cancelled on %s %s (client disconnect or upstream timeout)",
            request.method,
            request.url.path,
        )
        response = JSONResponse(
            status_code=503,
            content={"detail": "The server was still warming up. Please retry."},
        )
        origin = request.headers.get("origin")
        if origin and origin in settings.CORS_ORIGINS:
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        return response

    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    # In debug mode include the (redacted) error type; in production be opaque
    if settings.DEBUG:
        detail = _strip_pii_from_detail(f"{type(exc).__name__}: {exc}")
    else:
        detail = "An internal error occurred. Please try again later."

    response = JSONResponse(
        status_code=500,
        content={"detail": detail},
    )

    # Add CORS headers so browsers don't block error responses.
    # Exception handlers bypass CORSMiddleware, so we must add them manually.
    origin = request.headers.get("origin")
    if origin and origin in settings.CORS_ORIGINS:
        response.headers["access-control-allow-origin"] = origin
        response.headers["access-control-allow-credentials"] = "true"

    return response


# =============================================================================
# Request Body Size Limit Middleware
# =============================================================================

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests with body exceeding the configured limit.

    Note: True streaming/chunked-transfer enforcement requires wrapping the
    ASGI receive callable, which can conflict with Starlette internals.
    The Content-Length header check (fast path) combined with per-endpoint
    size validation is the pragmatic approach for production use.
    """

    def __init__(self, app, max_body_size: int = 25 * 1024 * 1024):  # 25MB
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        # Check Content-Length header first (fast path)
        if request.headers.get("content-length"):
            try:
                content_length = int(request.headers["content-length"])
                if content_length > self.max_body_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
            except ValueError:
                pass
        return await call_next(request)


# Middleware stack (order matters — last added runs first)
# 0. Request body size limit
app.add_middleware(MaxBodySizeMiddleware)

# 0.5. Consent enforcement (blocks requests missing required consent)
from app.middleware.consent_middleware import ConsentEnforcementMiddleware
app.add_middleware(ConsentEnforcementMiddleware)

# 1. Tenant context for RLS (sets PG session vars from JWT)
from app.middleware.tenant_context import TenantContextMiddleware
app.add_middleware(TenantContextMiddleware)

# 1.1. Security headers on all responses
app.add_middleware(SecurityHeadersMiddleware)

# 1.5. Request ID for tracing
app.add_middleware(RequestIDMiddleware)

# 2. Request logging (includes request_id)
app.add_middleware(RequestLoggingMiddleware)

# 3. CORS — in DEBUG allow any localhost origin (Word Add-in webview may send
#    unpredictable origins); in production use the explicit CORS_ORIGINS list.
_cors_kwargs = dict(
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-CSRF-Token"],
)
if settings.DEBUG:
    _cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
else:
    _cors_kwargs["allow_origins"] = settings.CORS_ORIGINS
app.add_middleware(CORSMiddleware, **_cors_kwargs)

# 4. Proxy headers (trust reverse proxy for real client IP)
_trusted = [h.strip() for h in settings.TRUSTED_PROXY_HOSTS.split(",") if h.strip()]
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=_trusted)

# 5. GZip compression (outermost — compresses final response body >= 500 bytes)
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)

# Rate limiting exception handler with logging
from app.api.v1.endpoints.auth import limiter
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom rate limit handler: returns 429 + Retry-After + logs the event."""
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(
        "rate_limit_exceeded ip=%s path=%s detail=%s",
        client_ip, request.url.path, exc.detail,
    )
    response = JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": 60,
        },
        headers={"Retry-After": "60"},
    )
    response = request.app.state.limiter._inject_headers(
        response, request.state.view_rate_limit
    )
    return response


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": APP_VERSION}


@app.get("/health/ai")
async def ai_health_check():
    """AI connectivity check — only available in debug mode."""
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")
    from app.core.vertex_client import is_available
    return {"ai_available": is_available()}


@app.get("/health/db")
async def db_health_check(response: Response):
    """Database connectivity check — returns actual error if DB is unreachable."""
    from sqlalchemy import text
    from app.db.session import engine
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "connected"}
    except Exception as e:
        logger.error("DB health check failed: %s", e)
        response.status_code = 503
        return {"status": "error", "detail": "Database unreachable"}


@app.get("/health/deep")
async def deep_health_check(response: Response):
    """
    Deep health check — tests DB, Redis, and AI provider connectivity.

    Returns 200 if all critical services are healthy, 503 if any are down.
    Non-critical services (Redis, AI) can be degraded without failing.
    """
    import time as _time
    from sqlalchemy import text
    from app.db.session import engine

    checks = {}
    overall = "healthy"
    start = _time.time()

    # 1. Database (critical)
    try:
        db_start = _time.time()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "connected",
            "latency_ms": round((_time.time() - db_start) * 1000, 1),
        }
    except Exception as e:
        checks["database"] = {"status": "error", "detail": "Database connection failed"}
        overall = "unhealthy"
        logger.error("DB health check failed: %s", e)

    # 2. Redis (non-critical — degrades gracefully)
    try:
        redis_start = _time.time()
        from app.services.cache_service import get_cache
        cache = await get_cache()
        if cache.is_connected:
            checks["redis"] = {
                "status": "connected",
                "latency_ms": round((_time.time() - redis_start) * 1000, 1),
            }
        else:
            checks["redis"] = {"status": "disconnected", "detail": "Degraded — caching disabled"}
    except Exception as e:
        checks["redis"] = {"status": "disconnected", "detail": "Cache service unavailable"}
        logger.warning("Redis health check failed: %s", e)

    # 3. AI Provider (non-critical)
    try:
        if settings.VERTEX_PROJECT_ID:
            checks["ai_provider"] = {"status": "configured"}
        else:
            checks["ai_provider"] = {"status": "not_configured"}
    except Exception:
        checks["ai_provider"] = {"status": "error"}

    total_ms = round((_time.time() - start) * 1000, 1)

    if overall != "healthy":
        response.status_code = 503

    return {
        "status": overall,
        "version": APP_VERSION,
        "checks": checks,
        "total_latency_ms": total_ms,
    }
