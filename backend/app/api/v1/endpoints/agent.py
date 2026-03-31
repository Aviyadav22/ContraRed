"""
Agent API endpoints.

Provides a high-level AI agent interface for contract review.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.review_agent import ReviewAgent
from app.services.smriti_mcp_client import smriti_client
from app.services.smriti_tools import get_tool_schemas_for_agent
from app.services.compliance_watch import ComplianceWatchAgent
from app.services.renewal_agent import RenewalAgent

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AgentReviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500000)
    instructions: Optional[str] = Field(None, max_length=2000, description="Natural language review instructions")
    playbook_id: Optional[str] = None
    compliance_layers: Optional[List[str]] = None
    jurisdiction: Optional[str] = None


class AgentFinding(BaseModel):
    id: str
    risk_level: str
    clause_type: str
    rule_name: str
    explanation: str
    fix: Optional[str] = None
    priority: int


class AgentReviewResponse(BaseModel):
    jurisdiction: Optional[str] = None
    contract_type: Optional[str] = None
    total_findings: int
    deal_breakers: List[AgentFinding]
    high_risk: List[AgentFinding]
    medium_risk: List[AgentFinding]
    low_risk: List[AgentFinding]
    compliance_scores: dict = {}
    summary: str
    partial: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/review", response_model=AgentReviewResponse)
async def agent_review(
    body: AgentReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a full AI-powered contract review.

    The agent orchestrates: jurisdiction detection → playbook selection →
    compliance layers → analysis → prioritization → fix generation.
    """
    agent = ReviewAgent(db)

    try:
        result = await agent.review(
            text=body.text,
            instructions=body.instructions,
            playbook_id=body.playbook_id,
            compliance_layers=body.compliance_layers,
            jurisdiction=body.jurisdiction,
        )
    except Exception as e:
        logger.error("Agent review failed: %s", e)
        raise HTTPException(status_code=500, detail="Agent review failed")

    return AgentReviewResponse(**result.to_dict())


# ---------------------------------------------------------------------------
# Research endpoint (Smriti MCP deep research)
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    clause_text: str = Field(..., min_length=1, max_length=10000)
    clause_type: Optional[str] = None
    jurisdiction: Optional[str] = None


class CaseLawItem(BaseModel):
    citation: str = ""
    court: str = ""
    date: str = ""
    summary: str = ""
    relevance_score: float = 0.0


class ResearchResponse(BaseModel):
    statutory_basis: Optional[dict] = None
    case_law: List[CaseLawItem] = []
    legal_principle: Optional[dict] = None
    smriti_available: bool = False


@router.post("/research", response_model=ResearchResponse)
async def agent_research(
    body: ResearchRequest,
    current_user: User = Depends(get_current_user),
):
    """Deep research on a specific clause using Smriti MCP.

    Returns statutory basis, relevant case law, and legal principles.
    """
    if not smriti_client.is_configured:
        return ResearchResponse(smriti_available=False)

    result = ResearchResponse(smriti_available=True)

    try:
        # Search for case law
        cases = await smriti_client.search_case_law(
            query=body.clause_text[:500],
            jurisdiction=body.jurisdiction,
            max_results=3,
        )
        result.case_law = [CaseLawItem(**c) for c in cases]

        # Get judicial interpretation if clause type known
        if body.clause_type:
            interpretations = await smriti_client.find_judicial_interpretation(
                clause_type=body.clause_type,
                jurisdiction=body.jurisdiction,
                max_results=2,
            )
            if interpretations:
                result.legal_principle = {
                    "clause_type": body.clause_type,
                    "interpretations": interpretations,
                }

    except Exception as e:
        logger.warning("Smriti research failed: %s", e)

    return result


@router.get("/tools", response_model=List[dict])
async def list_agent_tools(
    current_user: User = Depends(get_current_user),
):
    """List available agent tools and their schemas."""
    return get_tool_schemas_for_agent()


# ---------------------------------------------------------------------------
# Compliance Watch endpoint
# ---------------------------------------------------------------------------

class ComplianceWatchRequest(BaseModel):
    compliance_layer_code: str = Field(..., min_length=1, max_length=50)
    org_id: Optional[str] = None


class ComplianceDeltaItem(BaseModel):
    clause_type: str
    old_risk_level: Optional[str] = None
    new_risk_level: str
    change: str
    explanation: str = ""


class DocumentDeltaItem(BaseModel):
    document_id: str
    document_name: str
    old_score: Optional[dict] = None
    new_score: Optional[dict] = None
    deltas: List[ComplianceDeltaItem] = []
    newly_non_compliant: bool = False


class ComplianceWatchResponse(BaseModel):
    compliance_layer_code: str
    triggered_at: str = ""
    total_documents_scanned: int = 0
    newly_non_compliant_count: int = 0
    document_deltas: List[DocumentDeltaItem] = []
    summary: str = ""


@router.post("/compliance-watch/trigger", response_model=ComplianceWatchResponse)
async def trigger_compliance_watch(
    body: ComplianceWatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger a compliance re-scan for a specific compliance layer.

    Finds affected documents and produces a delta report showing
    newly non-compliant contracts.
    """
    from uuid import UUID as _UUID

    org_id = None
    if body.org_id:
        org_id = _UUID(body.org_id)
    elif current_user.organization_id:
        org_id = current_user.organization_id

    if not org_id:
        raise HTTPException(status_code=400, detail="Organization ID required")

    agent = ComplianceWatchAgent(db)

    try:
        report = await agent.trigger_rescan(
            compliance_layer_code=body.compliance_layer_code,
            org_id=org_id,
        )
    except Exception as e:
        logger.error("Compliance watch failed: %s", e)
        raise HTTPException(status_code=500, detail="Compliance watch scan failed")

    return ComplianceWatchResponse(**report.to_dict())


# ---------------------------------------------------------------------------
# Renewal Intelligence endpoint
# ---------------------------------------------------------------------------

class RenewalBriefItem(BaseModel):
    document_id: str
    document_name: str
    expiry_date: Optional[str] = None
    days_until_expiry: Optional[int] = None
    risk_summary: dict = {}
    top_risks: List[dict] = []
    recommendations: List[str] = []


class RenewalResponse(BaseModel):
    org_id: str
    days_ahead: int
    generated_at: str = ""
    total_expiring: int = 0
    briefs: List[RenewalBriefItem] = []
    summary: str = ""


@router.get("/renewals", response_model=RenewalResponse)
async def get_renewals(
    days_ahead: int = 90,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contracts approaching expiry with renewal briefs.

    Returns expiring contracts with risk summaries and recommendations.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")

    agent = RenewalAgent(db)

    try:
        report = await agent.scan_expiring_contracts(
            org_id=org_id,
            days_ahead=days_ahead,
        )
    except Exception as e:
        logger.error("Renewal scan failed: %s", e)
        raise HTTPException(status_code=500, detail="Renewal scan failed")

    return RenewalResponse(**report.to_dict())
