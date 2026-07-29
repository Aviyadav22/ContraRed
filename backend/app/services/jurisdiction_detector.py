"""
Jurisdiction Detector - Auto-detect governing law from contract text.

Provides deterministic regex-based detection of jurisdiction/governing law
clauses, plus 10+ jurisdiction profiles with legal context for dynamic
prompt injection into the AI analysis pipeline.

Zero AI dependency: purely regex-based detection.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JurisdictionProfile:
    """Legal profile for a specific jurisdiction.

    Contains the statutes, standards, and special considerations that
    inform how a contract should be reviewed under that jurisdiction's law.
    """

    code: str  # Short identifier, e.g. "IN", "DE-US", "NY"
    name: str  # Human-readable, e.g. "India"
    display_name: str  # Full form, e.g. "Republic of India"

    # Core legal framework
    key_statutes: List[str] = field(default_factory=list)
    indemnification_standard: str = ""
    non_compete_enforceability: str = ""
    arbitration_framework: str = ""
    data_protection_law: str = ""
    special_considerations: List[str] = field(default_factory=list)

    # For prompt injection
    legal_system: str = "common_law"  # common_law | civil_law | hybrid

    def to_prompt_context(self) -> str:
        """Generate the jurisdiction context block for AI prompt injection."""
        lines = [
            f"JURISDICTION: {self.display_name}",
            f"Legal System: {self.legal_system.replace('_', ' ').title()}",
            "",
            "KEY STATUTES:",
        ]
        for statute in self.key_statutes:
            lines.append(f"  - {statute}")

        lines.append("")
        lines.append(f"INDEMNIFICATION STANDARD: {self.indemnification_standard}")
        lines.append(f"NON-COMPETE ENFORCEABILITY: {self.non_compete_enforceability}")
        lines.append(f"ARBITRATION FRAMEWORK: {self.arbitration_framework}")
        lines.append(f"DATA PROTECTION: {self.data_protection_law}")

        if self.special_considerations:
            lines.append("")
            lines.append("SPECIAL CONSIDERATIONS:")
            for item in self.special_considerations:
                lines.append(f"  - {item}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Jurisdiction Profiles (10+)
# ---------------------------------------------------------------------------

JURISDICTION_PROFILES: Dict[str, JurisdictionProfile] = {}


def _register(profile: JurisdictionProfile) -> JurisdictionProfile:
    JURISDICTION_PROFILES[profile.code] = profile
    return profile


INDIA = _register(JurisdictionProfile(
    code="IN",
    name="India",
    display_name="Republic of India",
    legal_system="common_law",
    key_statutes=[
        "Indian Contract Act, 1872 (governs formation, performance, breach)",
        "Specific Relief Act, 1963 (injunctions, specific performance)",
        "Arbitration and Conciliation Act, 1996 (domestic & international arbitration)",
        "Information Technology Act, 2000 (electronic contracts, cybersecurity)",
        "Digital Personal Data Protection Act, 2023 (DPDP Act — data privacy)",
        "Foreign Exchange Management Act, 1999 (FEMA — cross-border payments)",
        "Competition Act, 2002 (anti-competitive agreements)",
        "Indian Stamp Act, 1899 (stamp duty on agreements)",
    ],
    indemnification_standard=(
        "Governed by S.73 and S.74 of the Indian Contract Act. S.73 allows "
        "damages for loss naturally arising from breach. S.74 treats liquidated "
        "damages as the upper ceiling — courts can award lesser amounts. "
        "Penalty clauses are unenforceable beyond reasonable pre-estimate of loss."
    ),
    non_compete_enforceability=(
        "Post-termination non-competes are VOID under S.27 of the Indian Contract Act "
        "(restraint of trade). Only during-term non-competes are enforceable. "
        "Non-solicitation clauses are generally enforceable if reasonable."
    ),
    arbitration_framework=(
        "Arbitration and Conciliation Act, 1996 (amended 2015, 2019, 2021). "
        "Seat of arbitration determines curial law. Indian courts have limited "
        "grounds for setting aside awards (S.34). Institutional arbitration "
        "encouraged (SIAC, ICC, MCIA)."
    ),
    data_protection_law=(
        "DPDP Act, 2023 and DPDP Rules, 2025 have phased commencement. "
        "Most substantive fiduciary, consent, rights, and breach provisions commence "
        "May 13, 2027; contracts spanning that date should allocate readiness duties. "
        "Section 16 permits Government-notified transfer restrictions."
    ),
    special_considerations=[
        "S.27 — post-termination non-competes are VOID; flag any such clause as RED",
        "Stamp duty — unstamped agreements may be inadmissible as evidence",
        "FEMA compliance required for cross-border payment obligations",
        "S.74 — liquidated damages are ceiling, not floor; courts can reduce",
        "Force majeure not codified — governed by S.56 (doctrine of frustration)",
        "Exclusive jurisdiction clauses are valid but subject to constitutional limits",
    ],
))

DELAWARE = _register(JurisdictionProfile(
    code="DE-US",
    name="Delaware",
    display_name="State of Delaware, United States",
    legal_system="common_law",
    key_statutes=[
        "Delaware General Corporation Law (DGCL) — corporate governance",
        "Delaware LLC Act (Title 6, Ch. 18) — maximum freedom of contract for LLCs",
        "Uniform Commercial Code (UCC) — sale of goods",
        "Delaware Revised Uniform Partnership Act",
    ],
    indemnification_standard=(
        "Very permissive. Delaware allows broad indemnification including advancement "
        "of expenses. DGCL S.145 governs corporate indemnification. LLC agreements "
        "can customize indemnification almost without limit."
    ),
    non_compete_enforceability=(
        "Enforceable if reasonable in scope, duration (typically 1-2 years), "
        "and geographic area. Blue-pencil doctrine applied — courts may modify "
        "overbroad restrictions rather than void them entirely."
    ),
    arbitration_framework=(
        "Federal Arbitration Act (FAA) applies. Delaware Rapid Arbitration Act (DRAA) "
        "available for business disputes. Court of Chancery handles corporate disputes."
    ),
    data_protection_law=(
        "Delaware Personal Data Privacy Act (DPDPA) effective 2025. "
        "No comprehensive federal privacy law; sector-specific (HIPAA, GLBA)."
    ),
    special_considerations=[
        "Court of Chancery — specialized business court, no jury trials",
        "Freedom of contract is paramount in LLC agreements",
        "Most Fortune 500 companies incorporated in Delaware",
        "Material Adverse Effect (MAE) clauses heavily litigated here",
        "Fiduciary duty standards: entire fairness vs. business judgment rule",
    ],
))

NEW_YORK = _register(JurisdictionProfile(
    code="NY-US",
    name="New York",
    display_name="State of New York, United States",
    legal_system="common_law",
    key_statutes=[
        "New York General Obligations Law (GOL)",
        "Uniform Commercial Code (UCC) — Articles 2, 2A, 9",
        "New York Civil Practice Law and Rules (CPLR)",
        "NY GOL S.5-1401 — choice of law for contracts > $250K",
        "NY GOL S.5-1402 — personal jurisdiction for contracts > $1M",
    ],
    indemnification_standard=(
        "Broad indemnification permitted. GOL S.5-322.1 voids indemnification "
        "for one's own negligence in construction contracts. Anti-subrogation "
        "rule applies. Consequential damages excluded by default under UCC."
    ),
    non_compete_enforceability=(
        "Enforceable if reasonable — must protect legitimate business interest. "
        "Courts apply strict scrutiny. Garden-leave provisions common. "
        "NY considering legislation to ban non-competes (watch for updates)."
    ),
    arbitration_framework=(
        "Federal Arbitration Act (FAA) applies. JAMS and AAA are common forums. "
        "New York Convention governs international arbitration enforcement."
    ),
    data_protection_law=(
        "NY SHIELD Act (S.899-AA) — data breach notification and security requirements. "
        "NYC local laws on automated employment decision tools (Local Law 144)."
    ),
    special_considerations=[
        "GOL S.5-1401 allows parties to choose NY law for contracts > $250K",
        "No consequential damages by default under UCC Article 2",
        "Litigation-friendly jurisdiction; heavy case law on contract interpretation",
        "Parol evidence rule strictly applied",
        "Anti-assignment clauses strictly construed",
    ],
))

CALIFORNIA = _register(JurisdictionProfile(
    code="CA-US",
    name="California",
    display_name="State of California, United States",
    legal_system="common_law",
    key_statutes=[
        "California Business and Professions Code (BPC) S.16600 — non-competes void",
        "California Civil Code S.1671 — liquidated damages",
        "California Consumer Privacy Act (CCPA/CPRA)",
        "California Labor Code — employee protections",
        "Uniform Commercial Code (California Commercial Code)",
    ],
    indemnification_standard=(
        "Broad indemnification permitted but subject to public policy limits. "
        "Cal. Civ. Code S.2782 restricts indemnity clauses in construction. "
        "Comparative fault applies. Liquidated damages must be reasonable "
        "at time of contracting (S.1671)."
    ),
    non_compete_enforceability=(
        "Post-employment non-competes are VOID under BPC S.16600 — one of the most "
        "employee-friendly jurisdictions in the world. Even narrow non-competes are "
        "unenforceable. Non-solicitation clauses are also suspect. Only trade secret "
        "protections (via CUTSA) are viable."
    ),
    arbitration_framework=(
        "FAA applies. California Arbitration Act (CCP S.1280 et seq.). "
        "Unconscionability doctrine aggressively applied to arbitration clauses "
        "in consumer/employment contexts."
    ),
    data_protection_law=(
        "CCPA/CPRA — comprehensive consumer privacy rights, right to delete, "
        "opt-out of sale, data minimization. California Privacy Protection Agency "
        "(CPPA) enforces. Private right of action for data breaches."
    ),
    special_considerations=[
        "BPC S.16600 — ALL post-employment non-competes are VOID; flag as RED",
        "Strong employee protections — independent contractor misclassification risk",
        "CCPA/CPRA — strictest US privacy law; requires specific contract provisions",
        "Unconscionability doctrine may void one-sided arbitration clauses",
        "Assignment of inventions — Labor Code S.2870 protects employee IP",
    ],
))

ENGLAND_AND_WALES = _register(JurisdictionProfile(
    code="GB-EW",
    name="England and Wales",
    display_name="England and Wales, United Kingdom",
    legal_system="common_law",
    key_statutes=[
        "Unfair Contract Terms Act 1977 (UCTA) — controls exclusion clauses",
        "Contracts (Rights of Third Parties) Act 1999",
        "Sale of Goods Act 1979 / Consumer Rights Act 2015",
        "Late Payment of Commercial Debts (Interest) Act 1998",
        "Arbitration Act 1996",
        "UK GDPR + Data Protection Act 2018",
    ],
    indemnification_standard=(
        "Indemnities must be clear and unambiguous. UCTA S.2 voids exclusion of "
        "liability for death/personal injury from negligence. Penalty doctrine "
        "reformed by Cavendish Square v Makdessi [2015] UKSC 67 — clauses must "
        "have legitimate interest and be proportionate, not penal."
    ),
    non_compete_enforceability=(
        "Enforceable if reasonable — must protect a legitimate business interest "
        "(trade secrets, client relationships, workforce stability). "
        "Duration typically 6-12 months. Garden leave may reduce enforceability. "
        "Blue-pencil severance is restrictive (cannot rewrite, only strike out)."
    ),
    arbitration_framework=(
        "Arbitration Act 1996 — party autonomy is paramount. London is a global "
        "arbitration hub (LCIA, ICC London). Limited court intervention. "
        "S.69 appeal on point of law (can be excluded by agreement)."
    ),
    data_protection_law=(
        "UK GDPR + Data Protection Act 2018. ICO enforces. International Data "
        "Transfer Agreement (IDTA) or EU-approved SCCs for cross-border transfers. "
        "Adequacy decisions for certain countries."
    ),
    special_considerations=[
        "Penalty doctrine (Cavendish v Makdessi) — liquidated damages must be proportionate",
        "UCTA — cannot exclude liability for negligence causing death/personal injury",
        "Entire agreement clauses do not exclude fraudulent misrepresentation",
        "Implied terms under common law (business efficacy, officious bystander tests)",
        "Boilerplate 'reasonable endeavours' vs 'best endeavours' distinction matters",
    ],
))

SINGAPORE = _register(JurisdictionProfile(
    code="SG",
    name="Singapore",
    display_name="Republic of Singapore",
    legal_system="common_law",
    key_statutes=[
        "Contracts Act (Cap. 53) — based on Indian Contract Act but diverged",
        "Sale of Goods Act (Cap. 393)",
        "Arbitration Act (Cap. 10) — domestic arbitration",
        "International Arbitration Act (Cap. 143A) — UNCITRAL Model Law adopted",
        "Personal Data Protection Act 2012 (PDPA)",
        "Computer Misuse Act (Cap. 50A)",
    ],
    indemnification_standard=(
        "English common law principles apply. No statutory restriction on "
        "commercial indemnities. Penalty clause doctrine follows English law "
        "(Cavendish/Makdessi). Liquidated damages must be genuine pre-estimate."
    ),
    non_compete_enforceability=(
        "Enforceable if reasonable — follows English restraint of trade doctrine. "
        "Must protect legitimate proprietary interest. Typically 1-2 years. "
        "Courts will not rewrite but may sever unreasonable portions."
    ),
    arbitration_framework=(
        "Singapore International Arbitration Centre (SIAC) — one of the world's "
        "top arbitration institutions. International Arbitration Act adopts "
        "UNCITRAL Model Law. Singapore Convention on Mediation. Minimal court "
        "interference with arbitral awards."
    ),
    data_protection_law=(
        "PDPA 2012 (amended 2020/2021) — consent obligation, purpose limitation, "
        "data breach notification (mandatory if significant), financial penalties "
        "up to SGD 1M or 10% of annual turnover."
    ),
    special_considerations=[
        "SIAC arbitration is globally recognized — premium choice for APAC contracts",
        "No jury trials — disputes decided by judges",
        "Strong IP protection framework",
        "PDPA mandatory breach notification — 3 business days to PDPC",
        "Singapore Convention on Mediation — cross-border enforcement of mediated settlements",
    ],
))

UAE_DIFC = _register(JurisdictionProfile(
    code="AE-DIFC",
    name="UAE-DIFC",
    display_name="Dubai International Financial Centre (DIFC), UAE",
    legal_system="common_law",
    key_statutes=[
        "DIFC Contract Law (DIFC Law No. 6 of 2004) — based on English common law",
        "DIFC Arbitration Law (DIFC Law No. 1 of 2008) — UNCITRAL Model Law",
        "DIFC Data Protection Law (DIFC Law No. 5 of 2020)",
        "DIFC Employment Law (DIFC Law No. 4 of 2005)",
        "UAE Federal Arbitration Law (Federal Law No. 6 of 2018) — outside DIFC",
    ],
    indemnification_standard=(
        "DIFC follows English common law principles. Broad indemnification "
        "clauses are generally enforceable. Penalty clause doctrine applies "
        "(similar to English law post-Cavendish). Outside DIFC, UAE Civil Code "
        "Article 390 treats penalties differently — courts can adjust."
    ),
    non_compete_enforceability=(
        "DIFC: Enforceable if reasonable (English common law principles). "
        "Onshore UAE: Article 909 of UAE Civil Code and Article 127 of UAE "
        "Labour Law — non-competes valid up to 2 years but must be narrowly drawn."
    ),
    arbitration_framework=(
        "DIFC-LCIA Arbitration Centre. DIFC Courts have enforcement jurisdiction. "
        "JAM gateway between DIFC Courts and onshore Dubai Courts for enforcement. "
        "New York Convention applicable."
    ),
    data_protection_law=(
        "DIFC Data Protection Law 2020 — modeled on EU GDPR. Commissioner of "
        "Data Protection enforces. Adequate protections for data transfers. "
        "Onshore UAE: Federal Decree-Law No. 45 of 2021 on Personal Data Protection."
    ),
    special_considerations=[
        "DIFC is a common-law island within a civil-law jurisdiction",
        "DIFC Courts operate independently from onshore UAE courts",
        "Specify 'DIFC' vs 'onshore UAE' carefully — very different legal regimes",
        "JAM enforcement gateway for cross-jurisdictional enforcement",
        "UAE onshore contracts may be subject to Arabic-language requirements",
    ],
))

UAE_ONSHORE = _register(JurisdictionProfile(
    code="AE",
    name="UAE",
    display_name="United Arab Emirates (Onshore)",
    legal_system="civil_law",
    key_statutes=[
        "UAE Civil Code (Federal Law No. 5 of 1985) — general contract law",
        "UAE Commercial Code (Federal Law No. 18 of 1993)",
        "UAE Federal Arbitration Law (Federal Law No. 6 of 2018)",
        "Federal Decree-Law No. 45 of 2021 on Personal Data Protection",
        "UAE Labour Law (Federal Decree-Law No. 33 of 2021)",
    ],
    indemnification_standard=(
        "Governed by UAE Civil Code Articles 282-298 (tort) and 389-390 (contractual). "
        "Article 390 allows courts to adjust penalties/liquidated damages to match actual loss. "
        "Indemnification is generally enforceable but subject to judicial discretion."
    ),
    non_compete_enforceability=(
        "Article 909 of UAE Civil Code and Article 10 of the new Labour Law — "
        "non-competes valid up to 2 years and must be narrowly drawn in scope, "
        "geography, and activity. Courts may reduce overbroad restrictions."
    ),
    arbitration_framework=(
        "Federal Arbitration Law No. 6 of 2018 (based on UNCITRAL Model Law). "
        "Common seats: Abu Dhabi, Dubai. Institutions include DIAC (Dubai), "
        "ADCCAC (Abu Dhabi). New York Convention applicable."
    ),
    data_protection_law=(
        "Federal Decree-Law No. 45 of 2021 on Personal Data Protection. "
        "Requires consent, purpose limitation, data minimization. "
        "Cross-border transfer restrictions apply."
    ),
    special_considerations=[
        "Civil law jurisdiction — courts may reinterpret contract terms per Civil Code",
        "Arabic is the official legal language — Arabic version prevails in disputes",
        "Article 390 — courts can adjust liquidated damages to match actual loss",
        "Distinguish between onshore UAE, DIFC (Dubai), and ADGM (Abu Dhabi) — different legal systems",
        "Sharia principles may influence contract interpretation in some contexts",
    ],
))

GERMANY = _register(JurisdictionProfile(
    code="DE",
    name="Germany",
    display_name="Federal Republic of Germany",
    legal_system="civil_law",
    key_statutes=[
        "Burgerliches Gesetzbuch (BGB) — German Civil Code",
        "Handelsgesetzbuch (HGB) — German Commercial Code",
        "Allgemeine Geschaftsbedingungen (AGB) — Standard Terms Control (BGB S.305-310)",
        "Gesetz gegen Wettbewerbsbeschrankungen (GWB) — Competition Act",
        "Bundesdatenschutzgesetz (BDSG) + EU GDPR",
        "Zivilprozessordnung (ZPO) — Code of Civil Procedure",
    ],
    indemnification_standard=(
        "BGB S.276 governs fault-based liability. AGB control (S.305-310) heavily "
        "restricts exclusion clauses in standard terms — cannot exclude liability for "
        "intent or gross negligence. Liquidated damages must be reasonable. "
        "Penalty clauses (Vertragsstrafe) are valid in B2B but subject to judicial review."
    ),
    non_compete_enforceability=(
        "Post-contractual non-competes for employees require Karenzentschadigung "
        "(compensation of at least 50% of last remuneration) under HGB S.74-75a. "
        "Without compensation, the non-compete is void but employee may choose to "
        "honor it. B2B non-competes are less regulated."
    ),
    arbitration_framework=(
        "ZPO S.1025-1066 governs arbitration (based on UNCITRAL Model Law). "
        "DIS (German Arbitration Institute) is the primary institution. "
        "Frankfurt and Munich are common seats."
    ),
    data_protection_law=(
        "EU GDPR + BDSG (Federal Data Protection Act). Strict enforcement by "
        "state-level DPAs (Datenschutzaufsichtsbehorden). Works councils have "
        "co-determination rights on employee data processing."
    ),
    special_considerations=[
        "AGB control — standard terms in B2B contracts heavily scrutinized by courts",
        "Non-compete requires mandatory compensation (Karenzentschadigung) for employees",
        "Civil law system — statutory provisions override contract terms more frequently",
        "Works council co-determination on employee-related contract terms",
        "German-language requirement may apply for certain regulatory filings",
    ],
))

FRANCE = _register(JurisdictionProfile(
    code="FR",
    name="France",
    display_name="French Republic",
    legal_system="civil_law",
    key_statutes=[
        "Code Civil (reformed 2016 — Ordonnance No. 2016-131)",
        "Code de Commerce — Commercial Code",
        "Code du Travail — Labour Code",
        "Loi Informatique et Libertes (1978, amended) + EU GDPR",
        "Code de la Consommation — Consumer Code",
    ],
    indemnification_standard=(
        "2016 reform codified many judicial doctrines. Art. 1231-5 — courts can "
        "increase or reduce liquidated damages (clause penale) if manifestly excessive "
        "or derisory. Duty of good faith (Art. 1104) is mandatory and cannot be "
        "contracted out of. Significant imbalance doctrine (Art. 1171) for adhesion contracts."
    ),
    non_compete_enforceability=(
        "Employment non-competes require financial compensation (jurisprudence constante), "
        "must be limited in time, geography, and activity. Without compensation, the "
        "clause is void. B2B non-competes governed by general contract law and competition law."
    ),
    arbitration_framework=(
        "Code de Procedure Civile, Book IV. Paris is a leading global arbitration seat. "
        "ICC headquartered in Paris. Very pro-arbitration judiciary. International "
        "arbitration awards rarely set aside."
    ),
    data_protection_law=(
        "EU GDPR + Loi Informatique et Libertes (as amended). CNIL enforces — "
        "known for significant fines. Strict cookie consent requirements. "
        "Employee data processing subject to additional labour law rules."
    ),
    special_considerations=[
        "Good faith (Art. 1104) is a mandatory overriding principle — cannot be excluded",
        "Courts can modify liquidated damages (clause penale) — Art. 1231-5",
        "Significant imbalance doctrine (Art. 1171) can void unfair terms in adhesion contracts",
        "Loi Sapin II — anti-corruption compliance obligations for large companies",
        "French language may be required for employment contracts in France",
    ],
))

HONG_KONG = _register(JurisdictionProfile(
    code="HK",
    name="Hong Kong",
    display_name="Hong Kong Special Administrative Region",
    legal_system="common_law",
    key_statutes=[
        "Contracts (Rights of Third Parties) Ordinance (Cap. 623)",
        "Sale of Goods Ordinance (Cap. 26)",
        "Arbitration Ordinance (Cap. 609) — UNCITRAL Model Law",
        "Personal Data (Privacy) Ordinance (PDPO) (Cap. 486)",
        "Control of Exemption Clauses Ordinance (CECO) (Cap. 71)",
        "Competition Ordinance (Cap. 619)",
    ],
    indemnification_standard=(
        "English common law principles apply. CECO (Cap. 71) restricts unreasonable "
        "exclusion clauses — similar to UK's UCTA. Penalty clause doctrine follows "
        "English law (Cavendish/Makdessi). Consequential damages can be excluded "
        "if reasonable."
    ),
    non_compete_enforceability=(
        "Follows English restraint of trade doctrine — enforceable if reasonable. "
        "Must protect legitimate business interest. Courts will not rewrite clauses. "
        "Garden-leave provisions recognized."
    ),
    arbitration_framework=(
        "Arbitration Ordinance (Cap. 609) adopts UNCITRAL Model Law. "
        "Hong Kong International Arbitration Centre (HKIAC) is a leading institution. "
        "Strong pro-arbitration policy. New York Convention applies."
    ),
    data_protection_law=(
        "PDPO (Cap. 486) — six data protection principles. Privacy Commissioner "
        "enforces. No mandatory data breach notification (as of 2024). "
        "Cross-border transfer provisions relatively flexible."
    ),
    special_considerations=[
        "Common law system within PRC — unique 'one country, two systems' framework",
        "HKIAC arbitration widely used for PRC-related cross-border disputes",
        "CECO restricts unreasonable exclusion clauses in consumer and B2B contracts",
        "No general competition-law restriction on vertical agreements (unlike EU)",
        "Bilingual legal system (English and Chinese) — both languages equally authoritative",
    ],
))

AUSTRALIA = _register(JurisdictionProfile(
    code="AU",
    name="Australia",
    display_name="Commonwealth of Australia",
    legal_system="common_law",
    key_statutes=[
        "Australian Consumer Law (ACL) — Schedule 2, Competition and Consumer Act 2010",
        "Corporations Act 2001 (Cth)",
        "International Arbitration Act 1974 (Cth)",
        "Privacy Act 1988 (Cth) — Australian Privacy Principles (APPs)",
        "Fair Work Act 2009 (Cth) — employment",
    ],
    indemnification_standard=(
        "Common law indemnification principles. ACL prohibits unfair contract terms "
        "in standard form contracts (extended to small business). Proportionate "
        "liability regimes in most states reduce joint liability exposure. "
        "Penalty rule applies — must be genuine pre-estimate of loss."
    ),
    non_compete_enforceability=(
        "Restraint of trade doctrine applies — enforceable if reasonable. "
        "Courts may read down unreasonable restraints (cascading restraints common "
        "in Australian contracts). Must protect legitimate business interest."
    ),
    arbitration_framework=(
        "International Arbitration Act 1974 (UNCITRAL Model Law). "
        "Domestic: Commercial Arbitration Acts in each state/territory. "
        "Australian Centre for International Commercial Arbitration (ACICA)."
    ),
    data_protection_law=(
        "Privacy Act 1988 — APPs govern personal information handling. "
        "Notifiable Data Breaches scheme (mandatory). OAIC enforces. "
        "Privacy Act review underway with potential expansion."
    ),
    special_considerations=[
        "ACL unfair contract terms provisions apply to small business contracts",
        "Proportionate liability — may reduce indemnification exposure",
        "Cascading restraint clauses are standard drafting practice",
        "Good faith implied in some contracts (relational contracts doctrine)",
        "Consumer guarantees under ACL cannot be excluded",
    ],
))

JAPAN = _register(JurisdictionProfile(
    code="JP",
    name="Japan",
    display_name="Japan",
    legal_system="civil_law",
    key_statutes=[
        "Minpo (Civil Code of Japan) — reformed 2020 (contract law modernization)",
        "Shoho (Commercial Code)",
        "Act on the Protection of Personal Information (APPI) — amended 2022",
        "Arbitration Act (Act No. 138 of 2003) — UNCITRAL Model Law",
        "Anti-Monopoly Act (AMA) — competition law",
        "Subcontractor Act — protections for subcontractors",
    ],
    indemnification_standard=(
        "2020 Civil Code reform modernized damages provisions. Liquidated damages "
        "(songai baisho gaku no yotei) are enforceable but courts retain power to "
        "reduce manifestly excessive amounts. Consequential damages recoverable if "
        "foreseeable. Good faith (shingi seijitsu) is a fundamental principle."
    ),
    non_compete_enforceability=(
        "Post-employment non-competes evaluated on reasonableness — period, scope, "
        "geography, compensation. Courts may void or reduce overbroad restrictions. "
        "Generally 1-2 years, must provide compensation or consideration."
    ),
    arbitration_framework=(
        "Arbitration Act 2003 (UNCITRAL Model Law). Japan Commercial Arbitration "
        "Association (JCAA). Tokyo is the primary seat. Courts supportive of "
        "arbitration. Japan is a signatory to the New York Convention."
    ),
    data_protection_law=(
        "APPI (amended 2022) — consent-based processing, cross-border transfer "
        "restrictions (adequacy + consent model), mandatory breach notification, "
        "PPC (Personal Information Protection Commission) enforces."
    ),
    special_considerations=[
        "Good faith (shingi seijitsu) is a fundamental mandatory principle",
        "2020 Civil Code reform — modernized warranty and damages provisions",
        "Subcontractor Act — special protections in B2B subcontracting relationships",
        "Hanko (seal) may be required alongside signatures for certain contracts",
        "Japanese language typically governs for domestic contracts",
    ],
))


# ---------------------------------------------------------------------------
# Jurisdiction aliases — maps common text references to profile codes
# ---------------------------------------------------------------------------

_JURISDICTION_ALIASES: Dict[str, str] = {
    # India — only match clear jurisdiction references, not adjectives like "Indian"
    "india": "IN",
    "republic of india": "IN",
    "laws of india": "IN",
    "mumbai": "IN",
    "delhi": "IN",
    "new delhi": "IN",
    "bangalore": "IN",
    "bengaluru": "IN",
    "chennai": "IN",
    "hyderabad": "IN",
    "kolkata": "IN",
    "pune": "IN",
    # Delaware
    "delaware": "DE-US",
    "state of delaware": "DE-US",
    # New York
    "new york": "NY-US",
    "state of new york": "NY-US",
    "ny": "NY-US",
    # California
    "california": "CA-US",
    "state of california": "CA-US",
    # England & Wales
    "england": "GB-EW",
    "england and wales": "GB-EW",
    "england & wales": "GB-EW",
    "english law": "GB-EW",
    "united kingdom": "GB-EW",
    "uk": "GB-EW",
    "london": "GB-EW",
    # Singapore
    "singapore": "SG",
    "republic of singapore": "SG",
    # UAE / DIFC / ADGM
    "difc": "AE-DIFC",
    "dubai international financial centre": "AE-DIFC",
    "dubai": "AE-DIFC",
    "uae": "AE",
    "united arab emirates": "AE",
    "abu dhabi": "AE",
    "adgm": "AE-ADGM",
    "abu dhabi global market": "AE-ADGM",
    # Germany
    "germany": "DE",
    "federal republic of germany": "DE",
    "german": "DE",
    "frankfurt": "DE",
    "munich": "DE",
    "berlin": "DE",
    # France
    "france": "FR",
    "french republic": "FR",
    "french": "FR",
    "paris": "FR",
    # Hong Kong
    "hong kong": "HK",
    "hksar": "HK",
    # Australia
    "australia": "AU",
    "commonwealth of australia": "AU",
    "new south wales": "AU",
    "nsw": "AU",
    "victoria": "AU",
    "queensland": "AU",
    "sydney": "AU",
    "melbourne": "AU",
    # Japan
    "japan": "JP",
    "tokyo": "JP",
    # US Federal
    "united states": "US",
    "us federal": "US",
    "federal law": "US",
    # Texas
    "texas": "TX-US",
    "state of texas": "TX-US",
    "houston": "TX-US",
    "dallas": "TX-US",
    "austin": "TX-US",
    "san antonio": "TX-US",
    # EU
    "eu": "EU",
    "european union": "EU",
    "brussels": "EU",
    "european": "EU",
    # ADGM
    # (already mapped above)
}


# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

_GOVERNING_LAW_PATTERNS: List[re.Pattern] = [
    # "governed by the laws of [X]"
    re.compile(
        r"(?:shall\s+be\s+)?govern(?:ed|ing)\s+by\s+(?:the\s+)?(?:laws?|legislation)\s+of\s+(?:the\s+)?(.{3,80}?)(?:\.|,|;|\band\b|\bwithout\b|\bexcluding\b)",
        re.IGNORECASE,
    ),
    # "subject to [X] law"
    re.compile(
        r"(?:shall\s+be\s+)?subject\s+to\s+(?:the\s+)?(?:laws?\s+of\s+)?(.{3,60}?)(?:\s+law[s]?)(?:\.|,|;|\band\b)",
        re.IGNORECASE,
    ),
    # "jurisdiction of [X]"
    re.compile(
        r"(?:exclusive\s+)?jurisdiction\s+of\s+(?:the\s+)?(?:courts?\s+(?:of|in|at)\s+)?(.{3,60}?)(?:\.|,|;|\bshall\b)",
        re.IGNORECASE,
    ),
    # "arbitration in [X]"
    re.compile(
        r"arbitration\s+(?:shall\s+be\s+)?(?:held\s+|conducted\s+|seated\s+)?in\s+(.{3,60}?)(?:\.|,|;|\bin\s+accordance\b|\bunder\b)",
        re.IGNORECASE,
    ),
    # "laws of the State of [X]"
    re.compile(
        r"laws?\s+of\s+the\s+(?:State|Commonwealth|Republic|Kingdom)\s+of\s+(.{3,60}?)(?:\.|,|;|\band\b|\bwithout\b)",
        re.IGNORECASE,
    ),
    # "construed in accordance with [X] law"
    re.compile(
        r"(?:construed|interpreted)\s+in\s+accordance\s+with\s+(?:the\s+)?(?:laws?\s+of\s+)?(.{3,60}?)(?:\s+law[s]?)?(?:\.|,|;)",
        re.IGNORECASE,
    ),
    # "under the laws of [X]"
    re.compile(
        r"under\s+(?:the\s+)?laws?\s+of\s+(?:the\s+)?(.{3,60}?)(?:\.|,|;|\band\b)",
        re.IGNORECASE,
    ),
    # "[X] law shall apply"
    re.compile(
        r"(.{3,40}?)\s+law[s]?\s+shall\s+(?:apply|govern)",
        re.IGNORECASE,
    ),
]


@dataclass
class JurisdictionDetectionResult:
    """Result of jurisdiction detection from contract text."""

    detected_jurisdiction: Optional[str]  # Profile code, e.g. "IN"
    profile: Optional[JurisdictionProfile]
    raw_match: str  # The raw text matched from the contract
    confidence: float  # 0.0 - 1.0
    all_matches: List[Dict[str, Any]]  # All candidate matches found
    source: str  # "auto" | "user_override" | "default"

    def prompt_context(self) -> str:
        """Return the jurisdiction context for prompt injection."""
        if self.profile:
            return self.profile.to_prompt_context()
        return f"JURISDICTION: Unknown ({self.raw_match})\nApply general commercial law principles."


class JurisdictionDetector:
    """
    Deterministic regex-based jurisdiction detector.

    Scans contract text for governing law / jurisdiction / arbitration
    clauses and maps them to jurisdiction profiles.

    Usage:
        detector = JurisdictionDetector()
        result = detector.detect("...contract text...")
        prompt_ctx = result.prompt_context()
    """

    def __init__(self, default_jurisdiction: Optional[str] = None):
        """
        Initialize detector.

        Args:
            default_jurisdiction: Profile code to use when no governing law
                is detected. Defaults to None (neutral — no assumption).
        """
        self.default_code = default_jurisdiction

    def detect(
        self,
        contract_text: str,
        user_override: Optional[str] = None,
    ) -> JurisdictionDetectionResult:
        """
        Detect jurisdiction from contract text.

        Args:
            contract_text: Full contract text to scan.
            user_override: If provided, skip auto-detection and use this
                jurisdiction code or name directly.

        Returns:
            JurisdictionDetectionResult with profile and prompt context.
        """
        # 1. User override takes precedence
        if user_override:
            profile = self._resolve_name(user_override)
            return JurisdictionDetectionResult(
                detected_jurisdiction=profile.code if profile else None,
                profile=profile,
                raw_match=user_override,
                confidence=1.0,
                all_matches=[],
                source="user_override",
            )

        # 2. Auto-detect from contract text
        all_matches = self._extract_candidates(contract_text)

        if not all_matches:
            # No governing law detected — stay neutral, don't assume any jurisdiction
            if self.default_code:
                default_profile = JURISDICTION_PROFILES.get(self.default_code)
            else:
                default_profile = None
            return JurisdictionDetectionResult(
                detected_jurisdiction=self.default_code,
                profile=default_profile,
                raw_match="",
                confidence=0.1,
                all_matches=[],
                source="default",
            )

        # Pick the best match (highest confidence)
        best = max(all_matches, key=lambda m: m["confidence"])
        profile = best.get("profile")

        return JurisdictionDetectionResult(
            detected_jurisdiction=profile.code if profile else None,
            profile=profile,
            raw_match=best["raw_text"],
            confidence=best["confidence"],
            all_matches=all_matches,
            source="auto",
        )

    def _extract_candidates(self, text: str) -> List[Dict[str, Any]]:
        """Run all patterns and collect candidate jurisdiction matches."""
        candidates: List[Dict[str, Any]] = []
        seen_raw: set = set()

        for pattern in _GOVERNING_LAW_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(1).strip().rstrip(".,;")
                raw_lower = raw.lower().strip()

                # Skip duplicates
                if raw_lower in seen_raw:
                    continue
                seen_raw.add(raw_lower)

                profile = self._resolve_name(raw)
                confidence = 0.9 if profile else 0.4

                candidates.append({
                    "raw_text": raw,
                    "profile": profile,
                    "confidence": confidence,
                    "pattern_source": pattern.pattern[:60],
                })

        return candidates

    def _resolve_name(self, name: str) -> Optional[JurisdictionProfile]:
        """
        Resolve a jurisdiction name/code to a profile.

        Tries:
        1. Direct code match (e.g. "IN", "DE-US")
        2. Alias lookup (e.g. "India", "Delaware")
        3. Fuzzy substring match against alias keys
        """
        if not name:
            return None

        clean = name.strip()

        # Direct code match
        if clean.upper() in JURISDICTION_PROFILES:
            return JURISDICTION_PROFILES[clean.upper()]

        # Alias lookup (exact)
        lower = clean.lower()
        if lower in _JURISDICTION_ALIASES:
            code = _JURISDICTION_ALIASES[lower]
            return JURISDICTION_PROFILES.get(code)

        # Word-boundary match against aliases — avoid "indian" matching "Indiana"
        import re as _re
        words = set(_re.findall(r'\b\w+\b', lower))
        for alias, code in _JURISDICTION_ALIASES.items():
            alias_words = set(_re.findall(r'\b\w+\b', alias))
            if alias_words and alias_words.issubset(words):
                return JURISDICTION_PROFILES.get(code)

        # Exact profile name match (not substring)
        for code, profile in JURISDICTION_PROFILES.items():
            if lower == profile.name.lower() or lower == profile.display_name.lower():
                return profile

        return None

    @staticmethod
    def get_all_profiles() -> Dict[str, JurisdictionProfile]:
        """Return all registered jurisdiction profiles."""
        return dict(JURISDICTION_PROFILES)

    @staticmethod
    def get_profile(code: str) -> Optional[JurisdictionProfile]:
        """Get a specific jurisdiction profile by code."""
        return JURISDICTION_PROFILES.get(code.upper())


# ---------------------------------------------------------------------------
# Phase 5: Jurisdiction-specific rule overrides
# ---------------------------------------------------------------------------

@dataclass
class RuleOverride:
    """Jurisdiction-specific override for a rule."""
    rule_id: str
    risk_level: Optional[str] = None  # Override risk level (RED/YELLOW/GREEN)
    suppress: bool = False  # Suppress rule entirely in this jurisdiction
    primary_position: Optional[str] = None  # Override primary position
    note: str = ""  # Explanation of the override


JURISDICTION_RULE_OVERRIDES: Dict[str, List[RuleOverride]] = {
    # === INDIA ===
    "IN": [
        RuleOverride(
            rule_id="non_compete",
            risk_level="GREEN",
            primary_position="Non-compete clauses are void under S.27 Indian Contract Act 1872 (exception: sale of goodwill). Flag but note unenforceability.",
            note="S.27 Indian Contract Act renders post-employment non-competes void as restraint of trade.",
        ),
        RuleOverride(
            rule_id="customer_non_solicitation",
            risk_level="YELLOW",
            primary_position="Non-solicitation clauses are generally enforceable in India if reasonable, unlike non-competes.",
            note="Indian courts distinguish non-solicitation from non-compete; former may survive S.27.",
        ),
        RuleOverride(
            rule_id="data_protection",
            risk_level="YELLOW",
            primary_position=(
                "Future-proof the agreement for DPDP substantive commencement on May 13, 2027: "
                "allocate fiduciary/processor duties, require affected-principal and initial Board "
                "notice without delay, and support the detailed Board report due within 72 hours."
            ),
            note=(
                "DPDP Act 2023 and Rules 2025 use phased commencement; do not present "
                "May 2027 duties as already effective."
            ),
        ),
        RuleOverride(
            rule_id="cross_border_transfer",
            risk_level="YELLOW",
            primary_position=(
                "Permit cross-border processing only subject to current Government restrictions, "
                "Rule 15 requirements, and any stricter applicable Indian sectoral law."
            ),
            note="DPDP Act S.16 permits restrictions by notification; verify current notifications.",
        ),
        RuleOverride(
            rule_id="limitation_period",
            primary_position="Indian Limitation Act 1963: general contract claims = 3 years; specific performance = 3 years; fraud = 3 years from discovery.",
            note="Limitation Act 1963 provides statutory limitation periods that cannot be shortened by contract.",
        ),
        RuleOverride(
            rule_id="arbitration",
            primary_position="Prefer SIAC (Singapore) or ICC arbitration for international contracts. For domestic, specify Indian Arbitration and Conciliation Act 1996 (amended 2019). Seat in Mumbai/Delhi.",
            note="Arbitration and Conciliation Act 1996 (amended 2015, 2019, 2021).",
        ),
        RuleOverride(
            rule_id="taxes_clause",
            primary_position="Clarify GST (18% on services), TDS obligations under Income Tax Act, and stamp duty requirements. Specify which party bears GST.",
            note="GST Act 2017, Income Tax Act 1961 (TDS), Indian Stamp Act 1899.",
        ),
        RuleOverride(
            rule_id="anti_bribery",
            primary_position="Include Prevention of Corruption Act 1988 (amended 2018) compliance. S.9 penalizes commercial organizations for bribery by associated persons.",
            note="Prevention of Corruption (Amendment) Act 2018 introduced corporate liability.",
        ),
    ],

    # === CALIFORNIA ===
    "CA-US": [
        RuleOverride(
            rule_id="non_compete",
            suppress=True,
            note="BPC §16600: California voids ALL post-employment non-competes (except narrow sale-of-business exception). AB 1076 (2020) codified. Void as a matter of public policy.",
        ),
        RuleOverride(
            rule_id="non_solicitation",
            risk_level="YELLOW",
            primary_position="Employee non-solicitation clauses face scrutiny in California post-AMN Healthcare (2020). Customer non-solicits may be permissible but risky.",
            note="AMN Healthcare v. Aya Healthcare (2020) — employee non-solicits may be unenforceable under BPC §16600.",
        ),
        RuleOverride(
            rule_id="jury_waiver",
            risk_level="YELLOW",
            primary_position="Pre-dispute jury waivers are generally enforceable in California federal courts but face challenges in state courts. Ensure knowing and voluntary waiver.",
            note="Grafton Partners v. Superior Court (2005) — CA Supreme Court expressed skepticism.",
        ),
    ],

    # === DELAWARE ===
    "DE-US": [
        RuleOverride(
            rule_id="non_compete",
            risk_level="YELLOW",
            primary_position="Delaware enforces reasonable non-competes. Must protect legitimate economic interest. Continued employment alone is sufficient consideration.",
            note="Delaware Chancery Court applies reasonableness test; relatively employer-friendly.",
        ),
        RuleOverride(
            rule_id="governing_law",
            risk_level="GREEN",
            primary_position="Delaware choice of law is widely accepted. DGCL §145 provides broad indemnification rights for officers/directors.",
            note="Delaware is the preferred jurisdiction for corporate governance matters.",
        ),
    ],

    # === NEW YORK ===
    "NY-US": [
        RuleOverride(
            rule_id="non_compete",
            risk_level="YELLOW",
            primary_position="New York applies strict reasonableness test for non-competes: (1) necessary to protect legitimate interest, (2) not unreasonably burdensome, (3) not harmful to public. Propose 12-month maximum.",
            note="NY courts scrutinize non-competes carefully. Blue-pencil doctrine allows courts to modify.",
        ),
        RuleOverride(
            rule_id="governing_law",
            risk_level="GREEN",
            primary_position="GOL §5-1401 permits NY choice of law for contracts >$250K. GOL §5-1402 permits NY jurisdiction for contracts >$1M.",
            note="General Obligations Law §5-1401 and §5-1402 facilitate NY choice of law/forum.",
        ),
    ],

    # === ENGLAND & WALES ===
    "GB-EW": [
        RuleOverride(
            rule_id="unlimited_liability",
            risk_level="RED",
            primary_position="UCTA S.2(1) prohibits excluding liability for death/personal injury from negligence. S.2(2) subjects other negligence exclusions to reasonableness test.",
            note="Unfair Contract Terms Act 1977 — key statutory restriction on exclusion clauses.",
        ),
        RuleOverride(
            rule_id="consequential_damages",
            primary_position="Consequential damages exclusions enforceable if reasonable under UCTA. Cavendish v Makdessi [2015] UKSC 67 — penalty rule: clause must protect legitimate interest.",
            note="Cavendish/Makdessi replaced the old 'genuine pre-estimate' test.",
        ),
        RuleOverride(
            rule_id="non_compete",
            risk_level="YELLOW",
            primary_position="English law enforces reasonable restraints. Must protect legitimate business interest (trade secrets, client connections, workforce stability). Garden leave clauses commonly used.",
            note="English courts will not rewrite — sever or void entirely.",
        ),
    ],

    # === SINGAPORE ===
    "SG": [
        RuleOverride(
            rule_id="data_protection",
            primary_position="Comply with PDPA 2012 (amended 2020/2021). Mandatory breach notification within 3 business days to PDPC if significant. Consent obligation with limited exceptions.",
            note="PDPA mandatory breach notification since Feb 2021.",
        ),
        RuleOverride(
            rule_id="arbitration",
            primary_position="SIAC arbitration recommended — globally recognized, efficient. International Arbitration Act (Cap. 143A) adopts UNCITRAL Model Law. Minimal court interference.",
            note="Singapore is a premier arbitration hub; SIAC widely used for APAC disputes.",
        ),
    ],

    # === GERMANY ===
    "DE": [
        RuleOverride(
            rule_id="non_compete",
            risk_level="YELLOW",
            primary_position="Post-employment non-competes require Karenzentschädigung (minimum 50% of last remuneration) under HGB §74-75a. Without compensation, clause is void but employee may choose to honor it.",
            note="HGB §74-75a — mandatory compensation for employee non-competes.",
        ),
        RuleOverride(
            rule_id="unlimited_liability",
            risk_level="RED",
            primary_position="AGB control (BGB §305-310) prohibits excluding liability for intent or gross negligence in standard terms. Cannot exclude liability for breach of cardinal obligations.",
            note="BGB §305-310 — strict AGB (standard terms) control in B2B.",
        ),
        RuleOverride(
            rule_id="consequential_damages",
            primary_position="Under AGB control, exclusion of consequential damages for intent/gross negligence is void. For individually negotiated terms, broader exclusions permissible.",
            note="Distinguish between AGB (standard terms) and individually negotiated terms.",
        ),
    ],

    # === FRANCE ===
    "FR": [
        RuleOverride(
            rule_id="non_compete",
            risk_level="YELLOW",
            primary_position="Employment non-competes require financial compensation (jurisprudence constante). Must be limited in time, geography, and activity. No compensation = void.",
            note="French courts void non-competes without compensation (Cass. soc., 10 July 2002).",
        ),
        RuleOverride(
            rule_id="consequential_damages",
            primary_position="Art. 1231-5 Code Civil allows courts to increase or reduce liquidated damages (clause pénale) if manifestly excessive or derisory. Good faith (Art. 1104) is mandatory.",
            note="Art. 1104 good faith obligation cannot be contracted out of.",
        ),
    ],

    # === AUSTRALIA ===
    "AU": [
        RuleOverride(
            rule_id="unlimited_liability",
            primary_position="ACL consumer guarantees cannot be excluded. Proportionate liability regimes in most states reduce joint liability. Consider Apportionment Acts impact.",
            note="Australian Consumer Law — unfair contract terms provisions apply to small business.",
        ),
        RuleOverride(
            rule_id="non_compete",
            risk_level="YELLOW",
            primary_position="Restraint of trade doctrine applies — use cascading restraint clauses (standard Australian practice). Courts may read down unreasonable restraints.",
            note="Cascading restraints allow courts to enforce the most reasonable alternative.",
        ),
    ],
}


def get_rule_overrides(jurisdiction_code: str) -> List[RuleOverride]:
    """Get all rule overrides for a jurisdiction."""
    return JURISDICTION_RULE_OVERRIDES.get(jurisdiction_code, [])


def get_rule_override(jurisdiction_code: str, rule_id: str) -> Optional[RuleOverride]:
    """Get a specific rule override for a jurisdiction + rule combination."""
    overrides = JURISDICTION_RULE_OVERRIDES.get(jurisdiction_code, [])
    for ov in overrides:
        if ov.rule_id == rule_id:
            return ov
    return None


def apply_jurisdiction_overrides(
    matches: list,
    jurisdiction_code: str,
) -> list:
    """
    Apply jurisdiction-specific rule overrides to a list of RuleMatch objects.

    This modifies risk levels, suppresses rules, and adds jurisdiction notes
    based on the detected jurisdiction.

    Args:
        matches: List of RuleMatch objects from the rule engine
        jurisdiction_code: Detected jurisdiction code (e.g., "IN", "CA-US")

    Returns:
        Modified list of RuleMatch objects with jurisdiction adjustments
    """
    from app.services.rule_engine import RiskLevel as RL

    overrides = get_rule_overrides(jurisdiction_code)
    if not overrides:
        return matches

    override_map = {ov.rule_id: ov for ov in overrides}
    result = []

    for match in matches:
        ov = override_map.get(match.rule_id)
        if not ov:
            result.append(match)
            continue

        # Suppress rule entirely in this jurisdiction
        if ov.suppress:
            continue

        # Apply risk level override
        if ov.risk_level:
            risk_map = {"RED": RL.RED, "YELLOW": RL.YELLOW, "GREEN": RL.GREEN}
            new_risk = risk_map.get(ov.risk_level)
            if new_risk and new_risk != match.risk_level:
                match.original_risk_level = match.risk_level
                match.risk_level = new_risk
                match.escalation_reason = f"Jurisdiction override ({jurisdiction_code}): {ov.note}"

        # Override primary position with jurisdiction-specific guidance
        if ov.primary_position:
            match.primary_position = ov.primary_position

        result.append(match)

    return result


# Singleton
jurisdiction_detector = JurisdictionDetector()
