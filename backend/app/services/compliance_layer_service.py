"""
Compliance Layer Service.
Handles loading, seeding, and merging of compliance layer rules with playbook rules.
"""

import copy
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

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
            "source_url": layer.source_url,
            "gazette_date": (
                layer.gazette_date.isoformat()
                if layer.gazette_date else None
            ),
            "effective_date": (
                layer.effective_date.isoformat()
                if layer.effective_date else None
            ),
            "last_verified_at": (
                layer.last_verified_at.isoformat()
                if layer.last_verified_at else None
            ),
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
    provenance_context = (
        f"Official legal source: {layer.source_url or 'not recorded'}. "
        f"Gazette date: {layer.gazette_date.isoformat() if layer.gazette_date else 'not recorded'}. "
        f"Main effective date for this layer: "
        f"{layer.effective_date.isoformat() if layer.effective_date else 'not recorded'}. "
        "Assess applicability from the contract facts and the law's phased "
        "commencement; do not assume every obligation is currently operative."
    )
    for rule in sorted(layer.rules, key=lambda r: r.sort_order):
        rules.append({
            "id": f"compliance:{layer.code}:{rule.id}",
            "name": rule.clause_type,
            "clause_type": rule.clause_type,
            "risk_level": rule.risk_level.upper() if rule.risk_level else "YELLOW",
            "primary_position": rule.primary_position or "",
            "fallback_position": rule.fallback_position or "",
            "is_deal_breaker": rule.is_deal_breaker,
            "detection_mode": rule.detection_mode or "ai_with_keywords",
            "risk_description": rule.risk_description or "",
            "acceptable_position": rule.acceptable_position or "",
            "unacceptable_signals": rule.unacceptable_signals or [],
            "acceptable_signals": rule.acceptable_signals or [],
            "clause_context": provenance_context,
            "verification_prompt": (
                "Based only on the supplied contract evidence, is this legal "
                "rule applicable, and is the stated obligation satisfied? "
                "Identify the exact supporting or conflicting text."
            ),
            "detection_patterns": copy.deepcopy(
                rule.detection_patterns or {}
            ),
            # Tag for grouping in results
            "_compliance_layer": layer_code,
            "_compliance_layers": [layer_code],
            "_legal_source_url": layer.source_url,
            "_legal_effective_date": (
                layer.effective_date.isoformat()
                if layer.effective_date else None
            ),
            "_legal_last_verified_at": (
                layer.last_verified_at.isoformat()
                if layer.last_verified_at else None
            ),
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
        merged[name] = copy.deepcopy(rule)

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
                # Compliance layer is stricter or equal - replace.
                merged[existing_key] = copy.deepcopy(rule)
            else:
                # Preserve statutory provenance even when a firmer client
                # playbook position is the effective obligation.
                existing_copy = copy.deepcopy(existing)
                layers = set(existing_copy.get("_compliance_layers") or [])
                layer_code = str(rule.get("_compliance_layer") or "")
                if layer_code:
                    layers.add(layer_code)
                existing_copy["_compliance_layers"] = sorted(layers)
                merged[existing_key] = existing_copy
        else:
            # Unique compliance layer rule — add it
            merged[name] = copy.deepcopy(rule)

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
            "unassessed": 0,
            "total_rules": 0,
            "deal_breakers_failing": 0,
            "complete": False,
            "status": "not_assessed",
        }

    compliant = 0
    partial = 0
    non_compliant = 0
    not_applicable = 0
    unassessed = 0
    deal_breakers_failing = 0

    for result in layer_results:
        assessment_status = str(result.get("status") or "").lower()
        if assessment_status == "not_applicable":
            not_applicable += 1
            continue
        if assessment_status in {"unassessed", "unverified"}:
            unassessed += 1
            continue

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
            unassessed += 1

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
        "unassessed": unassessed,
        "total_rules": total,
        "deal_breakers_failing": deal_breakers_failing,
        "complete": unassessed == 0,
        "status": "complete" if unassessed == 0 else "incomplete",
    }


def build_compliance_layer_score(
    layer_code: str,
    effective_rules: List[Dict[str, Any]],
    pipeline_result,
) -> Dict:
    """Score every effective obligation, including silent/unassessed rules."""
    tagged_rules = [
        rule for rule in effective_rules
        if layer_code in set(
            rule.get("_compliance_layers")
            or [rule.get("_compliance_layer")]
        )
    ]
    coverage = pipeline_result.playbook_coverage or {}
    statuses = coverage.get("rule_statuses", {})
    unresolved = set(coverage.get("unverified_finding_rule_ids", []))
    redlines_by_rule: Dict[str, List[Any]] = {}
    for redline in pipeline_result.redlines:
        redlines_by_rule.setdefault(str(redline.rule_id or ""), []).append(
            redline
        )

    rows: List[Dict[str, Any]] = []
    for rule in tagged_rules:
        rule_id = str(rule.get("id") or rule.get("rule_id") or "")
        assessment_status = statuses.get(rule_id, "unassessed")
        if rule_id in unresolved:
            assessment_status = "unverified"
        redlines = redlines_by_rule.get(rule_id, [])
        if assessment_status == "compliant":
            risk_level = "GREEN"
        elif assessment_status == "not_applicable":
            risk_level = ""
        elif redlines:
            risk_level = max(
                (item.risk_level for item in redlines),
                key=lambda risk: _RISK_SEVERITY.get(risk, 0),
            )
        elif assessment_status in {"violation", "missing"}:
            risk_level = str(rule.get("risk_level") or "YELLOW").upper()
        else:
            risk_level = ""
        rows.append({
            "rule_id": rule_id,
            "status": assessment_status,
            "risk_level": risk_level,
            "is_deal_breaker": bool(rule.get("is_deal_breaker")),
        })

    score = calculate_compliance_score(rows)
    score["layer_code"] = layer_code
    return score


async def seed_compliance_layers(db: AsyncSession) -> int:
    """Create or upgrade built-in legal layers by source version."""
    from scripts.compliance_layers.dpdp import DPDP_LAYER

    all_layers = [DPDP_LAYER]
    seeded = 0

    for layer_def in all_layers:
        code = layer_def["code"]

        existing_result = await db.execute(
            select(ComplianceLayer).where(ComplianceLayer.code == code)
        )
        layer = existing_result.scalar_one_or_none()
        source_version = int(layer_def.get("version", 1))
        if layer is not None and layer.version >= source_version:
            logger.info(
                "Compliance layer '%s' is current at version %d",
                code,
                layer.version,
            )
            continue

        if layer is None:
            layer = ComplianceLayer(
                code=code,
                name=layer_def["name"],
                description=layer_def["description"],
                jurisdiction=layer_def.get("jurisdiction"),
                version=source_version,
                is_active=True,
            )
            db.add(layer)
            await db.flush()

        layer.name = layer_def["name"]
        layer.description = layer_def["description"]
        layer.jurisdiction = layer_def.get("jurisdiction")
        layer.version = source_version
        layer.source_url = layer_def.get("source_url")
        layer.gazette_date = (
            date.fromisoformat(layer_def["gazette_date"])
            if layer_def.get("gazette_date") else None
        )
        layer.effective_date = (
            date.fromisoformat(layer_def["effective_date"])
            if layer_def.get("effective_date") else None
        )
        layer.last_verified_at = (
            datetime.fromisoformat(layer_def["last_verified_at"])
            if layer_def.get("last_verified_at") else None
        )
        layer.is_active = True

        current_rules_result = await db.execute(
            select(ComplianceLayerRule).where(
                ComplianceLayerRule.layer_id == layer.id
            )
        )
        current_rules = {
            rule.clause_type: rule
            for rule in current_rules_result.scalars().all()
        }

        for rule_def in layer_def["rules"]:
            clause_type = rule_def["clause_type"]
            rule = current_rules.get(clause_type)
            if rule is None:
                rule = ComplianceLayerRule(
                    layer_id=layer.id,
                    clause_type=clause_type,
                )
                db.add(rule)
            rule.primary_position = rule_def["primary_position"]
            rule.fallback_position = rule_def.get("fallback_position")
            rule.risk_level = rule_def.get("risk_level", "YELLOW")
            rule.is_deal_breaker = rule_def.get("is_deal_breaker", False)
            rule.detection_patterns = rule_def.get("detection_patterns")
            rule.detection_mode = rule_def.get(
                "detection_mode",
                "ai_with_keywords",
            )
            rule.risk_description = rule_def.get("risk_description")
            rule.acceptable_position = rule_def.get("acceptable_position")
            rule.unacceptable_signals = rule_def.get("unacceptable_signals")
            rule.acceptable_signals = rule_def.get("acceptable_signals")
            rule.sort_order = rule_def.get("sort_order", 0)

        await db.commit()
        seeded += 1
        logger.info(
            "Created or upgraded compliance layer '%s' to version %d with %d rules",
            code,
            source_version,
            len(layer_def["rules"]),
        )

    return seeded
