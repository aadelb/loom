"""SSE progress tracking for long-running tools.

Provides real-time progress streaming via Server-Sent Events (SSE).
Stores progress events in an async queue per job_id and serves them
via StreamingResponse with proper SSE formatting.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import AsyncGenerator

logger = logging.getLogger("loom.progress")


@dataclass(frozen=True)
class ProgressEvent:
    """Immutable progress event for a long-running job.

    Attributes:
        job_id: Unique job identifier
        stage: Current pipeline stage (e.g., "search", "fetch", "extract")
        percent: Progress percentage (0-100)
        message: Human-readable progress message
        timestamp: ISO 8601 timestamp when event was created
    """

    job_id: str
    stage: str
    percent: int
    message: str
    timestamp: str

    def to_sse_line(self) -> str:
        """Format as SSE event line.

        Returns:
            SSE-formatted line: `data: <json>\n\n`
        """
        import json

        data = {
            "job_id": self.job_id,
            "stage": self.stage,
            "percent": self.percent,
            "message": self.message,
            "timestamp": self.timestamp,
        }
        return f"data: {json.dumps(data)}\n\n"


class ProgressTracker:
    """Thread-safe progress tracker with per-job async queues.

    Uses asyncio.Queue for real-time event streaming. Each job_id
    maintains an independent queue so clients can subscribe to
    specific job progress via GET /progress/{job_id}.

    Attributes:
        _jobs: Dict mapping job_id -> asyncio.Queue of ProgressEvent
        _lock: asyncio.Lock for synchronizing access to _jobs
    """

    def __init__(self) -> None:
        """Initialize progress tracker with empty job dict."""
        self._jobs: dict[str, asyncio.Queue[ProgressEvent]] = {}
        self._lock = asyncio.Lock()

    async def report_progress(
        self,
        job_id: str,
        stage: str,
        percent: int,
        message: str,
    ) -> None:
        """Report progress for a job.

        Creates a ProgressEvent and enqueues it for streaming.
        Clamps percent to [0, 100].

        Args:
            job_id: Unique job identifier (created by caller or tool)
            stage: Current pipeline stage name
            percent: Progress percentage (0-100, auto-clamped)
            message: Human-readable progress message

        Raises:
            ValueError: If job_id is empty or stage is empty
        """
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")
        if not stage or not stage.strip():
            raise ValueError("stage cannot be empty")

        job_id = job_id.strip()
        stage = stage.strip()
        percent = max(0, min(100, percent))

        async with self._lock:
            if job_id not in self._jobs:
                self._jobs[job_id] = asyncio.Queue()

            queue = self._jobs[job_id]

        event = ProgressEvent(
            job_id=job_id,
            stage=stage,
            percent=percent,
            message=message,
            timestamp=datetime.now(UTC).isoformat(),
        )

        await queue.put(event)
        logger.debug(
            "progress_reported job_id=%s stage=%s percent=%d",
            job_id,
            stage,
            percent,
        )

    async def get_events(self, job_id: str) -> AsyncGenerator[ProgressEvent, None]:
        """Stream progress events for a job as async generator.

        Yields events from the job's queue indefinitely (blocks when empty).
        Useful for consuming all events from a job.

        Args:
            job_id: Unique job identifier

        Yields:
            ProgressEvent objects from the job's queue

        Raises:
            ValueError: If job_id is empty
        """
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        job_id = job_id.strip()

        async with self._lock:
            if job_id not in self._jobs:
                self._jobs[job_id] = asyncio.Queue()

            queue = self._jobs[job_id]

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                yield event
            except asyncio.TimeoutError:
                logger.debug("progress_stream_timeout job_id=%s", job_id)
                break

    async def sse_stream(self, job_id: str) -> AsyncGenerator[str, None]:
        """Stream progress events for a job as SSE-formatted lines.

        Yields SSE-formatted event strings suitable for StreamingResponse.
        Each line is formatted as: `data: <json>\n\n`

        Args:
            job_id: Unique job identifier

        Yields:
            SSE-formatted strings (one event per line)

        Raises:
            ValueError: If job_id is empty
        """
        async for event in self.get_events(job_id):
            yield event.to_sse_line()

    async def cleanup(self, job_id: str) -> None:
        """Clean up resources for a completed job.

        Removes the job's queue from the tracker. Safe to call
        multiple times.

        Args:
            job_id: Unique job identifier

        Raises:
            ValueError: If job_id is empty
        """
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        job_id = job_id.strip()

        async with self._lock:
            self._jobs.pop(job_id, None)

        logger.debug("progress_cleaned_up job_id=%s", job_id)

    async def list_jobs(self) -> list[str]:
        """List all active job IDs.

        Returns:
            List of job_id strings currently being tracked
        """
        async with self._lock:
            return list(self._jobs.keys())


# Global singleton instance
_progress_tracker: ProgressTracker | None = None


def get_progress_tracker() -> ProgressTracker:
    """Get or create the global progress tracker singleton.

    Returns:
        ProgressTracker instance
    """
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker


def create_job_id() -> str:
    """Generate a unique job ID.

    Returns:
        UUID4-based job ID string
    """
    return str(uuid.uuid4())
