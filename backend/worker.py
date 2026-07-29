"""
Background worker process for async contract analysis.

Drains the Redis-backed task queue and runs the analysis pipeline
for each job. Designed to run as a separate process alongside the
web server (e.g. a second Render service or a separate Procfile entry).

Usage:
    python worker.py

Configuration:
    REDIS_URL      — Redis connection string (required for worker mode)
    WORKER_POLL_INTERVAL — seconds between queue polls (default: 2)
    WORKER_MAX_JOBS      — max concurrent jobs (default: 3)

If Redis is unavailable, the worker exits after a grace period.
"""

import asyncio
import logging
import os
import signal
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("contrared.worker")

POLL_INTERVAL = int(os.environ.get("WORKER_POLL_INTERVAL", "2"))
MAX_CONCURRENT = int(os.environ.get("WORKER_MAX_JOBS", "3"))

# Graceful shutdown flag
_shutdown = asyncio.Event()


def _handle_signal(sig, _frame):
    logger.info("Received %s — shutting down gracefully", signal.Signals(sig).name)
    _shutdown.set()


async def process_job(job_id: str) -> None:
    """Fetch job data from Redis, run the analysis pipeline, update status."""
    from app.workers.tasks import task_queue, JobStatus

    logger.info("Processing job %s", job_id)
    try:
        job_data = await task_queue.get_job_status(job_id)
        if not job_data:
            logger.warning("Job %s not found in Redis — skipping", job_id)
            return

        if job_data.get("status") != JobStatus.QUEUED.value:
            logger.info("Job %s is %s — skipping", job_id, job_data.get("status"))
            return

        await task_queue.update_job_status(job_id, JobStatus.RUNNING)

        # Reconstruct the job
        from app.workers.tasks import AnalysisJob, _load_phase6_data
        job = AnalysisJob.from_dict(job_data)
        job.contract_text = await task_queue.get_contract_text(job_id)
        if not job.contract_text:
            raise ValueError(
                "Queued contract payload is missing or expired; resubmit the job."
            )

        # Build deal context + load Phase 6 data so the worker has parity
        # with the sync /analyze surface.
        from app.services.playbook_conditions_engine import DealContext
        from app.db.session import AsyncSessionLocal
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
                        await _load_phase6_data(db, job.playbook_id, job.tier_preference)
                    )
            except Exception as exc:
                raise RuntimeError(
                    "Playbook conditions, dependencies, or tiers could not "
                    "be loaded."
                ) from exc

        # Run the analysis pipeline
        from app.services.analysis_pipeline import analysis_pipeline
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
        from app.workers.tasks import attach_compliance_scores
        attach_compliance_scores(job, result, result_dict)
        await task_queue.store_job_result(job_id, result_dict)
        from app.workers.tasks import _persist_document_job_result
        await _persist_document_job_result(job.document_id, result_dict)
        await task_queue.update_job_status(job_id, JobStatus.COMPLETED)
        await task_queue.delete_contract_text(job_id)
        logger.info("Job %s completed: %d risks found", job_id, len(result.redlines))

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, e, exc_info=True)
        from app.workers.tasks import (
            _persist_document_job_result,
            task_queue,
            JobStatus,
        )
        if "job" in locals():
            await _persist_document_job_result(
                job.document_id, None, error=str(e)
            )
        await task_queue.update_job_status(job_id, JobStatus.FAILED, str(e))
        await task_queue.delete_contract_text(job_id)


async def worker_loop() -> None:
    """Main worker loop — polls Redis queue and processes jobs."""
    from app.workers.tasks import task_queue

    # Wait for Redis connection
    redis = await task_queue._get_redis()
    if not redis:
        logger.error("Redis is not available. Worker requires Redis to operate.")
        logger.info("Set REDIS_URL environment variable and restart.")
        return

    logger.info(
        "Worker started — polling every %ds, max %d concurrent jobs",
        POLL_INTERVAL, MAX_CONCURRENT,
    )

    active_tasks: set = set()

    while not _shutdown.is_set():
        try:
            # Clean up completed tasks
            done = {t for t in active_tasks if t.done()}
            for t in done:
                if t.exception():
                    logger.error("Task failed: %s", t.exception())
            active_tasks -= done

            # Only fetch new jobs if under capacity
            if len(active_tasks) < MAX_CONCURRENT:
                # BRPOP with 1s timeout (non-blocking enough for shutdown checks)
                result = await redis.brpop(task_queue._queue_key, timeout=1)
                if result:
                    _, job_id_raw = result
                    job_id = job_id_raw.decode() if isinstance(job_id_raw, bytes) else job_id_raw
                    task = asyncio.create_task(process_job(job_id))
                    active_tasks.add(task)
                else:
                    # No job available — wait before next poll
                    await asyncio.sleep(POLL_INTERVAL)
            else:
                # At capacity — wait for a slot
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Worker loop error: %s", e, exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)

    # Wait for in-flight jobs to finish (up to 30s)
    if active_tasks:
        logger.info("Waiting for %d in-flight jobs to complete...", len(active_tasks))
        done, pending = await asyncio.wait(active_tasks, timeout=30)
        if pending:
            logger.warning("Cancelling %d jobs that didn't finish in time", len(pending))
            for t in pending:
                t.cancel()

    logger.info("Worker shut down cleanly.")


def main():
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("ContraRed Analysis Worker starting...")
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
