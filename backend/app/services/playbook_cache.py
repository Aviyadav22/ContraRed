"""
In-memory cache for Playbook data and RuleEngine instances.

Avoids re-querying the DB and re-compiling regex patterns for the same
playbook on every analysis request.  Works without Redis.
"""

import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
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
_rules_dict_cache: Dict[Tuple[str, str], List[dict]] = {}

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
    key = _cache_key(playbook)
    cached = _rules_dict_cache.get(key)
    if cached is not None:
        return cached

    if len(_rules_dict_cache) >= _MAX_CACHE_SIZE:
        _rules_dict_cache.pop(next(iter(_rules_dict_cache)))

    rules = []
    for rule in (playbook.rules_list or []):
        d: dict = {
            "name": rule.clause_type,
            "risk_level": (
                rule.risk_level.value.upper()
                if hasattr(rule.risk_level, "value")
                else str(rule.risk_level).upper()
            ),
            "primary_position": rule.primary_position or "",
            "fallback_position": rule.fallback_position or "",
        }
        if include_deal_breaker:
            d["is_deal_breaker"] = rule.is_deal_breaker
        if include_verification:
            d["verification_prompt"] = rule.verification_prompt or ""
        d["detection_mode"] = rule.detection_mode or "keywords_only"
        d["risk_description"] = rule.risk_description or ""
        d["acceptable_position"] = rule.acceptable_position or ""
        d["unacceptable_signals"] = rule.unacceptable_signals or []
        d["acceptable_signals"] = rule.acceptable_signals or []
        d["clause_context"] = rule.clause_context or ""
        rules.append(d)

    _rules_dict_cache[key] = rules
    return rules


def invalidate_playbook_cache(playbook_id: str) -> None:
    """Remove all cached entries for *playbook_id* (call on update/delete)."""
    for cache in (_engine_cache, _rules_dict_cache):
        keys = [k for k in cache if k[0] == playbook_id]
        for k in keys:
            del cache[k]


# Map detected contract types to PlaybookCategory values in DB
_CONTRACT_TYPE_TO_CATEGORY = {
    "nda": "nda",
    "saas": "saas",
    "employment": "employment",
    "msa": "msa",
    "dpa": "dpa",
    "ma": "msa",       # M&A falls back to MSA-like rules
    "general": None,    # No auto-select for general
}


async def load_default_playbook_for_type(
    db: AsyncSession,
    contract_type: str,
) -> Optional[Playbook]:
    """Load the default public playbook matching a detected contract type.

    Returns None if no matching default playbook exists.
    """
    category = _CONTRACT_TYPE_TO_CATEGORY.get(contract_type)
    if not category:
        return None

    from sqlalchemy import func, cast, String
    query = (
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(
            Playbook.is_default == True,  # noqa: E712
            func.lower(cast(Playbook.category, String)) == category.lower(),
        )
        .limit(1)
    )
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

    if auth_in_query and current_user_org_id is not None:
        query = query.where(
            (Playbook.is_public == True)  # noqa: E712
            | (Playbook.organization_id == current_user_org_id)
            | (Playbook.created_by == current_user_id)
        )

    result = await db.execute(query)
    playbook = result.scalar_one_or_none()

    if playbook is None:
        return None

    if check_access and not auth_in_query and not playbook.is_public:
        if (
            playbook.created_by != current_user_id
            and playbook.organization_id != current_user_org_id
        ):
            return None  # access denied — caller decides HTTP code

    return playbook
