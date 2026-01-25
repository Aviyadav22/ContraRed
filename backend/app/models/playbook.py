"""
Playbook and ClauseLibrary models.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base


class PlaybookCategory(str, enum.Enum):
    SAAS = "saas"
    NDA = "nda"
    DPA = "dpa"
    EMPLOYMENT = "employment"
    MSA = "msa"
    CUSTOM = "custom"


class RiskLevel(str, enum.Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class Playbook(Base):
    __tablename__ = "playbooks"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[PlaybookCategory] = mapped_column(SQLEnum(PlaybookCategory), default=PlaybookCategory.CUSTOM)
    rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="playbooks")
    rules_list: Mapped[List["PlaybookRule"]] = relationship("PlaybookRule", back_populates="playbook", cascade="all, delete-orphan")


class PlaybookRule(Base):
    __tablename__ = "playbook_rules"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbooks.id"))
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_position: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(SQLEnum(RiskLevel), default=RiskLevel.YELLOW)
    is_deal_breaker: Mapped[bool] = mapped_column(Boolean, default=False)
    detection_patterns: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    suggested_language: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    
    # Hybrid Sentinel fields for two-pass AI verification
    requires_ai_verification: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    playbook: Mapped["Playbook"] = relationship("Playbook", back_populates="rules_list")


class ClauseLibrary(Base):
    __tablename__ = "clause_library"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
