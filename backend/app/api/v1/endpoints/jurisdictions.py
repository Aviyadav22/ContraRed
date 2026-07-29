"""
Jurisdiction API endpoints.

Provides read-only access to jurisdiction profiles and rule overrides
for the Global Jurisdiction Engine.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.jurisdiction import Jurisdiction

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class JurisdictionSummary(BaseModel):
    code: str
    name: str
    display_name: str
    legal_system: str
    is_active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class RuleOverrideResponse(BaseModel):
    clause_type: str
    risk_level: Optional[str] = None
    suppress: bool = False
    primary_position: Optional[str] = None
    note: Optional[str] = None
    statute_reference: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JurisdictionDetail(BaseModel):
    code: str
    name: str
    display_name: str
    legal_system: str
    parent_code: Optional[str] = None
    key_statutes: Optional[list] = None
    special_considerations: Optional[list] = None
    indemnification_standard: Optional[str] = None
    non_compete_enforceability: Optional[str] = None
    arbitration_framework: Optional[str] = None
    data_protection_law: Optional[str] = None
    aliases: Optional[list] = None
    is_active: bool
    sort_order: int
    rule_overrides: List[RuleOverrideResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[JurisdictionSummary])
async def list_jurisdictions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active jurisdictions (for toggle UI)."""
    result = await db.execute(
        select(Jurisdiction)
        .where(Jurisdiction.is_active == True)  # noqa: E712
        .order_by(Jurisdiction.sort_order, Jurisdiction.name)
    )
    jurisdictions = result.scalars().all()
    return jurisdictions


@router.get("/{code}", response_model=JurisdictionDetail)
async def get_jurisdiction(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full jurisdiction profile + rule overrides."""
    result = await db.execute(
        select(Jurisdiction)
        .options(selectinload(Jurisdiction.rule_overrides))
        .where(Jurisdiction.code == code.upper())
    )
    jurisdiction = result.scalar_one_or_none()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail=f"Jurisdiction '{code}' not found")

    return JurisdictionDetail(
        code=jurisdiction.code,
        name=jurisdiction.name,
        display_name=jurisdiction.display_name,
        legal_system=jurisdiction.legal_system,
        parent_code=jurisdiction.parent_code,
        key_statutes=jurisdiction.key_statutes,
        special_considerations=jurisdiction.special_considerations,
        indemnification_standard=jurisdiction.indemnification_standard,
        non_compete_enforceability=jurisdiction.non_compete_enforceability,
        arbitration_framework=jurisdiction.arbitration_framework,
        data_protection_law=jurisdiction.data_protection_law,
        aliases=jurisdiction.aliases,
        is_active=jurisdiction.is_active,
        sort_order=jurisdiction.sort_order,
        rule_overrides=[
            RuleOverrideResponse(
                clause_type=ov.clause_type,
                risk_level=ov.risk_level,
                suppress=ov.suppress,
                primary_position=ov.primary_position,
                note=ov.note,
                statute_reference=ov.statute_reference,
            )
            for ov in jurisdiction.rule_overrides
        ],
    )
