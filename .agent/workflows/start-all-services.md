---
description: Start all ContraRed services (Docker, Backend, Dashboard, Word Add-in)
---
# Start All ContraRed Services

This workflow starts all required services for the ContraRed application.

## Prerequisites
- Docker Desktop installed
- Node.js and npm installed
- Python 3.x with uvicorn installed

## Steps

### 1. Start Docker Desktop (if not running)
```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
```
Wait ~30-60 seconds for Docker to fully start.

// turbo
### 2. Start PostgreSQL and Redis containers
```powershell
cd d:\Startup\Redliniing\V1 addon word\backend
docker-compose up -d
```

// turbo
### 3. Start Backend API Server (Port 8000)
```powershell
cd d:\Startup\Redliniing\V1 addon word\backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Backend will run at: http://localhost:8000
API Docs at: http://localhost:8000/api/docs

// turbo
### 4. Start Dashboard (Port 5173)
```powershell
cd d:\Startup\Redliniing\V1 addon word\dashboard
npm run dev
```
Dashboard will run at: http://localhost:5173

// turbo
### 5. Start Word Add-in Dev Server (Port 3000)
```powershell
cd d:\Startup\Redliniing\V1 addon word\ContraRed-PoC
npx webpack serve --mode development --port 3000
```
Word Add-in will run at: https://localhost:3000

## Service URLs Summary

| Service | URL | Description |
|---------|-----|-------------|
| Backend API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/api/docs | Swagger documentation |
| Dashboard | http://localhost:5173 | Admin dashboard (Vite) |
| Word Add-in | https://localhost:3000 | Office Add-in dev server |

## Test Credentials

| Email | Password |
|-------|----------|
| demo@contrared.ai | demo123 |

## Stopping Services

To stop all services:
```powershell
# Stop processes on ports
Get-NetTCPConnection -LocalPort 8000,3000,5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

# Stop Docker containers
cd d:\Startup\Redliniing\V1 addon word\backend
docker-compose down
```
