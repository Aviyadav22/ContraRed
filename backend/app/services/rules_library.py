"""
Rules Library - 75 clause detection rules organized by category.

Phase 5: Contract Coverage expansion from 16 to 75 rules.
Three-layer detection: Enhanced Regex -> Scope Analysis -> AI Verification

Categories:
  1. Formation & Structure (5 rules)
  2. Term & Termination (7 rules)
  3. Financial (8 rules)
  4. Liability & Indemnification (8 rules)
  5. Intellectual Property (7 rules)
  6. Confidentiality & Data (8 rules)
  7. Representations & Warranties (6 rules)
  8. Restrictive Covenants (5 rules)
  9. Governance & Disputes (6 rules)
  10. Operational (9 rules)
  11. SaaS / Technology (6 rules)
"""

from typing import Dict, List, Optional

from app.services.rule_engine import RulePattern, SmartRule, RiskLevel

# ---------------------------------------------------------------------------
# Category constants
# ---------------------------------------------------------------------------
CATEGORY_FORMATION = "formation"
CATEGORY_TERM = "term"
CATEGORY_FINANCIAL = "financial"
CATEGORY_LIABILITY = "liability"
CATEGORY_IP = "intellectual_property"
CATEGORY_CONFIDENTIALITY = "confidentiality"
CATEGORY_REPS_WARRANTIES = "reps_warranties"
CATEGORY_RESTRICTIVE = "restrictive_covenant"
CATEGORY_GOVERNANCE = "governance"
CATEGORY_OPERATIONAL = "operational"
CATEGORY_SAAS = "saas_technology"

# ============================================================
# 1. FORMATION & STRUCTURE (5 rules)
# ============================================================

FORMATION_RULES: List[RulePattern] = [
    RulePattern(
        id="definitions_clause",
        name="Definitions Clause",
        clause_type="definitions",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(defined\s+terms)\b",
            r"\b(definitions)\b",
            r"\b(hereinafter\s+referred\s+to\s+as)\b",
            r'"[A-Z][^"]+"\s+means\b',
            r"\b(shall\s+have\s+the\s+meaning)\b",
        ],
        primary_position="Ensure all key terms are clearly defined with unambiguous meaning",
    ),
    RulePattern(
        id="recitals_clause",
        name="Recitals / Whereas",
        clause_type="recitals",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\bWHEREAS\b",
            r"\b(recitals)\b",
            r"\b(background)\b",
            r"\b(preamble)\b",
        ],
        primary_position="Recitals should accurately reflect the commercial intent of the parties",
    ),
    RulePattern(
        id="entire_agreement",
        name="Entire Agreement",
        clause_type="entire_agreement",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(entire\s+agreement)\b",
            r"\b(constitutes\s+the\s+entire)\b",
            r"\b(supersedes\s+all\s+prior)\b",
            r"\b(whole\s+agreement)\b",
            r"\b(embodies\s+the\s+complete)\b",
        ],
        primary_position="Standard entire agreement clause — confirm no side letters or oral agreements are intended to survive",
    ),
    SmartRule(
        id="amendments_clause",
        name="Amendment Restrictions",
        clause_type="amendments",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(amended\s+only\s+in\s+writing)\b",
            r"\b(no\s+amendment\s+unless)\b",
            r"\b(modification\s+requires\s+written\s+consent)\b",
            r"\b(amend(ment|ed)?.*\s+in\s+writing\s+signed)\b",
            r"\b(variation.*\s+in\s+writing)\b",
        ],
        primary_position="All amendments must be in writing signed by both parties",
        escalation_conditions=[
            r"\b(oral\s+amendments?\s+(are\s+)?(permitted|allowed|valid))\b",
            r"\b(may\s+be\s+amended\s+orally)\b",
        ],
    ),
    RulePattern(
        id="severability",
        name="Severability",
        clause_type="severability",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(severable)\b",
            r"\b(severability)\b",
            r"\bif\s+any\s+provision.*invalid\b",
            r"\b(invalidity.*shall\s+not\s+affect)\b",
            r"\b(unenforceable.*remaining\s+provisions)\b",
        ],
        primary_position="Standard severability clause ensuring invalid provisions do not void the entire agreement",
    ),
]

# ============================================================
# 2. TERM & TERMINATION (7 rules)
# ============================================================

TERM_RULES: List[RulePattern] = [
    RulePattern(
        id="contract_duration",
        name="Contract Duration",
        clause_type="term",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(term\s+of\s+this\s+agreement)\b",
            r"\b(initial\s+term)\b",
            r"\b(effective\s+date)\b",
            r"\b(commencement\s+date)\b",
            r"\b(term\s+shall\s+(be|commence))\b",
        ],
        primary_position="Contract term should be clearly defined with specific start and end dates",
    ),
    # auto_renewal — imported from DEFAULT_RULES
    SmartRule(
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
        context_window=500,
        escalation_conditions=[
            r"\b(no\s+opt[\s-]?out)\b",
            r"\b(irrevocable)\b",
            r"\b(without\s+(right\s+to\s+)?terminat)\b",
            r"\b(cannot\s+be\s+cancelled)\b",
        ],
        de_escalation_conditions=[
            r"\b(\d+\s+days?\s+(written\s+)?notice)\b",
            r"\b(opt[\s-]?out)\b",
            r"\b(non[\s-]?renewal\s+notice)\b",
        ],
    ),
    SmartRule(
        id="termination_for_cause",
        name="Termination for Cause",
        clause_type="termination",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(terminate\s+for\s+cause)\b",
            r"\b(material\s+breach)\b",
            r"\b(terminate.*upon.*breach)\b",
            r"\b(termination\s+for\s+default)\b",
            r"\b(right\s+to\s+terminate.*breach)\b",
        ],
        primary_position="Termination for cause should require written notice specifying the breach and a reasonable cure period",
        context_window=500,
        escalation_conditions=[
            r"\b(any\s+breach)\b",
            r"\b(without\s+cure)\b",
            r"\b(immediate(ly)?\s+terminat)\b",
            r"\b(no\s+opportunity\s+to\s+(cure|remedy))\b",
        ],
        de_escalation_conditions=[
            r"\b(cure\s+period)\b",
            r"\b(opportunity\s+to\s+cure)\b",
            r"\b(remedy\s+within\s+\d+\s+days)\b",
            r"\b(right\s+to\s+cure)\b",
            r"\b(material\s+breach)\b",
        ],
    ),
    SmartRule(
        id="termination_for_convenience",
        name="Termination for Convenience",
        clause_type="termination",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(terminate\s+for\s+convenience)\b",
            r"\b(terminate\s+without\s+cause.*notice)\b",
            r"\b(terminate.*upon.*\d+\s*days.*notice)\b",
            r"\b(termination\s+without\s+cause)\b",
        ],
        primary_position="Termination for convenience should require at least 30 days prior written notice",
        context_window=500,
        escalation_conditions=[
            r"\b(immediately\s+without\s+notice)\b",
            r"\b(without\s+(any\s+)?prior\s+notice)\b",
            r"\b(terminate\s+at\s+any\s+time\s+without\s+notice)\b",
            r"\b(sole\s+discretion)\b",
        ],
        de_escalation_conditions=[
            r"\b(either\s+party)\b",
            r"\b(reasonable\s+notice)\b",
            r"\b(\d+\s+days?\s+(prior\s+)?(written\s+)?notice)\b",
            r"\b(mutual\s+right)\b",
        ],
    ),
    RulePattern(
        id="cure_period",
        name="Cure / Remedy Period",
        clause_type="termination",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(cure\s+period)\b",
            r"\b(right\s+to\s+cure)\b",
            r"\b(remedy\s+within\s+\d+\s+days)\b",
            r"\b(opportunity\s+to\s+cure)\b",
            r"\b(cure\s+such\s+breach\s+within)\b",
        ],
        primary_position="Cure period of at least 30 days for non-material breaches",
    ),
    RulePattern(
        id="survival_clause",
        name="Survival of Obligations",
        clause_type="term",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(shall\s+survive)\b",
            r"\b(survive\s+termination)\b",
            r"\b(survival)\b",
            r"\b(surviving\s+provisions)\b",
            r"\b(survive\s+the\s+expiration)\b",
        ],
        primary_position="Survival clause should clearly list which provisions survive termination and for how long",
    ),
    RulePattern(
        id="transition_assistance",
        name="Transition Assistance",
        clause_type="termination",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(transition\s+assistance)\b",
            r"\b(wind[\s-]?down)\b",
            r"\b(transition\s+period)\b",
            r"\b(migration\s+assistance)\b",
            r"\b(exit\s+assistance)\b",
            r"\b(disengagement\s+assistance)\b",
        ],
        primary_position="Transition assistance for at least 90 days at reasonable cost upon termination or expiry",
    ),
]

# ============================================================
# 3. FINANCIAL (8 rules)
# ============================================================

FINANCIAL_RULES: List[RulePattern] = [
    SmartRule(
        id="payment_terms",
        name="Payment Terms",
        clause_type="payment",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\bnet\s+\d+\b",
            r"\b(payment.*due.*within)\b",
            r"\b(invoice.*payable)\b",
            r"\b(payment\s+terms)\b",
            r"\b(due\s+and\s+payable\s+within)\b",
        ],
        primary_position="Payment within 30 days of invoice (Net 30) with clear invoicing procedures",
        escalation_conditions=[
            r"\bnet\s+(6[1-9]|[7-9]\d|1\d{2,})\b",
            r"\b(payment.*within\s+(6[1-9]|[7-9]\d|1\d{2,})\s+days)\b",
        ],
        de_escalation_conditions=[
            r"\bnet\s+(1[0-9]|2[0-9]|30)\b",
            r"\b(payment.*within\s+(1[0-9]|2[0-9]|30)\s+days)\b",
        ],
    ),
    SmartRule(
        id="late_payment",
        name="Late Payment Penalties",
        clause_type="payment",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(late\s+payment)\b",
            r"\b(overdue.*interest)\b",
            r"\b(penalty.*late)\b",
            r"\b(interest.*overdue)\b",
            r"\b(late\s+fee)\b",
            r"\b(interest\s+at.*per\s+(month|annum))\b",
        ],
        primary_position="Late payment interest should not exceed 1.5% per month or the maximum legal rate",
        context_window=500,
        escalation_conditions=[
            r"\b(compound(ed|ing)?\s+interest)\b",
            r"\b(cumulative\s+(interest|penalty))\b",
            r"\b(immediate\s+termination.*late)\b",
            r"\b(acceleration\s+of\s+all\s+amounts)\b",
        ],
        de_escalation_conditions=[
            r"\b(grace\s+period)\b",
            r"\b(reasonable\s+(interest|rate))\b",
            r"\b(\d+\s+days?\s+(grace|cure))\b",
            r"\b(simple\s+interest)\b",
        ],
    ),
    RulePattern(
        id="price_escalation",
        name="Price Escalation",
        clause_type="pricing",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(price\s+increase)\b",
            r"\b(price\s+escalation)\b",
            r"\b(annual.*increase)\b",
            r"\b(CPI\s+adjustment)\b",
            r"\b(cost\s+of\s+living\s+adjustment)\b",
            r"\b(index(ed|ation).*price)\b",
        ],
        primary_position="Price increases capped at CPI or a fixed percentage (e.g. 5%) with 60 days prior notice",
    ),
    RulePattern(
        id="taxes_clause",
        name="Tax Obligations",
        clause_type="tax",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(responsible\s+for.*taxes)\b",
            r"\b(tax\s+obligations)\b",
            r"\b(withholding\s+tax)\b",
            r"\bGST\b",
            r"\b(sales\s+tax)\b",
            r"\b(value\s+added\s+tax|VAT)\b",
            r"\b(tax(es)?\s+(shall\s+be|are)\s+(borne|paid)\s+by)\b",
        ],
        primary_position="Each party responsible for its own taxes; withholding obligations clearly allocated",
    ),
    SmartRule(
        id="set_off_rights",
        name="Set-Off / Deduction Rights",
        clause_type="payment",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(right\s+of\s+set[\s-]?off)\b",
            r"\b(set[\s-]?off)\b",
            r"\b(deduct.*amount.*due)\b",
            r"\b(offset)\b",
            r"\b(right\s+to\s+withhold\s+payment)\b",
        ],
        primary_position="Set-off rights should be mutual and limited to undisputed amounts",
        context_window=500,
        escalation_conditions=[
            r"\b(sole\s+discretion)\b",
            r"\b(unilateral(ly)?)\b",
            r"\b(without\s+(prior\s+)?notice)\b",
            r"\b(any\s+amounts?\s+(it\s+)?deems)\b",
        ],
        de_escalation_conditions=[
            r"\b(mutual(ly)?)\b",
            r"\b(undisputed\s+amounts?)\b",
            r"\b(agreed\s+amounts?)\b",
        ],
    ),
    RulePattern(
        id="audit_rights",
        name="Financial Audit Rights",
        clause_type="audit",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(right\s+to\s+audit)\b",
            r"\b(audit\s+rights)\b",
            r"\b(inspect.*books.*records)\b",
            r"\b(audit.*accounts)\b",
            r"\b(examination\s+of\s+(books|records|accounts))\b",
        ],
        primary_position="Audit rights with reasonable notice (30 days), during business hours, no more than once per year, at auditor's cost",
    ),
    SmartRule(
        id="most_favored_nation",
        name="Most Favored Nation Pricing",
        clause_type="pricing",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(most\s+favou?red)\b",
            r"\bMFN\b",
            r"\b(no\s+less\s+favou?rable.*pricing)\b",
            r"\b(best\s+price\s+guarantee)\b",
            r"\b(price\s+parity)\b",
        ],
        primary_position="MFN clause should be mutual with clear benchmarking criteria and reasonable comparison period",
        escalation_conditions=[
            r"\b(unilateral(ly)?)\b",
            r"\b(sole\s+discretion)\b",
        ],
    ),
    RulePattern(
        id="currency_clause",
        name="Currency / FX Provisions",
        clause_type="payment",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(currency.*payment)\b",
            r"\b(exchange\s+rate)\b",
            r"\b(denominated\s+in)\b",
            r"\b(payable\s+in\s+(USD|INR|EUR|GBP|AUD|CAD|SGD))\b",
            r"\b(foreign\s+exchange)\b",
        ],
        primary_position="Payment currency clearly specified; FX risk allocation defined if cross-border",
    ),
]

# ============================================================
# 4. LIABILITY & INDEMNIFICATION (8 rules)
# ============================================================

LIABILITY_RULES: List[RulePattern] = [
    # unlimited_liability — from DEFAULT_RULES
    SmartRule(
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
        context_window=500,
        negative_patterns=[
            r"\bmutual(ly)?\b.*\bcapped?\s+(at|to)\b",
        ],
        de_escalation_conditions=[
            r"\b(capped?\s+(at|to))\b",
            r"\b(aggregate.*not\s+exceed)\b",
            r"\b(limited\s+to\s+the\s+(total|aggregate))\b",
        ],
    ),
    SmartRule(
        id="liability_cap",
        name="Liability Cap",
        clause_type="liability",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(aggregate\s+liability.*shall\s+not\s+exceed)\b",
            r"\b(total\s+liability.*limited\s+to)\b",
            r"\b(liability\s+cap)\b",
            r"\b(maximum\s+liability)\b",
            r"\b(liability.*not\s+(to\s+)?exceed)\b",
            r"\b(cap\s+on\s+liability)\b",
        ],
        primary_position="Liability cap at 12 months of fees paid; separate super-cap for IP/confidentiality breaches",
        context_window=500,
        escalation_conditions=[
            r"\b(one[\s-]?sided|only\s+the\s+(vendor|provider|supplier))\b",
            r"\b(less\s+than|1x?\s+month)\b",
            r"\b(nominal\s+(cap|amount))\b",
        ],
        de_escalation_conditions=[
            r"\b(mutual(ly)?)\b",
            r"\b(12\s+months?\s+(of\s+)?fees)\b",
            r"\b(each\s+party)\b",
        ],
    ),
    SmartRule(
        id="consequential_damages",
        name="Consequential Damages",
        clause_type="liability",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(consequential\s+damages)\b",
            r"\b(indirect.*damages)\b",
            r"\b(special.*incidental.*consequential)\b",
            r"\b(loss\s+of\s+profit(s)?)\b",
            r"\b(punitive\s+damages)\b",
            r"\b(exemplary\s+damages)\b",
        ],
        primary_position="Mutual exclusion of consequential, indirect, and punitive damages with carve-outs for IP infringement and confidentiality breaches",
        escalation_conditions=[
            r"\b(waive(s|d)?\s+(the\s+)?(exclusion|limitation)\s+of\s+consequential)\b",
            r"\b(consequential\s+damages.*shall\s+(be\s+)?recoverable)\b",
            r"\b(including\s+consequential\s+damages)\b",
        ],
        de_escalation_conditions=[
            r"\b(neither\s+party.*consequential)\b",
            r"\b(mutual(ly)?\s+exclude)\b",
            r"\b(exclude.*consequential.*damages)\b",
            r"\b(shall\s+not\s+be\s+liable.*consequential)\b",
        ],
    ),
    # broad_indemnification — from DEFAULT_RULES (SmartRule)
    SmartRule(
        id="broad_indemnification",
        name="Broad Indemnification",
        clause_type="indemnification",
        risk_level=RiskLevel.YELLOW,
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
            r"\bmutual(ly)?\b.{0,80}\blimited\s+to\b",
        ],
        context_window=500,
        escalation_conditions=[
            r"\b(one[\s-]?sided|unilateral)\b",
            r"\b(uncapped|without\s+(any\s+)?cap|no\s+cap)\b",
            r"\b(any\s+and\s+all\s+(loss|damage|claim|liabilit))",
        ],
        de_escalation_conditions=[
            r"\bmutual(ly)?\b.{0,120}\bcapped?\s+(at|to)\b",
        ],
    ),
    RulePattern(
        id="indemnification_procedure",
        name="Indemnification Procedure",
        clause_type="indemnification",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(indemnification\s+procedure)\b",
            r"\b(notify.*indemnifying\s+party)\b",
            r"\b(defense\s+of\s+claims)\b",
            r"\b(right\s+to\s+control.*defense)\b",
            r"\b(indemnified\s+party\s+shall\s+(promptly\s+)?notify)\b",
        ],
        primary_position="Clear indemnification procedure: prompt notice, right to control defense, consent for settlements, cooperation obligations",
    ),
    RulePattern(
        id="third_party_claims",
        name="Third-Party Claims",
        clause_type="indemnification",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(third[\s-]?party\s+claim)\b",
            r"\b(third[\s-]?party\s+action)\b",
            r"\b(claims\s+by\s+third\s+part(y|ies))\b",
            r"\b(third[\s-]?party\s+demand)\b",
        ],
        primary_position="Third-party claims defense costs and settlement authority clearly allocated between the parties",
    ),
    SmartRule(
        id="limitation_period",
        name="Limitation Period",
        clause_type="liability",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(limitation\s+period)\b",
            r"\b(statute\s+of\s+limitation)\b",
            r"\b(claims.*must\s+be\s+brought\s+within)\b",
            r"\b(time[\s-]?barred)\b",
            r"\b(limitation\s+of\s+action)\b",
            r"\b(prescriptive\s+period)\b",
        ],
        primary_position="Limitation period of at least 12 months from date the claim arose; never less than the statutory minimum",
        escalation_conditions=[
            r"\b(within\s+([1-5])\s+months)\b",
            r"\b(within\s+(30|60|90|120|150|180)\s+days)\b",
        ],
    ),
    SmartRule(
        id="insurance_requirement",
        name="Insurance Obligations",
        clause_type="insurance",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(maintain.*insurance)\b",
            r"\b(insurance\s+coverage)\b",
            r"\b(professional\s+indemnity)\b",
            r"\b(errors\s+and\s+omissions)\b",
            r"\b(E&O\s+insurance)\b",
            r"\b(commercial\s+general\s+liability)\b",
            r"\b(cyber\s+insurance)\b",
        ],
        primary_position="Insurance requirements proportionate to risk; specify minimum coverage amounts and require certificates of insurance",
        context_window=600,
        escalation_conditions=[
            r"\b(no\s+insurance)\b",
            r"\b(waive.*insurance)\b",
            r"\b(at\s+(its|their)\s+sole\s+discretion.*insurance)\b",
            r"\b(insurance.*not\s+required)\b",
        ],
        de_escalation_conditions=[
            r"\b(minimum.*coverage.*\$[\d,]+)\b",
            r"\b(certificate.*insurance)\b",
            r"\b(not\s+less\s+than\s+\$[\d,]+)\b",
            r"\b(evidence\s+of\s+insurance)\b",
        ],
    ),
]

# ============================================================
# 5. INTELLECTUAL PROPERTY (7 rules)
# ============================================================

IP_RULES: List[RulePattern] = [
    # ip_assignment — from DEFAULT_RULES
    SmartRule(
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
        context_window=500,
        negative_patterns=[
            r"\bpre[\s-]?existing\s+IP\b.*\bexclud",
            r"\bbackground\s+IP\b.*\bremain",
        ],
        de_escalation_conditions=[
            r"\b(background\s+IP)\b.*\bremain",
            r"\b(pre[\s-]?existing)\b.*\bretain",
            r"\b(excluding\s+pre[\s-]?existing)\b",
        ],
    ),
    SmartRule(
        id="ip_ownership",
        name="IP Ownership",
        clause_type="intellectual_property",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(intellectual\s+property.*owned\s+by)\b",
            r"\b(ownership\s+of\s+IP)\b",
            r"\b(all\s+IP.*belongs\s+to)\b",
            r"\b(proprietary\s+rights)\b",
            r"\b(ownership\s+of\s+intellectual\s+property)\b",
            r"\b(vesting\s+of\s+IP)\b",
        ],
        primary_position="Clear IP ownership split: background IP stays with creator, foreground IP jointly owned or licensed back",
        context_window=500,
        escalation_conditions=[
            r"\b(all\s+(IP|intellectual\s+property)\s+.*\b(vest|belong|assign))\b",
            r"\b(sole\s+ownership)\b",
            r"\b(all\s+rights.*transfer)\b",
        ],
        negative_patterns=[
            r"\bpre[\s-]?existing\s+IP\s+remains\b",
        ],
        de_escalation_conditions=[
            r"\b(jointly\s+owned)\b",
            r"\b(license[\s-]?back)\b",
            r"\b(background.*foreground.*split)\b",
        ],
    ),
    SmartRule(
        id="license_grant",
        name="License Grant",
        clause_type="intellectual_property",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(grants?.*license)\b",
            r"\b(license\s+to\s+use)\b",
            r"\b(non[\s-]?exclusive.*license)\b",
            r"\b(perpetual.*license)\b",
            r"\b(royalty[\s-]?free.*license)\b",
        ],
        primary_position="License scope clearly defined: territory, field of use, duration, sublicensing restrictions",
        context_window=500,
        escalation_conditions=[
            r"\b(irrevocable.*sublicensable)\b",
            r"\b(sublicensable.*irrevocable)\b",
            r"\b(irrevocable.*transferable.*sublicensable)\b",
            r"\b(perpetual.*irrevocable)\b",
            r"\b(exclusive\s+license)\b",
        ],
        de_escalation_conditions=[
            r"\b(non[\s-]?exclusive)\b",
            r"\b(limited\s+to)\b",
            r"\b(revocable)\b",
            r"\b(term\s+of\s+this\s+agreement)\b",
        ],
    ),
    RulePattern(
        id="background_ip",
        name="Background / Pre-existing IP",
        clause_type="intellectual_property",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(background\s+IP)\b",
            r"\b(pre[\s-]?existing.*intellectual\s+property)\b",
            r"\b(prior\s+IP)\b",
            r"\b(background\s+technology)\b",
            r"\b(pre[\s-]?existing\s+(IP|technology|work))\b",
        ],
        primary_position="Background IP clearly identified in a schedule; license to use for the purpose of the agreement only",
    ),
    RulePattern(
        id="ip_indemnification",
        name="IP Infringement Indemnity",
        clause_type="intellectual_property",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(IP.*infringement.*indemnif)\b",
            r"\b(indemnif.*intellectual\s+property)\b",
            r"\b(patent.*infringement)\b",
            r"\b(IP\s+claims)\b",
            r"\b(infringement.*indemnity)\b",
            r"\b(indemnif.*infring)\b",
        ],
        primary_position="Mutual IP infringement indemnity; provider should indemnify for third-party IP claims arising from the deliverables",
    ),
    SmartRule(
        id="open_source",
        name="Open Source Obligations",
        clause_type="intellectual_property",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(open\s+source)\b",
            r"\b(copyleft)\b",
            r"\bGPL\b",
            r"\b(open[\s-]?source\s+licen[cs]e)\b",
            r"\bFOSS\b",
            r"\bLGPL\b",
            r"\bAGPL\b",
        ],
        primary_position="Disclose all open source components; no copyleft licenses that could infect proprietary code",
        escalation_conditions=[
            r"\b(copyleft)\b",
            r"\bAGPL\b",
            r"\b(GPL(?!v?\d))\b",
        ],
    ),
    RulePattern(
        id="moral_rights",
        name="Moral Rights Waiver",
        clause_type="intellectual_property",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(moral\s+rights)\b",
            r"\b(waive.*moral)\b",
            r"\b(droit\s+moral)\b",
            r"\b(attribution\s+rights)\b",
            r"\b(right\s+of\s+paternity)\b",
            r"\b(right\s+of\s+integrity)\b",
        ],
        primary_position="Moral rights waiver only to the extent permitted by law; attribution rights preserved where feasible",
    ),
]

# ============================================================
# 6. CONFIDENTIALITY & DATA (8 rules)
# ============================================================

CONFIDENTIALITY_RULES: List[RulePattern] = [
    SmartRule(
        id="confidentiality_obligations",
        name="Confidentiality Obligations",
        clause_type="confidentiality",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(confidential\s+information)\b",
            r"\b(shall\s+maintain.*confidential)\b",
            r"\b(not\s+disclose)\b",
            r"\b(keep.*confidential)\b",
            r"\b(duty\s+of\s+confidence)\b",
        ],
        primary_position="Mutual confidentiality obligations with clearly defined scope; reasonable care standard",
        context_window=500,
        escalation_conditions=[
            r"\b(all\s+information.*deemed\s+confidential)\b",
            r"\b(any\s+and\s+all\s+information.*confidential)\b",
            r"\b(all\s+information\s+(disclosed|exchanged|shared).*confidential)\b",
            r"\b(one[\s-]?sided|only\s+the\s+(recipient|customer|buyer))\b",
        ],
        de_escalation_conditions=[
            r"\b(mutual(ly)?)\b",
            r"\b(each\s+party)\b",
            r"\b(reasonable\s+exceptions)\b",
            r"\b(clearly\s+marked|marked\s+as\s+confidential)\b",
        ],
    ),
    RulePattern(
        id="confidentiality_exceptions",
        name="Confidentiality Exceptions",
        clause_type="confidentiality",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(exclud(es?|ing).*confidential)\b",
            r"\b(shall\s+not\s+include)\b",
            r"\b(publicly\s+available)\b",
            r"\b(independently\s+developed)\b",
            r"\b(rightfully\s+(received|obtained))\b",
            r"\b(required\s+by\s+law\s+to\s+disclose)\b",
        ],
        primary_position="Standard carve-outs: publicly available, independently developed, rightfully received from third party, required by law",
    ),
    # confidentiality_term — from DEFAULT_RULES
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
        id="return_of_materials",
        name="Return / Destruction of Materials",
        clause_type="confidentiality",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(return.*confidential)\b",
            r"\b(destroy.*materials)\b",
            r"\b(return\s+or\s+destroy)\b",
            r"\b(certify\s+destruction)\b",
            r"\b(deletion\s+of.*data)\b",
        ],
        primary_position="Return or destroy all confidential materials within 30 days of termination with written certification",
    ),
    SmartRule(
        id="data_protection",
        name="Data Protection / GDPR / DPDP",
        clause_type="data_protection",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(data\s+protection)\b",
            r"\b(personal\s+data)\b",
            r"\b(data\s+processing)\b",
            r"\bGDPR\b",
            r"\bDPDP\b",
            r"\b(data\s+subject)\b",
            r"\b(personally\s+identifiable\s+information|PII)\b",
        ],
        primary_position=(
            "Compliance with applicable data protection laws; if a processor is engaged, "
            "use a valid contract that clearly allocates processing and security safeguards"
        ),
        escalation_conditions=[
            r"\b(no\s+(data\s+processing\s+agreement|DPA))\b",
            r"\b(without\s+a\s+DPA)\b",
        ],
    ),
    RulePattern(
        id="data_processing_agreement",
        name="Data Processing Agreement",
        clause_type="data_protection",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(data\s+processing\s+agreement)\b",
            r"\bDPA\b",
            r"\b(data\s+processor)\b",
            r"\b(sub[\s-]?processor)\b",
            r"\b(data\s+controller)\b",
            r"\b(processing\s+on\s+behalf)\b",
        ],
        primary_position="DPA attached as schedule; controller/processor roles clearly defined; sub-processor approval required",
    ),
    SmartRule(
        id="breach_notification",
        name="Data Breach Notification",
        clause_type="data_protection",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(data\s+breach)\b",
            r"\b(security\s+incident)\b",
            r"\b(breach\s+notification)\b",
            r"\b(notify.*within.*hours)\b",
            r"\b(security\s+breach)\b",
            r"\b(incident\s+response)\b",
        ],
        primary_position="Data breach notification within 48 hours; detailed incident report within 5 business days",
        escalation_conditions=[
            r"\b(notify.*within\s+(7[3-9]|[89]\d|\d{3,})\s+hours)\b",
            r"\b(notify.*within\s+([4-9]|\d{2,})\s+days)\b",
            r"\b(reasonable\s+time.*notify)\b",
        ],
    ),
    RulePattern(
        id="cross_border_transfer",
        name="Cross-Border Data Transfer",
        clause_type="data_protection",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(cross[\s-]?border)\b",
            r"\b(international\s+transfer)\b",
            r"\b(transfer.*outside)\b",
            r"\b(standard\s+contractual\s+clauses|SCC)\b",
            r"\b(adequacy\s+decision)\b",
            r"\b(transfer\s+mechanism)\b",
            r"\b(binding\s+corporate\s+rules|BCR)\b",
        ],
        primary_position="Cross-border transfers only with approved transfer mechanism (SCC, BCR, or adequacy decision); data localization requirements identified",
    ),
]

# ============================================================
# 7. REPRESENTATIONS & WARRANTIES (6 rules)
# ============================================================

REPS_WARRANTIES_RULES: List[RulePattern] = [
    RulePattern(
        id="general_reps_warranties",
        name="Representations & Warranties",
        clause_type="reps_warranties",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(represents\s+and\s+warrants)\b",
            r"\b(representation.*warranty)\b",
            r"\b(each\s+party\s+represents)\b",
            r"\b(hereby\s+represents)\b",
            r"\b(warrant(s|ies)?\s+that)\b",
        ],
        primary_position="Standard mutual representations and warranties; ensure they survive closing",
    ),
    SmartRule(
        id="as_is_disclaimer",
        name="AS-IS / No Warranty Disclaimer",
        clause_type="warranty_disclaimer",
        risk_level=RiskLevel.RED,
        patterns=[
            r"\bAS[\s-]?IS\b",
            r"\b(as[\s-]?is\s+basis)\b",
            r"\b(no\s+warrant(y|ies))\b",
            r"\b(without\s+warrant(y|ies))\b",
            r"\b(disclaimer\s+of\s+warranties)\b",
            r"\b(expressly\s+disclaims?\s+all\s+warranties)\b",
        ],
        primary_position="Reject blanket AS-IS disclaimers; require at minimum fitness for purpose and conformance to specifications warranties",
        fallback_position="AS-IS acceptable for evaluation/trial periods only",
        de_escalation_conditions=[
            r"\b(evaluation|trial|pilot|proof\s+of\s+concept|POC)\b",
            r"\b(beta|preview|early\s+access)\b",
        ],
    ),
    RulePattern(
        id="service_level",
        name="Service Level Commitments",
        clause_type="service_level",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(service\s+level)\b",
            r"\bSLA\b",
            r"\b(uptime.*guarantee)\b",
            r"\b(availability.*99)\b",
            r"\b(service\s+availability)\b",
            r"\b(performance\s+standard)\b",
        ],
        primary_position="SLA with 99.9% uptime commitment; meaningful service credits for downtime; exclusions for scheduled maintenance clearly defined",
    ),
    RulePattern(
        id="authority_rep",
        name="Authority Representation",
        clause_type="reps_warranties",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(duly\s+authorized)\b",
            r"\b(authority\s+to\s+enter)\b",
            r"\b(power\s+and\s+authority)\b",
            r"\b(legal\s+capacity)\b",
            r"\b(validly\s+existing)\b",
            r"\b(duly\s+organized)\b",
        ],
        primary_position="Standard authority representation confirming each party has power to enter into and perform the agreement",
    ),
    RulePattern(
        id="non_infringement",
        name="Non-Infringement Warranty",
        clause_type="reps_warranties",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(non[\s-]?infringement)\b",
            r"\b(does\s+not\s+infringe)\b",
            r"\b(no\s+infringement)\b",
            r"\b(free\s+from.*infringement)\b",
            r"\b(not\s+infringe.*rights)\b",
        ],
        primary_position="Provider should warrant non-infringement of third-party IP rights for all deliverables and services",
    ),
    RulePattern(
        id="compliance_warranty",
        name="Compliance Representation",
        clause_type="reps_warranties",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(comply\s+with.*applicable\s+law)\b",
            r"\b(compliance\s+with.*regulation)\b",
            r"\b(in\s+accordance\s+with.*law)\b",
            r"\b(applicable\s+laws?\s+and\s+regulations?)\b",
            r"\b(lawful(ly)?\s+conduct)\b",
        ],
        primary_position="Standard compliance warranty — each party shall comply with all applicable laws and regulations",
    ),
]

# ============================================================
# 8. RESTRICTIVE COVENANTS (5 rules)
# ============================================================

RESTRICTIVE_RULES: List[RulePattern] = [
    # non_compete — from DEFAULT_RULES
    SmartRule(
        id="non_compete",
        name="Non-Compete Clause",
        clause_type="restrictive_covenant",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(non[\s-]?compete)\b",
            r"\b(shall\s+not\s+compete)\b",
            r"\b(restriction\s+on\s+competition)\b",
            r"\b(compete\s+directly\s+or\s+indirectly)\b",
        ],
        primary_position="Non-compete limited to 12 months in same geography",
        context_window=500,
        escalation_conditions=[
            r"\b(worldwide|global)\b",
            r"\b(perpetual|indefinite)\b",
            r"\b(greater\s+than\s+\d+\s+years?)\b",
            r"\b(any\s+(business|industry|field))\b",
        ],
        de_escalation_conditions=[
            r"\b(limited\s+to.*\d+\s+months?)\b",
            r"\b(specific\s+geographic)\b",
            r"\b(within\s+\d+\s+(km|miles|kilometers))\b",
            r"\b(\d+\s+months?\s+post[\s-]?termination)\b",
        ],
    ),
    # non_solicitation — from DEFAULT_RULES
    SmartRule(
        id="non_solicitation",
        name="Non-Solicitation Clause",
        clause_type="restrictive_covenant",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(non[\s-]?solicit(ation)?)\b",
            r"\b(shall\s+not\s+solicit)\b",
            r"solicit.{0,100}(employee|personnel|staff|contractor)",
            r"\b(solicit,?\s+(induce,?\s+)?(recruit|hire|employ))\b",
            r"\b(recruit(ing)?\s+(any\s+)?employee)\b",
        ],
        primary_position="Non-solicitation limited to 12 months post-termination",
        context_window=500,
        escalation_conditions=[
            r"\b(all\s+employees)\b",
            r"\b(perpetual|indefinite)\b",
            r"\b(any\s+(employee|personnel|staff))\b",
        ],
        de_escalation_conditions=[
            r"\b(\d+\s+months?\s+post[\s-]?termination)\b",
            r"\b(key\s+employees?\s+only)\b",
            r"\b(directly\s+involved)\b",
        ],
    ),
    RulePattern(
        id="customer_non_solicitation",
        name="Customer Non-Solicitation",
        clause_type="restrictive_covenant",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(not\s+solicit.*customer)\b",
            r"\b(not\s+solicit.*client)\b",
            r"\b(customer.*non[\s-]?solicitation)\b",
            r"\b(client.*non[\s-]?solicitation)\b",
            r"\b(solicit.*business.*from.*customer)\b",
        ],
        primary_position="Customer non-solicitation limited to 12 months and only to customers actually served during the engagement",
    ),
    # exclusive_dealing — from DEFAULT_RULES
    SmartRule(
        id="exclusive_dealing",
        name="Exclusive Dealing",
        clause_type="exclusivity",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(exclusive\s+(right|license|agreement))\b",
            r"\b(sole\s+and\s+exclusive)\b",
            r"\b(exclusivity\s+(period|term|clause))\b",
            r"\b(exclusive\s+provider)\b",
            r"\b(exclusive\s+supplier)\b",
        ],
        primary_position="Non-exclusive arrangement or limited exclusivity period",
        context_window=500,
        escalation_conditions=[
            r"\b(perpetual|indefinite)\b",
            r"\b(worldwide|global)\b",
            r"\b(irrevocable\s+exclusivity)\b",
        ],
        de_escalation_conditions=[
            r"\b(limited\s+to)\b",
            r"\b(\d+\s+(months?|years?))\b",
            r"\b(specific\s+(territory|region))\b",
            r"\b(non[\s-]?exclusive)\b",
        ],
    ),
    # reverse_engineering — from DEFAULT_RULES
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
]

# ============================================================
# 9. GOVERNANCE & DISPUTES (6 rules)
# ============================================================

GOVERNANCE_RULES: List[RulePattern] = [
    # governing_law — from DEFAULT_RULES
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
        id="jurisdiction_clause",
        name="Jurisdiction / Venue",
        clause_type="jurisdiction",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(exclusive\s+jurisdiction)\b",
            r"\b(submit\s+to.*jurisdiction)\b",
            r"\b(courts\s+of)\b",
            r"\b(venue.*shall\s+be)\b",
            r"\b(forum\s+selection)\b",
            r"\b(subject\s+to\s+the\s+jurisdiction)\b",
        ],
        primary_position="Jurisdiction convenient to both parties; mutual submission; avoid exclusive foreign jurisdiction",
    ),
    SmartRule(
        id="arbitration",
        name="Arbitration Clause",
        clause_type="dispute_resolution",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(arbitration)\b",
            r"\b(arbitral\s+tribunal)\b",
            r"\bSIAC\b",
            r"\bICC\b",
            r"\bLCIA\b",
            r"\bAAA\b",
            r"\b(resolved\s+by\s+arbitration)\b",
            r"\b(binding\s+arbitration)\b",
        ],
        primary_position="Arbitration under recognized rules (SIAC/ICC/LCIA); seat in a neutral jurisdiction; language in English; panel of 3 arbitrators for high-value disputes",
        escalation_conditions=[
            r"\b(seat.*in\s+(a\s+)?foreign)\b",
            r"\b(arbitration.*in\s+(the\s+)?(People's\s+Republic\s+of\s+China|PRC|Russia|Iran))\b",
        ],
    ),
    RulePattern(
        id="mediation",
        name="Mediation Requirement",
        clause_type="dispute_resolution",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(mediation)\b",
            r"\b(attempt\s+to\s+mediate)\b",
            r"\b(mediation.*prior\s+to)\b",
            r"\b(good\s+faith.*mediation)\b",
            r"\b(escalation.*mediation)\b",
        ],
        primary_position="Tiered dispute resolution: negotiation first, then mediation, then arbitration/litigation",
    ),
    RulePattern(
        id="injunctive_relief",
        name="Injunctive Relief Carve-out",
        clause_type="dispute_resolution",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(injunctive\s+relief)\b",
            r"\b(equitable\s+relief)\b",
            r"\b(specific\s+performance)\b",
            r"\b(seek.*injunction)\b",
            r"\b(interim\s+(or\s+)?injunctive\s+relief)\b",
        ],
        primary_position="Standard carve-out for injunctive/equitable relief from courts notwithstanding arbitration clause",
    ),
    RulePattern(
        id="jury_waiver",
        name="Jury Trial Waiver",
        clause_type="dispute_resolution",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(waive.*jury)\b",
            r"\b(jury\s+trial\s+waiver)\b",
            r"\b(waiver\s+of\s+jury\s+trial)\b",
            r"\b(bench\s+trial)\b",
            r"\b(irrevocably\s+waive.*right\s+to\s+jury)\b",
        ],
        primary_position="Jury waiver should be mutual; verify enforceability in applicable jurisdiction",
    ),
]

# ============================================================
# 10. OPERATIONAL (9 rules)
# ============================================================

OPERATIONAL_RULES: List[RulePattern] = [
    SmartRule(
        id="force_majeure",
        name="Force Majeure",
        clause_type="force_majeure",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(force\s+majeure)\b",
            r"\b(act\s+of\s+god)\b",
            r"\b(beyond.*reasonable\s+control)\b",
            r"\b(unforeseeable\s+circumstances)\b",
            r"\b(events\s+beyond\s+control)\b",
        ],
        primary_position="Force majeure clause should be mutual, include pandemic/epidemic, and allow termination if event persists beyond 90 days",
        escalation_conditions=[
            r"\b(exclud(es?|ing).*pandemic)\b",
            r"\b(pandemic.*not.*force\s+majeure)\b",
            r"\b(epidemic.*excluded)\b",
        ],
    ),
    # assignment_restriction — from DEFAULT_RULES
    RulePattern(
        id="assignment_restriction",
        name="Assignment Restriction",
        clause_type="assignment",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(may\s+not\s+assign)\b",
            r"\b(no\s+assignment\s+without\s+consent)\b",
            r"\b(assignment\s+(is\s+)?(prohibited|restricted))\b",
            r"\b(shall\s+not\s+assign)\b",
        ],
        primary_position="Assignment permitted to affiliates without consent",
    ),
    SmartRule(
        id="change_of_control",
        name="Change of Control",
        clause_type="assignment",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(change\s+of\s+control)\b",
            r"\b(change\s+in\s+control)\b",
            r"\b(merger.*acquisition)\b",
            r"\b(controlling\s+interest)\b",
            r"\b(acquisition\s+of.*shares)\b",
            r"\b(change\s+of\s+ownership)\b",
        ],
        primary_position="Change of control should trigger notification right, not automatic termination; carve-out for internal restructuring",
        context_window=600,
        escalation_conditions=[
            r"\b(automatic(ally)?\s+terminat)\b",
            r"\b(immediate(ly)?\s+terminat)\b",
            r"\b(deemed\s+(an?\s+)?assignment)\b",
            r"\b(without\s+consent)\b",
        ],
        de_escalation_conditions=[
            r"\b(notification|notice)\b",
            r"\b(consent.*not.*unreasonably\s+withheld)\b",
            r"\b(internal\s+restructuring.*excluded)\b",
            r"\b(affiliate.*carve[\s-]?out)\b",
        ],
    ),
    RulePattern(
        id="subcontracting",
        name="Subcontracting Restrictions",
        clause_type="operational",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(subcontract)\b",
            r"\b(sub[\s-]?processor)\b",
            r"\b(sub[\s-]?contract)\b",
            r"\b(engage.*third\s+party.*perform)\b",
            r"\b(delegate.*obligations.*to.*third)\b",
        ],
        primary_position="Subcontracting permitted with prior written consent; provider remains fully liable for subcontractor performance",
    ),
    # notice_provision — from DEFAULT_RULES
    RulePattern(
        id="notice_provision",
        name="Notice Provision",
        clause_type="notice",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(notice(s)?\s+(shall|must|should)\s+be\s+(sent|given|provided))\b",
            r"\b(written\s+notice)\b",
            r"\b(notice\s+shall\s+be\s+deemed)\b",
        ],
        primary_position="Standard notice provision",
    ),
    RulePattern(
        id="anti_bribery",
        name="Anti-Bribery / Anti-Corruption",
        clause_type="compliance",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(anti[\s-]?bribery)\b",
            r"\b(anti[\s-]?corruption)\b",
            r"\bFCPA\b",
            r"\b(UK\s+Bribery\s+Act)\b",
            r"\b(Prevention\s+of\s+Corruption)\b",
            r"\b(not\s+(offer|give|pay).*bribe)\b",
        ],
        primary_position="Mutual anti-bribery representations; compliance with FCPA, UK Bribery Act, and local anti-corruption laws",
    ),
    RulePattern(
        id="sanctions_compliance",
        name="Sanctions Compliance",
        clause_type="compliance",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(economic\s+sanctions|trade\s+sanctions|sanctions\s+compliance|sanctions\s+list|sanctions\s+screening|sanctioned\s+(?:part(?:y|ies)|countr(?:y|ies)|entit(?:y|ies)))\b",
            r"\bOFAC\b",
            r"\b(trade\s+control)\b",
            r"\b(export\s+control)\b",
            r"\b(restricted\s+part(y|ies))\b",
            r"\b(sanctioned\s+(country|entity|person))\b",
            r"\b(denied\s+part(y|ies)\s+list)\b",
        ],
        primary_position="Compliance with OFAC, EU, and UN sanctions; screening obligations; right to terminate if counterparty is sanctioned",
    ),
    RulePattern(
        id="regulatory_compliance",
        name="Regulatory Compliance",
        clause_type="compliance",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(comply\s+with.*regulat)\b",
            r"\b(regulatory.*compliance)\b",
            r"\b(applicable.*regulation)\b",
            r"\b(statutory\s+compliance)\b",
            r"\b(regulatory\s+requirements)\b",
        ],
        primary_position="Standard regulatory compliance clause; each party responsible for its own regulatory obligations",
    ),
    RulePattern(
        id="business_continuity",
        name="Business Continuity / Disaster Recovery",
        clause_type="operational",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(business\s+continuity)\b",
            r"\b(disaster\s+recovery)\b",
            r"\b(BCP\s+(?:requirement|clause|provision|obligation)|business\s+continuity\s+plan(?:ning)?)\b",
            r"\b(contingency\s+plan)\b",
            r"\b(recovery\s+point\s+objective|RPO)\b",
            r"\b(recovery\s+time\s+objective|RTO)\b",
        ],
        primary_position="Provider must maintain and test BCP/DR plan; RTO and RPO commitments defined; annual testing required",
    ),
    SmartRule(
        id="counterparty_insolvency",
        name="Counterparty Insolvency / Bankruptcy",
        clause_type="insolvency",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(insolven(cy|t))\b",
            r"\b(bankrupt(cy)?)\b",
            r"\b(winding[\s-]?up)\b",
            r"\b(liquidat(ion|or|ed))\b",
            r"\b(receiv(er|ership))\b",
            r"\b(administration\s+order)\b",
            r"\b(voluntary\s+arrangement)\b",
            r"\b(unable\s+to\s+pay\s+its\s+debts)\b",
        ],
        primary_position="Right to terminate on counterparty insolvency with no penalty; immediate data return/portability rights",
        fallback_position="At minimum, right to suspend obligations on counterparty insolvency",
        context_window=600,
        escalation_conditions=[
            r"\b(waive|relinquish|forfeit).*insolvency\b",
            r"\b(no\s+right\s+to\s+terminate).*insolvency\b",
            r"\b(obligations\s+continue.*insolvency)\b",
        ],
        de_escalation_conditions=[
            r"\b(either\s+party|both\s+parties).*insolvency\b",
            r"\b(mutual).*terminat.*insolvency\b",
            r"\b(right\s+to\s+terminate.*insolvency)\b",
        ],
    ),
    SmartRule(
        id="payment_escalation_cap",
        name="Payment Escalation Protection",
        clause_type="payment_escalation",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(price\s+increase|fee\s+increase|rate\s+increase)\b",
            r"\b(adjust(ed|ment)?\s+annually)\b",
            r"\b(CPI|consumer\s+price\s+index|inflation)\b",
            r"\b(escalat(e|ion)\s+(clause|provision))\b",
        ],
        primary_position="Price increases capped at CPI or fixed percentage (e.g. 5%); right to terminate if increase exceeds cap",
        context_window=500,
        escalation_conditions=[
            r"\b(unlimited|uncapped|no\s+cap).*increase\b",
            r"\b(sole\s+discretion).*price\b",
            r"\b(unilateral(ly)?.*increas)\b",
        ],
        de_escalation_conditions=[
            r"\b(cap(ped)?\s+(at|to)).*increase\b",
            r"\b(not\s+exceed).*percent\b",
            r"\b(CPI[\s-]?linked)\b",
            r"\b(mutual\s+agreement.*price)\b",
        ],
    ),
]

# ============================================================
# 11. SAAS / TECHNOLOGY (6 rules)
# ============================================================

SAAS_RULES: List[RulePattern] = [
    RulePattern(
        id="sla_terms",
        name="SLA Specific Terms",
        clause_type="sla",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(service\s+level\s+agreement)\b",
            r"\b(SLA.*credits?)\b",
            r"\b(uptime\s+commitment)\b",
            r"\b(scheduled\s+maintenance)\b",
            r"\b(maintenance\s+window)\b",
            r"\b(planned\s+downtime)\b",
        ],
        primary_position="SLA with 99.9% uptime; scheduled maintenance windows defined with advance notice; exclusions clearly listed",
    ),
    RulePattern(
        id="sla_credits",
        name="SLA Credits / Remedies",
        clause_type="sla",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(service\s+credit)\b",
            r"\b(SLA\s+credit)\b",
            r"\b(credit.*downtime)\b",
            r"\b(remedy.*failure\s+to\s+meet)\b",
            r"\b(credit.*unavailability)\b",
            r"\b(refund.*downtime)\b",
        ],
        primary_position="Meaningful SLA credits (minimum 10% of monthly fees per hour of downtime); termination right if SLA persistently missed",
    ),
    SmartRule(
        id="data_portability",
        name="Data Portability / Export",
        clause_type="data_portability",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(data\s+portability)\b",
            r"\b(data\s+export)\b",
            r"\b(right\s+to\s+export)\b",
            r"\b(provide.*data.*format)\b",
            r"\b(data\s+extraction)\b",
            r"\b(export.*customer\s+data)\b",
        ],
        primary_position="Full data export in standard machine-readable format (CSV/JSON/XML) at no additional cost within 30 days of termination",
        escalation_conditions=[
            r"\b(no\s+(right\s+to\s+)?export)\b",
            r"\b(data.*not.*portable)\b",
            r"\b(additional\s+(fee|charge|cost).*export)\b",
        ],
    ),
    RulePattern(
        id="security_standards",
        name="Security Requirements",
        clause_type="security",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(ISO\s*27001)\b",
            r"\b(SOC\s*2)\b",
            r"\b(security\s+standards)\b",
            r"\b(security\s+measures)\b",
            r"\b(encryption)\b",
            r"\b(penetration\s+test)\b",
            r"\b(security\s+audit)\b",
            r"\b(information\s+security)\b",
        ],
        primary_position="Provider must maintain ISO 27001 or SOC 2 Type II certification; annual penetration testing; encryption at rest and in transit",
    ),
    RulePattern(
        id="acceptable_use",
        name="Acceptable Use Policy",
        clause_type="acceptable_use",
        risk_level=RiskLevel.GREEN,
        patterns=[
            r"\b(acceptable\s+use)\b",
            r"\b(permitted\s+use)\b",
            r"\b(use\s+restrictions)\b",
            r"\b(prohibited\s+use)\b",
            r"\b(fair\s+use\s+policy)\b",
        ],
        primary_position="Acceptable use policy should be reasonable, clearly defined, and not unilaterally modifiable",
    ),
    RulePattern(
        id="api_rights",
        name="API Access Rights",
        clause_type="technology",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(API\s+access)\b",
            r"\b(application\s+programming\s+interface)\b",
            r"\b(programmatic\s+access)\b",
            r"\b(API.*usage)\b",
            r"\b(API.*rate\s+limit)\b",
            r"\b(webhook)\b",
        ],
        primary_position="API access included at no extra cost; rate limits clearly defined; backward-compatible changes with deprecation notice",
    ),
    SmartRule(
        id="insurance_adequacy",
        name="Insurance Coverage Adequacy",
        clause_type="insurance",
        risk_level=RiskLevel.YELLOW,
        patterns=[
            r"\b(insurance\s+coverage)\b",
            r"\b(professional\s+indemnity\s+insurance)\b",
            r"\b(liability\s+insurance)\b",
            r"\b(errors\s+and\s+omissions)\b",
            r"\b(cyber\s+insurance)\b",
            r"\b(policy\s+limit)\b",
            r"\b(coverage\s+amount)\b",
        ],
        primary_position="Adequate insurance with coverage limits proportional to contract value; certificate of insurance required annually",
        fallback_position="At minimum, professional indemnity insurance maintained during term plus 12 months",
        context_window=600,
        escalation_conditions=[
            r"\b(no\s+insurance|waive.*insurance)\b",
            r"\b(self[\s-]?insur(ed|ance))\b",
            r"\b(insurance.*not\s+required)\b",
        ],
        de_escalation_conditions=[
            r"\b(certificate\s+of\s+insurance)\b",
            r"\b(minimum.*coverage)\b",
            r"\b(insurance.*shall\s+maintain)\b",
        ],
    ),
]

# ============================================================
# ALL RULES COMBINED (76 total)
# ============================================================

ALL_RULES: List[RulePattern] = (
    FORMATION_RULES
    + TERM_RULES
    + FINANCIAL_RULES
    + LIABILITY_RULES
    + IP_RULES
    + CONFIDENTIALITY_RULES
    + REPS_WARRANTIES_RULES
    + RESTRICTIVE_RULES
    + GOVERNANCE_RULES
    + OPERATIONAL_RULES
    + SAAS_RULES
)

# Category lookup map
_CATEGORY_MAP = {
    CATEGORY_FORMATION: FORMATION_RULES,
    CATEGORY_TERM: TERM_RULES,
    CATEGORY_FINANCIAL: FINANCIAL_RULES,
    CATEGORY_LIABILITY: LIABILITY_RULES,
    CATEGORY_IP: IP_RULES,
    CATEGORY_CONFIDENTIALITY: CONFIDENTIALITY_RULES,
    CATEGORY_REPS_WARRANTIES: REPS_WARRANTIES_RULES,
    CATEGORY_RESTRICTIVE: RESTRICTIVE_RULES,
    CATEGORY_GOVERNANCE: GOVERNANCE_RULES,
    CATEGORY_OPERATIONAL: OPERATIONAL_RULES,
    CATEGORY_SAAS: SAAS_RULES,
}

# Rule ID -> RulePattern lookup (built once at import time)
_RULE_BY_ID = {rule.id: rule for rule in ALL_RULES}


def get_rules_by_category(category: str) -> List[RulePattern]:
    """Return all rules for a given category constant.

    Args:
        category: One of the CATEGORY_* constants (e.g. "formation", "term").

    Returns:
        List of RulePattern/SmartRule instances, or empty list if category unknown.
    """
    return list(_CATEGORY_MAP.get(category, []))


def get_rule_by_id(rule_id: str) -> Optional[RulePattern]:
    """Return a single rule by its ID.

    Args:
        rule_id: The rule identifier (e.g. "unlimited_liability").

    Returns:
        The RulePattern/SmartRule if found, else None.
    """
    return _RULE_BY_ID.get(rule_id)


def get_all_categories() -> List[str]:
    """Return all available category names."""
    return list(_CATEGORY_MAP.keys())


def get_category_summary() -> dict:
    """Return a summary of rules per category.

    Returns:
        Dict mapping category name to count of rules.
    """
    return {cat: len(rules) for cat, rules in _CATEGORY_MAP.items()}


# ---------------------------------------------------------------------------
# Contract-type applicability mapping for pre-filtering.
#
# Keys are rule IDs (matching RulePattern.id).  Values are lists of contract
# types where the rule is relevant.  The special value ``"general"`` means the
# rule applies to ALL contract types and should never be filtered out.
# ---------------------------------------------------------------------------

RULE_TYPE_APPLICABILITY: Dict[str, List[str]] = {
    # Formation — applies to ALL
    "definitions_clause": ["general"],
    "recitals_clause": ["general"],
    "entire_agreement": ["general"],
    "amendments_clause": ["general"],
    "severability": ["general"],

    # Term & Termination — applies to ALL (with exceptions)
    "contract_duration": ["general"],
    "auto_renewal": ["saas", "msa", "nda"],
    "termination_for_cause": ["general"],
    "termination_for_convenience": ["general"],
    "cure_period": ["general"],
    "survival_clause": ["general"],
    "transition_assistance": ["msa", "saas"],

    # Financial — applies to most
    "payment_terms": ["msa", "saas", "ma"],
    "late_payment": ["msa", "saas"],
    "price_escalation": ["msa", "saas"],
    "taxes_clause": ["msa", "saas", "ma"],
    "set_off_rights": ["msa", "ma"],
    "audit_rights": ["msa", "saas", "ma"],
    "most_favored_nation": ["msa", "saas"],
    "currency_clause": ["msa", "saas", "ma"],

    # Liability — applies to ALL
    "unlimited_liability": ["general"],
    "liability_cap": ["general"],
    "consequential_damages": ["general"],
    "broad_indemnification": ["general"],
    "indemnification_procedure": ["general"],
    "third_party_claims": ["general"],
    "limitation_period": ["general"],
    "insurance_requirement": ["msa", "saas", "employment"],

    # IP — context-dependent
    "ip_assignment": ["msa", "employment", "ma"],
    "ip_ownership": ["msa", "employment", "ma"],
    "license_grant": ["saas", "msa", "nda"],
    "background_ip": ["msa", "employment"],
    "ip_indemnification": ["saas", "msa"],
    "open_source": ["saas", "msa"],
    "moral_rights": ["employment", "msa"],

    # Confidentiality — applies to most
    "confidentiality_obligations": ["general"],
    "confidentiality_exceptions": ["general"],
    "confidentiality_term": ["nda", "msa", "saas", "employment"],
    "return_of_materials": ["nda", "msa"],
    "data_protection": ["saas", "msa", "employment"],
    "data_processing_agreement": ["saas"],
    "breach_notification": ["saas", "msa"],
    "cross_border_transfer": ["saas", "msa"],

    # Reps & Warranties
    "general_reps_warranties": ["general"],
    "as_is_disclaimer": ["saas", "msa"],
    "service_level": ["saas", "msa"],
    "authority_rep": ["general"],
    "non_infringement": ["saas", "msa"],
    "compliance_warranty": ["general"],

    # Restrictive
    "non_compete": ["employment", "ma", "msa"],
    "non_solicitation": ["employment", "ma", "msa", "nda"],
    "customer_non_solicitation": ["employment", "ma"],
    "exclusive_dealing": ["msa", "ma"],
    "reverse_engineering": ["saas", "msa"],

    # Governance — applies to ALL
    "governing_law": ["general"],
    "jurisdiction_clause": ["general"],
    "arbitration": ["general"],
    "mediation": ["general"],
    "injunctive_relief": ["general"],
    "jury_waiver": ["general"],

    # Operational
    "force_majeure": ["general"],
    "assignment_restriction": ["general"],
    "change_of_control": ["msa", "saas", "ma"],
    "subcontracting": ["msa"],
    "notice_provision": ["general"],
    "anti_bribery": ["msa", "ma"],
    "sanctions_compliance": ["msa", "ma"],
    "regulatory_compliance": ["general"],
    "business_continuity": ["saas", "msa"],
    "counterparty_insolvency": ["msa", "saas", "ma"],
    "payment_escalation_cap": ["msa", "saas"],

    # SaaS / Technology
    "sla_terms": ["saas"],
    "sla_credits": ["saas"],
    "data_portability": ["saas"],
    "security_standards": ["saas"],
    "acceptable_use": ["saas"],
    "api_rights": ["saas"],
    "insurance_adequacy": ["saas", "msa"],
}
