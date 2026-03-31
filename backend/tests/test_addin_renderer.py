import pytest
from app.services.drafting.models import (
    RawDraft, DraftSection, DraftMetadata, FinalDraft, QualityReport,
)

def _make_final_draft():
    return FinalDraft(
        draft=RawDraft(
            contract_type="nda_mutual", title="NDA",
            sections=[DraftSection(number="1", heading="Preamble", content="Text here.",
                                   clause_type="preamble", tier_used="acceptable")],
            defined_terms={},
            metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=5, tokens_used=1000),
        ),
        quality_report=QualityReport(overall_score=90, risk_alignment=90, compliance_score=90,
                                      qa_score=90, annotations_applied=0, conflicts_flagged=0, open_annotations=[]),
    )

def test_addin_payload_structure():
    from app.services.drafting.renderer.addin_renderer import render_addin_payload
    payload = render_addin_payload(_make_final_draft(), draft_id="abc-123")
    assert payload["draft_id"] == "abc-123"
    assert payload["title"] == "NDA"
    assert len(payload["sections"]) == 1
    assert "quality_report_summary" in payload

def test_addin_sections_have_required_fields():
    from app.services.drafting.renderer.addin_renderer import render_addin_payload
    payload = render_addin_payload(_make_final_draft(), draft_id="x")
    section = payload["sections"][0]
    assert all(k in section for k in ["number", "heading", "content", "style"])
