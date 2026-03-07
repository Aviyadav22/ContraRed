-- Migration 008: Add performance indexes on frequently queried columns
-- These indexes prevent full table scans on user-scoped queries

-- Documents: queried by user_id in every list/stats call
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- DocumentRisks: queried by document_id when fetching risks
CREATE INDEX IF NOT EXISTS idx_document_risks_document_id ON document_risks(document_id);

-- UsageLogs: queried for monthly quota checks
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at DESC);

-- Playbooks: filtered by created_by in list queries
CREATE INDEX IF NOT EXISTS idx_playbooks_created_by ON playbooks(created_by);

-- AuditLogs: queried by organization and timestamp
CREATE INDEX IF NOT EXISTS idx_audit_logs_organization_id ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- ClauseLibrary: filtered by organization
CREATE INDEX IF NOT EXISTS idx_clause_library_organization_id ON clause_library(organization_id);
