"""Regression tests for lawyer-grade review flow and playbook fidelity."""

import json
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import RiskLevel as DBRiskLevel
from app.services.analysis_pipeline import AnalysisPipeline, _infer_clause_type
from app.services.analysis_pipeline import RawRedline
from app.services.gemini_analyzer import AIServiceError, GeminiAnalyzer
from app.services.playbook_cache import get_cached_rules_dicts, invalidate_playbook_cache
from app.services.rule_engine import RiskLevel, RuleMatch


CONTRACT = """SOFTWARE SERVICES AGREEMENT

The Provider may impose a unilateral price increase at any time in its sole discretion.
This Agreement is governed by the laws of Singapore. The parties have executed this Agreement.
"""


def _rule_dict(*, mode: str = "keywords_only") -> dict:
    return {
        "id": "rule-price",
        "name": "custom_price_control",
        "clause_type": "custom_price_control",
        "risk_level": "RED",
        "primary_position": "Price changes require mutual written agreement.",
        "fallback_position": "Annual increases capped at CPI.",
        "is_deal_breaker": True,
        "detection_mode": mode,
        "detection_patterns": {
            "match_type": "exact",
            "patterns": ["unilateral price increase"],
        },
    }


def test_selected_playbook_patterns_run_in_classification():
    pipeline = AnalysisPipeline()
    extraction = pipeline._stage1_extraction(CONTRACT)

    classification = pipeline._stage2_classification(extraction, [_rule_dict()])

    custom = [m for m in classification.rule_matches if m.rule_id == "rule-price"]
    assert len(custom) == 1
    assert custom[0].detection_mode == "keywords_only"
    assert "unilateral price increase" in custom[0].match_text


def test_semantic_keyword_candidate_is_not_a_fallback_violation():
    match = RuleMatch(
        rule_id="rule-price",
        rule_name="custom_price_control",
        clause_type="custom_price_control",
        match_text="unilateral price increase",
        start_offset=0,
        end_offset=25,
        risk_level=RiskLevel.RED,
        primary_position="Mutual agreement required",
        detection_mode="ai_with_keywords",
    )

    findings = AnalysisPipeline._rule_matches_to_raw_redlines(
        [match], [_rule_dict(mode="ai_with_keywords")]
    )

    assert findings == []


def test_playbook_coverage_identifies_unassessed_rules():
    rules = [
        {"id": "rule-a", "name": "a"},
        {"id": "rule-b", "name": "b"},
    ]
    outcomes = [
        {"rule_id": "rule-a", "rule_name": "a", "status": "compliant"},
    ]

    coverage = AnalysisPipeline._build_playbook_coverage(rules, outcomes)

    assert coverage["assessed_rules"] == 1
    assert coverage["rule_statuses"] == {"rule-a": "compliant"}
    assert coverage["unassessed_rule_ids"] == ["rule-b"]
    assert coverage["complete"] is False


def test_ai_parser_preserves_rule_ledger_and_statutory_sources():
    payload = {
        "executive_summary": ["One issue."],
        "rule_results": [{
            "rule_id": "rule-price",
            "rule_name": "custom_price_control",
            "status": "violation",
            "risk_level": "RED",
            "confidence": 0.94,
            "evidence": "unilateral price increase",
            "reasoning": "Contrary to the negotiated position.",
            "statutory_references": ["Section 10, Example Act"],
        }],
        "redlines": [{
            "rule_id": "rule-price",
            "rule_name": "custom_price_control",
            "redline_type": "violation",
            "risk_level": "RED",
            "confidence": 0.94,
            "original_text": "unilateral price increase",
            "explanation": "Contrary to the negotiated position.",
            "recommendation": "Require mutual agreement.",
            "statutory_references": ["Section 10, Example Act"],
        }],
    }

    result = GeminiAnalyzer()._parse_response(json.dumps(payload))

    assert result.redlines[0].rule_id == "rule-price"
    assert result.redlines[0].statutory_references == ["Section 10, Example Act"]
    assert result.rule_results and result.rule_results[0]["status"] == "violation"


def test_invalid_ai_json_raises_instead_of_looking_like_success():
    try:
        GeminiAnalyzer()._parse_response("not valid json")
    except AIServiceError as exc:
        assert exc.error_code == "ai_parse_error"
    else:
        raise AssertionError("Invalid model output must trigger the explicit fallback path")


def test_unanchored_findings_are_removed_and_coverage_is_incomplete():
    pipeline = AnalysisPipeline()
    raw = RawRedline(
        rule_name="liability_cap",
        rule_id="rule-liability",
        risk_level="RED",
        original_text="This quotation does not occur anywhere in the agreement.",
        explanation="Potential exposure.",
        recommendation="Add a cap.",
        redline_type="violation",
        is_deal_breaker=True,
    )

    verified, stats = pipeline._stage4_verification(CONTRACT, [raw])
    coverage = pipeline._build_playbook_coverage(
        [{"id": "rule-liability", "name": "liability_cap"}],
        [{
            "rule_id": "rule-liability",
            "rule_name": "liability_cap",
            "status": "violation",
        }],
    )
    reconciled = pipeline._reconcile_playbook_coverage(coverage, [raw], verified)

    assert verified == []
    assert stats.rejected == 1
    assert reconciled["ledger_complete"] is True
    assert reconciled["verification_complete"] is False
    assert reconciled["complete"] is False
    assert reconciled["unverified_finding_rule_ids"] == ["rule-liability"]


def test_custom_rule_label_is_not_collapsed_to_unknown():
    from app.api.v1.endpoints.playbooks import RuleCreate

    rule = RuleCreate(
        clause_type="AI Training Data Restriction",
        primary_position="No customer data may be used for model training.",
    )

    assert rule.clause_type == "ai_training_data_restriction"
    assert _infer_clause_type(rule.clause_type) == "ai_training_data_restriction"


def test_seed_categories_are_normalized_for_postgres_enum():
    from app.services.seed_defaults import _database_category

    assert _database_category("msa") == "MSA"
    assert _database_category("MSA") == "MSA"
    assert _database_category("VENDOR") == "CUSTOM"


def test_specialist_contract_detection():
    pipeline = AnalysisPipeline()
    dpa = (
        "DATA PROCESSING ADDENDUM. The Data Controller appoints the Data Processor "
        "to process Personal Data for Data Subjects under this Agreement."
    )
    mutual_nda = (
        "MUTUAL NON-DISCLOSURE AGREEMENT. Each party may be a Disclosing Party or "
        "Receiving Party and shall protect Confidential Information and trade secrets."
    )

    assert pipeline._detect_contract_type(dpa) == "dpa"
    assert pipeline._detect_contract_type(mutual_nda) == "nda_mutual"


def test_playbook_cache_shape_and_mutation_are_isolated():
    playbook_id = uuid4()
    rule = SimpleNamespace(
        id=uuid4(),
        clause_type="custom_price_control",
        risk_level=DBRiskLevel.RED,
        primary_position="Mutual agreement required",
        fallback_position="CPI cap",
        is_deal_breaker=True,
        verification_prompt="Compare the increase mechanism.",
        detection_mode="ai_with_keywords",
        risk_description="Unilateral or uncapped price increase",
        acceptable_position="Mutual agreement or capped CPI increase",
        unacceptable_signals=["sole discretion"],
        acceptable_signals=["mutual written agreement"],
        clause_context="Commercial pricing control",
        detection_patterns={"match_type": "exact", "patterns": ["price increase"]},
        suggested_language={"preferred": "Mutual agreement required"},
        priority=80,
        category="commercial",
        subcategory="pricing",
        tags=["pricing"],
    )
    playbook = SimpleNamespace(
        id=playbook_id,
        updated_at=datetime.now(timezone.utc),
        rules_list=[rule],
    )
    invalidate_playbook_cache(str(playbook_id))

    compact = get_cached_rules_dicts(playbook, include_verification=False)
    full = get_cached_rules_dicts(playbook, include_verification=True)
    compact[0]["primary_position"] = "MUTATED"
    full_again = get_cached_rules_dicts(playbook, include_verification=True)

    assert "verification_prompt" not in compact[0]
    assert full[0]["verification_prompt"] == "Compare the increase mechanism."
    assert full[0]["detection_patterns"]["patterns"] == ["price increase"]
    assert full_again[0]["primary_position"] == "Mutual agreement required"


def test_neutral_is_the_only_implicit_pipeline_perspective():
    signature = inspect.signature(AnalysisPipeline.run)
    assert signature.parameters["party_side"].default == "neutral"


def test_playbook_quality_requires_the_inputs_used_by_each_detection_mode():
    from app.api.v1.endpoints.playbooks import _playbook_quality_issues

    hybrid_rule = SimpleNamespace(
        clause_type="liability_cap",
        risk_level=DBRiskLevel.RED,
        primary_position="Liability is capped at twelve months of fees.",
        fallback_position="Liability is capped at the fees paid.",
        detection_mode="ai_with_keywords",
        detection_patterns={"patterns": []},
        risk_description="Detect unlimited or one-sided liability.",
        is_deal_breaker=True,
    )

    issues = _playbook_quality_issues([hybrid_rule])

    assert any("detection patterns" in issue for issue in issues)
    assert not any("risk description" in issue for issue in issues)


def test_playbook_quality_rejects_ambiguous_deal_breaker_severity():
    from app.api.v1.endpoints.playbooks import _playbook_quality_issues

    rule = SimpleNamespace(
        clause_type="data_use",
        risk_level=DBRiskLevel.YELLOW,
        primary_position="No use of customer data for model training.",
        fallback_position="Use only with express written consent.",
        detection_mode="ai_only",
        detection_patterns=None,
        risk_description="Detect rights to train models on customer data.",
        is_deal_breaker=True,
    )

    issues = _playbook_quality_issues([rule])

    assert any("deal-breaker must use red risk" in issue for issue in issues)


def test_new_playbooks_capture_review_perspective():
    from app.api.v1.endpoints.playbooks import PlaybookCreate, PlaybookUpdate

    assert PlaybookCreate(name="Neutral review").party_side == "neutral"
    assert PlaybookCreate(name="Seller review", party_side="seller").party_side == "seller"
    assert PlaybookUpdate(party_side="buyer").party_side == "buyer"


def test_async_job_without_perspective_is_neutral():
    from app.workers.tasks import AnalysisJob

    job = AnalysisJob.from_dict({
        "job_id": "job-1",
        "document_id": "doc-1",
        "user_id": "user-1",
    })

    assert job.party_side == "neutral"


def test_batch_pipeline_passes_an_explicit_effective_perspective():
    from app.api.v1.endpoints.documents import _process_batch

    source = inspect.getsource(_process_batch)
    assert "effective_party_side" in source
    assert "party_side=effective_party_side" in source
    assert "load_default_playbook_for_type" in source


def test_dependency_resolver_targets_production_rule_uuids():
    from app.services.dependency_resolver import (
        DependencyResolver,
        PlaybookRuleDependency,
    )

    source_id = str(uuid4())
    target_id = str(uuid4())
    matches = [
        RuleMatch(
            rule_id=source_id,
            rule_name="indemnification",
            clause_type="indemnification",
            match_text="The supplier has unlimited indemnification liability.",
            start_offset=0,
            end_offset=57,
            risk_level=RiskLevel.RED,
            primary_position="Capped indemnity",
        ),
        RuleMatch(
            rule_id=target_id,
            rule_name="liability_cap",
            clause_type="liability_cap",
            match_text="Liability is capped at fees paid.",
            start_offset=58,
            end_offset=91,
            risk_level=RiskLevel.YELLOW,
            primary_position="Twelve months of fees",
        ),
    ]
    dependency = PlaybookRuleDependency(
        source_rule_id=source_id,
        target_rule_id=target_id,
        trigger_condition="source_is_red",
        effect="escalate_risk",
        effect_params={"new_risk": "RED"},
    )

    resolved, actions = DependencyResolver().resolve(matches, [dependency])

    assert resolved[1].risk_level is RiskLevel.RED
    assert actions[0].target_clause == target_id
    assert actions[0].effect_params == {"new_risk": "RED"}


def test_dependency_effects_reach_ai_only_rule_prompt_shape():
    from app.services.dependency_resolver import DependencyAction

    target_id = str(uuid4())
    rules = [{
        "id": target_id,
        "name": "data_use",
        "clause_type": "data_use",
        "risk_level": "YELLOW",
        "primary_position": "No model training.",
        "detection_mode": "ai_only",
    }]
    actions = [
        DependencyAction(
            source_clause=str(uuid4()),
            target_clause=target_id,
            trigger="source_is_red",
            effect="escalate_risk",
            message="Escalate data use",
            effect_params={"new_risk": "RED"},
        ),
        DependencyAction(
            source_clause=str(uuid4()),
            target_clause=target_id,
            trigger="source_is_red",
            effect="add_flag",
            message="Review linked confidentiality exception",
            effect_params={"message": "Review linked confidentiality exception"},
        ),
    ]

    modified = AnalysisPipeline._apply_dependency_actions_to_rule_dicts(rules, actions)
    formatted = GeminiAnalyzer().format_playbook_rules(modified)

    assert modified[0]["risk_level"] == "RED"
    assert "Review linked confidentiality exception" in formatted


def test_single_clause_review_keeps_all_rules_and_requires_perspective():
    source = inspect.getsource(GeminiAnalyzer.analyze_clause)
    signature = inspect.signature(GeminiAnalyzer.analyze_clause)

    assert "playbook_rules[:20]" not in source
    assert "Do NOT report a missing-clause finding" in source
    assert signature.parameters["party_side"].default == "neutral"
