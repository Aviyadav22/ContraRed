import pytest
from app.services.drafting.models import DraftRequest


@pytest.mark.asyncio
async def test_validate_nda_request():
    from app.services.drafting.agents.intake_agent import IntakeAgent
    agent = IntakeAgent()
    raw = {
        "contract_type": "nda_mutual",
        "drafting_perspective": "balanced",
        "risk_appetite": "balanced",
        "jurisdiction": "US-DE",
        "party_1": {"name": "Acme Inc.", "entity_type": "Inc.", "jurisdiction": "US-DE"},
        "party_2": {"name": "Beta LLC", "entity_type": "LLC", "jurisdiction": "US-CA"},
        "term_months": 24,
        "governing_law": "Delaware",
        "nda_details": {"purpose": "Evaluate partnership"},
    }
    result = await agent.process(raw)
    assert isinstance(result, DraftRequest)
    assert result.contract_type == "nda_mutual"
    assert result.dispute_resolution == "arbitration"


@pytest.mark.asyncio
async def test_infer_defaults_governing_law():
    from app.services.drafting.agents.intake_agent import IntakeAgent
    agent = IntakeAgent()
    raw = {
        "contract_type": "nda_mutual",
        "drafting_perspective": "party_1",
        "risk_appetite": "protective",
        "jurisdiction": "US-CA",
        "party_1": {"name": "Acme Inc.", "entity_type": "Inc.", "jurisdiction": "US-CA"},
        "party_2": {"name": "Beta LLC", "entity_type": "LLC", "jurisdiction": "US-NY"},
        "nda_details": {"purpose": "Tech evaluation"},
    }
    result = await agent.process(raw)
    assert result.governing_law == "California"


@pytest.mark.asyncio
async def test_infer_short_names():
    from app.services.drafting.agents.intake_agent import IntakeAgent
    agent = IntakeAgent()
    raw = {
        "contract_type": "nda_mutual",
        "drafting_perspective": "balanced",
        "risk_appetite": "balanced",
        "jurisdiction": "US-DE",
        "party_1": {"name": "Acme Corporation Inc.", "entity_type": "Inc.", "jurisdiction": "US-DE"},
        "party_2": {"name": "Beta Technologies LLC", "entity_type": "LLC", "jurisdiction": "US-CA"},
        "nda_details": {"purpose": "Evaluate partnership"},
    }
    result = await agent.process(raw)
    assert result.party_1.name == "Acme Corporation Inc."


@pytest.mark.asyncio
async def test_select_playbook_nda():
    from app.services.drafting.agents.intake_agent import IntakeAgent
    agent = IntakeAgent()
    playbook = agent.select_playbook("nda_mutual", "US-DE")
    assert playbook["contract_type"] == "nda_mutual"


@pytest.mark.asyncio
async def test_select_playbook_saas():
    from app.services.drafting.agents.intake_agent import IntakeAgent
    agent = IntakeAgent()
    playbook = agent.select_playbook("saas", "US-DE")
    assert playbook["contract_type"] == "saas"


@pytest.mark.asyncio
async def test_reject_invalid_contract_type():
    from app.services.drafting.agents.intake_agent import IntakeAgent
    agent = IntakeAgent()
    raw = {
        "contract_type": "invalid_type",
        "drafting_perspective": "balanced",
        "risk_appetite": "balanced",
        "jurisdiction": "US-DE",
        "party_1": {"name": "A", "entity_type": "Inc.", "jurisdiction": "US-DE"},
        "party_2": {"name": "B", "entity_type": "LLC", "jurisdiction": "US-CA"},
    }
    with pytest.raises(ValueError, match="contract_type"):
        await agent.process(raw)


@pytest.mark.asyncio
async def test_saas_requires_saas_details():
    from app.services.drafting.agents.intake_agent import IntakeAgent
    agent = IntakeAgent()
    raw = {
        "contract_type": "saas",
        "drafting_perspective": "party_1",
        "risk_appetite": "protective",
        "jurisdiction": "US-DE",
        "party_1": {"name": "Provider Inc.", "entity_type": "Inc.", "jurisdiction": "US-DE"},
        "party_2": {"name": "Customer LLC", "entity_type": "LLC", "jurisdiction": "US-CA"},
    }
    with pytest.raises(ValueError, match="saas_details"):
        await agent.process(raw)
