"""
Report Generation Service — Phase 9.

Generates structured reports from analytics data:
  - Executive Summary: Board-ready 6 key metrics
  - GC Operations: General Counsel operational overview
  - Team Review: Per-reviewer performance breakdown
  - Risk Audit: Detailed risk analysis across portfolio
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import analytics_service
from app.services.roi_service import calculate_roi
from app.services.benchmark_service import (
    get_portfolio_risk,
    get_clause_analytics,
    get_team_performance,
)

logger = logging.getLogger(__name__)

REPORT_TYPES = ["executive_summary", "gc_operations", "team_review", "risk_audit"]


async def generate_report(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    report_type: str,
    title: Optional[str] = None,
    days: int = 30,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a report and store it in the database.

    Returns the generated report data.
    """
    if report_type not in REPORT_TYPES:
        raise ValueError(f"Invalid report type. Must be one of: {REPORT_TYPES}")

    # Generate report data based on type
    generators = {
        "executive_summary": _generate_executive_summary,
        "gc_operations": _generate_gc_operations,
        "team_review": _generate_team_review,
        "risk_audit": _generate_risk_audit,
    }

    report_data = await generators[report_type](db, org_id, days, filters)

    # Store in database
    from app.models.analytics import GeneratedReport

    report = GeneratedReport(
        organization_id=org_id,
        created_by=user_id,
        report_type=report_type,
        title=title or _default_title(report_type, days),
        parameters={"days": days, "filters": filters},
        report_data=report_data,
        format="json",
    )
    db.add(report)
    await db.flush()

    return {
        "id": str(report.id),
        "report_type": report_type,
        "title": report.title,
        "created_at": report.created_at.isoformat(),
        "data": report_data,
    }


def _default_title(report_type: str, days: int) -> str:
    """Generate a default title for a report."""
    type_names = {
        "executive_summary": "Executive Summary",
        "gc_operations": "GC Operations Report",
        "team_review": "Team Performance Review",
        "risk_audit": "Risk Audit Report",
    }
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{type_names.get(report_type, 'Report')} — {days}d ending {now}"


async def _generate_executive_summary(
    db: AsyncSession,
    org_id: UUID,
    days: int,
    filters: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Board-ready executive summary with 6 key metrics.
    Large-font, no clutter.
    """
    overview = await analytics_service.get_org_overview(db, org_id, days=days)
    roi = await calculate_roi(db, org_id, days=days)
    trends = await analytics_service.get_trend_data(db, org_id, period="weekly", weeks=max(days // 7, 4))

    # Calculate week-over-week change
    recent_scans = sum(t["scans"] for t in trends[-2:]) if len(trends) >= 2 else 0
    prior_scans = sum(t["scans"] for t in trends[-4:-2]) if len(trends) >= 4 else 0
    wow_change = ((recent_scans - prior_scans) / max(prior_scans, 1)) * 100

    return {
        "report_type": "executive_summary",
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "key_metrics": {
            "contracts_reviewed": overview["documents_analyzed"],
            "total_risks_identified": overview["total_risks"],
            "critical_risks": overview["red_risks"],
            "hours_saved": roi["time_savings"]["hours_saved"],
            "roi_value": roi["total_roi_value"],
            "roi_multiplier": roi["roi_multiplier"],
        },
        "trends": {
            "week_over_week_change_pct": round(wow_change, 1),
            "direction": "up" if wow_change > 0 else "down" if wow_change < 0 else "flat",
        },
        "highlights": [
            f"{overview['documents_analyzed']} contracts reviewed in {days} days",
            f"{overview['red_risks']} critical risks identified and flagged",
            f"{roi['time_savings']['hours_saved']} hours of manual review time saved",
            f"{roi['roi_multiplier']} return on investment",
        ],
    }


async def _generate_gc_operations(
    db: AsyncSession,
    org_id: UUID,
    days: int,
    filters: Optional[Dict] = None,
) -> Dict[str, Any]:
    """General Counsel operations overview."""
    overview = await analytics_service.get_org_overview(db, org_id, days=days)
    portfolio = await get_portfolio_risk(db, org_id, days=days)
    clause_data = await get_clause_analytics(db, org_id, days=days)
    roi = await calculate_roi(db, org_id, days=days)

    return {
        "report_type": "gc_operations",
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": overview,
        "portfolio_risk": portfolio["summary"],
        "risk_distribution": portfolio["risk_distribution"],
        "top_risk_areas": clause_data[:5],
        "high_risk_contracts": portfolio["high_risk_documents"][:5],
        "roi_summary": {
            "hours_saved": roi["time_savings"]["hours_saved"],
            "monetary_value": roi["time_savings"]["monetary_value"],
            "risk_value_protected": roi["risk_value"]["total_risk_value_protected"],
        },
    }


async def _generate_team_review(
    db: AsyncSession,
    org_id: UUID,
    days: int,
    filters: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Team performance review."""
    team = await get_team_performance(db, org_id, days=days)
    overview = await analytics_service.get_org_overview(db, org_id, days=days)

    # Calculate team-level stats
    active_reviewers = [m for m in team if m["documents_reviewed"] > 0]

    return {
        "report_type": "team_review",
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "team_summary": {
            "total_members": len(team),
            "active_reviewers": len(active_reviewers),
            "total_documents_reviewed": overview["documents_analyzed"],
            "total_risks_found": overview["total_risks"],
        },
        "members": team,
        "top_reviewer": active_reviewers[0] if active_reviewers else None,
    }


async def _generate_risk_audit(
    db: AsyncSession,
    org_id: UUID,
    days: int,
    filters: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Comprehensive risk audit across the portfolio."""
    portfolio = await get_portfolio_risk(db, org_id, days=days)
    clause_data = await get_clause_analytics(db, org_id, days=days)
    trends = await analytics_service.get_trend_data(db, org_id, period="weekly", weeks=max(days // 7, 4))

    return {
        "report_type": "risk_audit",
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_summary": portfolio["summary"],
        "risk_distribution": portfolio["risk_distribution"],
        "by_contract_type": portfolio["by_contract_type"],
        "clause_analysis": clause_data,
        "high_risk_documents": portfolio["high_risk_documents"],
        "risk_trends": trends,
    }


async def list_reports(
    db: AsyncSession,
    org_id: UUID,
    report_type: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """List previously generated reports."""
    from sqlalchemy import select
    from app.models.analytics import GeneratedReport

    query = (
        select(GeneratedReport)
        .where(GeneratedReport.organization_id == org_id)
        .order_by(GeneratedReport.created_at.desc())
        .limit(limit)
    )
    if report_type:
        query = query.where(GeneratedReport.report_type == report_type)

    result = await db.execute(query)
    reports = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "report_type": r.report_type,
            "title": r.title,
            "format": r.format,
            "created_at": r.created_at.isoformat(),
            "parameters": r.parameters,
        }
        for r in reports
    ]


async def get_report(
    db: AsyncSession,
    report_id: UUID,
    org_id: UUID,
) -> Optional[Dict[str, Any]]:
    """Get a specific report by ID."""
    from sqlalchemy import select
    from app.models.analytics import GeneratedReport

    result = await db.execute(
        select(GeneratedReport)
        .where(GeneratedReport.id == report_id)
        .where(GeneratedReport.organization_id == org_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        return None

    return {
        "id": str(r.id),
        "report_type": r.report_type,
        "title": r.title,
        "format": r.format,
        "parameters": r.parameters,
        "data": r.report_data,
        "created_at": r.created_at.isoformat(),
    }
