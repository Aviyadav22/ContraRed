-- Migration 019: AI-primary detection columns for playbook rules
-- Part of P2 #29: Migrate 44 rules to AI-primary detection

ALTER TABLE playbook_rules
    ADD COLUMN IF NOT EXISTS detection_mode VARCHAR(30) DEFAULT 'keywords_only',
    ADD COLUMN IF NOT EXISTS risk_description TEXT,
    ADD COLUMN IF NOT EXISTS acceptable_position TEXT,
    ADD COLUMN IF NOT EXISTS unacceptable_signals JSONB,
    ADD COLUMN IF NOT EXISTS acceptable_signals JSONB,
    ADD COLUMN IF NOT EXISTS clause_context TEXT;

CREATE INDEX IF NOT EXISTS idx_playbook_rules_detection_mode
    ON playbook_rules(detection_mode);

ALTER TABLE playbook_rules
    ADD CONSTRAINT chk_detection_mode
    CHECK (detection_mode IN ('ai_only', 'ai_with_keywords', 'keywords_only'));
