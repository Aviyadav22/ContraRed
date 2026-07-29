"""
Compliance Agent
================
Analyses a RawDraft for jurisdiction-specific enforceability,
data-protection compliance, and statutory requirements using Vertex AI.
"""

from __future__ import annotations

import json
import logging
import re
from typing import List

from app.services.drafting.compliance_rules import ComplianceRuleEngine
from app.services.drafting.models import Annotation, RawDraft
from app.services.prompt_sanitizer import sanitize_for_prompt

logger = logging.getLogger(__name__)


class ComplianceAgent:
    """Reviews a draft contract for compliance issues."""

    def __init__(self) -> None:
        self._rule_engine = ComplianceRuleEngine()

    async def review(
        self, draft: RawDraft, jurisdiction: str = "US-DE"
    ) -> List[Annotation]:
        """Return compliance-related annotations for *draft*.

        Hard rules run first (deterministic, zero-latency).
        AI review runs second (best-effort, may be unavailable).
        """
        rule_annotations = self._run_hard_rules(draft)

        try:
            from app.core.vertex_client import is_available
        except ImportError:
            is_available = lambda: False  # noqa: E731

        ai_annotations = (
            await self._ai_review(draft, jurisdiction) if is_available() else []
        )
        return rule_annotations + ai_annotations

    # ------------------------------------------------------------------ #
    # Deterministic hard-rule checks
    # ------------------------------------------------------------------ #

    def _run_hard_rules(self, draft: RawDraft) -> List[Annotation]:
        """Run deterministic compliance rules against the draft."""
        annotations: List[Annotation] = []

        # --- Efforts standard consistency across all sections ---
        clause_texts = [s.content for s in draft.sections]
        efforts_findings = self._rule_engine.check_efforts_consistency(clause_texts)
        for finding in efforts_findings:
            severity = "warning"
            if finding.startswith("CRITICAL"):
                severity = "critical"
            elif finding.startswith("INFO"):
                severity = "info"
            annotations.append(
                Annotation(
                    section_number="ALL",
                    agent="compliance",
                    severity=severity,
                    issue="Mixed efforts standards found. (Note: Style enforcer will normalize these automatically.)",
                    reasoning=finding,
                )
            )

        # --- Liability cap check ---
        all_text = " ".join(s.content for s in draft.sections)
        if "limitation of liability" in all_text.lower():
            cap_match = re.search(
                r'(\d+)\s*(?:months?|x)\s*(?:of\s+)?(?:fees?|amounts?)',
                all_text,
                re.IGNORECASE,
            )
            if cap_match:
                cap_months = int(cap_match.group(1))
                cap_findings = self._rule_engine.check_liability_cap(
                    cap_months=cap_months
                )
                for f in cap_findings:
                    annotations.append(
                        Annotation(
                            section_number="*",
                            agent="compliance",
                            severity="warning",
                            issue=f,
                            reasoning="Deterministic liability cap check",
                        )
                    )

        return annotations

    async def _ai_review(
        self, draft: RawDraft, jurisdiction: str
    ) -> List[Annotation]:
        """Send sections to Vertex AI for compliance analysis.

        Returns an empty list if AI is unavailable.
        """
        try:
            from app.core.vertex_client import get_generative_model, is_available
            from google.genai.types import GenerateContentConfig
        except ImportError:
            logger.warning("Vertex AI SDK not available — compliance review skipped")
            return []

        if not is_available():
            logger.warning("Vertex AI not configured — compliance review skipped")
            return []

        sections_text = "\n\n".join(
            f"Section {s.number} – {s.heading} (clause: {s.clause_type}):\n{s.content}"
            for s in draft.sections
        )

        safe_contract_type = sanitize_for_prompt(draft.contract_type, max_length=200)
        safe_jurisdiction = sanitize_for_prompt(jurisdiction, max_length=200)
        safe_sections = sanitize_for_prompt(sections_text, max_length=20000)

        prompt = (
            "You are a regulatory compliance analyst. Review the following contract "
            f"sections for a {safe_contract_type} agreement.\n\n"
            f"Target jurisdiction: {safe_jurisdiction}\n\n"
            f"Sections:\n{safe_sections}\n\n"
            "Check for:\n"
            "1. Jurisdiction-specific enforceability issues\n"
            "2. Data protection compliance (GDPR, CCPA, DPDP Act, etc.)\n"
            "3. Statutory requirements that may be missing\n"
            "4. Regulatory references that should be included\n\n"
            "For each issue found, return a JSON array of objects with keys:\n"
            '  "section_number" (string), "severity" ("critical"|"warning"|"info"),\n'
            '  "issue" (short description), "reasoning" (detailed explanation),\n'
            '  "suggested_fix" (optional improvement).\n\n'
            "If no issues, return an empty array: []"
        )

        try:
            from app.core.config import settings
            model = get_generative_model(settings.GEMINI_MODEL)
            response = await model.generate_content_async(
                [{"role": "user", "parts": [{"text": prompt}]}],
                generation_config=GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=4000,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text or "[]"
            items = json.loads(raw)
            return [
                Annotation(
                    section_number=item["section_number"],
                    agent="compliance",
                    severity=item.get("severity", "info"),
                    issue=item["issue"],
                    reasoning=item.get("reasoning", ""),
                    suggested_fix=item.get("suggested_fix"),
                )
                for item in items
            ]
        except Exception as exc:
            logger.error("Compliance agent AI review failed: %s", exc)
            return []
