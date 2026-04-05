# ContraRed Architecture

## System Overview

ContraRed is a three-component system: a FastAPI backend, a Word Add-in, and a React dashboard.

```
                    ┌──────────────────────┐
                    │   Word Add-in        │
                    │  (Office.js + TS)    │
                    └─────────┬────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────┐
│  React Dashboard │  │  FastAPI     │  │  AI Providers│
│  (React 19)      │  │  Backend     │  │  Vertex AI   │
└─────────────────┘  │              │  │  Azure OpenAI│
                      └──────┬───────┘  └──────────────┘
                             │
                    ┌────────┼────────┐
                    │                 │
              ┌─────▼─────┐    ┌─────▼─────┐
              │ PostgreSQL │    │   Redis   │
              │ (Supabase) │    │ (optional)│
              └───────────┘    └───────────┘
```

## Backend Architecture

### Entry Point

`backend/main.py` — FastAPI app (v1.4.0) with this middleware stack (order matters):

1. **SensitiveDataFilter** — PII redaction in logs
2. **MaxBodySizeMiddleware** — 25MB request limit
3. **TenantContextMiddleware** — RLS context from JWT
4. **SecurityHeadersMiddleware** — CSP, HSTS, X-Frame-Options
5. **RequestIDMiddleware** — X-Request-ID tracking
6. **RequestLoggingMiddleware** — HTTP request logging
7. **CORSMiddleware** — Origin whitelisting
8. **ProxyHeadersMiddleware** — X-Forwarded-For trust
9. **GZipMiddleware** — Response compression (>=500 bytes)

### Analysis Pipeline (5 Stages)

The core contract analysis runs through `app/services/analysis_pipeline.py`:

```
Stage 1: Extraction (deterministic)
  Input:  Raw contract text
  Output: ContractMap, DefinedTerms, JurisdictionHint

Stage 2: Classification (rule engine + Gemini Flash)
  Input:  ContractMap
  Output: ClauseInventory (clause types identified)

Stage 3: Risk Assessment (Gemini Pro)
  Input:  ClauseInventory + Playbook rules
  Output: RawRedlines with confidence scores

Stage 4: Verification (hallucination guard)
  Input:  RawRedlines
  Output: VerifiedRedlines (false positives removed)

Stage 5: Enrichment (Gemini Flash per-redline)
  Input:  VerifiedRedlines
  Output: FinalRedlines with cross-references, fixes
```

### Drafting Pipeline (Multi-Agent)

`app/services/drafting/orchestrator.py` drives contract generation:

```
Raw Input
    │
    ▼
IntakeAgent ──► Validate input, select playbook
    │
    ▼
DraftAgent ──► Generate sections using playbook templates + AI
    │
    ├──► RiskAgent (parallel)     ──► Risk annotations
    ├──► ComplianceAgent (parallel)──► Compliance annotations
    └──► QAAgent (parallel)       ──► Quality annotations
    │
    ▼
JurisdictionRuleEngine ──► Jurisdiction-specific checks
    │
    ▼
ConsistencyEngine ──► Cross-section consistency
    │
    ▼
StyleRules ──► Formatting enforcement
    │
    ▼
Assembler ──► FinalDraft + QualityReport
```

Each stage has a 120-second timeout. Risk, Compliance, and QA agents run in parallel.

### AI Integration

Two providers configured in `app/core/vertex_client.py` and `app/services/ai_service.py`:

| Provider | Models | Use Case |
|----------|--------|----------|
| Vertex AI (primary) | gemini-2.5-pro, gemini-2.5-flash | All AI operations |
| Azure OpenAI (fallback) | gpt-4o, gpt-4o-mini | Backup when Vertex unavailable |

Model routing:
- **Scout** (gemini-2.5-flash): Classification, enrichment — fast, cheap
- **Pro** (gemini-2.5-pro): Risk assessment, drafting — accurate, expensive
- **Surgeon** (gemini-2.5-pro): Fix generation — precise replacements

### Database Layer

**35 tables** across these domains:

| Domain | Tables | Key Models |
|--------|--------|------------|
| Auth & Users | 3 | User, Organization, Subscription |
| Documents | 5 | Document, DocumentVersion, DocumentRisk, DocumentComparison, UsageLog |
| Playbooks | 8 | Playbook, PlaybookRule, PlaybookRuleTier, PlaybookCondition, PlaybookRuleOverride, PlaybookRuleDependency, PlaybookVersion, PlaybookMarketplace |
| Compliance | 3 | ComplianceLayer, ComplianceLayerRule, Jurisdiction |
| Billing | 3 | Subscription, Invoice, WebhookEvent |
| Analytics | 5 | AuditLog, ReviewSession, TimeBenchmark, BenchmarkProfile, GeneratedReport |
| Other | 8 | ClauseLibrary, ContractTemplate, BatchJob, DraftSession, Feedback, etc. |

**Row-Level Security (RLS)**: All tenant data isolated via `app/db/tenant.py` and `app/middleware/tenant_context.py`. PostgreSQL RLS policies enforce org-level isolation at the database layer.

### Authentication Flow

```
Client → POST /auth/login (email + password)
  ├─ Check account lockout (5 attempts → 15 min lock)
  ├─ Verify password (bcrypt)
  ├─ If MFA enabled → return MFA challenge token
  │   └─ POST /auth/mfa/challenge (TOTP code) → tokens
  └─ Set HttpOnly cookies (access: 30min, refresh: 7 days)

Token refresh: POST /auth/refresh (reads HttpOnly cookie)
Logout: POST /auth/logout (blacklists token)
```

RBAC tiers: `viewer` → `user` → `editor` → `admin` → `super_admin`

### Subscription & Billing

| Tier | Scans/Month | Price |
|------|-------------|-------|
| FREE | 5 | $0 |
| STARTER | 50 | varies |
| PRO | 200 | varies |
| BUSINESS | 1000 | varies |
| ENTERPRISE | Unlimited | custom |

Payment gateways: Razorpay (INR), Stripe (USD/EUR/GBP). Webhook idempotency via `WebhookEvent` table.

## Word Add-in Architecture

### Stack
- TypeScript + Office.js (Word API 1.4+)
- Webpack 5 (bundler)
- Fuse.js (fuzzy search)
- Custom CSS (no framework)

### Key Files
- `src/taskpane/taskpane.ts` (3,275 lines) — All UI logic, Office.js integration
- `src/taskpane/api.ts` (676 lines) — API client singleton
- `src/taskpane/taskpane.html` — UI template
- `manifest.xml` — Office add-in manifest (production URLs)

### Office.js Integration Points

| API | Purpose |
|-----|---------|
| `Word.run()` | Async context for all Word operations |
| `body.search()` | Find text for highlighting/replacement |
| `body.insertText()` | Template insertion |
| `changeTrackingMode = trackAll` | Enable Track Changes for redlines |
| `DocumentSelectionChanged` | Selection-aware scanning |

### Data Flow
1. User clicks "Scan" → `getDocumentText()` extracts full text via `body.load('text')`
2. Text sent to `/documents/analyze` with selected playbook
3. Results rendered as risk cards with RED/YELLOW/GREEN badges
4. User clicks "Apply Fix" → `applyAIRedline()` uses `body.search()` to find clause, replaces with fix, enables Track Changes

### Session Management
- Auth tokens in **HttpOnly cookies** (XSS-safe)
- User profile in **sessionStorage** (clears on tab close)
- Scan state cached in sessionStorage with 24h TTL + document hash verification

## Dashboard Architecture

### Stack
- React 19 + React Router v7
- Vite 7 (build tool)
- TailwindCSS 4 + custom design tokens
- React Query v5 (server state)
- Lucide React (icons)

### State Management
- **React Query**: Server data (playbooks, stats, audit logs) with 30s stale time
- **React Context**: Theme (dark/light) + Toast notifications
- **sessionStorage**: Auth user profile
- **useState**: Local form/modal state

### Route Structure
- **Public**: `/`, `/login`, `/register`, `/forgot-password`
- **Protected**: `/dashboard`, `/drafting`, `/playbooks`, `/clause-library`, `/templates`, `/compare`, `/batch-upload`, `/audit-logs`, `/marketplace`
- **Admin-only**: `/playbooks/:id`, `/analytics`, `/billing`, `/team`, `/executive`, `/reports`

### Design System
- Dark mode default, light mode toggle
- Brand color: `#C0392B` (ContraRed red)
- Risk colors: RED `#EF4444`, YELLOW `#F59E0B`, GREEN `#22C55E`
- Font: Inter (sans), JetBrains Mono (code)
- Sidebar: 240px expanded, 64px collapsed

## Compliance Layer System

Compliance layers are toggleable rule sets that overlay any playbook:

```
Playbook Rules (e.g., SaaS)
    +
Compliance Layer (e.g., DPDP Act 2023)
    =
Merged Rule Set (stricter rule wins on overlap)
```

Currently available: **DPDP Act 2023** (12 rules) in `backend/scripts/compliance_layers/dpdp.py`.

Rules are seeded to the `compliance_layers` + `compliance_layer_rules` tables and can be enabled per-analysis via the `/documents/compliance-layers` endpoint.

## Playbook System

14 pre-built playbooks in `backend/scripts/playbooks/`:

| Playbook | File | Rules |
|----------|------|-------|
| NDA (Mutual) | nda_mutual.py | Confidentiality, term, exclusions, remedies |
| NDA (Unilateral) | nda_unilateral.py | One-way protection |
| SaaS | saas.py | SLA, uptime, data handling, IP |
| MSA | msa.py | Scope, payment, liability, termination |
| Employment | employment.py | Non-compete, IP assignment, termination |
| DPA | dpa.py | GDPR/DPDP data processing |
| Lease | lease.py | Rent, maintenance, termination |
| Healthcare | healthcare.py | HIPAA, patient data |
| Fintech | fintech.py | Regulatory, AML/KYC |
| IT Services | it_services.py | SLA, support, change management |
| Joint Venture | joint_venture.py | Profit sharing, governance |
| Consulting | consulting.py | Scope, deliverables, IP |
| Vendor | vendor.py | Supply chain, quality |

Each playbook supports:
- **4-tier negotiation**: Ideal → Acceptable → Walk Away → Escalate
- **Conditional overrides**: Rules that change based on counterparty type, jurisdiction, contract value
- **Rule dependencies**: Rules that require other rules to be present
- **Version history**: Full rollback support
- **Marketplace**: Publish/fork/rate playbooks
