# ContraRed Environment Variables Reference

## Backend (`backend/.env`)

### Application

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APP_NAME` | ContraRed | No | Application name |
| `DEBUG` | false | No | Debug mode (enables /api/docs, /health/ai, relaxes CORS) |

### Database

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | — | **Yes (prod)** | PostgreSQL connection string. Format: `postgresql+asyncpg://user:pass@host:5432/db` |
| `DB_POOL_SIZE` | 5 | No | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | 10 | No | Max overflow connections beyond pool |

### Redis

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `REDIS_URL` | — | No | Redis connection URL. App degrades gracefully without Redis |

### Security & JWT

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SECRET_KEY` | — | **Yes (prod)** | JWT signing key (min 32 chars) |
| `ALGORITHM` | HS256 | No | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | No | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | No | Refresh token TTL |
| `TOKEN_BLACKLIST_TTL_SECONDS` | 604800 | No | Blacklist retention (7 days) |
| `ENCRYPTION_KEY` | — | **Yes (prod)** | Fernet key for AES-256 field-level encryption |

### AI Providers

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `AI_PROVIDER` | gemini | No | "gemini" or "azure" |
| `VERTEX_PROJECT_ID` | — | **Yes (for AI)** | Google Cloud project ID |
| `VERTEX_LOCATION` | us-central1 | No | Vertex AI region |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | **Yes (for AI)** | Path to GCP service account JSON |
| `GEMINI_MODEL` | gemini-2.5-pro | No | Default Gemini model |
| `GEMINI_ANALYSIS_MODEL` | gemini-2.5-pro | No | Full analysis model |
| `GEMINI_SCOUT_MODEL` | gemini-2.5-flash | No | Fast classification model |
| `GEMINI_SURGEON_MODEL` | gemini-2.5-pro | No | Precise fix generation model |
| `AZURE_OPENAI_ENDPOINT` | — | No | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | — | No | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_GPT4` | gpt-4o | No | GPT-4 deployment name |
| `AZURE_OPENAI_DEPLOYMENT_MINI` | gpt-4o-mini | No | GPT-4 Mini deployment name |

### CORS & Cookies

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `CORS_ORIGINS` | localhost:3000,localhost:5173 | No | Allowed origins (JSON array or comma-separated) |
| `COOKIE_DOMAIN` | (empty) | No | Cookie domain (empty = response origin) |
| `COOKIE_SECURE` | true | No | HttpOnly + Secure + SameSite=None cookies |
| `COOKIE_SAMESITE` | none | No | SameSite cookie attribute |
| `TRUSTED_PROXY_HOSTS` | 127.0.0.1 | No | Trusted reverse proxy IPs |

### Subscription Limits

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `FREE_TIER_SCANS` | 5 | No | Free tier monthly scan limit |
| `STARTER_TIER_SCANS` | 50 | No | Starter tier limit |
| `PRO_TIER_SCANS` | 200 | No | Pro tier limit |
| `BUSINESS_TIER_SCANS` | 1000 | No | Business tier limit |
| `ENTERPRISE_INCLUDED_SCANS` | -1 | No | Enterprise limit (-1 = unlimited) |

### Payment Gateways

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `RAZORPAY_KEY_ID` | — | No | Razorpay key ID (INR payments) |
| `RAZORPAY_KEY_SECRET` | — | No | Razorpay secret |
| `RAZORPAY_PLAN_STARTER_ID` | — | No | Razorpay plan ID for Starter |
| `RAZORPAY_PLAN_PRO_ID` | — | No | Razorpay plan ID for Pro |
| `RAZORPAY_PLAN_BUSINESS_ID` | — | No | Razorpay plan ID for Business |
| `STRIPE_SECRET_KEY` | — | No | Stripe secret key (USD/EUR/GBP) |
| `STRIPE_PUBLISHABLE_KEY` | — | No | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | — | No | Stripe webhook signing secret |

### SSO

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `WORKOS_API_KEY` | — | No | WorkOS API key for SSO |
| `WORKOS_CLIENT_ID` | — | No | WorkOS client ID |

### Email

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `RESEND_API_KEY` | — | No | Resend API key for emails |
| `EMAIL_FROM` | noreply@contrared.com | No | Sender email address |

### Frontend

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `FRONTEND_URL` | http://localhost:5173 | No | Frontend URL (used in email links) |

### Analysis

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ANALYSIS_MODE` | production | No | "demo" (mock data) or "production" (real AI) |
| `FUZZY_MATCH_THRESHOLD` | 0.85 | No | Text matching threshold (0-1) |
| `ZERO_DATA_RETENTION` | true | No | Never store contract text (RAM only) |

### Monitoring

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SENTRY_DSN` | — | No | Sentry error tracking DSN |
| `SENTRY_ENVIRONMENT` | development | No | Sentry environment name |
| `SENTRY_TRACES_SAMPLE_RATE` | 0.1 | No | Transaction sampling rate (10%) |

## Dashboard (`dashboard/.env`)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `VITE_API_URL` | — | **Yes** | Backend API base URL (e.g., `http://localhost:8000/api/v1`) |

## Word Add-in (`ContraRed-PoC/.env`)

Set in Netlify dashboard (not in .env file for production):

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `API_BASE_URL` | — | **Yes** | Backend API base URL (injected via webpack DefinePlugin) |

## Production Checklist

- [ ] `DATABASE_URL` points to production PostgreSQL (port 5432, ssl=True)
- [ ] `SECRET_KEY` is a strong random string (32+ chars)
- [ ] `ENCRYPTION_KEY` is set (Fernet key)
- [ ] `VERTEX_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS` configured
- [ ] `CORS_ORIGINS` lists only production domains (no localhost)
- [ ] `FRONTEND_URL` points to production dashboard URL
- [ ] `DEBUG` is false (or unset)
- [ ] `ZERO_DATA_RETENTION` is true
- [ ] `VITE_API_URL` (dashboard) points to production API
- [ ] `API_BASE_URL` (add-in) points to production API
