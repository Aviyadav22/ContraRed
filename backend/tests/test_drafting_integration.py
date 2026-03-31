"""
Integration tests for the full NDA and SaaS drafting pipelines.

These tests mock out AI calls so they run fast and deterministically,
but exercise the complete orchestrator -> renderer chain.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_full_nda_pipeline_no_ai():
    from app.services.drafting.orchestrator import DraftingOrchestrator

    orch = DraftingOrchestrator()
    with patch.object(orch.draft_agent, "_ai_adapt_clause", new_callable=AsyncMock) as mock_adapt, \
         patch.object(orch.risk_agent, "_ai_review", new_callable=AsyncMock) as mock_risk, \
         patch.object(orch.compliance_agent, "_ai_review", new_callable=AsyncMock) as mock_compliance:

        mock_adapt.side_effect = lambda text, guidance, jv: text
        mock_risk.return_value = []
        mock_compliance.return_value = []

        result = await orch.run({
            "contract_type": "nda_mutual",
            "drafting_perspective": "balanced",
            "risk_appetite": "balanced",
            "jurisdiction": "US-DE",
            "party_1": {"name": "Acme Inc.", "entity_type": "Inc.", "jurisdiction": "US-DE"},
            "party_2": {"name": "Beta LLC", "entity_type": "LLC", "jurisdiction": "US-CA"},
            "term_months": 24,
            "governing_law": "Delaware",
            "nda_details": {"purpose": "Evaluate a potential technology partnership"},
        })

    # Draft structure assertions
    assert result.draft.contract_type == "nda_mutual"
    assert result.draft.title == "MUTUAL NON-DISCLOSURE AGREEMENT"
    assert len(result.draft.sections) >= 14

    # Content assertions — party names, jurisdiction, key terms
    all_text = " ".join(s.content for s in result.draft.sections)
    assert "Acme Inc." in all_text
    assert "Beta LLC" in all_text
    assert "Delaware" in all_text
    assert "Confidential Information" in all_text

    # Quality report
    assert result.quality_report.overall_score > 0

    # DOCX rendering
    from app.services.drafting.renderer.docx_renderer import render_docx
    docx_bytes = render_docx(result)
    assert len(docx_bytes) > 1000

    # Add-in rendering
    from app.services.drafting.renderer.addin_renderer import render_addin_payload
    payload = render_addin_payload(result, draft_id="test-123")
    assert payload["title"] == "MUTUAL NON-DISCLOSURE AGREEMENT"
    assert len(payload["sections"]) >= 14


@pytest.mark.asyncio
async def test_full_saas_pipeline_no_ai():
    from app.services.drafting.orchestrator import DraftingOrchestrator

    orch = DraftingOrchestrator()
    with patch.object(orch.draft_agent, "_ai_adapt_clause", new_callable=AsyncMock) as mock_adapt, \
         patch.object(orch.risk_agent, "_ai_review", new_callable=AsyncMock) as mock_risk, \
         patch.object(orch.compliance_agent, "_ai_review", new_callable=AsyncMock) as mock_compliance:

        mock_adapt.side_effect = lambda text, guidance, jv: text
        mock_risk.return_value = []
        mock_compliance.return_value = []

        result = await orch.run({
            "contract_type": "saas",
            "drafting_perspective": "party_1",
            "risk_appetite": "protective",
            "jurisdiction": "US-DE",
            "party_1": {"name": "CloudCo Inc.", "entity_type": "Inc.", "jurisdiction": "US-DE"},
            "party_2": {"name": "Enterprise Corp.", "entity_type": "Corp.", "jurisdiction": "US-NY"},
            "term_months": 12,
            "governing_law": "Delaware",
            "saas_details": {
                "service_description": "Cloud-based CRM platform",
                "pricing_model": "per_user_monthly",
                "price_amount": 49.99,
                "billing_frequency": "monthly",
                "auto_renewal": True,
                "uptime_commitment": 99.9,
            },
        })

    # Draft structure assertions
    assert result.draft.contract_type == "saas"
    assert result.draft.title == "SAAS SUBSCRIPTION AGREEMENT"
    assert len(result.draft.sections) >= 20

    # Content assertions
    all_text = " ".join(s.content for s in result.draft.sections)
    assert "CloudCo Inc." in all_text
