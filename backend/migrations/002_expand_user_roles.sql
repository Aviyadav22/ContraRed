-- Migration 002: Add ANALYST role to UserRole enum
-- Safe: ADD VALUE IF NOT EXISTS is idempotent
-- Run in Supabase SQL editor

ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'analyst';
