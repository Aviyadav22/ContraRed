-- ============================================================================
-- Migration 014: Rule feedback table + contract_templates organization_id
--
-- NOTE: The rule_feedback table may already exist from migration 016 (which
-- was created out of order). All statements use IF NOT EXISTS / IF NOT EXISTS
-- to be fully idempotent.
--
-- This migration:
--   1. Creates rule_feedback table (if not already present from 016)
--   2. Adds organization_id column to contract_templates
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. RULE FEEDBACK TABLE
-- ============================================================================
-- Allows users to flag rules as helpful, not helpful, or false positives.
-- This feeds into the rule effectiveness analytics.

CREATE TABLE IF NOT EXISTS rule_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES playbook_rules(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id),
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('helpful', 'not_helpful', 'false_positive')),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rule_feedback_rule_id ON rule_feedback(rule_id);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_user_id ON rule_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_org_id ON rule_feedback(organization_id);

-- ============================================================================
-- 2. ADD organization_id TO contract_templates
-- ============================================================================
-- Enables RLS tenant isolation on templates. Existing templates with NULL
-- organization_id are treated as global/public templates.

ALTER TABLE contract_templates ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);
CREATE INDEX IF NOT EXISTS idx_contract_templates_org_id ON contract_templates(organization_id);

COMMIT;
