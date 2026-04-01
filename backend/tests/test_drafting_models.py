from __future__ import annotations

import pytest
from datetime import date


def test_party_info_valid():
    from app.services.drafting.models import PartyInfo
    p = PartyInfo(name="Acme Inc.", entity_type="Inc.", jurisdiction="US-DE", address="123 Main St")
    assert p.name == "Acme Inc."


def test_party_info_missing_name():
    from app.services.drafting.models import PartyInfo
    with pytest.raises(Exception):
        PartyInfo(name="", entity_type="Inc.", jurisdiction="US-DE")


def test_nda_details_defaults():
    from app.services.drafting.models import NDADetails
    d = NDADetails(purpose="Evaluate partnership")
    assert d.confidentiality_survival_years == 3
    assert d.non_solicitation is False
    assert d.marking_requirement is False


def test_saas_details_required_fields():
    from app.services.drafting.models import SaaSDetails
    s = SaaSDetails(service_description="Cloud CRM", pricing_model="per_user_monthly",
                    price_amount=29.99, billing_frequency="monthly", auto_renewal=True)
    assert s.price_amount == 29.99
    assert s.uptime_commitment is None


def test_draft_request_nda():
    from app.services.drafting.models import DraftRequest, PartyInfo, NDADetails
    req = DraftRequest(
        contract_type="nda_mutual", drafting_perspective="party_1",
        risk_appetite="balanced", jurisdiction="US-DE",
        party_1=PartyInfo(name="Acme Inc.", entity_type="Inc.", jurisdiction="US-DE"),
        party_2=PartyInfo(name="Beta LLC", entity_type="LLC", jurisdiction="US-CA"),
        term_months=24, governing_law="Delaware", dispute_resolution="arbitration",
        nda_details=NDADetails(purpose="Evaluate partnership"),
    )
    assert req.contract_type == "nda_mutual"
    assert req.saas_details is None


def test_draft_section():
    from app.services.drafting.models import DraftSection
    s = DraftSection(number="3", heading="Definition of Confidential Information",
                     content='"Confidential Information" means...', clause_type="confidential_info_definition", tier_used="preferred")
    assert s.number == "3"


def test_raw_draft():
    from app.services.drafting.models import RawDraft, DraftSection, DraftMetadata
    rd = RawDraft(
        contract_type="nda_mutual", title="MUTUAL NON-DISCLOSURE AGREEMENT",
        sections=[DraftSection(number="1", heading="Preamble", content="This Agreement...",
                               clause_type="preamble", tier_used="acceptable")],
        defined_terms={"Confidential Information": "means..."},
        metadata=DraftMetadata(playbook_id="nda-default", model="gemini-2.5-pro",
                               generation_seconds=12.5, tokens_used=4500),
    )
    assert len(rd.sections) == 1


def test_annotation():
    from app.services.drafting.models import Annotation
    a = Annotation(section_number="5", agent="risk", severity="warning",
                   issue="Liability cap missing", suggested_fix="Add 12-month cap", reasoning="Standard market practice")
    assert a.agent == "risk"


def test_quality_report():
    from app.services.drafting.models import QualityReport
    qr = QualityReport(overall_score=87.0, risk_alignment=92.0, compliance_score=85.0,
                        qa_score=88.0, annotations_applied=5, conflicts_flagged=1, open_annotations=[])
    assert qr.overall_score == 87.0


def test_final_draft():
    from app.services.drafting.models import FinalDraft, RawDraft, DraftSection, DraftMetadata, QualityReport
    rd = RawDraft(contract_type="nda_mutual", title="NDA",
                  sections=[DraftSection(number="1", heading="H", content="C", clause_type="preamble", tier_used="acceptable")],
                  defined_terms={}, metadata=DraftMetadata(playbook_id="x", model="m", generation_seconds=1.0, tokens_used=100))
    qr = QualityReport(overall_score=90, risk_alignment=90, compliance_score=90, qa_score=90,
                        annotations_applied=0, conflicts_flagged=0, open_annotations=[])
    fd = FinalDraft(draft=rd, quality_report=qr)
    assert fd.draft.title == "NDA"


def test_draft_request_with_risk_profile():
    from app.services.drafting.models import DraftRequest, PartyInfo
    req = DraftRequest(
        contract_type="saas",
        drafting_perspective="party_1",
        risk_appetite="balanced",
        jurisdiction="US-DE",
        party_1=PartyInfo(name="Acme", entity_type="Inc", jurisdiction="US-DE"),
        party_2=PartyInfo(name="Beta", entity_type="LLC", jurisdiction="US-CA"),
        term_months=12,
        governing_law="Delaware",
        risk_profile={"indemnification": "protective", "limitation_of_liability": "balanced"},
    )
    assert req.risk_profile["indemnification"] == "protective"


def test_draft_request_risk_profile_defaults_empty():
    from app.services.drafting.models import DraftRequest, PartyInfo
    req = DraftRequest(
        contract_type="nda_mutual",
        drafting_perspective="balanced",
        risk_appetite="balanced",
        jurisdiction="US-DE",
        party_1=PartyInfo(name="A", entity_type="Inc", jurisdiction="US-DE"),
        party_2=PartyInfo(name="B", entity_type="LLC", jurisdiction="US-CA"),
        term_months=12,
        governing_law="Delaware",
    )
    assert req.risk_profile == {}
