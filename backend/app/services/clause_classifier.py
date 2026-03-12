"""
Clause Classifier - Deterministic clause type identification.

Stage 2 of the analysis pipeline: takes extracted contract text sections
and classifies each into one of 30 clause categories using keyword matching
and structural analysis. Ambiguous clauses are marked for AI classification.

Zero AI dependency for the deterministic path.
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Clause taxonomy — 30 categories across 8 groups
# ---------------------------------------------------------------------------

class ClauseGroup(str, Enum):
    """Top-level grouping for clause categories."""
    FORMATION = "formation"
    TERM = "term"
    FINANCIAL = "financial"
    LIABILITY = "liability"
    IP = "ip"
    CONFIDENTIALITY = "confidentiality"
    GOVERNANCE = "governance"
    RESTRICTIVE = "restrictive"


class ClauseType(str, Enum):
    """The 30 clause categories."""
    # Formation
    DEFINITIONS = "definitions"
    RECITALS = "recitals"
    ENTIRE_AGREEMENT = "entire_agreement"
    AMENDMENTS = "amendments"
    SEVERABILITY = "severability"

    # Term
    DURATION = "duration"
    AUTO_RENEWAL = "auto_renewal"
    TERMINATION_FOR_CAUSE = "termination_for_cause"
    TERMINATION_FOR_CONVENIENCE = "termination_for_convenience"
    CURE_PERIOD = "cure_period"
    SURVIVAL = "survival"

    # Financial
    PAYMENT_TERMS = "payment_terms"
    LATE_PAYMENT = "late_payment"
    PRICE_ESCALATION = "price_escalation"
    TAXES = "taxes"
    AUDIT_RIGHTS = "audit_rights"

    # Liability
    LIABILITY_CAP = "liability_cap"
    CONSEQUENTIAL_DAMAGES = "consequential_damages"
    INDEMNIFICATION_SCOPE = "indemnification_scope"
    INSURANCE = "insurance"

    # IP
    IP_OWNERSHIP = "ip_ownership"
    LICENSE_GRANT = "license_grant"
    IP_INDEMNIFICATION = "ip_indemnification"

    # Confidentiality
    CONFIDENTIALITY_OBLIGATIONS = "confidentiality_obligations"
    CONFIDENTIALITY_EXCEPTIONS = "confidentiality_exceptions"
    DATA_PROTECTION = "data_protection"
    BREACH_NOTIFICATION = "breach_notification"

    # Governance
    GOVERNING_LAW = "governing_law"
    JURISDICTION = "jurisdiction"
    ARBITRATION = "arbitration"
    FORCE_MAJEURE = "force_majeure"

    # Restrictive
    NON_COMPETE = "non_compete"
    NON_SOLICITATION = "non_solicitation"
    EXCLUSIVITY = "exclusivity"

    # Fallback
    UNKNOWN = "unknown"


# Map each ClauseType to its group
_TYPE_TO_GROUP: Dict[ClauseType, ClauseGroup] = {
    ClauseType.DEFINITIONS: ClauseGroup.FORMATION,
    ClauseType.RECITALS: ClauseGroup.FORMATION,
    ClauseType.ENTIRE_AGREEMENT: ClauseGroup.FORMATION,
    ClauseType.AMENDMENTS: ClauseGroup.FORMATION,
    ClauseType.SEVERABILITY: ClauseGroup.FORMATION,
    ClauseType.DURATION: ClauseGroup.TERM,
    ClauseType.AUTO_RENEWAL: ClauseGroup.TERM,
    ClauseType.TERMINATION_FOR_CAUSE: ClauseGroup.TERM,
    ClauseType.TERMINATION_FOR_CONVENIENCE: ClauseGroup.TERM,
    ClauseType.CURE_PERIOD: ClauseGroup.TERM,
    ClauseType.SURVIVAL: ClauseGroup.TERM,
    ClauseType.PAYMENT_TERMS: ClauseGroup.FINANCIAL,
    ClauseType.LATE_PAYMENT: ClauseGroup.FINANCIAL,
    ClauseType.PRICE_ESCALATION: ClauseGroup.FINANCIAL,
    ClauseType.TAXES: ClauseGroup.FINANCIAL,
    ClauseType.AUDIT_RIGHTS: ClauseGroup.FINANCIAL,
    ClauseType.LIABILITY_CAP: ClauseGroup.LIABILITY,
    ClauseType.CONSEQUENTIAL_DAMAGES: ClauseGroup.LIABILITY,
    ClauseType.INDEMNIFICATION_SCOPE: ClauseGroup.LIABILITY,
    ClauseType.INSURANCE: ClauseGroup.LIABILITY,
    ClauseType.IP_OWNERSHIP: ClauseGroup.IP,
    ClauseType.LICENSE_GRANT: ClauseGroup.IP,
    ClauseType.IP_INDEMNIFICATION: ClauseGroup.IP,
    ClauseType.CONFIDENTIALITY_OBLIGATIONS: ClauseGroup.CONFIDENTIALITY,
    ClauseType.CONFIDENTIALITY_EXCEPTIONS: ClauseGroup.CONFIDENTIALITY,
    ClauseType.DATA_PROTECTION: ClauseGroup.CONFIDENTIALITY,
    ClauseType.BREACH_NOTIFICATION: ClauseGroup.CONFIDENTIALITY,
    ClauseType.GOVERNING_LAW: ClauseGroup.GOVERNANCE,
    ClauseType.JURISDICTION: ClauseGroup.GOVERNANCE,
    ClauseType.ARBITRATION: ClauseGroup.GOVERNANCE,
    ClauseType.FORCE_MAJEURE: ClauseGroup.GOVERNANCE,
    ClauseType.NON_COMPETE: ClauseGroup.RESTRICTIVE,
    ClauseType.NON_SOLICITATION: ClauseGroup.RESTRICTIVE,
    ClauseType.EXCLUSIVITY: ClauseGroup.RESTRICTIVE,
    ClauseType.UNKNOWN: ClauseGroup.FORMATION,  # fallback
}


@dataclass
class ClassifiedClause:
    """A single classified clause from the contract."""

    clause_type: ClauseType
    group: ClauseGroup
    confidence: float  # 0.0 - 1.0
    start_position: int
    end_position: int
    text_snippet: str  # First 300 chars for display
    full_text: str
    heading: str = ""  # Section heading if detected
    needs_ai_review: bool = False  # Flag for ambiguous classification
    matched_keywords: List[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    """Complete classification result for a contract."""

    clauses: List[ClassifiedClause]
    clause_count: int
    group_distribution: Dict[str, int]  # group_name -> count
    type_distribution: Dict[str, int]  # type_name -> count
    ambiguous_count: int  # Number of clauses needing AI review

    def get_clauses_by_type(self, clause_type: ClauseType) -> List[ClassifiedClause]:
        """Get all clauses of a specific type."""
        return [c for c in self.clauses if c.clause_type == clause_type]

    def get_clauses_by_group(self, group: ClauseGroup) -> List[ClassifiedClause]:
        """Get all clauses in a specific group."""
        return [c for c in self.clauses if c.group == group]

    def to_dict(self) -> Dict:
        """Serialize for API response."""
        return {
            "clause_count": self.clause_count,
            "ambiguous_count": self.ambiguous_count,
            "group_distribution": self.group_distribution,
            "type_distribution": self.type_distribution,
            "clauses": [
                {
                    "clause_type": c.clause_type.value,
                    "group": c.group.value,
                    "confidence": c.confidence,
                    "start_position": c.start_position,
                    "end_position": c.end_position,
                    "text_snippet": c.text_snippet,
                    "heading": c.heading,
                    "needs_ai_review": c.needs_ai_review,
                }
                for c in self.clauses
            ],
        }


# ---------------------------------------------------------------------------
# Keyword patterns for each clause type
# Each entry: (ClauseType, heading_patterns, body_patterns, weight)
# heading_patterns match section headings; body_patterns match clause text
# weight determines priority when multiple types match
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _ClassifierRule:
    clause_type: ClauseType
    heading_patterns: List[str]  # Regex patterns for section headings
    body_patterns: List[str]  # Regex patterns for clause body text
    weight: float = 1.0  # Priority weight (higher = preferred)


_CLASSIFIER_RULES: List[_ClassifierRule] = [
    # --- Formation ---
    _ClassifierRule(
        clause_type=ClauseType.DEFINITIONS,
        heading_patterns=[
            r"\bdefinitions?\b",
            r"\binterpretation\b",
            r"\bdefined\s+terms?\b",
        ],
        body_patterns=[
            r'["\u201c]\w+["\u201d]\s+(?:shall\s+)?means?\b',
            r"\bfor\s+(?:the\s+)?purposes?\s+of\s+this\b",
            r"\bas\s+used\s+(?:herein|in\s+this)\b",
            r"\bshall\s+have\s+the\s+meaning\b",
        ],
        weight=1.2,
    ),
    _ClassifierRule(
        clause_type=ClauseType.RECITALS,
        heading_patterns=[
            r"\brecitals?\b",
            r"\bwhereas\b",
            r"\bpreamble\b",
            r"\bbackground\b",
        ],
        body_patterns=[
            r"\bwhereas\b",
            r"\bhereinafter\s+referred\s+to\b",
            r"\bnow,?\s+therefore\b",
        ],
        weight=1.0,
    ),
    _ClassifierRule(
        clause_type=ClauseType.ENTIRE_AGREEMENT,
        heading_patterns=[
            r"\bentire\s+agreement\b",
            r"\bwhole\s+agreement\b",
            r"\bmerger\s+clause\b",
            r"\bintegration\b",
        ],
        body_patterns=[
            r"\bentire\s+(?:agreement|understanding)\b",
            r"\bsupersedes?\s+(?:all\s+)?(?:prior|previous)\b",
            r"\bno\s+(?:other\s+)?(?:representations?|warranties)\b.*\bbinding\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.AMENDMENTS,
        heading_patterns=[
            r"\bamendments?\b",
            r"\bmodifications?\b",
            r"\bvariations?\b",
            r"\bwaivers?\b",
        ],
        body_patterns=[
            r"\bamend(?:ed|ment)?\s+(?:only\s+)?(?:by|in)\s+writ(?:ing|ten)\b",
            r"\bno\s+(?:amendment|modification|waiver)\b.*\bunless\b.*\bwrit(?:ing|ten)\b",
            r"\bmodif(?:y|ied|ication)\s+(?:this|the)\s+agreement\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.SEVERABILITY,
        heading_patterns=[
            r"\bseverability\b",
            r"\bsavings?\s+clause\b",
            r"\binvalid(?:ity)?\s+(?:of\s+)?provisions?\b",
        ],
        body_patterns=[
            r"\bsever(?:able|ability)\b",
            r"\binvalid\b.*\bunenforceable\b.*\bremaining\b",
            r"\bstruck\s+(?:down|out)\b.*\bremain(?:ing)?\s+(?:in\s+)?(?:full\s+)?(?:force|effect)\b",
        ],
    ),

    # --- Term ---
    _ClassifierRule(
        clause_type=ClauseType.DURATION,
        heading_patterns=[
            r"\bterm\b(?!\s+(?:sheet|inati))",
            r"\bduration\b",
            r"\bcommencement\b",
            r"\beffective\s+date\b",
        ],
        body_patterns=[
            r"\bcommenc(?:e|ing)\s+(?:on|from)\b",
            r"\beffective\s+(?:as\s+of|from)\b",
            r"\bfor\s+a\s+(?:period|term)\s+of\b",
            r"\binitial\s+term\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.AUTO_RENEWAL,
        heading_patterns=[
            r"\bauto(?:matic)?[\s-]?renewal\b",
            r"\brenewal\b",
        ],
        body_patterns=[
            r"\bauto(?:matic(?:ally)?)?[\s-]?renew(?:al|s|ed)?\b",
            r"\brenew(?:s|ed)?\s+(?:automatically|for\s+(?:successive|additional)\s+(?:periods?|terms?))\b",
        ],
        weight=1.3,
    ),
    _ClassifierRule(
        clause_type=ClauseType.TERMINATION_FOR_CAUSE,
        heading_patterns=[
            r"\btermination\s+for\s+(?:cause|breach|default)\b",
            r"\btermination\b",
        ],
        body_patterns=[
            r"\bterminate?\s+(?:this\s+)?(?:agreement\s+)?(?:for\s+)?(?:cause|breach|default|material)\b",
            r"\bmaterial\s+breach\b.*\bterminate?\b",
            r"\bevent\s+of\s+default\b",
            r"\bbreach\b.*\bfail(?:ure|s)?\s+to\s+(?:cure|remedy)\b",
        ],
        weight=1.1,
    ),
    _ClassifierRule(
        clause_type=ClauseType.TERMINATION_FOR_CONVENIENCE,
        heading_patterns=[
            r"\btermination\s+(?:for\s+)?convenience\b",
            r"\btermination\s+without\s+cause\b",
        ],
        body_patterns=[
            r"\bterminate?\s+(?:this\s+)?(?:agreement\s+)?(?:for\s+)?convenience\b",
            r"\bterminate?\s+(?:at\s+)?any\s+time\b.*\bwithout\s+(?:cause|reason)\b",
            r"\bterminate?\s+(?:without\s+cause|for\s+any\s+reason\s+or\s+no\s+reason)\b",
        ],
        weight=1.2,
    ),
    _ClassifierRule(
        clause_type=ClauseType.CURE_PERIOD,
        heading_patterns=[
            r"\bcure\s+period\b",
            r"\bremedy\s+period\b",
            r"\bnotice\s+(?:and\s+)?cure\b",
        ],
        body_patterns=[
            r"\bcure\s+(?:such\s+)?(?:breach|default)\b",
            r"\b\d+\s+(?:days?|business\s+days?)\s+(?:to\s+)?(?:cure|remedy)\b",
            r"\bopportunity\s+to\s+(?:cure|remedy)\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.SURVIVAL,
        heading_patterns=[
            r"\bsurvival\b",
            r"\bsurviving\s+(?:provisions?|obligations?|clauses?)\b",
        ],
        body_patterns=[
            r"\bsurvive?\s+(?:the\s+)?(?:expiration|termination)\b",
            r"\bshall\s+(?:continue\s+to\s+)?survive\b",
            r"\bnotwithstanding\s+(?:any\s+)?(?:termination|expiration)\b.*\bsurvive\b",
        ],
    ),

    # --- Financial ---
    _ClassifierRule(
        clause_type=ClauseType.PAYMENT_TERMS,
        heading_patterns=[
            r"\bpayment\s+(?:terms?|conditions?|schedule)\b",
            r"\bfees?\b",
            r"\bcompensation\b",
            r"\bconsideration\b",
        ],
        body_patterns=[
            r"\bpay(?:ment|able)\b.*\b(?:within|net)\s+\d+\s+days?\b",
            r"\binvoice\b.*\b(?:payment|due)\b",
            r"\bfees?\s+(?:shall|will)\s+(?:be\s+)?(?:paid|payable|due)\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.LATE_PAYMENT,
        heading_patterns=[
            r"\blate\s+payment\b",
            r"\binterest\s+(?:on\s+)?(?:late|overdue)\b",
            r"\bpenalt(?:y|ies)\s+for\s+(?:late|delayed)\b",
        ],
        body_patterns=[
            r"\blate\s+(?:payment|fee)\b",
            r"\binterest\s+(?:at\s+)?(?:the\s+)?(?:rate\s+of\s+)?\d+%?\b.*\boverdue\b",
            r"\boverdue\s+(?:amounts?|payments?|invoices?)\b.*\binterest\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.PRICE_ESCALATION,
        heading_patterns=[
            r"\bprice\s+(?:escalation|adjustment|increase|revision)\b",
            r"\brate\s+(?:adjustment|increase)\b",
            r"\bcost\s+of\s+living\b",
        ],
        body_patterns=[
            r"\bprice\s+(?:increase|adjustment|escalation|revision)\b",
            r"\bconsumer\s+price\s+index\b",
            r"\bCPI\b",
            r"\bannual\s+(?:increase|adjustment)\b.*\b(?:rate|price|fee)\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.TAXES,
        heading_patterns=[
            r"\btaxe?s?\b",
            r"\bwithholding\b",
            r"\bGST\b",
            r"\bVAT\b",
        ],
        body_patterns=[
            r"\btax(?:es)?\s+(?:shall|will)\s+(?:be\s+)?(?:borne|paid|payable)\b",
            r"\bwithholding\s+tax\b",
            r"\b(?:GST|VAT|sales\s+tax|service\s+tax)\b",
            r"\btax\s+(?:deduct(?:ion|ed)|withheld)\s+at\s+source\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.AUDIT_RIGHTS,
        heading_patterns=[
            r"\baudit\s+(?:rights?|clause)\b",
            r"\binspection\s+rights?\b",
            r"\bbooks?\s+(?:and\s+)?records?\b",
        ],
        body_patterns=[
            r"\baudit\b.*\b(?:books|records|accounts)\b",
            r"\bright\s+to\s+(?:audit|inspect|examine)\b",
            r"\baccess\s+to\s+(?:books|records|accounts|premises)\b",
        ],
    ),

    # --- Liability ---
    _ClassifierRule(
        clause_type=ClauseType.LIABILITY_CAP,
        heading_patterns=[
            r"\blimitation\s+(?:of|on)\s+liability\b",
            r"\bliability\s+(?:cap|limit)\b",
            r"\baggregate\s+liability\b",
        ],
        body_patterns=[
            r"\baggregate\s+liability\b.*\bshall\s+not\s+exceed\b",
            r"\bliability\b.*\b(?:cap(?:ped)?|limit(?:ed)?)\s+(?:to|at)\b",
            r"\bmaximum\s+(?:aggregate\s+)?liability\b",
            r"\btotal\s+liability\b.*\bnot\s+exceed\b",
            r"\bunlimited\s+liability\b",
        ],
        weight=1.2,
    ),
    _ClassifierRule(
        clause_type=ClauseType.CONSEQUENTIAL_DAMAGES,
        heading_patterns=[
            r"\bconsequential\s+damages?\b",
            r"\bindirect\s+damages?\b",
            r"\bexclusion\s+of\s+(?:certain\s+)?damages?\b",
        ],
        body_patterns=[
            r"\bconsequential\b.*\bdamages?\b",
            r"\bindirect\b.*\bspecial\b.*\bdamages?\b",
            r"\blost\s+profits?\b",
            r"\bpunitive\s+damages?\b",
            r"\bincidental\b.*\bdamages?\b",
        ],
        weight=1.1,
    ),
    _ClassifierRule(
        clause_type=ClauseType.INDEMNIFICATION_SCOPE,
        heading_patterns=[
            r"\bindemnif(?:y|ication)\b",
            r"\bhold\s+harmless\b",
        ],
        body_patterns=[
            r"\bindemnif(?:y|ied|ication|ies)\b",
            r"\bhold\s+harmless\b",
            r"\bdefend,?\s+indemnif(?:y|ied)\b",
            r"\bindemnifying\s+party\b",
        ],
        weight=1.1,
    ),
    _ClassifierRule(
        clause_type=ClauseType.INSURANCE,
        heading_patterns=[
            r"\binsurance\b",
            r"\bcoverage\b.*\bpolic(?:y|ies)\b",
        ],
        body_patterns=[
            r"\binsurance\s+(?:polic(?:y|ies)|coverage)\b",
            r"\bmaintain\s+(?:\w+\s+)?insurance\b",
            r"\bprofessional\s+(?:liability|indemnity)\s+insurance\b",
            r"\bcertificate\s+of\s+insurance\b",
        ],
    ),

    # --- IP ---
    _ClassifierRule(
        clause_type=ClauseType.IP_OWNERSHIP,
        heading_patterns=[
            r"\bintellectual\s+property\b.*\bownership\b",
            r"\bIP\s+(?:ownership|rights)\b",
            r"\bownership\s+(?:of\s+)?(?:IP|intellectual\s+property|work\s+product)\b",
        ],
        body_patterns=[
            r"\b(?:all\s+)?(?:intellectual\s+property|IP)\s+(?:rights?\s+)?(?:shall\s+)?(?:vest|belong|remain)\b",
            r"\bwork(?:s)?\s+(?:for|made\s+for)\s+hire\b",
            r"\bassign(?:s|ment)?\s+(?:all\s+)?(?:right|title|interest)\b",
            r"\bpre-existing\s+(?:IP|intellectual\s+property)\b",
        ],
        weight=1.2,
    ),
    _ClassifierRule(
        clause_type=ClauseType.LICENSE_GRANT,
        heading_patterns=[
            r"\blicen[cs]e\s+(?:grant|rights?)\b",
            r"\bgrant\s+of\s+(?:licen[cs]e|rights?)\b",
        ],
        body_patterns=[
            r"\bgrant(?:s|ed)?\s+(?:a\s+)?(?:non-exclusive|exclusive|worldwide|perpetual|royalty-free)\b.*\blicen[cs]e\b",
            r"\blicen[cs]e\s+to\s+(?:use|copy|modify|distribute|reproduce)\b",
            r"\bright\s+(?:and\s+)?licen[cs]e\s+to\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.IP_INDEMNIFICATION,
        heading_patterns=[
            r"\bIP\s+indemnif(?:y|ication)\b",
            r"\binfringement\s+(?:indemnif(?:y|ication)|claims?)\b",
        ],
        body_patterns=[
            r"\b(?:patent|copyright|trademark|IP)\s+infringement\b.*\bindemnif\b",
            r"\bindemnif\b.*\binfring(?:e|ement|ing)\b",
            r"\bmisappropriation\s+of\s+(?:trade\s+secrets?|IP)\b",
        ],
        weight=1.1,
    ),

    # --- Confidentiality ---
    _ClassifierRule(
        clause_type=ClauseType.CONFIDENTIALITY_OBLIGATIONS,
        heading_patterns=[
            r"\bconfidentiality\b",
            r"\bnon[\s-]?disclosure\b",
            r"\bNDA\b",
            r"\bproprietary\s+information\b",
        ],
        body_patterns=[
            r"\bconfidential\s+information\b.*\bshall\s+not\b.*\bdisclose\b",
            r"\bmaintain\s+(?:the\s+)?confidentiality\b",
            r"\bnon[\s-]?disclosure\s+obligations?\b",
            r"\bnot\s+(?:to\s+)?disclose\b.*\bconfidential\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.CONFIDENTIALITY_EXCEPTIONS,
        heading_patterns=[
            r"\bexceptions?\s+(?:to\s+)?confidentiality\b",
            r"\bexclusions?\s+(?:from\s+)?confidential\b",
            r"\bpermitted\s+disclosures?\b",
        ],
        body_patterns=[
            r"\b(?:shall\s+)?not\s+(?:be\s+)?(?:deemed\s+)?confidential\b.*\bif\b",
            r"\bexcept(?:ion|s)?\b.*\bconfidential(?:ity)?\b",
            r"\bpublic(?:ly)?\s+(?:available|known|domain)\b",
            r"\bindependently\s+developed\b",
            r"\brequired\s+(?:by|under)\s+law\b.*\bdisclose\b",
        ],
        weight=1.1,
    ),
    _ClassifierRule(
        clause_type=ClauseType.DATA_PROTECTION,
        heading_patterns=[
            r"\bdata\s+protection\b",
            r"\bprivacy\b",
            r"\bpersonal\s+(?:data|information)\b",
            r"\bDPDP\b",
            r"\bGDPR\b",
            r"\bCCPA\b",
        ],
        body_patterns=[
            r"\bpersonal\s+(?:data|information)\b",
            r"\bdata\s+(?:controller|processor|fiduciary|principal)\b",
            r"\b(?:GDPR|DPDP|CCPA|PDPA|APPI)\b",
            r"\bdata\s+(?:subject|protection)\b",
            r"\bcross[\s-]?border\s+(?:data\s+)?transfer\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.BREACH_NOTIFICATION,
        heading_patterns=[
            r"\bbreach\s+notification\b",
            r"\bdata\s+breach\b",
            r"\bincident\s+(?:response|notification)\b",
        ],
        body_patterns=[
            r"\b(?:data\s+)?breach\b.*\bnotif(?:y|ication)\b",
            r"\bsecurity\s+incident\b.*\bnotif(?:y|ication)\b",
            r"\bwithout\s+(?:undue\s+)?delay\b.*\bnotif(?:y|ication)\b",
            r"\b(?:24|48|72)\s+hours?\b.*\bnotif(?:y|ication)\b",
        ],
    ),

    # --- Governance ---
    _ClassifierRule(
        clause_type=ClauseType.GOVERNING_LAW,
        heading_patterns=[
            r"\bgoverning\s+law\b",
            r"\bapplicable\s+law\b",
            r"\bchoice\s+of\s+law\b",
        ],
        body_patterns=[
            r"\bgoverned\s+by\s+(?:the\s+)?laws?\b",
            r"\bconstrued\s+in\s+accordance\s+with\b.*\blaws?\b",
            r"\bapplicable\s+law\b.*\bshall\s+be\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.JURISDICTION,
        heading_patterns=[
            r"\bjurisdiction\b",
            r"\bvenue\b",
            r"\bforum\b",
            r"\bcourts?\b",
        ],
        body_patterns=[
            r"\b(?:exclusive|non-exclusive)\s+jurisdiction\b",
            r"\bcourts?\s+(?:of|in|at)\b.*\bshall\s+have\s+(?:exclusive\s+)?jurisdiction\b",
            r"\bsubmit\s+to\s+(?:the\s+)?(?:exclusive\s+)?jurisdiction\b",
        ],
    ),
    _ClassifierRule(
        clause_type=ClauseType.ARBITRATION,
        heading_patterns=[
            r"\barbitration\b",
            r"\bdispute\s+resolution\b",
            r"\bADR\b",
        ],
        body_patterns=[
            r"\barbitration\b.*\b(?:rules?|proceedings?|tribunal|arbitrators?)\b",
            r"\breferred\s+to\s+(?:and\s+)?(?:finally\s+)?(?:resolved\s+by\s+)?arbitration\b",
            r"\b(?:SIAC|ICC|LCIA|AAA|JAMS|DIS|HKIAC|MCIA)\b",
            r"\bsole\s+arbitrator\b",
        ],
        weight=1.1,
    ),
    _ClassifierRule(
        clause_type=ClauseType.FORCE_MAJEURE,
        heading_patterns=[
            r"\bforce\s+majeure\b",
            r"\bact\s+of\s+god\b",
            r"\bunforeseen\s+(?:events?|circumstances?)\b",
        ],
        body_patterns=[
            r"\bforce\s+majeure\b",
            r"\bact\s+of\s+god\b",
            r"\b(?:epidemic|pandemic|war|earthquake|flood|fire)\b.*\bbeyond\s+(?:the\s+)?(?:reasonable\s+)?control\b",
            r"\bbeyond\s+(?:the\s+)?(?:reasonable\s+)?control\b.*\bparty\b",
        ],
    ),

    # --- Restrictive ---
    _ClassifierRule(
        clause_type=ClauseType.NON_COMPETE,
        heading_patterns=[
            r"\bnon[\s-]?compete?\b",
            r"\brestriction\s+on\s+competition\b",
            r"\brestrictive\s+covenant\b",
        ],
        body_patterns=[
            r"\bnon[\s-]?compete?\b",
            r"\bshall\s+not\s+(?:directly\s+or\s+indirectly\s+)?compete\b",
            r"\brefrain\s+from\s+(?:engaging\s+in\s+)?(?:any\s+)?(?:business|activities?)\s+(?:that\s+)?compet(?:e|ing)\b",
        ],
        weight=1.2,
    ),
    _ClassifierRule(
        clause_type=ClauseType.NON_SOLICITATION,
        heading_patterns=[
            r"\bnon[\s-]?solicitation\b",
            r"\bno[\s-]?(?:hire|poach)\b",
        ],
        body_patterns=[
            r"\bnon[\s-]?solicitation\b",
            r"\bshall\s+not\s+(?:directly\s+or\s+indirectly\s+)?solicit\b",
            r"\bsolicit\b.*\b(?:employee|personnel|staff|contractor|customer|client)\b",
            r"\bhire\b.*\b(?:employee|personnel|staff)\b.*\bperiod\b",
        ],
        weight=1.2,
    ),
    _ClassifierRule(
        clause_type=ClauseType.EXCLUSIVITY,
        heading_patterns=[
            r"\bexclusiv(?:e|ity)\b",
            r"\bsole\s+(?:and\s+exclusive\s+)?(?:right|supplier|provider)\b",
        ],
        body_patterns=[
            r"\bexclusive\s+(?:right|license|agreement|provider|supplier)\b",
            r"\bsole\s+and\s+exclusive\b",
            r"\bexclusivity\s+(?:period|term|obligation)\b",
            r"\bshall\s+not\b.*\b(?:engage|contract|deal)\b.*\b(?:third\s+part(?:y|ies)|competitor)\b",
        ],
    ),
]


class ClauseClassifier:
    """
    Deterministic clause classifier using keyword matching and structural analysis.

    Usage:
        classifier = ClauseClassifier()
        result = classifier.classify("...contract text...")
        # or classify pre-split sections:
        result = classifier.classify_sections(sections)
    """

    def __init__(self) -> None:
        """Pre-compile all regex patterns for performance."""
        self._compiled_rules: List[Tuple[_ClassifierRule, List[re.Pattern], List[re.Pattern]]] = []

        for rule in _CLASSIFIER_RULES:
            heading_compiled = []
            for pat in rule.heading_patterns:
                try:
                    heading_compiled.append(re.compile(pat, re.IGNORECASE))
                except re.error as e:
                    logger.warning("Invalid heading pattern in %s: %s", rule.clause_type.value, e)

            body_compiled = []
            for pat in rule.body_patterns:
                try:
                    body_compiled.append(re.compile(pat, re.IGNORECASE))
                except re.error as e:
                    logger.warning("Invalid body pattern in %s: %s", rule.clause_type.value, e)

            self._compiled_rules.append((rule, heading_compiled, body_compiled))

    def classify(self, contract_text: str) -> ClassificationResult:
        """
        Classify clauses in a full contract text.

        Splits the text into sections based on headings and numbering,
        then classifies each section.

        Args:
            contract_text: Full contract text.

        Returns:
            ClassificationResult with all classified clauses.
        """
        sections = self._split_into_sections(contract_text)
        return self.classify_sections(sections)

    def classify_sections(
        self,
        sections: List[Dict[str, str]],
    ) -> ClassificationResult:
        """
        Classify pre-split sections.

        Args:
            sections: List of dicts with keys:
                - "heading": section heading (may be empty)
                - "text": section body text
                - "start": start character offset
                - "end": end character offset

        Returns:
            ClassificationResult.
        """
        clauses: List[ClassifiedClause] = []
        type_dist: Dict[str, int] = {}
        group_dist: Dict[str, int] = {}
        ambiguous_count = 0

        for section in sections:
            heading = section.get("heading", "")
            text = section.get("text", "")
            start = section.get("start", 0)
            end = section.get("end", start + len(text))

            if not text.strip():
                continue

            clause_type, confidence, keywords = self._classify_single(heading, text)

            group = _TYPE_TO_GROUP.get(clause_type, ClauseGroup.FORMATION)
            needs_ai = confidence < 0.5

            if needs_ai:
                ambiguous_count += 1

            snippet = text[:300].strip()
            if len(text) > 300:
                snippet += "..."

            clauses.append(ClassifiedClause(
                clause_type=clause_type,
                group=group,
                confidence=confidence,
                start_position=start,
                end_position=end,
                text_snippet=snippet,
                full_text=text,
                heading=heading,
                needs_ai_review=needs_ai,
                matched_keywords=keywords,
            ))

            type_name = clause_type.value
            type_dist[type_name] = type_dist.get(type_name, 0) + 1
            group_name = group.value
            group_dist[group_name] = group_dist.get(group_name, 0) + 1

        return ClassificationResult(
            clauses=clauses,
            clause_count=len(clauses),
            group_distribution=group_dist,
            type_distribution=type_dist,
            ambiguous_count=ambiguous_count,
        )

    def _classify_single(
        self,
        heading: str,
        body: str,
    ) -> Tuple[ClauseType, float, List[str]]:
        """
        Classify a single section.

        Returns (clause_type, confidence, matched_keywords).
        """
        scores: Dict[ClauseType, float] = {}
        keywords_map: Dict[ClauseType, List[str]] = {}

        for rule, heading_patterns, body_patterns in self._compiled_rules:
            score = 0.0
            matched: List[str] = []

            # Heading match is strong signal (0.6 base)
            if heading:
                for pat in heading_patterns:
                    if pat.search(heading):
                        score += 0.6
                        matched.append(f"heading:{pat.pattern[:40]}")
                        break  # One heading match is enough

            # Body matches (0.2 each, max 0.6)
            body_score = 0.0
            for pat in body_patterns:
                if pat.search(body):
                    body_score += 0.2
                    matched.append(f"body:{pat.pattern[:40]}")
                    if body_score >= 0.6:
                        break

            score += min(body_score, 0.6)

            # Apply rule weight
            score *= rule.weight

            if score > 0:
                scores[rule.clause_type] = max(
                    scores.get(rule.clause_type, 0), score
                )
                existing_kw = keywords_map.get(rule.clause_type, [])
                keywords_map[rule.clause_type] = existing_kw + matched

        if not scores:
            return ClauseType.UNKNOWN, 0.1, []

        # Pick the highest scoring type
        best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
        raw_confidence = scores[best_type]

        # Normalize confidence to 0-1 range
        confidence = min(raw_confidence, 1.0)

        return best_type, confidence, keywords_map.get(best_type, [])

    def _split_into_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Split contract text into sections based on headings and numbering.

        Detects section boundaries via:
        - Numbered headings: "1. DEFINITIONS", "2.1 Payment Terms"
        - All-caps headings: "GOVERNING LAW"
        - Markdown-style headings (if present)
        """
        # Pattern for section headings
        heading_pattern = re.compile(
            r'^(?:'
            r'(?:\d+\.(?:\d+\.?)*)\s+'  # Numbered: "1.", "2.1.", "12.3.4"
            r'|(?:ARTICLE|SECTION|CLAUSE)\s+\d+'  # ARTICLE/SECTION N
            r'|(?:(?:SCHEDULE|ANNEXURE|EXHIBIT)\s+[A-Z0-9]+)'  # SCHEDULE A
            r'|(?:[IVXLCDMivxlcdm]+|[A-Z])\.\s+'  # Roman numeral or letter: "IV.", "A."
            r')'
            r'\s*[:\-\.]?\s*'
            r'(.+)',
            re.MULTILINE | re.IGNORECASE,
        )

        # Also detect ALL CAPS lines as headings
        allcaps_pattern = re.compile(
            r'^([A-Z][A-Z\s&,/()-]{3,80})$',
            re.MULTILINE,
        )

        sections: List[Dict[str, str]] = []
        lines = text.split('\n')

        current_heading = ""
        current_lines: List[str] = []
        current_start = 0

        offset = 0
        for line in lines:
            line_start = offset
            offset += len(line) + 1  # +1 for newline

            stripped = line.strip()
            if not stripped:
                current_lines.append(line)
                continue

            is_heading = False
            new_heading = ""

            # Check numbered heading
            m = heading_pattern.match(stripped)
            if m:
                is_heading = True
                new_heading = stripped
            elif allcaps_pattern.match(stripped) and len(stripped) > 5:
                is_heading = True
                new_heading = stripped

            if is_heading and current_lines:
                # Save previous section
                section_text = '\n'.join(current_lines).strip()
                if section_text:
                    sections.append({
                        "heading": current_heading,
                        "text": section_text,
                        "start": current_start,
                        "end": line_start,
                    })
                current_heading = new_heading
                current_lines = [line]
                current_start = line_start
            else:
                if is_heading:
                    current_heading = new_heading
                    current_start = line_start
                current_lines.append(line)

        # Don't forget the last section
        if current_lines:
            section_text = '\n'.join(current_lines).strip()
            if section_text:
                sections.append({
                    "heading": current_heading,
                    "text": section_text,
                    "start": current_start,
                    "end": offset,
                })

        return sections


# Singleton
clause_classifier = ClauseClassifier()
