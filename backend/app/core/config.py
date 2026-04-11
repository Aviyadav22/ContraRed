"""
Application configuration using Pydantic Settings.
"""

import logging
import secrets
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_config_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "ContraRed"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v, info):
        """Ensure DATABASE_URL is set in production."""
        import os
        if not v and os.environ.get("DEBUG", "").lower() != "true":
            raise ValueError(
                "DATABASE_URL must be set. "
                "Provide a valid PostgreSQL connection string."
            )
        return v

    # Redis — STRONGLY RECOMMENDED for production
    # Enables: AI result caching (20-40% cost savings), token blacklist persistence
    # Free tier: Upstash (https://upstash.com) — $0/month for 10K commands/day
    # Set: REDIS_URL=redis://default:password@hostname:port
    REDIS_URL: str = ""

    # JWT Authentication
    SECRET_KEY: str = ""

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v, info):
        """Ensure SECRET_KEY is set and sufficiently long."""
        import os
        # Check DEBUG from multiple sources (env var or already-parsed values)
        is_debug = (
            os.environ.get("DEBUG", "").lower() == "true"
            or (info.data.get("DEBUG") is True if info.data else False)
        )
        if not v or v.startswith("your-"):
            if not is_debug:
                raise ValueError(
                    "SECRET_KEY must be set to a secure value (min 32 chars). "
                    "Never use the default placeholder in production."
                )
            # Generate a random key per startup in debug mode
            return secrets.token_hex(32)
        return v
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT_GPT4: str = "gpt-4o"
    AZURE_OPENAI_DEPLOYMENT_MINI: str = "gpt-4o-mini"
    
    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_PLAN_STARTER_ID: str = ""
    RAZORPAY_PLAN_PRO_ID: str = ""
    RAZORPAY_PLAN_BUSINESS_ID: str = ""
    RAZORPAY_PLAN_ENTERPRISE_ID: str = ""

    # WorkOS (SSO/SAML brokering) — optional, degrades gracefully like Redis
    WORKOS_API_KEY: str = ""
    WORKOS_CLIENT_ID: str = ""
    
    # CORS - Allow Word Add-in and Dashboard origins
    CORS_ORIGINS: List[str] = [
        "https://localhost:3000",  # Word Add-in (HTTPS)
        "http://localhost:3000",   # Word Add-in (HTTP dev)
        "https://localhost:5173",  # Dashboard (HTTPS)
        "http://localhost:5173",   # Dashboard (Vite dev)
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from JSON string env var."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Support comma-separated string fallback
                return [origin.strip() for origin in v.split(",")]
        return v
    
    # Cookie-based auth (HttpOnly, Secure, SameSite=None for cross-origin)
    COOKIE_DOMAIN: str = ""  # Leave empty for default (response origin)
    COOKIE_SECURE: bool = True  # Must be True for SameSite=None
    COOKIE_SAMESITE: str = "none"  # "none" required for cross-origin (add-in iframe)

    # Subscription Limits (Phase 3 — tier inversion fix)
    FREE_TIER_SCANS: int = 5
    STARTER_TIER_SCANS: int = 50
    PRO_TIER_SCANS: int = 200
    BUSINESS_TIER_SCANS: int = 1000
    ENTERPRISE_INCLUDED_SCANS: int = -1  # Unlimited

    # Stripe (USD/EUR/GBP payments — optional, degrades gracefully)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # Enterprise: Zero Data Retention
    # When True: Document text is processed in RAM only, never stored
    ZERO_DATA_RETENTION: bool = True
    
    # Analysis Strategy: "demo" (Omni-Context) or "production" (Hybrid Sentinel)
    ANALYSIS_MODE: str = "production"
    
    # Fuzzy matching threshold for redline implementer (0.0-1.0)
    FUZZY_MATCH_THRESHOLD: float = 0.85
    
    # Azure OpenAI deployment mapping for Hybrid Sentinel
    # Scout (Pass 1): Fast, cheap model for flagging risky sections
    # Surgeon (Pass 2): Powerful model for precise redline generation
    AZURE_OPENAI_SCOUT_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_SURGEON_DEPLOYMENT: str = "gpt-4o"
    
    # Vertex AI (REQUIRED for AI features — consumer Gemini API is PROHIBITED)
    # Contract data must not transit public Google AI endpoints.
    # Vertex AI provides: project-level IAM, audit logging, data residency.
    VERTEX_PROJECT_ID: str = ""
    VERTEX_LOCATION: str = "global"  # 'global' supports both 2.5 and 3.x models

    # Gemini model names (used via Vertex AI, NOT consumer API)
    GEMINI_MODEL: str = "gemini-3.1-pro-preview"             # Pro model for all AI tasks
    GEMINI_ANALYSIS_MODEL: str = "gemini-3.1-pro-preview"    # Pro model for full contract analysis
    GEMINI_SCOUT_MODEL: str = "gemini-3-flash-preview"       # Flash for fast clause extraction
    GEMINI_SURGEON_MODEL: str = "gemini-3.1-pro-preview"     # Pro for fix generation (quality matters)

    # AI Provider selection: "gemini" (via Vertex AI) or "azure"
    AI_PROVIDER: str = "gemini"

    # Field-level encryption for stored clause text (AES-256 via Fernet)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    @field_validator("ENCRYPTION_KEY", mode="before")
    @classmethod
    def validate_encryption_key(cls, v, info):
        """Require ENCRYPTION_KEY in production; warn in development."""
        import os
        if not v:
            is_debug = (
                os.environ.get("DEBUG", "").lower() == "true"
                or (info.data.get("DEBUG") is True if info.data else False)
            )
            if is_debug:
                _config_logger.warning(
                    "ENCRYPTION_KEY is not set. Field-level encryption is disabled. "
                    "Set ENCRYPTION_KEY for production use."
                )
            else:
                raise ValueError(
                    "ENCRYPTION_KEY is required in production. "
                    "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
        return v

    # Token blacklist TTL (seconds) — how long revoked tokens stay in blacklist
    TOKEN_BLACKLIST_TTL_SECONDS: int = 604800  # 7 days (must cover REFRESH_TOKEN_EXPIRE_DAYS)

    # Frontend URL (for redirect links in emails, etc.)
    FRONTEND_URL: str = "http://localhost:5173"

    # Trusted proxy hosts for X-Forwarded-For processing
    TRUSTED_PROXY_HOSTS: str = "127.0.0.1"

    # Resend (transactional email — password resets, notifications)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "ContraRed <noreply@contrared.com>"

    # Sentry (error monitoring — optional, degrades gracefully)
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 10% of transactions


settings = Settings()

# Production safety checks (run at import time)
if not settings.DEBUG:
    _all_localhost = all("localhost" in origin for origin in settings.CORS_ORIGINS)
    if _all_localhost and settings.CORS_ORIGINS:
        _config_logger.critical(
            "CORS_ORIGINS contains only localhost origins in production (DEBUG=False). "
            "Set CORS_ORIGINS to include your production domains."
        )
    if "localhost" in settings.FRONTEND_URL:
        _config_logger.critical(
            "FRONTEND_URL is set to localhost in production (DEBUG=False). "
            "Password reset emails will link to localhost. Set FRONTEND_URL to your production URL."
        )
