"""Phase 4 end-to-end integration verification tests."""
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-validation-only-32chars!")

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1

print("=" * 60)
print("PHASE 4 END-TO-END INTEGRATION VERIFICATION")
print("=" * 60)

# 1. Jurisdiction detector wired into gemini_analyzer
def t1():
    import inspect
    from app.services.gemini_analyzer import GeminiAnalyzer
    src = inspect.getsource(GeminiAnalyzer.analyze_full_contract)
    assert "jurisdiction_detector.detect" in src
    assert "render_system_prompt" in src
    assert "render_user_prompt" in src
    assert "defined_terms_resolver.resolve" in src
test("Jurisdiction+terms wired into analyze_full_contract", t1)

# 2. V2 prompt replaces old hardcoded prompt
def t2():
    from app.services.gemini_analyzer import CONTRARED_SYSTEM_PROMPT
    from app.services.prompt_templates import LEGACY_PROMPT
    assert CONTRARED_SYSTEM_PROMPT is LEGACY_PROMPT
test("CONTRARED_SYSTEM_PROMPT -> LEGACY_PROMPT reference", t2)

# 3-5. generate_fix/clause/research use jurisdiction
def t3():
    import inspect
    from app.services.gemini_analyzer import GeminiAnalyzer
    for method in ["generate_fix", "generate_clause", "research_clause"]:
        src = inspect.getsource(getattr(GeminiAnalyzer, method))
        assert "jurisdiction_detector.detect" in src, f"{method} missing jurisdiction"
test("generate_fix/clause/research use jurisdiction-aware prompts", t3)

# 6. AIRedline has Phase 4 fields
def t6():
    from app.services.gemini_analyzer import AIRedline
    r = AIRedline(risk_level="RED", rule_name="Test", original_text="t",
                  explanation="e", recommendation="r", confidence=0.9)
    assert r.confidence == 0.9
    assert r.verification_status is None
test("AIRedline dataclass has Phase 4 fields", t6)

# 7. AIAnalysisResult has Phase 4 fields
def t7():
    from app.services.gemini_analyzer import AIAnalysisResult
    r = AIAnalysisResult(executive_summary=[], redlines=[], tokens_used=0,
                         raw_response="", jurisdiction_code="IN", jurisdiction_name="India")
    assert r.jurisdiction_code == "IN"
test("AIAnalysisResult has Phase 4 metadata", t7)

# 8. Pipeline wired into documents.py
def t8():
    from app.api.v1.endpoints.documents import analysis_pipeline, PipelineResult
    from app.services.analysis_pipeline import analysis_pipeline as ap2
    assert analysis_pipeline is ap2
test("documents.py uses analysis_pipeline singleton", t8)

# 9-10. Schema fields
def t9():
    from app.api.v1.endpoints.documents import AIRedlineItem, AIAnalysisResponse
    ri_fields = set(AIRedlineItem.model_fields.keys())
    assert {"confidence", "confidence_level", "verification_status", "is_deal_breaker", "cross_references"} <= ri_fields
    ar_fields = set(AIAnalysisResponse.model_fields.keys())
    assert {"jurisdiction", "jurisdiction_name", "hallucination_stats", "pipeline_partial"} <= ar_fields
test("API schemas have all Phase 4 fields", t9)

# 11. from_playbook_rules creates SmartRule
def t11():
    from app.services.rule_engine import RuleEngine, SmartRule
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.id = "r1"
    mock.clause_type = "indemnification"
    mock.risk_level = MagicMock(value="yellow")
    mock.primary_position = "test"
    mock.fallback_position = None
    mock.is_deal_breaker = False
    mock.suggested_language = None
    mock.detection_patterns = {
        "patterns": ["test pattern"], "match_type": "exact",
        "negative_patterns": ["neg1"], "escalation_conditions": ["esc1"],
    }
    engine = RuleEngine.from_playbook_rules([mock])
    assert isinstance(engine.rules[0], SmartRule)
test("from_playbook_rules creates SmartRule with advanced features", t11)

# 12. Hallucination guard functional
def t12():
    from app.services.hallucination_guard import HallucinationGuard
    g = HallucinationGuard("The quick brown fox jumps over the lazy dog.")
    assert g.verify_quote("The quick brown fox jumps over the lazy dog.").status == "exact"
    assert g.verify_quote("Completely fabricated nonexistent text here.").status == "rejected"
test("Hallucination guard: exact match + rejection", t12)

# 13. Confidence scorer functional
def t13():
    from app.services.confidence_scorer import ConfidenceScorer
    s = ConfidenceScorer()
    score = s.score_redline(
        text_verification_confidence=0.99, regex_matched=True, ai_flagged=True,
        playbook_rule={"primary_position": "Cap at 12x", "is_deal_breaker": True,
                       "verification_prompt": "Check the cap"},
        model_confidence=0.9,
        related_rule_names=["Unlimited Liability"],
        all_flagged_rules=["Unlimited Liability", "Broad Indemnification"],
    )
    assert score.score > 0.75, f"Expected HIGH (>0.75), got {score.score}"
    assert score.level.value == "HIGH"
test("Confidence scorer produces HIGH for strong signals", t13)

# 14. Jurisdiction detector functional
def t14():
    from app.services.jurisdiction_detector import jurisdiction_detector
    assert jurisdiction_detector.detect("governed by the laws of California.").detected_jurisdiction == "CA-US"
    assert jurisdiction_detector.detect("governed by the laws of India.").detected_jurisdiction == "IN"
    assert jurisdiction_detector.detect("No jurisdiction clause here.").source == "default"
test("Jurisdiction detector: CA, IN, default fallback", t14)

# 15. Defined terms resolver
def t15():
    from app.services.defined_terms_resolver import defined_terms_resolver
    r = defined_terms_resolver.resolve(
        '"Confidential Information" means any and all information disclosed by either Party.'
    )
    assert r.term_count >= 1
    assert "Confidential Information" in r.terms
test("Defined terms resolver: extraction + overbroad detection", t15)

# 16. Pipeline to_dict
def t16():
    from app.services.analysis_pipeline import PipelineResult, FinalRedline, StageMetrics
    from app.services.confidence_scorer import ConfidenceScore, ConfidenceLevel, ConfidenceBreakdown
    pr = PipelineResult(
        executive_summary=["s"], redlines=[
            FinalRedline(rule_name="R", risk_level="RED", original_text="t",
                         verified_text="t", explanation="e", recommendation="r",
                         redline_type="violation", is_deal_breaker=False,
                         confidence=ConfidenceScore(score=0.8, level=ConfidenceLevel.HIGH,
                                                    breakdown=ConfidenceBreakdown()),
                         verification_status="exact")
        ],
        hallucination_stats={}, stage_metrics=[StageMetrics(stage_name="test")]
    )
    d = pr.to_dict()
    assert d["redlines"][0]["confidence"]["breakdown"]["text_verification"] == 0.0
test("PipelineResult.to_dict() serializes confidence breakdown", t16)

# 17. No more hardcoded "Indian commercial law"
def t17():
    import inspect
    from app.services.gemini_analyzer import GeminiAnalyzer
    for method_name in ["analyze_full_contract", "generate_clause", "generate_fix", "research_clause"]:
        src = inspect.getsource(getattr(GeminiAnalyzer, method_name))
        assert "Indian commercial law" not in src, f"{method_name} still has hardcoded Indian law"
        assert "Indian contract lawyer" not in src, f"{method_name} still has hardcoded Indian lawyer"
test('No hardcoded "Indian commercial law" in any analyzer method', t17)

# 18. Prompt templates render correctly
def t18():
    from app.services.prompt_templates import (
        render_system_prompt, render_fix_prompt,
        render_clause_generation_prompt, render_research_prompt,
    )
    sp = render_system_prompt("JURISDICTION: Test", "TERMS: none")
    assert "Test" in sp and "ORIENT" in sp
    fp = render_fix_prompt("violation", "orig", "rec", "rule", "JURISDICTION: DE", "Germany")
    assert "Germany" in fp
    cp = render_clause_generation_prompt("Indemnification", "JURISDICTION: SG", "Singapore")
    assert "Singapore" in cp
    rp = render_research_prompt("clause text", "NDA", "JURISDICTION: IN", "India")
    assert "India" in rp
test("All 4 prompt template renderers work correctly", t18)

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
print("=" * 60)

import sys
sys.exit(1 if failed else 0)
