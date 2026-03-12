"""
Audit log query endpoints.
Provides filtered, paginated access to the audit trail.
Scoped by role: analysts see own logs, admins see org logs, super_admins see all.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.api.v1.endpoints.auth import get_current_user
from app.api.dependencies import ROLE_HIERARCHY


router = APIRouter()


class AuditLogResponse(BaseModel):
    id: str
    user_email: str
    action: str
    resource_type: str
    resource_name: str
    timestamp: str
    ip_address: Optional[str] = None
    status: str
    risk_count: Optional[int] = None
    details: Optional[str] = None


class AuditLogPage(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=AuditLogPage)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    user_email: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Query audit logs with filters and pagination.
    - ANALYST/USER: see only own logs
    - ADMIN: see all org logs
    - SUPER_ADMIN: see all logs
    """
    query = select(AuditLog)

    # Scope based on role
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    if user_level >= ROLE_HIERARCHY[UserRole.SUPER_ADMIN]:
        pass  # No filter — see all
    elif user_level >= ROLE_HIERARCHY[UserRole.ADMIN]:
        if current_user.organization_id:
            query = query.where(AuditLog.organization_id == current_user.organization_id)
        else:
            query = query.where(AuditLog.user_id == current_user.id)
    else:
        query = query.where(AuditLog.user_id == current_user.id)

    # Apply filters
    if action:
        query = query.where(AuditLog.action == action)
    if user_email:
        escaped = user_email.replace("%", "\\%").replace("_", "\\_")
        query = query.where(AuditLog.user_email.ilike(f"%{escaped}%"))
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(AuditLog.timestamp >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(AuditLog.timestamp <= dt)
        except ValueError:
            pass

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(desc(AuditLog.timestamp))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogPage(
        items=[
            AuditLogResponse(
                id=str(log.id),
                user_email=log.user_email or "",
                action=log.action,
                resource_type=log.resource_type,
                resource_name=log.resource_name,
                timestamp=log.timestamp.isoformat() if log.timestamp else "",
                ip_address=log.ip_address,
                status=log.status,
                risk_count=log.risk_count,
                details=log.details,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# Hash Chain Verification (Phase 2.4)
# ============================================================================

class ChainVerificationResult(BaseModel):
    valid: bool
    total_entries: int
    verified_entries: int
    first_broken_at: Optional[int] = None
    message: str


@router.get("/verify", response_model=ChainVerificationResult)
async def verify_audit_chain(
    limit: int = Query(1000, ge=1, le=10000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify the integrity of the audit log hash chain.

    Walks the chain from the beginning and verifies each entry's hash
    matches the computed hash from its fields + previous entry's hash.

    Only accessible to ADMIN+ roles.
    """
    import hashlib

    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    if user_level < ROLE_HIERARCHY[UserRole.ADMIN]:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to verify audit chain",
        )

    # Load entries ordered by sequence
    query = (
        select(AuditLog)
        .where(AuditLog.sequence_number.isnot(None))
        .order_by(AuditLog.sequence_number.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    entries = result.scalars().all()

    if not entries:
        return ChainVerificationResult(
            valid=True,
            total_entries=0,
            verified_entries=0,
            message="No hash-chained entries found. Chain verification not applicable to legacy entries.",
        )

    verified = 0
    expected_prev = "GENESIS"

    for entry in entries:
        if not entry.entry_hash:
            continue

        # Verify previous_hash linkage
        if entry.previous_hash != expected_prev:
            return ChainVerificationResult(
                valid=False,
                total_entries=len(entries),
                verified_entries=verified,
                first_broken_at=entry.sequence_number,
                message=f"Chain broken at sequence {entry.sequence_number}: "
                        f"expected previous_hash={expected_prev[:16]}..., "
                        f"got {(entry.previous_hash or 'None')[:16]}...",
            )

        # Recompute hash and verify
        hash_input = (
            f"{entry.sequence_number}|{entry.action}|{entry.user_id}"
            f"|{entry.timestamp.isoformat() if entry.timestamp else ''}|{entry.previous_hash}"
        )
        computed = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        if computed != entry.entry_hash:
            return ChainVerificationResult(
                valid=False,
                total_entries=len(entries),
                verified_entries=verified,
                first_broken_at=entry.sequence_number,
                message=f"Hash mismatch at sequence {entry.sequence_number}: "
                        f"entry may have been tampered with.",
            )

        expected_prev = entry.entry_hash
        verified += 1

    return ChainVerificationResult(
        valid=True,
        total_entries=len(entries),
        verified_entries=verified,
        message=f"All {verified} entries verified. Audit chain integrity confirmed.",
    )
