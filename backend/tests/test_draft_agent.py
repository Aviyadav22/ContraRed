import pytest
from unittest.mock import AsyncMock, patch
from app.services.drafting.models import DraftRequest, PartyInfo, NDADetails, RawDraft

def _make_nda_request() -> DraftRequest:
    return DraftRequest(
        contract_type="nda_mutual", drafting_perspective="balanced", risk_appetite="balanced",
        jurisdiction="US-DE",
        party_1=PartyInfo(name="Acme Inc.", entity_type="Inc.", jurisdiction="US-DE"),
        party_2=PartyInfo(name="Beta LLC", entity_type="LLC", jurisdiction="US-CA"),
        term_months=24, governing_law="Delaware", dispute_resolution="arbitration",
        nda_details=NDADetails(purpose="Evaluate partnership", confidentiality_survival_years=3),
    )

def test_build_placeholders():
    from app.services.drafting.agents.draft_agent import DraftAgent
    agent = DraftAgent()
    req = _make_nda_request()
    placeholders = agent._build_placeholders(req)
    assert placeholders["party_1_name"] == "Acme Inc."
    assert placeholders["party_2_name"] == "Beta LLC"
    assert placeholders["governing_law"] == "Delaware"
    assert placeholders["term_months"] == "24"
    assert placeholders["purpose"] == "Evaluate partnership"

def test_select_tier():
    from app.services.drafting.agents.draft_agent import DraftAgent
    agent = DraftAgent()
    assert agent._select_tier("party_1", "protective") == "preferred"
    assert agent._select_tier("party_1", "balanced") == "acceptable"
    assert agent._select_tier("party_1", "commercial") == "fallback"
    assert agent._select_tier("balanced", "protective") == "acceptable"

def test_fill_placeholders():
    from app.services.drafting.agents.draft_agent import DraftAgent
    agent = DraftAgent()
    template = "Agreement between {{party_1_name}} and {{party_2_name}}"
    result = agent._fill_placeholders(template, {"party_1_name": "Acme", "party_2_name": "Beta"})
    assert result == "Agreement between Acme and Beta"

def test_should_include_clause():
    from app.services.drafting.agents.draft_agent import DraftAgent
    agent = DraftAgent()
    req = _make_nda_request()
    req.nda_details.non_solicitation = False
    assert agent._should_include({"is_required": True, "conditional_on": None}, req) is True
    assert agent._should_include({"is_required": False, "conditional_on": "nda_details.non_solicitation == true"}, req) is False
    req.nda_details.non_solicitation = True
    assert agent._should_include({"is_required": False, "conditional_on": "nda_details.non_solicitation == true"}, req) is True

@pytest.mark.asyncio
async def test_generate_draft_structure():
    from app.services.drafting.agents.draft_agent import DraftAgent
    agent = DraftAgent()
    req = _make_nda_request()
    with patch.object(agent, "_ai_adapt_clause", new_callable=AsyncMock) as mock_ai:
        mock_ai.side_effect = lambda text, guidance, jurisdiction_variant: text
        from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
        result = await agent.generate(req, NDA_MUTUAL_PLAYBOOK)
    assert isinstance(result, RawDraft)
    assert result.contract_type == "nda_mutual"
    assert result.title == "MUTUAL NON-DISCLOSURE AGREEMENT"
    assert len(result.sections) >= 14
    assert result.sections[0].clause_type == "preamble"
    assert "Acme Inc." in result.sections[0].content
    assert "Beta LLC" in result.sections[0].content
