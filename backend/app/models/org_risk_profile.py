"""
Organization Risk Profile model.
Tracks institutional memory of how an org handles different clause types over time.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OrganizationRiskProfile(Base):
    """Aggregated org-level risk profile per clause type."""
    __tablename__ = "organization_risk_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "clause_type", name="uq_org_clause_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    total_encounters: Mapped[int] = mapped_column(Integer, default=0)
    accept_count: Mapped[int] = mapped_column(Integer, default=0)
    reject_count: Mapped[int] = mapped_column(Integer, default=0)
    modify_count: Mapped[int] = mapped_column(Integer, default=0)
    escalate_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_threshold: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # e.g., {"risk_tolerance": "low"}
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
