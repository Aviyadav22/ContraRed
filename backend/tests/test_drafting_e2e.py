"""
End-to-end drafting pipeline tests — 5 real-world lawyer scenarios.
Calls the orchestrator directly (no server needed).
"""

import asyncio
import logging
import sys
import os
import time
import traceback
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env
load_dotenv()

# Suppress noisy logs
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app.services.drafting").setLevel(logging.INFO)

from app.services.drafting.orchestrator import DraftingOrchestrator  # noqa: E402
from app.services.drafting.agents.draft_agent import DraftAgent  # noqa: E402

# ─── Patch AI adaptation to return template text (test deterministic pipeline) ─
_original_ai_generate = DraftAgent._ai_generate_clause

async def _passthrough_generate(self, clause, tier, context, semaphore):
    """Skip Vertex AI generation — test the deterministic pipeline."""
    tier_data = clause.get(tier, clause.get("acceptable", {}))
    return tier_data.get("template_text", ""), 0, False

# Also patch risk/compliance AI to return empty (test deterministic checks only)
SKIP_AI_REVIEW = os.environ.get("SKIP_AI_REVIEW", "1") == "1"

# ─── 5 Real-World Scenarios ───────────────────────────────────────────

SCENARIOS = [
    {
        "name": "TEST 1: Mutual NDA — Two CA tech cos, protective, IP evaluation",
        "input": {
            "contract_type": "nda_mutual",
            "drafting_perspective": "party_1",
            "risk_appetite": "protective",
            "jurisdiction": "US-CA",
            "party_1": {"name": "Acme Technologies Inc.", "entity_type": "corporation", "jurisdiction": "US-CA", "address": "100 Innovation Dr, San Jose, CA 95134"},
            "party_2": {"name": "ByteForge Labs LLC", "entity_type": "llc", "jurisdiction": "US-CA", "address": "500 Market St, San Francisco, CA 94105"},
            "term_months": 24,
            "governing_law": "California",
            "nda_details": {
                "purpose": "Evaluating a potential joint venture for AI-powered legal technology",
                "confidentiality_survival_years": 3,
                "non_solicitation": True,
                "non_solicitation_months": 12,
                "marking_requirement": False,
            },
        },
        "checks": {
            "min_sections": 8,
            "must_contain": ["Acme Technologies", "ByteForge Labs", "California", "Confidential Information"],
            "jurisdiction_flag": "non-compete",  # CA should flag non-compete/non-solicitation
        },
    },
    {
        "name": "TEST 2: SaaS Agreement — Vendor-side, balanced, Delaware",
        "input": {
            "contract_type": "saas",
            "drafting_perspective": "party_1",
            "risk_appetite": "balanced",
            "jurisdiction": "US-DE",
            "party_1": {"name": "CloudNova Solutions Inc.", "entity_type": "corporation", "jurisdiction": "US-DE", "address": "1209 Orange St, Wilmington, DE 19801"},
            "party_2": {"name": "RetailMax Corp.", "entity_type": "corporation", "jurisdiction": "US-NY", "address": "350 Fifth Avenue, New York, NY 10118"},
            "term_months": 12,
            "governing_law": "Delaware",
            "saas_details": {
                "service_description": "Cloud-based analytics platform for retail inventory optimization",
                "pricing_model": "per_user_monthly",
                "price_amount": 99.0,
                "billing_frequency": "monthly",
                "auto_renewal": True,
                "uptime_commitment": 99.9,
                "liability_cap_months": 12,
                "authorized_users": 50,
                "compliance_frameworks": ["SOC2", "GDPR"],
                "data_regions": ["us-east-1"],
            },
        },
        "checks": {
            "min_sections": 12,
            "must_contain": ["CloudNova", "RetailMax", "99.9%", "SOC"],
            "jurisdiction_flag": None,
        },
    },
    {
        "name": "TEST 3: Employment Contract — Indian jurisdiction, aggressive employer",
        "input": {
            "contract_type": "employment",
            "drafting_perspective": "party_1",
            "risk_appetite": "aggressive",
            "jurisdiction": "IN",
            "party_1": {"name": "TechVista India Pvt. Ltd.", "entity_type": "corporation", "jurisdiction": "IN", "address": "Tower B, Cyber City, Gurugram, Haryana 122002"},
            "party_2": {"name": "Rajesh Krishnamurthy", "entity_type": "individual", "jurisdiction": "IN", "address": "Flat 302, Prestige Apartments, Bangalore, Karnataka 560001"},
            "term_months": 0,  # at-will / permanent
            "governing_law": "India",
        },
        "checks": {
            "min_sections": 6,
            "must_contain": ["TechVista", "Rajesh Krishnamurthy"],
            "jurisdiction_flag": "non-compete",  # India should flag post-employment non-compete as void
        },
    },
    {
        "name": "TEST 4: MSA — UK jurisdiction, balanced, consulting engagement",
        "input": {
            "contract_type": "msa",
            "drafting_perspective": "balanced",
            "risk_appetite": "balanced",
            "jurisdiction": "GB",
            "party_1": {"name": "Pinnacle Consulting LLP", "entity_type": "llp", "jurisdiction": "GB", "address": "1 New Street Square, London EC4A 3HQ"},
            "party_2": {"name": "Thames Water Utilities Ltd.", "entity_type": "corporation", "jurisdiction": "GB", "address": "Clearwater Court, Vastern Road, Reading RG1 8DB"},
            "term_months": 36,
            "governing_law": "England and Wales",
        },
        "checks": {
            "min_sections": 8,
            "must_contain": ["Pinnacle Consulting", "Thames Water"],
            "jurisdiction_flag": "UCTA",  # UK should flag UCTA liability rules
        },
    },
    {
        "name": "TEST 5: Unilateral NDA — Singapore, protective discloser, IP-heavy",
        "input": {
            "contract_type": "nda_unilateral",
            "drafting_perspective": "party_1",
            "risk_appetite": "protective",
            "jurisdiction": "SG",
            "party_1": {"name": "Quantum Semiconductor Pte. Ltd.", "entity_type": "corporation", "jurisdiction": "SG", "address": "10 Collyer Quay, Ocean Financial Centre, Singapore 049315"},
            "party_2": {"name": "NexGen Chip Design Inc.", "entity_type": "corporation", "jurisdiction": "US-CA", "address": "2100 Logic Drive, San Jose, CA 95124"},
            "term_months": 18,
            "governing_law": "Singapore",
            "nda_details": {
                "purpose": "Disclosure of proprietary semiconductor fabrication processes and chip architecture IP for potential licensing arrangement",
                "confidentiality_survival_years": 5,
                "non_solicitation": False,
                "marking_requirement": True,
            },
        },
        "checks": {
            "min_sections": 8,
            "must_contain": ["Quantum Semiconductor", "NexGen Chip Design", "Disclosing Party"],
            "jurisdiction_flag": None,
        },
    },
]


def print_section_summary(sections, max_preview=120):
    """Print a compact summary of all sections."""
    for s in sections:
        preview = s.content[:max_preview].replace("\n", " ")
        tier_tag = f"[{s.tier_used}]" if s.tier_used else ""
        print(f"  {s.number}. {s.heading} {tier_tag} — {preview}...")


def print_annotations(annotations, label="Annotations"):
    """Print all annotations grouped by severity."""
    if not annotations:
        print(f"  {label}: None")
        return
    for sev in ["critical", "warning", "info"]:
        items = [a for a in annotations if a.severity == sev]
        if items:
            print(f"  [{sev.upper()}] ({len(items)}):")
            for a in items:
                fix_preview = ""
                if a.suggested_fix:
                    fix_preview = f"\n      Fix: {a.suggested_fix[:100]}..."
                print(f"    - S{a.section_number} [{a.agent}]: {a.issue}{fix_preview}")


def run_checks(result, checks):
    """Run validation checks and return pass/fail list."""
    issues = []
    # Section count
    if len(result.draft.sections) < checks["min_sections"]:
        issues.append(f"FAIL: Only {len(result.draft.sections)} sections (expected >= {checks['min_sections']})")
    else:
        print(f"  CHECK PASS: {len(result.draft.sections)} sections (>= {checks['min_sections']})")

    # Content checks
    full_text = " ".join(s.content for s in result.draft.sections)
    for term in checks.get("must_contain", []):
        if term.lower() not in full_text.lower():
            issues.append(f"FAIL: Missing expected term '{term}' in draft text")
        else:
            print(f"  CHECK PASS: Found '{term}' in draft")

    # Jurisdiction flag check
    jf = checks.get("jurisdiction_flag")
    if jf:
        ann_text = " ".join(a.issue + " " + a.reasoning for a in result.quality_report.open_annotations)
        if jf.lower() in ann_text.lower():
            print(f"  CHECK PASS: Jurisdiction rule '{jf}' was flagged")
        else:
            issues.append(f"WARN: Expected jurisdiction flag '{jf}' not found in annotations")

    # Quality score sanity
    if result.quality_report.overall_score < 50:
        issues.append(f"WARN: Very low overall score: {result.quality_report.overall_score}")

    return issues


async def run_all():
    orch = DraftingOrchestrator()
    all_issues = []

    # Patch draft agent to skip per-clause AI (deterministic pipeline test)
    DraftAgent._ai_generate_clause = _passthrough_generate

    if SKIP_AI_REVIEW:
        # Also patch risk agent to use empty annotations (skip Vertex AI)
        async def _empty_risk_review(self, draft, risk_appetite="balanced"):
            return []
        async def _empty_compliance_review(self, draft, jurisdiction="US-DE"):
            return []
        orch.risk_agent.review = _empty_risk_review.__get__(orch.risk_agent)
        orch.compliance_agent.review = _empty_compliance_review.__get__(orch.compliance_agent)
        print("NOTE: AI review agents SKIPPED (testing deterministic pipeline only)")
        print("      Set SKIP_AI_REVIEW=0 to include Vertex AI risk/compliance review")

    print(f"Running {len(SCENARIOS)} real-world drafting scenarios...\n")

    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n{'='*80}")
        print(f" {scenario['name']}")
        print(f"{'='*80}")

        start = time.time()
        try:
            result = await orch.run(scenario["input"])
            elapsed = time.time() - start
        except Exception as exc:
            elapsed = time.time() - start
            print(f"  FAILED in {elapsed:.1f}s: {exc}")
            traceback.print_exc()
            all_issues.append(f"Test {i}: CRASHED — {exc}")
            continue

        # Print results
        print(f"\n  Title: {result.draft.title}")
        print(f"  Generated in: {elapsed:.1f}s")
        print(f"  Sections: {len(result.draft.sections)}")
        print(f"  Defined Terms: {len(result.draft.defined_terms)}")
        print(f"  Model: {result.draft.metadata.model}")
        print(f"  Tokens: {result.draft.metadata.tokens_used}")

        print("\n  QUALITY SCORES:")
        qr = result.quality_report
        print(f"    Overall:    {qr.overall_score:.1f}/100")
        print(f"    Risk:       {qr.risk_alignment:.1f}/100")
        print(f"    Compliance: {qr.compliance_score:.1f}/100")
        print(f"    QA:         {qr.qa_score:.1f}/100")
        print(f"    Applied:    {qr.annotations_applied} | Conflicts: {qr.conflicts_flagged}")

        print("\n  SECTIONS:")
        print_section_summary(result.draft.sections)

        print(f"\n  DEFINED TERMS ({len(result.draft.defined_terms)}):")
        for term in sorted(result.draft.defined_terms.keys()):
            defn = result.draft.defined_terms[term][:80]
            print(f"    - {term}: {defn}...")

        print(f"\n  OPEN ANNOTATIONS ({len(qr.open_annotations)}):")
        print_annotations(qr.open_annotations)

        print("\n  VALIDATION CHECKS:")
        test_issues = run_checks(result, scenario["checks"])
        if test_issues:
            for issue in test_issues:
                print(f"  >> {issue}")
            all_issues.extend([f"Test {i}: {iss}" for iss in test_issues])
        else:
            print("  ALL CHECKS PASSED")

    # Final summary
    print(f"\n{'='*80}")
    print(" FINAL SUMMARY")
    print(f"{'='*80}")
    if all_issues:
        print(f" {len(all_issues)} issues found:")
        for iss in all_issues:
            print(f"   - {iss}")
    else:
        print(" All 5 tests passed all checks!")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(run_all())
