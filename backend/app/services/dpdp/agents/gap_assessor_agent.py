"""
DPDP Gap Assessor Agent — Organization-wide compliance scoring.

Questionnaire-driven + AI analysis that maps current state against every
DPDP section (4-17). Produces board-ready compliance reports with
section-by-section breakdown and remediation priorities.
"""

import json
import logging
from datetime import date

from app.services.dpdp.models import (
    AssessmentRequest,
    AssessmentQuestion,
    AssessmentCategory,
    GapAssessmentResult,
    SectionScore,
    ComplianceStatus,
    DPDPSection,
)

logger = logging.getLogger(__name__)

# Main substantive commencement date
DPDP_SUBSTANTIVE_COMMENCEMENT_DATE = date(2027, 5, 13)

# ---- Assessment Questions (40 questions across 10 categories) ----

ASSESSMENT_QUESTIONS: list[dict] = [
    # Consent Governance (Section 6)
    {
        "id": "cg_01",
        "category": "consent_governance",
        "section": "section_6",
        "question": "Where consent is the processing basis, do you collect free, specific, informed, unconditional, and unambiguous consent through clear affirmative action?",
        "guidance": "DPDP Section 6 requires consent to be free, specific, informed, unconditional, and unambiguous.",
        "weight": 2.0,
        "is_critical": True,
    },
    {
        "id": "cg_02",
        "category": "consent_governance",
        "section": "section_6",
        "question": "Does each consent request identify a specified purpose and only the personal data necessary for it?",
        "guidance": "Section 6 requires consent to relate to a specified purpose and necessary personal data. Separate controls are a strong implementation pattern, but the Rules do not prescribe a particular toggle or checkbox interface.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "cg_03",
        "category": "consent_governance",
        "section": "section_6",
        "question": "Can data principals easily withdraw consent at any time?",
        "guidance": "Section 6 requires the ease of withdrawal to be comparable to the ease of giving consent.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "cg_04",
        "category": "consent_governance",
        "section": "section_6",
        "question": "Do you maintain auditable records of all consent actions (grant, withdrawal, modification)?",
        "guidance": (
            "Keep sufficient evidence to prove compliant notice and consent under section 6(10). "
            "The seven-year minimum applies specifically to registered Consent Managers."
        ),
        "weight": 1.0,
        "is_critical": False,
    },
    # Notice Requirements (Section 5)
    {
        "id": "nr_01",
        "category": "consent_governance",
        "section": "section_5",
        "question": "Does every consent request have the required clear notice before or with the request?",
        "guidance": "Section 5 and Rule 3 require the personal data and specified purpose plus means to withdraw consent, exercise rights, use grievance redressal, and complain to the Board.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "nr_02",
        "category": "consent_governance",
        "section": "section_5",
        "question": "Can the Data Principal access the notice in English or a language in the Eighth Schedule?",
        "guidance": (
            "The Act requires an option to access the notice in English or any Eighth Schedule language; "
            "it does not require every notice to be bilingual."
        ),
        "weight": 1.0,
        "is_critical": False,
    },
    # Data Principal Rights (Sections 11-14)
    {
        "id": "dpr_01",
        "category": "data_principal_rights",
        "section": "section_11",
        "question": "Can data principals request a summary of their personal data and processing activities?",
        "guidance": "Section 11 covers a summary of personal data and processing plus prescribed information about sharing with other Data Fiduciaries and Data Processors, subject to statutory exceptions.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "dpr_02",
        "category": "data_principal_rights",
        "section": "section_12",
        "question": "Can data principals request correction, completion, or erasure of their data?",
        "guidance": "Section 12: Must correct inaccurate data and erase when purpose fulfilled.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "dpr_03",
        "category": "data_principal_rights",
        "section": "section_13",
        "question": "Do you provide a readily available grievance mechanism and publish an accountable privacy contact?",
        "guidance": "Sections 8 and 13 require an effective grievance mechanism and published business contact or DPO information. The published response period must respect the prescribed maximum.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "dpr_04",
        "category": "data_principal_rights",
        "section": "section_14",
        "question": "Can data principals nominate another person to exercise their rights (in case of death/incapacity)?",
        "guidance": "Section 14: Must support nomination of authorized representatives.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Fiduciary Obligations (Section 8)
    {
        "id": "fo_01",
        "category": "fiduciary_obligations",
        "section": "section_8",
        "question": "Do you implement reasonable security safeguards to protect personal data?",
        "guidance": "Sections 8(4) and 8(5), read with Rule 6, require appropriate organisational measures and reasonable safeguards. Controls are risk- and deployment-specific; the Rule gives non-exhaustive examples.",
        "weight": 2.0,
        "is_critical": True,
    },
    {
        "id": "fo_02",
        "category": "fiduciary_obligations",
        "section": "section_8",
        "question": "Do you ensure accuracy, completeness, and consistency of personal data?",
        "guidance": "Section 8(3): Especially when data is used for decisions or shared with others.",
        "weight": 1.0,
        "is_critical": False,
    },
    {
        "id": "fo_03",
        "category": "fiduciary_obligations",
        "section": "section_8",
        "question": "Are all processors engaged under valid contracts with processing and safeguard terms appropriate to the service?",
        "guidance": "Section 8(2) requires a valid contract for processor engagement in the covered context; Rule 6 requires appropriate security-safeguard provisions. Instruction, assistance, audit, deletion, and subprocessor terms are risk-based contractual controls.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "fo_04",
        "category": "fiduciary_obligations",
        "section": "section_8",
        "question": "Do you delete personal data when the purpose is fulfilled or consent is withdrawn?",
        "guidance": "Section 8(7): Erasure obligation unless retention required by law.",
        "weight": 1.5,
        "is_critical": True,
    },
    # Breach Readiness (Section 8(6))
    {
        "id": "br_01",
        "category": "breach_readiness",
        "section": "section_8",
        "question": "Do you have a documented incident response plan for personal data breaches?",
        "guidance": (
            "Notify affected principals and give the initial Board notice without delay; "
            "the updated detailed Board report is due within 72 hours unless extended."
        ),
        "weight": 2.0,
        "is_critical": True,
    },
    {
        "id": "br_02",
        "category": "breach_readiness",
        "section": "section_8",
        "question": "Can you detect, assess, and route personal-data and cyber incidents without delay?",
        "guidance": (
            "DPDP Rule 7 uses without-delay notices plus a 72-hour detailed Board report. "
            "CERT-In's six-hour direction applies to specified cyber incidents; classify scope separately."
        ),
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "br_03",
        "category": "breach_readiness",
        "section": "section_8",
        "question": "Do you have pre-drafted breach notification templates for DPB and data principals?",
        "guidance": "Pre-approved templates are a recommended readiness control, not a separately stated statutory duty.",
        "weight": 1.0,
        "is_critical": False,
    },
    {
        "id": "br_04",
        "category": "breach_readiness",
        "section": "section_8",
        "question": "Have you conducted breach simulation exercises in the last 12 months?",
        "guidance": "Exercises are a recommended operational control; the DPDP Act and Rules do not prescribe an annual drill.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Cross-Border (Section 16)
    {
        "id": "cb_01",
        "category": "cross_border",
        "section": "section_16",
        "question": "Do you transfer personal data outside India?",
        "guidance": (
            "Section 16 permits Government restrictions on transfers to notified countries or territories; "
            "Rule 15 may add requirements concerning foreign-government access. Check current notifications."
        ),
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "cb_02",
        "category": "cross_border",
        "section": "section_16",
        "question": "Do you maintain records of all cross-border data transfers (destination, purpose, safeguards)?",
        "guidance": "A transfer inventory is a recommended evidence and control mechanism for checking Section 16 notifications, Rule 15 requirements, contracts, and stricter sectoral law.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Vendor Management
    {
        "id": "vm_01",
        "category": "vendor_management",
        "section": "section_8",
        "question": "Do you conduct risk-based oversight of processors and verify material safeguards?",
        "guidance": "The Data Fiduciary remains responsible for processing on its behalf. Audit rights and cadence are contractual/risk controls, not a universal statutory annual-audit requirement.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "vm_02",
        "category": "vendor_management",
        "section": "section_8",
        "question": "Do vendor contracts document processing scope and safeguards supporting your DPDP obligations?",
        "guidance": "Use fact-specific contractual instructions, safeguards, incident support, rights assistance, retention/deletion, and subprocessor controls. The exact allocation is negotiated and must not be presented as verbatim statutory language.",
        "weight": 1.5,
        "is_critical": True,
    },
    # Children's Data (Section 9)
    {
        "id": "cd_01",
        "category": "children_data",
        "section": "section_9",
        "question": "Do you process personal data of children (under 18)?",
        "guidance": "Check verifiable parental consent, detrimental processing, tracking/behavioural monitoring, and targeted advertising, together with any applicable notified class- or purpose-specific exemption.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "cd_02",
        "category": "children_data",
        "section": "section_9",
        "question": "Do you have age verification mechanisms in place?",
        "guidance": "Rules 10-12 address verifiable parental consent and specified exemptions. Use proportionate age/parent verification based on reliable identity and age details or permitted tokens.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Significant Data Fiduciary (Section 10)
    {
        "id": "sf_01",
        "category": "significant_fiduciary",
        "section": "section_10",
        "question": "Has your organization been notified as a Significant Data Fiduciary?",
        "guidance": "Government notifies based on data volume, sensitivity, risk to sovereignty.",
        "weight": 1.0,
        "is_critical": False,
    },
    {
        "id": "sf_02",
        "category": "significant_fiduciary",
        "section": "section_10",
        "question": "Do you have a Data Protection Officer (resident in India) appointed?",
        "guidance": "Section 10: DPO must be resident in India; represents fiduciary to DPB.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "sf_03",
        "category": "significant_fiduciary",
        "section": "section_10",
        "question": "Do you conduct periodic Data Protection Impact Assessments (DPIAs)?",
        "guidance": "Section 10 and Rule 13 apply periodic DPIA and audit duties to entities notified as Significant Data Fiduciaries; they are not universal duties for every new processing activity.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Data Retention (Section 8(7))
    {
        "id": "dr_01",
        "category": "data_retention",
        "section": "section_8",
        "question": "Do you have defined retention periods for each category of personal data?",
        "guidance": "Section 8(7) requires erasure on consent withdrawal or when the specified purpose is no longer served, unless retention is necessary for compliance with law. Rule-specific retention may also apply.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "dr_02",
        "category": "data_retention",
        "section": "section_8",
        "question": "Do you have automated data purging/deletion processes?",
        "guidance": "Automation is a recommended control, not a universal statutory requirement. Whatever process is used must implement applicable erasure, warning, legal-hold, and processor-cascade rules.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Purpose Limitation (Section 6(1))
    {
        "id": "pl_01",
        "category": "purpose_limitation",
        "section": "section_6",
        "question": "Is each data processing activity tied to a specific, documented purpose?",
        "guidance": "Consent under Section 6 must relate to a specified purpose. Processing under a Section 7 legitimate use or another applicable basis must be documented against that basis rather than mislabeled as consent.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "pl_02",
        "category": "purpose_limitation",
        "section": "section_6",
        "question": "Before a new or incompatible purpose, do you reassess the processing basis and obtain fresh notice/consent where consent is required?",
        "guidance": "A new consent-based purpose requires compliant notice and fresh affirmative consent. Do not assume consent is required—or sufficient—where a legitimate use, statutory restriction, or other Indian law governs.",
        "weight": 1.0,
        "is_critical": False,
    },
]


class GapAssessorAgent:
    """Runs organization-wide DPDP compliance gap assessments."""

    def get_questions(
        self,
        processes_children_data: bool = False,
        is_significant_fiduciary: bool = False,
        has_cross_border: bool = False,
    ) -> list[AssessmentQuestion]:
        """Return applicable assessment questions based on org profile."""
        questions = []
        for q in ASSESSMENT_QUESTIONS:
            cat = q["category"]

            # Skip children's data questions if not applicable
            if cat == "children_data" and not processes_children_data:
                continue
            # Skip significant fiduciary if not applicable
            if cat == "significant_fiduciary" and not is_significant_fiduciary:
                continue
            # Skip cross-border if not applicable
            if cat == "cross_border" and not has_cross_border:
                continue

            questions.append(AssessmentQuestion(
                id=q["id"],
                category=AssessmentCategory(cat),
                section=DPDPSection(q["section"]),
                question=q["question"],
                guidance=q["guidance"],
                weight=q["weight"],
                is_critical=q["is_critical"],
            ))
        return questions

    async def assess(self, request: AssessmentRequest) -> GapAssessmentResult:
        """Run full gap assessment and return scored results.

        Stage 1: Score answers against questions (deterministic)
        Stage 2: AI analysis for recommendations (best-effort)
        """
        questions = self.get_questions(
            processes_children_data=request.processes_children_data,
            is_significant_fiduciary=request.is_significant_fiduciary,
            has_cross_border=request.has_cross_border_transfers,
        )

        # Build answer lookup
        answer_map = {a.question_id: a for a in request.answers}

        # Score by section
        section_data: dict[str, dict] = {}
        for q in questions:
            sec = q.section.value
            if sec not in section_data:
                section_data[sec] = {
                    "total_weight": 0,
                    "earned_weight": 0,
                    "findings": [],
                    "critical_gaps": [],
                }

            section_data[sec]["total_weight"] += q.weight
            answer = answer_map.get(q.id)

            if answer:
                if answer.answer == "yes":
                    section_data[sec]["earned_weight"] += q.weight
                elif answer.answer == "partial":
                    section_data[sec]["earned_weight"] += q.weight * 0.5
                    section_data[sec]["findings"].append(
                        f"Partial: {q.question}"
                    )
                elif answer.answer == "no":
                    section_data[sec]["findings"].append(
                        f"Gap: {q.question}"
                    )
                    if q.is_critical:
                        section_data[sec]["critical_gaps"].append(q.question)
                # not_applicable doesn't count
                elif answer.answer == "not_applicable":
                    section_data[sec]["total_weight"] -= q.weight
            else:
                # Unanswered = not assessed
                section_data[sec]["findings"].append(
                    f"Not assessed: {q.question}"
                )

        # Build section scores
        section_scores: list[SectionScore] = []
        total_weight = 0
        total_earned = 0
        all_critical_gaps: list[str] = []

        section_names = {
            "section_4": "Grounds for Processing",
            "section_5": "Notice Requirements",
            "section_6": "Consent",
            "section_7": "Legitimate Uses",
            "section_8": "Data Fiduciary Obligations",
            "section_9": "Children's Data & Consent Manager",
            "section_10": "Significant Data Fiduciary",
            "section_11": "Right to Information",
            "section_12": "Right to Correction/Erasure",
            "section_13": "Grievance Redressal",
            "section_14": "Nomination",
            "section_15": "Data Principal Duties",
            "section_16": "Cross-Border Transfer",
            "section_17": "Exemptions",
        }

        for sec, data in section_data.items():
            tw = data["total_weight"]
            ew = data["earned_weight"]
            total_weight += tw
            total_earned += ew

            score = (ew / tw * 100) if tw > 0 else 0
            if score >= 80:
                status = ComplianceStatus.COMPLIANT
                priority = "low"
            elif score >= 50:
                status = ComplianceStatus.PARTIAL
                priority = "medium"
            else:
                status = ComplianceStatus.NON_COMPLIANT
                priority = "critical" if data["critical_gaps"] else "high"

            all_critical_gaps.extend(data["critical_gaps"])

            # Generate recommendations
            recommendations = []
            if data["critical_gaps"]:
                recommendations.append(
                    f"URGENT: Address {len(data['critical_gaps'])} critical gap(s) before the May 2027 substantive commencement."
                )
            if data["findings"]:
                recommendations.append(
                    f"Review {len(data['findings'])} finding(s) in this section."
                )

            section_scores.append(SectionScore(
                section=DPDPSection(sec),
                section_name=section_names.get(sec, sec),
                status=status,
                score=round(score, 1),
                findings=data["findings"],
                recommendations=recommendations,
                priority=priority,
            ))

        overall_score = (total_earned / total_weight * 100) if total_weight > 0 else 0

        if overall_score >= 80:
            overall_status = ComplianceStatus.COMPLIANT
        elif overall_score >= 50:
            overall_status = ComplianceStatus.PARTIAL
        else:
            overall_status = ComplianceStatus.NON_COMPLIANT

        # AI-enhanced recommendations
        action_items = await self._generate_action_items(
            request, section_scores, all_critical_gaps
        )

        # Deadline risk
        days_to_commencement = (
            DPDP_SUBSTANTIVE_COMMENCEMENT_DATE - date.today()
        ).days
        if days_to_commencement <= 0:
            deadline_risk = (
                "SUBSTANTIVE PHASE ACTIVE — verify each provision's commencement "
                "and complete applicable compliance actions"
            )
        elif days_to_commencement <= 180:
            deadline_risk = (
                f"HIGH RISK — only {days_to_commencement} days until the main "
                "substantive commencement (May 13, 2027)"
            )
        elif days_to_commencement <= 365:
            deadline_risk = (
                f"MODERATE — {days_to_commencement} days until the main "
                "substantive commencement"
            )
        else:
            deadline_risk = (
                f"MANAGEABLE — {days_to_commencement} days until the main "
                "substantive commencement"
            )

        effort = "High" if overall_score < 40 else "Medium" if overall_score < 70 else "Low"

        return GapAssessmentResult(
            organization_name=request.organization_name,
            overall_score=round(overall_score, 1),
            overall_status=overall_status,
            section_scores=section_scores,
            critical_gaps=all_critical_gaps,
            action_items=action_items,
            estimated_remediation_effort=effort,
            deadline_risk=deadline_risk,
        )

    async def _generate_action_items(
        self,
        request: AssessmentRequest,
        section_scores: list[SectionScore],
        critical_gaps: list[str],
    ) -> list[str]:
        """Generate prioritized action items using AI."""
        # Start with deterministic action items
        actions: list[str] = []

        if critical_gaps:
            actions.append(
                f"[CRITICAL] Address {len(critical_gaps)} critical compliance gap(s) immediately."
            )

        non_compliant = [s for s in section_scores if s.status == ComplianceStatus.NON_COMPLIANT]
        partial = [s for s in section_scores if s.status == ComplianceStatus.PARTIAL]

        if non_compliant:
            sections = ", ".join(s.section_name for s in non_compliant)
            actions.append(f"[HIGH] Remediate non-compliant sections: {sections}")

        if partial:
            sections = ", ".join(s.section_name for s in partial)
            actions.append(f"[MEDIUM] Improve partial compliance in: {sections}")

        # Add standard action items based on gaps
        has_consent_gap = any(
            s.section in (DPDPSection.SEC_5, DPDPSection.SEC_6)
            and s.status != ComplianceStatus.COMPLIANT
            for s in section_scores
        )
        if has_consent_gap:
            actions.append(
                "[HIGH] Implement granular consent management system with per-purpose toggles."
            )

        has_breach_gap = any(
            "breach" in f.lower()
            for s in section_scores
            for f in s.findings
        )
        if has_breach_gap:
            actions.append(
                "[HIGH] Establish a without-delay initial-notice workflow and a 72-hour detailed Board-report workflow."
            )

        has_vendor_gap = any(
            "processor" in f.lower() or "vendor" in f.lower()
            for s in section_scores
            for f in s.findings
        )
        if has_vendor_gap:
            actions.append(
                "[HIGH] Review vendor contracts and add fact-specific processing, security, rights-support, breach, and deletion terms."
            )

        # Try AI enhancement
        try:
            ai_actions = await self._ai_action_items(request, section_scores)
            actions.extend(ai_actions)
        except Exception as exc:
            logger.error("AI action items failed: %s", exc)

        return actions

    async def _ai_action_items(
        self,
        request: AssessmentRequest,
        section_scores: list[SectionScore],
    ) -> list[str]:
        """Generate AI-enhanced action items."""
        try:
            from app.core.vertex_client import get_generative_model, is_available
        except ImportError:
            return []

        if not is_available():
            return []

        from app.core.config import settings

        gaps_summary = "\n".join(
            f"- {s.section_name}: {s.status.value} (score: {s.score})"
            for s in section_scores
            if s.status != ComplianceStatus.COMPLIANT
        )

        if not gaps_summary:
            return []

        prompt = f"""You are a DPDP Act 2023 compliance advisor. Based on this organization's compliance assessment, generate 3-5 specific, actionable remediation steps.

Organization: {request.organization_name}
Industry: {request.industry}
Employee count: {request.employee_count}
Processes children's data: {request.processes_children_data}
Significant Data Fiduciary: {request.is_significant_fiduciary}
Cross-border transfers: {request.has_cross_border_transfers}

Compliance Gaps:
{gaps_summary}

Return a JSON array of strings, each being a specific action item with priority tag [CRITICAL], [HIGH], or [MEDIUM].
Focus on practical, implementable steps. Be specific to the industry.
Return ONLY the JSON array."""

        try:
            model = get_generative_model(settings.GEMINI_SCOUT_MODEL)
            from google.genai.types import GenerateContentConfig

            response = await model.generate_content_async(
                [{"role": "user", "parts": [{"text": prompt}]}],
                generation_config=GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2000,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text or "[]"
            items = json.loads(raw)
            return [str(item) for item in items if isinstance(item, str)][:5]
        except Exception as exc:
            logger.error("AI action items parse error: %s", exc)
            return []
