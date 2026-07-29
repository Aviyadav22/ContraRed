"""
Contract Review Agent.

Orchestrates a full contract review using ContraRedToolkit:
1. Detect jurisdiction
2. Select appropriate playbook
3. Enable relevant compliance layers
4. Run analysis
5. Prioritize findings
6. Generate fixes for deal-breakers

Returns a structured ReviewResult.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_tools import ContraRedToolkit
from app.services.jurisdiction_detector import jurisdiction_detector

logger = logging.getLogger(__name__)


@dataclass
class ReviewFinding:
    """A prioritized finding from the review."""
    id: str
    risk_level: str
    clause_type: str
    rule_name: str
    explanation: str
    rule_id: Optional[str] = None
    clause_text: str = ""
    fix: Optional[str] = None
    is_deal_breaker: bool = False
    confidence: Optional[float] = None
    verification_status: Optional[str] = None
    priority: int = 0  # 1=highest


@dataclass
class ReviewResult:
    """Structured result from a full contract review."""
    jurisdiction: Optional[str] = None
    contract_type: Optional[str] = None
    review_perspective: Optional[str] = None
    total_findings: int = 0
    deal_breakers: List[ReviewFinding] = field(default_factory=list)
    high_risk: List[ReviewFinding] = field(default_factory=list)
    medium_risk: List[ReviewFinding] = field(default_factory=list)
    low_risk: List[ReviewFinding] = field(default_factory=list)
    compliance_scores: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    partial: bool = False
    ai_used: bool = True
    playbook_coverage: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jurisdiction": self.jurisdiction,
            "contract_type": self.contract_type,
            "review_perspective": self.review_perspective,
            "total_findings": self.total_findings,
            "deal_breakers": [_finding_dict(f) for f in self.deal_breakers],
            "high_risk": [_finding_dict(f) for f in self.high_risk],
            "medium_risk": [_finding_dict(f) for f in self.medium_risk],
            "low_risk": [_finding_dict(f) for f in self.low_risk],
            "compliance_scores": self.compliance_scores,
            "summary": self.summary,
            "partial": self.partial,
            "ai_used": self.ai_used,
            "playbook_coverage": self.playbook_coverage,
        }


def _finding_dict(f: ReviewFinding) -> Dict[str, Any]:
    return {
        "id": f.id,
        "rule_id": f.rule_id,
        "risk_level": f.risk_level,
        "clause_type": f.clause_type,
        "rule_name": f.rule_name,
        "clause_text": f.clause_text,
        "explanation": f.explanation,
        "fix": f.fix,
        "is_deal_breaker": f.is_deal_breaker,
        "confidence": f.confidence,
        "verification_status": f.verification_status,
        "priority": f.priority,
    }


class ReviewAgent:
    """AI-powered contract review agent.

    Orchestrates the full review workflow using ContraRedToolkit.
    """

    def __init__(
        self,
        db: AsyncSession,
        current_user_id=None,
        current_user_org_id=None,
    ):
        self.db = db
        self.toolkit = ContraRedToolkit(
            db,
            current_user_id=current_user_id,
            current_user_org_id=current_user_org_id,
        )

    async def review(
        self,
        text: str,
        instructions: Optional[str] = None,
        playbook_id: Optional[str] = None,
        compliance_layers: Optional[List[str]] = None,
        jurisdiction: Optional[str] = None,
        party_side: Optional[str] = None,
    ) -> ReviewResult:
        """Run a full contract review.

        Args:
            text: Contract text.
            instructions: Natural language instructions (e.g. "focus on IP risks").
            playbook_id: Specific playbook to use (optional).
            compliance_layers: Compliance layer codes (optional).
            jurisdiction: Jurisdiction override (optional).

        Returns:
            ReviewResult with prioritized findings and fixes.
        """
        # Step 1: Detect jurisdiction if not provided
        if not jurisdiction:
            jur_result = jurisdiction_detector.detect(text)
            jurisdiction = jur_result.detected_jurisdiction

        # Step 2: Auto-select compliance layers based on jurisdiction
        if compliance_layers is None:
            compliance_layers = self._suggest_compliance_layers(jurisdiction)

        # Step 3: Run full analysis
        analysis = await self.toolkit.analyze_document(
            text=text,
            playbook_id=playbook_id,
            compliance_layers=compliance_layers,
            jurisdiction=jurisdiction,
            party_side=party_side,
        )

        # Step 4: Prioritize findings. Natural-language focus instructions may
        # reorder the review, but never hide unrelated deal-breakers or risks.
        findings = analysis.get("findings", [])
        deal_breakers = []
        high_risk = []
        medium_risk = []
        low_risk = []

        focus_types = (
            set(self._parse_focus_from_instructions(instructions))
            if instructions else set()
        )
        risk_rank = {"RED": 0, "YELLOW": 1, "GREEN": 2}
        ordered_findings = sorted(
            findings,
            key=lambda finding: (
                0 if finding.get("is_deal_breaker") else 1,
                0 if finding.get("clause_type") in focus_types else 1,
                risk_rank.get(finding.get("risk_level"), 3),
                -(finding.get("confidence") or 0),
            ),
        )

        priority = 1
        for f in ordered_findings:
            rf = ReviewFinding(
                id=f["id"],
                rule_id=f.get("rule_id"),
                risk_level=f["risk_level"],
                clause_type=f.get("clause_type", ""),
                rule_name=f.get("rule_name", ""),
                clause_text=f.get("clause_text", ""),
                explanation=f.get("explanation", ""),
                fix=f.get("fix"),
                is_deal_breaker=bool(f.get("is_deal_breaker")),
                confidence=f.get("confidence"),
                verification_status=f.get("verification_status"),
                priority=priority,
            )
            if f["risk_level"] == "RED" and rf.is_deal_breaker:
                deal_breakers.append(rf)
            elif f["risk_level"] == "RED":
                high_risk.append(rf)
            elif f["risk_level"] == "YELLOW":
                medium_risk.append(rf)
            else:
                low_risk.append(rf)
            priority += 1

        # Step 5: Build summary
        summary = self._build_summary(
            jurisdiction=jurisdiction,
            contract_type=analysis.get("contract_type"),
            risk_summary=analysis.get("risk_summary", {}),
            compliance_scores=analysis.get("compliance_scores", {}),
            deal_breaker_count=len(deal_breakers),
        )

        return ReviewResult(
            jurisdiction=jurisdiction,
            contract_type=analysis.get("contract_type"),
            review_perspective=analysis.get("review_perspective"),
            total_findings=len(findings),
            deal_breakers=deal_breakers,
            high_risk=high_risk,
            medium_risk=medium_risk,
            low_risk=low_risk,
            compliance_scores=analysis.get("compliance_scores", {}),
            summary=summary,
            partial=analysis.get("partial", False),
            ai_used=analysis.get("ai_used", True),
            playbook_coverage=analysis.get("playbook_coverage"),
        )

    def _suggest_compliance_layers(self, jurisdiction: Optional[str]) -> List[str]:
        """Suggest compliance layers based on detected jurisdiction."""
        if not jurisdiction:
            return []
        suggestions = {
            "IN": ["dpdp"],
        }
        return suggestions.get(jurisdiction, [])

    def _parse_focus_from_instructions(self, instructions: str) -> List[str]:
        """Extract clause types to focus on from natural language instructions."""
        focus_map = {
            "ip": ["ip_ownership", "ip_assignment", "work_for_hire"],
            "intellectual property": ["ip_ownership", "ip_assignment", "work_for_hire"],
            "data": ["data_protection", "data_protection_dpdp", "data_retention", "cross_border_transfer"],
            "privacy": ["data_protection", "data_protection_dpdp", "sensitive_personal_data"],
            "liability": ["limitation_of_liability", "unlimited_liability", "indemnification"],
            "non-compete": ["non_compete", "customer_non_solicitation"],
            "termination": ["termination", "termination_for_convenience"],
        }
        lower = instructions.lower()
        focus = set()
        for keyword, types in focus_map.items():
            if keyword in lower:
                focus.update(types)
        return list(focus)

    def _build_summary(
        self,
        jurisdiction: Optional[str],
        contract_type: Optional[str],
        risk_summary: Dict,
        compliance_scores: Dict,
        deal_breaker_count: int = 0,
    ) -> str:
        """Build a human-readable review summary."""
        parts = []
        if contract_type:
            parts.append(f"Contract type: {contract_type}.")
        if jurisdiction:
            parts.append(f"Jurisdiction: {jurisdiction}.")

        red = risk_summary.get("red", 0)
        yellow = risk_summary.get("yellow", 0)
        total = risk_summary.get("total", 0)

        if red > 0:
            parts.append(f"{red} high-risk finding(s) require immediate attention.")
        if deal_breaker_count:
            parts.append(
                f"{deal_breaker_count} finding(s) are marked as playbook deal-breakers."
            )
        if yellow > 0:
            parts.append(f"{yellow} medium-risk finding(s) to review.")
        if total == 0:
            parts.append("No significant risks detected.")

        for code, score in compliance_scores.items():
            if isinstance(score, dict):
                s = score.get("score", 0)
                parts.append(f"{code.upper()} compliance: {s}%.")

        return " ".join(parts)
