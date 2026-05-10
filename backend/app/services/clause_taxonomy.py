"""
Clause taxonomy helpers (Phase C1).

`snap_to_clause_type(raw)` is the single normalization entry point for
free-string `clause_type` values entering the system from any boundary:
- AI output parsing (gemini_analyzer)
- Playbook rule create/update endpoints
- ClauseLibrary CRUD
- DocumentRisk persistence

It is deliberately permissive — falls back to ClauseType.UNKNOWN rather
than raising — because the snap is also called inside the AI parser
where rejecting the entire response over a typo would be worse than
storing UNKNOWN and logging a WARN.
"""

from __future__ import annotations

import logging
import re
from difflib import get_close_matches
from typing import Dict, Iterable, Optional

from app.services.clause_classifier import ClauseGroup, ClauseType, TYPE_TO_GROUP

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fast lookups
# ---------------------------------------------------------------------------

_VALID_VALUES: frozenset = frozenset(t.value for t in ClauseType)
_BY_NORMALIZED: Dict[str, ClauseType] = {t.value.lower(): t for t in ClauseType}


def _normalize(raw: str) -> str:
    """snake_case-ish normalization for matching."""
    if not raw:
        return ""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


# ---------------------------------------------------------------------------
# Keyword bridges — old free-string conventions to enum
# ---------------------------------------------------------------------------
#
# Folds the previous _infer_clause_type mapping that lived in
# analysis_pipeline.py. Each (substring -> ClauseType) is checked against
# the normalized input.

_KEYWORD_BRIDGES: tuple = (
    ("liability_cap", ClauseType.LIABILITY_CAP),
    ("limitation_of_liability", ClauseType.LIABILITY_CAP),
    ("limitation_on_liability", ClauseType.LIABILITY_CAP),
    ("aggregate_liability", ClauseType.LIABILITY_CAP),
    ("liability", ClauseType.LIABILITY_CAP),
    ("indemnif", ClauseType.INDEMNIFICATION_SCOPE),
    ("confidential", ClauseType.CONFIDENTIALITY_OBLIGATIONS),
    ("non_disclosure", ClauseType.CONFIDENTIALITY_OBLIGATIONS),
    ("data_protection", ClauseType.DATA_PROTECTION),
    ("dpdp", ClauseType.DATA_PROTECTION),
    ("breach_notif", ClauseType.BREACH_NOTIFICATION),
    ("term_for_cause", ClauseType.TERMINATION_FOR_CAUSE),
    ("term_for_convenience", ClauseType.TERMINATION_FOR_CONVENIENCE),
    ("terminat", ClauseType.TERMINATION_FOR_CAUSE),
    ("auto_renew", ClauseType.AUTO_RENEWAL),
    ("renewal", ClauseType.AUTO_RENEWAL),
    ("survival", ClauseType.SURVIVAL),
    ("cure_period", ClauseType.CURE_PERIOD),
    ("payment_term", ClauseType.PAYMENT_TERMS),
    ("late_payment", ClauseType.LATE_PAYMENT),
    ("price_escalation", ClauseType.PRICE_ESCALATION),
    ("audit_right", ClauseType.AUDIT_RIGHTS),
    ("most_favored", ClauseType.MOST_FAVORED_NATION),
    ("set_off", ClauseType.SET_OFF_RIGHTS),
    ("ip_ownership", ClauseType.IP_OWNERSHIP),
    ("intellectual_property", ClauseType.IP_OWNERSHIP),
    ("license_grant", ClauseType.LICENSE_GRANT),
    ("ip_indemnif", ClauseType.IP_INDEMNIFICATION),
    ("background_ip", ClauseType.BACKGROUND_IP),
    ("non_compete", ClauseType.NON_COMPETE),
    ("non_solicit", ClauseType.NON_SOLICITATION),
    ("exclusiv", ClauseType.EXCLUSIVITY),
    ("governing_law", ClauseType.GOVERNING_LAW),
    ("jurisdiction", ClauseType.JURISDICTION),
    ("arbitrat", ClauseType.ARBITRATION),
    ("force_majeure", ClauseType.FORCE_MAJEURE),
    ("entire_agreement", ClauseType.ENTIRE_AGREEMENT),
    ("merger", ClauseType.ENTIRE_AGREEMENT),
    ("amendment", ClauseType.AMENDMENTS),
    ("severability", ClauseType.SEVERABILITY),
    ("definitions", ClauseType.DEFINITIONS),
    ("recital", ClauseType.RECITALS),
    ("preamble", ClauseType.RECITALS),
    ("sla", ClauseType.SLA_TERMS),
    ("service_level", ClauseType.SLA_TERMS),
    ("data_portab", ClauseType.DATA_PORTABILITY),
    ("security_standard", ClauseType.SECURITY_STANDARDS),
    ("api_right", ClauseType.API_RIGHTS),
    ("acceptable_use", ClauseType.ACCEPTABLE_USE),
    ("anti_brib", ClauseType.ANTI_BRIBERY),
    ("sanctions", ClauseType.SANCTIONS_COMPLIANCE),
    ("regulatory", ClauseType.REGULATORY_COMPLIANCE),
    ("assignment", ClauseType.ASSIGNMENT),
    ("change_of_control", ClauseType.CHANGE_OF_CONTROL),
    ("subcontract", ClauseType.SUBCONTRACTING),
    ("business_continuity", ClauseType.BUSINESS_CONTINUITY),
    ("transition_assist", ClauseType.TRANSITION_ASSISTANCE),
    ("insolvency", ClauseType.COUNTERPARTY_INSOLVENCY),
    ("bankrupt", ClauseType.COUNTERPARTY_INSOLVENCY),
    ("return_of_material", ClauseType.RETURN_OF_MATERIALS),
    ("duration", ClauseType.DURATION),
    ("term", ClauseType.DURATION),
    ("insurance", ClauseType.INSURANCE),
    ("consequential", ClauseType.CONSEQUENTIAL_DAMAGES),
    ("currency", ClauseType.CURRENCY),
    ("tax", ClauseType.TAXES),
    ("moral_right", ClauseType.MORAL_RIGHTS),
    ("confidentiality_excep", ClauseType.CONFIDENTIALITY_EXCEPTIONS),
)


def snap_to_clause_type(raw: Optional[str]) -> ClauseType:
    """Normalize any free-string clause_type into a ClauseType enum value.

    Lookup order:
      1. Exact match on enum value (case-insensitive)
      2. Normalized snake_case match
      3. Substring keyword match
      4. difflib close-match (handles typos)
      5. ClauseType.UNKNOWN (with WARN log)
    """
    if not raw:
        return ClauseType.UNKNOWN

    normalized = _normalize(raw)
    if not normalized:
        return ClauseType.UNKNOWN

    # 1+2: direct lookup
    direct = _BY_NORMALIZED.get(normalized)
    if direct is not None:
        return direct

    # 3: substring bridges
    for needle, target in _KEYWORD_BRIDGES:
        if needle in normalized:
            return target

    # 4: difflib close match
    close = get_close_matches(normalized, list(_BY_NORMALIZED.keys()), n=1, cutoff=0.85)
    if close:
        return _BY_NORMALIZED[close[0]]

    logger.warning("snap_to_clause_type: no match for %r — defaulting to UNKNOWN", raw)
    return ClauseType.UNKNOWN


def is_valid_clause_type_value(value: str) -> bool:
    """Cheap predicate for places that just need a yes/no."""
    return value in _VALID_VALUES


def group_for(clause_type: ClauseType) -> ClauseGroup:
    return TYPE_TO_GROUP.get(clause_type, ClauseGroup.FORMATION)


def all_clause_type_values() -> Iterable[str]:
    return _VALID_VALUES
