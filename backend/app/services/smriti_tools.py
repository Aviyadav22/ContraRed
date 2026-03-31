"""
Smriti MCP Tool Definitions.

Typed tool schemas for Smriti legal research capabilities.
Used by agents and the enrichment pipeline to understand
what Smriti can provide.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolParameter:
    """A single parameter for an MCP tool."""
    name: str
    type: str  # "string", "integer", "boolean"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """Schema for a Smriti MCP tool."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = ""


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

SEARCH_CASE_LAW = ToolDefinition(
    name="search_case_law",
    description="Search for relevant case law based on a legal query. Returns cases with citations, summaries, and relevance scores.",
    parameters=[
        ToolParameter(name="query", type="string", description="Legal query or clause text to search for"),
        ToolParameter(name="jurisdiction", type="string", description="Jurisdiction code (e.g. IN, US, GB)", required=False),
        ToolParameter(name="max_results", type="integer", description="Maximum number of cases to return", required=False, default=3),
    ],
    returns="List of cases: [{citation, court, date, summary, relevance_score, url}]",
)

GET_STATUTE_TEXT = ToolDefinition(
    name="get_statute_text",
    description="Retrieve the full text of a specific statute section. Useful for verifying statutory references in contract clauses.",
    parameters=[
        ToolParameter(name="statute_reference", type="string", description="Statute reference (e.g. 'Indian Contract Act, Section 27')"),
        ToolParameter(name="jurisdiction", type="string", description="Jurisdiction code", required=False),
    ],
    returns="Dict: {section_text, statute_name, section_number, last_amended, url}",
)

FIND_JUDICIAL_INTERPRETATION = ToolDefinition(
    name="find_judicial_interpretation",
    description="Find how courts have interpreted a specific type of contract clause. Returns judicial opinions and established principles.",
    parameters=[
        ToolParameter(name="clause_type", type="string", description="Clause type (e.g. 'non_compete', 'limitation_of_liability')"),
        ToolParameter(name="jurisdiction", type="string", description="Jurisdiction code", required=False),
        ToolParameter(name="max_results", type="integer", description="Maximum interpretations", required=False, default=2),
    ],
    returns="List of interpretations: [{case_citation, principle, court, relevance}]",
)

GET_LEGAL_PRINCIPLE = ToolDefinition(
    name="get_legal_principle",
    description="Get a legal principle with supporting case law. Useful for understanding the legal basis behind a risk assessment.",
    parameters=[
        ToolParameter(name="principle_name", type="string", description="Name of the legal principle (e.g. 'restraint of trade', 'uberrimae fidei')"),
        ToolParameter(name="jurisdiction", type="string", description="Jurisdiction code", required=False),
    ],
    returns="Dict: {principle, description, supporting_cases: [{citation, summary}], statutes: [{reference, text}]}",
)

CHECK_STATUTE_COMPLIANCE = ToolDefinition(
    name="check_statute_compliance",
    description="Check if a contract clause complies with a specific statute. Returns compliance assessment with issues and recommendations.",
    parameters=[
        ToolParameter(name="clause_text", type="string", description="The clause text to check"),
        ToolParameter(name="statute_reference", type="string", description="Statute reference to check against"),
        ToolParameter(name="jurisdiction", type="string", description="Jurisdiction code", required=False),
    ],
    returns="Dict: {compliant: bool, issues: [str], recommendations: [str], confidence: float}",
)

# All available tools
ALL_TOOLS: List[ToolDefinition] = [
    SEARCH_CASE_LAW,
    GET_STATUTE_TEXT,
    FIND_JUDICIAL_INTERPRETATION,
    GET_LEGAL_PRINCIPLE,
    CHECK_STATUTE_COMPLIANCE,
]

TOOL_MAP: Dict[str, ToolDefinition] = {t.name: t for t in ALL_TOOLS}


def get_tool_schemas_for_agent() -> List[Dict[str, Any]]:
    """Return tool schemas in a format suitable for agent consumption."""
    schemas = []
    for tool in ALL_TOOLS:
        params = {}
        required = []
        for p in tool.parameters:
            params[p.name] = {
                "type": p.type,
                "description": p.description,
            }
            if p.default is not None:
                params[p.name]["default"] = p.default
            if p.required:
                required.append(p.name)

        schemas.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": params,
                "required": required,
            },
            "returns": tool.returns,
        })
    return schemas
