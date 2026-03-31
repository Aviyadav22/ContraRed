"""
Jurisdiction and JurisdictionRuleOverride models.

Database-driven jurisdiction profiles and rule overrides that replace
the hardcoded dicts in jurisdiction_detector.py.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    String, Boolean, DateTime, Integer, Float, Text,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_system: Mapped[str] = mapped_column(
        String(20), nullable=False, default="common_law",
    )  # common_law | civil_law | hybrid
    parent_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Legal framework details stored as structured JSON
    key_statutes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    special_considerations: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Textual fields for prompt injection
    indemnification_standard: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    non_compete_enforceability: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    arbitration_framework: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_protection_law: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Aliases for detection (e.g. ["india", "republic of india", "mumbai"])
    aliases: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    rule_overrides: Mapped[list["JurisdictionRuleOverride"]] = relationship(
        "JurisdictionRuleOverride", back_populates="jurisdiction", cascade="all, delete-orphan",
    )


class JurisdictionRuleOverride(Base):
    __tablename__ = "jurisdiction_rule_overrides"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "clause_type", name="uq_jurisdiction_clause_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True,
    )
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # RED/YELLOW/GREEN
    risk_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    suppress: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    statute_reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationship
    jurisdiction: Mapped["Jurisdiction"] = relationship(
        "Jurisdiction", back_populates="rule_overrides",
    )
