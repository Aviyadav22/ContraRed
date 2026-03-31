import pytest
from unittest.mock import AsyncMock, patch
from app.services.drafting.models import RawDraft, DraftSection, DraftMetadata, Annotation

def _make_raw_draft() -> RawDraft:
    return RawDraft(
        contract_type="nda_mutual", title="NDA",
        sections=[
            DraftSection(number="1", heading="Preamble", content='Agreement between Acme and Beta.',
                         clause_type="preamble", tier_used="acceptable"),
            DraftSection(number="3", heading="Confidential Information",
                         content='"Confidential Information" means all info.',
                         clause_type="confidential_info_definition", tier_used="acceptable"),
            DraftSection(number="8", heading="Term",
                         content="This Agreement is effective for 24 months.",
                         clause_type="term_and_duration", tier_used="acceptable"),
        ],
        defined_terms={"Confidential Information": "all info"},
        metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=1, tokens_used=0),
    )

@pytest.mark.asyncio
async def test_risk_agent_returns_annotations():
    from app.services.drafting.agents.risk_agent import RiskAgent
    agent = RiskAgent()
    draft = _make_raw_draft()
    with patch.object(agent, "_ai_review", new_callable=AsyncMock) as mock:
        mock.return_value = [
            Annotation(section_number="3", agent="risk", severity="warning",
                       issue="CI definition too broad", reasoning="May be unenforceable")
        ]
        result = await agent.review(draft, risk_appetite="balanced")
    assert len(result) >= 1
    assert result[0].agent == "risk"

@pytest.mark.asyncio
async def test_compliance_agent_returns_annotations():
    from app.services.drafting.agents.compliance_agent import ComplianceAgent
    agent = ComplianceAgent()
    draft = _make_raw_draft()
    with patch.object(agent, "_ai_review", new_callable=AsyncMock) as mock:
        mock.return_value = [
            Annotation(section_number="3", agent="compliance", severity="info",
                       issue="Consider DPDP Act reference for Indian jurisdiction",
                       reasoning="Personal data may be in CI scope")
        ]
        result = await agent.review(draft, jurisdiction="IN")
    assert len(result) >= 1
    assert result[0].agent == "compliance"

@pytest.mark.asyncio
async def test_qa_agent_checks_defined_terms():
    from app.services.drafting.agents.qa_agent import QAAgent
    agent = QAAgent()
    draft = _make_raw_draft()
    draft.sections.append(DraftSection(
        number="5", heading="Obligations",
        content='Representatives shall protect the Derivative Materials.',
        clause_type="receiving_party_obligations", tier_used="acceptable",
    ))
    result = await agent.review(draft)
    qa_issues = [a for a in result if a.agent == "qa"]
    assert len(qa_issues) >= 1

@pytest.mark.asyncio
async def test_qa_agent_checks_section_numbering():
    from app.services.drafting.agents.qa_agent import QAAgent
    agent = QAAgent()
    draft = _make_raw_draft()
    result = await agent.review(draft)
    numbering_issues = [a for a in result if "numbering" in a.issue.lower() or "gap" in a.issue.lower()]
    assert len(numbering_issues) >= 1
