# ContraRed Development Guide

## Prerequisites

- Python 3.11+ (backend)
- Node.js 20+ (add-in + dashboard)
- PostgreSQL 15 (or Supabase)
- Redis 7 (optional, app degrades gracefully)
- Microsoft Word (for add-in testing)

## Repository Structure

```
backend/              Python FastAPI backend
ContraRed-PoC/        Word Add-in (TypeScript + Office.js)
dashboard/            React dashboard
onboarding-neetiq/    Onboarding site (separate project)
```

## Backend Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configure Environment

Create `backend/.env`:

```bash
# Required
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/contrared
SECRET_KEY=your-secret-key-at-least-32-characters-long

# AI (required for analysis/drafting)
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Optional
REDIS_URL=redis://localhost:6379/0
DEBUG=true
CORS_ORIGINS=["http://localhost:3006","https://localhost:3007"]
FRONTEND_URL=http://localhost:3006
```

See [ENV_REFERENCE.md](ENV_REFERENCE.md) for all variables.

### 3. Database Setup

**Option A: Local PostgreSQL**
```bash
createdb contrared
cd backend
python setup_local_db.py
```

**Option B: Supabase (recommended)**
Use the pooled connection string from Supabase dashboard. Direct connection requires port 5432 with `ssl=True`.

### 4. Run Migrations

Migrations are SQL files in `backend/migrations/`. Apply them in order:
```bash
psql -d contrared -f migrations/001_add_ai_verification_fields.sql
# ... through 018
```

Or use the consolidated migration:
```bash
psql -d contrared -f migrations/CONSOLIDATED_ALL_MIGRATIONS.sql
```

### 5. Seed Data

```bash
cd backend
python -c "
import asyncio
from app.db.session import get_engine
from scripts.seed_default_playbooks import seed_playbooks
from scripts.seed_jurisdictions import seed_jurisdictions
asyncio.run(seed_playbooks())
asyncio.run(seed_jurisdictions())
"
```

### 6. Start Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API docs available at http://localhost:8000/api/docs

## Word Add-in Setup

### 1. Install Dependencies

```bash
cd ContraRed-PoC
npm install
```

### 2. Generate Dev Certificates

```bash
npx office-addin-dev-certs install
```

This creates self-signed certs in `~/.office-addin-dev-certs/`.

### 3. Start Dev Server

```bash
npm run dev-server
```

Serves on https://localhost:3007 with proxy to backend at localhost:8000.

### 4. Sideload in Word

**Desktop (Windows):**
```bash
npm run start:desktop
```

**Web (Word Online):**
1. Go to word.office.com
2. Insert > Add-ins > Upload My Add-in
3. Upload `manifest-local.xml`

### 5. Build for Production

```bash
API_BASE_URL=https://contrared-api.onrender.com/api/v1 npm run build
```

Output in `dist/`.

## Dashboard Setup

### 1. Install Dependencies

```bash
cd dashboard
npm install
```

### 2. Configure Environment

Create `dashboard/.env`:
```bash
VITE_API_URL=http://localhost:8000/api/v1
```

### 3. Start Dev Server

```bash
npm run dev
```

Serves on http://localhost:3006.

### 4. Build for Production

```bash
npm run build
```

Output in `dist/`.

## Running All Three Locally

Terminal 1 (Backend):
```bash
cd backend && uvicorn main:app --reload --port 8000
```

Terminal 2 (Word Add-in):
```bash
cd ContraRed-PoC && npm run dev-server
```

Terminal 3 (Dashboard):
```bash
cd dashboard && npm run dev
```

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

Key test files:
- `tests/test_compliance_layers.py` — Compliance layer loading/merging
- `tests/test_unified_pipeline.py` — Full analysis pipeline
- `tests/test_review_agents.py` — AI review agent
- `tests/test_assembler.py` — Draft assembly
- `tests/test_style_rules.py` — Style enforcement
- `tests/test_jurisdiction_rules.py` — Jurisdiction checks

### Word Add-in

```bash
cd ContraRed-PoC
npm run validate   # Validate manifest
npm run lint       # ESLint
```

### Dashboard

```bash
cd dashboard
npm run lint       # ESLint
npm run build      # Type check + build (catches TS errors)
```

## Code Conventions

### Backend (Python)

- **Async everywhere**: All DB operations use `async/await` with SQLAlchemy AsyncSession
- **Pydantic v2**: Request/response validation
- **Structured logging**: `logging.getLogger(__name__)` with PII redaction
- **Error handling**: FastAPI exception handlers, never expose internal errors to clients
- **Type hints**: Required on all function signatures

### Word Add-in (TypeScript)

- **Strict mode**: `tsconfig.json` has `strict: true`
- **Office.js pattern**: All Word operations wrapped in `Word.run(async context => { ... })`
- **XSS prevention**: `escapeHtml()` on all dynamic content
- **Session over local storage**: User data in sessionStorage (not localStorage)

### Dashboard (React/TypeScript)

- **Functional components**: Hooks-based, no class components
- **React Query**: For all server state (no manual fetch + useState)
- **Lazy loading**: All pages use `React.lazy()` with Suspense
- **Path alias**: `@/` maps to `src/`

## Database Conventions

- **UUID primary keys**: All tables use UUID (`gen_random_uuid()`)
- **Soft deletes**: Use `deleted_at` timestamp where applicable
- **Audit trail**: Critical operations logged to `audit_logs` with hash chain
- **RLS**: All tenant tables have Row-Level Security policies
- **Timestamps**: `created_at` and `updated_at` on all tables (UTC)
- **JSONB**: Used for flexible fields (rules, metadata, risk_summary)

## Git Workflow

- `main` branch is production
- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- Commit messages: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
