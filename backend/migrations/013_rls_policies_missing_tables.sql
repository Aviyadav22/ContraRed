-- ============================================================================
-- Migration 013: RLS policies for tables that are missing them
--
-- Migration 010 added RLS to: documents, document_risks, audit_logs, usage_logs
-- Migration 016 added RLS to: rule_feedback
-- Migration 017 ENABLED RLS on phase 6 tables but created NO policies
--
-- This migration adds RLS policies for all remaining tables:
--   - playbooks (organization_id)
--   - playbook_rules (via join to playbooks)
--   - document_versions (via join to documents)
--   - document_comparisons (via join to documents)
--   - clause_library (organization_id)
--   - contract_templates (organization_id — added by migration 014)
--   - review_sessions (organization_id)
--   - time_benchmarks (organization_id)
--   - roi_config (organization_id)
--   - benchmark_profiles (organization_id)
--   - generated_reports (organization_id)
--   - playbook_rule_tiers (via join to playbook_rules → playbooks)
--   - playbook_conditions (via join to playbooks)
--   - playbook_rule_overrides (via join to playbook_conditions → playbooks)
--   - playbook_rule_dependencies (via join to playbooks)
--   - playbook_versions (via join to playbooks)
--   - playbook_marketplace (via join to playbooks)
--   - playbook_ratings (user_id)
--
-- Session variables used:
--   current_setting('app.current_org_id', true)
--   current_setting('app.current_user_id', true)
--   current_setting('app.is_super_admin', true)
--
-- Idempotent: uses DO blocks with pg_policies checks before CREATE POLICY.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PLAYBOOKS — filter by organization_id
-- ============================================================================

ALTER TABLE playbooks ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbooks' AND policyname = 'tenant_isolation_playbooks') THEN
        CREATE POLICY tenant_isolation_playbooks ON playbooks
            FOR ALL
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
                OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
                OR is_public = true
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbooks' AND policyname = 'superadmin_bypass_playbooks') THEN
        CREATE POLICY superadmin_bypass_playbooks ON playbooks
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- ============================================================================
-- 2. PLAYBOOK_RULES — filter via join to playbooks
-- ============================================================================

ALTER TABLE playbook_rules ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_rules' AND policyname = 'tenant_isolation_playbook_rules') THEN
        CREATE POLICY tenant_isolation_playbook_rules ON playbook_rules
            FOR ALL
            USING (
                playbook_id IN (
                    SELECT id FROM playbooks
                    WHERE organization_id = current_setting('app.current_org_id', true)::uuid
                       OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
                       OR is_public = true
                )
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_rules' AND policyname = 'superadmin_bypass_playbook_rules') THEN
        CREATE POLICY superadmin_bypass_playbook_rules ON playbook_rules
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- ============================================================================
-- 3. DOCUMENT_VERSIONS — filter via join to documents
-- ============================================================================

ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'document_versions' AND policyname = 'tenant_isolation_document_versions') THEN
        CREATE POLICY tenant_isolation_document_versions ON document_versions
            FOR ALL
            USING (
                document_id IN (
                    SELECT id FROM documents
                    WHERE organization_id = current_setting('app.current_org_id', true)::uuid
                       OR (organization_id IS NULL AND user_id = current_setting('app.current_user_id', true)::uuid)
                )
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'document_versions' AND policyname = 'superadmin_bypass_document_versions') THEN
        CREATE POLICY superadmin_bypass_document_versions ON document_versions
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- ============================================================================
-- 4. DOCUMENT_COMPARISONS — filter via join to documents
-- ============================================================================

ALTER TABLE document_comparisons ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'document_comparisons' AND policyname = 'tenant_isolation_document_comparisons') THEN
        CREATE POLICY tenant_isolation_document_comparisons ON document_comparisons
            FOR ALL
            USING (
                document_id IN (
                    SELECT id FROM documents
                    WHERE organization_id = current_setting('app.current_org_id', true)::uuid
                       OR (organization_id IS NULL AND user_id = current_setting('app.current_user_id', true)::uuid)
                )
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'document_comparisons' AND policyname = 'superadmin_bypass_document_comparisons') THEN
        CREATE POLICY superadmin_bypass_document_comparisons ON document_comparisons
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- ============================================================================
-- 5. CLAUSE_LIBRARY — filter by organization_id
-- ============================================================================

ALTER TABLE clause_library ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'clause_library' AND policyname = 'tenant_isolation_clause_library') THEN
        CREATE POLICY tenant_isolation_clause_library ON clause_library
            FOR ALL
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
                OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'clause_library' AND policyname = 'superadmin_bypass_clause_library') THEN
        CREATE POLICY superadmin_bypass_clause_library ON clause_library
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- ============================================================================
-- 6. CONTRACT_TEMPLATES — filter by organization_id (added by migration 014)
--    Public templates (organization_id IS NULL) are visible to everyone.
-- ============================================================================

ALTER TABLE contract_templates ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'contract_templates' AND policyname = 'tenant_isolation_contract_templates') THEN
        CREATE POLICY tenant_isolation_contract_templates ON contract_templates
            FOR ALL
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
                OR organization_id IS NULL
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'contract_templates' AND policyname = 'superadmin_bypass_contract_templates') THEN
        CREATE POLICY superadmin_bypass_contract_templates ON contract_templates
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- ============================================================================
-- 7. ANALYTICS TABLES — all filter by organization_id
-- ============================================================================

-- 7a. review_sessions
ALTER TABLE review_sessions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'review_sessions' AND policyname = 'tenant_isolation_review_sessions') THEN
        CREATE POLICY tenant_isolation_review_sessions ON review_sessions
            FOR ALL
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
                OR user_id = current_setting('app.current_user_id', true)::uuid
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'review_sessions' AND policyname = 'superadmin_bypass_review_sessions') THEN
        CREATE POLICY superadmin_bypass_review_sessions ON review_sessions
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 7b. time_benchmarks
ALTER TABLE time_benchmarks ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'time_benchmarks' AND policyname = 'tenant_isolation_time_benchmarks') THEN
        CREATE POLICY tenant_isolation_time_benchmarks ON time_benchmarks
            FOR ALL
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'time_benchmarks' AND policyname = 'superadmin_bypass_time_benchmarks') THEN
        CREATE POLICY superadmin_bypass_time_benchmarks ON time_benchmarks
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 7c. roi_config
ALTER TABLE roi_config ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'roi_config' AND policyname = 'tenant_isolation_roi_config') THEN
        CREATE POLICY tenant_isolation_roi_config ON roi_config
            FOR ALL
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'roi_config' AND policyname = 'superadmin_bypass_roi_config') THEN
        CREATE POLICY superadmin_bypass_roi_config ON roi_config
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 7d. benchmark_profiles
ALTER TABLE benchmark_profiles ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'benchmark_profiles' AND policyname = 'tenant_isolation_benchmark_profiles') THEN
        CREATE POLICY tenant_isolation_benchmark_profiles ON benchmark_profiles
            FOR ALL
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'benchmark_profiles' AND policyname = 'superadmin_bypass_benchmark_profiles') THEN
        CREATE POLICY superadmin_bypass_benchmark_profiles ON benchmark_profiles
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 7e. generated_reports
ALTER TABLE generated_reports ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'generated_reports' AND policyname = 'tenant_isolation_generated_reports') THEN
        CREATE POLICY tenant_isolation_generated_reports ON generated_reports
            FOR ALL
            USING (
                organization_id = current_setting('app.current_org_id', true)::uuid
                OR created_by = current_setting('app.current_user_id', true)::uuid
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'generated_reports' AND policyname = 'superadmin_bypass_generated_reports') THEN
        CREATE POLICY superadmin_bypass_generated_reports ON generated_reports
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- ============================================================================
-- 8. PHASE 6 TABLES — migration 017 enabled RLS but created NO policies
-- ============================================================================

-- 8a. playbook_rule_tiers — via join to playbook_rules → playbooks
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_rule_tiers' AND policyname = 'tenant_isolation_playbook_rule_tiers') THEN
        CREATE POLICY tenant_isolation_playbook_rule_tiers ON playbook_rule_tiers
            FOR ALL
            USING (
                rule_id IN (
                    SELECT pr.id FROM playbook_rules pr
                    JOIN playbooks p ON pr.playbook_id = p.id
                    WHERE p.organization_id = current_setting('app.current_org_id', true)::uuid
                       OR (p.organization_id IS NULL AND p.created_by = current_setting('app.current_user_id', true)::uuid)
                       OR p.is_public = true
                )
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_rule_tiers' AND policyname = 'superadmin_bypass_playbook_rule_tiers') THEN
        CREATE POLICY superadmin_bypass_playbook_rule_tiers ON playbook_rule_tiers
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 8b. playbook_conditions — via join to playbooks
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_conditions' AND policyname = 'tenant_isolation_playbook_conditions') THEN
        CREATE POLICY tenant_isolation_playbook_conditions ON playbook_conditions
            FOR ALL
            USING (
                playbook_id IN (
                    SELECT id FROM playbooks
                    WHERE organization_id = current_setting('app.current_org_id', true)::uuid
                       OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
                       OR is_public = true
                )
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_conditions' AND policyname = 'superadmin_bypass_playbook_conditions') THEN
        CREATE POLICY superadmin_bypass_playbook_conditions ON playbook_conditions
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 8c. playbook_rule_overrides — via join to playbook_conditions → playbooks
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_rule_overrides' AND policyname = 'tenant_isolation_playbook_rule_overrides') THEN
        CREATE POLICY tenant_isolation_playbook_rule_overrides ON playbook_rule_overrides
            FOR ALL
            USING (
                condition_id IN (
                    SELECT pc.id FROM playbook_conditions pc
                    JOIN playbooks p ON pc.playbook_id = p.id
                    WHERE p.organization_id = current_setting('app.current_org_id', true)::uuid
                       OR (p.organization_id IS NULL AND p.created_by = current_setting('app.current_user_id', true)::uuid)
                       OR p.is_public = true
                )
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_rule_overrides' AND policyname = 'superadmin_bypass_playbook_rule_overrides') THEN
        CREATE POLICY superadmin_bypass_playbook_rule_overrides ON playbook_rule_overrides
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 8d. playbook_rule_dependencies — via join to playbooks
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_rule_dependencies' AND policyname = 'tenant_isolation_playbook_rule_dependencies') THEN
        CREATE POLICY tenant_isolation_playbook_rule_dependencies ON playbook_rule_dependencies
            FOR ALL
            USING (
                playbook_id IN (
                    SELECT id FROM playbooks
                    WHERE organization_id = current_setting('app.current_org_id', true)::uuid
                       OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
                       OR is_public = true
                )
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_rule_dependencies' AND policyname = 'superadmin_bypass_playbook_rule_dependencies') THEN
        CREATE POLICY superadmin_bypass_playbook_rule_dependencies ON playbook_rule_dependencies
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 8e. playbook_versions — via join to playbooks
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_versions' AND policyname = 'tenant_isolation_playbook_versions') THEN
        CREATE POLICY tenant_isolation_playbook_versions ON playbook_versions
            FOR ALL
            USING (
                playbook_id IN (
                    SELECT id FROM playbooks
                    WHERE organization_id = current_setting('app.current_org_id', true)::uuid
                       OR (organization_id IS NULL AND created_by = current_setting('app.current_user_id', true)::uuid)
                       OR is_public = true
                )
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_versions' AND policyname = 'superadmin_bypass_playbook_versions') THEN
        CREATE POLICY superadmin_bypass_playbook_versions ON playbook_versions
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 8f. playbook_marketplace — public by default (read), org-restricted for write
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_marketplace' AND policyname = 'tenant_isolation_playbook_marketplace') THEN
        CREATE POLICY tenant_isolation_playbook_marketplace ON playbook_marketplace
            FOR ALL
            USING (
                publisher_org_id = current_setting('app.current_org_id', true)::uuid
                OR publisher_org_id IS NULL
                OR true  -- marketplace entries are publicly readable
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_marketplace' AND policyname = 'superadmin_bypass_playbook_marketplace') THEN
        CREATE POLICY superadmin_bypass_playbook_marketplace ON playbook_marketplace
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

-- 8g. playbook_ratings — users can see all ratings, but only modify their own
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_ratings' AND policyname = 'tenant_isolation_playbook_ratings') THEN
        CREATE POLICY tenant_isolation_playbook_ratings ON playbook_ratings
            FOR SELECT
            USING (true);  -- all ratings are publicly readable
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_ratings' AND policyname = 'own_ratings_playbook_ratings') THEN
        CREATE POLICY own_ratings_playbook_ratings ON playbook_ratings
            FOR ALL
            USING (
                user_id = current_setting('app.current_user_id', true)::uuid
            );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'playbook_ratings' AND policyname = 'superadmin_bypass_playbook_ratings') THEN
        CREATE POLICY superadmin_bypass_playbook_ratings ON playbook_ratings
            FOR ALL
            USING (current_setting('app.is_super_admin', true) = 'true');
    END IF;
END
$$;

COMMIT;
