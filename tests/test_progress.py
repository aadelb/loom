"""Unit tests for SSE progress tracking system."""

from __future__ import annotations

import asyncio
import pytest

from loom.progress import (
    ProgressEvent,
    ProgressTracker,
    create_job_id,
    get_progress_tracker,
)


class TestProgressEvent:
    """Test ProgressEvent dataclass."""

    def test_event_creation(self) -> None:
        """Test creating a ProgressEvent."""
        event = ProgressEvent(
            job_id="job-123",
            stage="search",
            percent=50,
            message="Searching...",
            timestamp="2025-05-04T10:00:00+00:00",
        )
        assert event.job_id == "job-123"
        assert event.stage == "search"
        assert event.percent == 50
        assert event.message == "Searching..."

    def test_event_immutable(self) -> None:
        """Test that ProgressEvent is immutable."""
        event = ProgressEvent(
            job_id="job-123",
            stage="search",
            percent=50,
            message="Searching...",
            timestamp="2025-05-04T10:00:00+00:00",
        )
        with pytest.raises(AttributeError):
            event.percent = 60

    def test_event_to_sse_line(self) -> None:
        """Test SSE line formatting."""
        event = ProgressEvent(
            job_id="job-123",
            stage="search",
            percent=50,
            message="Searching...",
            timestamp="2025-05-04T10:00:00+00:00",
        )
        sse_line = event.to_sse_line()
        assert sse_line.startswith("data: ")
        assert "job-123" in sse_line
        assert "search" in sse_line
        assert sse_line.endswith("\n\n")


class TestProgressTracker:
    """Test ProgressTracker class."""

    @pytest.mark.asyncio
    async def test_report_progress(self) -> None:
        """Test reporting progress."""
        tracker = ProgressTracker()
        await tracker.report_progress(
            job_id="job-123",
            stage="search",
            percent=50,
            message="Searching...",
        )
        # Should not raise

    @pytest.mark.asyncio
    async def test_report_progress_invalid_job_id(self) -> None:
        """Test that empty job_id raises ValueError."""
        tracker = ProgressTracker()
        with pytest.raises(ValueError, match="job_id cannot be empty"):
            await tracker.report_progress(
                job_id="",
                stage="search",
                percent=50,
                message="Searching...",
            )

    @pytest.mark.asyncio
    async def test_report_progress_invalid_stage(self) -> None:
        """Test that empty stage raises ValueError."""
        tracker = ProgressTracker()
        with pytest.raises(ValueError, match="stage cannot be empty"):
            await tracker.report_progress(
                job_id="job-123",
                stage="",
                percent=50,
                message="Searching...",
            )

    @pytest.mark.asyncio
    async def test_percent_clamping(self) -> None:
        """Test that percent is clamped to [0, 100]."""
        tracker = ProgressTracker()

        # Test clamping at bottom
        await tracker.report_progress(
            job_id="job-123",
            stage="search",
            percent=-50,
            message="Searching...",
        )

        # Test clamping at top
        await tracker.report_progress(
            job_id="job-123",
            stage="search",
            percent=150,
            message="Searching...",
        )

    @pytest.mark.asyncio
    async def test_get_events(self) -> None:
        """Test streaming events from queue."""
        tracker = ProgressTracker()
        job_id = "job-123"

        # Report some events
        await tracker.report_progress(job_id, "stage1", 10, "msg1")
        await tracker.report_progress(job_id, "stage2", 50, "msg2")

        # Collect events with timeout
        events = []

        async def collect_events() -> None:
            async for event in tracker.get_events(job_id):
                events.append(event)
                if len(events) >= 2:
                    break

        await asyncio.wait_for(collect_events(), timeout=2)
        assert len(events) == 2
        assert events[0].stage == "stage1"
        assert events[1].stage == "stage2"

    @pytest.mark.asyncio
    async def test_sse_stream(self) -> None:
        """Test SSE stream formatting."""
        tracker = ProgressTracker()
        job_id = "job-123"

        # Report events
        await tracker.report_progress(job_id, "search", 50, "Searching...")

        # Collect SSE lines with timeout
        sse_lines = []

        async def collect_sse() -> None:
            async for line in tracker.sse_stream(job_id):
                sse_lines.append(line)
                if len(sse_lines) >= 1:
                    break

        await asyncio.wait_for(collect_sse(), timeout=2)
        assert len(sse_lines) == 1
        assert sse_lines[0].startswith("data: ")
        assert "\n\n" in sse_lines[0]

    @pytest.mark.asyncio
    async def test_cleanup(self) -> None:
        """Test cleanup of job tracker."""
        tracker = ProgressTracker()
        job_id = "job-123"

        # Report event
        await tracker.report_progress(job_id, "search", 50, "msg")

        # Verify job exists
        jobs = await tracker.list_jobs()
        assert job_id in jobs

        # Clean up
        await tracker.cleanup(job_id)

        # Verify job is removed
        jobs = await tracker.list_jobs()
        assert job_id not in jobs

    @pytest.mark.asyncio
    async def test_list_jobs(self) -> None:
        """Test listing active jobs."""
        tracker = ProgressTracker()

        # Report for multiple jobs
        await tracker.report_progress("job-1", "search", 50, "msg")
        await tracker.report_progress("job-2", "fetch", 75, "msg")

        # List jobs
        jobs = await tracker.list_jobs()
        assert "job-1" in jobs
        assert "job-2" in jobs
        assert len(jobs) >= 2


class TestProgressSingleton:
    """Test progress tracker singleton."""

    def test_singleton_instance(self) -> None:
        """Test that get_progress_tracker returns singleton."""
        tracker1 = get_progress_tracker()
        tracker2 = get_progress_tracker()
        assert tracker1 is tracker2


class TestJobIdGeneration:
    """Test job ID generation."""

    def test_create_job_id(self) -> None:
        """Test that create_job_id generates unique IDs."""
        id1 = create_job_id()
        id2 = create_job_id()
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0


@pytest.mark.asyncio
async def test_end_to_end() -> None:
    """End-to-end test of progress tracking."""
    tracker = ProgressTracker()
    job_id = "job-test-e2e"

    # Simulate a pipeline
    stages = [
        ("initialize", 0),
        ("search", 20),
        ("fetch", 50),
        ("extract", 80),
        ("complete", 100),
    ]

    # Report progress in background
    async def report_stages() -> None:
        for stage, percent in stages:
            await tracker.report_progress(
                job_id=job_id,
                stage=stage,
                percent=percent,
                message=f"Running {stage} stage",
            )
            await asyncio.sleep(0.1)

    # Collect events
    collected_events = []

    async def collect_all() -> None:
        async for event in tracker.get_events(job_id):
            collected_events.append(event)
            if len(collected_events) >= len(stages):
                break

    # Run both concurrently
    await asyncio.gather(
        report_stages(),
        collect_all(),
        return_exceptions=False,
    )

    # Verify
    assert len(collected_events) == len(stages)
    assert collected_events[0].stage == "initialize"
    assert collected_events[-1].stage == "complete"
    assert collected_events[-1].percent == 100
