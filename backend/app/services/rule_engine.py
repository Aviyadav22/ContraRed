"""
Rule Engine - Pattern-based clause detection and risk assessment.

This module provides regex-based rule matching against contract text,
returning matched clauses with risk levels and exact text snippets
for frontend highlighting.
"""

import re
import hashlib
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.services.text_normalizer import normalize_text


class RiskLevel(str, Enum):
    """Risk level enumeration - strict RED/YELLOW/GREEN."""
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


@dataclass
class RulePattern:
    """A single detection rule with patterns and metadata."""
    id: str
    name: str
    clause_type: str
    risk_level: RiskLevel
    patterns: List[str]  # Regex patterns
    primary_position: str  # What the playbook prefers
    fallback_position: Optional[str] = None
    is_deal_breaker: bool = False


@dataclass
class RuleMatch:
    """A matched clause from the document."""
    rule_id: str
    rule_name: str
    clause_type: str
    match_text: str  # Exact text snippet for Word highlighting
    start_offset: int  # Character position in plain text
    end_offset: int
    risk_level: RiskLevel
    primary_position: str
    fallback_position: Optional[str] = None
    is_deal_breaker: bool = False
    # These will be populated by AI service
    ai_explanation: Optional[str] = None
    suggested_fix: Optional[str] = None
    
    def cache_key(self) -> str:
        """Generate cache key for AI responses."""
        text_hash = hashlib.md5(self.match_text.encode()).hexdigest()[:12]
        return f"clause:{self.rule_id}:{text_hash}"


# Default rules for common contract clause patterns
DEFAULT_RULES: List[RulePattern] = [
    # === RED RISKS (Critical) ===
    RulePattern(
        id="unlimited_liability",
        name="Unlimited Liability",
        clause_type="liability",
        risk_level=RiskLevel.RED,
        patterns=[
            r"\b(unlimited\s+liability)\b",
            r"\b(no\s+(cap|limit|limitation)\s+(on|to)\s+liability)\b",
            r"\b(without\s+limit(ation)?\s+of\s+liability)\b",
            r"\b(liability\s+shall\s+not\s+be\s+limited)\b",
        ],
        primary_position="Liability capped at 12 months of fees paid",
        fallback_position="Liability capped at total contract value",
        is_deal_breaker=True,
    ),
    RulePattern(
        id="unilateral_termination",
        name="Unilateral Termination",
        clause_type="termination",
        risk_level=RiskLevel.RED,
        patterns=[
            r"\b(terminate\s+(this\s+)?(agreement|contract)\s+(at\s+)?any\s+time)\b",
            r"\b(termination\s+without\s+(cause|reason))\b",
            r"\b(may\s+terminate\s+(immediately|forthwith)\s+without\s+(notice|cause))\b",
        ],
        primary_position="Termination requires 30 days written notice with cure period",
        is_deal_breaker=True,
    ),
    RulePattern(
        id="broad_indemnification",
        name="Broad Indemnification",
        clause_type="indemnification",
        risk_level=RiskLevel.RED,
        patterns=[
            r"\b(indemnify\s+and\s+hold\s+harmless)\b",
            r"\b(defend,?\s+indemnify,?\s+(and\s+)?hold\s+harmless)\b",
            r"\b(indemnif(y|ication)\s+against\s+any\s+and\s+all)\b",
            r"\b(unlimited\s+indemnif(y|ication))\b",
        ],
        primary_position="Mutual indemnification limited to third-party IP claims",
        fallback_position="Indemnification capped at contract value",
    ),
    RulePattern(
        id="ip_assignment",
        name="Broad IP Assignment",
        clause_type="intellectual_property",
        risk_level=RiskLevel.RED,
        patterns=[
            r"\b(work(s)?\s+for\s+hire)\b",
            r"\b(assign(s|ment)?\s+(of\s+)?all\s+(intellectual\s+property|IP))\b",
            r"\b(all\s+(rights|IP|intellectual\s+property)\s+shall\s+(belong|vest)\s+to)\b",
        ],
        primary_position="Pre-existing IP remains with original owner",
        is_deal_breaker=True,
    ),
    
    # === YELLOW RISKS (Warning) ===
    RulePattern(
        id="auto_renewal",
        name="Auto-Renewal",
        clause_type="term",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(auto(matic(ally)?)?[\s-]?renew(al|s|ed)?)\b",
            r"\b(shall\s+(automatically\s+)?renew\s+for\s+(successive|additional))\b",
            r"\b(renew(s|ed)?\s+automatically)\b",
        ],
        primary_position="30-day opt-out notice before renewal date",
    ),
    RulePattern(
        id="assignment_restriction",
        name="Assignment Restriction",
        clause_type="assignment",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(may\s+not\s+assign)\b",
            r"\b(no\s+assignment\s+without\s+consent)\b",
            r"\b(assignment\s+(is\s+)?(prohibited|restricted))\b",
        ],
        primary_position="Assignment permitted to affiliates without consent",
    ),
    RulePattern(
        id="non_compete",
        name="Non-Compete Clause",
        clause_type="restrictive_covenant",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(non[\s-]?compete)\b",
            r"\b(shall\s+not\s+compete)\b",
            r"\b(restriction\s+on\s+competition)\b",
        ],
        primary_position="Non-compete limited to 12 months in same geography",
    ),
    RulePattern(
        id="exclusive_dealing",
        name="Exclusive Dealing",
        clause_type="exclusivity",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(exclusive\s+(right|license|agreement))\b",
            r"\b(sole\s+and\s+exclusive)\b",
            r"\b(exclusivity\s+(period|term|clause))\b",
        ],
        primary_position="Non-exclusive arrangement or limited exclusivity period",
    ),
    RulePattern(
        id="confidentiality_term",
        name="Perpetual Confidentiality",
        clause_type="confidentiality",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(perpetual\s+confidentiality)\b",
            r"\b(confidential(ity)?\s+(in\s+)?perpetuity)\b",
            r"\b(survive\s+(indefinitely|forever|in\s+perpetuity))\b",
        ],
        primary_position="Confidentiality obligations expire 3-5 years after termination",
    ),
    RulePattern(
        id="non_solicitation",
        name="Non-Solicitation Clause",
        clause_type="restrictive_covenant",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            # Flexible regex to catch "solicit...employees" with words in between
            r"\b(non[\s-]?solicit(ation)?)\b",
            r"\b(shall\s+not\s+solicit)\b",
            r"solicit.{0,100}(employee|personnel|staff|contractor)",
            r"\b(solicit,?\s+(induce,?\s+)?(recruit|hire|employ))\b",
            r"\b(recruit(ing)?\s+(any\s+)?employee)\b",
        ],
        primary_position="Non-solicitation limited to 12 months post-termination",
    ),
    RulePattern(
        id="reverse_engineering",
        name="Reverse Engineering Prohibition",
        clause_type="restrictive_covenant",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(reverse\s+engineer(ing)?)\b",
            r"\b(decompil(e|ation)|disassembl(e|y))\b",
            r"\b(derive\s+source\s+code)\b",
        ],
        primary_position="Reverse engineering permitted for interoperability",
    ),
    
    # === GREEN (Standard/Acceptable) ===
    RulePattern(
        id="governing_law",
        name="Governing Law",
        clause_type="governing_law",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(govern(ed|ing)\s+(by|law))\b",
            r"\b(laws\s+of\s+(the\s+)?(state|country|jurisdiction))\b",
            r"\b(applicable\s+law)\b",
        ],
        primary_position="Standard governing law clause",
    ),
    RulePattern(
        id="notice_provision",
        name="Notice Provision",
        clause_type="notice",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(notice(s)?\s+(shall|must|should)\s+be\s+(sent|given|provided))\b",
            r"\b(written\s+notice)\b",
        ],
        primary_position="Standard notice provision",
    ),
]


class RuleEngine:
    """
    Regex-based rule engine for contract clause detection.
    
    Usage:
        engine = RuleEngine()
        matches = engine.evaluate(contract_text)
        # Each match has match_text for Word highlighting
    """
    
    def __init__(self, rules: Optional[List[RulePattern]] = None):
        """
        Initialize with custom rules or use defaults.
        
        Args:
            rules: Custom rules to use. If None, uses DEFAULT_RULES.
        """
        self.rules = rules or DEFAULT_RULES
        # Compile patterns for performance
        self._compiled_rules = []
        for rule in self.rules:
            compiled_patterns = []
            for pattern in rule.patterns:
                try:
                    compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    print(f"Warning: Invalid pattern in rule {rule.id}: {e}")
            self._compiled_rules.append((rule, compiled_patterns))
    
    def evaluate(self, text: str) -> List[RuleMatch]:
        """
        Evaluate text against all rules.
        
        Args:
            text: Full contract text to analyze.
            
        Returns:
            List of RuleMatch objects with match_text snippets.
        """
        # INPUT HYGIENE: Normalize Word document artifacts
        # This handles non-breaking spaces, smart quotes, etc.
        text = normalize_text(text)
        
        matches: List[RuleMatch] = []
        
        for rule, compiled_patterns in self._compiled_rules:
            # Collect all matches for THIS rule, then de-duplicate
            rule_matches = []
            
            for pattern in compiled_patterns:
                for match in pattern.finditer(text):
                    match_text = match.group(0)
                    start_offset = match.start()
                    end_offset = match.end()
                    
                    # Expand match to get surrounding context (full sentence)
                    expanded_text = self._expand_to_sentence(text, start_offset, end_offset)
                    
                    rule_matches.append({
                        'start': start_offset,
                        'end': end_offset,
                        'match_text': expanded_text,
                    })
            
            # De-duplicate overlapping matches for this rule
            unique_matches = self._remove_overlapping_matches(rule_matches)
            
            for m in unique_matches:
                matches.append(RuleMatch(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    clause_type=rule.clause_type,
                    match_text=m['match_text'],
                    start_offset=m['start'],
                    end_offset=m['end'],
                    risk_level=rule.risk_level,
                    primary_position=rule.primary_position,
                    fallback_position=rule.fallback_position,
                    is_deal_breaker=rule.is_deal_breaker,
                ))
        
        # De-duplicate across ALL rules (same text matched by different rules)
        matches = self._dedupe_cross_rule_matches(matches)
        
        # Sort by position in document
        matches.sort(key=lambda m: m.start_offset)
        
        return matches
    
    def _remove_overlapping_matches(self, matches: List[dict]) -> List[dict]:
        """
        Remove overlapping matches for the SAME rule.
        
        Keep only one match per "sentence region" - if two matches are within
        the same general area of text, keep the one with most context.
        """
        if not matches:
            return []
        
        # Sort by start position
        sorted_matches = sorted(matches, key=lambda m: m['start'])
        
        result = []
        
        for m in sorted_matches:
            is_duplicate = False
            
            for existing in result:
                # Check if matches are in the same region (within 100 chars of each other)
                # This catches "reverse engineer" and "decompile" in the same sentence
                if abs(m['start'] - existing['start']) < 100:
                    is_duplicate = True
                    # Keep the one with longer expanded text
                    if len(m['match_text']) > len(existing['match_text']):
                        result.remove(existing)
                        result.append(m)
                    break
            
            if not is_duplicate:
                result.append(m)
        
        return result
    
    def _dedupe_cross_rule_matches(self, matches: List[RuleMatch]) -> List[RuleMatch]:
        """
        Remove duplicate detections where the SAME expanded text was matched.
        
        This prevents showing 'Reverse Engineering' 4 times for the same clause.
        """
        seen_texts = set()
        unique = []
        
        for m in matches:
            # Normalize text for comparison (lowercase, collapse whitespace)
            normalized = ' '.join(m.match_text.lower().split())
            
            if normalized not in seen_texts:
                unique.append(m)
                seen_texts.add(normalized)
        
        return unique
    
    def _expand_to_sentence(
        self, 
        text: str, 
        start: int, 
        end: int,
        max_length: int = 300
    ) -> str:
        """
        Expand match to include the full sentence for better context.
        
        Args:
            text: Full document text
            start: Match start position
            end: Match end position
            max_length: Maximum length of expanded text
            
        Returns:
            Expanded text snippet (full sentence or paragraph)
        """
        # Find sentence boundaries
        sentence_ends = '.!?;'
        
        # Look backward for sentence start
        sent_start = start
        while sent_start > 0 and text[sent_start - 1] not in sentence_ends:
            sent_start -= 1
            if start - sent_start > max_length // 2:
                break
        
        # Skip whitespace
        while sent_start < start and text[sent_start] in ' \n\t':
            sent_start += 1
        
        # Look forward for sentence end
        sent_end = end
        while sent_end < len(text) and text[sent_end - 1] not in sentence_ends:
            sent_end += 1
            if sent_end - end > max_length // 2:
                break
        
        return text[sent_start:sent_end].strip()
    
    def get_risk_summary(self, matches: List[RuleMatch]) -> dict:
        """
        Generate summary counts by risk level.
        
        Returns:
            Dict with red, yellow, green counts
        """
        summary = {"red": 0, "yellow": 0, "green": 0}
        for match in matches:
            level = match.risk_level.value.lower()
            if level in summary:
                summary[level] += 1
        return summary
    
    @staticmethod
    def get_default_rules() -> List[RulePattern]:
        """Get the default built-in rules."""
        return DEFAULT_RULES.copy()
    
    @classmethod
    def from_playbook_rules(cls, playbook_rules: list) -> "RuleEngine":
        """
        Create a RuleEngine from PlaybookRule database objects.
        
        Args:
            playbook_rules: List of PlaybookRule model instances
            
        Returns:
            RuleEngine configured with the playbook's rules
        """
        rules = []
        for rule in playbook_rules:
            # Parse detection patterns from JSONB
            raw_patterns = []
            match_type = "exact"  # Default to safe mode
            if rule.detection_patterns:
                raw_patterns = rule.detection_patterns.get("patterns", [])
                raw_patterns = raw_patterns if isinstance(raw_patterns, list) else []
                match_type = rule.detection_patterns.get("match_type", "exact")
            
            # Convert patterns based on match_type
            safe_patterns = []
            for pattern in raw_patterns:
                if not pattern:
                    continue
                try:
                    if match_type == "exact":
                        # Escape special regex characters for non-regex users
                        safe_patterns.append(r"\b" + re.escape(pattern) + r"\b")
                    elif match_type == "fuzzy":
                        # Word boundary matching without full regex
                        safe_patterns.append(r"\b" + re.escape(pattern))
                    else:  # regex - use as-is but validate
                        # Test compile to catch bad regex
                        re.compile(pattern, re.IGNORECASE)
                        safe_patterns.append(pattern)
                except re.error as e:
                    # Skip invalid regex patterns instead of crashing
                    print(f"Warning: Invalid regex pattern '{pattern}' in rule {rule.id}: {e}")
                    continue
            
            # Skip rules with no valid patterns
            if not safe_patterns:
                continue
            
            # Map risk level
            risk_map = {
                "red": RiskLevel.RED,
                "yellow": RiskLevel.YELLOW,
                "green": RiskLevel.GREEN,
            }
            risk_level = risk_map.get(rule.risk_level.value.lower(), RiskLevel.YELLOW)
            
            # Get suggested language
            suggested_text = None
            if rule.suggested_language:
                suggested_text = rule.suggested_language.get("text")
            
            rules.append(RulePattern(
                id=str(rule.id),
                name=rule.clause_type,
                clause_type=rule.clause_type,
                risk_level=risk_level,
                patterns=safe_patterns,
                primary_position=rule.primary_position or suggested_text or "",
                fallback_position=rule.fallback_position,
                is_deal_breaker=rule.is_deal_breaker,
            ))
        
        return cls(rules=rules) if rules else cls()
