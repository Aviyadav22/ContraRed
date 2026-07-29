"""
DPDP Compliance Command Center — Orchestrator.

Central engine that coordinates the 5 specialized DPDP agents:
  1. Scanner Agent — Bulk contract scanning
  2. Gap Assessor Agent — Organization-wide gap analysis
  3. Remediation Agent — AI-assisted drafts for legal and factual review
  4. Monitor Agent — Continuous compliance tracking
  5. Rights Agent — Data Principal rights automation

Loads DPDP rules from the compliance layer system and provides
a unified interface for all DPDP compliance operations.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dpdp.agents.scanner_agent import ScannerAgent
from app.services.dpdp.agents.gap_assessor_agent import GapAssessorAgent
from app.services.dpdp.agents.remediation_agent import RemediationAgent
from app.services.dpdp.agents.monitor_agent import MonitorAgent
from app.services.dpdp.agents.rights_agent import RightsAgent
from app.services.dpdp.consent_compliance_bridge import consent_compliance_bridge
from app.services.dpdp.knowledge_base import dpdp_knowledge_base
from app.services.dpdp.report_service import compliance_report_service
from app.services.dpdp.models import (
    ContractScanRequest,
    ContractScanResult,
    BulkScanRequest,
    PortfolioReport,
    AssessmentRequest,
    GapAssessmentResult,
    AssessmentQuestion,
    RemediationRequest,
    RemediationOutput,
    ComplianceDashboard,
    RightsRequestInput,
    GrievanceInput,
    BreachNotificationInput,
    BreachNotification,
)

logger = logging.getLogger(__name__)


class DPDPOrchestrator:
    """Central orchestrator for the DPDP Compliance Command Center."""

    def __init__(self):
        self.scanner = ScannerAgent()
        self.assessor = GapAssessorAgent()
        self.remediation = RemediationAgent()
        self.monitor = MonitorAgent()
        self.rights = RightsAgent()
        self.bridge = consent_compliance_bridge
        self.knowledge_base = dpdp_knowledge_base
        self.report_service = compliance_report_service

    # ---- Rule Loading ----

    async def _load_dpdp_rules(self, db: Optional[AsyncSession] = None) -> list[dict]:
        """Load DPDP rules from DB (compliance layer service) or fallback to static."""
        if db:
            try:
                from app.services.compliance_layer_service import get_layer_rules_as_dicts
                rules = await get_layer_rules_as_dicts(db, "dpdp")
                if rules:
                    return rules
            except Exception as exc:
                logger.warning("Could not load DPDP rules from DB: %s", exc)

        # Fallback: load from static definition
        from scripts.compliance_layers.dpdp import DPDP_LAYER
        return DPDP_LAYER.get("rules", [])

    # ---- Scanner Operations ----

    async def scan_contract(
        self,
        db: Optional[AsyncSession],
        request: ContractScanRequest,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> ContractScanResult:
        """Scan a single contract for DPDP compliance and persist results."""
        rules = await self._load_dpdp_rules(db)
        result = await self.scanner.scan_contract(request, rules)

        # Persist scan result for trend tracking
        if db:
            try:
                from app.models.compliance_result import ComplianceScanResult as ScanResultModel
                stored = ScanResultModel(
                    organization_id=uuid.UUID(organization_id) if organization_id else None,
                    user_id=uuid.UUID(user_id) if user_id else None,
                    contract_name=result.contract_name,
                    contract_type=result.contract_type,
                    jurisdiction=request.jurisdiction,
                    compliance_score=round(result.compliance_score),
                    total_findings=result.total_findings,
                    red_count=result.red_findings,
                    yellow_count=result.yellow_findings,
                    green_count=result.green_findings,
                    deal_breaker_count=result.deal_breakers,
                    findings=[f.model_dump() for f in result.findings] if result.findings else [],
                    risk_summary={
                        "red": result.red_findings,
                        "yellow": result.yellow_findings,
                        "green": result.green_findings,
                        "deal_breakers": result.deal_breakers,
                    },
                )
                db.add(stored)
                await db.commit()
            except Exception as e:
                logger.warning("Failed to persist scan result: %s", e)

        return result

    async def scan_portfolio(
        self,
        db: Optional[AsyncSession],
        request: BulkScanRequest,
    ) -> PortfolioReport:
        """Scan multiple contracts and generate portfolio report."""
        rules = await self._load_dpdp_rules(db)
        return await self.scanner.scan_portfolio(request.contracts, rules)

    # ---- Gap Assessment ----

    def get_assessment_questions(
        self,
        processes_children_data: bool = False,
        is_significant_fiduciary: bool = False,
        has_cross_border: bool = False,
    ) -> list[AssessmentQuestion]:
        """Get applicable assessment questions for an organization."""
        return self.assessor.get_questions(
            processes_children_data=processes_children_data,
            is_significant_fiduciary=is_significant_fiduciary,
            has_cross_border=has_cross_border,
        )

    async def run_assessment(
        self,
        request: AssessmentRequest,
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> GapAssessmentResult:
        """Run full DPDP gap assessment, auto-answering consent questions from real data."""
        # Auto-fill consent-related answers from real consent data
        if db:
            try:
                auto_answers = await self.bridge.auto_answer_consent_questions(
                    db, uuid.UUID(organization_id) if organization_id else None
                )
                # Merge auto-answers with manual answers (manual takes precedence)
                existing_ids = {a.question_id for a in (request.answers or [])}
                from app.services.dpdp.models import AssessmentAnswer
                for q_id, answer_val in auto_answers.items():
                    if q_id not in existing_ids:
                        request.answers.append(AssessmentAnswer(
                            question_id=q_id,
                            answer=answer_val,
                            evidence="Auto-detected from consent management system",
                        ))
            except Exception as e:
                logger.debug("Auto-answer consent questions failed: %s", e)

        result = await self.assessor.assess(request)

        # Persist assessment result
        if db:
            try:
                from app.models.compliance_result import ComplianceAssessment
                stored = ComplianceAssessment(
                    organization_id=uuid.UUID(organization_id) if organization_id else None,
                    user_id=uuid.UUID(user_id) if user_id else None,
                    organization_name=request.organization_name,
                    industry=request.industry,
                    overall_score=round(result.overall_score),
                    overall_status=result.overall_status.value if hasattr(result.overall_status, 'value') else str(result.overall_status),
                    section_scores=[s.model_dump() for s in result.section_scores] if result.section_scores else [],
                    critical_gaps=result.critical_gaps or [],
                    action_items=result.action_items or [],
                    estimated_remediation_effort=result.estimated_remediation_effort,
                    answers=[a.model_dump() for a in request.answers] if request.answers else [],
                )
                db.add(stored)
                await db.commit()
            except Exception as e:
                logger.warning("Failed to persist assessment result: %s", e)

        return result

    # ---- Remediation ----

    async def generate_remediation(
        self, request: RemediationRequest
    ) -> RemediationOutput:
        """Generate DPDP-oriented remediation content for legal review."""
        return await self.remediation.generate(request)

    async def generate_breach_notification(
        self, input_data: BreachNotificationInput
    ) -> BreachNotification:
        """Generate breach notification templates."""
        return await self.remediation.generate_breach_notification(input_data)

    # ---- Monitoring ----

    async def get_dashboard(
        self,
        db: AsyncSession,
        organization_id: Optional[str] = None,
    ) -> ComplianceDashboard:
        """Get real-time compliance dashboard with consent health."""
        dashboard = await self.monitor.get_dashboard(db, organization_id)

        # Enrich with consent health and real trend data
        try:
            org_uuid = uuid.UUID(organization_id) if organization_id else None
            consent_health = await self.bridge.get_consent_health(db, org_uuid)
            trend = await self.report_service.get_compliance_trend(db, org_uuid)

            # Update dashboard with real data
            dashboard.trend = trend
            # Blend consent health into overall score
            if consent_health.get("health_score", 0) > 0 and dashboard.overall_score > 0:
                dashboard.overall_score = round(
                    dashboard.overall_score * 0.7 + consent_health["health_score"] * 0.3
                )
        except Exception as e:
            logger.debug("Dashboard enrichment failed: %s", e)

        return dashboard

    # ---- Reports ----

    async def generate_report(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> dict:
        """Generate comprehensive DPDP compliance report."""
        return await self.report_service.generate_full_report(
            db,
            organization_id=uuid.UUID(organization_id) if organization_id else None,
            user_id=uuid.UUID(user_id) if user_id else None,
        )

    async def get_report_history(
        self, db: AsyncSession, organization_id: Optional[str] = None
    ) -> list:
        """Get compliance report history."""
        return await self.report_service.get_report_history(
            db,
            organization_id=uuid.UUID(organization_id) if organization_id else None,
        )

    # ---- Knowledge Base ----

    def search_regulation(self, query: str, max_results: int = 5) -> list:
        """Search DPDP Act/Rules for relevant provisions."""
        sections = self.knowledge_base.search(query, max_results)
        return [
            {
                "source": s.source,
                "section": s.section_number,
                "title": s.title,
                "summary": s.summary,
                "full_text": s.full_text,
                "penalties": s.penalties,
                "deadline": s.deadline,
            }
            for s in sections
        ]

    # ---- Consent Health ----

    async def get_consent_health(
        self, db: AsyncSession, organization_id: Optional[str] = None
    ) -> dict:
        """Get consent management health metrics."""
        org_uuid = uuid.UUID(organization_id) if organization_id else None
        return await self.bridge.get_consent_health(db, org_uuid)

    # ---- Rights Management ----

    async def submit_rights_request(
        self,
        db: AsyncSession,
        subject_id: str,
        input_data: RightsRequestInput,
        organization_id: Optional[str] = None,
    ) -> dict:
        """Submit a Data Principal rights request."""
        return await self.rights.submit_rights_request(
            db, subject_id, input_data, organization_id
        )

    async def get_rights_requests(
        self,
        db: AsyncSession,
        subject_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        """List rights requests."""
        return await self.rights.get_rights_requests(
            db, subject_id, organization_id, status_filter
        )

    async def update_rights_request(
        self,
        db: AsyncSession,
        request_id: str,
        new_status: str,
        response_details: Optional[dict] = None,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> dict:
        """Update rights request status."""
        return await self.rights.update_rights_request(
            db, request_id, new_status, response_details, assigned_to, resolution_notes
        )

    async def file_grievance(
        self,
        db: AsyncSession,
        subject_id: str,
        input_data: GrievanceInput,
        organization_id: Optional[str] = None,
    ) -> dict:
        """File a DPDP grievance."""
        return await self.rights.file_grievance(
            db, subject_id, input_data, organization_id
        )

    async def get_grievances(
        self,
        db: AsyncSession,
        subject_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> list[dict]:
        """List grievances."""
        return await self.rights.get_grievances(
            db, subject_id, organization_id, status_filter
        )

    async def update_grievance(
        self,
        db: AsyncSession,
        grievance_id: str,
        new_status: str,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> dict:
        """Update grievance status."""
        return await self.rights.update_grievance(
            db, grievance_id, new_status, assigned_to, resolution_notes
        )

    async def create_nomination(
        self,
        db: AsyncSession,
        subject_id: str,
        nominee_name: str,
        nominee_email: Optional[str] = None,
        nominee_phone: Optional[str] = None,
        relationship: Optional[str] = None,
    ) -> dict:
        """Create a nomination."""
        return await self.rights.create_nomination(
            db, subject_id, nominee_name, nominee_email, nominee_phone, relationship
        )

    async def get_nominations(
        self, db: AsyncSession, subject_id: str
    ) -> list[dict]:
        """Get nominations for a data principal."""
        return await self.rights.get_nominations(db, subject_id)

    async def revoke_nomination(
        self, db: AsyncSession, nomination_id: str, subject_id: str
    ) -> dict:
        """Revoke a nomination."""
        return await self.rights.revoke_nomination(db, nomination_id, subject_id)

    async def get_overdue_requests(
        self,
        db: AsyncSession,
        organization_id: Optional[str] = None,
    ) -> dict:
        """Get overdue rights requests and grievances."""
        return await self.rights.get_overdue_requests(db, organization_id)


# Singleton instance
_orchestrator: Optional[DPDPOrchestrator] = None


def get_dpdp_orchestrator() -> DPDPOrchestrator:
    """Get or create the DPDP orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DPDPOrchestrator()
    return _orchestrator
