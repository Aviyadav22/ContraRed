"""
Contract Template Library endpoints.

Pre-built Indian contract templates paired with playbooks.
Free users get non-premium templates; Pro/Enterprise get all.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.user import User, SubscriptionTier, UserRole
from app.models.template import ContractTemplate
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class TemplateListItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    is_premium: bool
    download_count: int
    paired_playbook_id: Optional[str] = None
    paired_playbook_name: Optional[str] = None

    class Config:
        from_attributes = True


class TemplateDetail(TemplateListItem):
    template_content: Optional[str] = None
    created_at: str


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: str = Field(default="custom", max_length=100)
    template_content: Optional[str] = Field(default=None, max_length=100000)
    paired_playbook_id: Optional[str] = Field(default=None, max_length=100)
    is_premium: bool = False


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[TemplateListItem])
async def list_templates(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available contract templates. Non-premium only for free users."""
    query = select(ContractTemplate).options(selectinload(ContractTemplate.paired_playbook))

    if category:
        query = query.where(ContractTemplate.category == category)

    # Free users only see non-premium templates
    is_free = current_user.subscription_tier == SubscriptionTier.FREE
    if is_free:
        query = query.where(ContractTemplate.is_premium == False)

    query = query.order_by(ContractTemplate.name)
    try:
        result = await db.execute(query)
        templates = result.scalars().all()
    except Exception as e:
        logger.warning("Could not query templates (table may not exist): %s", e)
        return []

    return [
        TemplateListItem(
            id=str(t.id),
            name=t.name,
            description=t.description,
            category=t.category,
            is_premium=t.is_premium,
            download_count=t.download_count,
            paired_playbook_id=str(t.paired_playbook_id) if t.paired_playbook_id else None,
            paired_playbook_name=t.paired_playbook.name if t.paired_playbook else None,
        )
        for t in templates
    ]


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get template details including content."""
    result = await db.execute(
        select(ContractTemplate)
        .options(selectinload(ContractTemplate.paired_playbook))
        .where(ContractTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Check premium access
    is_free = current_user.subscription_tier == SubscriptionTier.FREE
    if template.is_premium and is_free:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Premium template requires Pro or Enterprise subscription")

    return TemplateDetail(
        id=str(template.id),
        name=template.name,
        description=template.description,
        category=template.category,
        is_premium=template.is_premium,
        download_count=template.download_count,
        paired_playbook_id=str(template.paired_playbook_id) if template.paired_playbook_id else None,
        paired_playbook_name=template.paired_playbook.name if template.paired_playbook else None,
        template_content=template.template_content,
        created_at=template.created_at.isoformat() if template.created_at else "",
    )


@router.get("/{template_id}/download")
async def download_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download template content and increment download count."""
    result = await db.execute(
        select(ContractTemplate).where(ContractTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Check premium access
    is_free = current_user.subscription_tier == SubscriptionTier.FREE
    if template.is_premium and is_free:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Premium template requires Pro or Enterprise subscription")

    # Increment download count
    template.download_count = (template.download_count or 0) + 1
    await db.commit()

    return {
        "id": str(template.id),
        "name": template.name,
        "template_content": template.template_content,
        "paired_playbook_id": str(template.paired_playbook_id) if template.paired_playbook_id else None,
    }


@router.post("/", response_model=TemplateListItem, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: CreateTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new template (admin only)."""
    # Check admin role
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create templates")

    playbook_uuid = None
    if request.paired_playbook_id:
        try:
            playbook_uuid = UUID(request.paired_playbook_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid playbook ID")

    template = ContractTemplate(
        name=request.name,
        description=request.description,
        category=request.category,
        template_content=request.template_content,
        paired_playbook_id=playbook_uuid,
        is_premium=request.is_premium,
        created_by=current_user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return TemplateListItem(
        id=str(template.id),
        name=template.name,
        description=template.description,
        category=template.category,
        is_premium=template.is_premium,
        download_count=0,
        paired_playbook_id=str(template.paired_playbook_id) if template.paired_playbook_id else None,
        paired_playbook_name=None,
    )
