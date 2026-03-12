"""
AuditLog Model - Compliance Logging for Enterprise.

Tracks access events, not usage counts. Separate from UsageLog.

UsageLog = For billing ("User consumed 500 tokens")
AuditLog = For compliance ("User accessed Merger_Agreement.docx at 10:00 from IP X")

Phase 2.4: Immutable audit trail with SHA-256 hash chain.
Each entry contains:
  - entry_hash: SHA-256 of (sequence_number + action + user_id + timestamp + previous_hash)
  - previous_hash: Hash of the preceding entry (GENESIS for the first)
  - sequence_number: Monotonically increasing sequence for chain ordering

The chain can be verified with GET /audit-logs/verify.
"""

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

logger = logging.getLogger(__name__)

# Maximum length for the ``details`` JSON field to prevent unbounded storage.
_MAX_DETAILS_LENGTH = 10_000

# Patterns that should NEVER appear in audit log details (PII / contract text).
_FORBIDDEN_DETAIL_KEYS = {"contract_text", "document_text", "password", "token", "secret"}


def _validate_details(details: Optional[str]) -> Optional[str]:
    """Validate and sanitise the ``details`` field before storage.

    - Must be valid JSON (or None).
    - Must not exceed ``_MAX_DETAILS_LENGTH`` characters.
    - Must not contain keys that could leak PII or contract content.

    Returns the sanitised string, or None if invalid.
    """
    if details is None:
        return None

    if len(details) > _MAX_DETAILS_LENGTH:
        logger.warning(
            "Audit log details too large (%d chars), truncating to %d",
            len(details),
            _MAX_DETAILS_LENGTH,
        )
        details = details[:_MAX_DETAILS_LENGTH]

    # Must be valid JSON
    try:
        parsed = json.loads(details)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Audit log details is not valid JSON — discarding")
        return None

    # Strip forbidden keys (shallow check)
    if isinstance(parsed, dict):
        for forbidden in _FORBIDDEN_DETAIL_KEYS:
            if forbidden in parsed:
                logger.warning("Audit log details contained forbidden key '%s' — redacting", forbidden)
                parsed[forbidden] = "[REDACTED]"
        return json.dumps(parsed)

    return details


class AuditLog(Base):
    """
    Audit log for compliance tracking.
    
    Records WHO accessed WHAT, WHEN, and from WHERE.
    Does NOT store document content (Zero Data Retention).
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # WHO
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_email: Mapped[str] = mapped_column(String(255))  # Denormalized for query efficiency
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # WHAT (metadata only, NOT content)
    action: Mapped[str] = mapped_column(String(50))  # analyze, export, view, redline
    resource_type: Mapped[str] = mapped_column(String(50))  # document, playbook, rule
    resource_name: Mapped[str] = mapped_column(String(255))  # Filename only, NOT content
    
    # WHEN
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    # WHERE
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # RESULT
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failure, denied
    risk_count: Mapped[Optional[int]] = mapped_column(nullable=True)  # For analyze actions
    
    # Additional context (NEVER store document content)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON metadata

    # Hash chain fields (Phase 2.4 — immutable audit trail)
    entry_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sequence_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


# Helper function to create audit log entries
async def log_audit_event(
    db: AsyncSession,
    user: Optional["User"] = None,
    action: str = "",
    resource_type: str = "",
    resource_name: str = "",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    risk_count: Optional[int] = None,
    details: Optional[str] = None,
    user_email: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
) -> Optional[AuditLog]:
    """
    Create an audit log entry.

    Args:
        db: Database session
        user: User object (optional — pass None for failed login attempts)
        action: What was done (analyze, export, view, redline, login_success, etc.)
        resource_type: What type of thing (document, playbook, auth)
        resource_name: FILENAME ONLY, never content
        ip_address: Client IP
        user_agent: Browser/client info
        status: success/failure/denied
        risk_count: Number of risks found (for analyze)
        details: JSON metadata (NEVER document content)
        user_email: Override email (used when user object is None)
        organization_id: Override org ID (used when user object is None)
    """
    try:
        # Validate & sanitise the details field before storage
        sanitised_details = _validate_details(details)

        # Hash chain: get sequence number from DB sequence (race-condition safe)
        from sqlalchemy import select, desc, text

        seq_number = 1
        try:
            seq_result = await db.execute(text("SELECT nextval('audit_log_sequence')"))
            seq_number = seq_result.scalar()
        except Exception:
            # Fallback if sequence doesn't exist yet
            seq_number = 1

        # Get the previous entry's hash for chain integrity
        previous_hash = "GENESIS"
        try:
            last_result = await db.execute(
                select(AuditLog.entry_hash)
                .where(AuditLog.entry_hash.isnot(None))
                .order_by(desc(AuditLog.sequence_number))
                .limit(1)
            )
            last_hash = last_result.scalar()
            if last_hash:
                previous_hash = last_hash
        except Exception as chain_err:
            logger.debug("Hash chain lookup failed (non-fatal): %s", chain_err)

        timestamp_now = datetime.now(timezone.utc)
        user_id_val = user.id if user else None

        # Compute entry hash: SHA-256(seq + action + user_id + timestamp + previous_hash)
        hash_input = f"{seq_number}|{action}|{user_id_val}|{timestamp_now.isoformat()}|{previous_hash}"
        entry_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        entry = AuditLog(
            user_id=user_id_val,
            user_email=user_email or (user.email if user else "unknown"),
            organization_id=organization_id or (user.organization_id if user else None),
            action=action,
            resource_type=resource_type,
            resource_name=resource_name[:255] if resource_name else "",
            timestamp=timestamp_now,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            status=status,
            risk_count=risk_count,
            details=sanitised_details,
            entry_hash=entry_hash,
            previous_hash=previous_hash,
            sequence_number=seq_number,
        )
        db.add(entry)
        # Note: Caller should await db.commit() or use db.flush()
        return entry
    except Exception as e:
        # Log with full traceback so failures are visible in monitoring,
        # but do NOT re-raise — audit logging must never crash the main operation.
        logger.error(
            "Audit log failed for action=%s resource=%s: %s",
            action,
            resource_name,
            e,
            exc_info=True,
        )
        # Surface the failure via metrics / alerting if available
        # TODO: Increment a Prometheus counter here once observability is wired up
        return None
