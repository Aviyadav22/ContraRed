"""
Rule Engine - Pattern-based clause detection and risk assessment.

This module provides regex-based rule matching against contract text,
returning matched clauses with risk levels and exact text snippets
for frontend highlighting.

Rule Engine 2.0 adds the SmartRule system:
  - negative_patterns: match X, but NOT if Y appears in the same context window
  - context_window: chars around match for negative pattern checking (default 500)
  - escalation_conditions: conditions that raise risk (e.g., YELLOW -> RED)
  - de_escalation_conditions: conditions that lower risk (e.g., RED -> YELLOW)
  - Fixed: indemnification base risk YELLOW, escalates to RED only when one-sided
    AND (uncapped OR covers all losses)
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
import re
import hashlib
from typing import List, Optional

from app.services.text_normalizer import normalize_text


def _safe_compile_regex(pattern: str, timeout_ms: int = 100) -> re.Pattern:
    """Compile regex with basic catastrophic backtracking detection."""
    # Check for common ReDoS patterns
    redos_patterns = [
        r'\(.*\+\).*\+',      # (a+)+
        r'\(.*\*\).*\*',      # (a*)*
        r'\(.*\+\).*\*',      # (a+)*
        r'\(.*\{.*\}\).*\+',  # (a{1,})+
    ]
    for rdp in redos_patterns:
        if re.search(rdp, pattern):
            raise ValueError(f"Potentially unsafe regex pattern (ReDoS risk): {pattern[:50]}")
    # Also limit pattern length
    if len(pattern) > 500:
        raise ValueError(f"Regex pattern too long ({len(pattern)} chars, max 500)")
    return re.compile(pattern, re.IGNORECASE)

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level enumeration - strict RED/YELLOW/GREEN."""
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


@dataclass
class RulePattern:
    """A single detection rule with patterns and metadata.

    This is the original (v1) rule format.  Fully backward-compatible.
    SmartRule extends this with negative patterns and escalation logic.
    """
    id: str
    name: str
    clause_type: str
    risk_level: RiskLevel
    patterns: List[str]  # Regex patterns
    primary_position: str  # What the playbook prefers
    fallback_position: Optional[str] = None
    is_deal_breaker: bool = False


@dataclass
class SmartRule(RulePattern):
    """Rule Engine 2.0 - Enhanced rule with negative patterns and escalation.

    Extends RulePattern with:
      - negative_patterns: if ANY of these match within context_window, suppress the match
      - context_window: characters around match to check for negative patterns (default 500)
      - escalation_conditions: regex patterns that, if found in context, raise risk one level
      - de_escalation_conditions: regex patterns that, if found in context, lower risk one level
      - detection_mode: 'keywords_only' | 'ai_with_keywords' | 'ai_only' (P2 #29)

    Backward-compatible: a SmartRule can be used anywhere a RulePattern is expected.
    """
    negative_patterns: List[str] = field(default_factory=list)
    context_window: int = 500
    escalation_conditions: List[str] = field(default_factory=list)
    de_escalation_conditions: List[str] = field(default_factory=list)
    detection_mode: str = "keywords_only"


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
    # Rule Engine 2.0: track whether escalation/de-escalation was applied
    original_risk_level: Optional[RiskLevel] = None  # Set when escalation changes level
    escalation_reason: Optional[str] = None
    # Whether this match is itself a deterministic violation or only a
    # candidate that still needs semantic AI review.  Playbook rules marked
    # ``ai_with_keywords`` must not become false-positive fallback findings
    # merely because their topic is mentioned in the contract.
    detection_mode: str = "keywords_only"

    def cache_key(self) -> str:
        """Generate cache key for AI responses."""
        text_hash = hashlib.sha256(self.match_text.encode()).hexdigest()[:12]
        return f"clause:{self.rule_id}:{text_hash}"


# ---------------------------------------------------------------------------
# Risk escalation / de-escalation helpers
# ---------------------------------------------------------------------------

_RISK_ORDER = [RiskLevel.GREEN, RiskLevel.YELLOW, RiskLevel.RED]


def _escalate_risk(level: RiskLevel) -> RiskLevel:
    """Raise risk level by one step (GREEN->YELLOW, YELLOW->RED, RED stays RED)."""
    idx = _RISK_ORDER.index(level)
    return _RISK_ORDER[min(idx + 1, len(_RISK_ORDER) - 1)]


def _deescalate_risk(level: RiskLevel) -> RiskLevel:
    """Lower risk level by one step (RED->YELLOW, YELLOW->GREEN, GREEN stays GREEN)."""
    idx = _RISK_ORDER.index(level)
    return _RISK_ORDER[max(idx - 1, 0)]


# ---------------------------------------------------------------------------
# Default rules - backward-compatible list mixing RulePattern and SmartRule
# ---------------------------------------------------------------------------

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

    # --- INDEMNIFICATION: base risk YELLOW, escalates to RED only when one-sided
    #     AND (uncapped OR covers "any and all" losses).  This fixes the false
    #     positive where "mutual indemnify and hold harmless" was flagged RED.
    SmartRule(
        id="broad_indemnification",
        name="Broad Indemnification",
        clause_type="indemnification",
        risk_level=RiskLevel.YELLOW,   # <-- Changed from RED to YELLOW
        patterns=[
            r"\b(indemnify\s+and\s+hold\s+harmless)\b",
            r"\b(defend,?\s+indemnify,?\s+(and\s+)?hold\s+harmless)\b",
            r"\b(indemnif(y|ication)\s+against\s+any\s+and\s+all)\b",
            r"\b(unlimited\s+indemnif(y|ication))\b",
        ],
        primary_position="Mutual indemnification limited to third-party IP claims",
        fallback_position="Indemnification capped at contract value",
        is_deal_breaker=False,
        negative_patterns=[
            # Suppress if clause explicitly says "mutual" + "limited to"
            r"\bmutual(ly)?\b.{0,80}\blimited\s+to\b",
        ],
        context_window=500,
        escalation_conditions=[
            # Escalate YELLOW -> RED if one-sided AND (uncapped OR "any and all")
            r"\b(one[\s-]?sided|unilateral)\b",
            r"\b(uncapped|without\s+(any\s+)?cap|no\s+cap)\b",
            r"\b(any\s+and\s+all\s+(loss|damage|claim|liabilit))",
        ],
        de_escalation_conditions=[
            # De-escalate if "mutual" AND "capped at"
            r"\bmutual(ly)?\b.{0,120}\bcapped?\s+(at|to)\b",
        ],
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

    Supports both RulePattern (v1) and SmartRule (v2) transparently.
    SmartRule adds: negative_patterns, context_window, escalation/de-escalation.

    Usage:
        engine = RuleEngine()
        matches = engine.evaluate(contract_text)
        # Each match has match_text for Word highlighting
    """

    def __init__(self, rules: Optional[List[RulePattern]] = None, use_expanded: bool = True):
        """
        Initialize with custom rules or use defaults.

        Args:
            rules: Custom rules to use. If None, uses expanded rules library (75 rules)
                   or DEFAULT_RULES based on use_expanded flag.
                   Accepts both RulePattern and SmartRule instances.
            use_expanded: If True and no custom rules provided, use the Phase 5
                         expanded rules library (75 rules). If False, use legacy 16 rules.
        """
        if rules is not None:
            self.rules = rules
        elif use_expanded:
            try:
                from app.services.rules_library import ALL_RULES
                self.rules = ALL_RULES
            except ImportError:
                logger.warning("Rules library not found, falling back to default 16 rules")
                self.rules = DEFAULT_RULES
        else:
            self.rules = DEFAULT_RULES
        # Compile patterns for performance
        self._compiled_rules: List[tuple] = []
        for rule in self.rules:
            compiled_patterns = []
            for pattern in rule.patterns:
                try:
                    compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.warning("Invalid pattern in rule %s: %s", rule.id, e)

            # Compile negative patterns (SmartRule only)
            compiled_negatives = []
            if isinstance(rule, SmartRule):
                for neg_pat in rule.negative_patterns:
                    try:
                        compiled_negatives.append(re.compile(neg_pat, re.IGNORECASE))
                    except re.error as e:
                        logger.warning("Invalid negative pattern in rule %s: %s", rule.id, e)

            # Compile escalation conditions (SmartRule only)
            compiled_escalations = []
            compiled_deescalations = []
            if isinstance(rule, SmartRule):
                for esc_pat in rule.escalation_conditions:
                    try:
                        compiled_escalations.append(re.compile(esc_pat, re.IGNORECASE))
                    except re.error as e:
                        logger.warning("Invalid escalation pattern in rule %s: %s", rule.id, e)
                for deesc_pat in rule.de_escalation_conditions:
                    try:
                        compiled_deescalations.append(re.compile(deesc_pat, re.IGNORECASE))
                    except re.error as e:
                        logger.warning("Invalid de-escalation pattern in rule %s: %s", rule.id, e)

            self._compiled_rules.append((
                rule,
                compiled_patterns,
                compiled_negatives,
                compiled_escalations,
                compiled_deescalations,
            ))

    def evaluate(self, text: str) -> List[RuleMatch]:
        """
        Evaluate text against all rules.

        For SmartRule instances, applies negative pattern suppression and
        escalation/de-escalation logic on the context window around each match.

        Args:
            text: Full contract text to analyze.

        Returns:
            List of RuleMatch objects with match_text snippets.
        """
        # INPUT HYGIENE: Normalize Word document artifacts
        # This handles non-breaking spaces, smart quotes, etc.
        text = normalize_text(text)

        matches: List[RuleMatch] = []

        for rule, compiled_patterns, compiled_negatives, compiled_escalations, compiled_deescalations in self._compiled_rules:
            # Collect all matches for THIS rule, then de-duplicate
            rule_matches = []

            context_window = rule.context_window if isinstance(rule, SmartRule) else 500

            for pattern in compiled_patterns:
                for match in pattern.finditer(text):
                    start_offset = match.start()
                    end_offset = match.end()

                    # --- SmartRule: negative pattern suppression ---
                    if compiled_negatives:
                        ctx_start = max(0, start_offset - context_window)
                        ctx_end = min(len(text), end_offset + context_window)
                        context_text = text[ctx_start:ctx_end]

                        suppressed = False
                        for neg_re in compiled_negatives:
                            if neg_re.search(context_text):
                                logger.debug(
                                    "Suppressed match for rule %s due to negative pattern in context",
                                    rule.id,
                                )
                                suppressed = True
                                break
                        if suppressed:
                            continue

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
                # --- SmartRule: escalation / de-escalation ---
                effective_risk = rule.risk_level
                original_risk = None
                escalation_reason = None

                if compiled_escalations or compiled_deescalations:
                    ctx_start = max(0, m['start'] - (rule.context_window if isinstance(rule, SmartRule) else 500))
                    ctx_end = min(len(text), m['end'] + (rule.context_window if isinstance(rule, SmartRule) else 500))
                    context_text = text[ctx_start:ctx_end]

                    # Check de-escalation first (takes priority — more specific)
                    for deesc_re in compiled_deescalations:
                        if deesc_re.search(context_text):
                            new_risk = _deescalate_risk(effective_risk)
                            if new_risk != effective_risk:
                                original_risk = effective_risk
                                effective_risk = new_risk
                                escalation_reason = "De-escalated: context matches de-escalation pattern"
                                logger.debug(
                                    "Rule %s de-escalated %s -> %s",
                                    rule.id, original_risk.value, effective_risk.value,
                                )
                            break

                    # Check escalation (only if not already de-escalated)
                    if original_risk is None:
                        for esc_re in compiled_escalations:
                            if esc_re.search(context_text):
                                new_risk = _escalate_risk(effective_risk)
                                if new_risk != effective_risk:
                                    original_risk = effective_risk
                                    effective_risk = new_risk
                                    escalation_reason = "Escalated: context matches escalation pattern"
                                    logger.debug(
                                        "Rule %s escalated %s -> %s",
                                        rule.id, original_risk.value, effective_risk.value,
                                    )
                                break

                matches.append(RuleMatch(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    clause_type=rule.clause_type,
                    match_text=m['match_text'],
                    start_offset=m['start'],
                    end_offset=m['end'],
                    risk_level=effective_risk,
                    primary_position=rule.primary_position,
                    fallback_position=rule.fallback_position,
                    is_deal_breaker=rule.is_deal_breaker,
                    original_risk_level=original_risk,
                    escalation_reason=escalation_reason,
                    detection_mode=(
                        rule.detection_mode
                        if isinstance(rule, SmartRule)
                        else "keywords_only"
                    ),
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
        Remove duplicate detections of the SAME RULE on the same expanded text.

        A single contract clause can contain several independent legal issues
        (for example, an indemnity scope problem and an uncapped-liability
        problem).  De-duplicating on text alone silently discarded those
        separate issues and produced materially incomplete reviews.
        """
        seen = set()
        unique = []
        
        for m in matches:
            # Normalize text for comparison (lowercase, collapse whitespace)
            normalized = ' '.join(m.match_text.lower().split())
            key = (m.rule_id, normalized)

            if key not in seen:
                unique.append(m)
                seen.add(key)
        
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
            # P2 #29: Determine detection mode
            detection_mode = getattr(rule, 'detection_mode', None) or "keywords_only"

            # Parse detection patterns from JSONB
            raw_patterns = []
            match_type = "exact"  # Default to safe mode
            if rule.detection_patterns:
                raw_patterns = rule.detection_patterns.get("patterns", [])
                raw_patterns = raw_patterns if isinstance(raw_patterns, list) else []
                match_type = rule.detection_patterns.get("match_type", "exact")

            # P2 #29: For ai_only rules, skip regex pattern compilation entirely.
            # The rule will be detected purely by AI via the prompt context.
            if detection_mode == "ai_only":
                safe_patterns = []
            else:
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
                        else:  # regex - use as-is but validate (with ReDoS protection)
                            _safe_compile_regex(pattern)
                            safe_patterns.append(pattern)
                    except (re.error, ValueError) as e:
                        # Skip invalid/unsafe regex patterns instead of crashing
                        logger.warning("Invalid regex pattern '%s' in rule %s: %s", pattern, rule.id, e)
                        continue

            # Skip rules with no valid patterns UNLESS detection_mode is ai_only
            # (ai_only rules have no patterns — they rely entirely on AI)
            if not safe_patterns and detection_mode != "ai_only":
                continue

            # Map risk level
            risk_map = {
                "red": RiskLevel.RED,
                "yellow": RiskLevel.YELLOW,
                "green": RiskLevel.GREEN,
            }
            risk_level = risk_map.get(rule.risk_level.value.lower(), RiskLevel.YELLOW)

            # Suggested language for this rule. Lawyer-best path (Phase B9):
            # prefer the typed `primary_position` column (always populated for
            # both seeded and dashboard-authored rules); only fall back to the
            # legacy `suggested_language` JSONB for rules edited via the older
            # dashboard form that wrote {"text": str}. The `{preferred,fallback}`
            # shape from seeds is read via primary_position/fallback_position
            # directly.
            suggested_text: Optional[str] = None
            if rule.primary_position:
                suggested_text = rule.primary_position
            elif rule.suggested_language:
                # Legacy shapes: {"text": "..."} (dashboard) or
                # {"preferred": "...", "fallback": "..."} (seeds).
                suggested_text = (
                    rule.suggested_language.get("text")
                    or rule.suggested_language.get("preferred")
                )

            # Phase 4: Create SmartRule with escalation/de-escalation from detection_patterns
            negative_pats = []
            escalation_pats = []
            deescalation_pats = []
            context_win = 500
            if rule.detection_patterns:
                negative_pats = rule.detection_patterns.get("negative_patterns", [])
                negative_pats = negative_pats if isinstance(negative_pats, list) else []
                escalation_pats = rule.detection_patterns.get("escalation_conditions", [])
                escalation_pats = escalation_pats if isinstance(escalation_pats, list) else []
                deescalation_pats = rule.detection_patterns.get("de_escalation_conditions", [])
                deescalation_pats = deescalation_pats if isinstance(deescalation_pats, list) else []
                context_win = rule.detection_patterns.get("context_window", 500)

            # P2 #29: Always create SmartRule to store detection_mode
            if negative_pats or escalation_pats or deescalation_pats or detection_mode != "keywords_only":
                rules.append(SmartRule(
                    id=str(rule.id),
                    name=rule.clause_type,
                    clause_type=rule.clause_type,
                    risk_level=risk_level,
                    patterns=safe_patterns,
                    primary_position=rule.primary_position or suggested_text or "",
                    fallback_position=rule.fallback_position,
                    is_deal_breaker=rule.is_deal_breaker,
                    negative_patterns=negative_pats,
                    context_window=context_win,
                    escalation_conditions=escalation_pats,
                    de_escalation_conditions=deescalation_pats,
                    detection_mode=detection_mode,
                ))
            else:
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

        # An all-AI playbook legitimately produces an engine with zero regex
        # rules.  Falling back to the generic engine here made a selected
        # playbook appear wired while actually evaluating unrelated defaults.
        return cls(rules=rules)

    @classmethod
    def from_rule_dicts(cls, playbook_rules: list) -> "RuleEngine":
        """Create a rule engine from the dictionaries sent to the AI pipeline.

        The live analysis endpoint serializes SQLAlchemy ``PlaybookRule`` rows
        before handing them to :class:`AnalysisPipeline`.  Previously Stage 2
        ignored those dictionaries, so user-authored detection patterns never
        ran.  This mirrors :meth:`from_playbook_rules` without requiring a DB
        model or session.
        """
        rules: List[RulePattern] = []
        risk_map = {
            "red": RiskLevel.RED,
            "yellow": RiskLevel.YELLOW,
            "green": RiskLevel.GREEN,
        }

        for data in playbook_rules or []:
            if not isinstance(data, dict):
                continue

            rule_id = str(data.get("id") or data.get("rule_id") or data.get("name") or "")
            name = str(data.get("name") or data.get("rule_name") or data.get("clause_type") or "Unknown Rule")
            clause_type = str(data.get("clause_type") or name)
            detection_mode = str(data.get("detection_mode") or "keywords_only")

            detection = data.get("detection_patterns") or {}
            if isinstance(detection, list):
                detection = {"patterns": detection, "match_type": data.get("match_type", "exact")}
            if not isinstance(detection, dict):
                detection = {}

            raw_patterns = detection.get("patterns", [])
            if not isinstance(raw_patterns, list):
                raw_patterns = []
            match_type = str(detection.get("match_type") or data.get("match_type") or "exact")

            safe_patterns: List[str] = []
            if detection_mode != "ai_only":
                for pattern in raw_patterns:
                    if not isinstance(pattern, str) or not pattern.strip():
                        continue
                    try:
                        if match_type == "exact":
                            safe_patterns.append(r"\b" + re.escape(pattern.strip()) + r"\b")
                        elif match_type == "fuzzy":
                            safe_patterns.append(r"\b" + re.escape(pattern.strip()))
                        else:
                            _safe_compile_regex(pattern)
                            safe_patterns.append(pattern)
                    except (re.error, ValueError) as exc:
                        logger.warning("Invalid regex pattern '%s' in rule %s: %s", pattern, rule_id, exc)

            # AI-only rules intentionally have no regex representation.  Rules
            # with an empty/broken keyword set also cannot contribute to Stage 2.
            if not safe_patterns:
                continue

            risk_raw = data.get("risk_level", "yellow")
            risk_value = getattr(risk_raw, "value", risk_raw)
            risk_level = risk_map.get(str(risk_value).lower(), RiskLevel.YELLOW)

            def _list_field(key: str) -> List[str]:
                value = detection.get(key, [])
                return [str(v) for v in value] if isinstance(value, list) else []

            try:
                context_window = int(detection.get("context_window", 500))
            except (TypeError, ValueError):
                context_window = 500
            context_window = max(50, min(context_window, 5000))

            rules.append(SmartRule(
                id=rule_id or name,
                name=name,
                clause_type=clause_type,
                risk_level=risk_level,
                patterns=safe_patterns,
                primary_position=str(data.get("primary_position") or ""),
                fallback_position=data.get("fallback_position") or None,
                is_deal_breaker=bool(data.get("is_deal_breaker", False)),
                negative_patterns=_list_field("negative_patterns"),
                context_window=context_window,
                escalation_conditions=_list_field("escalation_conditions"),
                de_escalation_conditions=_list_field("de_escalation_conditions"),
                detection_mode=detection_mode,
            ))

        return cls(rules=rules)
