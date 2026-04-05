"""
Breach Notification Service - DPDP Act 72-hour requirement.

ALL personal data breaches must be reported to the Data Protection Board
within 72 hours AND to affected Data Principals without delay.

Unlike GDPR (which only requires notification for high-risk breaches),
DPDP requires ALL breaches to be reported regardless of risk assessment.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.audit_log import log_audit_event

logger = logging.getLogger(__name__)

# 72-hour notification window per DPDP Act
BOARD_NOTIFICATION_DEADLINE_HOURS = 72


class BreachNotificationService:
    """Manage data breach notifications per DPDP Act requirements."""

    async def report_breach(
        self,
        db: AsyncSession,
        breach_type: str,
        description: str,
        affected_user_ids: List[uuid.UUID],
        discovered_at: Optional[datetime] = None,
        severity: str = "high",
    ) -> dict:
        """Initiate a breach notification workflow.

        Args:
            db: Database session
            breach_type: Type of breach (unauthorized_access, data_leak, system_compromise, etc.)
            description: Details of the breach
            affected_user_ids: List of affected user UUIDs
            discovered_at: When the breach was discovered (defaults to now)
            severity: low, medium, high, critical

        Returns:
            Breach report summary with notification deadlines.
        """
        now = datetime.now(timezone.utc)
        discovered = discovered_at or now
        board_deadline = discovered + timedelta(hours=BOARD_NOTIFICATION_DEADLINE_HOURS)
        breach_id = str(uuid.uuid4())

        logger.critical(
            "DATA BREACH REPORTED [%s]: type=%s, severity=%s, affected_users=%d, "
            "discovered=%s, board_deadline=%s",
            breach_id, breach_type, severity, len(affected_user_ids),
            discovered.isoformat(), board_deadline.isoformat(),
        )

        # Audit log the breach
        import json as _json
        await log_audit_event(
            db,
            action="data_breach_reported",
            resource_type="security",
            resource_name=f"breach-{breach_id}",
            status="critical",
            details=_json.dumps({
                "breach_id": breach_id,
                "breach_type": breach_type,
                "severity": severity,
                "affected_count": len(affected_user_ids),
                "board_deadline": board_deadline.isoformat(),
            }),
        )

        # Notify affected users
        notification_results = []
        for user_id in affected_user_ids:
            result = await self._notify_affected_user(db, user_id, breach_id, breach_type, description)
            notification_results.append(result)

        await db.commit()

        return {
            "breach_id": breach_id,
            "breach_type": breach_type,
            "severity": severity,
            "discovered_at": discovered.isoformat(),
            "board_notification_deadline": board_deadline.isoformat(),
            "hours_remaining": max(0, (board_deadline - now).total_seconds() / 3600),
            "affected_users_count": len(affected_user_ids),
            "notifications_sent": sum(1 for r in notification_results if r.get("sent")),
            "notifications_failed": sum(1 for r in notification_results if not r.get("sent")),
            "next_steps": [
                f"1. Notify Data Protection Board within {BOARD_NOTIFICATION_DEADLINE_HOURS} hours (deadline: {board_deadline.isoformat()})",
                "2. Include: nature of breach, categories of data affected, approximate number of subjects, contact details of DPO",
                "3. Describe measures taken or proposed to address the breach",
                "4. Describe possible consequences of the breach",
            ],
        }

    async def _notify_affected_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        breach_id: str,
        breach_type: str,
        description: str,
    ) -> dict:
        """Send breach notification to an affected user."""
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar()
            if not user:
                return {"user_id": str(user_id), "sent": False, "reason": "user_not_found"}

            # Try to send email notification
            try:
                from app.services.email_service import send_breach_notification_email
                await send_breach_notification_email(
                    to_email=user.email,
                    user_name=user.name,
                    breach_id=breach_id,
                    breach_type=breach_type,
                    description=description,
                )
                return {"user_id": str(user_id), "sent": True, "method": "email"}
            except ImportError:
                # Email service not available
                logger.warning(
                    "Email service not available for breach notification to user %s",
                    user_id,
                )
                return {"user_id": str(user_id), "sent": False, "reason": "email_service_unavailable"}
            except Exception as e:
                logger.error("Breach notification email failed for user %s: %s", user_id, e)
                return {"user_id": str(user_id), "sent": False, "reason": str(e)}

        except Exception as e:
            logger.error("Failed to notify user %s of breach: %s", user_id, e)
            return {"user_id": str(user_id), "sent": False, "reason": str(e)}


# Singleton
breach_notification_service = BreachNotificationService()
