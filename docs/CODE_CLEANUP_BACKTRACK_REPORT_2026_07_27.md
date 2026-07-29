# ContraRed Dead and Stale Code Backtrack Report

Date: 27 July 2026

## Purpose

This report separates code that was proven dead from code that only looks
unused in a static search. Nothing in the candidate lists below should be
deleted until its complete backtrack gate is satisfied. This is especially
important in this repository because FastAPI decorators, SQLAlchemy model
registration, application lifespan hooks, string-based relationships,
background tasks, and external API clients can all make useful code appear to
have only one textual reference.

## Deletion gate

Before deleting a symbol, route, table, migration, or file:

1. Search definitions, imports, re-exports, string references, configuration,
   scripts, tests, and documentation.
2. Trace the call path in both directions: entry point to symbol and symbol to
   every side effect, persistence model, and downstream response field.
3. Check framework registration: FastAPI routers and dependencies, middleware,
   startup/shutdown hooks, task registries, ORM metadata, event listeners, and
   plugin/tool registries.
4. Check all product clients: dashboard, Word add-in, batch jobs, direct HTTP
   integrations, generated installers, and any published API documentation.
5. Check database history and production data. Never delete or rewrite an
   applied migration. Remove a table only through a new reversible migration
   after confirming row counts, foreign keys, retention duties, and rollback.
6. Review access logs or API telemetry for at least one agreed deprecation
   window. A missing in-repository client is not proof that customers do not
   call a route.
7. Add or retain a test for the replacement path, deploy the replacement, and
   only then remove the old path in a separate change.

## Confirmed dead code already removed

These removals had a traceable live replacement or no callers and no framework
registration:

| Removed item | Backtrack evidence | Live replacement |
| --- | --- | --- |
| `backend/app/services/intelligence_bridge.py` | No imports or runtime registration; it duplicated AI orchestration concepts | `analysis_pipeline.py`, `gemini_analyzer.py`, and the provider-specific service path |
| `backend/app/services/playbook_schema.py` | No live importer; its validation rules had diverged from the database and API | `/playbooks/{id}/quality` plus the publish-time quality gate in `playbooks.py` |
| `backend/app/db/tenant.py` | No live call path after dependency consolidation | request tenant context in middleware and API dependencies |
| `dashboard/src/pages/ComplianceDashboard.tsx` | Duplicate page not routed as the canonical command centre | `DPDPCommandCenter.tsx` |
| Unused dashboard API wrappers and response-only interfaces | Repository-wide TypeScript reference search showed declaration-only exports | Live page-specific calls retained in `dashboard/src/api/client.ts` |
| Dummy override-deletion mutation | The hook was created and immediately discarded; no override list exposed a delete control | Backend delete route retained for external compatibility and a future real UI |
| Orphan AI service/config methods and compiler-level unused imports/locals | No caller or registration; Ruff and build checks validate the remaining graph | Active AI and pipeline methods |

The backend override-deletion route was deliberately **not** deleted when the
unused dashboard hook was removed. That route may be an external API consumer's
only deletion path.

## Candidates that must remain for now

### Persistence models with no proven writer

| Candidate | Current backtrack | Why deletion is unsafe | Required proof |
| --- | --- | --- | --- |
| `DraftSession` | Model, migrations, model tests, and account-erasure cleanup exist; live drafting results currently use `_draft_store` | Production rows may exist and the model is the likely persistence replacement | Query row counts and retention needs; wire drafting to this table or formally sunset it; then migrate |
| `ReviewSession` | Model registration and erasure cleanup exist, but no current creation path was found | Analytics or older deployments may contain rows | Query production data and old release clients; map every report dependency; use a new migration |
| `DataTransfer` | Table, RLS policy, ORM model, and migration exist; no active service writer or reader was found | It may be intended as the compliance transfer inventory and may contain manually/imported data | Check row counts, admin integrations, and audit requirements; decide whether to wire an inventory service or deprecate |

`DataTransfer` was also carrying a stale “Rule 14” description. Its model
description now correctly identifies DPDP Act section 16 / Rule 15, but the
historical migration remains untouched.

### Public helpers with no in-repository caller

An AST definition scan was cross-checked with repository-wide text searches.
Decorated FastAPI handlers, Pydantic schema types, ORM registrations, startup
hooks, tests, and string-based tool calls were excluded from “dead” conclusions.
The following symbols have no current runtime call site in `backend/app`, but
they are public, operational, tested, documented, or may be used by scripts:

- `billing.get_plan_limit` — redundant with `get_plan_info`; likely removable
  after checking external imports.
- `billing.require_seat_limit` — no team-invite route currently uses it; keep
  until the team-seat workflow is either implemented with it or formally
  removed.
- `clause_taxonomy.is_valid_clause_type_value` and
  `clause_taxonomy.all_clause_type_values`, plus `group_for` — convenience API
  with no runtime caller.
- `playbook_cache.get_cached_rule_engine` — older cache shape; the live review
  path uses serialized rule dictionaries.
- `HallucinationGuard.verify_batch` — no live caller; it is a coherent public
  batch wrapper over the actively used quote verifier and is referenced by
  architecture documentation.
- `redline_implementer.apply_redline_suggestion` — top-level compatibility
  wrapper; the active implementation path must be compared before removal.
- `structure_extractor.extract_contract_structure` and
  `text_normalizer.normalize_for_search` — public wrappers with no internal
  caller; check scripts and downstream package imports.
- `org_learning.get_org_risk_profile` — used by organization-learning tests
  but not a live endpoint; check whether it is a planned personalization entry
  point before removal.
- `encryption.is_encryption_enabled` and `encryption.rotate_key` — operational
  status/key-rotation helpers with no application caller. These should move to
  an explicit administration script or be documented before any removal.

For each, first add a deprecation warning or move it to an explicitly documented
compatibility module. Remove it only after a release cycle with no import or
usage evidence.

### Registered code that is not dead

Do not delete these based on single-reference static reports:

- FastAPI endpoint functions are invoked through route decorators.
- `ConsentEnforcementMiddleware` is registered in `backend/main.py`.
- Cache and token shutdown functions are called by the application lifespan.
- Pydantic request/response classes are consumed through route annotations.
- SQLAlchemy models can be registered through metadata, re-exports, foreign
  keys, and string relationships.
- Agent tools may be selected by name through the tool registry and model tool
  calls rather than direct Python calls.

### External API surface with no current dashboard caller

Keep these until API telemetry and a published deprecation window prove they are
unused:

- Feedback submission, review, and rule-effectiveness endpoints.
- Template detail/download/create endpoints.
- Playbook version-detail and override-deletion endpoints.
- Analytics benchmark and BI/export endpoints.
- SSO administration endpoints.
- Document comparison, versioning, reports, installers, and operational admin
  endpoints.

These routes may be called by the Word add-in, scripts, enterprise integrations,
or customers using the HTTP API directly.

### Deprecated duplicate DPDP routes

`dpdp_compliance.py` still exposes deprecated rights, grievance, and nomination
routes while the canonical implementations live under `/rights` and
`/grievances`. They should be removed only after:

1. the deprecation response identifies the canonical replacement,
2. API logs show no callers for the agreed window,
3. clients and API documentation have migrated, and
4. contract tests confirm the canonical route has equivalent authorization,
   tenant scoping, response shape, audit trail, and side effects.

Until then, keeping the compatibility routes is safer than silently breaking an
external workflow.

## Stale material to archive, not blindly delete

The root contains multiple April 2026 audit/planning snapshots, including
`AUDIT_REPORT.md`, `FINAL_STATUS.md`, `DISCONNECTED_FUNCTIONS.md`,
`PRODUCTION_READINESS_REPORT.md`, `RALPH_*`, and older plan documents. Their
dates and status assertions are no longer reliable as current truth, but they
may record design rationale.

Recommended cleanup:

1. Mark `docs/LAWYER_GRADE_ANALYSIS_AUDIT.md`, this report, the current API
   reference, deployment guide, and environment reference as the canonical
   current documents.
2. Add an “historical snapshot” banner to superseded reports.
3. Move them into a dated `docs/archive/2026-04/` folder in a dedicated
   documentation change after checking inbound links.
4. Update or redirect links before any deletion.

Applied migrations are historical records, not cleanup targets. Migration
`025_consent_management.sql` contains old comments and a default legal-basis
assumption. Do not edit it in place. If the dormant transfer inventory is
activated, add a new migration that corrects current schema comments/defaults
and backfills rows only after a legal-basis mapping has been approved.

## Architecture cleanup, not dead-code cleanup

`backend/app/api/v1/endpoints/drafting.py` stores generated drafts in the
process-local `_draft_store`. This code is live, but it is unsuitable for
multi-worker durability and restart-safe downloads. The safe sequence is:

1. define the required zero-retention and expiry behavior,
2. persist only approved metadata/content using `DraftSession` or an encrypted
   ephemeral store,
3. migrate download and add-in payload reads,
4. test multi-worker, restart, expiration, erasure, and authorization behavior,
5. then remove `_draft_store`.

Deleting `_draft_store` before its replacement would break a useful live
workflow; deleting `DraftSession` first would remove the obvious persistence
model.

## Recommended cleanup order

1. Instrument and deprecate duplicate DPDP compatibility routes.
2. Decide the drafting persistence/ZDR architecture and reconcile
   `_draft_store` with `DraftSession`.
3. Audit production rows for `ReviewSession` and `DataTransfer`.
4. Add import/usage telemetry or deprecation warnings to the public helper
   candidates.
5. Archive stale documentation with redirects.
6. Batch the remaining Word API searches/loads where safe. The Office add-in
   linter reports several `context.sync()` calls inside long-clause matching
   loops; this is live performance debt, not dead code.
7. The add-in asset and Browserslist cleanup is complete: the validated
   manifest uses purpose-sized icons, the production bundle ships about 4.1 KiB
   of icons instead of the unused 913 KiB logo, the original logo is retained
   as a source asset, and `caniuse-lite` was refreshed.
8. Remove candidates in small, separately tested changes—not in one bulk
   deletion.

## Current validation evidence

- Backend: Ruff and bytecode compilation pass; 362 tests pass.
- Dashboard: TypeScript production build and ESLint pass.
- Word add-in: TypeScript and production build pass; manifest validation
  passes; ESLint reports zero errors and seven live Office performance
  warnings.
- No unproven persistence model, public helper, external route, compatibility
  route, historical migration, or user-owned asset was deleted in this final
  cleanup pass.
