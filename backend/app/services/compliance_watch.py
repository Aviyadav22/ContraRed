"""
Compliance Watch Agent.

Monitors compliance layer changes and re-scans affected documents
to produce delta reports showing newly non-compliant contracts.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRisk
from app.services.analysis_pipeline import analysis_pipeline, PipelineResult
from app.services.compliance_layer_service import (
    get_layer_rules_as_dicts,
    merge_rules,
    calculate_compliance_score,
)
from app.services.playbook_cache import load_default_playbook_for_type

logger = logging.getLogger(__name__)


@dataclass
class ComplianceDelta:
    """A single change in compliance status for a finding."""
    clause_type: str
    old_risk_level: Optional[str]
    new_risk_level: str
    change: str  # "new_risk", "risk_increased", "risk_decreased", "resolved"
    explanation: str = ""


@dataclass
class DocumentDelta:
    """Compliance changes for a single document."""
    document_id: str
    document_name: str
    old_score: Optional[Dict[str, Any]] = None
    new_score: Optional[Dict[str, Any]] = None
    deltas: List[ComplianceDelta] = field(default_factory=list)
    newly_non_compliant: bool = False


@dataclass
class ComplianceWatchReport:
    """Full compliance watch report."""
    compliance_layer_code: str
    triggered_at: str = ""
    total_documents_scanned: int = 0
    newly_non_compliant_count: int = 0
    document_deltas: List[DocumentDelta] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compliance_layer_code": self.compliance_layer_code,
            "triggered_at": self.triggered_at,
            "total_documents_scanned": self.total_documents_scanned,
            "newly_non_compliant_count": self.newly_non_compliant_count,
            "document_deltas": [
                {
                    "document_id": d.document_id,
                    "document_name": d.document_name,
                    "old_score": d.old_score,
                    "new_score": d.new_score,
                    "deltas": [
                        {
                            "clause_type": delta.clause_type,
                            "old_risk_level": delta.old_risk_level,
                            "new_risk_level": delta.new_risk_level,
                            "change": delta.change,
                            "explanation": delta.explanation,
                        }
                        for delta in d.deltas
                    ],
                    "newly_non_compliant": d.newly_non_compliant,
                }
                for d in self.document_deltas
            ],
            "summary": self.summary,
        }


class ComplianceWatchAgent:
    """Agent that monitors compliance layer changes and re-scans documents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_affected_documents(
        self,
        org_id: UUID,
        layer_code: Optional[str] = None,
    ) -> List[Document]:
        """Find documents that used a specific compliance layer.

        For now, returns all documents for the organization since we
        don't track which layers were used per document in the DB yet.
        """
        query = select(Document).where(
            Document.organization_id == org_id
        ).order_by(Document.created_at.desc()).limit(50)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def trigger_rescan(
        self,
        compliance_layer_code: str,
        org_id: UUID,
    ) -> ComplianceWatchReport:
        """Re-scan affected documents against updated compliance layer.

        Returns a delta report showing newly non-compliant contracts.
        """
        report = ComplianceWatchReport(
            compliance_layer_code=compliance_layer_code,
            triggered_at=datetime.now(timezone.utc).isoformat(),
        )

        # Find affected documents
        documents = await self.find_affected_documents(org_id, compliance_layer_code)
        report.total_documents_scanned = len(documents)

        if not documents:
            report.summary = "No documents found for organization."
            return report

        # Get old risk data for each document
        for doc in documents:
            old_risks = await self._get_existing_risks(doc.id)
            doc_delta = DocumentDelta(
                document_id=str(doc.id),
                document_name=doc.filename or str(doc.id),
            )

            # Get old compliance score from existing risks
            if old_risks:
                old_layer_results = [
                    {"risk_level": r.risk_level.value if r.risk_level else "GREEN"}
                    for r in old_risks
                ]
                doc_delta.old_score = calculate_compliance_score(old_layer_results)

            # Compute deltas between old and new risk profile
            # (Full re-scan requires document text which may not be stored;
            #  for now, compare existing risks against updated layer rules)
            layer_rules = await get_layer_rules_as_dicts(self.db, compliance_layer_code)
            if layer_rules:
                deltas = self._compute_rule_deltas(old_risks, layer_rules)
                doc_delta.deltas = deltas
                doc_delta.newly_non_compliant = any(
                    d.change in ("new_risk", "risk_increased") for d in deltas
                )

            if doc_delta.deltas:
                report.document_deltas.append(doc_delta)

        report.newly_non_compliant_count = sum(
            1 for d in report.document_deltas if d.newly_non_compliant
        )

        report.summary = self._build_summary(report)
        return report

    async def _get_existing_risks(self, document_id: UUID) -> List[DocumentRisk]:
        """Get existing risk records for a document."""
        result = await self.db.execute(
            select(DocumentRisk).where(DocumentRisk.document_id == document_id)
        )
        return list(result.scalars().all())

    def _compute_rule_deltas(
        self,
        old_risks: List[DocumentRisk],
        new_layer_rules: List[Dict[str, Any]],
    ) -> List[ComplianceDelta]:
        """Compare old risks against new compliance layer rules."""
        deltas = []
        old_by_type = {}
        for r in old_risks:
            if r.clause_type:
                old_by_type[r.clause_type] = r.risk_level.value if r.risk_level else "GREEN"

        risk_order = {"RED": 3, "YELLOW": 2, "GREEN": 1}

        for rule in new_layer_rules:
            clause_type = rule.get("clause_type", "")
            new_risk = rule.get("risk_level", "GREEN")
            old_risk = old_by_type.get(clause_type)

            if old_risk is None:
                # New rule — not previously assessed
                if new_risk in ("RED", "YELLOW"):
                    deltas.append(ComplianceDelta(
                        clause_type=clause_type,
                        old_risk_level=None,
                        new_risk_level=new_risk,
                        change="new_risk",
                        explanation=f"New compliance rule: {rule.get('rule_name', clause_type)}",
                    ))
            elif risk_order.get(new_risk, 0) > risk_order.get(old_risk, 0):
                deltas.append(ComplianceDelta(
                    clause_type=clause_type,
                    old_risk_level=old_risk,
                    new_risk_level=new_risk,
                    change="risk_increased",
                    explanation=f"Risk increased from {old_risk} to {new_risk}",
                ))
            elif risk_order.get(new_risk, 0) < risk_order.get(old_risk, 0):
                deltas.append(ComplianceDelta(
                    clause_type=clause_type,
                    old_risk_level=old_risk,
                    new_risk_level=new_risk,
                    change="risk_decreased",
                    explanation=f"Risk decreased from {old_risk} to {new_risk}",
                ))

        return deltas

    def _build_summary(self, report: ComplianceWatchReport) -> str:
        """Build human-readable summary of compliance watch results."""
        parts = [
            f"Compliance Watch: {report.compliance_layer_code}.",
            f"Scanned {report.total_documents_scanned} document(s).",
        ]
        if report.newly_non_compliant_count > 0:
            parts.append(
                f"{report.newly_non_compliant_count} document(s) newly non-compliant."
            )
        else:
            parts.append("No new compliance issues detected.")
        return " ".join(parts)
