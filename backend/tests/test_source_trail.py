"""Tests for source trail data exposure — confidence breakdown, cross references, hallucination stats."""
import pytest


# ============================================================
# RedlineItem model tests
# ============================================================

def test_redline_item_has_confidence_breakdown():
    """RedlineItem should accept confidence_breakdown dict."""
    from app.api.v1.endpoints.documents import RedlineItem
    item = RedlineItem(
        id="test-1",
        risk_level="RED",
        rule_name="Test Rule",
        clause_text="Some clause text",
        explanation="Risk explanation",
        confidence=0.85,
        confidence_level="HIGH",
        confidence_breakdown={
            "text_verification": 0.95,
            "ai_agreement": 0.8,
            "playbook_match": 0.9,
        },
    )
    assert item.confidence_breakdown is not None
    assert item.confidence_breakdown["text_verification"] == 0.95


def test_redline_item_has_cross_references():
    """RedlineItem should accept cross_references list."""
    from app.api.v1.endpoints.documents import RedlineItem
    item = RedlineItem(
        id="test-2",
        risk_level="YELLOW",
        rule_name="Test Rule",
        clause_text="Some clause text",
        explanation="Risk explanation",
        cross_references=["Liability Cap", "Indemnification"],
    )
    assert item.cross_references is not None
    assert len(item.cross_references) == 2


def test_redline_item_has_statutory_references():
    """RedlineItem should accept statutory_references list."""
    from app.api.v1.endpoints.documents import RedlineItem
    item = RedlineItem(
        id="test-3",
        risk_level="RED",
        rule_name="DPDP Consent",
        clause_text="Some clause text",
        explanation="Risk explanation",
        statutory_references=["Section 6, DPDP Act 2023", "Section 73, Indian Contract Act 1872"],
    )
    assert item.statutory_references is not None
    assert len(item.statutory_references) == 2
    assert "DPDP Act 2023" in item.statutory_references[0]


def test_redline_item_defaults_none_for_optional_fields():
    """Optional source trail fields should default to None."""
    from app.api.v1.endpoints.documents import RedlineItem
    item = RedlineItem(
        id="test-4",
        risk_level="GREEN",
        rule_name="Test Rule",
        clause_text="Some clause text",
        explanation="Risk explanation",
    )
    assert item.confidence_breakdown is None
    assert item.cross_references is None
    assert item.statutory_references is None


# ============================================================
# AnalysisResult model tests
# ============================================================

def test_analysis_result_has_hallucination_stats():
    """AnalysisResult should accept hallucination_stats dict."""
    from app.api.v1.endpoints.documents import AnalysisResult
    result = AnalysisResult(
        document_id="doc-1",
        filename="test.docx",
        risks=[],
        total_risks=0,
        risk_summary={"red": 0, "yellow": 0, "green": 0},
        hallucination_stats={
            "total_checked": 10,
            "exact_match": 7,
            "normalized": 2,
            "not_found": 1,
            "pass_rate": 0.9,
        },
    )
    assert result.hallucination_stats is not None
    assert result.hallucination_stats["pass_rate"] == 0.9


def test_analysis_result_hallucination_stats_optional():
    """hallucination_stats should be optional (backwards compatible)."""
    from app.api.v1.endpoints.documents import AnalysisResult
    result = AnalysisResult(
        document_id="doc-2",
        filename="test.docx",
        risks=[],
        total_risks=0,
        risk_summary={"red": 0, "yellow": 0, "green": 0},
    )
    assert result.hallucination_stats is None


# ============================================================
# VerificationSummaryResponse model tests
# ============================================================

def test_verification_summary_response_model():
    """VerificationSummaryResponse should accept all fields."""
    from app.api.v1.endpoints.documents import VerificationSummaryResponse
    summary = VerificationSummaryResponse(
        total_findings=10,
        verified_findings=8,
        exact_match=5,
        normalized_match=2,
        fuzzy_corrected=1,
        not_found=2,
        pass_rate=80.0,
        hallucination_rate=20.0,
        avg_confidence=0.75,
        confidence_distribution={"HIGH": 5, "MEDIUM": 3, "LOW": 2},
        industry_benchmark="Your analysis is GOOD.",
    )
    assert summary.total_findings == 10
    assert summary.pass_rate == 80.0
    assert summary.confidence_distribution["HIGH"] == 5


# ============================================================
# Prompt template tests
# ============================================================

def test_prompt_template_includes_statutory_reference_instruction():
    """System prompt should instruct AI to cite statute section numbers."""
    from app.services.prompt_templates import render_system_prompt
    prompt = render_system_prompt()
    assert "Statutory References" in prompt
    assert "section number" in prompt.lower()
    assert "statutory_references" in prompt


def test_prompt_template_output_format_has_statutory_references():
    """Prompt output format should include statutory_references array."""
    from app.services.prompt_templates import SYSTEM_PROMPT_V2
    assert '"statutory_references"' in SYSTEM_PROMPT_V2
