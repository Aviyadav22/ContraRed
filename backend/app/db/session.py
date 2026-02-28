"""
Database session and connection management.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings


# Determine SSL requirement (Supabase requires SSL)
# Use explicit SSLContext so hostname mismatch doesn't block connection
import ssl as _ssl

connect_args = {
    "timeout": 30,  # Increased timeout for cross-region connections
}
_is_supabase = "supabase.com" in settings.DATABASE_URL or "supabase.co" in settings.DATABASE_URL
if _is_supabase:
    _ssl_ctx = _ssl.create_default_context()
    _ssl_ctx.check_hostname = False   # Supabase uses project-specific hostnames
    _ssl_ctx.verify_mode = _ssl.CERT_NONE  # Skip cert verify (encrypted but not verified)
    connect_args["ssl"] = _ssl_ctx
    # Transaction pooler (port 6543) requires disabling prepared statements
    if ":6543/" in settings.DATABASE_URL:
        connect_args["statement_cache_size"] = 0

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,          # Reduced for Supabase free tier (max 15 connections)
    max_overflow=10,
    pool_recycle=300,     # Recycle connections every 5 minutes
    connect_args=connect_args,
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
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import models to register them
        from app.models import user, organization, playbook, document  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
