from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PartyInfo(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    entity_type: str
    jurisdiction: str
    address: str = ""


class NDADetails(BaseModel):
    purpose: str
    confidentiality_survival_years: int = 3
    ci_categories: list[str] = Field(default_factory=list)
    non_solicitation: bool = False
    non_solicitation_months: Optional[int] = None
    marking_requirement: bool = False


class SaaSDetails(BaseModel):
    service_description: str
    pricing_model: str
    price_amount: float = Field(..., gt=0)
    billing_frequency: str
    auto_renewal: bool = True
    uptime_commitment: Optional[float] = Field(default=None, ge=95, le=100)
    liability_cap_months: Optional[int] = None
    authorized_users: Optional[int] = None
    compliance_frameworks: list[str] = Field(default_factory=list)
    data_regions: Optional[list[str]] = None
    support_tiers: Optional[dict[str, str]] = None


class DraftRequest(BaseModel):
    contract_type: str
    drafting_perspective: str
    risk_appetite: str
    jurisdiction: str
    party_1: PartyInfo
    party_2: PartyInfo
    effective_date: Optional[date] = None
    term_months: int = 12
    governing_law: str
    dispute_resolution: str = "arbitration"
    venue: Optional[str] = None
    nda_details: Optional[NDADetails] = None
    saas_details: Optional[SaaSDetails] = None
    risk_profile: dict[str, str] = Field(default_factory=dict)
    negotiation_context: str = ""


class DraftSection(BaseModel):
    number: str
    heading: str
    content: str
    clause_type: str
    tier_used: str
    notes: Optional[str] = None


class DraftMetadata(BaseModel):
    playbook_id: str
    model: str
    generation_seconds: float
    tokens_used: int


class RawDraft(BaseModel):
    contract_type: str
    title: str
    sections: list[DraftSection]
    defined_terms: dict[str, str]
    metadata: DraftMetadata


class Annotation(BaseModel):
    section_number: str
    agent: str
    severity: str
    issue: str
    suggested_fix: Optional[str] = None
    reasoning: str = ""


class QualityReport(BaseModel):
    overall_score: float = Field(..., ge=0, le=100)
    risk_alignment: float = Field(..., ge=0, le=100)
    compliance_score: float = Field(..., ge=0, le=100)
    qa_score: float = Field(..., ge=0, le=100)
    annotations_applied: int = 0
    conflicts_flagged: int = 0
    open_annotations: list[Annotation] = Field(default_factory=list)


class FinalDraft(BaseModel):
    draft: RawDraft
    quality_report: QualityReport
