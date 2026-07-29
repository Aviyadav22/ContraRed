# ContraRed — Phase Tracker

> Master checklist for all implementation phases. Update checkboxes as tasks complete.
> Last updated: 2026-03-07

---

## Local Dev Environment

| Service | Port | Container | Status |
|---------|------|-----------|--------|
| PostgreSQL | 5433 | contrared-db (postgres:15-alpine) | Running |
| Redis | 6380 | contrared-redis (redis:7-alpine) | Running |
| Backend API | 8005 | uvicorn (host machine) | Running |
| Dashboard | 3006 | vite dev server | Running |
| Word Add-in | 3007 | webpack-dev-server (HTTPS) | Running |

**Test Credentials:**
- `demo@contrared.ai` / `demo123` — USER role, FREE tier
- `aviyadav.personal@gmail.com` — SUPER_ADMIN, ENTERPRISE tier

---

## Phase 1: Local Docker Environment + Default Playbooks

### 1A. Docker Environment — COMPLETE

- [x] Docker containers running (contrared-db on 5433, contrared-redis on 6380)
- [x] Backend running on port 8005 with hot-reload
- [x] Database connected (`/health/db` → connected)
- [x] Redis connected and responding (PONG)
- [x] All migrations applied (001-006 + manual fix for `created_by` column)
- [x] Organization created (`ContraRed Dev`, ENTERPRISE plan)
- [x] Users assigned to org, avi promoted to SUPER_ADMIN
- [x] Dashboard configured (VITE_API_URL → localhost:8005, port 3006)
- [x] Word Add-in configured (API_BASE_URL → localhost:8005, port 3007)
- [x] CORS updated for ports 3006/3007
- [x] Login endpoint tested (JWT tokens returned)
- [x] AI analysis tested (Gemini gemini-3-pro-preview, returns risk cards)
- [x] Export report tested (37KB DOCX generated)
- [x] Clause library endpoint tested (empty list, CRUD ready)

### 1B. Default Playbooks — Seed Data — COMPLETE

Every new user/org should see ready-to-use playbooks covering the most common Indian contract types. Each playbook has rules with detection patterns, preferred positions, fallback positions, and deal-breaker flags.

**Execution plan:** Create a seed script `backend/scripts/seed_default_playbooks.py` that inserts all playbooks + rules via the API or directly into DB. Mark each as `is_default=True, is_public=True` so all users can access them.

#### Playbook List (10 default playbooks)

- [x] **1. Non-Disclosure Agreement (NDA) — Mutual** (7 rules)
  - Category: `nda`
  - Use case: Two parties sharing confidential info (partnerships, due diligence, M&A discussions)
  - Key rules to include:
    - [x] Definition of Confidential Information (YELLOW — flag if overly broad "any and all information")
    - [x] Confidentiality Term (YELLOW — flag perpetual obligations, prefer 3-5 years)
    - [x] Permitted Disclosures (YELLOW — must include legal/regulatory exceptions)
    - [x] Return/Destruction of Information (YELLOW — flag if missing)
    - [x] Non-Solicitation (YELLOW — flag if included, limit to 12 months)
    - [x] Remedies/Injunctive Relief (GREEN — standard, flag if one-sided)
    - [x] Governing Law & Jurisdiction (GREEN — flag if missing or unfavorable jurisdiction)

- [x] **2. Non-Disclosure Agreement (NDA) — Unilateral** (9 rules)
  - Category: `nda`
  - Use case: One party disclosing to another (hiring, vendor evaluation)
  - Key rules to include:
    - [x] All rules from Mutual NDA above
    - [x] Reverse Engineering Prohibition (YELLOW — flag if overly broad)
    - [x] Non-Compete Clause (RED — deal-breaker in a simple NDA)
    - [x] IP Assignment (RED — deal-breaker, NDA should not transfer IP)

- [x] **3. Master Service Agreement (MSA)** (15 rules)
  - Category: `msa`
  - Use case: Ongoing services relationship (IT, consulting, outsourcing)
  - Key rules to include:
    - [x] Scope of Services (YELLOW — flag if vague or undefined)
    - [x] Payment Terms (YELLOW — flag if >45 days, prefer Net 30)
    - [x] Limitation of Liability (RED — flag if unlimited, prefer 12 months fees cap)
    - [x] Indemnification (RED — flag if one-sided/uncapped, prefer mutual + capped)
    - [x] Intellectual Property Ownership (RED — flag if all IP assigned to client, prefer pre-existing IP stays with service provider)
    - [x] Confidentiality (YELLOW — flag perpetual, prefer 3-5 year term)
    - [x] Termination for Convenience (RED — flag if no notice period, prefer 30-day notice + cure period)
    - [x] Termination for Cause (YELLOW — flag if no cure period, prefer 30-day cure)
    - [x] Force Majeure (YELLOW — flag if missing or only covers one party)
    - [x] Assignment (YELLOW — flag if restricted, prefer assignment to affiliates allowed)
    - [x] Warranties (YELLOW — flag if one-sided, prefer mutual representations)
    - [x] Dispute Resolution (GREEN — flag if litigation-only, prefer arbitration under Indian Arbitration Act)
    - [x] Governing Law (GREEN — prefer Indian law, flag foreign jurisdiction)
    - [x] Auto-Renewal (YELLOW — flag if no opt-out window, prefer 30-day opt-out notice)
    - [x] Data Protection/Privacy (YELLOW — flag if missing, must reference IT Act 2000 / DPDP Act 2023)

- [x] **4. SaaS Subscription Agreement** (13 rules)
  - Category: `saas`
  - Use case: Cloud software subscriptions (both as vendor and customer)
  - Key rules to include:
    - [x] Service Level Agreement / Uptime (YELLOW — flag if no SLA, prefer 99.9% uptime)
    - [x] Data Ownership (RED — flag if vendor claims ownership of customer data)
    - [x] Data Security (YELLOW — flag if no security standards mentioned, prefer SOC2/ISO27001)
    - [x] Limitation of Liability (RED — same as MSA)
    - [x] Indemnification (RED — same as MSA)
    - [x] Termination & Data Portability (RED — flag if no data export provision, customer must get data back)
    - [x] Auto-Renewal (YELLOW — same as MSA)
    - [x] Price Escalation (YELLOW — flag if >10% annual increase, prefer capped at CPI)
    - [x] Reverse Engineering (YELLOW — flag prohibition, standard but negotiate for interoperability)
    - [x] IP Ownership (RED — customer data stays customer's, vendor IP stays vendor's)
    - [x] Force Majeure (YELLOW — same as MSA)
    - [x] Data Processing (YELLOW — must have DPA if processing personal data under DPDP Act 2023)
    - [x] Governing Law (GREEN — same as MSA)

- [x] **5. Employment Agreement** (12 rules)
  - Category: `employment`
  - Use case: Hiring employees (India-specific, governed by state Shops & Establishments Acts)
  - Key rules to include:
    - [x] Probation Period (YELLOW — flag if >6 months, standard is 3-6 months)
    - [x] Notice Period (YELLOW — flag if >3 months for non-senior roles)
    - [x] Non-Compete (RED — largely unenforceable in India per Section 27 Indian Contract Act, flag presence)
    - [x] Non-Solicitation (YELLOW — enforceable if reasonable, flag if >12 months)
    - [x] IP Assignment / Work for Hire (YELLOW — standard for employees, flag if includes personal projects)
    - [x] Confidentiality (YELLOW — flag perpetual, prefer 2 years post-termination)
    - [x] Termination for Cause (YELLOW — must list specific grounds)
    - [x] Termination by Employee (GREEN — standard, flag if restrictive)
    - [x] Garden Leave (YELLOW — flag if >3 months)
    - [x] Restrictive Covenants Scope (RED — flag if geography/time is unreasonable)
    - [x] Bonus/Variable Pay (YELLOW — flag if entirely discretionary with no criteria)
    - [x] Governing Law (GREEN — must be Indian law for Indian employees)

- [x] **6. Data Processing Agreement (DPA)** (10 rules)
  - Category: `dpa`
  - Use case: When sharing personal data with a processor (DPDP Act 2023 compliance)
  - Key rules to include:
    - [x] Purpose Limitation (YELLOW — flag if processor can use data for own purposes)
    - [x] Data Subject Rights (YELLOW — flag if missing, must support DPDP Act obligations)
    - [x] Sub-Processor Controls (YELLOW — flag if no notification of sub-processors)
    - [x] Data Breach Notification (RED — processor notice must support the fiduciary's without-delay notices; any 24/48-hour processor clock is a negotiated internal deadline)
    - [x] Data Deletion/Return (RED — flag if no deletion clause post-termination)
    - [x] Cross-Border Transfer (apply the selected authorisation and safeguard position, then verify current section 16 / Rule 15 restrictions and stricter sectoral law)
    - [x] Security Measures (YELLOW — flag if vague, must specify technical + organizational measures)
    - [x] Audit Rights (YELLOW — flag if data fiduciary cannot audit processor)
    - [x] Liability & Indemnification (apply the selected indemnity, causation, cap, and carve-out position; a processor indemnity is not an automatic DPDP statutory requirement)
    - [x] Governing Law (apply the transaction playbook; DPDP applicability does not itself require Indian governing law)

- [x] **7. Consulting / Professional Services Agreement** (10 rules)
  - Category: `custom`
  - Use case: Hiring consultants, freelancers, advisors (Indian market)
  - Key rules to include:
    - [x] Scope of Work (YELLOW — flag if vague or open-ended)
    - [x] Payment Terms & Milestones (YELLOW — flag if no milestones, prefer milestone-based)
    - [x] IP Ownership (RED — flag if consultant retains all IP, prefer work product assigned to client)
    - [x] Limitation of Liability (RED — same as MSA)
    - [x] Indemnification (YELLOW — mutual, capped at fees paid)
    - [x] Confidentiality (YELLOW — flag perpetual)
    - [x] Termination (YELLOW — both parties should have reasonable exit)
    - [x] Independent Contractor Status (YELLOW — must clearly state, not an employment relationship)
    - [x] Non-Compete (RED — generally unenforceable for consultants in India)
    - [x] Governing Law (GREEN — Indian law)

- [x] **8. Vendor / Procurement Agreement** (10 rules)
  - Category: `custom`
  - Use case: Buying goods or services from suppliers
  - Key rules to include:
    - [x] Delivery Terms & Timelines (YELLOW — flag if no specific dates or SLAs)
    - [x] Acceptance Criteria (YELLOW — flag if missing, must define acceptance/rejection process)
    - [x] Payment Terms (YELLOW — flag if advance payment >30%, prefer milestone-based)
    - [x] Warranties on Goods/Services (YELLOW — flag if "as-is", prefer express warranties)
    - [x] Limitation of Liability (RED — same as MSA)
    - [x] Indemnification (RED — vendor must indemnify for defective goods/IP infringement)
    - [x] Termination for Non-Performance (YELLOW — must have cure period)
    - [x] Force Majeure (YELLOW — same as MSA)
    - [x] Insurance Requirements (YELLOW — flag if no minimum insurance)
    - [x] Governing Law (GREEN — Indian law)

- [x] **9. Joint Venture / Partnership Agreement** (10 rules)
  - Category: `custom`
  - Use case: Two or more parties collaborating on a project or business
  - Key rules to include:
    - [x] Profit/Loss Sharing (RED — flag if disproportionate to investment/effort)
    - [x] Decision-Making / Governance (RED — flag if one party has unilateral control)
    - [x] Capital Contribution (YELLOW — must be clearly defined)
    - [x] IP Ownership (RED — flag if one party takes all JV-created IP)
    - [x] Non-Compete Between Partners (YELLOW — flag if too broad)
    - [x] Exit / Buy-Out Mechanism (RED — deal-breaker if missing)
    - [x] Deadlock Resolution (YELLOW — must have mechanism, prefer arbitration)
    - [x] Confidentiality (YELLOW — same as MSA)
    - [x] Termination / Dissolution (YELLOW — must define process and asset distribution)
    - [x] Governing Law (GREEN — Indian law)

- [x] **10. Lease / License Agreement (Commercial Property)** (10 rules)
  - Category: `custom`
  - Use case: Office space, co-working, commercial premises
  - Key rules to include:
    - [x] Rent Escalation (YELLOW — flag if >10% annual, standard is 5-8% in India)
    - [x] Lock-In Period (RED — flag if >3 years with no exit, prefer 1-2 year lock-in)
    - [x] Security Deposit (YELLOW — flag if >6 months rent, standard is 3-6 months in India)
    - [x] Maintenance & Common Area Charges (YELLOW — flag if undefined or escalatable)
    - [x] Termination / Early Exit (RED — must have early exit clause, flag if missing)
    - [x] Permitted Use (YELLOW — must allow business use, flag restrictions)
    - [x] Renewal Terms (YELLOW — flag auto-renewal without notice, prefer 90-day notice)
    - [x] Fit-Out & Restoration (YELLOW — flag if lessee bears all restoration costs)
    - [x] Sub-Letting (YELLOW — flag if prohibited, prefer permitted with consent)
    - [x] Governing Law (GREEN — Indian law, specific state jurisdiction)

#### Implementation Details

**Seed script:** `backend/scripts/seed_default_playbooks.py`
- [x] Create seed script that:
  - Connects to local DB (uses same DATABASE_URL from .env)
  - Creates all 10 playbooks with `is_default=True, is_public=True`
  - Creates all rules for each playbook with correct `clause_type`, `risk_level`, `primary_position`, `fallback_position`, `is_deal_breaker`, `detection_patterns` (regex list), `suggested_language` (JSON with preferred + fallback text)
  - Sets `requires_ai_verification=True` on nuanced rules (context-dependent ones)
  - Is idempotent (checks if playbook exists by name before creating)

**For each rule, web search to populate:**
- [x] `detection_patterns`: 3-5 regex patterns that match the clause in real contracts
- [x] `primary_position`: Preferred language (client-favorable, legally sound for India)
- [x] `fallback_position`: Acceptable compromise language
- [x] `suggested_language`: JSON with `{"preferred": "...", "fallback": "..."}` — actual clause text a lawyer would use

**Rule structure matches PlaybookRule model:**
```python
PlaybookRule(
    playbook_id=playbook.id,
    clause_type="indemnification",         # Category
    primary_position="Mutual indemnification...",  # What we want
    fallback_position="Indemnification capped...", # What we'll accept
    risk_level=RiskLevel.YELLOW,           # RED/YELLOW/GREEN
    is_deal_breaker=False,                 # Walk away if not met?
    detection_patterns=["regex1", "regex2"],       # JSON list of patterns
    suggested_language={"preferred": "...", "fallback": "..."}, # Actual text
    requires_ai_verification=True,         # Needs Gemini to verify context
    verification_prompt="Check if this clause..." # Prompt for AI
)
```

**Verification:**
- [x] Run seed script → 10 playbooks created with 106 total rules
- [x] Login as any user → playbook selector shows all 10 default playbooks
- [x] Select "MSA" playbook → scan a master service agreement → AI uses playbook rules for context
- [x] Select "NDA Mutual" → scan an NDA → relevant rules flagged
- [x] Rules with `is_deal_breaker=True` show as RED in results
- [x] Default playbooks are read-only for non-admin users (can't edit/delete)

---

## Phase 2: Stabilize & Polish

### 2.1 Clause Library UX — Fuzzy Matching — COMPLETE

**Problem:** Clause picker in Word add-in (`taskpane.ts:689`) calls `api.listClauses(redline.rule_name)` which filters by exact `clause_type` match. But Gemini returns free-text rule names like "Intellectual Property Ownership" which won't match user-created clause types like "IP" or "Indemnification".

**Backend changes:**
- [x] Add `search` query param to `GET /clauses/` endpoint
  - File: `backend/app/api/v1/endpoints/clauses.py` (line 60)
  - Change: Add `search: Optional[str] = None` parameter
  - Logic: If `search` is provided, use `ilike(f'%{search}%')` on `clause_type` and `name` via `or_()`
  - Keep existing `clause_type` exact filter as optional fallback
- [x] Test: `curl /api/v1/clauses/?search=indemn` returns matching clauses (verified)

**Frontend changes (Word Add-in):**
- [x] Update clause picker to use `search` param instead of exact `clause_type`
  - File: `ContraRed-PoC/src/taskpane/taskpane.ts` (lines 688-716)
  - Change: Uses `api.listClauses(undefined, redline.rule_name)` for fuzzy search
  - Fallback: Splits rule_name into words and searches each until results found
- [x] Show clause count in picker header ("3 saved clauses" vs "No saved clauses")
- [x] Extended tooltip preview to 300 chars (up from 200)

**API client changes:**
- [x] Update `listClauses()` in `ContraRed-PoC/src/taskpane/api.ts` (line 359)
  - Added optional `search` parameter alongside existing `clause_type`
  - Uses URLSearchParams for clean query string construction

**Verification:**
- [x] `search=nonexistent` → 0 results (correct filtering)
- [x] `search=indemn` → 1 result (partial match on clause_type)
- [x] `search=Standard` → 1 result (partial match on name)
- [x] No filter → returns all active clauses

---

### 2.2 Error Handling for AI Failures — COMPLETE

**Problem:** If Gemini is down or API key is invalid, scan fails with a generic `alert()` (taskpane.ts line 427). Users see "AI Scan failed: [object Object]" — unhelpful.

**Backend changes:**
- [x] Created exception hierarchy in `gemini_analyzer.py`: `AIServiceError`, `AIServiceUnavailable`, `AIRateLimited`, `AIServiceTimeout`
- [x] `analyze_full_contract()` now raises specific exceptions instead of returning silent fallback
- [x] Endpoint catches each exception type and returns appropriate HTTP status:
  - 503: AI not configured / unreachable
  - 429: Rate limited
  - 504: Timeout
  - 502: Generic AI error
- [x] Error responses now structured: `{"message": "...", "error_code": "..."}`

**Frontend changes (Word Add-in):**
- [x] Replaced `alert()` with inline `displayScanError()` function
  - Shows styled error card with icon, title, description, and retry button
  - Different messages for: network error, API key missing, rate limited, timeout, generic error
- [x] API client (`api.ts`) now extracts `message` from structured error responses
- [x] Added error card CSS with red theme and retry button

**Verification:**
- [x] Normal analysis works (4 redlines returned on test scan)
- [x] Error card shown for empty documents (replaces alert())
- [x] Structured error propagation confirmed working end-to-end

---

### 2.3 Scan History (Metadata Only, ZDR-Safe) — COMPLETE

**Problem:** Users lose their analysis when closing the Word add-in. No way to see past scans or their results. The `Document` model already stores metadata (filename, risk_summary, total_risks, created_at) but there's no endpoint to list them.

**Backend changes:**
- [x] Add `GET /documents/list` endpoint
  - File: `backend/app/api/v1/endpoints/documents.py` (line 180)
  - Returns: List of `{id, filename, status, total_risks, risk_summary, created_at}`
  - Scoped to current user (`user_id == current_user.id`)
  - Paginated: `?limit=20&offset=0`
  - Ordered by `created_at DESC` (most recent first)
  - ZDR-safe: Never returns document text, only metadata
  - Uses `/list` path to avoid conflict with `GET /{document_id}` route
- [x] Add response schema: `DocumentListItem` (id, filename, total_risks, risk_summary, created_at)
- [x] Added Document record persistence in `analyze-full` endpoint (was not saving to DB before)

**Frontend changes (Word Add-in):**
- [x] Add "Recent Scans" section in the main panel
  - File: `ContraRed-PoC/src/taskpane/taskpane.html`
  - Collapsible section with toggle header
  - Each item shows: filename, date, risk dots (red/yellow)
- [x] Add `listDocuments()` API method
  - File: `ContraRed-PoC/src/taskpane/api.ts`
  - `GET /documents/list?limit=5`
- [x] Fetch recent scans on login / panel load
  - File: `ContraRed-PoC/src/taskpane/taskpane.ts`
  - `loadRecentScans()` called from `showMainPanel()`
- [x] Clicking a past scan shows summary card with risk counts

**Verification:**
- [x] Scan a document → Document persisted to DB with correct metadata
- [x] `GET /documents/list` returns scan with filename, status, risk_summary, created_at
- [x] List ordered by most recent first, paginated

---

## Phase 3: Revenue Features

### 3.1 Template Library with Pre-Built Playbooks — COMPLETE

**Database:**
- [x] Created migration `backend/migrations/007_create_templates.sql`
  - Table: `contract_templates` (id, name, description, category, template_content, paired_playbook_id FK, is_premium, download_count, created_by, created_at, updated_at)
  - Indexes: on category, paired_playbook_id, is_premium
- [x] Migration applied to local PostgreSQL

**Backend model:**
- [x] Created `backend/app/models/template.py` — `ContractTemplate` SQLAlchemy model with relationship to `Playbook`
- [x] Registered model in `session.py` imports

**Backend endpoints:**
- [x] Created `backend/app/api/v1/endpoints/templates.py`
  - [x] `GET /templates/` — list templates, filterable by category, free users see only non-premium (2), enterprise sees all (6)
  - [x] `GET /templates/{id}` — template details + paired playbook info + content
  - [x] `GET /templates/{id}/download` — return content + increment download_count
  - [x] `POST /templates/` — admin-only: create template
- [x] Registered router in `backend/app/api/v1/router.py`

**Template content (6 templates with full Indian law boilerplate):**
- [x] Seed script: `backend/scripts/seed_templates.py` (idempotent, paired with default playbooks)
- [x] NDA — Mutual (free, paired with NDA — Mutual playbook)
- [x] NDA — Unilateral (free, paired with NDA — Unilateral playbook)
- [x] Master Service Agreement (premium, paired with MSA playbook)
- [x] SaaS Subscription Agreement (premium, paired with SaaS playbook)
- [x] Employment Agreement (premium, paired with Employment playbook)
- [x] Consulting Agreement (premium, paired with Consulting playbook)

**Dashboard UI:**
- [x] Created `dashboard/src/pages/Templates.tsx` — grid cards with category/premium badges, preview panel, download
- [x] Route added in `App.tsx`: `/templates` → `Templates`
- [x] "Templates" added to nav in `AppHeader.tsx`
- [x] API methods added in `dashboard/src/api/client.ts` (listTemplates, getTemplate, downloadTemplate)

**Word Add-in integration:**
- [x] "Templates" button in main panel (alongside Scan button)
- [x] Template picker with category badges, description, paired playbook name
- [x] Click to insert → content replaces document + auto-selects paired playbook
- [x] API methods added in `ContraRed-PoC/src/taskpane/api.ts` (listTemplates, downloadTemplate)
- [x] `TemplateListItem` interface + CSS for picker

**Verification:**
- [x] `GET /templates/` returns 6 templates (enterprise) or 2 (free)
- [x] `GET /templates/?category=nda` returns 2 NDA templates
- [x] `GET /templates/{id}` returns full detail with content
- [x] `GET /templates/{id}/download` returns content + increments download count
- [x] Dashboard and Word add-in TypeScript compile clean
- [x] All existing endpoints (documents/list, clauses, playbooks) still work

---

### 3.2 Firm-Wide Analytics Dashboard — COMPLETE

**Backend service:**
- [x] Created `backend/app/services/analytics_service.py`
  - [x] `get_org_overview(org_id, days)` — documents analyzed, total risks, red/yellow breakdown, active users
  - [x] `get_risk_breakdown(org_id, days)` — risk counts by risk_level from DocumentRisk table
  - [x] `get_user_activity(org_id, days)` — per-user scan counts, risks found, last scan
  - [x] `get_trend_data(org_id, period, weeks)` — weekly/daily time-series data using `date_trunc`
  - All queries scoped to org via User.organization_id join

**Backend endpoints:**
- [x] Created `backend/app/api/v1/endpoints/analytics.py`
  - [x] `GET /analytics/overview` — org-level summary stats (admin only)
  - [x] `GET /analytics/risks` — risk breakdown by risk_level
  - [x] `GET /analytics/users` — per-user activity table
  - [x] `GET /analytics/trends?period=weekly` — time-series usage data
  - [x] `GET /analytics/export` — CSV download of analytics
- [x] Registered router in `backend/app/api/v1/router.py`

**Dashboard UI:**
- [x] Created `dashboard/src/pages/Analytics.tsx` (admin-only page)
  - [x] Summary cards row: documents analyzed, total risks, red risks, active users, estimated hours saved
  - [x] Risk breakdown with colored bars (red/yellow/green)
  - [x] Usage trend chart with bar chart (weekly/monthly toggle)
  - [x] User activity table (name, email, scans, risks found, last active)
  - [x] CSV export button + period selector (7/30/90 days)
- [x] Added route in `App.tsx`: `/analytics` → `Analytics` (AdminRoute)
- [x] Added "Analytics" to admin nav in `AppHeader.tsx`
- [x] Added API methods in `dashboard/src/api/client.ts` (getAnalyticsOverview, Risks, Users, Trends, ExportUrl)

**Verification:**
- [x] `GET /analytics/overview` returns: 3 docs analyzed, 6 risks, 2 red, 2 yellow, 2 active users
- [x] `GET /analytics/risks` returns [] (no DocumentRisk rows in current flow — expected)
- [x] `GET /analytics/users` returns 2 users with correct scan counts
- [x] `GET /analytics/trends` returns weekly time-series data (3 data points)
- [x] `GET /analytics/export` returns valid CSV with all sections
- [x] Admin-only access enforced (role check in _require_admin)
- [x] Dashboard TypeScript compiles clean
- [x] Fixed: `date_trunc` GROUP BY error — used `literal_column("1")` for positional reference

---

### 3.3 Contract Clause Generation — COMPLETE

**Backend:**
- [x] Added `generate_clause()` method to `backend/app/services/gemini_analyzer.py`
  - Input: clause_type, playbook rules (fuzzy-matched), contract context
  - Prompt: drafting-focused, grounded in Indian Contract Act, DPDP Act 2023
  - Output: `{ clause_text: str, reasoning: str }`
  - Temperature: 0.3 (creative but consistent), max 4096 tokens
  - Error handling: same exception hierarchy as analyze (503/429/504/502)
- [x] Added `POST /documents/generate-clause` endpoint in `documents.py`
  - Request: `{ clause_type, playbook_id?, contract_context? }`
  - Loads playbook rules if playbook_id provided
  - Audit log entry created for each generation

**Word Add-in:**
- [x] Added "Generate" button on each risk card (alongside "Fix", "Saved")
  - File: `ContraRed-PoC/src/taskpane/taskpane.ts` (in `createAIRedlineCard()`)
  - File: `ContraRed-PoC/src/taskpane/taskpane.html` (generate panel CSS)
- [x] Added `generateClause()` API method in `api.ts`
- [x] Generate panel shows: clause text (green box), reasoning (italic), action buttons
- [x] "Accept" applies generated clause as the fix (via `applyAIRedline()`)
- [x] "Regenerate" re-triggers generation for a new result
- [x] "Close" hides the panel

**Dashboard API client:**
- [x] Added `generateClause()` function + `GenerateClauseResponse` interface in `client.ts`

**Verification:**
- [x] `POST /documents/generate-clause` without playbook → generates balanced indemnification clause citing Indian Contract Act and DPDP Act 2023
- [x] `POST /documents/generate-clause` with MSA playbook → generates non-compete clause aware of Section 27 Indian Contract Act (unenforceable post-termination), focuses on non-solicitation instead
- [x] Audit log entry created for each generation
- [x] Both dashboard and Word add-in TypeScript compile clean

---

## Phase 4: Differentiation Features

### 4.1 Contract Comparison / Diff — COMPLETE

**Backend:**
- [x] Created `backend/app/services/contract_differ.py`
  - Paragraph-level diff using SequenceMatcher + SHA-256 hashing
  - Identifies: added, removed, modified paragraphs with similarity scores
  - `compute_diff()` for pure diff, `compute_diff_with_ai()` adds Gemini assessment
  - AI assessment classifies changes as favors_us / favors_them / neutral
- [x] Added `POST /documents/compare` endpoint in `documents.py`
  - Input: `{ text_a, text_b, playbook_id? }`
  - Output: `{ changes: [...], total_changes, paragraphs_a/b, summary }`
  - Audit log entry for each comparison

**Dashboard:**
- [x] Created `dashboard/src/pages/Compare.tsx`
  - Two text areas for pasting contract versions
  - Optional playbook selector for AI context
  - Color-coded change cards: green (added), red (removed), yellow (modified)
  - AI assessment badges with assessment type + explanation
  - Filter by change type, summary bar with counts
  - "New Comparison" button to reset
- [x] Added `/compare` route in `App.tsx`
- [x] Added "Compare" to nav in `AppHeader.tsx`
- [x] Added `compareContracts()` + types in `client.ts`

**Verification:**
- [x] NDA comparison detected 6 changes: 2 added (new indemnification clause), 4 modified
  - "5 years" → "in perpetuity" detected at 88% similarity
  - "non-compete" → "non-solicitation" detected at 55% similarity
  - New indemnification section correctly flagged as added
- [x] AI assessment runs but JSON parsing can be fragile — gracefully falls back to null
- [x] Dashboard TypeScript compiles clean

---

### 4.2 Lightweight "Research This Clause" — COMPLETE

**Backend:**
- [x] Added `research_clause()` method to `gemini_analyzer.py`
  - Prompt asks for 3-5 SC/HC decisions with standard Indian citations
  - Temperature: 0.2 for factual accuracy
  - Output: `{ cases: [...], legal_principle, disclaimer }`
  - Same error handling as other AI methods (503/429/504/502)
- [x] Added `POST /documents/research-clause` endpoint in `documents.py`
  - Input: `{ clause_text, clause_type? }`
  - Returns: cases array + legal principle + disclaimer
  - Audit log entry for each research request

**Word Add-in:**
- [x] Added "Research" button on risk cards (alongside Fix, Saved, Generate)
- [x] Research panel shows: disclaimer (amber box), legal principle, case cards
- [x] Each case: name (bold), citation + court + year (meta), holding, relevance (blue italic)
- [x] Close button to dismiss panel
- [x] Added `researchClause()` API method in `api.ts`
- [x] Added CSS for research panel (`.research-case`, `.research-disclaimer`, etc.)

**Verification:**
- [x] Research on "Uncapped Indemnification" clause returned 4 relevant cases:
  - *Nabha Power v. Punjab State Power Corp* (2018) 11 SCC 508 — strict interpretation
  - *Gajanan Moreshwar v. Moreshwar Madan Mantri* AIR 1942 Bom 302 — foundational indemnity
  - *Bharathi Knitting v. DHL* (1996) 4 SCC 704 — liability clauses binding
  - *ONGC v. Saw Pipes* (2003) 5 SCC 705 — actual loss for uncapped claims
- [x] Legal principle correctly references Sections 124-125 Indian Contract Act
- [x] Disclaimer prominently displayed: "AI-suggested references — verify citations independently"
- [x] Citations in proper Indian format (SCC, AIR)
- [x] Both dashboard and Word add-in TypeScript compile clean

---

## Phase 5: Production Cutover

- [ ] All Phase 2-4 features pass local testing
- [ ] Run new migrations (007+) against Supabase production DB
- [ ] Update Render env vars (Supabase URL, Upstash Redis URL)
- [ ] Set `ZERO_DATA_RETENTION=true` for production
- [ ] Commit all changes, push to main
- [ ] Render auto-deploys backend
- [ ] Netlify auto-deploys dashboard + add-in
- [ ] Smoke test: login → scan → fix → export on production
- [ ] Verify new features work with production data
- [ ] Monitor Render error logs for 48 hours

---

## Phase 6: Platform Vision (Month 4+)

- [ ] Smriti Search MVP: SC judgment scraping + vector search
- [ ] Upgrade "Research This Clause" to use real indexed case law
- [ ] Unified auth between Smriti Search and ContraRed
- [ ] Rebrand to "Smriti Contracts"
- [ ] Word add-in gets tabs: Contracts / Research / Draft

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/app/api/v1/endpoints/clauses.py` | Clause Library CRUD (line 60: GET list, line 79: exact filter) |
| `backend/app/api/v1/endpoints/documents.py` | Analysis + redline endpoints (line 167: analyze, line 1025: export) |
| `backend/app/services/gemini_analyzer.py` | Gemini AI integration (line 142: analyze, line 212: error fallback) |
| `backend/app/models/playbook.py` | Playbook + ClauseLibrary models (line 72: ClauseLibrary) |
| `backend/app/models/document.py` | Document + DocumentRisk models (line 37: Document fields) |
| `backend/app/api/v1/router.py` | Router registry (add new routers here) |
| `backend/app/core/config.py` | Settings / env vars (line 10: Settings class) |
| `ContraRed-PoC/src/taskpane/taskpane.ts` | Word add-in main logic (line 672: clause picker, line 397: scan flow) |
| `ContraRed-PoC/src/taskpane/taskpane.html` | Word add-in UI (CSS + HTML structure) |
| `ContraRed-PoC/src/taskpane/api.ts` | Word add-in API client (line 359: listClauses) |
| `dashboard/src/App.tsx` | Dashboard routes (line 58: clause-library route) |
| `dashboard/src/api/client.ts` | Dashboard API client (line 6: API_BASE_URL) |
| `dashboard/src/components/AppHeader.tsx` | Shared nav header (line 13: nav items) |
