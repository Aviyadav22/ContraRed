"""
API V1 Router - Aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, documents, playbooks, billing, audit, team, clauses, templates, analytics

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

# Audit Logs
api_router.include_router(
    audit.router,
    prefix="/audit-logs",
    tags=["Audit Logs"]
)

# Team Management
api_router.include_router(
    team.router,
    prefix="/team",
    tags=["Team Management"]
)

# Clause Library
api_router.include_router(
    clauses.router,
    prefix="/clauses",
    tags=["Clause Library"]
)

# Template Library
api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["Templates"]
)

# Analytics
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)
