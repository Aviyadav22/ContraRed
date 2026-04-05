"""
Compliance Result Models - Persistence for DPDP scan and assessment history.

Enables trend tracking, audit readiness, and real dashboard data.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ComplianceScanResult(Base):
    """Persisted result from DPDP contract scanner agent."""
    __tablename__ = "compliance_scan_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    contract_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    contract_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    compliance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    red_count: Mapped[int] = mapped_column(Integer, default=0)
    yellow_count: Mapped[int] = mapped_column(Integer, default=0)
    green_count: Mapped[int] = mapped_column(Integer, default=0)
    deal_breaker_count: Mapped[int] = mapped_column(Integer, default=0)
    findings: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    risk_summary: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ComplianceAssessment(Base):
    """Persisted result from DPDP gap assessor agent."""
    __tablename__ = "compliance_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    organization_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_status: Mapped[str] = mapped_column(String(20), nullable=False)
    section_scores: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    critical_gaps: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    action_items: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    estimated_remediation_effort: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    answers: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ComplianceReport(Base):
    """Persisted compliance report for audit readiness."""
    __tablename__ = "compliance_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), default="full")
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    compliance_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
