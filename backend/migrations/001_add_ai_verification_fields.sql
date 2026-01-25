-- ContraRed Database Migration: Add Hybrid Sentinel Fields to PlaybookRule
-- Version: 001_add_ai_verification_fields
-- Date: 2026-01-22
-- Description: Adds requires_ai_verification and verification_prompt columns 
--              to playbook_rules table for Hybrid Sentinel support

-- ============================================================================
-- UPGRADE
-- ============================================================================

-- Add requires_ai_verification column (default True for existing rules)
ALTER TABLE playbook_rules 
ADD COLUMN IF NOT EXISTS requires_ai_verification BOOLEAN NOT NULL DEFAULT TRUE;

-- Add verification_prompt column (nullable text for custom Scout prompts)
ALTER TABLE playbook_rules 
ADD COLUMN IF NOT EXISTS verification_prompt TEXT NULL;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify columns were added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'playbook_rules' 
  AND column_name IN ('requires_ai_verification', 'verification_prompt');

-- ============================================================================
-- DOWNGRADE (if needed - run separately)
-- ============================================================================

-- To rollback, run:
-- ALTER TABLE playbook_rules DROP COLUMN IF EXISTS requires_ai_verification;
-- ALTER TABLE playbook_rules DROP COLUMN IF EXISTS verification_prompt;
