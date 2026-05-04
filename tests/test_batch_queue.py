"""Tests for batch queue functionality.

Comprehensive test suite for batch processing queue with:
- Job submission and retrieval
- Status tracking
- Background processing
- Error handling and retries
- Webhook callbacks
- Parameter validation
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.batch_queue import (
    BatchItem,
    BatchListParams,
    BatchQueue,
    BatchStatusParams,
    BatchSubmitParams,
    DEFAULT_BATCH_CONCURRENCY,
    get_batch_queue,
    research_batch_list,
    research_batch_status,
    research_batch_submit,
)


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "batch_queue.db"


@pytest.fixture
def batch_queue(temp_db: Path) -> BatchQueue:
    """Create a batch queue instance with temporary database."""
    return BatchQueue(db_path=temp_db, concurrency=2)


class TestBatchQueue:
    """Tests for BatchQueue class."""

    def test_initialization(self, batch_queue: BatchQueue) -> None:
        """Test batch queue initialization."""
        assert batch_queue.concurrency == 2
        assert batch_queue.db_path.exists()
        # Verify schema exists
        with sqlite3.connect(batch_queue.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='batch_items'"
            )
            assert cursor.fetchone() is not None

    def test_submit_job(self, batch_queue: BatchQueue) -> None:
        """Test submitting a job to the batch queue."""
        batch_id = batch_queue.submit(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
        )

        assert batch_id is not None
        assert len(batch_id) == 36  # UUID4 format

        # Verify in database
        with sqlite3.connect(batch_queue.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM batch_items WHERE id = ?", (batch_id,)).fetchone()

        assert row is not None
        assert row["tool_name"] == "research_fetch"
        assert row["status"] == "pending"
        assert json.loads(row["params_json"]) == {"url": "https://example.com"}

    def test_submit_with_callback_url(self, batch_queue: BatchQueue) -> None:
        """Test submitting a job with a callback URL."""
        callback_url = "https://example.com/callback"
        batch_id = batch_queue.submit(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            callback_url=callback_url,
        )

        with sqlite3.connect(batch_queue.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM batch_items WHERE id = ?", (batch_id,)).fetchone()

        assert row["callback_url"] == callback_url

    def test_submit_invalid_params(self, batch_queue: BatchQueue) -> None:
        """Test submitting with invalid parameters."""
        with pytest.raises(ValueError):
            batch_queue.submit(tool_name="", params={})

        with pytest.raises(ValueError):
            batch_queue.submit(tool_name="research_fetch", params="not a dict")

    def test_get_status_existing_job(self, batch_queue: BatchQueue) -> None:
        """Test getting status of an existing job."""
        batch_id = batch_queue.submit(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
        )

        status = batch_queue.get_status(batch_id)

        assert status["id"] == batch_id
        assert status["tool_name"] == "research_fetch"
        assert status["status"] == "pending"
        assert status["result"] is None
        assert status["error_message"] is None

    def test_get_status_nonexistent_job(self, batch_queue: BatchQueue) -> None:
        """Test getting status of a non-existent job."""
        with pytest.raises(ValueError):
            batch_queue.get_status("00000000-0000-0000-0000-000000000000")

    def test_list_items_all(self, batch_queue: BatchQueue) -> None:
        """Test listing all batch items."""
        # Submit multiple jobs
        for i in range(5):
            batch_queue.submit(
                tool_name=f"tool_{i}",
                params={"index": i},
            )

        items = batch_queue.list_items(limit=10)

        assert len(items) == 5
        assert all(item["status"] == "pending" for item in items)

    def test_list_items_with_limit(self, batch_queue: BatchQueue) -> None:
        """Test listing items with limit."""
        for i in range(10):
            batch_queue.submit(
                tool_name="test_tool",
                params={"index": i},
            )

        items = batch_queue.list_items(limit=5)

        assert len(items) == 5

    def test_list_items_with_status_filter(self, batch_queue: BatchQueue) -> None:
        """Test listing items with status filter."""
        batch_id = batch_queue.submit(
            tool_name="test_tool",
            params={},
        )

        # Update one to 'done'
        with sqlite3.connect(batch_queue.db_path) as conn:
            conn.execute(
                "UPDATE batch_items SET status = 'done' WHERE id = ?",
                (batch_id,),
            )
            conn.commit()

        # Filter by done
        items = batch_queue.list_items(status_filter="done")
        assert len(items) == 1
        assert items[0]["status"] == "done"

        # Filter by pending
        items = batch_queue.list_items(status_filter="pending")
        assert len(items) == 0

    def test_register_tool(self, batch_queue: BatchQueue) -> None:
        """Test registering a tool handler."""

        def mock_handler(params: dict[str, Any]) -> dict[str, Any]:
            return {"result": "success"}

        batch_queue.register_tool("test_tool", mock_handler)

        assert "test_tool" in batch_queue._tool_registry
        assert batch_queue._tool_registry["test_tool"] == mock_handler


class TestBatchQueueProcessing:
    """Tests for batch queue background processing."""

    @pytest.mark.asyncio
    async def test_process_pending_sync_handler(self, batch_queue: BatchQueue) -> None:
        """Test processing a pending job with a sync handler."""

        def mock_handler(params: dict[str, Any]) -> dict[str, Any]:
            return {"processed": True, "url": params.get("url")}

        batch_queue.register_tool("research_fetch", mock_handler)

        batch_id = batch_queue.submit(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
        )

        # Process pending
        processed = await batch_queue.process_pending()

        assert processed == 1

        # Check status
        status = batch_queue.get_status(batch_id)
        assert status["status"] == "done"
        assert status["result"] == {"processed": True, "url": "https://example.com"}

    @pytest.mark.asyncio
    async def test_process_pending_async_handler(self, batch_queue: BatchQueue) -> None:
        """Test processing a pending job with an async handler."""

        async def mock_handler(params: dict[str, Any]) -> dict[str, Any]:
            await asyncio.sleep(0.01)
            return {"async_result": params.get("value")}

        batch_queue.register_tool("async_tool", mock_handler)

        batch_id = batch_queue.submit(
            tool_name="async_tool",
            params={"value": "test"},
        )

        processed = await batch_queue.process_pending()

        assert processed == 1

        status = batch_queue.get_status(batch_id)
        assert status["status"] == "done"
        assert status["result"]["async_result"] == "test"

    @pytest.mark.asyncio
    async def test_process_pending_unregistered_tool(self, batch_queue: BatchQueue) -> None:
        """Test processing a job for an unregistered tool."""
        batch_id = batch_queue.submit(
            tool_name="nonexistent_tool",
            params={},
        )

        processed = await batch_queue.process_pending()

        assert processed == 1

        status = batch_queue.get_status(batch_id)
        assert status["status"] == "failed"
        assert "not registered" in status["error_message"]

    @pytest.mark.asyncio
    async def test_process_pending_handler_exception(self, batch_queue: BatchQueue) -> None:
        """Test processing a job when handler raises exception."""

        def failing_handler(params: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("Test error")

        batch_queue.register_tool("failing_tool", failing_handler)

        batch_id = batch_queue.submit(
            tool_name="failing_tool",
            params={},
            max_retries=1,  # Only 1 retry
        )

        # First process attempt
        await batch_queue.process_pending()

        status = batch_queue.get_status(batch_id)
        assert status["status"] == "pending"  # Retrying
        assert status["retry_count"] == 1

        # Second process attempt (should fail permanently)
        await batch_queue.process_pending()

        status = batch_queue.get_status(batch_id)
        assert status["status"] == "failed"
        assert status["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_process_pending_concurrency_limit(self, batch_queue: BatchQueue) -> None:
        """Test that processing respects concurrency limit."""
        batch_queue.concurrency = 1

        processing_times = []

        async def slow_handler(params: dict[str, Any]) -> dict[str, Any]:
            processing_times.append("started")
            await asyncio.sleep(0.05)
            return {"done": True}

        batch_queue.register_tool("slow_tool", slow_handler)

        # Submit 3 jobs
        for i in range(3):
            batch_queue.submit(tool_name="slow_tool", params={"index": i})

        # Process first job
        processed1 = await batch_queue.process_pending()
        assert processed1 == 1

        # Simulate second job being processed
        processed2 = await batch_queue.process_pending()
        assert processed2 == 1

        # Third job
        processed3 = await batch_queue.process_pending()
        assert processed3 == 1

    @pytest.mark.asyncio
    async def test_process_pending_no_pending_jobs(self, batch_queue: BatchQueue) -> None:
        """Test processing when no pending jobs exist."""
        processed = await batch_queue.process_pending()

        assert processed == 0


class TestBatchQueueWebhook:
    """Tests for webhook callback functionality."""

    @pytest.mark.asyncio
    async def test_trigger_callback_success(self) -> None:
        """Test successful webhook callback."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            await BatchQueue._trigger_callback(
                callback_url="https://example.com/callback",
                batch_id="test-id",
                status="done",
                result={"data": "test"},
                error_msg=None,
            )

            # Verify the callback was called
            assert mock_post.called

    @pytest.mark.asyncio
    async def test_trigger_callback_failure(self) -> None:
        """Test handling of failed webhook callback."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_post.return_value.__aenter__.return_value = mock_response

            # Should not raise, just log
            await BatchQueue._trigger_callback(
                callback_url="https://example.com/callback",
                batch_id="test-id",
                status="done",
                result=None,
                error_msg=None,
            )

            assert mock_post.called


class TestParameterValidation:
    """Tests for Pydantic parameter validation."""

    def test_batch_submit_params_valid(self) -> None:
        """Test valid BatchSubmitParams."""
        params = BatchSubmitParams(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            callback_url="https://example.com/callback",
            max_retries=5,
        )

        assert params.tool_name == "research_fetch"
        assert params.max_retries == 5

    def test_batch_submit_params_invalid_tool_name(self) -> None:
        """Test invalid tool name."""
        with pytest.raises(ValueError):
            BatchSubmitParams(
                tool_name="invalid-tool!",
                params={},
            )

    def test_batch_submit_params_invalid_callback_url(self) -> None:
        """Test invalid callback URL."""
        with pytest.raises(ValueError):
            BatchSubmitParams(
                tool_name="research_fetch",
                params={},
                callback_url="not-a-url",
            )

    def test_batch_submit_params_invalid_max_retries(self) -> None:
        """Test invalid max_retries."""
        with pytest.raises(ValueError):
            BatchSubmitParams(
                tool_name="research_fetch",
                params={},
                max_retries=15,  # > 10
            )

    def test_batch_status_params_valid(self) -> None:
        """Test valid BatchStatusParams."""
        params = BatchStatusParams(batch_id="550e8400-e29b-41d4-a716-446655440000")
        assert len(params.batch_id) == 36

    def test_batch_status_params_invalid(self) -> None:
        """Test invalid batch ID."""
        with pytest.raises(ValueError):
            BatchStatusParams(batch_id="not-a-uuid")

    def test_batch_list_params_valid(self) -> None:
        """Test valid BatchListParams."""
        params = BatchListParams(
            limit=50,
            status_filter="done",
            offset=10,
        )
        assert params.limit == 50

    def test_batch_list_params_limit_capped(self) -> None:
        """Test that limit is capped at MAX_BATCH_ITEMS_PER_LIST."""
        with pytest.raises(ValueError):
            BatchListParams(limit=200)


class TestMCPTools:
    """Tests for MCP tool functions."""

    @pytest.mark.asyncio
    async def test_research_batch_submit(self) -> None:
        """Test research_batch_submit MCP tool."""
        result = await research_batch_submit(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
        )

        assert "batch_id" in result
        assert result["status"] == "pending"
        assert result["tool_name"] == "research_fetch"

    @pytest.mark.asyncio
    async def test_research_batch_status(self) -> None:
        """Test research_batch_status MCP tool."""
        # First submit
        submit_result = await research_batch_submit(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
        )

        batch_id = submit_result["batch_id"]

        # Then get status
        status_result = await research_batch_status(batch_id)

        assert status_result["id"] == batch_id
        assert status_result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_research_batch_list(self) -> None:
        """Test research_batch_list MCP tool."""
        # Submit a few items
        for i in range(3):
            await research_batch_submit(
                tool_name=f"tool_{i}",
                params={"index": i},
            )

        # List them
        result = await research_batch_list(limit=10)

        assert "items" in result
        assert "count" in result
        assert result["count"] >= 3


class TestBatchItem:
    """Tests for BatchItem dataclass."""

    def test_batch_item_creation(self) -> None:
        """Test creating a BatchItem."""
        item = BatchItem(
            tool_name="research_fetch",
            params_json='{"url": "https://example.com"}',
        )

        assert item.id is not None
        assert item.tool_name == "research_fetch"
        assert item.status == "pending"

    def test_batch_item_to_dict(self) -> None:
        """Test converting BatchItem to dict."""
        item = BatchItem(
            tool_name="research_fetch",
            params_json='{"url": "https://example.com"}',
        )

        item_dict = item.to_dict()

        assert isinstance(item_dict, dict)
        assert item_dict["tool_name"] == "research_fetch"
        assert item_dict["status"] == "pending"


class TestBatchQueuePersistence:
    """Tests for SQLite persistence."""

    def test_persistence_across_instances(self, temp_db: Path) -> None:
        """Test that data persists across queue instances."""
        # Create queue and submit job
        queue1 = BatchQueue(db_path=temp_db)
        batch_id = queue1.submit(
            tool_name="research_fetch",
            params={"url": "https://example.com"},
        )

        # Create new queue instance
        queue2 = BatchQueue(db_path=temp_db)
        status = queue2.get_status(batch_id)

        assert status["id"] == batch_id
        assert status["tool_name"] == "research_fetch"

    def test_atomic_writes(self, temp_db: Path) -> None:
        """Test that writes are atomic."""
        queue = BatchQueue(db_path=temp_db)

        # Submit multiple jobs rapidly
        batch_ids = []
        for i in range(10):
            batch_id = queue.submit(
                tool_name="test_tool",
                params={"index": i},
            )
            batch_ids.append(batch_id)

        # Verify all were persisted
        for batch_id in batch_ids:
            status = queue.get_status(batch_id)
            assert status["id"] == batch_id


# Integration tests
class TestBatchQueueIntegration:
    """Integration tests for batch queue end-to-end flow."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, batch_queue: BatchQueue) -> None:
        """Test complete batch processing workflow."""

        def process_func(params: dict[str, Any]) -> dict[str, Any]:
            return {"processed": True, "input": params}

        batch_queue.register_tool("process_tool", process_func)

        # 1. Submit jobs
        batch_ids = []
        for i in range(3):
            batch_id = batch_queue.submit(
                tool_name="process_tool",
                params={"index": i},
            )
            batch_ids.append(batch_id)

        # 2. Process all jobs
        for _ in range(3):
            await batch_queue.process_pending()

        # 3. Verify all completed
        for batch_id in batch_ids:
            status = batch_queue.get_status(batch_id)
            assert status["status"] == "done"
            assert status["result"]["processed"] is True

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, batch_queue: BatchQueue) -> None:
        """Test processing mix of successful and failed jobs."""

        def process_func(params: dict[str, Any]) -> dict[str, Any]:
            if params.get("fail"):
                raise ValueError("Intentional failure")
            return {"success": True}

        batch_queue.register_tool("mixed_tool", process_func)

        # Submit mix of jobs
        success_id = batch_queue.submit(
            tool_name="mixed_tool",
            params={"fail": False},
            max_retries=0,
        )
        fail_id = batch_queue.submit(
            tool_name="mixed_tool",
            params={"fail": True},
            max_retries=0,
        )

        # Process both
        await batch_queue.process_pending()
        await batch_queue.process_pending()

        # Check results
        success_status = batch_queue.get_status(success_id)
        assert success_status["status"] == "done"

        fail_status = batch_queue.get_status(fail_id)
        assert fail_status["status"] == "failed"
