-- Phase 6: Playbook System (4/10 → 10/10)
-- Negotiation tiers, conditional logic, cross-clause dependencies, versioning, marketplace

-- 1. Negotiation Tier System
-- Replaces binary primary/fallback with 4-tier ladder
CREATE TABLE IF NOT EXISTS playbook_rule_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES playbook_rules(id) ON DELETE CASCADE,
    tier_level INTEGER NOT NULL CHECK (tier_level BETWEEN 1 AND 4),
    -- 1=Ideal, 2=Acceptable, 3=Walk-Away, 4=Escalate
    position_text TEXT NOT NULL,
    guidance_notes TEXT,
    risk_level_at_tier VARCHAR(10) DEFAULT 'yellow',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(rule_id, tier_level)
);

CREATE INDEX IF NOT EXISTS idx_rule_tiers_rule_id ON playbook_rule_tiers(rule_id);

-- 2. Conditional Logic Engine
-- Conditions that determine when rule overrides apply
CREATE TABLE IF NOT EXISTS playbook_conditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    condition_type VARCHAR(50) NOT NULL,
    -- counterparty_type, deal_size, jurisdiction, contract_side, custom
    operator VARCHAR(20) NOT NULL DEFAULT 'equals',
    -- equals, not_equals, greater_than, less_than, in, not_in, contains
    condition_value JSONB NOT NULL,
    -- e.g. {"values": ["fortune_500", "government"]} or {"min": 50000, "max": 500000}
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conditions_playbook_id ON playbook_conditions(playbook_id);
CREATE INDEX IF NOT EXISTS idx_conditions_type ON playbook_conditions(condition_type);

-- Rule overrides triggered by conditions
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

-- 3. Cross-Clause Dependencies
CREATE TABLE IF NOT EXISTS playbook_rule_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    source_rule_id UUID NOT NULL REFERENCES playbook_rules(id) ON DELETE CASCADE,
    target_rule_id UUID NOT NULL REFERENCES playbook_rules(id) ON DELETE CASCADE,
    trigger_condition VARCHAR(50) NOT NULL,
    -- source_is_red, source_is_yellow, source_missing, source_uncapped, source_unlimited
    effect VARCHAR(50) NOT NULL,
    -- escalate_risk, add_flag, change_position, suppress
    effect_params JSONB,
    -- e.g. {"new_risk": "red", "message": "Uncapped liability makes indemnification critical"}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_rule_id, target_rule_id, trigger_condition)
);

CREATE INDEX IF NOT EXISTS idx_deps_playbook_id ON playbook_rule_dependencies(playbook_id);
CREATE INDEX IF NOT EXISTS idx_deps_source ON playbook_rule_dependencies(source_rule_id);
CREATE INDEX IF NOT EXISTS idx_deps_target ON playbook_rule_dependencies(target_rule_id);

-- 4. Playbook Version Control
CREATE TABLE IF NOT EXISTS playbook_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    -- Full snapshot: rules, tiers, conditions, overrides, dependencies
    change_summary TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(playbook_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_versions_playbook_id ON playbook_versions(playbook_id);

-- 5. Marketplace
CREATE TABLE IF NOT EXISTS playbook_marketplace (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    published_at TIMESTAMPTZ DEFAULT NOW(),
    publisher_org_id UUID REFERENCES organizations(id),
    is_verified BOOLEAN DEFAULT FALSE,
    -- "Verified by ContraRed" badge
    download_count INTEGER DEFAULT 0,
    avg_rating NUMERIC(3,2) DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    tags JSONB DEFAULT '[]'::jsonb,
    preview_rules JSONB,
    -- First 3-5 rules shown before fork
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

-- 6. Migrate existing data: primary_position → tier 1, fallback_position → tier 3
-- This runs as an idempotent INSERT...ON CONFLICT DO NOTHING
INSERT INTO playbook_rule_tiers (rule_id, tier_level, position_text, guidance_notes, risk_level_at_tier)
SELECT
    pr.id,
    1,
    pr.primary_position,
    'Ideal opening position (auto-migrated)',
    pr.risk_level::VARCHAR
FROM playbook_rules pr
WHERE pr.primary_position IS NOT NULL
ON CONFLICT (rule_id, tier_level) DO NOTHING;

INSERT INTO playbook_rule_tiers (rule_id, tier_level, position_text, guidance_notes, risk_level_at_tier)
SELECT
    pr.id,
    3,
    pr.fallback_position,
    'Walk-away minimum (auto-migrated from fallback)',
    pr.risk_level::VARCHAR
FROM playbook_rules pr
WHERE pr.fallback_position IS NOT NULL
ON CONFLICT (rule_id, tier_level) DO NOTHING;

-- RLS policies
ALTER TABLE playbook_rule_tiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_conditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_rule_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_rule_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_marketplace ENABLE ROW LEVEL SECURITY;
ALTER TABLE playbook_ratings ENABLE ROW LEVEL SECURITY;
