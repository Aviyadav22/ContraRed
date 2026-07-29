from __future__ import annotations


from app.services.drafting.compliance_rules import ComplianceRuleEngine


def test_liability_cap_too_low():
    engine = ComplianceRuleEngine()
    findings = engine.check_liability_cap(
        cap_months=1, has_ip_carveout=False, has_confidentiality_carveout=False
    )
    assert any(
        "below market" in f.lower() or "unconscionable" in f.lower() for f in findings
    )


def test_liability_cap_missing_ip_carveout():
    engine = ComplianceRuleEngine()
    findings = engine.check_liability_cap(
        cap_months=12, has_ip_carveout=False, has_confidentiality_carveout=True
    )
    assert any("ip" in f.lower() for f in findings)


def test_liability_cap_missing_confidentiality_carveout():
    engine = ComplianceRuleEngine()
    findings = engine.check_liability_cap(
        cap_months=12, has_ip_carveout=True, has_confidentiality_carveout=False
    )
    assert any("confidentiality" in f.lower() for f in findings)


def test_liability_cap_reasonable():
    engine = ComplianceRuleEngine()
    findings = engine.check_liability_cap(
        cap_months=12,
        has_ip_carveout=True,
        has_confidentiality_carveout=True,
        has_gross_negligence_carveout=True,
    )
    critical = [f for f in findings if "CRITICAL" in f]
    assert len(critical) == 0


def test_liability_cap_zero_months():
    engine = ComplianceRuleEngine()
    findings = engine.check_liability_cap(cap_months=0, has_ip_carveout=True)
    assert any("unconscionable" in f.lower() or "zero" in f.lower() for f in findings)


def test_gdpr_completeness_missing():
    engine = ComplianceRuleEngine()
    present = {"processing_on_instructions", "security_measures", "audit_rights"}
    missing = engine.check_gdpr_completeness(present)
    assert len(missing) > 0
    assert "sub_processor_management" in missing or "breach_notification" in missing


def test_gdpr_completeness_all_present():
    engine = ComplianceRuleEngine()
    present = set(engine.GDPR_ARTICLE_28_REQUIREMENTS)
    missing = engine.check_gdpr_completeness(present)
    assert len(missing) == 0


def test_gdpr_completeness_empty():
    engine = ComplianceRuleEngine()
    missing = engine.check_gdpr_completeness(set())
    assert missing == set(engine.GDPR_ARTICLE_28_REQUIREMENTS)


def test_efforts_consistency_mixed():
    engine = ComplianceRuleEngine()
    texts = [
        "use best efforts to deliver",
        "use commercially reasonable efforts to notify",
    ]
    findings = engine.check_efforts_consistency(texts)
    assert len(findings) >= 1


def test_efforts_consistency_uniform():
    engine = ComplianceRuleEngine()
    texts = ["use reasonable efforts to deliver", "use reasonable efforts to notify"]
    findings = engine.check_efforts_consistency(texts)
    assert len(findings) == 0


def test_efforts_consistency_empty():
    engine = ComplianceRuleEngine()
    findings = engine.check_efforts_consistency([])
    assert len(findings) == 0


def test_efforts_consistency_single():
    engine = ComplianceRuleEngine()
    findings = engine.check_efforts_consistency(["use best efforts to perform"])
    assert len(findings) == 0
