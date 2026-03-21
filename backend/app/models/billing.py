"""
Billing models — Phase 3.

Invoice: Payment records for subscription charges and overages.
WebhookEvent: Idempotency tracking for payment gateway webhooks.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Invoice(Base):
    """Payment invoice record."""
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)

    # Payment details
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # In smallest currency unit (paise/cents)
    currency: Mapped[str] = mapped_column(String(3), default="INR")  # ISO 4217
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, paid, failed, refunded
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Gateway info
    gateway: Mapped[str] = mapped_column(String(20), default="razorpay")  # razorpay, stripe
    gateway_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gateway_invoice_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookEvent(Base):
    """Idempotency tracking for payment gateway webhooks.

    Prevents duplicate processing of the same webhook event
    (e.g., concurrent subscription.charged events resetting used_scans).
    """
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("gateway", "gateway_event_id", name="uq_webhook_gateway_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gateway: Mapped[str] = mapped_column(String(20), nullable=False)  # razorpay, stripe
    gateway_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
