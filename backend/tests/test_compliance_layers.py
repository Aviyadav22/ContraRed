"""Unit tests for compliance layer service — merge_rules, calculate_compliance_score, and DPDP layer validation."""
import pytest
from app.services.compliance_layer_service import (
    merge_rules,
    calculate_compliance_score,
    _strip_layer_prefix,
    _find_matching_key,
)


# ============================================================
# merge_rules tests
# ============================================================

def test_merge_rules_no_overlap():
    """Separate clause types should all be present in merged output."""
    playbook = [
        {"name": "limitation_of_liability", "risk_level": "RED", "primary_position": "Cap at 12 months"},
        {"name": "indemnification", "risk_level": "RED", "primary_position": "Mutual"},
    ]
    layer = [
        {"name": "dpdp_consent_mechanism", "risk_level": "RED", "primary_position": "DPDP consent"},
        {"name": "dpdp_breach_notification", "risk_level": "RED", "primary_position": "72h notify"},
    ]
    result = merge_rules(playbook, layer)
    names = [r["name"] for r in result]
    assert "limitation_of_liability" in names
    assert "indemnification" in names
    assert "dpdp_consent_mechanism" in names
    assert "dpdp_breach_notification" in names
    assert len(result) == 4


def test_merge_rules_with_overlap_layer_stricter():
    """When compliance layer has stricter risk, it should replace playbook rule."""
    playbook = [
        {"name": "data_protection", "risk_level": "YELLOW", "primary_position": "Basic data protection"},
    ]
    layer = [
        {"name": "dpdp_data_protection", "risk_level": "RED", "primary_position": "DPDP strict"},
    ]
    result = merge_rules(playbook, layer)
    assert len(result) == 1
    assert result[0]["risk_level"] == "RED"
    assert result[0]["primary_position"] == "DPDP strict"


def test_merge_rules_with_overlap_playbook_stricter():
    """When playbook has stricter risk, it should be kept over compliance layer rule."""
    playbook = [
        {"name": "data_retention", "risk_level": "RED", "primary_position": "Strict retention"},
    ]
    layer = [
        {"name": "dpdp_data_retention", "risk_level": "YELLOW", "primary_position": "DPDP retention"},
    ]
    result = merge_rules(playbook, layer)
    assert len(result) == 1
    assert result[0]["risk_level"] == "RED"
    assert result[0]["primary_position"] == "Strict retention"


def test_merge_rules_empty_layer():
    """Empty layer rules should return playbook rules unchanged."""
    playbook = [
        {"name": "scope", "risk_level": "YELLOW", "primary_position": "Scope rule"},
    ]
    result = merge_rules(playbook, [])
    assert len(result) == 1
    assert result[0]["name"] == "scope"


def test_merge_rules_empty_playbook():
    """Empty playbook should return layer rules."""
    layer = [
        {"name": "dpdp_consent_mechanism", "risk_level": "RED", "primary_position": "Consent"},
    ]
    result = merge_rules(None, layer)
    assert len(result) == 1
    assert result[0]["name"] == "dpdp_consent_mechanism"


def test_merge_rules_both_empty():
    """Both empty should return empty list."""
    result = merge_rules(None, [])
    assert result == []
    result2 = merge_rules([], [])
    assert result2 == []


# ============================================================
# DPDP layer validation
# ============================================================

def test_dpdp_layer_has_18_rules():
    """The current lawyer-reviewed DPDP layer contains 18 rules."""
    from scripts.compliance_layers.dpdp import DPDP_LAYER
    assert len(DPDP_LAYER["rules"]) == 18


def test_dpdp_deal_breakers():
    """The current DPDP pack has six expressly escalated deal-breakers."""
    from scripts.compliance_layers.dpdp import DPDP_LAYER
    deal_breakers = [r for r in DPDP_LAYER["rules"] if r.get("is_deal_breaker")]
    assert len(deal_breakers) == 6
    db_types = {r["clause_type"] for r in deal_breakers}
    assert "dpdp_consent_mechanism" in db_types
    assert "dpdp_data_principal_rights" in db_types
    assert "dpdp_breach_notification" in db_types
    assert "dpdp_cross_border_transfer" in db_types


def test_dpdp_all_rules_have_required_fields():
    """Every DPDP rule must have clause_type, risk_level, primary_position, detection_patterns."""
    from scripts.compliance_layers.dpdp import DPDP_LAYER
    for rule in DPDP_LAYER["rules"]:
        assert "clause_type" in rule, "Missing clause_type in rule"
        assert "risk_level" in rule, f"Missing risk_level in {rule['clause_type']}"
        assert "primary_position" in rule, f"Missing primary_position in {rule['clause_type']}"
        assert "detection_patterns" in rule, f"Missing detection_patterns in {rule['clause_type']}"
        assert len(rule["detection_patterns"]) > 0, f"Empty detection_patterns in {rule['clause_type']}"


# ============================================================
# calculate_compliance_score tests
# ============================================================

def test_compliance_score_all_green():
    """All GREEN should score 100."""
    results = [
        {"risk_level": "GREEN", "is_deal_breaker": False},
        {"risk_level": "GREEN", "is_deal_breaker": False},
        {"risk_level": "GREEN", "is_deal_breaker": False},
    ]
    score = calculate_compliance_score(results)
    assert score["score"] == 100
    assert score["compliant"] == 3
    assert score["non_compliant"] == 0
    assert score["deal_breakers_failing"] == 0


def test_compliance_score_all_red():
    """All RED should score 0."""
    results = [
        {"risk_level": "RED", "is_deal_breaker": True},
        {"risk_level": "RED", "is_deal_breaker": False},
    ]
    score = calculate_compliance_score(results)
    assert score["score"] == 0
    assert score["non_compliant"] == 2
    assert score["deal_breakers_failing"] == 1


def test_compliance_score_mixed():
    """Mixed results should calculate weighted score."""
    results = [
        {"risk_level": "GREEN", "is_deal_breaker": False},
        {"risk_level": "YELLOW", "is_deal_breaker": False},
        {"risk_level": "RED", "is_deal_breaker": True},
        {"risk_level": "RED", "is_deal_breaker": False},
    ]
    score = calculate_compliance_score(results)
    # (1*1.0 + 1*0.5 + 0 + 0) / 4 = 0.375 → 38%
    assert score["score"] == 38
    assert score["compliant"] == 1
    assert score["partial"] == 1
    assert score["non_compliant"] == 2
    assert score["deal_breakers_failing"] == 1


def test_compliance_score_empty():
    """Empty results should return zero score."""
    score = calculate_compliance_score([])
    assert score["score"] == 0
    assert score["total_rules"] == 0
    assert score["status"] == "not_assessed"


def test_compliance_score_does_not_reward_unassessed_rules():
    results = [
        {"status": "compliant", "risk_level": "GREEN"},
        {"status": "unassessed", "risk_level": ""},
    ]
    score = calculate_compliance_score(results)
    assert score["score"] == 50
    assert score["unassessed"] == 1
    assert score["complete"] is False


def test_merge_preserves_compliance_provenance_when_playbook_is_stricter():
    playbook = [{
        "id": "pb-rule",
        "name": "data_retention",
        "risk_level": "RED",
    }]
    layer = [{
        "id": "compliance:dpdp:1",
        "name": "dpdp_data_retention",
        "risk_level": "YELLOW",
        "_compliance_layer": "dpdp",
        "_compliance_layers": ["dpdp"],
    }]
    merged = merge_rules(playbook, layer)
    assert merged[0]["id"] == "pb-rule"
    assert merged[0]["_compliance_layers"] == ["dpdp"]


# ============================================================
# Helper function tests
# ============================================================

def test_strip_layer_prefix():
    """Layer prefix stripping should work correctly."""
    assert _strip_layer_prefix("dpdp_consent_mechanism") == "consent_mechanism"
    assert _strip_layer_prefix("gdpr_data_retention") == "data_retention"
    assert _strip_layer_prefix("ccpa_consumer_rights") == "consumer_rights"
    assert _strip_layer_prefix("limitation_of_liability") == "limitation_of_liability"


def test_find_matching_key():
    """Matching key lookup should find overlapping base types."""
    rules = {
        "data_protection": {"name": "data_protection"},
        "limitation_of_liability": {"name": "limitation_of_liability"},
    }
    assert _find_matching_key(rules, "data_protection") == "data_protection"
    assert _find_matching_key(rules, "consent_mechanism") is None


# ============================================================
# API integration tests
# ============================================================

@pytest.mark.asyncio
async def test_list_compliance_layers_requires_auth(client):
    """GET /compliance-layers should require authentication."""
    resp = await client.get("/api/v1/documents/compliance-layers")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_compliance_layers_empty(client, test_user_data):
    """GET /compliance-layers returns empty list when no layers are seeded."""
    from tests.conftest import register_and_login
    token = await register_and_login(client, test_user_data)
    resp = await client.get(
        "/api/v1/documents/compliance-layers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_compliance_layer_not_found(client, test_user_data):
    """GET /compliance-layers/{code} returns 404 for unknown layer."""
    from tests.conftest import register_and_login
    token = await register_and_login(client, test_user_data)
    resp = await client.get(
        "/api/v1/documents/compliance-layers/nonexistent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_compliance_layers_after_seed(client, db_session, test_user_data):
    """GET /compliance-layers returns seeded layers."""
    from tests.conftest import register_and_login
    from app.services.compliance_layer_service import seed_compliance_layers
    await seed_compliance_layers(db_session)
    token = await register_and_login(client, test_user_data)
    resp = await client.get(
        "/api/v1/documents/compliance-layers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    layers = resp.json()
    assert len(layers) >= 1
    codes = [layer["code"] for layer in layers]
    assert "dpdp" in codes


@pytest.mark.asyncio
async def test_get_compliance_layer_detail(client, db_session, test_user_data):
    """GET /compliance-layers/dpdp returns layer with 12 rules."""
    from tests.conftest import register_and_login
    from app.services.compliance_layer_service import seed_compliance_layers
    await seed_compliance_layers(db_session)
    token = await register_and_login(client, test_user_data)
    resp = await client.get(
        "/api/v1/documents/compliance-layers/dpdp",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "dpdp"
    assert len(data["rules"]) == 18
    # Verify deal-breaker count
    deal_breakers = [r for r in data["rules"] if r["is_deal_breaker"]]
    assert len(deal_breakers) == 6


@pytest.mark.asyncio
async def test_analyze_request_schema_accepts_no_compliance_layers():
    """AnalyzeRequest model should accept requests without compliance_layers (backwards compatible)."""
    # Import the Pydantic model directly to verify schema compatibility
    # (Can't do full HTTP test because tenant_context middleware uses PostgreSQL set_config)
    import sys
    sys.path.insert(0, ".")
    from app.api.v1.endpoints.documents import AnalyzeRequest
    # No compliance_layers — should default to empty list
    req = AnalyzeRequest(text="Test contract text here.")
    assert req.compliance_layers == []
    # With compliance_layers
    req2 = AnalyzeRequest(text="Test contract text here.", compliance_layers=["dpdp"])
    assert req2.compliance_layers == ["dpdp"]
