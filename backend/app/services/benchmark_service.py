"""
Benchmark Service — Phase 9.

Internal benchmarking for contract analysis:
  - Compare a document's risk against historical org data
  - Generate and cache benchmark profiles per contract type
  - Portfolio-level risk aggregation
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentRisk, DocumentStatus
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_document_percentile(
    db: AsyncSession,
    org_id: UUID,
    document_id: UUID,
) -> Dict[str, Any]:
    """
    Compare a document's risk score against org historical data.

    Returns percentile ranking and comparison stats.
    """
    # Get the target document
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        return {"error": "Document not found"}

    contract_type = doc.contract_type or "unknown"
    doc_risk_score = float(doc.risk_score) if doc.risk_score else 0.0
    doc_total_risks = doc.total_risks or 0

    # Get all completed docs of same type in org
    user_ids_subq = select(User.id).where(User.organization_id == org_id)

    scores_result = await db.execute(
        select(
            Document.risk_score,
            Document.total_risks,
        )
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.status == DocumentStatus.COMPLETED)
        .where(Document.risk_score.isnot(None))
    )
    all_scores = [(float(r.risk_score), r.total_risks or 0) for r in scores_result.all()]

    if not all_scores:
        return {
            "document_id": str(document_id),
            "contract_type": contract_type,
            "risk_score": doc_risk_score,
            "percentile": None,
            "comparison": "Insufficient data for benchmarking",
            "sample_size": 0,
        }

    # Calculate percentile (% of docs with LOWER risk)
    lower_count = sum(1 for s, _ in all_scores if s < doc_risk_score)
    percentile = round((lower_count / len(all_scores)) * 100, 1)

    avg_score = sum(s for s, _ in all_scores) / len(all_scores)
    avg_risks = sum(r for _, r in all_scores) / len(all_scores)

    if percentile >= 75:
        comparison = f"Riskier than {percentile}% of historical {contract_type} contracts"
    elif percentile >= 50:
        comparison = f"Above average risk (percentile: {percentile}%)"
    elif percentile >= 25:
        comparison = f"Below average risk (percentile: {percentile}%)"
    else:
        comparison = f"Lower risk than {100 - percentile}% of historical {contract_type} contracts"

    return {
        "document_id": str(document_id),
        "contract_type": contract_type,
        "risk_score": doc_risk_score,
        "total_risks": doc_total_risks,
        "percentile": percentile,
        "comparison": comparison,
        "org_averages": {
            "avg_risk_score": round(avg_score, 2),
            "avg_risks_per_doc": round(avg_risks, 1),
        },
        "sample_size": len(all_scores),
    }


async def get_portfolio_risk(
    db: AsyncSession,
    org_id: UUID,
    days: int = 90,
) -> Dict[str, Any]:
    """
    Portfolio-level risk aggregation across all contracts.

    Answers: "Across all contracts, where is our aggregate exposure?"
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    user_ids_subq = select(User.id).where(User.organization_id == org_id)

    # Overall stats
    overall = await db.execute(
        select(
            func.count(Document.id).label("total_docs"),
            func.avg(Document.risk_score).label("avg_risk_score"),
            func.sum(Document.total_risks).label("total_risks"),
            func.avg(Document.total_risks).label("avg_risks_per_doc"),
        )
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    stats = overall.one()

    # Breakdown by contract type
    by_type = await db.execute(
        select(
            func.coalesce(Document.contract_type, "unclassified").label("contract_type"),
            func.count(Document.id).label("count"),
            func.avg(Document.risk_score).label("avg_risk"),
            func.sum(Document.total_risks).label("total_risks"),
        )
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
        .group_by(func.coalesce(Document.contract_type, "unclassified"))
        .order_by(func.sum(Document.total_risks).desc())
    )

    type_breakdown = [
        {
            "contract_type": row.contract_type,
            "document_count": row.count,
            "avg_risk_score": round(float(row.avg_risk or 0), 2),
            "total_risks": row.total_risks or 0,
        }
        for row in by_type.all()
    ]

    # Risk level distribution from risk_summary JSONB
    summaries = await db.execute(
        select(Document.risk_summary)
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
        .where(Document.risk_summary.isnot(None))
    )
    total_red = 0
    total_yellow = 0
    total_green = 0
    for (summary,) in summaries.all():
        if isinstance(summary, dict):
            total_red += summary.get("red", 0)
            total_yellow += summary.get("yellow", 0)
            total_green += summary.get("green", 0)

    # High-risk documents (risk_score >= 7)
    high_risk = await db.execute(
        select(
            Document.id, Document.filename, Document.risk_score,
            Document.total_risks, Document.contract_type, Document.counterparty,
        )
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
        .where(Document.risk_score >= 7)
        .order_by(Document.risk_score.desc())
        .limit(10)
    )

    high_risk_docs = [
        {
            "document_id": str(r.id),
            "filename": r.filename,
            "risk_score": float(r.risk_score) if r.risk_score else None,
            "total_risks": r.total_risks,
            "contract_type": r.contract_type,
            "counterparty": r.counterparty,
        }
        for r in high_risk.all()
    ]

    return {
        "period_days": days,
        "summary": {
            "total_documents": stats.total_docs or 0,
            "avg_risk_score": round(float(stats.avg_risk_score or 0), 2),
            "total_risks": stats.total_risks or 0,
            "avg_risks_per_document": round(float(stats.avg_risks_per_doc or 0), 1),
        },
        "risk_distribution": {
            "red": total_red,
            "yellow": total_yellow,
            "green": total_green,
        },
        "by_contract_type": type_breakdown,
        "high_risk_documents": high_risk_docs,
    }


async def get_clause_analytics(
    db: AsyncSession,
    org_id: UUID,
    days: int = 90,
) -> List[Dict[str, Any]]:
    """
    Clause-level analytics: which clause types cause the most risk?

    Groups risks by clause_type (from DocumentRisk extra info or rule category).
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    user_ids_subq = select(User.id).where(User.organization_id == org_id)
    doc_ids_subq = (
        select(Document.id)
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.created_at >= since)
    )

    # Group risks by category (clause type), not just risk_level
    result = await db.execute(
        select(
            func.coalesce(DocumentRisk.category, "uncategorized").label("category"),
            DocumentRisk.risk_level,
            func.count(DocumentRisk.id).label("count"),
            func.count(case((DocumentRisk.is_resolved.is_(True), 1))).label("resolved_count"),
        )
        .where(DocumentRisk.document_id.in_(doc_ids_subq))
        .group_by(func.coalesce(DocumentRisk.category, "uncategorized"), DocumentRisk.risk_level)
        .order_by(func.count(DocumentRisk.id).desc())
    )

    return [
        {
            "category": row.category,
            "risk_level": row.risk_level.value if hasattr(row.risk_level, "value") else str(row.risk_level),
            "count": row.count,
            "resolved_count": row.resolved_count,
            "resolution_rate": round((row.resolved_count / row.count * 100), 1) if row.count > 0 else 0,
        }
        for row in result.all()
    ]


async def get_team_performance(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Team performance metrics: who reviews fastest? Who finds the most risks?
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            User.id,
            User.email,
            User.name,
            func.count(Document.id).label("documents_reviewed"),
            func.sum(func.coalesce(Document.total_risks, 0)).label("total_risks_found"),
            func.avg(func.coalesce(Document.processing_duration_ms, 0)).label("avg_processing_ms"),
            func.sum(func.coalesce(Document.word_count, 0)).label("total_words_reviewed"),
        )
        .join(Document, Document.user_id == User.id, isouter=True)
        .where(User.organization_id == org_id)
        .where((Document.created_at >= since) | (Document.created_at.is_(None)))
        .where((Document.status == DocumentStatus.COMPLETED) | (Document.status.is_(None)))
        .group_by(User.id, User.email, User.name)
        .order_by(func.count(Document.id).desc())
    )

    return [
        {
            "user_id": str(row.id),
            "email": row.email,
            "name": row.name,
            "documents_reviewed": row.documents_reviewed or 0,
            "total_risks_found": row.total_risks_found or 0,
            "avg_processing_ms": int(row.avg_processing_ms or 0),
            "total_words_reviewed": row.total_words_reviewed or 0,
            "avg_risks_per_doc": round(
                (row.total_risks_found or 0) / max(row.documents_reviewed or 1, 1), 1
            ),
        }
        for row in result.all()
    ]


async def refresh_benchmark_profiles(
    db: AsyncSession,
    org_id: UUID,
) -> int:
    """
    Refresh cached benchmark profiles for the org.

    Calculates averages per contract type for the last 90 days.
    Returns number of profiles updated.
    """
    from app.models.analytics import BenchmarkProfile

    since = datetime.now(timezone.utc) - timedelta(days=90)
    period_start = (datetime.now(timezone.utc) - timedelta(days=90)).date()
    period_end = datetime.now(timezone.utc).date()

    user_ids_subq = select(User.id).where(User.organization_id == org_id)

    # Get stats per contract type
    result = await db.execute(
        select(
            func.coalesce(Document.contract_type, "unclassified").label("ct"),
            func.avg(Document.risk_score).label("avg_rs"),
            func.avg(Document.total_risks).label("avg_risks"),
            func.avg(
                case(
                    (Document.risk_summary.isnot(None),
                     func.cast(Document.risk_summary["red"].as_string(), Decimal)),
                    else_=Decimal("0"),
                )
            ).label("avg_red"),
            func.avg(Document.processing_duration_ms).label("avg_ms"),
            func.count(Document.id).label("doc_count"),
        )
        .where(Document.user_id.in_(user_ids_subq))
        .where(Document.created_at >= since)
        .where(Document.status == DocumentStatus.COMPLETED)
        .group_by(func.coalesce(Document.contract_type, "unclassified"))
    )

    count = 0
    for row in result.all():
        # Upsert benchmark profile
        existing = await db.execute(
            select(BenchmarkProfile).where(
                and_(
                    BenchmarkProfile.organization_id == org_id,
                    BenchmarkProfile.contract_type == row.ct,
                    BenchmarkProfile.period_start == period_start,
                    BenchmarkProfile.period_end == period_end,
                )
            )
        )
        profile = existing.scalar_one_or_none()

        if not profile:
            profile = BenchmarkProfile(
                organization_id=org_id,
                contract_type=row.ct,
                period_start=period_start,
                period_end=period_end,
            )
            db.add(profile)

        profile.avg_risk_score = Decimal(str(round(float(row.avg_rs or 0), 2)))
        profile.avg_risks_per_doc = Decimal(str(round(float(row.avg_risks or 0), 2)))
        profile.avg_red_risks = Decimal(str(round(float(row.avg_red or 0), 2)))
        profile.avg_processing_ms = int(row.avg_ms or 0)
        profile.document_count = row.doc_count or 0
        count += 1

    await db.flush()
    return count
