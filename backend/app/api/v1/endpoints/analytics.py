"""
Analytics endpoints — Firm-wide dashboard stats.

Admin-only endpoints providing aggregated usage and risk data.
"""

import csv
import io
import logging
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.api.dependencies import require_permission
from app.services import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _sanitize_csv_value(value) -> str:
    """Prevent CSV injection by escaping formula-triggering characters."""
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


@router.get("/overview")
async def analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Org-level summary stats: scans, risks, active users."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_org_overview(db, current_user.organization_id, days=days)


@router.get("/risks")
async def analytics_risks(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Risk breakdown by clause type and level."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_risk_breakdown(db, current_user.organization_id, days=days)


@router.get("/users")
async def analytics_users(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Per-user activity stats."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_user_activity(db, current_user.organization_id, days=days)


@router.get("/trends")
async def analytics_trends(
    period: Literal["weekly", "daily"] = "weekly",
    weeks: int = Query(default=12, ge=1, le=52),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Time-series usage data (weekly or daily)."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_trend_data(db, current_user.organization_id, period=period, weeks=weeks)


@router.get("/export")
async def analytics_export(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.export")),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics as CSV."""
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


# ============================================================================
# Phase 9: Advanced Analytics Endpoints
# ============================================================================


@router.get("/executive")
async def analytics_executive(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Board-ready executive dashboard: 6 key metrics + ROI + trends."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_executive_dashboard(db, current_user.organization_id, days=days)


@router.get("/roi")
async def analytics_roi(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Comprehensive ROI calculation with methodology."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from app.services.roi_service import calculate_roi
    return await calculate_roi(db, current_user.organization_id, days=days)


@router.put("/roi/benchmarks")
async def update_benchmarks(
    pages_per_hour: float = Query(default=None, ge=0.1, le=100),
    minutes_per_risk: float = Query(default=None, ge=0.1, le=120),
    hourly_rate: float = Query(default=None, ge=0),
    currency: str = Query(default=None, max_length=3),
    current_user: User = Depends(require_permission("analytics.export")),
    db: AsyncSession = Depends(get_db),
):
    """Update org-specific time benchmarks for ROI calculation."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from decimal import Decimal
    from app.services.roi_service import update_org_benchmarks
    result = await update_org_benchmarks(
        db, current_user.organization_id,
        pages_per_hour=Decimal(str(pages_per_hour)) if pages_per_hour is not None else None,
        minutes_per_risk=Decimal(str(minutes_per_risk)) if minutes_per_risk is not None else None,
        hourly_rate=Decimal(str(hourly_rate)) if hourly_rate is not None else None,
        currency=currency,
    )
    await db.commit()
    return result


@router.put("/roi/config")
async def update_roi_config(
    risk_value_per_red: float = Query(default=None, ge=0),
    risk_value_per_yellow: float = Query(default=None, ge=0),
    include_risk_value: bool = Query(default=None),
    include_time_savings: bool = Query(default=None),
    custom_note: str = Query(default=None, max_length=500),
    current_user: User = Depends(require_permission("analytics.export")),
    db: AsyncSession = Depends(get_db),
):
    """Update org-specific ROI configuration."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from decimal import Decimal
    from app.services.roi_service import update_roi_config as _update_roi_config
    result = await _update_roi_config(
        db, current_user.organization_id,
        risk_value_per_red=Decimal(str(risk_value_per_red)) if risk_value_per_red is not None else None,
        risk_value_per_yellow=Decimal(str(risk_value_per_yellow)) if risk_value_per_yellow is not None else None,
        include_risk_value=include_risk_value,
        include_time_savings=include_time_savings,
        custom_note=custom_note,
    )
    await db.commit()
    return result


@router.get("/portfolio")
async def analytics_portfolio(
    days: int = Query(default=90, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-level risk aggregation across all contracts."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from app.services.benchmark_service import get_portfolio_risk
    return await get_portfolio_risk(db, current_user.organization_id, days=days)


@router.get("/clauses")
async def analytics_clauses(
    days: int = Query(default=90, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Clause-level analytics: which clause types cause the most risk?"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from app.services.benchmark_service import get_clause_analytics
    return await get_clause_analytics(db, current_user.organization_id, days=days)


@router.get("/team-performance")
async def analytics_team_performance(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Team performance metrics: reviews, risks found, processing speed."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from app.services.benchmark_service import get_team_performance
    return await get_team_performance(db, current_user.organization_id, days=days)


@router.get("/benchmark/{document_id}")
async def analytics_benchmark(
    document_id: str,
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Compare a document's risk against org historical data."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from uuid import UUID as _UUID
    from app.services.benchmark_service import get_document_percentile
    return await get_document_percentile(db, current_user.organization_id, _UUID(document_id))


@router.post("/benchmarks/refresh")
async def refresh_benchmarks(
    current_user: User = Depends(require_permission("analytics.export")),
    db: AsyncSession = Depends(get_db),
):
    """Refresh cached benchmark profiles for the organization."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from app.services.benchmark_service import refresh_benchmark_profiles
    count = await refresh_benchmark_profiles(db, current_user.organization_id)
    await db.commit()
    return {"profiles_updated": count}


@router.get("/bi-export/{dataset}")
async def analytics_bi_export(
    dataset: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.export")),
    db: AsyncSession = Depends(get_db),
):
    """Structured JSON export for BI tools (Power BI, Tableau)."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    return await analytics_service.get_bi_export_data(
        db, current_user.organization_id, dataset=dataset, days=days
    )


@router.post("/reports/generate")
async def generate_report(
    report_type: str = Query(..., description="One of: executive_summary, gc_operations, team_review, risk_audit"),
    title: str = Query(default=None, max_length=255),
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_permission("analytics.export")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured report and save it."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from app.services.report_service import generate_report as _generate_report, REPORT_TYPES
    if report_type not in REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid report_type. Must be one of: {REPORT_TYPES}")

    result = await _generate_report(
        db, current_user.organization_id, current_user.id,
        report_type=report_type, title=title, days=days,
    )
    await db.commit()
    return result


@router.get("/reports")
async def list_reports(
    report_type: str = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """List previously generated reports."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from app.services.report_service import list_reports as _list_reports
    return await _list_reports(db, current_user.organization_id, report_type=report_type, limit=limit)


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(require_permission("analytics.read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report by ID."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    from uuid import UUID as _UUID
    from app.services.report_service import get_report as _get_report
    result = await _get_report(db, _UUID(report_id), current_user.organization_id)
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    return result
