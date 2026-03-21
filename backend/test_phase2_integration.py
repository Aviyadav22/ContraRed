"""Phase 2 end-to-end integration verification tests."""
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-validation-only-32chars!")

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1

print("=" * 60)
print("PHASE 2 END-TO-END INTEGRATION VERIFICATION")
print("=" * 60)

# ========================================================================
# 2.1 Document Versioning
# ========================================================================
print("\n--- 2.1 Document Versioning ---")

def t1():
    from app.models.document import Document
    # Check versioning columns exist
    fields = set(Document.__table__.columns.keys())
    required = {"parent_document_id", "root_document_id", "version_number", "content_hash", "organization_id"}
    assert required <= fields, f"Missing columns: {required - fields}"
test("Document model has versioning columns", t1)

def t2():
    from app.models.document import Document
    h = Document.compute_content_hash("test contract text")
    assert len(h) == 64  # SHA-256 hex
    # Same input = same hash
    assert h == Document.compute_content_hash("test contract text")
    # Different input = different hash
    assert h != Document.compute_content_hash("different text")
test("compute_content_hash produces consistent SHA-256", t2)

def t3():
    from app.models.document import DocumentVersion
    fields = set(DocumentVersion.__table__.columns.keys())
    required = {"id", "document_id", "version_number", "content_hash", "risk_summary", "total_risks", "created_by", "created_at"}
    assert required <= fields, f"Missing columns: {required - fields}"
    # "metadata" is the column name, mapped as "version_metadata" in Python
    assert hasattr(DocumentVersion, "version_metadata")
test("DocumentVersion model has all required fields", t3)

def t4():
    from app.models.document import DocumentComparison
    fields = set(DocumentComparison.__table__.columns.keys())
    required = {"id", "document_id", "version_a", "version_b", "diff_data", "created_at"}
    assert required <= fields, f"Missing columns: {required - fields}"
test("DocumentComparison model has all required fields", t4)

def t5():
    from app.models import DocumentVersion, DocumentComparison
    assert DocumentVersion is not None
    assert DocumentComparison is not None
test("DocumentVersion and DocumentComparison exported from models.__init__", t5)

# ========================================================================
# 2.2 Multi-Tenancy
# ========================================================================
print("\n--- 2.2 Multi-Tenancy ---")

def t6():
    from app.middleware.tenant_context import set_tenant_context, clear_tenant_context, TenantContextMiddleware
    assert callable(set_tenant_context)
    assert callable(clear_tenant_context)
    assert TenantContextMiddleware is not None
test("Tenant context middleware and helpers importable", t6)

def t7():
    from app.db.tenant import get_tenant_db
    import inspect
    sig = inspect.signature(get_tenant_db)
    assert "db" in sig.parameters
    assert "current_user" in sig.parameters
test("get_tenant_db dependency has correct signature", t7)

def t8():
    # Verify TenantContextMiddleware is registered in main.py
    import inspect
    import main
    src = inspect.getsource(main)
    assert "TenantContextMiddleware" in src
    assert "app.add_middleware(TenantContextMiddleware)" in src
test("TenantContextMiddleware registered in main.py", t8)

def t9():
    # Document model now has organization_id FK
    from app.models.document import Document
    col = Document.__table__.columns["organization_id"]
    fks = [fk.target_fullname for fk in col.foreign_keys]
    assert "organizations.id" in fks
test("Document.organization_id has FK to organizations", t9)

# ========================================================================
# 2.3 Async Processing
# ========================================================================
print("\n--- 2.3 Async Processing ---")

def t10():
    from app.workers.tasks import TaskQueue, AnalysisJob, JobStatus, task_queue
    assert task_queue is not None
    assert isinstance(task_queue, TaskQueue)
    assert JobStatus.QUEUED.value == "queued"
    assert JobStatus.COMPLETED.value == "completed"
test("TaskQueue and AnalysisJob importable, singleton exists", t10)

def t11():
    from app.workers.tasks import AnalysisJob, JobStatus
    job = AnalysisJob(
        job_id="test-123",
        document_id="doc-456",
        user_id="user-789",
        contract_text="This is a test contract.",
        playbook_name="Test Playbook",
    )
    d = job.to_dict()
    assert d["job_id"] == "test-123"
    assert d["status"] == "queued"

    # Round-trip
    job2 = AnalysisJob.from_dict(d)
    assert job2.job_id == "test-123"
    assert job2.status == JobStatus.QUEUED
test("AnalysisJob serialization round-trip", t11)

def t12():
    # Verify async endpoints exist in documents.py
    import inspect
    from app.api.v1.endpoints import documents
    src = inspect.getsource(documents)
    assert "analyze-async" in src
    assert "AsyncAnalyzeResponse" in src
    assert "jobs/{job_id}" in src
    assert "JobStatusResponse" in src
test("Async analysis endpoints exist in documents.py", t12)

# ========================================================================
# 2.4 Immutable Audit Trail
# ========================================================================
print("\n--- 2.4 Immutable Audit Trail ---")

def t13():
    from app.models.audit_log import AuditLog
    fields = set(AuditLog.__table__.columns.keys())
    required = {"entry_hash", "previous_hash", "sequence_number"}
    assert required <= fields, f"Missing hash chain columns: {required - fields}"
test("AuditLog has hash chain columns", t13)

def t14():
    # Verify log_audit_event computes hashes
    import inspect
    from app.models.audit_log import log_audit_event
    src = inspect.getsource(log_audit_event)
    assert "hashlib.sha256" in src
    assert "previous_hash" in src
    assert "entry_hash" in src
    assert "sequence_number" in src
    assert "GENESIS" in src
test("log_audit_event computes hash chain", t14)

def t15():
    # Verify audit chain verification endpoint exists
    import inspect
    from app.api.v1.endpoints import audit
    src = inspect.getsource(audit)
    assert "verify" in src
    assert "ChainVerificationResult" in src
    assert "chain integrity" in src.lower() or "chain broken" in src.lower()
test("Audit chain verification endpoint exists", t15)

# ========================================================================
# 2.5 Infrastructure
# ========================================================================
print("\n--- 2.5 Infrastructure ---")

def t16():
    # Deep health check endpoint
    import inspect
    import main
    src = inspect.getsource(main)
    assert "/health/deep" in src
    assert "database" in src
    assert "redis" in src
    assert "ai_provider" in src
test("Deep health check endpoint exists with DB/Redis/AI checks", t16)

def t17():
    # Sentry integration
    import inspect
    import main
    src = inspect.getsource(main)
    assert "SENTRY_DSN" in src
    assert "sentry_sdk" in src
    assert "_before_send" in src
    assert "[REDACTED]" in src
test("Sentry integration with PII-stripping before_send hook", t17)

def t18():
    from app.core.config import settings
    assert hasattr(settings, "SENTRY_DSN")
    assert hasattr(settings, "SENTRY_ENVIRONMENT")
    assert hasattr(settings, "SENTRY_TRACES_SAMPLE_RATE")
test("Sentry config fields in settings", t18)

# ========================================================================
# Migration file
# ========================================================================
print("\n--- Migration ---")

def t19():
    import os
    path = os.path.join(os.path.dirname(__file__), "migrations", "010_phase2_architecture.sql")
    assert os.path.exists(path), "Migration file not found"
    with open(path) as f:
        sql = f.read()
    # Key elements
    assert "document_versions" in sql
    assert "document_comparisons" in sql
    assert "ROW LEVEL SECURITY" in sql
    assert "tenant_isolation" in sql
    assert "prevent_audit_mutation" in sql
    assert "entry_hash" in sql
    assert "previous_hash" in sql
    assert "sequence_number" in sql
test("Migration 010 contains all Phase 2 schema changes", t19)

def t20():
    # Version bump
    import inspect
    import main
    src = inspect.getsource(main)
    assert '"1.3.0"' in src
test("Version bumped to 1.3.0", t20)

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
print("=" * 60)

import sys
sys.exit(1 if failed else 0)
