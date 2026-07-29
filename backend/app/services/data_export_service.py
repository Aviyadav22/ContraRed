"""
Data Export Service - Right to Access (DPDP Section 11).

Collects all personal data associated with a user and packages it as JSON.
Respects Zero Data Retention: contract text is never stored, so it won't
appear in the export. Only metadata (filenames, timestamps, risk counts) is exported.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.billing import Invoice
from app.models.consent import (
    ConsentRecord, ConsentPurposeGrant, ConsentEvent, ConsentReceipt,
    RightsRequest, Grievance, ConsentNomination,
)
from app.models.document import Document, DocumentRisk, UsageLog
from app.models.feedback import RuleFeedback
from app.core.config import settings

logger = logging.getLogger(__name__)


async def export_user_data(db: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    """Export all personal data for a user (DPDP Section 11 - Right to Access).

    Returns a dict suitable for JSON serialization.
    """
    # 1. User profile
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()
    if not user:
        return {"error": "User not found"}

    profile = {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role.value if user.role else None,
        "subscription_tier": user.subscription_tier.value if user.subscription_tier else None,
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "mfa_enabled": user.mfa_enabled,
        "sso_provider_id": user.sso_provider_id,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }

    # 2. Consent records
    consent_result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.subject_id == user_id)
    )
    consent_records = []
    for cr in consent_result.scalars().all():
        grants_result = await db.execute(
            select(ConsentPurposeGrant).where(ConsentPurposeGrant.consent_record_id == cr.id)
        )
        grants = [
            {
                "purpose_code": g.purpose_code,
                "granted": g.granted,
                "granted_at": g.granted_at.isoformat() if g.granted_at else None,
                "withdrawn_at": g.withdrawn_at.isoformat() if g.withdrawn_at else None,
            }
            for g in grants_result.scalars().all()
        ]
        consent_records.append({
            "id": str(cr.id),
            "status": cr.status,
            "collection_method": cr.collection_method,
            "created_at": cr.created_at.isoformat(),
            "purpose_grants": grants,
        })

    # 3. Consent events (audit trail)
    events_result = await db.execute(
        select(ConsentEvent)
        .where(ConsentEvent.subject_id == user_id)
        .order_by(desc(ConsentEvent.created_at))
        .limit(500)
    )
    consent_events = [
        {
            "event_type": e.event_type,
            "purpose_code": e.purpose_code,
            "actor": e.actor,
            "created_at": e.created_at.isoformat(),
        }
        for e in events_result.scalars().all()
    ]

    # 4. Consent receipts
    receipts_result = await db.execute(
        select(ConsentReceipt)
        .join(ConsentRecord, ConsentReceipt.consent_record_id == ConsentRecord.id)
        .where(ConsentRecord.subject_id == user_id)
    )
    receipts = [
        {
            "receipt_data": r.receipt_data,
            "schema_version": r.schema_version,
            "issued_at": r.issued_at.isoformat(),
        }
        for r in receipts_result.scalars().all()
    ]

    # 5. Audit logs (user's own activity)
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(desc(AuditLog.timestamp))
        .limit(1000)
    )
    audit_logs = [
        {
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_name": a.resource_name,
            "timestamp": a.timestamp.isoformat(),
            "status": a.status,
        }
        for a in audit_result.scalars().all()
    ]

    # 6. Rights requests
    rights_result = await db.execute(
        select(RightsRequest)
        .where(RightsRequest.subject_id == user_id)
        .order_by(desc(RightsRequest.submitted_at))
    )
    rights_requests = [
        {
            "request_type": r.request_type,
            "status": r.status,
            "submitted_at": r.submitted_at.isoformat(),
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        }
        for r in rights_result.scalars().all()
    ]

    # 7. Grievances
    grievance_result = await db.execute(
        select(Grievance)
        .where(Grievance.subject_id == user_id)
        .order_by(desc(Grievance.submitted_at))
    )
    grievance_list = [
        {
            "category": g.category,
            "description": g.description,
            "status": g.status,
            "submitted_at": g.submitted_at.isoformat(),
            "resolved_at": g.resolved_at.isoformat() if g.resolved_at else None,
        }
        for g in grievance_result.scalars().all()
    ]

    # 8. Nominations
    nom_result = await db.execute(
        select(ConsentNomination)
        .where(ConsentNomination.subject_id == user_id)
    )
    nominations = [
        {
            "nominee_name": n.nominee_name,
            "relationship": n.relationship,
            "is_active": n.is_active,
            "created_at": n.created_at.isoformat(),
        }
        for n in nom_result.scalars().all()
    ]

    # 9. Document metadata and, only when ZDR is disabled, stored findings.
    document_result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(desc(Document.created_at))
    )
    documents = []
    document_ids = []
    for document in document_result.scalars().all():
        document_ids.append(document.id)
        documents.append({
            "id": str(document.id),
            "filename": document.filename,
            "status": document.status.value if document.status else None,
            "contract_type": document.contract_type,
            "counterparty": document.counterparty,
            "contract_value": str(document.contract_value) if document.contract_value is not None else None,
            "expiry_date": document.expiry_date.isoformat() if document.expiry_date else None,
            "risk_summary": document.risk_summary,
            "total_risks": document.total_risks,
            "created_at": document.created_at.isoformat(),
            "processed_at": document.processed_at.isoformat() if document.processed_at else None,
        })

    stored_findings = []
    if not settings.ZERO_DATA_RETENTION and document_ids:
        finding_result = await db.execute(
            select(DocumentRisk).where(DocumentRisk.document_id.in_(document_ids))
        )
        stored_findings = [
            {
                "document_id": str(f.document_id),
                "rule_name": f.rule_name,
                "clause_text": f.clause_text,
                "risk_level": f.risk_level.value if f.risk_level else None,
                "explanation": f.ai_explanation,
                "suggested_fix": f.suggested_fix,
                "created_at": f.created_at.isoformat(),
            }
            for f in finding_result.scalars().all()
        ]

    # 10. Usage records.
    usage_result = await db.execute(
        select(UsageLog)
        .where(UsageLog.user_id == user_id)
        .order_by(desc(UsageLog.created_at))
    )
    usage_logs = [
        {
            "action": u.action.value if u.action else None,
            "tokens_used": u.tokens_used,
            "cost_usd": str(u.cost_usd),
            "metadata": u.extra_data,
            "created_at": u.created_at.isoformat(),
        }
        for u in usage_result.scalars().all()
    ]

    # 11. Billing records retained for the account.
    invoice_result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == user_id)
        .order_by(desc(Invoice.created_at))
    )
    invoices = [
        {
            "id": str(invoice.id),
            "amount": invoice.amount,
            "currency": invoice.currency,
            "status": invoice.status,
            "plan": invoice.plan,
            "description": invoice.description,
            "gateway": invoice.gateway,
            "gateway_payment_id": invoice.gateway_payment_id,
            "gateway_invoice_id": invoice.gateway_invoice_id,
            "created_at": invoice.created_at.isoformat(),
            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        }
        for invoice in invoice_result.scalars().all()
    ]

    # 12. Lawyer feedback submitted by the user.
    feedback_result = await db.execute(
        select(RuleFeedback)
        .where(RuleFeedback.user_id == user_id)
        .order_by(desc(RuleFeedback.created_at))
    )
    feedback = [
        {
            "id": str(item.id),
            "feedback_type": item.feedback_type,
            "clause_text": item.clause_text,
            "comment": item.user_comment,
            "suggested_risk_level": item.suggested_risk_level,
            "created_at": item.created_at.isoformat(),
        }
        for item in feedback_result.scalars().all()
    ]

    return {
        "export_metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "data_controller": "ContraRed",
            "dpdp_section": "Section 11 - Right to Information About Personal Data",
            "format_version": "1.0",
        },
        "profile": profile,
        "consent_records": consent_records,
        "consent_events": consent_events,
        "consent_receipts": receipts,
        "audit_logs": audit_logs,
        "rights_requests": rights_requests,
        "grievances": grievance_list,
        "nominations": nominations,
        "documents": documents,
        "stored_findings": stored_findings,
        "usage_logs": usage_logs,
        "invoices": invoices,
        "feedback": feedback,
        "note": (
            "Contract text is not included because this deployment operates in "
            "Zero Data Retention mode; only document metadata is stored."
            if settings.ZERO_DATA_RETENTION
            else "Stored finding text is included because Zero Data Retention is disabled."
        ),
    }
