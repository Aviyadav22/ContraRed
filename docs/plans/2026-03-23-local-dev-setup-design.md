# Local Dev Environment Setup — Design

**Date:** 2026-03-23
**Status:** Approved

## Goal
Run all backend services locally against Docker-based PostgreSQL and Redis, with all Supabase tables migrated to the local DB.

## Architecture

```
docker compose up → PostgreSQL 15 (localhost:5433) + Redis 7 (localhost:6380)
                         ↑
    .env.local overrides DATABASE_URL + REDIS_URL only
                         ↑
    CONSOLIDATED_ALL_MIGRATIONS.sql auto-applied via Postgres init script
    seed_dev_data.sql inserts demo admin user
                         ↑
    uvicorn main:app --reload (reads .env.local → .env fallback)
```

## Changes

### 1. `.env.local` (new file)
Overrides DATABASE_URL and REDIS_URL to point to Docker containers. All other config (Gemini key, JWT secret, CORS origins) inherited from `.env`.

### 2. `config.py` (modify)
Change `env_file` from `".env"` to `[".env.local", ".env"]`. Pydantic-settings loads the first file found, with later files providing defaults for missing keys.

### 3. `docker-compose.yml` (modify)
Mount `migrations/CONSOLIDATED_ALL_MIGRATIONS.sql` and `migrations/seed_dev_data.sql` into `/docker-entrypoint-initdb.d/` so they run on first startup.

### 4. `seed_dev_data.sql` (new file)
Insert demo admin user (admin@contrared.com / ContraRed1@) with bcrypt hash, demo organization, and FREE subscription.

### 5. `session.py` (no changes)
Already handles non-Supabase URLs correctly (no SSL, no pooler workarounds).

## What stays the same
- `.env` untouched (production Supabase config)
- Dashboard `.env` already points to localhost:8000
- All frontend code unchanged
