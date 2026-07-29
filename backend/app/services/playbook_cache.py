"""
In-memory cache for Playbook data and RuleEngine instances.

Avoids re-querying the DB and re-compiling regex patterns for the same
playbook on every analysis request.  Works without Redis.
"""

import copy
import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.playbook import Playbook
from app.services.rule_engine import RuleEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------
_MAX_CACHE_SIZE = 64

# (playbook_id_str, updated_at_iso) -> RuleEngine
_engine_cache: Dict[Tuple[str, str], RuleEngine] = {}

# (playbook_id_str, updated_at_iso) -> list of rule dicts
_rules_dict_cache: Dict[Tuple[str, str, bool, bool], List[dict]] = {}

# Singleton default RuleEngine (no playbook)
_default_engine: Optional[RuleEngine] = None


def get_default_rule_engine() -> RuleEngine:
    """Return a cached default RuleEngine (built-in rules only)."""
    global _default_engine
    if _default_engine is None:
        _default_engine = RuleEngine()
    return _default_engine


def _cache_key(playbook: Playbook) -> Tuple[str, str]:
    updated = playbook.updated_at.isoformat() if playbook.updated_at else "none"
    return (str(playbook.id), updated)


def get_cached_rule_engine(playbook: Playbook) -> RuleEngine:
    """Get or create a cached RuleEngine for *playbook*."""
    key = _cache_key(playbook)
    engine = _engine_cache.get(key)
    if engine is None:
        if len(_engine_cache) >= _MAX_CACHE_SIZE:
            _engine_cache.pop(next(iter(_engine_cache)))
        if playbook.rules_list:
            engine = RuleEngine.from_playbook_rules(playbook.rules_list)
        else:
            engine = get_default_rule_engine()
        _engine_cache[key] = engine
    return engine


def get_cached_rules_dicts(
    playbook: Playbook,
    include_verification: bool = False,
    include_deal_breaker: bool = True,
) -> List[dict]:
    """Get cached list-of-dict representation of playbook rules."""
    base_key = _cache_key(playbook)
    # The old cache key ignored the two shape flags.  A request that first
    # asked for the small shape could therefore poison later legal-analysis
    # requests by silently removing verification and deal-breaker guidance.
    key = (base_key[0], base_key[1], include_verification, include_deal_breaker)
    cached = _rules_dict_cache.get(key)
    if cached is not None:
        # Phase-6 tier and condition handling mutates rule dictionaries.  Never
        # hand callers the cached objects themselves or one scan can change the
        # playbook applied to a later scan.
        return copy.deepcopy(cached)

    if len(_rules_dict_cache) >= _MAX_CACHE_SIZE:
        _rules_dict_cache.pop(next(iter(_rules_dict_cache)))

    rules = []
    for rule in (playbook.rules_list or []):
        d: dict = {
            "id": str(rule.id),  # Phase C3 — needed for tier/override targeting
            "name": rule.clause_type,
            "clause_type": rule.clause_type,  # Phase C3 — explicit field
            "risk_level": (
                rule.risk_level.value.upper()
                if hasattr(rule.risk_level, "value")
                else str(rule.risk_level).upper()
            ),
            "primary_position": rule.primary_position or "",
            "fallback_position": rule.fallback_position or "",
            # Stage 2 needs the actual user-authored patterns.  They were
            # previously omitted, leaving the selected playbook disconnected
            # from deterministic classification and fallback analysis.
            "detection_patterns": copy.deepcopy(rule.detection_patterns or {}),
            "suggested_language": copy.deepcopy(rule.suggested_language or {}),
            "priority": rule.priority,
            "category": rule.category,
            "subcategory": rule.subcategory,
            "tags": copy.deepcopy(rule.tags or []),
        }
        if include_deal_breaker:
            d["is_deal_breaker"] = rule.is_deal_breaker
        if include_verification:
            d["verification_prompt"] = rule.verification_prompt or ""
        detection_mode = rule.detection_mode or "keywords_only"
        # Older API versions accepted aliases that the rule engine and AI
        # formatter never interpreted. Normalize them at the execution edge.
        detection_mode = {
            "ai_primary": "ai_only",
            "hybrid": "ai_with_keywords",
        }.get(detection_mode, detection_mode)
        d["detection_mode"] = detection_mode
        d["risk_description"] = rule.risk_description or ""
        d["acceptable_position"] = rule.acceptable_position or ""
        d["unacceptable_signals"] = rule.unacceptable_signals or []
        d["acceptable_signals"] = rule.acceptable_signals or []
        d["clause_context"] = rule.clause_context or ""
        rules.append(d)

    _rules_dict_cache[key] = rules
    return copy.deepcopy(rules)


def invalidate_playbook_cache(playbook_id: str) -> None:
    """Remove all cached entries for *playbook_id* (call on update/delete)."""
    for cache in (_engine_cache, _rules_dict_cache):
        keys = [k for k in cache if k[0] == playbook_id]
        for k in keys:
            del cache[k]


# Map detected contract types to PlaybookCategory values in DB
_CONTRACT_TYPE_TO_CATEGORY = {
    "nda": "nda",
    "nda_mutual": "nda",
    "nda_unilateral": "nda",
    "saas": "saas",
    "employment": "employment",
    "msa": "msa",
    "dpa": "dpa",
    "ma": "msa",       # M&A falls back to MSA-like rules
    "general": None,    # No auto-select for general
}

_CONTRACT_TYPE_TO_PLAYBOOK_NAME = {
    "nda_mutual": "NDA — Mutual",
    "nda_unilateral": "NDA — Unilateral",
    "dpa": "Data Processing Agreement (DPA)",
    "consulting": "Consulting / Professional Services Agreement",
    "vendor": "Vendor / Procurement Agreement",
    "joint_venture": "Joint Venture / Partnership Agreement",
    "lease": "Lease / License Agreement (Commercial Property)",
    "healthcare": "Healthcare Vendor Agreement (India)",
    "fintech": "Fintech Services Agreement (India)",
    "it_services": "IT Services Agreement (India)",
}


async def load_default_playbook_for_type(
    db: AsyncSession,
    contract_type: str,
) -> Optional[Playbook]:
    """Load the default public playbook matching a detected contract type.

    Returns None if no matching default playbook exists.
    """
    category = _CONTRACT_TYPE_TO_CATEGORY.get(contract_type)
    playbook_name = _CONTRACT_TYPE_TO_PLAYBOOK_NAME.get(contract_type)
    if not category and not playbook_name:
        return None

    from sqlalchemy import cast, String
    query = (
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.is_default == True)  # noqa: E712
    )
    if playbook_name:
        # Name matching disambiguates mutual vs unilateral NDAs and the
        # specialist playbooks that share the legacy CUSTOM/MSA category.
        query = query.where(func.lower(Playbook.name) == playbook_name.lower())
    elif category:
        query = query.where(func.lower(cast(Playbook.category, String)) == category.lower())
    query = query.limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def load_playbook(
    db: AsyncSession,
    playbook_id_raw,
    *,
    check_access: bool = True,
    current_user_id: Optional[UUID] = None,
    current_user_org_id: Optional[UUID] = None,
    auth_in_query: bool = False,
) -> Optional[Playbook]:
    """Load a Playbook with eager-loaded rules_list.

    Args:
        playbook_id_raw: str or UUID of the playbook.
        check_access: Whether to enforce access control.
        auth_in_query: If True, adds auth filter in the SQL WHERE clause
                       instead of checking after load.
    Returns:
        The Playbook, or None if not found / access denied.
    Raises:
        ValueError: If playbook_id_raw is not a valid UUID.
    """
    pb_uuid = playbook_id_raw if isinstance(playbook_id_raw, UUID) else UUID(str(playbook_id_raw))

    query = (
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == pb_uuid)
    )

    if auth_in_query:
        access_conditions = [
            Playbook.is_public.is_(True),
            Playbook.created_by == current_user_id,
        ]
        # SQL NULL = NULL is not tenant membership. An org-less caller may
        # only see public playbooks and playbooks they personally created.
        if current_user_org_id is not None:
            access_conditions.append(
                Playbook.organization_id == current_user_org_id
            )
        query = query.where(or_(*access_conditions))

    result = await db.execute(query)
    playbook = result.scalar_one_or_none()

    if playbook is None:
        return None

    if check_access and not auth_in_query and not playbook.is_public:
        is_owner = (
            current_user_id is not None
            and playbook.created_by == current_user_id
        )
        is_same_org = (
            current_user_org_id is not None
            and playbook.organization_id is not None
            and playbook.organization_id == current_user_org_id
        )
        if not is_owner and not is_same_org:
            return None  # access denied - caller decides HTTP code

    return playbook
