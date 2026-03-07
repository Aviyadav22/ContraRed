# ContraRed — Comprehensive Project Audit Report
**Date**: 2026-03-07 | **Audited by**: 6 parallel AI agents covering security, features, deployment, data models, frontend quality, and infrastructure

---

## CRITICAL (Must Fix Before Production)

### C1. Default SECRET_KEY Falls Through to Production
**File**: `backend/app/core/config.py:30`
**Issue**: `SECRET_KEY: str = "your-secret-key-change-in-production"` — if env var is unset on Render, all JWTs are forgeable. App should refuse to start with the default key when `DEBUG=False`.

### C2. SSL Certificate Verification Disabled for Supabase
**File**: `backend/app/db/session.py:21-23`
**Issue**: `check_hostname = False` + `verify_mode = CERT_NONE` makes the DB connection vulnerable to MITM attacks. Encrypted but not verified.

### C3. JWT Refresh Token Type Not Validated
**File**: `backend/app/core/security.py:64-75`
**Issue**: `decode_token()` does not check the JWT `type` claim. An access token can be used as a refresh token and vice versa, allowing persistent access from a short-lived token.

### C4. Super Admin Password Exposed in Git
**File**: `backend/migrations/005_create_super_admin.sql:3,12`
**Issue**: Comment reveals password is `admin@123`, bcrypt hash is committed. Anyone reading the repo has super admin access.

### C5. Dashboard CSP connect-src Points to Wrong API URL
**File**: `dashboard/netlify.toml:22`
**Issue**: CSP allows `https://contrared.onrender.com` but actual API is at `https://contrared-api.onrender.com`. **All dashboard API calls are blocked by CSP in production.**

### C6. Token Storage in localStorage (XSS-vulnerable)
**File**: `ContraRed-PoC/src/taskpane/api.ts:144-166`
**Issue**: Access + refresh tokens stored in `localStorage`, accessible to any JS on the same origin. Combined with missing CSP (C8), any XSS can exfiltrate tokens.

### C7. No Token Refresh Implementation
**File**: `ContraRed-PoC/src/taskpane/api.ts:169-197`
**Issue**: `refreshToken` is stored but never used. When access token expires, all API calls fail silently. Users must manually re-login with no indication of why things stopped working.

### C8. Invalid X-Frame-Options + Missing CSP on Word Add-in
**File**: `ContraRed-PoC/netlify.toml:15,19`
**Issue**: `X-Frame-Options: ALLOWALL` is invalid (browsers ignore it). `Access-Control-Allow-Origin: *` on all paths. No Content-Security-Policy header at all.

### C9. Duplicate RiskLevel Enum Causes DB Ambiguity
**Files**: `backend/app/models/document.py:24-27`, `backend/app/models/playbook.py:25-28`
**Issue**: Two separate `RiskLevel` enums with identical values create duplicate PostgreSQL types. Migration/schema issues when one is altered independently.

### C10. AuditLog + ContractTemplate Not Registered in models/__init__.py
**File**: `backend/app/models/__init__.py`
**Issue**: `AuditLog` and `ContractTemplate` not exported from `__init__.py`. While `init_db()` imports modules directly, `__all__` is incomplete and `from app.models import *` will miss them.

### C11. Billing verify_payment Hardcodes PRO Tier
**File**: `backend/app/api/v1/endpoints/billing.py`
**Issue**: Payment verification always sets `subscription_tier = PRO` regardless of what was purchased. Enterprise payments get downgraded.

---

## HIGH (Should Fix Soon)

### H1. OpenAPI/Swagger Docs Exposed in Production
**File**: `backend/main.py:89-91`
**Issue**: `/api/docs`, `/api/redoc`, `/api/openapi.json` publicly accessible, revealing full API surface to attackers.
**Fix**: `docs_url="/api/docs" if settings.DEBUG else None`

### H2. DB Health Check Leaks Internal Error Details
**File**: `backend/main.py:126-136`
**Issue**: `/health/db` is unauthenticated and returns raw exception messages including hostnames and connection details.

### H3. No Rate Limiting on AI Endpoints
**File**: `backend/app/api/v1/endpoints/documents.py`
**Issue**: `/analyze-full`, `/generate-clause`, `/research-clause` have no rate limits. A single user can exhaust the Gemini API quota.

### H4. innerHTML XSS Vector in displayScanError
**File**: `ContraRed-PoC/src/taskpane/taskpane.ts:618-625`
**Issue**: `title` and `description` from error messages injected via innerHTML without escaping. Server-crafted error messages could execute JS.
**Fix**: Wrap with `escapeHtml()`.

### H5. Race Condition: API Call Inside Word.run()
**File**: `ContraRed-PoC/src/taskpane/taskpane.ts:1133-1166`
**Issue**: Network call `api.generateRedlineZDR()` happens inside `Word.run()` context. If API takes too long, the Word context expires causing `GeneralException`.
**Fix**: Fetch OOXML before entering `Word.run()`.

### H6. applyAllRedlines Corrupts Document on Partial Failure
**File**: `ContraRed-PoC/src/taskpane/taskpane.ts:1178-1245`
**Issue**: Sequential fixes modify document text. Later `findTextInDocument` calls may find wrong text. No undo/rollback mechanism. Partial failure leaves document in inconsistent state.

### H7. manifest.xml Still Points to localhost
**File**: `ContraRed-PoC/manifest.xml:14-26`
**Issue**: All URLs point to `https://localhost:3007`. Production manifest not created for `contrared-addin.netlify.app`.

### H8. razorpay Package Missing from requirements.txt
**File**: `backend/requirements.txt`
**Issue**: `billing.py` does `import razorpay` but package not in requirements. All billing endpoints throw `ModuleNotFoundError` on Render.

### H9. Change-Password Has Weaker Validation Than Registration
**File**: `backend/app/api/v1/endpoints/auth.py:303-308`
**Issue**: Registration requires uppercase+lowercase+digit+special char. Change-password only requires 8 chars. Users can downgrade password strength.

### H10. Dashboard Shows [object Object] for AI Error Messages
**File**: `dashboard/src/api/client.ts:155-156`
**Issue**: Error handler does `throw new Error(error.detail)` but AI endpoints return `detail: {message, error_code}`. Shows `[object Object]` instead of readable message.

### H11. Missing Database Indexes on Hot Columns
**Files**: `backend/app/models/document.py:41,50,60,78,84`, `backend/app/models/playbook.py:36`
**Issue**: No indexes on `Document.user_id`, `Document.created_at`, `DocumentRisk.document_id`, `UsageLog.user_id`, `Playbook.created_by`. Full table scans on every user-scoped query.

### H12. Analytics CSV Export URL Lacks Auth Token
**File**: `dashboard/src/api/client.ts:529-532`
**Issue**: `getAnalyticsExportUrl()` returns a bare URL used in `<a href>`. The endpoint requires Bearer auth. Download link is broken — always returns 401.

### H13. Install-ContraRed.bat Points to Wrong API URL
**File**: `dashboard/public/Install-ContraRed.bat:24`
**Issue**: Uses `https://contrared.onrender.com` instead of `https://contrared-api.onrender.com`.

### H14. Source Maps Enabled in Production Build
**File**: `ContraRed-PoC/webpack.config.js:21`
**Issue**: `devtool: "source-map"` is unconditional. Production build exposes full TypeScript source code.
**Fix**: `devtool: dev ? "source-map" : false`

### H15. 27 console.log Statements Leak Debug Info
**File**: `ContraRed-PoC/src/taskpane/taskpane.ts` (27 instances)
**Issue**: Token status, risk counts, analysis details, contract text snippets logged to console. Unprofessional for legal/enterprise product.

### H16. No Request Timeout on API Calls
**File**: `ContraRed-PoC/src/taskpane/api.ts:182-185`
**Issue**: `fetch()` has no `AbortController` timeout. AI analysis can hang indefinitely with no way to cancel.

---

## MEDIUM (Fix Before Scaling)

### M1. RiskLevel Enum Case Mismatch Across Subsystems
**Issue**: Model enums use lowercase (`"red"`), API schemas use uppercase (`"RED"`), service layer has its own enum. Fragile `.lower()`/`.upper()` conversions scattered throughout.

### M2. PlaybookRule Update Loses match_type
**File**: `backend/app/api/v1/endpoints/playbooks.py:468`
**Issue**: `rule.detection_patterns = {"patterns": ...}` drops existing `match_type` from JSONB.

### M3. Templates Endpoint Uses String Comparison Instead of Enum
**File**: `backend/app/api/v1/endpoints/templates.py:77,118,152,177`
**Issue**: `getattr(current_user, 'subscription_tier', 'free') == 'free'` — comparing enum to string. Dead uppercase checks in role validation.

### M4. Templates Page Missing from Dashboard Navigation
**File**: `dashboard/src/components/AppHeader.tsx`
**Issue**: `/templates` route exists but no nav link in `NAV_ITEMS`. Users can't discover the Templates page.

### M5. Duplicate Event Listeners on Every showMainPanel() Call
**File**: `ContraRed-PoC/src/taskpane/taskpane.ts:229-232,323-340`
**Issue**: `loadRecentScans()` and `bindAdminActions()` add new click listeners without removing old ones. Causes flickering and duplicate playbook creation.

### M6. login() and exportReport() Bypass Centralized request() Method
**File**: `ContraRed-PoC/src/taskpane/api.ts:210-229,389-420`
**Issue**: Raw `fetch()` instead of `this.request()`. Misses future enhancements (timeout, retry, token refresh).

### M7. isLoggedIn() Only Checks Token Existence, Not Validity
**File**: `ContraRed-PoC/src/taskpane/api.ts:235-237`
**Issue**: Returns `true` even if token is expired. Combined with no refresh logic, leads to broken state.

### M8. Naive Datetimes Serialized Without UTC Indicator
**Issue**: All backend datetimes serialized as `isoformat()` without `Z` suffix. JavaScript `new Date()` interprets as local time, not UTC.

### M9. No Token Refresh Logic in Dashboard Either
**File**: `dashboard/src/api/client.ts`
**Issue**: Dashboard redirects to `/login` on 401 but has no auto-refresh. Short token expiry means frequent re-logins.

### M10. No Migration Tracking System
**Issue**: Plain SQL files with no version table, no Alembic integration despite it being in requirements.txt. No way to know which migrations have been applied.

### M11. Pool Size (5+10=15) Exactly Equals Supabase Free Tier Limit
**File**: `backend/app/db/session.py:34-35`
**Issue**: Any external connection (dashboard SQL editor, migration script) will be refused.

### M12. package-lock.json Gitignored — Non-deterministic Builds
**File**: `.gitignore:50`
**Issue**: Netlify installs potentially different dependency versions on each build.

### M13. Render Region (Oregon) Far from Supabase Region (Southeast Asia)
**Issue**: 150-250ms latency per DB query due to cross-Pacific round-trips.

### M14. AuditLog.organization_id Missing ForeignKey Constraint
**File**: `backend/app/models/audit_log.py:34`
**Issue**: No referential integrity — can contain UUIDs that don't exist in organizations table.

### M15. Subscription Model Missing updated_at Column
**File**: `backend/app/models/organization.py:48-64`
**Issue**: Only has `created_at`. Loses audit trail of subscription modifications.

### M16. datetime.utcnow() Deprecated in Python 3.12+
**Issue**: Used across all model files. Will generate warnings on Python upgrade.

### M17. .env.example Model Names Mismatch config.py Defaults
**Issue**: `.env.example` suggests `gemini-3-pro-preview`, config.py defaults to `gemini-2.0-flash`.

### M18. render.yaml Missing GEMINI_MODEL Environment Variables
**Issue**: Production will always use `gemini-2.0-flash` defaults regardless of `.env.example` suggestions.

### M19. No Scan Button Debouncing
**File**: `ContraRed-PoC/src/taskpane/taskpane.ts:95`
**Issue**: Rapid double-click before `setScanLoading(true)` can trigger two concurrent AI analyses.

### M20. Dashboard Has No Billing Subscription API Integration
**Issue**: Billing page uses static data. No function to call `GET /billing/subscription`.

### M21. Dashboard Has No DOCX Report Export Function
**Issue**: `POST /documents/export-report` exists but dashboard has no client function for it.

### M22. External Google Fonts CDN Dependency (Privacy Concern)
**File**: `ContraRed-PoC/src/taskpane/taskpane.html:9`
**Issue**: Google receives analytics on every add-in load. Corporate firewalls may block it.

### M23. Playbook.rules JSONB Column Is Dead/Unused
**File**: `backend/app/models/playbook.py:40`
**Issue**: Rules are stored in `playbook_rules` table. The `rules` JSONB column is never read or written.

### M24. Missing Relationships in Models (7 instances)
**Issue**: `Playbook.created_by`, `ClauseLibrary`, `ContractTemplate`, `Document.playbook_id`, `UsageLog.organization_id`, `DocumentRisk.rule_id` — all have FKs but no SQLAlchemy `relationship()`.

### M25. Hardcoded Localhost Fallback URLs Differ Across Clients
**Issue**: Word Add-in falls back to port 8007, Dashboard to port 8000. Inconsistent dev experience.

### M26. Quota Enforcement Not Active
**Issue**: Backend has `FREE_TIER_SCANS = 5` but quota checks in endpoints are incomplete or commented out.

---

## LOW (Nice to Have)

### L1. Browserslist Targets IE 11 (Unnecessary Polyfill Bloat)
### L2. Manifest Uses Placeholder UUID
### L3. Template Content Replaces Entire Document Without Confirmation
### L4. No User Feedback When Highlight/Fix Cannot Find Text
### L5. loadPlaybooks Silently Swallows Errors (Shows "Default Rules" Only)
### L6. Docker-compose Version Key Deprecated
### L7. No Dockerfile for Backend (Limits Portability)
### L8. No Version Ceiling Pins in requirements.txt
### L9. organization_id Missing from Frontend User Interfaces
### L10. match_type Missing from Word Add-in PlaybookRule Interface
### L11. No Frontend changePassword() Function
### L12. Playbook created_at/updated_at Not Exposed in API Response
### L13. Mixed UUID Handling (UUID path params vs str body fields)
### L14. Dead Green Risk Badge (Always Shows "0")
### L15. Unused _documentId Parameter in createAIRedlineCard
### L16. requires_ai_verification/verification_prompt Not Exposed in API
### L17. *.txt Broadly Gitignored
### L18. No ANALYSIS_MODE Validation (Accepts Any String)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 11 |
| HIGH | 16 |
| MEDIUM | 26 |
| LOW | 18 |
| **TOTAL** | **71** |

## Recommended Fix Order

**Phase 1 — Security (C1-C8, H1-H4, H14-H15)**: Fix auth, tokens, CSP, XSS, exposed APIs
**Phase 2 — Production Blockers (C5, C11, H7-H8, H10, H12-H13)**: Fix wrong URLs, missing deps, broken features
**Phase 3 — Data Integrity (C9-C10, H5-H6, H11, M1-M2)**: Fix enums, indexes, race conditions
**Phase 4 — Quality of Life (M3-M26)**: Templates, debouncing, migrations, tokens refresh
**Phase 5 — Polish (L1-L18)**: Dead code cleanup, minor type fixes
