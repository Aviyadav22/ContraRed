"""
Database session and connection management.
"""

import asyncio
import logging
from typing import AsyncGenerator

import asyncpg
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)


# Determine SSL requirement (Supabase requires SSL)
connect_args = {
    "timeout": 12,  # Fail stuck handshakes fast; our retry wrapper covers transients.
}
_is_supabase = "supabase.com" in settings.DATABASE_URL or "supabase.co" in settings.DATABASE_URL
if _is_supabase:
    import ssl as _ssl
    _ctx = _ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = _ssl.CERT_NONE
    connect_args["ssl"] = _ctx
    # Transaction pooler (port 6543) requires disabling prepared statements
    if ":6543/" in settings.DATABASE_URL:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = lambda: ""

# asyncpg doesn't understand the SQLAlchemy "+asyncpg" scheme suffix.
_async_dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# These keys are consumed by SQLAlchemy's asyncpg dialect before it calls
# asyncpg.connect() — when we bypass the dialect via async_creator, we must
# strip them or asyncpg raises TypeError on the unexpected kwarg.
_DIALECT_ONLY_CONNECT_ARGS = {"prepared_statement_name_func"}
_asyncpg_kwargs = {k: v for k, v in connect_args.items() if k not in _DIALECT_ONLY_CONNECT_ARGS}


async def _connect_with_retry() -> asyncpg.Connection:
    """One-retry wrapper around asyncpg.connect to mask transient cross-cloud flakes.

    Retries only on network-level transients. CancelledError is re-raised
    untouched — that signal means the client disconnected, and resurrecting
    the attempt would be wrong. Non-transient errors (auth, bad DSN, etc.)
    also fall through on the first attempt.
    """
    last_exc: BaseException | None = None
    for attempt in (1, 2):
        try:
            return await asyncpg.connect(_async_dsn, **_asyncpg_kwargs)
        except asyncio.CancelledError:
            raise
        except (asyncio.TimeoutError, ConnectionError, OSError,
                asyncpg.exceptions.ConnectionFailureError) as e:
            last_exc = e
            if attempt == 1:
                logger.warning(
                    "asyncpg connect attempt 1/2 failed (%s: %s) — retrying in 500ms",
                    type(e).__name__, e,
                )
                await asyncio.sleep(0.5)
    assert last_exc is not None
    raise last_exc


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=1800,    # Recycle every 30 min; pool_pre_ping catches Supabase's ~600s idle close.
    pool_timeout=10,      # Wait up to 10s for a connection from the pool
    async_creator=_connect_with_retry,
    connect_args=connect_args,  # Still read by SQLAlchemy internals (e.g. dialect inspection).
)

_is_transaction_pooler = ":6543/" in settings.DATABASE_URL

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def init_db():
    """Initialize database tables.

    Skipped when using Supabase transaction pooler (port 6543) because
    DDL + prepared statements don't work through PgBouncer transaction mode.
    Tables must be created via SQL migrations instead.
    """
    if _is_transaction_pooler:
        import logging
        logging.getLogger(__name__).info("Skipping init_db (transaction pooler — use SQL migrations)")
        return
    async with engine.begin() as conn:
        # Import models to register them
        from app.models import user, organization, playbook, document, audit_log, feedback, template, billing, analytics, consent, compliance_result  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def get_db(request: Request = None) -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session with optional tenant context for RLS.

    When called via FastAPI dependency injection, the Request is automatically
    provided.  The TenantContextMiddleware stores JWT-derived tenant info in
    ``request.state``, and this function forwards it to PostgreSQL session
    variables so that Row-Level Security policies activate on every query.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Set RLS context if request has tenant info from middleware
            if (
                request
                and hasattr(request.state, "tenant_user_id")
                and request.state.tenant_user_id
            ):
                from app.middleware.tenant_context import set_tenant_context

                await set_tenant_context(
                    db=session,
                    user_id=request.state.tenant_user_id,
                    organization_id=request.state.tenant_org_id,
                    is_super_admin=request.state.tenant_is_super_admin,
                )
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            from app.middleware.tenant_context import clear_tenant_context
            await clear_tenant_context(session)
