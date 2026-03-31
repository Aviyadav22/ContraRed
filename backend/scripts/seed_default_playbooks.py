"""
Seed script: Create 10 default playbooks with rules for common Indian contract types.
Run: cd backend && python -m scripts.seed_default_playbooks
"""

import asyncio
import uuid
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load env
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/contrared")

# Admin user (from Supabase). Org is NULL for system-level default playbooks.
ADMIN_USER_ID = "19f4b5b2-8fc3-4e75-bbae-6a60ef225b0e"
ORG_ID = None  # System defaults have no org — visible to all


def make_rule(clause_type, primary_position, risk_level, detection_patterns,
              fallback_position=None, is_deal_breaker=False,
              suggested_language=None, requires_ai_verification=True,
              verification_prompt=None, order_index=0):
    """Helper to create a rule dict."""
    sl = suggested_language or {}
    if not sl and primary_position:
        sl = {"preferred": primary_position}
        if fallback_position:
            sl["fallback"] = fallback_position
    return {
        "id": str(uuid.uuid4()),
        "clause_type": clause_type,
        "primary_position": primary_position,
        "fallback_position": fallback_position,
        "risk_level": risk_level,
        "is_deal_breaker": is_deal_breaker,
        "detection_patterns": detection_patterns,
        "suggested_language": sl,
        "requires_ai_verification": requires_ai_verification,
        "verification_prompt": verification_prompt,
        "order_index": order_index,
    }


# ============================================================
# PLAYBOOK DEFINITIONS - imported from separate modules
# ============================================================
from scripts.playbooks.nda_mutual import NDA_MUTUAL
from scripts.playbooks.nda_unilateral import NDA_UNILATERAL
from scripts.playbooks.msa import MSA
from scripts.playbooks.saas import SAAS
from scripts.playbooks.employment import EMPLOYMENT
from scripts.playbooks.dpa import DPA
from scripts.playbooks.consulting import CONSULTING
from scripts.playbooks.vendor import VENDOR
from scripts.playbooks.joint_venture import JOINT_VENTURE
from scripts.playbooks.lease import LEASE
from scripts.playbooks.fintech import FINTECH
from scripts.playbooks.healthcare import HEALTHCARE
from scripts.playbooks.it_services import IT_SERVICES

ALL_PLAYBOOKS = [
    NDA_MUTUAL, NDA_UNILATERAL, MSA, SAAS, EMPLOYMENT,
    DPA, CONSULTING, VENDOR, JOINT_VENTURE, LEASE,
    FINTECH, HEALTHCARE, IT_SERVICES,
]


async def seed():
    # Use statement_cache_size=0 for PgBouncer transaction pooler compatibility
    connect_args = {}
    if "supabase" in DATABASE_URL:
        import ssl as _ssl
        _ctx = _ssl.create_default_context()
        _ctx.check_hostname = False
        _ctx.verify_mode = _ssl.CERT_NONE
        connect_args["ssl"] = _ctx
        if ":6543/" in DATABASE_URL:
            connect_args["statement_cache_size"] = 0
            connect_args["prepared_statement_name_func"] = lambda: ""
    engine = create_async_engine(DATABASE_URL, echo=False, connect_args=connect_args)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for pb in ALL_PLAYBOOKS:
            # Check if playbook already exists by name
            result = await session.execute(
                text("SELECT id FROM playbooks WHERE name = :name AND is_default = true"),
                {"name": pb["name"]}
            )
            existing = result.fetchone()
            if existing:
                print(f"  SKIP: '{pb['name']}' already exists (id={existing[0]})")
                continue

            playbook_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO playbooks (id, organization_id, created_by, name, description, category, party_side, is_public, is_default, version, created_at, updated_at)
                    VALUES (:id, :org_id, :user_id, :name, :description, :category, :party_side, true, true, 1, NOW(), NOW())
                """),
                {
                    "id": playbook_id,
                    "org_id": ORG_ID,
                    "user_id": ADMIN_USER_ID,
                    "name": pb["name"],
                    "description": pb["description"],
                    "category": pb["category"],
                    "party_side": pb.get("party_side", "buyer"),
                }
            )

            for i, rule in enumerate(pb["rules"]):
                await session.execute(
                    text("""
                        INSERT INTO playbook_rules (id, playbook_id, clause_type, primary_position, fallback_position,
                            risk_level, is_deal_breaker, detection_patterns, suggested_language, order_index,
                            requires_ai_verification, verification_prompt,
                            detection_mode, risk_description, acceptable_position,
                            unacceptable_signals, acceptable_signals, clause_context)
                        VALUES (:id, :playbook_id, :clause_type, :primary_position, :fallback_position,
                            :risk_level, :is_deal_breaker, CAST(:detection_patterns AS jsonb), CAST(:suggested_language AS jsonb),
                            :order_index, :requires_ai_verification, :verification_prompt,
                            :detection_mode, :risk_description, :acceptable_position,
                            CAST(:unacceptable_signals AS jsonb), CAST(:acceptable_signals AS jsonb), :clause_context)
                    """),
                    {
                        "id": rule["id"],
                        "playbook_id": playbook_id,
                        "clause_type": rule["clause_type"],
                        "primary_position": rule["primary_position"],
                        "fallback_position": rule.get("fallback_position"),
                        "risk_level": rule["risk_level"].upper(),
                        "is_deal_breaker": rule.get("is_deal_breaker", False),
                        "detection_patterns": __import__("json").dumps(rule["detection_patterns"]),
                        "suggested_language": __import__("json").dumps(rule.get("suggested_language", {})),
                        "order_index": rule.get("order_index", i),
                        "requires_ai_verification": rule.get("requires_ai_verification", True),
                        "verification_prompt": rule.get("verification_prompt"),
                        "detection_mode": rule.get("detection_mode", "keywords_only"),
                        "risk_description": rule.get("risk_description"),
                        "acceptable_position": rule.get("acceptable_position"),
                        "unacceptable_signals": __import__("json").dumps(rule.get("unacceptable_signals", [])),
                        "acceptable_signals": __import__("json").dumps(rule.get("acceptable_signals", [])),
                        "clause_context": rule.get("clause_context"),
                    }
                )

            await session.commit()
            print(f"  CREATED: '{pb['name']}' with {len(pb['rules'])} rules")

    await engine.dispose()
    print(f"\nDone. {len(ALL_PLAYBOOKS)} playbooks processed.")


if __name__ == "__main__":
    print("Seeding default playbooks...")
    asyncio.run(seed())
