"""
Data Principal Rights API Endpoints - DPDP Act Sections 11-14.

Provides endpoints for:
  - Right to Access (data export)
  - Right to Correction
  - Right to Erasure (account deletion)
  - Right to Nomination (authorized representative)
  - Request status tracking (90-day SLA)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.consent import (
    RightsRequest, RightsRequestType, RightsRequestStatus,
    ConsentNomination, ConsentEvent, ConsentEventType,
)
from app.services.consent_service import consent_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class AccessRequestBody(BaseModel):
    """Request data export."""
    notes: Optional[str] = Field(None, max_length=1000)


class CorrectionRequestBody(BaseModel):
    """Request data correction."""
    field_name: str = Field(..., max_length=255, description="Which data field needs correction")
    current_value: Optional[str] = Field(None, max_length=1000)
    corrected_value: str = Field(..., max_length=1000)
    reason: Optional[str] = Field(None, max_length=1000)


class ErasureRequestBody(BaseModel):
    """Request account deletion / data erasure."""
    reason: Optional[str] = Field(None, max_length=1000)
    confirm: bool = Field(..., description="Must be true to confirm erasure request")


class NominationBody(BaseModel):
    """Designate authorized representative (DPDP Section 14)."""
    nominee_name: str = Field(..., min_length=1, max_length=255)
    nominee_email: Optional[str] = Field(None, max_length=255)
    nominee_phone: Optional[str] = Field(None, max_length=20)
    relationship: Optional[str] = Field(None, max_length=100)


class RightsRequestResponse(BaseModel):
    id: str
    request_type: str
    status: str
    request_details: Optional[dict] = None
    response_details: Optional[dict] = None
    submitted_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_deadline: Optional[str] = None
    resolution_notes: Optional[str] = None


class NominationResponse(BaseModel):
    id: str
    nominee_name: str
    nominee_email: Optional[str]
    nominee_phone: Optional[str]
    relationship: Optional[str]
    is_active: bool
    created_at: str


# ---- Endpoints ----

@router.post("/access", status_code=status.HTTP_201_CREATED)
async def request_data_access(
    body: AccessRequestBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Request a copy of all personal data (DPDP Section 11).

    Creates an async export job. The export will be available for
    download once processed. 90-day SLA applies.
    """
    req = RightsRequest(
        subject_id=current_user.id,
        organization_id=current_user.organization_id,
        request_type=RightsRequestType.ACCESS.value,
        status=RightsRequestStatus.SUBMITTED.value,
        request_details={"notes": body.notes} if body.notes else {},
    )
    db.add(req)

    # Record consent event
    await consent_service._record_event(
        db, None, current_user.id,
        ConsentEventType.RIGHTS_REQUEST.value,
        details={"request_type": "access", "request_id": str(req.id)},
    )

    await db.commit()
    await db.refresh(req)

    return {
        "id": str(req.id),
        "request_type": req.request_type,
        "status": req.status,
        "submitted_at": req.submitted_at.isoformat(),
        "resolution_deadline": req.resolution_deadline.isoformat() if req.resolution_deadline else None,
        "message": "Your data access request has been submitted. You will be notified when your data export is ready.",
    }


@router.post("/correction", status_code=status.HTTP_201_CREATED)
async def request_data_correction(
    body: CorrectionRequestBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Request correction of inaccurate personal data (DPDP Section 12)."""
    req = RightsRequest(
        subject_id=current_user.id,
        organization_id=current_user.organization_id,
        request_type=RightsRequestType.CORRECTION.value,
        status=RightsRequestStatus.SUBMITTED.value,
        request_details={
            "field_name": body.field_name,
            "current_value": body.current_value,
            "corrected_value": body.corrected_value,
            "reason": body.reason,
        },
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    return {
        "id": str(req.id),
        "request_type": req.request_type,
        "status": req.status,
        "submitted_at": req.submitted_at.isoformat(),
        "resolution_deadline": req.resolution_deadline.isoformat() if req.resolution_deadline else None,
        "message": "Your data correction request has been submitted.",
    }


@router.post("/erasure", status_code=status.HTTP_201_CREATED)
async def request_data_erasure(
    body: ErasureRequestBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Request erasure of personal data / account deletion (DPDP Section 12).

    This does not immediately delete the account. The request is processed
    according to the 90-day SLA, with legal retention obligations respected.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm the erasure request by setting confirm=true",
        )

    req = RightsRequest(
        subject_id=current_user.id,
        organization_id=current_user.organization_id,
        request_type=RightsRequestType.ERASURE.value,
        status=RightsRequestStatus.SUBMITTED.value,
        request_details={"reason": body.reason} if body.reason else {},
    )
    db.add(req)

    await consent_service._record_event(
        db, None, current_user.id,
        ConsentEventType.RIGHTS_REQUEST.value,
        details={"request_type": "erasure", "request_id": str(req.id)},
    )

    await db.commit()
    await db.refresh(req)

    return {
        "id": str(req.id),
        "request_type": req.request_type,
        "status": req.status,
        "submitted_at": req.submitted_at.isoformat(),
        "resolution_deadline": req.resolution_deadline.isoformat() if req.resolution_deadline else None,
        "message": "Your account deletion request has been submitted. Your data will be anonymised within the DPDP-mandated 90-day period.",
    }


@router.get("/requests", response_model=List[RightsRequestResponse])
async def list_rights_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all rights requests for the current user."""
    result = await db.execute(
        select(RightsRequest)
        .where(RightsRequest.subject_id == current_user.id)
        .order_by(desc(RightsRequest.submitted_at))
    )
    requests = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "request_type": r.request_type,
            "status": r.status,
            "request_details": r.request_details,
            "response_details": r.response_details,
            "submitted_at": r.submitted_at.isoformat(),
            "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            "resolution_deadline": r.resolution_deadline.isoformat() if r.resolution_deadline else None,
            "resolution_notes": r.resolution_notes,
        }
        for r in requests
    ]


@router.get("/requests/{request_id}", response_model=RightsRequestResponse)
async def get_rights_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific rights request."""
    import uuid
    try:
        req_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID")

    result = await db.execute(
        select(RightsRequest)
        .where(RightsRequest.id == req_uuid, RightsRequest.subject_id == current_user.id)
    )
    req = result.scalar()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    return {
        "id": str(req.id),
        "request_type": req.request_type,
        "status": req.status,
        "request_details": req.request_details,
        "response_details": req.response_details,
        "submitted_at": req.submitted_at.isoformat(),
        "acknowledged_at": req.acknowledged_at.isoformat() if req.acknowledged_at else None,
        "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
        "resolution_deadline": req.resolution_deadline.isoformat() if req.resolution_deadline else None,
        "resolution_notes": req.resolution_notes,
    }


# ---- Nominations ----

@router.post("/nomination", status_code=status.HTTP_201_CREATED)
async def create_nomination(
    body: NominationBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Designate an authorized representative (DPDP Section 14).

    The nominee can exercise your rights in case of death or incapacity.
    """
    nomination = ConsentNomination(
        subject_id=current_user.id,
        nominee_name=body.nominee_name,
        nominee_email=body.nominee_email,
        nominee_phone=body.nominee_phone,
        relationship=body.relationship,
    )
    db.add(nomination)
    await db.commit()
    await db.refresh(nomination)

    return {
        "id": str(nomination.id),
        "nominee_name": nomination.nominee_name,
        "is_active": nomination.is_active,
        "message": "Nominee registered successfully.",
    }


@router.get("/nominations", response_model=List[NominationResponse])
async def list_nominations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active nominations."""
    result = await db.execute(
        select(ConsentNomination)
        .where(
            ConsentNomination.subject_id == current_user.id,
            ConsentNomination.is_active == True,
        )
    )
    noms = result.scalars().all()
    return [
        {
            "id": str(n.id),
            "nominee_name": n.nominee_name,
            "nominee_email": n.nominee_email,
            "nominee_phone": n.nominee_phone,
            "relationship": n.relationship,
            "is_active": n.is_active,
            "created_at": n.created_at.isoformat(),
        }
        for n in noms
    ]


@router.delete("/nominations/{nomination_id}")
async def revoke_nomination(
    nomination_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke a nomination."""
    import uuid
    from datetime import datetime, timezone

    try:
        nom_uuid = uuid.UUID(nomination_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid nomination ID")

    result = await db.execute(
        select(ConsentNomination)
        .where(
            ConsentNomination.id == nom_uuid,
            ConsentNomination.subject_id == current_user.id,
        )
    )
    nomination = result.scalar()
    if not nomination:
        raise HTTPException(status_code=404, detail="Nomination not found")

    nomination.is_active = False
    nomination.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Nomination revoked successfully."}
