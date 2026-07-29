-- Migration 029: make neutral the safe default for newly-created playbooks.
--
-- Existing values are intentionally preserved because an existing buyer-side
-- playbook may be deliberate. Owners can now review and change the represented
-- side through the API and dashboard.
--
-- IDEMPOTENT: safe to run multiple times.

BEGIN;

ALTER TABLE playbooks
    ALTER COLUMN party_side SET DEFAULT 'neutral';

UPDATE playbooks
SET party_side = 'neutral'
WHERE party_side IS NULL;

COMMIT;
