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
