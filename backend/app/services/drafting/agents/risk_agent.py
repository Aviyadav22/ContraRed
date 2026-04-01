"""
Risk Agent
==========
Analyses a RawDraft for risk-posture alignment issues using Vertex AI.
"""

from __future__ import annotations

import json
import logging
from typing import List

from app.services.drafting.models import Annotation, RawDraft
from app.services.prompt_sanitizer import sanitize_for_prompt

logger = logging.getLogger(__name__)


class RiskAgent:
    """Reviews a draft contract for risk alignment issues."""

    async def review(
        self, draft: RawDraft, risk_appetite: str = "balanced"
    ) -> List[Annotation]:
        """Return risk-related annotations for *draft*."""
        annotations = await self._ai_review(draft, risk_appetite)
        if not annotations:
            annotations.append(Annotation(
                section_number="*",
                agent="risk",
                severity="info",
                issue="Risk review was not performed (AI unavailable). Manual risk review recommended.",
                reasoning="Vertex AI was not available for automated risk assessment.",
            ))
        return annotations

    async def _ai_review(
        self, draft: RawDraft, risk_appetite: str
    ) -> List[Annotation]:
        """Send sections to Vertex AI for risk analysis.

        Returns an empty list if AI is unavailable.
        """
        try:
            from app.core.vertex_client import get_generative_model, is_available
            from google.genai.types import GenerateContentConfig
        except ImportError:
            logger.warning("Vertex AI SDK not available — risk review skipped")
            return []

        if not is_available():
            logger.warning("Vertex AI not configured — risk review skipped")
            return []

        sections_text = "\n\n".join(
            f"Section {s.number} – {s.heading} (tier: {s.tier_used}):\n{s.content}"
            for s in draft.sections
        )

        safe_contract_type = sanitize_for_prompt(draft.contract_type, max_length=200)
        safe_risk_appetite = sanitize_for_prompt(risk_appetite, max_length=200)
        safe_sections = sanitize_for_prompt(sections_text, max_length=20000)

        prompt = (
            "You are a contract risk analyst. Review the following contract sections "
            f"for a {safe_contract_type} agreement.\n\n"
            f"Risk appetite: {safe_risk_appetite}\n\n"
            f"Sections:\n{safe_sections}\n\n"
            "For each risk issue found, return a JSON array of objects with keys:\n"
            '  "section_number" (string), "severity" ("critical"|"warning"|"info"),\n'
            '  "issue" (short description), "reasoning" (why this is a risk),\n'
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
                    agent="risk",
                    severity=item.get("severity", "warning"),
                    issue=item["issue"],
                    reasoning=item.get("reasoning", ""),
                    suggested_fix=item.get("suggested_fix"),
                )
                for item in items
            ]
        except Exception as exc:
            logger.error("Risk agent AI review failed: %s", exc)
            return []
