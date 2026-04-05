"""
DPDP Act Consent Management Models.

ISO 27560 compliant consent records with immutable hash-chained audit trail.
Supports the full consent lifecycle: collection, verification, withdrawal,
rights requests, grievance redressal, nominations, and cross-border tracking.

Tables:
  - consent_purposes:       Versioned processing purpose definitions
  - consent_policies:       Privacy policy versions with SHA-256 checksums
  - consent_records:        Master consent per user (mutable status for fast lookups)
  - consent_purpose_grants: Per-purpose grant/deny (individual toggles, no bundling)
  - consent_events:         Immutable audit trail (hash-chained like audit_logs)
  - consent_receipts:       ISO 27560 JSON-LD machine-readable receipts
  - rights_requests:        Data Principal rights (access, correction, erasure, nomination)
  - grievances:             DPDP Section 13 grievance redressal
  - consent_nominations:    DPDP Section 14 authorized representatives
  - data_transfers:         Cross-border transfer tracking
"""

import enum
import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Boolean, DateTime, Integer, BigInteger, Text,
    Enum as SQLEnum, ForeignKey, ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import select, desc, text

from app.db.session import Base

logger = logging.getLogger(__name__)

# 7-year retention as required by DPDP Act for Consent Managers
CONSENT_RETENTION_YEARS = 7


# ---- Enums ----

class ConsentStatus(str, enum.Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    REFUSED = "refused"


class ConsentEventType(str, enum.Enum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    RENEWED = "renewed"
    MODIFIED = "modified"
    REFUSED = "refused"
    VERIFICATION_REQUESTED = "verification_requested"
    VERIFICATION_SUCCEEDED = "verification_succeeded"
    VERIFICATION_FAILED = "verification_failed"
    POLICY_ACCEPTED = "policy_accepted"
    RIGHTS_REQUEST = "rights_request"
    GRIEVANCE_FILED = "grievance_filed"


class RightsRequestType(str, enum.Enum):
    ACCESS = "access"
    CORRECTION = "correction"
    ERASURE = "erasure"
    NOMINATION = "nomination"
    PORTABILITY = "portability"


class RightsRequestStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class GrievanceCategory(str, enum.Enum):
    CONSENT_VIOLATION = "consent_violation"
    DATA_BREACH = "data_breach"
    PROCESSING_ERROR = "processing_error"
    RIGHTS_DENIAL = "rights_denial"
    UNAUTHORIZED_PROCESSING = "unauthorized_processing"
    OTHER = "other"


class GrievanceStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


# ---- Models ----

class ConsentPurpose(Base):
    """Versioned processing purpose definitions.

    Each purpose has a unique code (e.g. 'contract_analysis') and is versioned.
    When description or data categories change, a new version is created.
    """
    __tablename__ = "consent_purposes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purpose_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    personal_data_categories: Mapped[list] = mapped_column(ARRAY(String), default=list)
    third_parties: Mapped[list] = mapped_column(ARRAY(String), default=list)
    retention_period: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    translations: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ConsentPolicy(Base):
    """Privacy policy versions with SHA-256 checksums for tamper evidence."""
    __tablename__ = "consent_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en")
    purpose_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    effective_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def compute_checksum(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ConsentRecord(Base):
    """Master consent record per user.

    Status is mutable for fast O(1) lookups during enforcement.
    Every status change is also recorded in consent_events for full audit trail.
    """
    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    policy_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("consent_policies.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ConsentStatus.ACTIVE.value)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    collection_method: Mapped[str] = mapped_column(String(50), default="web_form")
    expression_method: Mapped[str] = mapped_column(String(50), default="checkbox")
    consent_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    purpose_grants: Mapped[List["ConsentPurposeGrant"]] = relationship("ConsentPurposeGrant", back_populates="consent_record", cascade="all, delete-orphan")
    events: Mapped[List["ConsentEvent"]] = relationship("ConsentEvent", back_populates="consent_record")
    receipts: Mapped[List["ConsentReceipt"]] = relationship("ConsentReceipt", back_populates="consent_record", cascade="all, delete-orphan")


class ConsentPurposeGrant(Base):
    """Per-purpose consent grant/deny.

    DPDP requires individual toggles per purpose (no bundling).
    """
    __tablename__ = "consent_purpose_grants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consent_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consent_records.id", ondelete="CASCADE"), nullable=False)
    purpose_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consent_purposes.id"), nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(100), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    consent_record: Mapped["ConsentRecord"] = relationship("ConsentRecord", back_populates="purpose_grants")
    purpose: Mapped["ConsentPurpose"] = relationship("ConsentPurpose")


class ConsentEvent(Base):
    """Immutable consent event audit trail.

    Hash-chained using the same SHA-256 pattern as AuditLog.
    Trigger in DB prevents UPDATE/DELETE.
    """
    __tablename__ = "consent_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consent_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("consent_records.id"), nullable=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    purpose_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    actor: Mapped[str] = mapped_column(String(50), default="data_subject")
    details: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Hash chain
    entry_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sequence_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Retention (7 years per DPDP)
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    consent_record: Mapped[Optional["ConsentRecord"]] = relationship("ConsentRecord", back_populates="events")


class ConsentReceipt(Base):
    """ISO 27560 compliant consent receipt in JSON-LD format."""
    __tablename__ = "consent_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consent_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consent_records.id", ondelete="CASCADE"), nullable=False)
    receipt_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    digital_signature: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(20), default="27560:2023")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    consent_record: Mapped["ConsentRecord"] = relationship("ConsentRecord", back_populates="receipts")


class RightsRequest(Base):
    """Data Principal rights requests (DPDP Sections 11-14).

    90-day SLA auto-calculated via DB trigger.
    """
    __tablename__ = "rights_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RightsRequestStatus.SUBMITTED.value)
    request_details: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    response_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Grievance(Base):
    """DPDP Section 13 grievance redressal.

    90-day SLA auto-calculated via DB trigger.
    """
    __tablename__ = "grievances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default=GrievanceStatus.SUBMITTED.value)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ConsentNomination(Base):
    """DPDP Section 14 - Authorized representative for death/incapacity."""
    __tablename__ = "consent_nominations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nominee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    nominee_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nominee_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    nominee_contact: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    relationship: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DataTransfer(Base):
    """Cross-border data transfer tracking (DPDP Rule 14)."""
    __tablename__ = "data_transfers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    destination_country: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_country: Mapped[str] = mapped_column(String(10), default="IN")
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    personal_data_categories: Mapped[list] = mapped_column(ARRAY(String), default=list)
    purpose_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    legal_basis: Mapped[str] = mapped_column(String(50), default="consent")
    transfer_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
