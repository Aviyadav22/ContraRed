# ContraRed Security Implementation Plan
## From 3/10 to 10/10 -- Enterprise Legal SaaS Grade

**Date:** 2026-03-11
**Current Score:** 3/10
**Target Score:** 10/10
**Audience:** Engineering team, CISO reviewers, SOC 2 auditors

---

## Table of Contents

1. [Executive Threat Assessment](#1-executive-threat-assessment)
2. [EXISTENTIAL: Attorney-Client Privilege Protection](#2-existential-attorney-client-privilege-protection)
3. [SSO/SAML Implementation](#3-ssosaml-implementation)
4. [Multi-Factor Authentication (MFA)](#4-multi-factor-authentication-mfa)
5. [AI Data Protection](#5-ai-data-protection)
6. [Leakage Vector Elimination](#6-leakage-vector-elimination)
7. [RBAC Overhaul](#7-rbac-overhaul)
8. [Session Security](#8-session-security)
9. [Encryption at Rest and Field-Level](#9-encryption-at-rest-and-field-level)
10. [Compliance Roadmap](#10-compliance-roadmap)
11. [Security Operations](#11-security-operations)
12. [Implementation Priority & Timeline](#12-implementation-priority--timeline)
13. [Success Criteria: What a Law Firm CISO Requires](#13-success-criteria)

---

## 1. Executive Threat Assessment

### What We Have (Score: 3/10)

| Component | Status | Risk |
|---|---|---|
| Authentication | JWT with bcrypt, rate limiting, account lockout | Acceptable foundation |
| Authorization | 3-tier RBAC (Analyst/Admin/SuperAdmin) | Too coarse for legal workflows |
| SSO/SAML | `sso_enabled` and `entra_tenant_id` fields exist but are unused | Blocker for every law firm |
| MFA | None | Insurance disqualifier |
| AI Data Protection | Raw contract text sent to Gemini consumer API | **Privilege-destroying** |
| Encryption at Rest | Supabase default (disk-level only) | No field-level encryption |
| Session Management | Stateless JWT, no revocation, no rotation | Token theft = full access |
| Logging | Audit log exists but `details` field accepts free text | Potential leakage vector |
| Security Headers | HSTS, X-Frame-Options, CSP basics | Good foundation |
| Compliance | None (no SOC 2, no ISO 27001, no DPDP) | Sales blocker |

### Existential Risk: Attorney-Client Privilege

Contract text sent to Google Gemini via consumer API (`google.generativeai`) with no Data Processing Agreement (DPA). Under *Upjohn Co. v. United States* and subsequent case law, attorney-client privilege can be waived by disclosure to third parties without adequate confidentiality protections. A law firm using ContraRed today risks:

1. **Privilege waiver** -- Gemini consumer API terms allow Google to use data for model improvement
2. **Ethical violation** -- ABA Model Rule 1.6 (Confidentiality) requires "reasonable efforts" to prevent unauthorized disclosure
3. **Malpractice liability** -- The law firm and ContraRed could face malpractice claims
4. **Regulatory exposure** -- Bar associations can discipline attorneys for inadequate data safeguards

**This is not a feature gap. This is a liability that could destroy the company.**

---

## 2. EXISTENTIAL: Attorney-Client Privilege Protection

**Complexity: XL | Priority: P0 | Timeline: Weeks 1-4**

### 2.1 Immediate: Migrate from Consumer Gemini to Enterprise AI

**Current code path** (`backend/app/services/gemini_analyzer.py` line 234):
```python
genai.configure(api_key=settings.GEMINI_API_KEY)
self._client = genai.GenerativeModel(settings.GEMINI_MODEL)
```

This uses the consumer `google.generativeai` SDK with a standard API key. There is no DPA, no data residency guarantee, and Google's terms permit data use for model training.

**Migration options (pick one):**

#### Option A: Google Vertex AI with DPA (Recommended)
- Sign Google Cloud enterprise agreement with BAA/DPA addendum
- Migrate from `google.generativeai` SDK to `google-cloud-aiplatform` SDK
- Enable VPC Service Controls for data perimeter enforcement
- Configure Customer-Managed Encryption Keys (CMEK)
- Set data residency to `asia-south1` (Mumbai) for DPDP compliance

**Code change in `gemini_analyzer.py`:**
```python
# BEFORE (consumer API -- privilege-destroying)
import google.generativeai as genai
genai.configure(api_key=settings.GEMINI_API_KEY)
client = genai.GenerativeModel(settings.GEMINI_MODEL)
response = client.generate_content(prompt)

# AFTER (Vertex AI with enterprise DPA)
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel

aiplatform.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_REGION)
client = GenerativeModel(settings.GEMINI_MODEL)
response = client.generate_content(prompt)
```

**New config fields in `config.py`:**
```python
# Google Cloud / Vertex AI (enterprise, DPA-covered)
GCP_PROJECT_ID: str = ""
GCP_REGION: str = "asia-south1"  # Mumbai for DPDP compliance
GCP_SERVICE_ACCOUNT_KEY: str = ""  # Path to service account JSON
```

#### Option B: Azure OpenAI with Private Endpoints
- Already have Azure config fields in `config.py` (lines 52-55)
- Deploy Azure OpenAI in `centralindia` region
- Configure private endpoint (no public internet exposure)
- Enable Azure Customer Lockbox
- Sign Microsoft DPA (included in Enterprise Agreement)

#### Option C: Self-Hosted Model (Maximum Security)
- Deploy Llama 3.1 70B or Mixtral 8x22B on Azure/GCP
- Zero data leaves your infrastructure
- Higher latency and cost, but absolute privilege protection
- Consider for Enterprise tier customers only

### 2.2 In-Transit Protection for AI Calls

Regardless of provider, add these safeguards:

```python
# backend/app/services/ai_data_protection.py (NEW FILE)

import hashlib
import re
from typing import Tuple

class PrivilegeProtector:
    """
    Sanitizes contract text before AI processing to minimize
    privilege exposure while maintaining analysis quality.
    """

    # Patterns that indicate attorney work product
    PRIVILEGED_PATTERNS = [
        r'(?i)attorney[\s-]client\s+privilege',
        r'(?i)work\s+product',
        r'(?i)privileged\s+and\s+confidential',
        r'(?i)prepared\s+at\s+the\s+direction\s+of\s+counsel',
    ]

    @staticmethod
    def redact_metadata(text: str) -> Tuple[str, dict]:
        """
        Strip client-identifying metadata before sending to AI.
        Returns (redacted_text, redaction_map) so we can restore later.
        """
        redaction_map = {}

        # Redact email addresses
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        for i, email in enumerate(set(emails)):
            placeholder = f"[EMAIL_{i}]"
            redaction_map[placeholder] = email
            text = text.replace(email, placeholder)

        # Redact phone numbers (Indian format)
        phones = re.findall(r'\+?91[\s-]?\d{10}|\b\d{10}\b', text)
        for i, phone in enumerate(set(phones)):
            placeholder = f"[PHONE_{i}]"
            redaction_map[placeholder] = phone
            text = text.replace(phone, placeholder)

        # Redact specific entity names if configured
        # (Organization names from the org's settings)

        return text, redaction_map

    @staticmethod
    def check_for_privileged_content(text: str) -> bool:
        """Warn if document appears to contain privileged communications."""
        for pattern in PrivilegeProtector.PRIVILEGED_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    @staticmethod
    def create_processing_receipt(
        document_hash: str,
        ai_provider: str,
        region: str,
        dpa_reference: str,
    ) -> dict:
        """
        Generate an audit receipt proving how AI processing was handled.
        Required for privilege logs in case of litigation.
        """
        return {
            "document_hash_sha256": document_hash,
            "ai_provider": ai_provider,
            "processing_region": region,
            "dpa_reference": dpa_reference,
            "data_retention": "zero",
            "encryption_in_transit": "TLS 1.3",
            "timestamp_utc": datetime.utcnow().isoformat(),
        }
```

### 2.3 Legal Documentation Required

- [ ] Execute DPA with AI provider (Google Cloud or Microsoft Azure)
- [ ] Add "Sub-processor List" to ContraRed's Terms of Service
- [ ] Create "AI Processing Addendum" for law firm contracts
- [ ] Publish a "Technical Security White Paper" for CISO review
- [ ] Get legal opinion on privilege preservation with chosen architecture

---

## 3. SSO/SAML Implementation

**Complexity: L | Priority: P0 | Timeline: Weeks 2-6**

### 3.1 Current State

The `Organization` model (`backend/app/models/organization.py`) already has:
```python
sso_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
entra_tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
```

These fields are **never checked** in the auth flow. The login endpoint (`auth.py`) only supports email/password.

### 3.2 Architecture: Use an Identity Broker

Do NOT implement SAML/OIDC protocol parsing from scratch. Use one of:

| Option | Pros | Cons |
|---|---|---|
| **WorkOS** (Recommended) | Purpose-built for B2B SaaS SSO. Supports 50+ IdPs. | $125/mo per org after free tier |
| **Auth0/Okta** | Battle-tested. Large ecosystem. | Complex pricing. Overkill for current stage. |
| **Clerk** | Good DX. Built-in MFA. | Less enterprise focus. |
| **Self-built with python-saml2** | No vendor dependency. | 3-6 months of work. SAML is notoriously complex. |

**Recommendation: WorkOS** -- it is specifically built for the "I need SSO to sell to enterprises" problem.

### 3.3 Implementation Plan

#### Database Changes

```sql
-- Migration: 002_sso_support.sql

ALTER TABLE organizations ADD COLUMN sso_provider VARCHAR(50);          -- 'azure_ad', 'okta', 'google_workspace'
ALTER TABLE organizations ADD COLUMN sso_connection_id VARCHAR(255);    -- WorkOS connection ID
ALTER TABLE organizations ADD COLUMN sso_enforce BOOLEAN DEFAULT FALSE; -- Force SSO (no password login)
ALTER TABLE organizations ADD COLUMN allowed_domains TEXT[];            -- Email domains allowed

ALTER TABLE users ADD COLUMN sso_subject_id VARCHAR(255);              -- IdP user identifier
ALTER TABLE users ADD COLUMN auth_method VARCHAR(20) DEFAULT 'password'; -- 'password', 'sso', 'sso_mfa'
ALTER TABLE users ADD COLUMN last_sso_login TIMESTAMP;
```

#### Backend Flow

```python
# backend/app/api/v1/endpoints/sso.py (NEW FILE)

from fastapi import APIRouter, HTTPException, Request
import workos

router = APIRouter(prefix="/sso", tags=["SSO"])

workos_client = workos.WorkOS(api_key=settings.WORKOS_API_KEY)

@router.get("/authorize")
async def sso_authorize(
    organization_domain: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Redirect user to their IdP.
    Called when user enters email with SSO-enabled domain.
    """
    # Look up org by email domain
    org = await db.execute(
        select(Organization).where(Organization.domain == organization_domain)
    )
    org = org.scalar_one_or_none()

    if not org or not org.sso_enabled:
        raise HTTPException(400, "SSO not configured for this organization")

    authorization_url = workos_client.sso.get_authorization_url(
        connection=org.sso_connection_id,
        redirect_uri=f"{settings.API_BASE_URL}/api/v1/sso/callback",
        state=str(org.id),  # CSRF: sign this with HMAC in production
    )
    return {"authorization_url": authorization_url}


@router.get("/callback")
async def sso_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Handle IdP callback, create/update user, return JWT.
    """
    # Exchange code for profile
    profile = workos_client.sso.get_profile_and_token(code)
    sso_profile = profile.profile

    # Find or create user
    user = await db.execute(
        select(User).where(User.email == sso_profile.email)
    )
    user = user.scalar_one_or_none()

    if not user:
        user = User(
            email=sso_profile.email,
            name=f"{sso_profile.first_name} {sso_profile.last_name}",
            organization_id=state,  # UUID from state parameter
            sso_subject_id=sso_profile.id,
            auth_method="sso",
            is_verified=True,  # IdP has verified the email
            role=UserRole.ANALYST,
        )
        db.add(user)
    else:
        user.sso_subject_id = sso_profile.id
        user.auth_method = "sso"
        user.last_sso_login = datetime.now(timezone.utc)

    await db.commit()

    # Issue JWT (same as password login)
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "org_id": str(user.organization_id),
        "auth_method": "sso",
    }
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
    }
```

#### Enforce SSO for Organization

Add check to existing login endpoint (`auth.py`):

```python
# In the login() function, BEFORE password verification:

if user and user.organization_id:
    org = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = org.scalar_one_or_none()
    if org and org.sso_enforce:
        raise HTTPException(
            status_code=403,
            detail="Your organization requires SSO login. Use SSO to sign in.",
        )
```

### 3.4 Supported Identity Providers

| IdP | Method | Notes |
|---|---|---|
| Azure AD / Entra ID | SAML 2.0 or OIDC | 90% of law firm market share |
| Okta | SAML 2.0 | Common in AmLaw 200 |
| Google Workspace | OIDC | Smaller firms, startups |
| OneLogin | SAML 2.0 | Some mid-market firms |
| PingIdentity | SAML 2.0 | Large enterprises |

---

## 4. Multi-Factor Authentication (MFA)

**Complexity: M | Priority: P0 | Timeline: Weeks 3-5**

### 4.1 MFA Strategy

Support three factors in priority order:

1. **TOTP** (Time-based One-Time Password) -- Google Authenticator, Authy, 1Password
2. **WebAuthn/FIDO2** -- YubiKey, Windows Hello, Touch ID
3. **SMS** (deprecated but required for some users) -- Twilio Verify

### 4.2 Database Changes

```sql
-- Migration: 003_mfa_support.sql

ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN mfa_method VARCHAR(20);  -- 'totp', 'webauthn', 'sms'
ALTER TABLE users ADD COLUMN mfa_secret_encrypted BYTEA;  -- AES-256 encrypted TOTP secret
ALTER TABLE users ADD COLUMN mfa_backup_codes_encrypted BYTEA;  -- AES-256 encrypted backup codes
ALTER TABLE users ADD COLUMN mfa_phone VARCHAR(20);  -- For SMS fallback
ALTER TABLE users ADD COLUMN mfa_enrolled_at TIMESTAMP;

-- WebAuthn credentials table (users can register multiple keys)
CREATE TABLE webauthn_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credential_id BYTEA NOT NULL UNIQUE,
    public_key BYTEA NOT NULL,
    sign_count INTEGER DEFAULT 0,
    device_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Organization-level MFA policy
ALTER TABLE organizations ADD COLUMN mfa_required BOOLEAN DEFAULT FALSE;
ALTER TABLE organizations ADD COLUMN mfa_grace_period_days INTEGER DEFAULT 7;
```

### 4.3 TOTP Implementation

```python
# backend/app/services/mfa_service.py (NEW FILE)

import pyotp
import secrets
import json
from cryptography.fernet import Fernet
from app.core.config import settings

class MFAService:
    """TOTP-based MFA with encrypted secret storage."""

    def __init__(self):
        # Derive Fernet key from SECRET_KEY for MFA secret encryption
        self._cipher = Fernet(settings.MFA_ENCRYPTION_KEY)

    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    def encrypt_secret(self, secret: str) -> bytes:
        """Encrypt TOTP secret before storing in database."""
        return self._cipher.encrypt(secret.encode())

    def decrypt_secret(self, encrypted: bytes) -> str:
        """Decrypt TOTP secret from database."""
        return self._cipher.decrypt(encrypted).decode()

    def generate_provisioning_uri(self, secret: str, email: str) -> str:
        """Generate QR code URI for authenticator app enrollment."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name="ContraRed")

    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify a TOTP code. Allows 1-step clock drift."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """Generate single-use backup codes."""
        return [secrets.token_hex(4).upper() for _ in range(count)]

    def encrypt_backup_codes(self, codes: list[str]) -> bytes:
        """Encrypt backup codes for storage."""
        return self._cipher.encrypt(json.dumps(codes).encode())

    def decrypt_backup_codes(self, encrypted: bytes) -> list[str]:
        """Decrypt backup codes."""
        return json.loads(self._cipher.decrypt(encrypted).decode())
```

### 4.4 Login Flow with MFA

Modify `auth.py` login to return a partial token when MFA is required:

```python
# Modified login flow:
# 1. Verify email/password --> if MFA not enabled, return tokens (current behavior)
# 2. If MFA enabled --> return a short-lived MFA challenge token (5 min TTL)
# 3. Client calls /auth/mfa/verify with challenge token + TOTP code
# 4. On success --> return full access + refresh tokens

@router.post("/mfa/verify")
async def verify_mfa(
    challenge_token: str,
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Step 2 of MFA login: verify TOTP code."""
    # Decode the challenge token (type="mfa_challenge")
    token_data = decode_token(challenge_token, expected_type="mfa_challenge")
    if not token_data:
        raise HTTPException(401, "Invalid or expired MFA challenge")

    user = await db.execute(select(User).where(User.id == token_data.user_id))
    user = user.scalar_one_or_none()
    if not user or not user.mfa_enabled:
        raise HTTPException(401, "MFA not configured")

    mfa_service = MFAService()
    secret = mfa_service.decrypt_secret(user.mfa_secret_encrypted)

    if not mfa_service.verify_totp(secret, code):
        # Check backup codes
        backup_codes = mfa_service.decrypt_backup_codes(user.mfa_backup_codes_encrypted)
        if code.upper() in backup_codes:
            backup_codes.remove(code.upper())
            user.mfa_backup_codes_encrypted = mfa_service.encrypt_backup_codes(backup_codes)
        else:
            raise HTTPException(401, "Invalid MFA code")

    # Issue full tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "org_id": str(user.organization_id),
        "mfa_verified": True,
    }
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )
```

### 4.5 Organization-Level MFA Enforcement

```python
# In get_current_user(), after user validation:
if user.organization:
    org = user.organization
    if org.mfa_required and not user.mfa_enabled:
        # Check grace period
        if user.created_at + timedelta(days=org.mfa_grace_period_days) < datetime.now(timezone.utc):
            raise HTTPException(403, "MFA enrollment required by your organization. Please enable MFA in settings.")
```

---

## 5. AI Data Protection

**Complexity: L | Priority: P0 | Timeline: Weeks 1-6**

### 5.1 Current Data Flow (INSECURE)

```
User (Word Add-in) --> ContraRed API --> Google Gemini Consumer API
                                          ^
                                          |
                                     NO DPA
                                     NO data residency
                                     Google may train on data
                                     Full contract text in transit
```

### 5.2 Target Data Flow (SECURE)

```
User (Word Add-in) --> ContraRed API --> [Metadata Redaction] --> Vertex AI (DPA)
                          |                                           |
                          v                                           v
                     [Audit Receipt]                          [VPC Service Controls]
                     [Processing Log]                         [CMEK Encryption]
                                                              [asia-south1 region]
                                                              [Zero retention]
```

### 5.3 Implementation Steps

#### Step 1: Vertex AI Migration

File: `backend/app/services/gemini_analyzer.py`

```python
# Replace google.generativeai with Vertex AI SDK
# BEFORE:
import google.generativeai as genai
genai.configure(api_key=settings.GEMINI_API_KEY)

# AFTER:
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

vertexai.init(
    project=settings.GCP_PROJECT_ID,
    location=settings.GCP_REGION,
)
```

#### Step 2: Add Pre-Processing Pipeline

Before sending to ANY AI provider:

1. **Redact PII** -- emails, phone numbers, addresses
2. **Check for privileged markers** -- warn if document contains privilege assertions
3. **Truncate to minimum necessary** -- do not send full 200KB documents if a clause-level call suffices
4. **Log processing receipt** -- hash of document, provider, region, timestamp

#### Step 3: Post-Processing Cleanup

After receiving AI response:

1. **Restore redacted PII** using the redaction map
2. **Validate response** -- ensure AI did not hallucinate PII back
3. **Purge prompt from memory** -- explicitly delete the prompt string
4. **Log completion** -- tokens used, latency, no content

#### Step 4: Enterprise Tier -- Private Deployment

For Enterprise customers who refuse cloud AI:

- Deploy a fine-tuned open model (Llama 3.1 70B) on customer's Azure subscription
- ContraRed provides the model weights and prompts
- Customer's data never leaves their tenant
- Higher cost, but absolute privilege protection

---

## 6. Leakage Vector Elimination

**Complexity: M | Priority: P0 | Timeline: Weeks 2-4**

### Vector 1: Gemini API Logs

**Risk:** Google logs API requests including full prompts containing contract text.
**Fix:** Migrate to Vertex AI with DPA (Section 2). Vertex AI DPA explicitly prohibits Google from using customer data for model training.
**Verification:** Review GCP audit logs. Enable VPC Service Controls to ensure no data exfiltration.

### Vector 2: Redis Cache

**Current code** (`cache_service.py` line 150):
```python
text_hash = hashlib.sha256(clause_text.encode()).hexdigest()[:16]
return f"ai:clause:{rule_id}:{text_hash}"
```

**Risk:** Cache keys contain only hashes (good), but cached VALUES store full AI responses which may echo contract text.

**Fix:**
```python
# Option A: Disable caching for privileged content (simple)
async def set(self, key: str, value: dict, ttl: int = 3600) -> bool:
    if not self._client:
        return False
    # Encrypt cached values
    encrypted = self._cipher.encrypt(json.dumps(value).encode())
    await self._client.setex(key, ttl, encrypted)

# Option B: Use Redis encryption at rest (Upstash TLS + encryption)
# Configure REDIS_URL with TLS: rediss://... (note double 's')

# Option C: Cache only non-sensitive metadata (explanation length, risk level)
# Never cache clause_text or suggested_fix in Redis
```

**Recommended: Option C** -- change the cache to store only structural metadata, never contract content.

### Vector 3: Server Logs

**Current code** (`main.py` line 61):
```python
logger.info(
    "method=%s path=%s status=%d duration=%.3fs ip=%s",
    request.method, request.url.path, response.status_code, ...
)
```

**Risk:** Currently safe (logs only method/path/status). BUT:
- `auth.py` line 172: `logger.error("Registration failed", exc_info=True)` -- stack traces may contain user data
- Gemini analyzer errors may log partial prompts

**Fix:**
```python
# backend/app/core/logging_config.py (NEW FILE)

import logging
import re

class SensitiveDataFilter(logging.Filter):
    """Strip PII and contract content from log records."""

    PATTERNS = [
        (re.compile(r'password["\s:=]+\S+', re.I), 'password=***'),
        (re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+'), '[EMAIL]'),
        (re.compile(r'Bearer\s+\S+'), 'Bearer ***'),
        (re.compile(r'api[_-]?key["\s:=]+\S+', re.I), 'api_key=***'),
    ]

    def filter(self, record):
        if record.exc_text:
            for pattern, replacement in self.PATTERNS:
                record.exc_text = pattern.sub(replacement, record.exc_text)
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True
```

Apply this filter to all loggers in `main.py`:

```python
logging.getLogger().addFilter(SensitiveDataFilter())
```

### Vector 4: Audit Log `details` Field

**Current code** (`audit_log.py` line 57):
```python
details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON metadata
```

**Risk:** The `details` field is free-text. Callers COULD (accidentally) store contract content. The docstring says "NEVER document content" but there is no enforcement.

**Fix:**
```python
# In log_audit_event(), validate details before storage:

FORBIDDEN_DETAIL_KEYS = {"contract_text", "clause_text", "document_content", "full_text", "body"}

async def log_audit_event(db, ..., details: Optional[str] = None, ...):
    # Enforce: no contract content in audit details
    if details:
        try:
            parsed = json.loads(details)
            if isinstance(parsed, dict):
                for key in FORBIDDEN_DETAIL_KEYS:
                    if key in parsed:
                        logger.warning(f"Blocked attempt to store '{key}' in audit log")
                        del parsed[key]
                details = json.dumps(parsed)
        except json.JSONDecodeError:
            pass
        # Hard limit on details length (prevent content dumps)
        if len(details) > 2000:
            details = details[:2000]
    ...
```

### Vector 5: Error Tracebacks

**Risk:** Unhandled exceptions in document analysis could leak contract text in 500 responses or error tracking services.

**Current mitigation** (partial): The `documents.py` endpoint catches exceptions, but the error messages sometimes include internal details.

**Fix:**
```python
# Global exception handler in main.py

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Never expose internal errors to clients."""
    logger.error(
        "Unhandled exception: %s (path=%s)",
        type(exc).__name__,  # Log type only, NOT message (may contain data)
        request.url.path,
        exc_info=True,  # Full trace goes to structured logging only
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
```

---

## 7. RBAC Overhaul

**Complexity: M | Priority: P1 | Timeline: Weeks 4-6**

### 7.1 Current State

Role hierarchy in `dependencies.py`:
```python
ROLE_HIERARCHY = {
    UserRole.USER: 0,        # Legacy
    UserRole.ANALYST: 0,
    UserRole.ADMIN: 1,
    UserRole.SUPER_ADMIN: 2,
}
```

This is too coarse. A law firm needs:

### 7.2 Target Role Hierarchy

| Role | Level | Permissions |
|---|---|---|
| **Viewer** | 0 | Read-only access to assigned documents. No AI analysis. No export. |
| **Reviewer** | 1 | Full analysis. Read/write on assigned documents. Export results. |
| **Manager** | 2 | Everything Reviewer + create/edit playbooks + assign documents + view team analytics. |
| **Admin** | 3 | Everything Manager + manage users + billing + SSO config + org settings. |
| **Super Admin** | 4 | Platform-level. ContraRed staff only. Cross-org access. |

### 7.3 Granular Permission System

```python
# backend/app/core/permissions.py (NEW FILE)

from enum import Enum
from typing import Set

class Permission(str, Enum):
    # Documents
    DOCUMENT_READ = "document:read"
    DOCUMENT_ANALYZE = "document:analyze"
    DOCUMENT_EXPORT = "document:export"
    DOCUMENT_DELETE = "document:delete"

    # Playbooks
    PLAYBOOK_READ = "playbook:read"
    PLAYBOOK_CREATE = "playbook:create"
    PLAYBOOK_EDIT = "playbook:edit"
    PLAYBOOK_DELETE = "playbook:delete"

    # Team
    TEAM_VIEW = "team:view"
    TEAM_INVITE = "team:invite"
    TEAM_REMOVE = "team:remove"
    TEAM_ASSIGN_ROLE = "team:assign_role"

    # Organization
    ORG_SETTINGS = "org:settings"
    ORG_BILLING = "org:billing"
    ORG_SSO = "org:sso"
    ORG_AUDIT_LOG = "org:audit_log"

    # Analytics
    ANALYTICS_PERSONAL = "analytics:personal"
    ANALYTICS_TEAM = "analytics:team"
    ANALYTICS_ORG = "analytics:org"

    # AI
    AI_GENERATE_FIX = "ai:generate_fix"
    AI_CLAUSE_LIBRARY = "ai:clause_library"


ROLE_PERMISSIONS: dict[str, Set[Permission]] = {
    "viewer": {
        Permission.DOCUMENT_READ,
        Permission.PLAYBOOK_READ,
        Permission.ANALYTICS_PERSONAL,
    },
    "reviewer": {
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_ANALYZE,
        Permission.DOCUMENT_EXPORT,
        Permission.PLAYBOOK_READ,
        Permission.AI_GENERATE_FIX,
        Permission.AI_CLAUSE_LIBRARY,
        Permission.ANALYTICS_PERSONAL,
    },
    "manager": {
        # Reviewer + management
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_ANALYZE,
        Permission.DOCUMENT_EXPORT,
        Permission.DOCUMENT_DELETE,
        Permission.PLAYBOOK_READ,
        Permission.PLAYBOOK_CREATE,
        Permission.PLAYBOOK_EDIT,
        Permission.PLAYBOOK_DELETE,
        Permission.AI_GENERATE_FIX,
        Permission.AI_CLAUSE_LIBRARY,
        Permission.TEAM_VIEW,
        Permission.TEAM_INVITE,
        Permission.ANALYTICS_PERSONAL,
        Permission.ANALYTICS_TEAM,
    },
    "admin": {
        # Manager + admin
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_ANALYZE,
        Permission.DOCUMENT_EXPORT,
        Permission.DOCUMENT_DELETE,
        Permission.PLAYBOOK_READ,
        Permission.PLAYBOOK_CREATE,
        Permission.PLAYBOOK_EDIT,
        Permission.PLAYBOOK_DELETE,
        Permission.AI_GENERATE_FIX,
        Permission.AI_CLAUSE_LIBRARY,
        Permission.TEAM_VIEW,
        Permission.TEAM_INVITE,
        Permission.TEAM_REMOVE,
        Permission.TEAM_ASSIGN_ROLE,
        Permission.ORG_SETTINGS,
        Permission.ORG_BILLING,
        Permission.ORG_SSO,
        Permission.ORG_AUDIT_LOG,
        Permission.ANALYTICS_PERSONAL,
        Permission.ANALYTICS_TEAM,
        Permission.ANALYTICS_ORG,
    },
}


def require_permission(permission: Permission):
    """FastAPI dependency: require specific permission."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        user_permissions = ROLE_PERMISSIONS.get(current_user.role.value, set())
        if permission not in user_permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions: {permission.value} required",
            )
        return current_user
    return _check
```

### 7.4 Document-Level Access Control

Beyond role-based access, add document-level assignments:

```sql
-- Migration: 004_document_access.sql

CREATE TABLE document_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_level VARCHAR(20) NOT NULL DEFAULT 'read',  -- 'read', 'write', 'admin'
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id, user_id)
);

CREATE INDEX idx_doc_access_user ON document_access(user_id);
CREATE INDEX idx_doc_access_doc ON document_access(document_id);
```

---

## 8. Session Security

**Complexity: M | Priority: P1 | Timeline: Weeks 3-5**

### 8.1 Current Vulnerabilities

1. **No token revocation** -- `logout` endpoint logs the event but does not invalidate the JWT
2. **No token rotation** -- Refresh tokens are not rotated on use (replay attacks possible)
3. **No session limits** -- A user can have unlimited active sessions
4. **No device tracking** -- No way to see "where am I logged in?"

### 8.2 Token Blacklist (Redis-based)

```python
# backend/app/services/token_service.py (NEW FILE)

class TokenService:
    """JWT token lifecycle management with Redis-backed revocation."""

    def __init__(self, redis_client):
        self._redis = redis_client

    async def revoke_token(self, jti: str, exp: datetime):
        """Add token JTI to blacklist until its natural expiry."""
        ttl = int((exp - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            await self._redis.setex(f"revoked:{jti}", ttl, "1")

    async def is_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked."""
        return await self._redis.exists(f"revoked:{jti}") > 0

    async def revoke_all_user_tokens(self, user_id: str):
        """Revoke all tokens for a user (forced logout everywhere)."""
        # Store a "revoked_before" timestamp; reject any token issued before this
        await self._redis.set(
            f"user_revoked_before:{user_id}",
            datetime.now(timezone.utc).isoformat(),
        )

    async def rotate_refresh_token(self, old_jti: str, old_exp: datetime) -> None:
        """Revoke old refresh token after issuing new one (rotation)."""
        await self.revoke_token(old_jti, old_exp)
```

### 8.3 Modify `decode_token` to Check Blacklist

```python
# In security.py, add blacklist check:

async def decode_token_with_revocation(
    token: str,
    token_service: TokenService,
    expected_type: str = "access",
) -> Optional[TokenData]:
    """Decode JWT and verify it hasn't been revoked."""
    token_data = decode_token(token, expected_type)
    if not token_data:
        return None

    # Check individual token revocation
    if token_data.jti and await token_service.is_revoked(token_data.jti):
        return None

    return token_data
```

### 8.4 Session Limits

```python
# Track active sessions per user
MAX_SESSIONS_PER_USER = 5

async def enforce_session_limit(user_id: str, token_service: TokenService):
    """Ensure user doesn't exceed max concurrent sessions."""
    active = await token_service.get_active_session_count(user_id)
    if active >= MAX_SESSIONS_PER_USER:
        # Revoke oldest session
        await token_service.revoke_oldest_session(user_id)
```

### 8.5 Security Headers Enhancement

Add to `SecurityHeadersMiddleware` in `main.py`:

```python
# Content Security Policy
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self' https://contrared-api.onrender.com; "
    "frame-ancestors 'none';"
)
```

---

## 9. Encryption at Rest and Field-Level

**Complexity: L | Priority: P1 | Timeline: Weeks 4-8**

### 9.1 Current Encryption State

| Layer | Status |
|---|---|
| In transit (API) | TLS 1.2+ via Render's load balancer |
| In transit (DB) | SSL=True to Supabase |
| In transit (Redis) | Not configured (no Redis in production) |
| At rest (DB) | Supabase default disk encryption (AES-256) |
| At rest (Redis) | N/A |
| Field-level | None |

### 9.2 Field-Level Encryption for Sensitive Data

Fields that MUST be encrypted at the application level (not just disk encryption):

| Model | Field | Why |
|---|---|---|
| `DocumentRisk` | `clause_text` | Contains contract excerpts |
| `DocumentRisk` | `ai_explanation` | May reference contract content |
| `DocumentRisk` | `suggested_fix` | Contains replacement clause text |
| `User` | `mfa_secret_encrypted` | TOTP secret (already planned as encrypted) |
| `AuditLog` | `details` | May contain metadata |

### 9.3 Implementation: Application-Level Encryption

```python
# backend/app/core/encryption.py (NEW FILE)

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64
import os

class FieldEncryptor:
    """
    AES-256 field-level encryption for database columns.

    Uses Fernet (AES-128-CBC + HMAC-SHA256) which provides
    authenticated encryption. Key is derived from ENCRYPTION_KEY
    env var using PBKDF2.
    """

    def __init__(self, master_key: str, salt: bytes = None):
        if not salt:
            salt = os.environ.get("ENCRYPTION_SALT", "contrared-salt-v1").encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string. Returns base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext."""
        return self._fernet.decrypt(ciphertext.encode()).decode()


# Global instance
_encryptor = None

def get_encryptor() -> FieldEncryptor:
    global _encryptor
    if _encryptor is None:
        from app.core.config import settings
        _encryptor = FieldEncryptor(settings.ENCRYPTION_KEY)
    return _encryptor
```

### 9.4 Config Addition

```python
# In config.py:
ENCRYPTION_KEY: str = ""  # Must be set in production. Min 32 chars.
MFA_ENCRYPTION_KEY: str = ""  # Separate key for MFA secrets.
```

### 9.5 SQLAlchemy Encrypted Column Type

```python
# backend/app/core/encrypted_type.py (NEW FILE)

from sqlalchemy import TypeDecorator, Text
from app.core.encryption import get_encryptor

class EncryptedText(TypeDecorator):
    """SQLAlchemy column type that transparently encrypts/decrypts."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return get_encryptor().encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return get_encryptor().decrypt(value)
        return value
```

Usage in models:

```python
# In DocumentRisk:
clause_text: Mapped[str] = mapped_column(EncryptedText, nullable=False)
ai_explanation: Mapped[Optional[str]] = mapped_column(EncryptedText, nullable=True)
suggested_fix: Mapped[Optional[str]] = mapped_column(EncryptedText, nullable=True)
```

### 9.6 Key Rotation Strategy

- Store key version in ciphertext prefix: `v1:encrypted_data`
- When rotating, re-encrypt all rows in a background migration
- Support decrypting with old key during rotation window
- Key stored in cloud secret manager (GCP Secret Manager or AWS Secrets Manager), NOT in env vars

---

## 10. Compliance Roadmap

**Complexity: XL | Priority: P1 | Timeline: Months 2-8**

### 10.1 SOC 2 Type II

**What it is:** Annual audit by a CPA firm verifying that your security controls operate effectively over time.

**Timeline: 6-9 months total**

| Phase | Duration | Activities |
|---|---|---|
| **Readiness** | Months 1-2 | Gap assessment, policy writing, tool selection |
| **Type I** | Month 3 | Point-in-time audit (controls exist) |
| **Observation** | Months 4-8 | Controls must operate for 3-6 months |
| **Type II** | Month 9 | Auditor reviews evidence from observation period |

**Controls to implement:**

| Trust Service Criteria | Current | Required |
|---|---|---|
| CC6.1 Logical Access | Partial (JWT + RBAC) | SSO + MFA + session management |
| CC6.2 Data Encryption | Partial (TLS) | Field-level encryption + encrypted backups |
| CC6.3 Transmission Security | TLS in transit | Enforce TLS 1.3, certificate pinning |
| CC6.6 System Boundaries | None | Network segmentation, firewall rules |
| CC6.7 Change Management | Git history | Formal PR review policy, deployment gates |
| CC6.8 Vulnerability Management | None | Dependency scanning, pen testing |
| CC7.1 Monitoring | Basic logging | SIEM integration, alerting |
| CC7.2 Incident Response | None | Documented IR plan, runbooks |
| CC8.1 Change Control | None | RFC process, CAB reviews |

**Recommended audit firm for Indian SaaS:** KPMG India, Deloitte India, or Prescient Assurance (SOC 2 specialist, affordable).

**Compliance automation tool:** Use **Vanta** or **Drata** to continuously monitor controls and auto-generate evidence for auditors. Cost: ~$10K-25K/year.

### 10.2 ISO 27001

**Overlap with SOC 2:** ~70% of controls overlap. If doing SOC 2 first, ISO 27001 is incremental.

**Additional requirements:**
- Formal ISMS (Information Security Management System)
- Risk register and treatment plan
- Management review meetings (quarterly)
- Internal audit program

**Timeline:** 3-4 months after SOC 2 Type I.

### 10.3 DPDP Act 2023 (India)

The Digital Personal Data Protection Act 2023 is India's GDPR equivalent. As a company processing contracts that contain Indian PII:

| Requirement | Implementation |
|---|---|
| Consent management | Add explicit consent flow for AI processing |
| Data localization | Process Indian contracts in `asia-south1` region |
| Right to erasure | Implement user data deletion endpoint |
| Breach notification | 72-hour notification to DPBI |
| Data Processing Agreement | Publish DPA template for customers |
| Data Protection Officer | Appoint DPO (can be part-time for startup) |
| Cross-border transfer | Document legal basis for any non-India processing |

### 10.4 Additional Certifications to Consider

| Certification | When | Why |
|---|---|---|
| HIPAA BAA | If serving healthcare law firms | Health data in contracts |
| ITAR compliance | If serving defense contractors | Export-controlled data |
| CCPA/CPRA | If serving California clients | Consumer data rights |
| GDPR DPA | If serving EU law firms | EU data protection |

---

## 11. Security Operations

**Complexity: L | Priority: P1 | Timeline: Ongoing**

### 11.1 Penetration Testing

| Type | Frequency | Scope | Vendor |
|---|---|---|---|
| **Application pen test** | Annually + after major releases | API, dashboard, Word add-in | BreachLock, Cobalt, or HackerOne |
| **Infrastructure pen test** | Annually | Render, Supabase, Netlify configs | Same vendor |
| **Red team exercise** | Every 18 months | Full kill chain simulation | Specialized firm |

**Budget estimate:** INR 5-15 lakh/year for annual pen tests.

### 11.2 Vulnerability Scanning

```yaml
# .github/workflows/security-scan.yml

name: Security Scan
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday scan

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Python dependency audit
        run: |
          pip install pip-audit
          pip-audit -r backend/requirements.txt

      - name: NPM audit (Dashboard)
        run: |
          cd dashboard
          npm audit --audit-level=high

      - name: NPM audit (Word Add-in)
        run: |
          cd ContraRed-PoC
          npm audit --audit-level=high

  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Bandit (Python SAST)
        run: |
          pip install bandit
          bandit -r backend/app/ -f json -o bandit-results.json || true

      - name: Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/python
            p/typescript
            p/security-audit
            p/owasp-top-ten

  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
```

### 11.3 Incident Response Plan

```
CONTRARED INCIDENT RESPONSE PLAN v1.0

SEVERITY LEVELS:
  P1 (Critical): Data breach, privilege compromise, production down
  P2 (High): Vulnerability exploited, unauthorized access attempt
  P3 (Medium): Security misconfiguration, failed pen test finding
  P4 (Low): Policy violation, minor vulnerability

RESPONSE TIMELINE:
  P1: 15 min acknowledge, 1 hr containment, 24 hr resolution
  P2: 1 hr acknowledge, 4 hr containment, 72 hr resolution
  P3: 24 hr acknowledge, 1 week resolution
  P4: 1 week acknowledge, 1 month resolution

STEPS:
  1. DETECT: Monitoring alerts, user reports, security scan
  2. TRIAGE: Classify severity, assign incident commander
  3. CONTAIN: Isolate affected systems, revoke compromised credentials
  4. ERADICATE: Remove threat, patch vulnerability
  5. RECOVER: Restore service, verify integrity
  6. POST-MORTEM: Root cause analysis, update controls, notify customers

NOTIFICATION:
  - Internal: Slack #security channel immediately
  - Customers: Within 72 hours for data breaches (DPDP requirement)
  - Regulators: Within 72 hours to DPBI (DPDP requirement)
  - Law enforcement: If criminal activity suspected

CONTACTS:
  - Incident Commander: [CTO]
  - Legal Counsel: [External counsel]
  - Forensics: [Retained firm]
  - PR/Comms: [Head of Comms]
```

### 11.4 Security Monitoring & Alerting

| Signal | Tool | Alert |
|---|---|---|
| Failed login bursts (>10/min) | Application logs + PagerDuty | Immediate |
| Unusual API patterns | Rate limiter metrics | Warning |
| New admin user created | Audit log trigger | Immediate |
| SSO configuration changed | Audit log trigger | Immediate |
| Dependency vulnerability (CVE) | GitHub Dependabot | Daily digest |
| TLS certificate expiry | Render/Netlify monitoring | 30 days before |
| Database connection anomalies | Supabase monitoring | Warning |

---

## 12. Implementation Priority & Timeline

### Phase 1: Stop the Bleeding (Weeks 1-4) -- Score: 3 -> 6

| # | Item | Complexity | Files Changed | Score Impact |
|---|---|---|---|---|
| 1 | Migrate Gemini consumer API to Vertex AI with DPA | L | `gemini_analyzer.py`, `ai_service.py`, `config.py` | +1.5 |
| 2 | Add metadata redaction before AI calls | M | New: `ai_data_protection.py` | +0.5 |
| 3 | Fix all 5 leakage vectors | M | `cache_service.py`, `main.py`, `audit_log.py`, new: `logging_config.py` | +0.5 |
| 4 | Implement token blacklist (logout actually works) | S | `security.py`, `auth.py`, new: `token_service.py` | +0.5 |

### Phase 2: Enterprise Readiness (Weeks 4-8) -- Score: 6 -> 8

| # | Item | Complexity | Files Changed | Score Impact |
|---|---|---|---|---|
| 5 | SSO/SAML via WorkOS | L | New: `sso.py`, `organization.py`, `auth.py`, migrations | +1.0 |
| 6 | MFA (TOTP + backup codes) | M | New: `mfa_service.py`, `auth.py`, `user.py`, migrations | +0.5 |
| 7 | RBAC overhaul (5-tier + permissions) | M | New: `permissions.py`, `dependencies.py`, `user.py` | +0.5 |

### Phase 3: Hardening (Weeks 8-12) -- Score: 8 -> 9

| # | Item | Complexity | Files Changed | Score Impact |
|---|---|---|---|---|
| 8 | Field-level encryption (AES-256) | L | New: `encryption.py`, `encrypted_type.py`, models, migration | +0.5 |
| 9 | Session management (rotation, limits, device tracking) | M | `token_service.py`, `auth.py` | +0.25 |
| 10 | Security scanning CI pipeline | S | New: `.github/workflows/security-scan.yml` | +0.25 |

### Phase 4: Compliance (Months 3-9) -- Score: 9 -> 10

| # | Item | Complexity | Files Changed | Score Impact |
|---|---|---|---|---|
| 11 | SOC 2 Type I readiness | XL | Policies, procedures, evidence collection | +0.5 |
| 12 | Penetration test + remediation | L | Varies by findings | +0.25 |
| 13 | DPDP Act compliance | L | Consent flows, DPO appointment, DPA templates | +0.25 |

### Resource Estimate

| Phase | Engineering Weeks | Cost Estimate (INR) |
|---|---|---|
| Phase 1 | 4 person-weeks | Internal |
| Phase 2 | 6 person-weeks | WorkOS: ~$125/mo per org |
| Phase 3 | 4 person-weeks | GCP: ~$200/mo for KMS |
| Phase 4 | 8 person-weeks | SOC 2 audit: 8-15 lakh, Vanta: ~8 lakh/yr |

---

## 13. Success Criteria

### What a Law Firm CISO Will Ask

A General Counsel or CISO at an AmLaw 100 / India Top 50 firm will evaluate ContraRed against this checklist. Every "No" is a deal-breaker.

| # | Question | Current | Target |
|---|---|---|---|
| 1 | "Does your platform support SSO with our Azure AD/Okta?" | No | Yes (WorkOS) |
| 2 | "Is MFA required for all users?" | No | Yes (TOTP + WebAuthn) |
| 3 | "Do you have SOC 2 Type II?" | No | Type I by Month 3, Type II by Month 9 |
| 4 | "Where is our data processed geographically?" | Unknown (Google's choice) | asia-south1 (Mumbai) with Vertex AI |
| 5 | "Can our data be used to train your AI models?" | Possibly (Gemini consumer terms) | No (Vertex AI DPA, zero retention) |
| 6 | "Do you have a DPA we can sign?" | No | Yes (templated, jurisdiction-specific) |
| 7 | "How do you protect attorney-client privilege?" | We don't | Metadata redaction, enterprise AI DPA, zero data retention, processing receipts |
| 8 | "Can we force SSO-only login for our organization?" | No | Yes (`sso_enforce` flag) |
| 9 | "What role-based access controls do you offer?" | 3 roles | 5 roles + granular permissions + document-level ACLs |
| 10 | "Can an admin force-logout all users?" | No | Yes (token revocation) |
| 11 | "Is data encrypted at rest beyond disk encryption?" | No | Yes (AES-256 field-level for contract content) |
| 12 | "When was your last penetration test?" | Never | Within last 12 months |
| 13 | "Do you have an incident response plan?" | No | Yes (documented, tested) |
| 14 | "Can you provide your security white paper?" | No | Yes (technical architecture document) |
| 15 | "Are you compliant with DPDP Act 2023?" | No | Yes (consent, data residency, DPO) |

### Definition of Done: Score 10/10

All of the following must be true:

- [ ] AI processing uses enterprise-grade API with executed DPA
- [ ] Zero contract text reaches any system without DPA coverage
- [ ] SSO works with Azure AD, Okta, and Google Workspace
- [ ] MFA is available and enforceable at the organization level
- [ ] 5-tier RBAC with granular permissions is enforced on every endpoint
- [ ] All 5 leakage vectors are closed with verifiable controls
- [ ] Field-level encryption protects contract content in the database
- [ ] Token revocation works (logout actually invalidates sessions)
- [ ] SOC 2 Type II report is issued
- [ ] Annual penetration test completed with no critical/high findings
- [ ] DPDP Act compliance documented and verified
- [ ] Incident response plan documented, contacts identified
- [ ] Security scanning runs on every PR and weekly
- [ ] A law firm CISO has reviewed and approved the security architecture

---

## Appendix A: New Environment Variables Required

```bash
# Vertex AI (replaces GEMINI_API_KEY)
GCP_PROJECT_ID=contrared-prod
GCP_REGION=asia-south1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# WorkOS (SSO)
WORKOS_API_KEY=sk_live_...
WORKOS_CLIENT_ID=client_...

# Encryption
ENCRYPTION_KEY=<64-char-random-hex>
MFA_ENCRYPTION_KEY=<base64-fernet-key>
ENCRYPTION_SALT=<random-salt>

# Redis (required for token revocation + session management)
REDIS_URL=rediss://default:password@redis-host:6379  # Note: rediss:// for TLS

# Security
MAX_SESSIONS_PER_USER=5
MFA_GRACE_PERIOD_DAYS=7
```

## Appendix B: New Python Dependencies

```txt
# requirements.txt additions
google-cloud-aiplatform>=1.40.0    # Vertex AI SDK (replaces google-generativeai)
workos>=4.0.0                       # SSO/SAML broker
pyotp>=2.9.0                        # TOTP for MFA
cryptography>=42.0.0                # Field-level encryption
py-webauthn>=2.0.0                  # FIDO2/WebAuthn support
pip-audit>=2.7.0                    # Dependency vulnerability scanning
bandit>=1.7.0                       # Python SAST (dev dependency)
```

## Appendix C: New Database Migrations Required

1. `002_sso_support.sql` -- SSO fields on organizations and users
2. `003_mfa_support.sql` -- MFA fields on users, webauthn_credentials table
3. `004_document_access.sql` -- Document-level ACLs
4. `005_session_tracking.sql` -- Active sessions table
5. `006_encrypt_sensitive_fields.sql` -- Re-encrypt existing data with field-level encryption
6. `007_rbac_migration.sql` -- Add viewer/reviewer/manager roles, migrate existing users
