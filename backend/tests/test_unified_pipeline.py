"""Integration tests for the unified AI-first analysis pipeline."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.analysis_pipeline import AnalysisPipeline, PipelineResult, FinalRedline


NDA_TEXT = """MUTUAL NON-DISCLOSURE AGREEMENT

1. CONFIDENTIAL INFORMATION
Confidential Information means any and all information disclosed by either party.

2. OBLIGATIONS
The Receiving Party agrees to hold all Confidential Information in strict confidence.

3. TERM
This Agreement shall remain in effect for ten (10) years. Obligations survive in perpetuity.

4. REMEDIES
Any breach shall result in liquidated damages of $5,000,000 per breach.

5. GOVERNING LAW
This Agreement shall be governed by the laws of the Cayman Islands.
"""


@pytest.mark.asyncio
async def test_pipeline_returns_unified_result():
    """Pipeline returns PipelineResult with all expected fields."""
    pipeline = AnalysisPipeline()
    with patch.object(pipeline._analyzer, 'analyze_full_contract') as mock_ai:
        mock_ai.return_value = MagicMock(
            redlines=[
                MagicMock(
                    rule_name="Liquidated Damages",
                    risk_level="RED",
                    original_text="liquidated damages of $5,000,000 per breach",
                    explanation="Disproportionate liquidated damages",
                    recommendation="Cap at actual damages",
                    redline_type="violation",
                    confidence=0.95,
                )
            ],
            executive_summary=["High-risk NDA with disproportionate penalties."],
            tokens_used=500,
        )
        with patch.object(pipeline._analyzer, 'generate_fix') as mock_fix:
            mock_fix.return_value = {"fix_text": "actual damages proven by the non-breaching party", "reasoning": "..."}
            result = await pipeline.run(NDA_TEXT, playbook_rules=None)

    assert isinstance(result, PipelineResult)
    assert len(result.executive_summary) > 0
    assert len(result.redlines) > 0
    redline = result.redlines[0]
    assert hasattr(redline, 'suggested_fix')
    assert redline.risk_level in ("RED", "YELLOW", "GREEN")
    assert redline.confidence is not None


@pytest.mark.asyncio
async def test_pipeline_graceful_degradation():
    """When AI is unavailable, pipeline falls back to rule engine."""
    pipeline = AnalysisPipeline()
    with patch.object(pipeline._analyzer, 'analyze_full_contract', side_effect=Exception("API key not set")):
        with patch.object(pipeline._analyzer, 'generate_fix', side_effect=Exception("API key not set")):
            result = await pipeline.run(NDA_TEXT, playbook_rules=None)

    assert result.partial is True
    assert result.redlines is not None


@pytest.mark.asyncio
async def test_dedup_preserves_distinct_issues_in_same_clause():
    """A lawyer can identify multiple independent issues in one clause."""
    pipeline = AnalysisPipeline()
    from app.services.confidence_scorer import ConfidenceScore, ConfidenceLevel, ConfidenceBreakdown

    r1 = FinalRedline(
        rule_name="Rule A", risk_level="RED", original_text="the same clause text here",
        verified_text="the same clause text here", explanation="...", recommendation="...",
        redline_type="violation", is_deal_breaker=False,
        confidence=ConfidenceScore(score=0.9, level=ConfidenceLevel.HIGH, breakdown=ConfidenceBreakdown()),
        verification_status="exact",
    )
    r2 = FinalRedline(
        rule_name="Rule B", risk_level="YELLOW", original_text="the same clause text here",
        verified_text="the same clause text here", explanation="...", recommendation="...",
        redline_type="violation", is_deal_breaker=False,
        confidence=ConfidenceScore(score=0.8, level=ConfidenceLevel.HIGH, breakdown=ConfidenceBreakdown()),
        verification_status="exact",
    )

    result = pipeline._dedupe_by_overlap([r1, r2], "prefix the same clause text here suffix")
    assert len(result) == 2


def test_dedup_removes_duplicate_of_same_rule():
    pipeline = AnalysisPipeline()
    from app.services.confidence_scorer import ConfidenceScore, ConfidenceLevel, ConfidenceBreakdown

    confidence = ConfidenceScore(score=0.9, level=ConfidenceLevel.HIGH, breakdown=ConfidenceBreakdown())
    r1 = FinalRedline(
        rule_name="Liability Cap", rule_id="rule-liability", risk_level="RED",
        original_text="the same clause text here", verified_text="the same clause text here",
        explanation="...", recommendation="...", redline_type="violation",
        is_deal_breaker=True, confidence=confidence, verification_status="exact",
    )
    r2 = FinalRedline(
        rule_name="Liability Cap", rule_id="rule-liability", risk_level="YELLOW",
        original_text="the same clause text here", verified_text="the same clause text here",
        explanation="duplicate", recommendation="...", redline_type="violation",
        is_deal_breaker=False, confidence=confidence, verification_status="exact",
    )

    result = pipeline._dedupe_by_overlap([r1, r2], "prefix the same clause text here suffix")
    assert len(result) == 1
    assert result[0].risk_level == "RED"


def test_infer_clause_type():
    """Known concepts snap canonically; custom concepts keep a stable slug."""
    from app.services.analysis_pipeline import _infer_clause_type
    assert _infer_clause_type("Liability Cap") == "liability_cap"
    assert _infer_clause_type("Non-Compete Clause") == "non_compete"
    assert _infer_clause_type("Governing Law") == "governing_law"
    assert _infer_clause_type("Data Protection") == "data_protection"
    assert _infer_clause_type("Random Unknown") == "random_unknown"
