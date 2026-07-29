"""
DPDP Act Knowledge Base - Structured regulatory reference for agent grounding.

Provides section-level retrieval of verified summaries of the DPDP Act 2023
and DPDP Rules 2025. These are grounding aids, not verbatim statutory text;
legal output must cite and verify the official Gazette.

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
    full_text: str                 # Verified structured paraphrase, not a quotation
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
        summary="A consent request must be accompanied or preceded by the required notice",
        full_text="""Section 5 - Notice:
(1) Every consent request under section 6 must be accompanied or preceded by a notice informing the Data Principal of:
(a) the personal data and the purpose for which the same is proposed to be processed;
(b) the manner in which the Data Principal may withdraw consent and use grievance redressal;
(c) the manner in which the Data Principal may make a complaint to the Board.

(2) For consent given before commencement, the Data Fiduciary must provide the corresponding notice as soon as reasonably practicable.

(3) The Data Principal must have the option to access the notice in English or any Eighth Schedule language.""",
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
(1) Consent must be free, specific, informed, unconditional and unambiguous, use clear affirmative action, relate to a specified purpose, and be limited to necessary personal data.

(2) A term of consent that infringes the Act, Rules, or another law is invalid to that extent.

(3) The request must use clear and plain language, offer English or an Eighth Schedule language, and provide the applicable privacy contact.

(4) Where consent given by the Data Principal is the basis of processing of personal data, such Data Principal shall have the right to withdraw her consent at any time, with the ease of doing so being comparable to the ease with which such consent was given.

(5) The withdrawal of consent shall not affect the lawfulness of processing of personal data based on consent before its withdrawal.

(6) After withdrawal, the Data Fiduciary must within a reasonable time cease and cause processors to cease consent-based processing, unless processing without consent is authorised by the DPDP framework or another Indian law.

(7)-(9) A Data Principal may manage consent through a registered Consent Manager, which acts on her behalf and is accountable to her.

(10) If consent is disputed in a proceeding, the Data Fiduciary must prove compliant notice and consent.""",
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
(1) The Data Fiduciary remains responsible for processing by it or on its behalf, irrespective of contrary agreements.

(2) A Data Processor may be engaged for offering goods or services only under a valid contract.

(3) Completeness, accuracy, and consistency are required when data is used for a decision affecting the Data Principal or disclosed to another Data Fiduciary.

(4) Appropriate technical and organisational measures must support effective observance.

(5) Reasonable security safeguards must protect personal data in the Data Fiduciary's possession or control, including processor activity.

(6) A personal data breach must be intimated to the Board and each affected Data Principal in the prescribed manner.

(7) Personal data and processor copies must be erased on consent withdrawal or when the specified purpose is no longer served, unless retention is necessary under law.

(9) The applicable DPO or privacy-contact information must be published.

(10) An effective grievance-redressal mechanism must be established.""",
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
(1)-(2) For covered processing, a Data Principal may request correction of inaccurate or misleading data, completion of incomplete data, and updating; the Data Fiduciary must carry out those actions.

(3) On an erasure request, the Data Fiduciary must erase the personal data unless retention is necessary for the specified purpose or compliance with law.""",
        keywords=["correction", "erasure", "deletion", "right to be forgotten", "inaccurate", "incomplete", "updating"],
        related_sections=["11", "8"],
    ),
    RegulatorySection(
        source="DPDP Act 2023",
        section_number="13",
        title="Right to Grievance Redressal",
        summary="Readily available grievance redressal must be exhausted before approaching the Board",
        full_text="""Section 13 - Grievance Redressal:
(1) A Data Principal has the right to readily available grievance redressal concerning a Data Fiduciary's or Consent Manager's obligations and her rights.
(2) The Data Fiduciary or Consent Manager must respond within the prescribed period.
(3) The Data Principal must exhaust this grievance opportunity before approaching the Board.""",
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
        summary="Transfers may be restricted by Government notification and remain subject to stricter Indian laws",
        full_text="""Section 16 - Transfer of Personal Data Outside India:
(1) The Central Government may, by notification, restrict transfer of personal data for processing to a notified country or territory.

(2) Indian laws that provide a higher degree of protection or restriction continue to apply.
Rule 15 also permits Government-specified requirements concerning availability of transferred data to a foreign State, or persons or entities under its control.
Always check current notifications; a static knowledge base must not assert that no restrictions exist.""",
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
        summary="Standalone, clear notice with itemised data, purposes, and rights links",
        full_text="""Rule 3 - Notice and Consent:
The notice must be understandable independently of other information and use clear, plain language.
- Itemise the personal data and each specified processing purpose
- Describe the goods, services, or uses enabled by the processing
- Provide a communication link or other means for consent withdrawal, exercise of rights, and complaint to the Board
- The Act separately requires free, specific, informed, unconditional and unambiguous consent through clear affirmative action
- Separate purpose controls are a sound implementation pattern, but the Rules do not mandate a particular checkbox or 'privacy center' interface""",
        keywords=["notice", "consent", "purpose", "affirmative action", "withdrawal", "rights"],
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
        summary="Minimum technical, organisational, logging, resilience, and processor-contract safeguards",
        full_text="""Rule 6 - Reasonable Security Safeguards:
At a minimum, a Data Fiduciary must:
1. Use appropriate data-security measures such as encryption, obfuscation, masking, or virtual tokens
2. Control access to relevant computer resources
3. Maintain visibility through appropriate logs, monitoring, and review
4. Take reasonable continuity measures, such as backups
5. Retain relevant logs and personal data for one year for detection, investigation, remediation, recurrence prevention, and continuity, unless another law requires otherwise
6. Put appropriate security-safeguard provisions in processor contracts
7. Maintain appropriate technical and organisational measures""",
        keywords=["security", "encryption", "access control", "audit log", "backup", "vendor", "processor"],
        penalties="Up to Rs 250 Crore",
        deadline="May 13, 2027",
    ),
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 7",
        title="Breach Notification",
        summary="Initial Board and affected-principal notices without delay; detailed Board report within 72 hours",
        full_text="""Rule 7 - Personal Data Breach:
- Notify each affected Data Principal without delay, using her account or registered communication channel
- Notify the Board without delay with the nature, extent, timing, location, and likely impact
- Supply the updated detailed Board report within 72 hours, unless the Board grants more time on written request
- The detailed report covers events and reasons, mitigation, findings about the person responsible, recurrence prevention, and principal-notification status
- The final rule does not state a risk threshold that excuses notification""",
        keywords=["breach", "notification", "72 hours", "without delay", "data protection board"],
        related_sections=["Rule 6"],
        penalties="Up to Rs 200 Crore",
        deadline="May 13, 2027",
    ),
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 8",
        title="Data Erasure",
        summary="Scheduled inactivity erasure for specified large platforms plus one-year processing records",
        full_text="""Rule 8 - Erasure of Personal Data:
- The Act separately requires erasure on consent withdrawal or when the specified purpose is no longer served, unless retention is legally necessary
- Rule 8's inactivity periods and 48-hour warning apply to the classes and purposes listed in the Third Schedule, not universally
- Rule 8 also requires one-year retention of specified processing data, traffic data, and logs for the Seventh Schedule purposes, unless another law requires longer retention
- Processor erasure remains the Data Fiduciary's responsibility under section 8(7) of the Act""",
        keywords=["erasure", "deletion", "48 hours", "automated", "cascade", "processor", "retention"],
        deadline="May 13, 2027",
    ),
    RegulatorySection(
        source="DPDP Rules 2025",
        section_number="Rule 10",
        title="Children's Data",
        summary="Verifiable parental consent using reliable age and identity details, subject to notified exemptions",
        full_text="""Rules 10-11 - Children's Data:
- Verifiable parental consent required before processing any child's personal data
- Use reliable identity and age details, or details/virtual tokens issued by an authorised entity; DigiLocker is one permitted route
- The Act prohibits tracking or behavioural monitoring of children and targeted advertising directed at children
- Rule 12 and the Fourth Schedule contain class-, purpose-, and condition-specific exemptions; do not assume a blanket safety exception
- Under the Act, a child is an individual below eighteen years""",
        keywords=["children", "under 18", "parental consent", "age verification", "DigiLocker", "tracking"],
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
