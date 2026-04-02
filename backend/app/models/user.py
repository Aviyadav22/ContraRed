"""
User model.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Integer, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base


class UserRole(str, enum.Enum):
    """
    5-tier RBAC role hierarchy (enterprise-grade).

    Migration note: legacy "user" and "analyst" map to VIEWER and REVIEWER
    respectively in the new hierarchy. Existing DB rows with old enum values
    are handled by keeping the old values in the enum for backward compat.
    """
    # --- Legacy values (kept for DB backward compatibility) ---
    USER = "user"               # Legacy — maps to VIEWER in permission checks
    ANALYST = "analyst"         # Legacy — maps to REVIEWER in permission checks

    # --- New 5-tier hierarchy ---
    VIEWER = "viewer"           # Read-only access (clients, external counsel)
    REVIEWER = "reviewer"       # Can annotate, comment, suggest changes
    MANAGER = "manager"         # Team lead — manage playbooks, team, templates
    ADMIN = "admin"             # Org admin — billing, settings, SSO
    SUPER_ADMIN = "super_admin" # Platform admin (ContraRed staff)


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    razorpay_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # --- MFA fields ---
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted TOTP secret
    mfa_backup_codes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Hashed backup codes

    # --- SSO fields ---
    sso_provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # WorkOS user ID / IdP subject

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="users")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="user")
    usage_logs: Mapped[List["UsageLog"]] = relationship("UsageLog", back_populates="user")
