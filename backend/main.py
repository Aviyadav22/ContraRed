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


import httpx
from fastapi.responses import Response

@app.get("/api/v1/documents/manifest", response_class=Response)
async def download_manifest():
    """
    Download the Word Add-in manifest.xml file.
    Fetches the raw file from GitHub and serves it with the correct
    Content-Disposition headers to force a download instead of displaying in browser.
    """
    github_url = "https://raw.githubusercontent.com/Aviyadav22/ContraRed/main/ContraRed-PoC/manifest.xml"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(github_url)
            
        if response.status_code != 200:
            from fastapi import HTTPException
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch manifest from repository")
            
        return Response(
            content=response.content,
            media_type="application/xml",
            headers={"Content-Disposition": 'attachment; filename="contrared-manifest.xml"'}
        )
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error serving manifest: {str(e)}")


@app.get("/health/db")
async def db_health_check():
    """Database connectivity check — returns actual error if DB is unreachable."""
    from sqlalchemy import text
    from app.db.session import engine
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "detail": str(e), "type": type(e).__name__}
