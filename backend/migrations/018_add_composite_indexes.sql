-- Migration 018: Add composite indexes for common query patterns
-- These serve the actual query patterns better than separate single-column indexes.
-- Use CONCURRENTLY to avoid locking tables in production.

-- Documents: list_documents() queries WHERE user_id = ? ORDER BY created_at DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_user_created
    ON documents(user_id, created_at DESC);

-- UsageLogs: quota check queries WHERE user_id = ? AND created_at >= ?
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_logs_user_created
    ON usage_logs(user_id, created_at DESC);

-- DocumentRisks: joined/filtered by document_id, often ordered by created_at
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_document_risks_doc_created
    ON document_risks(document_id, created_at DESC);
