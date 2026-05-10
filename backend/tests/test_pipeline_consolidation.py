"""Phase D verification — sanity tests for the consolidation work.

Covers:
  - snap_to_clause_type maps free strings into the canonical taxonomy
  - _apply_phase6_wiring swaps tier positions and applies overrides
  - _apply_overrides_to_rule_dicts honors suppress / risk / position effects

These tests intentionally avoid DB / network — they exercise pure functions
on plain dicts and lightweight stand-ins for the SQLAlchemy models.
"""

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from app.services.analysis_pipeline import AnalysisPipeline
from app.services.clause_classifier import ClauseType
from app.services.clause_taxonomy import snap_to_clause_type


# ---------------------------------------------------------------------------
# C1 — snap_to_clause_type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("liability_cap", ClauseType.LIABILITY_CAP),
        ("Liability Cap", ClauseType.LIABILITY_CAP),
        ("Limitation of Liability", ClauseType.LIABILITY_CAP),
        ("LIABILITY-CAP", ClauseType.LIABILITY_CAP),
        ("Indemnification", ClauseType.INDEMNIFICATION_SCOPE),
        ("Confidentiality Obligations", ClauseType.CONFIDENTIALITY_OBLIGATIONS),
        ("Auto-Renewal Clause", ClauseType.AUTO_RENEWAL),
        ("Termination for Cause", ClauseType.TERMINATION_FOR_CAUSE),
        ("Governing Law", ClauseType.GOVERNING_LAW),
        ("force majeure", ClauseType.FORCE_MAJEURE),
        ("garbage nonsense", ClauseType.UNKNOWN),
        ("", ClauseType.UNKNOWN),
        (None, ClauseType.UNKNOWN),
    ],
)
def test_snap_to_clause_type(raw, expected):
    assert snap_to_clause_type(raw) is expected


# ---------------------------------------------------------------------------
# C3 — _apply_overrides_to_rule_dicts
# ---------------------------------------------------------------------------

def _make_rule_dict(rule_id: str, clause_type: str, **kwargs) -> Dict[str, Any]:
    base = {
        "id": rule_id,
        "name": clause_type,
        "clause_type": clause_type,
        "risk_level": "YELLOW",
        "primary_position": "Original position text",
        "fallback_position": "Original fallback",
        "is_deal_breaker": False,
    }
    base.update(kwargs)
    return base


def _override(
    rule_id: str,
    *,
    risk: str = None,
    position: str = None,
    deal_breaker: bool = None,
    suppress: bool = False,
):
    return SimpleNamespace(
        rule_id=rule_id,
        override_risk_level=risk,
        override_position_text=position,
        override_is_deal_breaker=deal_breaker,
        suppress_rule=suppress,
        rule=None,
    )


def test_apply_overrides_to_rule_dicts_changes_risk_and_position():
    rules = [_make_rule_dict("rule-A", "liability_cap")]
    overrides = [_override("rule-A", risk="GREEN", position="Adjusted position")]

    out = AnalysisPipeline._apply_overrides_to_rule_dicts(
        rules, overrides, {}
    )
    assert len(out) == 1
    assert out[0]["risk_level"] == "GREEN"
    assert out[0]["primary_position"] == "Adjusted position"
    assert out[0]["is_deal_breaker"] is False


def test_apply_overrides_to_rule_dicts_suppresses():
    rules = [
        _make_rule_dict("rule-A", "liability_cap"),
        _make_rule_dict("rule-B", "non_compete"),
    ]
    overrides = [_override("rule-A", suppress=True)]

    out = AnalysisPipeline._apply_overrides_to_rule_dicts(
        rules, overrides, {}
    )
    assert len(out) == 1
    assert out[0]["id"] == "rule-B"


def test_apply_overrides_to_rule_dicts_matches_by_clause_type_fallback():
    """When the override's rule_id doesn't match any dict's id, fall back to
    matching on the clause_type via the supplied mapping."""
    rules = [_make_rule_dict("dict-id-X", "liability_cap")]
    # override rule_id intentionally does NOT match any dict id
    overrides = [_override("uuid-not-in-dicts", risk="RED")]
    rule_id_to_clause_type = {"uuid-not-in-dicts": "liability_cap"}

    out = AnalysisPipeline._apply_overrides_to_rule_dicts(
        rules, overrides, rule_id_to_clause_type
    )
    assert out[0]["risk_level"] == "RED"


# ---------------------------------------------------------------------------
# C3 — _apply_phase6_wiring tier swap
# ---------------------------------------------------------------------------

def test_phase6_tier_swap_replaces_primary_position():
    pipe = AnalysisPipeline()
    rules = [
        _make_rule_dict("rule-A", "liability_cap"),
        _make_rule_dict("rule-B", "non_compete"),
    ]
    tier = SimpleNamespace(
        rule_id="rule-A",
        tier_level=3,
        position_text="Walk-away: refuse any cap below 24 months ARR",
    )
    rule_tiers = {"rule-A": tier}

    new_rules, new_matches = pipe._apply_phase6_wiring(
        playbook_rules=rules,
        rule_matches=[],
        deal_context=None,
        conditions=None,
        dependencies=None,
        rule_tiers_by_rule=rule_tiers,
        tier_preference="walk_away",
    )

    by_id = {r["id"]: r for r in new_rules}
    assert by_id["rule-A"]["primary_position"].startswith("Walk-away:")
    # rule-B left untouched
    assert by_id["rule-B"]["primary_position"] == "Original position text"


def test_phase6_tier_swap_skipped_when_preference_is_ideal():
    pipe = AnalysisPipeline()
    rules = [_make_rule_dict("rule-A", "liability_cap")]
    tier = SimpleNamespace(
        rule_id="rule-A", tier_level=3,
        position_text="should-not-be-used",
    )

    new_rules, _ = pipe._apply_phase6_wiring(
        playbook_rules=rules,
        rule_matches=[],
        deal_context=None,
        conditions=None,
        dependencies=None,
        rule_tiers_by_rule={"rule-A": tier},
        tier_preference="ideal",
    )

    assert new_rules[0]["primary_position"] == "Original position text"


# ---------------------------------------------------------------------------
# B5 — Stage 6 fix generation removed
# ---------------------------------------------------------------------------

def test_pipeline_no_stage6_method():
    """Stage 6 batched fix generation was removed (B5). Ensure the method
    is gone so future code doesn't accidentally reintroduce it."""
    assert not hasattr(AnalysisPipeline, "_stage6_fix_generation")


# ---------------------------------------------------------------------------
# AI-primary path discipline — the rule engine must NEVER add findings to
# the final output when AI is healthy. It exists only as a fallback when AI
# is down (and as a regex_matched corroboration signal). These tests guard
# against accidental reintroduction of merged AI + rule-engine output.
# ---------------------------------------------------------------------------


def test_ai_path_is_exclusive_in_stage3_source():
    """Read the Stage 3 AI-success branch and assert it builds raw_redlines
    only from `ai_result.redlines` — the rule_matches list is used solely
    for the regex_matched flag, never to add new findings."""
    import inspect
    src = inspect.getsource(AnalysisPipeline._stage3_risk_assessment)
    # The for-loop must iterate AI redlines, not rule matches.
    assert "for ai_redline in ai_result.redlines:" in src, (
        "Stage 3 happy path must produce one RawRedline per AI redline. "
        "If this assertion ever fires it means the rule-engine output is "
        "being merged into the AI happy path — that violates AI-primary."
    )
    # The fallback must NOT live in this method.
    assert "_rule_matches_to_raw_redlines" not in src, (
        "_stage3_risk_assessment is the AI-only path. The rule-engine "
        "fallback must be invoked from run() in the except branch, not here."
    )


def test_ai_down_branch_sets_ai_used_false():
    """When AI fails, run() must flip ai_used=False so the frontend can
    surface the fallback warning. This is the user-visible contract."""
    import inspect
    src = inspect.getsource(AnalysisPipeline.run)
    # Both AIServiceUnavailable and generic Exception branches must flip the flag.
    occurrences = src.count("ai_used = False")
    assert occurrences >= 2, (
        f"Expected at least 2 'ai_used = False' assignments in run() "
        f"(AIServiceUnavailable + generic Exception); found {occurrences}"
    )


def test_fallback_executive_summary_marks_rule_engine_only():
    """The fallback executive_summary must explicitly tell the user this
    is the secondary path."""
    import inspect
    src = inspect.getsource(AnalysisPipeline.run)
    assert "AI analysis unavailable" in src
    assert "rule engine only" in src
