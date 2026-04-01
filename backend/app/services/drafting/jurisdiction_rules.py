"""Deterministic jurisdiction-specific rule engine.

Hard-coded rules that catch enforceability issues without relying on the LLM.
Acts as a safety net below the AI review agents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.drafting.models import RawDraft

from app.services.drafting.models import Annotation

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class JurisdictionFinding:
    section_number: str
    severity: str          # critical, warning, info
    issue: str
    statute: str
    action: str            # REMOVE_CLAUSE, FLAG_FOR_REVIEW, ADD_NOTE
    suggested_fix: str | None = None


# ---------------------------------------------------------------------------
# Regex patterns for clause detection
# ---------------------------------------------------------------------------

_NON_COMPETE_RE = re.compile(
    r"(non[- ]?compete|shall not compete|restrictive covenant|covenant not to compete|"
    r"refrain from competing|agree not to compete)",
    re.IGNORECASE,
)

_NON_SOLICIT_RE = re.compile(
    r"(non[- ]?solicit|shall not solicit|refrain from soliciting|"
    r"agree not to solicit|non[- ]?solicitation)",
    re.IGNORECASE,
)

_PERSONAL_DATA_RE = re.compile(
    r"(personal data|personally identifiable information|\bPII\b|\bGDPR\b|\bCCPA\b|"
    r"data subject|personal information)",
    re.IGNORECASE,
)

_LIABILITY_CAP_RE = re.compile(
    r"(limitation of liability|liability cap|aggregate liability|"
    r"maximum liability|cap on liability|total liability shall not exceed)",
    re.IGNORECASE,
)

_NEGLIGENCE_DEATH_RE = re.compile(
    r"(negligence|death|personal injury)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Jurisdiction-specific rules
# ---------------------------------------------------------------------------
# Each rule is a callable: (sections_text, section_number) -> list[JurisdictionFinding]
# The engine iterates sections and applies all rules for the given jurisdiction.

def _us_ca_rules(section_number: str, text: str) -> list[JurisdictionFinding]:
    findings: list[JurisdictionFinding] = []
    if _NON_COMPETE_RE.search(text):
        findings.append(JurisdictionFinding(
            section_number=section_number,
            severity="critical",
            issue="Non-compete clause is VOID in California.",
            statute="Cal. Bus. & Prof. Code Section 16600",
            action="REMOVE_CLAUSE",
            suggested_fix="Remove the non-compete clause entirely or limit to trade-secret protection.",
        ))
    if _NON_SOLICIT_RE.search(text):
        findings.append(JurisdictionFinding(
            section_number=section_number,
            severity="warning",
            issue="Non-solicitation clause is restricted in California and may be unenforceable.",
            statute="Cal. Bus. & Prof. Code Section 16600",
            action="FLAG_FOR_REVIEW",
            suggested_fix="Narrow to customer non-solicitation with reasonable scope, or remove.",
        ))
    return findings


def _us_ny_rules(section_number: str, text: str) -> list[JurisdictionFinding]:
    findings: list[JurisdictionFinding] = []
    if _NON_COMPETE_RE.search(text):
        findings.append(JurisdictionFinding(
            section_number=section_number,
            severity="warning",
            issue="Non-compete must be reasonable in scope, duration, and geography under NY law.",
            statute="NY common law — reasonableness test",
            action="FLAG_FOR_REVIEW",
            suggested_fix="Ensure duration <= 2 years, limited geography, and narrow activity scope.",
        ))
    return findings


def _in_rules(section_number: str, text: str) -> list[JurisdictionFinding]:
    findings: list[JurisdictionFinding] = []
    if _NON_COMPETE_RE.search(text):
        findings.append(JurisdictionFinding(
            section_number=section_number,
            severity="critical",
            issue="Post-employment non-compete is void in India.",
            statute="Indian Contract Act, 1872, Section 27",
            action="REMOVE_CLAUSE",
            suggested_fix="Remove post-employment non-compete; use confidentiality and IP assignment clauses instead.",
        ))
    return findings


def _in_global_rules() -> list[JurisdictionFinding]:
    """Rules that apply to the entire contract for India, not per-section."""
    return [
        JurisdictionFinding(
            section_number="general",
            severity="warning",
            issue="Indian agreements may require stamp duty. Ensure proper stamping before execution.",
            statute="Indian Stamp Act, 1899",
            action="ADD_NOTE",
            suggested_fix="Verify applicable stamp duty for the state of execution and pay before signing.",
        )
    ]


def _gb_rules(section_number: str, text: str) -> list[JurisdictionFinding]:
    findings: list[JurisdictionFinding] = []
    if _LIABILITY_CAP_RE.search(text) and _NEGLIGENCE_DEATH_RE.search(text):
        findings.append(JurisdictionFinding(
            section_number=section_number,
            severity="warning",
            issue="UCTA: liability exclusion for negligence causing death or personal injury is void.",
            statute="Unfair Contract Terms Act 1977, Section 2(1)",
            action="FLAG_FOR_REVIEW",
            suggested_fix="Remove exclusion of liability for death/personal injury caused by negligence.",
        ))
    if _PERSONAL_DATA_RE.search(text):
        findings.append(JurisdictionFinding(
            section_number=section_number,
            severity="warning",
            issue="UK GDPR requires a lawful basis for data processing and a data processing agreement.",
            statute="UK GDPR, Articles 6 & 28",
            action="FLAG_FOR_REVIEW",
            suggested_fix="Include or reference a Data Processing Agreement (DPA) compliant with UK GDPR.",
        ))
    return findings


def _sg_rules(section_number: str, text: str) -> list[JurisdictionFinding]:
    findings: list[JurisdictionFinding] = []
    if _PERSONAL_DATA_RE.search(text):
        findings.append(JurisdictionFinding(
            section_number=section_number,
            severity="warning",
            issue="PDPA compliance required when processing personal data in Singapore.",
            statute="Personal Data Protection Act 2012 (PDPA)",
            action="FLAG_FOR_REVIEW",
            suggested_fix="Ensure consent, purpose limitation, and data protection obligations are documented.",
        ))
    return findings


# Registry: jurisdiction code -> list of per-section rule functions
_JURISDICTION_SECTION_RULES: dict[str, list] = {
    "US-CA": [_us_ca_rules],
    "US-NY": [_us_ny_rules],
    "IN":    [_in_rules],
    "GB":    [_gb_rules],
    "SG":    [_sg_rules],
}

# Registry: jurisdiction code -> list of global (whole-contract) rule functions
_JURISDICTION_GLOBAL_RULES: dict[str, list] = {
    "IN": [_in_global_rules],
}


# ---------------------------------------------------------------------------
# Contract-type global rules
# ---------------------------------------------------------------------------

def _saas_global_rules(sections_texts: list[str]) -> list[JurisdictionFinding]:
    """If any section mentions personal data in a SaaS contract, flag DPA need."""
    combined = " ".join(sections_texts)
    if _PERSONAL_DATA_RE.search(combined):
        return [JurisdictionFinding(
            section_number="general",
            severity="warning",
            issue="SaaS contract references personal data — a Data Processing Agreement (DPA) should be attached.",
            statute="General best practice / GDPR Art. 28",
            action="ADD_NOTE",
            suggested_fix="Attach a DPA as a schedule or exhibit to this agreement.",
        )]
    return []


_CONTRACT_TYPE_RULES: dict[str, list] = {
    "saas": [_saas_global_rules],
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class JurisdictionRuleEngine:
    """Run deterministic jurisdiction and contract-type rules against a draft."""

    def check(
        self,
        draft: "RawDraft",
        jurisdiction: str,
        contract_type: str,
    ) -> list[JurisdictionFinding]:
        findings: list[JurisdictionFinding] = []

        section_rules = _JURISDICTION_SECTION_RULES.get(jurisdiction, [])
        for section in draft.sections:
            for rule_fn in section_rules:
                findings.extend(rule_fn(section.number, section.content))

        # Global jurisdiction rules (e.g. stamp duty)
        for global_fn in _JURISDICTION_GLOBAL_RULES.get(jurisdiction, []):
            findings.extend(global_fn())

        # Contract-type rules
        sections_texts = [s.content for s in draft.sections]
        for ct_fn in _CONTRACT_TYPE_RULES.get(contract_type, []):
            findings.extend(ct_fn(sections_texts))

        return findings

    @staticmethod
    def to_annotations(findings: list[JurisdictionFinding]) -> list[Annotation]:
        return [
            Annotation(
                section_number=f.section_number,
                agent="jurisdiction",
                severity=f.severity,
                issue=f.issue,
                suggested_fix=f.suggested_fix,
                reasoning=f"Statute: {f.statute} | Action: {f.action}",
            )
            for f in findings
        ]
