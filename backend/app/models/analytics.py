"""
Phase 9 Analytics models: review sessions, time benchmarks, ROI config,
benchmark profiles, and generated reports.
"""

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String, DateTime, Integer, ForeignKey, Text, Numeric, Boolean, Date, Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ReviewSession(Base):
    """Tracks an individual review session by a user on a document.

    NOTE: This model is defined for table creation but not yet wired into
    any endpoint. Future work: create POST /analytics/sessions/start and
    PUT /analytics/sessions/{id}/end to track review sessions from the
    Word Add-in or dashboard.
    """
    __tablename__ = "review_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    risks_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    risks_accepted: Mapped[int] = mapped_column(Integer, default=0)
    risks_rejected: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TimeBenchmark(Base):
    """Organisation-level time benchmarks for manual review (used in ROI calculations)."""
    __tablename__ = "time_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True)
    pages_per_hour: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=5.0)
    minutes_per_risk: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=15.0)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=5000.00)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)


class ROIConfig(Base):
    """Organisation-level configuration for ROI / value-at-risk calculations."""
    __tablename__ = "roi_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True)
    risk_value_per_red: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=500000.00)
    risk_value_per_yellow: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=100000.00)
    include_risk_value: Mapped[bool] = mapped_column(Boolean, default=True)
    include_time_savings: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_methodology_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)


class BenchmarkProfile(Base):
    """Aggregated benchmark data per contract type for an organisation over a time period."""
    __tablename__ = "benchmark_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    contract_type: Mapped[str] = mapped_column(String(100), nullable=False)
    avg_risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    avg_risks_per_doc: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    avg_red_risks: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    avg_processing_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("organization_id", "contract_type", "period_start", "period_end", name="uq_benchmark_org_type_period"),
    )


class GeneratedReport(Base):
    """Persisted analytics report (executive summary, GC ops, team review, risk audit)."""
    __tablename__ = "generated_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    report_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="json")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
