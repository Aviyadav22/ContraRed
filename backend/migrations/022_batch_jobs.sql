-- Migration 022: Batch Jobs
-- Persist batch analysis state to database (replaces in-memory dict)

-- Batch job (one per batch-analyze request)
CREATE TABLE IF NOT EXISTS batch_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'processing',
    total_files INTEGER NOT NULL DEFAULT 0,
    completed_files INTEGER NOT NULL DEFAULT 0,
    failed_files INTEGER NOT NULL DEFAULT 0,
    playbook_id UUID,
    compliance_layers JSONB DEFAULT '[]',
    risk_summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_batch_jobs_user_id ON batch_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_org_id ON batch_jobs(organization_id);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_created_at ON batch_jobs(created_at DESC);

-- Batch job file (one per file in a batch)
CREATE TABLE IF NOT EXISTS batch_job_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES batch_jobs(id) ON DELETE CASCADE,
    document_id UUID,
    filename VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    error_message TEXT,
    risk_summary JSONB,
    processing_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_batch_job_files_batch_id ON batch_job_files(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_job_files_status ON batch_job_files(status);

-- Enable RLS
ALTER TABLE batch_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE batch_job_files ENABLE ROW LEVEL SECURITY;

-- RLS policies: users can only see their own batch jobs
CREATE POLICY batch_jobs_user_policy ON batch_jobs
    FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY batch_job_files_user_policy ON batch_job_files
    FOR ALL USING (
        batch_id IN (
            SELECT id FROM batch_jobs
            WHERE user_id = current_setting('app.current_user_id')::uuid
        )
    );
