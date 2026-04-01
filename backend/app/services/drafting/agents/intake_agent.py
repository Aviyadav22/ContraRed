"""
Intake Agent
=============
Validates raw form data, infers sensible defaults, and selects the
appropriate drafting playbook for the downstream Draft Agent.
"""

from __future__ import annotations

from typing import Any, Dict

from app.services.drafting.models import (
    DraftRequest,
    NDADetails,
    PartyInfo,
    SaaSDetails,
)

# ---------------------------------------------------------------------------
# Playbook imports (conditional so parallel tasks don't block each other)
# ---------------------------------------------------------------------------

from app.services.drafting.playbooks.nda_drafting import (
    NDA_MUTUAL_PLAYBOOK,
    NDA_UNILATERAL_PLAYBOOK,
)

try:
    from app.services.drafting.playbooks.saas_drafting import SAAS_PLAYBOOK
except ImportError:  # pragma: no cover – SaaS playbook may not exist yet
    SAAS_PLAYBOOK: Dict[str, Any] = {
        "contract_type": "saas",
        "name": "SaaS Subscription Agreement (placeholder)",
        "clauses": [],
    }

from app.services.drafting.playbooks.msa_drafting import MSA_PLAYBOOK
from app.services.drafting.playbooks.employment_drafting import EMPLOYMENT_PLAYBOOK

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLAYBOOK_REGISTRY: Dict[str, Dict[str, Any]] = {
    "nda_mutual": NDA_MUTUAL_PLAYBOOK,
    "nda_unilateral": NDA_UNILATERAL_PLAYBOOK,
    "saas": SAAS_PLAYBOOK,
    "msa": MSA_PLAYBOOK,
    "employment": EMPLOYMENT_PLAYBOOK,
}
VALID_CONTRACT_TYPES = frozenset(PLAYBOOK_REGISTRY.keys())
NDA_TYPES = {"nda_mutual", "nda_unilateral"}

JURISDICTION_TO_GOVERNING_LAW: Dict[str, str] = {
    "US-DE": "Delaware",
    "US-CA": "California",
    "US-NY": "New York",
    "US-TX": "Texas",
    "IN": "India",
    "GB": "England and Wales",
    "SG": "Singapore",
}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class IntakeAgent:
    """First stage of the drafting pipeline.

    Responsibilities:
    1. Validate that the contract type is supported.
    2. Ensure type-specific detail blocks are present (e.g. saas_details).
    3. Infer sensible defaults (governing_law, dispute_resolution, etc.).
    4. Return a fully-populated ``DraftRequest``.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process(self, raw: dict) -> DraftRequest:
        """Validate *raw* form data and return a hydrated ``DraftRequest``."""

        contract_type = raw.get("contract_type", "")
        if contract_type not in VALID_CONTRACT_TYPES:
            raise ValueError(
                f"Invalid contract_type '{contract_type}'. "
                f"Must be one of {sorted(VALID_CONTRACT_TYPES)}."
            )

        # --- type-specific detail checks ---
        if contract_type == "saas" and not raw.get("saas_details"):
            raise ValueError(
                "saas_details is required when contract_type is 'saas'."
            )

        # Build party objects
        party_1 = PartyInfo(**raw["party_1"])
        party_2 = PartyInfo(**raw["party_2"])

        # Infer governing_law from jurisdiction when not provided
        jurisdiction = raw.get("jurisdiction", "")
        governing_law = raw.get("governing_law") or self._infer_governing_law(jurisdiction)

        # Build optional detail blocks
        nda_details = self._build_nda_details(raw, contract_type)
        saas_details = self._build_saas_details(raw, contract_type)

        return DraftRequest(
            contract_type=contract_type,
            drafting_perspective=raw.get("drafting_perspective", "balanced"),
            risk_appetite=raw.get("risk_appetite", "balanced"),
            jurisdiction=jurisdiction,
            party_1=party_1,
            party_2=party_2,
            effective_date=raw.get("effective_date"),
            term_months=raw.get("term_months", 12),
            governing_law=governing_law,
            dispute_resolution=raw.get("dispute_resolution", "arbitration"),
            venue=raw.get("venue"),
            nda_details=nda_details,
            saas_details=saas_details,
        )

    def select_playbook(self, contract_type: str, jurisdiction: str) -> dict:
        """Return the playbook dict matching *contract_type*."""
        if contract_type not in PLAYBOOK_REGISTRY:
            raise ValueError(
                f"No playbook for contract_type '{contract_type}'."
            )
        return PLAYBOOK_REGISTRY[contract_type]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_governing_law(jurisdiction: str) -> str:
        return JURISDICTION_TO_GOVERNING_LAW.get(jurisdiction, jurisdiction)

    @staticmethod
    def _build_nda_details(raw: dict, contract_type: str):
        if contract_type not in NDA_TYPES:
            return None
        nda_raw = raw.get("nda_details") or {}
        if not nda_raw.get("purpose"):
            nda_raw.setdefault("purpose", "General business discussions")
        return NDADetails(**nda_raw)

    @staticmethod
    def _build_saas_details(raw: dict, contract_type: str):
        if contract_type != "saas":
            return None
        return SaaSDetails(**raw["saas_details"])
