"""
AuditLog Model - Compliance Logging for Enterprise.

Tracks access events, not usage counts. Separate from UsageLog.

UsageLog = For billing ("User consumed 500 tokens")
AuditLog = For compliance ("User accessed Merger_Agreement.docx at 10:00 from IP X")
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditLog(Base):
    """
    Audit log for compliance tracking.
    
    Records WHO accessed WHAT, WHEN, and from WHERE.
    Does NOT store document content (Zero Data Retention).
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # WHO
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    user_email: Mapped[str] = mapped_column(String(255))  # Denormalized for query efficiency
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # WHAT (metadata only, NOT content)
    action: Mapped[str] = mapped_column(String(50))  # analyze, export, view, redline
    resource_type: Mapped[str] = mapped_column(String(50))  # document, playbook, rule
    resource_name: Mapped[str] = mapped_column(String(255))  # Filename only, NOT content
    
    # WHEN
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # WHERE
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # RESULT
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failure, denied
    risk_count: Mapped[Optional[int]] = mapped_column(nullable=True)  # For analyze actions
    
    # Additional context (NEVER store document content)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON metadata


# Helper function to create audit log entries
async def log_audit_event(
    db,
    user,
    action: str,
    resource_type: str,
    resource_name: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    risk_count: Optional[int] = None,
    details: Optional[str] = None
):
    """
    Create an audit log entry.
    
    Args:
        db: Database session
        user: User object
        action: What was done (analyze, export, view, redline)
        resource_type: What type of thing (document, playbook)
        resource_name: FILENAME ONLY, never content
        ip_address: Client IP
        user_agent: Browser/client info
        status: success/failure/denied
        risk_count: Number of risks found (for analyze)
        details: JSON metadata (NEVER document content)
    """
    entry = AuditLog(
        user_id=user.id,
        user_email=user.email,
        organization_id=user.organization_id,
        action=action,
        resource_type=resource_type,
        resource_name=resource_name[:255],  # Truncate long filenames
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
        status=status,
        risk_count=risk_count,
        details=details,
    )
    db.add(entry)
    # Note: Caller should await db.commit() or use db.flush()
    return entry
