"""
Organization and Subscription models.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base


class PlanType(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    plan_type: Mapped[PlanType] = mapped_column(SQLEnum(PlanType), default=PlanType.FREE)

    # --- SSO fields ---
    sso_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    entra_tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    workos_org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # WorkOS organization ID
    sso_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "azure_ad", "okta", "google"

    # --- MFA enforcement ---
    mfa_required: Mapped[bool] = mapped_column(Boolean, default=False)  # Org-level MFA enforcement

    org_settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships - using string references to avoid circular imports
    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
    playbooks: Mapped[List["Playbook"]] = relationship("Playbook", back_populates="organization")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="organization")


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    razorpay_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    razorpay_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gateway: Mapped[str] = mapped_column(String(20), default="razorpay")  # razorpay, stripe
    status: Mapped[SubscriptionStatus] = mapped_column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    plan: Mapped[PlanType] = mapped_column(SQLEnum(PlanType))
    seats: Mapped[int] = mapped_column(Integer, default=1)
    included_scans: Mapped[int] = mapped_column(Integer, default=5)  # Matches FREE tier limit
    used_scans: Mapped[int] = mapped_column(Integer, default=0)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Dunning fields — track failed payment retries
    dunning_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_dunning_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dunning_next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    organization: Mapped["Organization"] = relationship("Organization", back_populates="subscriptions")
