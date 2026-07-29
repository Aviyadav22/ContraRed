"""
Playbook management endpoints.
Full CRUD for playbooks, rules, tiers, conditions, dependencies, versions, marketplace.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Literal, Optional
import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_, delete
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.user import User
from app.services.playbook_cache import invalidate_playbook_cache
from app.services.rule_engine import _safe_compile_regex
from app.services.clause_taxonomy import snap_to_clause_type
from app.models.playbook import (
    Playbook, PlaybookRule, PlaybookCategory, RiskLevel,
    PlaybookRuleTier, PlaybookCondition, PlaybookRuleOverride,
    PlaybookRuleDependency, PlaybookMarketplace, PlaybookRating,
)
from app.api.v1.endpoints.auth import get_current_user, limiter
# Playbook ops are gated by ownership via _get_playbook_or_403, not by role —
# any authenticated user can create + manage their own playbooks.
from app.models.audit_log import log_audit_event
from app.services.playbook_versioning import playbook_versioning_service

logger = logging.getLogger(__name__)


router = APIRouter()


# ============================================================================
# Shared access-check helper
# ============================================================================

def _playbook_quality_issues(rules: List[PlaybookRule]) -> List[str]:
    """Return lawyer-facing issues that make a playbook unsafe to publish."""
    if not rules:
        return ["Add at least one rule before publishing the playbook."]

    issues: List[str] = []
    for index, rule in enumerate(rules, start=1):
        label = rule.clause_type or f"Rule {index}"
        risk_level = (
            rule.risk_level.value.upper()
            if getattr(rule.risk_level, "value", None)
            else str(rule.risk_level).upper()
        )
        if not (rule.primary_position or "").strip():
            issues.append(f"{label}: add the client's primary position.")
        if risk_level in {"RED", "YELLOW"} and not (rule.fallback_position or "").strip():
            issues.append(f"{label}: add a fallback negotiation position.")

        detection_mode = rule.detection_mode or "keywords_only"
        patterns = (
            (rule.detection_patterns or {}).get("patterns", [])
            if isinstance(rule.detection_patterns, dict)
            else []
        )
        keyword_modes = {"keywords_only", "ai_with_keywords", "hybrid"}
        ai_modes = {"ai_only", "ai_with_keywords", "ai_primary", "hybrid"}
        if detection_mode not in keyword_modes | ai_modes:
            issues.append(f"{label}: choose a supported detection mode.")
        if detection_mode in keyword_modes and not patterns:
            issues.append(f"{label}: add detection patterns or switch to AI-primary detection.")
        if detection_mode in ai_modes and not (rule.risk_description or "").strip():
            issues.append(f"{label}: add a risk description for AI verification.")
        if detection_mode in ai_modes and not (
            getattr(rule, "verification_prompt", None) or ""
        ).strip():
            issues.append(
                f"{label}: add a rule-specific verification question."
            )
        if rule.is_deal_breaker and risk_level != "RED":
            issues.append(f"{label}: a deal-breaker must use red risk so escalation is unambiguous.")

    return issues


def _playbook_quality_recommendations(rules: List[PlaybookRule]) -> List[str]:
    """Return non-blocking improvements that make AI review more lawyer-like."""
    recommendations: List[str] = []
    ai_modes = {"ai_only", "ai_with_keywords", "ai_primary", "hybrid"}
    for index, rule in enumerate(rules, start=1):
        label = rule.clause_type or f"Rule {index}"
        detection_mode = rule.detection_mode or "keywords_only"
        if not rule.suggested_language:
            recommendations.append(
                f"{label}: add preferred drafting language so proposed fixes stay consistent."
            )
        if detection_mode in ai_modes:
            if not (rule.acceptable_position or "").strip():
                recommendations.append(
                    f"{label}: describe an acceptable position to reduce false positives."
                )
            if not (rule.clause_context or "").strip():
                recommendations.append(
                    f"{label}: add commercial context, dependencies, and exceptions."
                )
            if not rule.unacceptable_signals and not rule.acceptable_signals:
                recommendations.append(
                    f"{label}: add acceptable or unacceptable signals to anchor the AI comparison."
                )
    return recommendations


def _require_publishable_playbook(rules: List[PlaybookRule]) -> None:
    issues = _playbook_quality_issues(rules)
    if issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Complete the playbook before publishing.",
                "issues": issues,
            },
        )


def _mark_playbook_changed(playbook: Playbook) -> None:
    """Version a mutation and require legal-quality review before republishing."""
    playbook.version += 1
    playbook.is_public = False


async def _get_playbook_or_403(
    db: AsyncSession,
    playbook_id: UUID,
    current_user,
    require_owner: bool = False,
) -> "Playbook":
    """Fetch a playbook and verify the current user has access.

    Raises 404 if not found, 403 if no access.
    If require_owner=True, only the creator can access (not just same-org).
    """
    result = await db.execute(
        select(Playbook).where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    # Public playbooks are readable by anyone (but not writable)
    if playbook.is_public and not require_owner:
        return playbook

    # Check ownership
    is_owner = str(playbook.created_by) == str(current_user.id)
    is_same_org = (
        hasattr(current_user, 'organization_id')
        and current_user.organization_id
        and str(playbook.organization_id) == str(current_user.organization_id)
    )
    is_super = getattr(current_user, 'role', None) == 'super_admin'

    if require_owner:
        if not is_owner and not is_super:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        if not is_owner and not is_same_org and not is_super:
            raise HTTPException(status_code=403, detail="Access denied")

    return playbook


# ============================================================================
# Schemas
# ============================================================================

class PlaybookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: str = "custom"
    is_public: bool = False
    party_side: Literal["buyer", "seller", "neutral"] = "neutral"


class PlaybookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    party_side: Optional[Literal["buyer", "seller", "neutral"]] = None


class PlaybookResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str
    is_public: bool
    is_default: bool
    version: int
    party_side: Literal["buyer", "seller", "neutral"] = "neutral"
    rules_count: int = 0
    # Whether the requesting user owns this playbook (drives Edit/Delete UI).
    is_owner: bool = False

    model_config = ConfigDict(from_attributes=True)


def _normalize_rule_label(value: str) -> str:
    """Canonicalize known types while preserving custom rule identity."""
    raw = (value or "").strip()
    snapped = snap_to_clause_type(raw).value
    if snapped != "unknown" or raw.lower() == "unknown":
        return snapped
    slug = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return (slug or "custom_rule")[:100]


class RuleCreate(BaseModel):
    clause_type: str = Field(..., min_length=1, max_length=200)
    primary_position: str = Field(..., min_length=1, max_length=5000)
    fallback_position: Optional[str] = Field(default=None, max_length=5000)
    risk_level: Literal["red", "yellow", "green"] = "yellow"
    is_deal_breaker: bool = False
    detection_patterns: List[str] = Field(default_factory=list)
    match_type: Literal["exact", "fuzzy", "regex"] = "exact"
    suggested_language: Optional[str] = Field(default=None, max_length=5000)
    # P2 #29: AI-primary detection fields
    detection_mode: str = "keywords_only"

    @field_validator("clause_type")
    @classmethod
    def normalize_clause_type(cls, v: str) -> str:
        # Phase C1 — snap free strings to canonical taxonomy
        return _normalize_rule_label(v)

    @field_validator("detection_mode")
    @classmethod
    def validate_detection_mode(cls, v: str) -> str:
        aliases = {"ai_primary": "ai_only", "hybrid": "ai_with_keywords"}
        v = aliases.get(v, v)
        allowed = {"ai_only", "ai_with_keywords", "keywords_only"}
        if v not in allowed:
            raise ValueError(f"detection_mode must be one of {allowed}, got '{v}'")
        return v
    risk_description: Optional[str] = Field(default=None, max_length=5000)
    acceptable_position: Optional[str] = Field(default=None, max_length=5000)
    unacceptable_signals: Optional[List[str]] = None
    acceptable_signals: Optional[List[str]] = None
    clause_context: Optional[str] = Field(default=None, max_length=5000)
    verification_prompt: Optional[str] = Field(default=None, max_length=5000)


class RuleUpdate(BaseModel):
    clause_type: Optional[str] = None
    primary_position: Optional[str] = None
    fallback_position: Optional[str] = None
    risk_level: Optional[Literal["red", "yellow", "green"]] = None
    is_deal_breaker: Optional[bool] = None
    detection_patterns: Optional[List[str]] = None
    match_type: Optional[Literal["exact", "fuzzy", "regex"]] = None
    suggested_language: Optional[str] = None
    # P2 #29: AI-primary detection fields
    detection_mode: Optional[str] = None

    @field_validator("clause_type")
    @classmethod
    def normalize_clause_type(cls, v: Optional[str]) -> Optional[str]:
        # Phase C1 — snap free strings to canonical taxonomy
        if v is None:
            return None
        return _normalize_rule_label(v)

    @field_validator("detection_mode")
    @classmethod
    def validate_detection_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            aliases = {"ai_primary": "ai_only", "hybrid": "ai_with_keywords"}
            v = aliases.get(v, v)
            allowed = {"ai_only", "ai_with_keywords", "keywords_only"}
            if v not in allowed:
                raise ValueError(f"detection_mode must be one of {allowed}, got '{v}'")
        return v
    risk_description: Optional[str] = None
    acceptable_position: Optional[str] = None
    unacceptable_signals: Optional[List[str]] = None
    acceptable_signals: Optional[List[str]] = None
    clause_context: Optional[str] = None
    verification_prompt: Optional[str] = Field(default=None, max_length=5000)


class RuleResponse(BaseModel):
    id: str
    clause_type: str
    primary_position: str
    fallback_position: Optional[str]
    risk_level: str
    is_deal_breaker: bool
    detection_patterns: List[str]
    match_type: str = "exact"
    suggested_language: Optional[str]
    order_index: int
    # P2 #29: AI-primary detection fields
    detection_mode: str = "keywords_only"
    risk_description: Optional[str] = None
    acceptable_position: Optional[str] = None
    unacceptable_signals: Optional[List[str]] = None
    acceptable_signals: Optional[List[str]] = None
    clause_context: Optional[str] = None
    verification_prompt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PlaybookDetail(PlaybookResponse):
    rules: List[RuleResponse]


class PlaybookListResponse(BaseModel):
    items: List[PlaybookResponse]
    total: int
    skip: int
    limit: int


class ReorderRequest(BaseModel):
    rule_ids: List[str]  # Ordered list of rule IDs


# ============================================================================
# Playbook CRUD Endpoints
# ============================================================================

@router.get("/", response_model=PlaybookListResponse)
async def list_playbooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available playbooks for the current user."""
    access_conditions = [
        Playbook.is_public.is_(True),
        Playbook.created_by == current_user.id,
    ]
    if current_user.organization_id is not None:
        access_conditions.append(
            Playbook.organization_id == current_user.organization_id
        )
    access_filter = or_(*access_conditions)

    # Total count
    count_query = select(func.count(Playbook.id)).where(access_filter)
    total = (await db.execute(count_query)).scalar() or 0

    # Paginated data
    query = (
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(access_filter)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    playbooks = result.scalars().all()

    return PlaybookListResponse(
        items=[
            PlaybookResponse(
                id=str(p.id),
                name=p.name,
                description=p.description,
                category=p.category.value,
                is_public=p.is_public,
                is_default=p.is_default,
                version=p.version,
                party_side=p.party_side or "neutral",
                rules_count=len(p.rules_list) if p.rules_list else 0,
                is_owner=str(p.created_by) == str(current_user.id),
            )
            for p in playbooks
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")  # AUDIT FIX M3: Rate limit playbook write endpoints
async def create_playbook(
    request: Request,
    playbook_data: PlaybookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new playbook. Open to any authenticated user — playbooks are
    scoped to the creator and their organization (see _get_playbook_or_403)."""
    
    if playbook_data.is_public:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Create the playbook privately, add and validate its rules, "
                "then use the publish action."
            ),
        )

    try:
        category = PlaybookCategory(playbook_data.category)
    except ValueError:
        category = PlaybookCategory.CUSTOM
    
    playbook = Playbook(
        name=playbook_data.name,
        description=playbook_data.description,
        category=category,
        created_by=current_user.id,
        organization_id=current_user.organization_id,
        is_public=False,
        party_side=playbook_data.party_side,
    )
    
    db.add(playbook)
    await db.flush()

    await log_audit_event(
        db=db, user=current_user, action="playbook_created",
        resource_type="playbook", resource_name=playbook.name, status="success",
    )
    await db.commit()
    await db.refresh(playbook)

    return PlaybookResponse(
        id=str(playbook.id),
        name=playbook.name,
        description=playbook.description,
        category=playbook.category.value,
        is_public=playbook.is_public,
        is_default=playbook.is_default,
        version=playbook.version,
        party_side=playbook.party_side or "neutral",
        rules_count=0,
        is_owner=True,
    )


# ============================================================================
# Marketplace routes (MUST be registered before /{playbook_id} to avoid shadowing)
# ============================================================================

class MarketplaceListItem(BaseModel):
    id: str
    playbook_id: str
    playbook_name: str
    category: str
    description: Optional[str]
    is_verified: bool
    download_count: int
    avg_rating: float
    rating_count: int
    tags: List[str]


class MarketplacePublishRequest(BaseModel):
    tags: List[str] = Field(default_factory=list)


class MarketplaceBrowseResponse(BaseModel):
    items: List[MarketplaceListItem]
    total: int


class RatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = None


@router.get("/marketplace/browse", response_model=MarketplaceBrowseResponse)
async def browse_marketplace(
    category: Optional[str] = None,
    search: Optional[str] = Query(None, max_length=200, description="Search by playbook name"),
    sort_by: Optional[str] = Query("rating", pattern=r"^(rating|downloads|name)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Browse community playbooks in the marketplace."""
    base_query = (
        select(PlaybookMarketplace)
        .join(Playbook, PlaybookMarketplace.playbook_id == Playbook.id)
        .where(Playbook.is_public.is_(True))
    )

    # Filter by category
    if category:
        try:
            cat_enum = PlaybookCategory(category)
            base_query = base_query.where(Playbook.category == cat_enum)
        except ValueError:
            return MarketplaceBrowseResponse(items=[], total=0)

    # Search by name
    if search:
        escaped_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        base_query = base_query.where(Playbook.name.ilike(f"%{escaped_search}%"))

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    if sort_by == "downloads":
        base_query = base_query.order_by(PlaybookMarketplace.download_count.desc())
    elif sort_by == "name":
        base_query = base_query.order_by(Playbook.name)
    else:  # default: rating
        base_query = base_query.order_by(PlaybookMarketplace.avg_rating.desc())

    # Paginated results
    data_query = base_query.options(selectinload(PlaybookMarketplace.playbook)).offset(skip).limit(limit)
    result = await db.execute(data_query)
    items = result.scalars().all()

    return MarketplaceBrowseResponse(
        items=[
            MarketplaceListItem(
                id=str(item.id), playbook_id=str(item.playbook_id),
                playbook_name=item.playbook.name, category=item.playbook.category.value,
                description=item.playbook.description, is_verified=item.is_verified,
                download_count=item.download_count,
                avg_rating=float(item.avg_rating or 0),
                rating_count=item.rating_count,
                tags=item.tags if isinstance(item.tags, list) else [],
            )
            for item in items
        ],
        total=total,
    )


@router.post("/marketplace/{marketplace_id}/fork", response_model=PlaybookResponse)
async def fork_playbook(
    marketplace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fork a marketplace playbook into your organization."""
    # Get marketplace entry with playbook and rules
    mp_result = await db.execute(
        select(PlaybookMarketplace)
        .options(
            selectinload(PlaybookMarketplace.playbook)
            .selectinload(Playbook.rules_list)
            .selectinload(PlaybookRule.tiers)
        )
        .where(PlaybookMarketplace.id == marketplace_id)
    )
    mp = mp_result.scalar_one_or_none()
    if not mp:
        raise HTTPException(status_code=404, detail="Marketplace entry not found")

    source = mp.playbook
    if not source.is_public:
        raise HTTPException(status_code=404, detail="Marketplace entry not found")

    # Create new playbook (fork)
    new_pb = Playbook(
        name=f"{source.name} (Fork)",
        description=source.description,
        category=source.category,
        created_by=current_user.id,
        organization_id=current_user.organization_id,
        party_side=source.party_side or "neutral",
    )
    db.add(new_pb)
    await db.flush()

    # Copy rules and tiers, building a map of old rule IDs to new rule IDs
    rule_id_map = {}  # str(old_rule_id) -> str(new_rule_id)
    for rule in (source.rules_list or []):
        new_rule = PlaybookRule(
            playbook_id=new_pb.id,
            clause_type=rule.clause_type,
            primary_position=rule.primary_position,
            fallback_position=rule.fallback_position,
            risk_level=rule.risk_level,
            is_deal_breaker=rule.is_deal_breaker,
            detection_patterns=rule.detection_patterns,
            suggested_language=rule.suggested_language,
            order_index=rule.order_index,
            requires_ai_verification=rule.requires_ai_verification,
            verification_prompt=rule.verification_prompt,
            jurisdiction_overrides=rule.jurisdiction_overrides,
            priority=rule.priority,
            category=rule.category,
            subcategory=rule.subcategory,
            tags=rule.tags,
            # P2 #29: Copy AI-primary detection fields
            detection_mode=rule.detection_mode,
            risk_description=rule.risk_description,
            acceptable_position=rule.acceptable_position,
            unacceptable_signals=rule.unacceptable_signals,
            acceptable_signals=rule.acceptable_signals,
            clause_context=rule.clause_context,
        )
        db.add(new_rule)
        await db.flush()
        rule_id_map[str(rule.id)] = str(new_rule.id)

        for tier in (rule.tiers or []):
            new_tier = PlaybookRuleTier(
                rule_id=new_rule.id,
                tier_level=tier.tier_level,
                position_text=tier.position_text,
                guidance_notes=tier.guidance_notes,
                risk_level_at_tier=tier.risk_level_at_tier,
            )
            db.add(new_tier)

    # Copy conditions and their overrides
    old_conditions = await db.execute(
        select(PlaybookCondition).where(PlaybookCondition.playbook_id == source.id)
    )
    for old_cond in old_conditions.scalars().all():
        new_cond = PlaybookCondition(
            id=uuid.uuid4(),
            playbook_id=new_pb.id,
            name=old_cond.name,
            description=old_cond.description,
            condition_type=old_cond.condition_type,
            operator=old_cond.operator,
            condition_value=old_cond.condition_value,
            priority=old_cond.priority,
            is_active=old_cond.is_active,
        )
        db.add(new_cond)
        await db.flush()

        # Copy overrides for this condition, remapping rule_ids
        old_overrides = await db.execute(
            select(PlaybookRuleOverride).where(PlaybookRuleOverride.condition_id == old_cond.id)
        )
        for old_ov in old_overrides.scalars().all():
            new_rule_id = rule_id_map.get(str(old_ov.rule_id))
            if new_rule_id:
                new_ov = PlaybookRuleOverride(
                    id=uuid.uuid4(),
                    condition_id=new_cond.id,
                    rule_id=uuid.UUID(new_rule_id),
                    override_risk_level=old_ov.override_risk_level,
                    override_position_text=old_ov.override_position_text,
                    override_is_deal_breaker=old_ov.override_is_deal_breaker,
                    override_tier_level=old_ov.override_tier_level,
                    suppress_rule=old_ov.suppress_rule,
                )
                db.add(new_ov)

    # Copy dependencies, remapping rule_ids
    if rule_id_map:
        old_deps = await db.execute(
            select(PlaybookRuleDependency).where(
                PlaybookRuleDependency.source_rule_id.in_([uuid.UUID(k) for k in rule_id_map.keys()])
            )
        )
        for old_dep in old_deps.scalars().all():
            new_source = rule_id_map.get(str(old_dep.source_rule_id))
            new_target = rule_id_map.get(str(old_dep.target_rule_id))
            if new_source and new_target:
                new_dep = PlaybookRuleDependency(
                    id=uuid.uuid4(),
                    playbook_id=new_pb.id,
                    source_rule_id=uuid.UUID(new_source),
                    target_rule_id=uuid.UUID(new_target),
                    trigger_condition=old_dep.trigger_condition,
                    effect=old_dep.effect,
                    effect_params=old_dep.effect_params,
                    is_active=old_dep.is_active,
                )
                db.add(new_dep)

    # Increment download count
    mp.download_count = (mp.download_count or 0) + 1

    await db.commit()
    await db.refresh(new_pb)

    return PlaybookResponse(
        id=str(new_pb.id), name=new_pb.name, description=new_pb.description,
        category=new_pb.category.value, is_public=new_pb.is_public,
        is_default=new_pb.is_default, version=new_pb.version,
        party_side=new_pb.party_side or "neutral",
        rules_count=len(source.rules_list or []),
        is_owner=True,
    )


@router.post("/marketplace/{marketplace_id}/rate", status_code=201)
async def rate_playbook(
    marketplace_id: UUID,
    data: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rate a marketplace playbook."""
    # Check marketplace entry exists
    mp_result = await db.execute(
        select(PlaybookMarketplace).where(PlaybookMarketplace.id == marketplace_id)
    )
    mp = mp_result.scalar_one_or_none()
    if not mp:
        raise HTTPException(status_code=404, detail="Marketplace entry not found")
    playbook_result = await db.execute(
        select(Playbook.is_public).where(Playbook.id == mp.playbook_id)
    )
    if playbook_result.scalar_one_or_none() is not True:
        raise HTTPException(status_code=404, detail="Marketplace entry not found")

    # Prevent duplicate ratings from the same user
    existing = await db.execute(
        select(PlaybookRating).where(
            PlaybookRating.marketplace_id == marketplace_id,
            PlaybookRating.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already rated this playbook. Update your existing rating instead.",
        )

    rating = PlaybookRating(
        marketplace_id=marketplace_id,
        user_id=current_user.id,
        rating=data.rating,
        review=data.review,
    )
    db.add(rating)

    # Update aggregate
    total = (mp.avg_rating or 0) * (mp.rating_count or 0) + data.rating
    mp.rating_count = (mp.rating_count or 0) + 1
    mp.avg_rating = total / mp.rating_count

    await db.commit()
    return {"status": "ok"}


@router.put("/marketplace/{marketplace_id}/rate")
async def update_rating(
    marketplace_id: UUID,
    data: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing marketplace playbook rating."""
    # Check marketplace entry exists
    mp_result = await db.execute(
        select(PlaybookMarketplace).where(PlaybookMarketplace.id == marketplace_id)
    )
    mp = mp_result.scalar_one_or_none()
    if not mp:
        raise HTTPException(status_code=404, detail="Marketplace entry not found")
    playbook_result = await db.execute(
        select(Playbook.is_public).where(Playbook.id == mp.playbook_id)
    )
    if playbook_result.scalar_one_or_none() is not True:
        raise HTTPException(status_code=404, detail="Marketplace entry not found")

    # Find existing rating
    existing_result = await db.execute(
        select(PlaybookRating).where(
            PlaybookRating.marketplace_id == marketplace_id,
            PlaybookRating.user_id == current_user.id,
        )
    )
    existing_rating = existing_result.scalar_one_or_none()
    if not existing_rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existing rating found. Use POST to create a rating first.",
        )

    # Recalculate aggregate: subtract old, add new
    old_total = (mp.avg_rating or 0) * (mp.rating_count or 0)
    new_total = old_total - existing_rating.rating + data.rating
    mp.avg_rating = new_total / mp.rating_count if mp.rating_count else data.rating

    # Update rating
    existing_rating.rating = data.rating
    existing_rating.review = data.review

    await db.commit()
    return {"status": "ok"}


# ============================================================================
# Playbook detail and sub-resource routes (/{playbook_id} catch-all MUST come after
# all specific path routes like /marketplace/... to avoid route shadowing)
# ============================================================================

@router.get("/{playbook_id}", response_model=PlaybookDetail)
async def get_playbook(
    playbook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get playbook details including rules."""
    await _get_playbook_or_403(db, playbook_id, current_user)
    result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    
    # Sort rules by order_index
    sorted_rules = sorted(playbook.rules_list, key=lambda r: r.order_index) if playbook.rules_list else []
    
    return PlaybookDetail(
        id=str(playbook.id),
        name=playbook.name,
        description=playbook.description,
        category=playbook.category.value,
        is_public=playbook.is_public,
        is_default=playbook.is_default,
        version=playbook.version,
        party_side=playbook.party_side or "neutral",
        rules_count=len(sorted_rules),
        rules=[
            RuleResponse(
                id=str(r.id),
                clause_type=r.clause_type,
                primary_position=r.primary_position,
                fallback_position=r.fallback_position,
                risk_level=r.risk_level.value,
                is_deal_breaker=r.is_deal_breaker,
                detection_patterns=r.detection_patterns.get("patterns", []) if r.detection_patterns else [],
                match_type=r.detection_patterns.get("match_type", "exact") if isinstance(r.detection_patterns, dict) else "exact",
                suggested_language=r.suggested_language.get("text") if r.suggested_language else None,
                order_index=r.order_index,
                detection_mode=r.detection_mode or "keywords_only",
                risk_description=r.risk_description,
                acceptable_position=r.acceptable_position,
                unacceptable_signals=r.unacceptable_signals,
                acceptable_signals=r.acceptable_signals,
                clause_context=r.clause_context,
                verification_prompt=r.verification_prompt,
            )
            for r in sorted_rules
        ],
    )


@router.put("/{playbook_id}", response_model=PlaybookResponse)
@limiter.limit("30/minute")  # AUDIT FIX M3
async def update_playbook(
    request: Request,
    playbook_id: UUID,
    update_data: PlaybookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update playbook metadata. Requires ADMIN role."""
    result = await db.execute(
        select(Playbook).where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    # Check ownership
    if playbook.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can update this playbook")
    
    # Update fields
    if update_data.name is not None:
        playbook.name = update_data.name
    if update_data.description is not None:
        playbook.description = update_data.description
    if update_data.category is not None:
        try:
            playbook.category = PlaybookCategory(update_data.category)
        except ValueError:
            pass
    if update_data.party_side is not None:
        playbook.party_side = update_data.party_side
    
    _mark_playbook_changed(playbook)

    await log_audit_event(
        db=db, user=current_user, action="playbook_updated",
        resource_type="playbook", resource_name=playbook.name, status="success",
    )
    await db.commit()
    invalidate_playbook_cache(str(playbook_id))

    # Reload with rules to get accurate count
    result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one()

    return PlaybookResponse(
        id=str(playbook.id),
        name=playbook.name,
        description=playbook.description,
        category=playbook.category.value,
        is_public=playbook.is_public,
        is_default=playbook.is_default,
        version=playbook.version,
        party_side=playbook.party_side or "neutral",
        rules_count=len(playbook.rules_list) if playbook.rules_list else 0,
        is_owner=str(playbook.created_by) == str(current_user.id),
    )


@router.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")  # AUDIT FIX M3
async def delete_playbook(
    request: Request,
    playbook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a playbook. Requires ADMIN role."""
    playbook = await _get_playbook_or_403(db, playbook_id, current_user, require_owner=True)

    playbook_name = playbook.name
    await db.delete(playbook)

    await log_audit_event(
        db=db, user=current_user, action="playbook_deleted",
        resource_type="playbook", resource_name=playbook_name, status="success",
    )
    await db.commit()
    invalidate_playbook_cache(str(playbook_id))


@router.post("/{playbook_id}/publish", response_model=PlaybookResponse)
async def toggle_publish(
    playbook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle playbook public/private status. Requires ADMIN role."""
    result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    if playbook.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can publish this playbook")
    
    publishing = not playbook.is_public
    if publishing:
        _require_publishable_playbook(list(playbook.rules_list or []))

    playbook.is_public = publishing
    playbook.version += 1

    await db.commit()

    # Reload with rules to get accurate count
    result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one()

    return PlaybookResponse(
        id=str(playbook.id),
        name=playbook.name,
        description=playbook.description,
        category=playbook.category.value,
        is_public=playbook.is_public,
        is_default=playbook.is_default,
        version=playbook.version,
        party_side=playbook.party_side or "neutral",
        rules_count=len(playbook.rules_list) if playbook.rules_list else 0,
        is_owner=str(playbook.created_by) == str(current_user.id),
    )


@router.get("/{playbook_id}/quality")
async def get_playbook_quality(
    playbook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explain whether a playbook contains enough context for reliable analysis."""
    await _get_playbook_or_403(db, playbook_id, current_user)
    result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one()
    issues = _playbook_quality_issues(list(playbook.rules_list or []))
    recommendations = _playbook_quality_recommendations(list(playbook.rules_list or []))
    return {
        "playbook_id": str(playbook.id),
        "publishable": not issues,
        "issues": issues,
        "recommendations": recommendations,
        "rules_count": len(playbook.rules_list or []),
    }


# ============================================================================
# Rule Management Endpoints
# ============================================================================

@router.post("/{playbook_id}/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")  # AUDIT FIX M3
async def add_rule(
    request: Request,
    playbook_id: UUID,
    rule_data: RuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a rule to a playbook. Requires ADMIN role."""
    result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    if playbook.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can add rules")

    # Validate regex patterns before storing
    if rule_data.match_type == "regex":
        for pattern in rule_data.detection_patterns:
            try:
                _safe_compile_regex(pattern)
            except (re.error, ValueError) as e:
                logger.warning("Invalid regex pattern submitted: %s", e)
                raise HTTPException(status_code=400, detail="Invalid regex pattern. Please check your pattern syntax.")

    # Validate risk level
    try:
        risk_level = RiskLevel(rule_data.risk_level.lower())
    except ValueError:
        risk_level = RiskLevel.YELLOW
    
    # Get next order index
    max_order = max((r.order_index for r in playbook.rules_list), default=-1)
    
    rule = PlaybookRule(
        playbook_id=playbook.id,
        clause_type=rule_data.clause_type,
        primary_position=rule_data.primary_position,
        fallback_position=rule_data.fallback_position,
        risk_level=risk_level,
        is_deal_breaker=rule_data.is_deal_breaker,
        detection_patterns={"patterns": rule_data.detection_patterns, "match_type": rule_data.match_type},
        suggested_language={"text": rule_data.suggested_language} if rule_data.suggested_language else None,
        order_index=max_order + 1,
        # P2 #29: AI-primary detection fields
        detection_mode=rule_data.detection_mode,
        risk_description=rule_data.risk_description,
        acceptable_position=rule_data.acceptable_position,
        unacceptable_signals=rule_data.unacceptable_signals,
        acceptable_signals=rule_data.acceptable_signals,
        clause_context=rule_data.clause_context,
        verification_prompt=rule_data.verification_prompt,
    )

    db.add(rule)
    _mark_playbook_changed(playbook)

    await db.commit()
    await db.refresh(rule)

    return RuleResponse(
        id=str(rule.id),
        clause_type=rule.clause_type,
        primary_position=rule.primary_position,
        fallback_position=rule.fallback_position,
        risk_level=rule.risk_level.value,
        is_deal_breaker=rule.is_deal_breaker,
        detection_patterns=rule_data.detection_patterns,
        match_type=rule_data.match_type,
        suggested_language=rule_data.suggested_language,
        order_index=rule.order_index,
        detection_mode=rule.detection_mode,
        risk_description=rule.risk_description,
        acceptable_position=rule.acceptable_position,
        unacceptable_signals=rule.unacceptable_signals,
        acceptable_signals=rule.acceptable_signals,
        clause_context=rule.clause_context,
        verification_prompt=rule.verification_prompt,
    )


@router.put("/{playbook_id}/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    playbook_id: UUID,
    rule_id: UUID,
    update_data: RuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a rule in a playbook. Requires ADMIN role."""
    # Check playbook ownership
    playbook_result = await db.execute(
        select(Playbook).where(Playbook.id == playbook_id)
    )
    playbook = playbook_result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    if playbook.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can update rules")
    
    # Get rule
    rule_result = await db.execute(
        select(PlaybookRule).where(
            PlaybookRule.id == rule_id,
            PlaybookRule.playbook_id == playbook_id
        )
    )
    rule = rule_result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update fields
    if update_data.clause_type is not None:
        rule.clause_type = update_data.clause_type
    if update_data.primary_position is not None:
        rule.primary_position = update_data.primary_position
    if update_data.fallback_position is not None:
        rule.fallback_position = update_data.fallback_position
    if update_data.risk_level is not None:
        rule.risk_level = RiskLevel(update_data.risk_level)
    if update_data.is_deal_breaker is not None:
        rule.is_deal_breaker = update_data.is_deal_breaker
    if (
        update_data.detection_patterns is not None
        or update_data.match_type is not None
    ):
        existing_patterns = (rule.detection_patterns or {}).get("patterns", [])
        existing_match_type = (rule.detection_patterns or {}).get(
            "match_type", "exact"
        )
        new_patterns = (
            update_data.detection_patterns
            if update_data.detection_patterns is not None
            else existing_patterns
        )
        new_match_type = update_data.match_type or existing_match_type
        if new_match_type == "regex":
            for pattern in new_patterns:
                try:
                    _safe_compile_regex(pattern)
                except (re.error, ValueError) as exc:
                    logger.warning("Invalid regex pattern submitted: %s", exc)
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Invalid regex pattern. Please check your "
                            "pattern syntax."
                        ),
                    ) from exc
        rule.detection_patterns = {
            "patterns": new_patterns,
            "match_type": new_match_type,
        }
    if update_data.suggested_language is not None:
        rule.suggested_language = {"text": update_data.suggested_language}
    # P2 #29: AI-primary detection fields
    if update_data.detection_mode is not None:
        rule.detection_mode = update_data.detection_mode
    if update_data.risk_description is not None:
        rule.risk_description = update_data.risk_description
    if update_data.acceptable_position is not None:
        rule.acceptable_position = update_data.acceptable_position
    if update_data.unacceptable_signals is not None:
        rule.unacceptable_signals = update_data.unacceptable_signals
    if update_data.acceptable_signals is not None:
        rule.acceptable_signals = update_data.acceptable_signals
    if update_data.clause_context is not None:
        rule.clause_context = update_data.clause_context
    if update_data.verification_prompt is not None:
        rule.verification_prompt = update_data.verification_prompt

    _mark_playbook_changed(playbook)

    await db.commit()
    await db.refresh(rule)

    return RuleResponse(
        id=str(rule.id),
        clause_type=rule.clause_type,
        primary_position=rule.primary_position,
        fallback_position=rule.fallback_position,
        risk_level=rule.risk_level.value,
        is_deal_breaker=rule.is_deal_breaker,
        detection_patterns=rule.detection_patterns.get("patterns", []) if rule.detection_patterns else [],
        match_type=rule.detection_patterns.get("match_type", "exact") if isinstance(rule.detection_patterns, dict) else "exact",
        suggested_language=rule.suggested_language.get("text") if rule.suggested_language else None,
        order_index=rule.order_index,
        detection_mode=rule.detection_mode or "keywords_only",
        risk_description=rule.risk_description,
        acceptable_position=rule.acceptable_position,
        unacceptable_signals=rule.unacceptable_signals,
        acceptable_signals=rule.acceptable_signals,
        clause_context=rule.clause_context,
        verification_prompt=rule.verification_prompt,
    )


@router.delete("/{playbook_id}/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")  # AUDIT FIX M3
async def delete_rule(
    request: Request,
    playbook_id: UUID,
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a rule from a playbook. Requires ADMIN role."""
    # Check playbook ownership
    playbook_result = await db.execute(
        select(Playbook).where(Playbook.id == playbook_id)
    )
    playbook = playbook_result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    if playbook.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can delete rules")
    
    # Get rule
    rule_result = await db.execute(
        select(PlaybookRule).where(
            PlaybookRule.id == rule_id,
            PlaybookRule.playbook_id == playbook_id
        )
    )
    rule = rule_result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.delete(rule)
    _mark_playbook_changed(playbook)
    await db.commit()


@router.post("/{playbook_id}/rules/reorder", response_model=List[RuleResponse])
async def reorder_rules(
    playbook_id: UUID,
    reorder_data: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reorder rules within a playbook. Requires ADMIN role."""
    playbook_result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    playbook = playbook_result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    if playbook.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can reorder rules")
    
    rule_map = {str(r.id): r for r in playbook.rules_list}
    submitted = reorder_data.rule_ids
    if len(submitted) != len(set(submitted)) or set(submitted) != set(rule_map):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "rule_ids must contain every rule in this playbook exactly "
                "once."
            ),
        )

    for index, rule_id in enumerate(reorder_data.rule_ids):
        rule_map[rule_id].order_index = index
    
    _mark_playbook_changed(playbook)
    await db.commit()
    
    # Return reordered rules
    sorted_rules = sorted(playbook.rules_list, key=lambda r: r.order_index)
    
    return [
        RuleResponse(
            id=str(r.id),
            clause_type=r.clause_type,
            primary_position=r.primary_position,
            fallback_position=r.fallback_position,
            risk_level=r.risk_level.value,
            is_deal_breaker=r.is_deal_breaker,
            detection_patterns=r.detection_patterns.get("patterns", []) if r.detection_patterns else [],
            match_type=r.detection_patterns.get("match_type", "exact") if isinstance(r.detection_patterns, dict) else "exact",
            suggested_language=r.suggested_language.get("text") if r.suggested_language else None,
            order_index=r.order_index,
            detection_mode=r.detection_mode or "keywords_only",
            risk_description=r.risk_description,
            acceptable_position=r.acceptable_position,
            unacceptable_signals=r.unacceptable_signals,
            acceptable_signals=r.acceptable_signals,
            clause_context=r.clause_context,
            verification_prompt=r.verification_prompt,
        )
        for r in sorted_rules
    ]


# ============================================================================
# Phase 6: Tier Schemas & Endpoints
# ============================================================================

class TierCreate(BaseModel):
    tier_level: int = Field(..., ge=1, le=4)
    position_text: str = Field(..., min_length=1)
    guidance_notes: Optional[str] = None
    risk_level_at_tier: Literal["red", "yellow", "green"] = "yellow"


class TierResponse(BaseModel):
    id: str
    tier_level: int
    position_text: str
    guidance_notes: Optional[str]
    risk_level_at_tier: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/{playbook_id}/rules/{rule_id}/tiers", response_model=List[TierResponse])
async def list_tiers(
    playbook_id: UUID,
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all negotiation tiers for a rule."""
    await _get_playbook_or_403(db, playbook_id, current_user)

    # Verify rule belongs to this playbook
    rule_result = await db.execute(
        select(PlaybookRule).where(
            PlaybookRule.id == rule_id,
            PlaybookRule.playbook_id == playbook_id,
        )
    )
    rule = rule_result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found in this playbook")

    result = await db.execute(
        select(PlaybookRuleTier)
        .where(PlaybookRuleTier.rule_id == rule_id)
        .order_by(PlaybookRuleTier.tier_level)
    )
    tiers = result.scalars().all()
    return [
        TierResponse(
            id=str(t.id), tier_level=t.tier_level, position_text=t.position_text,
            guidance_notes=t.guidance_notes, risk_level_at_tier=t.risk_level_at_tier or "yellow",
        )
        for t in tiers
    ]


@router.put("/{playbook_id}/rules/{rule_id}/tiers", response_model=List[TierResponse])
async def upsert_tiers(
    playbook_id: UUID,
    rule_id: UUID,
    tiers_data: List[TierCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or replace all tiers for a rule (bulk upsert). Requires ADMIN role."""
    await _get_playbook_or_403(db, playbook_id, current_user, require_owner=True)

    # Verify rule belongs to playbook
    rule_result = await db.execute(
        select(PlaybookRule).where(PlaybookRule.id == rule_id, PlaybookRule.playbook_id == playbook_id)
    )
    rule = rule_result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    tier_levels = [tier.tier_level for tier in tiers_data]
    if len(tier_levels) != len(set(tier_levels)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Each negotiation tier level may appear only once.",
        )

    # Delete existing tiers
    await db.execute(delete(PlaybookRuleTier).where(PlaybookRuleTier.rule_id == rule_id))

    # Create new tiers
    new_tiers = []
    for td in tiers_data:
        tier = PlaybookRuleTier(
            rule_id=rule_id,
            tier_level=td.tier_level,
            position_text=td.position_text,
            guidance_notes=td.guidance_notes,
            risk_level_at_tier=td.risk_level_at_tier,
        )
        db.add(tier)
        new_tiers.append(tier)

    # Snapshot version
    playbook_result = await db.execute(select(Playbook).where(Playbook.id == playbook_id))
    playbook = playbook_result.scalar_one()
    _mark_playbook_changed(playbook)

    await db.commit()
    for t in new_tiers:
        await db.refresh(t)

    return [
        TierResponse(
            id=str(t.id), tier_level=t.tier_level, position_text=t.position_text,
            guidance_notes=t.guidance_notes, risk_level_at_tier=t.risk_level_at_tier or "yellow",
        )
        for t in sorted(new_tiers, key=lambda x: x.tier_level)
    ]


# ============================================================================
# Phase 6: Condition Schemas & Endpoints
# ============================================================================

class ConditionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    condition_type: Literal[
        "counterparty_type", "deal_size", "jurisdiction",
        "contract_side", "custom",
    ]
    operator: Literal[
        "equals", "not_equals", "in", "not_in", "contains",
        "greater_than", "less_than", "between",
    ] = "equals"
    condition_value: dict = Field(..., max_length=50)  # Max 50 keys in the dict
    is_active: bool = True
    priority: int = 0

    @field_validator("condition_value")
    @classmethod
    def validate_condition_value_size(cls, v: dict) -> dict:
        """Limit condition_value dict size to prevent abuse."""
        import json
        serialized = json.dumps(v)
        if len(serialized) > 10000:
            raise ValueError("condition_value is too large (max 10KB serialized)")
        if len(v) > 50:
            raise ValueError("condition_value has too many keys (max 50)")
        return v

    @model_validator(mode="after")
    def validate_operator_and_value(self) -> "ConditionCreate":
        string_operators = {
            "equals", "not_equals", "in", "not_in", "contains",
        }
        numeric_operators = {
            "equals", "not_equals", "greater_than", "less_than", "between",
        }
        if self.condition_type == "deal_size":
            if self.operator not in numeric_operators:
                raise ValueError(
                    f"Operator '{self.operator}' is not valid for deal_size"
                )
            if self.operator == "between":
                minimum = self.condition_value.get("min")
                maximum = self.condition_value.get("max")
                if not isinstance(minimum, (int, float)) or not isinstance(
                    maximum, (int, float)
                ):
                    raise ValueError(
                        "A between deal-size condition requires numeric min and max"
                    )
                if minimum > maximum:
                    raise ValueError("Deal-size min cannot exceed max")
            else:
                threshold = self.condition_value.get(
                    "threshold",
                    self.condition_value.get("value"),
                )
                if not isinstance(threshold, (int, float)):
                    raise ValueError(
                        "A deal-size condition requires a numeric threshold"
                    )
            return self

        if self.operator not in string_operators:
            raise ValueError(
                f"Operator '{self.operator}' is not valid for "
                f"{self.condition_type}"
            )
        if self.condition_type == "custom" and not self.condition_value.get("key"):
            raise ValueError("A custom condition requires a key")
        if self.operator in {"in", "not_in"}:
            values = self.condition_value.get("values")
            if not isinstance(values, list) or not values:
                raise ValueError(
                    f"Operator '{self.operator}' requires a non-empty values list"
                )
        elif "value" not in self.condition_value:
            raise ValueError(
                f"Operator '{self.operator}' requires a value"
            )
        return self


class ConditionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    condition_type: str
    operator: str
    condition_value: dict
    is_active: bool
    priority: int
    overrides_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class OverrideCreate(BaseModel):
    rule_id: str
    override_risk_level: Optional[
        Literal["red", "yellow", "green"]
    ] = None
    override_position_text: Optional[str] = None
    override_is_deal_breaker: Optional[bool] = None
    override_tier_level: Optional[int] = Field(default=None, ge=1, le=4)
    suppress_rule: bool = False
    notes: Optional[str] = None


class OverrideResponse(BaseModel):
    id: str
    condition_id: str
    rule_id: str
    override_risk_level: Optional[str]
    override_position_text: Optional[str]
    override_is_deal_breaker: Optional[bool]
    override_tier_level: Optional[int]
    suppress_rule: bool
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


@router.get("/{playbook_id}/conditions", response_model=List[ConditionResponse])
async def list_conditions(
    playbook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conditions for a playbook."""
    await _get_playbook_or_403(db, playbook_id, current_user)

    result = await db.execute(
        select(PlaybookCondition)
        .options(selectinload(PlaybookCondition.rule_overrides))
        .where(PlaybookCondition.playbook_id == playbook_id)
        .order_by(PlaybookCondition.priority.desc())
    )
    conditions = result.scalars().all()
    return [
        ConditionResponse(
            id=str(c.id), name=c.name, description=c.description,
            condition_type=c.condition_type, operator=c.operator,
            condition_value=c.condition_value, is_active=c.is_active,
            priority=c.priority,
            overrides_count=len(c.rule_overrides) if c.rule_overrides else 0,
        )
        for c in conditions
    ]


@router.post("/{playbook_id}/conditions", response_model=ConditionResponse, status_code=201)
async def create_condition(
    playbook_id: UUID,
    data: ConditionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new condition for a playbook."""
    playbook = await _get_playbook_or_403(
        db, playbook_id, current_user, require_owner=True
    )

    condition = PlaybookCondition(
        playbook_id=playbook_id,
        name=data.name,
        description=data.description,
        condition_type=data.condition_type,
        operator=data.operator,
        condition_value=data.condition_value,
        is_active=data.is_active,
        priority=data.priority,
    )
    db.add(condition)
    _mark_playbook_changed(playbook)
    await db.commit()
    await db.refresh(condition)

    return ConditionResponse(
        id=str(condition.id), name=condition.name, description=condition.description,
        condition_type=condition.condition_type, operator=condition.operator,
        condition_value=condition.condition_value, is_active=condition.is_active,
        priority=condition.priority, overrides_count=0,
    )


@router.delete("/{playbook_id}/conditions/{condition_id}", status_code=204)
async def delete_condition(
    playbook_id: UUID,
    condition_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a condition and its overrides."""
    playbook = await _get_playbook_or_403(
        db, playbook_id, current_user, require_owner=True
    )

    result = await db.execute(
        select(PlaybookCondition).where(
            PlaybookCondition.id == condition_id,
            PlaybookCondition.playbook_id == playbook_id,
        )
    )
    condition = result.scalar_one_or_none()
    if not condition:
        raise HTTPException(status_code=404, detail="Condition not found")
    await db.delete(condition)
    _mark_playbook_changed(playbook)
    await db.commit()


@router.post("/{playbook_id}/conditions/{condition_id}/overrides", response_model=OverrideResponse, status_code=201)
async def add_override(
    playbook_id: UUID,
    condition_id: UUID,
    data: OverrideCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a rule override to a condition."""
    playbook = await _get_playbook_or_403(
        db, playbook_id, current_user, require_owner=True
    )

    # Verify condition belongs to this playbook
    cond_result = await db.execute(
        select(PlaybookCondition).where(
            PlaybookCondition.id == condition_id,
            PlaybookCondition.playbook_id == playbook_id,
        )
    )
    if not cond_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Condition not found in this playbook")

    try:
        rule_id_val = UUID(data.rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule_id format")
    rule_result = await db.execute(
        select(PlaybookRule.id).where(
            PlaybookRule.id == rule_id_val,
            PlaybookRule.playbook_id == playbook_id,
        )
    )
    if rule_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404, detail="Rule not found in this playbook"
        )

    override = PlaybookRuleOverride(
        condition_id=condition_id,
        rule_id=rule_id_val,
        override_risk_level=data.override_risk_level,
        override_position_text=data.override_position_text,
        override_is_deal_breaker=data.override_is_deal_breaker,
        override_tier_level=data.override_tier_level,
        suppress_rule=data.suppress_rule,
        notes=data.notes,
    )
    db.add(override)
    _mark_playbook_changed(playbook)
    await db.commit()
    await db.refresh(override)

    return OverrideResponse(
        id=str(override.id), condition_id=str(override.condition_id),
        rule_id=str(override.rule_id), override_risk_level=override.override_risk_level,
        override_position_text=override.override_position_text,
        override_is_deal_breaker=override.override_is_deal_breaker,
        override_tier_level=override.override_tier_level,
        suppress_rule=override.suppress_rule, notes=override.notes,
    )


@router.delete("/{playbook_id}/conditions/{condition_id}/overrides/{override_id}", status_code=204)
async def delete_override(
    playbook_id: UUID,
    condition_id: UUID,
    override_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a rule override."""
    playbook = await _get_playbook_or_403(
        db, playbook_id, current_user, require_owner=True
    )

    # Verify condition belongs to this playbook
    cond_result = await db.execute(
        select(PlaybookCondition).where(
            PlaybookCondition.id == condition_id,
            PlaybookCondition.playbook_id == playbook_id,
        )
    )
    if not cond_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Condition not found in this playbook")

    result = await db.execute(
        select(PlaybookRuleOverride).where(
            PlaybookRuleOverride.id == override_id,
            PlaybookRuleOverride.condition_id == condition_id,
        )
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")
    await db.delete(override)
    _mark_playbook_changed(playbook)
    await db.commit()


# ============================================================================
# Phase 6: Cross-Clause Dependencies
# ============================================================================

class DependencyCreate(BaseModel):
    source_rule_id: str
    target_rule_id: str
    trigger_condition: Literal[
        "source_is_red", "source_is_yellow", "source_missing",
        "source_uncapped", "source_deal_breaker",
    ]
    effect: Literal[
        "escalate_risk", "add_flag", "change_position", "suppress"
    ]
    effect_params: Optional[dict] = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_effect_parameters(self) -> "DependencyCreate":
        params = self.effect_params or {}
        if self.source_rule_id == self.target_rule_id:
            raise ValueError("A dependency cannot target its own source rule")
        if self.effect == "escalate_risk":
            risk = str(params.get("new_risk", "")).upper()
            if risk not in {"RED", "YELLOW", "GREEN"}:
                raise ValueError(
                    "escalate_risk requires new_risk set to RED, YELLOW, or GREEN"
                )
        elif self.effect == "add_flag":
            if not str(params.get("message", "")).strip():
                raise ValueError("add_flag requires a non-empty message")
        elif self.effect == "change_position":
            if not str(params.get("new_position", "")).strip():
                raise ValueError(
                    "change_position requires a non-empty new_position"
                )
        return self


class DependencyResponse(BaseModel):
    id: str
    source_rule_id: str
    target_rule_id: str
    trigger_condition: str
    effect: str
    effect_params: Optional[dict]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


@router.get("/{playbook_id}/dependencies", response_model=List[DependencyResponse])
async def list_dependencies(
    playbook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all cross-clause dependencies for a playbook."""
    await _get_playbook_or_403(db, playbook_id, current_user)

    result = await db.execute(
        select(PlaybookRuleDependency).where(PlaybookRuleDependency.playbook_id == playbook_id)
    )
    deps = result.scalars().all()
    return [
        DependencyResponse(
            id=str(d.id), source_rule_id=str(d.source_rule_id),
            target_rule_id=str(d.target_rule_id), trigger_condition=d.trigger_condition,
            effect=d.effect, effect_params=d.effect_params, is_active=d.is_active,
        )
        for d in deps
    ]


@router.post("/{playbook_id}/dependencies", response_model=DependencyResponse, status_code=201)
async def create_dependency(
    playbook_id: UUID,
    data: DependencyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a cross-clause dependency."""
    playbook = await _get_playbook_or_403(
        db, playbook_id, current_user, require_owner=True
    )

    try:
        source_rule_id_val = UUID(data.source_rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid source_rule_id format")
    try:
        target_rule_id_val = UUID(data.target_rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid target_rule_id format")
    rule_rows = await db.execute(
        select(PlaybookRule.id).where(
            PlaybookRule.playbook_id == playbook_id,
            PlaybookRule.id.in_(
                [source_rule_id_val, target_rule_id_val]
            ),
        )
    )
    if set(rule_rows.scalars().all()) != {
        source_rule_id_val, target_rule_id_val
    }:
        raise HTTPException(
            status_code=404,
            detail="Source and target rules must belong to this playbook",
        )

    existing_rows = await db.execute(
        select(
            PlaybookRuleDependency.source_rule_id,
            PlaybookRuleDependency.target_rule_id,
        ).where(
            PlaybookRuleDependency.playbook_id == playbook_id,
            PlaybookRuleDependency.is_active.is_(True),
        )
    )
    adjacency: dict[UUID, set[UUID]] = {}
    for source_id, target_id in existing_rows.all():
        adjacency.setdefault(source_id, set()).add(target_id)
    adjacency.setdefault(source_rule_id_val, set()).add(target_rule_id_val)
    pending = [target_rule_id_val]
    visited: set[UUID] = set()
    while pending:
        node = pending.pop()
        if node == source_rule_id_val:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This dependency would create a cycle. Remove or reverse "
                    "an existing dependency first."
                ),
            )
        if node in visited:
            continue
        visited.add(node)
        pending.extend(adjacency.get(node, set()))

    dep = PlaybookRuleDependency(
        playbook_id=playbook_id,
        source_rule_id=source_rule_id_val,
        target_rule_id=target_rule_id_val,
        trigger_condition=data.trigger_condition,
        effect=data.effect,
        effect_params=data.effect_params,
        is_active=data.is_active,
    )
    db.add(dep)
    _mark_playbook_changed(playbook)
    await db.commit()
    await db.refresh(dep)

    return DependencyResponse(
        id=str(dep.id), source_rule_id=str(dep.source_rule_id),
        target_rule_id=str(dep.target_rule_id), trigger_condition=dep.trigger_condition,
        effect=dep.effect, effect_params=dep.effect_params, is_active=dep.is_active,
    )


@router.delete("/{playbook_id}/dependencies/{dep_id}", status_code=204)
async def delete_dependency(
    playbook_id: UUID,
    dep_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dependency."""
    playbook = await _get_playbook_or_403(
        db, playbook_id, current_user, require_owner=True
    )

    result = await db.execute(
        select(PlaybookRuleDependency).where(
            PlaybookRuleDependency.id == dep_id,
            PlaybookRuleDependency.playbook_id == playbook_id,
        )
    )
    dep = result.scalar_one_or_none()
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
    await db.delete(dep)
    _mark_playbook_changed(playbook)
    await db.commit()


# ============================================================================
# Phase 6: Version Control
# ============================================================================

class VersionResponse(BaseModel):
    id: str
    version_number: int
    change_summary: Optional[str]
    created_by: Optional[str]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class VersionDetailResponse(VersionResponse):
    snapshot: dict


class DiffResponse(BaseModel):
    rules_added: List[dict]
    rules_removed: List[dict]
    rules_modified: List[dict]
    conditions_added: List[dict]
    conditions_removed: List[dict]
    dependencies_added: List[dict]
    dependencies_removed: List[dict]


@router.get("/{playbook_id}/versions", response_model=List[VersionResponse])
async def list_versions(
    playbook_id: UUID,
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List version history for a playbook."""
    await _get_playbook_or_403(db, playbook_id, current_user)

    versions = await playbook_versioning_service.get_versions(db, playbook_id, limit)
    return [
        VersionResponse(
            id=str(v["id"]), version_number=v["version_number"],
            change_summary=v.get("change_summary"),
            created_by=str(v["created_by"]) if v.get("created_by") else None,
            created_at=str(v["created_at"]),
        )
        for v in versions
    ]


@router.post("/{playbook_id}/versions", response_model=VersionResponse, status_code=201)
async def create_version_snapshot(
    playbook_id: UUID,
    change_summary: str = Query("Manual snapshot"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a version snapshot of the current playbook state."""
    await _get_playbook_or_403(db, playbook_id, current_user, require_owner=True)

    version = await playbook_versioning_service.create_snapshot(
        db, playbook_id, change_summary, current_user.id
    )
    return VersionResponse(
        id=str(version.id), version_number=version.version_number,
        change_summary=version.change_summary,
        created_by=str(version.created_by) if version.created_by else None,
        created_at=str(version.created_at),
    )


@router.get("/{playbook_id}/versions/diff/{version_a_id}/{version_b_id}", response_model=DiffResponse)
async def diff_versions(
    playbook_id: UUID,
    version_a_id: UUID,
    version_b_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare two versions of a playbook."""
    await _get_playbook_or_403(db, playbook_id, current_user)
    try:
        version_a = await playbook_versioning_service.get_version(
            db, version_a_id
        )
        version_b = await playbook_versioning_service.get_version(
            db, version_b_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Version not found") from exc
    if (
        str(version_a["playbook_id"]) != str(playbook_id)
        or str(version_b["playbook_id"]) != str(playbook_id)
    ):
        raise HTTPException(
            status_code=404,
            detail="One or both versions do not belong to this playbook",
        )

    diff = await playbook_versioning_service.diff_versions(db, version_a_id, version_b_id)
    return DiffResponse(**diff)


@router.get("/{playbook_id}/versions/{version_id}", response_model=VersionDetailResponse)
async def get_version_detail(
    playbook_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full snapshot for a specific version."""
    await _get_playbook_or_403(db, playbook_id, current_user)

    try:
        version_data = await playbook_versioning_service.get_version(
            db, version_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Version not found") from exc
    if str(version_data["playbook_id"]) != str(playbook_id):
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionDetailResponse(
        id=str(version_data["id"]), version_number=version_data["version_number"],
        change_summary=version_data.get("change_summary"),
        created_by=str(version_data["created_by"]) if version_data.get("created_by") else None,
        created_at=str(version_data["created_at"]),
        snapshot=version_data["snapshot"],
    )


@router.post("/{playbook_id}/versions/{version_id}/rollback", response_model=VersionResponse)
async def rollback_to_version(
    playbook_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rollback a playbook to a previous version."""
    await _get_playbook_or_403(db, playbook_id, current_user, require_owner=True)

    try:
        await playbook_versioning_service.rollback(
            db, playbook_id, version_id, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Return the new version created by rollback
    versions = await playbook_versioning_service.get_versions(db, playbook_id, 1)
    v = versions[0]
    return VersionResponse(
        id=str(v["id"]), version_number=v["version_number"],
        change_summary=v.get("change_summary"),
        created_by=str(v["created_by"]) if v.get("created_by") else None,
        created_at=str(v["created_at"]),
    )


@router.post("/{playbook_id}/marketplace/publish", response_model=MarketplaceListItem)
async def publish_to_marketplace(
    playbook_id: UUID,
    data: MarketplacePublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a playbook to the marketplace."""
    # Get playbook with rules for preview
    pb_result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    pb = pb_result.scalar_one_or_none()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")

    if pb.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can publish")

    _require_publishable_playbook(list(pb.rules_list or []))

    # Make playbook public only after the latest quality gate passes.
    pb.is_public = True
    pb.version += 1

    # Preview: first 5 rules
    preview = [
        {"clause_type": r.clause_type, "risk_level": r.risk_level.value}
        for r in sorted(pb.rules_list, key=lambda r: r.order_index)[:5]
    ] if pb.rules_list else []

    existing_entry = await db.execute(
        select(PlaybookMarketplace).where(
            PlaybookMarketplace.playbook_id == playbook_id
        )
    )
    entry = existing_entry.scalar_one_or_none()
    if entry is None:
        entry = PlaybookMarketplace(
            playbook_id=playbook_id,
            publisher_org_id=current_user.organization_id,
            tags=data.tags,
            preview_rules=preview,
        )
        db.add(entry)
    else:
        entry.publisher_org_id = current_user.organization_id
        entry.tags = data.tags
        entry.preview_rules = preview
        entry.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(entry)

    return MarketplaceListItem(
        id=str(entry.id), playbook_id=str(entry.playbook_id),
        playbook_name=pb.name, category=pb.category.value,
        description=pb.description, is_verified=False,
        download_count=0, avg_rating=0.0, rating_count=0,
        tags=data.tags,
    )
