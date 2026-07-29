# ContraRed Security and Data Protection Summary

Prepared for client security review
Date: May 25, 2026
Scope reviewed: backend API, Word add-in, dashboard, deployment notes, migrations, privacy/terms pages, and security documentation.

## Executive Positioning

ContraRed is designed for legal document review, where confidentiality, privilege protection, access control, and auditability matter. The safest way to present the system is:

> ContraRed uses zero data retention processing for core contract review, encrypts sensitive stored fields, keeps authentication tokens out of browser JavaScript, enforces organization-level access controls, and routes AI processing through enterprise-grade model APIs where contractual data retention controls are available.

Do not describe this as "ZDR encryption." Zero data retention is a processing and retention control. Encryption is a separate control for data in transit and data at rest.

## Security Measures Currently Implemented

### 1. Zero Data Retention application mode

The backend defaults `ZERO_DATA_RETENTION=true`.

For the core `/documents/analyze` workflow:

- Full contract text is processed in memory.
- Full contract text is not written to the database.
- Persisted records are limited to metadata such as filename, document ID, risk counts, summary counts, content hash, word count, timestamps, and processing duration.
- Audit logs store who performed the analysis, on which file name, when, and the result, but are designed not to store contract content.
- The Word add-in receives findings for immediate user review and redlining, rather than relying on persisted full document content.

Internal caveat before making a strict enterprise ZDR claim: batch analysis currently persists clause-level findings in `DocumentRisk` for full batch reports. For a lawyer client requiring strict ZDR across all modes, disable or remediate batch persistence, purge old `DocumentRisk` rows, and document which features are ZDR-safe.

### 2. AI provider controls

Current backend implementation uses Google Gemini through Vertex AI, not the consumer/public Gemini API path. `backend/app/core/vertex_client.py` initializes the Google GenAI SDK in `vertexai=True` mode and refuses operation if `VERTEX_PROJECT_ID` is missing.

Security-relevant controls in the current AI path:

- Service account authentication instead of browser-side API keys.
- Google Cloud project isolation.
- IAM-based access control.
- Vertex AI audit logging availability through Google Cloud audit logs.
- Regional/location configuration through `VERTEX_LOCATION`.
- No contract text in client-side API keys or static frontend code.

Provider positioning:

- Vertex AI is the preferred route for lawyer and enterprise clients.
- Public Gemini API or AI Studio should be described as a pilot/developer API lane only, unless governed by a paid/enterprise arrangement and documented data processing terms.
- If a client signs a proper enterprise contract, the service can be deployed under enterprise data retention terms, including Google Cloud/Vertex AI zero data retention configuration steps where available.

### 3. Authentication and session security

The app implements:

- JWT access tokens with a 30-minute default TTL.
- Refresh tokens with a 7-day default TTL.
- Tokens stored in HttpOnly cookies, not localStorage.
- Secure cookies with `SameSite=None` for cross-origin Office add-in use.
- Double-submit CSRF protection through a non-HttpOnly CSRF cookie and `X-CSRF-Token` header.
- Refresh token rotation and revocation.
- Logout and password-change token revocation through Redis when configured, with in-memory fallback.
- Concurrent session limiting when Redis is available.
- IP anomaly logging for new login IPs when Redis is available.

Production recommendation: configure Redis. Without Redis, blacklist/session controls work only within a single backend process and should be described as degraded.

### 4. Password, MFA, and SSO controls

Implemented controls:

- Passwords are hashed with bcrypt and unique salts.
- Account lockout after repeated failed login attempts.
- Password reset uses time-limited reset tokens and avoids account enumeration.
- TOTP MFA is supported.
- Backup codes are generated and stored as bcrypt hashes.
- Organization-level MFA enforcement is supported.
- WorkOS-based SSO supports Azure AD, Okta, Google Workspace, and SAML 2.0 providers.
- SSO uses HMAC-signed state for CSRF protection.

Client presentation: position MFA and SSO as enterprise controls available for firm-wide deployments.

### 5. Role-based access control and tenant isolation

The app implements a five-tier role model:

| Role | Typical use |
| --- | --- |
| `viewer` | Read-only users, client-side reviewers |
| `reviewer` | Legal reviewers and associates |
| `manager` | Team leads and playbook managers |
| `admin` | Organization administrators |
| `super_admin` | Platform administrators |

Granular permissions cover documents, playbooks, clauses, templates, team management, billing, analytics, audit logs, settings, SSO, and API keys.

The database uses PostgreSQL Row-Level Security policies for tenant isolation. The backend sets `app.current_user_id`, `app.current_org_id`, and `app.is_super_admin` session variables before database access, so organization boundaries are enforced at the database layer.

Internal caveat: some newer DPDP/compliance migration policies reference `app.current_is_super_admin` while the middleware sets `app.is_super_admin`. Core document/playbook policies use `app.is_super_admin`; newer policies should be normalized before enterprise handoff.

### 6. Encryption

Transport and hosting:

- Production traffic is intended to run over HTTPS.
- Backend sets HSTS headers.
- Dashboard and Word add-in Netlify configs include HSTS and CSP headers.
- CORS is explicit in production and limited to configured origins.

Application and database:

- Sensitive fields use Fernet field-level encryption, which is built on AES-128-CBC plus HMAC in the Fernet specification and commonly described in the codebase as AES-256/Fernet because of key size. For external materials, use the safer wording: "Fernet authenticated field-level encryption using a production-only encryption key."
- `ENCRYPTION_KEY` is required in production.
- MFA secrets are encrypted before storage.
- Backup codes are bcrypt-hashed.
- Passwords are bcrypt-hashed.

Internal caveat: the Supabase connection path currently disables certificate verification for Supabase SSL contexts in code. Before a formal enterprise deployment, tighten database TLS certificate verification or use a deployment path where certificate validation is enforced.

### 7. API and web application security

Implemented controls:

- Pydantic request validation on API inputs.
- Contract text length limits.
- Request body size middleware with a 25 MB limit.
- Upload type checks for document workflows.
- Rate limiting through SlowAPI on authentication and AI-heavy endpoints.
- Security headers on the backend: CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, no-store cache control, and cross-domain policy restrictions.
- Production CORS allowlist.
- Opaque production error responses.
- Request IDs for traceability.

The Word add-in and dashboard also include:

- Auth tokens in HttpOnly cookies.
- Non-sensitive user profile in sessionStorage.
- Migration away from localStorage for sensitive session state.
- XSS escaping for dynamic add-in HTML rendering.
- CSP and frame-ancestor controls in Netlify config.
- Add-in iframe allowance limited to Microsoft Office domains.

### 8. Logging, monitoring, and auditability

Implemented controls:

- SensitiveDataFilter redacts emails, bearer tokens, JWTs, likely secrets, and long quoted strings from logs.
- Sentry integration is optional and configured to redact request bodies and user emails before events are sent.
- Audit logs record user, action, resource type/name, IP, user agent, status, risk count, timestamp, and hash-chain fields.
- Audit details are JSON-validated, length-limited, and scrubbed for forbidden keys such as `contract_text`, `document_text`, `password`, `token`, and `secret`.
- Audit logs use SHA-256 hash chaining.
- A database trigger prevents audit log update/delete.
- `/audit-logs/verify` verifies hash-chain integrity for admin users.

Client presentation: describe this as tamper-evident audit logging, not absolute immutability against database superuser compromise.

### 9. Prompt-injection and AI-output controls

Implemented controls:

- `prompt_sanitizer.py` strips control characters and neutralizes common prompt-injection phrases before AI prompt construction.
- Analysis uses a staged pipeline rather than a single unstructured AI call.
- AI output is parsed into structured schemas.
- `HallucinationGuard` verifies quoted source text against the contract using exact, normalized, and fuzzy matching.
- Low-confidence or unverified findings are labeled and can be rejected or downgraded.
- Confidence scores and verification status are returned to the UI.
- The product includes lawyer-facing warnings to verify low-confidence or AI-suggested legal references.

Client presentation: describe AI as an assistive legal review system with source verification and human review, not as autonomous legal advice.

### 10. Privacy, consent, and DPDP workflows

Implemented controls:

- Consent purposes are versioned.
- Users can grant/withdraw consent per purpose.
- Consent enforcement middleware blocks protected processing endpoints when required consent is missing.
- Consent events are hash-chained and protected by immutability triggers.
- ISO 27560-style consent receipts are modeled.
- Privacy settings UI allows users to manage processing preferences.
- Data rights workflows exist for access, correction, erasure, nomination, and grievance redressal.
- Rights requests and grievances include deadline tracking.
- Cross-border transfer tracking is modeled.
- DPDP compliance layers and a DPDP command center are present.

Internal caveat: consent middleware currently fails open if the consent check errors. For strict legal-sector deployment, fail-closed behavior should be considered for AI processing endpoints.

### 11. Billing and quota integrity

Implemented controls:

- Usage quotas are enforced server-side.
- Subscription tier limits cannot be bypassed solely through frontend changes.
- Razorpay and Stripe signature verification are implemented.
- Webhook idempotency prevents double processing.

## AI Provider and Data Retention Language for Clients

Use this wording:

> ContraRed's preferred enterprise deployment routes Gemini model calls through Google Cloud Vertex AI or another contracted enterprise model API. Under enterprise terms, we configure the model provider and our application to minimize or eliminate retention of customer content where the provider supports it. For core review workflows, ContraRed itself does not persist the full contract text; it stores only metadata and audit records needed to operate the service.

For Gemini:

- Current code path: Gemini through Vertex AI.
- Vertex AI documentation states Google will not use customer data to train or fine-tune AI/ML models without prior permission or instruction.
- Vertex AI zero data retention requires configuration discipline, including disabling data caching where required, avoiding Search/Maps grounding when ZDR is required, avoiding Live API session resumption, and requesting an abuse-monitoring exception if the customer is in scope for prompt logging.
- Gemini API unpaid services should not receive sensitive or confidential legal content. Google's current Gemini API terms state that unpaid services may be used to improve Google products and may involve human review.
- Gemini API paid services state that prompts and responses are not used to improve products, but prompts and responses may still be logged for a limited period for prohibited-use detection and legal/regulatory disclosures.

For OpenAI/Azure fallback:

- OpenAI API business data is not used for training by default, and eligible customers may request Zero Data Retention after approval.
- Azure OpenAI/Foundry model data is not available to OpenAI or other model providers and is not used to train foundation models without permission; stored data is encrypted at rest in the customer's Azure geography where applicable.

## How to Present the Security Package Documentarily

For a lawyer or law firm client, prepare these artifacts:

1. Security Architecture Memo
   Include deployment diagram, data flow, AI provider path, and where contract text is processed.

2. Data Retention and ZDR Addendum
   State which workflows are ZDR-safe, what metadata is retained, how long logs are retained, and which features are excluded unless configured.

3. AI Provider Disclosure
   List Vertex AI, Azure OpenAI if enabled, and any public Gemini API use. Include whether data is used for training, abuse monitoring retention, geography, and contractual path.

4. Subprocessor List
   Include Render, Netlify, Supabase, Google Cloud Vertex AI, Azure OpenAI if enabled, WorkOS, Sentry if enabled, Resend, Razorpay, Stripe, and Redis/Upstash if enabled.

5. Access Control Matrix
   Map viewer, reviewer, manager, admin, and super_admin to permissions.

6. Audit Log and Evidence Policy
   Explain tamper-evident hash chaining, admin verification endpoint, and what is logged.

7. Incident Response Procedure
   Include secret rotation, token invalidation, audit-chain verification, breach notification contacts, and escalation process.

8. Data Rights and Consent SOP
   Explain consent collection, withdrawal, access/correction/erasure requests, nomination, grievance handling, and DPDP timelines.

9. Secure Deployment Checklist
   Include production environment variables, CORS allowlist, Redis, valid encryption key, TLS certificate verification, Sentry redaction, and provider ZDR settings.

10. Security Verification Appendix
   Include dependency audit results, penetration-test status, vulnerability remediation date, and test evidence.

## Internal Pre-Client Remediation Notes

These items should be handled before telling a legal client the deployment is enterprise-ready:

| Item | Why it matters | Recommended action |
| --- | --- | --- |
| Batch analysis stores clause-level findings | Strict ZDR claim is not true across all workflows | Disable batch reports for ZDR clients or change persistence to metadata-only |
| Redis not configured in deployment docs | Token blacklist/session limits degrade to process-local memory | Add production Redis and document it |
| Dependency audit findings | `cryptography`, dashboard, and add-in audits show high-severity issues | Upgrade dependencies and re-run audit |
| Database TLS certificate verification | Supabase path disables cert verification | Enforce verified TLS or use direct verified connection |
| Privacy policy wording | Current add-in privacy page says contract text is encrypted at rest and analysis results retained 90 days | Align policy with ZDR mode and actual retention behavior |
| Consent fail-open behavior | AI processing may continue if consent service errors | Consider fail-closed for legal clients |
| Super-admin RLS variable mismatch in newer migrations | Some policies may not honor super_admin bypass consistently | Normalize to `app.is_super_admin` |
| Provider ZDR configuration evidence | Contractual ZDR needs proof, not just intent | Keep screenshots/exported settings for Vertex AI cache, abuse-monitoring exception, and grounding/session exclusions |

## Recommended Client-Facing One-Page Summary

ContraRed protects legal documents through layered controls:

- Contract text is processed transiently in core review mode and is not stored as full document text.
- Authentication uses HttpOnly cookies, CSRF protection, password hashing, MFA, and optional SSO.
- Role-based permissions and PostgreSQL Row-Level Security isolate each organization.
- Sensitive stored fields are encrypted, and passwords/backup codes are hashed.
- API traffic uses HTTPS, HSTS, CORS allowlists, security headers, rate limiting, and request validation.
- Logs and error monitoring redact sensitive information and avoid storing contract text.
- Audit logs are tamper-evident through SHA-256 hash chaining and database immutability triggers.
- AI outputs are checked against source contract text with hallucination guards and confidence scoring.
- Enterprise deployments can use Vertex AI or other contracted enterprise APIs with documented data retention controls.
- DPDP consent, rights, grievance, and compliance workflows are built into the platform.

## Source Links

- Google Cloud Vertex AI zero data retention and training restriction: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/vertex-ai-zero-data-retention
- Gemini API Additional Terms of Service, current as reviewed: https://ai.google.dev/gemini-api/terms
- OpenAI enterprise privacy and API retention: https://openai.com/enterprise-privacy/
- OpenAI API data controls and ZDR: https://developers.openai.com/api/docs/guides/your-data
- Microsoft Azure OpenAI/Foundry data privacy: https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy
- Google Cloud default encryption at rest: https://cloud.google.com/docs/security/encryption/default-encryption
- Vertex AI IAM access control: https://cloud.google.com/vertex-ai/docs/general/access-control
- Vertex AI audit logging: https://cloud.google.com/vertex-ai/docs/general/audit-logging
