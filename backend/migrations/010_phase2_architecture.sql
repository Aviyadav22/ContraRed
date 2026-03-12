-- Phase 2: Architecture for Legal (3.7/10 → 10/10)
-- Migration 010: Document versioning, multi-tenancy, immutable audit trail
-- Run AFTER all previous migrations (001-009)

BEGIN;

-- ============================================================================
-- 2.1 Document Versioning & Revision Chains
-- ============================================================================

-- Add versioning columns to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS parent_document_id UUID REFERENCES documents(id) ON DELETE SET NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS root_document_id UUID REFERENCES documents(id) ON DELETE SET NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_documents_root_document_id ON documents(root_document_id);
CREATE INDEX IF NOT EXISTS ix_documents_organization_id ON documents(organization_id);
CREATE INDEX IF NOT EXISTS ix_documents_content_hash ON documents(content_hash);

-- Immutable version snapshots
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    risk_summary JSONB,
    total_risks INTEGER DEFAULT 0,
    metadata JSONB,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_doc_versions_doc_version ON document_versions(document_id, version_number);
CREATE INDEX IF NOT EXISTS ix_doc_versions_document_id ON document_versions(document_id);

-- Cached diffs between versions
CREATE TABLE IF NOT EXISTS document_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_a INTEGER NOT NULL,
    version_b INTEGER NOT NULL,
    diff_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_doc_comparisons_unique ON document_comparisons(document_id, version_a, version_b);

-- ============================================================================
-- 2.2 Multi-Tenancy with Row-Level Security
-- ============================================================================

-- Backfill organization_id on documents from user's org
UPDATE documents d
SET organization_id = u.organization_id
FROM users u
WHERE d.user_id = u.id
  AND d.organization_id IS NULL
  AND u.organization_id IS NOT NULL;

-- Enable RLS on documents
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policy: users can only see docs from their org (or their own if no org)
CREATE POLICY tenant_isolation_documents ON documents
    FOR ALL
    USING (
        organization_id = current_setting('app.current_org_id', true)::uuid
        OR (organization_id IS NULL AND user_id = current_setting('app.current_user_id', true)::uuid)
    );

-- Super admin bypass policy
CREATE POLICY superadmin_bypass_documents ON documents
    FOR ALL
    USING (current_setting('app.is_super_admin', true) = 'true');

-- Enable RLS on document_risks (cascade through document ownership)
ALTER TABLE document_risks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_document_risks ON document_risks
    FOR ALL
    USING (
        document_id IN (
            SELECT id FROM documents
            WHERE organization_id = current_setting('app.current_org_id', true)::uuid
               OR (organization_id IS NULL AND user_id = current_setting('app.current_user_id', true)::uuid)
        )
    );

CREATE POLICY superadmin_bypass_document_risks ON document_risks
    FOR ALL
    USING (current_setting('app.is_super_admin', true) = 'true');

-- Enable RLS on audit_logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    FOR ALL
    USING (
        organization_id = current_setting('app.current_org_id', true)::uuid
        OR user_id = current_setting('app.current_user_id', true)::uuid
    );

CREATE POLICY superadmin_bypass_audit_logs ON audit_logs
    FOR ALL
    USING (current_setting('app.is_super_admin', true) = 'true');

-- Enable RLS on usage_logs
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_usage_logs ON usage_logs
    FOR ALL
    USING (
        organization_id = current_setting('app.current_org_id', true)::uuid
        OR user_id = current_setting('app.current_user_id', true)::uuid
    );

CREATE POLICY superadmin_bypass_usage_logs ON usage_logs
    FOR ALL
    USING (current_setting('app.is_super_admin', true) = 'true');

-- ============================================================================
-- 2.4 Immutable Audit Trail with Hash Chain
-- ============================================================================

-- Add hash chain columns to audit_logs
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entry_hash VARCHAR(64);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS previous_hash VARCHAR(64);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS sequence_number BIGINT;

CREATE INDEX IF NOT EXISTS ix_audit_logs_sequence ON audit_logs(sequence_number);
CREATE INDEX IF NOT EXISTS ix_audit_logs_entry_hash ON audit_logs(entry_hash);

-- Create sequence for audit log numbering
CREATE SEQUENCE IF NOT EXISTS audit_log_sequence START 1;

-- Trigger to prevent UPDATE/DELETE on audit_logs (immutability)
CREATE OR REPLACE FUNCTION prevent_audit_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable: % operations are not allowed', TG_OP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Only create trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_immutability_guard') THEN
        CREATE TRIGGER audit_immutability_guard
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_mutation();
    END IF;
END
$$;

-- ============================================================================
-- Performance indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_documents_user_created ON documents(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_documents_org_created ON documents(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_logs_org_timestamp ON audit_logs(organization_id, timestamp DESC);

COMMIT;
