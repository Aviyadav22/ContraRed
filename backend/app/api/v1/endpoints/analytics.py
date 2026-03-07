"""
Analytics endpoints — Firm-wide dashboard stats.

Admin-only endpoints providing aggregated usage and risk data.
"""

import csv
import io
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import get_current_user
from app.services import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _sanitize_csv_value(value) -> str:
    """Prevent CSV injection by escaping formula-triggering characters."""
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def _require_admin(user: User):
    """Raise 403 if user is not admin."""
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.get("/overview")
async def analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Org-level summary stats: scans, risks, active users."""
    _require_admin(current_user)

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_org_overview(db, current_user.organization_id, days=days)


@router.get("/risks")
async def analytics_risks(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Risk breakdown by clause type and level."""
    _require_admin(current_user)

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_risk_breakdown(db, current_user.organization_id, days=days)


@router.get("/users")
async def analytics_users(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-user activity stats."""
    _require_admin(current_user)

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_user_activity(db, current_user.organization_id, days=days)


@router.get("/trends")
async def analytics_trends(
    period: str = "weekly",
    weeks: int = Query(default=12, ge=1, le=52),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Time-series usage data (weekly or daily)."""
    _require_admin(current_user)

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    if period not in ("weekly", "daily"):
        raise HTTPException(status_code=400, detail="Period must be 'weekly' or 'daily'")

    return await analytics_service.get_trend_data(db, current_user.organization_id, period=period, weeks=weeks)


@router.get("/export")
async def analytics_export(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics as CSV."""
    _require_admin(current_user)

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # Gather all data
    overview = await analytics_service.get_org_overview(db, current_user.organization_id, days=days)
    risks = await analytics_service.get_risk_breakdown(db, current_user.organization_id, days=days)
    users = await analytics_service.get_user_activity(db, current_user.organization_id, days=days)

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Overview section
    writer.writerow(["ContraRed Analytics Report"])
    writer.writerow([f"Period: Last {days} days"])
    writer.writerow([])
    writer.writerow(["Overview"])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Documents Analyzed", overview["documents_analyzed"]])
    writer.writerow(["Total Risks Found", overview["total_risks"]])
    writer.writerow(["Red Risks", overview["red_risks"]])
    writer.writerow(["Yellow Risks", overview["yellow_risks"]])
    writer.writerow(["Active Users", overview["active_users"]])
    writer.writerow([])

    # Risk breakdown
    writer.writerow(["Risk Breakdown by Level"])
    writer.writerow(["Risk Level", "Red", "Yellow", "Green", "Total"])
    for r in risks:
        writer.writerow([_sanitize_csv_value(r["risk_level"]), r["red"], r["yellow"], r["green"], r["total"]])
    writer.writerow([])

    # User activity
    writer.writerow(["User Activity"])
    writer.writerow(["Name", "Email", "Scans", "Risks Found", "Last Scan"])
    for u in users:
        writer.writerow([_sanitize_csv_value(u["name"]), _sanitize_csv_value(u["email"]), u["scan_count"], u["risks_found"], u["last_scan"] or "Never"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=contrared_analytics_{days}d.csv"},
    )
