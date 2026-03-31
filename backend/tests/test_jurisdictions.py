"""Tests for Global Jurisdiction Engine."""
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jurisdiction import Jurisdiction, JurisdictionRuleOverride
from app.services.jurisdiction_detector import (
    JurisdictionDetector,
    JURISDICTION_PROFILES,
    get_rule_overrides,
    apply_jurisdiction_overrides,
)
from scripts.seed_jurisdictions import (
    JURISDICTION_SEED_DATA,
    RULE_OVERRIDES_SEED_DATA,
    seed_jurisdictions,
)


# ============================================================
# Model tests
# ============================================================

def test_jurisdiction_model_import():
    """Jurisdiction model should import cleanly."""
    assert Jurisdiction.__tablename__ == "jurisdictions"


def test_jurisdiction_override_model_import():
    """JurisdictionRuleOverride should import cleanly."""
    assert JurisdictionRuleOverride.__tablename__ == "jurisdiction_rule_overrides"


def test_jurisdiction_override_has_unique_constraint():
    """Model should have unique constraint on (jurisdiction_id, clause_type)."""
    constraints = [
        c.name for c in JurisdictionRuleOverride.__table__.constraints
        if hasattr(c, 'name')
    ]
    assert "uq_jurisdiction_clause_type" in constraints


# ============================================================
# Seed data tests
# ============================================================

def test_seed_data_has_17_jurisdictions():
    """Seed data should have 17 jurisdiction profiles (13 original + 4 new)."""
    assert len(JURISDICTION_SEED_DATA) == 17


def test_seed_data_has_all_required_fields():
    """Every jurisdiction in seed data should have required fields."""
    for j in JURISDICTION_SEED_DATA:
        assert "code" in j, f"Missing 'code' in {j.get('name', 'unknown')}"
        assert "name" in j
        assert "display_name" in j
        assert "legal_system" in j
        assert j["legal_system"] in ("common_law", "civil_law", "hybrid")


def test_new_jurisdictions_exist():
    """US Federal, Texas, EU, ADGM should be in seed data."""
    codes = {j["code"] for j in JURISDICTION_SEED_DATA}
    assert "US" in codes, "US Federal missing"
    assert "TX-US" in codes, "Texas missing"
    assert "EU" in codes, "EU missing"
    assert "AE-ADGM" in codes, "ADGM missing"


def test_india_enhanced_with_new_statutes():
    """India should have enhanced statutes (MSME, Labour Codes, Companies Act)."""
    india = next(j for j in JURISDICTION_SEED_DATA if j["code"] == "IN")
    statute_text = " ".join(india["key_statutes"])
    assert "MSME" in statute_text
    assert "Labour Codes" in statute_text
    assert "Companies Act" in statute_text


def test_all_jurisdictions_have_overrides_or_none():
    """Each override jurisdiction code should match a seed data code."""
    seed_codes = {j["code"] for j in JURISDICTION_SEED_DATA}
    for code in RULE_OVERRIDES_SEED_DATA:
        assert code in seed_codes, f"Override code '{code}' not in seed data"


# ============================================================
# Detector tests (existing hardcoded profiles)
# ============================================================

def test_detector_has_13_hardcoded_profiles():
    """Detector should have 13 hardcoded jurisdiction profiles."""
    assert len(JURISDICTION_PROFILES) >= 13


def test_auto_detect_india():
    """Should detect India from governing law clause."""
    detector = JurisdictionDetector()
    result = detector.detect("This agreement shall be governed by the laws of India.")
    assert result.detected_jurisdiction == "IN"
    assert result.source == "auto"
    assert result.confidence >= 0.8


def test_auto_detect_california():
    """Should detect California from governing law clause."""
    detector = JurisdictionDetector()
    result = detector.detect(
        "This Agreement is governed by the laws of the State of California."
    )
    assert result.detected_jurisdiction == "CA-US"


def test_auto_detect_no_match():
    """Should return default when no governing law detected."""
    detector = JurisdictionDetector()
    result = detector.detect("This is a random text about cats and dogs.")
    assert result.detected_jurisdiction is None
    assert result.source == "default"
    assert result.confidence < 0.5


def test_user_override():
    """User override should take precedence over auto-detection."""
    detector = JurisdictionDetector()
    result = detector.detect(
        "governed by the laws of India",
        user_override="CA-US",
    )
    assert result.detected_jurisdiction == "CA-US"
    assert result.source == "user_override"
    assert result.confidence == 1.0


def test_adgm_alias_mapping():
    """ADGM alias should resolve to AE-ADGM (no profile until DB seeded)."""
    from app.services.jurisdiction_detector import _JURISDICTION_ALIASES
    assert _JURISDICTION_ALIASES["adgm"] == "AE-ADGM"
    assert _JURISDICTION_ALIASES["abu dhabi global market"] == "AE-ADGM"


# ============================================================
# Rule overrides tests (hardcoded)
# ============================================================

def test_india_overrides():
    """India should have 8 rule overrides."""
    overrides = get_rule_overrides("IN")
    assert len(overrides) == 8


def test_california_non_compete_suppressed():
    """California should suppress non-compete rule."""
    overrides = get_rule_overrides("CA-US")
    nc_override = next((o for o in overrides if o.rule_id == "non_compete"), None)
    assert nc_override is not None
    assert nc_override.suppress is True


# ============================================================
# AnalyzeRequest schema tests
# ============================================================

def test_analyze_request_accepts_jurisdiction():
    """AnalyzeRequest should accept jurisdiction field."""
    from app.api.v1.endpoints.documents import AnalyzeRequest
    req = AnalyzeRequest(text="test contract", jurisdiction="IN")
    assert req.jurisdiction == "IN"


def test_analyze_request_jurisdiction_optional():
    """AnalyzeRequest should work without jurisdiction (backwards compatible)."""
    from app.api.v1.endpoints.documents import AnalyzeRequest
    req = AnalyzeRequest(text="test contract")
    assert req.jurisdiction is None


# ============================================================
# API tests
# ============================================================

def test_jurisdiction_api_response_models():
    """Response models should import cleanly."""
    from app.api.v1.endpoints.jurisdictions import (
        JurisdictionSummary,
        JurisdictionDetail,
        RuleOverrideResponse,
    )
    summary = JurisdictionSummary(
        code="TEST", name="Test", display_name="Test Jurisdiction",
        legal_system="common_law", is_active=True, sort_order=1,
    )
    assert summary.code == "TEST"


@pytest.mark.asyncio
async def test_list_jurisdictions_requires_auth(client):
    """GET /jurisdictions should require auth."""
    resp = await client.get("/api/v1/jurisdictions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_jurisdiction_requires_auth(client):
    """GET /jurisdictions/IN should require auth."""
    resp = await client.get("/api/v1/jurisdictions/IN")
    assert resp.status_code == 401


# ============================================================
# DB seeding tests
# ============================================================

@pytest.mark.asyncio
async def test_seed_jurisdictions_creates_records(db_session: AsyncSession):
    """seed_jurisdictions should create 17 jurisdiction records."""
    count = await seed_jurisdictions(db_session)
    await db_session.commit()
    assert count == 17


@pytest.mark.asyncio
async def test_seed_jurisdictions_idempotent(db_session: AsyncSession):
    """Running seed twice should not create duplicates."""
    first = await seed_jurisdictions(db_session)
    await db_session.commit()
    second = await seed_jurisdictions(db_session)
    await db_session.commit()
    assert first == 17
    assert second == 0  # All already exist


@pytest.mark.asyncio
async def test_seeded_jurisdiction_has_overrides(db_session: AsyncSession):
    """Seeded India should have rule overrides."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    await seed_jurisdictions(db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(Jurisdiction)
        .options(selectinload(Jurisdiction.rule_overrides))
        .where(Jurisdiction.code == "IN")
    )
    india = result.scalar_one_or_none()
    assert india is not None
    assert india.name == "India"
    assert len(india.rule_overrides) == 8
    override_types = {ov.clause_type for ov in india.rule_overrides}
    assert "non_compete" in override_types
