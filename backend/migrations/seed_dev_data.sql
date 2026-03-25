-- ContraRed — Development Seed Data
-- Inserts demo admin user and organization for local development.
--
-- AUDIT FIX C2: Production safety guard — this script will ABORT if DEBUG != 'true'

DO $$
BEGIN
    -- Block execution in production environments
    -- Set DEBUG=true in your local .env to allow seed data insertion
    IF NOT (current_setting('app.debug', true) = 'true'
            OR current_setting('server.debug', true) = 'true') THEN
        -- Check if this looks like a production database (has real users)
        IF (SELECT count(*) FROM users WHERE email NOT LIKE '%@contrared.com') > 0 THEN
            RAISE EXCEPTION '[AUDIT FIX C2] Seed data blocked: production database detected. '
                'This script is for LOCAL DEVELOPMENT ONLY. '
                'Set app.debug=true via SET app.debug = ''true'' to override.';
        END IF;
    END IF;
END $$;

-- Create demo organization
INSERT INTO organizations (id, name, plan_type, sso_enabled, mfa_required, created_at, updated_at)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'ContraRed Demo',
    'FREE',
    false,
    false,
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Development seed user (DO NOT use in production — change password immediately)
INSERT INTO users (id, email, name, password_hash, role, subscription_tier, organization_id, is_active, is_verified, failed_login_attempts, mfa_enabled, created_at, updated_at)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'admin@contrared.com',
    'Admin User',
    E'\\$2b\\$12\\$qwXrb8Kd0pcun7NqF.GWbu3ttsxkqbcHBV9t2vqGFMN4CST7D.1X.',
    'ADMIN',
    'FREE',
    'a0000000-0000-0000-0000-000000000001',
    true,
    true,
    0,
    false,
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Create subscription for the organization
INSERT INTO subscriptions (id, organization_id, plan_type, status, current_period_start, current_period_end, created_at, updated_at)
VALUES (
    'c0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    'FREE',
    'ACTIVE',
    NOW(),
    NOW() + INTERVAL '1 year',
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;
