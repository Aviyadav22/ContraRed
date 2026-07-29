-- Migration 031: Version the legal source behind compliance-layer analysis.
-- Legal rules must expose their source, commencement date, and verification
-- date so a static rule pack is never silently represented as current law.

ALTER TABLE compliance_layers
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS gazette_date DATE,
    ADD COLUMN IF NOT EXISTS effective_date DATE,
    ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;
