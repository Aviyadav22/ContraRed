# ContraRed Production-Readiness Audit Report

**Date:** 2026-03-25
**Auditor:** Claude Opus 4.6 (automated deep audit)
**Scope:** Full-stack — Backend, Dashboard, Word Add-in, CI/CD, Database, Dependencies
**Branch:** `contrared-refactor`

---

## Executive Summary

ContraRed demonstrates **strong security foundations** — HttpOnly cookies, CSRF double-submit, rate limiting on all endpoints, RLS, PII log redaction, security headers (CSP/HSTS), and a CI pipeline with pip-audit + Trivy + npm audit. The architecture is production-capable.

However, **12 findings** need attention before go-live, including **2 critical** and **4 high** severity issues.

| Severity | Count |
|----------|-------|
| CRITICAL | 2     |
| HIGH     | 4     |
| MEDIUM   | 4     |
| LOW      | 2     |

---

## CRITICAL Findings

### C1. Super Admin Password Hash Committed to Git
**File:** `backend/migrations/005_create_super_admin.sql:11`
**Issue:** The bcrypt hash `$2b$12$VmlJ6IfllgkK93y...` for the super admin account (`aviyadav.official@gmail.com`) is hardcoded in a migration file checked into git. While bcrypt is one-way, the original password was weak enough to hash — and if it's reused anywhere or brute-forceable, this is a direct admin account compromise. The `ON CONFLICT` clause also resets the password hash on every migration run, preventing password changes from persisting.
**Risk:** Credential exposure, admin account takeover
**Fix:**
1. Remove the hardcoded hash from the migration file
2. Use an environment variable or one-time setup script to create the super admin
3. Remove the `ON CONFLICT DO UPDATE SET password_hash = ...` clause — it overwrites password changes
4. Rotate the super admin password immediately
5. Consider `git filter-branch` or BFG to scrub the hash from git history

### C2. Dev Seed Data May Run in Production
**File:** `backend/migrations/seed_dev_data.sql`
**Issue:** The seed data file creates a demo admin user (`admin@contrared.com`) with a known password hash and predictable UUID (`b0000000-0000-0000-0000-000000000001`). While it uses `ON CONFLICT DO NOTHING`, if this migration is applied to production (via the consolidated migration or manually), it creates a backdoor account.
**Risk:** Backdoor admin account in production
**Fix:**
1. Add a guard: `DO $$ BEGIN IF current_setting('app.environment', true) = 'production' THEN RAISE EXCEPTION 'Seed data cannot run in production'; END IF; END $$;`
2. Or remove seed_dev_data.sql from consolidated migrations entirely
3. Ensure CONSOLIDATED_ALL_MIGRATIONS.sql does NOT include seed data

---

## HIGH Findings

### H1. CSRF Bypass When No Cookie Is Set
**File:** `backend/app/core/cookies.py:104-106`
**Issue:** The `validate_csrf()` function bypasses CSRF checks when `csrf_cookie` is not set AND the request has a `Bearer` Authorization header. However, in `auth.py:254-259`, CSRF is only validated when the token comes from a cookie (not header). This creates an edge case: if an attacker can set a forged `access_token` cookie without a `csrf_token` cookie, and includes any `Authorization: Bearer X` header, the CSRF check passes. The actual auth still validates the JWT signature, but the CSRF logic has a gap.
**Risk:** Potential CSRF bypass in cookie-based auth flows
**Fix:** In `validate_csrf()`, when no `csrf_cookie` is present, verify that the *actual* token being used came from the Authorization header (not just that the header exists). The current code checks `auth_header.startswith("Bearer ")` but doesn't verify it's the token source.

### H2. Email Enumeration on Registration
**File:** `backend/app/api/v1/endpoints/auth.py:300-307`
**Issue:** The registration endpoint returns `"Email already registered"` when a duplicate email is submitted. This allows attackers to enumerate valid email addresses. A comment acknowledges this as a known trade-off, but for a B2B legal SaaS product handling sensitive contracts, this should be tightened.
**Risk:** User enumeration for targeted phishing attacks against legal professionals
**Fix:** Return a generic message like `"If this email is not already registered, you will receive a verification email."` and send a notification email to existing users when someone tries to re-register their email.

### H3. In-Memory MFA Attempt Tracking Not Shared Across Workers
**File:** `backend/app/api/v1/endpoints/auth.py:67-70`
**Issue:** `_mfa_attempts` is an in-memory dict. On Render with multiple uvicorn workers (or if scaled horizontally), each worker has its own dict. An attacker can retry MFA codes across workers, multiplying their attempts by the number of workers. The code tries Redis first but falls back to in-memory without warning.
**Risk:** MFA brute-force amplification (5 attempts × N workers)
**Fix:**
1. Log a WARNING at startup when Redis is unavailable: "MFA rate limiting degraded — in-memory only, not shared across workers"
2. Configure Redis (strongly recommended for production)
3. Or reduce `_MFA_MAX_ATTEMPTS` to 3 when Redis is unavailable

### H4. Stripe Checkout Session User Verification Missing
**File:** `backend/app/api/v1/endpoints/billing.py:632-636`
**Issue:** When verifying a Stripe checkout session, the `user_id` in `session.metadata` is read but never compared to `current_user.id`. A user could potentially verify another user's checkout session and get their plan upgrade applied to themselves.
**Risk:** Subscription fraud — user A pays, user B gets the plan
**Fix:** Add: `if session.metadata.get("user_id") != str(current_user.id): raise HTTPException(403, "Session does not belong to this user")`

---

## MEDIUM Findings

### M1. Package Lock Files Not Gitignored but Inconsistently Tracked
**File:** `.gitignore` (missing lock file entries)
**Issue:** `package-lock.json` files appear as untracked (`??`) in git status for all 3 Node projects. They should either be consistently committed (for reproducible builds) or consistently ignored. Currently, CI uses `npm install` (not `npm ci`) for the dashboard, which doesn't enforce the lock file.
**Risk:** Non-reproducible builds, potential supply chain attack vector
**Fix:**
1. Commit all `package-lock.json` files
2. Change `npm install` to `npm ci` in CI for dashboard-build step (line 115)
3. Or explicitly add `**/package-lock.json` to `.gitignore` if you don't want them

### M2. npm audit Failures Don't Block CI
**File:** `.github/workflows/ci.yml:61,66`
**Issue:** Both `npm audit` commands use `|| true`, meaning they never fail the CI pipeline regardless of vulnerabilities found. The `pip-audit` and Trivy scans do block on HIGH/CRITICAL, but npm vulnerabilities are silently accepted.
**Risk:** Known JS vulnerabilities shipped to production
**Fix:** Remove `|| true` or change to `npm audit --audit-level=critical` (block on critical only)

### M3. No Rate Limiting on Playbook/Team Write Endpoints
**File:** `backend/app/api/v1/endpoints/playbooks.py`
**Issue:** While auth, billing, documents, and SSO endpoints all have `@limiter.limit()` decorators, playbook CRUD endpoints (create, update, delete) have no rate limiting. An authenticated attacker could create thousands of playbooks to abuse storage.
**Risk:** Resource exhaustion via authenticated user
**Fix:** Add `@limiter.limit("30/minute")` to playbook create/update/delete endpoints

### M4. `isAdmin()` Check Based on localStorage (Dashboard)
**File:** `dashboard/src/api/client.ts:142-145`
**Issue:** The `isAdmin()` function reads role from `localStorage` which can be trivially modified by the user. If any admin-only UI features render sensitive data fetched client-side based on this check (without backend validation), information could leak.
**Risk:** Client-side authorization bypass (UI-only — backend still validates via `require_admin`/`require_permission`)
**Fix:** Acceptable IF all admin-only data/actions are gated by backend middleware. Verify this is the case for Analytics and any admin panels.

---

## LOW Findings

### L1. Blanket `*.txt` in Gitignore
**File:** `.gitignore:76`
**Issue:** `*.txt` is gitignored with exceptions only for specific .md files and requirements.txt. Any other `.txt` files (LICENSE.txt, CHANGELOG.txt) will be silently excluded.
**Risk:** Accidentally excluded files
**Fix:** Use more specific patterns like `*_output.txt`, `*_results.txt`, `*_debug*.txt`

### L2. Word Add-in Stores User Object in localStorage
**File:** `ContraRed-PoC/src/taskpane/api.ts:180-191`
**Issue:** The user object (email, name, role, subscription tier) is stored in `localStorage` which persists across sessions and is accessible to any JS in the same origin. Tokens are properly in HttpOnly cookies (good), but user profile PII in localStorage could leak if XSS is found.
**Risk:** PII exposure if XSS occurs (mitigated by strong CSP)
**Fix:** Consider `sessionStorage` instead, or clear localStorage on add-in unload.

---

## What's Done Well (Security Strengths)

| Area | Implementation |
|------|---------------|
| **Auth tokens** | HttpOnly + Secure + SameSite=None cookies (not localStorage) |
| **CSRF** | Double-submit cookie pattern with X-CSRF-Token header validation |
| **Password security** | bcrypt hashing, strong policy (8+ chars, upper/lower/digit/special), lockout after 5 failures |
| **Rate limiting** | slowapi on all auth, billing, document, and SSO endpoints |
| **SQL injection** | All queries use SQLAlchemy ORM/parameterized — zero raw f-string SQL |
| **XSS prevention** | No `dangerouslySetInnerHTML` in dashboard, CSP headers on all frontends |
| **Security headers** | CSP, HSTS (2yr + preload), X-Frame-Options, X-Content-Type-Options, Permissions-Policy, Referrer-Policy |
| **Secret management** | SECRET_KEY and ENCRYPTION_KEY validated at startup, refuse to start with defaults in production |
| **Log sanitization** | SensitiveDataFilter redacts emails, JWTs, API keys, contract text from ALL logs |
| **Error handling** | Global exception handler strips PII, generic errors in production, Sentry PII scrubbing |
| **MFA** | Full TOTP with backup codes, per-token attempt limiting, org-level enforcement |
| **Token revocation** | Redis blacklist with in-memory fallback, concurrent session limiting (max 5), refresh rotation |
| **Audit trail** | All auth events logged with IP, user-agent, and details |
| **Tenant isolation** | PostgreSQL RLS with session-level context vars |
| **IDOR protection** | Ownership checks on playbooks (`_get_playbook_or_403`), invoices scoped to `current_user.id` |
| **Zero Data Retention** | Document text processed in RAM only, never persisted |
| **CI/CD security** | pip-audit, Trivy (blocks HIGH/CRITICAL), npm audit, CodeQL SARIF upload |
| **Webhook security** | HMAC signature verification with `hmac.compare_digest` (timing-safe), idempotency via `WebhookEvent` table with `FOR UPDATE` locks |
| **API docs** | Swagger/ReDoc disabled in production (`docs_url=None`) |
| **Body size limits** | 25MB max request body via middleware |
| **IP anomaly detection** | New login IPs flagged and logged |
| **Source maps** | Disabled in production (`sourcemap: false`) |
| **Proxy trust** | `TRUSTED_PROXY_HOSTS` configurable, X-Forwarded-For only trusted from known proxies |
| **Input validation** | Pydantic models with min/max length, strict enums, password complexity validation |
| **Encryption at rest** | AES-256 Fernet encryption for stored clause text (`ENCRYPTION_KEY` required in prod) |

---

## Recommended Fix Priority

| Priority | Finding | Effort | Impact |
|----------|---------|--------|--------|
| 1 (NOW) | C1 — Rotate super admin pwd, remove hash | 30 min | Prevents admin takeover |
| 2 (NOW) | C2 — Guard seed data from production | 15 min | Prevents backdoor |
| 3 (NOW) | H4 — Stripe user_id verification | 5 min | Prevents billing fraud |
| 4 (Before launch) | H3 — Configure Redis on Render | 30 min | Enables MFA protection |
| 5 (Before launch) | H1 — Tighten CSRF validation | 20 min | Closes CSRF edge case |
| 6 (Before launch) | M1 — Lock files + `npm ci` | 15 min | Reproducible builds |
| 7 (Before launch) | M2 — npm audit blocks CI | 5 min | Catches JS vulns |
| 8 (Before launch) | M3 — Rate limit playbook endpoints | 10 min | Prevents abuse |
| 9 (Post-launch) | H2 — Fix email enumeration | 1 hr | Prevents user enumeration |
| 10 (Post-launch) | M4 — Verify admin UI gating | 30 min | Verification only |
| 11 (Post-launch) | L1, L2 — Minor fixes | 15 min | Polish |

---

## Pre-Production Checklist

- [ ] **C1:** Rotate super admin password and remove hardcoded hash from migration
- [ ] **C2:** Verify seed_dev_data.sql is NOT in production migrations
- [ ] **H4:** Add `user_id` verification to Stripe checkout verification
- [ ] **H3:** Configure Redis (REDIS_URL) on Render — [Upstash free tier](https://upstash.com)
- [ ] Add `GEMINI_API_KEY` to Render env vars (AI features currently disabled)
- [ ] **M1:** Commit package-lock.json files and use `npm ci` in CI
- [ ] **M2:** Remove `|| true` from npm audit in CI
- [ ] **M3:** Add rate limiting to playbook CRUD endpoints
- [ ] Verify `CORS_ORIGINS` on Render matches only production domains
- [ ] Verify `ENCRYPTION_KEY` is set on Render
- [ ] Set `SENTRY_ENVIRONMENT=production` and `SENTRY_DSN` on Render
- [ ] Run `pip-audit` locally and fix any HIGH/CRITICAL findings
- [ ] Test webhook signature verification end-to-end (Razorpay + Stripe)
- [ ] Perform manual penetration test on auth flows
