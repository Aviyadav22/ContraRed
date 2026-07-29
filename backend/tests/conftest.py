import sqlite3
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, INET, UUID as PG_UUID
from sqlalchemy import ARRAY as SQLARRAY, JSON, String, Uuid, TypeDecorator

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
            elif isinstance(column.type, (ARRAY, SQLARRAY)):
                column.type = JSON()
            elif isinstance(column.type, INET):
                column.type = String(45)
            elif isinstance(column.type, PG_UUID):
                column.type = SQLiteUUID()
            elif isinstance(column.type, Uuid):
                column.type = SQLiteUUID()


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
    app.state.consent_session_factory = session_factory
    # Disable rate limiter for tests
    app.state.limiter.enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.state.limiter.enabled = True
    delattr(app.state, "consent_session_factory")
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
    """Register/login and grant the purposes required by general API tests."""
    await client.post("/api/v1/auth/register", json=user_data)
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": user_data["email"],
        "password": user_data["password"],
    })
    token = login_resp.json()["access_token"]
    grant_resp = await client.post(
        "/api/v1/consent/grant",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "purpose_codes": [
                "contract_analysis",
                "ai_drafting",
                "billing",
                "sso_integration",
            ]
        },
    )
    assert grant_resp.status_code == 200, grant_resp.text
    return token
