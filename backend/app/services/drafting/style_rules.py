"""Deterministic style enforcer based on Ken Adams' Manual of Style for Contract Drafting.

Post-processes generated contract clauses to ensure consistent, professional
legal language. All functions are pure (no I/O) and operate on plain text.
"""
from __future__ import annotations

import re
from typing import Set

# ---------------------------------------------------------------------------
# 1. Shall / Will normalisation
# ---------------------------------------------------------------------------

# Future-tense verbs that should NOT be converted (they express futurity,
# not obligation). Checked as the word immediately after "will"/"shall".
_FUTURE_TENSE_VERBS = {
    "expire", "terminate", "commence", "become", "occur",
    "arise", "lapse", "be", "take", "have", "result", "remain",
    "continue", "cease", "accrue",
}


def normalize_shall_will(text: str, preference: str = "shall") -> str:
    """Replace obligation verbs (shall/will) with the chosen *preference*.

    Future-tense uses (e.g. "will expire", "will terminate") are left
    untouched regardless of the preference setting.
    """
    if preference not in ("shall", "will"):
        raise ValueError(f"preference must be 'shall' or 'will', got {preference!r}")

    source = "will" if preference == "shall" else "shall"
    target = preference

    def _replace(m: re.Match) -> str:
        verb = m.group(2).lower()
        # Check if the following verb is future-tense — protect in BOTH directions
        if verb in _FUTURE_TENSE_VERBS:
            return m.group(0)  # Don't replace
        # Preserve original capitalisation of the modal
        original = m.group(1)
        replacement = target.capitalize() if original[0].isupper() else target
        return replacement + " " + m.group(2)

    # Match "shall/will" followed by a verb (word)
    pattern = rf"\b({source})\s+(\w+)"
    return re.sub(pattern, _replace, text, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# 2. Number-word pairs
# ---------------------------------------------------------------------------

_NUMBER_WORDS: dict[int, str] = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
    15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen", 20: "twenty", 24: "twenty-four", 25: "twenty-five",
    30: "thirty", 45: "forty-five", 60: "sixty", 90: "ninety",
    180: "one hundred eighty", 365: "three hundred sixty-five",
}

_TIME_UNITS = r"(?:days?|months?|years?|weeks?|hours?|business\s+days?|calendar\s+days?)"


def normalize_number_words(text: str) -> str:
    """Convert bare numbers before time units to 'word (N) unit' format.

    Already-formatted text like "thirty (30) days" is left untouched.
    """
    # First, skip anything already in "word (N) unit" form
    def _replace(m: re.Match) -> str:
        num = int(m.group(1))
        unit = m.group(2)
        word = _NUMBER_WORDS.get(num)
        if word is None:
            return m.group(0)  # unknown number, leave as-is
        return f"{word} ({num}) {unit}"

    # Negative lookbehind is tricky with variable width; instead we skip
    # matches that are already formatted by checking for "(N)" after word.
    already_formatted = rf"\b[a-z][\w-]*\s+\(\d+\)\s+{_TIME_UNITS}"

    # Protect already-formatted spans
    protected: list[tuple[int, int]] = []
    for m in re.finditer(already_formatted, text, flags=re.IGNORECASE):
        protected.append((m.start(), m.end()))

    def _in_protected(m: re.Match) -> bool:
        for start, end in protected:
            if start <= m.start() < end:
                return True
        return False

    parts: list[str] = []
    last = 0
    for m in re.finditer(rf"\b(\d+)\s+({_TIME_UNITS})\b", text, flags=re.IGNORECASE):
        if _in_protected(m):
            continue
        parts.append(text[last:m.start()])
        parts.append(_replace(m))
        last = m.end()
    parts.append(text[last:])
    return "".join(parts)


# ---------------------------------------------------------------------------
# 3. Efforts standard
# ---------------------------------------------------------------------------

_EFFORTS_PATTERNS = [
    r"commercially\s+reasonable\s+efforts",
    r"reasonable\s+best\s+efforts",
    r"best\s+efforts",
]


def normalize_efforts_standard(text: str) -> str:
    """Replace all effort-standard variants with 'reasonable efforts'."""
    for pat in _EFFORTS_PATTERNS:
        text = re.sub(pat, "reasonable efforts", text, flags=re.IGNORECASE)
    return text


# ---------------------------------------------------------------------------
# 4. Archaism removal
# ---------------------------------------------------------------------------

_ARCHAISM_MAP: dict[str, str] = {
    "herein": "in this Agreement",
    "hereof": "of this Agreement",
    "hereby": "",
    "thereof": "of it",
    "therein": "in it",
    "hereinafter": "",
    "aforesaid": "",
}


def remove_archaisms(text: str) -> str:
    """Replace archaic legalisms with plain-English equivalents."""
    for archaic, replacement in _ARCHAISM_MAP.items():
        text = re.sub(rf"\b{archaic}\b", replacement, text, flags=re.IGNORECASE)
    # Collapse double+ spaces
    text = re.sub(r"  +", " ", text)
    return text


# ---------------------------------------------------------------------------
# 5. Defined-term formatting
# ---------------------------------------------------------------------------

def format_defined_term_first_use(
    text: str,
    defined_terms: Set[str],
) -> str:
    """Wrap the FIRST occurrence of each defined term in curly quotes.

    Already-quoted terms (with \u201c\u201d or plain quotes) are skipped.
    """
    for term in sorted(defined_terms, key=len, reverse=True):
        # Skip if already quoted anywhere
        if f"\u201c{term}\u201d" in text or f'"{term}"' in text:
            continue
        # Replace only the first occurrence
        text = re.sub(
            rf"(?<!\u201c)\b{re.escape(term)}\b(?!\u201d)",
            f"\u201c{term}\u201d",
            text,
            count=1,
        )
    return text


# ---------------------------------------------------------------------------
# 6. Master function
# ---------------------------------------------------------------------------

def apply_all_style_rules(
    text: str,
    defined_terms: Set[str] | None = None,
    shall_preference: str = "shall",
) -> str:
    """Apply all style rules in the recommended order."""
    text = normalize_shall_will(text, preference=shall_preference)
    text = normalize_number_words(text)
    text = normalize_efforts_standard(text)
    text = remove_archaisms(text)
    if defined_terms:
        text = format_defined_term_first_use(text, defined_terms)
    return text
