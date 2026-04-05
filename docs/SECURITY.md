# ContraRed Security Architecture

## Overview

ContraRed handles sensitive legal documents. Security is enforced at every layer: transport, application, database, and AI processing.

## Zero Data Retention (ZDR)

When `ZERO_DATA_RETENTION=true` (default):
- Contract text is **never written to disk or database**
- Text is processed entirely in RAM
- Only metadata is persisted: filename, risk counts, timestamps, document ID
- Audit logs record WHO analyzed WHAT (by filename) but never the content

## Authentication

### JWT Token System

- **Access token**: 30-minute TTL, stored in HttpOnly cookie
- **Refresh token**: 7-day TTL, stored in HttpOnly cookie
- **Token blacklist**: Maintained in Redis (or in-memory fallback)
- **CSRF protection**: Token in cookie, verified via `X-CSRF-Token` header

### Password Security

- **Hashing**: bcrypt with auto-generated salt
- **Account lockout**: 5 failed attempts triggers 15-minute lockout
- **Reset flow**: Time-limited email token via Resend

### Multi-Factor Authentication (MFA)

- **TOTP**: Time-based one-time passwords (RFC 6238)
- **Backup codes**: 8 single-use recovery codes
- **Org enforcement**: Admins can require MFA for all members
- **Attempt limiting**: Stricter limits when Redis unavailable

### SSO (Single Sign-On)

- **Provider**: WorkOS (supports Azure AD, Okta, Google Workspace, SAML 2.0)
- **CSRF state**: HMAC-signed and verified server-side
- **Auto-provisioning**: Users created on first SSO login

## Authorization (RBAC)

5-tier role hierarchy:

| Role | Permissions |
|------|------------|
| `viewer` | Read-only access to shared documents |
| `user` | Analyze documents, use playbooks |
| `editor` | Create/edit playbooks, manage clauses |
| `admin` | Team management, billing, analytics, SSO config |
| `super_admin` | All admin + system configuration |

Default role for new users: `viewer` (least privilege).

## Data Isolation

### Row-Level Security (RLS)

- **48 RLS policies** across 25 tables
- PostgreSQL enforces isolation at the database layer
- `tenant_context` middleware sets `app.current_org_id` on every request
- Even SQL injection cannot access other orgs' data

### Organization Boundaries

- Users belong to exactly one organization
- All queries are scoped to the user's org via RLS
- Cross-org data access is architecturally impossible

## Encryption

### In Transit

- **HTTPS only** in production
- **HSTS**: `max-age=31536000; includeSubDomains; preload`
- **SSL to database**: `ssl=True` (CERT_REQUIRED in production, CERT_NONE only in DEBUG)

### At Rest

- **Field-level encryption**: AES-256 Fernet for sensitive fields
- **ENCRYPTION_KEY**: Required in production (ValueError if missing)
- **Failure mode**: `encrypt_text()` raises RuntimeError on failure (never silently returns plaintext)

## API Security

### Rate Limiting

- SlowAPI rate limiter on all endpoints
- 429 responses include `Retry-After` header

### Request Validation

- **Max body size**: 25MB (middleware enforced)
- **Input validation**: Pydantic v2 models on all endpoints
- **File uploads**: Type-checked (DOCX/PDF only)

### Response Security

- **PII redaction**: SensitiveDataFilter strips credentials from all logs
- **Error sanitization**: Internal errors never exposed to clients
- **Security headers**: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy

### CORS

- Production: Explicit allowlist only
- DEBUG mode: Adds localhost origins
- `CORS_ORIGINS` must be JSON array string in environment

## Audit Trail

### Immutable Audit Logs

Every significant action is logged to `audit_logs` table:

| Field | Description |
|-------|-------------|
| `user_id` | Who performed the action |
| `action` | What they did (analyze, export, view, redline, login, etc.) |
| `resource_type` | What resource (document, playbook, team, etc.) |
| `resource_id` | Specific resource ID |
| `ip_address` | Client IP |
| `user_agent` | Browser/client info |
| `risk_count` | Number of risks found (for analysis actions) |
| `status` | Success/failure |
| `timestamp` | UTC timestamp |
| `hash` | SHA-256 hash chain (each log hashes the previous) |

### Hash Chain Integrity

- Each audit log entry includes a hash of the previous entry
- `GET /audit-logs/verify` validates the entire chain
- Tampered entries break the chain, making manipulation detectable

## AI Security

### Vertex AI (Enterprise)

- **Service account authentication**: Not consumer API keys
- **Data processing**: Google Cloud's enterprise data policies apply
- **No training**: Contract data is NOT used to train models
- **Project isolation**: Dedicated GCP project

### Prompt Injection Protection

- `prompt_sanitizer.py` sanitizes all user input before AI prompts
- Hallucination guard verifies AI outputs against source text
- Confidence scoring flags low-confidence findings

## Billing Security

### Payment Processing

- **Razorpay**: Server-side payment verification (signature validation)
- **Stripe**: Webhook signature verification
- **Idempotency**: `WebhookEvent` table prevents double-processing
- **Plan derivation**: Plan derived from payment notes, not hardcoded

### Subscription Enforcement

- Usage tracked per-scan in `usage_logs` table
- Tier limits enforced server-side before analysis
- Cannot bypass via API — checked in endpoint handlers

## Word Add-in Security

- **HttpOnly cookies**: Tokens not accessible to JavaScript (XSS-safe)
- **sessionStorage**: User profile (not localStorage — clears on tab close)
- **Content Security Policy**: Strict CSP in `netlify.toml`
- **XSS prevention**: `escapeHtml()` on all dynamic content
- **frame-ancestors**: Only Microsoft Office domains allowed

## Security Audit Status

See [SECURITY_AUDIT_REFERENCE.md](SECURITY_AUDIT_REFERENCE.md) for the detailed checklist.

### Completed

- C1-C4: Critical blockers (health endpoint gating, auth on drafting, SSL, hardcoded creds)
- H1-H6, H8-H10: Auth hardening (encryption key validation, encrypt failure handling, default role, MFA token scoping, Razorpay verification, SSO CSRF)

### Pending

- H7: Redis job serialization (deferred — requires architectural change to task queue)

## Incident Response

If a security incident is detected:

1. Check audit log integrity: `GET /audit-logs/verify`
2. Review recent audit entries: `GET /audit-logs?action=login&page_size=100`
3. Rotate secrets: `SECRET_KEY`, `ENCRYPTION_KEY`, database password
4. Invalidate all tokens: Restart the backend (clears in-memory blacklist)
5. If Redis configured: `FLUSHDB` to clear cached sessions
