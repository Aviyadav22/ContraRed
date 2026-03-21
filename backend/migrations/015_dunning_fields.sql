-- Migration 015: Dunning management fields on subscriptions
-- Tracks failed payment retries and escalation schedule

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS dunning_attempts INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_dunning_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS dunning_next_retry_at TIMESTAMPTZ;

-- Index for querying subscriptions needing dunning action
CREATE INDEX IF NOT EXISTS ix_subscriptions_dunning
    ON subscriptions (dunning_next_retry_at)
    WHERE status = 'past_due' AND dunning_next_retry_at IS NOT NULL;
