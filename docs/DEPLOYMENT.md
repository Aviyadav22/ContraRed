# ContraRed Deployment Guide

## Current Production Setup

| Component | Platform | URL |
|-----------|----------|-----|
| Backend | Render.com | https://contrared-api.onrender.com |
| Dashboard | Netlify | https://contrared-dashboard.netlify.app |
| Word Add-in | Netlify | https://contrared-addin.netlify.app |
| Database | Supabase | PostgreSQL (ap-south-1) |
| Redis | Not configured | App degrades gracefully |

## Backend (Render.com)

### Service Configuration

- **Service ID**: srv-d6hbqckr85hc739caik0
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Python Version**: 3.11.0 (set via `backend/.python-version`)
- **Region**: Oregon (US)

### Required Environment Variables

```bash
# Database (Supabase)
DATABASE_URL=postgresql+asyncpg://postgres.xxx:password@aws-1-ap-south-1.pooler.supabase.com:5432/postgres

# Security
SECRET_KEY=<32+ char random string>
ENCRYPTION_KEY=<Fernet key for field-level encryption>

# AI
VERTEX_PROJECT_ID=<GCP project ID>
VERTEX_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/gcp-key.json

# CORS
CORS_ORIGINS=["https://contrared-dashboard.netlify.app","https://contrared-addin.netlify.app"]

# Frontend
FRONTEND_URL=https://contrared-dashboard.netlify.app

# Payment (optional)
RAZORPAY_KEY_ID=<key>
RAZORPAY_KEY_SECRET=<secret>
STRIPE_SECRET_KEY=<key>

# SSO (optional)
WORKOS_API_KEY=<key>
WORKOS_CLIENT_ID=<id>

# Email (optional)
RESEND_API_KEY=<key>
```

### Important Notes

- **DATABASE_URL**: Use port 5432 (direct), NOT 6543 (PgBouncer). asyncpg SSL: use `ssl=True` (bool), NOT `ssl="require"` (string)
- **CORS_ORIGINS**: Must be a JSON array string
- **render.yaml**: Must be at repo root, not inside `backend/`
- **Render PUT /env-vars replaces ALL vars** — always include every variable in the payload
- **GOOGLE_APPLICATION_CREDENTIALS**: Upload service account JSON as a secret file

### Deploy Process

1. Push to `main` branch
2. Render auto-deploys from GitHub (if connected)
3. Manual deploy: Render dashboard > Manual Deploy > Deploy latest commit

### Health Check

```bash
curl https://contrared-api.onrender.com/health
# { "status": "ok", "version": "1.4.0" }

curl https://contrared-api.onrender.com/health/deep
# { "database": "ok", "redis": "unavailable", "ai": "ok", ... }
```

## Dashboard (Netlify)

### Build Configuration

In `dashboard/netlify.toml`:
```toml
[build]
  base = "dashboard"
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"
```

### Environment Variables (Netlify Dashboard)

```bash
VITE_API_URL=https://contrared-api.onrender.com/api/v1
```

### Security Headers

Configured in `netlify.toml`:
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: connect-src 'self' https://contrared-api.onrender.com`
- SPA redirect: `/* → /index.html` (status 200)

## Word Add-in (Netlify)

### Build Configuration

In `ContraRed-PoC/netlify.toml`:
```toml
[build]
  base = "ContraRed-PoC"
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"
```

### Environment Variables (Netlify Dashboard)

```bash
API_BASE_URL=https://contrared-api.onrender.com/api/v1
```

### Security Headers

- NO `X-Frame-Options` (add-in runs in Office iframe)
- `frame-ancestors: 'self' https://*.office.com https://*.microsoft.com https://*.office365.com`
- `script-src: 'self' 'unsafe-eval' https://appsforoffice.microsoft.com` (required by Office.js)

### Manifest

`ContraRed-PoC/manifest.xml` must point to production URLs:
- Source: `https://contrared-addin.netlify.app/taskpane.html`
- Icons: `https://contrared-addin.netlify.app/assets/icon-*.png`
- App domains: `contrared-addin.netlify.app`, `contrared.com`, `contrared-api.onrender.com`

## Database (Supabase)

### Connection Details

- **Project ref**: qjlkdmozcoqnwefuxjwa
- **Region**: ap-south-1 (Mumbai)
- **Direct**: `postgresql://postgres:***@db.qjlkdmozcoqnwefuxjwa.supabase.co:5432/postgres`
- **Pooled**: `postgresql://postgres.qjlkdmozcoqnwefuxjwa:***@aws-1-ap-south-1.pooler.supabase.com:6543/postgres`

### Migration Application

Apply all 18 migrations in order, or use the consolidated file:
```bash
psql $DATABASE_URL -f migrations/CONSOLIDATED_ALL_MIGRATIONS.sql
```

### Current State

- 30 tables, 136 indexes, 48 RLS policies, 25 RLS-enabled tables
- Enum case mismatch: `subscriptiontier` has both uppercase (FREE/PRO/ENTERPRISE) and lowercase (starter/business) values — code handles both

## Monitoring

### Health Endpoints

```
GET /health        → Basic alive check
GET /health/db     → Database connectivity
GET /health/deep   → Full system check (DB + Redis + AI) with latencies
```

### Error Tracking (Optional)

Set on Render:
```bash
SENTRY_DSN=<your-sentry-dsn>
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Logs

- Render: Dashboard > Service > Logs (real-time streaming)
- All logs have PII redacted by SensitiveDataFilter middleware

## Scaling Notes

- **Render**: Free tier spins down after 15 min idle. Upgrade to paid for always-on.
- **Database**: Supabase free tier allows 500MB. Monitor usage in Supabase dashboard.
- **Redis**: Not currently configured. When needed, use Upstash Redis and add `REDIS_URL` to Render env vars. The app uses Redis for: token blacklist, playbook caching, rate limiting state.
- **AI**: Vertex AI quotas are per-project. Monitor in GCP Console > IAM > Quotas.
