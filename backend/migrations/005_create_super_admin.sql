-- Migration 005: Create Super Admin user
-- Run this in Supabase SQL Editor
-- Password: admin@123 (change via /api/v1/auth/change-password after first login)
-- NOTE: SQLAlchemy uses enum NAMES (uppercase) as DB values

INSERT INTO users (id, email, name, password_hash, role, subscription_tier, is_active, is_verified, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'aviyadav.official@gmail.com',
    'Avi Yadav',
    '$2b$12$VmlJ6IfllgkK93y/3o/GVuMFozfkpTbz6I3tNpD4soz2DaBz3026y',
    'SUPER_ADMIN',
    'ENTERPRISE',
    true,
    true,
    NOW(),
    NOW()
)
ON CONFLICT (email) DO UPDATE SET
    role = 'SUPER_ADMIN',
    subscription_tier = 'ENTERPRISE',
    password_hash = '$2b$12$VmlJ6IfllgkK93y/3o/GVuMFozfkpTbz6I3tNpD4soz2DaBz3026y';
