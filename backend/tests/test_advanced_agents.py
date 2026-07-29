"""Tests for Advanced Agents — Compliance Watch + Renewal Intelligence."""
import pytest


# ============================================================
# Compliance Watch Agent tests
# ============================================================

def test_compliance_watch_import():
    """ComplianceWatchAgent should import cleanly."""
    from app.services.compliance_watch import (
        ComplianceWatchAgent,
        ComplianceWatchReport,
        ComplianceDelta,
        DocumentDelta,
    )
    assert ComplianceWatchAgent is not None
    assert ComplianceWatchReport is not None
    assert ComplianceDelta is not None
    assert DocumentDelta is not None


def test_compliance_watch_report_to_dict():
    """ComplianceWatchReport.to_dict() should return a proper dict."""
    from app.services.compliance_watch import (
        ComplianceWatchReport,
        ComplianceDelta,
        DocumentDelta,
    )
    report = ComplianceWatchReport(
        compliance_layer_code="dpdp",
        triggered_at="2026-03-31T00:00:00Z",
        total_documents_scanned=3,
        newly_non_compliant_count=1,
        document_deltas=[
            DocumentDelta(
                document_id="doc-1",
                document_name="MSA.docx",
                newly_non_compliant=True,
                deltas=[
                    ComplianceDelta(
                        clause_type="data_protection",
                        old_risk_level="GREEN",
                        new_risk_level="RED",
                        change="risk_increased",
                        explanation="Risk increased from GREEN to RED",
                    )
                ],
            )
        ],
        summary="1 newly non-compliant",
    )
    d = report.to_dict()
    assert d["compliance_layer_code"] == "dpdp"
    assert d["total_documents_scanned"] == 3
    assert d["newly_non_compliant_count"] == 1
    assert len(d["document_deltas"]) == 1
    assert d["document_deltas"][0]["newly_non_compliant"] is True
    assert len(d["document_deltas"][0]["deltas"]) == 1
    assert d["document_deltas"][0]["deltas"][0]["change"] == "risk_increased"


def test_compliance_watch_delta_types():
    """ComplianceDelta should support all change types."""
    from app.services.compliance_watch import ComplianceDelta
    for change_type in ("new_risk", "risk_increased", "risk_decreased", "resolved"):
        delta = ComplianceDelta(
            clause_type="test",
            old_risk_level="GREEN",
            new_risk_level="RED",
            change=change_type,
        )
        assert delta.change == change_type


def test_compliance_watch_rule_deltas():
    """ComplianceWatchAgent._compute_rule_deltas should detect changes."""
    from app.services.compliance_watch import ComplianceWatchAgent

    agent = ComplianceWatchAgent.__new__(ComplianceWatchAgent)

    # Simulate new rules vs no old risks
    new_rules = [
        {"clause_type": "data_protection", "risk_level": "RED", "rule_name": "DPDP Data Protection"},
        {"clause_type": "consent", "risk_level": "YELLOW", "rule_name": "Consent Mechanism"},
        {"clause_type": "retention", "risk_level": "GREEN", "rule_name": "Data Retention"},
    ]
    deltas = agent._compute_rule_deltas([], new_rules)
    # Rule severity alone cannot prove a contract violates the new rule.
    assert len(deltas) == 3
    assert all(d.change == "reassessment_required" for d in deltas)
    assert all(d.new_risk_level == "UNASSESSED" for d in deltas)
    clause_types = {d.clause_type for d in deltas}
    assert "data_protection" in clause_types
    assert "consent" in clause_types


def test_compliance_watch_build_summary():
    """ComplianceWatchAgent._build_summary should produce readable text."""
    from app.services.compliance_watch import ComplianceWatchAgent, ComplianceWatchReport

    agent = ComplianceWatchAgent.__new__(ComplianceWatchAgent)
    report = ComplianceWatchReport(
        compliance_layer_code="dpdp",
        total_documents_scanned=5,
        newly_non_compliant_count=2,
    )
    summary = agent._build_summary(report)
    assert "dpdp" in summary
    assert "5" in summary
    assert "no new non-compliance determination" in summary


# ============================================================
# Renewal Intelligence Agent tests
# ============================================================

def test_renewal_agent_import():
    """RenewalAgent should import cleanly."""
    from app.services.renewal_agent import (
        RenewalAgent,
        RenewalReport,
        RenewalBrief,
    )
    assert RenewalAgent is not None
    assert RenewalReport is not None
    assert RenewalBrief is not None


def test_renewal_report_to_dict():
    """RenewalReport.to_dict() should return a proper dict."""
    from app.services.renewal_agent import RenewalReport, RenewalBrief
    report = RenewalReport(
        org_id="org-1",
        days_ahead=90,
        generated_at="2026-03-31T00:00:00Z",
        total_expiring=1,
        briefs=[
            RenewalBrief(
                document_id="doc-1",
                document_name="MSA.docx",
                expiry_date="2026-06-01T00:00:00Z",
                days_until_expiry=62,
                risk_summary={"red": 1, "yellow": 2, "green": 3, "total": 6},
                top_risks=[{"clause_type": "liability", "risk_level": "RED"}],
                recommendations=["Address 1 deal-breaker before renewal."],
            )
        ],
        summary="1 contract(s) expiring",
    )
    d = report.to_dict()
    assert d["org_id"] == "org-1"
    assert d["days_ahead"] == 90
    assert d["total_expiring"] == 1
    assert len(d["briefs"]) == 1
    assert d["briefs"][0]["days_until_expiry"] == 62
    assert len(d["briefs"][0]["recommendations"]) == 1


def test_renewal_recommendations_urgent():
    """Renewal agent should flag urgent contracts (≤30 days)."""
    from app.services.renewal_agent import RenewalAgent, RenewalBrief

    agent = RenewalAgent.__new__(RenewalAgent)
    brief = RenewalBrief(
        document_id="doc-1",
        document_name="test.docx",
        risk_summary={"red": 0, "yellow": 0},
    )
    recs = agent._generate_recommendations(brief, days_remaining=15)
    assert any("URGENT" in r for r in recs)
    assert any("30 days" in r for r in recs)


def test_renewal_recommendations_medium():
    """Renewal agent should flag contracts expiring in 30-60 days."""
    from app.services.renewal_agent import RenewalAgent, RenewalBrief

    agent = RenewalAgent.__new__(RenewalAgent)
    brief = RenewalBrief(
        document_id="doc-1",
        document_name="test.docx",
        risk_summary={"red": 0, "yellow": 0},
    )
    recs = agent._generate_recommendations(brief, days_remaining=45)
    assert any("60 days" in r for r in recs)


def test_renewal_recommendations_with_risks():
    """Renewal agent should recommend addressing risks before renewal."""
    from app.services.renewal_agent import RenewalAgent, RenewalBrief

    agent = RenewalAgent.__new__(RenewalAgent)
    brief = RenewalBrief(
        document_id="doc-1",
        document_name="test.docx",
        risk_summary={"red": 2, "yellow": 3},
    )
    recs = agent._generate_recommendations(brief, days_remaining=60)
    assert any("2 deal-breaker" in r for r in recs)
    assert any("3 medium-risk" in r for r in recs)


def test_renewal_recommendations_low_risk():
    """Low risk contracts should suggest auto-renewal."""
    from app.services.renewal_agent import RenewalAgent, RenewalBrief

    agent = RenewalAgent.__new__(RenewalAgent)
    brief = RenewalBrief(
        document_id="doc-1",
        document_name="test.docx",
        risk_summary={"red": 0, "yellow": 0},
    )
    recs = agent._generate_recommendations(brief, days_remaining=80)
    assert any("auto-renewal" in r for r in recs)


def test_renewal_build_summary_no_expiring():
    """Summary should handle zero expiring contracts."""
    from app.services.renewal_agent import RenewalAgent, RenewalReport

    agent = RenewalAgent.__new__(RenewalAgent)
    report = RenewalReport(org_id="org-1", days_ahead=90, total_expiring=0)
    summary = agent._build_summary(report)
    assert "No contracts" in summary


def test_renewal_build_summary_with_expiring():
    """Summary should report expiring contracts count."""
    from app.services.renewal_agent import RenewalAgent, RenewalReport, RenewalBrief

    agent = RenewalAgent.__new__(RenewalAgent)
    report = RenewalReport(
        org_id="org-1",
        days_ahead=90,
        total_expiring=3,
        briefs=[
            RenewalBrief(document_id="1", document_name="a", days_until_expiry=10),
            RenewalBrief(document_id="2", document_name="b", days_until_expiry=50),
            RenewalBrief(document_id="3", document_name="c", days_until_expiry=80),
        ],
    )
    summary = agent._build_summary(report)
    assert "3 contract(s)" in summary
    assert "1 require(s) immediate attention" in summary


# ============================================================
# API endpoint tests
# ============================================================

def test_compliance_watch_request_schema():
    """ComplianceWatchRequest should validate correctly."""
    from app.api.v1.endpoints.agent import ComplianceWatchRequest
    req = ComplianceWatchRequest(
        compliance_layer_code="dpdp",
        org_id="12345678-1234-1234-1234-123456789012",
    )
    assert req.compliance_layer_code == "dpdp"


def test_compliance_watch_response_schema():
    """ComplianceWatchResponse should validate correctly."""
    from app.api.v1.endpoints.agent import ComplianceWatchResponse
    resp = ComplianceWatchResponse(
        compliance_layer_code="dpdp",
        total_documents_scanned=0,
        newly_non_compliant_count=0,
        summary="No documents found.",
    )
    assert resp.total_documents_scanned == 0


def test_renewal_response_schema():
    """RenewalResponse should validate correctly."""
    from app.api.v1.endpoints.agent import RenewalResponse
    resp = RenewalResponse(
        org_id="org-1",
        days_ahead=90,
        total_expiring=0,
        summary="No contracts expiring.",
    )
    assert resp.days_ahead == 90


@pytest.mark.asyncio
async def test_compliance_watch_requires_auth(client):
    """POST /agent/compliance-watch/trigger should require auth."""
    resp = await client.post("/api/v1/agent/compliance-watch/trigger", json={
        "compliance_layer_code": "dpdp",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_renewals_requires_auth(client):
    """GET /agent/renewals should require auth."""
    resp = await client.get("/api/v1/agent/renewals")
    assert resp.status_code == 401
