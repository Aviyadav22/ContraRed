"""
DPDP Rights Agent — Data Principal rights automation.

Handles:
  - Rights requests (access, correction, erasure, nomination, portability)
  - Internal service-target tracking with auto-escalation
  - Grievance management (Section 13)
  - Nomination management (Section 14)
  - Breach notification workflow
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import (
    RightsRequest,
    RightsRequestStatus,
    RightsRequestType,
    Grievance,
    GrievanceStatus,
    GrievanceCategory,
    ConsentNomination,
    ConsentEventType,
)
from app.services.consent_event_bus import consent_event_bus
from app.services.consent_service import consent_service
from app.services.data_erasure_service import erase_user_data
from app.services.dpdp.models import (
    RightsRequestInput,
    GrievanceInput,
)

logger = logging.getLogger(__name__)

# Operational targets. DPDP Rule 14(3) sets a maximum published period of
# 90 days for grievance responses; it does not impose a universal 90-day
# deadline on all other Data Principal rights requests.
GRIEVANCE_SERVICE_TARGET_DAYS = 30
RIGHTS_SERVICE_TARGET_DAYS = 90


class RightsAgent:
    """Manages Data Principal rights workflows under DPDP Act."""

    # ---- Rights Requests (Sections 11-12) ----

    async def submit_rights_request(
        self,
        db: AsyncSession,
        subject_id: str,
        input_data: RightsRequestInput,
        organization_id: Optional[str] = None,
    ) -> dict:
        """Submit a new Data Principal rights request."""
        # Validate request type
        valid_types = [t.value for t in RightsRequestType]
        if input_data.request_type not in valid_types:
            raise ValueError(
                f"Invalid request type: {input_data.request_type}. "
                f"Valid types: {valid_types}"
            )

        deadline = datetime.now(timezone.utc) + timedelta(days=RIGHTS_SERVICE_TARGET_DAYS)

        request = RightsRequest(
            id=uuid.uuid4(),
            subject_id=uuid.UUID(subject_id),
            organization_id=uuid.UUID(organization_id) if organization_id else None,
            request_type=input_data.request_type,
            status=RightsRequestStatus.SUBMITTED.value,
            request_details={
                "subject_name": input_data.subject_name,
                "subject_email": input_data.subject_email,
                "description": input_data.description,
                "evidence": input_data.evidence,
            },
            resolution_deadline=deadline,
        )

        db.add(request)

        await consent_service._record_event(
            db,
            None,
            uuid.UUID(subject_id),
            ConsentEventType.RIGHTS_REQUEST.value,
            details={
                "request_type": input_data.request_type,
                "request_id": str(request.id),
            },
        )

        await db.commit()
        await consent_event_bus.publish_rights_request(
            subject_id, input_data.request_type, str(request.id)
        )

        return {
            "request_id": str(request.id),
            "status": request.status,
            "request_type": input_data.request_type,
            "resolution_deadline": deadline.isoformat(),
            "message": (
                "Rights request submitted. Internal service target: "
                f"{deadline.strftime('%Y-%m-%d')}."
            ),
        }

    async def get_rights_requests(
        self,
        db: AsyncSession,
        subject_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """List rights requests with optional filters."""
        query = select(RightsRequest).order_by(RightsRequest.submitted_at.desc())

        if subject_id:
            query = query.where(RightsRequest.subject_id == uuid.UUID(subject_id))
        if organization_id:
            query = query.where(RightsRequest.organization_id == uuid.UUID(organization_id))
        if status_filter:
            query = query.where(RightsRequest.status == status_filter)

        query = query.limit(limit)
        result = await db.execute(query)
        requests = result.scalars().all()

        return [
            {
                "id": str(r.id),
                "request_type": r.request_type,
                "status": r.status,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
                "resolution_deadline": r.resolution_deadline.isoformat() if r.resolution_deadline else None,
                "is_overdue": (
                    r.resolution_deadline
                    and r.status not in (RightsRequestStatus.COMPLETED.value, RightsRequestStatus.REJECTED.value)
                    and datetime.now(timezone.utc) > r.resolution_deadline
                ),
                "details": r.request_details,
                "assigned_to": r.assigned_to,
            }
            for r in requests
        ]

    async def update_rights_request(
        self,
        db: AsyncSession,
        request_id: str,
        new_status: str,
        response_details: Optional[dict] = None,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> dict:
        """Update a rights request status (admin action)."""
        result = await db.execute(
            select(RightsRequest).where(RightsRequest.id == uuid.UUID(request_id))
        )
        request = result.scalar_one_or_none()
        if not request:
            raise ValueError(f"Rights request {request_id} not found")

        valid_statuses = {status.value for status in RightsRequestStatus}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid rights-request status: {new_status}")

        now = datetime.now(timezone.utc)

        if new_status == RightsRequestStatus.COMPLETED.value:
            if request.request_type == RightsRequestType.ERASURE.value:
                erasure = await erase_user_data(db, request.subject_id, commit=False)
                if "error" in erasure:
                    raise ValueError(erasure["error"])
                response_details = {
                    "fulfilled_at": now.isoformat(),
                    "method": "anonymisation_and_session_revocation",
                }
            elif request.request_type == RightsRequestType.ACCESS.value:
                response_details = {
                    **(response_details or {}),
                    "delivery": "authenticated_download",
                    "download_url": f"/api/v1/rights/requests/{request.id}/download",
                }
            elif (
                request.request_type == RightsRequestType.CORRECTION.value
                and not (response_details or {}).get("corrected_fields")
            ):
                raise ValueError(
                    "Correction requests require response_details.corrected_fields "
                    "before they can be completed"
                )

        request.status = new_status
        if new_status == RightsRequestStatus.ACKNOWLEDGED.value:
            request.acknowledged_at = now
        elif new_status in (RightsRequestStatus.COMPLETED.value, RightsRequestStatus.REJECTED.value):
            request.resolved_at = now

        if response_details:
            request.response_details = response_details
        if assigned_to:
            request.assigned_to = assigned_to
        if resolution_notes:
            request.resolution_notes = resolution_notes

        await db.commit()

        return {
            "request_id": request_id,
            "status": new_status,
            "updated_at": now.isoformat(),
        }

    # ---- Grievances (Section 13) ----

    async def file_grievance(
        self,
        db: AsyncSession,
        subject_id: str,
        input_data: GrievanceInput,
        organization_id: Optional[str] = None,
    ) -> dict:
        """File a DPDP Section 13 grievance."""
        valid_categories = [c.value for c in GrievanceCategory]
        if input_data.category not in valid_categories:
            raise ValueError(
                f"Invalid category: {input_data.category}. "
                f"Valid categories: {valid_categories}"
            )

        deadline = datetime.now(timezone.utc) + timedelta(days=GRIEVANCE_SERVICE_TARGET_DAYS)

        grievance = Grievance(
            id=uuid.uuid4(),
            subject_id=uuid.UUID(subject_id),
            organization_id=uuid.UUID(organization_id) if organization_id else None,
            category=input_data.category,
            description=input_data.description,
            evidence=input_data.evidence,
            status=GrievanceStatus.SUBMITTED.value,
            resolution_deadline=deadline,
        )

        db.add(grievance)

        await consent_service._record_event(
            db,
            None,
            uuid.UUID(subject_id),
            ConsentEventType.GRIEVANCE_FILED.value,
            details={
                "grievance_id": str(grievance.id),
                "category": input_data.category,
            },
        )

        await db.commit()
        await consent_event_bus.publish_grievance(
            subject_id, input_data.category, str(grievance.id)
        )

        return {
            "grievance_id": str(grievance.id),
            "status": grievance.status,
            "category": input_data.category,
            "resolution_deadline": deadline.isoformat(),
            "message": (
                "Grievance filed. Our published service target is to respond by "
                f"{deadline.strftime('%Y-%m-%d')}."
            ),
        }

    async def get_grievances(
        self,
        db: AsyncSession,
        subject_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """List grievances with optional filters."""
        query = select(Grievance).order_by(Grievance.submitted_at.desc())

        if subject_id:
            query = query.where(Grievance.subject_id == uuid.UUID(subject_id))
        if organization_id:
            query = query.where(Grievance.organization_id == uuid.UUID(organization_id))
        if status_filter:
            query = query.where(Grievance.status == status_filter)

        query = query.limit(limit)
        result = await db.execute(query)
        grievances = result.scalars().all()

        return [
            {
                "id": str(g.id),
                "category": g.category,
                "description": g.description,
                "status": g.status,
                "submitted_at": g.submitted_at.isoformat() if g.submitted_at else None,
                "acknowledged_at": g.acknowledged_at.isoformat() if g.acknowledged_at else None,
                "resolved_at": g.resolved_at.isoformat() if g.resolved_at else None,
                "resolution_deadline": g.resolution_deadline.isoformat() if g.resolution_deadline else None,
                "is_overdue": (
                    g.resolution_deadline
                    and g.status not in (GrievanceStatus.RESOLVED.value,)
                    and datetime.now(timezone.utc) > g.resolution_deadline
                ),
                "resolution_notes": g.resolution_notes,
            }
            for g in grievances
        ]

    async def update_grievance(
        self,
        db: AsyncSession,
        grievance_id: str,
        new_status: str,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> dict:
        """Update grievance status (admin action)."""
        result = await db.execute(
            select(Grievance).where(Grievance.id == uuid.UUID(grievance_id))
        )
        grievance = result.scalar_one_or_none()
        if not grievance:
            raise ValueError(f"Grievance {grievance_id} not found")

        valid_statuses = {status.value for status in GrievanceStatus}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid grievance status: {new_status}")

        now = datetime.now(timezone.utc)
        grievance.status = new_status

        if new_status == GrievanceStatus.ACKNOWLEDGED.value:
            grievance.acknowledged_at = now
        elif new_status == GrievanceStatus.RESOLVED.value:
            grievance.resolved_at = now

        if assigned_to:
            grievance.assigned_to = assigned_to
        if resolution_notes:
            grievance.resolution_notes = resolution_notes

        await db.commit()

        return {
            "grievance_id": grievance_id,
            "status": new_status,
            "updated_at": now.isoformat(),
        }

    # ---- Nominations (Section 14) ----

    async def create_nomination(
        self,
        db: AsyncSession,
        subject_id: str,
        nominee_name: str,
        nominee_email: Optional[str] = None,
        nominee_phone: Optional[str] = None,
        relationship: Optional[str] = None,
    ) -> dict:
        """Create a Data Principal nomination (Section 14)."""
        nomination = ConsentNomination(
            id=uuid.uuid4(),
            subject_id=uuid.UUID(subject_id),
            nominee_name=nominee_name,
            nominee_email=nominee_email,
            nominee_phone=nominee_phone,
            nominee_contact={
                "email": nominee_email,
                "phone": nominee_phone,
            },
            relationship=relationship,
            is_active=True,
        )

        db.add(nomination)
        await db.commit()

        return {
            "nomination_id": str(nomination.id),
            "nominee_name": nominee_name,
            "status": "active",
            "message": "Nomination created. The nominee can exercise your rights in case of death or incapacity.",
        }

    async def get_nominations(
        self,
        db: AsyncSession,
        subject_id: str,
    ) -> list[dict]:
        """List active nominations for a data principal."""
        result = await db.execute(
            select(ConsentNomination)
            .where(
                and_(
                    ConsentNomination.subject_id == uuid.UUID(subject_id),
                    ConsentNomination.is_active.is_(True),
                )
            )
            .order_by(ConsentNomination.created_at.desc())
        )
        nominations = result.scalars().all()

        return [
            {
                "id": str(n.id),
                "nominee_name": n.nominee_name,
                "nominee_email": n.nominee_email,
                "relationship": n.relationship,
                "is_active": n.is_active,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in nominations
        ]

    async def revoke_nomination(
        self,
        db: AsyncSession,
        nomination_id: str,
        subject_id: str,
    ) -> dict:
        """Revoke a nomination."""
        result = await db.execute(
            select(ConsentNomination).where(
                and_(
                    ConsentNomination.id == uuid.UUID(nomination_id),
                    ConsentNomination.subject_id == uuid.UUID(subject_id),
                )
            )
        )
        nomination = result.scalar_one_or_none()
        if not nomination:
            raise ValueError("Nomination not found")

        nomination.is_active = False
        nomination.revoked_at = datetime.now(timezone.utc)
        await db.commit()

        return {
            "nomination_id": nomination_id,
            "status": "revoked",
        }

    # ---- Service-target monitoring ----

    async def get_overdue_requests(
        self,
        db: AsyncSession,
        organization_id: Optional[str] = None,
    ) -> dict:
        """Get all overdue rights requests and grievances."""
        now = datetime.now(timezone.utc)
        overdue: dict = {"rights_requests": [], "grievances": []}

        # Overdue rights requests
        rr_query = select(RightsRequest).where(
            and_(
                RightsRequest.resolution_deadline < now,
                RightsRequest.status.in_([
                    RightsRequestStatus.SUBMITTED.value,
                    RightsRequestStatus.ACKNOWLEDGED.value,
                    RightsRequestStatus.IN_PROGRESS.value,
                ]),
            )
        )
        if organization_id:
            rr_query = rr_query.where(
                RightsRequest.organization_id == uuid.UUID(organization_id)
            )

        result = await db.execute(rr_query)
        for r in result.scalars().all():
            days_overdue = (now - r.resolution_deadline).days if r.resolution_deadline else 0
            overdue["rights_requests"].append({
                "id": str(r.id),
                "type": r.request_type,
                "status": r.status,
                "days_overdue": days_overdue,
                "deadline": r.resolution_deadline.isoformat() if r.resolution_deadline else None,
            })

        # Overdue grievances
        gr_query = select(Grievance).where(
            and_(
                Grievance.resolution_deadline < now,
                Grievance.status.in_([
                    GrievanceStatus.SUBMITTED.value,
                    GrievanceStatus.ACKNOWLEDGED.value,
                    GrievanceStatus.INVESTIGATING.value,
                ]),
            )
        )
        if organization_id:
            gr_query = gr_query.where(
                Grievance.organization_id == uuid.UUID(organization_id)
            )

        result = await db.execute(gr_query)
        for g in result.scalars().all():
            days_overdue = (now - g.resolution_deadline).days if g.resolution_deadline else 0
            overdue["grievances"].append({
                "id": str(g.id),
                "category": g.category,
                "status": g.status,
                "days_overdue": days_overdue,
                "deadline": g.resolution_deadline.isoformat() if g.resolution_deadline else None,
            })

        overdue["total_overdue"] = (
            len(overdue["rights_requests"]) + len(overdue["grievances"])
        )

        return overdue
