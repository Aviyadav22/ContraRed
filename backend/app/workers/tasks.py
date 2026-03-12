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

import asyncio
import json
import logging
import uuid
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
    status: JobStatus = JobStatus.QUEUED
    created_at: str = ""
    completed_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "playbook_id": self.playbook_id,
            "playbook_name": self.playbook_name,
            "playbook_rules": self.playbook_rules,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
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
            status=JobStatus(data.get("status", "queued")),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
            error=data.get("error"),
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
                mapping={k: json.dumps(v) if isinstance(v, (list, dict)) else str(v) for k, v in job.to_dict().items()},
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

    async def run_analysis_inline(self, job: AnalysisJob) -> Dict[str, Any]:
        """
        Run analysis inline (non-queued fallback).

        Used when Redis is unavailable. Runs the pipeline in the current
        process but still returns immediately via asyncio.create_task().
        """
        from app.services.analysis_pipeline import analysis_pipeline

        await self.update_job_status(job.job_id, JobStatus.RUNNING)
        try:
            result = await analysis_pipeline.run(
                contract_text=job.contract_text,
                playbook_rules=job.playbook_rules,
                playbook_name=job.playbook_name,
            )
            await self.update_job_status(job.job_id, JobStatus.COMPLETED)
            return result.to_dict()
        except Exception as e:
            logger.error("Inline analysis failed for job %s: %s", job.job_id, e)
            await self.update_job_status(job.job_id, JobStatus.FAILED, str(e))
            return {"error": str(e)}


# Singleton
task_queue = TaskQueue()
