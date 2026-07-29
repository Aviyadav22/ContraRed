"""
Data Erasure Service - Right to Erasure (DPDP Section 12).

Removes user-controlled content, anonymises identity fields, preserves only
the minimum audit facts governed by the deployment's retention schedule, and
revokes all active sessions.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.consent import (
    ConsentRecord, ConsentPurposeGrant, ConsentStatus, ConsentNomination,
    ConsentReceipt, RightsRequest, Grievance, GrievanceStatus,
)
from app.models.document import Document, UsageLog
from app.models.drafting import DraftSession
from app.models.batch_job import BatchJob, BatchJobFile
from app.models.analytics import ReviewSession
from app.models.feedback import RuleFeedback

logger = logging.getLogger(__name__)

# Placeholder values for anonymised fields
ANON_NAME = "Deleted User"


async def erase_user_data(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    commit: bool = True,
) -> dict:
    """Erase personal data for a user (DPDP Section 12).

    - Anonymises PII fields (email, name) in users table
    - Deactivates the account
    - Withdraws all consents
    - Deactivates nominations
    - Removes stored document/drafting content and user activity rows
    - Retains only anonymised audit/consent facts under configured retention
    - Revokes sessions via token blacklist

    Returns a summary of actions taken.
    """
    now = datetime.now(timezone.utc)
    actions = []

    # 1. Anonymise user profile
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()
    if not user:
        return {"error": "User not found"}

    unresolved_grievances = await db.scalar(
        select(Grievance.id)
        .where(
            Grievance.subject_id == user_id,
            Grievance.status != GrievanceStatus.RESOLVED.value,
        )
        .limit(1)
    )
    if unresolved_grievances:
        return {
            "error": (
                "Erasure is blocked while a grievance remains unresolved. "
                "Resolve or lawfully reject the grievance first."
            )
        }

    original_email = user.email
    anon_suffix = str(user_id)[:8]

    user.email = f"deleted-{anon_suffix}@anonymised.contrared.app"
    user.name = ANON_NAME
    user.password_hash = None
    user.is_active = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    user.sso_provider_id = None
    user.razorpay_customer_id = None
    user.organization_id = None
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = None
    user.updated_at = now
    actions.append("User profile anonymised")

    # 2. Withdraw all consents
    consent_result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.subject_id == user_id, ConsentRecord.status == ConsentStatus.ACTIVE.value)
    )
    for cr in consent_result.scalars().all():
        cr.status = ConsentStatus.WITHDRAWN.value
        cr.ip_address = None
        cr.user_agent = None
        cr.consent_metadata = {"redacted_after_erasure": True}
        cr.updated_at = now
        # Withdraw all grants
        grants_result = await db.execute(
            select(ConsentPurposeGrant)
            .where(ConsentPurposeGrant.consent_record_id == cr.id, ConsentPurposeGrant.granted.is_(True))
        )
        for grant in grants_result.scalars().all():
            grant.granted = False
            grant.withdrawn_at = now
    actions.append("All consents withdrawn")

    # 3. Redact consent receipts while retaining proof that a receipt existed.
    receipt_result = await db.execute(
        select(ConsentReceipt)
        .join(ConsentRecord, ConsentReceipt.consent_record_id == ConsentRecord.id)
        .where(ConsentRecord.subject_id == user_id)
    )
    for receipt in receipt_result.scalars().all():
        receipt.receipt_data = {
            "status": "redacted_after_erasure",
            "schema_version": receipt.schema_version,
        }
        receipt.digital_signature = None
    actions.append("Consent receipt payloads redacted")

    # 4. Deactivate and redact nominations
    nom_result = await db.execute(
        select(ConsentNomination).where(ConsentNomination.subject_id == user_id)
    )
    for nom in nom_result.scalars().all():
        nom.is_active = False
        nom.revoked_at = now
        nom.nominee_name = "Deleted Nominee"
        nom.nominee_email = None
        nom.nominee_phone = None
        nom.nominee_contact = {}
        nom.relationship = None
    actions.append("Nominations deactivated and redacted")

    # 5. Redact request and resolved-grievance payloads.
    rights_result = await db.execute(
        select(RightsRequest).where(RightsRequest.subject_id == user_id)
    )
    for rights_request in rights_result.scalars().all():
        rights_request.request_details = {"redacted_after_erasure": True}
        rights_request.response_details = {"redacted_after_erasure": True}

    grievance_result = await db.execute(
        select(Grievance).where(Grievance.subject_id == user_id)
    )
    for grievance in grievance_result.scalars().all():
        grievance.description = "[REDACTED AFTER ERASURE]"
        grievance.evidence = {}
        grievance.resolution_notes = None
    actions.append("Rights and grievance payloads redacted")

    # 6. Remove user-controlled contract and drafting content.
    batch_ids = select(BatchJob.id).where(BatchJob.user_id == user_id)
    await db.execute(delete(BatchJobFile).where(BatchJobFile.batch_id.in_(batch_ids)))
    await db.execute(delete(BatchJob).where(BatchJob.user_id == user_id))
    await db.execute(delete(DraftSession).where(DraftSession.user_id == user_id))
    await db.execute(delete(Document).where(Document.user_id == user_id))
    await db.execute(delete(UsageLog).where(UsageLog.user_id == user_id))
    await db.execute(delete(ReviewSession).where(ReviewSession.user_id == user_id))
    await db.execute(
        update(RuleFeedback)
        .where(RuleFeedback.user_id == user_id)
        .values(
            user_id=None,
            clause_text=None,
            user_comment=None,
            document_id=None,
        )
    )
    actions.append("Stored contract, drafting, batch, feedback, and usage data removed")

    # 7. Retain audit event facts while removing identifiers and metadata.
    await db.execute(
        update(AuditLog)
        .where(AuditLog.user_id == user_id)
        .values(
            user_email=f"deleted-{anon_suffix}@anonymised.contrared.app",
            resource_name="[REDACTED AFTER ERASURE]",
            ip_address=None,
            user_agent=None,
            details=None,
        )
    )
    actions.append("Audit logs anonymised")

    # 8. Revoke all active sessions
    try:
        from app.services.token_service import get_token_blacklist
        blacklist = await get_token_blacklist()
        revoked = await blacklist.revoke_all_for_user(str(user_id))
        actions.append(
            f"Account deactivated; {revoked} active session(s) explicitly revoked"
        )
    except Exception as e:
        logger.warning("Token blacklist not available: %s", e)
        actions.append("Account deactivated (token blacklist unavailable)")

    if commit:
        await db.commit()
    else:
        await db.flush()

    logger.info(
        "Data erasure completed for user %s (original email: %s). Actions: %s",
        user_id, original_email, actions,
    )

    return {
        "user_id": str(user_id),
        "erasure_completed_at": now.isoformat(),
        "actions": actions,
        "retention_note": (
            "Minimal anonymised audit and consent-event facts remain subject "
            "to the configured legal, security, and dispute-retention schedule."
        ),
    }
