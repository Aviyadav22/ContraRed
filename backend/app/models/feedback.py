"""Rule feedback model for tracking user feedback on playbook rules.

Phase 5: Continuous learning through lawyer input.
Maps to the rule_feedback table created in migration 016.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RuleFeedback(Base):
    """Tracks lawyer feedback on playbook rule matches (false positives, etc.)."""

    __tablename__ = "rule_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    playbook_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbook_rules.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Feedback type: false_positive, false_negative, correct, needs_improvement
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Details
    clause_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_risk_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Tracking
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
