"""
ContraRed Agent Toolkit.

Provides a structured tool interface for AI agents to interact with
ContraRed's analysis capabilities. Each method wraps existing services
in an agent-friendly format.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRisk
from app.services.analysis_pipeline import analysis_pipeline, PipelineResult
from app.services.compliance_layer_service import (
    get_layer_rules_as_dicts,
    merge_rules,
    calculate_compliance_score,
)
from app.services.playbook_cache import get_cached_rules_dicts, load_default_playbook_for_type

logger = logging.getLogger(__name__)


class ContraRedToolkit:
    """Agent-friendly wrapper around ContraRed analysis services."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_document(
        self,
        text: str,
        playbook_id: Optional[str] = None,
        party_side: str = "buyer",
        compliance_layers: Optional[List[str]] = None,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a full contract document.

        Returns structured results with findings, risk summary, and compliance scores.
        """
        # Load playbook rules
        playbook_rules = []
        playbook_name = "Default"
        if playbook_id:
            rules = await get_cached_rules_dicts(self.db, UUID(playbook_id))
            if rules:
                playbook_rules = rules
        if not playbook_rules:
            default = await load_default_playbook_for_type(self.db, "msa")
            if default:
                playbook_rules = default.get("rules", [])
                playbook_name = default.get("name", "Default")

        # Merge compliance layer rules
        compliance_scores = {}
        if compliance_layers:
            for code in compliance_layers:
                layer_rules = await get_layer_rules_as_dicts(self.db, code)
                if layer_rules:
                    playbook_rules = merge_rules(playbook_rules, layer_rules)

        # Run pipeline
        result: PipelineResult = await analysis_pipeline.run(
            contract_text=text,
            playbook_rules=playbook_rules,
            playbook_name=playbook_name,
            party_side=party_side,
            jurisdiction_override=jurisdiction,
        )

        # Compute compliance scores
        if compliance_layers:
            for code in compliance_layers:
                layer_results = [
                    {"risk_level": r.risk_level}
                    for r in result.redlines
                ]
                compliance_scores[code] = calculate_compliance_score(layer_results)

        return {
            "findings": [
                {
                    "id": r.id,
                    "risk_level": r.risk_level,
                    "rule_name": r.rule_name,
                    "clause_text": r.clause_text[:200],
                    "explanation": r.explanation,
                    "fix": r.suggested_fix,
                    "clause_type": r.clause_type,
                }
                for r in result.redlines
            ],
            "risk_summary": {
                "red": sum(1 for r in result.redlines if r.risk_level == "RED"),
                "yellow": sum(1 for r in result.redlines if r.risk_level == "YELLOW"),
                "green": sum(1 for r in result.redlines if r.risk_level == "GREEN"),
                "total": len(result.redlines),
            },
            "compliance_scores": compliance_scores,
            "jurisdiction": result.jurisdiction_detected,
            "contract_type": result.contract_type_detected,
            "partial": result.partial,
        }

    async def analyze_clause(
        self,
        clause_text: str,
        clause_type: Optional[str] = None,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a single contract clause.

        Wraps the full pipeline but for a single clause excerpt.
        """
        result = await self.analyze_document(
            text=clause_text,
            jurisdiction=jurisdiction,
        )
        findings = result.get("findings", [])
        if clause_type:
            findings = [f for f in findings if f.get("clause_type") == clause_type]
        return {
            "clause_text": clause_text[:200],
            "findings": findings,
            "risk_level": findings[0]["risk_level"] if findings else "GREEN",
        }

    async def check_compliance(
        self,
        text: str,
        layer_codes: List[str],
    ) -> Dict[str, Any]:
        """Check contract against specific compliance layers.

        Returns compliance scores for each layer.
        """
        result = await self.analyze_document(
            text=text,
            compliance_layers=layer_codes,
        )
        return {
            "compliance_scores": result["compliance_scores"],
            "findings_count": result["risk_summary"]["total"],
            "deal_breakers": [
                f for f in result["findings"]
                if f["risk_level"] == "RED"
            ],
        }

    async def get_risk_summary(
        self,
        document_id: UUID,
    ) -> Dict[str, Any]:
        """Get risk summary for a previously analyzed document."""
        result = await self.db.execute(
            select(DocumentRisk).where(DocumentRisk.document_id == document_id)
        )
        risks = result.scalars().all()

        if not risks:
            return {"error": "No risks found for document", "document_id": str(document_id)}

        return {
            "document_id": str(document_id),
            "total_risks": len(risks),
            "red": sum(1 for r in risks if r.risk_level and r.risk_level.value == "RED"),
            "yellow": sum(1 for r in risks if r.risk_level and r.risk_level.value == "YELLOW"),
            "green": sum(1 for r in risks if r.risk_level and r.risk_level.value == "GREEN"),
            "risks": [
                {
                    "clause_type": r.clause_type,
                    "risk_level": r.risk_level.value if r.risk_level else "UNKNOWN",
                    "description": r.description,
                }
                for r in risks[:20]  # Limit to 20 for agent context
            ],
        }

    async def compare_versions(
        self,
        text_a: str,
        text_b: str,
        label_a: str = "Version A",
        label_b: str = "Version B",
    ) -> Dict[str, Any]:
        """Compare two contract versions and highlight risk differences."""
        result_a = await self.analyze_document(text=text_a)
        result_b = await self.analyze_document(text=text_b)

        findings_a = {f["clause_type"]: f for f in result_a["findings"]}
        findings_b = {f["clause_type"]: f for f in result_b["findings"]}

        all_types = set(findings_a.keys()) | set(findings_b.keys())

        changes = []
        for ct in sorted(all_types):
            a = findings_a.get(ct)
            b = findings_b.get(ct)
            if a and b:
                if a["risk_level"] != b["risk_level"]:
                    changes.append({
                        "clause_type": ct,
                        "change": "risk_changed",
                        "from": a["risk_level"],
                        "to": b["risk_level"],
                    })
            elif a and not b:
                changes.append({"clause_type": ct, "change": "removed_in_b", "risk_level": a["risk_level"]})
            elif b and not a:
                changes.append({"clause_type": ct, "change": "added_in_b", "risk_level": b["risk_level"]})

        return {
            "label_a": label_a,
            "label_b": label_b,
            "summary_a": result_a["risk_summary"],
            "summary_b": result_b["risk_summary"],
            "changes": changes,
            "total_changes": len(changes),
        }
