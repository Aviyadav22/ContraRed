"""
Consent Management API Endpoints - DPDP Act Compliance.

Provides endpoints for:
  - Viewing available consent purposes (public)
  - Viewing current privacy policy (public)
  - Checking and managing consent status (authenticated)
  - Granting and withdrawing consent (authenticated)
  - Downloading ISO 27560 receipts (authenticated)
  - Viewing consent event history (authenticated)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.consent_service import consent_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Request/Response Schemas ----

class ConsentGrantRequest(BaseModel):
    """Request to grant consent for specific purposes."""
    purpose_codes: List[str] = Field(..., min_length=1, description="List of purpose codes to grant consent for")
    privacy_policy_version: Optional[str] = Field(None, description="Checksum of accepted privacy policy version")


class ConsentWithdrawRequest(BaseModel):
    """Request to withdraw consent for specific purposes."""
    purpose_codes: List[str] = Field(..., min_length=1, description="List of purpose codes to withdraw consent from")
    reason: Optional[str] = Field(None, max_length=1000, description="Optional reason for withdrawal")


class ConsentPurposeResponse(BaseModel):
    code: str
    name: str
    description: str
    is_required: bool
    personal_data_categories: List[str]
    third_parties: List[str]
    retention_period: Optional[str]
    translations: dict = {}


class ConsentStatusPurpose(BaseModel):
    code: str
    name: str
    description: str
    is_required: bool
    granted: bool
    granted_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    personal_data_categories: List[str]
    third_parties: List[str]
    retention_period: Optional[str]
    translations: dict = {}


class ConsentStatusResponse(BaseModel):
    has_consent_record: bool
    consent_record_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    purposes: List[ConsentStatusPurpose]


class ConsentEventResponse(BaseModel):
    id: str
    event_type: str
    purpose_code: Optional[str]
    actor: str
    details: dict
    created_at: str


class ConsentReceiptResponse(BaseModel):
    id: str
    receipt_data: dict
    schema_version: str
    digital_signature: Optional[str]
    issued_at: str
    downloaded_at: Optional[str]


class PolicyResponse(BaseModel):
    id: str
    version: int
    title: str
    content: str
    language: str
    checksum: str
    effective_from: str


# ---- Public Endpoints (no auth required) ----

@router.get("/purposes", response_model=List[ConsentPurposeResponse])
async def list_purposes(db: AsyncSession = Depends(get_db)):
    """List all active consent purposes with descriptions.

    Public endpoint — shown during registration and in consent notices.
    Returns purpose details including data categories, third parties,
    and retention periods as required by DPDP Act Section 5 (Notice).
    """
    return await consent_service.get_purposes(db)


@router.get("/policy/current", response_model=Optional[PolicyResponse])
async def get_current_policy(
    language: str = "en",
    db: AsyncSession = Depends(get_db),
):
    """Get the current active privacy policy.

    Public endpoint — users must be able to review the policy before
    granting consent (DPDP Act Section 6 — informed consent).
    """
    policy = await consent_service.get_current_policy(db, language=language)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active privacy policy found",
        )
    return policy


# ---- Authenticated Endpoints ----

@router.get("/status", response_model=ConsentStatusResponse)
async def get_consent_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's consent status for all purposes.

    Returns the grant/withdraw state for each purpose, suitable for
    rendering the consent preference center.
    """
    return await consent_service.get_consent_status(db, current_user.id)


@router.post("/grant")
async def grant_consent(
    request: Request,
    body: ConsentGrantRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Grant consent for specified purposes.

    Creates consent records and per-purpose grants. Generates an
    ISO 27560 consent receipt. Emits immutable audit events.

    DPDP Act Section 6: Consent must be free, specific, informed,
    unconditional, and unambiguous.
    """
    try:
        # Look up policy version if checksum provided
        policy_version_id = None
        if body.privacy_policy_version:
            from sqlalchemy import select
            from app.models.consent import ConsentPolicy
            result = await db.execute(
                select(ConsentPolicy.id)
                .where(ConsentPolicy.checksum == body.privacy_policy_version)
                .limit(1)
            )
            policy_version_id = result.scalar()

        result = await consent_service.grant_consent(
            db=db,
            subject_id=current_user.id,
            purpose_codes=body.purpose_codes,
            policy_version_id=policy_version_id,
            organization_id=current_user.organization_id,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/withdraw")
async def withdraw_consent(
    request: Request,
    body: ConsentWithdrawRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Withdraw consent for specified purposes.

    DPDP Act Section 6(6): Withdrawal must be as easy as giving consent.
    This endpoint mirrors the grant endpoint's simplicity.
    """
    try:
        result = await consent_service.withdraw_consent(
            db=db,
            subject_id=current_user.id,
            purpose_codes=body.purpose_codes,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            reason=body.reason,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history", response_model=List[ConsentEventResponse])
async def get_consent_history(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """View consent event history (audit trail).

    Returns chronological list of all consent actions taken by or
    affecting this user.
    """
    return await consent_service.get_consent_history(
        db, current_user.id, limit=min(limit, 200), offset=offset
    )


@router.get("/receipts", response_model=List[ConsentReceiptResponse])
async def get_consent_receipts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download consent receipts (ISO 27560 JSON-LD format).

    Machine-readable consent records as required by DPDP Act
    for Consent Manager interoperability.
    """
    return await consent_service.get_receipts(db, current_user.id)


# ---- Helpers ----

def _get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP, respecting X-Forwarded-For from trusted proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
