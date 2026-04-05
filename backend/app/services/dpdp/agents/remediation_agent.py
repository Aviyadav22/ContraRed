"""
DPDP Remediation Agent — AI-generated compliant content.

Generates:
  - DPDP-compliant contract clauses
  - Data Processing Agreements (DPAs)
  - Privacy notices (Section 5)
  - Consent collection templates
  - Breach notification templates (DPB + data principals + CERT-In)
  - Policy update recommendations

All output in English + Hindi (DPDP requirement).
"""

import json
import logging
from datetime import datetime

from app.services.dpdp.models import (
    RemediationRequest,
    RemediationOutput,
    RemediationType,
    DPDPSection,
    BreachNotificationInput,
    BreachNotification,
)

logger = logging.getLogger(__name__)


# Pre-built templates for deterministic fallback (no AI needed)
_TEMPLATES = {
    RemediationType.PRIVACY_NOTICE: {
        "title": "Privacy Notice — DPDP Act 2023 Compliant",
        "sections": [
            {
                "heading": "1. Data Fiduciary Information",
                "content": "{{COMPANY_NAME}} (\"we\", \"us\", \"our\"), registered at {{ADDRESS}}, is the Data Fiduciary responsible for your personal data under the Digital Personal Data Protection Act, 2023.",
            },
            {
                "heading": "2. Personal Data We Collect",
                "content": "We collect and process the following categories of personal data:\n- Identity data (name, email, phone number)\n- Account data (login credentials, preferences)\n- Usage data (service interactions, logs)\n- Payment data (billing information, transaction history)\n\nWe process this data only for the specific purposes described below.",
            },
            {
                "heading": "3. Purpose of Processing",
                "content": "We process your personal data for the following purposes:\n{{PURPOSE_LIST}}\n\nWe will not process your data for any purpose other than those stated above without obtaining fresh consent.",
            },
            {
                "heading": "4. Consent",
                "content": "We collect your consent for each processing purpose individually. You may:\n- Grant or deny consent for each purpose separately\n- Withdraw consent at any time through {{WITHDRAWAL_METHOD}}\n- Withdrawal of consent is as easy as giving consent\n- Withdrawal does not affect the lawfulness of processing done before withdrawal",
            },
            {
                "heading": "5. Your Rights as Data Principal",
                "content": "Under the DPDP Act 2023, you have the following rights:\n\n(a) Right to Information (Section 11): You may request a summary of your personal data being processed, the processing activities, and identities of all entities your data has been shared with.\n\n(b) Right to Correction and Erasure (Section 12): You may request correction of inaccurate data, completion of incomplete data, updating of outdated data, and erasure of data no longer necessary for the stated purpose.\n\n(c) Right to Grievance Redressal (Section 13): You may file a complaint with our Grievance Officer. We will acknowledge within 48 hours and resolve within 30 days.\n\n(d) Right to Nominate (Section 14): You may nominate another person to exercise your rights in case of your death or incapacity.\n\nTo exercise any right, contact: {{GRIEVANCE_OFFICER_EMAIL}}",
            },
            {
                "heading": "6. Data Retention",
                "content": "We retain your personal data only for as long as necessary to fulfill the purpose for which it was collected. Upon fulfillment of purpose or withdrawal of consent, your data will be erased within {{RETENTION_PERIOD}}, unless retention is required by law.",
            },
            {
                "heading": "7. Data Security",
                "content": "We implement reasonable security safeguards as required by Section 8(4) of the DPDP Act, including encryption, access controls, audit logging, and regular security assessments.",
            },
            {
                "heading": "8. Cross-Border Transfer",
                "content": "Your personal data may be transferred to countries/territories notified by the Central Government under Section 16 of the DPDP Act. We do not transfer data to restricted jurisdictions.",
            },
            {
                "heading": "9. Grievance Officer",
                "content": "Name: {{GRIEVANCE_OFFICER_NAME}}\nEmail: {{GRIEVANCE_OFFICER_EMAIL}}\nAddress: {{ADDRESS}}\n\nYou may also file a complaint with the Data Protection Board of India if you are not satisfied with our response.",
            },
        ],
        "applicable_sections": ["section_5", "section_6", "section_11", "section_12", "section_13", "section_14"],
    },
    RemediationType.CONSENT_FORM: {
        "title": "Consent Collection Form — DPDP Act 2023",
        "sections": [
            {
                "heading": "Consent Notice",
                "content": "{{COMPANY_NAME}} requests your consent to process your personal data for the purposes listed below. Please review each purpose carefully and provide your consent individually.\n\nYou may withdraw consent at any time by {{WITHDRAWAL_METHOD}}. Withdrawal will not affect the lawfulness of processing done before withdrawal.",
            },
            {
                "heading": "Processing Purposes",
                "content": "Please grant or deny consent for each purpose:\n\n[ ] Account Management — Required for service delivery (REQUIRED)\n[ ] AI-Powered Analysis — To provide AI-driven contract analysis\n[ ] Product Analytics — To improve our services\n[ ] Marketing Communications — To send product updates\n[ ] Third-Party Sharing — To share data with authorized partners\n\nNote: Each purpose can be individually toggled. We do not bundle consent.",
            },
            {
                "heading": "Privacy Policy",
                "content": "By granting consent, you acknowledge that you have read and understood our Privacy Notice (Version {{POLICY_VERSION}}). A copy of the privacy notice is available at {{PRIVACY_NOTICE_URL}}.",
            },
            {
                "heading": "Data Principal Acknowledgment",
                "content": "I confirm that:\n- I am {{AGE_CONFIRMATION}} years of age or older\n- The information I provide is accurate\n- I understand I can withdraw consent at any time\n- I have read the Privacy Notice\n\nSignature: ________________________\nDate: ________________________",
            },
        ],
        "applicable_sections": ["section_6"],
    },
    RemediationType.DPA_TEMPLATE: {
        "title": "Data Processing Agreement — DPDP Act 2023 Compliant",
        "sections": [
            {
                "heading": "1. Definitions",
                "content": "\"Data Fiduciary\" means {{PARTY_1_NAME}}.\n\"Data Processor\" means {{PARTY_2_NAME}}.\n\"Personal Data\" has the meaning assigned under the Digital Personal Data Protection Act, 2023.\n\"Processing\" includes collection, storage, use, modification, erasure, and any other operation on personal data.\n\"Data Principal\" means the individual whose personal data is being processed.\n\"Data Protection Board\" or \"DPB\" means the Data Protection Board of India established under the DPDP Act.",
            },
            {
                "heading": "2. Scope and Purpose",
                "content": "The Data Processor shall process personal data solely on behalf of and per the documented instructions of the Data Fiduciary, for the following purposes:\n{{PROCESSING_PURPOSES}}\n\nThe Data Processor shall not process personal data for any purpose other than those documented by the Data Fiduciary.",
            },
            {
                "heading": "3. Processor Obligations (Section 8(2))",
                "content": "The Data Processor shall:\n(a) Process personal data only per the Data Fiduciary's documented instructions;\n(b) Implement reasonable security safeguards as required by Section 8(4);\n(c) Not engage sub-processors without prior written consent of the Data Fiduciary;\n(d) Assist the Data Fiduciary in responding to Data Principal rights requests;\n(e) Delete or return all personal data upon termination of this agreement;\n(f) Make available all information necessary to demonstrate compliance;\n(g) Allow and contribute to audits by the Data Fiduciary or its authorized auditor.",
            },
            {
                "heading": "4. Security Safeguards (Section 8(4))",
                "content": "The Data Processor shall implement:\n(a) Encryption of personal data at rest and in transit (AES-256 minimum);\n(b) Access controls with role-based permissions and multi-factor authentication;\n(c) Audit logging of all access to and operations on personal data;\n(d) Regular vulnerability assessments and penetration testing;\n(e) Incident detection and response capabilities;\n(f) Employee training on data protection obligations.",
            },
            {
                "heading": "5. Breach Notification (Section 8(6))",
                "content": "The Data Processor shall:\n(a) Notify the Data Fiduciary of any personal data breach within 24 hours of discovery;\n(b) Provide sufficient information for the Data Fiduciary to notify the DPB and affected Data Principals;\n(c) Cooperate with the Data Fiduciary in breach investigation and remediation;\n(d) Maintain records of all breaches including facts, effects, and remedial actions.",
            },
            {
                "heading": "6. Data Principal Rights (Sections 11-14)",
                "content": "The Data Processor shall assist the Data Fiduciary in fulfilling obligations to:\n(a) Provide Data Principals with information about processing (Section 11);\n(b) Correct, complete, update, or erase personal data upon request (Section 12);\n(c) Respond to grievances within prescribed timelines (Section 13);\n(d) Honor nominations by Data Principals (Section 14).",
            },
            {
                "heading": "7. Cross-Border Transfer (Section 16)",
                "content": "The Data Processor shall not transfer personal data outside India except to countries/territories notified by the Central Government. Any cross-border transfer must be:\n(a) Documented with destination country, data categories, and safeguards;\n(b) Subject to adequate protection measures;\n(c) Reported to the Data Fiduciary.",
            },
            {
                "heading": "8. Data Retention and Deletion (Section 8(7))",
                "content": "The Data Processor shall:\n(a) Retain personal data only for the duration necessary to fulfill the processing purpose;\n(b) Delete all personal data within {{DELETION_PERIOD}} of purpose fulfillment or instruction from Data Fiduciary;\n(c) Provide written confirmation of deletion;\n(d) Ensure sub-processors delete data on the same terms.",
            },
            {
                "heading": "9. Audit Rights",
                "content": "The Data Fiduciary (or its authorized auditor) may audit the Data Processor's compliance with this agreement and the DPDP Act:\n(a) Upon reasonable notice (minimum 15 business days);\n(b) During normal business hours;\n(c) At the Data Fiduciary's expense (unless non-compliance is found);\n(d) Results of audits shall be shared with both parties.",
            },
            {
                "heading": "10. Liability and Indemnification",
                "content": "The Data Processor shall indemnify the Data Fiduciary against:\n(a) Penalties imposed by the Data Protection Board due to Processor's non-compliance (up to Rs 250 crore per violation);\n(b) Claims by Data Principals arising from Processor's breach of this agreement;\n(c) Costs of breach notification and remediation caused by Processor's actions;\n(d) Third-party claims arising from unauthorized processing by the Processor.",
            },
            {
                "heading": "11. Term and Termination",
                "content": "This agreement shall continue for the duration of the processing relationship. Upon termination:\n(a) The Data Processor shall cease all processing within {{CESSATION_PERIOD}};\n(b) All personal data shall be deleted or returned per Section 8;\n(c) Obligations regarding confidentiality and breach notification survive termination.",
            },
        ],
        "applicable_sections": [
            "section_8", "section_6", "section_11", "section_12",
            "section_13", "section_14", "section_16",
        ],
    },
}


class RemediationAgent:
    """Generates DPDP-compliant remediation content."""

    async def generate(self, request: RemediationRequest) -> RemediationOutput:
        """Generate remediation content based on type.

        Stage 1: Use pre-built templates (instant)
        Stage 2: AI customization based on context (best-effort)
        """
        template = _TEMPLATES.get(request.remediation_type)

        if template:
            # Start with template, then customize with AI
            output = RemediationOutput(
                remediation_type=request.remediation_type,
                title=template["title"],
                content="",
                language=request.language,
                sections=template["sections"],
                applicable_dpdp_sections=[
                    DPDPSection(s) for s in template.get("applicable_sections", [])
                ],
            )

            # Try AI customization
            try:
                customized = await self._customize_template(request, output)
                if customized:
                    return customized
            except Exception as exc:
                logger.error("AI customization failed: %s", exc)

            # Return template with placeholder substitution
            output.sections = self._substitute_placeholders(
                output.sections, request
            )
            output.content = self._sections_to_text(output.sections)
            return output

        # No template — fully AI-generated
        return await self._ai_generate(request)

    async def generate_breach_notification(
        self, input_data: BreachNotificationInput
    ) -> BreachNotification:
        """Generate dual breach notifications (DPB + data principals + CERT-In)."""
        from datetime import timedelta

        discovery_time = input_data.breach_discovered_at
        cert_in_deadline = discovery_time + timedelta(hours=6)
        dpb_deadline = discovery_time + timedelta(hours=72)

        # Deterministic template
        dpb_text = f"""PERSONAL DATA BREACH NOTIFICATION
To: Data Protection Board of India
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}

1. NATURE OF BREACH
{input_data.breach_description}

2. CATEGORIES OF DATA AFFECTED
{', '.join(input_data.data_categories_affected) or 'Under investigation'}

3. ESTIMATED RECORDS AFFECTED
{input_data.estimated_records_affected or 'Under investigation'}

4. DATE AND TIME OF DISCOVERY
{discovery_time.strftime('%Y-%m-%d %H:%M:%S IST')}

5. CURRENT STATUS
{'Ongoing — containment in progress' if input_data.is_ongoing else 'Contained'}

6. CONTAINMENT MEASURES TAKEN
{input_data.containment_measures or 'Immediate investigation initiated'}

7. POTENTIAL CONSEQUENCES
Impact assessment in progress. Affected Data Principals will be notified separately.

8. REMEDIAL ACTIONS
- Incident response team activated
- Forensic investigation initiated
- Affected systems isolated
- Enhanced monitoring deployed

This notification is submitted in compliance with Section 8(6) of the Digital Personal Data Protection Act, 2023."""

        principal_text = f"""IMPORTANT: NOTICE OF PERSONAL DATA BREACH

Dear Data Principal,

We are writing to inform you of a personal data breach that may affect your personal data.

WHAT HAPPENED:
{input_data.breach_description}

WHAT DATA WAS AFFECTED:
{', '.join(input_data.data_categories_affected) or 'We are still investigating the full scope'}

WHEN IT HAPPENED:
The breach was discovered on {discovery_time.strftime('%B %d, %Y')}.

WHAT WE ARE DOING:
{input_data.containment_measures or 'We have initiated immediate containment and investigation measures.'}

We have notified the Data Protection Board of India as required by the DPDP Act 2023.

WHAT YOU CAN DO:
- Change your passwords if login credentials may be affected
- Monitor your accounts for unusual activity
- Contact our Grievance Officer for questions or concerns

YOUR RIGHTS:
Under the DPDP Act 2023, you have the right to:
- Request information about the breach (Section 11)
- File a grievance with our Grievance Officer (Section 13)
- Escalate to the Data Protection Board of India

CONTACT:
Grievance Officer: [INSERT CONTACT]
Data Protection Board of India: https://www.dpb.gov.in

We sincerely apologize for this incident and are taking all necessary steps to prevent recurrence."""

        cert_in_text = f"""CYBER SECURITY INCIDENT REPORT
To: CERT-In (Indian Computer Emergency Response Team)
Reporting Deadline: Within 6 hours of discovery

1. Type of Incident: Personal Data Breach
2. Date/Time of Discovery: {discovery_time.strftime('%Y-%m-%d %H:%M:%S IST')}
3. Systems Affected: [INSERT AFFECTED SYSTEMS]
4. Description: {input_data.breach_description}
5. Estimated Impact: {input_data.estimated_records_affected} records
6. Data Categories: {', '.join(input_data.data_categories_affected)}
7. Containment Status: {'Ongoing' if input_data.is_ongoing else 'Contained'}
8. Actions Taken: {input_data.containment_measures}

This report is filed per CERT-In Directions dated April 28, 2022."""

        return BreachNotification(
            dpb_notification=dpb_text,
            principal_notification=principal_text,
            cert_in_notification=cert_in_text,
            timeline={
                "breach_discovered": discovery_time.isoformat(),
                "cert_in_deadline": cert_in_deadline.isoformat(),
                "dpb_deadline": dpb_deadline.isoformat(),
                "cert_in_hours_remaining": max(
                    0, (cert_in_deadline - datetime.now()).total_seconds() / 3600
                ),
                "dpb_hours_remaining": max(
                    0, (dpb_deadline - datetime.now()).total_seconds() / 3600
                ),
            },
            recommended_actions=[
                "Activate incident response team immediately",
                "Isolate affected systems",
                f"File CERT-In report by {cert_in_deadline.strftime('%H:%M IST')} (6-hour window)",
                f"Notify DPB by {dpb_deadline.strftime('%Y-%m-%d %H:%M IST')} (72-hour window)",
                "Notify affected Data Principals without undue delay",
                "Preserve evidence for forensic investigation",
                "Engage external forensic experts if needed",
                "Prepare for potential DPB inquiry",
            ],
        )

    def _substitute_placeholders(
        self, sections: list[dict], request: RemediationRequest
    ) -> list[dict]:
        """Replace {{PLACEHOLDER}} values from request context."""
        context = request.context or {}
        result = []
        for section in sections:
            content = section.get("content", "")
            for key, value in context.items():
                content = content.replace(f"{{{{{key}}}}}", str(value))
            # Also substitute from request fields
            content = content.replace("{{PARTY_1_NAME}}", request.party_1_name)
            content = content.replace("{{PARTY_2_NAME}}", request.party_2_name)
            result.append({**section, "content": content})
        return result

    def _sections_to_text(self, sections: list[dict]) -> str:
        """Convert sections to plain text."""
        parts = []
        for s in sections:
            parts.append(f"{s.get('heading', '')}\n\n{s.get('content', '')}")
        return "\n\n---\n\n".join(parts)

    async def _customize_template(
        self,
        request: RemediationRequest,
        output: RemediationOutput,
    ) -> RemediationOutput | None:
        """Customize template content with AI based on context."""
        try:
            from app.core.vertex_client import get_generative_model, is_available
        except ImportError:
            return None

        if not is_available():
            return None

        from app.core.config import settings

        template_text = self._sections_to_text(output.sections)
        context_str = json.dumps(request.context, default=str) if request.context else "{}"

        prompt = f"""You are a DPDP Act 2023 compliance expert. Customize this {request.remediation_type.value} template for the following context:

Industry: {request.industry}
Party 1: {request.party_1_name}
Party 2: {request.party_2_name}
Language: {request.language}
Gaps to address: {', '.join(request.gaps_to_address)}
Additional context: {context_str}

TEMPLATE:
{template_text[:8000]}

Return the customized document as a JSON object with:
{{
  "title": "...",
  "sections": [
    {{"heading": "...", "content": "..."}}
  ],
  "notes": ["any important notes about this document"]
}}

Keep all DPDP Act references and section numbers accurate. Fill in placeholders with appropriate values from context. If language is "hi", provide Hindi translation alongside English."""

        try:
            model = get_generative_model(settings.GEMINI_MODEL)
            from google.genai.types import GenerateContentConfig

            response = await model.generate_content_async(
                [{"role": "user", "parts": [{"text": prompt}]}],
                generation_config=GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=8000,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text or "{}"
            data = json.loads(raw)

            return RemediationOutput(
                remediation_type=request.remediation_type,
                title=data.get("title", output.title),
                content=self._sections_to_text(data.get("sections", output.sections)),
                language=request.language,
                sections=data.get("sections", output.sections),
                applicable_dpdp_sections=output.applicable_dpdp_sections,
                notes=data.get("notes", []),
            )
        except Exception as exc:
            logger.error("Template customization failed: %s", exc)
            return None

    async def _ai_generate(self, request: RemediationRequest) -> RemediationOutput:
        """Fully AI-generated remediation content for types without templates."""
        try:
            from app.core.vertex_client import get_generative_model, is_available
        except ImportError:
            raise RuntimeError("AI not available for this remediation type")

        if not is_available():
            raise RuntimeError("Vertex AI not configured")

        from app.core.config import settings

        prompt = f"""You are a DPDP Act 2023 compliance expert. Generate a {request.remediation_type.value} document.

Context:
- Industry: {request.industry}
- Party 1: {request.party_1_name}
- Party 2: {request.party_2_name}
- Jurisdiction: {request.jurisdiction}
- Language: {request.language}
- Gaps to address: {', '.join(request.gaps_to_address)}
- Additional context: {json.dumps(request.context, default=str)}

Requirements:
1. Must comply with DPDP Act 2023 (all relevant sections)
2. Include specific DPDP section references
3. Be legally sound and practically implementable
4. If language is "hi", include Hindi alongside English

Return as JSON:
{{
  "title": "...",
  "sections": [{{"heading": "...", "content": "..."}}],
  "applicable_sections": ["section_6", "section_8"],
  "notes": ["..."]
}}"""

        model = get_generative_model(settings.GEMINI_MODEL)
        from google.genai.types import GenerateContentConfig

        response = await model.generate_content_async(
            [{"role": "user", "parts": [{"text": prompt}]}],
            generation_config=GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8000,
                response_mime_type="application/json",
            ),
        )
        raw = response.text or "{}"
        data = json.loads(raw)

        return RemediationOutput(
            remediation_type=request.remediation_type,
            title=data.get("title", f"DPDP {request.remediation_type.value}"),
            content=self._sections_to_text(data.get("sections", [])),
            language=request.language,
            sections=data.get("sections", []),
            applicable_dpdp_sections=[
                DPDPSection(s) for s in data.get("applicable_sections", [])
            ],
            notes=data.get("notes", []),
        )
