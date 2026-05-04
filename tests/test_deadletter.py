"""Tests for deadletter queue implementation.

Tests DeadletterQueue functionality including:
- Enqueue/dequeue operations
- Exponential backoff calculation
- Retry counting and permanent failure
- Statistics tracking
- SQLite persistence
- Thread safety
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from loom.deadletter import DeadletterQueue, DeadletterQueueWorker, get_dlq


class TestDeadletterQueue:
    """Test DeadletterQueue core functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_dlq.db"
            yield db_path

    @pytest.fixture
    def dlq(self, temp_db):
        """Create DeadletterQueue instance with temp database."""
        return DeadletterQueue(db_path=temp_db, max_retries=3)

    def test_init_creates_database(self, temp_db):
        """Test that __init__ creates SQLite database and schema."""
        dlq = DeadletterQueue(db_path=temp_db)
        assert temp_db.exists()

        # Verify schema exists
        with dlq._get_connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [row[0] for row in tables]

        assert "dlq_pending" in table_names
        assert "dlq_failed" in table_names

    def test_enqueue_basic(self, dlq):
        """Test basic enqueue operation."""
        params = {"url": "https://example.com", "timeout": 30}
        error = "Connection timeout"

        dlq_id = dlq.enqueue("research_fetch", params, error)

        assert isinstance(dlq_id, int)
        assert dlq_id > 0

    def test_enqueue_invalid_params(self, dlq):
        """Test enqueue with non-serializable params."""
        class NonSerializable:
            pass

        params = {"obj": NonSerializable()}

        with pytest.raises(ValueError, match="Cannot serialize"):
            dlq.enqueue("research_fetch", params, "error")

    def test_dequeue_empty(self, dlq):
        """Test dequeue from empty queue."""
        items = dlq.dequeue()
        assert items == []

    def test_dequeue_ready_items(self, dlq):
        """Test dequeue returns only items past retry time."""
        params = {"url": "https://example.com"}

        # Enqueue item (next_retry_at will be in future)
        dlq_id = dlq.enqueue("research_fetch", params, "error")

        # Item should not be ready yet
        items = dlq.dequeue()
        assert len(items) == 0

    def test_dequeue_respects_limit(self, dlq):
        """Test dequeue respects limit parameter."""
        for i in range(5):
            dlq.enqueue("research_fetch", {"index": i}, f"error {i}")

        items = dlq.dequeue(limit=2)
        assert len(items) <= 2

    def test_mark_success(self, dlq):
        """Test mark_success removes item from queue."""
        dlq_id = dlq.enqueue("research_fetch", {"url": "test"}, "error")

        # Item exists in pending
        items = dlq.get_items_by_tool("research_fetch")
        assert len(items) == 1

        # Mark success
        result = dlq.mark_success(dlq_id)
        assert result is True

        # Item removed from pending
        items = dlq.get_items_by_tool("research_fetch")
        assert len(items) == 0

    def test_mark_success_not_found(self, dlq):
        """Test mark_success with non-existent ID."""
        result = dlq.mark_success(9999)
        assert result is False

    def test_mark_permanent_failure(self, dlq):
        """Test mark_permanent_failure moves item to failed table."""
        dlq_id = dlq.enqueue("research_fetch", {"url": "test"}, "error")

        # Item in pending
        pending = dlq.get_items_by_tool("research_fetch", include_failed=False)
        assert len(pending) == 1

        # Mark permanent failure
        result = dlq.mark_permanent_failure(dlq_id)
        assert result is True

        # Item moved to failed
        pending = dlq.get_items_by_tool("research_fetch", include_failed=False)
        assert len(pending) == 0

        failed = dlq.get_items_by_tool("research_fetch", include_failed=True)
        assert len(failed) == 1
        assert failed[0]["status"] == "failed"

    def test_increment_retry_count(self, dlq):
        """Test retry count incrementation and backoff calculation."""
        dlq_id = dlq.enqueue("research_fetch", {"url": "test"}, "error")

        # Get initial retry count
        items = dlq.get_items_by_tool("research_fetch")
        assert items[0]["retry_count"] == 0

        # Increment
        result = dlq.increment_retry_count(dlq_id)
        assert result is True

        items = dlq.get_items_by_tool("research_fetch")
        assert items[0]["retry_count"] == 1

    def test_calculate_next_retry_backoff(self, dlq):
        """Test exponential backoff calculation."""
        # Retry 0: 60s
        next_retry_0 = dlq._calculate_next_retry(0, dlq.BACKOFF_SCHEDULE)
        now = datetime.now(UTC)
        retry_time_0 = datetime.fromisoformat(next_retry_0)
        delay_0 = (retry_time_0 - now).total_seconds()
        assert 59 <= delay_0 <= 61

        # Retry 1: 300s
        next_retry_1 = dlq._calculate_next_retry(1, dlq.BACKOFF_SCHEDULE)
        retry_time_1 = datetime.fromisoformat(next_retry_1)
        delay_1 = (retry_time_1 - now).total_seconds()
        assert 299 <= delay_1 <= 301

        # Retry 2: 1800s
        next_retry_2 = dlq._calculate_next_retry(2, dlq.BACKOFF_SCHEDULE)
        retry_time_2 = datetime.fromisoformat(next_retry_2)
        delay_2 = (retry_time_2 - now).total_seconds()
        assert 1799 <= delay_2 <= 1801

    def test_get_stats(self, dlq):
        """Test statistics gathering."""
        # Add some items
        dlq.enqueue("research_fetch", {"url": "1"}, "error 1")
        dlq.enqueue("research_spider", {"urls": ["a"]}, "error 2")
        dlq.enqueue("research_fetch", {"url": "2"}, "error 3")

        stats = dlq.get_stats()

        assert stats["pending"] == 3
        assert stats["failed"] == 0
        assert stats["total_retried"] == 0
        assert stats["avg_retry_count"] == 0.0

    def test_get_stats_with_retries(self, dlq):
        """Test statistics with retried items."""
        dlq_id1 = dlq.enqueue("research_fetch", {"url": "1"}, "error")
        dlq_id2 = dlq.enqueue("research_fetch", {"url": "2"}, "error")

        dlq.increment_retry_count(dlq_id1)
        dlq.increment_retry_count(dlq_id1)
        dlq.increment_retry_count(dlq_id2)

        stats = dlq.get_stats()

        assert stats["pending"] == 2
        assert stats["total_retried"] == 3
        assert stats["avg_retry_count"] == 1.5

    def test_cleanup_old_failed(self, dlq):
        """Test cleanup of old failed items."""
        # Create failed item
        dlq_id = dlq.enqueue("research_fetch", {"url": "test"}, "error")
        dlq.mark_permanent_failure(dlq_id)

        # Verify it exists
        stats_before = dlq.get_stats()
        assert stats_before["failed"] == 1

        # Should not delete recent item
        deleted = dlq.cleanup_old_failed(days=30)
        assert deleted == 0

        stats_after = dlq.get_stats()
        assert stats_after["failed"] == 1

    def test_thread_safety(self, dlq):
        """Test that concurrent operations don't corrupt database."""
        import threading

        def enqueue_items(count):
            for i in range(count):
                dlq.enqueue("research_fetch", {"index": i}, f"error {i}")

        threads = [
            threading.Thread(target=enqueue_items, args=(10,))
            for _ in range(5)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        stats = dlq.get_stats()
        assert stats["pending"] == 50

    def test_get_items_by_tool(self, dlq):
        """Test filtering items by tool name."""
        dlq.enqueue("research_fetch", {"url": "1"}, "error 1")
        dlq.enqueue("research_spider", {"urls": ["a"]}, "error 2")
        dlq.enqueue("research_fetch", {"url": "2"}, "error 3")

        fetch_items = dlq.get_items_by_tool("research_fetch")
        assert len(fetch_items) == 2

        spider_items = dlq.get_items_by_tool("research_spider")
        assert len(spider_items) == 1


class TestBackoffSchedule:
    """Test exponential backoff scheduling."""

    @pytest.fixture
    def dlq(self, tmp_path):
        return DeadletterQueue(db_path=tmp_path / "dlq.db")

    def test_backoff_progression(self, dlq):
        """Test that backoff delays increase exponentially."""
        delays = []
        for retry_count in range(3):
            next_retry = dlq._calculate_next_retry(retry_count, dlq.BACKOFF_SCHEDULE)
            retry_time = datetime.fromisoformat(next_retry)
            delay_seconds = (retry_time - datetime.now(UTC)).total_seconds()
            delays.append(delay_seconds)

        # Verify delays increase
        assert delays[0] < delays[1] < delays[2]

        # Verify expected values (with 1s tolerance)
        assert 59 <= delays[0] <= 61
        assert 299 <= delays[1] <= 301
        assert 1799 <= delays[2] <= 1801

    def test_backoff_beyond_schedule(self, dlq):
        """Test backoff continues with final delay beyond schedule."""
        # Request retry beyond schedule length
        next_retry = dlq._calculate_next_retry(5, dlq.BACKOFF_SCHEDULE)
        retry_time = datetime.fromisoformat(next_retry)
        delay = (retry_time - datetime.now(UTC)).total_seconds()

        # Should use final schedule value (1800s)
        assert 1799 <= delay <= 1801


class TestDeadletterQueueWorker:
    """Test background worker for retry processing."""

    @pytest.fixture
    def temp_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "dlq.db"

    @pytest.fixture
    def dlq(self, temp_db):
        return DeadletterQueue(db_path=temp_db, max_retries=2)

    @pytest.mark.asyncio
    async def test_worker_start_stop(self, dlq):
        """Test worker lifecycle management."""
        mock_executor = AsyncMock()
        worker = DeadletterQueueWorker(dlq, mock_executor, poll_interval=1)

        # Start worker
        await worker.start()
        assert worker._running is True
        assert worker._task is not None

        # Stop worker
        await worker.stop()
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_worker_process_batch(self, dlq):
        """Test worker processes ready items."""
        # Enqueue item and mark as ready
        dlq_id = dlq.enqueue("research_fetch", {"url": "test"}, "error")

        # Manually set next_retry_at to past for testing
        with dlq._lock:
            with dlq._get_connection() as conn:
                past = datetime.now(UTC) - timedelta(seconds=10)
                conn.execute(
                    "UPDATE dlq_pending SET next_retry_at = ? WHERE id = ?",
                    (past.isoformat(), dlq_id),
                )
                conn.commit()

        # Mock executor that succeeds
        mock_executor = AsyncMock(return_value={"success": True})
        worker = DeadletterQueueWorker(dlq, mock_executor, poll_interval=1)

        # Process batch
        await worker._process_batch()

        # Item should be removed from queue
        stats = dlq.get_stats()
        assert stats["pending"] == 0

    @pytest.mark.asyncio
    async def test_worker_retry_on_failure(self, dlq):
        """Test worker retries on failure and increments count."""
        dlq_id = dlq.enqueue("research_fetch", {"url": "test"}, "error")

        # Mark as ready
        with dlq._lock:
            with dlq._get_connection() as conn:
                past = datetime.now(UTC) - timedelta(seconds=10)
                conn.execute(
                    "UPDATE dlq_pending SET next_retry_at = ? WHERE id = ?",
                    (past.isoformat(), dlq_id),
                )
                conn.commit()

        # Mock executor that fails
        mock_executor = AsyncMock(side_effect=Exception("Network error"))
        worker = DeadletterQueueWorker(dlq, mock_executor, poll_interval=1)

        # Process batch
        await worker._process_batch()

        # Item should still be in queue with incremented retry count
        items = dlq.get_items_by_tool("research_fetch")
        assert len(items) == 1
        assert items[0]["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_worker_permanent_failure(self, dlq):
        """Test worker moves items to failed after max retries."""
        dlq_id = dlq.enqueue("research_fetch", {"url": "test"}, "error")

        # Set retry count to max
        with dlq._lock:
            with dlq._get_connection() as conn:
                past = datetime.now(UTC) - timedelta(seconds=10)
                conn.execute(
                    "UPDATE dlq_pending SET next_retry_at = ?, retry_count = ? WHERE id = ?",
                    (past.isoformat(), dlq.max_retries, dlq_id),
                )
                conn.commit()

        mock_executor = AsyncMock(side_effect=Exception("Network error"))
        worker = DeadletterQueueWorker(dlq, mock_executor, poll_interval=1)

        # Process batch
        await worker._process_batch()

        # Item should be moved to failed
        pending = dlq.get_items_by_tool("research_fetch", include_failed=False)
        assert len(pending) == 0

        failed = dlq.get_items_by_tool("research_fetch", include_failed=True)
        assert len(failed) == 1


class TestSingleton:
    """Test singleton pattern for DeadletterQueue."""

    def test_get_dlq_returns_singleton(self):
        """Test that get_dlq returns same instance."""
        dlq1 = get_dlq()
        dlq2 = get_dlq()

        assert dlq1 is dlq2

    def test_singleton_thread_safety(self):
        """Test singleton creation is thread-safe."""
        import threading

        instances = []
        lock = threading.Lock()

        def get_instance():
            # Import fresh to avoid module-level caching
            from loom.deadletter import get_dlq as get_dlq_fn

            instance = get_dlq_fn()
            with lock:
                instances.append(instance)

        threads = [threading.Thread(target=get_instance) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All should be same instance
        first = instances[0]
        assert all(inst is first for inst in instances)
