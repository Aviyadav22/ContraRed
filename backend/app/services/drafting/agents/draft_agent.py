"""
Draft Agent
===========
Transforms a DraftRequest + drafting playbook into a full contract document
(RawDraft) clause-by-clause.  Each clause is selected at the appropriate
negotiation tier, placeholders are filled, and (optionally) refined via
Vertex AI for natural language polish.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.prompt_sanitizer import sanitize_for_prompt

from app.services.drafting.models import (
    DraftMetadata,
    DraftRequest,
    DraftSection,
    RawDraft,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Title map
# ---------------------------------------------------------------------------

_TITLE_MAP: Dict[str, str] = {
    "nda_mutual": "MUTUAL NON-DISCLOSURE AGREEMENT",
    "nda_unilateral": "NON-DISCLOSURE AGREEMENT",
    "saas": "SAAS SUBSCRIPTION AGREEMENT",
    "msa": "MASTER SERVICE AGREEMENT",
    "employment": "EMPLOYMENT AGREEMENT",
}

# ---------------------------------------------------------------------------
# Tier selection matrix
# ---------------------------------------------------------------------------

_TIER_MATRIX: Dict[tuple[str, str], str] = {
    ("party_1", "protective"): "preferred",
    ("party_1", "balanced"): "acceptable",
    ("party_1", "commercial"): "fallback",
    ("party_2", "protective"): "preferred",
    ("party_2", "balanced"): "acceptable",
    ("party_2", "commercial"): "fallback",
    ("party_1", "aggressive"): "fallback",
    ("party_2", "aggressive"): "fallback",
}


class DraftAgent:
    """Core drafting agent — builds a RawDraft from a request and playbook."""

    # ------------------------------------------------------------------
    # Tier selection
    # ------------------------------------------------------------------

    @staticmethod
    def _select_tier(
        perspective: str,
        risk_appetite: str,
        clause_category: str | None = None,
        risk_profile: dict[str, str] | None = None,
    ) -> str:
        """Map (perspective, risk_appetite) to a playbook tier name.

        Per-clause override via *risk_profile* takes priority when the
        clause_category is present in the profile.  Otherwise falls back
        to the global perspective/risk_appetite matrix.
        """
        # Per-clause override takes priority
        if risk_profile and clause_category and clause_category in risk_profile:
            override = risk_profile[clause_category].lower()
            return {
                "protective": "preferred",
                "balanced": "acceptable",
                "commercial": "fallback",
                "aggressive": "fallback",
            }.get(override, "acceptable")

        # Global fallback (existing logic)
        if perspective == "balanced":
            return "acceptable"
        return _TIER_MATRIX.get((perspective, risk_appetite), "acceptable")

    # ------------------------------------------------------------------
    # Placeholder building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_placeholders(req: DraftRequest) -> Dict[str, str]:
        """Extract all template variables from a DraftRequest."""
        eff_date = (
            req.effective_date.isoformat()
            if req.effective_date
            else date.today().isoformat()
        )

        p: Dict[str, str] = {
            # Party 1
            "party_1_name": req.party_1.name,
            "party_1_short_name": req.party_1.name.split()[0],
            "party_1_entity_type": req.party_1.entity_type,
            "party_1_jurisdiction": req.party_1.jurisdiction,
            "party_1_address": req.party_1.address or "[Address]",
            # Party 2
            "party_2_name": req.party_2.name,
            "party_2_short_name": req.party_2.name.split()[0],
            "party_2_entity_type": req.party_2.entity_type,
            "party_2_jurisdiction": req.party_2.jurisdiction,
            "party_2_address": req.party_2.address or "[Address]",
            # Dates / terms
            "effective_date": eff_date,
            "term_months": str(req.term_months),
            "governing_law": req.governing_law,
            "dispute_resolution": req.dispute_resolution,
            "venue": req.venue or req.governing_law,
        }

        # Unilateral NDA aliases (party_1 = disclosing, party_2 = receiving)
        p["disclosing_party_name"] = req.party_1.name
        p["disclosing_party_short_name"] = req.party_1.name.split()[0]
        p["receiving_party_name"] = req.party_2.name
        p["receiving_party_short_name"] = req.party_2.name.split()[0]

        # SaaS-style aliases (party_1 = provider, party_2 = customer)
        p["provider_name"] = req.party_1.name
        p["provider_short_name"] = req.party_1.name.split()[0]
        p["provider_entity_type"] = req.party_1.entity_type
        p["provider_jurisdiction"] = req.party_1.jurisdiction
        p["provider_address"] = req.party_1.address or "[Address]"
        p["customer_name"] = req.party_2.name
        p["customer_short_name"] = req.party_2.name.split()[0]
        p["customer_entity_type"] = req.party_2.entity_type
        p["customer_jurisdiction"] = req.party_2.jurisdiction
        p["customer_address"] = req.party_2.address or "[Address]"

        # MSA-style aliases (party_1 = service provider, party_2 = client)
        p["service_provider_name"] = req.party_1.name
        p["client_name"] = req.party_2.name

        # Employment-style aliases (party_1 = company, party_2 = employee)
        p["company_name"] = req.party_1.name
        p["employee_name"] = req.party_2.name

        # Default for all contract types (NDA block may override below)
        p["confidentiality_survival_years"] = "3"

        # Employment-specific
        if req.contract_type == "employment":
            p["employee_title"] = req.employee_title or "[Title]"
            p["base_salary"] = req.base_salary or "[Amount]"
            p["reporting_manager"] = req.reporting_manager or "[Manager]"
            p["work_location"] = req.work_location or "[Location]"
            p["bonus_target_pct"] = "[X]"
            p["bonus_min_pct"] = "[Y]"
            p["pto_days"] = "20"
            p["equity_grant"] = "[shares/options]"
            p["travel_days_per_month"] = "5"
            p["professional_dev_budget"] = "$5,000"

        # NDA-specific
        if req.nda_details:
            nda = req.nda_details
            p["purpose"] = nda.purpose
            p["confidentiality_survival_years"] = str(
                nda.confidentiality_survival_years
            )
            p["non_solicitation_months"] = str(nda.non_solicitation_months or 12)
            # CI categories clause
            if nda.ci_categories:
                p["ci_categories_clause"] = ", ".join(nda.ci_categories)
            else:
                p["ci_categories_clause"] = (
                    "technical data, trade secrets, business plans, financial "
                    "information, and other proprietary information"
                )

        # SaaS-specific
        if req.saas_details:
            saas = req.saas_details
            p["service_description"] = saas.service_description
            p["pricing_model"] = saas.pricing_model
            p["price_amount"] = f"{saas.price_amount:,.2f}"
            p["billing_frequency"] = saas.billing_frequency
            p["uptime_commitment"] = (
                f"{saas.uptime_commitment}%" if saas.uptime_commitment else "99.9%"
            )
            p["authorized_users"] = str(saas.authorized_users or "unlimited")
            p["auto_renewal_text"] = (
                "automatically renew for successive periods of equal length"
                if saas.auto_renewal
                else "expire at the end of the Initial Term unless renewed in writing"
            )
            freq_multiplier = {"monthly": 12, "quarterly": 4, "annual": 1}.get(
                getattr(req.saas_details, 'billing_frequency', 'monthly') if req.saas_details else 'monthly', 12
            )
            p["annual_value"] = f"{saas.price_amount * freq_multiplier:,.2f}"

        return p

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _fill_placeholders(template: str, placeholders: Dict[str, str]) -> str:
        """Replace ``{{key}}`` tokens with values from *placeholders*."""

        def _replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            return placeholders.get(key, match.group(0))

        return re.sub(r"\{\{(\s*\w+\s*)\}\}", _replacer, template)

    # ------------------------------------------------------------------
    # Conditional inclusion
    # ------------------------------------------------------------------

    @staticmethod
    def _should_include(clause: Dict[str, Any], req: DraftRequest) -> bool:
        """Decide whether a clause should appear in the draft.

        A clause is included if:
        - ``is_required`` is True, OR
        - ``conditional_on`` evaluates to True against the request.

        Supported expression format: ``dotted.path == value``
        """
        if clause.get("is_required", True):
            return True

        condition = clause.get("conditional_on")
        if not condition:
            return True

        # Parse "field.path == value"
        match = re.match(r"([\w.]+)\s*==\s*(.+)", condition.strip())
        if not match:
            return True

        path_str, expected_raw = match.group(1), match.group(2).strip()

        # Resolve dotted path on req
        obj: Any = req
        for part in path_str.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return False

        # Normalise expected value
        if expected_raw.lower() == "true":
            return bool(obj) is True
        if expected_raw.lower() == "false":
            return bool(obj) is False

        return str(obj) == expected_raw

    # ------------------------------------------------------------------
    # AI adaptation (optional polish)
    # ------------------------------------------------------------------

    async def _ai_adapt_clause(
        self,
        text: str,
        guidance: str,
        jurisdiction_variant: Optional[str] = None,
    ) -> str:
        """Refine clause text via Vertex AI without changing legal substance.

        Falls back to returning the template text verbatim if AI is
        unavailable or errors.
        """
        try:
            from app.core.vertex_client import get_generative_model, is_available

            if not is_available():
                return text

            from app.core.config import settings
            model = get_generative_model(settings.GEMINI_MODEL)

            prompt = (
                "You are a contract drafting assistant. Refine the following "
                "contract clause for natural language flow and professional tone. "
                "Do NOT change the legal substance, defined terms, or placeholder "
                "tokens (anything in {{curly braces}}). Return ONLY the refined "
                "clause text, nothing else.\n\n"
            )
            if guidance:
                prompt += f"Drafting guidance: {sanitize_for_prompt(guidance, max_length=2000)}\n\n"
            if jurisdiction_variant:
                prompt += f"Jurisdiction note: {sanitize_for_prompt(jurisdiction_variant, max_length=500)}\n\n"
            prompt += f"Clause:\n{sanitize_for_prompt(text, max_length=10000)}"

            response = await model.generate_content_async(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": 2048},
            )
            result = response.text.strip() if hasattr(response, "text") else text
            return result if result else text

        except Exception:
            logger.debug("AI adaptation unavailable, using template text", exc_info=True)
            return text

    # ------------------------------------------------------------------
    # Main generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        req: DraftRequest,
        playbook: Dict[str, Any],
    ) -> RawDraft:
        """Build a full RawDraft from *req* using *playbook* clause templates."""
        start = time.monotonic()

        global_tier = self._select_tier(req.drafting_perspective, req.risk_appetite)
        placeholders = self._build_placeholders(req)

        sections: List[DraftSection] = []
        defined_terms: Dict[str, str] = {}
        tokens_used = 0

        clause_list: List[Dict[str, Any]] = playbook.get("clauses", [])
        section_order: List[str] = playbook.get("section_order", [])

        # Sort clauses by position
        sorted_clauses = sorted(
            clause_list, key=lambda c: c.get("position_in_order", 0)
        )

        for idx, clause in enumerate(sorted_clauses):
            if not self._should_include(clause, req):
                continue

            # Per-clause risk calibration
            clause_category = clause.get("category", clause.get("clause_type"))
            tier_name = self._select_tier(
                req.drafting_perspective,
                req.risk_appetite,
                clause_category=clause_category,
                risk_profile=req.risk_profile or None,
            )

            # Select tier content
            tier_data = clause.get(tier_name, clause.get("acceptable", {}))
            template_text = tier_data.get("template_text", "")
            guidance = tier_data.get("guidance", "")

            # Fill placeholders
            filled = self._fill_placeholders(template_text, placeholders)

            # Jurisdiction variant
            jur_key = req.jurisdiction.split("-")[0] if req.jurisdiction else ""
            jur_variants = clause.get("jurisdiction_variants", {})
            jur_variant = jur_variants.get(req.jurisdiction) or jur_variants.get(
                jur_key
            )

            # AI adaptation
            content = await self._ai_adapt_clause(filled, guidance, jur_variant)

            # Section numbering
            section_num = str(len(sections) + 1)

            sections.append(
                DraftSection(
                    number=section_num,
                    heading=clause.get("section_heading", ""),
                    content=content,
                    clause_type=clause.get("clause_type", "unknown"),
                    tier_used=tier_name,
                    notes=clause.get("drafting_notes"),
                )
            )

            # Collect defined terms
            for term in clause.get("required_defined_terms", []):
                if term not in defined_terms:
                    defined_terms[term] = clause.get("section_heading", "")

        elapsed = time.monotonic() - start
        title = _TITLE_MAP.get(
            req.contract_type,
            req.contract_type.upper().replace("_", " ") + " AGREEMENT",
        )

        return RawDraft(
            contract_type=req.contract_type,
            title=title,
            sections=sections,
            defined_terms=defined_terms,
            metadata=DraftMetadata(
                playbook_id=playbook.get("contract_type", req.contract_type),
                model=settings.GEMINI_MODEL,
                generation_seconds=round(elapsed, 3),
                tokens_used=tokens_used,
            ),
        )
