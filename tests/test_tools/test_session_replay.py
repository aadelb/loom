"""Tests for session replay tool."""

import pytest
import json
from pathlib import Path
from datetime import UTC, datetime

from loom.tools.session_replay import (
    research_session_record,
    research_session_replay,
    research_session_list,
    _get_replay_dir,
)


@pytest.fixture
def replay_dir(tmp_path, monkeypatch):
    """Override replay directory for tests."""
    replay_dir = tmp_path / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)

    def mock_get_replay_dir():
        return replay_dir

    monkeypatch.setattr(
        "loom.tools.session_replay._get_replay_dir",
        mock_get_replay_dir,
    )
    return replay_dir


@pytest.mark.asyncio
async def test_session_record_creates_jsonl(replay_dir):
    """Test that recording a step creates a JSONL file."""
    result = await research_session_record(
        session_id="test_session",
        tool_name="research_fetch",
        params={"url": "https://example.com"},
        result_summary="Fetched successfully",
        duration_ms=1500.0,
    )

    assert result["recorded"] is True
    assert result["session_id"] == "test_session"
    assert result["step_number"] == 1

    # Verify file exists
    session_file = replay_dir / "test_session.jsonl"
    assert session_file.exists()

    # Verify JSON content
    with session_file.open() as f:
        step = json.loads(f.readline())
    assert step["step"] == 1
    assert step["tool"] == "research_fetch"
    assert step["duration_ms"] == 1500.0


@pytest.mark.asyncio
async def test_session_record_appends_steps(replay_dir):
    """Test that multiple records append to the same session."""
    # First record
    await research_session_record(
        session_id="multi_test",
        tool_name="research_fetch",
        params={"url": "https://example.com"},
        result_summary="Step 1",
        duration_ms=100.0,
    )

    # Second record
    await research_session_record(
        session_id="multi_test",
        tool_name="research_search",
        params={"query": "test"},
        result_summary="Step 2",
        duration_ms=200.0,
    )

    # Verify file has 2 lines
    session_file = replay_dir / "multi_test.jsonl"
    with session_file.open() as f:
        lines = f.readlines()
    assert len(lines) == 2

    step1 = json.loads(lines[0])
    step2 = json.loads(lines[1])
    assert step1["step"] == 1
    assert step2["step"] == 2


@pytest.mark.asyncio
async def test_session_replay_loads_all_steps(replay_dir):
    """Test that replay loads all recorded steps."""
    # Record multiple steps
    for i in range(3):
        await research_session_record(
            session_id="replay_test",
            tool_name=f"tool_{i}",
            params={"index": i},
            result_summary=f"Result {i}",
            duration_ms=100.0 * (i + 1),
        )

    # Replay the session
    result = await research_session_replay("replay_test")

    assert result["session_id"] == "replay_test"
    assert result["total_steps"] == 3
    assert len(result["steps"]) == 3
    assert result["total_duration_ms"] == 600.0  # 100 + 200 + 300

    # Verify step details
    assert result["steps"][0]["tool"] == "tool_0"
    assert result["steps"][1]["tool"] == "tool_1"
    assert result["steps"][2]["tool"] == "tool_2"


@pytest.mark.asyncio
async def test_session_replay_nonexistent_session(replay_dir):
    """Test replay returns proper error for nonexistent session."""
    result = await research_session_replay("nonexistent")

    assert result["session_id"] == "nonexistent"
    assert result["total_steps"] == 0
    assert result["steps"] == []
    assert "error" in result


@pytest.mark.asyncio
async def test_session_list_empty(replay_dir):
    """Test list returns empty when no sessions exist."""
    result = await research_session_list()

    assert result["total_sessions"] == 0
    assert result["sessions"] == []


@pytest.mark.asyncio
async def test_session_list_returns_all_sessions(replay_dir):
    """Test list returns metadata for all sessions."""
    # Create multiple sessions
    sessions = ["session_a", "session_b", "session_c"]

    for session_id in sessions:
        for i in range(2):
            await research_session_record(
                session_id=session_id,
                tool_name=f"tool_{i}",
                params={},
                result_summary=f"Result {i}",
                duration_ms=100.0,
            )

    result = await research_session_list()

    assert result["total_sessions"] == 3
    assert len(result["sessions"]) == 3

    # Verify each session summary
    session_ids = [s["id"] for s in result["sessions"]]
    assert set(session_ids) == set(sessions)

    for session in result["sessions"]:
        assert session["steps_count"] == 2
        assert session["total_duration_ms"] == 200.0
        assert "first_step_at" in session
        assert "last_step_at" in session


@pytest.mark.asyncio
async def test_session_list_sorted(replay_dir):
    """Test that sessions are returned in sorted order."""
    # Create sessions in non-alphabetical order
    for session_id in ["z_session", "a_session", "m_session"]:
        await research_session_record(
            session_id=session_id,
            tool_name="tool",
            params={},
            result_summary="Result",
            duration_ms=100.0,
        )

    result = await research_session_list()

    session_ids = [s["id"] for s in result["sessions"]]
    assert session_ids == ["a_session", "m_session", "z_session"]


@pytest.mark.asyncio
async def test_params_truncation(replay_dir):
    """Test that long params and results are truncated."""
    long_params = {"data": "x" * 500}
    long_result = "y" * 1000

    await research_session_record(
        session_id="truncate_test",
        tool_name="test_tool",
        params=long_params,
        result_summary=long_result,
        duration_ms=100.0,
    )

    session_file = replay_dir / "truncate_test.jsonl"
    with session_file.open() as f:
        step = json.loads(f.readline())

    assert len(step["params_summary"]) <= 200
    assert len(step["result_summary"]) <= 500


@pytest.mark.asyncio
async def test_timestamp_fields(replay_dir):
    """Test that timestamp fields are properly recorded."""
    await research_session_record(
        session_id="timestamp_test",
        tool_name="test_tool",
        params={},
        result_summary="Test",
        duration_ms=100.0,
    )

    result = await research_session_replay("timestamp_test")

    assert len(result["steps"]) == 1
    timestamp = result["steps"][0]["timestamp"]
    # Verify it's a valid ISO 8601 timestamp
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
