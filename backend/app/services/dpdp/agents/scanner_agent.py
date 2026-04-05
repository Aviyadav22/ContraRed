"""
DPDP Scanner Agent — Bulk contract scanning for DPDP compliance gaps.

Scans contracts against all 18 DPDP rules and produces per-contract
risk reports plus portfolio-level heatmaps.

Architecture: Hard rules (keyword/regex) first, then AI review via Vertex AI.
"""

import json
import logging
import re
from typing import Optional

from app.services.dpdp.models import (
    ContractScanRequest,
    ContractScanResult,
    ContractFinding,
    PortfolioReport,
    ComplianceStatus,
    DPDPSection,
)

logger = logging.getLogger(__name__)

# Map rule IDs to DPDP sections
_RULE_SECTION_MAP = {
    "dpdp_consent_mechanism": DPDPSection.SEC_6,
    "dpdp_data_principal_rights": DPDPSection.SEC_11,
    "dpdp_fiduciary_obligations": DPDPSection.SEC_8,
    "dpdp_breach_notification": DPDPSection.SEC_8,
    "dpdp_cross_border_transfer": DPDPSection.SEC_16,
    "dpdp_consent_manager": DPDPSection.SEC_9,
    "dpdp_processor_agreement": DPDPSection.SEC_8,
    "dpdp_childrens_data": DPDPSection.SEC_9,
    "dpdp_purpose_limitation": DPDPSection.SEC_6,
    "dpdp_data_retention": DPDPSection.SEC_8,
    "dpdp_significant_fiduciary": DPDPSection.SEC_10,
    "dpdp_penalty_indemnification": DPDPSection.SEC_8,
    # New rules (expanded to 18)
    "dpdp_notice_requirements": DPDPSection.SEC_5,
    "dpdp_lawful_purpose": DPDPSection.SEC_4,
    "dpdp_data_accuracy": DPDPSection.SEC_8,
    "dpdp_grievance_officer": DPDPSection.SEC_13,
    "dpdp_consent_withdrawal": DPDPSection.SEC_6,
    "dpdp_data_principal_duties": DPDPSection.SEC_15,
}

# Keyword patterns for deterministic pre-screening
_KEYWORD_PATTERNS = {
    "dpdp_consent_mechanism": [
        r"\bconsent\b", r"\bpersonal data\b", r"\bdata principal\b",
        r"\blawful basis\b", r"\bprocessing\b",
    ],
    "dpdp_breach_notification": [
        r"\bbreach\b", r"\bsecurity incident\b", r"\bdata breach\b",
        r"\bnotif(?:y|ication)\b",
    ],
    "dpdp_cross_border_transfer": [
        r"\bcross.?border\b", r"\bdata transfer\b", r"\boutside India\b",
        r"\binternational transfer\b", r"\bdata locali[sz]ation\b",
    ],
    "dpdp_processor_agreement": [
        r"\bdata process(?:or|ing)\b", r"\bsub.?process(?:or|ing)\b",
        r"\bon behalf of\b", r"\boutsourc\b",
    ],
    "dpdp_data_retention": [
        r"\bretention\b", r"\berasure\b", r"\bdelet(?:e|ion)\b",
        r"\bstorage limitation\b",
    ],
    "dpdp_childrens_data": [
        r"\bchild(?:ren)?\b", r"\bminor\b", r"\bparental consent\b",
        r"\bunder 18\b", r"\bage verif\b",
    ],
    "dpdp_data_principal_rights": [
        r"\bright to access\b", r"\bright to correction\b",
        r"\bright to erasure\b", r"\bgrievance\b", r"\bnominat\b",
    ],
    "dpdp_notice_requirements": [
        r"\bnotice\b", r"\bprivacy notice\b", r"\binform(?:ation|ed)\b",
        r"\btransparency\b",
    ],
    "dpdp_consent_withdrawal": [
        r"\bwithdraw(?:al)?\b", r"\brevok(?:e|ation)\b",
        r"\bopt.?out\b", r"\bease of withdrawal\b",
    ],
    "dpdp_grievance_officer": [
        r"\bgrievance officer\b", r"\bgrievance redressal\b",
        r"\bcomplaint\b", r"\bdata protection officer\b",
    ],
}

# Unacceptable signals that indicate non-compliance
_RED_FLAGS = {
    "dpdp_consent_mechanism": [
        "blanket consent", "deemed consent", "consent bundled",
        "by using this service you agree", "implied consent",
    ],
    "dpdp_cross_border_transfer": [
        "unrestricted transfer", "data may be stored anywhere",
        "transfer to any country", "no restrictions on transfer",
    ],
    "dpdp_data_retention": [
        "indefinite retention", "perpetual storage", "data kept forever",
        "no retention period", "retained indefinitely",
    ],
    "dpdp_breach_notification": [
        "no obligation to notify", "notification at discretion",
        "may choose to notify", "no breach notification",
    ],
    "dpdp_data_principal_rights": [
        "waiver of rights", "no right to access", "rights at discretion",
        "no obligation to respond",
    ],
}


class ScannerAgent:
    """Scans contracts for DPDP Act compliance gaps using hybrid detection."""

    async def scan_contract(
        self,
        request: ContractScanRequest,
        rules: list[dict],
    ) -> ContractScanResult:
        """Scan a single contract against DPDP rules.

        Stage 1: Deterministic keyword/regex scan (zero latency)
        Stage 2: AI review via Vertex AI (best-effort)
        """
        text_lower = request.contract_text.lower()
        findings: list[ContractFinding] = []

        # Stage 1: Hard rules — keyword and red flag detection
        hard_findings = self._run_hard_rules(request.contract_text, text_lower, rules)
        findings.extend(hard_findings)

        # Stage 2: AI review — deeper semantic analysis
        try:
            ai_findings = await self._ai_scan(request, rules)
            # Deduplicate: skip AI findings that match existing hard rule findings
            existing_rules = {f.rule_id for f in findings}
            for f in ai_findings:
                if f.rule_id not in existing_rules:
                    findings.append(f)
        except Exception as exc:
            logger.error("AI scan failed for %s: %s", request.contract_name, exc)

        # Calculate scores
        red = sum(1 for f in findings if f.risk_level == "RED")
        yellow = sum(1 for f in findings if f.risk_level == "YELLOW")
        green = sum(1 for f in findings if f.risk_level == "GREEN")
        deal_breakers = sum(1 for f in findings if f.is_deal_breaker)

        total_rules = len(rules) if rules else 18
        compliant = total_rules - red - yellow
        score = max(0, (compliant * 100) / total_rules) if total_rules > 0 else 0

        return ContractScanResult(
            contract_name=request.contract_name or "Untitled",
            contract_type=request.contract_type,
            total_findings=len(findings),
            red_findings=red,
            yellow_findings=yellow,
            green_findings=green,
            deal_breakers=deal_breakers,
            compliance_score=round(score, 1),
            findings=findings,
        )

    def _run_hard_rules(
        self,
        text: str,
        text_lower: str,
        rules: list[dict],
    ) -> list[ContractFinding]:
        """Deterministic keyword/regex-based scanning."""
        findings: list[ContractFinding] = []

        for rule in rules:
            rule_id = rule.get("clause_type", "")
            patterns = rule.get("detection_patterns", [])
            risk_level = rule.get("risk_level", "YELLOW")
            is_deal_breaker = rule.get("is_deal_breaker", False)

            # Check if any detection patterns are present
            pattern_found = False
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    pattern_found = True
                    break

            # Check for red flags (unacceptable signals)
            red_flags_found = []
            for signal in rule.get("unacceptable_signals", []):
                if signal.lower() in text_lower:
                    red_flags_found.append(signal)

            # Check for green flags (acceptable signals)
            green_flags = []
            for signal in rule.get("acceptable_signals", []):
                if signal.lower() in text_lower:
                    green_flags.append(signal)

            # Decision logic
            if red_flags_found:
                findings.append(ContractFinding(
                    rule_id=rule_id,
                    section=_RULE_SECTION_MAP.get(rule_id, DPDPSection.SEC_8),
                    risk_level="RED",
                    is_deal_breaker=is_deal_breaker,
                    title=rule.get("risk_description", f"DPDP non-compliance: {rule_id}"),
                    description=f"Contract contains non-compliant language: {', '.join(red_flags_found)}. "
                               f"Required: {rule.get('primary_position', '')}",
                    suggested_fix=rule.get("fallback_position", ""),
                    confidence=0.85,
                ))
            elif not pattern_found and not green_flags:
                # Topic not even mentioned — likely a gap
                findings.append(ContractFinding(
                    rule_id=rule_id,
                    section=_RULE_SECTION_MAP.get(rule_id, DPDPSection.SEC_8),
                    risk_level=risk_level,
                    is_deal_breaker=is_deal_breaker,
                    title=rule.get("risk_description", f"DPDP gap: {rule_id}"),
                    description=f"Contract does not address this DPDP requirement. "
                               f"Required: {rule.get('primary_position', '')}",
                    suggested_fix=rule.get("acceptable_position", ""),
                    confidence=0.6,
                ))
            elif pattern_found and not green_flags:
                # Topic mentioned but no compliant language found
                findings.append(ContractFinding(
                    rule_id=rule_id,
                    section=_RULE_SECTION_MAP.get(rule_id, DPDPSection.SEC_8),
                    risk_level="YELLOW",
                    is_deal_breaker=False,
                    title=f"Partial coverage: {rule.get('risk_description', rule_id)}",
                    description=f"Contract mentions this topic but may not fully comply. "
                               f"Ideal: {rule.get('acceptable_position', '')}",
                    suggested_fix=rule.get("fallback_position", ""),
                    confidence=0.5,
                ))

        return findings

    async def _ai_scan(
        self,
        request: ContractScanRequest,
        rules: list[dict],
    ) -> list[ContractFinding]:
        """AI-powered deep semantic scan via Vertex AI."""
        try:
            from app.core.vertex_client import get_generative_model, is_available
        except ImportError:
            return []

        if not is_available():
            return []

        from app.core.config import settings

        # Build rule summaries for the prompt
        rule_summaries = []
        for r in rules[:18]:  # Cap at 18 rules for prompt length
            rule_summaries.append(
                f"- {r['clause_type']}: {r.get('primary_position', '')[:200]}"
            )
        rules_text = "\n".join(rule_summaries)

        # Truncate contract text to avoid token limits
        contract_excerpt = request.contract_text[:15000]

        prompt = f"""You are a DPDP Act 2023 compliance expert. Analyze this contract for compliance with India's Digital Personal Data Protection Act 2023.

CONTRACT TYPE: {request.contract_type}
JURISDICTION: {request.jurisdiction}

CONTRACT TEXT:
{contract_excerpt}

DPDP RULES TO CHECK:
{rules_text}

For each rule that is violated or partially addressed, return a JSON array of findings:
[
  {{
    "rule_id": "dpdp_consent_mechanism",
    "risk_level": "RED",
    "is_deal_breaker": true,
    "title": "Missing consent mechanism",
    "description": "Detailed explanation of the gap",
    "clause_text": "Exact quote from contract if available",
    "suggested_fix": "Recommended compliant language",
    "confidence": 0.9
  }}
]

Only include rules that have actual issues. If a rule is fully compliant, skip it.
Return ONLY the JSON array, no other text."""

        try:
            model = get_generative_model(settings.GEMINI_SCOUT_MODEL)
            from google.genai.types import GenerateContentConfig

            response = await model.generate_content_async(
                [{"role": "user", "parts": [{"text": prompt}]}],
                generation_config=GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4000,
                    response_mime_type="application/json",
                ),
            )

            raw = response.text or "[]"
            items = json.loads(raw)
            return [
                ContractFinding(
                    rule_id=item.get("rule_id", "unknown"),
                    section=_RULE_SECTION_MAP.get(
                        item.get("rule_id", ""), DPDPSection.SEC_8
                    ),
                    risk_level=item.get("risk_level", "YELLOW"),
                    is_deal_breaker=item.get("is_deal_breaker", False),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    clause_text=item.get("clause_text", ""),
                    suggested_fix=item.get("suggested_fix", ""),
                    confidence=min(1.0, max(0.0, item.get("confidence", 0.7))),
                )
                for item in items
                if isinstance(item, dict) and item.get("rule_id")
            ]
        except Exception as exc:
            logger.error("AI scan parse error: %s", exc)
            return []

    async def scan_portfolio(
        self,
        contracts: list[ContractScanRequest],
        rules: list[dict],
    ) -> PortfolioReport:
        """Scan multiple contracts and generate portfolio-level report."""
        import asyncio

        results: list[ContractScanResult] = []

        # Process contracts concurrently (max 10 at a time)
        semaphore = asyncio.Semaphore(10)

        async def _scan_one(req: ContractScanRequest) -> ContractScanResult:
            async with semaphore:
                return await self.scan_contract(req, rules)

        tasks = [_scan_one(c) for c in contracts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, ContractScanResult)]

        # Build portfolio report
        total = len(valid_results)
        avg_score = (
            sum(r.compliance_score for r in valid_results) / total
            if total > 0
            else 0
        )
        deal_breaker_contracts = sum(
            1 for r in valid_results if r.deal_breakers > 0
        )

        # Risk heatmap: count findings per rule
        heatmap: dict[str, int] = {}
        for r in valid_results:
            for f in r.findings:
                heatmap[f.rule_id] = heatmap.get(f.rule_id, 0) + 1

        # Section coverage
        section_coverage: dict[str, ComplianceStatus] = {}
        for section in DPDPSection:
            section_findings = [
                f
                for r in valid_results
                for f in r.findings
                if f.section == section
            ]
            if not section_findings:
                section_coverage[section.value] = ComplianceStatus.COMPLIANT
            elif any(f.risk_level == "RED" for f in section_findings):
                section_coverage[section.value] = ComplianceStatus.NON_COMPLIANT
            else:
                section_coverage[section.value] = ComplianceStatus.PARTIAL

        # Top risks
        top_risks = sorted(heatmap.items(), key=lambda x: x[1], reverse=True)[:5]

        return PortfolioReport(
            total_contracts=total,
            average_compliance_score=round(avg_score, 1),
            contracts_with_deal_breakers=deal_breaker_contracts,
            risk_heatmap=heatmap,
            section_coverage=section_coverage,
            top_risks=[f"{r[0]} ({r[1]} contracts)" for r in top_risks],
            contract_results=valid_results,
        )
