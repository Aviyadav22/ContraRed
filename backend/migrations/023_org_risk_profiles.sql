-- Migration 023: Organization Risk Profiles
-- Institutional memory: track how orgs handle different clause types

CREATE TABLE IF NOT EXISTS organization_risk_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    clause_type VARCHAR(100) NOT NULL,
    total_encounters INTEGER NOT NULL DEFAULT 0,
    accept_count INTEGER NOT NULL DEFAULT 0,
    reject_count INTEGER NOT NULL DEFAULT 0,
    modify_count INTEGER NOT NULL DEFAULT 0,
    escalate_count INTEGER NOT NULL DEFAULT 0,
    avg_threshold JSONB,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_clause_type UNIQUE (organization_id, clause_type)
);

CREATE INDEX IF NOT EXISTS idx_org_risk_profiles_org_id ON organization_risk_profiles(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_risk_profiles_clause_type ON organization_risk_profiles(clause_type);

-- Enable RLS
ALTER TABLE organization_risk_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_risk_profiles_policy ON organization_risk_profiles
    FOR ALL USING (
        organization_id IN (
            SELECT organization_id FROM users
            WHERE id = current_setting('app.current_user_id')::uuid
        )
    );
