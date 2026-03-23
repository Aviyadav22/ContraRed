"""
Playbook Templates - Pre-built playbook templates for common contract types.

Phase 5: 5 curated templates covering the most common contract types.
Each template contains jurisdiction-aware rules with detection patterns,
negotiation positions, and risk levels.

Templates:
  1. NDA - Indian Law (22 rules)
  2. SaaS Agreement (35 rules)
  3. Employment - India (28 rules)
  4. MSA / Services (30 rules)
  5. M&A / SPA (25 rules)
"""

import json
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class PlaybookTemplate:
    """A pre-built playbook template."""
    id: str
    name: str
    description: str
    category: str
    jurisdiction: str
    rules: List[Dict[str, Any]]
    tags: List[str] = field(default_factory=list)


def _rule(
    clause_type: str,
    primary_position: str,
    risk_level: str = "YELLOW",
    patterns: List[str] = None,
    fallback_position: str = None,
    is_deal_breaker: bool = False,
    order_index: int = 0,
    requires_ai: bool = True,
    match_type: str = "regex",
    negative_patterns: List[str] = None,
    escalation_conditions: List[str] = None,
    de_escalation_conditions: List[str] = None,
    category: str = None,
) -> Dict[str, Any]:
    """Helper to build a rule dict."""
    detection = {"patterns": patterns or [], "match_type": match_type}
    if negative_patterns:
        detection["negative_patterns"] = negative_patterns
    if escalation_conditions:
        detection["escalation_conditions"] = escalation_conditions
    if de_escalation_conditions:
        detection["de_escalation_conditions"] = de_escalation_conditions
    return {
        "clause_type": clause_type,
        "primary_position": primary_position,
        "fallback_position": fallback_position,
        "risk_level": risk_level,
        "is_deal_breaker": is_deal_breaker,
        "detection_patterns": detection,
        "order_index": order_index,
        "requires_ai_verification": requires_ai,
        "category": category,
    }


# ============================================================
# TEMPLATE 1: NDA - INDIAN LAW (22 rules)
# ============================================================

NDA_INDIAN_LAW = PlaybookTemplate(
    id="nda_indian_law",
    name="NDA - Indian Law",
    description="Comprehensive NDA review playbook for agreements governed by Indian law. Covers confidential information scope, S.27 non-compete, DPDP Act compliance, and standard NDA provisions.",
    category="nda",
    jurisdiction="IN",
    tags=["india", "nda", "confidentiality", "dpdp"],
    rules=[
        _rule("confidentiality", "Confidential Information should be narrowly defined to specific categories (technical data, business plans, customer lists) rather than 'all information disclosed'. Overbroad definitions create compliance burden.", "YELLOW", [
            r"\b(confidential\s+information)\b", r"\b(proprietary\s+information)\b",
            r"\b(shall\s+maintain\s+(?:in\s+)?confidential)", r"\b(not\s+disclose)\b",
        ], "At minimum, require information to be marked 'Confidential' or confirmed in writing within 7 days of oral disclosure.", order_index=1,
        escalation_conditions=[r"\b(all\s+information)\b", r"\b(any\s+and\s+all\s+information)\b"], category="confidentiality"),

        _rule("confidentiality_exceptions", "Ensure standard carve-outs: (a) publicly available, (b) already known, (c) independently developed, (d) received from third party without restriction, (e) required by law/court order.", "YELLOW", [
            r"\b(excluding|shall\s+not\s+include|does\s+not\s+apply)\b",
            r"\b(publicly\s+available|public\s+domain)\b", r"\b(independently\s+developed)\b",
        ], order_index=2, category="confidentiality"),

        _rule("confidentiality_term", "Confidentiality obligations should expire 3-5 years after termination. Perpetual obligations are unreasonable for commercial NDAs under Indian law.", "YELLOW", [
            r"\b(perpetual\s+confidentiality)\b", r"\b(confidential.*in\s+perpetuity)\b",
            r"\b(survive\s+(indefinitely|forever))\b",
        ], "Cap at 5 years post-termination maximum.", order_index=3, category="confidentiality"),

        _rule("permitted_disclosure", "Include permitted disclosure to: (a) employees/agents on need-to-know basis, (b) professional advisors under duty of confidence, (c) affiliates. Receiving party remains liable for breaches by permitted recipients.", "YELLOW", [
            r"\b(permitted\s+disclos(ure|e))\b", r"\b(authorized\s+to\s+disclose)\b",
            r"\b(may\s+disclose\s+to)\b",
        ], order_index=4, category="confidentiality"),

        _rule("return_of_materials", "Upon termination, require return or certified destruction of all confidential materials within 15 business days. Retain right to keep one archival copy for legal compliance.", "GREEN", [
            r"\b(return.*confidential)\b", r"\b(destroy.*materials)\b",
            r"\b(return\s+or\s+destroy)\b", r"\b(certify\s+destruction)\b",
        ], order_index=5, category="confidentiality"),

        _rule("non_compete", "Non-compete clauses are VOID under Section 27 of the Indian Contract Act 1872 (restraint of trade). Exception: sale of goodwill (S.27 proviso). Flag but note unenforceability.", "GREEN", [
            r"\b(non[\s-]?compete)\b", r"\b(shall\s+not\s+compete)\b",
            r"\b(restriction\s+on\s+competition)\b",
        ], "Remove non-compete entirely or replace with narrowly-drafted non-solicitation.", order_index=6, is_deal_breaker=False, category="restrictive_covenant"),

        _rule("non_solicitation", "Non-solicitation of employees is generally enforceable in India if reasonable in scope and duration. Limit to 12 months post-termination.", "YELLOW", [
            r"\b(non[\s-]?solicit(ation)?)\b", r"\b(shall\s+not\s+solicit)\b",
            r"solicit.{0,100}(employee|personnel|staff)",
        ], "Non-solicitation limited to 12 months, covering only employees directly involved.", order_index=7, category="restrictive_covenant"),

        _rule("ip_ownership", "Pre-existing IP remains with disclosing party. No implied license should arise from disclosure of confidential information.", "YELLOW", [
            r"\b(intellectual\s+property.*owned)\b", r"\b(ownership\s+of\s+IP)\b",
            r"\b(no\s+implied\s+license)\b", r"\b(all\s+IP.*belongs\s+to)\b",
        ], order_index=8, category="intellectual_property"),

        _rule("remedies", "Include specific acknowledgment that breach may cause irreparable harm and that disclosing party is entitled to seek injunctive relief (Order XXXIX CPC) without proving actual damages.", "GREEN", [
            r"\b(injunctive\s+relief)\b", r"\b(irreparable\s+harm)\b",
            r"\b(equitable\s+relief)\b", r"\b(specific\s+performance)\b",
        ], order_index=9, category="governance"),

        _rule("governing_law", "Governing law: Laws of India. Jurisdiction: Courts at [specify city — Mumbai/Delhi/Bangalore]. Avoid 'exclusive jurisdiction' without arbitration alternative.", "GREEN", [
            r"\b(govern(ed|ing)\s+(by|law))\b", r"\b(laws\s+of\s+India)\b",
            r"\b(applicable\s+law)\b",
        ], order_index=10, category="governance"),

        _rule("arbitration", "For disputes >₹1 crore, include SIAC or ICC arbitration clause. For smaller disputes, Indian Arbitration Act 1996 (amended 2019) with seat in Mumbai/Delhi. 3 arbitrators for large disputes.", "YELLOW", [
            r"\b(arbitration)\b", r"\b(arbitral\s+tribunal)\b",
            r"\b(resolved\s+by\s+arbitration)\b",
        ], "At minimum, include mediation as mandatory first step before arbitration.", order_index=11, category="governance"),

        _rule("term_and_termination", "NDA term should be 2-3 years with option to extend. Either party should have right to terminate with 30 days written notice. Confidentiality obligations survive termination.", "GREEN", [
            r"\b(term\s+of\s+this\s+agreement)\b", r"\b(initial\s+term)\b",
            r"\b(effective\s+date)\b",
        ], order_index=12, category="term"),

        _rule("termination_for_cause", "Immediate termination right for material breach (after 15-day cure period). Breach of confidentiality obligations should be expressly listed as material breach.", "YELLOW", [
            r"\b(terminate\s+for\s+cause)\b", r"\b(material\s+breach)\b",
            r"\b(terminate.*upon.*breach)\b",
        ], order_index=13, de_escalation_conditions=[r"\b(cure\s+period|right\s+to\s+cure)\b"], category="term"),

        _rule("data_protection", "Include DPDP Act 2023 compliance clause: consent-based processing, data fiduciary obligations, 72-hour breach notification to Data Protection Board of India.", "YELLOW", [
            r"\b(data\s+protection)\b", r"\b(personal\s+data)\b",
            r"\b(DPDP)\b", r"\b(data\s+subject)\b",
        ], "At minimum, acknowledge applicability of DPDP Act and define data handling obligations.", order_index=14, category="data_protection"),

        _rule("indemnification", "Mutual indemnification for breach of confidentiality obligations. Cap indemnification at contract value or 12 months' fees (whichever is higher). Exclude consequential damages.", "YELLOW", [
            r"\b(indemnif(y|ication))\b", r"\b(hold\s+harmless)\b",
        ], order_index=15, escalation_conditions=[r"\b(unlimited|uncapped)\b"], category="liability"),

        _rule("limitation_of_liability", "Total liability capped at amount paid/payable under the NDA (if consideration exists) or ₹50 lakhs, whichever is lower. Exclude wilful misconduct and breach of confidentiality from cap.", "YELLOW", [
            r"\b(limitation\s+of\s+liability)\b", r"\b(liability.*shall\s+not\s+exceed)\b",
            r"\b(aggregate\s+liability)\b",
        ], order_index=16, category="liability"),

        _rule("notice_provision", "Notices in writing via email with read receipt + registered post/courier to registered addresses. Email alone insufficient for termination notices.", "GREEN", [
            r"\b(notice.*shall\s+be.*given)\b", r"\b(written\s+notice)\b",
        ], order_index=17, category="operational"),

        _rule("entire_agreement", "Entire agreement clause: this NDA supersedes all prior discussions, understandings, and agreements. No amendment except in writing signed by both parties.", "GREEN", [
            r"\b(entire\s+agreement)\b", r"\b(constitutes\s+the\s+entire)\b",
            r"\b(supersedes\s+all\s+prior)\b",
        ], order_index=18, category="formation"),

        _rule("assignment", "Neither party may assign rights/obligations without prior written consent. Exception: assignment to affiliates or successor entity in M&A.", "YELLOW", [
            r"\b(may\s+not\s+assign)\b", r"\b(assignment.*without\s+consent)\b",
            r"\b(assignment.*prohibited)\b",
        ], order_index=19, category="operational"),

        _rule("severability", "Standard severability: if any provision is invalid, remaining provisions continue in full force. Invalid provision to be reformed to closest permissible interpretation.", "GREEN", [
            r"\b(severab(le|ility))\b", r"\b(if\s+any\s+provision.*invalid)\b",
        ], order_index=20, category="formation"),

        _rule("stamp_duty", "Ensure NDA is properly stamped per Indian Stamp Act 1899 (varies by state). Unstamped agreements are inadmissible as evidence. Maharashtra/Karnataka have specific rates for NDAs.", "YELLOW", [
            r"\b(stamp\s+duty)\b", r"\b(stamped)\b",
            r"\b(Indian\s+Stamp\s+Act)\b",
        ], order_index=21, requires_ai=False, category="operational"),

        _rule("force_majeure", "Include force majeure clause covering natural disasters, pandemics, government actions, and strikes. Affected party must notify within 7 days. If FM exceeds 90 days, either party may terminate.", "YELLOW", [
            r"\b(force\s+majeure)\b", r"\b(act\s+of\s+god)\b",
            r"\b(beyond.*reasonable\s+control)\b",
        ], order_index=22, category="operational"),
    ],
)


# ============================================================
# TEMPLATE 2: SAAS AGREEMENT (35 rules)
# ============================================================

SAAS_AGREEMENT = PlaybookTemplate(
    id="saas_agreement",
    name="SaaS Agreement",
    description="Comprehensive SaaS agreement review covering SLA, data ownership, liability caps, security standards, and subscription terms. Applicable across jurisdictions.",
    category="saas",
    jurisdiction="",
    tags=["saas", "technology", "subscription", "cloud"],
    rules=[
        _rule("sla_uptime", "SLA should guarantee minimum 99.9% uptime (excluding scheduled maintenance). Define measurement period (monthly). Include calculation methodology.", "YELLOW", [
            r"\b(service\s+level|SLA)\b", r"\b(uptime.*guarantee)\b",
            r"\b(availability.*99)\b", r"\b(service\s+availability)\b",
        ], "Minimum acceptable: 99.5% uptime with clearly defined measurement window.", order_index=1, category="saas_technology"),

        _rule("sla_credits", "SLA credits should be meaningful: 10% for 99.0-99.9%, 25% for 95-99%, 50% for <95%. Credits should apply automatically without requiring formal claim.", "YELLOW", [
            r"\b(service\s+credit)\b", r"\b(SLA\s+credit)\b",
            r"\b(credit.*downtime)\b", r"\b(remedy.*failure)\b",
        ], order_index=2, category="saas_technology"),

        _rule("data_ownership", "Customer retains all ownership of Customer Data. Provider has limited license to process data solely to provide the service. No mining/analytics on customer data without consent.", "RED", [
            r"\b(data\s+ownership)\b", r"\b(customer\s+data.*owned)\b",
            r"\b(retain.*ownership)\b", r"\b(proprietary\s+rights.*data)\b",
        ], "Customer must own all data input into the platform.", order_index=3, is_deal_breaker=True, category="intellectual_property"),

        _rule("data_portability", "Customer must have right to export all data in standard format (CSV, JSON, API) at any time, including during wind-down period. No data hostage scenarios.", "YELLOW", [
            r"\b(data\s+portability)\b", r"\b(data\s+export)\b",
            r"\b(right\s+to\s+export)\b", r"\b(provide.*data.*format)\b",
        ], order_index=4, escalation_conditions=[r"\b(no\s+export|cannot\s+export)\b"], category="saas_technology"),

        _rule("liability_cap", "Total liability capped at 12 months of fees paid. Exclude IP infringement, data breaches, and confidentiality breaches from cap.", "YELLOW", [
            r"\b(liability.*shall\s+not\s+exceed)\b", r"\b(aggregate\s+liability)\b",
            r"\b(liability\s+cap)\b", r"\b(maximum\s+liability)\b",
        ], "Minimum acceptable: 6 months of fees paid.", order_index=5, category="liability"),

        _rule("unlimited_liability", "No uncapped liability. If provider insists on unlimited liability, it must be mutual and limited to wilful misconduct only.", "RED", [
            r"\b(unlimited\s+liability)\b", r"\b(no\s+cap.*liability)\b",
            r"\b(without\s+limit.*liability)\b",
        ], order_index=6, is_deal_breaker=True, category="liability"),

        _rule("consequential_damages", "Mutual exclusion of indirect/consequential damages. Carve-out for: IP infringement, data breaches, confidentiality breaches, wilful misconduct.", "YELLOW", [
            r"\b(consequential\s+damages)\b", r"\b(indirect.*damages)\b",
            r"\b(special.*incidental)\b", r"\b(loss\s+of\s+profit)\b",
        ], order_index=7, category="liability"),

        _rule("indemnification", "Mutual indemnification for IP infringement and data breaches. Provider indemnifies for platform IP issues. Customer indemnifies for content/data they upload.", "YELLOW", [
            r"\b(indemnif(y|ication))\b", r"\b(hold\s+harmless)\b",
            r"\b(defend.*indemnify)\b",
        ], order_index=8, escalation_conditions=[r"\b(one[\s-]?sided|unilateral)\b", r"\b(uncapped)\b"], category="liability"),

        _rule("ip_rights", "Provider retains all IP in the platform. Customer retains all IP in their data. No transfer of IP through use of the service.", "GREEN", [
            r"\b(intellectual\s+property.*rights)\b", r"\b(IP.*ownership)\b",
            r"\b(proprietary\s+rights)\b",
        ], order_index=9, category="intellectual_property"),

        _rule("license_grant", "Non-exclusive, non-transferable, revocable license to access the SaaS platform during the subscription term. No sublicense rights unless explicitly granted.", "GREEN", [
            r"\b(grant.*license)\b", r"\b(license\s+to\s+use)\b",
            r"\b(non-exclusive.*license)\b",
        ], order_index=10, escalation_conditions=[r"\b(irrevocable)\b", r"\b(sublicens(e|able))\b"], category="intellectual_property"),

        _rule("payment_terms", "Net 30 payment terms. Annual prepayment with 10% discount. No price increases during initial term. Price increases capped at 5% or CPI for renewals.", "YELLOW", [
            r"\b(net\s+\d+)\b", r"\b(payment.*due.*within)\b",
            r"\b(invoice.*payable)\b",
        ], order_index=11, escalation_conditions=[r"\b(net\s+(?:6[1-9]|[7-9]\d|1\d\d))\b"], category="financial"),

        _rule("auto_renewal", "30-day opt-out notice before renewal date. No auto-increase on renewal without 60-day prior written notice. Customer right to downgrade at renewal.", "YELLOW", [
            r"\b(auto.*renew(al)?)\b", r"\b(automatically\s+renew)\b",
            r"\b(renew.*automatically)\b",
        ], order_index=12, category="term"),

        _rule("termination_for_convenience", "Either party may terminate with 30 days written notice. Customer entitled to pro-rata refund of prepaid fees for unused term.", "YELLOW", [
            r"\b(terminate\s+for\s+convenience)\b", r"\b(terminate\s+without\s+cause)\b",
            r"\b(terminate.*upon.*days.*notice)\b",
        ], order_index=13, category="term"),

        _rule("termination_for_cause", "Immediate termination for material breach after 30-day cure period. Data breach or security incident = immediate termination right without cure period.", "YELLOW", [
            r"\b(terminate\s+for\s+cause)\b", r"\b(material\s+breach)\b",
            r"\b(terminate.*breach)\b",
        ], order_index=14, category="term"),

        _rule("transition_assistance", "90-day transition period post-termination during which provider continues service at then-current rates. Full data export assistance included.", "YELLOW", [
            r"\b(transition\s+assistance)\b", r"\b(wind-down)\b",
            r"\b(transition\s+period)\b", r"\b(migration\s+assistance)\b",
        ], order_index=15, category="term"),

        _rule("confidentiality", "Mutual confidentiality obligations. Standard exceptions. 3-year survival post-termination. Trade secrets protected indefinitely.", "YELLOW", [
            r"\b(confidential\s+information)\b", r"\b(maintain.*confidential)\b",
            r"\b(not\s+disclose)\b",
        ], order_index=16, category="confidentiality"),

        _rule("data_protection", "Provider must comply with applicable data protection laws (GDPR/DPDP/CCPA). Execute DPA as addendum. Provide Data Processing Impact Assessment upon request.", "YELLOW", [
            r"\b(data\s+protection)\b", r"\b(personal\s+data)\b",
            r"\b(GDPR|DPDP|CCPA)\b", r"\b(data\s+processing)\b",
        ], order_index=17, category="data_protection"),

        _rule("security_standards", "Provider must maintain SOC 2 Type II or ISO 27001 certification. Annual penetration testing. Encryption at rest (AES-256) and in transit (TLS 1.2+).", "YELLOW", [
            r"\b(ISO\s*27001)\b", r"\b(SOC\s*2)\b",
            r"\b(security\s+standards)\b", r"\b(encryption)\b",
        ], order_index=18, category="saas_technology"),

        _rule("breach_notification", "Notify customer of data breach within 72 hours. Include: nature of breach, data affected, remediation steps, point of contact.", "YELLOW", [
            r"\b(data\s+breach)\b", r"\b(security\s+incident)\b",
            r"\b(breach\s+notification)\b",
        ], order_index=19, escalation_conditions=[r"\b(7\s+days|14\s+days|30\s+days)\b"], category="data_protection"),

        _rule("subprocessors", "Provider must maintain list of sub-processors. 30-day prior notice of new sub-processors. Customer right to object. Provider remains liable for sub-processor breaches.", "YELLOW", [
            r"\b(sub[\s-]?processor)\b", r"\b(subcontract)\b",
            r"\b(third\s+party.*process)\b",
        ], order_index=20, category="operational"),

        _rule("warranty_disclaimer", "Avoid blanket 'AS-IS' disclaimers. Provider should warrant: (a) platform performs materially as documented, (b) services conform to SLA, (c) no known malware.", "RED", [
            r"\b(AS[\s-]IS)\b", r"\b(no\s+warranty)\b",
            r"\b(without\s+warranty)\b", r"\b(disclaimer.*warrant)\b",
        ], order_index=21, de_escalation_conditions=[r"\b(trial|evaluation|beta)\b"], category="reps_warranties"),

        _rule("acceptable_use", "Acceptable use policy should be reasonable. No restrictions that prevent normal business use. Changes to AUP require 30-day notice.", "GREEN", [
            r"\b(acceptable\s+use)\b", r"\b(permitted\s+use)\b",
            r"\b(use\s+restrictions)\b",
        ], order_index=22, category="saas_technology"),

        _rule("api_access", "API access included in subscription. Rate limits clearly defined. API versioning with 12-month deprecation notice for breaking changes.", "YELLOW", [
            r"\b(API\s+access)\b", r"\b(programmatic\s+access)\b",
            r"\b(application\s+programming\s+interface)\b",
        ], order_index=23, category="saas_technology"),

        _rule("force_majeure", "Standard force majeure clause. Include pandemics. Affected party must mitigate. If FM exceeds 60 days, either party may terminate.", "YELLOW", [
            r"\b(force\s+majeure)\b", r"\b(act\s+of\s+god)\b",
            r"\b(beyond.*reasonable\s+control)\b",
        ], order_index=24, category="operational"),

        _rule("governing_law", "Choose neutral governing law appropriate for both parties. For international SaaS, consider Singapore or England.", "GREEN", [
            r"\b(govern(ed|ing)\s+(by|law))\b", r"\b(applicable\s+law)\b",
        ], order_index=25, category="governance"),

        _rule("dispute_resolution", "Tiered dispute resolution: (1) executive escalation 30 days, (2) mediation 60 days, (3) arbitration. Costs split equally for mediation.", "GREEN", [
            r"\b(dispute\s+resolution)\b", r"\b(resolve.*dispute)\b",
            r"\b(escalat.*dispute)\b",
        ], order_index=26, category="governance"),

        _rule("insurance", "Provider must maintain: professional indemnity (min $2M), cyber liability ($5M), general liability ($1M). Certificates on request.", "YELLOW", [
            r"\b(maintain.*insurance)\b", r"\b(insurance\s+coverage)\b",
            r"\b(professional\s+indemnity)\b", r"\b(cyber.*liability)\b",
        ], order_index=27, category="operational"),

        _rule("audit_rights", "Customer (or independent auditor) may audit provider's compliance with security/data obligations once per year with 30 days notice. Provider bears cost if non-compliant.", "YELLOW", [
            r"\b(right\s+to\s+audit)\b", r"\b(audit\s+rights)\b",
            r"\b(inspect.*records)\b",
        ], order_index=28, category="financial"),

        _rule("non_solicitation", "Mutual non-solicitation of employees for 12 months post-termination. Exception: general job postings.", "YELLOW", [
            r"\b(non[\s-]?solicit(ation)?)\b", r"\b(shall\s+not\s+solicit)\b",
        ], order_index=29, category="restrictive_covenant"),

        _rule("assignment", "Neither party may assign without consent, except to affiliate or successor in merger/acquisition. Change of control to competitor triggers termination right.", "YELLOW", [
            r"\b(may\s+not\s+assign)\b", r"\b(assignment.*consent)\b",
            r"\b(assignment.*prohibited)\b",
        ], order_index=30, category="operational"),

        _rule("entire_agreement", "Standard entire agreement clause. Amendments in writing only. Order of precedence: DPA > MSA > SOW > Order Form.", "GREEN", [
            r"\b(entire\s+agreement)\b", r"\b(constitutes\s+the\s+entire)\b",
        ], order_index=31, category="formation"),

        _rule("notices", "Written notices via email to designated contacts. Material notices (termination, breach) also require registered mail/courier.", "GREEN", [
            r"\b(notice.*shall\s+be)\b", r"\b(written\s+notice)\b",
        ], order_index=32, category="operational"),

        _rule("anti_bribery", "Both parties warrant compliance with applicable anti-bribery laws (FCPA, UK Bribery Act, Prevention of Corruption Act).", "GREEN", [
            r"\b(anti[\s-]?bribery)\b", r"\b(anti[\s-]?corruption)\b",
            r"\b(FCPA)\b",
        ], order_index=33, category="operational"),

        _rule("survival", "Sections that survive termination: confidentiality, limitation of liability, indemnification, data portability, IP ownership, dispute resolution.", "GREEN", [
            r"\b(shall\s+survive)\b", r"\b(survive\s+termination)\b",
            r"\b(surviving\s+provisions)\b",
        ], order_index=34, category="term"),

        _rule("change_of_control", "Termination right if provider undergoes change of control to competitor. 90-day notice required for any change of control.", "YELLOW", [
            r"\b(change\s+of\s+control)\b", r"\b(merger.*acquisition)\b",
            r"\b(controlling\s+interest)\b",
        ], order_index=35, category="operational"),
    ],
)


# ============================================================
# TEMPLATE 3: EMPLOYMENT - INDIA (28 rules)
# ============================================================

EMPLOYMENT_INDIA = PlaybookTemplate(
    id="employment_india",
    name="Employment Agreement - India",
    description="Employment agreement review playbook for Indian law. Covers S.27 non-compete, POSH Act, PF/ESIC, confidentiality, and standard employment terms.",
    category="employment",
    jurisdiction="IN",
    tags=["india", "employment", "labor", "hr"],
    rules=[
        _rule("non_compete", "Non-compete clauses are VOID under S.27 Indian Contract Act 1872. During employment is enforceable; post-employment is void. Remove or replace with non-solicitation.", "RED", [
            r"\b(non[\s-]?compete)\b", r"\b(shall\s+not\s+compete)\b",
            r"\b(restriction\s+on\s+competition)\b", r"\b(restrictive\s+covenant)\b",
        ], "Delete non-compete or explicitly limit to during-employment period only.", order_index=1, is_deal_breaker=True, category="restrictive_covenant"),

        _rule("non_solicitation", "Non-solicitation of employees/clients is generally enforceable if reasonable. Limit to 12 months post-termination, specific individuals/clients.", "YELLOW", [
            r"\b(non[\s-]?solicit(ation)?)\b", r"\b(shall\s+not\s+solicit)\b",
            r"solicit.{0,100}(employee|client|customer)",
        ], order_index=2, category="restrictive_covenant"),

        _rule("notice_period", "Notice period should be symmetrical (employer and employee have same notice period). Standard: 30-90 days. Include garden leave option.", "YELLOW", [
            r"\b(notice\s+period)\b", r"\b(resignation.*notice)\b",
            r"\b(\d+\s+(days?|months?)\s+notice)\b",
        ], order_index=3, category="term"),

        _rule("termination_for_cause", "Define 'cause' clearly: fraud, theft, habitual negligence, breach of company policy, conviction of criminal offense. Employee must have right to be heard (audi alteram partem).", "YELLOW", [
            r"\b(terminate\s+for\s+cause)\b", r"\b(dismissal\s+for\s+misconduct)\b",
            r"\b(termination.*cause)\b",
        ], order_index=4, category="term"),

        _rule("garden_leave", "Garden leave period should count towards notice period. Employee continues to receive full salary and benefits during garden leave.", "YELLOW", [
            r"\b(garden\s+leave)\b", r"\b(paid\s+leave.*notice)\b",
        ], order_index=5, requires_ai=False, category="term"),

        _rule("confidentiality", "Confidentiality obligations continue post-employment. Reasonable scope — limited to actual trade secrets and proprietary information accessed during employment.", "YELLOW", [
            r"\b(confidential\s+information)\b", r"\b(maintain.*confidential)\b",
            r"\b(trade\s+secret)\b",
        ], order_index=6, category="confidentiality"),

        _rule("ip_assignment", "Work product created during employment using company resources belongs to employer (work-for-hire). Prior inventions should be excluded and disclosed upfront.", "YELLOW", [
            r"\b(work.*for\s+hire)\b", r"\b(assign.*intellectual\s+property)\b",
            r"\b(IP.*belongs\s+to.*employer)\b", r"\b(work\s+product)\b",
        ], order_index=7, category="intellectual_property"),

        _rule("moral_rights", "Under Indian Copyright Act 1957, S.57 — moral rights (right to paternity and integrity) cannot be waived. Any waiver clause is void.", "YELLOW", [
            r"\b(moral\s+rights)\b", r"\b(waive.*moral)\b",
            r"\b(right\s+of\s+paternity)\b",
        ], order_index=8, category="intellectual_property"),

        _rule("pf_esic", "Employer must comply with Employees' Provident Fund Act 1952 (12% contribution) and ESIC Act 1948 for applicable employees. Deductions must be explicitly stated.", "YELLOW", [
            r"\b(provident\s+fund|PF)\b", r"\b(ESIC|ESI)\b",
            r"\b(gratuity)\b", r"\b(statutory.*deduction)\b",
        ], order_index=9, requires_ai=False, category="financial"),

        _rule("gratuity", "Payment of Gratuity Act 1972: 15 days wages per year of service after 5 years. Cannot be contracted out of. Include reference in compensation section.", "GREEN", [
            r"\b(gratuity)\b", r"\b(Payment\s+of\s+Gratuity)\b",
        ], order_index=10, requires_ai=False, category="financial"),

        _rule("posh_compliance", "Sexual Harassment of Women at Workplace Act 2013 (POSH Act): employer must constitute Internal Complaints Committee, conduct awareness programs, and include policy reference.", "YELLOW", [
            r"\b(sexual\s+harassment)\b", r"\b(POSH)\b",
            r"\b(Internal\s+Complaints?\s+Committee)\b", r"\b(ICC)\b",
        ], order_index=11, requires_ai=False, category="operational"),

        _rule("background_verification", "Background verification must comply with Information Technology Act 2000 and right to privacy (Puttaswamy judgment). Employee consent required. Limitation on scope of checks.", "YELLOW", [
            r"\b(background\s+verification)\b", r"\b(background\s+check)\b",
            r"\b(reference\s+check)\b",
        ], order_index=12, category="operational"),

        _rule("data_protection", "Employee personal data handling must comply with DPDP Act 2023. Consent for processing. Right to access and correction. Data minimization principle.", "YELLOW", [
            r"\b(data\s+protection)\b", r"\b(personal\s+data)\b",
            r"\b(DPDP)\b", r"\b(employee.*data)\b",
        ], order_index=13, category="data_protection"),

        _rule("salary_structure", "CTC breakdown should be clear: basic (min 40-50% of gross), HRA, special allowance, PF contribution, gratuity, bonus. Variable pay criteria defined.", "YELLOW", [
            r"\b(cost\s+to\s+company|CTC)\b", r"\b(salary\s+structure)\b",
            r"\b(basic\s+salary)\b", r"\b(compensation)\b",
        ], order_index=14, requires_ai=False, category="financial"),

        _rule("leave_policy", "Minimum leave per Shops & Establishments Act (varies by state). Standard: 24 earned leave, 12 casual leave, 12 sick leave. Carry-forward and encashment rules.", "GREEN", [
            r"\b(leave\s+policy)\b", r"\b(earned\s+leave)\b",
            r"\b(casual\s+leave)\b", r"\b(annual\s+leave)\b",
        ], order_index=15, requires_ai=False, category="operational"),

        _rule("anti_bribery", "Include Prevention of Corruption Act 1988 compliance clause. Employee must report any gifts/hospitality exceeding threshold (₹5,000).", "GREEN", [
            r"\b(anti[\s-]?bribery)\b", r"\b(anti[\s-]?corruption)\b",
            r"\b(Prevention\s+of\s+Corruption)\b",
        ], order_index=16, category="operational"),

        _rule("governing_law", "Indian law. Jurisdiction: courts at employer's registered office location.", "GREEN", [
            r"\b(govern(ed|ing)\s+(by|law))\b", r"\b(laws\s+of\s+India)\b",
        ], order_index=17, category="governance"),

        _rule("arbitration", "Employment disputes: consider Labour Court/Industrial Tribunal for workmen (Industrial Disputes Act 1947). For non-workmen, arbitration under Arbitration Act 1996.", "YELLOW", [
            r"\b(arbitration)\b", r"\b(dispute\s+resolution)\b",
        ], order_index=18, category="governance"),

        _rule("force_majeure", "Include force majeure clause for employment continuity. Pandemic/epidemic provisions. Employer's right to implement salary cuts/furlough during FM (with limits).", "YELLOW", [
            r"\b(force\s+majeure)\b", r"\b(act\s+of\s+god)\b",
        ], order_index=19, category="operational"),

        _rule("exclusive_service", "During employment, employee devotes full time and attention to employer. Moonlighting restrictions must be reasonable and comply with dual employment guidelines.", "YELLOW", [
            r"\b(exclusive\s+service)\b", r"\b(full\s+time.*attention)\b",
            r"\b(moonlighting)\b", r"\b(dual\s+employment)\b",
        ], order_index=20, category="restrictive_covenant"),

        _rule("invention_disclosure", "Employee must promptly disclose all inventions made during employment. Prior inventions to be listed in schedule. Clear ownership assignment for employer inventions.", "YELLOW", [
            r"\b(invention.*disclos(ure|e))\b", r"\b(prior\s+invention)\b",
            r"\b(disclose.*invention)\b",
        ], order_index=21, category="intellectual_property"),

        _rule("entire_agreement", "Entire agreement clause. Supersedes offer letter and prior discussions. Amendments in writing signed by both parties.", "GREEN", [
            r"\b(entire\s+agreement)\b", r"\b(supersedes)\b",
        ], order_index=22, category="formation"),

        _rule("probation", "Probation period: 3-6 months. During probation: shorter notice period (15 days). Confirmation in writing after successful completion.", "GREEN", [
            r"\b(probation(ary)?\s+period)\b", r"\b(probation)\b",
        ], order_index=23, requires_ai=False, category="term"),

        _rule("bonus", "Bonus structure clearly defined: performance criteria, measurement period, payment timeline. Statutory bonus under Payment of Bonus Act 1965 for eligible employees.", "YELLOW", [
            r"\b(bonus)\b", r"\b(performance.*incentive)\b",
            r"\b(Payment\s+of\s+Bonus)\b",
        ], order_index=24, requires_ai=False, category="financial"),

        _rule("severability", "Standard severability clause. Critical for employment agreements where individual provisions may be challenged.", "GREEN", [
            r"\b(severab(le|ility))\b",
        ], order_index=25, category="formation"),

        _rule("code_of_conduct", "Reference to company code of conduct and policies. Employee acknowledges receipt and agreement to comply. Changes to policies require reasonable notice.", "GREEN", [
            r"\b(code\s+of\s+conduct)\b", r"\b(company\s+polic(y|ies))\b",
        ], order_index=26, requires_ai=False, category="operational"),

        _rule("retirement_age", "Retirement age clearly stated (typically 58-60 for private sector). Superannuation benefits. Option for extension on mutual agreement.", "GREEN", [
            r"\b(retirement\s+age)\b", r"\b(superannuation)\b",
        ], order_index=27, requires_ai=False, category="term"),

        _rule("indemnification", "Employee indemnification limited to actual losses caused by gross negligence or willful misconduct. Cannot deduct from final settlement without consent.", "YELLOW", [
            r"\b(indemnif(y|ication))\b", r"\b(hold\s+harmless)\b",
        ], order_index=28, category="liability"),
    ],
)


# ============================================================
# TEMPLATE 4: MSA / SERVICES AGREEMENT (30 rules)
# ============================================================

MSA_SERVICES = PlaybookTemplate(
    id="msa_services",
    name="MSA / Services Agreement",
    description="Master Services Agreement review playbook covering SLAs, change orders, subcontracting, insurance, and service delivery terms.",
    category="msa",
    jurisdiction="",
    tags=["msa", "services", "outsourcing", "professional_services"],
    rules=[
        _rule("scope_of_services", "Scope of services clearly defined in SOW. Any work outside SOW requires written change order. Ambiguous scope creates disputes.", "YELLOW", [
            r"\b(scope\s+of\s+(services?|work))\b", r"\b(statement\s+of\s+work|SOW)\b",
        ], order_index=1, category="formation"),

        _rule("change_order", "Change order process defined: written request, impact assessment (timeline + cost), approval before work begins. No oral change orders.", "YELLOW", [
            r"\b(change\s+order)\b", r"\b(change\s+request)\b",
            r"\b(modification.*scope)\b", r"\b(variation\s+order)\b",
        ], order_index=2, category="operational"),

        _rule("acceptance_criteria", "Deliverables subject to acceptance testing with defined criteria. Acceptance period: 10-15 business days. Deemed acceptance if no written rejection.", "YELLOW", [
            r"\b(acceptance\s+(criteria|testing))\b", r"\b(deemed\s+accept(ed|ance))\b",
            r"\b(acceptance\s+period)\b",
        ], order_index=3, category="operational"),

        _rule("payment_terms", "Net 30 payment terms from invoice date. Late payment interest: RBI repo rate + 2% (India) or SOFR + 2% (international). No payment contingent on third-party approval.", "YELLOW", [
            r"\b(net\s+\d+)\b", r"\b(payment.*due.*within)\b",
            r"\b(invoice.*payable)\b",
        ], order_index=4, escalation_conditions=[r"\b(net\s+(?:6[1-9]|[7-9]\d))\b"], category="financial"),

        _rule("sla", "Service levels defined with measurable KPIs. Monthly reporting. Service credits for failures (not mere 'best efforts'). Repeated SLA failure = termination right.", "YELLOW", [
            r"\b(service\s+level)\b", r"\b(SLA)\b",
            r"\b(key\s+performance\s+indicator|KPI)\b",
        ], order_index=5, category="saas_technology"),

        _rule("subcontracting", "Provider may not subcontract without prior written consent. Provider remains fully liable for subcontractor performance. Right to approve/reject key subcontractors.", "YELLOW", [
            r"\b(subcontract)\b", r"\b(sub[\s-]?contract)\b",
            r"\b(engage.*third\s+party.*perform)\b",
        ], order_index=6, category="operational"),

        _rule("insurance", "Provider must maintain: professional indemnity ($2-5M), general liability ($1-2M), worker's compensation, cyber liability. Certificates annually.", "YELLOW", [
            r"\b(maintain.*insurance)\b", r"\b(insurance\s+coverage)\b",
            r"\b(professional\s+indemnity)\b",
        ], order_index=7, category="operational"),

        _rule("liability_cap", "Total liability capped at 12 months of fees paid under the SOW (not aggregate MSA). Uncapped for: IP infringement, data breaches, confidentiality, wilful misconduct.", "YELLOW", [
            r"\b(liability.*shall\s+not\s+exceed)\b", r"\b(aggregate\s+liability)\b",
            r"\b(liability\s+cap)\b",
        ], order_index=8, category="liability"),

        _rule("indemnification", "Mutual indemnification. Provider indemnifies for: IP infringement, negligence, breach of law. Customer indemnifies for: materials provided, instructions given.", "YELLOW", [
            r"\b(indemnif(y|ication))\b", r"\b(hold\s+harmless)\b",
        ], order_index=9, escalation_conditions=[r"\b(one[\s-]?sided|unilateral)\b"], category="liability"),

        _rule("consequential_damages", "Mutual exclusion of consequential/indirect damages. Carve-outs for: IP infringement, confidentiality breach, data breach, wilful misconduct.", "YELLOW", [
            r"\b(consequential\s+damages)\b", r"\b(indirect.*damages)\b",
        ], order_index=10, category="liability"),

        _rule("ip_ownership", "Customer owns all deliverables and work product. Provider retains pre-existing IP with perpetual license to customer. Background IP clearly identified.", "YELLOW", [
            r"\b(intellectual\s+property.*own)\b", r"\b(work\s+product.*belongs)\b",
            r"\b(deliverables.*owned)\b",
        ], order_index=11, category="intellectual_property"),

        _rule("confidentiality", "Mutual confidentiality. 5-year survival. Standard exceptions. Return/destroy within 30 days of termination.", "YELLOW", [
            r"\b(confidential\s+information)\b", r"\b(maintain.*confidential)\b",
        ], order_index=12, category="confidentiality"),

        _rule("data_protection", "Comply with applicable data protection laws. Execute DPA if personal data processed. Data breach notification within 72 hours.", "YELLOW", [
            r"\b(data\s+protection)\b", r"\b(personal\s+data)\b",
            r"\b(GDPR|DPDP)\b",
        ], order_index=13, category="data_protection"),

        _rule("termination_for_convenience", "Either party: 60 days written notice. Customer pays for work completed + reasonable wind-down costs. No penalty for early termination.", "YELLOW", [
            r"\b(terminate\s+for\s+convenience)\b", r"\b(terminate\s+without\s+cause)\b",
        ], order_index=14, category="term"),

        _rule("termination_for_cause", "Material breach + 30-day cure period. Insolvency/bankruptcy = immediate termination. Repeated SLA failures (3 in 6 months) = termination for cause.", "YELLOW", [
            r"\b(terminate\s+for\s+cause)\b", r"\b(material\s+breach)\b",
        ], order_index=15, category="term"),

        _rule("transition_assistance", "Provider must provide transition assistance for 90 days post-termination at then-current rates. Knowledge transfer, documentation, and data migration included.", "YELLOW", [
            r"\b(transition\s+assistance)\b", r"\b(knowledge\s+transfer)\b",
            r"\b(wind-down)\b",
        ], order_index=16, category="term"),

        _rule("audit_rights", "Customer may audit provider's compliance once per year with 30 days notice. If non-compliance found, provider bears audit costs and remediates within 30 days.", "YELLOW", [
            r"\b(right\s+to\s+audit)\b", r"\b(audit\s+rights)\b",
            r"\b(inspect.*records)\b",
        ], order_index=17, category="financial"),

        _rule("key_personnel", "Named key personnel in SOW. Provider cannot reassign without 30 days notice and customer approval. Replacement of equivalent skill/experience.", "YELLOW", [
            r"\b(key\s+personnel)\b", r"\b(named\s+resources?)\b",
            r"\b(dedicated\s+team)\b",
        ], order_index=18, category="operational"),

        _rule("non_solicitation", "Mutual non-solicitation of employees for 12 months. Exception: general job advertisements. Doesn't apply if employee approaches independently.", "YELLOW", [
            r"\b(non[\s-]?solicit(ation)?)\b",
        ], order_index=19, category="restrictive_covenant"),

        _rule("force_majeure", "Standard force majeure with pandemic inclusion. Obligation to mitigate. 90-day FM = termination right. No liability for FM delays.", "YELLOW", [
            r"\b(force\s+majeure)\b", r"\b(act\s+of\s+god)\b",
        ], order_index=20, category="operational"),

        _rule("governing_law", "Appropriate governing law for both parties. International MSAs: consider Singapore, England, or New York.", "GREEN", [
            r"\b(govern(ed|ing)\s+(by|law))\b",
        ], order_index=21, category="governance"),

        _rule("dispute_resolution", "Tiered: (1) project managers discuss 10 days, (2) senior executives 20 days, (3) mediation 30 days, (4) arbitration.", "GREEN", [
            r"\b(dispute\s+resolution)\b", r"\b(resolve.*dispute)\b",
        ], order_index=22, category="governance"),

        _rule("warranty", "Provider warrants services performed in professional and workmanlike manner. Deliverables conform to specifications. 90-day warranty period post-acceptance.", "YELLOW", [
            r"\b(warrant(y|ies|s)?)\b", r"\b(workmanlike)\b",
            r"\b(professional\s+standard)\b",
        ], order_index=23, category="reps_warranties"),

        _rule("taxes", "Each party responsible for own taxes. If withholding required, gross-up clause. GST/VAT clearly allocated. Tax invoices provided.", "YELLOW", [
            r"\b(tax(es)?)\b", r"\b(GST)\b", r"\b(withholding)\b",
        ], order_index=24, category="financial"),

        _rule("assignment", "No assignment without consent. Exception: affiliates, corporate restructuring. Provider assignment to competitor requires customer consent.", "YELLOW", [
            r"\b(may\s+not\s+assign)\b", r"\b(assignment.*consent)\b",
        ], order_index=25, category="operational"),

        _rule("entire_agreement", "MSA + SOW + Change Orders constitute entire agreement. Order of precedence: MSA > SOW > Change Order (unless SOW expressly overrides).", "GREEN", [
            r"\b(entire\s+agreement)\b", r"\b(order\s+of\s+precedence)\b",
        ], order_index=26, category="formation"),

        _rule("anti_bribery", "Both parties comply with anti-bribery laws. No facilitation payments. Gift/hospitality policy. Right to audit compliance.", "GREEN", [
            r"\b(anti[\s-]?bribery)\b", r"\b(anti[\s-]?corruption)\b",
        ], order_index=27, category="operational"),

        _rule("business_continuity", "Provider must maintain business continuity plan. Annual BCP testing. RPO/RTO commitments for critical services.", "YELLOW", [
            r"\b(business\s+continuity)\b", r"\b(disaster\s+recovery)\b",
            r"\b(BCP)\b",
        ], order_index=28, category="operational"),

        _rule("compliance", "Both parties comply with applicable laws and regulations. Provider complies with industry-specific regulations relevant to services.", "GREEN", [
            r"\b(comply.*applicable.*law)\b", r"\b(regulatory.*compliance)\b",
        ], order_index=29, category="operational"),

        _rule("notices", "Written notices via email + registered post. Effective on receipt. Termination notices require senior officer signature.", "GREEN", [
            r"\b(notice.*shall\s+be)\b", r"\b(written\s+notice)\b",
        ], order_index=30, category="operational"),
    ],
)


# ============================================================
# TEMPLATE 5: M&A / SPA (25 rules)
# ============================================================

MA_SPA = PlaybookTemplate(
    id="ma_spa",
    name="M&A / Share Purchase Agreement",
    description="M&A transaction review playbook covering MAC clauses, reps & warranties, indemnification, FEMA/CCI compliance (India), and closing conditions.",
    category="custom",
    jurisdiction="IN",
    tags=["ma", "spa", "acquisition", "merger", "fema", "cci"],
    rules=[
        _rule("mac_clause", "Material Adverse Change clause must be narrowly defined. Exclude: general economic conditions, industry-wide changes, changes in law, pandemic effects. Qualitative + quantitative thresholds.", "RED", [
            r"\b(material\s+adverse\s+(change|effect|event)|MAC|MAE)\b",
            r"\b(materially\s+adverse)\b",
        ], "MAC should have specific financial threshold (e.g., >15% revenue decline) and exclude force majeure events.", order_index=1, is_deal_breaker=True, category="formation"),

        _rule("reps_warranties", "Comprehensive R&W schedule. Seller warrants: financial statements accurate, no undisclosed liabilities, material contracts valid, compliance with law, IP ownership, no litigation. Buyer: authority, financing.", "RED", [
            r"\b(represent(s|ation)?\s+and\s+warrant(s|y|ies)?)\b",
            r"\b(seller\s+represents)\b", r"\b(warrant(s|ies)\s+that)\b",
        ], "All R&W must survive closing for minimum 18-24 months (general) and statute of limitations period (fundamental).", order_index=2, is_deal_breaker=True, category="reps_warranties"),

        _rule("indemnification", "Seller indemnifies buyer for R&W breaches. Survival: 18 months general, 36 months tax/employment, statute of limitations for fundamental reps (title, authority, tax).", "RED", [
            r"\b(indemnif(y|ication))\b", r"\b(hold\s+harmless)\b",
        ], "Indemnification cap at 100% of purchase price for fundamental reps, 20-30% for general reps.", order_index=3, is_deal_breaker=True, category="liability"),

        _rule("indemnification_basket", "De minimis threshold (claims <₹5L ignored) + basket/deductible (aggregate threshold before indemnification kicks in, typically 1-2% of deal value). Tipping vs true deductible.", "YELLOW", [
            r"\b(basket|deductible)\b", r"\b(de\s+minimis)\b",
            r"\b(threshold.*indemnif)\b", r"\b(tipping\s+basket)\b",
        ], order_index=4, category="liability"),

        _rule("escrow", "Escrow of 10-15% of purchase price held for 18 months to secure indemnification claims. Joint instructions for release. Escrow agent: reputable bank.", "YELLOW", [
            r"\b(escrow)\b", r"\b(holdback)\b",
            r"\b(escrow\s+agent)\b", r"\b(retention\s+amount)\b",
        ], order_index=5, category="financial"),

        _rule("earnout", "Earnout provisions: clear metrics (revenue/EBITDA), measurement period, accounting methodology, buyer's obligation to operate business in ordinary course. Anti-manipulation protections.", "YELLOW", [
            r"\b(earn[\s-]?out)\b", r"\b(contingent\s+consideration)\b",
            r"\b(milestone\s+payment)\b", r"\b(deferred\s+consideration)\b",
        ], order_index=6, category="financial"),

        _rule("closing_conditions", "Conditions precedent: CCI approval, FEMA compliance, third-party consents, no MAC, compliance certificate, bring-down of R&W.", "YELLOW", [
            r"\b(conditions?\s+precedent)\b", r"\b(closing\s+condition)\b",
            r"\b(condition.*completion)\b",
        ], order_index=7, category="formation"),

        _rule("fema_compliance", "FEMA compliance for cross-border M&A: RBI approval (if required), pricing guidelines, reporting requirements (FC-GPR/FC-TRS), sectoral caps, FDI policy.", "RED", [
            r"\b(FEMA)\b", r"\b(Foreign\s+Exchange\s+Management)\b",
            r"\b(RBI\s+approval)\b", r"\b(FDI)\b", r"\b(FC-GPR|FC-TRS)\b",
        ], "Ensure FEMA compliance is a condition precedent. Non-compliance = void transaction.", order_index=8, is_deal_breaker=True, category="governance"),

        _rule("cci_approval", "Competition Commission of India approval required if: (a) combined assets >₹2,000 crores or turnover >₹6,000 crores (India), or (b) global assets >$1B or turnover >$500M.", "YELLOW", [
            r"\b(CCI|Competition\s+Commission)\b", r"\b(competition\s+approval)\b",
            r"\b(antitrust)\b", r"\b(merger\s+control)\b",
        ], order_index=9, category="governance"),

        _rule("non_compete", "Post-closing non-compete for seller/promoters: 3-5 years, limited to relevant business and geography. Adequate consideration. Note: S.27 does not apply to sale of goodwill.", "YELLOW", [
            r"\b(non[\s-]?compete)\b", r"\b(shall\s+not\s+compete)\b",
            r"\b(restrictive\s+covenant)\b",
        ], "S.27 exception: non-compete in sale of goodwill is enforceable if reasonable.", order_index=10, category="restrictive_covenant"),

        _rule("non_solicitation", "Seller/promoters shall not solicit employees or customers of target for 3 years post-closing.", "YELLOW", [
            r"\b(non[\s-]?solicit(ation)?)\b",
        ], order_index=11, category="restrictive_covenant"),

        _rule("interim_operations", "Between signing and closing: seller operates business in ordinary course. No material contracts, no dividends, no capital expenditure above threshold, no employee changes without buyer consent.", "YELLOW", [
            r"\b(interim\s+(?:period|operation|covenant))\b", r"\b(ordinary\s+course)\b",
            r"\b(between\s+signing\s+and\s+closing)\b",
        ], order_index=12, category="operational"),

        _rule("disclosure_schedules", "Comprehensive disclosure schedules against each R&W. Specific disclosures qualify the R&W. Update mechanism between signing and closing.", "YELLOW", [
            r"\b(disclosure\s+schedule)\b", r"\b(disclosure\s+letter)\b",
            r"\b(exceptions?\s+to\s+represent)\b",
        ], order_index=13, category="reps_warranties"),

        _rule("purchase_price", "Purchase price mechanism: locked box (fixed price with leakage protections) vs completion accounts (post-closing adjustment). For India, locked box preferred.", "YELLOW", [
            r"\b(purchase\s+price)\b", r"\b(consideration)\b",
            r"\b(locked\s+box)\b", r"\b(completion\s+accounts?)\b",
        ], order_index=14, category="financial"),

        _rule("tax_indemnity", "Separate tax indemnity (not subject to general cap/basket). Seller indemnifies for pre-closing tax liabilities. Buyer controls post-closing tax matters. Tax sharing agreement.", "RED", [
            r"\b(tax\s+indemnit(y|ification))\b", r"\b(pre-closing\s+tax)\b",
            r"\b(tax.*liabilit)\b",
        ], "Tax indemnity should survive for limitation period under Income Tax Act (6-7 years).", order_index=15, is_deal_breaker=True, category="liability"),

        _rule("employee_matters", "Continuity of employment terms. No forced terminations pre-closing without buyer consent. ESOP/stock option treatment. Gratuity/PF liabilities quantified.", "YELLOW", [
            r"\b(employee\s+matters?)\b", r"\b(continuity.*employment)\b",
            r"\b(ESOP|stock\s+option)\b",
        ], order_index=16, category="operational"),

        _rule("ip_reps", "Seller warrants: (a) owns/has right to all IP, (b) no infringement claims, (c) IP is valid and subsisting, (d) no open-source contamination, (e) all registrations current.", "YELLOW", [
            r"\b(intellectual\s+property.*represent)\b", r"\b(IP.*warrant)\b",
            r"\b(own.*intellectual\s+property)\b",
        ], order_index=17, category="intellectual_property"),

        _rule("material_contracts", "Schedule of material contracts. Consent/assignment provisions in change of control. No undisclosed commitments >₹50L.", "YELLOW", [
            r"\b(material\s+contract)\b", r"\b(key\s+contract)\b",
            r"\b(change\s+of\s+control.*consent)\b",
        ], order_index=18, category="operational"),

        _rule("governing_law", "Indian law for domestic M&A. For cross-border: consider Singapore or English law for neutral jurisdiction. Arbitration: SIAC or ICC.", "GREEN", [
            r"\b(govern(ed|ing)\s+(by|law))\b",
        ], order_index=19, category="governance"),

        _rule("stamp_duty", "Stamp duty on share transfer (varies by state: 0.25% typical for shares). Stamp duty on SPA. Ensure proper stamping to avoid inadmissibility.", "YELLOW", [
            r"\b(stamp\s+duty)\b", r"\b(Indian\s+Stamp\s+Act)\b",
        ], order_index=20, requires_ai=False, category="financial"),

        _rule("termination_rights", "Either party may terminate if: (a) closing conditions not met by long-stop date, (b) MAC occurs, (c) material breach of interim covenants. Break fee: 1-3% of deal value.", "YELLOW", [
            r"\b(terminat(e|ion).*agreement)\b", r"\b(long[\s-]?stop\s+date)\b",
            r"\b(break\s+fee|termination\s+fee)\b",
        ], order_index=21, category="term"),

        _rule("confidentiality", "Strict confidentiality around deal terms. Standstill provisions. No-shop/go-shop clause. Public announcement jointly agreed.", "YELLOW", [
            r"\b(confidential)\b", r"\b(standstill)\b",
            r"\b(no[\s-]?shop)\b", r"\b(go[\s-]?shop)\b",
        ], order_index=22, category="confidentiality"),

        _rule("anti_bribery", "Target's compliance with Prevention of Corruption Act 1988 warranted. Due diligence on past compliance. Indemnity for pre-closing violations.", "YELLOW", [
            r"\b(anti[\s-]?bribery)\b", r"\b(Prevention\s+of\s+Corruption)\b",
        ], order_index=23, category="operational"),

        _rule("regulatory_approvals", "List all required regulatory approvals: CCI, RBI/FEMA, SEBI (if listed entity), sector-specific regulators. Timeline for applications.", "YELLOW", [
            r"\b(regulatory\s+approval)\b", r"\b(government\s+approval)\b",
            r"\b(SEBI)\b",
        ], order_index=24, category="governance"),

        _rule("dispute_resolution", "Arbitration for deal disputes. Seat: Mumbai/Singapore/London. 3 arbitrators. Emergency arbitrator available for interim relief. Costs: unsuccessful party bears.", "YELLOW", [
            r"\b(arbitration)\b", r"\b(dispute\s+resolution)\b",
        ], order_index=25, category="governance"),
    ],
)


# ============================================================
# TEMPLATE REGISTRY
# ============================================================

_TEMPLATES: Dict[str, PlaybookTemplate] = {
    t.id: t for t in [NDA_INDIAN_LAW, SAAS_AGREEMENT, EMPLOYMENT_INDIA, MSA_SERVICES, MA_SPA]
}


def get_template(template_id: str) -> Optional[PlaybookTemplate]:
    """Get a playbook template by ID."""
    return _TEMPLATES.get(template_id)


def list_templates() -> List[PlaybookTemplate]:
    """List all available playbook templates."""
    return list(_TEMPLATES.values())


def get_templates_by_category(category: str) -> List[PlaybookTemplate]:
    """Get templates filtered by category."""
    return [t for t in _TEMPLATES.values() if t.category == category]


def get_templates_by_jurisdiction(jurisdiction: str) -> List[PlaybookTemplate]:
    """Get templates filtered by jurisdiction."""
    return [t for t in _TEMPLATES.values() if t.jurisdiction == jurisdiction]


async def create_playbook_from_template(
    template_id: str,
    org_id,
    user_id,
    db,
    custom_name: str = None,
) -> dict:
    """
    Create a Playbook + PlaybookRules in the database from a template.

    Args:
        template_id: Template identifier (e.g., "nda_indian_law")
        org_id: Organization UUID
        user_id: User UUID who is creating the playbook
        db: AsyncSession database session
        custom_name: Optional custom name for the playbook

    Returns:
        Dict with playbook_id and rule_count
    """
    from sqlalchemy import text as sql_text
    import uuid as _uuid

    template = get_template(template_id)
    if not template:
        raise ValueError(f"Template '{template_id}' not found")

    playbook_id = _uuid.uuid4()
    playbook_name = custom_name or template.name

    # Create playbook
    await db.execute(
        sql_text("""
            INSERT INTO playbooks (id, organization_id, created_by, name, description, category, is_public, is_default, version)
            VALUES (:id, :org_id, :user_id, :name, :desc, :category, false, false, 1)
        """),
        {
            "id": playbook_id,
            "org_id": org_id,
            "user_id": user_id,
            "name": playbook_name,
            "desc": template.description,
            "category": template.category,
        },
    )

    # Create rules
    for rule_dict in template.rules:
        rule_id = _uuid.uuid4()
        await db.execute(
            sql_text("""
                INSERT INTO playbook_rules (
                    id, playbook_id, clause_type, primary_position, fallback_position,
                    risk_level, is_deal_breaker, detection_patterns, order_index,
                    requires_ai_verification, category
                ) VALUES (
                    :id, :pb_id, :clause_type, :primary, :fallback,
                    :risk, :deal_breaker, :patterns::jsonb, :order_idx,
                    :requires_ai, :category
                )
            """),
            {
                "id": rule_id,
                "pb_id": playbook_id,
                "clause_type": rule_dict["clause_type"],
                "primary": rule_dict["primary_position"],
                "fallback": rule_dict.get("fallback_position"),
                "risk": rule_dict["risk_level"],
                "deal_breaker": rule_dict["is_deal_breaker"],
                "patterns": json.dumps(rule_dict["detection_patterns"]) if rule_dict.get("detection_patterns") else "{}",
                "order_idx": rule_dict.get("order_index", 0),
                "requires_ai": rule_dict.get("requires_ai_verification", True),
                "category": rule_dict.get("category"),
            },
        )

    await db.commit()

    return {
        "playbook_id": str(playbook_id),
        "name": playbook_name,
        "template_id": template_id,
        "rule_count": len(template.rules),
    }
