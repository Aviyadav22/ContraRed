import pytest
from app.services.drafting.models import (
    RawDraft, DraftSection, DraftMetadata, Annotation, FinalDraft,
)


def _make_draft_and_annotations():
    draft = RawDraft(
        contract_type="nda_mutual", title="NDA",
        sections=[
            DraftSection(number="1", heading="Preamble", content="Original preamble.",
                         clause_type="preamble", tier_used="acceptable"),
            DraftSection(number="2", heading="CI Definition",
                         content="CI means everything.",
                         clause_type="confidential_info_definition", tier_used="acceptable"),
        ],
        defined_terms={},
        metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=1, tokens_used=0),
    )
    annotations = [
        Annotation(section_number="2", agent="risk", severity="warning",
                   issue="Too broad", suggested_fix="CI means marked info.", reasoning="Market standard"),
        Annotation(section_number="2", agent="compliance", severity="info",
                   issue="Add DPDP reference", suggested_fix=None, reasoning="Indian jurisdiction"),
        Annotation(section_number="*", agent="qa", severity="info",
                   issue="Section numbering OK", reasoning="Consecutive"),
    ]
    return draft, annotations


@pytest.mark.asyncio
async def test_assembler_applies_non_conflicting_fixes():
    from app.services.drafting.assembler import Assembler
    assembler = Assembler()
    draft, annotations = _make_draft_and_annotations()
    result = await assembler.assemble(draft, annotations)
    assert isinstance(result, FinalDraft)
    # Fixes are now advisory-only (never auto-applied to section content)
    assert result.draft.sections[1].content == "CI means everything."
    # The fix annotation should appear in open_annotations instead
    assert len(result.quality_report.open_annotations) >= 1


@pytest.mark.asyncio
async def test_assembler_flags_conflicts():
    from app.services.drafting.assembler import Assembler
    assembler = Assembler()
    draft, _ = _make_draft_and_annotations()
    conflicting = [
        Annotation(section_number="2", agent="risk", severity="warning",
                   issue="Too broad", suggested_fix="CI means marked info.", reasoning="Risk"),
        Annotation(section_number="2", agent="compliance", severity="warning",
                   issue="Not compliant", suggested_fix="CI means DPDP-compliant info.", reasoning="Compliance"),
    ]
    result = await assembler.assemble(draft, conflicting)
    assert result.quality_report.conflicts_flagged >= 1
    assert len(result.quality_report.open_annotations) >= 1


@pytest.mark.asyncio
async def test_assembler_quality_scores():
    from app.services.drafting.assembler import Assembler
    assembler = Assembler()
    draft, annotations = _make_draft_and_annotations()
    result = await assembler.assemble(draft, annotations)
    assert 0 <= result.quality_report.overall_score <= 100
    assert 0 <= result.quality_report.risk_alignment <= 100
