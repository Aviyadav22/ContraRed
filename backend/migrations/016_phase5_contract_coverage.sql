-- Migration 016: Phase 5 - Contract Coverage & Rule Feedback
-- Adds rule feedback system for continuous learning through lawyer input
-- Idempotent: safe to run multiple times

BEGIN;

-- ============================================================================
-- 1. rule_feedback table — lawyers mark false positives/negatives per rule
-- ============================================================================

CREATE TABLE IF NOT EXISTS rule_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    playbook_rule_id UUID REFERENCES playbook_rules(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,

    -- Feedback type
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('false_positive', 'false_negative', 'correct', 'needs_improvement')),

    -- Details
    clause_text TEXT,  -- the clause that was flagged (or should have been)
    user_comment TEXT,  -- lawyer's explanation
    suggested_risk_level VARCHAR(10),  -- what risk level should it be

    -- Tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes
    CONSTRAINT fk_rule_feedback_org FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_rule_feedback_rule ON rule_feedback(playbook_rule_id);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_org ON rule_feedback(organization_id);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_type ON rule_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_rule_feedback_created ON rule_feedback(created_at);

-- ============================================================================
-- 2. Add columns to playbook_rules for coverage tracking
-- ============================================================================

ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS jurisdiction_overrides JSONB DEFAULT '{}';
ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 50;
ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS subcategory VARCHAR(50);
ALTER TABLE playbook_rules ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]';

-- ============================================================================
-- 3. rule_effectiveness materialized view for analytics
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS rule_effectiveness AS
SELECT
    pr.id AS rule_id,
    pr.clause_type,
    pr.playbook_id,
    COUNT(rf.id) AS total_feedback,
    COUNT(CASE WHEN rf.feedback_type = 'false_positive' THEN 1 END) AS false_positives,
    COUNT(CASE WHEN rf.feedback_type = 'false_negative' THEN 1 END) AS false_negatives,
    COUNT(CASE WHEN rf.feedback_type = 'correct' THEN 1 END) AS correct_count,
    CASE
        WHEN COUNT(rf.id) > 0 THEN
            ROUND(COUNT(CASE WHEN rf.feedback_type = 'false_positive' THEN 1 END)::numeric / COUNT(rf.id) * 100, 1)
        ELSE 0
    END AS false_positive_rate,
    CASE
        WHEN COUNT(rf.id) >= 10 AND
             COUNT(CASE WHEN rf.feedback_type = 'false_positive' THEN 1 END)::numeric / COUNT(rf.id) > 0.3
        THEN true
        ELSE false
    END AS needs_review
FROM playbook_rules pr
LEFT JOIN rule_feedback rf ON rf.playbook_rule_id = pr.id
GROUP BY pr.id, pr.clause_type, pr.playbook_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_rule_effectiveness_rule ON rule_effectiveness(rule_id);

-- ============================================================================
-- 4. Row Level Security for tenant isolation
-- ============================================================================

ALTER TABLE rule_feedback ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'rule_feedback' AND policyname = 'rule_feedback_tenant_isolation'
    ) THEN
        CREATE POLICY rule_feedback_tenant_isolation ON rule_feedback
            USING (organization_id = current_setting('app.current_org_id', true)::uuid);
    END IF;
END
$$;

COMMIT;
