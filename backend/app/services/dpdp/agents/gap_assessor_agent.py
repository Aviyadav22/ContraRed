"""
DPDP Gap Assessor Agent — Organization-wide compliance scoring.

Questionnaire-driven + AI analysis that maps current state against every
DPDP section (4-17). Produces board-ready compliance reports with
section-by-section breakdown and remediation priorities.
"""

import json
import logging
from datetime import date, datetime, timezone

from app.services.dpdp.models import (
    AssessmentRequest,
    AssessmentAnswer,
    AssessmentQuestion,
    AssessmentCategory,
    GapAssessmentResult,
    SectionScore,
    ComplianceStatus,
    DPDPSection,
)

logger = logging.getLogger(__name__)

# Enforcement deadline
DPDP_ENFORCEMENT_DATE = date(2027, 5, 13)

# ---- Assessment Questions (40 questions across 10 categories) ----

ASSESSMENT_QUESTIONS: list[dict] = [
    # Consent Governance (Section 6)
    {
        "id": "cg_01",
        "category": "consent_governance",
        "section": "section_6",
        "question": "Do you collect free, specific, informed, and unambiguous consent before processing personal data?",
        "guidance": "DPDP Section 6 requires consent to be free, specific, informed, unconditional, and unambiguous.",
        "weight": 2.0,
        "is_critical": True,
    },
    {
        "id": "cg_02",
        "category": "consent_governance",
        "section": "section_6",
        "question": "Is consent collected separately for each processing purpose (no bundling)?",
        "guidance": "Each purpose must have its own consent toggle. Bundled consent is non-compliant.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "cg_03",
        "category": "consent_governance",
        "section": "section_6",
        "question": "Can data principals easily withdraw consent at any time?",
        "guidance": "Withdrawal must be as easy as giving consent. No friction or penalties.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "cg_04",
        "category": "consent_governance",
        "section": "section_6",
        "question": "Do you maintain auditable records of all consent actions (grant, withdrawal, modification)?",
        "guidance": "Immutable consent records must be maintained for at least 7 years.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Notice Requirements (Section 5)
    {
        "id": "nr_01",
        "category": "consent_governance",
        "section": "section_5",
        "question": "Do you provide a clear privacy notice before or at the time of data collection?",
        "guidance": "Notice must describe data collected, purposes, rights, and how to exercise them.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "nr_02",
        "category": "consent_governance",
        "section": "section_5",
        "question": "Is the privacy notice available in English and Hindi (or the language of the data principal)?",
        "guidance": "DPDP requires notice in languages specified in Schedule VIII of the Constitution.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Data Principal Rights (Sections 11-14)
    {
        "id": "dpr_01",
        "category": "data_principal_rights",
        "section": "section_11",
        "question": "Can data principals request a summary of their personal data and processing activities?",
        "guidance": "Section 11: Right to information about processing, categories, and third-party sharing.",
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
        "question": "Do you have a grievance redressal mechanism with a designated officer?",
        "guidance": "Section 13: Must have a grievance officer; respond within prescribed time.",
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
        "guidance": "Section 8(4): Encryption, access controls, audit logging, incident detection.",
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
        "question": "Do you have Data Processing Agreements with all third-party processors?",
        "guidance": "Section 8(2): Processor must act only per fiduciary instructions.",
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
        "guidance": "Must notify DPB and affected principals 'without undue delay' (effectively 72 hours).",
        "weight": 2.0,
        "is_critical": True,
    },
    {
        "id": "br_02",
        "category": "breach_readiness",
        "section": "section_8",
        "question": "Can you detect data breaches within 24 hours?",
        "guidance": "CERT-In requires 6-hour reporting; DPDP requires 72-hour notification.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "br_03",
        "category": "breach_readiness",
        "section": "section_8",
        "question": "Do you have pre-drafted breach notification templates for DPB and data principals?",
        "guidance": "Speed is critical; templates ensure compliance under pressure.",
        "weight": 1.0,
        "is_critical": False,
    },
    {
        "id": "br_04",
        "category": "breach_readiness",
        "section": "section_8",
        "question": "Have you conducted breach simulation exercises in the last 12 months?",
        "guidance": "Regular drills ensure the team can execute the plan under real conditions.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Cross-Border (Section 16)
    {
        "id": "cb_01",
        "category": "cross_border",
        "section": "section_16",
        "question": "Do you transfer personal data outside India?",
        "guidance": "Section 16: Only to government-notified countries. Maintain transfer records.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "cb_02",
        "category": "cross_border",
        "section": "section_16",
        "question": "Do you maintain records of all cross-border data transfers (destination, purpose, safeguards)?",
        "guidance": "Must track destination country, data categories, legal basis, and safeguards.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Vendor Management
    {
        "id": "vm_01",
        "category": "vendor_management",
        "section": "section_8",
        "question": "Do you audit your data processors/vendors for DPDP compliance?",
        "guidance": "Data Fiduciary is responsible even when processing is outsourced.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "vm_02",
        "category": "vendor_management",
        "section": "section_8",
        "question": "Do your vendor contracts include DPDP-compliant data processing clauses?",
        "guidance": "DPA must restrict processor to act only per fiduciary instructions.",
        "weight": 1.5,
        "is_critical": True,
    },
    # Children's Data (Section 9)
    {
        "id": "cd_01",
        "category": "children_data",
        "section": "section_9",
        "question": "Do you process personal data of children (under 18)?",
        "guidance": "If yes, verifiable parental consent required; no behavioral monitoring.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "cd_02",
        "category": "children_data",
        "section": "section_9",
        "question": "Do you have age verification mechanisms in place?",
        "guidance": "Must verify age before processing; different rules for different age groups.",
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
        "guidance": "Section 10: DPIAs required for new processing activities with high risk.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Data Retention (Section 8(7))
    {
        "id": "dr_01",
        "category": "data_retention",
        "section": "section_8",
        "question": "Do you have defined retention periods for each category of personal data?",
        "guidance": "Must not retain data beyond what's necessary for the stated purpose.",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "dr_02",
        "category": "data_retention",
        "section": "section_8",
        "question": "Do you have automated data purging/deletion processes?",
        "guidance": "Manual deletion is error-prone; automation ensures compliance at scale.",
        "weight": 1.0,
        "is_critical": False,
    },
    # Purpose Limitation (Section 6(1))
    {
        "id": "pl_01",
        "category": "purpose_limitation",
        "section": "section_6",
        "question": "Is each data processing activity tied to a specific, documented purpose?",
        "guidance": "Processing without a defined purpose violates Section 6(1).",
        "weight": 1.5,
        "is_critical": True,
    },
    {
        "id": "pl_02",
        "category": "purpose_limitation",
        "section": "section_6",
        "question": "Do you obtain fresh consent before using data for secondary/new purposes?",
        "guidance": "Repurposing data without fresh consent is a Section 6 violation.",
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
                    f"URGENT: Address {len(data['critical_gaps'])} critical gap(s) before May 2027 enforcement."
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
        days_to_enforcement = (DPDP_ENFORCEMENT_DATE - date.today()).days
        if days_to_enforcement <= 0:
            deadline_risk = "ENFORCEMENT ACTIVE — immediate compliance required"
        elif days_to_enforcement <= 180:
            deadline_risk = f"HIGH RISK — only {days_to_enforcement} days until enforcement (May 13, 2027)"
        elif days_to_enforcement <= 365:
            deadline_risk = f"MODERATE — {days_to_enforcement} days until enforcement"
        else:
            deadline_risk = f"MANAGEABLE — {days_to_enforcement} days until enforcement"

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
                "[HIGH] Establish incident response plan with 72-hour notification workflow."
            )

        has_vendor_gap = any(
            "processor" in f.lower() or "vendor" in f.lower()
            for s in section_scores
            for f in s.findings
        )
        if has_vendor_gap:
            actions.append(
                "[HIGH] Review and update all vendor contracts with DPDP-compliant DPA clauses."
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
