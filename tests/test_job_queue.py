"""Tests for the async job queue system."""

from __future__ import annotations

import asyncio
import json
import pytest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loom.job_queue import Job, JobQueue, get_job_queue
from loom.tools.job_tools import (
    research_job_submit,
    research_job_status,
    research_job_result,
    research_job_list,
    research_job_cancel,
)


@pytest.fixture
def job_queue_temp(tmp_path: Path) -> JobQueue:
    """Create a temporary job queue for testing."""
    db_path = str(tmp_path / "test_jobs.db")
    return JobQueue(db_path=db_path)


@pytest.mark.asyncio
class TestJobQueueCore:
    """Test core job queue functionality."""

    async def test_init_creates_database(self, job_queue_temp: JobQueue) -> None:
        """Test that initialization creates the database."""
        assert Path(job_queue_temp.db_path).exists()

    async def test_submit_returns_job_id(self, job_queue_temp: JobQueue) -> None:
        """Test that submit returns a UUID string."""
        job_id = await job_queue_temp.submit(
            tool_name="test_tool",
            params={"key": "value"}
        )
        assert job_id
        assert len(job_id) == 36  # UUID format
        assert "-" in job_id

    async def test_load_and_save_job(self, job_queue_temp: JobQueue) -> None:
        """Test that jobs can be saved and loaded."""
        job = Job(
            job_id="test-id-123",
            tool_name="test_tool",
            params={"key": "value"},
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
        )
        job_queue_temp._save_job(job)

        loaded = job_queue_temp._load_job("test-id-123")
        assert loaded is not None
        assert loaded.tool_name == "test_tool"
        assert loaded.params == {"key": "value"}
        assert loaded.status == "pending"

    async def test_get_status_pending(self, job_queue_temp: JobQueue) -> None:
        """Test get_status for pending job."""
        job_id = await job_queue_temp.submit(
            tool_name="test_tool",
            params={"key": "value"}
        )
        status = await job_queue_temp.get_status(job_id)

        assert status["job_id"] == job_id
        assert status["status"] == "pending"
        assert status["tool_name"] == "test_tool"
        assert status["error"] is None

    async def test_get_status_not_found(self, job_queue_temp: JobQueue) -> None:
        """Test get_status for non-existent job."""
        status = await job_queue_temp.get_status("non-existent-id")
        assert status["error"] == "job not found"

    async def test_get_result_pending_job(self, job_queue_temp: JobQueue) -> None:
        """Test get_result for pending job."""
        job_id = await job_queue_temp.submit(
            tool_name="test_tool",
            params={"key": "value"}
        )
        result = await job_queue_temp.get_result(job_id)

        assert result["status"] == "pending"
        assert "still in progress" in result.get("message", "")

    async def test_get_result_completed_job(self, job_queue_temp: JobQueue) -> None:
        """Test get_result for completed job."""
        job = Job(
            job_id="completed-123",
            tool_name="test_tool",
            params={"key": "value"},
            status="completed",
            result={"output": "test result"},
            created_at=datetime.now(UTC).isoformat(),
        )
        job_queue_temp._save_job(job)

        result = await job_queue_temp.get_result("completed-123")
        assert result["status"] == "completed"
        assert result["result"] == {"output": "test result"}

    async def test_get_result_failed_job(self, job_queue_temp: JobQueue) -> None:
        """Test get_result for failed job."""
        job = Job(
            job_id="failed-123",
            tool_name="test_tool",
            params={"key": "value"},
            status="failed",
            error="Test error message",
            created_at=datetime.now(UTC).isoformat(),
        )
        job_queue_temp._save_job(job)

        result = await job_queue_temp.get_result("failed-123")
        assert result["status"] == "failed"
        assert result["error"] == "Test error message"


@pytest.mark.asyncio
class TestJobQueueList:
    """Test job listing functionality."""

    async def test_list_jobs_empty(self, job_queue_temp: JobQueue) -> None:
        """Test listing jobs when queue is empty."""
        jobs = await job_queue_temp.list_jobs()
        assert jobs == []

    async def test_list_jobs_all_statuses(self, job_queue_temp: JobQueue) -> None:
        """Test listing jobs across all statuses."""
        # Create jobs with different statuses
        for i, status in enumerate(["pending", "running", "completed", "failed"]):
            job = Job(
                job_id=f"job-{i}",
                tool_name="test_tool",
                params={"key": f"value{i}"},
                status=status,
                created_at=datetime.now(UTC).isoformat(),
            )
            job_queue_temp._save_job(job)

        jobs = await job_queue_temp.list_jobs()
        assert len(jobs) == 4
        statuses = {job["status"] for job in jobs}
        assert statuses == {"pending", "running", "completed", "failed"}

    async def test_list_jobs_filter_by_status(self, job_queue_temp: JobQueue) -> None:
        """Test listing jobs filtered by status."""
        # Create jobs with different statuses
        for i, status in enumerate(["pending", "running", "completed"]):
            job = Job(
                job_id=f"job-{i}",
                tool_name="test_tool",
                params={"key": f"value{i}"},
                status=status,
                created_at=datetime.now(UTC).isoformat(),
            )
            job_queue_temp._save_job(job)

        # Filter by status
        jobs = await job_queue_temp.list_jobs(status="completed")
        assert len(jobs) == 1
        assert jobs[0]["status"] == "completed"

    async def test_list_jobs_limit(self, job_queue_temp: JobQueue) -> None:
        """Test listing jobs with limit."""
        # Create multiple jobs
        for i in range(30):
            job = Job(
                job_id=f"job-{i}",
                tool_name="test_tool",
                params={"key": f"value{i}"},
                status="pending",
                created_at=datetime.now(UTC).isoformat(),
            )
            job_queue_temp._save_job(job)

        # Test default limit (20)
        jobs = await job_queue_temp.list_jobs()
        assert len(jobs) == 20

        # Test custom limit
        jobs = await job_queue_temp.list_jobs(limit=10)
        assert len(jobs) == 10

        # Test max limit enforcement
        jobs = await job_queue_temp.list_jobs(limit=500)
        assert len(jobs) == 20  # Max 20 of 30


@pytest.mark.asyncio
class TestJobCancellation:
    """Test job cancellation functionality."""

    async def test_cancel_pending_job(self, job_queue_temp: JobQueue) -> None:
        """Test cancelling a pending job."""
        job_id = await job_queue_temp.submit(
            tool_name="test_tool",
            params={"key": "value"}
        )
        # Give it a moment to be saved
        await asyncio.sleep(0.1)

        success = await job_queue_temp.cancel(job_id)
        assert success is True

        # Check that job is marked as failed
        status = await job_queue_temp.get_status(job_id)
        assert status["status"] == "failed"
        assert "cancelled" in status["error"].lower()

    async def test_cancel_non_existent_job(self, job_queue_temp: JobQueue) -> None:
        """Test cancelling a non-existent job."""
        success = await job_queue_temp.cancel("non-existent-id")
        assert success is False

    async def test_cancel_completed_job(self, job_queue_temp: JobQueue) -> None:
        """Test that cancelling a completed job returns False."""
        job = Job(
            job_id="completed-123",
            tool_name="test_tool",
            params={"key": "value"},
            status="completed",
            result={"output": "test"},
            created_at=datetime.now(UTC).isoformat(),
        )
        job_queue_temp._save_job(job)

        success = await job_queue_temp.cancel("completed-123")
        assert success is False


@pytest.mark.asyncio
class TestJobCleanup:
    """Test job cleanup functionality."""

    async def test_cleanup_expired_jobs(self, job_queue_temp: JobQueue) -> None:
        """Test cleaning up expired jobs."""
        # Create old completed job (pretend it's 48 hours old)
        old_date = (datetime.now(UTC) - asyncio.sleep.__self__.__class__(hours=48)).isoformat() if False else None
        if not old_date:
            from datetime import timedelta
            old_date = (datetime.now(UTC) - timedelta(hours=48)).isoformat()

        job_old = Job(
            job_id="old-job",
            tool_name="test_tool",
            params={"key": "value"},
            status="completed",
            created_at=old_date,
        )
        job_queue_temp._save_job(job_old)

        # Create recent completed job
        job_new = Job(
            job_id="new-job",
            tool_name="test_tool",
            params={"key": "value"},
            status="completed",
            created_at=datetime.now(UTC).isoformat(),
        )
        job_queue_temp._save_job(job_new)

        # Cleanup older than 24 hours
        deleted = await job_queue_temp.cleanup_expired(older_than_hours=24)

        # Old job should be deleted, new job should remain
        assert deleted == 1
        assert job_queue_temp._load_job("old-job") is None
        assert job_queue_temp._load_job("new-job") is not None


@pytest.mark.asyncio
class TestJobTools:
    """Test MCP tool functions."""

    async def test_research_job_submit(self, job_queue_temp) -> None:
        """Test research_job_submit tool."""
        # We need to mock the global queue for this
        import loom.tools.job_tools as job_tools_module
        original_get_queue = job_tools_module.get_job_queue

        try:
            job_tools_module.get_job_queue = lambda: job_queue_temp
            result = await research_job_submit(
                tool_name="test_tool",
                params={"key": "value"}
            )

            assert "job_id" in result
            assert result["status"] == "pending"
            assert len(result["job_id"]) == 36
        finally:
            job_tools_module.get_job_queue = original_get_queue

    async def test_research_job_status_tool(self, job_queue_temp) -> None:
        """Test research_job_status tool."""
        import loom.tools.job_tools as job_tools_module
        original_get_queue = job_tools_module.get_job_queue

        try:
            job_tools_module.get_job_queue = lambda: job_queue_temp

            # First submit a job
            submit_result = await research_job_submit(
                tool_name="test_tool",
                params={"key": "value"}
            )
            job_id = submit_result["job_id"]

            # Then get its status
            status = await research_job_status(job_id)

            assert status["job_id"] == job_id
            assert status["status"] == "pending"
        finally:
            job_tools_module.get_job_queue = original_get_queue


@pytest.mark.unit
@pytest.mark.asyncio
async def test_job_to_dict() -> None:
    """Test Job dataclass to_dict method."""
    job = Job(
        job_id="test-123",
        tool_name="test_tool",
        params={"key": "value"},
        status="pending",
        created_at=datetime.now(UTC).isoformat(),
    )
    job_dict = job.to_dict()

    assert job_dict["job_id"] == "test-123"
    assert job_dict["tool_name"] == "test_tool"
    assert job_dict["params"] == {"key": "value"}
    assert job_dict["status"] == "pending"
    assert job_dict["result"] is None
    assert job_dict["error"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_queue_singleton() -> None:
    """Test that get_job_queue returns singleton."""
    q1 = get_job_queue()
    q2 = get_job_queue()
    assert q1 is q2
