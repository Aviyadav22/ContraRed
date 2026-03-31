-- Migration 021: Compliance Layers
-- Adds compliance layer tables for toggleable regulatory overlays (DPDP, GDPR, CCPA, etc.)

-- 1. Compliance layers table
CREATE TABLE IF NOT EXISTS compliance_layers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    jurisdiction    VARCHAR(10),
    version         INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compliance_layers_code ON compliance_layers(code);
CREATE INDEX IF NOT EXISTS idx_compliance_layers_active ON compliance_layers(is_active);

-- 2. Compliance layer rules table
CREATE TABLE IF NOT EXISTS compliance_layer_rules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    layer_id            UUID NOT NULL REFERENCES compliance_layers(id) ON DELETE CASCADE,
    clause_type         VARCHAR(100) NOT NULL,
    primary_position    TEXT NOT NULL,
    fallback_position   TEXT,
    risk_level          VARCHAR(10) NOT NULL DEFAULT 'YELLOW',
    is_deal_breaker     BOOLEAN DEFAULT FALSE,
    detection_patterns  JSONB,
    detection_mode      VARCHAR(50) DEFAULT 'ai_with_keywords',
    risk_description    TEXT,
    acceptable_position TEXT,
    unacceptable_signals JSONB,
    acceptable_signals  JSONB,
    sort_order          INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_compliance_layer_rules_layer_id ON compliance_layer_rules(layer_id);
CREATE INDEX IF NOT EXISTS idx_compliance_layer_rules_clause_type ON compliance_layer_rules(clause_type);

-- 3. Add compliance_layers column to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS compliance_layers JSONB DEFAULT '[]';
