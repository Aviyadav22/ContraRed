"""
ContraRed Backend - AI Contract Redlining API

Main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup - non-fatal DB init (app stays healthy even if DB is temporarily unreachable)
    try:
        await init_db()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"DB init failed on startup: {e}. App will still start.")
    yield
    # Shutdown
    pass


app = FastAPI(
    title="ContraRed API",
    description="AI-powered contract redlining and review platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
