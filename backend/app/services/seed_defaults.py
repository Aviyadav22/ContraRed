"""
Auto-seed default playbooks on app startup.

Checks if default playbooks exist in DB; creates any that are missing.
Designed to be called from the lifespan hook — fast no-op when already seeded.
"""

import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Admin user (from Supabase). Org is NULL for system-level default playbooks.
_ADMIN_USER_ID = "19f4b5b2-8fc3-4e75-bbae-6a60ef225b0e"
_ORG_ID = None  # System defaults have no org — visible to all


def _load_all_playbooks():
    """Import seed playbooks lazily to avoid import-time side effects."""
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

    return [
        NDA_MUTUAL, NDA_UNILATERAL, MSA, SAAS, EMPLOYMENT,
        DPA, CONSULTING, VENDOR, JOINT_VENTURE, LEASE,
    ]


async def seed_default_playbooks(session: AsyncSession) -> int:
    """Seed missing default playbooks. Returns count of newly created playbooks."""
    try:
        all_playbooks = _load_all_playbooks()
    except Exception as e:
        logger.warning("Could not load seed playbooks: %s", e)
        return 0

    created = 0
    for pb in all_playbooks:
        try:
            result = await session.execute(
                text("SELECT id FROM playbooks WHERE name = :name AND is_default = true"),
                {"name": pb["name"]},
            )
            if result.fetchone():
                continue

            playbook_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO playbooks
                        (id, organization_id, created_by, name, description, category,
                         party_side, is_public, is_default, version, created_at, updated_at)
                    VALUES
                        (:id, :org_id, :user_id, :name, :description, :category,
                         :party_side, true, true, 1, NOW(), NOW())
                """),
                {
                    "id": playbook_id,
                    "org_id": _ORG_ID,
                    "user_id": _ADMIN_USER_ID,
                    "name": pb["name"],
                    "description": pb["description"],
                    "category": pb["category"],
                    "party_side": pb.get("party_side", "buyer"),
                },
            )

            for i, rule in enumerate(pb["rules"]):
                await session.execute(
                    text("""
                        INSERT INTO playbook_rules
                            (id, playbook_id, clause_type, primary_position, fallback_position,
                             risk_level, is_deal_breaker, detection_patterns, suggested_language,
                             order_index, requires_ai_verification, verification_prompt,
                             detection_mode, risk_description, acceptable_position,
                             unacceptable_signals, acceptable_signals, clause_context)
                        VALUES
                            (:id, :playbook_id, :clause_type, :primary_position, :fallback_position,
                             :risk_level, :is_deal_breaker, CAST(:detection_patterns AS jsonb),
                             CAST(:suggested_language AS jsonb), :order_index,
                             :requires_ai_verification, :verification_prompt,
                             :detection_mode, :risk_description, :acceptable_position,
                             CAST(:unacceptable_signals AS jsonb),
                             CAST(:acceptable_signals AS jsonb), :clause_context)
                    """),
                    {
                        "id": rule["id"],
                        "playbook_id": playbook_id,
                        "clause_type": rule["clause_type"],
                        "primary_position": rule["primary_position"],
                        "fallback_position": rule.get("fallback_position"),
                        "risk_level": rule["risk_level"].upper(),
                        "is_deal_breaker": rule.get("is_deal_breaker", False),
                        "detection_patterns": json.dumps(rule["detection_patterns"]),
                        "suggested_language": json.dumps(rule.get("suggested_language", {})),
                        "order_index": rule.get("order_index", i),
                        "requires_ai_verification": rule.get("requires_ai_verification", True),
                        "verification_prompt": rule.get("verification_prompt"),
                        "detection_mode": rule.get("detection_mode", "ai_with_keywords"),
                        "risk_description": rule.get("risk_description"),
                        "acceptable_position": rule.get("acceptable_position"),
                        "unacceptable_signals": json.dumps(rule.get("unacceptable_signals", [])),
                        "acceptable_signals": json.dumps(rule.get("acceptable_signals", [])),
                        "clause_context": rule.get("clause_context"),
                    },
                )

            await session.commit()
            created += 1
            logger.info("Seeded default playbook: '%s' (%d rules)", pb["name"], len(pb["rules"]))

        except Exception as e:
            await session.rollback()
            logger.warning("Failed to seed playbook '%s': %s", pb["name"], e)

    return created
