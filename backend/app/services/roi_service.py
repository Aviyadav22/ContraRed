"""
ROI (Return on Investment) Calculation Service — Phase 9.

Replaces the hardcoded "2 hours saved per scan" with real, defensible metrics:
  - Actual processing_duration_ms (measured)
  - Estimated manual review time: (word_count / 250) * (60 / pages_per_hour) + (risk_count * minutes_per_risk)
  - Configurable benchmarks per org (default: 5 pages/hour, 15 min/risk)
  - Risk value protected: red_risks * risk_value_per_red + yellow_risks * risk_value_per_yellow
  - Methodology always shown so numbers are defensible
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.user import User

logger = logging.getLogger(__name__)

# Default benchmarks (used when org has no custom config)
DEFAULT_PAGES_PER_HOUR = Decimal("5.0")
DEFAULT_MINUTES_PER_RISK = Decimal("15.0")
DEFAULT_HOURLY_RATE = Decimal("5000.00")  # INR
DEFAULT_RISK_VALUE_RED = Decimal("500000.00")  # ₹5L
DEFAULT_RISK_VALUE_YELLOW = Decimal("100000.00")  # ₹1L
WORDS_PER_PAGE = 250


async def get_org_benchmarks(db: AsyncSession, org_id: UUID) -> Dict[str, Any]:
    """Load org-specific benchmarks or return defaults."""
    from app.models.analytics import TimeBenchmark, ROIConfig

    # Time benchmarks
    tb_result = await db.execute(
        select(TimeBenchmark).where(TimeBenchmark.organization_id == org_id)
    )
    tb = tb_result.scalar_one_or_none()

    # ROI config
    roi_result = await db.execute(
        select(ROIConfig).where(ROIConfig.organization_id == org_id)
    )
    roi = roi_result.scalar_one_or_none()

    return {
        "pages_per_hour": tb.pages_per_hour if tb else DEFAULT_PAGES_PER_HOUR,
        "minutes_per_risk": tb.minutes_per_risk if tb else DEFAULT_MINUTES_PER_RISK,
        "hourly_rate": tb.hourly_rate if tb else DEFAULT_HOURLY_RATE,
        "currency": tb.currency if tb else "INR",
        "risk_value_per_red": roi.risk_value_per_red if roi else DEFAULT_RISK_VALUE_RED,
        "risk_value_per_yellow": roi.risk_value_per_yellow if roi else DEFAULT_RISK_VALUE_YELLOW,
        "include_risk_value": roi.include_risk_value if roi else True,
        "include_time_savings": roi.include_time_savings if roi else True,
        "custom_note": roi.custom_methodology_note if roi else None,
    }


def estimate_manual_review_minutes(
    word_count: Optional[int],
    risk_count: int,
    pages_per_hour: Decimal,
    minutes_per_risk: Decimal,
) -> Decimal:
    """
    Estimate how long a manual review would take (in minutes).

    Formula: (pages * 60 / pages_per_hour) + (risks * minutes_per_risk)
    """
    pages = Decimal(word_count or 0) / Decimal(WORDS_PER_PAGE)
    reading_minutes = pages * Decimal("60") / pages_per_hour if pages_per_hour > 0 else Decimal("0")
    risk_minutes = Decimal(risk_count) * minutes_per_risk
    return reading_minutes + risk_minutes


async def calculate_roi(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Calculate comprehensive ROI for an organization.

    Returns:
        {
            "period_days": 30,
            "documents_analyzed": 42,
            "total_risks_found": 156,
            "red_risks": 23,
            "yellow_risks": 89,
            "time_savings": {
                "estimated_manual_hours": 84.5,
                "actual_ai_hours": 0.35,
                "hours_saved": 84.15,
                "monetary_value": 420750.00,
                "currency": "INR",
            },
            "risk_value": {
                "red_risk_value": 11500000.00,
                "yellow_risk_value": 8900000.00,
                "total_risk_value_protected": 20400000.00,
                "currency": "INR",
            },
            "total_roi_value": 20820750.00,
            "roi_multiplier": "12.4x",
            "subscription_cost": null,  # filled if billing data available
            "methodology": {
                "pages_per_hour": 5.0,
                "minutes_per_risk": 15.0,
                "hourly_rate": 5000.00,
                "risk_value_per_red": 500000.00,
                "risk_value_per_yellow": 100000.00,
                "note": "Based on industry benchmarks..."
            }
        }
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    benchmarks = await get_org_benchmarks(db, org_id)

    # Get document stats for the period
    docs_result = await db.execute(
        select(
            func.count(Document.id).label("doc_count"),
            func.sum(func.coalesce(Document.word_count, 0)).label("total_words"),
            func.sum(func.coalesce(Document.total_risks, 0)).label("total_risks"),
            func.sum(func.coalesce(Document.processing_duration_ms, 0)).label("total_processing_ms"),
        )
        .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    row = docs_result.one()
    doc_count = row.doc_count or 0
    total_words = row.total_words or 0
    total_risks = row.total_risks or 0
    total_processing_ms = row.total_processing_ms or 0

    # Get red/yellow risk counts from risk_summary JSONB
    summary_result = await db.execute(
        select(Document.risk_summary)
        .where(Document.user_id.in_(select(User.id).where(User.organization_id == org_id)))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
        .where(Document.risk_summary.isnot(None))
    )
    red_risks = 0
    yellow_risks = 0
    total_manual_minutes = Decimal("0")

    for (summary,) in summary_result.all():
        if isinstance(summary, dict):
            red_risks += summary.get("red", 0)
            yellow_risks += summary.get("yellow", 0)

    # Calculate estimated manual time per document
    # Use average word count if individual docs don't have it
    avg_words = total_words // doc_count if doc_count > 0 else 2500  # ~10 pages default
    avg_risks = total_risks // doc_count if doc_count > 0 else 0
    single_doc_manual = estimate_manual_review_minutes(
        avg_words,
        avg_risks,
        benchmarks["pages_per_hour"],
        benchmarks["minutes_per_risk"],
    )
    total_manual_minutes = Decimal(doc_count) * single_doc_manual

    # Time savings
    estimated_manual_hours = float(total_manual_minutes / Decimal("60"))
    actual_ai_hours = total_processing_ms / 3_600_000  # ms to hours
    hours_saved = max(estimated_manual_hours - actual_ai_hours, 0)
    time_monetary = float(Decimal(str(hours_saved)) * benchmarks["hourly_rate"])

    # Risk value protected
    red_value = float(Decimal(red_risks) * benchmarks["risk_value_per_red"])
    yellow_value = float(Decimal(yellow_risks) * benchmarks["risk_value_per_yellow"])
    total_risk_value = red_value + yellow_value

    # Total ROI
    total_roi = 0.0
    if benchmarks["include_time_savings"]:
        total_roi += time_monetary
    if benchmarks["include_risk_value"]:
        total_roi += total_risk_value

    # ROI multiplier (vs actual subscription cost from billing)
    try:
        from app.models.organization import Subscription, PlanType
        sub_result = await db.execute(
            select(Subscription).where(Subscription.organization_id == org_id).limit(1)
        )
        sub = sub_result.scalar_one_or_none()
        plan_costs = {
            PlanType.FREE: 0, PlanType.STARTER: 999,
            PlanType.PRO: 2999, PlanType.BUSINESS: 6999,
            PlanType.ENTERPRISE: 14999,
        }
        estimated_monthly_cost = float(plan_costs.get(sub.plan, 2999)) if sub else 2999.0
    except Exception:
        estimated_monthly_cost = 2999.0
    period_cost = estimated_monthly_cost * (days / 30)
    roi_multiplier = round(total_roi / period_cost, 1) if period_cost > 0 else 0

    return {
        "period_days": days,
        "documents_analyzed": doc_count,
        "total_risks_found": total_risks,
        "red_risks": red_risks,
        "yellow_risks": yellow_risks,
        "time_savings": {
            "estimated_manual_hours": round(estimated_manual_hours, 1),
            "actual_ai_hours": round(actual_ai_hours, 2),
            "hours_saved": round(hours_saved, 1),
            "monetary_value": round(time_monetary, 2),
            "currency": benchmarks["currency"],
        },
        "risk_value": {
            "red_risk_value": round(red_value, 2),
            "yellow_risk_value": round(yellow_value, 2),
            "total_risk_value_protected": round(total_risk_value, 2),
            "currency": benchmarks["currency"],
        },
        "total_roi_value": round(total_roi, 2),
        "roi_multiplier": f"{roi_multiplier}x",
        "methodology": {
            "pages_per_hour": float(benchmarks["pages_per_hour"]),
            "minutes_per_risk": float(benchmarks["minutes_per_risk"]),
            "hourly_rate": float(benchmarks["hourly_rate"]),
            "risk_value_per_red": float(benchmarks["risk_value_per_red"]),
            "risk_value_per_yellow": float(benchmarks["risk_value_per_yellow"]),
            "words_per_page": WORDS_PER_PAGE,
            "note": benchmarks["custom_note"] or "Based on industry benchmarks for legal contract review. Configure under Settings > Analytics.",
        },
    }


async def update_org_benchmarks(
    db: AsyncSession,
    org_id: UUID,
    pages_per_hour: Optional[Decimal] = None,
    minutes_per_risk: Optional[Decimal] = None,
    hourly_rate: Optional[Decimal] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """Update org-specific time benchmarks."""
    from app.models.analytics import TimeBenchmark

    result = await db.execute(
        select(TimeBenchmark).where(TimeBenchmark.organization_id == org_id)
    )
    tb = result.scalar_one_or_none()

    if not tb:
        tb = TimeBenchmark(organization_id=org_id)
        db.add(tb)

    if pages_per_hour is not None:
        tb.pages_per_hour = pages_per_hour
    if minutes_per_risk is not None:
        tb.minutes_per_risk = minutes_per_risk
    if hourly_rate is not None:
        tb.hourly_rate = hourly_rate
    if currency is not None:
        tb.currency = currency

    tb.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "pages_per_hour": float(tb.pages_per_hour),
        "minutes_per_risk": float(tb.minutes_per_risk),
        "hourly_rate": float(tb.hourly_rate),
        "currency": tb.currency,
    }


async def update_roi_config(
    db: AsyncSession,
    org_id: UUID,
    risk_value_per_red: Optional[Decimal] = None,
    risk_value_per_yellow: Optional[Decimal] = None,
    include_risk_value: Optional[bool] = None,
    include_time_savings: Optional[bool] = None,
    custom_note: Optional[str] = None,
) -> Dict[str, Any]:
    """Update org-specific ROI configuration."""
    from app.models.analytics import ROIConfig

    result = await db.execute(
        select(ROIConfig).where(ROIConfig.organization_id == org_id)
    )
    roi = result.scalar_one_or_none()

    if not roi:
        roi = ROIConfig(organization_id=org_id)
        db.add(roi)

    if risk_value_per_red is not None:
        roi.risk_value_per_red = risk_value_per_red
    if risk_value_per_yellow is not None:
        roi.risk_value_per_yellow = risk_value_per_yellow
    if include_risk_value is not None:
        roi.include_risk_value = include_risk_value
    if include_time_savings is not None:
        roi.include_time_savings = include_time_savings
    if custom_note is not None:
        roi.custom_methodology_note = custom_note

    roi.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "risk_value_per_red": float(roi.risk_value_per_red),
        "risk_value_per_yellow": float(roi.risk_value_per_yellow),
        "include_risk_value": roi.include_risk_value,
        "include_time_savings": roi.include_time_savings,
        "custom_note": roi.custom_methodology_note,
    }
