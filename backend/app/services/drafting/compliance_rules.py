"""
Deterministic Compliance Rule Engine
=====================================
Hard-coded legal compliance checks that run BEFORE the LLM call.
Acts as a safety net for:
  - Liability cap reasonableness (ACC 10-point test)
  - GDPR Article 28 completeness
  - Efforts standard consistency
"""

from __future__ import annotations

import re
from typing import List, Set


class ComplianceRuleEngine:
    """Deterministic compliance checks that never depend on an LLM."""

    GDPR_ARTICLE_28_REQUIREMENTS = frozenset(
        {
            "processing_on_instructions",
            "confidentiality_obligations",
            "security_measures",
            "sub_processor_management",
            "data_subject_rights",
            "deletion_on_termination",
            "audit_rights",
            "breach_notification",
        }
    )

    # Canonical efforts standards ordered from weakest to strongest
    EFFORTS_PATTERNS = [
        ("reasonable efforts", re.compile(r"\breasonable\s+efforts\b", re.IGNORECASE)),
        (
            "commercially reasonable efforts",
            re.compile(r"\bcommercially\s+reasonable\s+efforts\b", re.IGNORECASE),
        ),
        ("best efforts", re.compile(r"\bbest\s+efforts\b", re.IGNORECASE)),
    ]

    # ------------------------------------------------------------------ #
    # Liability cap
    # ------------------------------------------------------------------ #

    def check_liability_cap(
        self,
        cap_months: int,
        contract_value_annual: float = 0,
        has_ip_carveout: bool = False,
        has_confidentiality_carveout: bool = False,
        has_gross_negligence_carveout: bool = False,
    ) -> List[str]:
        """Check liability cap reasonableness per ACC 10-point test.

        Returns a list of plain-English finding strings (empty = no issues).
        """
        findings: List[str] = []

        # --- Cap amount ---
        if cap_months <= 0:
            findings.append(
                "CRITICAL: Liability cap is zero or negative months of fees "
                "-- likely unconscionable and unenforceable in most jurisdictions."
            )
        elif cap_months < 3:
            findings.append(
                "CRITICAL: Liability cap below 3 months of fees is below market "
                "standard and may be deemed unconscionable."
            )
        elif cap_months < 6:
            findings.append(
                "WARNING: Liability cap below 6 months of fees is below market "
                "median for enterprise contracts."
            )

        # --- Carve-outs ---
        if not has_ip_carveout:
            findings.append(
                "WARNING: No IP infringement carve-out from the liability cap. "
                "Market standard is to exclude IP claims from the cap."
            )

        if not has_confidentiality_carveout:
            findings.append(
                "WARNING: No confidentiality breach carve-out from the liability "
                "cap. Consider excluding confidentiality breaches."
            )

        if not has_gross_negligence_carveout:
            findings.append(
                "INFO: No gross negligence / wilful misconduct carve-out. "
                "Many jurisdictions void caps on intentional misconduct anyway."
            )

        return findings

    # ------------------------------------------------------------------ #
    # GDPR Article 28 completeness
    # ------------------------------------------------------------------ #

    def check_gdpr_completeness(self, present_provisions: Set[str]) -> Set[str]:
        """Return the set of GDPR Art 28 provisions that are *missing*."""
        return self.GDPR_ARTICLE_28_REQUIREMENTS - present_provisions

    # ------------------------------------------------------------------ #
    # Efforts standard consistency
    # ------------------------------------------------------------------ #

    def check_efforts_consistency(self, clause_texts: List[str]) -> List[str]:
        """Flag inconsistent efforts standards across clauses.

        Scans each clause text for known efforts standards and flags if more
        than one distinct standard is used across the contract.
        """
        found_standards: set[str] = set()

        for text in clause_texts:
            for label, pattern in self.EFFORTS_PATTERNS:
                if pattern.search(text):
                    found_standards.add(label)

        findings: List[str] = []
        if len(found_standards) > 1:
            standards_str = ", ".join(sorted(found_standards))
            findings.append(
                f"WARNING: Multiple efforts standards detected ({standards_str}). "
                "Using inconsistent standards weakens enforceability and creates "
                "ambiguity. Consider harmonising to a single standard."
            )

        return findings
