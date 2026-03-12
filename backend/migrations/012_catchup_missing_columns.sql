-- ============================================================================
-- Migration 012: Catchup — add columns that exist in Python models but
-- were never explicitly migrated (relied on create_all for initial setup).
--
-- These columns are needed for:
--   - RLS policy on usage_logs (references organization_id)
--   - Razorpay customer tracking on users
--   - Login tracking on users
--   - Org-level settings
-- ============================================================================

-- 1. usage_logs.organization_id (CRITICAL: RLS policy in 010 references this)
ALTER TABLE usage_logs
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);

CREATE INDEX IF NOT EXISTS idx_usage_logs_organization_id
    ON usage_logs(organization_id);

-- 2. users.razorpay_customer_id
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR(255);

-- 3. users.last_login
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

-- 4. organizations.org_settings
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS org_settings JSONB;

-- Done
