"""
Consent Event Bus - Event-driven consent change propagation.

Uses Redis Streams when available, falls back to no-op (events are
already recorded in consent_events table regardless).

CloudEvents-compatible event schema for interoperability.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)


class ConsentEventBus:
    """Publish consent events for downstream consumers.

    Events are published to Redis Streams when available.
    The consent_events table serves as the durable store regardless.
    """

    def __init__(self):
        self._redis = None
        self._stream_key = "contrared:consent:events"
        self._handlers: List[Callable] = []

    async def connect(self, redis_client) -> bool:
        """Connect to Redis for event streaming."""
        self._redis = redis_client
        if self._redis:
            logger.info("Consent event bus connected to Redis Streams")
            return True
        return False

    async def publish(
        self,
        event_type: str,
        subject_id: str,
        data: dict,
        consent_record_id: Optional[str] = None,
    ) -> None:
        """Publish a consent event.

        Args:
            event_type: e.g. 'consent.granted', 'consent.withdrawn'
            subject_id: UUID of the data principal
            data: Event payload
            consent_record_id: Associated consent record UUID
        """
        event = {
            "specversion": "1.0",
            "type": event_type,
            "source": "/consent-service",
            "id": str(uuid.uuid4()),
            "time": datetime.now(timezone.utc).isoformat(),
            "subject": subject_id,
            "datacontenttype": "application/json",
            "data": json.dumps(data),
        }
        if consent_record_id:
            event["consent_record_id"] = consent_record_id

        # Publish to Redis Stream if available
        if self._redis:
            try:
                await self._redis.xadd(
                    self._stream_key,
                    event,
                    maxlen=10000,  # Keep last 10K events
                )
            except Exception as e:
                logger.warning("Redis Stream publish failed (non-fatal): %s", e)

        # Execute registered handlers
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error("Event handler failed: %s", e)

    def on(self, handler: Callable) -> None:
        """Register an event handler."""
        self._handlers.append(handler)

    async def publish_consent_granted(
        self, subject_id: str, purposes: List[str], consent_record_id: str
    ):
        await self.publish(
            "consent.granted", subject_id,
            {"purposes": purposes, "consent_record_id": consent_record_id},
            consent_record_id,
        )

    async def publish_consent_withdrawn(
        self, subject_id: str, purposes: List[str], consent_record_id: str
    ):
        await self.publish(
            "consent.withdrawn", subject_id,
            {"purposes": purposes, "consent_record_id": consent_record_id, "effective_immediately": True},
            consent_record_id,
        )

    async def publish_rights_request(
        self, subject_id: str, request_type: str, request_id: str
    ):
        await self.publish(
            "rights.request.submitted", subject_id,
            {"request_type": request_type, "request_id": request_id},
        )

    async def publish_grievance(
        self, subject_id: str, category: str, grievance_id: str
    ):
        await self.publish(
            "grievance.submitted", subject_id,
            {"category": category, "grievance_id": grievance_id},
        )


# Singleton
consent_event_bus = ConsentEventBus()
