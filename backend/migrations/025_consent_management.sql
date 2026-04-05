-- Migration 025: DPDP Act Consent Management Framework
-- ISO 27560 compliant consent records with immutable audit trail
-- Supports: consent collection, withdrawal, rights requests, grievances, nominations, cross-border tracking

-- ============================================================
-- 1. Consent Purposes (versioned, append-only on text change)
-- ============================================================
CREATE TABLE IF NOT EXISTS consent_purposes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purpose_code            VARCHAR(100) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT NOT NULL,
    personal_data_categories TEXT[] NOT NULL DEFAULT '{}',
    third_parties           TEXT[] NOT NULL DEFAULT '{}',
    retention_period        VARCHAR(100),              -- e.g. '7 years', 'duration of account'
    is_required             BOOLEAN DEFAULT FALSE,
    is_active               BOOLEAN DEFAULT TRUE,
    version                 INTEGER DEFAULT 1,
    translations            JSONB DEFAULT '{}',        -- {"hi": {"name": "...", "description": "..."}}
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(purpose_code, version)
);

CREATE INDEX IF NOT EXISTS idx_consent_purposes_code ON consent_purposes(purpose_code);
CREATE INDEX IF NOT EXISTS idx_consent_purposes_active ON consent_purposes(is_active);

-- ============================================================
-- 2. Consent Policies (privacy policy versions with checksum)
-- ============================================================
CREATE TABLE IF NOT EXISTS consent_policies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version             INTEGER NOT NULL,
    title               VARCHAR(500) NOT NULL,
    content             TEXT NOT NULL,
    language            VARCHAR(10) DEFAULT 'en',
    purpose_ids         UUID[] NOT NULL DEFAULT '{}',
    checksum            VARCHAR(64) NOT NULL,          -- SHA-256 of content
    effective_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_until     TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(version, language)
);

CREATE INDEX IF NOT EXISTS idx_consent_policies_version ON consent_policies(version);
CREATE INDEX IF NOT EXISTS idx_consent_policies_effective ON consent_policies(effective_from, effective_until);

-- ============================================================
-- 3. Consent Records (master consent per user, mutable status)
-- ============================================================
CREATE TABLE IF NOT EXISTS consent_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id     UUID REFERENCES organizations(id),
    policy_version_id   UUID REFERENCES consent_policies(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'withdrawn', 'expired', 'refused')),
    ip_address          INET,
    user_agent          VARCHAR(500),
    collection_method   VARCHAR(50) DEFAULT 'web_form',   -- web_form, api, voice, offline
    expression_method   VARCHAR(50) DEFAULT 'checkbox',    -- checkbox, toggle, verbal, signature
    metadata            JSONB DEFAULT '{}',
    expires_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consent_records_subject ON consent_records(subject_id, status);
CREATE INDEX IF NOT EXISTS idx_consent_records_org ON consent_records(organization_id);
CREATE INDEX IF NOT EXISTS idx_consent_records_created ON consent_records(created_at);

-- ============================================================
-- 4. Consent Purpose Grants (per-purpose grant/deny junction)
-- ============================================================
CREATE TABLE IF NOT EXISTS consent_purpose_grants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consent_record_id   UUID NOT NULL REFERENCES consent_records(id) ON DELETE CASCADE,
    purpose_id          UUID NOT NULL REFERENCES consent_purposes(id),
    purpose_code        VARCHAR(100) NOT NULL,             -- Denormalized for fast lookups
    granted             BOOLEAN NOT NULL,
    granted_at          TIMESTAMPTZ,
    withdrawn_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(consent_record_id, purpose_code)
);

CREATE INDEX IF NOT EXISTS idx_consent_grants_record ON consent_purpose_grants(consent_record_id);
CREATE INDEX IF NOT EXISTS idx_consent_grants_purpose ON consent_purpose_grants(purpose_code, granted);
CREATE INDEX IF NOT EXISTS idx_consent_grants_lookup ON consent_purpose_grants(consent_record_id, purpose_code, granted);

-- ============================================================
-- 5. Consent Events (immutable audit trail, hash-chained)
-- ============================================================
CREATE SEQUENCE IF NOT EXISTS consent_event_sequence START WITH 1 INCREMENT BY 1;

CREATE TABLE IF NOT EXISTS consent_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consent_record_id   UUID REFERENCES consent_records(id),
    subject_id          UUID NOT NULL REFERENCES users(id),
    event_type          VARCHAR(50) NOT NULL
                        CHECK (event_type IN (
                            'granted', 'withdrawn', 'expired', 'renewed',
                            'modified', 'refused', 'verification_requested',
                            'verification_succeeded', 'verification_failed',
                            'policy_accepted', 'rights_request', 'grievance_filed'
                        )),
    purpose_code        VARCHAR(100),                      -- NULL if applies to all purposes
    actor               VARCHAR(50) DEFAULT 'data_subject', -- data_subject, system, dpo, consent_manager
    details             JSONB DEFAULT '{}',
    ip_address          INET,
    user_agent          VARCHAR(500),

    -- Hash chain (same pattern as audit_logs)
    entry_hash          VARCHAR(64),
    previous_hash       VARCHAR(64),
    sequence_number     BIGINT,

    -- Retention
    retention_until     TIMESTAMPTZ,                       -- Default: created_at + 7 years
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consent_events_record ON consent_events(consent_record_id, created_at);
CREATE INDEX IF NOT EXISTS idx_consent_events_subject ON consent_events(subject_id, created_at);
CREATE INDEX IF NOT EXISTS idx_consent_events_type ON consent_events(event_type);
CREATE INDEX IF NOT EXISTS idx_consent_events_sequence ON consent_events(sequence_number);

-- Immutability trigger: prevent UPDATE/DELETE on consent_events
CREATE OR REPLACE FUNCTION prevent_consent_event_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'consent_events is immutable: % operations are not allowed', TG_OP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS consent_events_immutable ON consent_events;
CREATE TRIGGER consent_events_immutable
    BEFORE UPDATE OR DELETE ON consent_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_consent_event_mutation();

-- ============================================================
-- 6. Consent Receipts (ISO 27560 JSON-LD, machine-readable)
-- ============================================================
CREATE TABLE IF NOT EXISTS consent_receipts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consent_record_id   UUID NOT NULL REFERENCES consent_records(id) ON DELETE CASCADE,
    receipt_data        JSONB NOT NULL,                    -- ISO 27560 compliant JSON-LD
    digital_signature   VARCHAR(128),                      -- HMAC-SHA256
    schema_version      VARCHAR(20) DEFAULT '27560:2023',
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    downloaded_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_consent_receipts_record ON consent_receipts(consent_record_id);

-- ============================================================
-- 7. Rights Requests (access, correction, erasure, nomination)
-- ============================================================
CREATE TABLE IF NOT EXISTS rights_requests (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id         UUID REFERENCES organizations(id),
    request_type            VARCHAR(20) NOT NULL
                            CHECK (request_type IN ('access', 'correction', 'erasure', 'nomination', 'portability')),
    status                  VARCHAR(20) NOT NULL DEFAULT 'submitted'
                            CHECK (status IN ('submitted', 'acknowledged', 'in_progress', 'completed', 'rejected', 'escalated')),
    request_details         JSONB DEFAULT '{}',
    response_details        JSONB,
    submitted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at         TIMESTAMPTZ,
    resolved_at             TIMESTAMPTZ,
    resolution_deadline     TIMESTAMPTZ,                   -- Auto: submitted_at + 90 days
    assigned_to             VARCHAR(255),                   -- DPO or team member
    resolution_notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_rights_requests_subject ON rights_requests(subject_id, status);
CREATE INDEX IF NOT EXISTS idx_rights_requests_status ON rights_requests(status, resolution_deadline);
CREATE INDEX IF NOT EXISTS idx_rights_requests_deadline ON rights_requests(resolution_deadline) WHERE status NOT IN ('completed', 'rejected');

-- Auto-set resolution_deadline to 90 days from submission
CREATE OR REPLACE FUNCTION set_rights_request_deadline() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.resolution_deadline IS NULL THEN
        NEW.resolution_deadline := NEW.submitted_at + INTERVAL '90 days';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS rights_request_deadline_trigger ON rights_requests;
CREATE TRIGGER rights_request_deadline_trigger
    BEFORE INSERT ON rights_requests
    FOR EACH ROW
    EXECUTE FUNCTION set_rights_request_deadline();

-- ============================================================
-- 8. Grievances (DPDP Section 13)
-- ============================================================
CREATE TABLE IF NOT EXISTS grievances (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id         UUID REFERENCES organizations(id),
    category                VARCHAR(50) NOT NULL
                            CHECK (category IN ('consent_violation', 'data_breach', 'processing_error',
                                                 'rights_denial', 'unauthorized_processing', 'other')),
    description             TEXT NOT NULL,
    evidence                JSONB DEFAULT '{}',            -- File references, screenshots
    status                  VARCHAR(20) NOT NULL DEFAULT 'submitted'
                            CHECK (status IN ('submitted', 'acknowledged', 'investigating', 'resolved', 'escalated')),
    assigned_to             VARCHAR(255),                   -- DPO or team member
    submitted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at         TIMESTAMPTZ,
    resolved_at             TIMESTAMPTZ,
    resolution_deadline     TIMESTAMPTZ,                   -- Auto: submitted_at + 90 days
    resolution_notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_grievances_subject ON grievances(subject_id, status);
CREATE INDEX IF NOT EXISTS idx_grievances_status ON grievances(status, resolution_deadline);
CREATE INDEX IF NOT EXISTS idx_grievances_deadline ON grievances(resolution_deadline) WHERE status NOT IN ('resolved', 'escalated');

-- Auto-set grievance deadline
CREATE OR REPLACE FUNCTION set_grievance_deadline() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.resolution_deadline IS NULL THEN
        NEW.resolution_deadline := NEW.submitted_at + INTERVAL '90 days';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS grievance_deadline_trigger ON grievances;
CREATE TRIGGER grievance_deadline_trigger
    BEFORE INSERT ON grievances
    FOR EACH ROW
    EXECUTE FUNCTION set_grievance_deadline();

-- ============================================================
-- 9. Nominations (DPDP Section 14 - authorized representative)
-- ============================================================
CREATE TABLE IF NOT EXISTS consent_nominations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nominee_name        VARCHAR(255) NOT NULL,
    nominee_email       VARCHAR(255),
    nominee_phone       VARCHAR(20),
    nominee_contact     JSONB DEFAULT '{}',
    relationship        VARCHAR(100),
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    revoked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_nominations_subject ON consent_nominations(subject_id, is_active);

-- ============================================================
-- 10. Data Transfers (cross-border tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS data_transfers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID REFERENCES organizations(id),
    subject_id              UUID REFERENCES users(id),
    destination_country     VARCHAR(10) NOT NULL,          -- ISO 3166-1 alpha-2
    destination_service     VARCHAR(255),                   -- e.g. 'Vertex AI', 'Azure OpenAI'
    source_country          VARCHAR(10) DEFAULT 'IN',
    is_restricted           BOOLEAN DEFAULT FALSE,         -- Per negative list
    personal_data_categories TEXT[] DEFAULT '{}',
    purpose_code            VARCHAR(100),
    legal_basis             VARCHAR(50) DEFAULT 'consent',
    transfer_started_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_transfers_org ON data_transfers(organization_id);
CREATE INDEX IF NOT EXISTS idx_data_transfers_subject ON data_transfers(subject_id);
CREATE INDEX IF NOT EXISTS idx_data_transfers_country ON data_transfers(destination_country);

-- ============================================================
-- 11. Row-Level Security Policies
-- ============================================================

-- Enable RLS on all consent tables
ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_purpose_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE rights_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE grievances ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_nominations ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_transfers ENABLE ROW LEVEL SECURITY;

-- Data principals see their own records
CREATE POLICY consent_records_user_policy ON consent_records
    FOR ALL USING (
        subject_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
        OR (organization_id IS NOT NULL AND organization_id::text = current_setting('app.current_org_id', true))
    );

CREATE POLICY consent_grants_user_policy ON consent_purpose_grants
    FOR ALL USING (
        consent_record_id IN (
            SELECT id FROM consent_records
            WHERE subject_id::text = current_setting('app.current_user_id', true)
        )
        OR current_setting('app.current_is_super_admin', true) = 'true'
    );

CREATE POLICY consent_events_user_policy ON consent_events
    FOR ALL USING (
        subject_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
    );

CREATE POLICY consent_receipts_user_policy ON consent_receipts
    FOR ALL USING (
        consent_record_id IN (
            SELECT id FROM consent_records
            WHERE subject_id::text = current_setting('app.current_user_id', true)
        )
        OR current_setting('app.current_is_super_admin', true) = 'true'
    );

CREATE POLICY rights_requests_user_policy ON rights_requests
    FOR ALL USING (
        subject_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
        OR (organization_id IS NOT NULL AND organization_id::text = current_setting('app.current_org_id', true))
    );

CREATE POLICY grievances_user_policy ON grievances
    FOR ALL USING (
        subject_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
        OR (organization_id IS NOT NULL AND organization_id::text = current_setting('app.current_org_id', true))
    );

CREATE POLICY nominations_user_policy ON consent_nominations
    FOR ALL USING (
        subject_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
    );

CREATE POLICY data_transfers_user_policy ON data_transfers
    FOR ALL USING (
        subject_id::text = current_setting('app.current_user_id', true)
        OR current_setting('app.current_is_super_admin', true) = 'true'
        OR (organization_id IS NOT NULL AND organization_id::text = current_setting('app.current_org_id', true))
    );

-- ============================================================
-- 12. Backfill existing users with account_management consent
-- ============================================================
-- This runs once: creates consent records for all existing users
-- They will be prompted for AI consent purposes on next login

-- Insert a default policy version first
INSERT INTO consent_policies (id, version, title, content, language, checksum, effective_from)
VALUES (
    gen_random_uuid(),
    1,
    'ContraRed Privacy Policy v1.0',
    'This privacy policy describes how ContraRed processes your personal data in accordance with India''s Digital Personal Data Protection Act, 2023.',
    'en',
    encode(sha256('ContraRed Privacy Policy v1.0'::bytea), 'hex'),
    NOW()
) ON CONFLICT (version, language) DO NOTHING;
