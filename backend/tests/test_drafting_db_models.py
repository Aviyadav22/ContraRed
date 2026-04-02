"""Tests for DraftSession and DraftingPlaybook database models."""

from __future__ import annotations

import pytest


def test_draft_session_model_exists():
    from app.models.drafting import DraftSession
    assert DraftSession.__tablename__ == "draft_sessions"


def test_draft_session_fields():
    from app.models.drafting import DraftSession
    columns = {c.name for c in DraftSession.__table__.columns}
    expected = {"id", "user_id", "org_id", "contract_type", "status",
                "draft_request", "raw_draft", "quality_report", "final_draft",
                "tokens_used", "created_at", "completed_at"}
    assert expected.issubset(columns)


def test_drafting_playbook_model_exists():
    from app.models.drafting import DraftingPlaybook
    assert DraftingPlaybook.__tablename__ == "drafting_playbooks"


def test_drafting_playbook_fields():
    from app.models.drafting import DraftingPlaybook
    columns = {c.name for c in DraftingPlaybook.__table__.columns}
    expected = {"id", "org_id", "contract_type", "name", "jurisdiction",
                "clauses", "is_default", "created_at", "updated_at"}
    assert expected.issubset(columns)


def test_draft_session_status_enum():
    from app.models.drafting import DraftSessionStatus
    assert DraftSessionStatus.PROCESSING.value == "processing"
    assert DraftSessionStatus.COMPLETE.value == "complete"
