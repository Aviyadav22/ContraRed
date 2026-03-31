"""
Seed script: Migrate hardcoded jurisdiction profiles and rule overrides to DB.

Reads existing profiles from jurisdiction_detector.py dataclasses and inserts
them into the jurisdictions / jurisdiction_rule_overrides tables.

Usage:
    python -m scripts.seed_jurisdictions
"""

import asyncio
import logging
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jurisdiction import Jurisdiction, JurisdictionRuleOverride

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Jurisdiction profile data (migrated from jurisdiction_detector.py)
# ---------------------------------------------------------------------------

JURISDICTION_SEED_DATA: List[Dict] = [
    {
        "code": "IN",
        "name": "India",
        "display_name": "Republic of India",
        "legal_system": "common_law",
        "sort_order": 1,
        "aliases": [
            "india", "republic of india", "laws of india",
            "mumbai", "delhi", "new delhi", "bangalore", "bengaluru",
            "chennai", "hyderabad", "kolkata", "pune",
        ],
        "key_statutes": [
            "Indian Contract Act, 1872 (governs formation, performance, breach)",
            "Specific Relief Act, 1963 (injunctions, specific performance)",
            "Arbitration and Conciliation Act, 1996 (domestic & international arbitration)",
            "Information Technology Act, 2000 (electronic contracts, cybersecurity)",
            "Digital Personal Data Protection Act, 2023 (DPDP Act — data privacy)",
            "Foreign Exchange Management Act, 1999 (FEMA — cross-border payments)",
            "Competition Act, 2002 (anti-competitive agreements)",
            "Indian Stamp Act, 1899 (stamp duty on agreements)",
            "MSME Development Act, 2006 (payment protections for micro/small enterprises)",
            "Labour Codes 2020 (Industrial Relations, Social Security, Wages, OSH)",
            "Companies Act, 2013 (corporate governance, related-party transactions)",
        ],
        "indemnification_standard": (
            "Governed by S.73 and S.74 of the Indian Contract Act. S.73 allows "
            "damages for loss naturally arising from breach. S.74 treats liquidated "
            "damages as the upper ceiling — courts can award lesser amounts. "
            "Penalty clauses are unenforceable beyond reasonable pre-estimate of loss."
        ),
        "non_compete_enforceability": (
            "Post-termination non-competes are VOID under S.27 of the Indian Contract Act "
            "(restraint of trade). Only during-term non-competes are enforceable. "
            "Non-solicitation clauses are generally enforceable if reasonable."
        ),
        "arbitration_framework": (
            "Arbitration and Conciliation Act, 1996 (amended 2015, 2019, 2021). "
            "Seat of arbitration determines curial law. Indian courts have limited "
            "grounds for setting aside awards (S.34). Institutional arbitration "
            "encouraged (SIAC, ICC, MCIA)."
        ),
        "data_protection_law": (
            "DPDP Act, 2023 — consent-based processing, data fiduciary obligations, "
            "cross-border transfer restrictions (government-notified blacklist model), "
            "significant penalties up to INR 250 crore."
        ),
        "special_considerations": [
            "S.27 — post-termination non-competes are VOID; flag any such clause as RED",
            "Stamp duty — unstamped agreements may be inadmissible as evidence",
            "FEMA compliance required for cross-border payment obligations",
            "S.74 — liquidated damages are ceiling, not floor; courts can reduce",
            "Force majeure not codified — governed by S.56 (doctrine of frustration)",
            "Exclusive jurisdiction clauses are valid but subject to constitutional limits",
            "MSME Act — 45-day payment obligation to micro/small enterprises",
            "Labour Codes 2020 — fixed-term employment, standing orders modernized",
        ],
    },
    {
        "code": "DE-US",
        "name": "Delaware",
        "display_name": "State of Delaware, United States",
        "legal_system": "common_law",
        "sort_order": 2,
        "aliases": ["delaware", "state of delaware"],
        "key_statutes": [
            "Delaware General Corporation Law (DGCL) — corporate governance",
            "Delaware LLC Act (Title 6, Ch. 18) — maximum freedom of contract for LLCs",
            "Uniform Commercial Code (UCC) — sale of goods",
            "Delaware Revised Uniform Partnership Act",
        ],
        "indemnification_standard": (
            "Very permissive. Delaware allows broad indemnification including advancement "
            "of expenses. DGCL S.145 governs corporate indemnification. LLC agreements "
            "can customize indemnification almost without limit."
        ),
        "non_compete_enforceability": (
            "Enforceable if reasonable in scope, duration (typically 1-2 years), "
            "and geographic area. Blue-pencil doctrine applied — courts may modify "
            "overbroad restrictions rather than void them entirely."
        ),
        "arbitration_framework": (
            "Federal Arbitration Act (FAA) applies. Delaware Rapid Arbitration Act (DRAA) "
            "available for business disputes. Court of Chancery handles corporate disputes."
        ),
        "data_protection_law": (
            "Delaware Personal Data Privacy Act (DPDPA) effective 2025. "
            "No comprehensive federal privacy law; sector-specific (HIPAA, GLBA)."
        ),
        "special_considerations": [
            "Court of Chancery — specialized business court, no jury trials",
            "Freedom of contract is paramount in LLC agreements",
            "Most Fortune 500 companies incorporated in Delaware",
            "Material Adverse Effect (MAE) clauses heavily litigated here",
            "Fiduciary duty standards: entire fairness vs. business judgment rule",
        ],
    },
    {
        "code": "NY-US",
        "name": "New York",
        "display_name": "State of New York, United States",
        "legal_system": "common_law",
        "sort_order": 3,
        "aliases": ["new york", "state of new york", "ny"],
        "key_statutes": [
            "New York General Obligations Law (GOL)",
            "Uniform Commercial Code (UCC) — Articles 2, 2A, 9",
            "New York Civil Practice Law and Rules (CPLR)",
            "NY GOL S.5-1401 — choice of law for contracts > $250K",
            "NY GOL S.5-1402 — personal jurisdiction for contracts > $1M",
        ],
        "indemnification_standard": (
            "Broad indemnification permitted. GOL S.5-322.1 voids indemnification "
            "for one's own negligence in construction contracts. Anti-subrogation "
            "rule applies. Consequential damages excluded by default under UCC."
        ),
        "non_compete_enforceability": (
            "Enforceable if reasonable — must protect legitimate business interest. "
            "Courts apply strict scrutiny. Garden-leave provisions common. "
            "NY considering legislation to ban non-competes (watch for updates)."
        ),
        "arbitration_framework": (
            "Federal Arbitration Act (FAA) applies. JAMS and AAA are common forums. "
            "New York Convention governs international arbitration enforcement."
        ),
        "data_protection_law": (
            "NY SHIELD Act (S.899-AA) — data breach notification and security requirements. "
            "NYC local laws on automated employment decision tools (Local Law 144)."
        ),
        "special_considerations": [
            "GOL S.5-1401 allows parties to choose NY law for contracts > $250K",
            "No consequential damages by default under UCC Article 2",
            "Litigation-friendly jurisdiction; heavy case law on contract interpretation",
            "Parol evidence rule strictly applied",
            "Anti-assignment clauses strictly construed",
        ],
    },
    {
        "code": "CA-US",
        "name": "California",
        "display_name": "State of California, United States",
        "legal_system": "common_law",
        "sort_order": 4,
        "aliases": ["california", "state of california"],
        "key_statutes": [
            "California Business and Professions Code (BPC) S.16600 — non-competes void",
            "California Civil Code S.1671 — liquidated damages",
            "California Consumer Privacy Act (CCPA/CPRA)",
            "California Labor Code — employee protections",
            "Uniform Commercial Code (California Commercial Code)",
        ],
        "indemnification_standard": (
            "Broad indemnification permitted but subject to public policy limits. "
            "Cal. Civ. Code S.2782 restricts indemnity clauses in construction. "
            "Comparative fault applies. Liquidated damages must be reasonable "
            "at time of contracting (S.1671)."
        ),
        "non_compete_enforceability": (
            "Post-employment non-competes are VOID under BPC S.16600 — one of the most "
            "employee-friendly jurisdictions in the world. Even narrow non-competes are "
            "unenforceable. Non-solicitation clauses are also suspect. Only trade secret "
            "protections (via CUTSA) are viable."
        ),
        "arbitration_framework": (
            "FAA applies. California Arbitration Act (CCP S.1280 et seq.). "
            "Unconscionability doctrine aggressively applied to arbitration clauses "
            "in consumer/employment contexts."
        ),
        "data_protection_law": (
            "CCPA/CPRA — comprehensive consumer privacy rights, right to delete, "
            "opt-out of sale, data minimization. California Privacy Protection Agency "
            "(CPPA) enforces. Private right of action for data breaches."
        ),
        "special_considerations": [
            "BPC S.16600 — ALL post-employment non-competes are VOID; flag as RED",
            "Strong employee protections — independent contractor misclassification risk",
            "CCPA/CPRA — strictest US privacy law; requires specific contract provisions",
            "Unconscionability doctrine may void one-sided arbitration clauses",
            "Assignment of inventions — Labor Code S.2870 protects employee IP",
        ],
    },
    {
        "code": "GB-EW",
        "name": "England and Wales",
        "display_name": "England and Wales, United Kingdom",
        "legal_system": "common_law",
        "sort_order": 5,
        "aliases": [
            "england", "england and wales", "england & wales",
            "english law", "united kingdom", "uk", "london",
        ],
        "key_statutes": [
            "Unfair Contract Terms Act 1977 (UCTA) — controls exclusion clauses",
            "Contracts (Rights of Third Parties) Act 1999",
            "Sale of Goods Act 1979 / Consumer Rights Act 2015",
            "Late Payment of Commercial Debts (Interest) Act 1998",
            "Arbitration Act 1996",
            "UK GDPR + Data Protection Act 2018",
        ],
        "indemnification_standard": (
            "Indemnities must be clear and unambiguous. UCTA S.2 voids exclusion of "
            "liability for death/personal injury from negligence. Penalty doctrine "
            "reformed by Cavendish Square v Makdessi [2015] UKSC 67 — clauses must "
            "have legitimate interest and be proportionate, not penal."
        ),
        "non_compete_enforceability": (
            "Enforceable if reasonable — must protect a legitimate business interest "
            "(trade secrets, client relationships, workforce stability). "
            "Duration typically 6-12 months. Garden leave may reduce enforceability. "
            "Blue-pencil severance is restrictive (cannot rewrite, only strike out)."
        ),
        "arbitration_framework": (
            "Arbitration Act 1996 — party autonomy is paramount. London is a global "
            "arbitration hub (LCIA, ICC London). Limited court intervention. "
            "S.69 appeal on point of law (can be excluded by agreement)."
        ),
        "data_protection_law": (
            "UK GDPR + Data Protection Act 2018. ICO enforces. International Data "
            "Transfer Agreement (IDTA) or EU-approved SCCs for cross-border transfers. "
            "Adequacy decisions for certain countries."
        ),
        "special_considerations": [
            "Penalty doctrine (Cavendish v Makdessi) — liquidated damages must be proportionate",
            "UCTA — cannot exclude liability for negligence causing death/personal injury",
            "Entire agreement clauses do not exclude fraudulent misrepresentation",
            "Implied terms under common law (business efficacy, officious bystander tests)",
            "Boilerplate 'reasonable endeavours' vs 'best endeavours' distinction matters",
        ],
    },
    {
        "code": "SG",
        "name": "Singapore",
        "display_name": "Republic of Singapore",
        "legal_system": "common_law",
        "sort_order": 6,
        "aliases": ["singapore", "republic of singapore"],
        "key_statutes": [
            "Contracts Act (Cap. 53) — based on Indian Contract Act but diverged",
            "Sale of Goods Act (Cap. 393)",
            "Arbitration Act (Cap. 10) — domestic arbitration",
            "International Arbitration Act (Cap. 143A) — UNCITRAL Model Law adopted",
            "Personal Data Protection Act 2012 (PDPA)",
            "Computer Misuse Act (Cap. 50A)",
        ],
        "indemnification_standard": (
            "English common law principles apply. No statutory restriction on "
            "commercial indemnities. Penalty clause doctrine follows English law "
            "(Cavendish/Makdessi). Liquidated damages must be genuine pre-estimate."
        ),
        "non_compete_enforceability": (
            "Enforceable if reasonable — follows English restraint of trade doctrine. "
            "Must protect legitimate proprietary interest. Typically 1-2 years. "
            "Courts will not rewrite but may sever unreasonable portions."
        ),
        "arbitration_framework": (
            "Singapore International Arbitration Centre (SIAC) — one of the world's "
            "top arbitration institutions. International Arbitration Act adopts "
            "UNCITRAL Model Law. Singapore Convention on Mediation. Minimal court "
            "interference with arbitral awards."
        ),
        "data_protection_law": (
            "PDPA 2012 (amended 2020/2021) — consent obligation, purpose limitation, "
            "data breach notification (mandatory if significant), financial penalties "
            "up to SGD 1M or 10% of annual turnover."
        ),
        "special_considerations": [
            "SIAC arbitration is globally recognized — premium choice for APAC contracts",
            "No jury trials — disputes decided by judges",
            "Strong IP protection framework",
            "PDPA mandatory breach notification — 3 business days to PDPC",
            "Singapore Convention on Mediation — cross-border enforcement of mediated settlements",
        ],
    },
    {
        "code": "AE-DIFC",
        "name": "UAE-DIFC",
        "display_name": "Dubai International Financial Centre (DIFC), UAE",
        "legal_system": "common_law",
        "sort_order": 7,
        "aliases": ["difc", "dubai international financial centre", "dubai"],
        "key_statutes": [
            "DIFC Contract Law (DIFC Law No. 6 of 2004) — based on English common law",
            "DIFC Arbitration Law (DIFC Law No. 1 of 2008) — UNCITRAL Model Law",
            "DIFC Data Protection Law (DIFC Law No. 5 of 2020)",
            "DIFC Employment Law (DIFC Law No. 4 of 2005)",
            "UAE Federal Arbitration Law (Federal Law No. 6 of 2018) — outside DIFC",
        ],
        "indemnification_standard": (
            "DIFC follows English common law principles. Broad indemnification "
            "clauses are generally enforceable. Penalty clause doctrine applies "
            "(similar to English law post-Cavendish). Outside DIFC, UAE Civil Code "
            "Article 390 treats penalties differently — courts can adjust."
        ),
        "non_compete_enforceability": (
            "DIFC: Enforceable if reasonable (English common law principles). "
            "Onshore UAE: Article 909 of UAE Civil Code and Article 127 of UAE "
            "Labour Law — non-competes valid up to 2 years but must be narrowly drawn."
        ),
        "arbitration_framework": (
            "DIFC-LCIA Arbitration Centre. DIFC Courts have enforcement jurisdiction. "
            "JAM gateway between DIFC Courts and onshore Dubai Courts for enforcement. "
            "New York Convention applicable."
        ),
        "data_protection_law": (
            "DIFC Data Protection Law 2020 — modeled on EU GDPR. Commissioner of "
            "Data Protection enforces. Adequate protections for data transfers. "
            "Onshore UAE: Federal Decree-Law No. 45 of 2021 on Personal Data Protection."
        ),
        "special_considerations": [
            "DIFC is a common-law island within a civil-law jurisdiction",
            "DIFC Courts operate independently from onshore UAE courts",
            "Specify 'DIFC' vs 'onshore UAE' carefully — very different legal regimes",
            "JAM enforcement gateway for cross-jurisdictional enforcement",
            "UAE onshore contracts may be subject to Arabic-language requirements",
        ],
    },
    {
        "code": "AE",
        "name": "UAE",
        "display_name": "United Arab Emirates (Onshore)",
        "legal_system": "civil_law",
        "sort_order": 8,
        "aliases": ["uae", "united arab emirates", "abu dhabi"],
        "key_statutes": [
            "UAE Civil Code (Federal Law No. 5 of 1985) — general contract law",
            "UAE Commercial Code (Federal Law No. 18 of 1993)",
            "UAE Federal Arbitration Law (Federal Law No. 6 of 2018)",
            "Federal Decree-Law No. 45 of 2021 on Personal Data Protection",
            "UAE Labour Law (Federal Decree-Law No. 33 of 2021)",
        ],
        "indemnification_standard": (
            "Governed by UAE Civil Code Articles 282-298 (tort) and 389-390 (contractual). "
            "Article 390 allows courts to adjust penalties/liquidated damages to match actual loss. "
            "Indemnification is generally enforceable but subject to judicial discretion."
        ),
        "non_compete_enforceability": (
            "Article 909 of UAE Civil Code and Article 10 of the new Labour Law — "
            "non-competes valid up to 2 years and must be narrowly drawn in scope, "
            "geography, and activity. Courts may reduce overbroad restrictions."
        ),
        "arbitration_framework": (
            "Federal Arbitration Law No. 6 of 2018 (based on UNCITRAL Model Law). "
            "Common seats: Abu Dhabi, Dubai. Institutions include DIAC (Dubai), "
            "ADCCAC (Abu Dhabi). New York Convention applicable."
        ),
        "data_protection_law": (
            "Federal Decree-Law No. 45 of 2021 on Personal Data Protection. "
            "Requires consent, purpose limitation, data minimization. "
            "Cross-border transfer restrictions apply."
        ),
        "special_considerations": [
            "Civil law jurisdiction — courts may reinterpret contract terms per Civil Code",
            "Arabic is the official legal language — Arabic version prevails in disputes",
            "Article 390 — courts can adjust liquidated damages to match actual loss",
            "Distinguish between onshore UAE, DIFC (Dubai), and ADGM (Abu Dhabi) — different legal systems",
            "Sharia principles may influence contract interpretation in some contexts",
        ],
    },
    {
        "code": "DE",
        "name": "Germany",
        "display_name": "Federal Republic of Germany",
        "legal_system": "civil_law",
        "sort_order": 9,
        "aliases": ["germany", "federal republic of germany", "german", "frankfurt", "munich", "berlin"],
        "key_statutes": [
            "Burgerliches Gesetzbuch (BGB) — German Civil Code",
            "Handelsgesetzbuch (HGB) — German Commercial Code",
            "Allgemeine Geschaftsbedingungen (AGB) — Standard Terms Control (BGB S.305-310)",
            "Gesetz gegen Wettbewerbsbeschrankungen (GWB) — Competition Act",
            "Bundesdatenschutzgesetz (BDSG) + EU GDPR",
            "Zivilprozessordnung (ZPO) — Code of Civil Procedure",
        ],
        "indemnification_standard": (
            "BGB S.276 governs fault-based liability. AGB control (S.305-310) heavily "
            "restricts exclusion clauses in standard terms — cannot exclude liability for "
            "intent or gross negligence. Liquidated damages must be reasonable. "
            "Penalty clauses (Vertragsstrafe) are valid in B2B but subject to judicial review."
        ),
        "non_compete_enforceability": (
            "Post-contractual non-competes for employees require Karenzentschadigung "
            "(compensation of at least 50% of last remuneration) under HGB S.74-75a. "
            "Without compensation, the non-compete is void but employee may choose to "
            "honor it. B2B non-competes are less regulated."
        ),
        "arbitration_framework": (
            "ZPO S.1025-1066 governs arbitration (based on UNCITRAL Model Law). "
            "DIS (German Arbitration Institute) is the primary institution. "
            "Frankfurt and Munich are common seats."
        ),
        "data_protection_law": (
            "EU GDPR + BDSG (Federal Data Protection Act). Strict enforcement by "
            "state-level DPAs (Datenschutzaufsichtsbehorden). Works councils have "
            "co-determination rights on employee data processing."
        ),
        "special_considerations": [
            "AGB control — standard terms in B2B contracts heavily scrutinized by courts",
            "Non-compete requires mandatory compensation (Karenzentschadigung) for employees",
            "Civil law system — statutory provisions override contract terms more frequently",
            "Works council co-determination on employee-related contract terms",
            "German-language requirement may apply for certain regulatory filings",
        ],
    },
    {
        "code": "FR",
        "name": "France",
        "display_name": "French Republic",
        "legal_system": "civil_law",
        "sort_order": 10,
        "aliases": ["france", "french republic", "french", "paris"],
        "key_statutes": [
            "Code Civil (reformed 2016 — Ordonnance No. 2016-131)",
            "Code de Commerce — Commercial Code",
            "Code du Travail — Labour Code",
            "Loi Informatique et Libertes (1978, amended) + EU GDPR",
            "Code de la Consommation — Consumer Code",
        ],
        "indemnification_standard": (
            "2016 reform codified many judicial doctrines. Art. 1231-5 — courts can "
            "increase or reduce liquidated damages (clause penale) if manifestly excessive "
            "or derisory. Duty of good faith (Art. 1104) is mandatory and cannot be "
            "contracted out of. Significant imbalance doctrine (Art. 1171) for adhesion contracts."
        ),
        "non_compete_enforceability": (
            "Employment non-competes require financial compensation (jurisprudence constante), "
            "must be limited in time, geography, and activity. Without compensation, the "
            "clause is void. B2B non-competes governed by general contract law and competition law."
        ),
        "arbitration_framework": (
            "Code de Procedure Civile, Book IV. Paris is a leading global arbitration seat. "
            "ICC headquartered in Paris. Very pro-arbitration judiciary. International "
            "arbitration awards rarely set aside."
        ),
        "data_protection_law": (
            "EU GDPR + Loi Informatique et Libertes (as amended). CNIL enforces — "
            "known for significant fines. Strict cookie consent requirements. "
            "Employee data processing subject to additional labour law rules."
        ),
        "special_considerations": [
            "Good faith (Art. 1104) is a mandatory overriding principle — cannot be excluded",
            "Courts can modify liquidated damages (clause penale) — Art. 1231-5",
            "Significant imbalance doctrine (Art. 1171) can void unfair terms in adhesion contracts",
            "Loi Sapin II — anti-corruption compliance obligations for large companies",
            "French language may be required for employment contracts in France",
        ],
    },
    {
        "code": "HK",
        "name": "Hong Kong",
        "display_name": "Hong Kong Special Administrative Region",
        "legal_system": "common_law",
        "sort_order": 11,
        "aliases": ["hong kong", "hksar"],
        "key_statutes": [
            "Contracts (Rights of Third Parties) Ordinance (Cap. 623)",
            "Sale of Goods Ordinance (Cap. 26)",
            "Arbitration Ordinance (Cap. 609) — UNCITRAL Model Law",
            "Personal Data (Privacy) Ordinance (PDPO) (Cap. 486)",
            "Control of Exemption Clauses Ordinance (CECO) (Cap. 71)",
            "Competition Ordinance (Cap. 619)",
        ],
        "indemnification_standard": (
            "English common law principles apply. CECO (Cap. 71) restricts unreasonable "
            "exclusion clauses — similar to UK's UCTA. Penalty clause doctrine follows "
            "English law (Cavendish/Makdessi). Consequential damages can be excluded "
            "if reasonable."
        ),
        "non_compete_enforceability": (
            "Follows English restraint of trade doctrine — enforceable if reasonable. "
            "Must protect legitimate business interest. Courts will not rewrite clauses. "
            "Garden-leave provisions recognized."
        ),
        "arbitration_framework": (
            "Arbitration Ordinance (Cap. 609) adopts UNCITRAL Model Law. "
            "Hong Kong International Arbitration Centre (HKIAC) is a leading institution. "
            "Strong pro-arbitration policy. New York Convention applies."
        ),
        "data_protection_law": (
            "PDPO (Cap. 486) — six data protection principles. Privacy Commissioner "
            "enforces. No mandatory data breach notification (as of 2024). "
            "Cross-border transfer provisions relatively flexible."
        ),
        "special_considerations": [
            "Common law system within PRC — unique 'one country, two systems' framework",
            "HKIAC arbitration widely used for PRC-related cross-border disputes",
            "CECO restricts unreasonable exclusion clauses in consumer and B2B contracts",
            "No general competition-law restriction on vertical agreements (unlike EU)",
            "Bilingual legal system (English and Chinese) — both languages equally authoritative",
        ],
    },
    {
        "code": "AU",
        "name": "Australia",
        "display_name": "Commonwealth of Australia",
        "legal_system": "common_law",
        "sort_order": 12,
        "aliases": [
            "australia", "commonwealth of australia",
            "new south wales", "nsw", "victoria", "queensland",
            "sydney", "melbourne",
        ],
        "key_statutes": [
            "Australian Consumer Law (ACL) — Schedule 2, Competition and Consumer Act 2010",
            "Corporations Act 2001 (Cth)",
            "International Arbitration Act 1974 (Cth)",
            "Privacy Act 1988 (Cth) — Australian Privacy Principles (APPs)",
            "Fair Work Act 2009 (Cth) — employment",
        ],
        "indemnification_standard": (
            "Common law indemnification principles. ACL prohibits unfair contract terms "
            "in standard form contracts (extended to small business). Proportionate "
            "liability regimes in most states reduce joint liability exposure. "
            "Penalty rule applies — must be genuine pre-estimate of loss."
        ),
        "non_compete_enforceability": (
            "Restraint of trade doctrine applies — enforceable if reasonable. "
            "Courts may read down unreasonable restraints (cascading restraints common "
            "in Australian contracts). Must protect legitimate business interest."
        ),
        "arbitration_framework": (
            "International Arbitration Act 1974 (UNCITRAL Model Law). "
            "Domestic: Commercial Arbitration Acts in each state/territory. "
            "Australian Centre for International Commercial Arbitration (ACICA)."
        ),
        "data_protection_law": (
            "Privacy Act 1988 — APPs govern personal information handling. "
            "Notifiable Data Breaches scheme (mandatory). OAIC enforces. "
            "Privacy Act review underway with potential expansion."
        ),
        "special_considerations": [
            "ACL unfair contract terms provisions apply to small business contracts",
            "Proportionate liability — may reduce indemnification exposure",
            "Cascading restraint clauses are standard drafting practice",
            "Good faith implied in some contracts (relational contracts doctrine)",
            "Consumer guarantees under ACL cannot be excluded",
        ],
    },
    {
        "code": "JP",
        "name": "Japan",
        "display_name": "Japan",
        "legal_system": "civil_law",
        "sort_order": 13,
        "aliases": ["japan", "tokyo"],
        "key_statutes": [
            "Minpo (Civil Code of Japan) — reformed 2020 (contract law modernization)",
            "Shoho (Commercial Code)",
            "Act on the Protection of Personal Information (APPI) — amended 2022",
            "Arbitration Act (Act No. 138 of 2003) — UNCITRAL Model Law",
            "Anti-Monopoly Act (AMA) — competition law",
            "Subcontractor Act — protections for subcontractors",
        ],
        "indemnification_standard": (
            "2020 Civil Code reform modernized damages provisions. Liquidated damages "
            "(songai baisho gaku no yotei) are enforceable but courts retain power to "
            "reduce manifestly excessive amounts. Consequential damages recoverable if "
            "foreseeable. Good faith (shingi seijitsu) is a fundamental principle."
        ),
        "non_compete_enforceability": (
            "Post-employment non-competes evaluated on reasonableness — period, scope, "
            "geography, compensation. Courts may void or reduce overbroad restrictions. "
            "Generally 1-2 years, must provide compensation or consideration."
        ),
        "arbitration_framework": (
            "Arbitration Act 2003 (UNCITRAL Model Law). Japan Commercial Arbitration "
            "Association (JCAA). Tokyo is the primary seat. Courts supportive of "
            "arbitration. Japan is a signatory to the New York Convention."
        ),
        "data_protection_law": (
            "APPI (amended 2022) — consent-based processing, cross-border transfer "
            "restrictions (adequacy + consent model), mandatory breach notification, "
            "PPC (Personal Information Protection Commission) enforces."
        ),
        "special_considerations": [
            "Good faith (shingi seijitsu) is a fundamental mandatory principle",
            "2020 Civil Code reform — modernized warranty and damages provisions",
            "Subcontractor Act — special protections in B2B subcontracting relationships",
            "Hanko (seal) may be required alongside signatures for certain contracts",
            "Japanese language typically governs for domestic contracts",
        ],
    },
    # ======== NEW JURISDICTIONS (Sprint 3) ========
    {
        "code": "US",
        "name": "US Federal",
        "display_name": "United States (Federal)",
        "legal_system": "common_law",
        "sort_order": 14,
        "aliases": ["united states", "us federal", "federal law", "u.s."],
        "key_statutes": [
            "Federal Arbitration Act (FAA) — 9 U.S.C. §§1-16",
            "Defend Trade Secrets Act (DTSA) — 18 U.S.C. §§1836-1839",
            "FTC Act — Section 5 (unfair or deceptive acts)",
            "CLOUD Act — Clarifying Lawful Overseas Use of Data Act",
            "Sherman Act — antitrust (15 U.S.C. §§1-7)",
            "Sarbanes-Oxley Act (SOX) — corporate governance, whistleblower protection",
            "Foreign Corrupt Practices Act (FCPA) — anti-bribery",
            "HIPAA — health data privacy",
            "Gramm-Leach-Bliley Act (GLBA) — financial data privacy",
        ],
        "indemnification_standard": (
            "No unified federal indemnification standard — governed by state law. "
            "Federal procurement contracts follow FAR (Federal Acquisition Regulation). "
            "DTSA provides federal civil remedy for trade secret misappropriation. "
            "FAA strongly favors enforcement of arbitration agreements."
        ),
        "non_compete_enforceability": (
            "FTC proposed ban on non-competes (2024) — status uncertain. Currently governed "
            "by state law. DTSA provides federal trade secret protection as alternative to "
            "non-competes. Federal employees subject to specific restrictions."
        ),
        "arbitration_framework": (
            "Federal Arbitration Act (FAA) — strong federal policy favoring arbitration. "
            "Preempts state laws that single out arbitration agreements. AAA and JAMS are "
            "primary institutions. New York Convention for international arbitration."
        ),
        "data_protection_law": (
            "No comprehensive federal privacy law. Sector-specific: HIPAA (health), "
            "GLBA (financial), COPPA (children), FERPA (education). CLOUD Act governs "
            "cross-border data access by US law enforcement."
        ),
        "special_considerations": [
            "No comprehensive federal privacy law — patchwork of sector-specific statutes",
            "FAA preempts state arbitration laws — strong pro-arbitration policy",
            "FCPA — extraterritorial anti-bribery with strict corporate liability",
            "CLOUD Act — US can compel data from US providers regardless of data location",
            "DTSA — federal trade secret protection with ex parte seizure remedy",
            "SOX whistleblower protections for public companies",
        ],
    },
    {
        "code": "TX-US",
        "name": "Texas",
        "display_name": "State of Texas, United States",
        "legal_system": "common_law",
        "sort_order": 15,
        "parent_code": "US",
        "aliases": ["texas", "state of texas", "houston", "dallas", "austin", "san antonio"],
        "key_statutes": [
            "Texas Business and Commerce Code (TBCC) — UCC adoption + non-compete provisions",
            "Texas Covenants Not to Compete Act (TBCC Ch. 15.50-15.52)",
            "Texas Data Privacy and Security Act (TDPSA) — effective 2024",
            "Texas Citizens Participation Act (TCPA) — anti-SLAPP",
            "Texas Arbitration Act (TAA) — Title 7, CPRC",
        ],
        "indemnification_standard": (
            "Texas broadly enforces indemnification clauses. Anti-indemnity statute "
            "(TBCC §127.003) for oilfield/construction prohibits indemnity for sole/partial "
            "negligence of indemnitee. Liquidated damages enforced if reasonable. "
            "Comparative fault (proportionate responsibility) applies."
        ),
        "non_compete_enforceability": (
            "Texas Covenants Not to Compete Act (TBCC §15.50-15.52): enforceable if "
            "ancillary to an otherwise enforceable agreement, supported by consideration, "
            "and reasonable in time/geography/scope. Courts MUST reform overbroad provisions "
            "(mandatory reformation, not blue-pencil)."
        ),
        "arbitration_framework": (
            "Texas Arbitration Act (CPRC Ch. 171). FAA preempts for interstate commerce. "
            "Houston and Dallas are common arbitration seats. Texas courts generally "
            "pro-arbitration."
        ),
        "data_protection_law": (
            "TDPSA (2024) — consumer data privacy rights, opt-out of sale/targeted advertising, "
            "data protection assessments required. AG enforces. Identity Theft Enforcement "
            "and Protection Act for breach notification."
        ),
        "special_considerations": [
            "Mandatory reformation of overbroad non-competes (unique to Texas)",
            "Anti-indemnity statute for oilfield/construction contracts",
            "No state income tax — impacts employment contract structuring",
            "TDPSA — new comprehensive privacy law effective 2024",
            "Strong energy/oil & gas contract traditions — industry-specific terms",
            "Proportionate responsibility (comparative fault) system",
        ],
    },
    {
        "code": "EU",
        "name": "European Union",
        "display_name": "European Union",
        "legal_system": "civil_law",
        "sort_order": 16,
        "aliases": ["eu", "european union", "brussels", "european"],
        "key_statutes": [
            "General Data Protection Regulation (GDPR) — Regulation (EU) 2016/679",
            "AI Act — Regulation (EU) 2024/1689",
            "Digital Services Act (DSA) — Regulation (EU) 2022/2065",
            "Digital Markets Act (DMA) — Regulation (EU) 2022/1925",
            "NIS2 Directive — Directive (EU) 2022/2555 (network/information security)",
            "Rome I Regulation — applicable law for contractual obligations",
            "Brussels I Regulation (recast) — jurisdiction and enforcement",
        ],
        "indemnification_standard": (
            "No unified EU indemnification law — governed by applicable national law "
            "under Rome I Regulation. GDPR Art. 82 creates specific data breach liability. "
            "AI Act creates liability framework for high-risk AI systems."
        ),
        "non_compete_enforceability": (
            "Governed by national law of applicable member state. EU competition law "
            "(TFEU Art. 101) restricts anti-competitive agreements. Block exemptions "
            "for vertical agreements set limits on non-compete duration (max 5 years)."
        ),
        "arbitration_framework": (
            "No unified EU arbitration law. National arbitration laws apply. "
            "EU Court of Justice has jurisdiction over EU law questions. "
            "Rome I Regulation determines applicable law for disputes."
        ),
        "data_protection_law": (
            "GDPR — gold standard for data protection. DPAs enforce in each member state. "
            "Standard Contractual Clauses (SCCs) for international transfers. "
            "Data Protection Impact Assessments (DPIA) mandatory for high-risk processing."
        ),
        "special_considerations": [
            "GDPR — maximum fines of 4% global turnover or EUR 20M",
            "AI Act — classified risk approach, high-risk AI requires conformity assessment",
            "DSA/DMA — platform regulation with gatekeepers obligations",
            "NIS2 — mandatory cybersecurity measures and incident reporting",
            "Rome I — choice of law for contracts (mandatory rules may override party choice)",
            "Brussels I recast — jurisdiction rules, lis pendens, enforcement of judgments",
        ],
    },
    {
        "code": "AE-ADGM",
        "name": "ADGM",
        "display_name": "Abu Dhabi Global Market (ADGM), UAE",
        "legal_system": "common_law",
        "sort_order": 17,
        "aliases": ["adgm", "abu dhabi global market"],
        "key_statutes": [
            "ADGM Application of English Law Regulations 2015 — English common law applies",
            "ADGM Arbitration Regulations 2015 — based on UNCITRAL Model Law",
            "ADGM Data Protection Regulations 2021 — modeled on EU GDPR",
            "ADGM Employment Regulations 2019",
            "ADGM Companies Regulations 2020",
            "ADGM Contracts Regulations 2015",
        ],
        "indemnification_standard": (
            "English common law principles apply directly (ADGM Application of English Law "
            "Regulations). Indemnification clauses broadly enforceable. Penalty doctrine "
            "follows Cavendish v Makdessi. Separate from onshore UAE Civil Code regime."
        ),
        "non_compete_enforceability": (
            "Follows English common law restraint of trade doctrine. Must protect legitimate "
            "business interest, reasonable in scope and duration. ADGM Employment Regulations "
            "2019 govern employee-specific restrictions."
        ),
        "arbitration_framework": (
            "ADGM Arbitration Regulations 2015 (UNCITRAL Model Law). ADGM Courts have "
            "exclusive jurisdiction for ADGM entities. Enforcement through ADGM Courts "
            "and mutual enforcement arrangements with onshore Abu Dhabi courts."
        ),
        "data_protection_law": (
            "ADGM Data Protection Regulations 2021 — closely aligned with EU GDPR. "
            "Commissioner of Data Protection enforces. Adequate protections for "
            "international data transfers. Separate from onshore UAE data protection."
        ),
        "special_considerations": [
            "Common-law free zone — English law applies directly (unlike onshore UAE civil law)",
            "ADGM Courts operate independently from onshore Abu Dhabi courts",
            "Distinct from DIFC (Dubai) — different free zone, different courts",
            "ADGM Data Protection closely mirrors EU GDPR",
            "English language is the legal language (unlike onshore UAE Arabic requirement)",
            "Growing fintech and virtual assets regulatory framework",
        ],
    },
]


# ---------------------------------------------------------------------------
# Rule overrides data (migrated from jurisdiction_detector.py)
# ---------------------------------------------------------------------------

RULE_OVERRIDES_SEED_DATA: Dict[str, List[Dict]] = {
    "IN": [
        {"clause_type": "non_compete", "risk_level": "GREEN",
         "primary_position": "Non-compete clauses are void under S.27 Indian Contract Act 1872 (exception: sale of goodwill). Flag but note unenforceability.",
         "note": "S.27 Indian Contract Act renders post-employment non-competes void as restraint of trade.",
         "statute_reference": "S.27, Indian Contract Act 1872"},
        {"clause_type": "customer_non_solicitation", "risk_level": "YELLOW",
         "primary_position": "Non-solicitation clauses are generally enforceable in India if reasonable, unlike non-competes.",
         "note": "Indian courts distinguish non-solicitation from non-compete; former may survive S.27."},
        {"clause_type": "data_protection", "risk_level": "YELLOW",
         "primary_position": "Ensure compliance with DPDP Act 2023: consent-based processing, data fiduciary obligations, 72-hour breach notification to Data Protection Board.",
         "note": "Digital Personal Data Protection Act 2023 imposes data fiduciary obligations.",
         "statute_reference": "DPDP Act 2023"},
        {"clause_type": "cross_border_transfer", "risk_level": "YELLOW",
         "primary_position": "DPDP Act 2023 allows cross-border transfers except to government-notified restricted countries. No adequacy framework yet.",
         "note": "DPDP Act S.16 — Central Government may restrict transfers to specific countries.",
         "statute_reference": "S.16, DPDP Act 2023"},
        {"clause_type": "limitation_period",
         "primary_position": "Indian Limitation Act 1963: general contract claims = 3 years; specific performance = 3 years; fraud = 3 years from discovery.",
         "note": "Limitation Act 1963 provides statutory limitation periods that cannot be shortened by contract.",
         "statute_reference": "Limitation Act, 1963"},
        {"clause_type": "arbitration",
         "primary_position": "Prefer SIAC (Singapore) or ICC arbitration for international contracts. For domestic, specify Indian Arbitration and Conciliation Act 1996 (amended 2019). Seat in Mumbai/Delhi.",
         "note": "Arbitration and Conciliation Act 1996 (amended 2015, 2019, 2021).",
         "statute_reference": "Arbitration and Conciliation Act, 1996"},
        {"clause_type": "taxes_clause",
         "primary_position": "Clarify GST (18% on services), TDS obligations under Income Tax Act, and stamp duty requirements. Specify which party bears GST.",
         "note": "GST Act 2017, Income Tax Act 1961 (TDS), Indian Stamp Act 1899.",
         "statute_reference": "GST Act 2017; Income Tax Act 1961; Indian Stamp Act 1899"},
        {"clause_type": "anti_bribery",
         "primary_position": "Include Prevention of Corruption Act 1988 (amended 2018) compliance. S.9 penalizes commercial organizations for bribery by associated persons.",
         "note": "Prevention of Corruption (Amendment) Act 2018 introduced corporate liability.",
         "statute_reference": "Prevention of Corruption Act, 1988 (as amended 2018)"},
    ],
    "CA-US": [
        {"clause_type": "non_compete", "suppress": True,
         "note": "BPC §16600: California voids ALL post-employment non-competes (except narrow sale-of-business exception).",
         "statute_reference": "BPC §16600"},
        {"clause_type": "non_solicitation", "risk_level": "YELLOW",
         "primary_position": "Employee non-solicitation clauses face scrutiny in California post-AMN Healthcare (2020). Customer non-solicits may be permissible but risky.",
         "note": "AMN Healthcare v. Aya Healthcare (2020) — employee non-solicits may be unenforceable under BPC §16600.",
         "statute_reference": "BPC §16600; AMN Healthcare v. Aya Healthcare (2020)"},
        {"clause_type": "jury_waiver", "risk_level": "YELLOW",
         "primary_position": "Pre-dispute jury waivers are generally enforceable in California federal courts but face challenges in state courts.",
         "note": "Grafton Partners v. Superior Court (2005) — CA Supreme Court expressed skepticism."},
    ],
    "DE-US": [
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "Delaware enforces reasonable non-competes. Must protect legitimate economic interest. Continued employment alone is sufficient consideration.",
         "note": "Delaware Chancery Court applies reasonableness test; relatively employer-friendly."},
        {"clause_type": "governing_law", "risk_level": "GREEN",
         "primary_position": "Delaware choice of law is widely accepted. DGCL §145 provides broad indemnification rights for officers/directors.",
         "note": "Delaware is the preferred jurisdiction for corporate governance matters.",
         "statute_reference": "DGCL §145"},
    ],
    "NY-US": [
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "New York applies strict reasonableness test for non-competes: (1) necessary to protect legitimate interest, (2) not unreasonably burdensome, (3) not harmful to public.",
         "note": "NY courts scrutinize non-competes carefully. Blue-pencil doctrine allows courts to modify."},
        {"clause_type": "governing_law", "risk_level": "GREEN",
         "primary_position": "GOL §5-1401 permits NY choice of law for contracts >$250K. GOL §5-1402 permits NY jurisdiction for contracts >$1M.",
         "note": "General Obligations Law §5-1401 and §5-1402 facilitate NY choice of law/forum.",
         "statute_reference": "NY GOL §5-1401, §5-1402"},
    ],
    "GB-EW": [
        {"clause_type": "unlimited_liability", "risk_level": "RED",
         "primary_position": "UCTA S.2(1) prohibits excluding liability for death/personal injury from negligence. S.2(2) subjects other negligence exclusions to reasonableness test.",
         "note": "Unfair Contract Terms Act 1977 — key statutory restriction on exclusion clauses.",
         "statute_reference": "UCTA 1977, S.2"},
        {"clause_type": "consequential_damages",
         "primary_position": "Consequential damages exclusions enforceable if reasonable under UCTA. Cavendish v Makdessi [2015] UKSC 67 — penalty rule.",
         "note": "Cavendish/Makdessi replaced the old 'genuine pre-estimate' test."},
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "English law enforces reasonable restraints. Must protect legitimate business interest. Garden leave clauses commonly used.",
         "note": "English courts will not rewrite — sever or void entirely."},
    ],
    "SG": [
        {"clause_type": "data_protection",
         "primary_position": "Comply with PDPA 2012 (amended 2020/2021). Mandatory breach notification within 3 business days to PDPC if significant.",
         "note": "PDPA mandatory breach notification since Feb 2021.",
         "statute_reference": "PDPA 2012 (amended 2020/2021)"},
        {"clause_type": "arbitration",
         "primary_position": "SIAC arbitration recommended — globally recognized, efficient. International Arbitration Act (Cap. 143A) adopts UNCITRAL Model Law.",
         "note": "Singapore is a premier arbitration hub; SIAC widely used for APAC disputes.",
         "statute_reference": "International Arbitration Act (Cap. 143A)"},
    ],
    "DE": [
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "Post-employment non-competes require Karenzentschadigung (minimum 50% of last remuneration) under HGB §74-75a.",
         "note": "HGB §74-75a — mandatory compensation for employee non-competes.",
         "statute_reference": "HGB §74-75a"},
        {"clause_type": "unlimited_liability", "risk_level": "RED",
         "primary_position": "AGB control (BGB §305-310) prohibits excluding liability for intent or gross negligence in standard terms.",
         "note": "BGB §305-310 — strict AGB (standard terms) control in B2B.",
         "statute_reference": "BGB §305-310"},
        {"clause_type": "consequential_damages",
         "primary_position": "Under AGB control, exclusion of consequential damages for intent/gross negligence is void.",
         "note": "Distinguish between AGB (standard terms) and individually negotiated terms."},
    ],
    "FR": [
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "Employment non-competes require financial compensation (jurisprudence constante). Must be limited in time, geography, and activity.",
         "note": "French courts void non-competes without compensation (Cass. soc., 10 July 2002)."},
        {"clause_type": "consequential_damages",
         "primary_position": "Art. 1231-5 Code Civil allows courts to increase or reduce liquidated damages (clause penale).",
         "note": "Art. 1104 good faith obligation cannot be contracted out of.",
         "statute_reference": "Art. 1104, Art. 1231-5, Code Civil"},
    ],
    "AU": [
        {"clause_type": "unlimited_liability",
         "primary_position": "ACL consumer guarantees cannot be excluded. Proportionate liability regimes in most states reduce joint liability.",
         "note": "Australian Consumer Law — unfair contract terms provisions apply to small business."},
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "Restraint of trade doctrine applies — use cascading restraint clauses (standard Australian practice).",
         "note": "Cascading restraints allow courts to enforce the most reasonable alternative."},
    ],
    # ======== NEW JURISDICTION OVERRIDES (Sprint 3) ========
    "US": [
        {"clause_type": "non_compete",
         "primary_position": "FTC proposed non-compete ban (status uncertain). Currently governed by state law. DTSA provides federal trade secret protection as alternative.",
         "note": "Federal non-compete regulation in flux; defer to applicable state law.",
         "statute_reference": "DTSA (18 U.S.C. §§1836-1839)"},
        {"clause_type": "anti_bribery", "risk_level": "RED",
         "primary_position": "FCPA prohibits bribing foreign officials. Strict liability for issuers and domestic concerns. Extraterritorial reach.",
         "note": "Foreign Corrupt Practices Act — severe penalties (criminal + civil).",
         "statute_reference": "FCPA (15 U.S.C. §§78dd-1 to 78dd-3)"},
        {"clause_type": "data_protection", "risk_level": "YELLOW",
         "primary_position": "No comprehensive federal privacy law. Sector-specific: HIPAA, GLBA, COPPA, FERPA. CLOUD Act governs cross-border data access.",
         "note": "Patchwork federal privacy — identify which sector-specific laws apply.",
         "statute_reference": "HIPAA; GLBA; COPPA; CLOUD Act"},
    ],
    "TX-US": [
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "Texas Covenants Not to Compete Act (TBCC §15.50-15.52): enforceable if ancillary, supported by consideration, and reasonable. Courts MUST reform (not void) overbroad provisions.",
         "note": "Mandatory reformation unique to Texas — courts rewrite rather than void.",
         "statute_reference": "TBCC §15.50-15.52"},
        {"clause_type": "indemnification",
         "primary_position": "Texas anti-indemnity statute (TBCC §127.003) for oilfield/construction prohibits indemnity for sole/partial negligence of indemnitee.",
         "note": "Industry-specific anti-indemnity — check if contract involves oilfield/construction.",
         "statute_reference": "TBCC §127.003"},
    ],
    "EU": [
        {"clause_type": "data_protection", "risk_level": "RED",
         "primary_position": "GDPR compliance mandatory. Include DPA, SCCs for international transfers, DPIA for high-risk processing. Maximum fines: 4% global turnover or EUR 20M.",
         "note": "GDPR is the strictest data protection regime globally.",
         "statute_reference": "GDPR Art. 82, Art. 83"},
        {"clause_type": "ai_clause", "risk_level": "YELLOW",
         "primary_position": "EU AI Act (2024) classifies AI by risk. High-risk AI systems require conformity assessment. Prohibited practices include social scoring and real-time biometric ID.",
         "note": "AI Act — check if contract involves AI systems and applicable risk classification.",
         "statute_reference": "AI Act — Regulation (EU) 2024/1689"},
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "EU competition law (TFEU Art. 101) restricts anti-competitive agreements. Vertical block exemption limits non-competes to max 5 years.",
         "note": "EU-wide competition rules may apply alongside national non-compete laws.",
         "statute_reference": "TFEU Art. 101; Vertical Block Exemption Regulation"},
    ],
    "AE-ADGM": [
        {"clause_type": "data_protection", "risk_level": "YELLOW",
         "primary_position": "ADGM Data Protection Regulations 2021 closely mirror GDPR. Include data processing provisions, international transfer safeguards.",
         "note": "ADGM DP Regulations separate from onshore UAE data protection law.",
         "statute_reference": "ADGM Data Protection Regulations 2021"},
        {"clause_type": "non_compete", "risk_level": "YELLOW",
         "primary_position": "English common law restraint of trade doctrine applies in ADGM. Must protect legitimate business interest, reasonable scope/duration.",
         "note": "ADGM follows English common law directly via Application of English Law Regulations."},
    ],
}


async def seed_jurisdictions(db: AsyncSession) -> int:
    """Seed jurisdiction profiles and rule overrides. Returns count of jurisdictions seeded."""
    seeded = 0

    for jdata in JURISDICTION_SEED_DATA:
        # Check if already exists
        result = await db.execute(
            select(Jurisdiction).where(Jurisdiction.code == jdata["code"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            continue

        jurisdiction = Jurisdiction(
            code=jdata["code"],
            name=jdata["name"],
            display_name=jdata["display_name"],
            legal_system=jdata["legal_system"],
            sort_order=jdata.get("sort_order", 0),
            aliases=jdata.get("aliases"),
            key_statutes=jdata.get("key_statutes"),
            special_considerations=jdata.get("special_considerations"),
            indemnification_standard=jdata.get("indemnification_standard"),
            non_compete_enforceability=jdata.get("non_compete_enforceability"),
            arbitration_framework=jdata.get("arbitration_framework"),
            data_protection_law=jdata.get("data_protection_law"),
            parent_code=jdata.get("parent_code"),
        )
        db.add(jurisdiction)
        await db.flush()

        # Seed rule overrides for this jurisdiction
        overrides = RULE_OVERRIDES_SEED_DATA.get(jdata["code"], [])
        for ov_data in overrides:
            override = JurisdictionRuleOverride(
                jurisdiction_id=jurisdiction.id,
                clause_type=ov_data["clause_type"],
                risk_level=ov_data.get("risk_level"),
                suppress=ov_data.get("suppress", False),
                primary_position=ov_data.get("primary_position"),
                note=ov_data.get("note"),
                statute_reference=ov_data.get("statute_reference"),
            )
            db.add(override)

        seeded += 1
        logger.info("Seeded jurisdiction: %s (%s)", jdata["code"], jdata["name"])

    if seeded:
        await db.flush()
    return seeded


async def main():
    """CLI entry point for seeding jurisdictions."""
    import sys
    sys.path.insert(0, ".")

    from app.db.session import AsyncSessionLocal

    logging.basicConfig(level=logging.INFO)

    async with AsyncSessionLocal() as db:
        count = await seed_jurisdictions(db)
        await db.commit()
        print(f"Seeded {count} jurisdictions.")


if __name__ == "__main__":
    asyncio.run(main())
