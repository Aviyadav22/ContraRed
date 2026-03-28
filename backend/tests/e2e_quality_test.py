#!/usr/bin/env python3
"""
E2E Quality Test — Runs real contracts through the live Gemini AI pipeline
and evaluates result quality (precision, coverage, fix quality).

Usage:
    cd backend
    python tests/e2e_quality_test.py
"""
import asyncio
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")


def _setup():
    """Setup and validate Vertex AI. Must be called before running tests."""
    from dotenv import load_dotenv
    load_dotenv(override=True)

    os.environ.setdefault("DEBUG", "true")

    vertex_project = os.environ.get("VERTEX_PROJECT_ID", "")
    if not vertex_project:
        print("ERROR: VERTEX_PROJECT_ID not found in .env. Cannot run E2E test.")
        print("Consumer Gemini API is prohibited — Vertex AI is required.")
        sys.exit(1)
    print(f"Vertex AI project: {vertex_project}")

    from app.services.analysis_pipeline import analysis_pipeline as _pipeline
    from app.core.config import settings
    from app.core.vertex_client import get_backend

    print(f"Settings AI_PROVIDER={settings.AI_PROVIDER}, VERTEX_PROJECT_ID={settings.VERTEX_PROJECT_ID}")
    print(f"VERTEX_LOCATION={settings.VERTEX_LOCATION}")
    print(f"Models: analysis={settings.GEMINI_ANALYSIS_MODEL}, subtask={settings.GEMINI_MODEL}")

    backend = get_backend()
    print(f"AI backend: {backend}")
    if backend != "vertex":
        print("ERROR: Vertex AI failed to initialize. Check credentials.")
        sys.exit(1)

    return _pipeline

# ─────────────────────────────────────────────────────────────
# TEST CONTRACTS — Each has known issues for quality validation
# ─────────────────────────────────────────────────────────────

NDA_CONTRACT = """MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of January 15, 2026, between TechCorp Inc. ("Disclosing Party") and StartupXYZ Ltd. ("Receiving Party").

1. DEFINITION OF CONFIDENTIAL INFORMATION
"Confidential Information" means any and all technical and non-technical information disclosed by either party, including but not limited to patent, copyright, trade secret, and proprietary information, techniques, sketches, drawings, models, inventions, know-how, processes, apparatus, equipment, algorithms, software programs, and source code.

2. OBLIGATIONS OF RECEIVING PARTY
The Receiving Party agrees to hold and maintain the Confidential Information in strictest confidence. The Receiving Party shall not, without prior written approval of the Disclosing Party, use for Receiving Party's own benefit, publish, copy, or otherwise disclose to others, or permit the use by others for their benefit or to the detriment of the Disclosing Party.

3. TERM AND DURATION
This Agreement shall remain in effect for a period of ten (10) years from the Effective Date. The confidentiality obligations shall survive termination of this Agreement in perpetuity. There shall be no right to terminate this Agreement prior to the expiration of the term.

4. NON-SOLICITATION
During the term of this Agreement and for a period of five (5) years thereafter, neither party shall directly or indirectly solicit, hire, or engage any employee, contractor, or consultant of the other party. This restriction applies worldwide without any geographic limitation.

5. LIQUIDATED DAMAGES
In the event of any breach or threatened breach of this Agreement, the breaching party shall pay to the non-breaching party the sum of Five Million Dollars ($5,000,000) per breach as liquidated damages, in addition to any other remedies available at law or in equity.

6. INDEMNIFICATION
The Receiving Party shall indemnify, defend, and hold harmless the Disclosing Party from any and all claims, damages, losses, costs, and expenses (including reasonable attorneys' fees) arising out of or related to any breach of this Agreement, without any cap or limitation on such indemnification obligation.

7. GOVERNING LAW AND JURISDICTION
This Agreement shall be governed by and construed in accordance with the laws of the Cayman Islands. Any dispute arising under this Agreement shall be resolved exclusively in the courts of the Cayman Islands. The parties waive any right to a jury trial.

8. ASSIGNMENT
This Agreement may not be assigned by the Receiving Party without the prior written consent of the Disclosing Party. The Disclosing Party may freely assign this Agreement without notice or consent.

9. REMEDIES
The parties acknowledge that monetary damages may not be a sufficient remedy for unauthorized disclosure of Confidential Information. The Disclosing Party shall be entitled to seek injunctive or other equitable relief, without the necessity of posting bond.
"""

SaaS_CONTRACT = """SOFTWARE AS A SERVICE AGREEMENT

This Software as a Service Agreement ("Agreement") is entered into as of February 1, 2026, between CloudVendor Inc., a Delaware corporation ("Provider"), and Enterprise Customer Corp. ("Customer").

1. SERVICES
Provider shall provide Customer with access to Provider's cloud-based software platform ("Service") as described in the applicable Order Form. The Service shall be available 24/7, subject to scheduled maintenance windows.

2. SERVICE LEVEL AGREEMENT
Provider shall use commercially reasonable efforts to maintain Service availability of 95% measured monthly. In the event of downtime exceeding the SLA threshold, Customer shall receive service credits equal to 5% of the monthly fees for each additional 1% of downtime.

Service credits shall be Customer's sole and exclusive remedy for any failure to meet the SLA.

3. DATA OWNERSHIP AND PROCESSING
All data uploaded to or created within the Service by Customer ("Customer Data") shall remain the property of Customer. Provider shall have the right to use Customer Data for any purpose, including but not limited to analytics, machine learning model training, aggregate benchmarking, and sharing with third-party partners. Provider shall retain a perpetual, irrevocable, worldwide license to all Customer Data even after termination.

4. SECURITY
Provider shall implement commercially reasonable security measures. Provider assumes no liability for data breaches, unauthorized access, or loss of Customer Data regardless of the cause, including Provider's negligence.

5. FEES AND PAYMENT
Customer shall pay the fees set forth in the Order Form. Provider may increase fees at any time with 15 days' written notice. If Customer does not agree to a fee increase, Customer's sole remedy is to terminate this Agreement. All fees are non-refundable.

6. INTELLECTUAL PROPERTY
Any customizations, configurations, integrations, or workflows created by Customer using the Service shall become the intellectual property of Provider. Customer hereby assigns all rights, title, and interest in such works to Provider.

7. LIMITATION OF LIABILITY
IN NO EVENT SHALL PROVIDER BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES. PROVIDER'S TOTAL AGGREGATE LIABILITY SHALL NOT EXCEED THE FEES PAID BY CUSTOMER IN THE ONE (1) MONTH PRECEDING THE CLAIM.

8. TERM AND TERMINATION
The initial term shall be three (3) years ("Initial Term"). This Agreement shall automatically renew for successive one (1) year periods unless either party provides written notice of non-renewal at least 180 days prior to the end of the then-current term. Early termination by Customer shall require payment of all remaining fees for the balance of the term.

9. INDEMNIFICATION
Customer shall indemnify and hold harmless Provider against any and all claims, damages, and expenses arising from Customer's use of the Service. Provider shall have no obligation to indemnify Customer for any reason whatsoever, including claims that the Service infringes third-party intellectual property rights.

10. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware. Any disputes shall be resolved by binding arbitration administered by a single arbitrator selected by Provider in Wilmington, Delaware.
"""

EMPLOYMENT_CONTRACT = """EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into as of March 1, 2026, between MegaCorp Technologies Inc., a California corporation ("Company"), and John Doe ("Employee").

1. POSITION AND DUTIES
Employee is hired as Senior Software Engineer and shall report to the VP of Engineering. Employee shall devote substantially all of their working time and attention to the business affairs of the Company. Employee shall not engage in any outside employment, consulting, or business activities without prior written consent of the Company.

2. COMPENSATION
Employee shall receive a base salary of $180,000 per year, payable in accordance with the Company's standard payroll practices. The Company may reduce Employee's salary at any time and for any reason, with or without notice.

3. AT-WILL EMPLOYMENT
Employee's employment with the Company is "at will." Either party may terminate this Agreement at any time, with or without cause or notice. However, Employee must provide 90 days' advance written notice prior to resignation.

4. INTELLECTUAL PROPERTY ASSIGNMENT
Employee hereby assigns to the Company all rights, title, and interest in any and all inventions, discoveries, improvements, works of authorship, and intellectual property, whether or not patentable or copyrightable, that Employee may conceive, develop, or reduce to practice, either alone or jointly with others, during or outside of working hours, whether or not related to the Company's business. This assignment extends to any work created during Employee's personal time using Employee's own equipment and resources.

5. NON-COMPETE
During the term of employment and for a period of three (3) years following termination for any reason, Employee shall not directly or indirectly compete with the Company or work for any competitor anywhere in the world. This includes any business that develops, markets, sells, or supports software of any kind.

6. NON-SOLICITATION
For a period of three (3) years following termination, Employee shall not directly or indirectly solicit, recruit, or hire any employee, contractor, or consultant of the Company, or encourage any such person to leave the Company.

7. CONFIDENTIALITY
Employee shall not disclose any Confidential Information during or after employment, in perpetuity. Confidential Information includes all information relating to the Company's business, regardless of whether marked as confidential. Employee's obligations under this section survive termination indefinitely.

8. TERMINATION
Upon termination for any reason, Employee shall immediately return all Company property and shall not be entitled to any severance pay, accrued benefits, or unused vacation pay. The Company may withhold Employee's final paycheck for up to 60 days following termination.

9. DISPUTE RESOLUTION
Any disputes arising out of this Agreement shall be resolved through mandatory binding arbitration before a single arbitrator selected by the Company, conducted in San Francisco, California. Employee waives the right to a jury trial, the right to participate in a class action, and the right to appeal the arbitration award.

10. GOVERNING LAW
This Agreement shall be governed by the laws of the State of California, without regard to its conflict of laws principles.

11. GARDEN LEAVE
Upon notice of termination (by either party), the Company may place Employee on garden leave for up to 12 months, during which time Employee shall remain employed but shall not be required to report to work. During garden leave, Employee shall continue to receive base salary but shall not be eligible for any bonuses or equity vesting.
"""

# Known issues each contract SHOULD flag (for quality scoring)
EXPECTED_ISSUES = {
    "NDA": {
        "must_flag": [
            "perpetual confidentiality",
            "liquidated damages ($5M)",
            "Cayman Islands governing law",
            "uncapped indemnification",
            "5-year non-solicitation",
            "no-termination clause",
            "asymmetric assignment rights",
        ],
        "min_red": 3,
        "min_yellow": 2,
    },
    "SaaS": {
        "must_flag": [
            "data usage rights (training, sharing)",
            "perpetual data license after termination",
            "no liability for data breaches",
            "1-month liability cap",
            "customer IP assignment to provider",
            "180-day termination notice",
            "no provider indemnification",
            "fee increase with only 15 days notice",
            "auto-renewal with early termination penalty",
        ],
        "min_red": 4,
        "min_yellow": 2,
    },
    "Employment": {
        "must_flag": [
            "worldwide non-compete (3 years)",
            "IP assignment for personal projects",
            "salary reduction without notice",
            "withholding final paycheck (60 days)",
            "no severance or accrued benefits",
            "arbitrator selected by company",
            "12-month garden leave",
            "90-day resignation notice (asymmetric)",
        ],
        "min_red": 4,
        "min_yellow": 2,
    },
}


def _score_quality(contract_name: str, result) -> dict:
    """Score the quality of analysis results against expected issues."""
    expected = EXPECTED_ISSUES[contract_name]

    findings = result.redlines if result.redlines else []
    red_count = sum(1 for f in findings if f.risk_level == "RED")
    yellow_count = sum(1 for f in findings if f.risk_level == "YELLOW")
    green_count = sum(1 for f in findings if f.risk_level == "GREEN")

    # Check which expected issues were found
    all_text = " ".join([
        f"{f.rule_name} {f.explanation} {f.recommendation} {f.original_text}"
        for f in findings
    ]).lower()

    found_issues = []
    missed_issues = []
    for issue in expected["must_flag"]:
        # Check if any keywords from the expected issue appear in findings
        keywords = issue.lower().split()
        # At least 2 keywords or 50% of keywords must match
        matches = sum(1 for kw in keywords if kw in all_text)
        if matches >= max(2, len(keywords) * 0.4):
            found_issues.append(issue)
        else:
            missed_issues.append(issue)

    coverage = len(found_issues) / len(expected["must_flag"]) * 100

    # Check fix quality
    fixes_present = sum(1 for f in findings if getattr(f, 'suggested_fix', None))
    fix_rate = (fixes_present / len(findings) * 100) if findings else 0

    # Confidence scores
    confidences = [
        f.confidence.score if hasattr(f.confidence, 'score') else (f.confidence if isinstance(f.confidence, (int, float)) else 0)
        for f in findings if f.confidence
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    return {
        "contract": contract_name,
        "total_findings": len(findings),
        "red": red_count,
        "yellow": yellow_count,
        "green": green_count,
        "expected_red_min": expected["min_red"],
        "expected_yellow_min": expected["min_yellow"],
        "red_sufficient": red_count >= expected["min_red"],
        "yellow_sufficient": yellow_count >= expected["min_yellow"],
        "coverage_pct": round(coverage, 1),
        "found_issues": found_issues,
        "missed_issues": missed_issues,
        "fix_rate_pct": round(fix_rate, 1),
        "avg_confidence": round(avg_confidence, 3),
        "has_executive_summary": bool(result.executive_summary),
        "executive_summary_len": len(result.executive_summary) if result.executive_summary else 0,
        "partial": result.partial,
    }


async def run_e2e_quality_test(analysis_pipeline):
    """Run all 3 contracts through the pipeline and evaluate quality."""
    contracts = [
        ("NDA", NDA_CONTRACT),
        ("SaaS", SaaS_CONTRACT),
        ("Employment", EMPLOYMENT_CONTRACT),
    ]

    results = []
    overall_start = time.time()

    for name, text in contracts:
        print(f"\n{'='*60}")
        print(f"  ANALYZING: {name} Contract")
        print(f"  Text length: {len(text)} chars, ~{len(text.split())} words")
        print(f"{'='*60}")

        start = time.time()
        try:
            result = await analysis_pipeline.run(text, playbook_rules=None)
            elapsed = time.time() - start

            score = _score_quality(name, result)
            score["execution_time_s"] = round(elapsed, 1)
            score["tokens_used"] = result.total_tokens_used

            print(f"\n  Results ({elapsed:.1f}s):")
            print(f"    Findings: {score['total_findings']} (RED:{score['red']} YELLOW:{score['yellow']} GREEN:{score['green']})")
            print(f"    Coverage: {score['coverage_pct']}% of expected issues found")
            print(f"    Fix rate: {score['fix_rate_pct']}%")
            print(f"    Avg confidence: {score['avg_confidence']}")
            print(f"    Partial (fallback): {score['partial']}")

            if score['missed_issues']:
                print(f"\n    MISSED issues:")
                for issue in score['missed_issues']:
                    print(f"      - {issue}")

            print(f"\n    Found issues:")
            for issue in score['found_issues']:
                print(f"      + {issue}")

            # Print each finding
            print(f"\n    All findings:")
            for i, f in enumerate(result.redlines or [], 1):
                fix_status = "HAS FIX" if getattr(f, 'suggested_fix', None) else "NO FIX"
                conf = f.confidence.score if hasattr(f.confidence, 'score') else f.confidence
                print(f"      {i}. [{f.risk_level}] {f.rule_name} (conf:{conf}) [{fix_status}]")
                print(f"         {f.explanation[:100]}...")

            if result.executive_summary:
                print(f"\n    Executive Summary:")
                for line in result.executive_summary[:5]:
                    print(f"      - {line[:120]}")

            results.append(score)

        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.1f}s: {e}")
            results.append({
                "contract": name,
                "error": str(e),
                "execution_time_s": round(elapsed, 1),
            })

    total_time = time.time() - overall_start

    # ── OVERALL QUALITY REPORT ──
    print(f"\n\n{'='*60}")
    print(f"  E2E QUALITY REPORT")
    print(f"{'='*60}")
    print(f"  Total time: {total_time:.1f}s")

    passed = 0
    failed = 0
    for r in results:
        if "error" in r:
            failed += 1
            print(f"\n  {r['contract']}: FAILED ({r['error'][:60]})")
            continue

        issues = []
        if not r["red_sufficient"]:
            issues.append(f"RED findings ({r['red']}) below minimum ({r['expected_red_min']})")
        if not r["yellow_sufficient"]:
            issues.append(f"YELLOW findings ({r['yellow']}) below minimum ({r['expected_yellow_min']})")
        if r["coverage_pct"] < 50:
            issues.append(f"Coverage only {r['coverage_pct']}% (target: 50%+)")
        if r["fix_rate_pct"] < 50:
            issues.append(f"Fix rate only {r['fix_rate_pct']}% (target: 50%+)")
        if r["partial"]:
            issues.append("Fell back to rule engine (AI unavailable)")

        status = "PASS" if not issues else "WARN" if len(issues) <= 2 else "FAIL"
        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1
        else:
            passed += 1  # WARN still counts as pass

        print(f"\n  {r['contract']}: {status}")
        print(f"    Findings: {r['total_findings']} | Coverage: {r['coverage_pct']}% | Fix rate: {r['fix_rate_pct']}%")
        print(f"    Time: {r['execution_time_s']}s | Tokens: {r.get('total_tokens_used', r.get('tokens_used', 'N/A'))}")
        if issues:
            for issue in issues:
                print(f"    ⚠ {issue}")

    print(f"\n  Overall: {passed} passed, {failed} failed out of {len(results)}")

    # Save results
    with open("e2e_quality_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to e2e_quality_results.json")

    return results


if __name__ == "__main__":
    pipeline = _setup()
    results = asyncio.run(run_e2e_quality_test(pipeline))
