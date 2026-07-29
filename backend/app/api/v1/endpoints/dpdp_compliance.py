"""
DPDP Compliance Command Center — API Endpoints.

Provides REST API for the 5-agent DPDP compliance system:
  - Contract scanning (single + bulk portfolio)
  - Gap assessment (questionnaire + scoring)
  - Remediation (DPA, privacy notice, consent form, breach templates)
  - Compliance dashboard (deadlines, alerts, posture)
  - Rights management (requests, grievances, nominations)
"""

import logging
from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.consent import Grievance, RightsRequest
from app.models.user import User, UserRole
from app.services.breach_notification_service import breach_notification_service
from app.services.dpdp.orchestrator import get_dpdp_orchestrator
from app.services.dpdp.models import (
    ContractScanRequest,
    BulkScanRequest,
    AssessmentRequest,
    RemediationRequest,
    RemediationType,
    BreachNotificationInput,
    RightsRequestInput,
    GrievanceInput,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Contract Scanning ----


@router.post("/scan", summary="Scan a contract for DPDP compliance")
async def scan_contract(
    request: ContractScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Scan a single contract against all 18 DPDP rules.

    Returns per-rule findings with risk levels, suggested fixes,
    and an overall compliance score.
    """
    orchestrator = get_dpdp_orchestrator()
    result = await orchestrator.scan_contract(
        db, request,
        user_id=str(current_user.id),
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
    )
    return result.model_dump()


@router.post("/scan/bulk", summary="Bulk scan contracts for DPDP compliance")
async def scan_portfolio(
    request: BulkScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Scan up to 100 contracts and generate a portfolio compliance report.

    Returns individual contract results plus aggregate heatmap,
    section coverage, and top risks across the portfolio.
    """
    orchestrator = get_dpdp_orchestrator()
    report = await orchestrator.scan_portfolio(db, request)
    return report.model_dump()


# ---- Gap Assessment ----


@router.get("/assessment/questions", summary="Get DPDP assessment questionnaire")
async def get_assessment_questions(
    processes_children_data: bool = Query(False),
    is_significant_fiduciary: bool = Query(False),
    has_cross_border: bool = Query(False),
    current_user=Depends(get_current_user),
):
    """Get the applicable DPDP compliance assessment questions.

    Questions are filtered based on the organization profile
    (children's data, SDF status, cross-border transfers).
    """
    orchestrator = get_dpdp_orchestrator()
    questions = orchestrator.get_assessment_questions(
        processes_children_data=processes_children_data,
        is_significant_fiduciary=is_significant_fiduciary,
        has_cross_border=has_cross_border,
    )
    return [q.model_dump() for q in questions]


@router.post("/assessment", summary="Run DPDP gap assessment")
async def run_assessment(
    request: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run a full DPDP compliance gap assessment.

    Analyzes answers against 40+ compliance questions, produces
    section-by-section scores, critical gaps, action items,
    and deadline risk assessment.

    Consent-related questions are auto-answered from real consent data.
    """
    orchestrator = get_dpdp_orchestrator()
    result = await orchestrator.run_assessment(
        request,
        db=db,
        user_id=str(current_user.id),
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
    )
    return result.model_dump()


# ---- Remediation ----


@router.post("/remediate", summary="Generate DPDP-oriented draft for legal review")
async def generate_remediation(
    request: RemediationRequest,
    current_user=Depends(get_current_user),
):
    """Generate DPDP-oriented remediation content for legal and factual review.

    Supported types:
    - contract_clause: Draft contract language addressing selected gaps
    - dpa_template: Data Processing Agreement draft
    - privacy_notice: Notice draft aligned to DPDP Section 5 / Rule 3
    - consent_form: Granular consent collection form
    - breach_notification_template: DPB + data principal templates
    - policy_update: Privacy policy update recommendations
    - process_recommendation: Process improvement steps
    """
    orchestrator = get_dpdp_orchestrator()
    output = await orchestrator.generate_remediation(request)
    return output.model_dump()


@router.post("/remediate/breach-notification", summary="Generate breach notifications")
async def generate_breach_notification(
    input_data: BreachNotificationInput,
    current_user=Depends(get_current_user),
):
    """Generate staged DPDP notices and a conditional CERT-In template.

    Produces:
    1. Initial Board notice due without delay
    2. Detailed Board update due within 72 hours unless extended
    3. Affected Data Principal notice due without delay
    4. CERT-In template for incidents within its specified reportable categories

    Also calculates the remaining time for the detailed and conditional reports.
    """
    orchestrator = get_dpdp_orchestrator()
    notification = await orchestrator.generate_breach_notification(input_data)
    return notification.model_dump()


class BreachReportRequest(BaseModel):
    breach_type: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=4000)
    affected_user_ids: List[UUID] = Field(..., min_length=1, max_length=1000)
    discovered_at: Optional[datetime] = None
    severity: Literal["low", "medium", "high", "critical"] = "high"


@router.post("/breaches/report", summary="Report and notify affected account holders")
async def report_personal_data_breach(
    report: BreachReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create an auditable breach workflow and send affected-user notices."""
    discovered_at = report.discovered_at
    if discovered_at:
        if discovered_at.tzinfo is None:
            discovered_at = discovered_at.replace(tzinfo=timezone.utc)
        if discovered_at > datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="discovered_at cannot be in the future")

    user_result = await db.execute(
        select(User.id, User.organization_id).where(
            User.id.in_(report.affected_user_ids)
        )
    )
    matched = {row.id: row.organization_id for row in user_result.all()}
    if set(report.affected_user_ids) != set(matched):
        raise HTTPException(status_code=400, detail="One or more affected users do not exist")
    if (
        current_user.role != UserRole.SUPER_ADMIN
        and (
            current_user.organization_id is None
            or any(
                org_id is None
                or org_id != current_user.organization_id
                for org_id in matched.values()
            )
        )
    ):
        raise HTTPException(status_code=403, detail="Affected users must belong to your organization")

    return await breach_notification_service.report_breach(
        db=db,
        breach_type=report.breach_type,
        description=report.description,
        affected_user_ids=report.affected_user_ids,
        discovered_at=discovered_at,
        severity=report.severity,
    )


@router.get("/remediate/templates", summary="List available remediation templates")
async def list_templates(
    current_user=Depends(get_current_user),
):
    """List all available DPDP remediation template types."""
    return {
        "templates": [
            {
                "type": t.value,
                "name": t.value.replace("_", " ").title(),
                "description": _TEMPLATE_DESCRIPTIONS.get(t.value, ""),
            }
            for t in RemediationType
        ]
    }


_TEMPLATE_DESCRIPTIONS = {
    "contract_clause": "Generate DPDP-oriented contract clauses for legal review",
    "dpa_template": "Data Processing Agreement draft aligned to Section 8(2), for legal review",
    "privacy_notice": "Privacy Notice draft aligned to DPDP Section 5 in the requested supported language",
    "consent_form": "Granular consent collection form with per-purpose toggles",
    "breach_notification_template": "Breach notification templates for DPB, data principals, and CERT-In",
    "policy_update": "Recommendations for updating existing privacy policies to DPDP standards",
    "process_recommendation": "Process improvement steps for DPDP compliance",
}


# ---- Compliance Dashboard ----


@router.get("/dashboard", summary="Get DPDP compliance dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get real-time DPDP compliance posture dashboard.

    Includes:
    - Upcoming deadlines (Consent Manager provisions Nov 2026, substantive phase May 2027)
    - Active alerts and recommendations
    - Pending rights requests and grievances
    - Contracts scanned count
    """
    orchestrator = get_dpdp_orchestrator()
    org_id = getattr(current_user, "organization_id", None)
    dashboard = await orchestrator.get_dashboard(
        db, organization_id=str(org_id) if org_id else None
    )
    return dashboard.model_dump()


# ---- Rights Management ----


@router.post("/rights/request", summary="Submit a Data Principal rights request", deprecated=True)
async def submit_rights_request(
    input_data: RightsRequestInput,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit a DPDP rights request (access, correction, erasure, nomination, portability).

    Applies the service's internal 90-day target and logs to the audit trail.
    """
    orchestrator = get_dpdp_orchestrator()
    org_id = getattr(current_user, "organization_id", None)
    return await orchestrator.submit_rights_request(
        db,
        subject_id=str(current_user.id),
        input_data=input_data,
        organization_id=str(org_id) if org_id else None,
    )


@router.get("/rights/requests", summary="List rights requests", deprecated=True)
async def list_rights_requests(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List Data Principal rights requests.

    Admin users see all requests for their organization.
    Regular users see only their own requests.
    """
    orchestrator = get_dpdp_orchestrator()
    org_id = getattr(current_user, "organization_id", None)
    role = current_user.role

    if role == UserRole.SUPER_ADMIN:
        return await orchestrator.get_rights_requests(
            db,
            organization_id=None,
            status_filter=status,
        )
    if role == UserRole.ADMIN and org_id is not None:
        return await orchestrator.get_rights_requests(
            db,
            organization_id=str(org_id) if org_id else None,
            status_filter=status,
        )
    else:
        return await orchestrator.get_rights_requests(
            db,
            subject_id=str(current_user.id),
            status_filter=status,
        )


class RightsRequestUpdate(BaseModel):
    status: str
    response_details: Optional[dict] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


@router.patch("/rights/requests/{request_id}", summary="Update a rights request", deprecated=True)
async def update_rights_request(
    request_id: str,
    update: RightsRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update a rights request status (admin only)."""
    role = current_user.role
    if role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        request_uuid = UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID")
    request_result = await db.execute(
        select(RightsRequest).where(RightsRequest.id == request_uuid)
    )
    rights_request = request_result.scalar_one_or_none()
    if not rights_request or (
        role != UserRole.SUPER_ADMIN
        and (
            current_user.organization_id is None
            or rights_request.organization_id is None
            or rights_request.organization_id != current_user.organization_id
        )
    ):
        raise HTTPException(status_code=404, detail="Rights request not found")

    orchestrator = get_dpdp_orchestrator()
    try:
        return await orchestrator.update_rights_request(
            db,
            request_id=request_id,
            new_status=update.status,
            response_details=update.response_details,
            assigned_to=update.assigned_to,
            resolution_notes=update.resolution_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ---- Grievances ----


@router.post("/grievances", summary="File a DPDP grievance", deprecated=True)
async def file_grievance(
    input_data: GrievanceInput,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """File a DPDP Section 13 grievance.

    Applies the service's internal 30-day response target. Any acknowledgment
    target is operational policy, not a separate DPDP statutory deadline.
    """
    orchestrator = get_dpdp_orchestrator()
    org_id = getattr(current_user, "organization_id", None)
    return await orchestrator.file_grievance(
        db,
        subject_id=str(current_user.id),
        input_data=input_data,
        organization_id=str(org_id) if org_id else None,
    )


@router.get("/grievances", summary="List grievances", deprecated=True)
async def list_grievances(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List grievances. Admin sees org-wide, users see their own."""
    orchestrator = get_dpdp_orchestrator()
    org_id = getattr(current_user, "organization_id", None)
    role = current_user.role

    if role == UserRole.SUPER_ADMIN:
        return await orchestrator.get_grievances(
            db,
            organization_id=None,
            status_filter=status,
        )
    if role == UserRole.ADMIN and org_id is not None:
        return await orchestrator.get_grievances(
            db,
            organization_id=str(org_id) if org_id else None,
            status_filter=status,
        )
    else:
        return await orchestrator.get_grievances(
            db,
            subject_id=str(current_user.id),
            status_filter=status,
        )


class GrievanceUpdate(BaseModel):
    status: str
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


@router.patch("/grievances/{grievance_id}", summary="Update a grievance", deprecated=True)
async def update_grievance(
    grievance_id: str,
    update: GrievanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update grievance status (admin only)."""
    role = current_user.role
    if role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        grievance_uuid = UUID(grievance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid grievance ID")
    grievance_result = await db.execute(
        select(Grievance).where(Grievance.id == grievance_uuid)
    )
    grievance = grievance_result.scalar_one_or_none()
    if not grievance or (
        role != UserRole.SUPER_ADMIN
        and (
            current_user.organization_id is None
            or grievance.organization_id is None
            or grievance.organization_id != current_user.organization_id
        )
    ):
        raise HTTPException(status_code=404, detail="Grievance not found")

    orchestrator = get_dpdp_orchestrator()
    try:
        return await orchestrator.update_grievance(
            db,
            grievance_id=grievance_id,
            new_status=update.status,
            assigned_to=update.assigned_to,
            resolution_notes=update.resolution_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ---- Nominations ----


class NominationCreate(BaseModel):
    nominee_name: str = Field(..., min_length=1)
    nominee_email: Optional[str] = None
    nominee_phone: Optional[str] = None
    relationship: Optional[str] = None


@router.post("/nominations", summary="Create a nomination", deprecated=True)
async def create_nomination(
    data: NominationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a Data Principal nomination (Section 14).

    Nominate someone to exercise your rights in case of death or incapacity.
    """
    orchestrator = get_dpdp_orchestrator()
    return await orchestrator.create_nomination(
        db,
        subject_id=str(current_user.id),
        nominee_name=data.nominee_name,
        nominee_email=data.nominee_email,
        nominee_phone=data.nominee_phone,
        relationship=data.relationship,
    )


@router.get("/nominations", summary="List nominations", deprecated=True)
async def list_nominations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List your active nominations."""
    orchestrator = get_dpdp_orchestrator()
    return await orchestrator.get_nominations(db, str(current_user.id))


@router.delete("/nominations/{nomination_id}", summary="Revoke a nomination", deprecated=True)
async def revoke_nomination(
    nomination_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Revoke an existing nomination."""
    orchestrator = get_dpdp_orchestrator()
    return await orchestrator.revoke_nomination(
        db, nomination_id, str(current_user.id)
    )


# ---- Overdue Tracking ----


@router.get("/overdue", summary="Get overdue rights requests and grievances")
async def get_overdue(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all overdue rights requests and grievances (admin only).

    Helps compliance teams track missed published service targets.
    """
    role = current_user.role
    if role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    orchestrator = get_dpdp_orchestrator()
    org_id = (
        None
        if role == UserRole.SUPER_ADMIN
        else getattr(current_user, "organization_id", None)
    )
    if role != UserRole.SUPER_ADMIN and org_id is None:
        raise HTTPException(
            status_code=403,
            detail="Organization membership is required for the overdue queue.",
        )
    return await orchestrator.get_overdue_requests(
        db, organization_id=str(org_id) if org_id else None
    )


# ---- Compliance Reports ----


@router.post("/report", summary="Generate comprehensive DPDP compliance report")
async def generate_report(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate a full DPDP compliance report for audit readiness.

    Aggregates contract scan results, gap assessments, consent health,
    and regulatory citations into a comprehensive report.
    """
    orchestrator = get_dpdp_orchestrator()
    org_id = getattr(current_user, "organization_id", None)
    return await orchestrator.generate_report(
        db,
        user_id=str(current_user.id),
        organization_id=str(org_id) if org_id else None,
    )


@router.get("/reports", summary="Get compliance report history")
async def get_report_history(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get previously generated compliance reports."""
    orchestrator = get_dpdp_orchestrator()
    org_id = getattr(current_user, "organization_id", None)
    return await orchestrator.get_report_history(
        db, organization_id=str(org_id) if org_id else None
    )


# ---- Knowledge Base ----


@router.get("/knowledge/search", summary="Search DPDP Act provisions")
async def search_regulation(
    q: str = Query(..., min_length=2, description="Search query"),
    max_results: int = Query(5, ge=1, le=20),
    current_user=Depends(get_current_user),
):
    """Search DPDP Act 2023 and DPDP Rules 2025 for relevant provisions.

    Returns matching sections with full text, penalties, and deadlines.
    Useful for understanding regulatory requirements for specific compliance areas.
    """
    orchestrator = get_dpdp_orchestrator()
    return orchestrator.search_regulation(q, max_results)


# ---- Consent Health ----


@router.get("/consent-health", summary="Get consent management health metrics")
async def get_consent_health(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get consent management health metrics for the compliance dashboard.

    Returns consent coverage, purpose-level stats, recent events, and
    an overall health score used in compliance scoring.
    """
    orchestrator = get_dpdp_orchestrator()
    org_id = getattr(current_user, "organization_id", None)
    return await orchestrator.get_consent_health(
        db, organization_id=str(org_id) if org_id else None
    )
