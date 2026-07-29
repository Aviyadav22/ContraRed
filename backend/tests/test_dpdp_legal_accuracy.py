"""Regression checks for statutory timing and DPDP drafting guardrails."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.dpdp.agents.monitor_agent import DPDP_DEADLINES
from app.services.dpdp.agents.gap_assessor_agent import ASSESSMENT_QUESTIONS
from app.services.dpdp.agents.remediation_agent import RemediationAgent, _TEMPLATES
from app.services.dpdp.knowledge_base import DPDP_RULES_SECTIONS
from app.services.dpdp.models import (
    AssessmentRequest,
    BreachNotificationInput,
    GapAssessmentResult,
)
from app.services.dpdp.orchestrator import DPDPOrchestrator
from app.services.seed_consent_defaults import DEFAULT_PRIVACY_POLICY
from scripts.compliance_layers.dpdp import DPDP_LAYER
from scripts.playbooks.dpa import DPA
from scripts.playbooks.fintech import FINTECH
from scripts.playbooks.healthcare import HEALTHCARE
from scripts.playbooks.it_services import IT_SERVICES
from scripts.playbooks.msa import MSA
from scripts.playbooks.saas import SAAS


def _all_template_text() -> str:
    return "\n".join(
        section["content"]
        for template in _TEMPLATES.values()
        for section in template["sections"]
    )


def test_rule_7_preserves_staged_board_notification_timing():
    rule_7 = next(
        section
        for section in DPDP_RULES_SECTIONS
        if section.section_number == "Rule 7"
    )

    text = f"{rule_7.summary}\n{rule_7.full_text}".lower()
    assert "without delay" in text
    assert "detailed board report within 72 hours" in text
    assert "unless the board grants more time" in text


def test_dpdp_templates_do_not_reintroduce_known_legal_misstatements():
    text = _all_template_text()
    lowered = text.lower()

    assert "rs 250 crore per violation" not in lowered
    assert "except to countries/territories notified" not in lowered
    assert "security safeguards as required by section 8(4)" not in lowered
    assert "sections 8(4) and 8(5)" in lowered
    assert "drafting aid, not as proof of compliance" not in lowered


def test_seed_privacy_policy_distinguishes_policy_from_statutory_minimum():
    policy = DEFAULT_PRIVACY_POLICY
    content = policy["content"].lower()

    assert policy["version"] == 2
    assert "continued use constitutes acceptance" not in content
    assert "7-year minimum applies only" in content
    assert "consent alone does not override a transfer restriction" in content
    assert "fresh affirmative consent" in content


def test_seeded_dpdp_contract_rules_use_final_transfer_and_penalty_structure():
    by_type = {
        rule["clause_type"]: rule
        for rule in DPDP_LAYER["rules"]
    }
    transfer = " ".join(
        str(value)
        for value in by_type["dpdp_cross_border_transfer"].values()
    ).lower()
    penalty_positions = " ".join(
        str(by_type["dpdp_penalty_indemnification"].get(field, ""))
        for field in (
            "primary_position",
            "fallback_position",
            "acceptable_position",
        )
    ).lower()
    penalty_detection = " ".join(
        by_type["dpdp_penalty_indemnification"]["unacceptable_signals"]
    ).lower()
    fiduciary = by_type["dpdp_fiduciary_obligations"]["primary_position"].lower()
    consent_manager = by_type["dpdp_consent_manager"]["primary_position"].lower()
    withdrawal = by_type["dpdp_consent_withdrawal"]["primary_position"].lower()

    assert "notified countries only" not in transfer
    assert "positive allowlist" in transfer
    assert "rule 15" in transfer
    assert "250 crore per violation" not in penalty_positions
    assert "category-specific maxima" in penalty_positions
    assert "250 crore per violation" in penalty_detection
    assert "section 8(4)" in fiduciary
    assert "section 8(5)" in fiduciary
    assert "section 6(7)-(9)" in consent_manager
    assert "section 9" not in consent_manager
    assert "section 6(4)" in withdrawal
    assert DPDP_LAYER["version"] == 2
    assert DPDP_LAYER["effective_date"] == "2027-05-13"


def test_default_contract_playbooks_distinguish_law_from_negotiated_controls():
    dpa_text = " ".join(
        str(value)
        for rule in DPA["rules"]
        for value in rule.values()
    ).lower()
    healthcare_text = " ".join(
        str(value)
        for rule in HEALTHCARE["rules"]
        for value in rule.values()
    ).lower()

    assert "72 hours is the global standard" not in dpa_text
    assert "whitelisted jurisdictions" not in dpa_text
    assert "except to countries or territories notified" not in dpa_text
    assert "must be indian law for dpdp" not in dpa_text
    assert "processor's statutory deadline" in dpa_text
    assert "does not itself prescribe a gdpr-style" in dpa_text
    assert "does not create a separate sensitive-data category" in healthcare_text
    assert "specified cert-in incidents" in healthcare_text


def test_legally_corrected_system_playbooks_are_versioned_for_upgrade():
    for playbook in (DPA, HEALTHCARE, FINTECH, IT_SERVICES, MSA, SAAS):
        assert playbook["version"] >= 2, playbook["name"]


def test_monitor_uses_phased_commencement_not_all_provisions_claim():
    substantive = next(
        item for item in DPDP_DEADLINES if "Substantive Compliance" in item["title"]
    )

    assert substantive["deadline"] == datetime(2027, 5, 13).date()
    assert "substantive" in substantive["title"].lower()
    assert "most substantive provisions" in substantive["description"].lower()
    assert "all provisions" not in substantive["description"].lower()


def test_gap_questions_distinguish_law_from_recommended_controls():
    by_id = {item["id"]: item for item in ASSESSMENT_QUESTIONS}

    assert "must have its own consent toggle" not in by_id["cg_02"]["guidance"].lower()
    assert "do not prescribe" in by_id["cg_02"]["guidance"].lower()
    assert "8(5)" in by_id["fo_01"]["guidance"]
    assert "not a universal statutory" in by_id["dr_02"]["guidance"].lower()
    assert "recommended operational control" in by_id["br_04"]["guidance"].lower()


@pytest.mark.asyncio
async def test_breach_generator_uses_initial_and_detailed_board_steps():
    discovered = datetime(2026, 7, 1, 9, 30, tzinfo=timezone.utc)
    notice = await RemediationAgent().generate_breach_notification(
        BreachNotificationInput(
            breach_description="Unauthorised access under investigation.",
            data_categories_affected=["email address"],
            estimated_records_affected=10,
            breach_discovered_at=discovered,
        )
    )

    detailed_due = datetime.fromisoformat(notice.timeline["detailed_board_deadline"])
    assert notice.timeline["initial_board_notice_due"] == "without_delay"
    assert detailed_due - discovered == timedelta(hours=72)
    assert "INITIAL PERSONAL DATA BREACH NOTICE" in notice.dpb_notification
    assert "DETAILED BOARD UPDATE" in notice.dpb_notification
    assert "only if the incident is within" in notice.cert_in_notification.lower()
    assert "after exhausting" in notice.principal_notification.lower()


@pytest.mark.asyncio
async def test_gap_assessment_persists_the_canonical_organization_name():
    class FakeBridge:
        async def auto_answer_consent_questions(self, db, organization_id):
            return {}

    class FakeAssessor:
        async def assess(self, request):
            return GapAssessmentResult(
                organization_name=request.organization_name,
                overall_score=80,
            )

    class FakeDB:
        added = None
        committed = False

        def add(self, value):
            self.added = value

        async def commit(self):
            self.committed = True

    orchestrator = DPDPOrchestrator()
    orchestrator.bridge = FakeBridge()
    orchestrator.assessor = FakeAssessor()
    db = FakeDB()

    await orchestrator.run_assessment(
        AssessmentRequest(organization_name="Acme Legal"),
        db=db,
    )

    assert db.added is not None
    assert db.added.organization_name == "Acme Legal"
    assert db.committed is True
