"""
ContraRed Agent Toolkit.

Provides a structured tool interface for AI agents to interact with
ContraRed's analysis capabilities. Each method wraps existing services
in an agent-friendly format.
"""

import logging
import hashlib
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentRisk
from app.services.analysis_pipeline import AnalysisPipeline, analysis_pipeline, PipelineResult
from app.services.compliance_layer_service import (
    build_compliance_layer_score,
    get_layer_rules_as_dicts,
    merge_rules,
)
from app.services.playbook_cache import (
    get_cached_rules_dicts,
    load_default_playbook_for_type,
    load_playbook,
)

logger = logging.getLogger(__name__)


class ContraRedToolkit:
    """Agent-friendly wrapper around ContraRed analysis services."""

    def __init__(
        self,
        db: AsyncSession,
        current_user_id: Optional[UUID] = None,
        current_user_org_id: Optional[UUID] = None,
    ):
        self.db = db
        self.current_user_id = current_user_id
        self.current_user_org_id = current_user_org_id

    async def analyze_document(
        self,
        text: str,
        playbook_id: Optional[str] = None,
        party_side: Optional[str] = None,
        compliance_layers: Optional[List[str]] = None,
        jurisdiction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a full contract document.

        Returns structured results with findings, risk summary, and compliance scores.
        """
        # Load playbook rules
        playbook_rules = []
        playbook_name = "Default"
        selected_playbook = None
        if playbook_id:
            try:
                playbook_uuid = UUID(playbook_id)
            except ValueError as exc:
                raise ValueError("Invalid playbook_id format.") from exc
            selected_playbook = await load_playbook(
                self.db,
                playbook_uuid,
                current_user_id=self.current_user_id,
                current_user_org_id=self.current_user_org_id,
            )
            if selected_playbook is None:
                raise PermissionError(
                    "Selected playbook was not found or is not accessible."
                )
            playbook_rules = get_cached_rules_dicts(
                selected_playbook,
                include_verification=True,
            )
            if not playbook_rules:
                raise ValueError("Selected playbook has no active rules.")
            playbook_name = selected_playbook.name
        else:
            detected_type = AnalysisPipeline._detect_contract_type(text)
            selected_playbook = await load_default_playbook_for_type(
                self.db,
                detected_type,
            )
            if selected_playbook:
                playbook_rules = get_cached_rules_dicts(
                    selected_playbook,
                    include_verification=True,
                )
                playbook_name = f"{selected_playbook.name} (auto-selected)"

        effective_party_side = (
            party_side
            or (
                selected_playbook.party_side
                if selected_playbook is not None
                else None
            )
            or "neutral"
        )

        # Merge compliance layer rules
        compliance_scores = {}
        loaded_compliance_layers = set()
        if compliance_layers:
            for code in compliance_layers:
                layer_rules = await get_layer_rules_as_dicts(self.db, code)
                if layer_rules:
                    playbook_rules = merge_rules(playbook_rules, layer_rules)
                    loaded_compliance_layers.add(code)

        # Run pipeline
        result: PipelineResult = await analysis_pipeline.run(
            contract_text=text,
            playbook_rules=playbook_rules,
            playbook_name=playbook_name,
            party_side=effective_party_side,
            jurisdiction_override=jurisdiction,
        )

        # Compute compliance scores
        for code in loaded_compliance_layers:
            compliance_scores[code] = build_compliance_layer_score(
                code,
                playbook_rules,
                result,
            )

        return {
            "findings": [
                {
                    "id": (
                        r.rule_id
                        or hashlib.sha256(
                            f"{r.rule_name}\0{r.verified_text or r.original_text}".encode()
                        ).hexdigest()[:24]
                    ),
                    "rule_id": r.rule_id or None,
                    "risk_level": r.risk_level,
                    "rule_name": r.rule_name,
                    "clause_text": r.verified_text or r.original_text,
                    "explanation": r.explanation,
                    "fix": r.suggested_fix,
                    "clause_type": r.clause_type,
                    "is_deal_breaker": r.is_deal_breaker,
                    "confidence": r.confidence.score,
                    "verification_status": r.verification_status,
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
            "jurisdiction": result.jurisdiction_code,
            "contract_type": result.contract_type,
            "review_perspective": effective_party_side,
            "partial": result.partial,
            "ai_used": result.ai_used,
            "playbook_coverage": result.playbook_coverage,
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
