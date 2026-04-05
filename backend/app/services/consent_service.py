"""
Consent Service - Core business logic for DPDP Act consent management.

Handles the full consent lifecycle:
  - Grant consent (with per-purpose granularity)
  - Withdraw consent (per-purpose or all)
  - Check consent (fast path for middleware enforcement)
  - Get consent status (full dashboard view)
  - Generate ISO 27560 receipts
  - Record immutable hash-chained events

Uses Redis cache (when available) for O(1) consent checks during enforcement.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, desc, text, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.consent import (
    ConsentPurpose, ConsentPolicy, ConsentRecord, ConsentPurposeGrant,
    ConsentEvent, ConsentReceipt, ConsentStatus, ConsentEventType,
    CONSENT_RETENTION_YEARS,
)

logger = logging.getLogger(__name__)

# Cache TTL for consent checks (seconds)
CONSENT_CACHE_TTL = 60


class ConsentService:
    """Core consent management service."""

    def __init__(self, cache_client=None):
        self._cache = cache_client

    # ----------------------------------------------------------------
    # Grant consent
    # ----------------------------------------------------------------

    async def grant_consent(
        self,
        db: AsyncSession,
        subject_id: uuid.UUID,
        purpose_codes: List[str],
        policy_version_id: Optional[uuid.UUID] = None,
        organization_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        collection_method: str = "web_form",
        expression_method: str = "checkbox",
        metadata: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Grant consent for specified purposes.

        Creates or updates a consent record and per-purpose grants.
        Emits consent events and generates an ISO 27560 receipt.

        Returns dict with consent_record_id, receipt_id, and granted purposes.
        """
        now = datetime.now(timezone.utc)

        # Look up purpose definitions
        purposes = await self._get_active_purposes(db, purpose_codes)
        if not purposes:
            raise ValueError(f"No active purposes found for codes: {purpose_codes}")

        # Find existing active consent record for this user, or create new
        existing = await self._get_active_record(db, subject_id, organization_id)

        if existing:
            record = existing
            record.updated_at = now
            if policy_version_id:
                record.policy_version_id = policy_version_id
        else:
            record = ConsentRecord(
                subject_id=subject_id,
                organization_id=organization_id,
                policy_version_id=policy_version_id,
                status=ConsentStatus.ACTIVE.value,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,
                collection_method=collection_method,
                expression_method=expression_method,
                consent_metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )
            db.add(record)
            await db.flush()

        # Upsert per-purpose grants
        granted_codes = []
        for purpose in purposes:
            grant = await self._get_purpose_grant(db, record.id, purpose.purpose_code)
            if grant:
                grant.granted = True
                grant.granted_at = now
                grant.withdrawn_at = None
            else:
                grant = ConsentPurposeGrant(
                    consent_record_id=record.id,
                    purpose_id=purpose.id,
                    purpose_code=purpose.purpose_code,
                    granted=True,
                    granted_at=now,
                    created_at=now,
                )
                db.add(grant)
            granted_codes.append(purpose.purpose_code)

        # Emit consent events
        for code in granted_codes:
            await self._record_event(
                db, record.id, subject_id, ConsentEventType.GRANTED.value,
                purpose_code=code, ip_address=ip_address, user_agent=user_agent,
                details={"collection_method": collection_method},
            )

        # Generate receipt
        receipt = await self._generate_receipt(db, record, granted_codes, purposes)

        await db.flush()

        # Invalidate cache
        await self._invalidate_cache(subject_id, granted_codes)

        # Publish event (non-fatal)
        try:
            from app.services.consent_event_bus import consent_event_bus
            await consent_event_bus.publish_consent_granted(
                str(subject_id), granted_codes, str(record.id),
            )
        except Exception as e:
            logger.debug("Event bus publish failed (non-fatal): %s", e)

        return {
            "consent_record_id": str(record.id),
            "receipt_id": str(receipt.id),
            "granted_purposes": granted_codes,
            "status": record.status,
        }

    # ----------------------------------------------------------------
    # Withdraw consent
    # ----------------------------------------------------------------

    async def withdraw_consent(
        self,
        db: AsyncSession,
        subject_id: uuid.UUID,
        purpose_codes: List[str],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Withdraw consent for specified purposes.

        If all purposes are withdrawn, the consent record status becomes 'withdrawn'.
        """
        now = datetime.now(timezone.utc)

        record = await self._get_active_record(db, subject_id)
        if not record:
            raise ValueError("No active consent record found")

        withdrawn_codes = []
        for code in purpose_codes:
            grant = await self._get_purpose_grant(db, record.id, code)
            if grant and grant.granted:
                grant.granted = False
                grant.withdrawn_at = now
                withdrawn_codes.append(code)

                await self._record_event(
                    db, record.id, subject_id, ConsentEventType.WITHDRAWN.value,
                    purpose_code=code, ip_address=ip_address, user_agent=user_agent,
                    details={"reason": reason} if reason else {},
                )

        # Check if all purposes are now withdrawn
        remaining = await db.execute(
            select(ConsentPurposeGrant)
            .where(
                ConsentPurposeGrant.consent_record_id == record.id,
                ConsentPurposeGrant.granted == True,
            )
        )
        if not remaining.scalars().first():
            record.status = ConsentStatus.WITHDRAWN.value

        record.updated_at = now
        await db.flush()

        # Invalidate cache
        await self._invalidate_cache(subject_id, withdrawn_codes)

        # Publish event (non-fatal)
        try:
            from app.services.consent_event_bus import consent_event_bus
            await consent_event_bus.publish_consent_withdrawn(
                str(subject_id), withdrawn_codes, str(record.id),
            )
        except Exception as e:
            logger.debug("Event bus publish failed (non-fatal): %s", e)

        return {
            "consent_record_id": str(record.id),
            "withdrawn_purposes": withdrawn_codes,
            "status": record.status,
        }

    # ----------------------------------------------------------------
    # Check consent (fast path for middleware)
    # ----------------------------------------------------------------

    async def check_consent(
        self,
        db: AsyncSession,
        subject_id: uuid.UUID,
        purpose_code: str,
    ) -> bool:
        """Check if user has granted consent for a specific purpose.

        Uses Redis cache when available for O(1) lookups.
        """
        # Try cache first
        cached = await self._get_from_cache(subject_id, purpose_code)
        if cached is not None:
            return cached

        # DB lookup
        result = await db.execute(
            select(ConsentPurposeGrant.granted)
            .join(ConsentRecord, ConsentPurposeGrant.consent_record_id == ConsentRecord.id)
            .where(
                ConsentRecord.subject_id == subject_id,
                ConsentRecord.status == ConsentStatus.ACTIVE.value,
                ConsentPurposeGrant.purpose_code == purpose_code,
                ConsentPurposeGrant.granted == True,
            )
            .limit(1)
        )
        granted = result.scalar() is not None

        # Cache the result
        await self._set_in_cache(subject_id, purpose_code, granted)

        return granted

    # ----------------------------------------------------------------
    # Get full consent status
    # ----------------------------------------------------------------

    async def get_consent_status(
        self,
        db: AsyncSession,
        subject_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get comprehensive consent status for a user (preference center data)."""
        record = await self._get_active_record(db, subject_id)
        if not record:
            # Return all purposes with no grants
            purposes = await self._get_all_active_purposes(db)
            return {
                "has_consent_record": False,
                "purposes": [
                    {
                        "code": p.purpose_code,
                        "name": p.name,
                        "description": p.description,
                        "is_required": p.is_required,
                        "granted": False,
                        "personal_data_categories": p.personal_data_categories,
                        "third_parties": p.third_parties,
                        "retention_period": p.retention_period,
                        "translations": p.translations or {},
                    }
                    for p in purposes
                ],
            }

        # Load grants
        grants_result = await db.execute(
            select(ConsentPurposeGrant)
            .where(ConsentPurposeGrant.consent_record_id == record.id)
        )
        grants = {g.purpose_code: g for g in grants_result.scalars().all()}

        purposes = await self._get_all_active_purposes(db)

        return {
            "has_consent_record": True,
            "consent_record_id": str(record.id),
            "status": record.status,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "purposes": [
                {
                    "code": p.purpose_code,
                    "name": p.name,
                    "description": p.description,
                    "is_required": p.is_required,
                    "granted": grants.get(p.purpose_code, None) is not None
                               and grants[p.purpose_code].granted,
                    "granted_at": grants[p.purpose_code].granted_at.isoformat()
                                  if grants.get(p.purpose_code) and grants[p.purpose_code].granted_at
                                  else None,
                    "withdrawn_at": grants[p.purpose_code].withdrawn_at.isoformat()
                                    if grants.get(p.purpose_code) and grants[p.purpose_code].withdrawn_at
                                    else None,
                    "personal_data_categories": p.personal_data_categories,
                    "third_parties": p.third_parties,
                    "retention_period": p.retention_period,
                    "translations": p.translations or {},
                }
                for p in purposes
            ],
        }

    # ----------------------------------------------------------------
    # Get consent event history
    # ----------------------------------------------------------------

    async def get_consent_history(
        self,
        db: AsyncSession,
        subject_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get consent event history for a user."""
        result = await db.execute(
            select(ConsentEvent)
            .where(ConsentEvent.subject_id == subject_id)
            .order_by(desc(ConsentEvent.created_at))
            .limit(limit)
            .offset(offset)
        )
        events = result.scalars().all()
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "purpose_code": e.purpose_code,
                "actor": e.actor,
                "details": e.details,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]

    # ----------------------------------------------------------------
    # Get consent receipts
    # ----------------------------------------------------------------

    async def get_receipts(
        self,
        db: AsyncSession,
        subject_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """Get all consent receipts for a user."""
        result = await db.execute(
            select(ConsentReceipt)
            .join(ConsentRecord, ConsentReceipt.consent_record_id == ConsentRecord.id)
            .where(ConsentRecord.subject_id == subject_id)
            .order_by(desc(ConsentReceipt.issued_at))
        )
        receipts = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "receipt_data": r.receipt_data,
                "schema_version": r.schema_version,
                "digital_signature": r.digital_signature,
                "issued_at": r.issued_at.isoformat(),
                "downloaded_at": r.downloaded_at.isoformat() if r.downloaded_at else None,
            }
            for r in receipts
        ]

    # ----------------------------------------------------------------
    # Get purposes
    # ----------------------------------------------------------------

    async def get_purposes(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all active consent purposes."""
        purposes = await self._get_all_active_purposes(db)
        return [
            {
                "code": p.purpose_code,
                "name": p.name,
                "description": p.description,
                "is_required": p.is_required,
                "personal_data_categories": p.personal_data_categories,
                "third_parties": p.third_parties,
                "retention_period": p.retention_period,
                "translations": p.translations or {},
            }
            for p in purposes
        ]

    # ----------------------------------------------------------------
    # Get current policy
    # ----------------------------------------------------------------

    async def get_current_policy(
        self, db: AsyncSession, language: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """Get the current active privacy policy."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ConsentPolicy)
            .where(
                ConsentPolicy.language == language,
                ConsentPolicy.effective_from <= now,
            )
            .order_by(desc(ConsentPolicy.version))
            .limit(1)
        )
        policy = result.scalar()
        if not policy:
            return None
        return {
            "id": str(policy.id),
            "version": policy.version,
            "title": policy.title,
            "content": policy.content,
            "language": policy.language,
            "checksum": policy.checksum,
            "effective_from": policy.effective_from.isoformat(),
        }

    # ================================================================
    # Private helpers
    # ================================================================

    async def _get_active_purposes(
        self, db: AsyncSession, purpose_codes: List[str]
    ) -> List[ConsentPurpose]:
        """Get active purpose definitions by code (latest version of each)."""
        # Get latest version of each requested purpose
        purposes = []
        for code in purpose_codes:
            result = await db.execute(
                select(ConsentPurpose)
                .where(
                    ConsentPurpose.purpose_code == code,
                    ConsentPurpose.is_active == True,
                )
                .order_by(desc(ConsentPurpose.version))
                .limit(1)
            )
            purpose = result.scalar()
            if purpose:
                purposes.append(purpose)
        return purposes

    async def _get_all_active_purposes(self, db: AsyncSession) -> List[ConsentPurpose]:
        """Get all active purposes (latest version of each)."""
        # Get all distinct purpose codes, then latest version of each
        result = await db.execute(
            select(ConsentPurpose)
            .where(ConsentPurpose.is_active == True)
            .order_by(ConsentPurpose.purpose_code, desc(ConsentPurpose.version))
        )
        all_purposes = result.scalars().all()
        # Deduplicate: keep first (latest version) per code
        seen = set()
        unique = []
        for p in all_purposes:
            if p.purpose_code not in seen:
                seen.add(p.purpose_code)
                unique.append(p)
        return unique

    async def _get_active_record(
        self, db: AsyncSession, subject_id: uuid.UUID,
        organization_id: Optional[uuid.UUID] = None,
    ) -> Optional[ConsentRecord]:
        """Get the active consent record for a user."""
        query = select(ConsentRecord).where(
            ConsentRecord.subject_id == subject_id,
            ConsentRecord.status == ConsentStatus.ACTIVE.value,
        )
        if organization_id:
            query = query.where(ConsentRecord.organization_id == organization_id)
        query = query.order_by(desc(ConsentRecord.created_at)).limit(1)
        result = await db.execute(query)
        return result.scalar()

    async def _get_purpose_grant(
        self, db: AsyncSession, consent_record_id: uuid.UUID, purpose_code: str
    ) -> Optional[ConsentPurposeGrant]:
        """Get a specific purpose grant."""
        result = await db.execute(
            select(ConsentPurposeGrant).where(
                ConsentPurposeGrant.consent_record_id == consent_record_id,
                ConsentPurposeGrant.purpose_code == purpose_code,
            )
        )
        return result.scalar()

    async def _record_event(
        self,
        db: AsyncSession,
        consent_record_id: Optional[uuid.UUID],
        subject_id: uuid.UUID,
        event_type: str,
        purpose_code: Optional[str] = None,
        actor: str = "data_subject",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> ConsentEvent:
        """Record an immutable consent event with hash chain."""
        now = datetime.now(timezone.utc)

        # Get sequence number
        seq_number = 1
        try:
            seq_result = await db.execute(text("SELECT nextval('consent_event_sequence')"))
            seq_number = seq_result.scalar()
        except Exception:
            seq_number = 1

        # Get previous hash
        previous_hash = "GENESIS"
        try:
            last_result = await db.execute(
                select(ConsentEvent.entry_hash)
                .where(ConsentEvent.entry_hash.isnot(None))
                .order_by(desc(ConsentEvent.sequence_number))
                .limit(1)
            )
            last_hash = last_result.scalar()
            if last_hash:
                previous_hash = last_hash
        except Exception as e:
            logger.debug("Consent event hash chain lookup failed (non-fatal): %s", e)

        # Compute hash
        hash_input = f"{seq_number}|{event_type}|{subject_id}|{now.isoformat()}|{previous_hash}"
        entry_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        event = ConsentEvent(
            consent_record_id=consent_record_id,
            subject_id=subject_id,
            event_type=event_type,
            purpose_code=purpose_code,
            actor=actor,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            entry_hash=entry_hash,
            previous_hash=previous_hash,
            sequence_number=seq_number,
            retention_until=now + timedelta(days=365 * CONSENT_RETENTION_YEARS),
            created_at=now,
        )
        db.add(event)
        return event

    async def _generate_receipt(
        self,
        db: AsyncSession,
        record: ConsentRecord,
        purpose_codes: List[str],
        purposes: List[ConsentPurpose],
    ) -> ConsentReceipt:
        """Generate an ISO 27560 compliant consent receipt."""
        now = datetime.now(timezone.utc)
        receipt_id = str(uuid.uuid4())

        # Build ISO 27560 JSON-LD receipt
        receipt_data = {
            "@context": "https://www.w3.org/ns/dpv",
            "@type": "ConsentRecord",
            "schema_version": "ISO/IEC TS 27560:2023",
            "record_id": receipt_id,
            "data_subject": str(record.subject_id),
            "data_controller": {
                "name": settings.APP_NAME,
                "jurisdiction": "IN",
            },
            "consent_timestamp": now.isoformat(),
            "consent_state": "active",
            "processing": [
                {
                    "purpose": p.purpose_code,
                    "purpose_description": p.description,
                    "personal_data_categories": p.personal_data_categories,
                    "recipients": p.third_parties,
                    "retention_period": p.retention_period,
                    "collection_method": record.collection_method,
                    "withdrawal_method": "API endpoint: POST /api/v1/consent/withdraw",
                }
                for p in purposes
                if p.purpose_code in purpose_codes
            ],
            "privacy_notice_reference": f"/api/v1/consent/policy/current",
            "jurisdiction": "IN",
            "dpdp_act_section": "Section 6",
        }

        # Sign the receipt
        signature = self._sign_receipt(receipt_data)

        receipt = ConsentReceipt(
            consent_record_id=record.id,
            receipt_data=receipt_data,
            digital_signature=signature,
            schema_version="27560:2023",
            issued_at=now,
        )
        db.add(receipt)
        return receipt

    def _sign_receipt(self, receipt_data: dict) -> str:
        """HMAC-SHA256 sign a consent receipt."""
        key = getattr(settings, "SECRET_KEY", "default-key")
        message = json.dumps(receipt_data, sort_keys=True).encode("utf-8")
        return hmac.new(key.encode("utf-8"), message, hashlib.sha256).hexdigest()

    # ---- Cache helpers ----

    async def _get_from_cache(self, subject_id: uuid.UUID, purpose_code: str) -> Optional[bool]:
        if not self._cache:
            return None
        try:
            key = f"consent:{subject_id}:{purpose_code}"
            val = await self._cache.get(key)
            if val is not None:
                return val == "1"
        except Exception as e:
            logger.debug("Consent cache read failed (non-fatal): %s", e)
        return None

    async def _set_in_cache(self, subject_id: uuid.UUID, purpose_code: str, granted: bool):
        if not self._cache:
            return
        try:
            key = f"consent:{subject_id}:{purpose_code}"
            await self._cache.set(key, "1" if granted else "0", ex=CONSENT_CACHE_TTL)
        except Exception as e:
            logger.debug("Consent cache write failed (non-fatal): %s", e)

    async def _invalidate_cache(self, subject_id: uuid.UUID, purpose_codes: List[str]):
        if not self._cache:
            return
        try:
            for code in purpose_codes:
                key = f"consent:{subject_id}:{code}"
                await self._cache.delete(key)
        except Exception as e:
            logger.debug("Consent cache invalidation failed (non-fatal): %s", e)


# Singleton instance
consent_service = ConsentService()
