# ContraRed Backend

AI-powered contract redlining API built with FastAPI.

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
# or with dev dependencies
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Setup Database

```bash
# Start PostgreSQL (if using Docker)
docker run -d --name contrared-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=contrared \
  -p 5432:5432 postgres:15

# Tables are auto-created on startup
```

### 4. Run Server

```bash
# Development
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 5. API Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Project Structure

```
backend/
├── main.py                 # FastAPI application
├── app/
│   ├── api/v1/            # API endpoints
│   │   ├── endpoints/
│   │   │   ├── auth.py    # Authentication
│   │   │   ├── users.py   # User management
│   │   │   ├── documents.py # Document analysis
│   │   │   └── playbooks.py # Playbook management
│   │   └── router.py      # API router
│   ├── core/              # Core config
│   │   ├── config.py      # Settings
│   │   └── security.py    # JWT auth
│   ├── db/                # Database
│   │   └── session.py     # SQLAlchemy session
│   └── models/            # SQLAlchemy models
│       ├── user.py
│       ├── organization.py
│       ├── playbook.py
│       └── document.py
└── pyproject.toml         # Dependencies
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login (OAuth2) |
| `/api/v1/auth/me` | GET | Get current user |
| `/api/v1/documents/analyze` | POST | Analyze document |
| `/api/v1/documents/redline` | POST | Generate redline |
| `/api/v1/playbooks` | GET/POST | List/Create playbooks |
