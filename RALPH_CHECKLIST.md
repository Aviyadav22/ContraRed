# ContraRed Implementation Checklist — Ralph Loop

> **PLAN:** `docs/plans/2026-03-31-contrared-next-features.md`
> **LOG:** `RALPH_LOOP_LOG.md`
> **STATUS:** IN_PROGRESS
> **CURRENT_SPRINT:** 1
> **CURRENT_TASK:** S1-F1-T06
> **LAST_GREEN_COMMIT:** (none yet)
> **TESTS_PASSING:** true (baseline)

---

## QUALITY GATES (MANDATORY — READ EVERY ITERATION)

Before marking ANY task ✅:
1. `cd backend && python -m pytest tests/ -v --tb=short` — ALL tests MUST pass
2. `cd backend && python -m pytest tests/test_regression.py -v` — Regression suite MUST pass
3. `cd backend && python -c "from main import app; print('IMPORT OK')"` — App MUST import
4. No new linting errors in changed files
5. Git commit with descriptive message after each completed task

If ANY gate fails:
- DO NOT mark task complete
- DO NOT move to next task
- Fix the failure first
- Log the failure in RALPH_LOOP_LOG.md

---

## SPRINT 1: FOUNDATION (DPDP Compliance Layer + Source Trail)

### Feature 1: DPDP Compliance Layer System

#### S1-F1-T01: Create compliance_layers model
- [x] Create `backend/app/models/compliance_layer.py`
  - ComplianceLayer model: id, code (unique), name, description, jurisdiction, version, is_active, created_at
  - ComplianceLayerRule model: id, layer_id (FK), clause_type, primary_position, fallback_position, risk_level, is_deal_breaker, detection_patterns (JSON), detection_mode, risk_description, acceptable_position, unacceptable_signals (JSON), acceptable_signals (JSON), sort_order
- [x] Register models in `backend/app/models/__init__.py`
- [x] GATE: `pytest tests/ -v` passes
- [x] GATE: `python -c "from app.models.compliance_layer import ComplianceLayer, ComplianceLayerRule; print('OK')"`
- **STATUS:** DONE

#### S1-F1-T02: Create compliance_layers migration SQL
- [x] Create `backend/migrations/021_compliance_layers.sql`
  - CREATE TABLE compliance_layers (...)
  - CREATE TABLE compliance_layer_rules (...)
  - CREATE INDEX on layer_id, code
  - Add compliance_layers JSONB column to documents table
- [x] GATE: SQL is syntactically valid
- [x] GATE: pytest passes (no model conflicts)
- **STATUS:** DONE

#### S1-F1-T03: Create DPDP layer seed script
- [x] Create `backend/scripts/compliance_layers/dpdp.py`
  - 12 DPDP Act 2023 rules as defined in the plan
  - Rules: consent_mechanism, data_principal_rights, fiduciary_obligations, breach_notification, cross_border_transfer, consent_manager, processor_agreement, childrens_data, purpose_limitation, data_retention, significant_fiduciary, penalty_indemnification
  - Each rule has: clause_type, risk_level, is_deal_breaker, primary_position, detection_patterns, unacceptable_signals, risk_description
- [x] GATE: Python syntax valid
- [x] GATE: pytest passes
- **STATUS:** DONE

#### S1-F1-T04: Create compliance layer seeding service
- [x] Create `backend/app/services/compliance_layer_service.py`
  - `seed_compliance_layers(db)` — inserts DPDP layer + rules if not exists
  - `get_active_layers(db)` — returns all active layers
  - `get_layer_rules(db, layer_code)` — returns rules for a layer (get_layer_rules_as_dicts)
  - `merge_rules(playbook_rules, layer_rules)` — merges playbook + compliance layer rules, deduplicates by clause_type (keeps stricter risk level)
  - `calculate_compliance_score(layer_results)` — readiness score calculation
- [x] GATE: pytest passes
- [ ] GATE: Unit test for merge_rules logic (deferred to S1-F1-T05)
- **STATUS:** DONE

#### S1-F1-T05: Write unit tests for compliance layer service
- [x] Create `backend/tests/test_compliance_layers.py`
  - test_merge_rules_no_overlap — separate rules combine
  - test_merge_rules_with_overlap_layer_stricter — compliance layer RED beats playbook YELLOW
  - test_merge_rules_with_overlap_playbook_stricter — playbook RED kept over layer YELLOW
  - test_merge_rules_empty_layer — no layer rules returns playbook rules unchanged
  - test_merge_rules_empty_playbook — no playbook returns layer rules
  - test_merge_rules_both_empty — both empty returns empty
  - test_dpdp_layer_has_12_rules — validate count
  - test_dpdp_deal_breakers — exactly 4 deal-breakers (consent, data_principal_rights, breach notification, cross-border)
  - test_dpdp_all_rules_have_required_fields — structural validation
  - test_compliance_score_all_green/red/mixed/empty — scoring logic
  - test_strip_layer_prefix — helper function
  - test_find_matching_key — helper function
- [x] GATE: `pytest tests/test_compliance_layers.py -v` — 15/15 pass
- [x] GATE: `pytest tests/ -v` — 50/50 pass
- **STATUS:** DONE

#### S1-F1-T06: Modify AnalyzeRequest to accept compliance_layers
- [ ] Edit `backend/app/api/v1/endpoints/documents.py`
  - Add `compliance_layers: List[str] = []` to AnalyzeRequest
  - In analyze endpoint: load layer rules, call merge_rules
  - Pass merged rules to pipeline.run()
  - Store compliance_layers in document record
- [ ] GATE: pytest passes (existing document tests still green)
- [ ] GATE: Import check passes
- **STATUS:** NOT_DONE

#### S1-F1-T07: Modify analysis pipeline to handle merged rules
- [ ] Edit `backend/app/services/analysis_pipeline.py`
  - Pipeline.run() already takes playbook_rules — verify merged rules work
  - Add compliance_layer_results grouping to PipelineResult
  - Add `compliance_score` calculation to PipelineResult.to_dict()
- [ ] GATE: test_unified_pipeline.py still passes
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S1-F1-T08: Add compliance_layers to batch-analyze endpoint
- [ ] Edit `backend/app/api/v1/endpoints/documents.py`
  - Add `compliance_layers` field to batch request
  - Pass through to each file's analysis
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S1-F1-T09: Create GET /compliance-layers endpoint
- [ ] Add new endpoint in documents.py or new compliance.py router
  - `GET /api/v1/compliance-layers` — returns list of active layers with rule count
  - `GET /api/v1/compliance-layers/{code}` — returns layer detail with rules
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S1-F1-T10: Write API integration tests
- [ ] Add to `backend/tests/test_compliance_layers.py`:
  - test_list_compliance_layers — GET returns list
  - test_analyze_with_compliance_layer — POST /analyze with compliance_layers=["dpdp"]
  - test_analyze_without_compliance_layer — POST /analyze without (backwards compatible)
  - test_invalid_compliance_layer — POST with unknown layer returns 400
- [ ] GATE: ALL tests pass
- [ ] GATE: `pytest tests/ -v` — full suite green
- **STATUS:** NOT_DONE

#### S1-F1-T11: DPDP readiness score calculation
- [ ] Add `calculate_compliance_score(layer_code, layer_results)` to compliance_layer_service.py
  - Returns: score (0-100), compliant count, partial count, non_compliant count, not_applicable count, deal_breakers_failing count
  - GREEN=1.0, YELLOW=0.5, RED=0.0, N/A excluded from denominator
- [ ] Add unit test for score calculation
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S1-F1-CHECKPOINT: Feature 1 Complete
- [ ] ALL S1-F1-T* tasks marked ✅
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(compliance): add DPDP compliance layer system with checkbox overlay"
- [ ] GATE: App imports clean
- **STATUS:** NOT_DONE

---

### Feature 3: Source Trail UI (Backend Part — Expose Hidden Data)

#### S1-F3-T01: Add statutory_reference field to prompt templates
- [ ] Edit `backend/app/services/prompt_templates.py`
  - In SYSTEM_PROMPT_V2: add instruction for AI to include specific statute section numbers in explanation
  - Example: "Always cite the specific section number when referencing a statute (e.g., 'Section 73, Indian Contract Act 1872')"
- [ ] GATE: pytest passes
- [ ] GATE: prompt_templates module imports clean
- **STATUS:** NOT_DONE

#### S1-F3-T02: Expose cross_references in API response
- [ ] Verify PipelineResult.to_dict() includes cross_references per redline
- [ ] Verify confidence breakdown is included in API response
- [ ] Verify hallucination_stats is included in API response
- [ ] If any are missing, add them
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S1-F3-T03: Add verification summary endpoint
- [ ] Add `GET /api/v1/documents/{id}/verification-summary`
  - Returns: total_findings, exact_matches, normalized, fuzzy_corrected, rejected, pass_rate, hallucination_rate
  - Plus: industry_benchmark comparison text
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S1-F3-T04: Write tests for source trail data
- [ ] Add `backend/tests/test_source_trail.py`:
  - test_pipeline_result_has_confidence_breakdown
  - test_pipeline_result_has_cross_references
  - test_pipeline_result_has_hallucination_stats
  - test_verification_summary_endpoint
- [ ] GATE: ALL tests pass
- **STATUS:** NOT_DONE

#### S1-F3-CHECKPOINT: Sprint 1 Feature 3 Complete
- [ ] ALL S1-F3-T* tasks marked ✅
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(source-trail): expose verification data and cross-references in API"
- **STATUS:** NOT_DONE

---

### SPRINT 1 FINAL GATE
- [ ] ALL Sprint 1 tasks complete
- [ ] `pytest tests/ -v` — full green (0 failures)
- [ ] `python -c "from main import app; print('OK')"` — clean
- [ ] No import errors
- [ ] All new code has tests
- [ ] Git tag: `v1.5.0-sprint1`
- **STATUS:** NOT_DONE

---

## SPRINT 2: ENTERPRISE (Bulk Upload Upgrades + Institutional Memory)

### Feature 2: Bulk Upload Upgrades

#### S2-F2-T01: Create batch_jobs database model
- [ ] Create/edit `backend/app/models/batch_job.py`
  - BatchJob: id, user_id (FK), organization_id (FK), status, total_files, completed_files, failed_files, playbook_id (FK), compliance_layers (JSON), created_at, completed_at
  - BatchJobFile: id, batch_id (FK), document_id (FK), filename, status, error_message, risk_summary (JSON), processing_ms, created_at
- [ ] Register in models __init__.py
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F2-T02: Create batch_jobs migration SQL
- [ ] Create `backend/migrations/022_batch_jobs.sql`
- [ ] GATE: SQL valid
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F2-T03: Migrate in-memory batch store to DB
- [ ] Edit `backend/app/api/v1/endpoints/documents.py`
  - Replace `_batch_store` dict with BatchJob/BatchJobFile DB queries
  - `POST /documents/batch-analyze` → create BatchJob + BatchJobFile records
  - `GET /documents/batch/{id}/status` → query DB instead of dict
  - `_process_batch()` → update DB records as files complete
- [ ] Preserve existing behavior (backwards compatible response format)
- [ ] GATE: pytest passes
- [ ] GATE: batch-analyze endpoint still works (API contract unchanged)
- **STATUS:** NOT_DONE

#### S2-F2-T04: Add batch history endpoint
- [ ] Add `GET /api/v1/documents/batches` — list user's past batches with pagination
  - Returns: batch_id, date, file_count, status, risk_summary (aggregate red/yellow/green)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F2-T05: Add consolidated batch report endpoint
- [ ] Add `GET /api/v1/documents/batch/{id}/report`
  - Returns DOCX or JSON with: executive summary across all docs, per-doc risk table, common risks, DPDP scores (if applicable), priorities
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F2-T06: Add compliance_layers support to batch
- [ ] Ensure `compliance_layers` field works in batch-analyze
- [ ] Store compliance_layers in BatchJob record
- [ ] Include compliance scores in batch status response
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F2-T07: Increase file limit for paid tiers
- [ ] Make max files configurable by subscription tier:
  - Free: 5, Starter: 10, Pro: 25, Business: 50, Enterprise: 50
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F2-T08: Write batch upgrade tests
- [ ] Add `backend/tests/test_batch_jobs.py`:
  - test_batch_persists_to_db
  - test_batch_history_returns_past_batches
  - test_batch_report_endpoint
  - test_batch_with_compliance_layers
  - test_batch_file_limit_by_tier
- [ ] GATE: ALL tests pass
- **STATUS:** NOT_DONE

#### S2-F2-CHECKPOINT: Feature 2 Complete
- [ ] ALL S2-F2-T* tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(batch): persist batch state to DB, add history and reports"
- **STATUS:** NOT_DONE

---

### Feature 4: Institutional Memory (Playbook Learning)

#### S2-F4-T01: Create organization_risk_profiles model
- [ ] Create/edit model file
  - OrganizationRiskProfile: id, organization_id (FK), clause_type, total_encounters, accept_count, reject_count, modify_count, escalate_count, avg_threshold (JSON), last_updated
  - UNIQUE(organization_id, clause_type)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F4-T02: Create migration SQL for risk profiles
- [ ] Create `backend/migrations/023_org_risk_profiles.sql`
- [ ] GATE: SQL valid
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F4-T03: Create feedback aggregation service
- [ ] Create `backend/app/services/org_learning.py`
  - `record_user_decision(db, org_id, clause_type, decision)` — update counters
  - `get_org_risk_profile(db, org_id)` — return all profiles for org
  - `generate_org_context(db, org_id, clause_types)` — produce prompt text for AI
  - Only inject context when total_encounters >= 10 for a clause_type
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F4-T04: Wire feedback recording to existing feedback endpoint
- [ ] Edit `backend/app/api/v1/endpoints/feedback.py`
  - On POST /feedback: also call record_user_decision()
  - Map feedback types: correct→accept, false_positive→reject, needs_improvement→modify
- [ ] GATE: pytest passes (existing feedback tests still green)
- **STATUS:** NOT_DONE

#### S2-F4-T05: Inject org context into analysis pipeline
- [ ] Edit `backend/app/services/analysis_pipeline.py`
  - Before AI analysis (Stage 3): load org_risk_profile
  - If profile has sufficient data, append to system prompt
- [ ] GATE: test_unified_pipeline.py still passes
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S2-F4-T06: Write institutional memory tests
- [ ] Add `backend/tests/test_org_learning.py`:
  - test_record_decision_creates_profile
  - test_record_decision_increments_counters
  - test_generate_context_below_threshold — returns empty when <10 encounters
  - test_generate_context_above_threshold — returns prompt text
  - test_feedback_endpoint_records_decision
- [ ] GATE: ALL tests pass
- **STATUS:** NOT_DONE

#### S2-F4-CHECKPOINT: Feature 4 Complete
- [ ] ALL S2-F4-T* tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(learning): add org risk profiles and institutional memory"
- **STATUS:** NOT_DONE

---

### SPRINT 2 FINAL GATE
- [ ] ALL Sprint 2 tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Full regression: all Sprint 1 tests still pass
- [ ] Git tag: `v1.6.0-sprint2`
- **STATUS:** NOT_DONE

---

## SPRINT 3: GLOBAL (Jurisdiction Engine + Marketplace)

### Feature 5: Global Jurisdiction Engine

#### S3-F5-T01: Create jurisdictions database model
- [ ] Create `backend/app/models/jurisdiction.py`
  - Jurisdiction: id, code (unique), name, display_name, legal_system, parent_code, key_statutes (JSON), special_considerations (JSON), prompt_context (TEXT), is_active, sort_order, created_at
  - JurisdictionRuleOverride: id, jurisdiction_id (FK), clause_type, risk_level, risk_weight (FLOAT), suppress (BOOL), primary_position, note, statute_reference
  - UNIQUE(jurisdiction_id, clause_type)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F5-T02: Create jurisdiction migration SQL
- [ ] Create `backend/migrations/024_jurisdictions.sql`
- [ ] GATE: SQL valid
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F5-T03: Migrate hardcoded profiles to seed script
- [ ] Create `backend/scripts/seed_jurisdictions.py`
  - Migrate all 13 existing JurisdictionProfile entries from jurisdiction_detector.py to DB seed data
  - Keep jurisdiction_detector.py regex detection logic
  - Load profiles from DB instead of hardcoded dict
- [ ] GATE: jurisdiction_detector.py still works (same output, DB-backed)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F5-T04: Migrate hardcoded overrides to DB
- [ ] Move JURISDICTION_RULE_OVERRIDES dict entries to JurisdictionRuleOverride seed data
  - India: 8 overrides, California: 3, Delaware: 2, New York: 2, England: 3, Singapore: 2, Germany: 3, France: 2
- [ ] Load overrides from DB in apply_jurisdiction_overrides()
- [ ] GATE: same behavior as before (regression safe)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F5-T05: Add 5 new jurisdictions
- [ ] Add to seed script:
  - US Federal (US) — FAA, DTSA, FTC Act, CLOUD Act
  - Texas (TX-US) — Bus. & Com. Code, strong non-compete
  - EU (EU) — GDPR, AI Act, DSA/DMA, NIS2
  - ADGM (AE-ADGM) — separate from DIFC
  - Enhance existing India (add MSME Act, Labour Codes, Companies Act)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F5-T06: Create jurisdiction API endpoints
- [ ] Add endpoints:
  - `GET /api/v1/jurisdictions` — list active jurisdictions (for toggle UI)
  - `GET /api/v1/jurisdictions/{code}` — full profile + overrides
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F5-T07: Add jurisdiction parameter to analyze endpoint
- [ ] Edit documents.py
  - Add `jurisdiction: Optional[str] = None` to AnalyzeRequest
  - If provided, override auto-detection
  - Pass to pipeline
- [ ] GATE: existing analyze tests pass (backwards compatible)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F5-T08: Write jurisdiction engine tests
- [ ] Add `backend/tests/test_jurisdictions.py`:
  - test_list_jurisdictions — returns 18+ entries
  - test_get_jurisdiction_india — returns IN profile with statutes
  - test_analyze_with_jurisdiction_override — user-selected jurisdiction applied
  - test_auto_detect_still_works — regex detection unchanged
  - test_jurisdiction_overrides_loaded_from_db
  - test_new_jurisdictions_exist — US, TX-US, EU, AE-ADGM all present
- [ ] GATE: ALL tests pass
- **STATUS:** NOT_DONE

#### S3-F5-CHECKPOINT: Feature 5 Complete
- [ ] ALL S3-F5-T* tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(jurisdiction): database-driven global jurisdiction engine with 18 jurisdictions"
- **STATUS:** NOT_DONE

---

### Feature 7: Playbook Marketplace Activation

#### S3-F7-T01: Create marketplace listing endpoint
- [ ] Add `GET /api/v1/playbooks/marketplace` — public playbooks with ratings, usage count
  - Filterable by category, search by name
  - Sorted by rating or usage
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F7-T02: Create "use playbook" endpoint
- [ ] Add `POST /api/v1/playbooks/{id}/fork` — copy public playbook to user's org
  - Creates a copy with source_playbook_id reference
  - User can then customize
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F7-T03: Activate rating/review system
- [ ] Add `POST /api/v1/playbooks/{id}/rate` — submit rating (1-5) + review text
- [ ] Add `GET /api/v1/playbooks/{id}/ratings` — list ratings
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F7-T04: Create industry-specific playbook seeds
- [ ] Create 3 industry playbooks in `backend/scripts/playbooks/`:
  - `fintech.py` — MSA + RBI data localization, PPI guidelines
  - `healthcare.py` — Vendor + sensitive personal data, CDSCO
  - `it_services.py` — MSA + IT Act 2000, CERT-In, SOC2
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S3-F7-T05: Write marketplace tests
- [ ] Add `backend/tests/test_marketplace.py`:
  - test_marketplace_listing
  - test_fork_playbook
  - test_rate_playbook
  - test_industry_playbooks_seeded
- [ ] GATE: ALL tests pass
- **STATUS:** NOT_DONE

#### S3-F7-CHECKPOINT: Feature 7 Complete
- [ ] ALL S3-F7-T* tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(marketplace): activate playbook marketplace with industry templates"
- **STATUS:** NOT_DONE

---

### SPRINT 3 FINAL GATE
- [ ] ALL Sprint 3 tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Full regression: Sprint 1+2 tests pass
- [ ] Git tag: `v1.7.0-sprint3`
- **STATUS:** NOT_DONE

---

## SPRINT 4: INTELLIGENCE (Agentic AI + Smriti MCP)

### Feature 6: Agentic AI — Tool Interface + Review Agent

#### S4-F6-T01: Create agent tools interface
- [ ] Create `backend/app/services/agent_tools.py`
  - ContraRedToolkit class with methods:
    - analyze_document() — wraps pipeline.run()
    - analyze_clause() — wraps single-clause analysis
    - check_compliance() — wraps compliance layer check
    - generate_fix() — wraps fix generation
    - get_risk_summary() — query document risks
    - compare_versions() — diff two docs
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S4-F6-T02: Create contract review agent
- [ ] Create `backend/app/services/review_agent.py`
  - ReviewAgent class using ContraRedToolkit
  - `async review(text, instructions)` method
  - Orchestrates: detect jurisdiction → select playbook → enable compliance layers → run analysis → prioritize → generate fixes for deal-breakers
  - Returns structured ReviewResult
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S4-F6-T03: Create agent API endpoint
- [ ] Add `POST /api/v1/agent/review`
  - Input: text, instructions (natural language), playbook_id (optional), compliance_layers (optional)
  - Output: structured review with prioritized findings + ready fixes
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S4-F6-T04: Write agent tests
- [ ] Add `backend/tests/test_agent.py`:
  - test_toolkit_analyze_document
  - test_toolkit_check_compliance
  - test_review_agent_orchestrates_pipeline
  - test_agent_endpoint_returns_structured_review
- [ ] GATE: ALL tests pass
- **STATUS:** NOT_DONE

#### S4-F6-CHECKPOINT: Feature 6 Phase 1-2 Complete
- [ ] ALL S4-F6-T* tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(agent): add contract review agent with tool interface"
- **STATUS:** NOT_DONE

---

### Feature 8: Smriti MCP Integration

#### S4-F8-T01: Create Smriti MCP client
- [ ] Create `backend/app/services/smriti_mcp_client.py`
  - SmritiClient class
  - `call_tool(tool_name, **kwargs)` — calls Smriti MCP server
  - Graceful fallback if Smriti unavailable (returns empty, logs warning)
  - Config: SMRITI_MCP_URL env var (optional)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S4-F8-T02: Create MCP tool definitions
- [ ] Create `backend/app/services/smriti_tools.py`
  - Define tool schemas for: search_case_law, get_statute_text, find_judicial_interpretation, get_legal_principle, check_statute_compliance
  - Each tool has typed parameters + return format
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S4-F8-T03: Integrate Smriti into Stage 5 enrichment
- [ ] Edit `backend/app/services/analysis_pipeline.py`
  - After Stage 4 verification, optionally call Smriti for:
    - Statutory text for referenced sections
    - Relevant case law (top 2)
  - Add results to enriched redline as `statutory_basis` and `case_law_context`
  - MUST be optional — pipeline works without Smriti
- [ ] GATE: test_unified_pipeline.py still passes (Smriti disabled)
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S4-F8-T04: Add research endpoint with Smriti
- [ ] Add `POST /api/v1/documents/{id}/research/{redline_index}`
  - Calls Smriti MCP for deep research on a specific finding
  - Returns: statutory_basis, case_law (citations + paragraphs), legal_principle
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S4-F8-T05: Write Smriti integration tests
- [ ] Add `backend/tests/test_smriti_integration.py`:
  - test_smriti_client_graceful_fallback — returns empty when unavailable
  - test_pipeline_without_smriti — works as before
  - test_pipeline_with_smriti_mock — enrichment adds case law
  - test_research_endpoint
- [ ] GATE: ALL tests pass
- **STATUS:** NOT_DONE

#### S4-F8-CHECKPOINT: Feature 8 Complete
- [ ] ALL S4-F8-T* tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(smriti): add Smriti MCP client with case law enrichment"
- **STATUS:** NOT_DONE

---

### SPRINT 4 FINAL GATE
- [ ] ALL Sprint 4 tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Full regression: Sprint 1+2+3 tests pass
- [ ] Git tag: `v1.8.0-sprint4`
- **STATUS:** NOT_DONE

---

## SPRINT 5: ADVANCED AGENTS (Compliance Watch + Renewal Intelligence)

### Feature 6 Continued: Advanced Agents

#### S5-F6-T01: Create Compliance Watch Agent
- [ ] Create `backend/app/services/compliance_watch.py`
  - ComplianceWatchAgent class
  - `trigger_rescan(compliance_layer_code, updated_rules, org_id)` — find affected docs, re-scan, produce delta report
  - `find_affected_documents(org_id, layer_code)` — query docs with this layer
  - `compute_delta(old_result, new_result)` — diff findings
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S5-F6-T02: Create Compliance Watch endpoint
- [ ] Add `POST /api/v1/agent/compliance-watch/trigger`
  - Input: compliance_layer_code, org_id
  - Output: delta report with newly non-compliant contracts
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S5-F6-T03: Create Renewal Intelligence Agent
- [ ] Create `backend/app/services/renewal_agent.py`
  - RenewalAgent class
  - `scan_expiring_contracts(org_id, days_ahead=90)` — find docs with expiry metadata
  - `generate_renewal_brief(document_id)` — re-analyze + compare against org profile
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S5-F6-T04: Create Renewal Intelligence endpoint
- [ ] Add `GET /api/v1/agent/renewals?days_ahead=90`
  - Returns list of expiring contracts with renewal briefs
- [ ] GATE: pytest passes
- **STATUS:** NOT_DONE

#### S5-F6-T05: Write advanced agent tests
- [ ] Add `backend/tests/test_advanced_agents.py`:
  - test_compliance_watch_finds_affected_docs
  - test_compliance_watch_delta_report
  - test_renewal_agent_finds_expiring
  - test_renewal_brief_generation
- [ ] GATE: ALL tests pass
- **STATUS:** NOT_DONE

#### S5-F6-CHECKPOINT: Advanced Agents Complete
- [ ] ALL S5-F6-T* tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] Git commit: "feat(agents): add compliance watch and renewal intelligence agents"
- **STATUS:** NOT_DONE

---

### SPRINT 5 FINAL GATE
- [ ] ALL Sprint 5 tasks complete
- [ ] `pytest tests/ -v` — full green
- [ ] FULL REGRESSION: ALL tests from Sprint 1-5 pass
- [ ] Git tag: `v2.0.0-complete`
- **STATUS:** NOT_DONE

---

## TASK COUNT SUMMARY

| Sprint | Feature | Tasks | Tests |
|--------|---------|-------|-------|
| S1 | F1: DPDP Compliance Layer | 11 + checkpoint | 10+ unit/integration |
| S1 | F3: Source Trail Backend | 4 + checkpoint | 4 |
| S2 | F2: Bulk Upload Upgrades | 8 + checkpoint | 5+ |
| S2 | F4: Institutional Memory | 6 + checkpoint | 5 |
| S3 | F5: Jurisdiction Engine | 8 + checkpoint | 6+ |
| S3 | F7: Marketplace | 5 + checkpoint | 4 |
| S4 | F6: Agentic AI (Phase 1-2) | 4 + checkpoint | 4 |
| S4 | F8: Smriti MCP | 5 + checkpoint | 4 |
| S5 | F6: Advanced Agents | 5 + checkpoint | 4 |
| **TOTAL** | | **56 tasks** | **46+ tests** |
