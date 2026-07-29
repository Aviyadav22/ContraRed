import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.drafting.models import (
    DraftRequest, PartyInfo, NDADetails, RawDraft, DraftSection,
    DraftMetadata, FinalDraft, QualityReport,
)

def _make_nda_request():
    return DraftRequest(
        contract_type="nda_mutual", drafting_perspective="balanced", risk_appetite="balanced",
        jurisdiction="US-DE",
        party_1=PartyInfo(name="Acme Inc.", entity_type="Inc.", jurisdiction="US-DE"),
        party_2=PartyInfo(name="Beta LLC", entity_type="LLC", jurisdiction="US-CA"),
        term_months=24, governing_law="Delaware", dispute_resolution="arbitration",
        nda_details=NDADetails(purpose="Evaluate partnership"),
    )

def _make_raw_draft():
    return RawDraft(
        contract_type="nda_mutual", title="NDA",
        sections=[DraftSection(number="1", heading="H", content="C", clause_type="preamble", tier_used="acceptable")],
        defined_terms={}, metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=1, tokens_used=0),
    )

def _make_final_draft():
    return FinalDraft(
        draft=_make_raw_draft(),
        quality_report=QualityReport(overall_score=90, risk_alignment=90, compliance_score=90,
                                      qa_score=90, annotations_applied=0, conflicts_flagged=0, open_annotations=[]),
    )

@pytest.mark.asyncio
async def test_orchestrator_full_pipeline():
    from app.services.drafting.orchestrator import DraftingOrchestrator
    orch = DraftingOrchestrator()
    orch.intake_agent.process = AsyncMock(return_value=_make_nda_request())
    orch.intake_agent.select_playbook = MagicMock(return_value={"contract_type": "nda_mutual", "clauses": []})
    orch.draft_agent.generate = AsyncMock(return_value=_make_raw_draft())
    orch.risk_agent.review = AsyncMock(return_value=[])
    orch.compliance_agent.review = AsyncMock(return_value=[])
    orch.qa_agent.review = AsyncMock(return_value=[])
    orch.assembler.assemble = AsyncMock(return_value=_make_final_draft())

    result = await orch.run({"contract_type": "nda_mutual", "party_1": {"name": "A", "entity_type": "I", "jurisdiction": "US-DE"}, "party_2": {"name": "B", "entity_type": "L", "jurisdiction": "US-CA"}, "nda_details": {"purpose": "test"}})
    assert isinstance(result, FinalDraft)
    assert result.quality_report.overall_score == 90
    orch.intake_agent.process.assert_awaited_once()
    orch.draft_agent.generate.assert_awaited_once()
    orch.risk_agent.review.assert_awaited_once()
    orch.compliance_agent.review.assert_awaited_once()
    orch.qa_agent.review.assert_awaited_once()
    orch.assembler.assemble.assert_awaited_once()

@pytest.mark.asyncio
async def test_orchestrator_parallel_review():
    import asyncio
    from app.services.drafting.orchestrator import DraftingOrchestrator
    orch = DraftingOrchestrator()
    orch.intake_agent.process = AsyncMock(return_value=_make_nda_request())
    orch.intake_agent.select_playbook = MagicMock(return_value={"contract_type": "nda_mutual", "clauses": []})
    orch.draft_agent.generate = AsyncMock(return_value=_make_raw_draft())
    orch.assembler.assemble = AsyncMock(return_value=_make_final_draft())

    call_order = []

    async def mock_risk(*a, **kw):
        call_order.append("risk_start")
        await asyncio.sleep(0.01)
        call_order.append("risk_end")
        return []

    async def mock_compliance(*a, **kw):
        call_order.append("compliance_start")
        await asyncio.sleep(0.01)
        call_order.append("compliance_end")
        return []

    async def mock_qa(*a, **kw):
        call_order.append("qa_start")
        await asyncio.sleep(0.01)
        call_order.append("qa_end")
        return []

    orch.risk_agent.review = mock_risk
    orch.compliance_agent.review = mock_compliance
    orch.qa_agent.review = mock_qa

    await orch.run({"contract_type": "nda_mutual", "party_1": {"name": "A", "entity_type": "I", "jurisdiction": "US-DE"}, "party_2": {"name": "B", "entity_type": "L", "jurisdiction": "US-CA"}, "nda_details": {"purpose": "test"}})
    starts = [i for i, x in enumerate(call_order) if x.endswith("_start")]
    ends = [i for i, x in enumerate(call_order) if x.endswith("_end")]
    assert len(starts) == 3
    assert max(starts) < min(ends), f"Not parallel: {call_order}"


@pytest.mark.asyncio
async def test_orchestrator_stage5_style_and_consistency():
    """Stage 5 should apply style rules and add consistency annotations."""
    from app.services.drafting.orchestrator import DraftingOrchestrator

    # Build a draft with known style issues
    draft_with_issues = RawDraft(
        contract_type="nda_mutual",
        title="NDA",
        sections=[
            DraftSection(
                number="1",
                heading="Obligations",
                content=(
                    "The Receiving Party will deliver the documents within 30 days "
                    "and will use best efforts to comply. See Section 99."
                ),
                clause_type="obligation",
                tier_used="acceptable",
            ),
        ],
        defined_terms={"Receiving Party": "the party receiving Confidential Information"},
        metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=1, tokens_used=0),
    )
    final_with_issues = FinalDraft(
        draft=draft_with_issues,
        quality_report=QualityReport(
            overall_score=90, risk_alignment=90, compliance_score=90,
            qa_score=90, annotations_applied=0, conflicts_flagged=0,
            open_annotations=[],
        ),
    )

    orch = DraftingOrchestrator()
    orch.intake_agent.process = AsyncMock(return_value=_make_nda_request())
    orch.intake_agent.select_playbook = MagicMock(return_value={"contract_type": "nda_mutual", "clauses": []})
    orch.draft_agent.generate = AsyncMock(return_value=_make_raw_draft())
    orch.risk_agent.review = AsyncMock(return_value=[])
    orch.compliance_agent.review = AsyncMock(return_value=[])
    orch.qa_agent.review = AsyncMock(return_value=[])
    orch.assembler.assemble = AsyncMock(return_value=final_with_issues)

    result = await orch.run({
        "contract_type": "nda_mutual",
        "party_1": {"name": "A", "entity_type": "I", "jurisdiction": "US-DE"},
        "party_2": {"name": "B", "entity_type": "L", "jurisdiction": "US-CA"},
        "nda_details": {"purpose": "test"},
    })

    section_content = result.draft.sections[0].content
    # Style rule: "will deliver" -> "shall deliver"
    assert "shall deliver" in section_content
    # Style rule: "30 days" -> "thirty (30) days"
    assert "thirty (30) days" in section_content
    # Style rule: "best efforts" -> "reasonable efforts"
    assert "reasonable efforts" in section_content

    # Consistency engine should flag broken cross-reference to Section 99
    agents = [a.agent for a in result.quality_report.open_annotations]
    assert "consistency" in agents
    broken_ref = [a for a in result.quality_report.open_annotations if "Section 99" in a.issue]
    assert len(broken_ref) >= 1

    # QA score should be recomputed from annotations (2 warnings = 10 penalty)
    assert result.quality_report.qa_score == max(0.0, 100.0 - 5 * len(result.quality_report.open_annotations))
