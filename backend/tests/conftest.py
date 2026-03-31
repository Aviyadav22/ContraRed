import asyncio
import sqlite3
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PG_UUID
from sqlalchemy import JSON, String, Uuid, TypeDecorator

from app.db.session import Base, get_db
import app.models  # noqa: F401 — register all models with Base.metadata
from main import app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Register UUID adapter for SQLite (Python 3.12+ removed implicit converters)
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))
sqlite3.register_converter("UUID", lambda b: uuid.UUID(b.decode()))


class SQLiteUUID(TypeDecorator):
    """Store UUID as a 32-char hex string in SQLite, auto-convert on bind/result."""
    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return value.hex
            return uuid.UUID(value).hex
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


def _remap_pg_types_for_sqlite(base):
    """Replace PostgreSQL-specific column types with SQLite-compatible ones."""
    for table in base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, ARRAY):
                column.type = JSON()
            elif isinstance(column.type, PG_UUID):
                column.type = SQLiteUUID()
            elif isinstance(column.type, Uuid):
                column.type = SQLiteUUID()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def db_engine():
    _remap_pg_types_for_sqlite(Base)
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

@pytest_asyncio.fixture
async def client(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # Disable rate limiter for tests
    app.state.limiter.enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.state.limiter.enabled = True
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_data():
    return {
        "email": "test@contrared.ai",
        "password": "TestPassword123!",
        "name": "Test User",
    }

@pytest.fixture
def admin_user_data():
    return {
        "email": "admin@contrared.ai",
        "password": "AdminPassword123!",
        "name": "Admin User",
    }


async def register_and_login(client, user_data) -> str:
    """Register a user and login, returning the access_token."""
    await client.post("/api/v1/auth/register", json=user_data)
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": user_data["email"],
        "password": user_data["password"],
    })
    return login_resp.json()["access_token"]
