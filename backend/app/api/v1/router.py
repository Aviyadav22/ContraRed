"""
API V1 Router - Aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, documents, playbooks, billing

api_router = APIRouter()

# Auth endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# User management
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

# Document analysis
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"]
)

# Playbook management
api_router.include_router(
    playbooks.router,
    prefix="/playbooks",
    tags=["Playbooks"]
)

# Billing & Subscriptions
api_router.include_router(
    billing.router,
    prefix="/billing",
    tags=["Billing"]
)
