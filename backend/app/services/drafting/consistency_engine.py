"""Deterministic cross-clause consistency engine.

Pure-logic checks with zero LLM calls:
  - Cross-reference validation
  - Undefined defined-term detection
  - Leftover placeholder detection
  - Number-word consistency
  - Party name consistency
"""
from __future__ import annotations

import re
from typing import List

from app.services.drafting.models import Annotation, RawDraft

# ---------------------------------------------------------------------------
# Word-to-number mapping (covers 1-100 + common contract quantities)
# ---------------------------------------------------------------------------
_WORD_TO_NUM: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
}

# Common legal terms that look like defined terms but are not
_COMMON_LEGAL_TERMS: set[str] = {
    "Agreement", "Party", "Parties", "United States", "Effective Date",
    "Business Day", "Business Days", "Receiving Party", "Disclosing Party",
    "Governing Law", "Applicable Law", "State", "Federal", "Court",
    "Written Notice", "Prior Written Consent", "Intellectual Property",
    "Third Party", "Good Faith", "Material Breach", "Force Majeure",
    "Indemnified Party", "Indemnifying Party", "Confidential Information",
    "Initial Term", "Renewal Term", "Term", "Notice",
}

# Common synonym groups for party roles
_ROLE_SYNONYMS: dict[str, set[str]] = {
    "vendor": {"supplier", "provider", "seller", "contractor"},
    "supplier": {"vendor", "provider", "seller", "contractor"},
    "provider": {"vendor", "supplier", "seller", "contractor"},
    "seller": {"vendor", "supplier", "provider"},
    "contractor": {"vendor", "supplier", "provider", "consultant"},
    "consultant": {"contractor", "advisor"},
    "buyer": {"purchaser", "customer", "client"},
    "purchaser": {"buyer", "customer", "client"},
    "customer": {"buyer", "purchaser", "client"},
    "client": {"buyer", "purchaser", "customer"},
    "licensee": {"subscriber", "user"},
    "licensor": {"provider", "vendor"},
    "employer": {"company", "firm"},
    "employee": {"worker", "staff"},
    "landlord": {"lessor", "owner"},
    "tenant": {"lessee", "renter"},
    "lessor": {"landlord", "owner"},
    "lessee": {"tenant", "renter"},
}

# Regex patterns compiled once
_RE_SECTION_REF = re.compile(r"Section\s+(\d+(?:\.\d+)*)", re.IGNORECASE)
_RE_PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")
_RE_NUMBER_WORD = re.compile(
    r"\b([a-z]+(?:-[a-z]+)?)\s*\((\d+)\)",
    re.IGNORECASE,
)
_RE_PARTY_ROLE = re.compile(r"\(the\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\)")
_RE_DEFINED_TERM_CANDIDATE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)


class ConsistencyEngine:
    """Run deterministic consistency checks on a RawDraft."""

    def check(self, draft: RawDraft) -> List[Annotation]:
        annotations: List[Annotation] = []
        annotations.extend(self._check_cross_references(draft))
        annotations.extend(self._check_undefined_terms(draft))
        annotations.extend(self._check_placeholders(draft))
        annotations.extend(self._check_number_word_consistency(draft))
        annotations.extend(self._check_party_names(draft))
        return annotations

    # ------------------------------------------------------------------
    # 1. Cross-reference validation
    # ------------------------------------------------------------------
    def _check_cross_references(self, draft: RawDraft) -> List[Annotation]:
        valid_numbers: set[str] = {s.number for s in draft.sections}
        # Also consider sub-section prefixes valid (e.g. "2" is valid if "2.1" exists)
        for s in draft.sections:
            parts = s.number.split(".")
            for i in range(1, len(parts) + 1):
                valid_numbers.add(".".join(parts[:i]))

        issues: List[Annotation] = []
        for section in draft.sections:
            for match in _RE_SECTION_REF.finditer(section.content):
                ref = match.group(1)
                if ref not in valid_numbers:
                    issues.append(Annotation(
                        section_number=section.number,
                        agent="consistency",
                        severity="warning",
                        issue=f"Broken cross-reference: Section {ref} does not exist",
                        suggested_fix=f"Update or remove the reference to Section {ref}",
                        reasoning=f"The draft contains sections {sorted(valid_numbers)} but references Section {ref}",
                    ))
        return issues

    # ------------------------------------------------------------------
    # 2. Undefined defined-term detection
    # ------------------------------------------------------------------
    def _check_undefined_terms(self, draft: RawDraft) -> List[Annotation]:
        known: set[str] = set(draft.defined_terms.keys()) | _COMMON_LEGAL_TERMS

        issues: List[Annotation] = []
        for section in draft.sections:
            for match in _RE_DEFINED_TERM_CANDIDATE.finditer(section.content):
                term = match.group(1)
                # Strip leading "The " — common in sentences like "The Receiving Party"
                normalized = re.sub(r"^The\s+", "", term)
                if normalized != term and normalized in known:
                    continue
                if term not in known:
                    issues.append(Annotation(
                        section_number=section.number,
                        agent="consistency",
                        severity="warning",
                        issue=f"Possibly undefined term: \"{term}\"",
                        suggested_fix=f"Add \"{term}\" to the Definitions section or replace with a defined term",
                        reasoning=f"\"{term}\" appears as a capitalized multi-word phrase but is not in the defined terms list",
                    ))
                    # Once flagged, treat as known to avoid duplicate annotations
                    known.add(term)
        return issues

    # ------------------------------------------------------------------
    # 3. Leftover placeholder detection
    # ------------------------------------------------------------------
    def _check_placeholders(self, draft: RawDraft) -> List[Annotation]:
        issues: List[Annotation] = []
        for section in draft.sections:
            for match in _RE_PLACEHOLDER.finditer(section.content):
                placeholder = match.group(0)
                issues.append(Annotation(
                    section_number=section.number,
                    agent="consistency",
                    severity="critical",
                    issue=f"Leftover placeholder found: {placeholder}",
                    suggested_fix=f"Replace {placeholder} with the actual value",
                    reasoning="Placeholders must be resolved before the contract is finalized",
                ))
        return issues

    # ------------------------------------------------------------------
    # 4. Number-word consistency
    # ------------------------------------------------------------------
    def _check_number_word_consistency(self, draft: RawDraft) -> List[Annotation]:
        issues: List[Annotation] = []
        for section in draft.sections:
            for match in _RE_NUMBER_WORD.finditer(section.content):
                word = match.group(1).lower()
                digit = int(match.group(2))
                expected = _WORD_TO_NUM.get(word)
                if expected is not None and expected != digit:
                    issues.append(Annotation(
                        section_number=section.number,
                        agent="consistency",
                        severity="warning",
                        issue=f"Number-word mismatch: \"{match.group(1)}\" means {expected} but is paired with ({digit})",
                        suggested_fix=f"Change to match: either the word or the number should be corrected",
                        reasoning=f"The word \"{match.group(1)}\" conventionally represents {expected}, not {digit}",
                    ))
        return issues

    # ------------------------------------------------------------------
    # 5. Party name consistency
    # ------------------------------------------------------------------
    def _check_party_names(self, draft: RawDraft) -> List[Annotation]:
        # Extract defined roles from preamble-like sections (first few sections)
        defined_roles: set[str] = set()
        for section in draft.sections:
            for match in _RE_PARTY_ROLE.finditer(section.content):
                defined_roles.add(match.group(1))

        if not defined_roles:
            return []

        defined_roles_lower = {r.lower() for r in defined_roles}

        issues: List[Annotation] = []
        full_text = " ".join(s.content for s in draft.sections)
        # Check for synonyms of defined roles appearing in the text
        for role in list(defined_roles_lower):
            synonyms = _ROLE_SYNONYMS.get(role, set())
            for synonym in synonyms:
                # Look for the synonym as a standalone word (case-insensitive)
                pattern = re.compile(r"\b" + re.escape(synonym) + r"\b", re.IGNORECASE)
                if pattern.search(full_text) and synonym not in defined_roles_lower:
                    issues.append(Annotation(
                        section_number="",
                        agent="consistency",
                        severity="warning",
                        issue=f"Inconsistent party reference: \"{synonym.title()}\" appears but the defined role is \"{role.title()}\"",
                        suggested_fix=f"Replace \"{synonym.title()}\" with \"{role.title()}\" throughout the contract",
                        reasoning=f"\"{synonym.title()}\" is a common synonym for \"{role.title()}\" which may cause ambiguity",
                    ))
        return issues
