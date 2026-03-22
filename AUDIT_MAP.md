# ContraRed Audit Map

## AUDIT-1: Backend Services Layer (37 files, 198+ functions)

### ai_service.py — Multi-Provider AI Integration
| Function | Description | Workflow |
|----------|-------------|----------|
| `AIService.explain_risk()` | Generate plain-English explanation of a contract risk using Gemini/Azure | ai-provider |
| `AIService.suggest_fix()` | Generate suggested revisions for flagged risks | redline-generation |
| `AIService.enrich_match()` | Enhance rule match with AI context and business implications | ai-provider |
| `AIService.summarize_contract()` | Create executive summary of full contract with key terms | ai-provider |
| `AIService.suggest_fix_with_playbook()` | Generate revisions aligned with playbook language and position | redline-generation |

### analysis_pipeline.py — 5-Stage Analysis Orchestration
| Function | Description | Workflow |
|----------|-------------|----------|
| `AnalysisPipeline.analyze()` | Execute full 3-layer analysis (structure→rules→redlines) with hallucination detection | document-analysis |
| `AnalysisPipeline._verify_redlines()` | Post-generation verification of AI output against contract text | hallucination-detection |
| `AnalysisPipeline._score_confidence()` | Apply 5-factor confidence scoring to all redlines | confidence-scoring |
| `AnalysisPipeline._resolve_dependencies()` | Apply cascading risk escalations and suppressions | dependency-resolution |
| `AnalysisPipeline._apply_scope_analysis()` | Analyze breadth/mutuality/exposure for scope-based risk adjustment | scope-analysis |

### analytics_service.py — Organization-Level Analytics
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_org_overview()` | Fetch documents analyzed, total risks, and red/yellow breakdowns | analytics |
| `get_risk_breakdown()` | Calculate risk distribution across risk levels and categories | analytics |
| `get_user_activity()` | Track per-user review counts and performance metrics | analytics |
| `get_trend_data()` | Historical trend data (weekly/monthly) for risk and volume patterns | analytics |
| `get_executive_dashboard()` | Board-ready KPI summary with ROI and team performance | analytics |
| `get_bi_export_data()` | Full-export data for BI integration (Tableau, Power BI) | reporting |

### benchmark_service.py — Risk Benchmarking & Comparison
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_document_percentile()` | Calculate where this document ranks against portfolio | benchmarking |
| `get_portfolio_risk()` | Overall portfolio risk summary with high-risk contracts list | benchmarking |
| `get_clause_analytics()` | Per-clause-type risk rankings across portfolio | benchmarking |
| `get_team_performance()` | Per-reviewer speed, accuracy, and risk detection rates | benchmarking |
| `refresh_benchmark_profiles()` | Recompute all portfolio percentiles after new analyses | benchmarking |

### cache_service.py — Redis-Based Caching (Tenant-Isolated)
| Function | Description | Workflow |
|----------|-------------|----------|
| `CacheService.connect/disconnect()` | Initialize/close Redis connection | caching |
| `CacheService.get/set/delete()` | Key-value ops with org isolation | caching |
| `CacheService.delete_org_keys()` | Bulk-delete all keys for an organization | caching |
| `CacheService.make_analysis_key/make_clause_key()` | Generate org-isolated cache keys | caching |

### clause_classifier.py — Clause Categorization
| Function | Description | Workflow |
|----------|-------------|----------|
| `ClauseClassifier.classify()` | Detect clause type (e.g., "liability_cap") from text | clause-classification |
| `ClauseClassifier.classify_batch()` | Classify multiple clause snippets in bulk | clause-classification |

### confidence_scorer.py — Multi-Factor Confidence Scoring
| Function | Description | Workflow |
|----------|-------------|----------|
| `ConfidenceScorer.score_redline()` | Calculate confidence (0-1) using 5-factor model | confidence-scoring |
| `ConfidenceScorer.score_batch()` | Score multiple redlines with breakdown details | confidence-scoring |

### contract_differ.py — Contract Comparison
| Function | Description | Workflow |
|----------|-------------|----------|
| `compute_diff()` | Paragraph-by-paragraph diff between two contract versions | document-analysis |
| `compute_diff_with_ai()` | Enhanced diff with AI-assisted section matching | document-analysis |

### defined_terms_resolver.py — Defined Terms Extraction
| Function | Description | Workflow |
|----------|-------------|----------|
| `DefinedTermsResolver.resolve()` | Extract all defined terms and map definitions with circular ref handling | defined-terms |
| `DefinedTermsResolver._check_overbroad()` | Detect overbroad definitions using 10-signal pattern matching | defined-terms |

### dependency_resolver.py — Cross-Clause Risk Cascading
| Function | Description | Workflow |
|----------|-------------|----------|
| `DependencyResolver.resolve()` | Apply rule dependencies to cascade risk escalations/suppressions | dependency-resolution |
| `DependencyResolver._evaluate_trigger()` | Check if dependency trigger condition is met | dependency-resolution |
| `DependencyResolver._apply_effect()` | Apply effect (escalate/suppress/flag) to target rule | dependency-resolution |

### email_service.py — Transactional Email
| Function | Description | Workflow |
|----------|-------------|----------|
| `send_password_reset_email()` | Send password reset link via Resend | email |
| `send_dunning_email()` | Send payment overdue notification | billing |

### fix_verifier.py — AI Fix Verification
| Function | Description | Workflow |
|----------|-------------|----------|
| `FixVerifier.verify_fix()` | Post-generation verification: section refs, length, playbook alignment | hallucination-detection |

### gemini_analyzer.py — AI-First Contract Analysis
| Function | Description | Workflow |
|----------|-------------|----------|
| `GeminiAnalyzer.analyze_full_contract()` | Full AI analysis pipeline with jurisdiction awareness | document-analysis |
| `GeminiAnalyzer.generate_clause()` | AI generation of missing clause based on playbook | ai-provider |
| `GeminiAnalyzer.generate_fix()` | AI-generated revision for flagged risk | redline-generation |
| `GeminiAnalyzer.analyze_clause()` | Deep AI analysis of single clause | ai-provider |
| `GeminiAnalyzer.research_clause()` | Research-mode: explanation + case law references | ai-provider |

### hallucination_guard.py — Post-Generation Verification
| Function | Description | Workflow |
|----------|-------------|----------|
| `HallucinationGuard.verify_quote()` | 4-stage verification (exact→normalized→fuzzy→reject) | hallucination-detection |
| `HallucinationGuard.verify_batch()` | Verify multiple quotes in bulk | hallucination-detection |
| `HallucinationGuard.needs_requery()` | Determine if AI should be re-prompted | hallucination-detection |

### intelligence_bridge.py — Strategy Pattern for Analysis
| Function | Description | Workflow |
|----------|-------------|----------|
| `OmniContextStrategy.analyze()` | Full-doc-to-GPT-4o strategy (small contracts) | document-analysis |
| `HybridSentinelStrategy.analyze()` | Scout/Surgeon two-pass (large contracts) | document-analysis |
| `IntelligenceBridge.get_strategy()` | Factory: select strategy by doc size | document-analysis |

### invoice_pdf.py — Invoice PDF Generation
| Function | Description | Workflow |
|----------|-------------|----------|
| `generate_invoice_pdf()` | Generate single-page invoice PDF | billing |

### issues_exporter.py — Issue Export
| Function | Description | Workflow |
|----------|-------------|----------|
| `export_issues_to_csv()` | Export analysis issues to CSV | reporting |
| `export_issues_to_xlsx()` | Export issues to Excel with color-coded risk levels | reporting |

### jurisdiction_detector.py — Jurisdiction Detection
| Function | Description | Workflow |
|----------|-------------|----------|
| `JurisdictionDetector.detect()` | Identify governing law jurisdiction from text | jurisdiction-detection |
| `apply_jurisdiction_overrides()` | Apply jurisdiction-specific risk adjustments | jurisdiction-detection |

### mfa_service.py — Multi-Factor Authentication
| Function | Description | Workflow |
|----------|-------------|----------|
| `setup_mfa/confirm_mfa_setup/verify_mfa/disable_mfa()` | Full MFA lifecycle | mfa |
| `generate_backup_codes/regenerate_backup_codes()` | Backup code management | mfa |

### pdf_report_generator.py — PDF Report Generation
| Function | Description | Workflow |
|----------|-------------|----------|
| `generate_pdf_report()` | Generate PDF report with risk color coding | reporting |

### playbook_cache.py — Rule Engine Caching
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_default_rule_engine/get_cached_rule_engine()` | Cached RuleEngine instances | caching |
| `invalidate_playbook_cache()` | Clear cache on playbook mutation | caching |

### playbook_conditions_engine.py — Conditional Playbook Logic
| Function | Description | Workflow |
|----------|-------------|----------|
| `ConditionsEngine.process()` | Full condition evaluation and override application | playbook-matching |

### playbook_templates.py — Built-in Playbook Templates
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_default_playbook_data()` | Fetch default playbook template | playbook-matching |
| `get_playbook_by_industry()` | Fetch industry-specific playbook | playbook-matching |

### playbook_versioning.py — Playbook Version Control
| Function | Description | Workflow |
|----------|-------------|----------|
| `create_version_snapshot()` | Create JSON snapshot of playbook state | versioning |
| `rollback_to_version()` | Restore playbook to previous version | versioning |
| `diff_versions()` | Field-level diff between two versions | versioning |

### prompt_templates.py — Structured AI Prompts
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_system_prompt()` | 4-step system prompt (ORIENT→TERMS→RULE-BY-RULE→CROSS-CLAUSE) | prompt-engineering |
| `get_clause_prompt()` | Prompt for single-clause analysis | prompt-engineering |

### redline_implementer.py — Surgical Word-Level Redlines
| Function | Description | Workflow |
|----------|-------------|----------|
| `RedlineImplementer.find_anchor()` | Locate text using hash/exact/fuzzy matching | redline-generation |
| `RedlineImplementer.generate_track_changes_ooxml()` | Generate OOXML Track Changes for word-level diffs | redline-generation |
| `RedlineImplementer.generate_insert_only_ooxml()` | Generate OOXML for missing clause insertion | redline-generation |
| `RedlineImplementer.apply_redline()` | Apply single redline with anchor verification | redline-generation |

### report_generator.py — DOCX Report Generation
| Function | Description | Workflow |
|----------|-------------|----------|
| `generate_risk_report()` | Generate professional risk assessment DOCX | reporting |

### report_service.py — Report Management
| Function | Description | Workflow |
|----------|-------------|----------|
| `generate_report()` | Generate and store report (4 types: executive, gc, team, risk) | reporting |
| `list_reports/get_report()` | CRUD for generated reports | reporting |

### roi_service.py — ROI Calculation
| Function | Description | Workflow |
|----------|-------------|----------|
| `calculate_roi()` | Calculate time savings and monetary ROI | analytics |
| `update_org_benchmarks()` | Update org time/cost benchmarks | analytics |

### rule_engine.py — Pattern-Based Clause Detection
| Function | Description | Workflow |
|----------|-------------|----------|
| `RuleEngine.evaluate()` | Execute all rules against contract text | document-analysis |
| `RuleEngine.from_playbook_rules()` | Build RuleEngine from PlaybookRule objects | playbook-matching |

### rules_library.py — 75 Built-in Rules
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_default_rules()` | Fetch 75 pre-built clause detection rules | playbook-matching |

### scope_analyzer.py — Deterministic Scope Analysis
| Function | Description | Workflow |
|----------|-------------|----------|
| `ScopeAnalyzer.analyze()` | Analyze scope dimensions (breadth, mutuality, exposure, duration, trigger) | scope-analysis |
| `ScopeAnalyzer.get_coverage_report()` | Coverage analysis: which clause types found/missing | scope-analysis |

### sso_service.py — WorkOS-Based SSO
| Function | Description | Workflow |
|----------|-------------|----------|
| `get_authorization_url/handle_sso_callback()` | SSO login flow | sso |
| `enable_sso_for_org/disable_sso_for_org()` | SSO configuration | sso |

### structure_extractor.py — Document Structure Extraction
| Function | Description | Workflow |
|----------|-------------|----------|
| `StructureExtractor.extract_from_docx/extract_from_text()` | Parse document into ContractMap | document-analysis |
| `ContractMap.get_node_by_hash/get_all_text()` | Navigate extracted structure | document-analysis |

### text_normalizer.py — Text Normalization
| Function | Description | Workflow |
|----------|-------------|----------|
| `normalize_text()` | Normalize Word text for regex matching | text-normalization |
| `normalize_for_search()` | Aggressive normalization for search | text-normalization |

### token_service.py — JWT Token Blacklist
| Function | Description | Workflow |
|----------|-------------|----------|
| `TokenBlacklistService.revoke/is_revoked()` | Token blacklisting for logout | token-management |
| `TokenBlacklistService.register_session()` | Enforce concurrent session limits | token-management |
| `TokenBlacklistService.record_login_ip()` | IP tracking for anomaly detection | token-management |

---

## AUDIT-2: Backend Endpoints (13 files, 105+ routes)

### analytics.py (18 routes) — ALL CONNECTED
| Route | Service Called | Frontend Caller |
|-------|---------------|-----------------|
| `GET /overview` | `analytics_service.get_org_overview()` | Dashboard |
| `GET /risks` | `analytics_service.get_risk_breakdown()` | Dashboard |
| `GET /users` | `analytics_service.get_user_activity()` | Dashboard |
| `GET /trends` | `analytics_service.get_trend_data()` | Dashboard |
| `GET /export` | Multiple analytics functions | Dashboard |
| `GET /executive` | `analytics_service.get_executive_dashboard()` | Dashboard |
| `GET /roi` | `roi_service.calculate_roi()` | Dashboard |
| `PUT /roi/benchmarks` | `roi_service.update_org_benchmarks()` | Dashboard |
| `PUT /roi/config` | `roi_service.update_roi_config()` | Dashboard |
| `GET /portfolio` | `benchmark_service.get_portfolio_risk()` | Dashboard |
| `GET /clauses` | `benchmark_service.get_clause_analytics()` | Dashboard |
| `GET /team-performance` | `benchmark_service.get_team_performance()` | Dashboard |
| `GET /benchmark/{id}` | `benchmark_service.get_document_percentile()` | Dashboard |
| `POST /benchmarks/refresh` | `benchmark_service.refresh_benchmark_profiles()` | Dashboard |
| `GET /bi-export/{dataset}` | `analytics_service.get_bi_export_data()` | Dashboard |
| `POST /reports/generate` | `report_service.generate_report()` | Dashboard |
| `GET /reports` | `report_service.list_reports()` | Dashboard |
| `GET /reports/{id}` | `report_service.get_report()` | Dashboard |

### audit.py (2 routes) — ALL CONNECTED
| Route | Service Called | Frontend Caller |
|-------|---------------|-----------------|
| `GET /` | Direct SQLAlchemy query | Dashboard |
| `GET /verify` | Hash chain verification (inline) | Dashboard |

### auth.py (13 routes) — ALL CONNECTED
| Route | Service Called | Frontend Caller |
|-------|---------------|-----------------|
| `POST /register` | Direct user creation | Both |
| `POST /login` | `mfa_service` | Both |
| `POST /refresh` | `token_service` | Both |
| `GET /me` | Direct user fetch | Both |
| `POST /change-password` | `token_service` | Both |
| `POST /logout` | `token_service` | Both |
| `POST /mfa/*` (5 routes) | `mfa_service` | Dashboard |
| `POST /forgot-password` | `email_service.send_password_reset_email()` | Both |
| `POST /reset-password` | Direct password update | Both |

### billing.py (13 routes) — ALL CONNECTED
| Route | Service Called | Frontend Caller |
|-------|---------------|-----------------|
| `GET /subscription` | Inline helpers | Dashboard |
| `GET /plans` | PLAN_CATALOG constant | Dashboard |
| `GET /usage` | Inline helpers | Dashboard |
| `POST /create-subscription` | Razorpay/Stripe integration | Dashboard |
| `POST /verify` | Payment verification | Dashboard |
| `GET /invoices` | Direct query | Dashboard |
| `POST /webhook/razorpay` | Payment processing | External (Razorpay) |
| `POST /webhook/stripe` | Payment processing | External (Stripe) |
| `POST /webhook` | Compat endpoint | External |
| `GET /dunning/status` | Dunning logic | Dashboard |
| `GET /invoices/{id}/download` | `invoice_pdf.generate_invoice_pdf()` | Dashboard |
| `POST /admin/zdr/purge-risks` | Admin cleanup | Internal |

### clauses.py (5 routes) — ALL CONNECTED
Full CRUD for clause library. All called from Dashboard ClauseLibrary.tsx.

### documents.py (24 routes) — ALL CONNECTED
| Route | Service Called | Frontend Caller |
|-------|---------------|-----------------|
| `GET /list` | Direct query | Both |
| `POST /analyze` | `RuleEngine.evaluate()`, `AIService` | Word Add-in |
| `POST /analyze-async` | `task_queue.enqueue()` | Dashboard |
| `GET /jobs/{id}` | `task_queue.get_job_status()` | Dashboard |
| `POST /analyze-full` | `analysis_pipeline.run()` | Both |
| `POST /analyze-clause` | `analysis_pipeline.analyze_clause()` | Word Add-in |
| `POST /batch-analyze` | Batch processing | Dashboard |
| `GET /batch/{id}/status` | Batch status | Dashboard |
| `POST /generate-clause` | `gemini_analyzer.generate_clause()` | Word Add-in |
| `POST /generate-fix` | `gemini_analyzer.generate_fix()` | Word Add-in |
| `POST /research-clause` | `gemini_analyzer.research_clause()` | Word Add-in |
| `POST /compare` | `contract_differ.compute_diff()` | Dashboard |
| `POST /analyze-file` | File upload analysis | Dashboard |
| `POST /summarize` | `ai_service.summarize_contract()` | Dashboard |
| `POST /redline` | `redline_implementer.apply_redline()` | Word Add-in |
| `GET /manifest` | Serves XML | External |
| `GET /installer` | Serves JSON | External |
| `POST /export-report` | `report_generator.generate_risk_report()` | Word Add-in |
| `POST /export-issues` | `issues_exporter` | Dashboard |
| `GET /{id}` | Direct fetch | Dashboard |
| `POST /{id}/versions` | Version creation | Dashboard |
| `GET /{id}/versions` | Version listing | Dashboard |
| `GET /{id}/diff` | `contract_differ.compute_diff()` | Dashboard |

### feedback.py (3 routes) — ALL CONNECTED
Full CRUD for rule feedback. Called from Dashboard.

### playbooks.py (19 routes) — ALL CONNECTED
Full CRUD + rules + tiers + conditions + overrides + dependencies + versioning + marketplace. All called from Dashboard.

### sso.py (5 routes) — ALL CONNECTED
SSO authorize/callback/status/enable/disable. Service: `sso_service`. Note: requires WorkOS credentials.

### team.py (3 routes) — ALL CONNECTED
Team member listing, role change, removal. Called from Dashboard Team.tsx.

### templates.py (4 routes) — ALL CONNECTED
Template CRUD. Called from Dashboard Templates.tsx.

### users.py (5 routes) — ALL CONNECTED
User stats, profile update, org stats, account deletion. Called from Dashboard.

### UNEXPOSED Service Functions
No service functions were found without at least one route calling them. All 37 service files have routes that invoke their functions either directly or through the analysis pipeline chain.

---

## AUDIT-3: Dashboard React Components (19 pages + 1 shared component)

| Component | Renders | User Action | API Imports |
|-----------|---------|-------------|-------------|
| Landing.tsx | Landing page with features, pricing, CTA | Download installer, navigate to auth | None |
| Login.tsx | Email/password login form | Sign in | `login` |
| Register.tsx | Registration form with password validation | Create account | `register` |
| ForgotPassword.tsx | Password reset request form | Submit email for reset | **None (TODO: wire to backend)** |
| Dashboard.tsx | Stats cards (docs, risks, fixes) + admin links | View metrics, navigate | `getDashboardStats`, `isAdmin` |
| Playbooks.tsx | Playbook list with create/delete/publish | CRUD playbooks | `listPlaybooks`, `createPlaybook`, `deletePlaybook`, `togglePlaybookPublish` |
| PlaybookEditor.tsx | Advanced rule builder with tiers/conditions/deps/versions | Full rule management | 16+ API functions |
| ClauseLibrary.tsx | Approved clauses list with CRUD | Manage clauses | `listClauses`, `createClause`, `updateClause`, `deleteClause` |
| Templates.tsx | Contract template library | Download templates | `listTemplates`, `downloadTemplate` |
| Compare.tsx | Document diff viewer | Compare two contract versions | `compareContracts`, `listPlaybooks` |
| BatchUpload.tsx | Multi-file upload with progress | Batch analysis | `listPlaybooks`, `batchAnalyze`, `getBatchStatus` |
| AuditLogs.tsx | Audit log viewer with filters | Filter/paginate logs | `getAuditLogs` |
| Team.tsx | Team member management | Invite, role change, remove | `getTeamMembers`, `changeTeamMemberRole`, `removeTeamMember` |
| Billing.tsx | Subscription/usage/invoices dashboard | Upgrade plans, view usage | `getSubscription`, `getUsageStats`, `listInvoices`, `createSubscription` |
| Analytics.tsx | Multi-tab analytics (overview/portfolio/team/reports) | View analytics, generate reports | 12+ API functions |
| Executive.tsx | Executive dashboard with ROI/trends | Select time period | `getExecutiveDashboard` |
| Reports.tsx | Report generation and history | Generate/view reports | `generateAnalyticsReport`, `listAnalyticsReports`, `getAnalyticsReport` |
| Marketplace.tsx | Public playbook marketplace with ratings | Browse, fork, rate | `browseMarketplace`, `forkPlaybook`, `ratePlaybook` |
| NotFound.tsx | 404 page | Navigate back | None |
| AppHeader.tsx | Navigation header with user menu | Navigate, logout | `getStoredUser`, `logout`, `isAdmin` |

**Orphaned components: NONE** — All 19 pages routed in App.tsx.
**Notable gap:** ForgotPassword.tsx has a TODO — not wired to backend `/auth/forgot-password` endpoint.

---

## AUDIT-4: Word Add-in (2 core files)

### api.ts — ContraRedAPI Class (28 public methods)

**Auth (6):** `register`, `login`, `getCurrentUser`, `isLoggedIn`, `getUser`, `logout`
**Document Analysis (7):** `listDocuments`, `generateRedlineZDR`, `analyzeWithAI`, `analyzeClause`, `researchClause`, `generateClause`, `generateFix`
**Playbook CRUD (8):** `listPlaybooks`, `getPlaybook`, `createPlaybook`, `updatePlaybook`, `deletePlaybook`, `togglePlaybookPublish`, `addRule`, `updateRule`, `deleteRule`
**Clause/Template (4):** `listClauses`, `createClause`, `listTemplates`, `downloadTemplate`
**Utilities (3):** `exportReport`, `healthCheck`

### taskpane.ts — Core Functions

**Exported (5):** `scanDocument`, `highlightAIText`, `applyAIRedline`, `applyAllRedlines`, `exportReport`

**Key Internal Functions:**
| Function | What it does in Word | Called by |
|----------|---------------------|-----------|
| `handleLogin()` | Auth flow → show main panel | #loginBtn click |
| `scanDocument()` | Full contract AI analysis → risk cards | #scanBtn click |
| `scanSelection()` | Analyze selected text only | #scanSelectionBtn click |
| `highlightAIText()` | Highlight risk clause in document (3-tier search) | Risk card Highlight button |
| `applyAIRedline()` | Apply fix as Track Changes via insertOoxml | Risk card Apply button |
| `applyAllRedlines()` | Batch-apply all unfixed redlines | #applyAllBtn click |
| `undoRedlineFix()` | Revert applied Track Changes | Risk card Undo button |
| `exportReport()` | Download DOCX risk report | #exportReportBtn click |
| `toggleNegotiationMode()` | Enable accept/counter/escalate UI | #negotiationBtn click |
| `createAIRedlineCard()` | Build risk card HTML with all buttons | displayAIResults() |
| `findTextInDocument()` | Search doc with fuzzy/exact/regex | highlightAIText() |
| `loadPlaybooks()` | Populate playbook dropdown | showMainPanel() |
| `toggleTemplatePicker()` | Show/hide template library | #templateBtn click |
| `applyTemplate()` | Insert template text into document | Template selection |

### Key Call Chains
1. **Scan:** `#scanBtn` → `scanDocument()` → `api.analyzeWithAI()` → `displayAIResults()` → `renderRedlineList()`
2. **Fix:** Risk card → `api.generateFix()` → preview diff → `applyAIRedline()` → `api.generateRedlineZDR()` → `insertOoxml()` → Track Changes in Word
3. **Negotiate:** `#negotiationBtn` → `toggleNegotiationMode()` → Accept/Counter/Escalate buttons → `recordNegotiationDecision()`

### API Methods Not Called from taskpane.ts
| Method | Status |
|--------|--------|
| `getCurrentUser()` | Not called — user info from cached `getUser()` |
| `generateClause()` | Not called — no UI for clause generation in add-in |
| `getPlaybook()` | Not called — detail view not implemented |
| `updatePlaybook()` | Not called — edit not implemented in add-in |
| `deletePlaybook()` | Not called — delete not implemented in add-in |
| `togglePlaybookPublish()` | Not called — publish toggle not in add-in |
| `addRule/updateRule/deleteRule()` | Not called — rule CRUD not in add-in |
| `listClauses/createClause()` | Not called — clause library not in add-in |

**Note:** These API methods exist because the add-in codebase shares the API client pattern with the dashboard. They're available for future add-in features but playbook/clause management is intentionally dashboard-only.

---

## AUDIT-5: 5-Stage Analysis Pipeline (analysis_pipeline.py)

### Pipeline Flow
```
run() orchestrator
├── Pre-Stage: Input validation (min 100 chars, English check, contract check)
├── Stage 1: EXTRACTION (deterministic, CPU-bound via thread pool)
│   ├── StructureExtractor.extract_from_text() → ContractMap with SHA-256 hashes
│   ├── DefinedTermsResolver.resolve() → defined terms + overbroad flags
│   └── JurisdictionDetector.detect() → jurisdiction hints
├── Stage 2: CLASSIFICATION (rule engine, CPU-bound via thread pool)
│   ├── RuleEngine.evaluate() → RuleMatch objects against contract text
│   └── Optional: playbook_rules override default rules
├── Scope Analysis (between Stage 2-3, deterministic)
│   ├── ScopeAnalyzer.analyze() → breadth/mutuality/exposure/duration/trigger
│   ├── ScopeAnalyzer.get_coverage_report() → clause types found/missing
│   └── apply_jurisdiction_overrides() → jurisdiction-specific risk adjustments
├── Stage 3: RISK ASSESSMENT (Gemini Pro, async AI call)
│   ├── GeminiAnalyzer.analyze_full_contract() → raw redlines with AI explanations
│   └── Fallback: _rule_matches_to_raw_redlines() if AI unavailable
├── Stage 4: VERIFICATION (hallucination guard, CPU-bound via thread pool)
│   ├── HallucinationGuard.verify_batch() → 4-stage verification (exact→normalized→fuzzy→reject)
│   └── Stats: total_checked, exact_matches, fuzzy_matches, rejected
└── Stage 5: ENRICHMENT (confidence scoring, CPU-bound via thread pool)
    ├── ConfidenceScorer.score_batch() → 5-factor confidence (0-1) per redline
    └── ConfidenceLevel: HIGH (>0.7) / MEDIUM (0.4-0.7) / LOW (<0.4)
```

### Graceful Degradation
- Each stage wrapped in try/except — failure returns partial results from completed stages
- Stage 3 fallback: if AI unavailable, converts rule matches to raw redlines (rule-engine-only mode)
- Stage 4 fallback: if verification fails, passes unverified redlines with low confidence (0.2)
- Stage 5 fallback: if scoring fails, assigns MEDIUM confidence (0.5) to all

### Dependencies Verified
| Import | From | Status |
|--------|------|--------|
| `GeminiAnalyzer, gemini_analyzer` | `gemini_analyzer.py` | OK |
| `HallucinationGuard, HallucinationStats` | `hallucination_guard.py` | OK |
| `ConfidenceScorer, ConfidenceScore` | `confidence_scorer.py` | OK |
| `RuleEngine, RuleMatch` | `rule_engine.py` | OK |
| `StructureExtractor, ContractMap` | `structure_extractor.py` | OK |
| `ScopeAnalyzer, scope_analyzer` | `scope_analyzer.py` | OK |
| `jurisdiction_detector, apply_jurisdiction_overrides` | `jurisdiction_detector.py` | OK |

**No broken imports. All stages call functions that exist. Pipeline is fully wired.**

---

## AUDIT-6: AI Provider Chain

### Provider Hierarchy
```
vertex_client.py (core/vertex_client.py)
├── get_backend() → "vertex" | "consumer" | None (thread-safe, double-checked locking)
├── _try_init_vertex() → Vertex AI SDK (enterprise, DPA-compliant)
├── _try_init_consumer() → Consumer google.generativeai SDK (dev/free tier)
├── get_generative_model(name) → GenerativeModel for either backend
└── is_available() → True if any backend works
```

### Call Chain
1. `gemini_analyzer.py` imports `get_generative_model` from `vertex_client.py`
2. `GeminiAnalyzer.__init__()` calls `get_generative_model("gemini-2.0-flash")` (or configured model)
3. Model is used for `generate_content()` calls in all Gemini methods
4. `analysis_pipeline.py` uses `gemini_analyzer` singleton for Stage 3 (Risk Assessment)
5. `ai_service.py` provides legacy Azure OpenAI fallback via `AsyncAzureOpenAI` (lazy import)

### Fallback Logic
- Priority 1: Vertex AI (if `VERTEX_PROJECT_ID` set + SDK installed)
- Priority 2: Consumer Gemini API (if `GEMINI_API_KEY` set)
- Priority 3: None → `RuntimeError("No AI backend available")`
- `REQUIRE_VERTEX_AI=true` blocks consumer fallback (enterprise compliance)
- Azure OpenAI: separate path in `ai_service.py`, not used by main pipeline

**Status: No broken links. Provider chain is fully functional.**

---

## AUDIT-7: Redline Generation Pipeline

### Full Chain
```
Word Add-in (taskpane.ts)                    Backend (documents.py + redline_implementer.py)
─────────────────────────                    ──────────────────────────────────────────────
1. User clicks "Generate Fix" on risk card
   → api.generateFix()                       → POST /documents/generate-fix
                                              → GeminiAnalyzer.generate_fix()
                                              → FixVerifier.verify_fix() (section refs, length, playbook)
                                              → Returns { fix_text, reasoning }

2. User sees word-level diff preview
   → wordDiff(original, modified)            (client-side SequenceMatcher in taskpane.ts)
   → Red deletions, green insertions shown

3. User clicks "Apply"
   → api.generateRedlineZDR()                → POST /documents/redline (ZDR mode)
                                              → RedlineImplementer.find_anchor()
                                                ├── Hash match (SHA-256 paragraph hash)
                                                ├── Exact substring match
                                                └── Fuzzy match (rapidfuzz, threshold 80%)
                                              → RedlineImplementer.generate_track_changes_ooxml()
                                                └── SequenceMatcher word-level diff → OOXML Track Changes
                                              OR: generate_insert_only_ooxml() for missing clauses
                                              → Returns { ooxml, match_confidence, match_method }

4. Word applies Track Changes
   → range.insertOoxml(ooxml, InsertLocation.replace)    (for violations)
   → range.insertOoxml(ooxml, InsertLocation.after)       (for missing clauses)
```

### Surgical Word-Level Diff (SequenceMatcher)
- Uses `difflib.SequenceMatcher` to tokenize original and replacement by whitespace
- Generates OOXML `<w:del>` (red strikethrough) and `<w:ins>` (green underline) tags
- Each word is individually marked as equal/insert/delete — NOT bulk paragraph replacement
- Match confidence tracked: exact (1.0) > normalized > fuzzy (<1.0)

**Status: Fully wired end-to-end. No broken links.**
