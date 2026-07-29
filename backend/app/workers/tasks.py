"""
Background task definitions for async contract analysis.

Phase 2.3: Async Processing — contracts are analyzed in background workers
so the API can return 202 Accepted immediately with a job_id.

Architecture:
  - API endpoint receives analysis request → creates job → returns 202 + job_id
  - Worker picks up job → runs analysis pipeline → stores results
  - Frontend polls GET /documents/{id}/status until completed

When Redis is not available (graceful degradation):
  - Falls back to in-process async execution (current behavior)
  - No queueing, but still non-blocking via asyncio

When Redis IS available:
  - Uses a simple task queue backed by Redis lists
  - Worker process polls for new jobs
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AnalysisJob:
    """Represents a queued analysis job."""
    job_id: str
    document_id: str
    user_id: str
    organization_id: Optional[str] = None
    contract_text: str = ""
    playbook_id: Optional[str] = None
    playbook_name: str = "Default"
    playbook_rules: List[Dict] = field(default_factory=list)
    # Scan-time inputs (parity with /analyze sync path)
    party_side: str = "neutral"
    jurisdiction: Optional[str] = None
    compliance_layers: List[str] = field(default_factory=list)
    tier_preference: str = "ideal"
    counterparty_type: Optional[str] = None
    deal_size: Optional[float] = None
    contract_side: Optional[str] = None
    status: JobStatus = JobStatus.QUEUED
    created_at: str = ""
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "playbook_id": self.playbook_id,
            "playbook_name": self.playbook_name,
            "playbook_rules": self.playbook_rules,
            "party_side": self.party_side,
            "jurisdiction": self.jurisdiction,
            "compliance_layers": self.compliance_layers,
            "tier_preference": self.tier_preference,
            "counterparty_type": self.counterparty_type,
            "deal_size": self.deal_size,
            "contract_side": self.contract_side,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisJob":
        return cls(
            job_id=data["job_id"],
            document_id=data["document_id"],
            user_id=data["user_id"],
            organization_id=data.get("organization_id"),
            contract_text=data.get("contract_text", ""),
            playbook_id=data.get("playbook_id"),
            playbook_name=data.get("playbook_name", "Default"),
            playbook_rules=data.get("playbook_rules", []),
            party_side=data.get("party_side") or "neutral",
            jurisdiction=data.get("jurisdiction"),
            compliance_layers=data.get("compliance_layers", []),
            tier_preference=data.get("tier_preference", "ideal"),
            counterparty_type=data.get("counterparty_type"),
            deal_size=data.get("deal_size"),
            contract_side=data.get("contract_side"),
            status=JobStatus(data.get("status", "queued")),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
            error=data.get("error"),
            result=data.get("result"),
        )


class TaskQueue:
    """
    Simple Redis-backed task queue for background analysis.

    Falls back to in-process execution when Redis is unavailable.
    """

    def __init__(self):
        self._redis = None
        self._in_memory_jobs: Dict[str, AnalysisJob] = {}
        self._queue_key = "contrared:analysis_queue"
        self._jobs_key = "contrared:jobs"

    async def _get_redis(self):
        """Lazy Redis connection."""
        if self._redis is not None:
            return self._redis
        try:
            from app.services.cache_service import get_cache
            cache = await get_cache()
            if cache.is_connected and hasattr(cache, '_redis'):
                self._redis = cache._redis
                return self._redis
        except Exception:
            pass
        return None

    @property
    def is_redis_available(self) -> bool:
        return self._redis is not None

    _text_key = "contrared:job_text"

    async def enqueue(self, job: AnalysisJob) -> str:
        """Add a job to the queue. Returns job_id."""
        job.created_at = datetime.now(timezone.utc).isoformat()

        redis = await self._get_redis()
        if redis:
            # Store job metadata
            await redis.hset(
                f"{self._jobs_key}:{job.job_id}",
                mapping={
                    key: json.dumps(value)
                    for key, value in job.to_dict().items()
                },
            )
            # Store contract text in a separate key with 1-hour TTL
            # (excluded from to_dict() for security, but worker needs it)
            if job.contract_text:
                await redis.set(
                    f"{self._text_key}:{job.job_id}",
                    job.contract_text,
                    ex=3600,
                )
            # Push to queue
            await redis.lpush(self._queue_key, job.job_id)
            logger.info("Job %s enqueued to Redis", job.job_id)
        else:
            # In-memory fallback
            self._in_memory_jobs[job.job_id] = job
            logger.info("Job %s stored in-memory (no Redis)", job.job_id)

        return job.job_id

    async def get_contract_text(self, job_id: str) -> str:
        """Retrieve contract text stored separately for a queued job."""
        redis = await self._get_redis()
        if redis:
            text = await redis.get(f"{self._text_key}:{job_id}")
            if text:
                return text.decode() if isinstance(text, bytes) else text
        # In-memory fallback
        job = self._in_memory_jobs.get(job_id)
        return job.contract_text if job else ""

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status by ID."""
        redis = await self._get_redis()
        if redis:
            data = await redis.hgetall(f"{self._jobs_key}:{job_id}")
            if data:
                # Decode Redis bytes
                decoded = {}
                for k, v in data.items():
                    key = k.decode() if isinstance(k, bytes) else k
                    val = v.decode() if isinstance(v, bytes) else v
                    try:
                        decoded[key] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        decoded[key] = val
                return decoded
            return None
        else:
            job = self._in_memory_jobs.get(job_id)
            return job.to_dict() if job else None

    async def update_job_status(
        self, job_id: str, status: JobStatus, error: Optional[str] = None
    ):
        """Update job status."""
        redis = await self._get_redis()
        updates = {"status": status.value}
        if status == JobStatus.COMPLETED:
            updates["completed_at"] = datetime.now(timezone.utc).isoformat()
        if error:
            updates["error"] = error

        if redis:
            await redis.hset(f"{self._jobs_key}:{job_id}", mapping=updates)
            # Set TTL (24 hours) for completed/failed jobs
            if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                await redis.expire(f"{self._jobs_key}:{job_id}", 86400)
        else:
            job = self._in_memory_jobs.get(job_id)
            if job:
                job.status = status
                if error:
                    job.error = error
                if status == JobStatus.COMPLETED:
                    job.completed_at = datetime.now(timezone.utc).isoformat()

    async def store_job_result(
        self, job_id: str, result: Dict[str, Any]
    ) -> None:
        """Store a pollable result for 24 hours without mixing it with input."""
        redis = await self._get_redis()
        if redis:
            key = f"{self._jobs_key}:{job_id}"
            await redis.hset(key, mapping={"result": json.dumps(result)})
            await redis.expire(key, 86400)
        else:
            job = self._in_memory_jobs.get(job_id)
            if job:
                job.result = result

    async def delete_contract_text(self, job_id: str) -> None:
        """Delete the temporary input payload as soon as processing ends."""
        redis = await self._get_redis()
        if redis:
            await redis.delete(f"{self._text_key}:{job_id}")
        job = self._in_memory_jobs.get(job_id)
        if job:
            job.contract_text = ""

    async def run_analysis_inline(self, job: AnalysisJob) -> Dict[str, Any]:
        """
        Run analysis inline (non-queued fallback).

        Used when Redis is unavailable. Runs the pipeline in the current
        process but still returns immediately via asyncio.create_task().
        Loads Phase-6 data (conditions, dependencies, tiers) from a fresh
        DB session so the async path matches the sync /analyze surface.
        """
        from app.services.analysis_pipeline import analysis_pipeline
        from app.services.playbook_conditions_engine import DealContext
        from app.db.session import AsyncSessionLocal

        await self.update_job_status(job.job_id, JobStatus.RUNNING)
        try:
            deal_context = DealContext(
                counterparty_type=job.counterparty_type,
                deal_size=job.deal_size,
                jurisdiction=job.jurisdiction,
                contract_side=job.contract_side,
            )

            playbook_conditions = None
            playbook_dependencies = None
            rule_tiers_by_rule = None
            if job.playbook_id:
                try:
                    async with AsyncSessionLocal() as db:
                        playbook_conditions, playbook_dependencies, rule_tiers_by_rule = (
                            await _load_phase6_data(
                                db, job.playbook_id, job.tier_preference
                            )
                        )
                except Exception as exc:
                    raise RuntimeError(
                        "Playbook conditions, dependencies, or tiers could "
                        "not be loaded."
                    ) from exc

            result = await analysis_pipeline.run(
                contract_text=job.contract_text,
                playbook_rules=job.playbook_rules,
                playbook_name=job.playbook_name,
                party_side=job.party_side,
                jurisdiction_override=job.jurisdiction,
                deal_context=deal_context,
                playbook_conditions=playbook_conditions,
                playbook_dependencies=playbook_dependencies,
                rule_tiers_by_rule=rule_tiers_by_rule,
                tier_preference=job.tier_preference,
            )
            result_dict = result.to_dict()
            attach_compliance_scores(job, result, result_dict)
            await self.store_job_result(job.job_id, result_dict)
            await _persist_document_job_result(job.document_id, result_dict)
            await self.update_job_status(job.job_id, JobStatus.COMPLETED)
            await self.delete_contract_text(job.job_id)
            return result_dict
        except Exception as e:
            logger.error("Inline analysis failed for job %s: %s", job.job_id, e)
            await self.update_job_status(job.job_id, JobStatus.FAILED, str(e))
            await _persist_document_job_result(
                job.document_id, None, error=str(e)
            )
            await self.delete_contract_text(job.job_id)
            return {"error": str(e)}


async def _persist_document_job_result(
    document_id: str,
    result: Optional[Dict[str, Any]],
    *,
    error: Optional[str] = None,
) -> None:
    """Keep the document dashboard consistent with the queue status."""
    from uuid import UUID

    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.document import Document, DocumentStatus

    try:
        async with AsyncSessionLocal() as db:
            query = select(Document).where(Document.id == UUID(document_id))
            document = (await db.execute(query)).scalar_one_or_none()
            if document is None:
                return
            if error:
                document.status = DocumentStatus.FAILED
            else:
                redlines = (result or {}).get("redlines", [])
                document.status = DocumentStatus.COMPLETED
                document.total_risks = len(redlines)
                document.risk_summary = {
                    "red": sum(
                        1 for item in redlines
                        if item.get("risk_level") == "RED"
                    ),
                    "yellow": sum(
                        1 for item in redlines
                        if item.get("risk_level") == "YELLOW"
                    ),
                    "green": sum(
                        1 for item in redlines
                        if item.get("risk_level") == "GREEN"
                    ),
                }
                document.processed_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception:
        logger.exception(
            "Failed to persist document status for async job document %s",
            document_id,
        )


def attach_compliance_scores(
    job: AnalysisJob,
    pipeline_result,
    result_dict: Dict[str, Any],
) -> None:
    """Add requested rule-ledger scores to async results.

    The synchronous endpoint already returns these scores. Keeping this logic
    beside the queue model gives both the in-process fallback and the external
    worker the same result contract.
    """
    if not job.compliance_layers:
        return
    from app.services.compliance_layer_service import (
        build_compliance_layer_score,
    )

    result_dict["compliance_scores"] = {
        layer_code: build_compliance_layer_score(
            layer_code,
            job.playbook_rules,
            pipeline_result,
        )
        for layer_code in job.compliance_layers
    }


async def _load_phase6_data(db, playbook_id: str, tier_preference: str):
    """Load PlaybookCondition + Dependency + Tier rows for the given playbook.

    Returns (conditions, dependencies, rule_tiers_by_rule). Mirrors the
    inline loader in /documents/analyze so the async + sync paths produce
    the same Phase 6 behavior.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from uuid import UUID
    from app.models.playbook import (
        PlaybookCondition, PlaybookRuleOverride,
        PlaybookRuleDependency, PlaybookRuleTier, PlaybookRule,
    )

    pb_uuid = UUID(playbook_id)
    cond_q = (
        select(PlaybookCondition)
        .where(
            PlaybookCondition.playbook_id == pb_uuid,
            PlaybookCondition.is_active == True,  # noqa: E712
        )
        .options(
            selectinload(PlaybookCondition.rule_overrides).selectinload(
                PlaybookRuleOverride.rule
            )
        )
        .order_by(PlaybookCondition.priority.desc())
    )
    conditions = list((await db.execute(cond_q)).scalars().all())

    dep_q = select(PlaybookRuleDependency).where(
        PlaybookRuleDependency.playbook_id == pb_uuid,
        PlaybookRuleDependency.is_active == True,  # noqa: E712
    )
    dependencies = list((await db.execute(dep_q)).scalars().all())

    tier_level_map = {"ideal": 1, "acceptable": 2, "walk_away": 3, "escalate": 4}
    target_tier_level = tier_level_map.get((tier_preference or "ideal").lower(), 1)
    rule_tiers_by_rule = None
    if target_tier_level != 1:
        tier_q = select(PlaybookRuleTier).where(
            PlaybookRuleTier.tier_level == target_tier_level,
            PlaybookRuleTier.rule_id.in_(
                select(PlaybookRule.id).where(PlaybookRule.playbook_id == pb_uuid)
            ),
        )
        tiers = list((await db.execute(tier_q)).scalars().all())
        rule_tiers_by_rule = {str(t.rule_id): t for t in tiers}

    return conditions, dependencies, rule_tiers_by_rule


# Singleton
task_queue = TaskQueue()
