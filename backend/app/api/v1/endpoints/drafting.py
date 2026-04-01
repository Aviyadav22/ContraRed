"""
Contract Drafting API endpoints.

Provides intake schema, contract generation, download (DOCX),
add-in payload (JSON), and playbook listing.
"""

from __future__ import annotations

import io
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.drafting.orchestrator import drafting_orchestrator
from app.services.drafting.renderer.docx_renderer import render_docx
from app.services.drafting.renderer.addin_renderer import render_addin_payload
from app.services.drafting.agents.intake_agent import (
    PLAYBOOK_REGISTRY,
    VALID_CONTRACT_TYPES,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Auth dependency — gracefully degrade in test environments
# ---------------------------------------------------------------------------

from app.api.v1.endpoints.auth import get_current_user

# ---------------------------------------------------------------------------
# In-memory draft store (replace with DB persistence when ready)
# ---------------------------------------------------------------------------

import re as _re
import time as _time

_draft_store: Dict[str, Any] = {}
_draft_timestamps: Dict[str, float] = {}
_DRAFT_TTL_SECONDS = 3600  # 1 hour
_DRAFT_MAX_ENTRIES = 200


def _store_draft(draft_id: str, result: Any) -> None:
    """Store a draft with TTL tracking and size limits."""
    _cleanup_drafts()
    _draft_store[draft_id] = result
    _draft_timestamps[draft_id] = _time.time()


def _cleanup_drafts() -> None:
    """Remove expired drafts and enforce max entries."""
    now = _time.time()
    expired = [k for k, ts in _draft_timestamps.items() if now - ts > _DRAFT_TTL_SECONDS]
    for k in expired:
        _draft_store.pop(k, None)
        _draft_timestamps.pop(k, None)
    # If still over limit, remove oldest
    while len(_draft_store) > _DRAFT_MAX_ENTRIES:
        oldest = min(_draft_timestamps, key=_draft_timestamps.get)
        _draft_store.pop(oldest, None)
        _draft_timestamps.pop(oldest, None)

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class PartyInput(BaseModel):
    name: str
    entity_type: str
    jurisdiction: str
    address: str = ""


class NDADetailsInput(BaseModel):
    purpose: str = "General business discussions"
    confidentiality_survival_years: int = 3
    ci_categories: List[str] = Field(default_factory=list)
    non_solicitation: bool = False
    non_solicitation_months: Optional[int] = None
    marking_requirement: bool = False


class SaaSDetailsInput(BaseModel):
    service_description: str
    pricing_model: str
    price_amount: float
    billing_frequency: str
    auto_renewal: bool = True
    uptime_commitment: Optional[float] = None
    liability_cap_months: Optional[int] = None
    authorized_users: Optional[int] = None
    compliance_frameworks: List[str] = Field(default_factory=list)
    data_regions: Optional[List[str]] = None
    support_tiers: Optional[Dict[str, str]] = None


class GenerateRequest(BaseModel):
    contract_type: str
    perspective: str = "balanced"
    risk_appetite: str = "balanced"
    jurisdiction: str = "US-DE"
    party_1: PartyInput
    party_2: PartyInput
    term: int = 12
    governing_law: str = "Delaware"
    nda_details: Optional[NDADetailsInput] = None
    saas_details: Optional[SaaSDetailsInput] = None
    dispute_resolution: str = "arbitration"
    risk_profile: Dict[str, str] = Field(default_factory=dict)
    negotiation_context: str = ""
    # Employment-specific
    employee_title: str = ""
    base_salary: str = ""
    reporting_manager: str = ""
    work_location: str = "Hybrid"


class GenerateResponse(BaseModel):
    draft_id: str
    title: str
    overall_score: float
    risk_alignment: float
    compliance_score: float
    qa_score: float
    section_count: int
    annotations: int


class PlaybookInfo(BaseModel):
    name: str
    contract_type: str
    jurisdiction: str
    clause_count: int


# ---------------------------------------------------------------------------
# Intake-schema field definitions
# ---------------------------------------------------------------------------

_BASICS_FIELDS = [
    {"name": "contract_type", "type": "select", "required": True, "default": "nda_mutual",
     "options": ["nda_mutual", "nda_unilateral", "saas", "msa", "employment"], "placeholder": "Select contract type"},
    {"name": "perspective", "type": "select", "required": True, "default": "balanced",
     "options": ["party_1", "balanced", "party_2"], "placeholder": "Drafting perspective"},
    {"name": "risk_appetite", "type": "select", "required": True, "default": "balanced",
     "options": ["protective", "balanced", "aggressive"], "placeholder": "Risk appetite"},
    {"name": "jurisdiction", "type": "select", "required": True, "default": "US-DE",
     "options": ["US-DE", "US-CA", "US-NY", "US-TX", "IN", "GB", "SG"],
     "placeholder": "Jurisdiction"},
]

_PARTIES_FIELDS = [
    {"name": "party_1_name", "type": "text", "required": True, "placeholder": "Your company name"},
    {"name": "party_1_entity_type", "type": "text", "required": True, "placeholder": "Inc., LLC, etc."},
    {"name": "party_1_jurisdiction", "type": "text", "required": True, "placeholder": "e.g. US-DE"},
    {"name": "party_2_name", "type": "text", "required": True, "placeholder": "Counter-party name"},
    {"name": "party_2_entity_type", "type": "text", "required": True, "placeholder": "Inc., LLC, etc."},
    {"name": "party_2_jurisdiction", "type": "text", "required": True, "placeholder": "e.g. US-CA"},
]

_NDA_FIELDS = [
    {"name": "purpose", "type": "textarea", "required": True, "placeholder": "Purpose of NDA",
     "show_when": {"contract_type": ["nda_mutual", "nda_unilateral"]}},
    {"name": "confidentiality_survival_years", "type": "number", "required": False, "default": 3,
     "show_when": {"contract_type": ["nda_mutual", "nda_unilateral"]}},
    {"name": "non_solicitation", "type": "checkbox", "required": False, "default": False,
     "show_when": {"contract_type": ["nda_mutual", "nda_unilateral"]}},
]

_SAAS_FIELDS = [
    {"name": "service_description", "type": "textarea", "required": True,
     "placeholder": "Describe the SaaS service",
     "show_when": {"contract_type": ["saas"]}},
    {"name": "pricing_model", "type": "select", "required": True,
     "options": ["per_user_monthly", "flat_monthly", "usage_based", "tiered"],
     "show_when": {"contract_type": ["saas"]}},
    {"name": "price_amount", "type": "number", "required": True,
     "placeholder": "Price per unit/month",
     "show_when": {"contract_type": ["saas"]}},
    {"name": "billing_frequency", "type": "select", "required": True, "default": "monthly",
     "options": ["monthly", "quarterly", "annual"],
     "show_when": {"contract_type": ["saas"]}},
    {"name": "uptime_commitment", "type": "number", "required": False, "default": 99.9,
     "placeholder": "e.g. 99.9",
     "show_when": {"contract_type": ["saas"]}},
]

_EMPLOYMENT_FIELDS = [
    {"name": "employee_title", "type": "text", "required": True, "placeholder": "e.g. VP of Engineering",
     "show_when": {"contract_type": ["employment"]}},
    {"name": "base_salary", "type": "text", "required": True, "placeholder": "e.g. $250,000",
     "show_when": {"contract_type": ["employment"]}},
    {"name": "reporting_manager", "type": "text", "required": False, "placeholder": "e.g. CTO",
     "show_when": {"contract_type": ["employment"]}},
    {"name": "work_location", "type": "text", "required": False, "default": "Hybrid", "placeholder": "Office/Remote/Hybrid",
     "show_when": {"contract_type": ["employment"]}},
]

_LEGAL_FIELDS = [
    {"name": "term", "type": "number", "required": True, "default": 12, "placeholder": "Term in months"},
    {"name": "governing_law", "type": "text", "required": True, "default": "Delaware",
     "placeholder": "Governing law state/country"},
]


def _build_schema(contract_type: str) -> dict:
    """Return stage-based intake schema filtered for *contract_type*."""
    stages = [
        {"stage": "basics", "label": "Contract Basics", "fields": _BASICS_FIELDS},
        {"stage": "parties", "label": "Parties", "fields": _PARTIES_FIELDS},
    ]
    if contract_type in ("nda_mutual", "nda_unilateral"):
        stages.append({"stage": "nda_details", "label": "NDA Details", "fields": _NDA_FIELDS})
    if contract_type == "saas":
        stages.append({"stage": "saas_details", "label": "SaaS Details", "fields": _SAAS_FIELDS})
    if contract_type == "employment":
        stages.append({"stage": "employment_details", "label": "Employment Details", "fields": _EMPLOYMENT_FIELDS})
    stages.append({"stage": "legal", "label": "Legal Terms", "fields": _LEGAL_FIELDS})
    return {"contract_type": contract_type, "stages": stages}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/intake-schema")
async def get_intake_schema(contract_type: str = Query("nda_mutual")):
    """Return the dynamic intake form schema for *contract_type*."""
    if contract_type not in VALID_CONTRACT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported contract_type '{contract_type}'. "
                   f"Valid: {sorted(VALID_CONTRACT_TYPES)}",
        )
    return _build_schema(contract_type)


@router.post("/generate", response_model=GenerateResponse)
async def generate_draft(req: GenerateRequest, current_user = Depends(get_current_user)):
    """Generate a contract draft using the multi-agent pipeline."""
    # Build the raw input dict expected by the orchestrator
    raw_input: Dict[str, Any] = {
        "contract_type": req.contract_type,
        "drafting_perspective": req.perspective,
        "risk_appetite": req.risk_appetite,
        "jurisdiction": req.jurisdiction,
        "party_1": req.party_1.model_dump(),
        "party_2": req.party_2.model_dump(),
        "term_months": req.term,
        "governing_law": req.governing_law,
    }
    raw_input["dispute_resolution"] = req.dispute_resolution
    if req.nda_details:
        raw_input["nda_details"] = req.nda_details.model_dump()
    if req.saas_details:
        raw_input["saas_details"] = req.saas_details.model_dump()
    if req.risk_profile:
        raw_input["risk_profile"] = req.risk_profile
    if req.negotiation_context:
        raw_input["negotiation_context"] = req.negotiation_context
    # Employment-specific passthrough
    if req.employee_title:
        raw_input["employee_title"] = req.employee_title
    if req.base_salary:
        raw_input["base_salary"] = req.base_salary
    if req.reporting_manager:
        raw_input["reporting_manager"] = req.reporting_manager
    if req.work_location and req.work_location != "Hybrid":
        raw_input["work_location"] = req.work_location

    try:
        result = await drafting_orchestrator.run(raw_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Draft generation failed")
        raise HTTPException(status_code=500, detail="Internal error during draft generation")

    draft_id = str(uuid.uuid4())
    _store_draft(draft_id, result)

    qr = result.quality_report
    return GenerateResponse(
        draft_id=draft_id,
        title=result.draft.title,
        overall_score=qr.overall_score,
        risk_alignment=qr.risk_alignment,
        compliance_score=qr.compliance_score,
        qa_score=qr.qa_score,
        section_count=len(result.draft.sections),
        annotations=len(qr.open_annotations),
    )


@router.get("/download/{draft_id}")
async def download_draft(draft_id: str, current_user = Depends(get_current_user)):
    """Download the generated contract as a .docx file."""
    result = _draft_store.get(draft_id)
    if not result:
        raise HTTPException(status_code=404, detail="Draft not found")

    docx_bytes = render_docx(result)
    safe_type = _re.sub(r'[^\w\-.]', '_', result.draft.contract_type)
    safe_id = _re.sub(r'[^\w\-]', '', draft_id[:8])
    filename = f"{safe_type}_{safe_id}.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/addin-payload/{draft_id}")
async def get_addin_payload(draft_id: str, current_user = Depends(get_current_user)):
    """Return the draft as a JSON payload for the Word add-in."""
    result = _draft_store.get(draft_id)
    if not result:
        raise HTTPException(status_code=404, detail="Draft not found")

    return render_addin_payload(result, draft_id=draft_id)


@router.get("/playbooks", response_model=List[PlaybookInfo])
async def list_playbooks(current_user = Depends(get_current_user)):
    """List available drafting playbooks."""
    items: List[PlaybookInfo] = []
    for ct, pb in PLAYBOOK_REGISTRY.items():
        items.append(PlaybookInfo(
            name=pb.get("name") or pb.get("display_name", ct),
            contract_type=ct,
            jurisdiction=pb.get("jurisdiction", "Any"),
            clause_count=len(pb.get("clauses", [])),
        ))
    return items
