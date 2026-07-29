"""Tests for the drafting API endpoint router."""



def test_intake_schema_endpoint_exists():
    from app.api.v1.endpoints.drafting import router
    paths = [r.path for r in router.routes]
    assert "/intake-schema" in paths


def test_generate_endpoint_exists():
    from app.api.v1.endpoints.drafting import router
    paths = [r.path for r in router.routes]
    assert "/generate" in paths


def test_playbooks_endpoint_exists():
    from app.api.v1.endpoints.drafting import router
    paths = [r.path for r in router.routes]
    assert "/playbooks" in paths


def test_download_endpoint_exists():
    from app.api.v1.endpoints.drafting import router
    paths = [r.path for r in router.routes]
    assert "/download/{draft_id}" in paths


def test_addin_payload_endpoint_exists():
    from app.api.v1.endpoints.drafting import router
    paths = [r.path for r in router.routes]
    assert "/addin-payload/{draft_id}" in paths


def test_intake_schema_returns_stages():
    """Verify _build_schema returns the expected stage structure."""
    from app.api.v1.endpoints.drafting import _build_schema

    schema = _build_schema("nda_mutual")
    assert schema["contract_type"] == "nda_mutual"
    stage_names = [s["stage"] for s in schema["stages"]]
    assert "basics" in stage_names
    assert "parties" in stage_names
    assert "nda_details" in stage_names
    assert "legal" in stage_names


def test_intake_schema_saas_stages():
    """SaaS schema should include saas_details but not nda_details."""
    from app.api.v1.endpoints.drafting import _build_schema

    schema = _build_schema("saas")
    stage_names = [s["stage"] for s in schema["stages"]]
    assert "saas_details" in stage_names
    assert "nda_details" not in stage_names


def test_playbook_info_fields():
    """Playbook list endpoint should have correct response model fields."""
    from app.api.v1.endpoints.drafting import PlaybookInfo

    info = PlaybookInfo(
        name="Test", contract_type="nda_mutual", jurisdiction="US-DE", clause_count=10
    )
    assert info.name == "Test"
    assert info.clause_count == 10
