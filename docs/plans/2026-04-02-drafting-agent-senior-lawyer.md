# Senior-Lawyer Drafting Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the ContraRed drafting agent from a 2nd-year associate to a senior-partner-level system that generates strategically calibrated, jurisdiction-compliant, internally consistent, professionally styled contracts.

**Architecture:** 6 pillars implemented as new agents/modules that plug into the existing 4-stage orchestrator pipeline. Pillar 5 (Style Enforcer) and Pillar 2 (Consistency Engine) are deterministic post-processors. Pillar 1 (Clause-Level Risk) extends the models and tier selection. Pillar 3 (Jurisdiction Rules) and Pillar 4 (Enhanced Compliance) are rule-engine + LLM hybrids. Pillar 6 (Feedback Loop) adds persistence.

**Tech Stack:** Python 3.11, Pydantic v2, pytest (asyncio_mode=auto), Vertex AI (google-genai), existing FastAPI backend

---

## Phase A: Style Enforcer + Consistency Engine (Deterministic)

### Task 1: Add Style Rules Data Model

**Files:**
- Create: `backend/app/services/drafting/style_rules.py`
- Test: `backend/tests/test_style_rules.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_style_rules.py
from __future__ import annotations
import pytest
from app.services.drafting.style_rules import (
    normalize_shall_will,
    normalize_number_words,
    normalize_efforts_standard,
    remove_archaisms,
    format_defined_term_first_use,
)


def test_shall_will_normalization_to_shall():
    text = 'The Company will deliver the goods. The Vendor will pay on time.'
    result = normalize_shall_will(text, preference="shall")
    assert "shall deliver" in result
    assert "shall pay" in result
    assert "will deliver" not in result


def test_shall_will_normalization_to_will():
    text = 'The Company shall deliver. The Vendor shall pay.'
    result = normalize_shall_will(text, preference="will")
    assert "will deliver" in result
    assert "will pay" not in result


def test_shall_will_skips_future_tense():
    text = 'This Agreement will expire on the date set forth above.'
    result = normalize_shall_will(text, preference="shall")
    # "will expire" is future tense, not obligation — should stay as-is
    assert "will expire" in result


def test_number_word_pairs():
    text = "within 30 days of notice"
    result = normalize_number_words(text)
    assert "thirty (30) days" in result


def test_number_word_pairs_already_correct():
    text = "within thirty (30) days"
    result = normalize_number_words(text)
    assert "thirty (30) days" in result


def test_number_word_large():
    text = "not to exceed 12 months"
    result = normalize_number_words(text)
    assert "twelve (12) months" in result


def test_efforts_standard_normalization():
    text = 'Party shall use best efforts to obtain consent. Party shall use commercially reasonable efforts to deliver.'
    result = normalize_efforts_standard(text)
    assert "reasonable efforts" in result
    assert "best efforts" not in result
    assert "commercially reasonable efforts" not in result


def test_remove_archaisms():
    text = "The party herein agrees to the terms hereof and hereby acknowledges thereof."
    result = remove_archaisms(text)
    assert "herein" not in result
    assert "hereof" not in result
    assert "hereby" not in result
    assert "thereof" not in result


def test_format_defined_term_first_use():
    text = 'The Confidential Information means all data. The Receiving Party shall protect Confidential Information.'
    defined = {"Confidential Information", "Receiving Party"}
    result = format_defined_term_first_use(text, defined)
    # First occurrence should be quoted
    assert '"Confidential Information"' in result or "\u201cConfidential Information\u201d" in result
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_style_rules.py -v`
Expected: FAIL (module not found)

**Step 3: Implement style_rules.py**

```python
# backend/app/services/drafting/style_rules.py
"""
Deterministic contract drafting style enforcer.
Based on Ken Adams' Manual of Style for Contract Drafting (5th ed).
"""
from __future__ import annotations

import re
from typing import Set

# ── shall / will normalization ──────────────────────────────────────

_OBLIGATION_RE = re.compile(
    r'\b(shall|will)\s+'
    r'(?!expire|terminate|commence|become|be\s+deemed|result|occur|arise|lapse)',
    re.IGNORECASE,
)

_FUTURE_VERBS = frozenset({
    "expire", "terminate", "commence", "become", "result",
    "occur", "arise", "lapse", "take effect", "be deemed",
})


def normalize_shall_will(text: str, preference: str = "shall") -> str:
    """Normalize obligation verbs to consistent shall or will."""
    target = preference.lower()
    replace_from = "will" if target == "shall" else "shall"

    def _replace(m: re.Match) -> str:
        verb = m.group(0)
        rest = verb.split(None, 1)
        if len(rest) < 2:
            return verb
        following = rest[1].lower().strip()
        # Don't replace future-tense uses
        for fv in _FUTURE_VERBS:
            if following.startswith(fv):
                return verb
        if rest[0].lower() == replace_from:
            case = rest[0]
            replacement = target.capitalize() if case[0].isupper() else target
            return replacement + " " + rest[1]
        return verb

    return _OBLIGATION_RE.sub(_replace, text)


# ── number-word pairs ───────────────────────────────────────────────

_NUM_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
    15: "fifteen", 18: "eighteen", 20: "twenty", 24: "twenty-four",
    30: "thirty", 45: "forty-five", 60: "sixty", 90: "ninety",
    180: "one hundred eighty", 365: "three hundred sixty-five",
}

_NUM_UNIT_RE = re.compile(
    r'(?<!\()\b(\d{1,3})\s+(days?|months?|years?|business\s+days?|calendar\s+days?)\b'
    r'(?!\s*\))',
    re.IGNORECASE,
)


def normalize_number_words(text: str) -> str:
    """Convert bare numbers before time units to 'word (N) unit' format."""
    def _replace(m: re.Match) -> str:
        num = int(m.group(1))
        unit = m.group(2)
        word = _NUM_WORDS.get(num)
        if word:
            return f"{word} ({num}) {unit}"
        return m.group(0)

    # Skip if already in "word (N)" format
    already = re.compile(r'\w+\s+\(\d+\)\s+(days?|months?|years?)', re.IGNORECASE)
    parts = already.split(text)
    return _NUM_UNIT_RE.sub(_replace, text)


# ── efforts standard ────────────────────────────────────────────────

_EFFORTS_RE = re.compile(
    r'\b(best\s+efforts|commercially\s+reasonable\s+efforts|reasonable\s+best\s+efforts)\b',
    re.IGNORECASE,
)


def normalize_efforts_standard(text: str) -> str:
    """Normalize all efforts standards to 'reasonable efforts' per Adams."""
    return _EFFORTS_RE.sub("reasonable efforts", text)


# ── archaism removal ────────────────────────────────────────────────

_ARCHAISMS = {
    r'\bherein\b': 'in this Agreement',
    r'\bhereof\b': 'of this Agreement',
    r'\bhereby\b': '',
    r'\bthereof\b': 'of it',
    r'\btherein\b': 'in it',
    r'\bwhereas\b': '',  # Recital marker — keep if at line start
    r'\bhereinafter\b': '',
    r'\baforesaid\b': '',
    r'\bnotwithstanding\s+the\s+foregoing\b': 'Despite the above',
}


def remove_archaisms(text: str) -> str:
    """Replace archaic legalese with plain English equivalents."""
    for pattern, replacement in _ARCHAISMS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Clean up double spaces
    text = re.sub(r'  +', ' ', text)
    return text.strip()


# ── defined term formatting ─────────────────────────────────────────


def format_defined_term_first_use(text: str, defined_terms: Set[str]) -> str:
    """Quote the first occurrence of each defined term."""
    for term in sorted(defined_terms, key=len, reverse=True):
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        match = pattern.search(text)
        if match and not _is_already_quoted(text, match.start()):
            quoted = f'\u201c{match.group()}\u201d'
            text = text[:match.start()] + quoted + text[match.end():]
    return text


def _is_already_quoted(text: str, pos: int) -> bool:
    """Check if position is already inside quotes."""
    if pos == 0:
        return False
    before = text[max(0, pos - 2):pos]
    return any(c in before for c in '"\u201c\u201d')


# ── master apply ────────────────────────────────────────────────────


def apply_all_style_rules(
    text: str,
    defined_terms: Set[str] | None = None,
    shall_preference: str = "shall",
) -> str:
    """Apply all style rules to a clause text."""
    text = normalize_shall_will(text, shall_preference)
    text = normalize_number_words(text)
    text = normalize_efforts_standard(text)
    text = remove_archaisms(text)
    if defined_terms:
        text = format_defined_term_first_use(text, defined_terms)
    return text
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_style_rules.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/services/drafting/style_rules.py backend/tests/test_style_rules.py
git commit -m "feat(drafting): add deterministic style enforcer (shall/will, number-words, efforts, archaisms)"
```

---

### Task 2: Add Consistency Engine (Deterministic Checks)

**Files:**
- Create: `backend/app/services/drafting/consistency_engine.py`
- Test: `backend/tests/test_consistency_engine.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_consistency_engine.py
from __future__ import annotations
import pytest
from app.services.drafting.models import DraftSection, RawDraft, DraftMetadata, Annotation
from app.services.drafting.consistency_engine import ConsistencyEngine


def _make_draft(sections, defined_terms=None):
    return RawDraft(
        contract_type="nda_mutual",
        title="Test NDA",
        sections=sections,
        defined_terms=defined_terms or {},
        metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=0.1, tokens_used=0),
    )


def test_undefined_terms_detected():
    sections = [
        DraftSection(section_number="1", heading="Definitions", content='The "Confidential Information" means all data.'),
        DraftSection(section_number="2", heading="Obligations", content='The Receiving Party shall protect all Derivative Works.'),
    ]
    draft = _make_draft(sections, {"Confidential Information": "all data"})
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    issues = [a for a in annotations if "Derivative Works" in a.issue]
    assert len(issues) >= 1


def test_cross_reference_valid():
    sections = [
        DraftSection(section_number="1", heading="Definitions", content="See Section 2 for details."),
        DraftSection(section_number="2", heading="Details", content="The details are here."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    xref_issues = [a for a in annotations if "cross-reference" in a.issue.lower()]
    assert len(xref_issues) == 0


def test_cross_reference_broken():
    sections = [
        DraftSection(section_number="1", heading="Definitions", content="See Section 5 for details."),
        DraftSection(section_number="2", heading="Details", content="As per Section 9."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    xref_issues = [a for a in annotations if "cross-reference" in a.issue.lower()]
    assert len(xref_issues) >= 1


def test_party_name_consistency():
    sections = [
        DraftSection(section_number="1", heading="Preamble", content="Acme Inc. (the Company) and Beta LLC (the Vendor)"),
        DraftSection(section_number="2", heading="Terms", content="The Supplier shall deliver goods to the Company."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    name_issues = [a for a in annotations if "party" in a.issue.lower() or "inconsistent" in a.issue.lower()]
    # "Supplier" was not defined in preamble — "Vendor" was
    assert len(name_issues) >= 1


def test_number_word_mismatch():
    sections = [
        DraftSection(section_number="1", heading="Term", content="This Agreement shall last for twenty (30) days."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    num_issues = [a for a in annotations if "number" in a.issue.lower() or "mismatch" in a.issue.lower()]
    assert len(num_issues) >= 1


def test_placeholder_leftover():
    sections = [
        DraftSection(section_number="1", heading="Parties", content="This Agreement between {{party_1_name}} and Acme."),
    ]
    draft = _make_draft(sections)
    engine = ConsistencyEngine()
    annotations = engine.check(draft)
    ph_issues = [a for a in annotations if "placeholder" in a.issue.lower()]
    assert len(ph_issues) >= 1
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_consistency_engine.py -v`
Expected: FAIL (module not found)

**Step 3: Implement consistency_engine.py**

```python
# backend/app/services/drafting/consistency_engine.py
"""
Deterministic cross-clause consistency engine.
Validates defined terms, cross-references, party names, and numeric consistency.
No LLM calls — pure logic.
"""
from __future__ import annotations

import re
from typing import List, Set

from app.services.drafting.models import Annotation, RawDraft

_SECTION_REF_RE = re.compile(r'Section\s+(\d+(?:\.\d+)?)', re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r'\{\{[^}]+\}\}')
_QUOTED_TERM_RE = re.compile(r'["\u201c]([A-Z][A-Za-z\s]+?)["\u201d]')
_CAP_TERM_RE = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
_NUM_WORD_RE = re.compile(
    r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
    r'thirteen|fourteen|fifteen|eighteen|twenty|twenty-four|thirty|'
    r'forty-five|sixty|ninety)\s*\((\d+)\)',
    re.IGNORECASE,
)
_PARTY_ROLE_RE = re.compile(
    r'\((?:the\s+)?["\u201c]?([A-Z][A-Za-z\s]+?)["\u201d]?\)',
)

_WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "eighteen": 18, "twenty": 20, "twenty-four": 24,
    "thirty": 30, "forty-five": 45, "sixty": 60, "ninety": 90,
}

_COMMON_LEGAL = frozenset({
    "Agreement", "Party", "Parties", "United States", "Effective Date",
    "Business Day", "New York", "State", "Federal", "Annual", "General",
    "Third Party", "Prior Written", "Written Consent", "Material Breach",
    "Intellectual Property", "Trade Secret", "Good Faith",
})


class ConsistencyEngine:
    """Run all deterministic consistency checks on a draft."""

    def check(self, draft: RawDraft) -> List[Annotation]:
        annotations: List[Annotation] = []
        annotations.extend(self._check_cross_references(draft))
        annotations.extend(self._check_undefined_terms(draft))
        annotations.extend(self._check_placeholders(draft))
        annotations.extend(self._check_number_word_consistency(draft))
        annotations.extend(self._check_party_names(draft))
        return annotations

    def _check_cross_references(self, draft: RawDraft) -> List[Annotation]:
        """Verify all 'Section N' references point to existing sections."""
        valid_numbers = {s.section_number for s in draft.sections}
        issues: List[Annotation] = []
        for s in draft.sections:
            for m in _SECTION_REF_RE.finditer(s.content):
                ref = m.group(1)
                if ref not in valid_numbers:
                    issues.append(Annotation(
                        section_number=s.section_number,
                        agent="consistency",
                        severity="warning",
                        issue=f"Broken cross-reference: Section {ref} does not exist",
                        suggested_fix=None,
                        reasoning=f"Section {s.section_number} references Section {ref} but valid sections are: {sorted(valid_numbers)}",
                    ))
        return issues

    def _check_undefined_terms(self, draft: RawDraft) -> List[Annotation]:
        """Find capitalized terms used but not defined."""
        defined = set(draft.defined_terms.keys())
        all_text = " ".join(s.content for s in draft.sections)

        # Collect quoted defined terms from text
        for m in _QUOTED_TERM_RE.finditer(all_text):
            defined.add(m.group(1).strip())

        # Find all capitalized multi-word terms
        used_terms: Set[str] = set()
        for m in _CAP_TERM_RE.finditer(all_text):
            term = m.group(1).strip()
            if term not in _COMMON_LEGAL:
                used_terms.add(term)

        issues: List[Annotation] = []
        for term in sorted(used_terms - defined):
            # Find which section uses it
            for s in draft.sections:
                if term in s.content:
                    issues.append(Annotation(
                        section_number=s.section_number,
                        agent="consistency",
                        severity="warning",
                        issue=f"Potentially undefined term: '{term}' used but not found in defined terms",
                        suggested_fix=None,
                        reasoning="Capitalized multi-word term not matched to a definition. May need defining or may be a proper noun.",
                    ))
                    break
        return issues

    def _check_placeholders(self, draft: RawDraft) -> List[Annotation]:
        """Find unfilled {{placeholder}} patterns."""
        issues: List[Annotation] = []
        for s in draft.sections:
            for m in _PLACEHOLDER_RE.finditer(s.content):
                issues.append(Annotation(
                    section_number=s.section_number,
                    agent="consistency",
                    severity="critical",
                    issue=f"Unfilled placeholder: {m.group()}",
                    suggested_fix=None,
                    reasoning="Template placeholder was not resolved during generation.",
                ))
        return issues

    def _check_number_word_consistency(self, draft: RawDraft) -> List[Annotation]:
        """Check that 'twenty (30)' type mismatches are caught."""
        issues: List[Annotation] = []
        for s in draft.sections:
            for m in _NUM_WORD_RE.finditer(s.content):
                word = m.group(1).lower()
                num = int(m.group(2))
                expected = _WORD_TO_NUM.get(word)
                if expected is not None and expected != num:
                    issues.append(Annotation(
                        section_number=s.section_number,
                        agent="consistency",
                        severity="critical",
                        issue=f"Number-word mismatch: '{m.group(1)}' ({num}) — word says {expected} but number says {num}",
                        suggested_fix=f"Change to '{m.group(1)} ({expected})' or update the word",
                        reasoning="Inconsistent number-word pair creates ambiguity about the intended value.",
                    ))
        return issues

    def _check_party_names(self, draft: RawDraft) -> List[Annotation]:
        """Check that party role names are used consistently."""
        # Extract defined party roles from preamble (first 2 sections)
        preamble_text = " ".join(s.content for s in draft.sections[:2])
        defined_roles: Set[str] = set()
        for m in _PARTY_ROLE_RE.finditer(preamble_text):
            role = m.group(1).strip().strip('""\u201c\u201d')
            if len(role) > 2:
                defined_roles.add(role)

        if not defined_roles:
            return []

        # Common party synonyms that might indicate inconsistency
        _ROLE_SYNONYMS = {
            "Company": {"Corporation", "Firm", "Enterprise", "Employer"},
            "Vendor": {"Supplier", "Provider", "Contractor", "Seller"},
            "Customer": {"Client", "Buyer", "Purchaser", "User"},
            "Licensor": {"Supplier", "Provider"},
            "Licensee": {"Customer", "User", "Client"},
        }

        # Build set of synonyms NOT in defined roles
        suspect_terms: dict[str, str] = {}
        for role in defined_roles:
            synonyms = _ROLE_SYNONYMS.get(role, set())
            for syn in synonyms:
                if syn not in defined_roles:
                    suspect_terms[syn] = role

        issues: List[Annotation] = []
        for s in draft.sections[2:]:  # Skip preamble
            for suspect, correct in suspect_terms.items():
                if re.search(rf'\b{re.escape(suspect)}\b', s.content):
                    issues.append(Annotation(
                        section_number=s.section_number,
                        agent="consistency",
                        severity="warning",
                        issue=f"Inconsistent party reference: '{suspect}' used but preamble defines '{correct}'",
                        suggested_fix=f"Replace '{suspect}' with '{correct}'",
                        reasoning=f"Party roles should be consistent throughout. Preamble defines: {sorted(defined_roles)}",
                    ))
        return issues
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_consistency_engine.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/services/drafting/consistency_engine.py backend/tests/test_consistency_engine.py
git commit -m "feat(drafting): add deterministic consistency engine (cross-refs, defined terms, party names, numbers)"
```

---

### Task 3: Wire Style Enforcer + Consistency Engine into Pipeline

**Files:**
- Modify: `backend/app/services/drafting/orchestrator.py`
- Modify: `backend/app/services/drafting/assembler.py`
- Test: `backend/tests/test_orchestrator.py` (update existing)

**Step 1: Write failing test**

```python
# Add to backend/tests/test_orchestrator.py
@pytest.mark.asyncio
async def test_orchestrator_applies_style_rules():
    """Style rules should be applied to all section content in the final draft."""
    from app.services.drafting.orchestrator import DraftingOrchestrator
    from app.services.drafting.models import DraftSection, RawDraft, DraftMetadata, FinalDraft

    orch = DraftingOrchestrator()

    # Create a draft with style issues
    raw = RawDraft(
        contract_type="nda_mutual",
        title="Test",
        sections=[
            DraftSection(section_number="1", heading="Term",
                         content="The Company will deliver within 30 days using best efforts."),
        ],
        defined_terms={},
        metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=0.1, tokens_used=0),
    )

    # Mock all agents to return this draft directly
    with patch.object(orch._intake, 'process') as mock_intake, \
         patch.object(orch._drafter, 'generate', return_value=raw) as mock_draft, \
         patch.object(orch._risk, 'review', return_value=[]) as mock_risk, \
         patch.object(orch._compliance, 'review', return_value=[]) as mock_comp:

        mock_intake.return_value = (_make_nda_request(), {"name": "test", "clauses": []})
        result = await orch.run({"contract_type": "nda_mutual", "party_1": {"name": "A", "entity_type": "Inc", "jurisdiction": "US-DE"}, "party_2": {"name": "B", "entity_type": "LLC", "jurisdiction": "US-CA"}, "term_months": 12, "governing_law": "Delaware"})

    content = result.draft.sections[0].content
    # Style rules should have normalized:
    assert "thirty (30) days" in content  # number-word normalization
    assert "reasonable efforts" in content  # efforts normalization
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_orchestrator.py::test_orchestrator_applies_style_rules -v`
Expected: FAIL

**Step 3: Wire into orchestrator**

In `backend/app/services/drafting/orchestrator.py`, add a Stage 5 after assembly:

```python
# Add imports at top:
from app.services.drafting.style_rules import apply_all_style_rules
from app.services.drafting.consistency_engine import ConsistencyEngine

# In __init__:
self._consistency = ConsistencyEngine()

# After Stage 4 (assembly), add Stage 5:
# ── Stage 5: Style enforcement + consistency checks ──
try:
    defined_set = set(result.draft.defined_terms.keys())
    for section in result.draft.sections:
        section.content = apply_all_style_rules(
            section.content, defined_terms=defined_set
        )
    consistency_annotations = self._consistency.check(result.draft)
    result.quality_report.open_annotations.extend(consistency_annotations)
    # Recompute scores with new annotations
    all_annotations = result.quality_report.open_annotations
    penalty = sum(
        15 if a.severity == "critical" else 5 if a.severity == "warning" else 1
        for a in all_annotations
    )
    result.quality_report.qa_score = max(0.0, 100.0 - penalty)
except Exception as exc:
    logger.warning("Style/consistency stage failed: %s", exc)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_orchestrator.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/services/drafting/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat(drafting): wire style enforcer and consistency engine into pipeline as Stage 5"
```

---

## Phase B: Clause-Level Risk + Jurisdiction Rules

### Task 4: Extend Models for Per-Clause Risk

**Files:**
- Modify: `backend/app/services/drafting/models.py`
- Modify: `backend/app/api/v1/endpoints/drafting.py`
- Test: `backend/tests/test_drafting_models.py` (add tests)

**Step 1: Write failing test**

```python
# Add to backend/tests/test_drafting_models.py
def test_draft_request_with_risk_profile():
    req = DraftRequest(
        contract_type="saas",
        drafting_perspective="party_1",
        risk_appetite="balanced",
        jurisdiction="US-DE",
        party_1=PartyInfo(name="Acme", entity_type="Inc", jurisdiction="US-DE"),
        party_2=PartyInfo(name="Beta", entity_type="LLC", jurisdiction="US-CA"),
        term_months=12,
        governing_law="Delaware",
        risk_profile={
            "indemnification": "protective",
            "limitation_of_liability": "balanced",
            "ip_ownership": "protective",
            "confidentiality": "balanced",
            "termination": "commercial",
        },
    )
    assert req.risk_profile["indemnification"] == "protective"
    assert req.risk_profile["limitation_of_liability"] == "balanced"


def test_draft_request_risk_profile_defaults_empty():
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_drafting_models.py::test_draft_request_with_risk_profile -v`
Expected: FAIL (no risk_profile field)

**Step 3: Add risk_profile to DraftRequest**

In `backend/app/services/drafting/models.py`, add to `DraftRequest`:
```python
    risk_profile: dict[str, str] = Field(default_factory=dict)
    negotiation_context: str = ""
```

In `backend/app/api/v1/endpoints/drafting.py`, add to `GenerateRequest`:
```python
    risk_profile: dict[str, str] = Field(default_factory=dict)
    negotiation_context: str = ""
```

And pass it through in `generate_draft`:
```python
    if req.risk_profile:
        raw_input["risk_profile"] = req.risk_profile
    if req.negotiation_context:
        raw_input["negotiation_context"] = req.negotiation_context
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_drafting_models.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/services/drafting/models.py backend/app/api/v1/endpoints/drafting.py backend/tests/test_drafting_models.py
git commit -m "feat(drafting): add per-clause risk_profile and negotiation_context to DraftRequest"
```

---

### Task 5: Update Tier Selection for Per-Clause Risk

**Files:**
- Modify: `backend/app/services/drafting/agents/draft_agent.py`
- Test: `backend/tests/test_draft_agent.py` (create)

**Step 1: Write failing test**

```python
# backend/tests/test_draft_agent.py
from __future__ import annotations
import pytest
from app.services.drafting.agents.draft_agent import DraftAgent


def test_select_tier_global_balanced():
    tier = DraftAgent._select_tier("balanced", "balanced", clause_category=None, risk_profile={})
    assert tier == "acceptable"


def test_select_tier_per_clause_override():
    tier = DraftAgent._select_tier(
        "balanced", "balanced",
        clause_category="indemnification",
        risk_profile={"indemnification": "protective"},
    )
    assert tier == "preferred"


def test_select_tier_per_clause_commercial():
    tier = DraftAgent._select_tier(
        "party_1", "protective",
        clause_category="boilerplate",
        risk_profile={"boilerplate": "commercial"},
    )
    assert tier == "fallback"


def test_select_tier_unknown_category_falls_back_to_global():
    tier = DraftAgent._select_tier(
        "party_1", "protective",
        clause_category="unknown_clause_type",
        risk_profile={"indemnification": "protective"},
    )
    # No override for this category -> use global
    assert tier == "preferred"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_draft_agent.py -v`
Expected: FAIL (wrong signature)

**Step 3: Update _select_tier**

In `backend/app/services/drafting/agents/draft_agent.py`, update `_select_tier`:

```python
@staticmethod
def _select_tier(
    perspective: str,
    risk_appetite: str,
    clause_category: str | None = None,
    risk_profile: dict[str, str] | None = None,
) -> str:
    """Select clause tier based on per-clause risk profile or global settings."""
    # Per-clause override takes priority
    if risk_profile and clause_category and clause_category in risk_profile:
        override = risk_profile[clause_category].lower()
        return {"protective": "preferred", "balanced": "acceptable", "commercial": "fallback", "aggressive": "fallback"}.get(override, "acceptable")

    # Global fallback
    if perspective == "balanced":
        return "acceptable"
    if risk_appetite in ("protective",):
        return "preferred"
    if risk_appetite in ("commercial", "aggressive"):
        return "fallback"
    return "acceptable"
```

Update the call site in `generate()` to pass `clause_category` and `risk_profile`:

```python
tier = self._select_tier(
    req.drafting_perspective,
    req.risk_appetite,
    clause_category=clause_def.get("category", clause_def.get("clause_type")),
    risk_profile=req.risk_profile,
)
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_draft_agent.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/services/drafting/agents/draft_agent.py backend/tests/test_draft_agent.py
git commit -m "feat(drafting): per-clause risk profile tier selection"
```

---

### Task 6: Jurisdiction Rule Engine

**Files:**
- Create: `backend/app/services/drafting/jurisdiction_rules.py`
- Test: `backend/tests/test_jurisdiction_rules.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_jurisdiction_rules.py
from __future__ import annotations
import pytest
from app.services.drafting.jurisdiction_rules import (
    JurisdictionRuleEngine,
    JurisdictionFinding,
)
from app.services.drafting.models import DraftSection, RawDraft, DraftMetadata


def _make_draft(sections, jurisdiction="US-DE"):
    return RawDraft(
        contract_type="nda_mutual",
        title="Test",
        sections=sections,
        defined_terms={},
        metadata=DraftMetadata(playbook_id="test", model="test", generation_seconds=0.1, tokens_used=0),
    )


def test_california_non_compete_flagged():
    sections = [
        DraftSection(section_number="1", heading="Non-Competition",
                     content="Employee shall not compete with Company for 12 months after termination."),
    ]
    draft = _make_draft(sections, jurisdiction="US-CA")
    engine = JurisdictionRuleEngine()
    findings = engine.check(draft, jurisdiction="US-CA")
    assert any(f.severity == "critical" and "non-compete" in f.issue.lower() for f in findings)


def test_california_non_solicitation_flagged():
    sections = [
        DraftSection(section_number="1", heading="Non-Solicitation",
                     content="Party shall not solicit employees of the other Party for 24 months."),
    ]
    draft = _make_draft(sections, jurisdiction="US-CA")
    engine = JurisdictionRuleEngine()
    findings = engine.check(draft, jurisdiction="US-CA")
    assert any("non-solicit" in f.issue.lower() or "solicit" in f.issue.lower() for f in findings)


def test_india_stamp_duty_noted():
    sections = [
        DraftSection(section_number="1", heading="Execution", content="This Agreement is executed in Mumbai."),
    ]
    engine = JurisdictionRuleEngine()
    findings = engine.check(_make_draft(sections), jurisdiction="IN")
    assert any("stamp" in f.issue.lower() for f in findings)


def test_gdpr_dpa_required_for_eu():
    sections = [
        DraftSection(section_number="1", heading="Services", content="Provider processes personal data of EU residents."),
    ]
    engine = JurisdictionRuleEngine()
    findings = engine.check(_make_draft(sections), jurisdiction="GB", contract_type="saas")
    assert any("data protection" in f.issue.lower() or "gdpr" in f.issue.lower() for f in findings)


def test_delaware_no_special_flags():
    sections = [
        DraftSection(section_number="1", heading="Confidentiality", content="Standard confidentiality clause."),
    ]
    engine = JurisdictionRuleEngine()
    findings = engine.check(_make_draft(sections), jurisdiction="US-DE")
    critical = [f for f in findings if f.severity == "critical"]
    assert len(critical) == 0
```

**Step 2: Run test**

Run: `cd backend && python -m pytest tests/test_jurisdiction_rules.py -v`
Expected: FAIL

**Step 3: Implement jurisdiction_rules.py**

```python
# backend/app/services/drafting/jurisdiction_rules.py
"""
Hard-coded jurisdiction-specific rule engine.
Safety net below the LLM — catches enforceability issues deterministically.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from app.services.drafting.models import Annotation, RawDraft


@dataclass
class JurisdictionFinding:
    section_number: str
    severity: str  # critical, high, warning, info
    issue: str
    statute: str
    action: str  # REMOVE_CLAUSE, FLAG_FOR_REVIEW, ADD_CLAUSE, ADD_NOTE
    suggested_fix: Optional[str] = None


# ── Clause detection patterns ───────────────────────────────────────

_NON_COMPETE_RE = re.compile(
    r'\b(non[- ]?compet[ei]|shall not compete|refrain from competing|'
    r'restrictive covenant|compete with|competitive activit)',
    re.IGNORECASE,
)
_NON_SOLICIT_RE = re.compile(
    r'\b(non[- ]?solicit|shall not solicit|refrain from soliciting|'
    r'not.*solicit.*employees|not.*recruit)',
    re.IGNORECASE,
)
_PERSONAL_DATA_RE = re.compile(
    r'\b(personal data|personal information|PII|data subject|'
    r'data controller|data processor|GDPR|CCPA|DPDP)',
    re.IGNORECASE,
)
_LIABILITY_CAP_RE = re.compile(
    r'\b(limitation of liability|liability.*cap|aggregate liability|'
    r'total liability.*not exceed|maximum.*liability)',
    re.IGNORECASE,
)

# ── Jurisdiction rules database ─────────────────────────────────────

_RULES = {
    "US-CA": {
        "non_compete": {
            "pattern": _NON_COMPETE_RE,
            "severity": "critical",
            "statute": "Cal. B&P Code Section 16600",
            "issue": "Non-compete clause is VOID under California law (B&P Code 16600). California prohibits all non-compete agreements regardless of where signed.",
            "action": "REMOVE_CLAUSE",
            "fix": "Remove non-compete provision entirely. Use confidentiality + trade secret protections instead.",
        },
        "non_solicit": {
            "pattern": _NON_SOLICIT_RE,
            "severity": "high",
            "statute": "Cal. B&P Code Section 16600 (2024 amendment)",
            "issue": "Non-solicitation clause is restricted under California law. Post-2024, most non-solicitation provisions are void.",
            "action": "FLAG_FOR_REVIEW",
            "fix": "Narrow to customer non-solicitation (not employee) or remove. Consult CA employment counsel.",
        },
    },
    "US-NY": {
        "non_compete": {
            "pattern": _NON_COMPETE_RE,
            "severity": "warning",
            "statute": "NY common law reasonableness test",
            "issue": "Non-compete must be reasonable in scope, duration, and geography under NY law. Courts scrutinize heavily.",
            "action": "FLAG_FOR_REVIEW",
            "fix": "Ensure scope is narrow, duration is 12 months or less, and geographic scope is limited.",
        },
    },
    "IN": {
        "non_compete": {
            "pattern": _NON_COMPETE_RE,
            "severity": "high",
            "statute": "Indian Contract Act Section 27",
            "issue": "Post-employment non-compete is VOID under Indian Contract Act S.27. Only enforceable during employment.",
            "action": "FLAG_FOR_REVIEW",
            "fix": "Limit non-compete to employment term only. Post-employment non-competes are unenforceable.",
        },
        "stamp_duty": {
            "pattern": None,  # Always applicable
            "severity": "warning",
            "statute": "Indian Stamp Act 1899",
            "issue": "Contract governed by Indian law requires stamp duty. Amount varies by state (Maharashtra, Delhi, Karnataka have different rates). Unstamped agreements are inadmissible as evidence.",
            "action": "ADD_NOTE",
            "fix": "Add stamp duty acknowledgment clause. Verify applicable state stamp duty rate before execution.",
        },
    },
    "GB": {
        "unfair_terms": {
            "pattern": _LIABILITY_CAP_RE,
            "severity": "warning",
            "statute": "Unfair Contract Terms Act 1977 / Consumer Rights Act 2015",
            "issue": "Limitation of liability for negligence causing death/injury is void under UCTA S.2(1). Other liability exclusions must pass reasonableness test.",
            "action": "FLAG_FOR_REVIEW",
            "fix": "Ensure liability cap carves out death/personal injury. Other caps must be reasonable and proportionate.",
        },
        "data_protection": {
            "pattern": _PERSONAL_DATA_RE,
            "severity": "high",
            "statute": "UK GDPR / Data Protection Act 2018",
            "issue": "Processing of personal data requires UK GDPR-compliant data processing agreement with mandatory provisions.",
            "action": "FLAG_FOR_REVIEW",
            "fix": "Ensure DPA includes: lawful basis, data subject rights, breach notification (72h), international transfer safeguards.",
        },
    },
    "SG": {
        "data_protection": {
            "pattern": _PERSONAL_DATA_RE,
            "severity": "warning",
            "statute": "Personal Data Protection Act 2012 (PDPA)",
            "issue": "Collection/use of personal data requires compliance with Singapore PDPA consent and notification requirements.",
            "action": "FLAG_FOR_REVIEW",
            "fix": "Add PDPA consent acknowledgment. Ensure data protection obligations reference PDPA requirements.",
        },
    },
}

# Rules that apply to ALL jurisdictions
_GLOBAL_RULES = {
    "saas": {
        "data_processing": {
            "pattern": _PERSONAL_DATA_RE,
            "severity": "warning",
            "statute": "General best practice",
            "issue": "SaaS agreement references personal data but may lack a formal Data Processing Agreement (DPA).",
            "action": "FLAG_FOR_REVIEW",
            "fix": "Consider adding a DPA as an exhibit addressing: data categories, processing purposes, security measures, sub-processors, breach notification.",
        },
    },
}


class JurisdictionRuleEngine:
    """Check a draft against jurisdiction-specific hard rules."""

    def check(
        self,
        draft: RawDraft,
        jurisdiction: str = "US-DE",
        contract_type: str | None = None,
    ) -> List[JurisdictionFinding]:
        findings: List[JurisdictionFinding] = []
        ct = contract_type or draft.contract_type
        rules = _RULES.get(jurisdiction, {})

        for rule_name, rule in rules.items():
            pattern = rule.get("pattern")
            if pattern is None:
                # Always-applicable rule (e.g., stamp duty)
                findings.append(JurisdictionFinding(
                    section_number="*",
                    severity=rule["severity"],
                    issue=rule["issue"],
                    statute=rule["statute"],
                    action=rule["action"],
                    suggested_fix=rule.get("fix"),
                ))
                continue

            for section in draft.sections:
                if pattern.search(section.content):
                    findings.append(JurisdictionFinding(
                        section_number=section.section_number,
                        severity=rule["severity"],
                        issue=rule["issue"],
                        statute=rule["statute"],
                        action=rule["action"],
                        suggested_fix=rule.get("fix"),
                    ))
                    break  # One finding per rule

        # Check global (contract-type-specific) rules
        global_rules = _GLOBAL_RULES.get(ct, {})
        for rule_name, rule in global_rules.items():
            pattern = rule.get("pattern")
            if pattern:
                all_text = " ".join(s.content for s in draft.sections)
                if pattern.search(all_text):
                    findings.append(JurisdictionFinding(
                        section_number="*",
                        severity=rule["severity"],
                        issue=rule["issue"],
                        statute=rule["statute"],
                        action=rule["action"],
                        suggested_fix=rule.get("fix"),
                    ))

        return findings

    def to_annotations(self, findings: List[JurisdictionFinding]) -> List[Annotation]:
        """Convert findings to Annotation objects for the pipeline."""
        return [
            Annotation(
                section_number=f.section_number,
                agent="jurisdiction",
                severity=f.severity if f.severity != "high" else "warning",
                issue=f"[{f.statute}] {f.issue}",
                suggested_fix=f.suggested_fix,
                reasoning=f"Action: {f.action}",
            )
            for f in findings
        ]
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_jurisdiction_rules.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/services/drafting/jurisdiction_rules.py backend/tests/test_jurisdiction_rules.py
git commit -m "feat(drafting): add jurisdiction rule engine (CA non-compete, IN stamp duty, GB UCTA, GDPR)"
```

---

### Task 7: Wire Jurisdiction Rules into Orchestrator

**Files:**
- Modify: `backend/app/services/drafting/orchestrator.py`

**Step 1: Add jurisdiction check after Stage 3 (parallel review)**

```python
# Add import:
from app.services.drafting.jurisdiction_rules import JurisdictionRuleEngine

# In __init__:
self._jurisdiction = JurisdictionRuleEngine()

# After Stage 3, before Stage 4 (assembly):
jurisdiction_findings = self._jurisdiction.check(
    raw_draft,
    jurisdiction=request.jurisdiction,
    contract_type=request.contract_type,
)
all_annotations.extend(self._jurisdiction.to_annotations(jurisdiction_findings))
```

**Step 2: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v -k "drafting or orchestrator or assembler or consistency or style or jurisdiction"`
Expected: All PASS

**Step 3: Commit**

```bash
git add backend/app/services/drafting/orchestrator.py
git commit -m "feat(drafting): wire jurisdiction rule engine into orchestrator pipeline"
```

---

## Phase C: Enhanced Compliance + AI Cross-Clause Checks

### Task 8: Add Compliance Hard Rules to Compliance Agent

**Files:**
- Create: `backend/app/services/drafting/compliance_rules.py`
- Modify: `backend/app/services/drafting/agents/compliance_agent.py`
- Test: `backend/tests/test_compliance_rules.py`

This task adds a deterministic compliance rule engine that runs BEFORE the LLM call in the compliance agent, providing a safety net.

**Step 1: Write failing tests**

```python
# backend/tests/test_compliance_rules.py
from __future__ import annotations
import pytest
from app.services.drafting.compliance_rules import ComplianceRuleEngine


def test_liability_cap_reasonableness_flagged():
    engine = ComplianceRuleEngine()
    findings = engine.check_liability_cap(
        cap_months=1,
        contract_value_annual=120000,
        has_ip_carveout=False,
        has_confidentiality_carveout=False,
    )
    assert any("below market" in f.lower() or "carve-out" in f.lower() for f in findings)


def test_liability_cap_reasonable():
    engine = ComplianceRuleEngine()
    findings = engine.check_liability_cap(
        cap_months=12,
        contract_value_annual=120000,
        has_ip_carveout=True,
        has_confidentiality_carveout=True,
    )
    critical = [f for f in findings if "critical" in f.lower()]
    assert len(critical) == 0


def test_gdpr_dpa_completeness():
    engine = ComplianceRuleEngine()
    present = {"processing_on_instructions", "security_measures", "audit_rights"}
    required = engine.GDPR_ARTICLE_28_REQUIREMENTS
    missing = engine.check_gdpr_completeness(present)
    assert len(missing) > 0  # Not all requirements met
    assert "sub_processor_management" in missing or "breach_notification" in missing


def test_efforts_standard_consistency():
    engine = ComplianceRuleEngine()
    texts = ["use best efforts to deliver", "use commercially reasonable efforts to notify"]
    findings = engine.check_efforts_consistency(texts)
    assert len(findings) >= 1  # Inconsistent standards
```

**Step 2: Implement compliance_rules.py**

```python
# backend/app/services/drafting/compliance_rules.py
"""
Deterministic compliance rules engine — safety net below LLM compliance checks.
Based on ACC guidelines and market standards.
"""
from __future__ import annotations

import re
from typing import List, Set


class ComplianceRuleEngine:
    """Hard-coded compliance rules for contract provisions."""

    GDPR_ARTICLE_28_REQUIREMENTS = frozenset({
        "processing_on_instructions",
        "confidentiality_obligations",
        "security_measures",
        "sub_processor_management",
        "data_subject_rights",
        "deletion_on_termination",
        "audit_rights",
        "breach_notification",
    })

    _EFFORTS_RE = re.compile(
        r'\b(best\s+efforts|commercially\s+reasonable\s+efforts|'
        r'reasonable\s+efforts|reasonable\s+best\s+efforts)\b',
        re.IGNORECASE,
    )

    def check_liability_cap(
        self,
        cap_months: int,
        contract_value_annual: float = 0,
        has_ip_carveout: bool = False,
        has_confidentiality_carveout: bool = False,
        has_gross_negligence_carveout: bool = False,
    ) -> List[str]:
        """Check liability cap against market standards (ACC 10-point test)."""
        findings = []

        # Market standard: 12 months fees (1x annual)
        if cap_months < 3:
            findings.append(
                f"CRITICAL: Liability cap of {cap_months} months is below market standard "
                f"(typical: 12 months / 1x annual value). Per ACC guidelines, "
                f"courts may void unreasonably low caps as unconscionable."
            )
        elif cap_months < 12:
            findings.append(
                f"WARNING: Liability cap of {cap_months} months is below median market "
                f"standard of 12 months for enterprise contracts."
            )

        if not has_ip_carveout:
            findings.append(
                "WARNING: No IP infringement carve-out from liability cap. "
                "Market standard is to carve out IP indemnification obligations "
                "(either uncapped or with a super-cap of 2-5x)."
            )

        if not has_confidentiality_carveout:
            findings.append(
                "WARNING: No confidentiality breach carve-out from liability cap. "
                "Market standard for data-intensive agreements is to exclude "
                "confidentiality/data breach from the general cap."
            )

        if not has_gross_negligence_carveout:
            findings.append(
                "INFO: No gross negligence/willful misconduct carve-out. "
                "Most jurisdictions void liability limits for gross negligence."
            )

        return findings

    def check_gdpr_completeness(self, present_provisions: Set[str]) -> Set[str]:
        """Return GDPR Article 28 provisions that are missing."""
        return self.GDPR_ARTICLE_28_REQUIREMENTS - present_provisions

    def check_efforts_consistency(self, clause_texts: List[str]) -> List[str]:
        """Flag inconsistent efforts standards across clauses."""
        standards_found = set()
        for text in clause_texts:
            for m in self._EFFORTS_RE.finditer(text):
                standards_found.add(m.group(0).lower().strip())

        if len(standards_found) > 1:
            return [
                f"Inconsistent efforts standards found: {sorted(standards_found)}. "
                f"Per Ken Adams (MSCD), use 'reasonable efforts' consistently "
                f"and structure provisions to minimize vagueness."
            ]
        return []
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_compliance_rules.py -v`
Expected: All PASS

**Step 4: Wire into compliance_agent.py**

In `backend/app/services/drafting/agents/compliance_agent.py`, add before the LLM call:

```python
from app.services.drafting.compliance_rules import ComplianceRuleEngine
_rules = ComplianceRuleEngine()

# In review():
# Run deterministic rules first
rule_annotations = self._run_hard_rules(draft, jurisdiction)
# Then run LLM review
ai_annotations = await self._ai_review(draft, jurisdiction)
return rule_annotations + ai_annotations
```

**Step 5: Commit**

```bash
git add backend/app/services/drafting/compliance_rules.py backend/tests/test_compliance_rules.py backend/app/services/drafting/agents/compliance_agent.py
git commit -m "feat(drafting): add deterministic compliance rule engine (liability caps, GDPR, efforts)"
```

---

## Phase D: Feedback Loop + New Contract Types

### Task 9: Add Clause Category Metadata to Playbooks

**Files:**
- Modify: `backend/app/services/drafting/playbooks/nda_drafting.py`
- Modify: `backend/app/services/drafting/playbooks/saas_drafting.py`

Add a `"category"` key to each clause definition so per-clause risk selection works:

```python
# In each _clause() call, add category parameter:
# NDA clauses:
#   preamble -> "boilerplate"
#   recitals -> "boilerplate"
#   ci_definition -> "confidentiality"
#   ci_exclusions -> "confidentiality"
#   obligations -> "confidentiality"
#   permitted_disclosures -> "confidentiality"
#   compelled_disclosure -> "confidentiality"
#   term_duration -> "termination"
#   return_destruction -> "termination"
#   remedies -> "remedies"
#   no_license -> "ip_ownership"
#   governing_law -> "dispute_resolution"
#   non_solicitation -> "restrictive_covenants"
#   boilerplate -> "boilerplate"
#   signature -> "boilerplate"

# SaaS clauses:
#   indemnification -> "indemnification"
#   limitation_of_liability -> "limitation_of_liability"
#   ip_ownership -> "ip_ownership"
#   data_security -> "data_protection"
#   confidentiality -> "confidentiality"
#   fees_payment -> "commercial_terms"
#   term_termination -> "termination"
#   dispute_resolution -> "dispute_resolution"
#   reps_warranties -> "representations"
#   sla -> "commercial_terms"
#   dpa -> "data_protection"
```

**Step 1: Add `category` to the `_clause` helper**

In `nda_drafting.py`, update `_clause()` to accept and store `category`:

```python
def _clause(
    clause_type: str,
    heading: str,
    tiers: Dict[str, Any],
    *,
    category: str = "general",
    # ... existing params ...
) -> Dict[str, Any]:
    return {
        "clause_type": clause_type,
        "heading": heading,
        "category": category,
        "tiers": tiers,
        # ... rest ...
    }
```

**Step 2: Add category to every clause call in both playbook files**

This is a systematic edit across ~40 clause definitions.

**Step 3: Commit**

```bash
git add backend/app/services/drafting/playbooks/nda_drafting.py backend/app/services/drafting/playbooks/saas_drafting.py
git commit -m "feat(drafting): add clause categories to all playbook definitions for per-clause risk selection"
```

---

### Task 10: Add MSA + Employment Contract Playbooks (Stubs)

**Files:**
- Create: `backend/app/services/drafting/playbooks/msa_drafting.py`
- Create: `backend/app/services/drafting/playbooks/employment_drafting.py`
- Modify: `backend/app/services/drafting/agents/intake_agent.py`

These are structural stubs that follow the same pattern as existing playbooks. Populate with top-10 clauses each.

**Step 1: Create MSA playbook with key sections**

Sections: Preamble, Definitions, Services, SOW Structure, Fees, IP, Confidentiality, Indemnification, Liability, Insurance, Term, Termination, Dispute, Boilerplate, Signatures

**Step 2: Create Employment playbook with key sections**

Sections: Preamble, Position & Duties, Compensation, Benefits, Work Hours, Confidentiality, IP Assignment, Non-Compete (jurisdiction-aware), Termination, Governing Law

**Step 3: Register in intake_agent.py**

```python
from app.services.drafting.playbooks.msa_drafting import MSA_PLAYBOOK
from app.services.drafting.playbooks.employment_drafting import EMPLOYMENT_PLAYBOOK

PLAYBOOK_REGISTRY = {
    "nda_mutual": NDA_MUTUAL_PLAYBOOK,
    "nda_unilateral": NDA_UNILATERAL_PLAYBOOK,
    "saas": SAAS_PLAYBOOK,
    "msa": MSA_PLAYBOOK,
    "employment": EMPLOYMENT_PLAYBOOK,
}
VALID_CONTRACT_TYPES = frozenset(PLAYBOOK_REGISTRY.keys())
```

**Step 4: Commit**

```bash
git add backend/app/services/drafting/playbooks/msa_drafting.py backend/app/services/drafting/playbooks/employment_drafting.py backend/app/services/drafting/agents/intake_agent.py
git commit -m "feat(drafting): add MSA and Employment contract playbooks (5 contract types total)"
```

---

## Integration Summary

After all tasks, the pipeline becomes:

```
Stage 1: IntakeAgent (unchanged)
Stage 2: DraftAgent (per-clause tier selection via risk_profile)
Stage 3: PARALLEL [RiskAgent, ComplianceAgent (rule+LLM hybrid), QAAgent, JurisdictionRuleEngine]
Stage 4: Assembler (unchanged)
Stage 5: StyleEnforcer + ConsistencyEngine (NEW — deterministic post-processing)
```

**New modules added**: 5 files, ~800 lines
**New tests added**: 5 test files, ~300 lines
**Playbooks extended**: categories on all ~40 clauses + 2 new playbooks
**Contract types**: 3 → 5 (NDA mutual, NDA unilateral, SaaS, MSA, Employment)

---

## Testing Strategy

Run full suite after each task:
```bash
cd backend && python -m pytest tests/ -v -k "drafting or orchestrator or assembler or consistency or style or jurisdiction or compliance_rules or draft_agent"
```

End-to-end smoke test after Phase B:
```bash
cd backend && python -c "
import asyncio
from app.services.drafting.orchestrator import drafting_orchestrator
result = asyncio.run(drafting_orchestrator.run({
    'contract_type': 'nda_mutual',
    'party_1': {'name': 'Acme Inc.', 'entity_type': 'Inc.', 'jurisdiction': 'US-DE'},
    'party_2': {'name': 'Beta LLC', 'entity_type': 'LLC', 'jurisdiction': 'US-CA'},
    'term_months': 12,
    'governing_law': 'California',
    'risk_profile': {'confidentiality': 'protective', 'restrictive_covenants': 'commercial'},
}))
print(f'Score: {result.quality_report.overall_score}')
print(f'Annotations: {len(result.quality_report.open_annotations)}')
for a in result.quality_report.open_annotations:
    print(f'  [{a.agent}] {a.severity}: {a.issue[:80]}')
"
```
