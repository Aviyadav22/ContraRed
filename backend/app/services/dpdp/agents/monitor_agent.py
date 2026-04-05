"""
DPDP Monitor Agent — Continuous compliance tracking and alerting.

Provides:
  - Real-time compliance posture dashboard
  - Deadline tracking (consent manager Nov 2026, enforcement May 2027)
  - Regulatory update alerts
  - Contract expiry and renewal compliance checks
  - Compliance drift detection
"""

import logging
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dpdp.models import (
    ComplianceDashboard,
    ComplianceDeadline,
    ComplianceAlert,
    ComplianceStatus,
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
        "title": "DPDP Act Full Enforcement",
        "description": "All substantive provisions effective. Penalties up to Rs 250 crore enforceable. Must have: consent mechanisms, privacy notices, breach plans, DPAs, rights workflows.",
        "deadline": date(2027, 5, 13),
        "section": None,
    },
    {
        "title": "Significant Data Fiduciary — DPO Appointment",
        "description": "SDFs must appoint India-resident DPO and commence DPIAs before enforcement.",
        "deadline": date(2027, 5, 13),
        "section": "section_10",
    },
    {
        "title": "Privacy Notice Update Deadline",
        "description": "All existing privacy policies must be updated to DPDP-compliant format.",
        "deadline": date(2027, 5, 13),
        "section": "section_5",
    },
    {
        "title": "Vendor DPA Compliance",
        "description": "All data processor agreements must include DPDP-mandated clauses.",
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
                title="DPDP Full Enforcement in Less Than 90 Days",
                description=f"Only {days_to_enforcement} days until full DPDP enforcement on May 13, 2027. "
                           f"Penalties up to Rs 250 crore per violation.",
                action_required="Complete all compliance preparations immediately.",
            ))
        elif 0 < days_to_enforcement <= 180:
            alerts.append(ComplianceAlert(
                alert_type="deadline",
                severity="warning",
                title=f"DPDP Enforcement in {days_to_enforcement} Days",
                description="Full enforcement approaching. Ensure consent mechanisms, "
                           "privacy notices, breach plans, and DPAs are in place.",
                action_required="Run gap assessment and start remediation.",
            ))
        elif days_to_enforcement <= 0:
            alerts.append(ComplianceAlert(
                alert_type="deadline",
                severity="critical",
                title="DPDP Act Is Now Fully Enforceable",
                description="All provisions of the DPDP Act 2023 are now in effect. "
                           "Non-compliance may result in penalties.",
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
            description="Phase 1 (Board constitution) is effective. Phase 2 (consent managers) "
                       "takes effect Nov 2026. Phase 3 (full enforcement) takes effect May 2027.",
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
