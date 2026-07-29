-- Migration 030: Preserve batch compliance assessment completeness.
-- Scores include unassessed counts so a partial AI response cannot be
-- represented as a complete compliance result.

ALTER TABLE batch_jobs
    ADD COLUMN IF NOT EXISTS compliance_scores JSONB;

ALTER TABLE batch_job_files
    ADD COLUMN IF NOT EXISTS compliance_scores JSONB;
