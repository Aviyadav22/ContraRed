"""
DPDP Act Knowledge Base - Structured regulatory reference for agent grounding.

Provides section-level retrieval of DPDP Act 2023 and DPDP Rules 2025 text.
Used by agents to ground their AI responses in actual regulatory provisions,
reducing hallucination and enabling citation in compliance reports.

This is a lightweight in-memory knowledge base (no external vector DB needed).
Keyword + section-based retrieval is sufficient for regulatory text where
sections are well-structured and numbered.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RegulatorySection:
    """A section of regulatory text with metadata."""
    source: str                    # "DPDP Act 2023" or "DPDP Rules 2025"
    section_number: str            # "6", "8(6)", "Rule 3"
    title: str
    summary: str                   # One-line summary
    full_text: str                 # Full section text
    keywords: List[str] = field(default_factory=list)
    related_sections: List[str] = field(default_factory=list)
    penalties: Optional[str] = None
    deadline: Optional[str] = None


# ============================================================
# DPDP Act 2023 - Key Sections
# ============================================================

DPDP_ACT_SECTIONS: List[RegulatorySection] = [
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="5",
        title="Notice",
        summary="Data Fiduciary must give notice before or at the time of collecting personal data",
        full_text="""Section 5 - Notice:
(1) Every Data Fiduciary shall, before or at the time of collection of personal data, give to the Data Principal an itemised notice in clear and plain language containing:
(a) the personal data and the purpose for which the same is proposed to be processed;
(b) the manner in which the Data Principal may exercise rights under this Act;
(c) the manner in which the Data Principal may make a complaint to the Board.

(2) Where personal data is collected from a Data Principal before the commencement of this Act, the Data Fiduciary shall give notice as soon as reasonably practicable.

(3) The notice shall be available in English or any language specified in the Eighth Schedule to the Constitution.""",
        keywords=["notice", "collection", "itemised", "plain language", "purpose", "rights"],
        related_sections=["6", "11"],
        penalties="Up to Rs 50 Crore for non-compliance",
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="6",
        title="Consent",
        summary="Consent must be free, specific, informed, unconditional, and unambiguous with clear affirmative action",
        full_text="""Section 6 - Consent:
(1) Consent given by the Data Principal shall be free, specific, informed, unconditional and unambiguous with a clear affirmative action, signifying an agreement to the processing of her personal data for the specified purpose.

(2) Consent shall be limited to such personal data as is necessary for the specified purpose.

(3) Every request for consent shall be presented to the Data Principal in a clear and plain language with an itemised description of the personal data and the purpose of processing.

(4) Where consent given by the Data Principal is the basis of processing of personal data, such Data Principal shall have the right to withdraw her consent at any time, with the ease of doing so being comparable to the ease with which such consent was given.

(5) The withdrawal of consent shall not affect the lawfulness of processing of personal data based on consent before its withdrawal.

(6) If the Data Principal withdraws her consent to the processing of personal data, the Data Fiduciary shall, unless retention is required under any law, cease and cause its Data Processors to cease processing the personal data of such Data Principal within a reasonable time.

(7) Consent given by the Data Principal to a Consent Manager shall be deemed to be consent given to the Data Fiduciary.""",
        keywords=["consent", "free", "specific", "informed", "unconditional", "unambiguous", "withdrawal", "cease processing", "consent manager"],
        related_sections=["5", "7"],
        penalties="Up to Rs 50 Crore for non-compliance",
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="7",
        title="Certain Legitimate Uses",
        summary="Processing without consent for specified legitimate purposes (employment, State functions, legal obligations, etc.)",
        full_text="""Section 7 - Certain Legitimate Uses:
A Data Fiduciary may process personal data of a Data Principal for any of the following uses, without consent:
(a) for the specified purpose for which the Data Principal has voluntarily provided personal data and has not indicated that she does not consent;
(b) for the State or any instrumentality of the State to provide any subsidy, benefit, service, certificate, licence or permit;
(c) for purposes related to sovereignty and integrity of India, security of the State, friendly relations with foreign States, maintenance of public order;
(d) for compliance with any judgment or order issued under any law;
(e) for responding to a medical emergency involving a threat to life or immediate threat to health;
(f) for taking measures relating to safety during any disaster or breakdown of public order;
(g) for purposes related to employment.""",
        keywords=["legitimate use", "without consent", "employment", "state", "medical emergency", "public order", "voluntary"],
        related_sections=["6"],
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="8",
        title="Obligations of Data Fiduciary",
        summary="Data Fiduciaries must ensure accuracy, security, erasure after purpose fulfilled, and grievance redressal",
        full_text="""Section 8 - General Obligations of Data Fiduciary:
(1) A Data Fiduciary shall make reasonable efforts to ensure completeness, accuracy and consistency of personal data.

(3) A Data Fiduciary shall implement appropriate technical and organisational measures to ensure effective observance of the provisions of this Act.

(4) A Data Fiduciary shall protect personal data in its possession or under its control by taking reasonable security safeguards to prevent personal data breach.

(5) In the event of a personal data breach, the Data Fiduciary shall give the Board and each affected Data Principal, intimation of such breach in such form and manner as may be prescribed.

(6) When personal data is no longer needed for the purpose for which it was collected, or the Data Principal withdraws consent, the Data Fiduciary shall erase such data, unless retention is required under any law.

(7) The Data Fiduciary shall publish the business contact information of a Data Protection Officer or such other person who is able to answer on behalf of the Data Fiduciary, the questions of the Data Principal about the processing of her personal data.

(8) The Data Fiduciary shall establish an effective mechanism to redress the grievances of Data Principals.""",
        keywords=["security safeguards", "data breach", "erasure", "accuracy", "grievance redressal", "data protection officer"],
        related_sections=["9", "10", "13"],
        penalties="Up to Rs 250 Crore for security failures, Rs 200 Crore for breach notification failures",
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="9",
        title="Processing of Personal Data of Children",
        summary="Verifiable parental consent required for processing data of persons under 18; no tracking or targeted advertising",
        full_text="""Section 9 - Processing of Personal Data of Children:
(1) Before processing any personal data of a child, a Data Fiduciary shall obtain verifiable consent of the parent or lawful guardian of the child.

(2) A Data Fiduciary shall not undertake such processing of personal data that is likely to cause any detrimental effect on the well-being of a child.

(3) A Data Fiduciary shall not undertake tracking or behavioural monitoring of children or targeted advertising directed at children.

Note: "Child" means an individual who has not completed the age of eighteen years.""",
        keywords=["children", "child", "minor", "under 18", "parental consent", "verifiable consent", "tracking", "targeted advertising", "behavioural monitoring"],
        related_sections=["6"],
        penalties="Up to Rs 200 Crore",
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="10",
        title="Significant Data Fiduciary",
        summary="Central Government may designate SDFs who must appoint DPO, conduct DPIAs, and undergo audits",
        full_text="""Section 10 - Additional Obligations of Significant Data Fiduciary:
(1) The Central Government may, having regard to the volume and sensitivity of personal data processed, risk of harm to the Data Principal, potential impact on sovereignty and integrity of India, risk to electoral democracy, security of the State, and public order, notify any Data Fiduciary or class of Data Fiduciaries as Significant Data Fiduciary.

(2) A Significant Data Fiduciary shall:
(a) appoint a Data Protection Officer based in India;
(b) appoint an independent data auditor to carry out data audit;
(c) undertake Data Protection Impact Assessment;
(d) undertake periodic audit of its policies and practices;
(e) undertake such other measures consistent with the provisions of this Act.""",
        keywords=["significant data fiduciary", "SDF", "DPO", "data protection officer", "DPIA", "data audit", "impact assessment"],
        related_sections=["8"],
        penalties="Up to Rs 150 Crore for SDF non-compliance",
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="11",
        title="Right to Access Information About Personal Data",
        summary="Data Principals have the right to obtain summary of personal data being processed and processing activities",
        full_text="""Section 11 - Rights of Data Principal:
(1) The Data Principal shall have the right to obtain from the Data Fiduciary:
(a) a summary of personal data that is being processed by such Data Fiduciary and the processing activities undertaken by that Data Fiduciary with respect to such personal data;
(b) the identities of all other Data Fiduciaries and Data Processors with whom the personal data has been shared by the Data Fiduciary, along with a description of the personal data so shared;
(c) any other information related to the personal data of such Data Principal and its processing, as may be prescribed.""",
        keywords=["right to access", "summary", "personal data", "processing activities", "data principal rights"],
        related_sections=["12", "13", "14"],
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="12",
        title="Right to Correction and Erasure",
        summary="Data Principals can request correction of inaccurate data and erasure of data no longer needed",
        full_text="""Section 12 - Right to Correction and Erasure of Personal Data:
(1) The Data Principal shall have the right to correction of inaccurate or misleading personal data, completion of incomplete personal data, updating of personal data, and erasure of personal data unless retention of personal data is necessary for a specified purpose or for compliance with any law in force.""",
        keywords=["correction", "erasure", "deletion", "right to be forgotten", "inaccurate", "incomplete", "updating"],
        related_sections=["11", "8"],
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="13",
        title="Right to Grievance Redressal",
        summary="Data Principals can file grievances with the Data Fiduciary and escalate to the Board",
        full_text="""Section 13 - Grievance Redressal:
(1) A Data Principal who is not satisfied with the response of the Data Fiduciary to any grievance raised, may register a complaint with the Board in such manner and having such particulars as may be prescribed.""",
        keywords=["grievance", "complaint", "redressal", "data protection board", "escalation"],
        related_sections=["8", "14"],
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="14",
        title="Right of Nomination",
        summary="Data Principal may nominate any individual to exercise rights in the event of death or incapacity",
        full_text="""Section 14 - Nomination:
(1) The Data Principal shall have the right to nominate any other individual, who shall, in the event of death or incapacity of the Data Principal, exercise the rights of the Data Principal in accordance with the provisions of this Act.""",
        keywords=["nomination", "nominee", "death", "incapacity", "representative", "authorized"],
        related_sections=["11", "12", "13"],
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="16",
        title="Transfer of Personal Data Outside India",
        summary="Central Government may restrict transfer to notified countries (negative list approach)",
        full_text="""Section 16 - Transfer of Personal Data Outside India:
(1) The Central Government may, after an assessment of such factors as it may consider necessary, notify such countries or territories outside India to which a Data Fiduciary may transfer personal data, in accordance with such terms and conditions as may be specified.

Note: India uses a "negative list" approach — all transfers are permitted unless to countries specifically restricted by government notification. No restricted country list has been published as of April 2026.""",
        keywords=["cross-border", "transfer", "outside India", "negative list", "restricted countries", "data localization"],
        related_sections=["8"],
    ),
]

# ============================================================
# DPDP Rules 2025 - Key Rules
# ============================================================

DPDP_RULES_SECTIONS: List[RegulatorySection] = [
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 3",
        title="Consent and Notice",
        summary="Individual checkboxes per purpose, no pre-population, privacy center mandatory",
        full_text="""Rule 3 - Notice and Consent:
Every Data Fiduciary must deploy DPDP-compliant consent/privacy notices at all data collection touchpoints.
- Notices must be in clear, vernacular language stating what data is collected and why
- Individual checkboxes or toggles required for each processing purpose
- Pre-population of consent fields is prohibited
- A "privacy center" enabling consent withdrawal and complaint submission is mandatory
- Consent must be refreshed if purposes change""",
        keywords=["notice", "consent", "checkbox", "toggle", "privacy center", "withdrawal", "pre-population"],
        related_sections=["Rule 4"],
        deadline="May 13, 2027",
    ),
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 4",
        title="Consent Managers",
        summary="Registered intermediaries enabling citizens to manage consent across all Data Fiduciaries",
        full_text="""Rule 4 - Consent Managers:
Consent Managers are registered entities enabling Data Principals to manage consent across Data Fiduciaries.
- Must be incorporated in India with minimum Rs 2 Crore net worth
- Must maintain interoperable platform accessible to Data Principals
- Must ensure personal data remains unreadable to the Consent Manager itself
- Must retain consent records for at least 7 years
- Cannot subcontract performance of obligations
- Board can suspend or cancel registration""",
        keywords=["consent manager", "registered", "interoperable", "7 years", "net worth", "Rs 2 crore"],
        related_sections=["Rule 3"],
        deadline="November 13, 2026",
    ),
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 6",
        title="Security Safeguards",
        summary="Six mandatory security measures including encryption, access controls, audit logs, backups",
        full_text="""Rule 6 - Reasonable Security Safeguards:
Six mandatory security safeguards:
1. Encrypt personal data at rest and in transit
2. Implement access controls and authentication
3. Maintain audit logs of all data access and processing
4. Create regular data backups
5. Retain breach records for at least one year
6. Mandate equivalent security in all vendor/processor contracts""",
        keywords=["security", "encryption", "access control", "audit log", "backup", "vendor", "processor"],
        penalties="Up to Rs 250 Crore",
        deadline="May 13, 2027",
    ),
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 7",
        title="Breach Notification",
        summary="Notify Board within 72 hours AND affected Data Principals immediately for ALL breaches",
        full_text="""Rule 7 - Personal Data Breach:
- Notify the Data Protection Board within 72 hours of detecting a breach
- Notify affected Data Principals immediately with impact details and mitigation steps
- Unlike GDPR, ALL personal data breaches must be reported regardless of risk assessment
- Must include: nature of breach, categories of data affected, approximate number of Data Principals affected, measures taken""",
        keywords=["breach", "notification", "72 hours", "data protection board", "immediate", "all breaches"],
        related_sections=["Rule 6"],
        penalties="Up to Rs 200 Crore",
        deadline="May 13, 2027",
    ),
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 8",
        title="Data Erasure",
        summary="Automated deletion with 48-hour pre-deletion notification to Data Principals",
        full_text="""Rule 8 - Erasure of Personal Data:
- Data must be erased when the purpose is fulfilled or consent is withdrawn
- Automated deletion workflows are required
- 48-hour user warning before automated deletion
- Data Fiduciaries must maintain complete data logs for a minimum of one year
- Must cascade deletion to all Data Processors""",
        keywords=["erasure", "deletion", "48 hours", "automated", "cascade", "processor", "retention"],
        deadline="May 13, 2027",
    ),
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 10",
        title="Children's Data",
        summary="Verifiable parental consent for under-18, age verification mandatory, no profiling of children",
        full_text="""Rules 10-11 - Children's Data:
- Verifiable parental consent required before processing any child's personal data
- Age verification is mandatory before processing
- Verification methods: DigiLocker Age Token, existing parent account, government-authorized identity services
- Prohibited: tracking/behavioral monitoring of children, targeted advertising, profiling
- Exception: real-time tracking for safety without separate consent
- Child = under 18 years (stricter than GDPR's 13-16)""",
        keywords=["children", "under 18", "parental consent", "age verification", "DigiLocker", "profiling", "tracking"],
        penalties="Up to Rs 200 Crore",
        deadline="May 13, 2027",
    ),
]


class DPDPKnowledgeBase:
    """In-memory knowledge base for DPDP Act and Rules.

    Provides keyword-based and section-based retrieval for agent grounding.
    """

    def __init__(self):
        self._sections: List[RegulatorySection] = DPDP_ACT_SECTIONS + DPDP_RULES_SECTIONS
        self._by_number: Dict[str, RegulatorySection] = {
            s.section_number: s for s in self._sections
        }

    def get_section(self, section_number: str) -> Optional[RegulatorySection]:
        """Get a specific section by number (e.g. '6', 'Rule 3')."""
        return self._by_number.get(section_number)

    def search(self, query: str, max_results: int = 5) -> List[RegulatorySection]:
        """Search for relevant sections using keyword matching.

        Scores each section based on keyword overlap with the query.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for section in self._sections:
            score = 0
            # Title match (highest weight)
            if query_lower in section.title.lower():
                score += 10
            # Summary match
            if query_lower in section.summary.lower():
                score += 5
            # Keyword matches
            for kw in section.keywords:
                if kw.lower() in query_lower:
                    score += 3
                elif any(w in kw.lower() for w in query_words):
                    score += 1
            # Full text match
            if query_lower in section.full_text.lower():
                score += 2

            if score > 0:
                scored.append((score, section))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_results]]

    def get_context_for_rule(self, rule_id: str) -> str:
        """Get regulatory context text for a compliance rule.

        Used by agents to ground their responses with citations.
        """
        # Map rule IDs to DPDP sections
        rule_to_sections = {
            "dpdp_consent_mechanism": ["6", "Rule 3"],
            "dpdp_consent_withdrawal": ["6", "Rule 3"],
            "dpdp_consent_manager": ["6", "Rule 4"],
            "dpdp_notice_requirements": ["5", "Rule 3"],
            "dpdp_data_principal_rights": ["11", "12", "13", "14"],
            "dpdp_breach_notification": ["8", "Rule 7"],
            "dpdp_cross_border_transfer": ["16"],
            "dpdp_childrens_data": ["9", "Rule 10"],
            "dpdp_significant_fiduciary": ["10"],
            "dpdp_purpose_limitation": ["6"],
            "dpdp_data_retention": ["8", "Rule 8"],
            "dpdp_security_safeguards": ["8", "Rule 6"],
            "dpdp_grievance_officer": ["8", "13"],
            "dpdp_data_accuracy": ["8"],
            "dpdp_lawful_purpose": ["7"],
            "dpdp_data_principal_duties": [],
        }

        section_numbers = rule_to_sections.get(rule_id, [])
        if not section_numbers:
            return ""

        parts = []
        for num in section_numbers:
            section = self._by_number.get(num)
            if section:
                parts.append(f"[{section.source} {section.section_number}] {section.title}:\n{section.full_text}")
                if section.penalties:
                    parts.append(f"Penalty: {section.penalties}")
                if section.deadline:
                    parts.append(f"Deadline: {section.deadline}")

        return "\n\n".join(parts)

    def get_all_deadlines(self) -> List[Dict]:
        """Get all regulatory deadlines from the knowledge base."""
        deadlines = []
        for section in self._sections:
            if section.deadline:
                deadlines.append({
                    "source": section.source,
                    "section": section.section_number,
                    "title": section.title,
                    "deadline": section.deadline,
                })
        return deadlines

    def get_penalty_summary(self) -> List[Dict]:
        """Get all penalty provisions."""
        penalties = []
        for section in self._sections:
            if section.penalties:
                penalties.append({
                    "source": section.source,
                    "section": section.section_number,
                    "title": section.title,
                    "penalty": section.penalties,
                })
        return penalties


# Singleton
dpdp_knowledge_base = DPDPKnowledgeBase()
