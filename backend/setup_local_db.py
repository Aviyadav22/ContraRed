"""
Setup local development database.

Usage:
    1. docker compose up -d
    2. python setup_local_db.py

Creates all tables via SQLAlchemy ORM and seeds demo data.
Consolidated migrations are NOT needed — SQLAlchemy create_all
generates the full schema from models (including MFA, SSO, billing columns).
Migrations are only needed for Supabase (RLS policies, indexes, enum tweaks).
"""

import asyncio
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))


async def main():
    from app.core.config import settings
    from app.db.session import engine, Base, AsyncSessionLocal
    from sqlalchemy import text

    print(f"Database URL: {settings.DATABASE_URL.split('@')[0]}@***")
    print(f"Redis URL: {settings.REDIS_URL or '(not set)'}")

    # Step 1: Create all tables from SQLAlchemy models
    print("\n[1/2] Creating tables from SQLAlchemy models...")
    async with engine.begin() as conn:
        from app.models import user, organization, playbook, document, audit_log, feedback, template, billing, analytics  # noqa
        await conn.run_sync(Base.metadata.create_all)
    print("  Tables created.")

    # Create sequences and extras that the consolidated migrations would add
    print("  Creating sequences and extras...")
    extras = [
        "CREATE SEQUENCE IF NOT EXISTS audit_log_sequence START 1",
    ]
    for stmt in extras:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception:
            pass

    # Step 2: Seed demo data using ORM (avoids SQL $ escaping issues)
    print("\n[2/2] Seeding demo data...")
    import bcrypt
    from uuid import UUID as PyUUID

    async with AsyncSessionLocal() as session:
        try:
            from app.models.user import User, UserRole, SubscriptionTier
            from app.models.organization import Organization, PlanType

            # Check if demo user already exists
            existing = await session.execute(
                text("SELECT id FROM users WHERE email = 'admin@contrared.com'")
            )
            if existing.scalar():
                print("  Demo user already exists, skipping.")
            else:
                # Create org
                org = Organization(
                    id=PyUUID("a0000000-0000-0000-0000-000000000001"),
                    name="ContraRed Demo",
                    plan_type=PlanType.FREE,
                )
                session.add(org)
                await session.flush()

                # Create admin user
                hashed_pw = bcrypt.hashpw(b"ContraRed1@", bcrypt.gensalt()).decode()
                admin = User(
                    id=PyUUID("b0000000-0000-0000-0000-000000000001"),
                    email="admin@contrared.com",
                    name="Admin User",
                    password_hash=hashed_pw,
                    role=UserRole.ADMIN,
                    subscription_tier=SubscriptionTier.FREE,
                    organization_id=org.id,
                    is_active=True,
                    is_verified=True,
                )
                session.add(admin)
                await session.commit()
                print("  Demo data seeded. Login: admin@contrared.com / ContraRed1@")
        except Exception as e:
            await session.rollback()
            err = str(e)
            if "duplicate" in err.lower() or "unique" in err.lower():
                print("  Demo data already exists, skipping.")
            else:
                print(f"  Seed warning: {err[:150]}")

    # Verify
    print("\n--- Verification ---")
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
        count = result.scalar()
        print(f"Tables in database: {count}")

        result = await session.execute(text("SELECT email, role FROM users LIMIT 5"))
        users = result.fetchall()
        if users:
            print(f"Users: {[(u[0], u[1]) for u in users]}")
        else:
            print("Users: (none — register via the app)")

    await engine.dispose()
    print("\nLocal database setup complete!")
    print("Start the backend: python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload")


if __name__ == "__main__":
    asyncio.run(main())
