"""
Playbook management endpoints.
Full CRUD for playbooks and rules.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.user import User
from app.models.playbook import Playbook, PlaybookRule, PlaybookCategory, RiskLevel
from app.api.v1.endpoints.auth import get_current_user
from app.api.dependencies import require_admin
from app.models.audit_log import log_audit_event


router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class PlaybookCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "custom"
    is_public: bool = False


class PlaybookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class PlaybookResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str
    is_public: bool
    is_default: bool
    version: int
    rules_count: int = 0
    
    class Config:
        from_attributes = True


class RuleCreate(BaseModel):
    clause_type: str = Field(..., min_length=1, max_length=200)
    primary_position: str = Field(..., min_length=1, max_length=5000)
    fallback_position: Optional[str] = Field(default=None, max_length=5000)
    risk_level: str = "yellow"
    is_deal_breaker: bool = False
    detection_patterns: List[str] = Field(default_factory=list)
    match_type: str = "exact"  # exact|fuzzy|regex - 'exact' auto-escapes for non-regex users
    suggested_language: Optional[str] = Field(default=None, max_length=5000)


class RuleUpdate(BaseModel):
    clause_type: Optional[str] = None
    primary_position: Optional[str] = None
    fallback_position: Optional[str] = None
    risk_level: Optional[str] = None
    is_deal_breaker: Optional[bool] = None
    detection_patterns: Optional[List[str]] = None
    match_type: Optional[str] = None  # exact|fuzzy|regex
    suggested_language: Optional[str] = None


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
    
    class Config:
        from_attributes = True


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
    skip: int = 0,
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available playbooks for the current user."""
    access_filter = or_(
        Playbook.is_public == True,
        Playbook.created_by == current_user.id,
        Playbook.organization_id == current_user.organization_id,
    )

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
                rules_count=len(p.rules_list) if p.rules_list else 0,
            )
            for p in playbooks
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    playbook_data: PlaybookCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new playbook. Requires ADMIN role."""
    
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
        is_public=playbook_data.is_public,
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
        rules_count=0,
    )


@router.get("/{playbook_id}", response_model=PlaybookDetail)
async def get_playbook(
    playbook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get playbook details including rules."""
    result = await db.execute(
        select(Playbook)
        .options(selectinload(Playbook.rules_list))
        .where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found"
        )
    
    # Check access
    if not playbook.is_public:
        if playbook.created_by != current_user.id and playbook.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
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
            )
            for r in sorted_rules
        ],
    )


@router.put("/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    playbook_id: UUID,
    update_data: PlaybookUpdate,
    current_user: User = Depends(require_admin),
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
    
    playbook.version += 1

    await log_audit_event(
        db=db, user=current_user, action="playbook_updated",
        resource_type="playbook", resource_name=playbook.name, status="success",
    )
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
        rules_count=len(playbook.rules_list) if playbook.rules_list else 0,
    )


@router.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook(
    playbook_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a playbook. Requires ADMIN role."""
    result = await db.execute(
        select(Playbook).where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    playbook_name = playbook.name
    await db.delete(playbook)

    await log_audit_event(
        db=db, user=current_user, action="playbook_deleted",
        resource_type="playbook", resource_name=playbook_name, status="success",
    )
    await db.commit()


@router.post("/{playbook_id}/publish", response_model=PlaybookResponse)
async def toggle_publish(
    playbook_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Toggle playbook public/private status. Requires ADMIN role."""
    result = await db.execute(
        select(Playbook).where(Playbook.id == playbook_id)
    )
    playbook = result.scalar_one_or_none()
    
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    if playbook.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can publish this playbook")
    
    playbook.is_public = not playbook.is_public
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
        rules_count=len(playbook.rules_list) if playbook.rules_list else 0,
    )


# ============================================================================
# Rule Management Endpoints
# ============================================================================

@router.post("/{playbook_id}/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def add_rule(
    playbook_id: UUID,
    rule_data: RuleCreate,
    current_user: User = Depends(require_admin),
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
    )
    
    db.add(rule)
    playbook.version += 1
    
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
    )


@router.put("/{playbook_id}/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    playbook_id: UUID,
    rule_id: UUID,
    update_data: RuleUpdate,
    current_user: User = Depends(require_admin),
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
        try:
            rule.risk_level = RiskLevel(update_data.risk_level.lower())
        except ValueError:
            pass
    if update_data.is_deal_breaker is not None:
        rule.is_deal_breaker = update_data.is_deal_breaker
    if update_data.detection_patterns is not None:
        existing_match_type = (rule.detection_patterns or {}).get("match_type", "exact")
        rule.detection_patterns = {"patterns": update_data.detection_patterns, "match_type": update_data.match_type or existing_match_type}
    if update_data.suggested_language is not None:
        rule.suggested_language = {"text": update_data.suggested_language}
    
    playbook.version += 1
    
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
    )


@router.delete("/{playbook_id}/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    playbook_id: UUID,
    rule_id: UUID,
    current_user: User = Depends(require_admin),
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
    playbook.version += 1
    await db.commit()


@router.post("/{playbook_id}/rules/reorder", response_model=List[RuleResponse])
async def reorder_rules(
    playbook_id: UUID,
    reorder_data: ReorderRequest,
    current_user: User = Depends(require_admin),
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
    
    # Update order indices
    rule_map = {str(r.id): r for r in playbook.rules_list}
    
    for index, rule_id in enumerate(reorder_data.rule_ids):
        if rule_id in rule_map:
            rule_map[rule_id].order_index = index
    
    playbook.version += 1
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
        )
        for r in sorted_rules
    ]
