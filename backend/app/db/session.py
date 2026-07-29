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
from sqlalchemy.pool import NullPool

from app.core.config import settings


class _PgBouncerAnonStmtConnection(asyncpg.Connection):
    """asyncpg Connection that forces ANONYMOUS prepared statements.

    Required when running through Supabase's pgbouncer transaction-mode
    pooler (port 6543): pgbouncer multiplexes Postgres backends across
    client connections without resetting prepared-statement state. Even
    with `statement_cache_size=0`, asyncpg auto-names statements
    `__asyncpg_stmt_N__`; the next request lands on a backend that already
    has that name from a prior tx and fails with
    `DuplicatePreparedStatementError`.

    Forcing the statement name to `""` makes Postgres use the unnamed
    statement slot, which is session-private and reused atomically on
    each Parse — pgbouncer can't collide on it.
    """

    async def _prepare(self, query, *, name=None, timeout=None,
                       use_cache=False, record_class=None):
        return await super()._prepare(
            query,
            name=name if name else "",
            timeout=timeout,
            use_cache=use_cache,
            record_class=record_class,
        )

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


_is_transaction_pooler = ":6543/" in settings.DATABASE_URL
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")


async def _connect_with_retry() -> asyncpg.Connection:
    """One-retry wrapper around asyncpg.connect to mask transient cross-cloud flakes.

    On the Supabase transaction pooler (port 6543), connect with the custom
    `_PgBouncerAnonStmtConnection` class so every prepared statement uses the
    unnamed slot — required because pgbouncer reuses backends across requests.

    Retries only on network-level transients. CancelledError is re-raised
    untouched — that signal means the client disconnected, and resurrecting
    the attempt would be wrong. Non-transient errors (auth, bad DSN, etc.)
    also fall through on the first attempt.
    """
    kwargs = dict(_asyncpg_kwargs)
    if _is_transaction_pooler:
        kwargs["connection_class"] = _PgBouncerAnonStmtConnection

    last_exc: BaseException | None = None
    for attempt in (1, 2):
        try:
            return await asyncpg.connect(_async_dsn, **kwargs)
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


# Create async engine.
#
# When connected through Supabase's transaction-mode pooler (port 6543),
# pgbouncer multiplexes Postgres backends across client connections without
# resetting prepared-statement state. Even with `statement_cache_size=0`,
# asyncpg auto-names statements like `__asyncpg_stmt_1__`; the second
# request lands on a backend that already has that name from a prior tx
# and fails with `DuplicatePreparedStatementError`. NullPool sidesteps the
# whole problem by NOT reusing connections — every request opens a fresh
# asyncpg connection and closes it on release. The connection-open cost is
# small (~50ms over the existing TCP/TLS round-trip we already pay).
#
# When using a direct connection (port 5432), the standard QueuePool with
# pre-ping + recycle is fine.
if _is_sqlite:
    # SQLite's StaticPool does not accept PostgreSQL QueuePool settings, and
    # the asyncpg connection creator must never be used for an aiosqlite URL.
    # This path is used by tests and local ephemeral databases.
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
    )
elif _is_transaction_pooler:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
        async_creator=_connect_with_retry,
        connect_args=connect_args,
    )
else:
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
