"""Tests for Smriti MCP Integration — Client, Tools, Pipeline, Endpoint."""
import pytest


# ============================================================
# Client tests
# ============================================================

def test_smriti_client_import():
    """SmritiClient should import cleanly."""
    from app.services.smriti_mcp_client import SmritiClient, smriti_client
    assert SmritiClient is not None
    assert smriti_client is not None


def test_smriti_client_not_configured_by_default():
    """Without SMRITI_MCP_URL env var, client is not configured."""
    from app.services.smriti_mcp_client import SmritiClient
    client = SmritiClient(base_url="")
    assert client.is_configured is False


def test_smriti_client_configured_with_url():
    """With a URL, client is configured."""
    from app.services.smriti_mcp_client import SmritiClient
    client = SmritiClient(base_url="http://localhost:8080")
    assert client.is_configured is True


@pytest.mark.asyncio
async def test_smriti_client_graceful_fallback_no_url():
    """Client returns empty when not configured."""
    from app.services.smriti_mcp_client import SmritiClient
    client = SmritiClient(base_url="")
    cases = await client.search_case_law("test query")
    assert cases == []


@pytest.mark.asyncio
async def test_smriti_client_graceful_fallback_connection_error():
    """Client returns empty when Smriti server unreachable."""
    from app.services.smriti_mcp_client import SmritiClient
    client = SmritiClient(base_url="http://localhost:99999", timeout=0.5)
    cases = await client.search_case_law("test query")
    assert cases == []


@pytest.mark.asyncio
async def test_smriti_client_get_statute_text_fallback():
    """get_statute_text returns empty dict when not configured."""
    from app.services.smriti_mcp_client import SmritiClient
    client = SmritiClient(base_url="")
    result = await client.get_statute_text("Indian Contract Act, Section 27")
    assert result == {}


@pytest.mark.asyncio
async def test_smriti_client_check_statute_compliance_fallback():
    """check_statute_compliance returns empty dict when not configured."""
    from app.services.smriti_mcp_client import SmritiClient
    client = SmritiClient(base_url="")
    result = await client.check_statute_compliance(
        clause_text="Non-compete for 5 years",
        statute_reference="Indian Contract Act, Section 27",
    )
    assert result == {}


# ============================================================
# Tool definition tests
# ============================================================

def test_smriti_tools_import():
    """Smriti tool definitions should import cleanly."""
    from app.services.smriti_tools import ALL_TOOLS, TOOL_MAP, get_tool_schemas_for_agent
    assert ALL_TOOLS is not None
    assert TOOL_MAP is not None
    assert get_tool_schemas_for_agent is not None


def test_smriti_tools_count():
    """Should have 5 defined tools."""
    from app.services.smriti_tools import ALL_TOOLS
    assert len(ALL_TOOLS) == 5


def test_smriti_tool_names():
    """All expected tools should be present."""
    from app.services.smriti_tools import TOOL_MAP
    expected = [
        "search_case_law",
        "get_statute_text",
        "find_judicial_interpretation",
        "get_legal_principle",
        "check_statute_compliance",
    ]
    for name in expected:
        assert name in TOOL_MAP, f"Missing tool: {name}"


def test_smriti_tool_schemas_structure():
    """Tool schemas should have required fields."""
    from app.services.smriti_tools import get_tool_schemas_for_agent
    schemas = get_tool_schemas_for_agent()
    assert len(schemas) == 5
    for schema in schemas:
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
        assert "returns" in schema
        assert "type" in schema["parameters"]
        assert "properties" in schema["parameters"]
        assert "required" in schema["parameters"]


def test_search_case_law_tool_params():
    """search_case_law should have query as required param."""
    from app.services.smriti_tools import TOOL_MAP
    tool = TOOL_MAP["search_case_law"]
    param_names = [p.name for p in tool.parameters]
    assert "query" in param_names
    assert "jurisdiction" in param_names
    assert "max_results" in param_names
    # query should be required
    query_param = next(p for p in tool.parameters if p.name == "query")
    assert query_param.required is True


# ============================================================
# Pipeline integration tests
# ============================================================

def test_pipeline_final_redline_has_smriti_fields():
    """FinalRedline should have statutory_basis and case_law_context fields."""
    from app.services.analysis_pipeline import FinalRedline
    from app.services.confidence_scorer import ConfidenceScore, ConfidenceLevel, ConfidenceBreakdown
    r = FinalRedline(
        rule_name="test",
        risk_level="RED",
        original_text="test",
        verified_text="test",
        explanation="test",
        recommendation="test",
        redline_type="test",
        is_deal_breaker=False,
        confidence=ConfidenceScore(score=0.5, level=ConfidenceLevel.MEDIUM, breakdown=ConfidenceBreakdown()),
        verification_status="verified",
    )
    assert r.statutory_basis is None
    assert r.case_law_context == []


def test_pipeline_result_dict_includes_smriti_fields():
    """PipelineResult.to_dict() should include Smriti fields in redlines."""
    from app.services.analysis_pipeline import PipelineResult, FinalRedline
    from app.services.confidence_scorer import ConfidenceScore, ConfidenceLevel, ConfidenceBreakdown
    r = FinalRedline(
        rule_name="test",
        risk_level="RED",
        original_text="orig",
        verified_text="verified",
        explanation="explain",
        recommendation="rec",
        redline_type="missing_clause",
        is_deal_breaker=True,
        confidence=ConfidenceScore(score=0.9, level=ConfidenceLevel.HIGH, breakdown=ConfidenceBreakdown()),
        verification_status="verified",
        statutory_basis={"section_text": "Section 27..."},
        case_law_context=[{"citation": "Pepsi v. Gujarat", "summary": "Non-compete void"}],
    )
    result = PipelineResult(
        executive_summary=["test"],
        redlines=[r],
        hallucination_stats={},
        stage_metrics=[],
    )
    d = result.to_dict()
    redline_dict = d["redlines"][0]
    assert redline_dict["statutory_basis"] == {"section_text": "Section 27..."}
    assert len(redline_dict["case_law_context"]) == 1
    assert redline_dict["case_law_context"][0]["citation"] == "Pepsi v. Gujarat"


# ============================================================
# API endpoint tests
# ============================================================

def test_research_request_schema():
    """ResearchRequest should validate correctly."""
    from app.api.v1.endpoints.agent import ResearchRequest
    req = ResearchRequest(
        clause_text="Non-compete clause for 5 years",
        clause_type="non_compete",
        jurisdiction="IN",
    )
    assert req.clause_type == "non_compete"
    assert req.jurisdiction == "IN"


def test_research_response_schema():
    """ResearchResponse should validate correctly."""
    from app.api.v1.endpoints.agent import ResearchResponse
    resp = ResearchResponse(
        smriti_available=False,
        case_law=[],
    )
    assert resp.smriti_available is False
    assert resp.statutory_basis is None


def test_case_law_item_schema():
    """CaseLawItem should validate correctly."""
    from app.api.v1.endpoints.agent import CaseLawItem
    item = CaseLawItem(
        citation="Pepsi Foods v. Bharat",
        court="Supreme Court of India",
        date="2000",
        summary="Non-compete held void",
        relevance_score=0.95,
    )
    assert item.citation == "Pepsi Foods v. Bharat"


def test_tools_endpoint_schema():
    """GET /agent/tools should return tool schemas."""
    from app.services.smriti_tools import get_tool_schemas_for_agent
    schemas = get_tool_schemas_for_agent()
    assert isinstance(schemas, list)
    assert len(schemas) == 5


@pytest.mark.asyncio
async def test_research_endpoint_requires_auth(client):
    """POST /agent/research should require auth."""
    resp = await client.post("/api/v1/agent/research", json={
        "clause_text": "Non-compete for 5 years",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_tools_endpoint_requires_auth(client):
    """GET /agent/tools should require auth."""
    resp = await client.get("/api/v1/agent/tools")
    assert resp.status_code == 401
