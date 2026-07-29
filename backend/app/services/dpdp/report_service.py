"""
Compliance Report Service - Generate audit-ready compliance reports.

Aggregates data from scanner results, gap assessments, consent health,
and knowledge base citations into structured reports that lawyers can
use for compliance audits and board presentations.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_result import ComplianceScanResult, ComplianceAssessment, ComplianceReport
from app.services.dpdp.consent_compliance_bridge import consent_compliance_bridge
from app.services.dpdp.knowledge_base import dpdp_knowledge_base

logger = logging.getLogger(__name__)


class ComplianceReportService:
    """Generate and persist comprehensive DPDP compliance reports."""

    async def generate_full_report(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive DPDP compliance report.

        Aggregates:
        - Latest scan results (contract compliance)
        - Latest gap assessment (organizational compliance)
        - Consent health metrics
        - DPDP deadline status
        - Penalty exposure analysis
        - Remediation roadmap
        """
        now = datetime.now(timezone.utc)

        # 1. Get latest scan results
        scan_summary = await self._get_scan_summary(db, organization_id)

        # 2. Get latest assessment
        assessment_summary = await self._get_assessment_summary(db, organization_id)

        # 3. Get consent health
        consent_health = await consent_compliance_bridge.get_consent_health(db, organization_id)

        # 4. Calculate overall compliance score
        overall_score = self._calculate_overall_score(
            scan_summary.get("avg_score", 0),
            assessment_summary.get("score", 0),
            consent_health.get("health_score", 0),
        )

        # 5. Get deadlines and penalties from knowledge base
        deadlines = dpdp_knowledge_base.get_all_deadlines()
        penalties = dpdp_knowledge_base.get_penalty_summary()

        # 6. Build risk analysis
        risk_analysis = self._build_risk_analysis(scan_summary, assessment_summary)

        # 7. Build remediation roadmap
        roadmap = self._build_remediation_roadmap(assessment_summary, scan_summary, consent_health)

        report_content = {
            "metadata": {
                "report_type": "full",
                "generated_at": now.isoformat(),
                "organization_id": str(organization_id) if organization_id else None,
                "dpdp_enforcement_deadline": "2027-05-13",
                "report_version": "1.0",
            },
            "executive_summary": {
                "overall_compliance_score": overall_score,
                "status": "Compliant" if overall_score >= 80 else "Partial" if overall_score >= 50 else "Non-Compliant",
                "contracts_scanned": scan_summary.get("total_scans", 0),
                "assessment_score": assessment_summary.get("score", 0),
                "consent_health_score": consent_health.get("health_score", 0),
                "key_risks": risk_analysis.get("top_risks", [])[:3],
                "days_to_enforcement": max(0, (datetime(2027, 5, 13, tzinfo=timezone.utc) - now).days),
            },
            "contract_compliance": scan_summary,
            "organizational_compliance": assessment_summary,
            "consent_management": {
                "health_score": consent_health.get("health_score", 0),
                "active_consents": consent_health.get("active_consents", 0),
                "consent_rate": consent_health.get("consent_rate", 0),
                "purpose_coverage": consent_health.get("purpose_stats", []),
                "recent_activity": consent_health.get("recent_events", {}),
                "privacy_policy_version": consent_health.get("privacy_policy_version"),
            },
            "risk_analysis": risk_analysis,
            "regulatory_deadlines": deadlines,
            "penalty_exposure": penalties,
            "remediation_roadmap": roadmap,
            "regulatory_citations": self._get_key_citations(),
        }

        # Generate executive summary text
        summary_text = self._generate_summary_text(report_content)

        # Persist the report
        report = ComplianceReport(
            organization_id=organization_id,
            user_id=user_id,
            report_type="full",
            title=f"DPDP Compliance Report - {now.strftime('%B %Y')}",
            content=report_content,
            summary=summary_text,
            compliance_score=overall_score,
            generated_at=now,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        return {
            "report_id": str(report.id),
            "title": report.title,
            "summary": summary_text,
            "compliance_score": overall_score,
            "content": report_content,
            "generated_at": now.isoformat(),
        }

    async def get_report_history(
        self, db: AsyncSession, organization_id: Optional[uuid.UUID] = None, limit: int = 10
    ) -> List[Dict]:
        """Get previous compliance reports."""
        query = select(ComplianceReport).order_by(desc(ComplianceReport.generated_at)).limit(limit)
        if organization_id:
            query = query.where(ComplianceReport.organization_id == organization_id)
        result = await db.execute(query)
        reports = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "summary": r.summary,
                "compliance_score": r.compliance_score,
                "report_type": r.report_type,
                "generated_at": r.generated_at.isoformat(),
            }
            for r in reports
        ]

    async def get_compliance_trend(
        self, db: AsyncSession, organization_id: Optional[uuid.UUID] = None, days: int = 90
    ) -> List[Dict]:
        """Get compliance score trend from stored scan results."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        # Use scan results for trend data
        query = (
            select(
                func.date_trunc('week', ComplianceScanResult.scanned_at).label('week'),
                func.avg(ComplianceScanResult.compliance_score).label('avg_score'),
                func.count(ComplianceScanResult.id).label('scan_count'),
            )
            .where(ComplianceScanResult.scanned_at >= cutoff)
            .group_by('week')
            .order_by('week')
            .limit(13)  # ~3 months of weekly data
        )
        if organization_id:
            query = query.where(ComplianceScanResult.organization_id == organization_id)

        try:
            result = await db.execute(query)
            rows = result.all()
            return [
                {
                    "week": row.week.isoformat() if row.week else None,
                    "avg_score": round(float(row.avg_score), 1) if row.avg_score else 0,
                    "scan_count": row.scan_count,
                }
                for row in rows
            ]
        except Exception as e:
            logger.debug("Trend query failed (table may not exist yet): %s", e)
            return []

    # ---- Private helpers ----

    async def _get_scan_summary(self, db: AsyncSession, organization_id=None) -> Dict:
        """Aggregate scan results for report."""
        query = select(ComplianceScanResult)
        if organization_id:
            query = query.where(ComplianceScanResult.organization_id == organization_id)
        query = query.order_by(desc(ComplianceScanResult.scanned_at)).limit(50)

        try:
            result = await db.execute(query)
            scans = result.scalars().all()
        except Exception:
            scans = []

        if not scans:
            return {"total_scans": 0, "avg_score": 0, "findings_summary": {}}

        avg_score = sum(s.compliance_score for s in scans) / len(scans)
        total_red = sum(s.red_count for s in scans)
        total_yellow = sum(s.yellow_count for s in scans)
        total_deal_breakers = sum(s.deal_breaker_count for s in scans)

        return {
            "total_scans": len(scans),
            "avg_score": round(avg_score, 1),
            "total_findings": sum(s.total_findings for s in scans),
            "red_findings": total_red,
            "yellow_findings": total_yellow,
            "deal_breakers": total_deal_breakers,
            "latest_scan": scans[0].scanned_at.isoformat() if scans else None,
        }

    async def _get_assessment_summary(self, db: AsyncSession, organization_id=None) -> Dict:
        """Get latest assessment for report."""
        query = select(ComplianceAssessment)
        if organization_id:
            query = query.where(ComplianceAssessment.organization_id == organization_id)
        query = query.order_by(desc(ComplianceAssessment.assessed_at)).limit(1)

        try:
            result = await db.execute(query)
            assessment = result.scalar()
        except Exception:
            assessment = None

        if not assessment:
            return {"score": 0, "status": "not_assessed", "critical_gaps": []}

        return {
            "score": assessment.overall_score,
            "status": assessment.overall_status,
            "section_scores": assessment.section_scores or [],
            "critical_gaps": assessment.critical_gaps or [],
            "action_items": assessment.action_items or [],
            "effort": assessment.estimated_remediation_effort,
            "assessed_at": assessment.assessed_at.isoformat(),
        }

    def _calculate_overall_score(self, scan_score, assessment_score, consent_score) -> int:
        """Weighted overall compliance score.

        Weights: Assessment 40% (org-level), Scan 35% (contract-level), Consent 25%
        """
        weights = []
        if assessment_score > 0:
            weights.append((assessment_score, 0.4))
        if scan_score > 0:
            weights.append((scan_score, 0.35))
        if consent_score > 0:
            weights.append((consent_score, 0.25))

        if not weights:
            return 0

        total_weight = sum(w for _, w in weights)
        weighted_sum = sum(s * w for s, w in weights)
        return round(weighted_sum / total_weight)

    def _build_risk_analysis(self, scan_summary, assessment_summary) -> Dict:
        """Build risk analysis section."""
        top_risks = []

        if scan_summary.get("deal_breakers", 0) > 0:
            top_risks.append({
                "severity": "CRITICAL",
                "area": "Contract Compliance",
                "description": f"{scan_summary['deal_breakers']} deal-breaker clauses found across {scan_summary['total_scans']} scanned contracts",
                "citation": "DPDP Act Sections 5, 6, 8",
            })

        for gap in assessment_summary.get("critical_gaps", [])[:5]:
            top_risks.append({
                "severity": "HIGH",
                "area": "Organizational Compliance",
                "description": str(gap) if isinstance(gap, str) else gap.get("description", "Critical gap identified"),
            })

        return {
            "top_risks": top_risks,
            "total_red_findings": scan_summary.get("red_findings", 0),
            "total_deal_breakers": scan_summary.get("deal_breakers", 0),
            "critical_gaps_count": len(assessment_summary.get("critical_gaps", [])),
        }

    def _build_remediation_roadmap(self, assessment, scan, consent) -> List[Dict]:
        """Build prioritized remediation roadmap."""
        roadmap = []

        # Phase 1: Critical (0-30 days)
        if assessment.get("critical_gaps"):
            roadmap.append({
                "phase": 1,
                "timeline": "0-30 days",
                "priority": "CRITICAL",
                "title": "Address Critical Compliance Gaps",
                "items": [str(g) if isinstance(g, str) else g.get("description", "") for g in assessment["critical_gaps"][:5]],
            })

        # Phase 2: High priority (30-90 days)
        high_items = []
        if scan.get("deal_breakers", 0) > 0:
            high_items.append(f"Remediate {scan['deal_breakers']} deal-breaker contract clauses")
        if consent.get("health_score", 100) < 60:
            high_items.append("Improve consent health score (currently below 60%)")
        if high_items:
            roadmap.append({
                "phase": 2,
                "timeline": "30-90 days",
                "priority": "HIGH",
                "title": "Contract and Consent Remediation",
                "items": high_items,
            })

        # Phase 3: Medium (90-180 days)
        roadmap.append({
            "phase": 3,
            "timeline": "90-180 days",
            "priority": "MEDIUM",
            "title": "Operational Excellence",
            "items": assessment.get("action_items", ["Implement continuous compliance monitoring"])[:5],
        })

        return roadmap

    def _get_key_citations(self) -> List[Dict]:
        """Get key DPDP citations for the report."""
        key_sections = ["5", "6", "8", "9", "10", "11", "16", "Rule 3", "Rule 6", "Rule 7"]
        citations = []
        for num in key_sections:
            section = dpdp_knowledge_base.get_section(num)
            if section:
                citations.append({
                    "source": section.source,
                    "section": section.section_number,
                    "title": section.title,
                    "summary": section.summary,
                    "penalty": section.penalties,
                })
        return citations

    def _generate_summary_text(self, report: Dict) -> str:
        """Generate executive summary text."""
        exec_summary = report["executive_summary"]
        score = exec_summary["overall_compliance_score"]
        status = exec_summary["status"]
        days = exec_summary["days_to_enforcement"]
        scans = exec_summary["contracts_scanned"]

        lines = [
            f"Overall DPDP Compliance Score: {score}/100 ({status})",
            f"Days to full DPDP enforcement: {days}",
            f"Contracts scanned: {scans}",
            f"Assessment score: {exec_summary['assessment_score']}/100",
            f"Consent health: {exec_summary['consent_health_score']}/100",
        ]

        risks = exec_summary.get("key_risks", [])
        if risks:
            lines.append(f"Top risks: {len(risks)} critical/high findings requiring attention")

        return "\n".join(lines)


# Singleton
compliance_report_service = ComplianceReportService()
