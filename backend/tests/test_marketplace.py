"""Tests for Playbook Marketplace activation."""
import pytest
from pydantic import ValidationError


# ============================================================
# Model tests
# ============================================================

def test_marketplace_model_import():
    """PlaybookMarketplace should import cleanly."""
    from app.models.playbook import PlaybookMarketplace
    assert PlaybookMarketplace.__tablename__ == "playbook_marketplace"


def test_rating_model_import():
    """PlaybookRating should import cleanly."""
    from app.models.playbook import PlaybookRating
    assert PlaybookRating.__tablename__ == "playbook_ratings"


def test_marketplace_has_unique_constraint():
    """Marketplace should have unique constraint on playbook_id."""
    from app.models.playbook import PlaybookMarketplace
    constraints = [
        c.name for c in PlaybookMarketplace.__table__.constraints
        if hasattr(c, 'name')
    ]
    assert "uq_marketplace_playbook" in constraints


def test_rating_has_unique_constraint():
    """Rating should have unique constraint on (marketplace_id, user_id)."""
    from app.models.playbook import PlaybookRating
    constraints = [
        c.name for c in PlaybookRating.__table__.constraints
        if hasattr(c, 'name')
    ]
    assert "uq_rating_user" in constraints


# ============================================================
# Response model tests
# ============================================================

def test_marketplace_list_item_schema():
    """MarketplaceListItem should validate correctly."""
    from app.api.v1.endpoints.playbooks import MarketplaceListItem
    item = MarketplaceListItem(
        id="abc", playbook_id="def", playbook_name="Test",
        category="MSA", description="A test playbook",
        is_verified=False, download_count=10,
        avg_rating=4.5, rating_count=3, tags=["india"],
    )
    assert item.avg_rating == 4.5
    assert item.tags == ["india"]


def test_marketplace_browse_response_schema():
    """MarketplaceBrowseResponse should validate correctly."""
    from app.api.v1.endpoints.playbooks import MarketplaceBrowseResponse
    resp = MarketplaceBrowseResponse(items=[], total=0)
    assert resp.total == 0


def test_rating_create_validation():
    """RatingCreate should enforce 1-5 range."""
    from app.api.v1.endpoints.playbooks import RatingCreate
    r = RatingCreate(rating=5, review="Great!")
    assert r.rating == 5

    with pytest.raises(ValidationError):
        RatingCreate(rating=0)
    with pytest.raises(ValidationError):
        RatingCreate(rating=6)


# ============================================================
# Industry playbook seed tests
# ============================================================

def test_fintech_playbook():
    """Fintech playbook should have RBI/DPDP rules."""
    from scripts.playbooks.fintech import FINTECH
    assert FINTECH["name"] == "Fintech Services Agreement (India)"
    assert FINTECH["category"] == "MSA"
    assert len(FINTECH["rules"]) >= 8
    clause_types = [r["clause_type"] for r in FINTECH["rules"]]
    assert "rbi_data_localization" in clause_types
    assert "ppi_guidelines" in clause_types
    assert "data_protection_dpdp" in clause_types


def test_healthcare_playbook():
    """Healthcare playbook should have DPDP/CDSCO rules."""
    from scripts.playbooks.healthcare import HEALTHCARE
    assert HEALTHCARE["name"] == "Healthcare Vendor Agreement (India)"
    assert HEALTHCARE["category"] == "VENDOR"
    assert len(HEALTHCARE["rules"]) >= 8
    clause_types = [r["clause_type"] for r in HEALTHCARE["rules"]]
    assert "sensitive_personal_data" in clause_types
    assert "cdsco_compliance" in clause_types


def test_it_services_playbook():
    """IT Services playbook should have IT Act/CERT-In/SOC2 rules."""
    from scripts.playbooks.it_services import IT_SERVICES
    assert IT_SERVICES["name"] == "IT Services Agreement (India)"
    assert IT_SERVICES["category"] == "MSA"
    assert len(IT_SERVICES["rules"]) >= 9
    clause_types = [r["clause_type"] for r in IT_SERVICES["rules"]]
    assert "certin_incident_reporting" in clause_types
    assert "soc2_iso27001" in clause_types


def test_total_playbooks_count():
    """Should have 10 system-default playbooks (the orphan industry seed
    script was retired in Phase A consolidation; industry playbooks live as
    standalone modules in scripts/playbooks/ and are seeded on demand via
    seed_defaults._load_all_playbooks)."""
    from app.services.seed_defaults import _load_all_playbooks
    playbooks = _load_all_playbooks()
    assert len(playbooks) == 10


def test_industry_playbooks_have_deal_breakers():
    """Each industry playbook should have at least one deal-breaker rule."""
    from scripts.playbooks.fintech import FINTECH
    from scripts.playbooks.healthcare import HEALTHCARE
    from scripts.playbooks.it_services import IT_SERVICES

    for pb in [FINTECH, HEALTHCARE, IT_SERVICES]:
        deal_breakers = [r for r in pb["rules"] if r.get("is_deal_breaker")]
        assert len(deal_breakers) >= 1, f"{pb['name']} has no deal-breaker rules"


def test_all_industry_rules_have_required_fields():
    """All rules in industry playbooks should have required fields."""
    from scripts.playbooks.fintech import FINTECH
    from scripts.playbooks.healthcare import HEALTHCARE
    from scripts.playbooks.it_services import IT_SERVICES

    for pb in [FINTECH, HEALTHCARE, IT_SERVICES]:
        for rule in pb["rules"]:
            assert "clause_type" in rule, f"Missing clause_type in {pb['name']}"
            assert "primary_position" in rule
            assert "risk_level" in rule
            assert rule["risk_level"] in ("red", "yellow", "green")


# ============================================================
# API tests
# ============================================================

@pytest.mark.asyncio
async def test_marketplace_browse_requires_auth(client):
    """GET /playbooks/marketplace/browse should require auth."""
    resp = await client.get("/api/v1/playbooks/marketplace/browse")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_marketplace_fork_requires_auth(client):
    """POST /playbooks/marketplace/{id}/fork should require auth."""
    resp = await client.post("/api/v1/playbooks/marketplace/00000000-0000-0000-0000-000000000000/fork")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_marketplace_rate_requires_auth(client):
    """POST /playbooks/marketplace/{id}/rate should require auth."""
    resp = await client.post(
        "/api/v1/playbooks/marketplace/00000000-0000-0000-0000-000000000000/rate",
        json={"rating": 5},
    )
    assert resp.status_code == 401
