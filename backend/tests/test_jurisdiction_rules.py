"""Tests for the deterministic jurisdiction rule engine."""

import pytest
from app.services.drafting.models import (
    RawDraft, DraftSection, DraftMetadata, Annotation,
)
from app.services.drafting.jurisdiction_rules import (
    JurisdictionRuleEngine, JurisdictionFinding,
)


def _make_draft(sections: list[DraftSection] | None = None) -> RawDraft:
    if sections is None:
        sections = [
            DraftSection(
                number="1", heading="Preamble",
                content="This is a standard preamble.",
                clause_type="preamble", tier_used="acceptable",
            ),
        ]
    return RawDraft(
        contract_type="nda_mutual",
        title="Test Agreement",
        sections=sections,
        defined_terms={},
        metadata=DraftMetadata(
            playbook_id="test", model="test",
            generation_seconds=1, tokens_used=0,
        ),
    )


def _draft_with_content(content: str, section_number: str = "5") -> RawDraft:
    return _make_draft([
        DraftSection(
            number=section_number, heading="Test Clause",
            content=content, clause_type="restriction",
            tier_used="aggressive",
        ),
    ])


class TestCaliforniaRules:
    def test_california_non_compete_flagged(self):
        draft = _draft_with_content(
            "Employee shall not compete with the Company for a period of 12 months."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="US-CA", contract_type="nda_mutual")
        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) >= 1
        assert any("VOID" in f.issue or "void" in f.issue.lower() for f in critical)
        assert any("16600" in f.statute for f in critical)

    def test_california_non_solicitation_flagged(self):
        draft = _draft_with_content(
            "The Consultant agrees to a non-solicitation obligation for 24 months."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="US-CA", contract_type="nda_mutual")
        assert len(findings) >= 1
        assert any("non-solicitation" in f.issue.lower() or "non-solicit" in f.issue.lower() for f in findings)

    def test_california_restrictive_covenant_flagged(self):
        draft = _draft_with_content(
            "This restrictive covenant prevents the employee from engaging in business."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="US-CA", contract_type="nda_mutual")
        assert len(findings) >= 1


class TestIndiaRules:
    def test_india_stamp_duty_noted(self):
        draft = _make_draft()  # plain draft, no special clauses
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="IN", contract_type="nda_mutual")
        stamp = [f for f in findings if "stamp duty" in f.issue.lower()]
        assert len(stamp) >= 1
        assert stamp[0].severity == "warning"

    def test_india_non_compete_void(self):
        draft = _draft_with_content(
            "The employee agrees to a non-compete for 2 years post-employment."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="IN", contract_type="nda_mutual")
        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) >= 1
        assert any("Section 27" in f.statute for f in critical)


class TestGBRules:
    def test_gdpr_dpa_required_for_gb(self):
        draft = _draft_with_content(
            "The Processor shall handle personal data of data subjects in accordance with GDPR."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="GB", contract_type="saas")
        gdpr = [f for f in findings if "GDPR" in f.issue or "gdpr" in f.issue.lower()]
        assert len(gdpr) >= 1

    def test_ucta_liability_negligence_death(self):
        draft = _draft_with_content(
            "The limitation of liability excludes liability for negligence causing death."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="GB", contract_type="nda_mutual")
        ucta = [f for f in findings if "UCTA" in f.issue]
        assert len(ucta) >= 1


class TestDelawareNoSpecialFlags:
    def test_delaware_no_special_flags(self):
        draft = _draft_with_content(
            "This agreement is governed by the laws of Delaware."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="US-DE", contract_type="nda_mutual")
        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) == 0


class TestContractTypeRules:
    def test_saas_personal_data_flags_dpa(self):
        draft = _draft_with_content(
            "The service processes personal data including PII from end users."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="US-DE", contract_type="saas")
        dpa = [f for f in findings if "DPA" in f.issue or "Data Processing" in f.issue]
        assert len(dpa) >= 1

    def test_non_saas_no_dpa_flag(self):
        draft = _draft_with_content(
            "The service processes personal data including PII from end users."
        )
        engine = JurisdictionRuleEngine()
        findings = engine.check(draft, jurisdiction="US-DE", contract_type="nda_mutual")
        dpa = [f for f in findings if "DPA" in f.issue or "Data Processing" in f.issue]
        assert len(dpa) == 0


class TestToAnnotations:
    def test_converts_findings_to_annotations(self):
        findings = [
            JurisdictionFinding(
                section_number="3",
                severity="critical",
                issue="Non-compete is void",
                statute="Cal. B&P 16600",
                action="REMOVE_CLAUSE",
                suggested_fix="Remove clause",
            ),
        ]
        engine = JurisdictionRuleEngine()
        annotations = engine.to_annotations(findings)
        assert len(annotations) == 1
        ann = annotations[0]
        assert isinstance(ann, Annotation)
        assert ann.agent == "jurisdiction"
        assert ann.severity == "critical"
        assert ann.section_number == "3"
        assert "16600" in ann.reasoning
