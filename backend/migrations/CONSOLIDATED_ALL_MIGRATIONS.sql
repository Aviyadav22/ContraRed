-- ============================================================================
-- CONSOLIDATED CONTRARED DATABASE MIGRATIONS
-- Run this entire script in Supabase SQL Editor
-- Date: 2026-03-17
-- Migrations: 001 through 018 (20 files)
-- All statements are idempotent (safe to re-run)
--
-- IMPORTANT: Run this as the database owner / service_role
-- NOTE: Migration 018 uses CONCURRENTLY indexes — those CANNOT run inside
--       a transaction. They are placed at the very end outside any BEGIN/COMMIT.
-- ============================================================================


-- ============================================================================
-- MIGRATION 001: Add Hybrid Sentinel Fields to PlaybookRule
-- ============================================================================

ALTER TABLE playbook_rules
ADD COLUMN IF NOT EXISTS requires_ai_verification BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE playbook_rules
ADD COLUMN IF NOT EXISTS verification_prompt TEXT NULL;


-- ============================================================================
-- MIGRATION 002: Add ANALYST role to UserRole enum
-- ============================================================================

ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ANALYST';


-- ============================================================================
-- MIGRATION 003: Audit log indexes + nullable user_id
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_audit_logs_org_timestamp
    ON audit_logs(organization_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp
    ON audit_logs(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action
    ON audit_logs(action);

ALTER TABLE audit_logs ALTER COLUMN user_id DROP NOT NULL;


-- ============================================================================
-- MIGRATION 004: Account lockout fields
-- ============================================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP NULL;


-- ============================================================================
-- MIGRATION 005: Create Super Admin user
-- Password: admin@123 (CHANGE IMMEDIATELY via /api/v1/auth/change-password)
-- ============================================================================

INSERT INTO users (id, email, name, password_hash, role, subscription_tier, is_active, is_verified, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'aviyadav.official@gmail.com',
    'Avi Yadav',
    '$2b$12$VmlJ6IfllgkK93y/3o/GVuMFozfkpTbz6I3tNpD4soz2DaBz3026y',
    'SUPER_ADMIN',
    'ENTERPRISE',
    true,
    true,
    NOW(),
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    role = 'SUPER_ADMIN',
    subscription_tier = 'ENTERPRISE',
    password_hash = '$2b$12$VmlJ6IfllgkK93y/3o/GVuMFozfkpTbz6I3tNpD4soz2DaBz3026y';


-- ============================================================================
-- MIGRATION 006: Create clause_library table
-- ============================================================================

CREATE TABLE IF NOT EXISTS clause_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    clause_type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    approved_text TEXT NOT NULL,
    is_mandatory BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clause_library_org ON clause_library(organization_id);
CREATE INDEX IF NOT EXISTS idx_clause_library_type ON clause_library(organization_id, clause_type);
CREATE INDEX IF NOT EXISTS idx_clause_library_creator ON clause_library(created_by);


-- ============================================================================
-- MIGRATION 007: Create contract_templates table
-- ============================================================================

CREATE TABLE IF NOT EXISTS contract_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL DEFAULT 'custom',
    template_content TEXT,
    paired_playbook_id UUID REFERENCES playbooks(id) ON DELETE SET NULL,
    is_premium BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_templates_category ON contract_templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_paired_playbook ON contract_templates(paired_playbook_id);
CREATE INDEX IF NOT EXISTS idx_templates_is_premium ON contract_templates(is_premium);


-- ============================================================================
-- MIGRATION 008: Performance indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_document_risks_document_id ON document_risks(document_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_playbooks_created_by ON playbooks(created_by);
CREATE INDEX IF NOT EXISTS idx_audit_logs_organization_id ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_clause_library_organization_id ON clause_library(organization_id);


-- ============================================================================
-- MIGRATION 009: Phase 1 Security — MFA, SSO, RBAC
-- ============================================================================

DO $$ BEGIN ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'viewer'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'reviewer'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'manager'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'admin'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_backup_codes JSONB;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_provider_id VARCHAR(255);

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS workos_org_id VARCHAR(255);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS sso_provider VARCHAR(50);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS mfa_required BOOLEAN DEFAULT FALSE;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS sso_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS entra_tenant_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_users_mfa_enabled ON users(mfa_enabled) WHERE mfa_enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_users_sso_provider_id ON users(sso_provider_id) WHERE sso_provider_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_organizations_sso_enabled ON organizations(sso_enabled) WHERE sso_enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_organizations_workos_org_id ON organizations(workos_org_id) WHERE workos_org_id IS NOT NULL;

COMMENT ON COLUMN users.mfa_enabled IS 'Whether TOTP MFA is active for this user';
COMMENT ON COLUMN users.mfa_secret IS 'Encrypted TOTP secret (pyotp base32 key)';
COMMENT ON COLUMN users.mfa_backup_codes IS 'JSON array of bcrypt-hashed backup codes';
COMMENT ON COLUMN users.sso_provider_id IS 'WorkOS user ID or IdP subject identifier';
COMMENT ON COLUMN organizations.workos_org_id IS 'WorkOS organization ID for SSO brokering';
COMMENT ON COLUMN organizations.sso_provider IS 'SSO IdP type: azure_ad, okta, google';
COMMENT ON COLUMN organizations.mfa_required IS 'If true, all org users must enable MFA';


-- ============================================================================
-- MIGRATION 010: Phase 2 — Document versioning, multi-tenancy, audit trail
-- ============================================================================

BEGIN;

ALTER TABLE documents ADD COLUMN IF NOT EXISTS parent_document_id UUID REFERENCES documents(id) ON DELETE SET NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS root_document_id UUID REFERENCES documents(id) ON DELETE SET NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_documents_root_document_id ON documents(root_document_id);
CREATE INDEX IF NOT EXISTS ix_documents_organization_id ON documents(organization_id);
CREATE INDEX IF NOT EXISTS ix_documents_content_hash ON documents(content_hash);

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

CREATE TABLE IF NOT EXISTS document_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_a INTEGER NOT NULL,
    version_b INTEGER NOT NULL,
    diff_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_doc_comparisons_unique ON document_comparisons(document_id, version_a, version_b);

-- Backfill organization_id from users
UPDATE documents d
SET organization_id = u.organization_id
FROM users u
WHERE d.user_id = u.id
  AND d.organization_id IS NULL
  AND u.organization_id IS NOT NULL;

-- RLS on documents
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='documents' AND policyname='tenant_isolation_documents') THEN
        CREATE POLICY tenant_isolation_documents ON documents FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid
            OR (organization_id IS NULL AND user_id = current_setting('app.current_user_id', true)::uuid));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='documents' AND policyname='superadmin_bypass_documents') THEN
        CREATE POLICY superadmin_bypass_documents ON documents FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- RLS on document_risks
ALTER TABLE document_risks ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='document_risks' AND policyname='tenant_isolation_document_risks') THEN
        CREATE POLICY tenant_isolation_document_risks ON document_risks FOR ALL
        USING (document_id IN (SELECT id FROM documents WHERE organization_id = current_setting('app.current_org_id', true)::uuid
            OR (organization_id IS NULL AND user_id = current_setting('app.current_user_id', true)::uuid)));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='document_risks' AND policyname='superadmin_bypass_document_risks') THEN
        CREATE POLICY superadmin_bypass_document_risks ON document_risks FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- RLS on audit_logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='audit_logs' AND policyname='tenant_isolation_audit_logs') THEN
        CREATE POLICY tenant_isolation_audit_logs ON audit_logs FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid
            OR user_id = current_setting('app.current_user_id', true)::uuid);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='audit_logs' AND policyname='superadmin_bypass_audit_logs') THEN
        CREATE POLICY superadmin_bypass_audit_logs ON audit_logs FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- RLS on usage_logs
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='usage_logs' AND policyname='tenant_isolation_usage_logs') THEN
        CREATE POLICY tenant_isolation_usage_logs ON usage_logs FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid
            OR user_id = current_setting('app.current_user_id', true)::uuid);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='usage_logs' AND policyname='superadmin_bypass_usage_logs') THEN
        CREATE POLICY superadmin_bypass_usage_logs ON usage_logs FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- Immutable audit trail hash chain
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entry_hash VARCHAR(64);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS previous_hash VARCHAR(64);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS sequence_number BIGINT;

CREATE INDEX IF NOT EXISTS ix_audit_logs_sequence ON audit_logs(sequence_number);
CREATE INDEX IF NOT EXISTS ix_audit_logs_entry_hash ON audit_logs(entry_hash);
CREATE SEQUENCE IF NOT EXISTS audit_log_sequence START 1;

CREATE OR REPLACE FUNCTION prevent_audit_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable: % operations are not allowed', TG_OP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_immutability_guard') THEN
        CREATE TRIGGER audit_immutability_guard
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_documents_user_created ON documents(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_documents_org_created ON documents(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_logs_org_timestamp ON audit_logs(organization_id, timestamp DESC);

COMMIT;


-- ============================================================================
-- MIGRATION 011: Phase 3 — Billing Model
-- ============================================================================

ALTER TYPE plantype ADD VALUE IF NOT EXISTS 'starter' AFTER 'free';
ALTER TYPE plantype ADD VALUE IF NOT EXISTS 'business' AFTER 'pro';
ALTER TYPE subscriptiontier ADD VALUE IF NOT EXISTS 'starter' AFTER 'free';
ALTER TYPE subscriptiontier ADD VALUE IF NOT EXISTS 'business' AFTER 'pro';

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255) UNIQUE,
    ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS gateway VARCHAR(20) DEFAULT 'razorpay';

CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_sub_id
    ON subscriptions(stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_subscriptions_gateway ON subscriptions(gateway);

CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    subscription_id UUID REFERENCES subscriptions(id),
    amount INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    status VARCHAR(20) DEFAULT 'pending',
    plan VARCHAR(50) NOT NULL,
    description TEXT,
    gateway VARCHAR(20) DEFAULT 'razorpay',
    gateway_payment_id VARCHAR(255),
    gateway_invoice_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    paid_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_organization_id ON invoices(organization_id);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);

ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='invoices' AND policyname='tenant_isolation_invoices') THEN
        CREATE POLICY tenant_isolation_invoices ON invoices FOR ALL
        USING (organization_id::text = current_setting('app.current_org_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
            OR user_id::text = current_setting('app.current_user_id', true));
    END IF;
END $$;


-- ============================================================================
-- MIGRATION 012: Catchup missing columns
-- ============================================================================

ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_organization_id ON usage_logs(organization_id);

ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS org_settings JSONB;


-- ============================================================================
-- MIGRATION 013: RLS policies for all remaining tables
-- (playbooks, playbook_rules, document_versions, document_comparisons,
--  clause_library, contract_templates, analytics tables, phase 6 tables)
-- ============================================================================

BEGIN;

-- Playbooks
ALTER TABLE playbooks ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbooks' AND policyname='tenant_isolation_playbooks') THEN
        CREATE POLICY tenant_isolation_playbooks ON playbooks FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid
            OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
            OR is_public = true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbooks' AND policyname='superadmin_bypass_playbooks') THEN
        CREATE POLICY superadmin_bypass_playbooks ON playbooks FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- Playbook rules
ALTER TABLE playbook_rules ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_rules' AND policyname='tenant_isolation_playbook_rules') THEN
        CREATE POLICY tenant_isolation_playbook_rules ON playbook_rules FOR ALL
        USING (playbook_id IN (SELECT id FROM playbooks
            WHERE organization_id = current_setting('app.current_org_id', true)::uuid
               OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
               OR is_public = true));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_rules' AND policyname='superadmin_bypass_playbook_rules') THEN
        CREATE POLICY superadmin_bypass_playbook_rules ON playbook_rules FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- Document versions
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='document_versions' AND policyname='tenant_isolation_document_versions') THEN
        CREATE POLICY tenant_isolation_document_versions ON document_versions FOR ALL
        USING (document_id IN (SELECT id FROM documents
            WHERE organization_id = current_setting('app.current_org_id', true)::uuid
               OR (organization_id IS NULL AND user_id = current_setting('app.current_user_id', true)::uuid)));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='document_versions' AND policyname='superadmin_bypass_document_versions') THEN
        CREATE POLICY superadmin_bypass_document_versions ON document_versions FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- Document comparisons
ALTER TABLE document_comparisons ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='document_comparisons' AND policyname='tenant_isolation_document_comparisons') THEN
        CREATE POLICY tenant_isolation_document_comparisons ON document_comparisons FOR ALL
        USING (document_id IN (SELECT id FROM documents
            WHERE organization_id = current_setting('app.current_org_id', true)::uuid
               OR (organization_id IS NULL AND user_id = current_setting('app.current_user_id', true)::uuid)));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='document_comparisons' AND policyname='superadmin_bypass_document_comparisons') THEN
        CREATE POLICY superadmin_bypass_document_comparisons ON document_comparisons FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- Clause library
ALTER TABLE clause_library ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='clause_library' AND policyname='tenant_isolation_clause_library') THEN
        CREATE POLICY tenant_isolation_clause_library ON clause_library FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid
            OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='clause_library' AND policyname='superadmin_bypass_clause_library') THEN
        CREATE POLICY superadmin_bypass_clause_library ON clause_library FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

-- Contract templates
ALTER TABLE contract_templates ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='contract_templates' AND policyname='tenant_isolation_contract_templates') THEN
        CREATE POLICY tenant_isolation_contract_templates ON contract_templates FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid OR organization_id IS NULL);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='contract_templates' AND policyname='superadmin_bypass_contract_templates') THEN
        CREATE POLICY superadmin_bypass_contract_templates ON contract_templates FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

COMMIT;


-- ============================================================================
-- MIGRATION 014a: Rule feedback + templates org_id
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS rule_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES playbook_rules(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id),
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('helpful', 'not_helpful', 'false_positive', 'false_negative', 'correct', 'needs_improvement')),
    comment TEXT,
    clause_text TEXT,
    user_comment TEXT,
    suggested_risk_level VARCHAR(10),
    playbook_rule_id UUID REFERENCES playbook_rules(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rule_feedback_rule_id ON rule_feedback(rule_id);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_user_id ON rule_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_org_id ON rule_feedback(organization_id);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_rule ON rule_feedback(playbook_rule_id);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_type ON rule_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_created ON rule_feedback(created_at);

ALTER TABLE contract_templates ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);
CREATE INDEX IF NOT EXISTS idx_contract_templates_org_id ON contract_templates(organization_id);

COMMIT;


-- ============================================================================
-- MIGRATION 014b: Webhook idempotency tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gateway VARCHAR(20) NOT NULL,
    gateway_event_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_webhook_gateway_event UNIQUE (gateway, gateway_event_id)
);

CREATE INDEX IF NOT EXISTS ix_webhook_events_processed_at ON webhook_events(processed_at);

ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='webhook_events' AND policyname='webhook_events_service_policy') THEN
        CREATE POLICY webhook_events_service_policy ON webhook_events FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true')
        WITH CHECK (true);
    END IF;
END $$;


-- ============================================================================
-- MIGRATION 015a: Dunning management fields
-- ============================================================================

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS dunning_attempts INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_dunning_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS dunning_next_retry_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_subscriptions_dunning
    ON subscriptions(dunning_next_retry_at)
    WHERE status = 'past_due' AND dunning_next_retry_at IS NOT NULL;


-- ============================================================================
-- MIGRATION 015b: Phase 9 — Analytics
-- ============================================================================

ALTER TABLE documents ADD COLUMN IF NOT EXISTS word_count INTEGER DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_duration_ms INTEGER DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS contract_type VARCHAR(100) DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5,2) DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS counterparty VARCHAR(255) DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS contract_value NUMERIC(15,2) DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS expiry_date DATE DEFAULT NULL;

CREATE TABLE IF NOT EXISTS review_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    risks_reviewed INTEGER DEFAULT 0,
    risks_accepted INTEGER DEFAULT 0,
    risks_rejected INTEGER DEFAULT 0,
    notes TEXT,
    session_metadata JSONB
);

CREATE TABLE IF NOT EXISTS time_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    pages_per_hour NUMERIC(5,1) DEFAULT 5.0,
    minutes_per_risk NUMERIC(5,1) DEFAULT 15.0,
    hourly_rate NUMERIC(10,2) DEFAULT 5000.00,
    currency VARCHAR(3) DEFAULT 'INR',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roi_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    risk_value_per_red NUMERIC(12,2) DEFAULT 500000.00,
    risk_value_per_yellow NUMERIC(12,2) DEFAULT 100000.00,
    include_risk_value BOOLEAN DEFAULT true,
    include_time_savings BOOLEAN DEFAULT true,
    custom_methodology_note TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS benchmark_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    contract_type VARCHAR(100) NOT NULL,
    avg_risk_score NUMERIC(5,2),
    avg_risks_per_doc NUMERIC(8,2),
    avg_red_risks NUMERIC(8,2),
    avg_processing_ms INTEGER,
    document_count INTEGER DEFAULT 0,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_benchmark_org_type_period UNIQUE (organization_id, contract_type, period_start, period_end)
);

CREATE TABLE IF NOT EXISTS generated_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    parameters JSONB,
    report_data JSONB NOT NULL,
    format VARCHAR(20) DEFAULT 'json',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_documents_contract_type ON documents(contract_type);
CREATE INDEX IF NOT EXISTS ix_documents_risk_score ON documents(risk_score);
CREATE INDEX IF NOT EXISTS ix_documents_counterparty ON documents(counterparty);
CREATE INDEX IF NOT EXISTS ix_documents_expiry_date ON documents(expiry_date);
CREATE INDEX IF NOT EXISTS ix_review_sessions_user ON review_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_review_sessions_org ON review_sessions(organization_id);
CREATE INDEX IF NOT EXISTS ix_review_sessions_doc ON review_sessions(document_id);
CREATE INDEX IF NOT EXISTS ix_generated_reports_org ON generated_reports(organization_id);
CREATE INDEX IF NOT EXISTS ix_benchmark_profiles_org_type ON benchmark_profiles(organization_id, contract_type);

-- RLS for analytics tables (policies created in migration 013)
ALTER TABLE review_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_benchmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE roi_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmark_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_reports ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='review_sessions' AND policyname='tenant_isolation_review_sessions') THEN
        CREATE POLICY tenant_isolation_review_sessions ON review_sessions FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid
            OR user_id = current_setting('app.current_user_id', true)::uuid);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='review_sessions' AND policyname='superadmin_bypass_review_sessions') THEN
        CREATE POLICY superadmin_bypass_review_sessions ON review_sessions FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='time_benchmarks' AND policyname='tenant_isolation_time_benchmarks') THEN
        CREATE POLICY tenant_isolation_time_benchmarks ON time_benchmarks FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='time_benchmarks' AND policyname='superadmin_bypass_time_benchmarks') THEN
        CREATE POLICY superadmin_bypass_time_benchmarks ON time_benchmarks FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='roi_config' AND policyname='tenant_isolation_roi_config') THEN
        CREATE POLICY tenant_isolation_roi_config ON roi_config FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='roi_config' AND policyname='superadmin_bypass_roi_config') THEN
        CREATE POLICY superadmin_bypass_roi_config ON roi_config FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='benchmark_profiles' AND policyname='tenant_isolation_benchmark_profiles') THEN
        CREATE POLICY tenant_isolation_benchmark_profiles ON benchmark_profiles FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='benchmark_profiles' AND policyname='superadmin_bypass_benchmark_profiles') THEN
        CREATE POLICY superadmin_bypass_benchmark_profiles ON benchmark_profiles FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='generated_reports' AND policyname='tenant_isolation_generated_reports') THEN
        CREATE POLICY tenant_isolation_generated_reports ON generated_reports FOR ALL
        USING (organization_id = current_setting('app.current_org_id', true)::uuid
            OR created_by = current_setting('app.current_user_id', true)::uuid);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='generated_reports' AND policyname='superadmin_bypass_generated_reports') THEN
        CREATE POLICY superadmin_bypass_generated_reports ON generated_reports FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;


-- ============================================================================
-- MIGRATION 016: Phase 5 — Contract Coverage & Rule Feedback enhancements
-- ============================================================================

BEGIN;

ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS jurisdiction_overrides JSONB DEFAULT '{}';
ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 50;
ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS subcategory VARCHAR(50);
ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]';

CREATE MATERIALIZED VIEW IF NOT EXISTS rule_effectiveness AS
SELECT
    pr.id AS rule_id,
    pr.clause_type,
    pr.playbook_id,
    COUNT(rf.id) AS total_feedback,
    COUNT(CASE WHEN rf.feedback_type = 'false_positive' THEN 1 END) AS false_positives,
    COUNT(CASE WHEN rf.feedback_type = 'false_negative' THEN 1 END) AS false_negatives,
    COUNT(CASE WHEN rf.feedback_type = 'correct' THEN 1 END) AS correct_count,
    CASE WHEN COUNT(rf.id) > 0 THEN
        ROUND(COUNT(CASE WHEN rf.feedback_type = 'false_positive' THEN 1 END)::numeric / COUNT(rf.id) * 100, 1)
    ELSE 0 END AS false_positive_rate,
    CASE WHEN COUNT(rf.id) >= 10 AND
        COUNT(CASE WHEN rf.feedback_type = 'false_positive' THEN 1 END)::numeric / COUNT(rf.id) > 0.3
    THEN true ELSE false END AS needs_review
FROM playbook_rules pr
LEFT JOIN rule_feedback rf ON rf.playbook_rule_id = pr.id
GROUP BY pr.id, pr.clause_type, pr.playbook_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_rule_effectiveness_rule ON rule_effectiveness(rule_id);

ALTER TABLE rule_feedback ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='rule_feedback' AND policyname='rule_feedback_tenant_isolation') THEN
        CREATE POLICY rule_feedback_tenant_isolation ON rule_feedback
        USING (organization_id = current_setting('app.current_org_id', true)::uuid);
    END IF;
END $$;

COMMIT;


-- ============================================================================
-- MIGRATION 017: Phase 6 — Playbook System
-- ============================================================================

CREATE TABLE IF NOT EXISTS playbook_rule_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES playbook_rules(id) ON DELETE CASCADE,
    tier_level INTEGER NOT NULL CHECK (tier_level BETWEEN 1 AND 4),
    position_text TEXT NOT NULL,
    guidance_notes TEXT,
    risk_level_at_tier VARCHAR(10) DEFAULT 'yellow',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(rule_id, tier_level)
);
CREATE INDEX IF NOT EXISTS idx_rule_tiers_rule_id ON playbook_rule_tiers(rule_id);

CREATE TABLE IF NOT EXISTS playbook_conditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    condition_type VARCHAR(50) NOT NULL,
    operator VARCHAR(20) NOT NULL DEFAULT 'equals',
    condition_value JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conditions_playbook_id ON playbook_conditions(playbook_id);
CREATE INDEX IF NOT EXISTS idx_conditions_type ON playbook_conditions(condition_type);

CREATE TABLE IF NOT EXISTS playbook_rule_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condition_id UUID NOT NULL REFERENCES playbook_conditions(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES playbook_rules(id) ON DELETE CASCADE,
    override_risk_level VARCHAR(10),
    override_position_text TEXT,
    override_is_deal_breaker BOOLEAN,
    override_tier_level INTEGER CHECK (override_tier_level IS NULL OR override_tier_level BETWEEN 1 AND 4),
    suppress_rule BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(condition_id, rule_id)
);
CREATE INDEX IF NOT EXISTS idx_overrides_condition_id ON playbook_rule_overrides(condition_id);
CREATE INDEX IF NOT EXISTS idx_overrides_rule_id ON playbook_rule_overrides(rule_id);

CREATE TABLE IF NOT EXISTS playbook_rule_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    source_rule_id UUID NOT NULL REFERENCES playbook_rules(id) ON DELETE CASCADE,
    target_rule_id UUID NOT NULL REFERENCES playbook_rules(id) ON DELETE CASCADE,
    trigger_condition VARCHAR(50) NOT NULL,
    effect VARCHAR(50) NOT NULL,
    effect_params JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_rule_id, target_rule_id, trigger_condition)
);
CREATE INDEX IF NOT EXISTS idx_deps_playbook_id ON playbook_rule_dependencies(playbook_id);
CREATE INDEX IF NOT EXISTS idx_deps_source ON playbook_rule_dependencies(source_rule_id);
CREATE INDEX IF NOT EXISTS idx_deps_target ON playbook_rule_dependencies(target_rule_id);

CREATE TABLE IF NOT EXISTS playbook_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    change_summary TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(playbook_id, version_number)
);
CREATE INDEX IF NOT EXISTS idx_versions_playbook_id ON playbook_versions(playbook_id);

CREATE TABLE IF NOT EXISTS playbook_marketplace (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    published_at TIMESTAMPTZ DEFAULT NOW(),
    publisher_org_id UUID REFERENCES organizations(id),
    is_verified BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    avg_rating NUMERIC(3,2) DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    tags JSONB DEFAULT '[]'::jsonb,
    preview_rules JSONB,
    UNIQUE(playbook_id)
);

CREATE TABLE IF NOT EXISTS playbook_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace_id UUID NOT NULL REFERENCES playbook_marketplace(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(marketplace_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_marketplace_playbook ON playbook_marketplace(playbook_id);
CREATE INDEX IF NOT EXISTS idx_ratings_marketplace ON playbook_ratings(marketplace_id);

-- Data migration: primary_position → tier 1, fallback_position → tier 3
INSERT INTO playbook_rule_tiers (rule_id, tier_level, position_text, guidance_notes, risk_level_at_tier)
SELECT pr.id, 1, pr.primary_position, 'Ideal opening position (auto-migrated)', pr.risk_level::VARCHAR
FROM playbook_rules pr WHERE pr.primary_position IS NOT NULL
ON CONFLICT (rule_id, tier_level) DO NOTHING;

INSERT INTO playbook_rule_tiers (rule_id, tier_level, position_text, guidance_notes, risk_level_at_tier)
SELECT pr.id, 3, pr.fallback_position, 'Walk-away minimum (auto-migrated from fallback)', pr.risk_level::VARCHAR
FROM playbook_rules pr WHERE pr.fallback_position IS NOT NULL
ON CONFLICT (rule_id, tier_level) DO NOTHING;

-- Enable RLS on phase 6 tables
ALTER TABLE playbook_rule_tiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_conditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_rule_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_rule_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_marketplace ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_ratings ENABLE ROW LEVEL SECURITY;

-- Phase 6 RLS policies
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_rule_tiers' AND policyname='tenant_isolation_playbook_rule_tiers') THEN
        CREATE POLICY tenant_isolation_playbook_rule_tiers ON playbook_rule_tiers FOR ALL
        USING (rule_id IN (SELECT pr.id FROM playbook_rules pr JOIN playbooks p ON pr.playbook_id = p.id
            WHERE p.organization_id = current_setting('app.current_org_id', true)::uuid
               OR (p.organization_id IS NULL AND p.created_by = current_setting('app.current_user_id', true)::uuid)
               OR p.is_public = true));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_rule_tiers' AND policyname='superadmin_bypass_playbook_rule_tiers') THEN
        CREATE POLICY superadmin_bypass_playbook_rule_tiers ON playbook_rule_tiers FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_conditions' AND policyname='tenant_isolation_playbook_conditions') THEN
        CREATE POLICY tenant_isolation_playbook_conditions ON playbook_conditions FOR ALL
        USING (playbook_id IN (SELECT id FROM playbooks
            WHERE organization_id = current_setting('app.current_org_id', true)::uuid
               OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
               OR is_public = true));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_conditions' AND policyname='superadmin_bypass_playbook_conditions') THEN
        CREATE POLICY superadmin_bypass_playbook_conditions ON playbook_conditions FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_rule_overrides' AND policyname='tenant_isolation_playbook_rule_overrides') THEN
        CREATE POLICY tenant_isolation_playbook_rule_overrides ON playbook_rule_overrides FOR ALL
        USING (condition_id IN (SELECT pc.id FROM playbook_conditions pc JOIN playbooks p ON pc.playbook_id = p.id
            WHERE p.organization_id = current_setting('app.current_org_id', true)::uuid
               OR (p.organization_id IS NULL AND p.created_by = current_setting('app.current_user_id', true)::uuid)
               OR p.is_public = true));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_rule_overrides' AND policyname='superadmin_bypass_playbook_rule_overrides') THEN
        CREATE POLICY superadmin_bypass_playbook_rule_overrides ON playbook_rule_overrides FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_rule_dependencies' AND policyname='tenant_isolation_playbook_rule_dependencies') THEN
        CREATE POLICY tenant_isolation_playbook_rule_dependencies ON playbook_rule_dependencies FOR ALL
        USING (playbook_id IN (SELECT id FROM playbooks
            WHERE organization_id = current_setting('app.current_org_id', true)::uuid
               OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
               OR is_public = true));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_rule_dependencies' AND policyname='superadmin_bypass_playbook_rule_dependencies') THEN
        CREATE POLICY superadmin_bypass_playbook_rule_dependencies ON playbook_rule_dependencies FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_versions' AND policyname='tenant_isolation_playbook_versions') THEN
        CREATE POLICY tenant_isolation_playbook_versions ON playbook_versions FOR ALL
        USING (playbook_id IN (SELECT id FROM playbooks
            WHERE organization_id = current_setting('app.current_org_id', true)::uuid
               OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
               OR is_public = true));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_versions' AND policyname='superadmin_bypass_playbook_versions') THEN
        CREATE POLICY superadmin_bypass_playbook_versions ON playbook_versions FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_marketplace' AND policyname='tenant_isolation_playbook_marketplace') THEN
        CREATE POLICY tenant_isolation_playbook_marketplace ON playbook_marketplace FOR ALL
        USING (publisher_org_id = current_setting('app.current_org_id', true)::uuid OR publisher_org_id IS NULL OR true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_marketplace' AND policyname='superadmin_bypass_playbook_marketplace') THEN
        CREATE POLICY superadmin_bypass_playbook_marketplace ON playbook_marketplace FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_ratings' AND policyname='tenant_isolation_playbook_ratings') THEN
        CREATE POLICY tenant_isolation_playbook_ratings ON playbook_ratings FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_ratings' AND policyname='own_ratings_playbook_ratings') THEN
        CREATE POLICY own_ratings_playbook_ratings ON playbook_ratings FOR ALL
        USING (user_id = current_setting('app.current_user_id', true)::uuid);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='playbook_ratings' AND policyname='superadmin_bypass_playbook_ratings') THEN
        CREATE POLICY superadmin_bypass_playbook_ratings ON playbook_ratings FOR ALL
        USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END $$;


-- ============================================================================
-- MIGRATION 018: Composite indexes (CONCURRENTLY — must be outside transaction)
-- NOTE: If these fail because the index already exists, that's fine.
-- ============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_user_created
    ON documents(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_logs_user_created
    ON usage_logs(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_document_risks_doc_created
    ON document_risks(document_id, created_at DESC);


-- ============================================================================
-- VERIFICATION: Run these queries to confirm migration success
-- ============================================================================

-- Check new tables exist
-- SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;

-- Check indexes
-- SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'idx_%' ORDER BY indexname;

-- Check RLS policies
-- SELECT tablename, policyname FROM pg_policies WHERE schemaname='public' ORDER BY tablename;

-- Check enum values
-- SELECT unnest(enum_range(NULL::userrole));
-- SELECT unnest(enum_range(NULL::plantype));
-- SELECT unnest(enum_range(NULL::subscriptiontier));
