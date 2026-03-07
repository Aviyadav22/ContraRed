"""
Clause Library endpoints.
CRUD for organization-scoped saved clauses.
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.models.user import User
from app.models.playbook import ClauseLibrary
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class ClauseCreate(BaseModel):
    clause_type: str
    name: str
    approved_text: str
    is_mandatory: bool = False


class ClauseUpdate(BaseModel):
    name: Optional[str] = None
    approved_text: Optional[str] = None
    clause_type: Optional[str] = None
    is_mandatory: Optional[bool] = None


class ClauseResponse(BaseModel):
    id: str
    clause_type: str
    name: str
    approved_text: str
    is_mandatory: bool
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[ClauseResponse])
async def list_clauses(
    clause_type: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List active clauses. Filter by exact clause_type or fuzzy search on clause_type + name."""
    query = select(ClauseLibrary).where(ClauseLibrary.is_active == True)

    # Scope to user's org or clauses they created
    if current_user.organization_id:
        query = query.where(
            (ClauseLibrary.organization_id == current_user.organization_id) |
            (ClauseLibrary.created_by == current_user.id)
        )
    else:
        query = query.where(ClauseLibrary.created_by == current_user.id)

    if clause_type:
        query = query.where(ClauseLibrary.clause_type == clause_type)

    if search:
        search_term = f"%{search}%"
        query = query.where(or_(
            ClauseLibrary.clause_type.ilike(search_term),
            ClauseLibrary.name.ilike(search_term)
        ))

    query = query.order_by(ClauseLibrary.clause_type, ClauseLibrary.name)
    result = await db.execute(query)
    clauses = result.scalars().all()

    return [
        ClauseResponse(
            id=str(c.id),
            clause_type=c.clause_type,
            name=c.name,
            approved_text=c.approved_text,
            is_mandatory=c.is_mandatory,
            is_active=c.is_active,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in clauses
    ]


@router.post("/", response_model=ClauseResponse, status_code=status.HTTP_201_CREATED)
async def create_clause(
    data: ClauseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new saved clause."""
    clause = ClauseLibrary(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        clause_type=data.clause_type,
        name=data.name,
        approved_text=data.approved_text,
        is_mandatory=data.is_mandatory,
    )
    db.add(clause)
    await db.commit()
    await db.refresh(clause)

    return ClauseResponse(
        id=str(clause.id),
        clause_type=clause.clause_type,
        name=clause.name,
        approved_text=clause.approved_text,
        is_mandatory=clause.is_mandatory,
        is_active=clause.is_active,
        created_at=clause.created_at.isoformat(),
        updated_at=clause.updated_at.isoformat(),
    )


@router.get("/{clause_id}", response_model=ClauseResponse)
async def get_clause(
    clause_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a single clause."""
    clause = await _get_clause_or_404(clause_id, current_user, db)
    return ClauseResponse(
        id=str(clause.id),
        clause_type=clause.clause_type,
        name=clause.name,
        approved_text=clause.approved_text,
        is_mandatory=clause.is_mandatory,
        is_active=clause.is_active,
        created_at=clause.created_at.isoformat(),
        updated_at=clause.updated_at.isoformat(),
    )


@router.put("/{clause_id}", response_model=ClauseResponse)
async def update_clause(
    clause_id: UUID,
    data: ClauseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a saved clause."""
    clause = await _get_clause_or_404(clause_id, current_user, db)

    if data.name is not None:
        clause.name = data.name
    if data.approved_text is not None:
        clause.approved_text = data.approved_text
    if data.clause_type is not None:
        clause.clause_type = data.clause_type
    if data.is_mandatory is not None:
        clause.is_mandatory = data.is_mandatory

    await db.commit()
    await db.refresh(clause)

    return ClauseResponse(
        id=str(clause.id),
        clause_type=clause.clause_type,
        name=clause.name,
        approved_text=clause.approved_text,
        is_mandatory=clause.is_mandatory,
        is_active=clause.is_active,
        created_at=clause.created_at.isoformat(),
        updated_at=clause.updated_at.isoformat(),
    )


@router.delete("/{clause_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clause(
    clause_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft-delete a clause (set is_active=False)."""
    clause = await _get_clause_or_404(clause_id, current_user, db)
    clause.is_active = False
    await db.commit()


async def _get_clause_or_404(
    clause_id: UUID,
    current_user: User,
    db: AsyncSession
) -> ClauseLibrary:
    """Fetch clause by ID, verifying access."""
    result = await db.execute(
        select(ClauseLibrary).where(ClauseLibrary.id == clause_id)
    )
    clause = result.scalar_one_or_none()

    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")

    # Check access: must belong to user's org or be created by user
    if current_user.organization_id:
        if clause.organization_id != current_user.organization_id and clause.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        if clause.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return clause
