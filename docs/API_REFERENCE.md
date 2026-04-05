# ContraRed API Reference

Base URL: `https://contrared-api.onrender.com/api/v1`
Local: `http://localhost:8000/api/v1`

All endpoints require `Authorization: Bearer <token>` unless marked PUBLIC.

## Health Checks (PUBLIC)

```
GET /health              Basic status + version
GET /health/db           Database connectivity
GET /health/deep         Full system health (DB, Redis, AI) with latencies
GET /health/ai           AI connectivity (DEBUG mode only)
```

## Authentication

```
POST /auth/register          Register new user
  Body: { email, password, name }
  Returns: { id, email, name, role }

POST /auth/login             Login (sets HttpOnly cookies)
  Body: form-urlencoded { username, password }
  Returns: { user } or { mfa_required: true, mfa_token }

POST /auth/mfa/challenge     Complete MFA login
  Body: { mfa_token, code }

POST /auth/refresh           Refresh access token (reads cookie)
GET  /auth/me                Get current user profile
POST /auth/logout            Logout (blacklists token)
POST /auth/change-password   Change password
POST /auth/forgot-password   Send password reset email
POST /auth/reset-password    Reset password with token

POST /auth/mfa/setup         Setup TOTP (returns QR URI + backup codes)
POST /auth/mfa/verify        Verify TOTP code
POST /auth/mfa/disable       Disable MFA
POST /auth/mfa/backup-codes  Regenerate backup codes
```

## Documents & Analysis

```
POST /documents/analyze          Full contract analysis (sync, <240s)
  Body: { text, playbook_id?, filename?, compliance_layers?[] }
  Returns: { document_id, risks[], executive_summary[], risk_summary, tokens_used }

POST /documents/analyze-async    Async analysis (returns job_id)
GET  /documents/jobs/{job_id}    Get async job status + results

POST /documents/analyze-clause   Single clause analysis
  Body: { clause_text, playbook_id? }

POST /documents/analyze-file     Upload DOCX/PDF for analysis
  Body: multipart/form-data { file, playbook_id? }

POST /documents/analyze-full     Full analysis with cross-refs
POST /documents/batch-analyze    Batch upload multiple documents

GET  /documents/list             List analyzed documents (paginated)
GET  /documents/{id}             Get document details
POST /documents/{id}/versions    Create new version
GET  /documents/{id}/versions    List versions
GET  /documents/{id}/diff        Compare two versions

POST /documents/generate-clause  AI-generate custom clause
POST /documents/generate-fix     AI-suggest fix for a risk
POST /documents/research-clause  AI research clause implications
POST /documents/compare          Compare two documents
POST /documents/summarize        Contract summary
POST /documents/redline          Apply redlines (OOXML generation)
POST /documents/export-report    Export PDF report
POST /documents/export-issues    Export issues to CSV

GET  /documents/compliance-layers       List compliance layers
GET  /documents/compliance-layers/{code} Get layer details
GET  /documents/{id}/verification-summary Verification stats
GET  /documents/manifest          Word add-in manifest XML
GET  /documents/installer         Word add-in installer
```

## Contract Drafting

```
GET  /drafting/intake-schema     Get dynamic form schema for contract type
  Query: ?contract_type=nda_mutual

POST /drafting/generate          Generate contract draft
  Body: {
    contract_type: "nda_mutual" | "saas" | "msa" | "employment",
    jurisdiction: "US-DE" | "IN" | "GB" | "SG",
    party_a: { name, address, ... },
    party_b: { name, address, ... },
    parameters: { ... contract-type-specific fields }
  }
  Returns: { draft_id, sections[], quality_report, annotations[] }

GET  /drafting/download/{draft_id}      Download as DOCX
GET  /drafting/addin-payload/{draft_id} Get draft for Word add-in
GET  /drafting/playbooks                List drafting playbooks
```

## Playbooks

```
GET    /playbooks/                     List user playbooks
POST   /playbooks/                     Create playbook
  Body: { name, description, category, is_public }

GET    /playbooks/{id}                 Get playbook with rules
PUT    /playbooks/{id}                 Update playbook
DELETE /playbooks/{id}                 Delete playbook

POST   /playbooks/{id}/rules          Add rule
PUT    /playbooks/{id}/rules/{rid}    Update rule
DELETE /playbooks/{id}/rules/{rid}    Delete rule
POST   /playbooks/{id}/rules/reorder  Reorder rules
  Body: { rule_ids: [uuid, ...] }

GET    /playbooks/{id}/rules/{rid}/tiers  Get negotiation tiers
PUT    /playbooks/{id}/rules/{rid}/tiers  Update tiers (4-tier system)

GET    /playbooks/{id}/conditions         Get conditions
POST   /playbooks/{id}/conditions         Add condition
DELETE /playbooks/{id}/conditions/{cid}   Delete condition
POST   /playbooks/{id}/conditions/{cid}/overrides      Add override
DELETE /playbooks/{id}/conditions/{cid}/overrides/{oid} Delete override

GET    /playbooks/{id}/dependencies       Get dependencies
POST   /playbooks/{id}/dependencies       Add dependency
DELETE /playbooks/{id}/dependencies/{did} Delete dependency

GET    /playbooks/{id}/versions           Version history
POST   /playbooks/{id}/versions           Create version snapshot
GET    /playbooks/{id}/versions/{vid}     Get version details
GET    /playbooks/{id}/versions/diff/{a}/{b} Compare versions
POST   /playbooks/{id}/versions/{vid}/rollback Rollback to version

POST   /playbooks/{id}/publish           Publish to marketplace
GET    /playbooks/templates/browse        Browse templates
POST   /playbooks/templates/{tid}/create  Create from template
GET    /playbooks/marketplace/browse      Browse marketplace
POST   /playbooks/marketplace/{mid}/fork  Fork marketplace playbook
POST   /playbooks/marketplace/{mid}/rate  Rate playbook
PUT    /playbooks/marketplace/{mid}/rate  Update rating
```

## Users

```
GET    /users/me/usage    Monthly scan usage + tier limit
PATCH  /users/me          Update profile (name)
GET    /users/me/stats    Dashboard stats
GET    /users/org/stats   Org-wide dashboard stats
DELETE /users/me          Account deletion (GDPR soft delete)
```

## Team Management

```
GET    /team/members              List org members
PUT    /team/members/{uid}/role   Update role (viewer/user/editor/admin)
DELETE /team/members/{uid}        Remove member
```

## Billing & Subscriptions

```
GET  /billing/subscription        Org subscription status
GET  /billing/plans               Available plans
GET  /billing/usage               Current month usage & limits
POST /billing/create-subscription Create subscription (Razorpay/Stripe)
POST /billing/verify              Verify payment
GET  /billing/invoices            List invoices
GET  /billing/invoices/{id}/download Download invoice PDF
GET  /billing/dunning/status      Failed payment retry status

POST /billing/webhook/razorpay    Razorpay webhook
POST /billing/webhook/stripe      Stripe webhook
POST /billing/admin/zdr/purge-risks Zero Data Retention purge (admin)
```

## Analytics & Reports

```
GET  /analytics/overview         Org analytics overview
GET  /analytics/risks            Risk breakdown
GET  /analytics/users            User analytics
GET  /analytics/trends           Trend analysis
GET  /analytics/export           Export analytics data
GET  /analytics/executive        Executive dashboard
GET  /analytics/roi              ROI calculations
PUT  /analytics/roi/benchmarks   Update ROI benchmarks
PUT  /analytics/roi/config       Update ROI config
GET  /analytics/portfolio        Contract portfolio analysis
GET  /analytics/clauses          Clause analytics
GET  /analytics/team-performance Team performance
GET  /analytics/benchmark/{did}  Document benchmark
POST /analytics/benchmarks/refresh Recalculate benchmarks
GET  /analytics/bi-export/{dataset} BI export (Tableau/Power BI)
POST /analytics/reports/generate Generate custom report
GET  /analytics/reports          List reports
GET  /analytics/reports/{rid}    Get report details
```

## Audit Logs

```
GET /audit-logs/        List audit logs (paginated, filterable)
  Query: ?page=1&page_size=20&action=analyze&user_email=...
GET /audit-logs/verify  Verify hash chain integrity
```

## AI Agent

```
POST /agent/review                    AI review of document
POST /agent/research                  AI research on clause
GET  /agent/tools                     List available AI tools
POST /agent/compliance-watch/trigger  Trigger compliance watch
GET  /agent/renewals                  Get contract renewals
```

## Other

```
GET    /clauses/              List clause library (paginated)
POST   /clauses/              Add clause
GET    /clauses/{id}          Get clause
PUT    /clauses/{id}          Update clause
DELETE /clauses/{id}          Delete clause

GET    /templates/            List templates
GET    /templates/{id}        Get template details
GET    /templates/{id}/download Download template
POST   /templates/            Create template

GET    /jurisdictions/        List all jurisdictions
GET    /jurisdictions/{code}  Get jurisdiction rules

POST   /feedback/             Submit rule feedback
GET    /feedback/             List feedback
GET    /feedback/stats        Rule effectiveness stats

GET    /sso/authorize         Initiate SSO flow
POST   /sso/callback          SSO callback (WorkOS)
GET    /sso/status            SSO status
POST   /sso/enable            Enable org SSO
POST   /sso/disable           Disable org SSO
```

## Error Responses

All errors return JSON:
```json
{
  "detail": "Human-readable error message"
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad request / validation error |
| 401 | Unauthorized (token expired/invalid) |
| 403 | Forbidden (insufficient role) |
| 404 | Resource not found |
| 429 | Rate limited (check Retry-After header) |
| 500 | Internal server error |
