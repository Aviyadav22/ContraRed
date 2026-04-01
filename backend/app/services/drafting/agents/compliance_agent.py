"""
Compliance Agent
================
Analyses a RawDraft for jurisdiction-specific enforceability,
data-protection compliance, and statutory requirements using Vertex AI.
"""

from __future__ import annotations

import json
import logging
from typing import List

from app.services.drafting.models import Annotation, RawDraft

logger = logging.getLogger(__name__)


class ComplianceAgent:
    """Reviews a draft contract for compliance issues."""

    async def review(
        self, draft: RawDraft, jurisdiction: str = "US-DE"
    ) -> List[Annotation]:
        """Return compliance-related annotations for *draft*."""
        return await self._ai_review(draft, jurisdiction)

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

        prompt = (
            "You are a regulatory compliance analyst. Review the following contract "
            f"sections for a {draft.contract_type} agreement.\n\n"
            f"Target jurisdiction: {jurisdiction}\n\n"
            f"Sections:\n{sections_text}\n\n"
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
            model = get_generative_model("gemini-2.5-flash")
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
