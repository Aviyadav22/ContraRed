"""
Application configuration using Pydantic Settings.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # Application
    APP_NAME: str = "ContraRed"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/contrared"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
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
    
    # CORS - Allow Word Add-in and Dashboard origins
    CORS_ORIGINS: List[str] = [
        "https://localhost:3000",  # Word Add-in (HTTPS)
        "http://localhost:3000",   # Word Add-in (HTTP dev)
        "https://localhost:5173",  # Dashboard (HTTPS)
        "http://localhost:5173",   # Dashboard (Vite dev)
    ]
    
    # Subscription Limits
    FREE_TIER_SCANS: int = 5
    PRO_TIER_SCANS: int = -1  # Unlimited
    ENTERPRISE_INCLUDED_SCANS: int = 500
    
    # Enterprise: Zero Data Retention
    # When True: Document text is processed in RAM only, never stored
    ZERO_DATA_RETENTION: bool = True
    
    # Analysis Strategy: "demo" (Omni-Context) or "production" (Hybrid Sentinel)
    ANALYSIS_MODE: str = "demo"
    
    # Fuzzy matching threshold for redline implementer (0.0-1.0)
    FUZZY_MATCH_THRESHOLD: float = 0.85
    
    # Azure OpenAI deployment mapping for Hybrid Sentinel
    # Scout (Pass 1): Fast, cheap model for flagging risky sections
    # Surgeon (Pass 2): Powerful model for precise redline generation
    AZURE_OPENAI_SCOUT_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_SURGEON_DEPLOYMENT: str = "gpt-4o"
    
    # Google Gemini API (primary AI provider)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_SCOUT_MODEL: str = "gemini-2.0-flash"
    GEMINI_SURGEON_MODEL: str = "gemini-2.0-flash"
    
    # AI Provider selection: "gemini" or "azure"
    AI_PROVIDER: str = "gemini"


settings = Settings()
