# ContraRed

> AI-Powered Contract Redlining Platform for Legal Teams

ContraRed is an enterprise-grade legaltech SaaS that analyzes contracts, identifies risky clauses, and generates precise redline suggestions. It ships as a Microsoft Word Add-in backed by a FastAPI cloud backend and a React dashboard.

## System Components

```
ContraRed/
  backend/          FastAPI (Python 3.11) — API, AI pipeline, rule engine
  ContraRed-PoC/    Word Add-in (TypeScript + Office.js)
  dashboard/        React 19 + Vite 7 + TailwindCSS 4
```

### Live Deployments

| Component | URL |
|-----------|-----|
| Backend API | https://contrared-api.onrender.com |
| Dashboard | https://contrared-dashboard.netlify.app |
| Word Add-in | https://contrared-addin.netlify.app |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Uvicorn |
| Database | PostgreSQL 15 (Supabase), Redis (optional) |
| Word Add-in | TypeScript, Office.js, Webpack, Fuse.js |
| Dashboard | React 19, Vite 7, TailwindCSS 4, React Query v5, React Router v7 |
| AI | Google Gemini via Vertex AI (primary), Azure OpenAI (fallback) |
| Auth | JWT + MFA (TOTP) + SSO (WorkOS/SAML) |
| Payments | Razorpay (INR), Stripe (USD/EUR/GBP) |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15
- Microsoft Word (for add-in testing)

### Backend

```bash
cd backend
pip install -r requirements.txt
# Set required env vars: DATABASE_URL, SECRET_KEY, VERTEX_PROJECT_ID
uvicorn main:app --reload --port 8000
```

### Word Add-in

```bash
cd ContraRed-PoC
npm install
npm run dev-server    # https://localhost:3007
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev           # http://localhost:3006
```

### Access Points

| Endpoint | URL |
|----------|-----|
| API Docs (Swagger) | http://localhost:8000/api/docs |
| Health Check | http://localhost:8000/health |
| Dashboard | http://localhost:3006 |
| Word Add-in | https://localhost:3007/taskpane.html |

## Key Features

- **5-Stage Analysis Pipeline**: Extraction, Classification, Risk Assessment, Verification, Enrichment
- **Multi-Agent Drafting**: Intake, Draft, Risk, Compliance, QA agents orchestrated in parallel
- **14 Playbook Types**: NDA, SaaS, MSA, Employment, DPA, Lease, Healthcare, Fintech, etc.
- **DPDP/GDPR/CCPA Compliance Layers**: Toggleable compliance rule sets
- **7 Jurisdictions**: US (DE/CA/NY/TX), India, UK, Singapore
- **Zero Data Retention**: Contract text processed in RAM only, never stored
- **Enterprise Security**: AES-256 encryption, RBAC (5-tier), audit log hash chain, RLS
- **5 Subscription Tiers**: Free (5 scans) to Enterprise (unlimited)

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, data flow, component design |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | All API endpoints with request/response examples |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, testing, coding conventions |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment on Render, Netlify, Supabase |
| [ENV_REFERENCE.md](docs/ENV_REFERENCE.md) | All environment variables with defaults |
| [SECURITY.md](docs/SECURITY.md) | Security architecture, audit checklist, compliance |

## Project Structure

```
backend/
  app/
    api/v1/endpoints/    15 endpoint modules (120+ routes)
    core/                Config, security, encryption, Vertex AI client
    db/                  SQLAlchemy async session, RLS tenant isolation
    middleware/          Tenant context, security headers, rate limiting
    models/              16 model files (35 tables)
    services/            50+ service files
      drafting/          Multi-agent drafting pipeline
        agents/          5 agents: intake, draft, risk, compliance, qa
        playbooks/       NDA, SaaS, MSA, Employment drafting templates
        renderer/        DOCX and Word add-in renderers
    workers/             Background task workers
  scripts/
    playbooks/           14 playbook definitions
    compliance_layers/   DPDP Act 2023 rules
  migrations/            18 SQL migration files
  tests/                 Test suite

ContraRed-PoC/           Word Add-in
  src/taskpane/
    taskpane.ts          Main UI logic (3,275 lines)
    taskpane.html        UI template
    api.ts               API client (676 lines)
  manifest.xml           Production manifest
  webpack.config.js      Build config

dashboard/               React Dashboard
  src/
    api/client.ts        API client (1,472 lines)
    components/          Layout + 13 UI components
    contexts/            Theme + Toast contexts
    pages/               35 page components
      drafting/          6-step drafting workflow
      playbook-editor/   13-file advanced editor
```

## License

Proprietary - All rights reserved.
