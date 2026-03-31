"""
QA Agent
========
Deterministic quality-assurance checks on a RawDraft.
No AI calls — purely rule-based.
"""

from __future__ import annotations

import re
from typing import List

from app.services.drafting.models import Annotation, RawDraft

# Common legal terms that are often capitalised but are not defined terms
_COMMON_LEGAL_WORDS = frozenset({
    "Agreement",
    "Section",
    "Party",
    "Parties",
    "Article",
    "Clause",
    "Exhibit",
    "Schedule",
    "Appendix",
    "Annex",
    "Recital",
    "Whereas",
    "Effective Date",
    "Date",
    "State",
    "Court",
    "Law",
    "Act",
    "Regulation",
    "Notice",
    "Amendment",
    "Termination",
    "Term",
    "Governing Law",
    "Jurisdiction",
    "Arbitration",
    "Confidential",
    "Disclosure",
    "Purpose",
    "Information",
})

# Regex to find quoted capitalised terms, e.g. "Derivative Materials"
_QUOTED_CAP_TERM_RE = re.compile(r'["\u201c]([A-Z][A-Za-z ]+?)["\u201d]')

# Regex to find {{placeholder}} patterns
_PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")


class QAAgent:
    """Deterministic quality-assurance reviewer."""

    async def review(self, draft: RawDraft) -> List[Annotation]:
        """Run all QA checks and return combined annotations."""
        annotations: List[Annotation] = []
        annotations.extend(self._check_defined_terms(draft))
        annotations.extend(self._check_section_numbering(draft))
        annotations.extend(self._check_placeholders(draft))
        return annotations

    # ------------------------------------------------------------------
    # Check 1: undefined terms
    # ------------------------------------------------------------------

    @staticmethod
    def _check_defined_terms(draft: RawDraft) -> List[Annotation]:
        """Find quoted capitalised terms not present in defined_terms."""
        known = set(draft.defined_terms.keys())
        annotations: List[Annotation] = []
        seen: set[str] = set()

        for section in draft.sections:
            matches = _QUOTED_CAP_TERM_RE.findall(section.content)
            for term in matches:
                term_stripped = term.strip()
                if (
                    term_stripped not in known
                    and term_stripped not in _COMMON_LEGAL_WORDS
                    and term_stripped not in seen
                ):
                    seen.add(term_stripped)
                    annotations.append(
                        Annotation(
                            section_number=section.number,
                            agent="qa",
                            severity="warning",
                            issue=f'Undefined term: "{term_stripped}"',
                            reasoning=(
                                f'The term "{term_stripped}" appears in quotes and is '
                                "capitalised but is not listed in defined_terms."
                            ),
                        )
                    )
        return annotations

    # ------------------------------------------------------------------
    # Check 2: section numbering gaps
    # ------------------------------------------------------------------

    @staticmethod
    def _check_section_numbering(draft: RawDraft) -> List[Annotation]:
        """Check that integer section numbers are consecutive."""
        int_numbers: list[int] = []
        for s in draft.sections:
            try:
                int_numbers.append(int(s.number))
            except ValueError:
                continue

        if not int_numbers:
            return []

        int_numbers.sort()
        gaps: list[str] = []
        for i in range(len(int_numbers) - 1):
            if int_numbers[i + 1] != int_numbers[i] + 1:
                gaps.append(f"{int_numbers[i]}→{int_numbers[i + 1]}")

        if not gaps:
            return []

        return [
            Annotation(
                section_number="0",
                agent="qa",
                severity="info",
                issue=f"Section numbering gap(s): {', '.join(gaps)}",
                reasoning=(
                    f"Expected consecutive numbering but found gaps: {', '.join(gaps)}. "
                    f"Actual sequence: {int_numbers}."
                ),
            )
        ]

    # ------------------------------------------------------------------
    # Check 3: unfilled placeholders
    # ------------------------------------------------------------------

    @staticmethod
    def _check_placeholders(draft: RawDraft) -> List[Annotation]:
        """Find unfilled {{placeholders}} in section content."""
        annotations: List[Annotation] = []
        for section in draft.sections:
            placeholders = _PLACEHOLDER_RE.findall(section.content)
            for ph in placeholders:
                annotations.append(
                    Annotation(
                        section_number=section.number,
                        agent="qa",
                        severity="critical",
                        issue=f"Unfilled placeholder: {ph}",
                        reasoning=(
                            f"The placeholder {ph} in section {section.number} "
                            "has not been replaced with actual content."
                        ),
                    )
                )
        return annotations
