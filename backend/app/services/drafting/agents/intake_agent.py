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
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "AU": "Australia",
    "DE": "Germany",
    "FR": "France",
    "CA-ON": "Ontario, Canada",
    "CA-BC": "British Columbia, Canada",
    "BR": "Brazil",
    "HK": "Hong Kong",
    "JP": "Japan",
}

# Inverse mapping used when the user typed a governing_law string like
# "India" or "Delaware" and we need to derive the canonical jurisdiction code.
_GOVERNING_LAW_TO_JURISDICTION: Dict[str, str] = {
    "delaware": "US-DE",
    "california": "US-CA",
    "new york": "US-NY",
    "texas": "US-TX",
    "india": "IN",
    "indian": "IN",
    "england and wales": "GB",
    "england": "GB",
    "uk": "GB",
    "united kingdom": "GB",
    "singapore": "SG",
    "uae": "AE",
    "united arab emirates": "AE",
    "saudi arabia": "SA",
    "australia": "AU",
    "germany": "DE",
    "france": "FR",
    "ontario": "CA-ON",
    "british columbia": "CA-BC",
    "brazil": "BR",
    "hong kong": "HK",
    "japan": "JP",
}

# Compliance-framework ↔ jurisdiction hints.
# User-selected frameworks are a strong signal of the intended jurisdiction.
_FRAMEWORK_TO_JURISDICTION: Dict[str, str] = {
    "DPDP": "IN",
    "GDPR": "EU",
    "UK GDPR": "GB",
    "CCPA": "US-CA",
    "CPRA": "US-CA",
    "HIPAA": "US",
    "PIPEDA": "CA-ON",
    "LGPD": "BR",
    "PDPA": "SG",   # Singapore (also used by Thailand, Malaysia — Singapore is the common case)
    "Privacy Act": "AU",
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

        # Jurisdiction derivation (fixes the "user typed India but jurisdiction
        # stayed US-DE" bug).  We take the explicit request value as a starting
        # point but upgrade it when other signals (party jurisdictions,
        # governing law, compliance frameworks) unambiguously point elsewhere.
        jurisdiction = self._derive_jurisdiction(
            raw_jurisdiction=raw.get("jurisdiction", ""),
            party_1_jurisdiction=party_1.jurisdiction,
            party_2_jurisdiction=party_2.jurisdiction,
            governing_law_text=raw.get("governing_law", ""),
            saas_details=raw.get("saas_details") or {},
        )

        # Infer governing_law from jurisdiction when not provided
        governing_law = raw.get("governing_law") or self._infer_governing_law(jurisdiction)
        # Normalise casing: users sometimes type 'new york' / 'DELAWARE' which
        # the AI then echoes verbatim into clauses ("the laws of new york").
        # Title-case everything except small connector words that shouldn't
        # be capitalised in a proper-noun phrase.
        governing_law = self._normalise_proper_noun(governing_law)

        # Same treatment for venue (also user-entered free text).
        venue_raw = raw.get("venue")
        venue = self._normalise_proper_noun(venue_raw) if venue_raw else venue_raw

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
            venue=venue,
            nda_details=nda_details,
            saas_details=saas_details,
            risk_profile=raw.get("risk_profile", {}),
            negotiation_context=raw.get("negotiation_context", ""),
            employee_title=raw.get("employee_title", ""),
            base_salary=raw.get("base_salary", ""),
            reporting_manager=raw.get("reporting_manager", ""),
            work_location=raw.get("work_location", "Hybrid"),
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
    def _normalise_proper_noun(value: str) -> str:
        """Title-case a proper-noun string like 'new york' -> 'New York'.

        Handling:
          - All-lowercase input ('new york') -> title-cased ('New York').
          - All-uppercase input ('NEW YORK') -> title-cased ('New York').
          - Mixed-case input ('New York', 'UAE', 'State of UAE') -> left
            untouched (we trust the user).
          - Connector words ('of', 'and', 'the') stay lowercase unless
            they start the string.
        Safe on empty / None input.
        """
        if not value:
            return value
        # Strip trailing punctuation.
        value = value.strip().rstrip(",.;")
        if not value:
            return value

        has_lower = any(c.islower() for c in value)
        has_upper = any(c.isupper() for c in value)
        # Mixed case (user already capitalised something) — trust them.
        if has_lower and has_upper:
            return value

        # Preserve short all-caps acronyms like 'UK', 'UAE', 'NY' — but ONLY
        # when the whole value is a single short token. 'NEW YORK' would
        # have multiple tokens and should get title-cased below.
        if (
            value.isupper()
            and " " not in value
            and len(value) <= 4
        ):
            return value

        # All one case, and either lowercase or long-enough to be a name.
        # Normalise to lower then title-case each token.
        connectors = {"of", "and", "the", "la", "le", "des"}
        parts = value.lower().split()
        out: List[str] = []
        for i, part in enumerate(parts):
            if i > 0 and part in connectors:
                out.append(part)
                continue
            out.append(part.capitalize())
        return " ".join(out)

    @staticmethod
    def _derive_jurisdiction(
        raw_jurisdiction: str,
        party_1_jurisdiction: str,
        party_2_jurisdiction: str,
        governing_law_text: str,
        saas_details: Dict[str, Any],
    ) -> str:
        """Derive the contract's jurisdiction from all user-supplied signals.

        The frontend has a single ``form.jurisdiction`` field that defaults to
        ``US-DE`` and — historically — had no user-facing widget.  Users who
        filled in "India" for governing law, selected both parties as Indian
        entities, and ticked DPDP in compliance frameworks still ended up with
        ``context.jurisdiction = US-DE``, which suppressed the DPDP repair
        path in the coherence pass and kept the DPA GDPR-flavoured.

        This method collects all of those signals and returns the best guess
        at the contract's governing jurisdiction:

            1. Explicit ``jurisdiction`` from the request, if non-default.
            2. If both parties share a country-level jurisdiction, use that.
            3. If governing_law text matches a known jurisdiction, use it.
            4. If the compliance frameworks list uniquely implies a region,
               use that.
            5. Otherwise fall back to the raw request value (or ``US-DE``).
        """
        # 1. Respect an explicit non-default jurisdiction.
        if raw_jurisdiction and raw_jurisdiction != "US-DE":
            return raw_jurisdiction

        # 2. Party-level agreement.  Use the country prefix so that e.g.
        #    "IN-MH" and "IN-DL" both collapse to "IN".
        def _country(code: str) -> str:
            return code.split("-", 1)[0] if code else ""

        p1_country = _country(party_1_jurisdiction)
        p2_country = _country(party_2_jurisdiction)
        if p1_country and p1_country == p2_country and p1_country != "US":
            # Both parties agree on a non-US country — good derivation.
            # Preserve the sub-region if party_1 carries one (e.g. IN-DL).
            return party_1_jurisdiction or p1_country

        # 3. Governing-law text lookup.
        gl_key = (governing_law_text or "").strip().lower()
        for keyword, code in _GOVERNING_LAW_TO_JURISDICTION.items():
            if keyword in gl_key:
                return code

        # 4. Compliance-framework signal.  If the user selected DPDP it is
        #    effectively a declaration that this is an India deal; similarly
        #    for GDPR (EU), CCPA (California), etc.
        frameworks = saas_details.get("compliance_frameworks") or []
        framework_votes: Dict[str, int] = {}
        for fw in frameworks:
            target = _FRAMEWORK_TO_JURISDICTION.get(fw)
            if target:
                framework_votes[target] = framework_votes.get(target, 0) + 1
        if framework_votes:
            # If there is a single unambiguous winner, use it.
            best = max(framework_votes.items(), key=lambda kv: kv[1])
            if list(framework_votes.values()).count(best[1]) == 1:
                return best[0]

        # 5. Last resort — keep the raw value (which may be US-DE default).
        return raw_jurisdiction or "US-DE"

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
