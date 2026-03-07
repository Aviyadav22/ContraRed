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

# Admin user and org IDs (from local dev setup)
ADMIN_USER_ID = "34193e6c-557e-4887-81d8-067e18432578"
ORG_ID = "78e2b3ab-9ea0-4735-9e6f-1fa4a15c52af"


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

ALL_PLAYBOOKS = [
    NDA_MUTUAL, NDA_UNILATERAL, MSA, SAAS, EMPLOYMENT,
    DPA, CONSULTING, VENDOR, JOINT_VENTURE, LEASE,
]


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)
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
                    INSERT INTO playbooks (id, organization_id, created_by, name, description, category, is_public, is_default, version, created_at, updated_at)
                    VALUES (:id, :org_id, :user_id, :name, :description, :category, true, true, 1, NOW(), NOW())
                """),
                {
                    "id": playbook_id,
                    "org_id": ORG_ID,
                    "user_id": ADMIN_USER_ID,
                    "name": pb["name"],
                    "description": pb["description"],
                    "category": pb["category"],
                }
            )

            for i, rule in enumerate(pb["rules"]):
                await session.execute(
                    text("""
                        INSERT INTO playbook_rules (id, playbook_id, clause_type, primary_position, fallback_position,
                            risk_level, is_deal_breaker, detection_patterns, suggested_language, order_index,
                            requires_ai_verification, verification_prompt)
                        VALUES (:id, :playbook_id, :clause_type, :primary_position, :fallback_position,
                            :risk_level, :is_deal_breaker, CAST(:detection_patterns AS jsonb), CAST(:suggested_language AS jsonb),
                            :order_index, :requires_ai_verification, :verification_prompt)
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
                    }
                )

            await session.commit()
            print(f"  CREATED: '{pb['name']}' with {len(pb['rules'])} rules")

    await engine.dispose()
    print(f"\nDone. {len(ALL_PLAYBOOKS)} playbooks processed.")


if __name__ == "__main__":
    print("Seeding default playbooks...")
    asyncio.run(seed())
