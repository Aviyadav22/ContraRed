"""
Batch Job models.
Persist batch analysis state to the database instead of in-memory dict.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BatchJob(Base):
    """A batch analysis job tracking multiple files."""
    __tablename__ = "batch_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")  # processing, completed, failed
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    completed_files: Mapped[int] = mapped_column(Integer, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, default=0)
    playbook_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    compliance_layers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # List of layer codes
    compliance_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    risk_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Aggregate {red, yellow, green}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    files: Mapped[List["BatchJobFile"]] = relationship("BatchJobFile", back_populates="batch", cascade="all, delete-orphan")


class BatchJobFile(Base):
    """A single file within a batch analysis job."""
    __tablename__ = "batch_job_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("batch_jobs.id"), nullable=False, index=True)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")  # queued, processing, completed, error
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {red, yellow, green, total}
    compliance_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    processing_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    batch: Mapped["BatchJob"] = relationship("BatchJob", back_populates="files")
