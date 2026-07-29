"""Tests for NDA Mutual and Unilateral drafting playbooks."""



def test_nda_mutual_playbook_exists():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    assert NDA_MUTUAL_PLAYBOOK["contract_type"] == "nda_mutual"


def test_nda_mutual_has_all_required_sections():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    clause_types = [c["clause_type"] for c in NDA_MUTUAL_PLAYBOOK["clauses"]]
    required = [
        "preamble", "recitals", "confidential_info_definition", "ci_exclusions",
        "receiving_party_obligations", "permitted_disclosures", "compelled_disclosure",
        "term_and_duration", "return_destruction", "remedies", "no_license",
        "governing_law", "boilerplate", "signature_blocks",
    ]
    for r in required:
        assert r in clause_types, f"Missing required clause: {r}"


def test_nda_mutual_three_tiers_per_clause():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    for clause in NDA_MUTUAL_PLAYBOOK["clauses"]:
        assert "preferred" in clause, f"{clause['clause_type']} missing preferred tier"
        assert "acceptable" in clause, f"{clause['clause_type']} missing acceptable tier"
        assert "fallback" in clause, f"{clause['clause_type']} missing fallback tier"


def test_nda_mutual_tiers_have_template_text():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    for clause in NDA_MUTUAL_PLAYBOOK["clauses"]:
        for tier in ["preferred", "acceptable", "fallback"]:
            assert "template_text" in clause[tier], (
                f"{clause['clause_type']}.{tier} missing template_text"
            )
            assert len(clause[tier]["template_text"]) > 50, (
                f"{clause['clause_type']}.{tier} template_text too short"
            )


def test_nda_mutual_has_section_order():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    assert "section_order" in NDA_MUTUAL_PLAYBOOK
    assert len(NDA_MUTUAL_PLAYBOOK["section_order"]) >= 14


def test_nda_mutual_placeholders():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    preamble = NDA_MUTUAL_PLAYBOOK["clauses"][0]
    assert "{{party_1_name}}" in preamble["preferred"]["template_text"]


def test_nda_unilateral_playbook_exists():
    from app.services.drafting.playbooks.nda_drafting import NDA_UNILATERAL_PLAYBOOK
    assert NDA_UNILATERAL_PLAYBOOK["contract_type"] == "nda_unilateral"


def test_nda_unilateral_uses_disclosing_receiving():
    from app.services.drafting.playbooks.nda_drafting import NDA_UNILATERAL_PLAYBOOK
    ci_clause = next(
        c for c in NDA_UNILATERAL_PLAYBOOK["clauses"]
        if c["clause_type"] == "confidential_info_definition"
    )
    text = ci_clause["preferred"]["template_text"]
    assert "Disclosing Party" in text or "{{disclosing_party_name}}" in text


# ── Additional structural tests ──────────────────────────────────────


def test_nda_mutual_clause_count():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    assert len(NDA_MUTUAL_PLAYBOOK["clauses"]) == 15


def test_nda_unilateral_clause_count():
    from app.services.drafting.playbooks.nda_drafting import NDA_UNILATERAL_PLAYBOOK
    assert len(NDA_UNILATERAL_PLAYBOOK["clauses"]) == 15


def test_nda_unilateral_has_all_required_sections():
    from app.services.drafting.playbooks.nda_drafting import NDA_UNILATERAL_PLAYBOOK
    clause_types = [c["clause_type"] for c in NDA_UNILATERAL_PLAYBOOK["clauses"]]
    required = [
        "preamble", "recitals", "confidential_info_definition", "ci_exclusions",
        "receiving_party_obligations", "permitted_disclosures", "compelled_disclosure",
        "term_and_duration", "return_destruction", "remedies", "no_license",
        "governing_law", "boilerplate", "signature_blocks",
    ]
    for r in required:
        assert r in clause_types, f"Missing required clause: {r}"


def test_nda_mutual_section_order_matches_clauses():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    order = NDA_MUTUAL_PLAYBOOK["section_order"]
    clause_types = [c["clause_type"] for c in NDA_MUTUAL_PLAYBOOK["clauses"]]
    for section in order:
        assert section in clause_types, f"section_order entry '{section}' not in clauses"


def test_nda_mutual_non_solicitation_is_conditional():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    ns = next(c for c in NDA_MUTUAL_PLAYBOOK["clauses"] if c["clause_type"] == "non_solicitation")
    assert ns["is_required"] is False
    assert ns["conditional_on"] is not None


def test_nda_mutual_tiers_have_tone():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    for clause in NDA_MUTUAL_PLAYBOOK["clauses"]:
        for tier in ["preferred", "acceptable", "fallback"]:
            assert "tone" in clause[tier], f"{clause['clause_type']}.{tier} missing tone"


def test_nda_unilateral_preamble_is_one_directional():
    from app.services.drafting.playbooks.nda_drafting import NDA_UNILATERAL_PLAYBOOK
    preamble = NDA_UNILATERAL_PLAYBOOK["clauses"][0]
    text = preamble["preferred"]["template_text"]
    assert "Disclosing Party" in text
    assert "Receiving Party" in text


def test_nda_mutual_name():
    from app.services.drafting.playbooks.nda_drafting import NDA_MUTUAL_PLAYBOOK
    assert NDA_MUTUAL_PLAYBOOK["name"] == "Mutual Non-Disclosure Agreement"


def test_nda_unilateral_name():
    from app.services.drafting.playbooks.nda_drafting import NDA_UNILATERAL_PLAYBOOK
    assert NDA_UNILATERAL_PLAYBOOK["name"] == "Unilateral Non-Disclosure Agreement"
