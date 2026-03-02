-- Migration 003: Add indexes for audit log queries
-- Safe: IF NOT EXISTS is idempotent

CREATE INDEX IF NOT EXISTS idx_audit_logs_org_timestamp
    ON audit_logs(organization_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp
    ON audit_logs(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action
    ON audit_logs(action);

-- Make user_id nullable for failed login audit entries
ALTER TABLE audit_logs ALTER COLUMN user_id DROP NOT NULL;
