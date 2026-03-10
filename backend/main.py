"""
ContraRed Backend - AI Contract Redlining API

Main application entry point.
"""

import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import init_db

logger = logging.getLogger("contrared")


# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses (SOC2 compliance)."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


# =============================================================================
# Request Logging Middleware
# =============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests for audit trail."""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response: Response = await call_next(request)
        duration = time.time() - start

        # Skip health check logs to reduce noise
        if not request.url.path.startswith("/health"):
            logger.info(
                "method=%s path=%s status=%d duration=%.3fs ip=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration,
                request.client.host if request.client else "unknown",
            )
        return response


# =============================================================================
# Application Setup
# =============================================================================

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
        logger.error(f"DB init failed on startup: {e}. App will still start.")
    yield
    # Shutdown
    from app.services.cache_service import shutdown_cache
    await shutdown_cache()


app = FastAPI(
    title="ContraRed API",
    description="AI-powered contract redlining and review platform",
    version="1.1.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Middleware stack (order matters — last added runs first)
# 1. Security headers on all responses
app.add_middleware(SecurityHeadersMiddleware)

# 2. Request logging
app.add_middleware(RequestLoggingMiddleware)

# 3. CORS — tightened from wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# 4. Proxy headers (trust reverse proxy for real client IP)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Rate limiting exception handler
from app.api.v1.endpoints.auth import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.1.0"}


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
        logger.error(f"DB health check failed: {e}")
        response.status_code = 503
        return {"status": "error", "detail": "Database unreachable"}
