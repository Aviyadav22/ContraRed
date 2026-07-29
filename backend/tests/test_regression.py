"""
Regression test suite for Ralph Loop quality gates.
These tests validate that EXISTING functionality is not broken by new changes.
Run after EVERY implementation task: pytest tests/test_regression.py -v
"""
import pytest
from tests.conftest import register_and_login


# ============================================================
# AUTH REGRESSION
# ============================================================

@pytest.mark.asyncio
async def test_reg_auth_register(client, test_user_data):
    """Auth: registration still works."""
    resp = await client.post("/api/v1/auth/register", json=test_user_data)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_reg_auth_login(client, test_user_data):
    """Auth: login still works."""
    await client.post("/api/v1/auth/register", json=test_user_data)
    resp = await client.post("/api/v1/auth/login", data={
        "username": test_user_data["email"],
        "password": test_user_data["password"],
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_reg_auth_me(client, test_user_data):
    """Auth: /me endpoint still works."""
    token = await register_and_login(client, test_user_data)
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


# ============================================================
# DOCUMENTS REGRESSION
# ============================================================

@pytest.mark.asyncio
async def test_reg_analyze_requires_auth(client):
    """Documents: analyze requires auth."""
    resp = await client.post("/api/v1/documents/analyze", json={"text": "test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reg_analyze_text_validation(client, test_user_data):
    """Documents: text length validation still works."""
    token = await register_and_login(client, test_user_data)
    long_text = "x" * 600000
    resp = await client.post("/api/v1/documents/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": long_text},
    )
    assert resp.status_code == 422


# ============================================================
# PLAYBOOKS REGRESSION
# ============================================================

@pytest.mark.asyncio
async def test_reg_playbook_list(client, test_user_data):
    """Playbooks: listing still works."""
    token = await register_and_login(client, test_user_data)
    resp = await client.get("/api/v1/playbooks/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reg_playbook_requires_auth(client):
    """Playbooks: auth still required."""
    resp = await client.get("/api/v1/playbooks/")
    assert resp.status_code == 401


# ============================================================
# PIPELINE REGRESSION
# ============================================================

@pytest.mark.asyncio
async def test_reg_pipeline_import():
    """Pipeline: AnalysisPipeline importable."""
    from app.services.analysis_pipeline import AnalysisPipeline, PipelineResult
    assert AnalysisPipeline is not None
    assert PipelineResult is not None


@pytest.mark.asyncio
async def test_reg_pipeline_graceful_degradation():
    """Pipeline: graceful degradation when AI unavailable."""
    from unittest.mock import patch
    from app.services.analysis_pipeline import AnalysisPipeline

    NDA_TEXT = """MUTUAL NON-DISCLOSURE AGREEMENT
    1. CONFIDENTIAL INFORMATION
    Confidential Information means any information disclosed by either party.
    2. TERM
    This Agreement shall remain in effect for five (5) years.
    3. GOVERNING LAW
    This Agreement shall be governed by the laws of India.
    """

    pipeline = AnalysisPipeline()
    with patch.object(pipeline._analyzer, 'analyze_full_contract', side_effect=Exception("No API key")):
        with patch.object(pipeline._analyzer, 'generate_fix', side_effect=Exception("No API key")):
            result = await pipeline.run(NDA_TEXT, playbook_rules=None)

    assert result.partial is True
    assert result.redlines is not None


# ============================================================
# HEALTH REGRESSION
# ============================================================

@pytest.mark.asyncio
async def test_reg_health_endpoint(client):
    """Health: basic health check works."""
    resp = await client.get("/health")
    assert resp.status_code == 200


# ============================================================
# IMPORTS REGRESSION
# ============================================================

def test_reg_main_imports():
    """Main: app imports without error."""
    from main import app
    assert app is not None


def test_reg_models_import():
    """Models: all core models import."""
    from app.models.user import User
    from app.models.document import Document
    from app.models.playbook import Playbook
    from app.models.organization import Organization
    assert User is not None
    assert Document is not None
    assert Playbook is not None
    assert Organization is not None


def test_reg_services_import():
    """Services: core services import."""
    from app.services.analysis_pipeline import AnalysisPipeline
    from app.services.jurisdiction_detector import JurisdictionDetector
    assert AnalysisPipeline is not None
    assert JurisdictionDetector is not None


# ============================================================
# BILLING REGRESSION
# ============================================================

@pytest.mark.asyncio
async def test_reg_billing_plans(client, test_user_data):
    """Billing: plan listing still works."""
    token = await register_and_login(client, test_user_data)
    resp = await client.get("/api/v1/billing/plans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
