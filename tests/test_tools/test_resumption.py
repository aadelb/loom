"""Tests for checkpoint resumption engine."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import loom.tools.infrastructure.resumption


@pytest.fixture
def temp_db_path(tmp_path):
    """Fixture to provide a temporary database path."""
    db_path = tmp_path / "test_checkpoints.db"
    with patch.object(resumption, "_DB_PATH", db_path):
        yield db_path


@pytest.mark.asyncio
async def test_checkpoint_save_new(temp_db_path):
    """Test saving a new checkpoint."""
    result = await resumption.research_checkpoint_save(
        task_id="test_task_1",
        state={"key": "value", "nested": {"data": 123}},
        progress_pct=50.0,
    )

    assert result["task_id"] == "test_task_1"
    assert result["progress_pct"] == 50.0
    assert result["action"] == "inserted"
    assert result["checkpoint_size_bytes"] > 0


@pytest.mark.asyncio
async def test_checkpoint_save_update(temp_db_path):
    """Test updating an existing checkpoint."""
    task_id = "test_task_2"

    # Save first checkpoint
    result1 = await resumption.research_checkpoint_save(
        task_id=task_id,
        state={"version": 1},
        progress_pct=25.0,
    )
    assert result1["action"] == "inserted"

    # Update same task
    result2 = await resumption.research_checkpoint_save(
        task_id=task_id,
        state={"version": 2, "extra": "data"},
        progress_pct=75.0,
    )
    assert result2["action"] == "updated"
    assert result2["progress_pct"] == 75.0


@pytest.mark.asyncio
async def test_checkpoint_save_validation(temp_db_path):
    """Test checkpoint save parameter validation."""
    # Invalid task_id (empty)
    with pytest.raises(ValueError):
        await resumption.research_checkpoint_save(
            task_id="",
            state={},
        )

    # Invalid task_id (not string)
    with pytest.raises(ValueError):
        await resumption.research_checkpoint_save(
            task_id=123,
            state={},
        )

    # Invalid state (not dict)
    with pytest.raises(ValueError):
        await resumption.research_checkpoint_save(
            task_id="test",
            state="not_a_dict",
        )

    # Invalid progress_pct (out of range)
    with pytest.raises(ValueError):
        await resumption.research_checkpoint_save(
            task_id="test",
            state={},
            progress_pct=150.0,
        )

    with pytest.raises(ValueError):
        await resumption.research_checkpoint_save(
            task_id="test",
            state={},
            progress_pct=-10.0,
        )


@pytest.mark.asyncio
async def test_checkpoint_resume_existing(temp_db_path):
    """Test resuming an existing checkpoint."""
    task_id = "test_resume_1"
    saved_state = {"url": "https://example.com", "results": [1, 2, 3]}

    # Save checkpoint
    await resumption.research_checkpoint_save(
        task_id=task_id,
        state=saved_state,
        progress_pct=60.0,
    )

    # Resume checkpoint
    result = await resumption.research_checkpoint_resume(task_id=task_id)

    assert result["task_id"] == task_id
    assert result["state"] == saved_state
    assert result["progress_pct"] == 60.0
    assert result["last_updated"] is not None
    assert result["age_seconds"] >= 0


@pytest.mark.asyncio
async def test_checkpoint_resume_not_found(temp_db_path):
    """Test resuming a non-existent checkpoint."""
    result = await resumption.research_checkpoint_resume(task_id="non_existent")

    assert result["task_id"] == "non_existent"
    assert result["state"] is None
    assert result["progress_pct"] is None
    assert result["last_updated"] is None
    assert result["age_seconds"] is None


@pytest.mark.asyncio
async def test_checkpoint_resume_validation(temp_db_path):
    """Test checkpoint resume parameter validation."""
    # Invalid task_id (empty)
    with pytest.raises(ValueError):
        await resumption.research_checkpoint_resume(task_id="")

    # Invalid task_id (not string)
    with pytest.raises(ValueError):
        await resumption.research_checkpoint_resume(task_id=123)


@pytest.mark.asyncio
async def test_checkpoint_list_all(temp_db_path):
    """Test listing all checkpoints."""
    # Save multiple checkpoints
    for i in range(3):
        await resumption.research_checkpoint_save(
            task_id=f"task_{i}",
            state={"index": i},
            progress_pct=float(i * 30),
        )

    result = await resumption.research_checkpoint_list(status="all")

    assert result["total"] == 3
    assert len(result["checkpoints"]) == 3
    assert all("task_id" in cp for cp in result["checkpoints"])
    assert all("progress" in cp for cp in result["checkpoints"])
    assert all("age_seconds" in cp for cp in result["checkpoints"])


@pytest.mark.asyncio
async def test_checkpoint_list_incomplete(temp_db_path):
    """Test listing incomplete checkpoints."""
    # Save complete and incomplete checkpoints
    await resumption.research_checkpoint_save(
        task_id="complete",
        state={},
        progress_pct=100.0,
    )
    await resumption.research_checkpoint_save(
        task_id="incomplete1",
        state={},
        progress_pct=50.0,
    )
    await resumption.research_checkpoint_save(
        task_id="incomplete2",
        state={},
        progress_pct=75.0,
    )

    result = await resumption.research_checkpoint_list(status="incomplete")

    assert result["total"] == 2
    assert result["incomplete_count"] == 2
    task_ids = {cp["task_id"] for cp in result["checkpoints"]}
    assert task_ids == {"incomplete1", "incomplete2"}


@pytest.mark.asyncio
async def test_checkpoint_list_stale(temp_db_path):
    """Test listing stale checkpoints."""
    # Create checkpoints with mocked timestamps
    await resumption.research_checkpoint_save(
        task_id="fresh",
        state={},
        progress_pct=50.0,
    )

    # Manually insert a stale checkpoint (older than 24 hours)
    conn = await resumption._get_db()
    try:
        old_time = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        await conn.execute(
            """
            INSERT INTO checkpoints (task_id, state, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("stale_task", '{"old": "data"}', 30.0, old_time, old_time),
        )
        await conn.commit()
    finally:
        await conn.close()

    result = await resumption.research_checkpoint_list(status="stale")

    assert result["total"] == 1
    assert result["checkpoints"][0]["task_id"] == "stale_task"


@pytest.mark.asyncio
async def test_checkpoint_list_cleanup(temp_db_path):
    """Test automatic cleanup of old checkpoints."""
    # Insert a checkpoint older than 7 days
    conn = await resumption._get_db()
    try:
        old_time = (datetime.now(UTC) - timedelta(days=8)).isoformat()
        await conn.execute(
            """
            INSERT INTO checkpoints (task_id, state, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("very_old_task", '{"data": "gone"}', 50.0, old_time, old_time),
        )

        # Add a fresh checkpoint
        await conn.execute(
            """
            INSERT INTO checkpoints (task_id, state, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("fresh_task", '{"data": "keep"}', 50.0, datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()),
        )
        await conn.commit()
    finally:
        await conn.close()

    # List should trigger cleanup
    result = await resumption.research_checkpoint_list(status="all")

    assert result["deleted_old_count"] == 1
    assert result["total"] == 1
    assert result["checkpoints"][0]["task_id"] == "fresh_task"


@pytest.mark.asyncio
async def test_checkpoint_list_validation(temp_db_path):
    """Test checkpoint list parameter validation."""
    with pytest.raises(ValueError):
        await resumption.research_checkpoint_list(status="invalid_status")


@pytest.mark.asyncio
async def test_checkpoint_large_state(temp_db_path):
    """Test checkpoint with large state data."""
    large_state = {
        "data": [{"id": i, "text": "x" * 1000} for i in range(100)]
    }

    result = await resumption.research_checkpoint_save(
        task_id="large_task",
        state=large_state,
        progress_pct=50.0,
    )

    assert result["checkpoint_size_bytes"] > 100000  # Expect > 100KB

    # Verify retrieval works
    resume_result = await resumption.research_checkpoint_resume(task_id="large_task")
    assert resume_result["state"] == large_state


@pytest.mark.asyncio
async def test_checkpoint_complex_state_types(temp_db_path):
    """Test checkpoint with various JSON-serializable types."""
    complex_state = {
        "strings": "value",
        "numbers": [1, 2.5, -10],
        "booleans": [True, False],
        "nulls": None,
        "nested": {
            "deeply": {
                "nested": {
                    "data": [1, 2, 3]
                }
            }
        }
    }

    await resumption.research_checkpoint_save(
        task_id="complex_task",
        state=complex_state,
        progress_pct=75.0,
    )

    result = await resumption.research_checkpoint_resume(task_id="complex_task")
    assert result["state"] == complex_state


@pytest.mark.asyncio
async def test_checkpoint_concurrent_access(temp_db_path):
    """Test concurrent checkpoint operations."""
    import asyncio

    async def save_checkpoint(task_num: int):
        return await resumption.research_checkpoint_save(
            task_id=f"concurrent_task_{task_num}",
            state={"task": task_num},
            progress_pct=float(task_num * 10),
        )

    # Save 5 checkpoints concurrently
    results = await asyncio.gather(*[save_checkpoint(i) for i in range(5)])

    assert len(results) == 5
    assert all(r["action"] in ("inserted", "updated") for r in results)

    # Verify all were saved
    list_result = await resumption.research_checkpoint_list()
    assert list_result["total"] == 5


@pytest.mark.asyncio
async def test_checkpoint_progress_boundary_values(temp_db_path):
    """Test checkpoint with boundary progress values."""
    for progress in [0.0, 0.1, 50.0, 99.9, 100.0]:
        result = await resumption.research_checkpoint_save(
            task_id=f"progress_{progress}",
            state={"progress": progress},
            progress_pct=progress,
        )
        assert result["progress_pct"] == progress

        resume = await resumption.research_checkpoint_resume(
            task_id=f"progress_{progress}"
        )
        assert resume["progress_pct"] == progress
