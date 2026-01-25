# ContraRed

> **AI-Powered Contract Redlining Platform for Legal Teams**

ContraRed is an enterprise-grade legaltech SaaS platform that revolutionizes contract review workflows. Built as a Microsoft Word Add-in with a powerful cloud backend, ContraRed uses advanced AI to analyze contracts, identify risky clauses, and generate precise redline suggestions—all while maintaining zero data retention for maximum security and compliance.

---

## 🎯 Overview

ContraRed transforms how legal teams review contracts by combining:

- **AI-Powered Analysis**: Advanced language models (Google Gemini, Azure OpenAI) perform holistic contract analysis
- **Playbook-Based Rules**: Customizable rule sets for different contract types (SaaS, NDA, DPA, Employment, MSA)
- **Zero Data Retention**: Enterprise-grade security with document text processed in RAM only
- **Native Word Integration**: Seamless Microsoft Word Add-in experience
- **Multi-Tenant Architecture**: Built for organizations with role-based access control

---

## ✨ Key Features

### 🔍 Intelligent Contract Analysis
- **Holistic Document Review**: AI analyzes entire contract structure for contradictions and inconsistencies
- **Risk Detection**: Automated identification of risky clauses with RED/YELLOW/GREEN risk levels
- **Context-Aware Analysis**: Understands contract context, not just keyword matching
- **Executive Summaries**: High-level risk assessments for quick decision-making

### 📝 Advanced Redlining
- **Surgical Precision**: Fuzzy matching ensures accurate text anchoring even with formatting differences
- **Track Changes Integration**: Native Word Track Changes OOXML generation
- **AI-Generated Fixes**: Contextual suggestions that comply with your playbook rules
- **Paragraph Hash Tracking**: SHA-256 hashing for drift detection during document edits

### 🛡️ Enterprise Security & Compliance
- **Zero Data Retention Mode**: Document text never stored—processed in RAM only
- **Comprehensive Audit Logs**: Full compliance tracking (WHO/WHAT/WHEN/WHERE)
- **Multi-Tenant Isolation**: Organization-level data segregation
- **JWT Authentication**: Secure token-based authentication with refresh tokens

### 📚 Playbook Management
- **Custom Rule Sets**: Define organization-specific contract standards
- **Multiple Playbook Types**: Pre-built templates for common contract categories
- **Clause Library**: Approved language templates for consistent redlining
- **Public & Private Playbooks**: Share standards across teams or keep them private

### 💼 Subscription Management
- **Flexible Tiers**: Free, Pro, and Enterprise plans
- **Usage Tracking**: Token-based billing with detailed usage logs
- **Razorpay Integration**: Seamless payment processing
- **Organization Management**: Multi-seat subscriptions with admin controls

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Microsoft Word Add-in                    │
│                   (TypeScript + Office.js)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP/REST API
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Rule Engine  │  │ AI Service   │  │ Redline      │    │
│  │              │  │              │  │ Implementer  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└──────────┬───────────────────┬──────────────────────────────┘
           │                   │
           │                   │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────────────┐
    │ PostgreSQL  │    │ Redis Cache  │    │ AI Providers │
    │  Database   │    │              │    │ (Gemini/     │
    │             │    │              │    │  Azure)      │
    └─────────────┘    └──────────────┘    └──────────────┘
```

### Three-Box Architecture

1. **Box 1: Structure Extractor** - Parses DOCX files, extracts structure, generates paragraph hashes
2. **Box 2: Intelligence Bridge** - Rule engine + AI analysis (Omni-Context or Hybrid Sentinel strategies)
3. **Box 3: Redline Implementer** - Applies suggestions with fuzzy matching and OOXML generation

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | TypeScript, Office.js, React (Dashboard), Webpack |
| **Backend** | FastAPI, Python 3.11+, Uvicorn |
| **Database** | PostgreSQL 15, SQLAlchemy 2.0 (async) |
| **Cache** | Redis 7 |
| **Authentication** | JWT (PyJWT), bcrypt |
| **AI Providers** | Google Gemini (primary), Azure OpenAI (optional) |
| **Payments** | Razorpay |
| **Document Processing** | python-docx, rapidfuzz |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Word Add-in and Dashboard)
- PostgreSQL 15
- Redis 7
- Microsoft Word (for Add-in testing)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Required: DATABASE_URL, REDIS_URL, SECRET_KEY, GEMINI_API_KEY

# Start PostgreSQL and Redis (using Docker)
docker-compose up -d

# Run database migrations (auto-created on first run)
# Tables are automatically created on startup

# Start development server
uvicorn main:app --reload --port 8000
```

### Word Add-in Setup

```bash
# Navigate to Word Add-in directory
cd ContraRed-PoC

# Install dependencies
npm install

# Start development server
npm run dev-server

# Load Add-in in Word
# Follow Microsoft Office Add-in development guide
```

### Dashboard Setup

```bash
# Navigate to dashboard directory
cd dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Access at http://localhost:5173
```

### Access Points

- **API Documentation**: http://localhost:8000/api/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health
- **Dashboard**: http://localhost:5173

---

## 📖 API Documentation

### Authentication

```bash
# Register new user
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "name": "John Doe"
}

# Login
POST /api/v1/auth/login
{
  "username": "user@example.com",
  "password": "SecurePassword123!"
}

# Get current user
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### Document Analysis

```bash
# Analyze document text
POST /api/v1/documents/analyze
Authorization: Bearer <access_token>
{
  "text": "Contract text here...",
  "playbook_id": "optional-playbook-uuid",
  "filename": "contract.docx"
}

# Analyze uploaded DOCX file
POST /api/v1/documents/analyze-file
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
file: <docx_file>
playbook_id: <optional>
```

### Playbook Management

```bash
# List playbooks
GET /api/v1/playbooks
Authorization: Bearer <access_token>

# Create playbook
POST /api/v1/playbooks
Authorization: Bearer <access_token>
{
  "name": "SaaS Agreement Playbook",
  "category": "saas",
  "is_public": false
}
```

Full API documentation available at `/api/docs` when server is running.

---

## 🔐 Security & Compliance

### Zero Data Retention (ZDR)

ContraRed offers enterprise-grade data privacy:

- **Document text is never stored** - processed in RAM only
- **Only metadata persisted** - filename, risk count, timestamps
- **Full audit trail** - compliance logs without content storage
- **Configurable mode** - Enable/disable via `ZERO_DATA_RETENTION` environment variable

### Audit Logging

Comprehensive compliance tracking:
- User access events (WHO accessed WHAT, WHEN, WHERE)
- IP address and user agent logging
- Action tracking (analyze, export, view, redline)
- Risk count and status logging

### Authentication & Authorization

- JWT-based authentication with refresh tokens
- Role-based access control (USER, ADMIN, SUPER_ADMIN)
- Organization-level multi-tenancy
- Secure password hashing with bcrypt

---

## 📊 Database Schema

### Core Entities

- **Users**: User accounts with roles and subscription tiers
- **Organizations**: Multi-tenant organization management
- **Subscriptions**: Billing and subscription tracking
- **Playbooks**: Rule sets for contract analysis
- **PlaybookRules**: Individual rules within playbooks
- **Documents**: Document metadata (no content stored in ZDR mode)
- **DocumentRisks**: Risk findings per document
- **UsageLogs**: Token consumption and billing tracking
- **AuditLogs**: Compliance and security audit trail

See `ARCHITECTURE.md` for detailed schema documentation.

---

## 🎛️ Configuration

### Environment Variables

Key configuration options (see `.env.example` for full list):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/contrared

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI Provider
AI_PROVIDER=gemini  # or "azure"
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash

# Enterprise Features
ZERO_DATA_RETENTION=true
ANALYSIS_MODE=demo  # or "production"

# Payments
RAZORPAY_KEY_ID=your-key-id
RAZORPAY_KEY_SECRET=your-key-secret

# CORS
CORS_ORIGINS=["https://yourdomain.com","http://localhost:3000"]
```

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Platforms

ContraRed can be deployed on:

- **Railway.app** - Recommended for quick deployment (~$5-20/month)
- **Render.com** - Managed PostgreSQL and Redis (~$7-25/month)
- **DigitalOcean App Platform** - Full control (~$12-30/month)
- **AWS/GCP/Azure** - Enterprise deployments
- **Self-hosted VPS** - Most cost-effective (~$6-12/month)

See deployment documentation for platform-specific guides.

---

## 📈 Subscription Tiers

| Tier | Scans/Month | Features |
|------|-------------|----------|
| **Free** | 5 | Basic analysis, public playbooks |
| **Pro** | Unlimited | Full analysis, custom playbooks, API access |
| **Enterprise** | 500 included | Custom playbooks, SSO, audit logs, priority support |

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for:

- Code style and standards
- Pull request process
- Issue reporting
- Development setup

---

## 📄 License

[Specify your license here]

---

## 📞 Support

- **Documentation**: See `ARCHITECTURE.md` for detailed technical documentation
- **API Docs**: Available at `/api/docs` when server is running
- **Issues**: Report bugs and feature requests via GitHub Issues

---

## 🏢 Enterprise

For enterprise deployments, custom integrations, or dedicated support:

- Custom playbook development
- SSO integration (Azure AD, Okta)
- On-premise deployment options
- Dedicated support and SLA

---

**Built with ❤️ for legal teams who demand precision, security, and efficiency.**

*Last Updated: January 2026*
