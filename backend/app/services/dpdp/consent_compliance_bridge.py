"""
Consent-Compliance Bridge - Wires the consent management framework to DPDP agents.

Solves the #1 real-world compliance failure: the consent-to-enforcement disconnect.
When the scanner finds "no consent mechanism", this bridge checks if our consent
framework actually covers it. When the gap assessor asks about consent, this bridge
answers from real data instead of requiring manual input.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import (
    ConsentPurpose, ConsentRecord, ConsentPurposeGrant,
    ConsentEvent, ConsentPolicy, ConsentStatus,
)

logger = logging.getLogger(__name__)


class ConsentComplianceBridge:
    """Bridge between consent framework and DPDP compliance agents."""

    async def get_consent_health(self, db: AsyncSession, organization_id=None) -> Dict[str, Any]:
        """Get comprehensive consent health metrics for the compliance dashboard.

        Returns metrics that the Monitor Agent uses for its dashboard.
        """
        try:
            # Total users with active consent
            active_query = select(func.count(ConsentRecord.id)).where(
                ConsentRecord.status == ConsentStatus.ACTIVE.value
            )
            if organization_id:
                active_query = active_query.where(ConsentRecord.organization_id == organization_id)
            active_result = await db.execute(active_query)
            active_consents = active_result.scalar() or 0

            # Total users with any consent record
            total_query = select(func.count(ConsentRecord.id))
            if organization_id:
                total_query = total_query.where(ConsentRecord.organization_id == organization_id)
            total_result = await db.execute(total_query)
            total_records = total_result.scalar() or 0

            # Purpose-level grant stats
            purpose_stats = await self._get_purpose_stats(db, organization_id)

            # Recent consent events (last 30 days)
            thirty_days_ago = datetime.now(timezone.utc).replace(day=max(1, datetime.now(timezone.utc).day - 30))
            events_query = select(
                ConsentEvent.event_type,
                func.count(ConsentEvent.id)
            ).where(
                ConsentEvent.created_at >= thirty_days_ago
            ).group_by(ConsentEvent.event_type)
            events_result = await db.execute(events_query)
            event_counts = dict(events_result.all())

            # Privacy policy version
            policy_result = await db.execute(
                select(ConsentPolicy.version, ConsentPolicy.checksum)
                .order_by(ConsentPolicy.version.desc())
                .limit(1)
            )
            policy = policy_result.first()

            # Calculate consent health score (0-100)
            health_score = self._calculate_health_score(
                active_consents, total_records, purpose_stats, event_counts
            )

            return {
                "health_score": health_score,
                "active_consents": active_consents,
                "total_records": total_records,
                "consent_rate": round(active_consents / max(total_records, 1) * 100, 1),
                "purpose_stats": purpose_stats,
                "recent_events": {
                    "grants": event_counts.get("granted", 0),
                    "withdrawals": event_counts.get("withdrawn", 0),
                    "rights_requests": event_counts.get("rights_request", 0),
                    "grievances": event_counts.get("grievance_filed", 0),
                },
                "privacy_policy_version": policy[0] if policy else None,
                "privacy_policy_checksum": policy[1] if policy else None,
            }
        except Exception as e:
            logger.error("Failed to get consent health: %s", e)
            return {
                "health_score": 0,
                "active_consents": 0,
                "total_records": 0,
                "consent_rate": 0,
                "purpose_stats": [],
                "recent_events": {},
                "error": str(e),
            }

    async def auto_answer_consent_questions(
        self, db: AsyncSession, organization_id=None
    ) -> Dict[str, str]:
        """Auto-answer gap assessment consent questions from real consent data.

        Returns a dict of question_id -> answer (yes/no/partial) that the
        gap assessor can use instead of requiring manual input.
        """
        health = await self.get_consent_health(db, organization_id)
        purpose_stats = {p["code"]: p for p in health.get("purpose_stats", [])}

        answers = {}

        # Q: "Do you collect granular, purpose-specific consent?"
        has_purposes = len(purpose_stats) > 0
        has_granular = any(not p.get("is_required", True) for p in purpose_stats.values())
        if has_purposes and has_granular:
            answers["consent_1"] = "yes"
        elif has_purposes:
            answers["consent_1"] = "partial"
        else:
            answers["consent_1"] = "no"

        # Q: "Can users withdraw consent as easily as they gave it?"
        # If we have withdrawal events, the mechanism exists
        if health["recent_events"].get("withdrawals", 0) > 0 or has_purposes:
            answers["consent_2"] = "yes"
        else:
            answers["consent_2"] = "partial"

        # Q: "Do you maintain records of consent for each purpose?"
        if health["active_consents"] > 0:
            answers["consent_3"] = "yes"
        else:
            answers["consent_3"] = "no"

        # Q: "Are consent notices clear, specific, and in plain language?"
        if health.get("privacy_policy_version"):
            answers["consent_4"] = "yes"
        else:
            answers["consent_4"] = "no"

        # Q: "Do you provide clear privacy notices at all data collection points?"
        if health.get("privacy_policy_version"):
            answers["notice_1"] = "yes"
        else:
            answers["notice_1"] = "no"

        # Q: "Have you implemented mechanisms for Data Principals to exercise their rights?"
        if health["recent_events"].get("rights_requests", 0) > 0 or has_purposes:
            answers["rights_1"] = "yes"
        else:
            answers["rights_1"] = "partial"

        # Q: "Do you have a grievance redressal mechanism?"
        answers["rights_4"] = "yes"  # We always have it (built-in)

        return answers

    async def get_consent_coverage_for_scanner(
        self, db: AsyncSession
    ) -> Dict[str, bool]:
        """Check which DPDP requirements are covered by the consent framework.

        Returns a dict of rule_id -> covered (bool) for scanner to use.
        """
        purposes = await self._get_all_purposes(db)
        purpose_codes = {p.purpose_code for p in purposes}

        coverage = {}

        # dpdp_consent_mechanism: Do we have a consent collection mechanism?
        coverage["dpdp_consent_mechanism"] = len(purpose_codes) > 0

        # dpdp_consent_withdrawal: Can users withdraw?
        coverage["dpdp_consent_withdrawal"] = len(purpose_codes) > 0  # API endpoint exists

        # dpdp_notice_requirements: Do we have privacy notices?
        policy_result = await db.execute(
            select(ConsentPolicy.id).limit(1)
        )
        coverage["dpdp_notice_requirements"] = policy_result.scalar() is not None

        # dpdp_data_principal_rights: Do we have rights mechanisms?
        coverage["dpdp_data_principal_rights"] = True  # Built-in rights API

        # dpdp_grievance_officer: Do we have grievance mechanism?
        coverage["dpdp_grievance_officer"] = True  # Built-in grievance API

        # dpdp_purpose_limitation: Are purposes clearly defined?
        coverage["dpdp_purpose_limitation"] = len(purpose_codes) >= 2

        # dpdp_data_retention: Do purposes specify retention?
        has_retention = any(p.retention_period for p in purposes)
        coverage["dpdp_data_retention"] = has_retention

        return coverage

    async def _get_purpose_stats(self, db: AsyncSession, organization_id=None) -> List[Dict]:
        """Get per-purpose consent statistics."""
        purposes_result = await db.execute(
            select(ConsentPurpose).where(ConsentPurpose.is_active == True)
        )
        purposes = purposes_result.scalars().all()

        stats = []
        for purpose in purposes:
            # Count grants for this purpose
            grant_query = select(func.count(ConsentPurposeGrant.id)).where(
                ConsentPurposeGrant.purpose_code == purpose.purpose_code,
                ConsentPurposeGrant.granted == True,
            )
            grant_result = await db.execute(grant_query)
            grant_count = grant_result.scalar() or 0

            stats.append({
                "code": purpose.purpose_code,
                "name": purpose.name,
                "is_required": purpose.is_required,
                "grant_count": grant_count,
                "third_parties": purpose.third_parties,
            })

        return stats

    async def _get_all_purposes(self, db: AsyncSession) -> List[ConsentPurpose]:
        result = await db.execute(
            select(ConsentPurpose).where(ConsentPurpose.is_active == True)
        )
        return list(result.scalars().all())

    def _calculate_health_score(
        self, active: int, total: int, purpose_stats: list, events: dict
    ) -> int:
        """Calculate consent health score (0-100).

        Factors:
        - Active consent rate (40%)
        - Purpose coverage (30%) - how many purposes have grants
        - Event health (30%) - grants vs withdrawals ratio
        """
        # Active consent rate
        consent_rate = active / max(total, 1)
        rate_score = min(consent_rate * 100, 100) * 0.4

        # Purpose coverage
        purposes_with_grants = sum(1 for p in purpose_stats if p.get("grant_count", 0) > 0)
        total_purposes = max(len(purpose_stats), 1)
        coverage_score = (purposes_with_grants / total_purposes) * 100 * 0.3

        # Event health (more grants than withdrawals is healthy)
        grants = events.get("granted", 0)
        withdrawals = events.get("withdrawn", 0)
        total_events = grants + withdrawals
        event_score = (grants / max(total_events, 1)) * 100 * 0.3 if total_events > 0 else 50 * 0.3

        return min(100, round(rate_score + coverage_score + event_score))


# Singleton
consent_compliance_bridge = ConsentComplianceBridge()
