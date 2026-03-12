-- ============================================================================
-- Migration 011: Phase 3 — Billing Model Overhaul
--
-- Changes:
--   1. Add STARTER and BUSINESS values to plantype enum
--   2. Add STARTER and BUSINESS values to subscriptiontier enum
--   3. Add Stripe columns to subscriptions table
--   4. Create invoices table
--   5. Update default included_scans
-- ============================================================================

-- 1. Extend PlanType enum with new tiers
ALTER TYPE plantype ADD VALUE IF NOT EXISTS 'starter' AFTER 'free';
ALTER TYPE plantype ADD VALUE IF NOT EXISTS 'business' AFTER 'pro';

-- 2. Extend SubscriptionTier enum with new tiers
ALTER TYPE subscriptiontier ADD VALUE IF NOT EXISTS 'starter' AFTER 'free';
ALTER TYPE subscriptiontier ADD VALUE IF NOT EXISTS 'business' AFTER 'pro';

-- 3. Add Stripe gateway columns to subscriptions
ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255) UNIQUE,
    ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS gateway VARCHAR(20) DEFAULT 'razorpay';

CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_sub_id
    ON subscriptions(stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_subscriptions_gateway
    ON subscriptions(gateway);

-- 4. Create invoices table
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

-- 5. RLS policy for invoices (tenant isolation)
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_invoices ON invoices
    FOR ALL
    USING (
        organization_id::text = current_setting('app.current_org_id', true)
        OR current_setting('app.is_super_admin', true) = 'true'
        OR user_id::text = current_setting('app.current_user_id', true)
    );

-- Done
