-- Migration 028: Consolidation Phase A (cleanup)
-- See plans/ok-first-most-importnt-toasty-backus.md
--
-- Drops the dead `Playbook.rules` JSONB column.
-- Active path is the `playbook_rules` relationship table (rules_list).
-- The JSONB column was only read by playbook_versioning._build_snapshot,
-- which has been updated to skip the field.
--
-- IDEMPOTENT — safe to run multiple times.

BEGIN;

-- 1. Drop the dead JSONB column on playbooks
ALTER TABLE playbooks
    DROP COLUMN IF EXISTS rules;

COMMIT;
