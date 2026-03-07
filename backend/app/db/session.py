"""
Database session and connection management.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings


# Determine SSL requirement (Supabase requires SSL)
connect_args = {
    "timeout": 30,  # Increased timeout for cross-region connections
}
_is_supabase = "supabase.com" in settings.DATABASE_URL or "supabase.co" in settings.DATABASE_URL
if _is_supabase:
    connect_args["ssl"] = True  # TLS with full certificate verification via system CA store
    # Transaction pooler (port 6543) requires disabling prepared statements
    if ":6543/" in settings.DATABASE_URL:
        connect_args["statement_cache_size"] = 0

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=3,          # Reduced for Supabase free tier (max 15 connections)
    max_overflow=5,
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
        from app.models import user, organization, playbook, document, audit_log, template  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
