"""
Scope Analyzer - Deterministic scope analysis for detected clauses.

Phase 5: Layer 2 of the three-layer detection system.
Analyzes breadth, mutuality, financial exposure, duration, and triggers
for each detected clause. Zero AI cost — purely regex/heuristic-based.
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class Breadth(str, Enum):
    NARROW = "narrow"
    STANDARD = "standard"
    BROAD = "broad"
    UNLIMITED = "unlimited"


class Mutuality(str, Enum):
    MUTUAL = "mutual"
    ONE_SIDED_FAVORABLE = "one_sided_favorable"
    ONE_SIDED_UNFAVORABLE = "one_sided_unfavorable"
    UNCLEAR = "unclear"


class FinancialExposure(str, Enum):
    CAPPED = "capped"
    UNCAPPED = "uncapped"
    NOT_APPLICABLE = "not_applicable"


class Duration(str, Enum):
    FIXED_TERM = "fixed_term"
    PERPETUAL = "perpetual"
    SURVIVAL = "survival"  # survives termination
    NOT_SPECIFIED = "not_specified"


class TriggerType(str, Enum):
    MATERIAL_BREACH = "material_breach"
    ANY_BREACH = "any_breach"
    NEGLIGENCE = "negligence"
    GROSS_NEGLIGENCE = "gross_negligence"
    WILLFUL_MISCONDUCT = "willful_misconduct"
    NONE_SPECIFIED = "none_specified"


@dataclass
class ScopeResult:
    """Scope analysis result for a single clause."""
    rule_id: str
    clause_type: str
    match_text: str

    breadth: Breadth = Breadth.STANDARD
    mutuality: Mutuality = Mutuality.UNCLEAR
    financial_exposure: FinancialExposure = FinancialExposure.NOT_APPLICABLE
    cap_amount: Optional[str] = None  # e.g., "$1,000,000" or "12 months fees"
    duration: Duration = Duration.NOT_SPECIFIED
    duration_value: Optional[str] = None  # e.g., "24 months", "3 years"
    trigger: TriggerType = TriggerType.NONE_SPECIFIED

    scope_score: float = 5.0  # 1-10, higher = more risk
    risk_adjustment: int = 0  # -1, 0, or +1 to adjust risk level
    analysis_notes: List[str] = field(default_factory=list)


@dataclass
class ScopeAnalysisResult:
    """Complete scope analysis for all clauses in a document."""
    results: List[ScopeResult] = field(default_factory=list)
    coverage_score: float = 0.0  # % of clause types covered by rules
    clause_types_found: List[str] = field(default_factory=list)
    clause_types_missing: List[str] = field(default_factory=list)
    total_clauses_analyzed: int = 0


class ScopeAnalyzer:
    """
    Deterministic scope analyzer for contract clauses.

    Analyzes detected clauses for breadth, mutuality, financial exposure,
    duration, and trigger conditions. Returns a scope_score that can
    adjust risk levels up or down.
    """

    # ALL 75 clause types from the taxonomy
    ALL_CLAUSE_TYPES = [
        # Formation & Structure
        "definitions", "recitals", "entire_agreement", "amendments", "severability",
        # Term & Termination
        "duration", "auto_renewal", "termination_for_cause", "termination_for_convenience",
        "cure_period", "survival", "transition",
        # Financial
        "payment_terms", "late_payment", "price_escalation", "taxes",
        "set_off", "audit_rights", "most_favored_nation", "currency",
        # Liability & Indemnification
        "liability_cap", "unlimited_liability", "consequential_damages",
        "indemnification", "indemnification_procedure", "third_party_claims",
        "limitation_period", "insurance",
        # IP
        "ip_ownership", "ip_assignment", "license_grant", "background_ip",
        "ip_indemnification", "open_source", "moral_rights",
        # Confidentiality & Data
        "confidentiality", "confidentiality_exceptions", "confidentiality_term",
        "return_of_materials", "data_protection", "data_processing_agreement",
        "breach_notification", "cross_border_transfer",
        # Reps & Warranties
        "reps_warranties", "as_is_disclaimer", "service_level",
        "authority", "non_infringement", "compliance_warranty",
        # Restrictive Covenants
        "non_compete", "non_solicitation", "customer_non_solicitation",
        "exclusivity", "reverse_engineering",
        # Governance & Disputes
        "governing_law", "jurisdiction", "arbitration", "mediation",
        "injunctive_relief", "jury_waiver",
        # Operational
        "force_majeure", "assignment", "change_of_control", "subcontracting",
        "notices", "anti_bribery", "sanctions", "regulatory_compliance", "business_continuity",
        # SaaS/Technology
        "sla", "sla_credits", "data_portability", "security_standards",
        "acceptable_use", "api_rights",
    ]

    # Breadth indicators
    BROAD_INDICATORS = [
        r"\b(any\s+and\s+all)\b",
        r"\b(all\s+(claims|losses|damages|liabilities))\b",
        r"\b(without\s+limitation)\b",
        r"\b(including\s+but\s+not\s+limited\s+to)\b",
        r"\b(whatsoever)\b",
        r"\b(of\s+any\s+kind\s+or\s+nature)\b",
        r"\b(whether\s+direct\s+or\s+indirect)\b",
        r"\b(all\s+information)\b",
    ]

    NARROW_INDICATORS = [
        r"\b(limited\s+to)\b",
        r"\b(solely|only|exclusively)\b",
        r"\b(specific(ally)?)\b",
        r"\b(to\s+the\s+extent)\b",
        r"\b(reasonable)\b",
        r"\b(proportionate)\b",
    ]

    UNLIMITED_INDICATORS = [
        r"\b(unlimited|without\s+limit(ation)?)\b",
        r"\b(no\s+(cap|limit|ceiling|maximum))\b",
        r"\b(uncapped)\b",
    ]

    # Mutuality indicators
    MUTUAL_INDICATORS = [
        r"\b(each\s+party|both\s+parties|mutual(ly)?)\b",
        r"\b(either\s+party)\b",
        r"\b(the\s+parties\s+shall)\b",
        r"\b(reciprocal)\b",
    ]

    ONE_SIDED_INDICATORS = [
        r"\b(the\s+(company|vendor|provider|licensor|employer)\s+shall\s+not)\b",
        r"\b(the\s+(customer|client|licensee|employee)\s+shall)\b",
        r"\b(you\s+(agree|shall|will|must))\b",
        r"\b(solely\s+at\s+(the|our)\s+discretion)\b",
    ]

    # Financial cap patterns
    CAP_PATTERNS = [
        r"(?:capped?\s+(?:at|to)|limited\s+to|shall\s+not\s+exceed|maximum\s+(?:of|amount))\s*(?:(?:USD?|INR|GBP|EUR|£|\$|₹)\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|lakh|crore|thousand))?|[\d,]+(?:\.\d+)?\s*(?:months?|years?)\s*(?:of\s+)?(?:fees?|charges?|contract\s+value|total\s+(?:contract\s+)?value))",
        r"(?:aggregate\s+liability|total\s+liability)\s+(?:shall\s+not\s+exceed|is\s+limited\s+to)\s+(.+?)(?:\.|;|$)",
    ]

    # Duration patterns
    PERPETUAL_PATTERNS = [
        r"\b(perpetual(ly)?|indefinite(ly)?|forever|in\s+perpetuity)\b",
        r"\b(survive\s+(?:indefinitely|in\s+perpetuity|forever))\b",
        r"\b(irrevocable)\b",
    ]

    FIXED_TERM_PATTERN = r"(\d+)\s*(months?|years?|days?|weeks?)"

    SURVIVAL_PATTERNS = [
        r"\b(shall\s+survive|survive\s+termination|surviving\s+provisions?)\b",
        r"\b(notwithstanding\s+(?:any\s+)?termination)\b",
    ]

    # Trigger patterns
    TRIGGER_PATTERNS = {
        TriggerType.MATERIAL_BREACH: [r"\b(material\s+breach)\b", r"\b(material\s+default)\b"],
        TriggerType.ANY_BREACH: [r"\b(any\s+breach)\b", r"\b(breach\s+of\s+any)\b"],
        TriggerType.NEGLIGENCE: [r"\b(negligence)\b", r"\b(negligent\s+act)\b"],
        TriggerType.GROSS_NEGLIGENCE: [r"\b(gross\s+negligence)\b", r"\b(willful\s+misconduct)\b"],
        TriggerType.WILLFUL_MISCONDUCT: [r"\b(willful|wilful)\s+misconduct\b", r"\b(intentional\s+breach)\b"],
    }

    def __init__(self):
        # Pre-compile all patterns
        self._broad = [re.compile(p, re.IGNORECASE) for p in self.BROAD_INDICATORS]
        self._narrow = [re.compile(p, re.IGNORECASE) for p in self.NARROW_INDICATORS]
        self._unlimited = [re.compile(p, re.IGNORECASE) for p in self.UNLIMITED_INDICATORS]
        self._mutual = [re.compile(p, re.IGNORECASE) for p in self.MUTUAL_INDICATORS]
        self._one_sided = [re.compile(p, re.IGNORECASE) for p in self.ONE_SIDED_INDICATORS]
        self._caps = [re.compile(p, re.IGNORECASE) for p in self.CAP_PATTERNS]
        self._perpetual = [re.compile(p, re.IGNORECASE) for p in self.PERPETUAL_PATTERNS]
        self._fixed_term = re.compile(self.FIXED_TERM_PATTERN, re.IGNORECASE)
        self._survival = [re.compile(p, re.IGNORECASE) for p in self.SURVIVAL_PATTERNS]
        self._triggers = {
            k: [re.compile(p, re.IGNORECASE) for p in pats]
            for k, pats in self.TRIGGER_PATTERNS.items()
        }

    def analyze(self, matches: list, full_text: str) -> ScopeAnalysisResult:
        """
        Analyze scope of all matched clauses.

        Args:
            matches: List of RuleMatch objects from rule engine
            full_text: Full contract text for context extraction

        Returns:
            ScopeAnalysisResult with per-clause analysis and coverage metrics
        """
        results = []
        clause_types_found = set()

        for match in matches:
            # Get extended context (500 chars before and after match)
            ctx_start = max(0, match.start_offset - 500)
            ctx_end = min(len(full_text), match.end_offset + 500)
            context = full_text[ctx_start:ctx_end]

            result = self._analyze_clause(match, context)
            results.append(result)
            clause_types_found.add(match.clause_type)

        # Calculate coverage
        found = list(clause_types_found)
        missing = [ct for ct in self.ALL_CLAUSE_TYPES if ct not in clause_types_found]
        coverage = (len(found) / len(self.ALL_CLAUSE_TYPES)) * 100 if self.ALL_CLAUSE_TYPES else 0

        return ScopeAnalysisResult(
            results=results,
            coverage_score=round(coverage, 1),
            clause_types_found=sorted(found),
            clause_types_missing=sorted(missing),
            total_clauses_analyzed=len(results),
        )

    def _analyze_clause(self, match, context: str) -> ScopeResult:
        """Analyze a single clause match."""
        result = ScopeResult(
            rule_id=match.rule_id,
            clause_type=match.clause_type,
            match_text=match.match_text,
        )

        # Analyze each dimension
        result.breadth = self._detect_breadth(context)
        result.mutuality = self._detect_mutuality(context)
        result.financial_exposure, result.cap_amount = self._detect_financial_exposure(context)
        result.duration, result.duration_value = self._detect_duration(context)
        result.trigger = self._detect_trigger(context)

        # Calculate composite scope score
        result.scope_score = self._calculate_scope_score(result)

        # Determine risk adjustment
        if result.scope_score >= 7.5:
            result.risk_adjustment = 1  # escalate
            result.analysis_notes.append("High scope score suggests elevated risk")
        elif result.scope_score <= 3.0:
            result.risk_adjustment = -1  # de-escalate
            result.analysis_notes.append("Low scope score suggests reduced risk")

        return result

    def _detect_breadth(self, text: str) -> Breadth:
        """Detect clause breadth."""
        unlimited_count = sum(1 for p in self._unlimited if p.search(text))
        if unlimited_count > 0:
            return Breadth.UNLIMITED

        broad_count = sum(1 for p in self._broad if p.search(text))
        narrow_count = sum(1 for p in self._narrow if p.search(text))

        if broad_count >= 2:
            return Breadth.BROAD
        elif narrow_count >= 2:
            return Breadth.NARROW
        elif broad_count > narrow_count:
            return Breadth.BROAD
        elif narrow_count > broad_count:
            return Breadth.NARROW
        return Breadth.STANDARD

    def _detect_mutuality(self, text: str) -> Mutuality:
        """Detect mutuality of obligations."""
        mutual_count = sum(1 for p in self._mutual if p.search(text))
        one_sided_count = sum(1 for p in self._one_sided if p.search(text))

        if mutual_count > 0 and one_sided_count == 0:
            return Mutuality.MUTUAL
        elif one_sided_count > 0 and mutual_count == 0:
            return Mutuality.ONE_SIDED_UNFAVORABLE
        elif mutual_count > 0 and one_sided_count > 0:
            return Mutuality.ONE_SIDED_FAVORABLE  # mixed signals
        return Mutuality.UNCLEAR

    def _detect_financial_exposure(self, text: str) -> Tuple[FinancialExposure, Optional[str]]:
        """Detect financial caps or uncapped exposure."""
        for p in self._caps:
            m = p.search(text)
            if m:
                cap_text = m.group(0).strip()
                return FinancialExposure.CAPPED, cap_text

        # Check for explicit uncapped language
        for p in self._unlimited:
            if p.search(text):
                return FinancialExposure.UNCAPPED, None

        return FinancialExposure.NOT_APPLICABLE, None

    def _detect_duration(self, text: str) -> Tuple[Duration, Optional[str]]:
        """Detect clause duration."""
        # Check perpetual first
        for p in self._perpetual:
            if p.search(text):
                return Duration.PERPETUAL, "perpetual"

        # Check survival
        for p in self._survival:
            if p.search(text):
                # Look for a specific survival period
                term_match = self._fixed_term.search(text)
                if term_match:
                    return Duration.SURVIVAL, f"{term_match.group(1)} {term_match.group(2)}"
                return Duration.SURVIVAL, None

        # Check fixed term
        term_match = self._fixed_term.search(text)
        if term_match:
            return Duration.FIXED_TERM, f"{term_match.group(1)} {term_match.group(2)}"

        return Duration.NOT_SPECIFIED, None

    def _detect_trigger(self, text: str) -> TriggerType:
        """Detect breach/trigger type."""
        # Check from most specific to least specific
        for trigger_type in [TriggerType.WILLFUL_MISCONDUCT, TriggerType.GROSS_NEGLIGENCE,
                             TriggerType.NEGLIGENCE, TriggerType.MATERIAL_BREACH, TriggerType.ANY_BREACH]:
            for p in self._triggers[trigger_type]:
                if p.search(text):
                    return trigger_type
        return TriggerType.NONE_SPECIFIED

    def _calculate_scope_score(self, result: ScopeResult) -> float:
        """
        Calculate composite scope score (1-10).

        Weights:
        - Breadth: 25%
        - Mutuality: 25%
        - Financial exposure: 25%
        - Duration: 15%
        - Trigger: 10%
        """
        breadth_scores = {
            Breadth.NARROW: 2.0, Breadth.STANDARD: 5.0,
            Breadth.BROAD: 7.5, Breadth.UNLIMITED: 10.0,
        }
        mutuality_scores = {
            Mutuality.MUTUAL: 3.0, Mutuality.UNCLEAR: 5.0,
            Mutuality.ONE_SIDED_FAVORABLE: 6.0, Mutuality.ONE_SIDED_UNFAVORABLE: 9.0,
        }
        exposure_scores = {
            FinancialExposure.NOT_APPLICABLE: 5.0,
            FinancialExposure.CAPPED: 3.0, FinancialExposure.UNCAPPED: 9.0,
        }
        duration_scores = {
            Duration.NOT_SPECIFIED: 5.0, Duration.FIXED_TERM: 3.0,
            Duration.SURVIVAL: 6.0, Duration.PERPETUAL: 9.0,
        }
        trigger_scores = {
            TriggerType.NONE_SPECIFIED: 5.0, TriggerType.MATERIAL_BREACH: 4.0,
            TriggerType.GROSS_NEGLIGENCE: 5.0, TriggerType.NEGLIGENCE: 6.5,
            TriggerType.ANY_BREACH: 8.0, TriggerType.WILLFUL_MISCONDUCT: 3.0,
        }

        score = (
            breadth_scores.get(result.breadth, 5.0) * 0.25 +
            mutuality_scores.get(result.mutuality, 5.0) * 0.25 +
            exposure_scores.get(result.financial_exposure, 5.0) * 0.25 +
            duration_scores.get(result.duration, 5.0) * 0.15 +
            trigger_scores.get(result.trigger, 5.0) * 0.10
        )

        return round(score, 1)

    def get_coverage_report(self, matches: list) -> Dict:
        """
        Generate a coverage report showing which clause types are present/missing.
        """
        found_types = set(m.clause_type for m in matches)
        all_types = set(self.ALL_CLAUSE_TYPES)
        missing = all_types - found_types

        # Group by category
        categories = {
            "Formation & Structure": ["definitions", "recitals", "entire_agreement", "amendments", "severability"],
            "Term & Termination": ["duration", "auto_renewal", "termination_for_cause", "termination_for_convenience", "cure_period", "survival", "transition"],
            "Financial": ["payment_terms", "late_payment", "price_escalation", "taxes", "set_off", "audit_rights", "most_favored_nation", "currency"],
            "Liability & Indemnification": ["liability_cap", "unlimited_liability", "consequential_damages", "indemnification", "indemnification_procedure", "third_party_claims", "limitation_period", "insurance"],
            "Intellectual Property": ["ip_ownership", "ip_assignment", "license_grant", "background_ip", "ip_indemnification", "open_source", "moral_rights"],
            "Confidentiality & Data": ["confidentiality", "confidentiality_exceptions", "confidentiality_term", "return_of_materials", "data_protection", "data_processing_agreement", "breach_notification", "cross_border_transfer"],
            "Reps & Warranties": ["reps_warranties", "as_is_disclaimer", "service_level", "authority", "non_infringement", "compliance_warranty"],
            "Restrictive Covenants": ["non_compete", "non_solicitation", "customer_non_solicitation", "exclusivity", "reverse_engineering"],
            "Governance & Disputes": ["governing_law", "jurisdiction", "arbitration", "mediation", "injunctive_relief", "jury_waiver"],
            "Operational": ["force_majeure", "assignment", "change_of_control", "subcontracting", "notices", "anti_bribery", "sanctions", "regulatory_compliance", "business_continuity"],
            "SaaS/Technology": ["sla", "sla_credits", "data_portability", "security_standards", "acceptable_use", "api_rights"],
        }

        category_coverage = {}
        for cat_name, cat_types in categories.items():
            cat_found = [t for t in cat_types if t in found_types]
            cat_missing = [t for t in cat_types if t not in found_types]
            category_coverage[cat_name] = {
                "found": cat_found,
                "missing": cat_missing,
                "coverage_pct": round(len(cat_found) / len(cat_types) * 100, 1) if cat_types else 0,
            }

        return {
            "total_clause_types": len(all_types),
            "found_count": len(found_types),
            "missing_count": len(missing),
            "overall_coverage_pct": round(len(found_types) / len(all_types) * 100, 1),
            "coverage_note": f"Coverage based on {len(found_types)}/{len(all_types)} clause types relevant to this contract type. Not all clause types apply to every agreement (e.g., SaaS terms are irrelevant to NDAs).",
            "categories": category_coverage,
        }


# Module-level singleton
scope_analyzer = ScopeAnalyzer()
