# CONTRARED REFACTOR PRD — Overnight Autonomous Run

## CONTEXT
ContraRed is an AI-powered contract redlining SaaS platform for lawyers and legal teams. A lawyer opens a contract in Microsoft Word, the add-in scans every clause against a playbook of rules, flags risks (RED/YELLOW), and generates surgical word-level redline suggestions that can be applied directly into the document with Track Changes.

Tech stack: FastAPI backend (Python 3.11), React 19 + Vite 7 + TailwindCSS 4 dashboard, TypeScript + Office.js Word Add-in, PostgreSQL (Supabase), Redis (optional, graceful fallback), Google Gemini AI (gemini-3.1-pro-preview for analysis, gemini-3.1-flash-lite-preview for fast subtasks), Azure OpenAI GPT-4O (legacy fallback), SQLAlchemy 2.0 async ORM, asyncpg, slowapi rate limiting.

This codebase was written by Claude Opus across multiple sessions. Many functions were written with intent but never wired up. Some represent earlier approaches that were superseded but never cleaned. Your job is to understand the CONTRACT REVIEW PURPOSE of each function, then either wire it into the app or mark it for human review with clear reasoning.

## DEPLOYMENT (LIVE)
- Backend: https://contrared.onrender.com (Render.com, service: srv-d6hh7ctm5p6s73bjhe80)
- Dashboard: https://contrared.netlify.app (Netlify)
- Word Add-in: https://contrared-addin.netlify.app (Netlify)
- Database: Supabase PostgreSQL (ap-south-1, 30 tables, 48 RLS policies)

## RULES
- WORK ON EXACTLY ONE TASK PER ITERATION
- After completing a task, update this file: change `[ ]` to `[x]` for that task
- Commit after every task with message: `[CONTRARED-REFACTOR] <task description>`
- NEVER delete a function unless you find its EXACT duplicate doing the same thing
- NEVER touch .env, API keys, secrets, or Render/Netlify deployment configs
- If a function exists, assume it was written for a reason — your job is to find WHERE it plugs in
- When wiring up a function, think like a corporate lawyer reviewing contracts: "Would this help me spot a risky indemnity clause faster? Would this help me generate a better redline? Would this help me track what risks I've fixed?"
- Update progress.txt after every iteration with what you did and what you learned about the codebase

## PHASE 1: DEEP AUDIT — Map Every Function to Its Legal Purpose
- [x] AUDIT-1: Read every Python file in backend/app/services/ (37 files). For each function, write a one-line description of what it does and what contract review workflow it serves (document analysis, clause classification, risk assessment, redline generation, playbook matching, hallucination detection, etc). Output to AUDIT_MAP.md
- [x] AUDIT-2: Read every Python file in backend/app/api/v1/endpoints/ (13 files). Map each route to: which service function it calls, which frontend component calls it. Mark any route that has no frontend caller as DISCONNECTED. Mark any service function with no route as UNEXPOSED. Add to AUDIT_MAP.md
- [x] AUDIT-3: Read every React component in dashboard/src/pages/ (19 files) and dashboard/src/components/. For each component, write what it renders and what user action it supports. Add to AUDIT_MAP.md
- [x] AUDIT-4: Read the Word Add-in files (ContraRed-PoC/src/taskpane/taskpane.ts and api.ts). Map each function to: what it does in the Word document context (scan, highlight, apply redline, negotiate, export). Add to AUDIT_MAP.md
- [x] AUDIT-5: Trace the 5-stage analysis pipeline (analysis_pipeline.py). Map each stage: Stage 1 (Extraction) → Stage 2 (Classification via rule_engine + Gemini Flash-Lite) → Stage 3 (Risk Assessment via Gemini Pro) → Stage 4 (Verification via hallucination_guard) → Stage 5 (Enrichment). Identify any stages that call functions which dont exist or have broken imports. Add to AUDIT_MAP.md
- [ ] AUDIT-6: Map the AI provider chain — vertex_client.py attempts Vertex AI → falls back to consumer Gemini API. gemini_analyzer.py wraps the calls. Identify any broken links in provider initialization or fallback logic. Add to AUDIT_MAP.md
- [ ] AUDIT-7: Map the redline generation pipeline — AI suggests fix → redline_implementer.py generates OOXML Track Changes → Word Add-in applies via insertOoxml(). Identify if the surgical word-level diff (using SequenceMatcher) is correctly wired through all code paths. Add to AUDIT_MAP.md
- [ ] AUDIT-8: Map the async task system — workers/tasks.py TaskQueue (Redis-backed with in-memory fallback) → AnalysisJob lifecycle (QUEUED→RUNNING→COMPLETED/FAILED) → frontend polls GET /documents/{id}/status. Identify any broken links. Add to AUDIT_MAP.md
- [ ] AUDIT-9: Create a DISCONNECTED_FUNCTIONS.md listing every function that exists but is not reachable from any user action. For each one, write your best guess of where it should plug in based on its name, parameters, and the contract review workflow it seems to serve.

## PHASE 2: WIRE THE DOCUMENT ANALYSIS PIPELINE
- [ ] ANALYZE-1: Verify document upload exists end-to-end: dashboard Documents.tsx upload button → POST /documents/upload → document stored in DB. If any link is broken, wire it.
- [ ] ANALYZE-2: Verify the full AI scan works: POST /documents/analyze-full → 5-stage pipeline runs → results stored in Document.analysis_results (JSONB). If any stage fails silently or returns empty, investigate and fix.
- [ ] ANALYZE-3: Verify the Word Add-in scan works: user clicks Scan Document → taskpane.ts calls api.analyzeWithAI() → POST /documents/analyze-full → results displayed as risk cards in the taskpane. Wire any disconnected step.
- [ ] ANALYZE-4: Verify Scan Selection works: user highlights text in Word → clicks Scan Selection → POST /documents/analyze-clause → results displayed. Wire if disconnected.
- [ ] ANALYZE-5: Verify the rule engine (rule_engine.py) and rules library (rules_library.py) are correctly called during Stage 2 classification. The rules_library.py is 63KB of RED/YELLOW flag patterns — verify these patterns actually get matched against contract text.
- [ ] ANALYZE-6: Verify the hallucination guard (Stage 4) actually runs and filters out AI-invented clause references. If it exists but is bypassed, wire it back in.
- [ ] ANALYZE-7: Verify playbook-aware analysis works: when a user selects a custom playbook, the AI analysis uses that playbook's rules instead of defaults. Trace from playbookSelect dropdown → API call → analysis_pipeline. Wire if disconnected.
- [ ] ANALYZE-8: Test the full pipeline on production: login → open contract → scan → verify results show risk cards with correct severity levels.

## PHASE 3: WIRE THE REDLINE AND FIX PIPELINE
- [ ] REDLINE-1: Verify "Generate Fix" works end-to-end: user clicks Generate Fix on a risk card → POST /documents/generate-fix → AI generates suggested text → displayed with word-level diff (red deletions, green insertions). Wire if any step is broken.
- [ ] REDLINE-2: Verify "Apply Fix" works end-to-end: user clicks Apply → POST /documents/redline (ZDR mode) → redline_implementer generates OOXML → insertOoxml() applies to Word document with Track Changes. Verify the surgical word-level OOXML (not bulk paragraph replacement) is correctly generated.
- [ ] REDLINE-3: Verify the text anchor matching works in redline_implementer — it should find the exact clause in the document using exact match → normalized match → fuzzy match (rapidfuzz). Test with a clause that has slight whitespace differences.
- [ ] REDLINE-4: Verify "Apply All" bulk redline works: applyAllRedlines() in taskpane.ts iterates all unfixed risks and applies them sequentially. Wire if disconnected.
- [ ] REDLINE-5: Verify "Fixed" / "Undo" state tracking works: after applying a fix, the risk card shows ✓ Fixed with an Undo button. State persists in fixedRisks Set and localStorage. Wire if disconnected.
- [ ] REDLINE-6: Verify the live negotiation feature works: user clicks negotiation button → enters counterparty negotiation mode → can Accept/Counter/Escalate each redline. Trace from UI button → API calls → backend NegotiationSession tracking. Wire if disconnected.
- [ ] REDLINE-7: Verify export works: Export Report button → generates PDF/DOCX of all risks, fixes, and recommendations. Wire if disconnected.

## PHASE 4: WIRE SUPPORTING FEATURES
- [ ] SUPPORT-1: Verify playbook CRUD works end-to-end: dashboard Playbooks.tsx → create/edit/delete playbooks → PlaybookEditor.tsx rule builder → backend stores in playbooks/playbook_rules tables. Wire if disconnected.
- [ ] SUPPORT-2: Verify playbook versioning works: PlaybookEditor saves versions → can diff/rollback via playbook_versioning.py. Wire if disconnected.
- [ ] SUPPORT-3: Verify the Playbook Marketplace works: publish playbook → appears in Marketplace.tsx → other users can browse/rate/clone. Wire if disconnected.
- [ ] SUPPORT-4: Verify Clause Library works: dashboard ClauseLibrary.tsx → CRUD approved clauses → backend clause_library table → used during analysis for clause suggestions. Wire if disconnected.
- [ ] SUPPORT-5: Verify team management works: Team.tsx → invite users → role assignment (admin/viewer/user) → backend team endpoints. Wire if disconnected.
- [ ] SUPPORT-6: Verify billing/subscription works: Billing.tsx → plan selection → Razorpay/Stripe payment → subscription stored → quota enforcement (FREE_TIER_SCANS limit). Wire if disconnected.
- [ ] SUPPORT-7: Verify audit logging works: every API action → AuditLog entry → viewable in AuditLogs.tsx → exportable. Wire if disconnected.
- [ ] SUPPORT-8: Verify analytics works: Analytics.tsx → risk trends, time benchmarks, ROI calculations → backend analytics_service.py. Wire if disconnected.
- [ ] SUPPORT-9: Verify search history / recent scans works: Word Add-in shows recent scans list → backend GET /documents/list → displays last 5 documents. Wire if disconnected.
- [ ] SUPPORT-10: If there are SSO functions (sso_service.py, sso.py endpoints) that exist but have no dashboard UI, document what's needed to wire them. Do NOT build the UI — just document the gap.
- [ ] SUPPORT-11: If there are feedback functions (feedback.py endpoints) that exist but have no dashboard UI, document the gap similarly.
- [ ] SUPPORT-12: Check for any UI components (modals, sidebars, settings pages) in the dashboard that exist but arent reachable from navigation. Wire them into React Router.

## PHASE 5: HARDEN
- [ ] HARDEN-1: Add try/except with proper HTTP error codes to every FastAPI route that lacks it. A lawyer getting a generic 500 error during a time-sensitive contract review loses trust instantly.
- [ ] HARDEN-2: Add Pydantic input validation to every endpoint that lacks it — especially analyze-full (text cant be empty), redline (original_text required), and auth (email format, password strength).
- [ ] HARDEN-3: Add type hints to every Python function in backend/app/services/ that is missing them.
- [ ] HARDEN-4: Add loading/error/empty states to every dashboard component that makes an API call. Currently some components show blank screen on error.
- [ ] HARDEN-5: Verify CORS is configured correctly — DEBUG=false must use explicit CORS_ORIGINS list (not allow_origin_regex which only matches localhost). Check main.py lines 310-321.
- [ ] HARDEN-6: Verify no API keys or secrets are hardcoded anywhere in the codebase. Check all .ts, .tsx, .py files. Flag any found.
- [ ] HARDEN-7: Verify rate limiting (slowapi) is correctly applied to all public endpoints. The @limiter.limit decorator requires the first parameter named `request` to be a Starlette Request object, NOT a Pydantic model. Check every endpoint with @limiter.limit.
- [ ] HARDEN-8: Verify the token blacklist (Redis-backed with in-memory fallback) works correctly for logout. Check token_service.py.
- [ ] HARDEN-9: Verify Row-Level Security (RLS) middleware (tenant_context.py) correctly sets PostgreSQL session vars from JWT claims on every request.
- [ ] HARDEN-10: Verify the Word Add-in CSP headers in ContraRed-PoC/netlify.toml allow connections to the correct API URL (https://contrared.onrender.com).

## PHASE 6: FINAL VERIFICATION
- [ ] VERIFY-1: Run `cd backend && python -c "from main import app; print('Backend imports OK')"` — verify zero import errors.
- [ ] VERIFY-2: Run `cd dashboard && npx tsc --noEmit --noUnusedLocals --noUnusedParameters` — verify zero TypeScript errors.
- [ ] VERIFY-3: Run `cd dashboard && npx vite build` — verify zero build errors.
- [ ] VERIFY-4: Run `cd ContraRed-PoC && npx tsc --noEmit` — verify zero TypeScript errors.
- [ ] VERIFY-5: Run `cd ContraRed-PoC && npm run build` — verify webpack builds successfully.
- [ ] VERIFY-6: Trace end-to-end: Lawyer opens Word → signs in → selects playbook → scans contract → sees risk cards → generates fix → sees word-level diff → applies fix → Track Changes appear in document → exports report. Document any step that fails.
- [ ] VERIFY-7: Trace dashboard end-to-end: Lawyer logs in → sees dashboard → uploads document → views analytics → manages playbooks → manages team → views audit logs → manages billing. Document any step that fails.
- [ ] VERIFY-8: Create FINAL_STATUS.md summarizing: what was wired, what was fixed, what needs human review, what was left untouched and why.
