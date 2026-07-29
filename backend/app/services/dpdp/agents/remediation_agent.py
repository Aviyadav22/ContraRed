"""
DPDP Remediation Agent — AI-generated draft content for legal review.

Generates:
  - DPDP-oriented contract clauses
  - Data Processing Agreements (DPAs)
  - Privacy notices (Section 5)
  - Consent collection templates
  - Breach notification templates (DPB + data principals + CERT-In)
  - Policy update recommendations

Outputs may be generated in a requested supported language. The DPDP Act
requires a language-access option; it does not require every artifact to be
bilingual.
"""

import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.services.dpdp.models import (
    RemediationRequest,
    RemediationOutput,
    RemediationType,
    DPDPSection,
    BreachNotificationInput,
    BreachNotification,
)

logger = logging.getLogger(__name__)
_IST = ZoneInfo("Asia/Kolkata")


# Pre-built templates for deterministic fallback (no AI needed)
_TEMPLATES = {
    RemediationType.PRIVACY_NOTICE: {
        "title": "Privacy Notice — DPDP Act 2023 Draft for Legal Review",
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
                "content": "We process personal data for the following specified purposes and stated legal bases:\n{{PURPOSE_LIST}}\n\nIf we propose a new or incompatible consent-based purpose, we will provide the required notice and request fresh affirmative consent before that processing begins.",
            },
            {
                "heading": "4. Consent",
                "content": "Where processing relies on consent, we request consent for the specified purpose and only the personal data necessary for it. You may:\n- Grant or deny each optional consent-based purpose\n- Withdraw consent at any time through {{WITHDRAWAL_METHOD}}\n- Withdraw consent as easily as it was given\n- Review what service consequence, if any, follows from refusing data necessary for a requested service\n- Rely on the lawfulness of processing completed before withdrawal",
            },
            {
                "heading": "5. Your Rights as Data Principal",
                "content": "Under the DPDP Act 2023, you have the following rights:\n\n(a) Right to Information (Section 11): You may request a summary of your personal data being processed and the processing activities, together with the prescribed sharing information.\n\n(b) Right to Correction and Erasure (Section 12): You may request correction of inaccurate or misleading data, completion of incomplete data, updating, and erasure where retention is not necessary for the specified purpose or compliance with law.\n\n(c) Right to Grievance Redressal (Section 13): You may file a grievance with our Grievance Officer. We aim to acknowledge within 48 hours and resolve within 30 days as internal service targets; our published response period will not exceed the applicable prescribed maximum.\n\n(d) Right to Nominate (Section 14): You may nominate another individual to exercise your rights in the event of your death or incapacity.\n\nTo exercise any right, contact: {{GRIEVANCE_OFFICER_EMAIL}}",
            },
            {
                "heading": "6. Data Retention",
                "content": "We retain your personal data only for as long as necessary to fulfill the purpose for which it was collected. Upon fulfillment of purpose or withdrawal of consent, your data will be erased within {{RETENTION_PERIOD}}, unless retention is required by law.",
            },
            {
                "heading": "7. Data Security",
                "content": "We implement appropriate technical and organisational measures under Section 8(4) and reasonable security safeguards under Section 8(5). Deployment-specific controls, retention, and residual risks should be described accurately rather than assumed from this template.",
            },
            {
                "heading": "8. Cross-Border Transfer",
                "content": "Personal data may be processed outside India subject to any transfer restriction notified by the Central Government under Section 16, any Rule 15 requirement, and any stricter applicable Indian law. We review current notifications before enabling a destination.",
            },
            {
                "heading": "9. Grievance Officer",
                "content": "Name: {{GRIEVANCE_OFFICER_NAME}}\nEmail: {{GRIEVANCE_OFFICER_EMAIL}}\nAddress: {{ADDRESS}}\n\nAfter exhausting this grievance process, you may approach the Data Protection Board of India through its current official channel.",
            },
        ],
        "applicable_sections": ["section_5", "section_6", "section_11", "section_12", "section_13", "section_14"],
    },
    RemediationType.CONSENT_FORM: {
        "title": "Consent Collection Form — DPDP Act 2023 Draft for Legal Review",
        "sections": [
            {
                "heading": "Consent Notice",
                "content": "{{COMPANY_NAME}} requests your consent to process your personal data for the purposes listed below. Please review each purpose carefully and provide your consent individually.\n\nYou may withdraw consent at any time by {{WITHDRAWAL_METHOD}}. Withdrawal will not affect the lawfulness of processing done before withdrawal.",
            },
            {
                "heading": "Processing Purposes",
                "content": "Configure this list from the actual data inventory; do not use these examples without verification:\n\n[ ] Account Management — identify necessary data and the consequence of refusal\n[ ] AI-Powered Analysis — identify contract data, provider, purpose, and retention\n[ ] Product Analytics — identify metrics and whether the purpose is optional\n[ ] Marketing Communications — optional, with a separate withdrawal control\n[ ] Third-Party Sharing — identify each recipient category, data, and purpose\n\nOptional consent-based purposes must not be bundled with a requested service. The interface may use controls other than checkboxes if it still records a clear affirmative action.",
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
        "title": "Data Processing Agreement — DPDP Act 2023 Draft for Legal Review",
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
                "content": "The Data Processor shall:\n(a) Process personal data only per the Data Fiduciary's documented instructions;\n(b) Implement appropriate technical and organisational measures and reasonable security safeguards supporting the Data Fiduciary's Sections 8(4) and 8(5) obligations;\n(c) Not engage sub-processors without prior written consent of the Data Fiduciary;\n(d) Assist the Data Fiduciary in responding to Data Principal rights requests;\n(e) Delete or return all personal data upon termination of this agreement, subject to documented legal retention;\n(f) Make available the information reasonably necessary to demonstrate compliance;\n(g) Allow and contribute to proportionate audits under the agreed audit procedure.",
            },
            {
                "heading": "4. Security Measures and Safeguards (Sections 8(4) and 8(5))",
                "content": "The Data Processor shall implement security safeguards appropriate to the nature and risk of the processing, including:\n(a) Appropriate encryption, masking, obfuscation, tokenisation, or equivalent protection where suitable;\n(b) Access controls with role-based permissions and multi-factor authentication where appropriate;\n(c) Logging, monitoring, and review sufficient to detect unauthorised access;\n(d) Risk-based vulnerability assessment and penetration testing;\n(e) Incident detection, response, resilience, and recovery capabilities;\n(f) Personnel confidentiality and data-protection training.\n\nAny mandatory algorithms, key lengths, testing frequencies, and recovery targets must be specified in the security schedule and verified against the deployed system.",
            },
            {
                "heading": "5. Breach Notification (Section 8(6))",
                "content": "The Data Processor shall:\n(a) Notify the Data Fiduciary without undue delay and, as a negotiated internal deadline, no later than 24 hours after becoming aware of a personal data breach;\n(b) Provide sufficient information for the Data Fiduciary's initial notices without delay and its detailed Board update within the prescribed period;\n(c) Cooperate with the Data Fiduciary in breach investigation, affected-principal notification, and remediation;\n(d) Maintain records of all breaches including facts, effects, and remedial actions.",
            },
            {
                "heading": "6. Data Principal Rights (Sections 11-14)",
                "content": "The Data Processor shall assist the Data Fiduciary in fulfilling obligations to:\n(a) Provide Data Principals with information about processing (Section 11);\n(b) Correct, complete, update, or erase personal data upon request (Section 12);\n(c) Respond to grievances within prescribed timelines (Section 13);\n(d) Honor nominations by Data Principals (Section 14).",
            },
            {
                "heading": "7. Cross-Border Transfer (Section 16)",
                "content": "The Data Processor shall not transfer personal data outside India without the Data Fiduciary's prior written authorisation. Each authorised transfer must:\n(a) Be documented with destination country or territory, data categories, purpose, recipients, and safeguards;\n(b) Comply with any restriction notified under Section 16, any Rule 15 requirement, and stricter applicable Indian law;\n(c) Be notified to the Data Fiduciary before the destination or material transfer arrangement changes.",
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
                "content": "Subject to the negotiated liability cap, its agreed carve-outs, causation standards, and applicable law, the Data Processor shall indemnify the Data Fiduciary against losses to the extent caused by the Processor's breach of this agreement, including:\n(a) Regulatory amounts that may lawfully be allocated or recovered between the parties;\n(b) Third-party claims arising from unauthorised processing by the Processor;\n(c) Reasonable breach-notification, investigation, and remediation costs caused by the Processor's acts or omissions.\n\nThe parties must expressly decide whether this indemnity and data-protection claims sit inside the general cap, under a super-cap, or outside the cap. The DPDP statutory schedule must not be described as a fixed contractual amount or a per-violation entitlement.",
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
    """Generates DPDP-oriented drafts that require legal and factual review."""

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
        """Generate staged Board, affected-principal, and conditional CERT-In templates."""
        from datetime import timedelta

        discovery_time = input_data.breach_discovered_at
        if discovery_time.tzinfo is None:
            discovery_time = discovery_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        now_ist = now.astimezone(_IST)
        discovery_ist = discovery_time.astimezone(_IST)
        cert_in_deadline = discovery_time + timedelta(hours=6)
        detailed_board_deadline = discovery_time + timedelta(hours=72)

        # Deterministic template
        dpb_text = f"""INITIAL PERSONAL DATA BREACH NOTICE — SEND WITHOUT DELAY
To: Data Protection Board of India
Date: {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}

1. NATURE, EXTENT, TIMING, AND LOCATION
{input_data.breach_description}
Location: [INSERT LOCATION OR SYSTEM]

2. LIKELY IMPACT
{input_data.estimated_records_affected or 'Number under investigation'} records may be affected.
Data categories: {', '.join(input_data.data_categories_affected) or 'Under investigation'}

This initial notice is submitted without delay under DPDP Rule 7(2)(a).

---
DETAILED BOARD UPDATE — DUE WITHIN 72 HOURS UNLESS EXTENDED

1. DATE AND TIME OF AWARENESS
{discovery_ist.strftime('%Y-%m-%d %H:%M:%S IST')}

2. UPDATED DESCRIPTION AND CURRENT STATUS
{'Ongoing — containment in progress' if input_data.is_ongoing else 'Contained'}

3. EVENTS, CIRCUMSTANCES, AND REASONS
[INSERT INVESTIGATION FINDINGS]

4. MITIGATION MEASURES
{input_data.containment_measures or 'Immediate investigation initiated'}

5. FINDINGS ABOUT THE PERSON RESPONSIBLE, IF KNOWN
[INSERT FINDINGS OR STATE UNKNOWN]

6. RECURRENCE-PREVENTION MEASURES
- Incident response team activated
- Forensic investigation initiated
- Affected systems isolated
- Enhanced monitoring deployed

7. AFFECTED DATA PRINCIPAL NOTIFICATION REPORT
[INSERT NUMBER NOTIFIED, CHANNELS, TIMES, FAILURES, AND RETRY STEPS]"""

        principal_text = f"""IMPORTANT: NOTICE OF PERSONAL DATA BREACH

Dear Data Principal,

We are writing to inform you of a personal data breach that may affect your personal data.

WHAT HAPPENED:
{input_data.breach_description}

WHAT DATA WAS AFFECTED:
{', '.join(input_data.data_categories_affected) or 'We are still investigating the full scope'}

WHEN IT HAPPENED:
The breach was discovered on {discovery_ist.strftime('%B %d, %Y')}.

WHAT WE ARE DOING:
{input_data.containment_measures or 'We have initiated immediate containment and investigation measures.'}

We are providing the notices required by the DPDP framework and documenting delivery.

WHAT YOU CAN DO:
- Change your passwords if login credentials may be affected
- Monitor your accounts for unusual activity
- Contact our Grievance Officer for questions or concerns

YOUR RIGHTS:
Under the DPDP Act 2023, you may:
- Request the information about your personal data and its processing described in Section 11
- File a grievance with our Grievance Officer (Section 13)
- Approach the Data Protection Board of India after exhausting the available grievance process

CONTACT:
Grievance Officer: [INSERT CONTACT]
Board complaint channel: [INSERT CURRENT OFFICIAL DIGITAL-OFFICE LINK]

We sincerely apologize for this incident and are taking all necessary steps to prevent recurrence."""

        cert_in_text = f"""CYBER SECURITY INCIDENT REPORT
To: CERT-In (Indian Computer Emergency Response Team)
Scope warning: Use this template only if the incident is within the CERT-In Directions' reportable categories.
Reporting Deadline if in scope: Within 6 hours of noticing the incident or being brought to notice

1. Type of Incident: Personal Data Breach
2. Date/Time of Discovery: {discovery_ist.strftime('%Y-%m-%d %H:%M:%S IST')}
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
                "initial_board_notice_due": "without_delay",
                "detailed_board_deadline": detailed_board_deadline.isoformat(),
                "cert_in_hours_remaining": max(
                    0, (cert_in_deadline - now).total_seconds() / 3600
                ),
                "detailed_board_hours_remaining": max(
                    0, (detailed_board_deadline - now).total_seconds() / 3600
                ),
            },
            recommended_actions=[
                "Activate incident response team immediately",
                "Isolate affected systems",
                "Send the initial Board notice without delay",
                f"Complete the detailed Board update by {detailed_board_deadline.astimezone(_IST).strftime('%Y-%m-%d %H:%M IST')}, unless extended",
                "Notify affected Data Principals without delay",
                f"If the incident is within CERT-In's specified categories, report by {cert_in_deadline.astimezone(_IST).strftime('%H:%M IST')}",
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

Use the supplied template as a drafting aid, not as proof of compliance. Keep the
verified statutory structure intact, distinguish statutory deadlines from
negotiated service targets, do not invent notifications or legal requirements,
and leave an explicit placeholder where facts or current law are unverified.
Fill only placeholders supported by the supplied context. If language is "hi",
provide Hindi alongside English and flag the translation for legal review."""

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
1. Produce a draft for legal and factual review; do not claim that generation proves compliance
2. Include a DPDP section reference only when confident it supports the proposition
3. Distinguish statutory duties from recommended controls and negotiated service targets
4. Mark facts, current notifications, sectoral-law issues, and unsupported legal conclusions for verification
5. Be practically implementable and avoid promising controls not supplied in the context
6. If language is "hi", include Hindi alongside English and flag the translation for review

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
