"""
Compliance Layer Service.
Handles loading, seeding, and merging of compliance layer rules with playbook rules.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compliance_layer import ComplianceLayer, ComplianceLayerRule

logger = logging.getLogger(__name__)

# Risk severity ordering for deduplication (higher = stricter)
_RISK_SEVERITY = {"RED": 3, "YELLOW": 2, "GREEN": 1}


async def get_active_layers(db: AsyncSession) -> List[Dict]:
    """Return all active compliance layers with rule counts."""
    query = (
        select(ComplianceLayer)
        .options(selectinload(ComplianceLayer.rules))
        .where(ComplianceLayer.is_active == True)  # noqa: E712
        .order_by(ComplianceLayer.code)
    )
    result = await db.execute(query)
    layers = result.scalars().all()
    return [
        {
            "code": layer.code,
            "name": layer.name,
            "description": layer.description,
            "jurisdiction": layer.jurisdiction,
            "version": layer.version,
            "rule_count": len(layer.rules),
        }
        for layer in layers
    ]


async def get_layer_by_code(db: AsyncSession, code: str) -> Optional[ComplianceLayer]:
    """Load a compliance layer by code, with rules eagerly loaded."""
    query = (
        select(ComplianceLayer)
        .options(selectinload(ComplianceLayer.rules))
        .where(ComplianceLayer.code == code, ComplianceLayer.is_active == True)  # noqa: E712
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_layer_rules_as_dicts(db: AsyncSession, layer_code: str) -> List[Dict]:
    """Load compliance layer rules as list of dicts (same format as playbook rules)."""
    layer = await get_layer_by_code(db, layer_code)
    if not layer:
        return []

    rules = []
    for rule in sorted(layer.rules, key=lambda r: r.sort_order):
        rules.append({
            "name": rule.clause_type,
            "risk_level": rule.risk_level.upper() if rule.risk_level else "YELLOW",
            "primary_position": rule.primary_position or "",
            "fallback_position": rule.fallback_position or "",
            "is_deal_breaker": rule.is_deal_breaker,
            "detection_mode": rule.detection_mode or "ai_with_keywords",
            "risk_description": rule.risk_description or "",
            "acceptable_position": rule.acceptable_position or "",
            "unacceptable_signals": rule.unacceptable_signals or [],
            "acceptable_signals": rule.acceptable_signals or [],
            "clause_context": "",
            "verification_prompt": "",
            # Tag for grouping in results
            "_compliance_layer": layer_code,
        })
    return rules


def merge_rules(
    playbook_rules: Optional[List[Dict]],
    layer_rules: List[Dict],
) -> List[Dict]:
    """Merge playbook rules with compliance layer rules.

    Deduplication: if both have the same clause_type base (ignoring prefixes),
    keep the one with stricter risk level. If a compliance layer rule has a
    unique clause_type (e.g., dpdp_consent_mechanism), it's always added.

    Args:
        playbook_rules: Existing playbook rules (may be None or empty).
        layer_rules: Compliance layer rules to overlay.

    Returns:
        Combined list of rules.
    """
    if not layer_rules:
        return playbook_rules or []
    if not playbook_rules:
        return list(layer_rules)

    # Build lookup by clause_type name
    merged: Dict[str, Dict] = {}

    # Add playbook rules first
    for rule in playbook_rules:
        name = rule.get("name", "")
        merged[name] = rule

    # Overlay compliance layer rules
    for rule in layer_rules:
        name = rule.get("name", "")
        # Strip common prefix to find overlapping base type
        # e.g., "dpdp_data_retention" matches "data_retention"
        base_name = _strip_layer_prefix(name)

        # Check if a playbook rule with the same base type exists
        existing_key = _find_matching_key(merged, base_name)

        if existing_key is not None:
            # Deduplicate: keep stricter risk level
            existing = merged[existing_key]
            existing_severity = _RISK_SEVERITY.get(existing.get("risk_level", "GREEN"), 0)
            new_severity = _RISK_SEVERITY.get(rule.get("risk_level", "GREEN"), 0)

            if new_severity >= existing_severity:
                # Compliance layer is stricter or equal — replace
                merged[existing_key] = rule
            # else: playbook rule is stricter — keep it
        else:
            # Unique compliance layer rule — add it
            merged[name] = rule

    return list(merged.values())


def _strip_layer_prefix(name: str) -> str:
    """Strip compliance layer prefix from clause type.

    Examples:
        'dpdp_data_retention' -> 'data_retention'
        'dpdp_breach_notification' -> 'breach_notification'
        'limitation_of_liability' -> 'limitation_of_liability'
    """
    prefixes = ["dpdp_", "gdpr_", "ccpa_", "aiact_"]
    for prefix in prefixes:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _find_matching_key(rules_dict: Dict[str, Dict], base_name: str) -> Optional[str]:
    """Find a key in rules_dict that matches the base_name.

    Matches if the key equals base_name, or if the key's stripped version equals base_name.
    """
    # Direct match
    if base_name in rules_dict:
        return base_name

    # Check if any existing key has the same base
    for key in rules_dict:
        if _strip_layer_prefix(key) == base_name:
            return key

    return None


def calculate_compliance_score(layer_results: List[Dict]) -> Dict:
    """Calculate compliance readiness score for a layer's results.

    Args:
        layer_results: List of redline dicts from the analysis that belong to a compliance layer.

    Returns:
        Dict with score (0-100), compliant, partial, non_compliant, not_applicable, deal_breakers_failing.
    """
    if not layer_results:
        return {
            "score": 0,
            "compliant": 0,
            "partial": 0,
            "non_compliant": 0,
            "not_applicable": 0,
            "total_rules": 0,
            "deal_breakers_failing": 0,
        }

    compliant = 0
    partial = 0
    non_compliant = 0
    not_applicable = 0
    deal_breakers_failing = 0

    for result in layer_results:
        risk = result.get("risk_level", "").upper()
        is_deal_breaker = result.get("is_deal_breaker", False)

        if risk == "GREEN":
            compliant += 1
        elif risk == "YELLOW":
            partial += 1
        elif risk == "RED":
            non_compliant += 1
            if is_deal_breaker:
                deal_breakers_failing += 1
        else:
            not_applicable += 1

    total = len(layer_results)
    applicable = total - not_applicable
    score = 0
    if applicable > 0:
        score = round(((compliant * 1.0 + partial * 0.5) / applicable) * 100)

    return {
        "score": score,
        "compliant": compliant,
        "partial": partial,
        "non_compliant": non_compliant,
        "not_applicable": not_applicable,
        "total_rules": total,
        "deal_breakers_failing": deal_breakers_failing,
    }


async def seed_compliance_layers(db: AsyncSession) -> int:
    """Seed default compliance layers if they don't exist. Returns count of layers seeded."""
    from scripts.compliance_layers.dpdp import DPDP_LAYER

    all_layers = [DPDP_LAYER]
    seeded = 0

    for layer_def in all_layers:
        code = layer_def["code"]

        # Check if already exists
        existing = await db.execute(
            select(ComplianceLayer).where(ComplianceLayer.code == code)
        )
        if existing.scalar_one_or_none() is not None:
            logger.info(f"Compliance layer '{code}' already exists, skipping")
            continue

        # Create layer
        layer = ComplianceLayer(
            code=code,
            name=layer_def["name"],
            description=layer_def["description"],
            jurisdiction=layer_def.get("jurisdiction"),
            version=1,
            is_active=True,
        )
        db.add(layer)
        await db.flush()  # Get layer.id

        # Create rules
        for rule_def in layer_def["rules"]:
            rule = ComplianceLayerRule(
                layer_id=layer.id,
                clause_type=rule_def["clause_type"],
                primary_position=rule_def["primary_position"],
                fallback_position=rule_def.get("fallback_position"),
                risk_level=rule_def.get("risk_level", "YELLOW"),
                is_deal_breaker=rule_def.get("is_deal_breaker", False),
                detection_patterns=rule_def.get("detection_patterns"),
                detection_mode=rule_def.get("detection_mode", "ai_with_keywords"),
                risk_description=rule_def.get("risk_description"),
                acceptable_position=rule_def.get("acceptable_position"),
                unacceptable_signals=rule_def.get("unacceptable_signals"),
                acceptable_signals=rule_def.get("acceptable_signals"),
                sort_order=rule_def.get("sort_order", 0),
            )
            db.add(rule)

        await db.commit()
        seeded += 1
        logger.info(f"Seeded compliance layer '{code}' with {len(layer_def['rules'])} rules")

    return seeded
