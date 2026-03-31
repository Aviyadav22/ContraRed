"""Tests for batch job persistence and new endpoints."""
import pytest


# ============================================================
# Model tests
# ============================================================

def test_batch_job_model_import():
    """BatchJob and BatchJobFile models should import cleanly."""
    from app.models.batch_job import BatchJob, BatchJobFile
    assert BatchJob.__tablename__ == "batch_jobs"
    assert BatchJobFile.__tablename__ == "batch_job_files"


def test_batch_job_has_compliance_layers_field():
    """BatchJob should have compliance_layers JSONB field."""
    from app.models.batch_job import BatchJob
    cols = {c.name for c in BatchJob.__table__.columns}
    assert "compliance_layers" in cols
    assert "risk_summary" in cols
    assert "playbook_id" in cols


def test_batch_job_file_has_processing_ms():
    """BatchJobFile should have processing_ms field."""
    from app.models.batch_job import BatchJobFile
    cols = {c.name for c in BatchJobFile.__table__.columns}
    assert "processing_ms" in cols
    assert "risk_summary" in cols
    assert "error_message" in cols


# ============================================================
# Response model tests
# ============================================================

def test_batch_history_item_model():
    """BatchHistoryItem should accept all expected fields."""
    from app.api.v1.endpoints.documents import BatchHistoryItem
    item = BatchHistoryItem(
        batch_id="test-1",
        created_at="2026-03-31T12:00:00Z",
        status="completed",
        total_files=5,
        completed_files=4,
        failed_files=1,
        risk_summary={"red": 3, "yellow": 5, "green": 10, "total": 18},
        compliance_layers=["dpdp"],
    )
    assert item.total_files == 5
    assert item.compliance_layers == ["dpdp"]


def test_batch_report_response_model():
    """BatchReportResponse should accept all expected fields."""
    from app.api.v1.endpoints.documents import BatchReportResponse
    report = BatchReportResponse(
        batch_id="test-1",
        total_files=3,
        completed_files=3,
        failed_files=0,
        aggregate_risk_summary={"red": 5, "yellow": 10, "green": 20, "total": 35},
        common_risks=["Limitation of Liability", "Indemnification"],
        per_file_summary=[
            {"filename": "a.docx", "status": "completed", "risk_summary": {"red": 2}},
        ],
    )
    assert report.total_files == 3
    assert len(report.common_risks) == 2


# ============================================================
# Tier-based batch file limit tests
# ============================================================

def test_batch_file_limit_free():
    """Free tier should have batch limit of 5."""
    from app.api.v1.endpoints.billing import get_plan_info
    plan = get_plan_info("free")
    assert plan["batch_files_limit"] == 5


def test_batch_file_limit_starter():
    """Starter tier should have batch limit of 10."""
    from app.api.v1.endpoints.billing import get_plan_info
    plan = get_plan_info("starter")
    assert plan["batch_files_limit"] == 10


def test_batch_file_limit_pro():
    """Pro tier should have batch limit of 25."""
    from app.api.v1.endpoints.billing import get_plan_info
    plan = get_plan_info("pro")
    assert plan["batch_files_limit"] == 25


def test_batch_file_limit_business():
    """Business tier should have batch limit of 50."""
    from app.api.v1.endpoints.billing import get_plan_info
    plan = get_plan_info("business")
    assert plan["batch_files_limit"] == 50


def test_batch_file_limit_enterprise():
    """Enterprise tier should have batch limit of 50."""
    from app.api.v1.endpoints.billing import get_plan_info
    plan = get_plan_info("enterprise")
    assert plan["batch_files_limit"] == 50


# ============================================================
# API integration tests
# ============================================================

@pytest.mark.asyncio
async def test_batch_history_requires_auth(client):
    """GET /batches should require authentication."""
    resp = await client.get("/api/v1/documents/batches")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_batch_history_empty(client, test_user_data):
    """GET /batches returns empty list for new user."""
    from tests.conftest import register_and_login
    token = await register_and_login(client, test_user_data)
    resp = await client.get(
        "/api/v1/documents/batches",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["batches"] == []
