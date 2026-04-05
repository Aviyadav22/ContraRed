-- Migration 026: Compliance Result Persistence
-- Stores scanner and assessor results for historical tracking, trend analysis, and audit readiness

-- ============================================================
-- 1. Compliance Scan Results (per-contract scan history)
-- ============================================================
CREATE TABLE IF NOT EXISTS compliance_scan_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id),
    user_id             UUID REFERENCES users(id),
    contract_name       VARCHAR(500),
    contract_type       VARCHAR(100),
    jurisdiction        VARCHAR(50),
    compliance_score    INTEGER NOT NULL CHECK (compliance_score BETWEEN 0 AND 100),
    total_findings      INTEGER DEFAULT 0,
    red_count           INTEGER DEFAULT 0,
    yellow_count        INTEGER DEFAULT 0,
    green_count         INTEGER DEFAULT 0,
    deal_breaker_count  INTEGER DEFAULT 0,
    findings            JSONB DEFAULT '[]',        -- Full findings array for audit
    risk_summary        JSONB DEFAULT '{}',        -- Aggregated risk data
    scanned_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_results_org ON compliance_scan_results(organization_id, scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_scan_results_user ON compliance_scan_results(user_id, scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_scan_results_score ON compliance_scan_results(compliance_score);

-- ============================================================
-- 2. Compliance Assessments (gap assessment history)
-- ============================================================
CREATE TABLE IF NOT EXISTS compliance_assessments (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id             UUID REFERENCES organizations(id),
    user_id                     UUID REFERENCES users(id),
    organization_name           VARCHAR(500),
    industry                    VARCHAR(100),
    overall_score               INTEGER NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    overall_status              VARCHAR(20) NOT NULL CHECK (overall_status IN ('compliant', 'partial', 'non_compliant', 'not_assessed')),
    section_scores              JSONB DEFAULT '[]',        -- Per-section scores
    critical_gaps               JSONB DEFAULT '[]',        -- List of critical gaps
    action_items                JSONB DEFAULT '[]',        -- Prioritized remediation steps
    estimated_remediation_effort VARCHAR(20),               -- high/medium/low
    answers                     JSONB DEFAULT '[]',        -- Raw answers for audit trail
    assessed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assessments_org ON compliance_assessments(organization_id, assessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_assessments_score ON compliance_assessments(overall_score);

-- ============================================================
-- 3. Compliance Reports (generated report history)
-- ============================================================
CREATE TABLE IF NOT EXISTS compliance_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID REFERENCES organizations(id),
    user_id             UUID REFERENCES users(id),
    report_type         VARCHAR(50) NOT NULL DEFAULT 'full',  -- full, scan_only, assessment_only
    title               VARCHAR(500),
    content             JSONB NOT NULL,            -- Structured report content
    summary             TEXT,                       -- Executive summary text
    compliance_score    INTEGER,
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_org ON compliance_reports(organization_id, generated_at DESC);

-- ============================================================
-- 4. RLS Policies
-- ============================================================
ALTER TABLE compliance_scan_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY scan_results_policy ON compliance_scan_results
    FOR ALL USING (
        user_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
        OR (organization_id IS NOT NULL AND organization_id::text = current_setting('app.current_org_id', true))
    );

CREATE POLICY assessments_policy ON compliance_assessments
    FOR ALL USING (
        user_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
        OR (organization_id IS NOT NULL AND organization_id::text = current_setting('app.current_org_id', true))
    );

CREATE POLICY reports_policy ON compliance_reports
    FOR ALL USING (
        user_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
        OR (organization_id IS NOT NULL AND organization_id::text = current_setting('app.current_org_id', true))
    );
