-- Migration 004: Add account lockout fields to users table
-- Safe: ADD COLUMN IF NOT EXISTS is idempotent

ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP NULL;
