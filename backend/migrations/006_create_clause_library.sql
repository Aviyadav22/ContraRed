-- 006: Create clause_library table
-- Stores organization-scoped saved clauses for reuse during contract review.

CREATE TABLE IF NOT EXISTS clause_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    clause_type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    approved_text TEXT NOT NULL,
    is_mandatory BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clause_library_org ON clause_library(organization_id);
CREATE INDEX IF NOT EXISTS idx_clause_library_type ON clause_library(organization_id, clause_type);
CREATE INDEX IF NOT EXISTS idx_clause_library_creator ON clause_library(created_by);
