-- Migration 014: Webhook idempotency tracking
-- Prevents duplicate processing of payment gateway webhook events

CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gateway VARCHAR(20) NOT NULL,           -- razorpay, stripe
    gateway_event_id VARCHAR(255) NOT NULL,  -- event ID from the gateway
    event_type VARCHAR(100) NOT NULL,        -- e.g. subscription.charged, invoice.paid
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_webhook_gateway_event UNIQUE (gateway, gateway_event_id)
);

CREATE INDEX IF NOT EXISTS ix_webhook_events_processed_at ON webhook_events (processed_at);

-- RLS policy: webhook_events is system-level, only accessible via service role
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY webhook_events_service_policy ON webhook_events
    FOR ALL
    USING (current_setting('app.is_super_admin', true) = 'true')
    WITH CHECK (true);
