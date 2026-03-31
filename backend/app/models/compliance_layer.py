"""
Compliance Layer models.
Compliance layers are toggleable rule overlays (e.g., DPDP, GDPR, CCPA) that stack on top of any playbook.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import RiskLevel


class ComplianceLayer(Base):
    __tablename__ = "compliance_layers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    rules: Mapped[List["ComplianceLayerRule"]] = relationship(
        "ComplianceLayerRule", back_populates="layer", cascade="all, delete-orphan"
    )


class ComplianceLayerRule(Base):
    __tablename__ = "compliance_layer_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    layer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_layers.id"), nullable=False, index=True)
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_position: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, default="YELLOW")
    is_deal_breaker: Mapped[bool] = mapped_column(Boolean, default=False)
    detection_patterns: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    detection_mode: Mapped[str] = mapped_column(String(50), default="ai_with_keywords")
    risk_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acceptable_position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unacceptable_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    acceptable_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    layer: Mapped["ComplianceLayer"] = relationship("ComplianceLayer", back_populates="rules")
