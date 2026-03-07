"""
Document and Usage models.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import String, DateTime, Enum as SQLEnum, Text, Integer, ForeignKey, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base
from app.models.enums import RiskLevel


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UsageAction(str, enum.Enum):
    SCAN = "scan"
    REDLINE = "redline"
    BULK_REVIEW = "bulk_review"
    EXPORT = "export"


class Document(Base):
    __tablename__ = "documents"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    playbook_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("playbooks.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    risk_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    total_risks: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped["User"] = relationship("User", back_populates="documents")
    risks: Mapped[List["DocumentRisk"]] = relationship("DocumentRisk", back_populates="document", cascade="all, delete-orphan")


class DocumentRisk(Base):
    __tablename__ = "document_risks"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("playbook_rules.id"), nullable=True)
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(SQLEnum(RiskLevel))
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    document: Mapped["Document"] = relationship("Document", back_populates="risks")


class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    action: Mapped[UsageAction] = mapped_column(SQLEnum(UsageAction))
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped["User"] = relationship("User", back_populates="usage_logs")
