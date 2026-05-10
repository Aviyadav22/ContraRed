"""
Clause taxonomy — 54 clause categories across 11 groups.

This module is the **canonical taxonomy** referenced by playbook rules,
DocumentRisk records, and the ClauseLibrary. The deterministic regex-based
classifier that previously lived here was unused by the active analysis
pipeline (Stage 2 uses the rule engine + AI) and has been removed; only
the enums and group mapping remain.

Phase C1 will introduce `clause_taxonomy.snap_to_clause_type()` to
normalize free-string `clause_type` values into these enum members at
write boundaries.
"""

from enum import Enum
from typing import Dict


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
    TECHNOLOGY = "technology"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"


class ClauseType(str, Enum):
    """The 54 clause categories (34 original + 20 expanded)."""
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
    MOST_FAVORED_NATION = "most_favored_nation"
    SET_OFF_RIGHTS = "set_off_rights"
    CURRENCY = "currency"

    # Liability
    LIABILITY_CAP = "liability_cap"
    CONSEQUENTIAL_DAMAGES = "consequential_damages"
    INDEMNIFICATION_SCOPE = "indemnification_scope"
    INSURANCE = "insurance"

    # IP
    IP_OWNERSHIP = "ip_ownership"
    LICENSE_GRANT = "license_grant"
    IP_INDEMNIFICATION = "ip_indemnification"
    MORAL_RIGHTS = "moral_rights"
    BACKGROUND_IP = "background_ip"

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

    # Technology / SaaS
    SLA_TERMS = "sla_terms"
    DATA_PORTABILITY = "data_portability"
    SECURITY_STANDARDS = "security_standards"
    API_RIGHTS = "api_rights"
    ACCEPTABLE_USE = "acceptable_use"

    # Compliance
    ANTI_BRIBERY = "anti_bribery"
    SANCTIONS_COMPLIANCE = "sanctions_compliance"
    REGULATORY_COMPLIANCE = "regulatory_compliance"

    # Operational
    ASSIGNMENT = "assignment"
    CHANGE_OF_CONTROL = "change_of_control"
    SUBCONTRACTING = "subcontracting"
    BUSINESS_CONTINUITY = "business_continuity"
    TRANSITION_ASSISTANCE = "transition_assistance"
    COUNTERPARTY_INSOLVENCY = "counterparty_insolvency"
    RETURN_OF_MATERIALS = "return_of_materials"

    # Fallback
    UNKNOWN = "unknown"


# Map each ClauseType to its group
TYPE_TO_GROUP: Dict[ClauseType, ClauseGroup] = {
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
    ClauseType.MOST_FAVORED_NATION: ClauseGroup.FINANCIAL,
    ClauseType.SET_OFF_RIGHTS: ClauseGroup.FINANCIAL,
    ClauseType.CURRENCY: ClauseGroup.FINANCIAL,
    ClauseType.LIABILITY_CAP: ClauseGroup.LIABILITY,
    ClauseType.CONSEQUENTIAL_DAMAGES: ClauseGroup.LIABILITY,
    ClauseType.INDEMNIFICATION_SCOPE: ClauseGroup.LIABILITY,
    ClauseType.INSURANCE: ClauseGroup.LIABILITY,
    ClauseType.IP_OWNERSHIP: ClauseGroup.IP,
    ClauseType.LICENSE_GRANT: ClauseGroup.IP,
    ClauseType.IP_INDEMNIFICATION: ClauseGroup.IP,
    ClauseType.MORAL_RIGHTS: ClauseGroup.IP,
    ClauseType.BACKGROUND_IP: ClauseGroup.IP,
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
    ClauseType.SLA_TERMS: ClauseGroup.TECHNOLOGY,
    ClauseType.DATA_PORTABILITY: ClauseGroup.TECHNOLOGY,
    ClauseType.SECURITY_STANDARDS: ClauseGroup.TECHNOLOGY,
    ClauseType.API_RIGHTS: ClauseGroup.TECHNOLOGY,
    ClauseType.ACCEPTABLE_USE: ClauseGroup.TECHNOLOGY,
    ClauseType.ANTI_BRIBERY: ClauseGroup.COMPLIANCE,
    ClauseType.SANCTIONS_COMPLIANCE: ClauseGroup.COMPLIANCE,
    ClauseType.REGULATORY_COMPLIANCE: ClauseGroup.COMPLIANCE,
    ClauseType.ASSIGNMENT: ClauseGroup.OPERATIONAL,
    ClauseType.CHANGE_OF_CONTROL: ClauseGroup.OPERATIONAL,
    ClauseType.SUBCONTRACTING: ClauseGroup.OPERATIONAL,
    ClauseType.BUSINESS_CONTINUITY: ClauseGroup.OPERATIONAL,
    ClauseType.TRANSITION_ASSISTANCE: ClauseGroup.OPERATIONAL,
    ClauseType.COUNTERPARTY_INSOLVENCY: ClauseGroup.OPERATIONAL,
    ClauseType.RETURN_OF_MATERIALS: ClauseGroup.OPERATIONAL,
    ClauseType.UNKNOWN: ClauseGroup.FORMATION,
}
