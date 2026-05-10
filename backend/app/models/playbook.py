"""
Playbook and ClauseLibrary models.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, Text, Integer, ForeignKey, Numeric, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base
from app.models.enums import RiskLevel


class PlaybookCategory(str, enum.Enum):
    SAAS = "saas"
    NDA = "nda"
    DPA = "dpa"
    EMPLOYMENT = "employment"
    MSA = "msa"
    CUSTOM = "custom"


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[PlaybookCategory] = mapped_column(SQLEnum(PlaybookCategory), default=PlaybookCategory.CUSTOM)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    party_side: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="buyer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

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

    # Phase 5: Contract Coverage extensions
    jurisdiction_overrides: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # P2 #29: AI-primary detection
    detection_mode: Mapped[str] = mapped_column(String(30), default="keywords_only")
    risk_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acceptable_position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unacceptable_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    acceptable_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    clause_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    playbook: Mapped["Playbook"] = relationship("Playbook", back_populates="rules_list")
    tiers: Mapped[List["PlaybookRuleTier"]] = relationship("PlaybookRuleTier", back_populates="rule", cascade="all, delete-orphan")
    overrides: Mapped[List["PlaybookRuleOverride"]] = relationship("PlaybookRuleOverride", back_populates="rule", cascade="all, delete-orphan")


# ============================================================================
# Phase 6: Negotiation Tier System
# ============================================================================

class TierLevel(int, enum.Enum):
    IDEAL = 1
    ACCEPTABLE = 2
    WALK_AWAY = 3
    ESCALATE = 4


class PlaybookRuleTier(Base):
    __tablename__ = "playbook_rule_tiers"
    __table_args__ = (
        UniqueConstraint("rule_id", "tier_level", name="uq_rule_tier"),
        CheckConstraint("tier_level BETWEEN 1 AND 4", name="ck_tier_level_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbook_rules.id", ondelete="CASCADE"), index=True)
    tier_level: Mapped[int] = mapped_column(Integer, nullable=False)
    position_text: Mapped[str] = mapped_column(Text, nullable=False)
    guidance_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level_at_tier: Mapped[Optional[str]] = mapped_column(String(10), default="yellow")  # Values: red, yellow, green (matches RiskLevel enum)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    rule: Mapped["PlaybookRule"] = relationship("PlaybookRule", back_populates="tiers")


# ============================================================================
# Phase 6: Conditional Logic Engine
# ============================================================================

class ConditionType(str, enum.Enum):
    COUNTERPARTY_TYPE = "counterparty_type"
    DEAL_SIZE = "deal_size"
    JURISDICTION = "jurisdiction"
    CONTRACT_SIDE = "contract_side"
    CUSTOM = "custom"


class PlaybookCondition(Base):
    __tablename__ = "playbook_conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Values: counterparty_type, deal_size, jurisdiction, contract_side, custom
    operator: Mapped[str] = mapped_column(String(20), default="equals")
    condition_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    playbook: Mapped["Playbook"] = relationship("Playbook")
    rule_overrides: Mapped[List["PlaybookRuleOverride"]] = relationship("PlaybookRuleOverride", back_populates="condition", cascade="all, delete-orphan")


class PlaybookRuleOverride(Base):
    __tablename__ = "playbook_rule_overrides"
    __table_args__ = (
        UniqueConstraint("condition_id", "rule_id", name="uq_condition_rule_override"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbook_conditions.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbook_rules.id", ondelete="CASCADE"), index=True)
    override_risk_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    override_position_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    override_is_deal_breaker: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    override_tier_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    suppress_rule: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    condition: Mapped["PlaybookCondition"] = relationship("PlaybookCondition", back_populates="rule_overrides")
    rule: Mapped["PlaybookRule"] = relationship("PlaybookRule", back_populates="overrides")


# ============================================================================
# Phase 6: Cross-Clause Dependencies
# ============================================================================

class PlaybookRuleDependency(Base):
    __tablename__ = "playbook_rule_dependencies"
    __table_args__ = (
        UniqueConstraint("source_rule_id", "target_rule_id", "trigger_condition", name="uq_dep_source_target_trigger"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), index=True)
    source_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbook_rules.id", ondelete="CASCADE"), index=True)
    target_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbook_rules.id", ondelete="CASCADE"), index=True)
    trigger_condition: Mapped[str] = mapped_column(String(50), nullable=False)
    effect: Mapped[str] = mapped_column(String(50), nullable=False)
    effect_params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    playbook: Mapped["Playbook"] = relationship("Playbook")
    source_rule: Mapped["PlaybookRule"] = relationship("PlaybookRule", foreign_keys=[source_rule_id])
    target_rule: Mapped["PlaybookRule"] = relationship("PlaybookRule", foreign_keys=[target_rule_id])


# ============================================================================
# Phase 6: Playbook Version Control
# ============================================================================

class PlaybookVersion(Base):
    __tablename__ = "playbook_versions"
    __table_args__ = (
        UniqueConstraint("playbook_id", "version_number", name="uq_playbook_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    playbook: Mapped["Playbook"] = relationship("Playbook")


# ============================================================================
# Phase 6: Marketplace
# ============================================================================

class PlaybookMarketplace(Base):
    __tablename__ = "playbook_marketplace"
    __table_args__ = (
        UniqueConstraint("playbook_id", name="uq_marketplace_playbook"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    publisher_org_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)
    preview_rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    playbook: Mapped["Playbook"] = relationship("Playbook")
    ratings: Mapped[List["PlaybookRating"]] = relationship("PlaybookRating", back_populates="marketplace_entry", cascade="all, delete-orphan")


class PlaybookRating(Base):
    __tablename__ = "playbook_ratings"
    __table_args__ = (
        UniqueConstraint("marketplace_id", "user_id", name="uq_rating_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marketplace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbook_marketplace.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    marketplace_entry: Mapped["PlaybookMarketplace"] = relationship("PlaybookMarketplace", back_populates="ratings")


class ClauseLibrary(Base):
    __tablename__ = "clause_library"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
