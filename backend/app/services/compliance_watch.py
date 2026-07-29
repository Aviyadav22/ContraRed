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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRisk
from app.services.compliance_layer_service import (
    get_layer_rules_as_dicts,
    calculate_compliance_score,
)

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
        # Source contract bodies are intentionally not retained. This endpoint
        # can identify reassessment candidates, but it cannot truthfully claim
        # that those contracts were re-scanned.
        report.total_documents_scanned = 0

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

            layer_rules = await get_layer_rules_as_dicts(self.db, compliance_layer_code)
            if layer_rules:
                old_by_type = {
                    risk.clause_type: risk for risk in old_risks
                    if risk.clause_type
                }
                old_layer_results = []
                for rule in layer_rules:
                    old_risk = old_by_type.get(rule.get("clause_type"))
                    old_layer_results.append({
                        "status": "violation" if old_risk else "unassessed",
                        "risk_level": (
                            old_risk.risk_level.value.upper()
                            if old_risk and old_risk.risk_level else ""
                        ),
                        "is_deal_breaker": bool(
                            rule.get("is_deal_breaker")
                        ),
                    })
                doc_delta.old_score = calculate_compliance_score(
                    old_layer_results
                )
                deltas = self._compute_rule_deltas(old_risks, layer_rules)
                doc_delta.deltas = deltas
                doc_delta.newly_non_compliant = False

            if doc_delta.deltas:
                report.document_deltas.append(doc_delta)

        report.newly_non_compliant_count = sum(
            1 for d in report.document_deltas if d.newly_non_compliant
        )

        report.summary = self._build_summary(report, len(documents))
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
        """List rules that require a real source-text reassessment."""
        deltas: List[ComplianceDelta] = []
        old_types = {risk.clause_type for risk in old_risks if risk.clause_type}
        for rule in new_layer_rules:
            clause_type = rule.get("clause_type", "")
            deltas.append(ComplianceDelta(
                clause_type=clause_type,
                old_risk_level=(
                    "finding_recorded" if clause_type in old_types else None
                ),
                new_risk_level="UNASSESSED",
                change="reassessment_required",
                explanation=(
                    "Supply the source contract and assess it against the "
                    "current rule before assigning compliance status."
                ),
            ))

        return deltas

    def _build_summary(
        self,
        report: ComplianceWatchReport,
        documents_considered: Optional[int] = None,
    ) -> str:
        """Build human-readable summary of compliance watch results."""
        if documents_considered is None:
            documents_considered = report.total_documents_scanned
        parts = [
            f"Compliance Watch: {report.compliance_layer_code}.",
            f"Identified {documents_considered} document(s) for reassessment.",
            "No contract bodies were re-scanned because source text is not "
            "retained; no new non-compliance determination has been made.",
        ]
        return " ".join(parts)
