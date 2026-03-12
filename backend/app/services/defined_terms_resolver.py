"""
Defined Terms Resolver - Extract and resolve definitions from contract text.

Parses "Defined Term" definitions from contracts, resolves recursive references
between defined terms, and flags overbroad definitions that may pose risks.

Zero AI dependency: purely regex-based extraction and analysis.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class DefinedTerm:
    """A single defined term extracted from the contract."""

    term: str  # The defined term itself, e.g. "Confidential Information"
    definition: str  # The full definition text
    raw_text: str  # The complete raw text including the term and definition
    start_offset: int  # Character position in the source text
    end_offset: int
    referenced_terms: List[str] = field(default_factory=list)  # Other defined terms referenced
    resolved_definition: str = ""  # Definition with all references expanded
    is_overbroad: bool = False
    overbroad_reason: str = ""


@dataclass
class DefinedTermsResult:
    """Complete result of defined terms extraction."""

    terms: Dict[str, DefinedTerm]  # term_name -> DefinedTerm
    overbroad_terms: List[str]  # Names of flagged overbroad terms
    term_count: int
    resolution_depth_reached: int  # Max recursion depth used

    def to_prompt_context(self) -> str:
        """Generate defined terms context for AI prompt injection.

        Returns a compact block listing each defined term and its
        resolved definition, plus overbroad warnings.
        """
        if not self.terms:
            return "DEFINED TERMS: None detected in the contract."

        lines = [
            f"DEFINED TERMS ({self.term_count} detected):",
            "",
        ]

        for name, dt in sorted(self.terms.items()):
            defn = dt.resolved_definition or dt.definition
            # Truncate very long definitions for prompt economy
            if len(defn) > 400:
                defn = defn[:397] + "..."
            lines.append(f'  "{name}": {defn}')

        if self.overbroad_terms:
            lines.append("")
            lines.append("OVERBROAD DEFINITION WARNINGS:")
            for term_name in self.overbroad_terms:
                dt = self.terms.get(term_name)
                if dt:
                    lines.append(f'  - "{term_name}": {dt.overbroad_reason}')

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Serialize to dict for API responses."""
        return {
            "terms": {
                name: {
                    "term": dt.term,
                    "definition": dt.definition,
                    "resolved_definition": dt.resolved_definition,
                    "is_overbroad": dt.is_overbroad,
                    "overbroad_reason": dt.overbroad_reason,
                    "referenced_terms": dt.referenced_terms,
                }
                for name, dt in self.terms.items()
            },
            "overbroad_terms": self.overbroad_terms,
            "term_count": self.term_count,
        }


# ---------------------------------------------------------------------------
# Detection patterns for defined terms
# ---------------------------------------------------------------------------

# Pattern 1: "Term" means ...
# Pattern 2: "Term" shall mean ...
# Pattern 3: "Term" is defined as ...
# Pattern 4: As used herein, "Term" ...
# Pattern 5: "Term" has the meaning ...
# Pattern 6: "Term" refers to ...
# Pattern 7: ("Term") — inline parenthetical definition

_DEFINITION_PATTERNS: List[re.Pattern] = [
    # "Term" means / shall mean / will mean
    re.compile(
        r'["\u201c]([A-Z][A-Za-z\s&,/()-]{1,80}?)["\u201d]\s+'
        r'(?:shall\s+)?(?:mean|means|will\s+mean)\s+'
        r'(.+?)(?=\n["\u201c][A-Z]|\n\n|\n\d+\.\s|\Z)',
        re.DOTALL,
    ),
    # "Term" is defined as ...
    re.compile(
        r'["\u201c]([A-Z][A-Za-z\s&,/()-]{1,80}?)["\u201d]\s+'
        r'(?:is|are)\s+defined\s+as\s+'
        r'(.+?)(?=\n["\u201c][A-Z]|\n\n|\n\d+\.\s|\Z)',
        re.DOTALL,
    ),
    # As used herein, "Term" means/refers to ...
    re.compile(
        r'[Aa]s\s+used\s+(?:herein|in\s+this\s+\w+),?\s*'
        r'["\u201c]([A-Z][A-Za-z\s&,/()-]{1,80}?)["\u201d]\s+'
        r'(?:shall\s+)?(?:mean|means|refer[s]?\s+to)\s+'
        r'(.+?)(?=\n["\u201c][A-Z]|\n\n|\n\d+\.\s|\Z)',
        re.DOTALL,
    ),
    # "Term" has the meaning ...
    re.compile(
        r'["\u201c]([A-Z][A-Za-z\s&,/()-]{1,80}?)["\u201d]\s+'
        r'(?:shall\s+have|has|have)\s+the\s+meaning\s+'
        r'(.+?)(?=\n["\u201c][A-Z]|\n\n|\n\d+\.\s|\Z)',
        re.DOTALL,
    ),
    # "Term" refers to ...
    re.compile(
        r'["\u201c]([A-Z][A-Za-z\s&,/()-]{1,80}?)["\u201d]\s+'
        r'(?:shall\s+)?refer[s]?\s+to\s+'
        r'(.+?)(?=\n["\u201c][A-Z]|\n\n|\n\d+\.\s|\Z)',
        re.DOTALL,
    ),
    # (hereinafter "Term" or "the Term") — capture context before
    re.compile(
        r'([A-Za-z][^.]{10,200}?)\s*'
        r'\((?:hereinafter\s+)?(?:referred\s+to\s+as\s+)?'
        r'["\u201c]([A-Z][A-Za-z\s&,/()-]{1,60}?)["\u201d]\)',
        re.DOTALL,
    ),
    # "Term": definition (colon or em-dash separated)
    re.compile(
        r'["\u201c]([A-Z][A-Za-z\s&,/()-]{1,80}?)["\u201d]\s*[:\u2014\u2013]\s*'
        r'(.+?)(?=\n["\u201c][A-Z]|\n\n|\n\d+\.\s|\Z)',
        re.DOTALL,
    ),
]

# Overbroad definition patterns — phrases that signal a dangerously broad definition
_OVERBROAD_SIGNALS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(r'\ball\s+information\b', re.IGNORECASE),
        "Definition covers 'all information' without meaningful limitation"
    ),
    (
        re.compile(r'\bany\s+and\s+all\b', re.IGNORECASE),
        "Uses 'any and all' language — extremely broad scope"
    ),
    (
        re.compile(r'\bwithout\s+limitation\b', re.IGNORECASE),
        "Contains 'without limitation' — open-ended catch-all"
    ),
    (
        re.compile(r'\bwhether\s+or\s+not\s+(?:marked|designated|identified)\b', re.IGNORECASE),
        "Applies regardless of whether information is marked as confidential"
    ),
    (
        re.compile(r'\bincluding\s+but\s+not\s+limited\s+to\b', re.IGNORECASE),
        "Uses 'including but not limited to' — non-exhaustive expansion"
    ),
    (
        re.compile(r'\bin\s+any\s+form\s+(?:or\s+)?(?:medium|format|manner)\b', re.IGNORECASE),
        "Covers information 'in any form or medium' — no format limitation"
    ),
    (
        re.compile(r'\bdirectly\s+or\s+indirectly\b', re.IGNORECASE),
        "Captures both 'directly or indirectly' — extended scope"
    ),
    (
        re.compile(r'\ball\s+(?:intellectual\s+property|IP)\b', re.IGNORECASE),
        "Sweeps in 'all intellectual property' without carve-outs"
    ),
    (
        re.compile(r'\beverything\b|\btotality\b', re.IGNORECASE),
        "Uses absolute language ('everything'/'totality') — maximally broad"
    ),
]


class DefinedTermsResolver:
    """
    Extract, resolve, and flag defined terms from contract text.

    Usage:
        resolver = DefinedTermsResolver()
        result = resolver.resolve("...contract text...")
        prompt_ctx = result.to_prompt_context()
    """

    MAX_RECURSION_DEPTH = 3

    def resolve(self, contract_text: str) -> DefinedTermsResult:
        """
        Extract defined terms, resolve cross-references, and flag overbroad definitions.

        Args:
            contract_text: Full contract text.

        Returns:
            DefinedTermsResult with all terms, resolutions, and warnings.
        """
        # Step 1: Extract raw definitions
        terms = self._extract_definitions(contract_text)

        if not terms:
            return DefinedTermsResult(
                terms={},
                overbroad_terms=[],
                term_count=0,
                resolution_depth_reached=0,
            )

        # Step 2: Identify cross-references between defined terms
        term_names = set(terms.keys())
        for dt in terms.values():
            dt.referenced_terms = self._find_referenced_terms(
                dt.definition, term_names, dt.term
            )

        # Step 3: Recursively resolve definitions
        max_depth = self._resolve_recursive(terms)

        # Step 4: Flag overbroad definitions
        overbroad: List[str] = []
        for name, dt in terms.items():
            reason = self._check_overbroad(dt.definition)
            if reason:
                dt.is_overbroad = True
                dt.overbroad_reason = reason
                overbroad.append(name)

        return DefinedTermsResult(
            terms=terms,
            overbroad_terms=overbroad,
            term_count=len(terms),
            resolution_depth_reached=max_depth,
        )

    def _extract_definitions(self, text: str) -> Dict[str, DefinedTerm]:
        """Extract defined terms using regex patterns."""
        terms: Dict[str, DefinedTerm] = {}

        for pattern in _DEFINITION_PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groups()

                # The last pattern has reversed groups (context first, then term)
                if pattern == _DEFINITION_PATTERNS[-1]:
                    definition_text = groups[0].strip()
                    term_name = groups[1].strip()
                else:
                    term_name = groups[0].strip()
                    definition_text = groups[1].strip()

                # Normalize the term name
                term_name = self._normalize_term_name(term_name)

                if not term_name or len(term_name) < 2:
                    continue

                # Clean definition text
                definition_text = self._clean_definition(definition_text)

                if not definition_text or len(definition_text) < 5:
                    continue

                # Avoid duplicates — keep the longest definition
                if term_name in terms:
                    if len(definition_text) <= len(terms[term_name].definition):
                        continue

                terms[term_name] = DefinedTerm(
                    term=term_name,
                    definition=definition_text,
                    raw_text=match.group(0),
                    start_offset=match.start(),
                    end_offset=match.end(),
                )

        return terms

    def _normalize_term_name(self, name: str) -> str:
        """Normalize a defined term name."""
        # Strip quotes and whitespace
        name = name.strip(' "\u201c\u201d\u2018\u2019\'')
        # Collapse internal whitespace
        name = re.sub(r'\s+', ' ', name)
        return name

    def _clean_definition(self, text: str) -> str:
        """Clean and normalize definition text."""
        # Remove leading/trailing whitespace and common separators
        text = text.strip(' \t\n\r:;,')
        # Collapse internal whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove trailing period if it looks like end of definition
        if text.endswith('.'):
            text = text[:-1].strip()
        return text

    def _find_referenced_terms(
        self,
        definition: str,
        all_term_names: Set[str],
        self_name: str,
    ) -> List[str]:
        """Find which other defined terms are referenced in this definition."""
        refs: List[str] = []
        for name in all_term_names:
            if name == self_name:
                continue
            # Look for the term name in quotes or as a capitalized phrase
            # Check both quoted and unquoted references
            if re.search(
                r'(?:["\u201c]' + re.escape(name) + r'["\u201d]|\b' + re.escape(name) + r'\b)',
                definition,
                re.IGNORECASE,
            ):
                refs.append(name)
        return refs

    def _resolve_recursive(
        self,
        terms: Dict[str, DefinedTerm],
    ) -> int:
        """
        Resolve cross-referenced definitions recursively.

        Each term's resolved_definition replaces references to other
        defined terms with their definitions, up to MAX_RECURSION_DEPTH.

        Returns the maximum depth reached.
        """
        max_depth = 0

        # Pre-compile patterns once for all terms
        compiled_patterns = {
            tname: re.compile(
                r'(?:["\u201c])' + re.escape(tname) + r'(?:["\u201d])',
                re.IGNORECASE,
            )
            for tname in terms
        }

        for name, dt in terms.items():
            resolved, depth = self._resolve_single(
                dt.definition,
                terms,
                visited={name},
                depth=0,
                compiled_patterns=compiled_patterns,
            )
            dt.resolved_definition = resolved
            max_depth = max(max_depth, depth)

        return max_depth

    def _resolve_single(
        self,
        text: str,
        terms: Dict[str, DefinedTerm],
        visited: Set[str],
        depth: int,
        compiled_patterns: Optional[Dict[str, re.Pattern]] = None,
    ) -> Tuple[str, int]:
        """Resolve a single definition by expanding referenced terms."""
        if depth >= self.MAX_RECURSION_DEPTH:
            return text, depth

        # Pre-compile patterns once and reuse across recursive calls
        if compiled_patterns is None:
            compiled_patterns = {
                name: re.compile(
                    r'(?:["\u201c])' + re.escape(name) + r'(?:["\u201d])',
                    re.IGNORECASE,
                )
                for name in terms
            }

        resolved = text
        current_depth = depth

        for ref_name in sorted(terms.keys(), key=len, reverse=True):
            if ref_name in visited:
                continue  # Avoid circular references

            # Check if this term is referenced using pre-compiled pattern
            pattern = compiled_patterns[ref_name]

            if pattern.search(resolved):
                ref_dt = terms[ref_name]
                # Recursively resolve the referenced term first
                sub_resolved, sub_depth = self._resolve_single(
                    ref_dt.definition,
                    terms,
                    visited | {ref_name},
                    depth + 1,
                    compiled_patterns,
                )
                current_depth = max(current_depth, sub_depth)

                # Replace the reference with the resolved definition
                replacement = f'{ref_name} [= {sub_resolved}]'
                resolved = pattern.sub(replacement, resolved, count=1)

        return resolved, current_depth

    def _check_overbroad(self, definition: str) -> str:
        """
        Check if a definition is overbroad.

        Returns the reason string if overbroad, empty string otherwise.
        A definition is flagged if it matches 2+ overbroad signals,
        or 1 signal from the high-severity subset.
        """
        reasons: List[str] = []
        for pattern, reason in _OVERBROAD_SIGNALS:
            if pattern.search(definition):
                reasons.append(reason)

        # Flag if 2+ signals, or the single signal is high-severity
        if len(reasons) >= 2:
            return "; ".join(reasons[:3])
        elif len(reasons) == 1 and any(
            keyword in reasons[0].lower()
            for keyword in ["all information", "everything", "totality"]
        ):
            return reasons[0]

        return ""


# Singleton
defined_terms_resolver = DefinedTermsResolver()
