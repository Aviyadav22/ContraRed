"""
FixVerifier: deterministic verification of AI-generated fix text for contract redlining.

Performs three cost-free (no AI calls) checks:
1. Section reference validation — ensures every cross-reference in the fix exists in the contract
2. Length sanity — flags suspiciously long fixes that suggest hallucinated boilerplate
3. Playbook alignment — keyword-checks the fix against the playbook position for contradictions
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class FixVerificationResult:
    passed: bool
    fix_text: str  # The original fix text (unchanged)
    warnings: List[str] = field(default_factory=list)  # Non-blocking warnings
    errors: List[str] = field(default_factory=list)  # Blocking errors
    section_refs_valid: bool = True
    playbook_aligned: bool = True


# Regex patterns for common contract cross-references
_SECTION_REF_PATTERNS = [
    re.compile(r"Section\s+\d+", re.IGNORECASE),
    re.compile(r"Article\s+\d+", re.IGNORECASE),
    re.compile(r"Clause\s+\d+(\.\d+)*", re.IGNORECASE),
    re.compile(r"Schedule\s+[A-Z0-9]", re.IGNORECASE),
    re.compile(r"Exhibit\s+[A-Z]", re.IGNORECASE),
    re.compile(r"Appendix\s+[A-Z0-9]", re.IGNORECASE),
    re.compile(r"Annex(?:ure)?\s+[A-Z0-9]", re.IGNORECASE),
]

# Contradiction pairs: (word_a, word_b) — if playbook contains one and fix
# contains the other, that is a potential misalignment.
_CONTRADICTION_PAIRS = [
    ("capped", "uncapped"),
    ("limited", "unlimited"),
    ("mutual", "unilateral"),
    ("reasonable", "unreasonable"),
    ("exclusive", "non-exclusive"),
]

# Length multiplier threshold: fix_text longer than this multiple of
# original_text is flagged as likely hallucinated boilerplate.
_LENGTH_MULTIPLIER_THRESHOLD = 5


class FixVerifier:
    """Deterministic verifier for AI-generated contract fix text."""

    def verify_fix(
        self,
        fix_text: str,
        original_text: str,
        contract_text: str,
        rule_name: str = "",
        playbook_rule: Optional[Dict] = None,
    ) -> FixVerificationResult:
        """
        Run all deterministic checks on the proposed fix text.

        Args:
            fix_text: The AI-generated replacement text to verify.
            original_text: The original clause text being replaced.
            contract_text: The full contract text (used for cross-reference validation).
            rule_name: Optional name of the rule that triggered the fix.
            playbook_rule: Optional dict with keys ``primary_position`` and
                optionally ``fallback_position``.

        Returns:
            A ``FixVerificationResult`` indicating pass/fail, warnings, and errors.
        """
        warnings: List[str] = []
        errors: List[str] = []
        section_refs_valid = True
        playbook_aligned = True

        # --- Check 1: Section reference validation ---
        section_errors = self._check_section_references(fix_text, contract_text)
        if section_errors:
            errors.extend(section_errors)
            section_refs_valid = False

        # --- Check 2: Length sanity ---
        length_warnings = self._check_length_sanity(fix_text, original_text, rule_name)
        if length_warnings:
            warnings.extend(length_warnings)

        # --- Check 3: Playbook alignment ---
        if playbook_rule:
            alignment_warnings = self._check_playbook_alignment(
                fix_text, playbook_rule, rule_name
            )
            if alignment_warnings:
                warnings.extend(alignment_warnings)
                playbook_aligned = False

        passed = len(errors) == 0

        return FixVerificationResult(
            passed=passed,
            fix_text=fix_text,
            warnings=warnings,
            errors=errors,
            section_refs_valid=section_refs_valid,
            playbook_aligned=playbook_aligned,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_section_references(
        self, fix_text: str, contract_text: str
    ) -> List[str]:
        """Find cross-references in fix_text and verify they exist in contract_text."""
        errors: List[str] = []
        contract_lower = contract_text.lower()

        for pattern in _SECTION_REF_PATTERNS:
            for match in pattern.finditer(fix_text):
                ref = match.group(0)
                # Normalise whitespace for comparison: collapse runs of spaces
                ref_normalised = re.sub(r"\s+", " ", ref).strip().lower()
                if ref_normalised not in contract_lower:
                    errors.append(
                        f"Fix references '{ref}' which does not appear in the contract"
                    )

        return errors

    def _check_length_sanity(
        self, fix_text: str, original_text: str, rule_name: str
    ) -> List[str]:
        """Flag if fix_text is suspiciously longer than original_text."""
        warnings: List[str] = []
        original_len = len(original_text.strip())

        # Avoid division-by-zero for empty originals; still flag very long fixes
        if original_len == 0:
            if len(fix_text.strip()) > 500:
                warnings.append(
                    f"Fix text is {len(fix_text.strip())} chars but original text is empty "
                    f"— possible hallucinated boilerplate"
                    + (f" (rule: {rule_name})" if rule_name else "")
                )
            return warnings

        ratio = len(fix_text.strip()) / original_len
        if ratio > _LENGTH_MULTIPLIER_THRESHOLD:
            warnings.append(
                f"Fix text is {ratio:.1f}x longer than original "
                f"({len(fix_text.strip())} vs {original_len} chars) "
                f"— possible hallucinated boilerplate"
                + (f" (rule: {rule_name})" if rule_name else "")
            )

        return warnings

    def _check_playbook_alignment(
        self, fix_text: str, playbook_rule: Dict, rule_name: str
    ) -> List[str]:
        """Check fix_text against playbook positions for contradictory keywords."""
        warnings: List[str] = []
        fix_lower = fix_text.lower()

        # Gather all playbook position text to check against
        positions: List[str] = []
        if playbook_rule.get("primary_position"):
            positions.append(playbook_rule["primary_position"])
        if playbook_rule.get("fallback_position"):
            positions.append(playbook_rule["fallback_position"])

        if not positions:
            return warnings

        playbook_text = " ".join(positions).lower()

        for word_a, word_b in _CONTRADICTION_PAIRS:
            # Check both directions: playbook says A but fix says B, or vice-versa
            if word_a in playbook_text and word_b in fix_lower:
                warnings.append(
                    f"Playbook position contains '{word_a}' but fix contains "
                    f"'{word_b}' — possible misalignment"
                    + (f" (rule: {rule_name})" if rule_name else "")
                )
            elif word_b in playbook_text and word_a in fix_lower:
                warnings.append(
                    f"Playbook position contains '{word_b}' but fix contains "
                    f"'{word_a}' — possible misalignment"
                    + (f" (rule: {rule_name})" if rule_name else "")
                )

        return warnings
