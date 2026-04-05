"""
DPDP Compliance Command Center — Data Models.

Pydantic models for compliance assessments, gap analysis,
remediation outputs, and portfolio scoring.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


# ---- Enums ----

class ComplianceStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


class DPDPSection(str, enum.Enum):
    SEC_4 = "section_4"   # Grounds for processing
    SEC_5 = "section_5"   # Notice
    SEC_6 = "section_6"   # Consent
    SEC_7 = "section_7"   # Legitimate uses
    SEC_8 = "section_8"   # Fiduciary obligations
    SEC_9 = "section_9"   # Children's data + consent manager
    SEC_10 = "section_10"  # Significant data fiduciary
    SEC_11 = "section_11"  # Right to information
    SEC_12 = "section_12"  # Right to correction/erasure
    SEC_13 = "section_13"  # Grievance redressal
    SEC_14 = "section_14"  # Nomination
    SEC_15 = "section_15"  # Data principal duties
    SEC_16 = "section_16"  # Cross-border transfer
    SEC_17 = "section_17"  # Exemptions


class RemediationType(str, enum.Enum):
    CONTRACT_CLAUSE = "contract_clause"
    DPA_TEMPLATE = "dpa_template"
    PRIVACY_NOTICE = "privacy_notice"
    CONSENT_FORM = "consent_form"
    BREACH_TEMPLATE = "breach_notification_template"
    POLICY_UPDATE = "policy_update"
    PROCESS_RECOMMENDATION = "process_recommendation"


class AssessmentCategory(str, enum.Enum):
    CONSENT_GOVERNANCE = "consent_governance"
    DATA_PRINCIPAL_RIGHTS = "data_principal_rights"
    FIDUCIARY_OBLIGATIONS = "fiduciary_obligations"
    BREACH_READINESS = "breach_readiness"
    CROSS_BORDER = "cross_border"
    VENDOR_MANAGEMENT = "vendor_management"
    CHILDREN_DATA = "children_data"
    SIGNIFICANT_FIDUCIARY = "significant_fiduciary"
    DATA_RETENTION = "data_retention"
    PURPOSE_LIMITATION = "purpose_limitation"


# ---- Scanner Agent Models ----

class ContractScanRequest(BaseModel):
    """Request to scan a single contract for DPDP compliance."""
    contract_text: str = Field(..., min_length=50)
    contract_type: str = "general"
    contract_name: str = ""
    parties: list[str] = Field(default_factory=list)
    jurisdiction: str = "IN"


class BulkScanRequest(BaseModel):
    """Request to scan multiple contracts in bulk."""
    contracts: list[ContractScanRequest] = Field(..., min_length=1, max_length=100)
    organization_id: Optional[str] = None
    generate_portfolio_report: bool = True


class ContractFinding(BaseModel):
    """A single DPDP compliance finding in a contract."""
    rule_id: str
    section: DPDPSection
    risk_level: str  # RED, YELLOW, GREEN
    is_deal_breaker: bool = False
    title: str
    description: str
    clause_text: str = ""
    suggested_fix: str = ""
    confidence: float = Field(0.0, ge=0, le=1)


class ContractScanResult(BaseModel):
    """Results of scanning a single contract."""
    contract_name: str
    contract_type: str
    total_findings: int = 0
    red_findings: int = 0
    yellow_findings: int = 0
    green_findings: int = 0
    deal_breakers: int = 0
    compliance_score: float = Field(0.0, ge=0, le=100)
    findings: list[ContractFinding] = Field(default_factory=list)
    scanned_at: datetime = Field(default_factory=lambda: datetime.now())


class PortfolioReport(BaseModel):
    """Aggregate compliance view across all scanned contracts."""
    total_contracts: int = 0
    average_compliance_score: float = 0.0
    contracts_with_deal_breakers: int = 0
    risk_heatmap: dict[str, int] = Field(default_factory=dict)
    section_coverage: dict[str, ComplianceStatus] = Field(default_factory=dict)
    top_risks: list[str] = Field(default_factory=list)
    contract_results: list[ContractScanResult] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now())


# ---- Gap Assessor Models ----

class AssessmentQuestion(BaseModel):
    """A single compliance assessment question."""
    id: str
    category: AssessmentCategory
    section: DPDPSection
    question: str
    guidance: str = ""
    weight: float = 1.0
    is_critical: bool = False


class AssessmentAnswer(BaseModel):
    """User's answer to an assessment question."""
    question_id: str
    answer: str  # yes, no, partial, not_applicable
    evidence: str = ""
    notes: str = ""


class AssessmentRequest(BaseModel):
    """Request for a gap assessment."""
    organization_name: str
    industry: str = ""
    employee_count: int = 0
    processes_children_data: bool = False
    is_significant_fiduciary: bool = False
    has_cross_border_transfers: bool = False
    answers: list[AssessmentAnswer] = Field(default_factory=list)
    uploaded_documents: list[str] = Field(default_factory=list)


class SectionScore(BaseModel):
    """Compliance score for a single DPDP section."""
    section: DPDPSection
    section_name: str
    status: ComplianceStatus
    score: float = Field(0.0, ge=0, le=100)
    findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    priority: str = "medium"  # critical, high, medium, low


class GapAssessmentResult(BaseModel):
    """Complete gap assessment results."""
    organization_name: str
    overall_score: float = Field(0.0, ge=0, le=100)
    overall_status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    section_scores: list[SectionScore] = Field(default_factory=list)
    critical_gaps: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    estimated_remediation_effort: str = ""
    deadline_risk: str = ""  # How far from May 2027 enforcement
    assessed_at: datetime = Field(default_factory=lambda: datetime.now())


# ---- Remediation Agent Models ----

class RemediationRequest(BaseModel):
    """Request for AI-generated remediation content."""
    remediation_type: RemediationType
    context: dict = Field(default_factory=dict)
    jurisdiction: str = "IN"
    language: str = "en"  # en or hi
    party_1_name: str = ""
    party_2_name: str = ""
    industry: str = ""
    gaps_to_address: list[str] = Field(default_factory=list)


class RemediationOutput(BaseModel):
    """AI-generated remediation content."""
    remediation_type: RemediationType
    title: str
    content: str
    language: str = "en"
    sections: list[dict] = Field(default_factory=list)
    applicable_dpdp_sections: list[DPDPSection] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now())


# ---- Monitor Agent Models ----

class ComplianceDeadline(BaseModel):
    """A compliance deadline to track."""
    title: str
    description: str
    deadline: date
    section: Optional[DPDPSection] = None
    status: str = "upcoming"  # upcoming, due_soon, overdue, completed
    days_remaining: int = 0


class ComplianceAlert(BaseModel):
    """A compliance alert/notification."""
    alert_type: str  # deadline, regulatory_update, drift, contract_expiry
    severity: str  # critical, warning, info
    title: str
    description: str
    action_required: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class ComplianceDashboard(BaseModel):
    """Real-time compliance posture dashboard data."""
    overall_score: float = 0.0
    status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    contracts_scanned: int = 0
    active_findings: int = 0
    resolved_findings: int = 0
    pending_rights_requests: int = 0
    pending_grievances: int = 0
    upcoming_deadlines: list[ComplianceDeadline] = Field(default_factory=list)
    recent_alerts: list[ComplianceAlert] = Field(default_factory=list)
    section_scores: dict[str, float] = Field(default_factory=dict)
    trend: list[dict] = Field(default_factory=list)  # Score over time


# ---- Rights Agent Models ----

class RightsRequestInput(BaseModel):
    """Input for creating a data principal rights request."""
    request_type: str  # access, correction, erasure, nomination, portability
    subject_name: str
    subject_email: str
    description: str
    evidence: dict = Field(default_factory=dict)


class GrievanceInput(BaseModel):
    """Input for filing a DPDP grievance."""
    category: str
    description: str
    evidence: dict = Field(default_factory=dict)


class BreachNotificationInput(BaseModel):
    """Input for generating a breach notification."""
    breach_description: str
    data_categories_affected: list[str] = Field(default_factory=list)
    estimated_records_affected: int = 0
    breach_discovered_at: datetime = Field(default_factory=lambda: datetime.now())
    containment_measures: str = ""
    is_ongoing: bool = False


class BreachNotification(BaseModel):
    """Generated breach notification for DPB and data principals."""
    dpb_notification: str  # For Data Protection Board
    principal_notification: str  # For affected data principals
    cert_in_notification: str  # For CERT-In (6-hour window)
    timeline: dict = Field(default_factory=dict)
    recommended_actions: list[str] = Field(default_factory=list)
