"""
Analytics Service — Aggregation queries for firm-wide dashboard.

Provides org-level and user-level stats from documents, document_risks,
and audit_logs tables.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select, func, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRisk, DocumentStatus
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_org_overview(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> Dict[str, Any]:
    """Get org-level overview stats for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Subquery for user IDs in this org
    user_ids_subq = select(User.id).where(User.organization_id == org_id).scalar_subquery()

    # Documents analyzed
    doc_result = await db.execute(
        select(func.count(Document.id))
        .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    documents_analyzed = doc_result.scalar() or 0

    if documents_analyzed == 0:
        return {
            "documents_analyzed": 0,
            "total_risks": 0,
            "red_risks": 0,
            "yellow_risks": 0,
            "active_users": 0,
            "period_days": days,
        }

    # Total risks
    total_result = await db.execute(
        select(func.sum(func.coalesce(Document.total_risks, 0)))
        .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    total_risks = total_result.scalar() or 0

    # Calculate red/yellow from risk_summary JSONB via SQL aggregation
    from sqlalchemy import cast, Integer, text as sa_text
    risk_agg = await db.execute(
        select(
            func.sum(cast(Document.risk_summary["red"].as_string(), Integer)).label("red_total"),
            func.sum(cast(Document.risk_summary["yellow"].as_string(), Integer)).label("yellow_total"),
        )
        .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
        .where(Document.risk_summary.isnot(None))
    )
    agg_row = risk_agg.one()
    red_total = agg_row.red_total or 0
    yellow_total = agg_row.yellow_total or 0

    # Active users (users who scanned at least one doc)
    active_result = await db.execute(
        select(func.count(func.distinct(Document.user_id)))
        .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
        .where(Document.created_at >= since)
    )
    active_users = active_result.scalar() or 0

    return {
        "documents_analyzed": documents_analyzed,
        "total_risks": total_risks,
        "red_risks": red_total,
        "yellow_risks": yellow_total,
        "active_users": active_users,
        "period_days": days,
    }


async def get_risk_breakdown(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Get risk counts by risk level from document_risks table."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Subquery: document IDs belonging to org users within time range
    doc_ids_subq = (
        select(Document.id)
        .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
        .where(Document.created_at >= since)
        .scalar_subquery()
    )

    # Get risk breakdown by risk_level
    breakdown_result = await db.execute(
        select(
            DocumentRisk.risk_level,
            func.count(DocumentRisk.id),
        )
        .where(DocumentRisk.document_id.in_(
            select(Document.id)
            .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
            .where(Document.created_at >= since)
        ))
        .group_by(DocumentRisk.risk_level)
    )

    results = []
    for risk_level, count in breakdown_result.all():
        level = risk_level.value if hasattr(risk_level, 'value') else str(risk_level).lower()
        results.append({
            "risk_level": level.upper(),
            "red": count if level == "red" else 0,
            "yellow": count if level == "yellow" else 0,
            "green": count if level == "green" else 0,
            "total": count,
        })

    return sorted(results, key=lambda x: -x["total"])


async def get_user_activity(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Get per-user activity stats."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            User.id,
            User.email,
            User.name,
            func.count(Document.id).label("scan_count"),
            func.sum(func.coalesce(Document.total_risks, 0)).label("risks_found"),
            func.max(Document.created_at).label("last_scan"),
        )
        .join(Document, Document.user_id == User.id, isouter=True)
        .where(User.organization_id == org_id)
        .where((Document.created_at >= since) | (Document.created_at.is_(None)))
        .group_by(User.id, User.email, User.name)
        .order_by(func.count(Document.id).desc())
    )

    return [
        {
            "user_id": str(row.id),
            "email": row.email,
            "name": row.name,
            "scan_count": row.scan_count or 0,
            "risks_found": row.risks_found or 0,
            "last_scan": row.last_scan.isoformat() if row.last_scan else None,
        }
        for row in result.all()
    ]


async def get_trend_data(
    db: AsyncSession,
    org_id: UUID,
    period: str = "weekly",
    weeks: int = 12,
) -> List[Dict[str, Any]]:
    """Get time-series usage data (weekly or daily)."""
    user_ids_subq = select(User.id).where(User.organization_id == org_id).scalar_subquery()

    trunc_unit = 'day' if period == "daily" else 'week'
    if period == "daily":
        days_back = min(weeks * 7, 90)
        since = datetime.now(timezone.utc) - timedelta(days=days_back)
    else:
        since = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    period_col = func.date_trunc(trunc_unit, Document.created_at).label("period")
    result = await db.execute(
        select(
            period_col,
            func.count(Document.id).label("scans"),
            func.sum(func.coalesce(Document.total_risks, 0)).label("risks"),
        )
        .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
        .where(Document.created_at >= since)
        .group_by(literal_column("1"))
        .order_by(literal_column("1"))
    )

    return [
        {
            "period": row.period.isoformat() if row.period else "",
            "scans": row.scans or 0,
            "risks": row.risks or 0,
        }
        for row in result.all()
    ]


async def get_executive_dashboard(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Board-ready executive dashboard: 6 key metrics on one screen.
    Combines overview + ROI + trends into a single response.
    """
    overview = await get_org_overview(db, org_id, days=days)

    # Import here to avoid circular
    from app.services.roi_service import calculate_roi
    roi = await calculate_roi(db, org_id, days=days)

    trends = await get_trend_data(db, org_id, period="weekly", weeks=max(days // 7, 4))

    return {
        **overview,
        "roi": roi,
        "trends": trends,
    }


async def get_bi_export_data(
    db: AsyncSession,
    org_id: UUID,
    dataset: str = "overview",
    days: int = 30,
) -> Dict[str, Any]:
    """
    Structured data export for BI tools (Power BI, Tableau, etc.).

    Datasets: overview, risks, users, trends, portfolio, team
    """
    from app.services.benchmark_service import (
        get_portfolio_risk,
        get_team_performance,
    )

    exporters = {
        "overview": lambda: get_org_overview(db, org_id, days),
        "risks": lambda: get_risk_breakdown(db, org_id, days),
        "users": lambda: get_user_activity(db, org_id, days),
        "trends": lambda: get_trend_data(db, org_id, period="weekly", weeks=max(days // 7, 4)),
        "portfolio": lambda: get_portfolio_risk(db, org_id, days),
        "team": lambda: get_team_performance(db, org_id, days),
    }

    if dataset not in exporters:
        return {"error": f"Unknown dataset. Available: {list(exporters.keys())}"}

    data = await exporters[dataset]()

    return {
        "dataset": dataset,
        "period_days": days,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
