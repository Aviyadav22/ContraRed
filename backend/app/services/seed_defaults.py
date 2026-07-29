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


def _database_category(raw_category: str) -> str:
    """Normalize seed metadata to the enum label stored by SQLAlchemy."""
    from app.models.playbook import PlaybookCategory

    value = str(raw_category or "custom").strip().lower()
    # VENDOR is a useful marketplace label but not a persisted enum member.
    if value == "vendor":
        value = PlaybookCategory.CUSTOM.value
    try:
        return PlaybookCategory(value).name
    except ValueError:
        logger.warning("Unknown playbook category '%s'; using CUSTOM", raw_category)
        return PlaybookCategory.CUSTOM.name
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
    from scripts.playbooks.healthcare import HEALTHCARE
    from scripts.playbooks.fintech import FINTECH
    from scripts.playbooks.it_services import IT_SERVICES

    return [
        NDA_MUTUAL, NDA_UNILATERAL, MSA, SAAS, EMPLOYMENT,
        DPA, CONSULTING, VENDOR, JOINT_VENTURE, LEASE,
        HEALTHCARE, FINTECH, IT_SERVICES,
    ]


def _rule_write_params(rule: dict, playbook_id: str, order: int) -> dict:
    """Return one canonical parameter set for default-rule insert/update."""
    return {
        "id": rule["id"],
        "playbook_id": playbook_id,
        "clause_type": rule["clause_type"],
        "primary_position": rule["primary_position"],
        "fallback_position": rule.get("fallback_position"),
        "risk_level": rule["risk_level"].upper(),
        "is_deal_breaker": rule.get("is_deal_breaker", False),
        "detection_patterns": json.dumps(rule["detection_patterns"]),
        "suggested_language": json.dumps(rule.get("suggested_language", {})),
        "order_index": rule.get("order_index", order),
        "requires_ai_verification": rule.get(
            "requires_ai_verification",
            True,
        ),
        "verification_prompt": rule.get("verification_prompt"),
        "detection_mode": rule.get("detection_mode", "ai_with_keywords"),
        "risk_description": rule.get("risk_description"),
        "acceptable_position": rule.get("acceptable_position"),
        "unacceptable_signals": json.dumps(
            rule.get("unacceptable_signals", [])
        ),
        "acceptable_signals": json.dumps(
            rule.get("acceptable_signals", [])
        ),
        "clause_context": rule.get("clause_context"),
    }


async def seed_default_playbooks(session: AsyncSession) -> int:
    """Create missing defaults and upgrade older system-managed versions.

    Existing rules are matched by clause type so their database IDs, tiers,
    dependencies, and references remain intact. Unknown extra rules are never
    deleted. A source definition must explicitly increment ``version`` before
    an installed default is changed.
    """
    try:
        all_playbooks = _load_all_playbooks()
    except Exception as e:
        logger.warning("Could not load seed playbooks: %s", e)
        return 0

    changed = 0
    for pb in all_playbooks:
        try:
            source_version = int(pb.get("version", 1))
            result = await session.execute(
                text(
                    "SELECT id, version FROM playbooks "
                    "WHERE name = :name AND is_default = true"
                ),
                {"name": pb["name"]},
            )
            existing = result.fetchone()
            if existing and int(existing.version or 1) >= source_version:
                continue

            if existing:
                playbook_id = str(existing.id)
                await session.execute(
                    text("""
                        UPDATE playbooks
                        SET description = :description,
                            category = :category,
                            party_side = :party_side,
                            version = :version,
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": playbook_id,
                        "description": pb["description"],
                        "category": _database_category(
                            pb.get("category", "custom")
                        ),
                        "party_side": pb.get("party_side", "neutral"),
                        "version": source_version,
                    },
                )
                rule_rows = await session.execute(
                    text(
                        "SELECT id, clause_type FROM playbook_rules "
                        "WHERE playbook_id = :playbook_id"
                    ),
                    {"playbook_id": playbook_id},
                )
                installed_rules = {
                    row.clause_type: str(row.id)
                    for row in rule_rows.fetchall()
                }
            else:
                playbook_id = str(uuid.uuid4())
                await session.execute(
                    text("""
                        INSERT INTO playbooks
                            (id, organization_id, created_by, name, description,
                             category, party_side, is_public, is_default,
                             version, created_at, updated_at)
                        VALUES
                            (:id, :org_id, :user_id, :name, :description,
                             :category, :party_side, true, true,
                             :version, NOW(), NOW())
                    """),
                    {
                        "id": playbook_id,
                        "org_id": _ORG_ID,
                        "user_id": _ADMIN_USER_ID,
                        "name": pb["name"],
                        "description": pb["description"],
                        "category": _database_category(
                            pb.get("category", "custom")
                        ),
                        "party_side": pb.get("party_side", "neutral"),
                        "version": source_version,
                    },
                )
                installed_rules = {}

            for i, rule in enumerate(pb["rules"]):
                params = _rule_write_params(rule, playbook_id, i)
                installed_rule_id = installed_rules.get(rule["clause_type"])
                if installed_rule_id:
                    params["id"] = installed_rule_id
                    await session.execute(
                        text("""
                            UPDATE playbook_rules
                            SET primary_position = :primary_position,
                                fallback_position = :fallback_position,
                                risk_level = :risk_level,
                                is_deal_breaker = :is_deal_breaker,
                                detection_patterns = CAST(:detection_patterns AS jsonb),
                                suggested_language = CAST(:suggested_language AS jsonb),
                                order_index = :order_index,
                                requires_ai_verification = :requires_ai_verification,
                                verification_prompt = :verification_prompt,
                                detection_mode = :detection_mode,
                                risk_description = :risk_description,
                                acceptable_position = :acceptable_position,
                                unacceptable_signals = CAST(:unacceptable_signals AS jsonb),
                                acceptable_signals = CAST(:acceptable_signals AS jsonb),
                                clause_context = :clause_context
                            WHERE id = :id AND playbook_id = :playbook_id
                        """),
                        params,
                    )
                else:
                    await session.execute(
                        text("""
                            INSERT INTO playbook_rules
                                (id, playbook_id, clause_type, primary_position,
                                 fallback_position, risk_level, is_deal_breaker,
                                 detection_patterns, suggested_language,
                                 order_index, requires_ai_verification,
                                 verification_prompt, detection_mode,
                                 risk_description, acceptable_position,
                                 unacceptable_signals, acceptable_signals,
                                 clause_context)
                            VALUES
                                (:id, :playbook_id, :clause_type,
                                 :primary_position, :fallback_position,
                                 :risk_level, :is_deal_breaker,
                                 CAST(:detection_patterns AS jsonb),
                                 CAST(:suggested_language AS jsonb),
                                 :order_index, :requires_ai_verification,
                                 :verification_prompt, :detection_mode,
                                 :risk_description, :acceptable_position,
                                 CAST(:unacceptable_signals AS jsonb),
                                 CAST(:acceptable_signals AS jsonb),
                                 :clause_context)
                        """),
                        params,
                    )

            await session.commit()
            changed += 1
            logger.info(
                "Created or upgraded default playbook '%s' to version %d "
                "(%d source rules; unrecognized installed rules preserved)",
                pb["name"],
                source_version,
                len(pb["rules"]),
            )

        except Exception as e:
            await session.rollback()
            logger.warning(
                "Failed to create or upgrade playbook '%s': %s",
                pb["name"],
                e,
            )

    return changed
