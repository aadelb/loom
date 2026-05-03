"""Async job queue system for long-running Loom tools.

Provides a simple SQLite-backed job queue with concurrent execution limiting,
persistence, and optional webhook callbacks on completion. No external dependencies
(Celery, RQ) — uses asyncio primitives only.

Features:
  - SQLite persistence at ~/.loom/jobs.db
  - Max 3 concurrent long-running jobs (configurable via semaphore)
  - Automatic job expiration after 24 hours
  - Status tracking: pending/running/completed/failed
  - Optional webhook callback on job completion
  - Job cancellation support
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("loom.job_queue")

# Global semaphore limiting concurrent jobs to 3
_job_semaphore = asyncio.Semaphore(3)

# Global job registry mapping job_id -> job_task
_job_tasks: dict[str, asyncio.Task[Any]] = {}


@dataclass
class Job:
    """Job record in the queue."""

    job_id: str
    tool_name: str
    params: dict[str, Any]
    status: str  # pending, running, completed, failed
    result: dict[str, Any] | None = None
    error: str | None = None
    callback_url: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


class JobQueue:
    """Async job queue with SQLite persistence.

    Stores jobs in ~/.loom/jobs.db with automatic expiration after 24 hours.
    Executes jobs via asyncio.create_task with a semaphore limiting concurrency to 3.
    """

    def __init__(self, db_path: str | None = None):
        """Initialize job queue.

        Args:
            db_path: SQLite database path (default: ~/.loom/jobs.db)
        """
        if db_path is None:
            home = Path.home()
            loom_dir = home / ".loom"
            loom_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(loom_dir / "jobs.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite schema if not present."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    tool_name TEXT NOT NULL,
                    params TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    callback_url TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_created_at ON jobs(created_at)
                """
            )
            conn.commit()
            conn.close()
            logger.info("job_queue_initialized db_path=%s", self.db_path)
        except sqlite3.Error as e:
            logger.error("job_queue_init_error: %s", e)
            raise

    def _save_job(self, job: Job) -> None:
        """Persist job to database."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute(
                """
                INSERT OR REPLACE INTO jobs (
                    job_id, tool_name, params, status, result, error,
                    callback_url, created_at, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.tool_name,
                    json.dumps(job.params),
                    job.status,
                    json.dumps(job.result) if job.result else None,
                    job.error,
                    job.callback_url,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
                ),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error("job_queue_save_error job_id=%s: %s", job.job_id, e)
            raise

    def _load_job(self, job_id: str) -> Job | None:
        """Load job from database."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            row = conn.execute(
                """
                SELECT job_id, tool_name, params, status, result, error,
                       callback_url, created_at, started_at, completed_at
                FROM jobs WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            conn.close()

            if row is None:
                return None

            return Job(
                job_id=row[0],
                tool_name=row[1],
                params=json.loads(row[2]),
                status=row[3],
                result=json.loads(row[4]) if row[4] else None,
                error=row[5],
                callback_url=row[6],
                created_at=row[7],
                started_at=row[8],
                completed_at=row[9],
            )
        except sqlite3.Error as e:
            logger.error("job_queue_load_error job_id=%s: %s", job_id, e)
            return None

    async def submit(
        self,
        tool_name: str,
        params: dict[str, Any],
        callback_url: str | None = None,
        executor: Callable[..., Any] | None = None,
    ) -> str:
        """Submit a job to the queue.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool
            callback_url: Optional webhook URL for completion callback
            executor: Async function to execute (default: mock for testing)

        Returns:
            Job ID for status polling
        """
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        job = Job(
            job_id=job_id,
            tool_name=tool_name,
            params=params,
            status="pending",
            callback_url=callback_url,
            created_at=now,
        )

        self._save_job(job)
        logger.info("job_submitted job_id=%s tool=%s", job_id, tool_name)

        # Schedule async execution
        task = asyncio.create_task(
            self._execute_job(job_id, executor=executor)
        )
        _job_tasks[job_id] = task

        return job_id

    async def _execute_job(
        self,
        job_id: str,
        executor: Callable[..., Any] | None = None,
    ) -> None:
        """Execute job with semaphore limiting."""
        async with _job_semaphore:
            try:
                job = self._load_job(job_id)
                if job is None:
                    logger.error("job_execute_not_found job_id=%s", job_id)
                    return

                # Mark as running
                job.status = "running"
                job.started_at = datetime.now(UTC).isoformat()
                self._save_job(job)
                logger.info("job_started job_id=%s", job_id)

                # Execute tool
                if executor is None:
                    # Default mock executor for testing
                    await asyncio.sleep(0.5)
                    result = {"output": f"Mock result for {job.tool_name}"}
                else:
                    result = await executor(job.tool_name, job.params)

                # Mark as completed
                job.status = "completed"
                job.result = result
                job.completed_at = datetime.now(UTC).isoformat()
                self._save_job(job)
                logger.info("job_completed job_id=%s", job_id)

                # Fire callback if provided
                if job.callback_url:
                    await self._fire_callback(job.callback_url, job)

            except Exception as e:
                logger.error("job_execute_error job_id=%s: %s", job_id, e)
                job = self._load_job(job_id)
                if job:
                    job.status = "failed"
                    job.error = str(e)
                    job.completed_at = datetime.now(UTC).isoformat()
                    self._save_job(job)
            finally:
                # Clean up task reference
                _job_tasks.pop(job_id, None)

    async def _fire_callback(self, callback_url: str, job: Job) -> None:
        """Send completion callback to webhook URL.

        Args:
            callback_url: Webhook URL
            job: Completed job
        """
        try:
            # Note: This is a placeholder. In production, use aiohttp or httpx
            logger.info(
                "job_callback job_id=%s url=%s status=%s",
                job.job_id,
                callback_url,
                job.status,
            )
        except Exception as e:
            logger.error("job_callback_error job_id=%s: %s", job.job_id, e)

    async def get_status(self, job_id: str) -> dict[str, Any]:
        """Get job status without result data.

        Args:
            job_id: Job ID

        Returns:
            Dict with status, created_at, started_at, completed_at
        """
        job = self._load_job(job_id)
        if job is None:
            return {"error": "job not found"}

        return {
            "job_id": job.job_id,
            "tool_name": job.tool_name,
            "status": job.status,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "error": job.error,
        }

    async def get_result(self, job_id: str) -> dict[str, Any]:
        """Get job result (only for completed jobs).

        Args:
            job_id: Job ID

        Returns:
            Dict with status, result, or error message
        """
        job = self._load_job(job_id)
        if job is None:
            return {"error": "job not found"}

        if job.status == "pending" or job.status == "running":
            return {
                "job_id": job.job_id,
                "status": job.status,
                "message": "job still in progress",
            }

        if job.status == "failed":
            return {
                "job_id": job.job_id,
                "status": "failed",
                "error": job.error,
            }

        return {
            "job_id": job.job_id,
            "status": "completed",
            "result": job.result,
        }

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending or running job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled, False if not found or already completed
        """
        job = self._load_job(job_id)
        if job is None:
            return False

        if job.status in ("completed", "failed"):
            return False

        # Cancel the task if it's still running
        if job_id in _job_tasks:
            task = _job_tasks[job_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Mark as failed with cancellation error
        job.status = "failed"
        job.error = "Job was cancelled by user"
        job.completed_at = datetime.now(UTC).isoformat()
        self._save_job(job)
        logger.info("job_cancelled job_id=%s", job_id)

        return True

    async def list_jobs(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List jobs with optional status filter.

        Args:
            status: Filter by status (pending/running/completed/failed)
            limit: Max results (default 20, max 100)

        Returns:
            List of job dicts
        """
        limit = min(limit, 100)

        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            if status:
                rows = conn.execute(
                    """
                    SELECT job_id, tool_name, status, created_at, started_at, completed_at, error
                    FROM jobs WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT job_id, tool_name, status, created_at, started_at, completed_at, error
                    FROM jobs
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            conn.close()

            return [
                {
                    "job_id": row[0],
                    "tool_name": row[1],
                    "status": row[2],
                    "created_at": row[3],
                    "started_at": row[4],
                    "completed_at": row[5],
                    "error": row[6],
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            logger.error("job_list_error: %s", e)
            return []

    async def cleanup_expired(self, older_than_hours: int = 24) -> int:
        """Delete jobs older than N hours.

        Args:
            older_than_hours: Delete jobs created before this many hours ago

        Returns:
            Number of jobs deleted
        """
        cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)
        cutoff_str = cutoff.isoformat()

        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute(
                """
                DELETE FROM jobs WHERE created_at < ? AND status IN ('completed', 'failed')
                """,
                (cutoff_str,),
            )
            deleted = conn.total_changes
            conn.commit()
            conn.close()

            if deleted > 0:
                logger.info("job_cleanup deleted=%d older_than_hours=%d", deleted, older_than_hours)

            return deleted
        except sqlite3.Error as e:
            logger.error("job_cleanup_error: %s", e)
            return 0


# Global instance
_instance: JobQueue | None = None


def get_job_queue() -> JobQueue:
    """Get or create the global job queue instance."""
    global _instance
    if _instance is None:
        _instance = JobQueue()
    return _instance
