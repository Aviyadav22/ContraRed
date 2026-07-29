"""Tests for institutional memory (org learning) service."""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.org_learning import (
    record_user_decision,
    get_org_risk_profile,
    generate_org_context,
    MIN_ENCOUNTERS_THRESHOLD,
)
from app.models.org_risk_profile import OrganizationRiskProfile
from app.models.organization import Organization


async def _create_test_org(db: AsyncSession) -> uuid.UUID:
    """Create a test organization and return its ID."""
    org = Organization(name="Test Org", domain="test.com")
    db.add(org)
    await db.flush()
    return org.id


# ============================================================
# Unit tests (use db_session fixture from conftest)
# ============================================================

@pytest.mark.asyncio
async def test_record_decision_creates_profile(db_session: AsyncSession):
    """First decision for a clause type should create a new profile."""
    org_id = await _create_test_org(db_session)
    await record_user_decision(db_session, org_id, "limitation_of_liability", "accept")
    await db_session.commit()

    profiles = await get_org_risk_profile(db_session, org_id)
    assert len(profiles) == 1
    assert profiles[0]["clause_type"] == "limitation_of_liability"
    assert profiles[0]["accept_count"] == 1
    assert profiles[0]["total_encounters"] == 1


@pytest.mark.asyncio
async def test_record_decision_increments_counters(db_session: AsyncSession):
    """Multiple decisions should increment the correct counters."""
    org_id = await _create_test_org(db_session)
    await record_user_decision(db_session, org_id, "indemnification", "accept")
    await record_user_decision(db_session, org_id, "indemnification", "reject")
    await record_user_decision(db_session, org_id, "indemnification", "modify")
    await record_user_decision(db_session, org_id, "indemnification", "reject")
    await db_session.commit()

    profiles = await get_org_risk_profile(db_session, org_id)
    assert len(profiles) == 1
    p = profiles[0]
    assert p["total_encounters"] == 4
    assert p["accept_count"] == 1
    assert p["reject_count"] == 2
    assert p["modify_count"] == 1


@pytest.mark.asyncio
async def test_generate_context_below_threshold(db_session: AsyncSession):
    """Should return empty string when encounters are below threshold."""
    org_id = await _create_test_org(db_session)
    # Record only 3 encounters (below MIN_ENCOUNTERS_THRESHOLD)
    for _ in range(3):
        await record_user_decision(db_session, org_id, "liability_cap", "accept")
    await db_session.commit()

    context = await generate_org_context(db_session, org_id)
    assert context == ""


@pytest.mark.asyncio
async def test_generate_context_above_threshold(db_session: AsyncSession):
    """Should return prompt text when encounters meet threshold."""
    org_id = await _create_test_org(db_session)
    # Record enough encounters
    for _ in range(MIN_ENCOUNTERS_THRESHOLD):
        await record_user_decision(db_session, org_id, "non_compete", "reject")
    await db_session.commit()

    context = await generate_org_context(db_session, org_id)
    assert "ORGANIZATION RISK CONTEXT" in context
    assert "Non Compete" in context
    assert "STRICT" in context  # 100% reject rate


@pytest.mark.asyncio
async def test_generate_context_none_org_id(db_session: AsyncSession):
    """Should return empty string when org_id is None."""
    context = await generate_org_context(db_session, None)
    assert context == ""


@pytest.mark.asyncio
async def test_multiple_clause_types(db_session: AsyncSession):
    """Should track different clause types separately."""
    org_id = await _create_test_org(db_session)
    await record_user_decision(db_session, org_id, "liability_cap", "accept")
    await record_user_decision(db_session, org_id, "indemnification", "reject")
    await record_user_decision(db_session, org_id, "liability_cap", "accept")
    await db_session.commit()

    profiles = await get_org_risk_profile(db_session, org_id)
    assert len(profiles) == 2
    by_type = {p["clause_type"]: p for p in profiles}
    assert by_type["liability_cap"]["accept_count"] == 2
    assert by_type["indemnification"]["reject_count"] == 1


# ============================================================
# Model tests
# ============================================================

def test_org_risk_profile_model_import():
    """OrganizationRiskProfile should import cleanly."""
    assert OrganizationRiskProfile.__tablename__ == "organization_risk_profiles"


def test_org_risk_profile_has_unique_constraint():
    """Model should have unique constraint on (org_id, clause_type)."""
    constraints = [c.name for c in OrganizationRiskProfile.__table__.constraints if hasattr(c, 'name')]
    assert "uq_org_clause_type" in constraints
