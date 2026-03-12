-- Migration 009: Phase 1 Security — MFA, SSO, RBAC columns
-- Adds MFA fields to users, SSO/MFA fields to organizations,
-- and expands the user role enum to support 5-tier RBAC.
--
-- Safe to run multiple times (all statements use IF NOT EXISTS / IF EXISTS).

-- ============================================================================
-- 1. Expand UserRole enum with new 5-tier values
-- ============================================================================
-- PostgreSQL enums need ALTER TYPE to add values.
-- These are idempotent: IF NOT EXISTS prevents errors on re-run.

DO $$ BEGIN
    ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'viewer';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'reviewer';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'manager';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 'admin' and 'super_admin' may already exist from migration 005
DO $$ BEGIN
    ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'admin';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin';
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;


-- ============================================================================
-- 2. MFA fields on users table
-- ============================================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_backup_codes JSONB;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_provider_id VARCHAR(255);


-- ============================================================================
-- 3. SSO and MFA enforcement fields on organizations table
-- ============================================================================

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS workos_org_id VARCHAR(255);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS sso_provider VARCHAR(50);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS mfa_required BOOLEAN DEFAULT FALSE;

-- sso_enabled and entra_tenant_id may already exist from initial schema
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS sso_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS entra_tenant_id VARCHAR(255);


-- ============================================================================
-- 4. Indexes for new columns
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_users_mfa_enabled ON users(mfa_enabled) WHERE mfa_enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_users_sso_provider_id ON users(sso_provider_id) WHERE sso_provider_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_organizations_sso_enabled ON organizations(sso_enabled) WHERE sso_enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_organizations_workos_org_id ON organizations(workos_org_id) WHERE workos_org_id IS NOT NULL;


-- ============================================================================
-- 5. Comments for documentation
-- ============================================================================

COMMENT ON COLUMN users.mfa_enabled IS 'Whether TOTP MFA is active for this user';
COMMENT ON COLUMN users.mfa_secret IS 'Encrypted TOTP secret (pyotp base32 key)';
COMMENT ON COLUMN users.mfa_backup_codes IS 'JSON array of bcrypt-hashed backup codes';
COMMENT ON COLUMN users.sso_provider_id IS 'WorkOS user ID or IdP subject identifier';
COMMENT ON COLUMN organizations.workos_org_id IS 'WorkOS organization ID for SSO brokering';
COMMENT ON COLUMN organizations.sso_provider IS 'SSO IdP type: azure_ad, okta, google';
COMMENT ON COLUMN organizations.mfa_required IS 'If true, all org users must enable MFA';
