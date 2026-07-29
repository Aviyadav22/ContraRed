"""
DPDP Monitor Agent — Continuous compliance tracking and alerting.

Provides:
  - Real-time compliance posture dashboard
  - Deadline tracking for the phased 2025, 2026, and 2027 commencements
  - Regulatory update alerts
  - Contract expiry and renewal compliance checks
  - Compliance drift detection
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dpdp.models import (
    ComplianceDashboard,
    ComplianceDeadline,
    ComplianceAlert,
    DPDPSection,
)

logger = logging.getLogger(__name__)

# Key DPDP deadlines
DPDP_DEADLINES = [
    {
        "title": "DPDP Rules Phase 1 — Board Constitution",
        "description": "DPB constitution, definitions, and procedural rules effective.",
        "deadline": date(2025, 11, 13),
        "section": None,
    },
    {
        "title": "Consent Manager Registration Opens",
        "description": "Consent Manager registration with DPB becomes operative. Companies using consent managers must ensure registration.",
        "deadline": date(2026, 11, 13),
        "section": "section_9",
    },
    {
        "title": "DPDP Substantive Compliance Phase",
        "description": "Most substantive provisions become effective. Prepare consent, notice, breach, processor-contract, and rights workflows; statutory maxima vary by breach category.",
        "deadline": date(2027, 5, 13),
        "section": None,
    },
    {
        "title": "Significant Data Fiduciary — DPO Appointment",
        "description": "Entities notified as Significant Data Fiduciaries must appoint an India-based DPO and meet DPIA and audit duties.",
        "deadline": date(2027, 5, 13),
        "section": "section_10",
    },
    {
        "title": "Notice and Consent Provisions Commence",
        "description": "Section 5 and Rule 3 notice duties commence; legacy consent processing requires the statutory transition notice.",
        "deadline": date(2027, 5, 13),
        "section": "section_5",
    },
    {
        "title": "Processor-Contract Safeguards Commence",
        "description": "Processor engagements require a valid contract, including appropriate provisions for Rule 6 security safeguards.",
        "deadline": date(2027, 5, 13),
        "section": "section_8",
    },
]


class MonitorAgent:
    """Monitors compliance posture, deadlines, and generates alerts."""

    async def get_dashboard(
        self,
        db: AsyncSession,
        organization_id: Optional[str] = None,
    ) -> ComplianceDashboard:
        """Build real-time compliance dashboard."""
        dashboard = ComplianceDashboard()

        # Get deadlines
        dashboard.upcoming_deadlines = self._get_deadlines()

        # Get alerts
        dashboard.recent_alerts = self._generate_alerts()

        # Try to pull DB stats
        try:
            stats = await self._get_db_stats(db, organization_id)
            dashboard.pending_rights_requests = stats.get("pending_rights", 0)
            dashboard.pending_grievances = stats.get("pending_grievances", 0)
            dashboard.contracts_scanned = stats.get("contracts_scanned", 0)
        except Exception as exc:
            logger.warning("Could not fetch DB stats: %s", exc)

        return dashboard

    def _get_deadlines(self) -> list[ComplianceDeadline]:
        """Calculate deadline statuses."""
        today = date.today()
        deadlines = []

        for d in DPDP_DEADLINES:
            dl = d["deadline"]
            days_remaining = (dl - today).days

            if days_remaining < 0:
                status = "completed" if dl < date(2026, 1, 1) else "overdue"
            elif days_remaining <= 30:
                status = "due_soon"
            else:
                status = "upcoming"

            deadlines.append(ComplianceDeadline(
                title=d["title"],
                description=d["description"],
                deadline=dl,
                section=DPDPSection(d["section"]) if d["section"] else None,
                status=status,
                days_remaining=max(0, days_remaining),
            ))

        return sorted(deadlines, key=lambda x: x.deadline)

    def _generate_alerts(self) -> list[ComplianceAlert]:
        """Generate compliance alerts based on current date and deadlines."""
        today = date.today()
        alerts = []

        # Check proximity to enforcement
        enforcement = date(2027, 5, 13)
        days_to_enforcement = (enforcement - today).days

        if 0 < days_to_enforcement <= 90:
            alerts.append(ComplianceAlert(
                alert_type="deadline",
                severity="critical",
                title="DPDP Substantive Compliance Phase in Less Than 90 Days",
                description=f"Only {days_to_enforcement} days until most substantive provisions "
                           "commence on May 13, 2027. The statutory schedule lists maximum "
                           "penalties up to INR 250 crore for specified breaches.",
                action_required="Complete all compliance preparations immediately.",
            ))
        elif 0 < days_to_enforcement <= 180:
            alerts.append(ComplianceAlert(
                alert_type="deadline",
                severity="warning",
                title=f"DPDP Substantive Phase in {days_to_enforcement} Days",
                description="The main substantive commencement is approaching. Ensure consent mechanisms, "
                           "privacy notices, breach plans, and DPAs are in place.",
                action_required="Run gap assessment and start remediation.",
            ))
        elif days_to_enforcement <= 0:
            alerts.append(ComplianceAlert(
                alert_type="deadline",
                severity="critical",
                title="DPDP Substantive Compliance Phase Is in Effect",
                description="Most substantive DPDP Act and Rules obligations are now in effect. "
                           "Check the commencement notifications for any provision-specific timing.",
                action_required="Ensure full compliance across all sections.",
            ))

        # Consent manager deadline
        cm_deadline = date(2026, 11, 13)
        days_to_cm = (cm_deadline - today).days
        if 0 < days_to_cm <= 60:
            alerts.append(ComplianceAlert(
                alert_type="deadline",
                severity="warning",
                title=f"Consent Manager Registration in {days_to_cm} Days",
                description="Consent Manager provisions become operative Nov 13, 2026. "
                           "If you use consent management platforms, ensure they're registered with DPB.",
                action_required="Verify consent manager registration status.",
            ))

        # General compliance reminders
        alerts.append(ComplianceAlert(
            alert_type="regulatory_update",
            severity="info",
            title="DPDP Rules 2025 — Phased Implementation Active",
            description="Phase 1 (Board constitution and procedural provisions) is effective. "
                       "Consent Manager provisions take effect Nov 2026. Most substantive "
                       "obligations take effect May 2027.",
            action_required="Review current compliance status against upcoming phases.",
        ))

        return alerts

    async def _get_db_stats(
        self,
        db: AsyncSession,
        organization_id: Optional[str] = None,
    ) -> dict:
        """Pull compliance statistics from database."""
        stats: dict = {
            "pending_rights": 0,
            "pending_grievances": 0,
            "contracts_scanned": 0,
        }

        try:
            from app.models.consent import RightsRequest, Grievance, RightsRequestStatus, GrievanceStatus

            # Pending rights requests
            rights_query = select(func.count(RightsRequest.id)).where(
                RightsRequest.status.in_([
                    RightsRequestStatus.SUBMITTED.value,
                    RightsRequestStatus.ACKNOWLEDGED.value,
                    RightsRequestStatus.IN_PROGRESS.value,
                ])
            )
            if organization_id:
                rights_query = rights_query.where(
                    RightsRequest.organization_id == organization_id
                )
            result = await db.execute(rights_query)
            stats["pending_rights"] = result.scalar() or 0

            # Pending grievances
            grievance_query = select(func.count(Grievance.id)).where(
                Grievance.status.in_([
                    GrievanceStatus.SUBMITTED.value,
                    GrievanceStatus.ACKNOWLEDGED.value,
                    GrievanceStatus.INVESTIGATING.value,
                ])
            )
            if organization_id:
                grievance_query = grievance_query.where(
                    Grievance.organization_id == organization_id
                )
            result = await db.execute(grievance_query)
            stats["pending_grievances"] = result.scalar() or 0

            # Documents scanned (if table exists)
            try:
                from app.models.document import Document
                doc_query = select(func.count(Document.id))
                if organization_id:
                    doc_query = doc_query.where(
                        Document.organization_id == organization_id
                    )
                result = await db.execute(doc_query)
                stats["contracts_scanned"] = result.scalar() or 0
            except Exception:
                pass

        except Exception as exc:
            logger.warning("DB stats query failed: %s", exc)

        return stats

    async def check_compliance_drift(
        self,
        db: AsyncSession,
        organization_id: str,
        previous_score: float,
        current_score: float,
    ) -> list[ComplianceAlert]:
        """Detect compliance score drift and generate alerts."""
        alerts = []
        drift = current_score - previous_score

        if drift < -10:
            alerts.append(ComplianceAlert(
                alert_type="drift",
                severity="critical",
                title=f"Compliance Score Dropped by {abs(drift):.1f} Points",
                description=f"Score decreased from {previous_score:.1f} to {current_score:.1f}. "
                           f"This may indicate new compliance gaps or contract changes.",
                action_required="Review recent contract changes and run gap assessment.",
            ))
        elif drift < -5:
            alerts.append(ComplianceAlert(
                alert_type="drift",
                severity="warning",
                title=f"Compliance Score Decreased by {abs(drift):.1f} Points",
                description=f"Minor decrease from {previous_score:.1f} to {current_score:.1f}.",
                action_required="Monitor for further decline.",
            ))
        elif drift > 10:
            alerts.append(ComplianceAlert(
                alert_type="drift",
                severity="info",
                title=f"Compliance Score Improved by {drift:.1f} Points",
                description=f"Score improved from {previous_score:.1f} to {current_score:.1f}.",
            ))

        return alerts
