"""
Grievance Redressal API Endpoints - DPDP Act Section 13.

Provides endpoints for Data Principals to submit and track grievances.
90-day SLA is auto-enforced via database trigger.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User, UserRole
from app.models.consent import Grievance, GrievanceCategory, GrievanceStatus
from app.services.consent_service import consent_service
from app.models.consent import ConsentEventType

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class GrievanceSubmitBody(BaseModel):
    category: str = Field(..., description="Category: consent_violation, data_breach, processing_error, rights_denial, unauthorized_processing, other")
    description: str = Field(..., min_length=10, max_length=5000)
    evidence: Optional[dict] = Field(None, description="Optional evidence references")


class GrievanceUpdateBody(BaseModel):
    """Admin-only: update grievance status."""
    status: str = Field(..., description="New status")
    resolution_notes: Optional[str] = Field(None, max_length=5000)


class GrievanceResponse(BaseModel):
    id: str
    category: str
    description: str
    status: str
    submitted_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_deadline: Optional[str] = None
    resolution_notes: Optional[str] = None


# ---- Endpoints ----

@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_grievance(
    body: GrievanceSubmitBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a grievance (DPDP Section 13).

    All Data Principals have the right to grievance redressal.
    90-day resolution deadline is automatically set.
    """
    # Validate category
    valid_categories = [c.value for c in GrievanceCategory]
    if body.category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {valid_categories}",
        )

    grievance = Grievance(
        subject_id=current_user.id,
        organization_id=current_user.organization_id,
        category=body.category,
        description=body.description,
        evidence=body.evidence or {},
    )
    db.add(grievance)

    # Record consent event
    await consent_service._record_event(
        db, None, current_user.id,
        ConsentEventType.GRIEVANCE_FILED.value,
        details={"category": body.category, "grievance_id": str(grievance.id)},
    )

    await db.commit()
    await db.refresh(grievance)

    return {
        "id": str(grievance.id),
        "category": grievance.category,
        "status": grievance.status,
        "submitted_at": grievance.submitted_at.isoformat(),
        "resolution_deadline": grievance.resolution_deadline.isoformat() if grievance.resolution_deadline else None,
        "message": "Your grievance has been submitted. We will acknowledge it within 7 days and resolve within 90 days as per DPDP Act.",
    }


@router.get("/", response_model=List[GrievanceResponse])
async def list_grievances(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List grievances for the current user."""
    result = await db.execute(
        select(Grievance)
        .where(Grievance.subject_id == current_user.id)
        .order_by(desc(Grievance.submitted_at))
    )
    grievances = result.scalars().all()
    return [
        {
            "id": str(g.id),
            "category": g.category,
            "description": g.description,
            "status": g.status,
            "submitted_at": g.submitted_at.isoformat(),
            "acknowledged_at": g.acknowledged_at.isoformat() if g.acknowledged_at else None,
            "resolved_at": g.resolved_at.isoformat() if g.resolved_at else None,
            "resolution_deadline": g.resolution_deadline.isoformat() if g.resolution_deadline else None,
            "resolution_notes": g.resolution_notes,
        }
        for g in grievances
    ]


@router.get("/{grievance_id}", response_model=GrievanceResponse)
async def get_grievance(
    grievance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific grievance."""
    import uuid
    try:
        g_uuid = uuid.UUID(grievance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid grievance ID")

    result = await db.execute(
        select(Grievance)
        .where(Grievance.id == g_uuid, Grievance.subject_id == current_user.id)
    )
    g = result.scalar()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")

    return {
        "id": str(g.id),
        "category": g.category,
        "description": g.description,
        "status": g.status,
        "submitted_at": g.submitted_at.isoformat(),
        "acknowledged_at": g.acknowledged_at.isoformat() if g.acknowledged_at else None,
        "resolved_at": g.resolved_at.isoformat() if g.resolved_at else None,
        "resolution_deadline": g.resolution_deadline.isoformat() if g.resolution_deadline else None,
        "resolution_notes": g.resolution_notes,
    }


@router.patch("/{grievance_id}")
async def update_grievance(
    grievance_id: str,
    body: GrievanceUpdateBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update grievance status (admin/DPO only)."""
    import uuid
    from datetime import datetime, timezone

    # Check admin permissions
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Only admins can update grievance status")

    try:
        g_uuid = uuid.UUID(grievance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid grievance ID")

    result = await db.execute(select(Grievance).where(Grievance.id == g_uuid))
    g = result.scalar()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")

    valid_statuses = [s.value for s in GrievanceStatus]
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    now = datetime.now(timezone.utc)
    g.status = body.status
    if body.resolution_notes:
        g.resolution_notes = body.resolution_notes
    if body.status == GrievanceStatus.ACKNOWLEDGED.value and not g.acknowledged_at:
        g.acknowledged_at = now
    if body.status == GrievanceStatus.RESOLVED.value and not g.resolved_at:
        g.resolved_at = now

    await db.commit()

    return {"id": str(g.id), "status": g.status, "message": "Grievance updated successfully."}
