

def test_saas_playbook_exists():
    from app.services.drafting.playbooks.saas_drafting import SAAS_PLAYBOOK
    assert SAAS_PLAYBOOK["contract_type"] == "saas"


def test_saas_has_all_msa_sections():
    from app.services.drafting.playbooks.saas_drafting import SAAS_PLAYBOOK
    clause_types = [c["clause_type"] for c in SAAS_PLAYBOOK["clauses"]]
    required = ["definitions", "scope_of_services", "grant_of_license", "customer_obligations",
                "fees_and_payment", "intellectual_property", "data_ownership", "confidentiality",
                "representations_warranties", "disclaimers", "indemnification", "limitation_of_liability",
                "data_security", "term_and_termination", "effects_of_termination", "dispute_resolution",
                "boilerplate", "signature_blocks"]
    for r in required:
        assert r in clause_types, f"Missing required SaaS clause: {r}"


def test_saas_three_tiers():
    from app.services.drafting.playbooks.saas_drafting import SAAS_PLAYBOOK
    for clause in SAAS_PLAYBOOK["clauses"]:
        for tier in ["preferred", "acceptable", "fallback"]:
            assert tier in clause, f"{clause['clause_type']} missing {tier}"
            assert "template_text" in clause[tier]
            assert len(clause[tier]["template_text"]) > 50


def test_saas_has_sla_section():
    from app.services.drafting.playbooks.saas_drafting import SAAS_PLAYBOOK
    clause_types = [c["clause_type"] for c in SAAS_PLAYBOOK["clauses"]]
    assert "sla" in clause_types


def test_saas_has_dpa_section():
    from app.services.drafting.playbooks.saas_drafting import SAAS_PLAYBOOK
    clause_types = [c["clause_type"] for c in SAAS_PLAYBOOK["clauses"]]
    assert "dpa" in clause_types


def test_saas_vendor_vs_customer_perspective():
    from app.services.drafting.playbooks.saas_drafting import SAAS_PLAYBOOK
    liability = next(c for c in SAAS_PLAYBOOK["clauses"] if c["clause_type"] == "limitation_of_liability")
    assert "month" in liability["preferred"]["template_text"].lower() or "fees" in liability["preferred"]["template_text"].lower()
