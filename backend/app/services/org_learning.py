"""
Organization Learning Service.
Records user decisions on clause types and generates contextual prompts
from institutional memory (org-level risk profiles).
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_risk_profile import OrganizationRiskProfile

logger = logging.getLogger(__name__)

# Minimum encounters before org context is injected into AI prompts
MIN_ENCOUNTERS_THRESHOLD = 10


async def record_user_decision(
    db: AsyncSession,
    org_id: UUID,
    clause_type: str,
    decision: str,
) -> None:
    """Record a user's decision on a clause type.

    Args:
        db: Database session.
        org_id: Organization ID.
        clause_type: The clause type (e.g., "limitation_of_liability").
        decision: One of "accept", "reject", "modify", "escalate".
    """
    if not org_id or not clause_type:
        return

    result = await db.execute(
        select(OrganizationRiskProfile).where(
            OrganizationRiskProfile.organization_id == org_id,
            OrganizationRiskProfile.clause_type == clause_type,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = OrganizationRiskProfile(
            organization_id=org_id,
            clause_type=clause_type,
        )
        db.add(profile)

    profile.total_encounters += 1
    if decision == "accept":
        profile.accept_count += 1
    elif decision == "reject":
        profile.reject_count += 1
    elif decision == "modify":
        profile.modify_count += 1
    elif decision == "escalate":
        profile.escalate_count += 1

    profile.last_updated = datetime.now(timezone.utc)
    await db.flush()


async def get_org_risk_profile(
    db: AsyncSession,
    org_id: UUID,
) -> List[Dict]:
    """Return all risk profiles for an organization."""
    result = await db.execute(
        select(OrganizationRiskProfile)
        .where(OrganizationRiskProfile.organization_id == org_id)
        .order_by(OrganizationRiskProfile.total_encounters.desc())
    )
    profiles = result.scalars().all()
    return [
        {
            "clause_type": p.clause_type,
            "total_encounters": p.total_encounters,
            "accept_count": p.accept_count,
            "reject_count": p.reject_count,
            "modify_count": p.modify_count,
            "escalate_count": p.escalate_count,
            "accept_rate": round(p.accept_count / p.total_encounters, 2) if p.total_encounters > 0 else 0,
            "reject_rate": round(p.reject_count / p.total_encounters, 2) if p.total_encounters > 0 else 0,
        }
        for p in profiles
    ]


async def generate_org_context(
    db: AsyncSession,
    org_id: Optional[UUID],
    clause_types: Optional[List[str]] = None,
) -> str:
    """Generate prompt context from org risk profiles.

    Only injects context for clause types with >= MIN_ENCOUNTERS_THRESHOLD encounters.
    Returns empty string if no relevant profiles or insufficient data.
    """
    if not org_id:
        return ""

    query = (
        select(OrganizationRiskProfile)
        .where(
            OrganizationRiskProfile.organization_id == org_id,
            OrganizationRiskProfile.total_encounters >= MIN_ENCOUNTERS_THRESHOLD,
        )
    )
    if clause_types:
        query = query.where(OrganizationRiskProfile.clause_type.in_(clause_types))

    result = await db.execute(query)
    profiles = result.scalars().all()

    if not profiles:
        return ""

    lines = ["## ORGANIZATION RISK CONTEXT (Institutional Memory)", ""]
    lines.append("This organization has historical preferences based on past contract reviews:")
    lines.append("")

    for p in profiles:
        accept_rate = round(p.accept_count / p.total_encounters * 100) if p.total_encounters > 0 else 0
        reject_rate = round(p.reject_count / p.total_encounters * 100) if p.total_encounters > 0 else 0
        modify_rate = round(p.modify_count / p.total_encounters * 100) if p.total_encounters > 0 else 0

        clause_label = p.clause_type.replace("_", " ").title()

        if reject_rate >= 60:
            stance = "STRICT — usually rejects this clause type"
        elif accept_rate >= 70:
            stance = "LENIENT — usually accepts this clause type"
        elif modify_rate >= 40:
            stance = "MODERATE — frequently requests modifications"
        else:
            stance = "VARIABLE — no strong preference"

        lines.append(
            f"- **{clause_label}** ({p.total_encounters} reviews): "
            f"{stance} (accept {accept_rate}%, reject {reject_rate}%, modify {modify_rate}%)"
        )

    lines.append("")
    lines.append("Use this context to calibrate your risk assessment. A clause type that this "
                  "organization frequently rejects should be flagged at a higher risk level.")

    return "\n".join(lines)
