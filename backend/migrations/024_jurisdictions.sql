-- Migration 024: Jurisdictions and jurisdiction rule overrides
-- Supports the Global Jurisdiction Engine feature

-- Jurisdictions table
CREATE TABLE IF NOT EXISTS jurisdictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    legal_system VARCHAR(20) NOT NULL DEFAULT 'common_law',
    parent_code VARCHAR(20),
    key_statutes JSONB,
    special_considerations JSONB,
    indemnification_standard TEXT,
    non_compete_enforceability TEXT,
    arbitration_framework TEXT,
    data_protection_law TEXT,
    prompt_context TEXT,
    aliases JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jurisdictions_code ON jurisdictions(code);
CREATE INDEX IF NOT EXISTS idx_jurisdictions_is_active ON jurisdictions(is_active);
CREATE INDEX IF NOT EXISTS idx_jurisdictions_parent_code ON jurisdictions(parent_code);

-- Jurisdiction rule overrides table
CREATE TABLE IF NOT EXISTS jurisdiction_rule_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction_id UUID NOT NULL REFERENCES jurisdictions(id) ON DELETE CASCADE,
    clause_type VARCHAR(100) NOT NULL,
    risk_level VARCHAR(10),
    risk_weight FLOAT,
    suppress BOOLEAN NOT NULL DEFAULT FALSE,
    primary_position TEXT,
    note TEXT,
    statute_reference VARCHAR(500),
    CONSTRAINT uq_jurisdiction_clause_type UNIQUE (jurisdiction_id, clause_type)
);

CREATE INDEX IF NOT EXISTS idx_jro_jurisdiction_id ON jurisdiction_rule_overrides(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_jro_clause_type ON jurisdiction_rule_overrides(clause_type);

-- RLS policies
ALTER TABLE jurisdictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE jurisdiction_rule_overrides ENABLE ROW LEVEL SECURITY;

-- Jurisdictions are readable by all authenticated users
CREATE POLICY jurisdictions_select_policy ON jurisdictions
    FOR SELECT USING (true);

CREATE POLICY jro_select_policy ON jurisdiction_rule_overrides
    FOR SELECT USING (true);

-- Only admins can insert/update/delete
CREATE POLICY jurisdictions_admin_policy ON jurisdictions
    FOR ALL USING (
        current_setting('app.user_role', true) = 'admin'
    );

CREATE POLICY jro_admin_policy ON jurisdiction_rule_overrides
    FOR ALL USING (
        current_setting('app.user_role', true) = 'admin'
    );
