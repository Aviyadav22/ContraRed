from __future__ import annotations


from app.services.drafting.models import DraftSection, RawDraft, DraftMetadata
from app.services.drafting.consistency_engine import ConsistencyEngine


def _make_draft(sections, defined_terms=None):
    return RawDraft(
        contract_type="nda_mutual",
        title="Test NDA",
        sections=sections,
        defined_terms=defined_terms or {},
        metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=0.1, tokens_used=0),
    )


def _sec(number, heading, content):
    return DraftSection(
        number=number,
        heading=heading,
        content=content,
        clause_type="general",
        tier_used="balanced",
    )


def test_undefined_terms_detected():
    sections = [
        _sec("1", "Definitions", 'The "Confidential Information" means all data.'),
        _sec("2", "Obligations", "The Receiving Party shall protect all Derivative Works."),
    ]
    draft = _make_draft(sections, {"Confidential Information": "all data"})
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    issues = [a for a in annotations if "Derivative Works" in a.issue]
    assert len(issues) >= 1


def test_cross_reference_valid():
    sections = [
        _sec("1", "Definitions", "See Section 2 for details."),
        _sec("2", "Details", "The details are here."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    xref_issues = [a for a in annotations if "cross-reference" in a.issue.lower()]
    assert len(xref_issues) == 0


def test_cross_reference_broken():
    sections = [
        _sec("1", "Definitions", "See Section 5 for details."),
        _sec("2", "Details", "As per Section 9."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    xref_issues = [a for a in annotations if "cross-reference" in a.issue.lower()]
    assert len(xref_issues) >= 1


def test_party_name_consistency():
    sections = [
        _sec("1", "Preamble", "Acme Inc. (the Company) and Beta LLC (the Vendor)"),
        _sec("2", "Terms", "The Supplier shall deliver goods to the Company."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    name_issues = [a for a in annotations if "party" in a.issue.lower() or "inconsistent" in a.issue.lower()]
    assert len(name_issues) >= 1


def test_number_word_mismatch():
    sections = [
        _sec("1", "Term", "This Agreement shall last for twenty (30) days."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    num_issues = [a for a in annotations if "number" in a.issue.lower() or "mismatch" in a.issue.lower()]
    assert len(num_issues) >= 1


def test_number_word_match():
    sections = [
        _sec("1", "Term", "This Agreement shall last for thirty (30) days."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    num_issues = [a for a in annotations if "number" in a.issue.lower() or "mismatch" in a.issue.lower()]
    assert len(num_issues) == 0


def test_placeholder_leftover():
    sections = [
        _sec("1", "Parties", "This Agreement between {{party_1_name}} and Acme."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    ph_issues = [a for a in annotations if "placeholder" in a.issue.lower()]
    assert len(ph_issues) >= 1


def test_placeholder_severity_is_critical():
    sections = [
        _sec("1", "Parties", "This Agreement between {{party_1_name}} and Acme."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    ph_issues = [a for a in annotations if "placeholder" in a.issue.lower()]
    assert all(a.severity == "critical" for a in ph_issues)


def test_all_clean_no_annotations():
    sections = [
        _sec("1", "Definitions", 'The "Confidential Information" means all data.'),
        _sec("2", "Obligations", "The Receiving Party shall protect all Confidential Information per Section 1."),
    ]
    draft = _make_draft(sections, {"Confidential Information": "all data"})
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    assert len(annotations) == 0


def test_agent_field_is_consistency():
    sections = [
        _sec("1", "Parties", "This Agreement between {{name}} and Acme."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    assert all(a.agent == "consistency" for a in annotations)
