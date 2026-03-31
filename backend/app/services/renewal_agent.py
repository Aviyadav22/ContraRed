"""
Renewal Intelligence Agent.

Scans for contracts approaching expiry and generates renewal briefs
with risk re-assessment against the organization's current risk profile.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRisk

logger = logging.getLogger(__name__)


@dataclass
class RenewalBrief:
    """A renewal brief for an expiring contract."""
    document_id: str
    document_name: str
    expiry_date: Optional[str] = None
    days_until_expiry: Optional[int] = None
    risk_summary: Dict[str, int] = field(default_factory=dict)
    top_risks: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class RenewalReport:
    """Full renewal intelligence report."""
    org_id: str
    days_ahead: int
    generated_at: str = ""
    total_expiring: int = 0
    briefs: List[RenewalBrief] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "org_id": self.org_id,
            "days_ahead": self.days_ahead,
            "generated_at": self.generated_at,
            "total_expiring": self.total_expiring,
            "briefs": [
                {
                    "document_id": b.document_id,
                    "document_name": b.document_name,
                    "expiry_date": b.expiry_date,
                    "days_until_expiry": b.days_until_expiry,
                    "risk_summary": b.risk_summary,
                    "top_risks": b.top_risks,
                    "recommendations": b.recommendations,
                }
                for b in self.briefs
            ],
            "summary": self.summary,
        }


class RenewalAgent:
    """Agent that identifies expiring contracts and generates renewal briefs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan_expiring_contracts(
        self,
        org_id: UUID,
        days_ahead: int = 90,
    ) -> RenewalReport:
        """Find contracts expiring within days_ahead and generate briefs.

        Since contract expiry dates may be stored as document metadata,
        we check the document's metadata JSON field for expiry_date.
        Falls back to creation-date-based heuristic for demo purposes.
        """
        report = RenewalReport(
            org_id=str(org_id),
            days_ahead=days_ahead,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Get all org documents
        result = await self.db.execute(
            select(Document).where(
                Document.organization_id == org_id
            ).order_by(Document.created_at.desc()).limit(100)
        )
        documents = list(result.scalars().all())

        if not documents:
            report.summary = "No documents found for organization."
            return report

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)

        for doc in documents:
            expiry_date = self._extract_expiry_date(doc)
            if expiry_date and expiry_date <= cutoff:
                brief = await self.generate_renewal_brief(doc, expiry_date, now)
                report.briefs.append(brief)

        report.total_expiring = len(report.briefs)
        report.summary = self._build_summary(report)
        return report

    async def generate_renewal_brief(
        self,
        document: Document,
        expiry_date: datetime,
        now: datetime,
    ) -> RenewalBrief:
        """Generate a renewal brief for a single document."""
        days_remaining = (expiry_date - now).days

        brief = RenewalBrief(
            document_id=str(document.id),
            document_name=document.filename or str(document.id),
            expiry_date=expiry_date.isoformat(),
            days_until_expiry=days_remaining,
        )

        # Get existing risk data
        result = await self.db.execute(
            select(DocumentRisk).where(DocumentRisk.document_id == document.id)
        )
        risks = list(result.scalars().all())

        if risks:
            brief.risk_summary = {
                "red": sum(1 for r in risks if r.risk_level and r.risk_level.value == "RED"),
                "yellow": sum(1 for r in risks if r.risk_level and r.risk_level.value == "YELLOW"),
                "green": sum(1 for r in risks if r.risk_level and r.risk_level.value == "GREEN"),
                "total": len(risks),
            }

            # Top risks (deal-breakers first)
            sorted_risks = sorted(
                risks,
                key=lambda r: (
                    0 if (r.risk_level and r.risk_level.value == "RED") else 1,
                    0 if (r.risk_level and r.risk_level.value == "YELLOW") else 1,
                ),
            )
            brief.top_risks = [
                {
                    "clause_type": r.clause_type or "",
                    "risk_level": r.risk_level.value if r.risk_level else "UNKNOWN",
                    "description": r.description or "",
                }
                for r in sorted_risks[:5]
            ]

        # Generate recommendations
        brief.recommendations = self._generate_recommendations(brief, days_remaining)
        return brief

    def _extract_expiry_date(self, document: Document) -> Optional[datetime]:
        """Extract expiry date from document metadata.

        Checks metadata JSON for 'expiry_date', 'expiration_date', or
        'term_end_date' fields.
        """
        metadata = getattr(document, "metadata_", None) or {}
        if isinstance(metadata, dict):
            for key in ("expiry_date", "expiration_date", "term_end_date"):
                val = metadata.get(key)
                if val:
                    try:
                        if isinstance(val, str):
                            return datetime.fromisoformat(val.replace("Z", "+00:00"))
                        elif isinstance(val, datetime):
                            return val
                    except (ValueError, TypeError):
                        continue
        return None

    def _generate_recommendations(self, brief: RenewalBrief, days_remaining: int) -> List[str]:
        """Generate renewal recommendations based on risk profile."""
        recs = []

        if days_remaining <= 30:
            recs.append("URGENT: Contract expires within 30 days. Initiate renewal immediately.")
        elif days_remaining <= 60:
            recs.append("Contract expires within 60 days. Begin renewal discussions.")
        else:
            recs.append("Contract approaching expiry. Schedule renewal review.")

        red_count = brief.risk_summary.get("red", 0)
        yellow_count = brief.risk_summary.get("yellow", 0)

        if red_count > 0:
            recs.append(f"Address {red_count} deal-breaker(s) before renewal.")
        if yellow_count > 0:
            recs.append(f"Review {yellow_count} medium-risk finding(s) for renegotiation.")
        if red_count == 0 and yellow_count == 0:
            recs.append("Low risk profile — consider auto-renewal if terms are acceptable.")

        return recs

    def _build_summary(self, report: RenewalReport) -> str:
        """Build human-readable summary."""
        if report.total_expiring == 0:
            return f"No contracts expiring within {report.days_ahead} days."

        urgent = sum(1 for b in report.briefs if (b.days_until_expiry or 999) <= 30)
        parts = [f"{report.total_expiring} contract(s) expiring within {report.days_ahead} days."]
        if urgent:
            parts.append(f"{urgent} require(s) immediate attention (≤30 days).")
        return " ".join(parts)
