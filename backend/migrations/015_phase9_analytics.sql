-- Migration 015: Phase 9 — Analytics Value (3/10 → 10/10)
--
-- Purpose: Transform ContraRed analytics from basic counters into a full
-- value-demonstration engine. Adds document metadata enrichment, review
-- session tracking, configurable time/ROI benchmarks, historical benchmark
-- profiles, and generated report storage.
--
-- Depends on: documents, users, organizations tables (existing)

-- ============================================================================
-- 1. ENRICH documents TABLE WITH ANALYTICS COLUMNS
-- ============================================================================
-- These columns capture per-document metadata that powers aggregate analytics,
-- benchmark comparisons, and ROI calculations.

ALTER TABLE documents ADD COLUMN IF NOT EXISTS word_count INTEGER DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_duration_ms INTEGER DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS contract_type VARCHAR(100) DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5,2) DEFAULT NULL;  -- 1-10 scale
ALTER TABLE documents ADD COLUMN IF NOT EXISTS counterparty VARCHAR(255) DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS contract_value NUMERIC(15,2) DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS expiry_date DATE DEFAULT NULL;

-- ============================================================================
-- 2. REVIEW SESSIONS — per-document review activity tracking
-- ============================================================================
-- Captures each time a user sits down to review a document's risks. Tracks
-- duration, how many risks were reviewed/accepted/rejected, and session
-- metadata (playbook, jurisdiction, etc.). This feeds time-savings analytics.

CREATE TABLE IF NOT EXISTS review_sessions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id   UUID REFERENCES organizations(id) ON DELETE SET NULL,
    document_id       UUID REFERENCES documents(id) ON DELETE SET NULL,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at          TIMESTAMPTZ,
    duration_seconds  INTEGER,              -- computed when session is closed
    risks_reviewed    INTEGER DEFAULT 0,
    risks_accepted    INTEGER DEFAULT 0,
    risks_rejected    INTEGER DEFAULT 0,
    notes             TEXT,
    session_metadata  JSONB                 -- playbook used, jurisdiction, etc.
);

COMMENT ON TABLE review_sessions IS 'Tracks individual review sessions for time-savings and productivity analytics';
COMMENT ON COLUMN review_sessions.duration_seconds IS 'Computed on session close: extract(epoch from ended_at - started_at)';
COMMENT ON COLUMN review_sessions.session_metadata IS 'Flexible JSONB for playbook_id, jurisdiction, review_mode, etc.';

-- ============================================================================
-- 3. TIME BENCHMARKS — org-level manual review baseline configuration
-- ============================================================================
-- Each org can configure how fast a human reviewer works manually. These
-- numbers are used to compute "time saved" by ContraRed. One row per org.

CREATE TABLE IF NOT EXISTS time_benchmarks (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    pages_per_hour    NUMERIC(5,1) DEFAULT 5.0,       -- manual review speed
    minutes_per_risk  NUMERIC(5,1) DEFAULT 15.0,      -- time to assess one risk manually
    hourly_rate       NUMERIC(10,2) DEFAULT 5000.00,   -- INR default
    currency          VARCHAR(3) DEFAULT 'INR',
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE time_benchmarks IS 'Per-org baseline for manual review speed; used to calculate time and cost savings';
COMMENT ON COLUMN time_benchmarks.pages_per_hour IS 'How many pages a human reviewer covers per hour without AI assistance';
COMMENT ON COLUMN time_benchmarks.hourly_rate IS 'Blended hourly cost of a reviewer in the configured currency';

-- ============================================================================
-- 4. ROI CONFIG — per-org ROI methodology settings
-- ============================================================================
-- Controls how ROI is calculated and displayed. Orgs can toggle whether risk
-- value and/or time savings are included, and set monetary values per risk
-- severity level.

CREATE TABLE IF NOT EXISTS roi_config (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    risk_value_per_red       NUMERIC(12,2) DEFAULT 500000.00,   -- INR ₹5L default
    risk_value_per_yellow    NUMERIC(12,2) DEFAULT 100000.00,   -- INR ₹1L default
    include_risk_value       BOOLEAN DEFAULT true,
    include_time_savings     BOOLEAN DEFAULT true,
    custom_methodology_note  TEXT,                                -- org-specific ROI explanation
    created_at               TIMESTAMPTZ DEFAULT now(),
    updated_at               TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE roi_config IS 'Per-org ROI calculation methodology — maps risk severities to monetary values';
COMMENT ON COLUMN roi_config.risk_value_per_red IS 'Estimated value protected per high-severity (red) risk caught';
COMMENT ON COLUMN roi_config.custom_methodology_note IS 'Free-text note explaining the org methodology, shown in reports';

-- ============================================================================
-- 5. BENCHMARK PROFILES — historical benchmark data by contract type
-- ============================================================================
-- Stores aggregated benchmark snapshots per org and contract type over time
-- periods. Used for trend analysis, peer comparison, and "you vs. average"
-- dashboards.

CREATE TABLE IF NOT EXISTS benchmark_profiles (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    contract_type     VARCHAR(100) NOT NULL,
    avg_risk_score    NUMERIC(5,2),
    avg_risks_per_doc NUMERIC(8,2),
    avg_red_risks     NUMERIC(8,2),
    avg_processing_ms INTEGER,
    document_count    INTEGER DEFAULT 0,
    period_start      DATE NOT NULL,
    period_end        DATE NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT uq_benchmark_org_type_period
        UNIQUE (organization_id, contract_type, period_start, period_end)
);

COMMENT ON TABLE benchmark_profiles IS 'Aggregated benchmark snapshots per org/contract-type/period for trend analysis';
COMMENT ON COLUMN benchmark_profiles.document_count IS 'Number of documents included in this benchmark period';

-- ============================================================================
-- 6. GENERATED REPORTS — stored report outputs
-- ============================================================================
-- Persists generated analytics reports so users can retrieve them later without
-- re-computing. Supports multiple formats (json, csv, pdf) and report types.

CREATE TABLE IF NOT EXISTS generated_reports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    report_type       VARCHAR(50) NOT NULL,     -- executive_summary, gc_operations, team_review, risk_audit
    title             VARCHAR(255) NOT NULL,
    parameters        JSONB,                    -- period, filters, etc.
    report_data       JSONB NOT NULL,           -- the actual report content
    format            VARCHAR(20) DEFAULT 'json',  -- json, csv, pdf
    created_at        TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE generated_reports IS 'Persisted analytics reports for retrieval without re-computation';
COMMENT ON COLUMN generated_reports.report_type IS 'One of: executive_summary, gc_operations, team_review, risk_audit';
COMMENT ON COLUMN generated_reports.parameters IS 'Input parameters used to generate the report (date range, filters, etc.)';
COMMENT ON COLUMN generated_reports.report_data IS 'Full report payload — structure varies by report_type';

-- ============================================================================
-- 7. INDEXES — query performance for analytics workloads
-- ============================================================================

-- Document metadata indexes for filtering and aggregation
CREATE INDEX IF NOT EXISTS ix_documents_contract_type ON documents(contract_type);
CREATE INDEX IF NOT EXISTS ix_documents_risk_score ON documents(risk_score);
CREATE INDEX IF NOT EXISTS ix_documents_counterparty ON documents(counterparty);
CREATE INDEX IF NOT EXISTS ix_documents_expiry_date ON documents(expiry_date);

-- Review session lookups by user, org, and document
CREATE INDEX IF NOT EXISTS ix_review_sessions_user ON review_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_review_sessions_org ON review_sessions(organization_id);
CREATE INDEX IF NOT EXISTS ix_review_sessions_doc ON review_sessions(document_id);

-- Report retrieval by org
CREATE INDEX IF NOT EXISTS ix_generated_reports_org ON generated_reports(organization_id);

-- Benchmark lookups by org + contract type (covers most dashboard queries)
CREATE INDEX IF NOT EXISTS ix_benchmark_profiles_org_type ON benchmark_profiles(organization_id, contract_type);

-- End of migration 015
