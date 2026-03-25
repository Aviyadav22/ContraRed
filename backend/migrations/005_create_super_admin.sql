-- Migration 005: Create Super Admin user
-- Run this in Supabase SQL Editor
--
-- AUDIT FIX C1: Password hash is NO LONGER hardcoded.
-- After running this migration, set the super admin password via:
--   UPDATE users SET password_hash = crypt('YOUR_SECURE_PASSWORD', gen_salt('bf', 12))
--   WHERE email = 'aviyadav.official@gmail.com';
--
-- Or use the backend's /auth/register endpoint + manually promote to SUPER_ADMIN.
-- NOTE: SQLAlchemy uses enum NAMES (uppercase) as DB values

-- Generate a random unusable password hash (forces password reset)
-- The bcrypt hash below is for a 64-char random string that nobody knows.
-- The admin MUST reset their password on first login.
DO $$
DECLARE
    random_hash TEXT;
BEGIN
    -- Generate a bcrypt hash of a random value (unguessable placeholder)
    random_hash := crypt(gen_random_uuid()::text || gen_random_uuid()::text, gen_salt('bf', 12));

    INSERT INTO users (id, email, name, password_hash, role, subscription_tier, is_active, is_verified, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'aviyadav.official@gmail.com',
        'Avi Yadav',
        random_hash,
        'SUPER_ADMIN',
        'ENTERPRISE',
        true,
        true,
        NOW(),
        NOW()
    )
    -- AUDIT FIX C1: ON CONFLICT no longer overwrites password_hash
    -- This preserves any password changes made after initial creation
    ON CONFLICT (email) DO UPDATE SET
        role = 'SUPER_ADMIN',
        subscription_tier = 'ENTERPRISE';
END $$;
