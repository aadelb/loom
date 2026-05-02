"""Session replay tool for debugging research workflows.

Records tool calls with parameters and results for workflow visualization and debugging.
Uses JSONL files for append-only storage with automatic directory creation.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.session_replay")


def _get_replay_dir() -> Path:
    """Get directory for session replay storage."""
    base = Path.home() / ".loom" / "sessions" / "replay"
    base.mkdir(parents=True, exist_ok=True)
    return base


async def research_session_record(
    session_id: str,
    tool_name: str,
    params: dict[str, Any],
    result_summary: str = "",
    duration_ms: float = 0.0,
) -> dict[str, Any]:
    """Record a tool call as part of a named session.

    Appends to ~/.loom/sessions/replay/{session_id}.jsonl for append-only
    storage without locking overhead. Each line is a complete JSON step record.

    Args:
        session_id: Session identifier (alphanumeric, dash, underscore)
        tool_name: Name of the tool called (e.g., "research_fetch")
        params: Tool parameters as dictionary
        result_summary: Brief summary of the result
        duration_ms: Execution duration in milliseconds

    Returns:
        Dict with: {recorded: True, session_id, step_number, timestamp}
    """
    replay_dir = _get_replay_dir()
    session_file = replay_dir / f"{session_id}.jsonl"

    # Count existing steps to compute step number
    step_number = 0
    if session_file.exists():
        try:
            step_number = sum(1 for _ in session_file.open())
        except OSError as e:
            logger.warning("session_record_step_count_failed session=%s: %s", session_id, e)

    step_number += 1

    # Create step record
    step = {
        "step": step_number,
        "tool": tool_name,
        "params_summary": str(params)[:200],  # Truncate to 200 chars
        "result_summary": result_summary[:500],  # Truncate to 500 chars
        "duration_ms": duration_ms,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Append to JSONL (atomic per-line writes)
    try:
        with session_file.open("a") as f:
            f.write(json.dumps(step) + "\n")
    except OSError as e:
        logger.error("session_record_write_failed session=%s: %s", session_id, e)
        return {"recorded": False, "session_id": session_id, "error": str(e)}

    return {
        "recorded": True,
        "session_id": session_id,
        "step_number": step_number,
        "timestamp": step["timestamp"],
    }


async def research_session_replay(
    session_id: str,
) -> dict[str, Any]:
    """Load and return the full session timeline.

    Reads all steps from JSONL file and reconstructs the workflow sequence.

    Args:
        session_id: Session identifier to replay

    Returns:
        Dict with: {session_id, steps: list of step dicts, total_steps, total_duration_ms}
    """
    replay_dir = _get_replay_dir()
    session_file = replay_dir / f"{session_id}.jsonl"

    if not session_file.exists():
        return {
            "session_id": session_id,
            "steps": [],
            "total_steps": 0,
            "total_duration_ms": 0.0,
            "error": f"Session not found: {session_id}",
        }

    steps = []
    total_duration_ms = 0.0

    try:
        with session_file.open() as f:
            for line in f:
                if line.strip():
                    step = json.loads(line)
                    steps.append(step)
                    total_duration_ms += step.get("duration_ms", 0.0)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("session_replay_read_failed session=%s: %s", session_id, e)
        return {
            "session_id": session_id,
            "steps": steps,
            "total_steps": len(steps),
            "total_duration_ms": total_duration_ms,
            "error": str(e),
        }

    return {
        "session_id": session_id,
        "steps": steps,
        "total_steps": len(steps),
        "total_duration_ms": round(total_duration_ms, 2),
    }


async def research_session_list() -> dict[str, Any]:
    """List all recorded sessions with metadata.

    Scans replay directory and returns summary for each session file found.

    Returns:
        Dict with: {sessions: list[{id, steps_count, total_duration_ms, first_step_at, last_step_at}], total_sessions}
    """
    replay_dir = _get_replay_dir()

    if not replay_dir.exists():
        return {"sessions": [], "total_sessions": 0}

    sessions = []

    for session_file in sorted(replay_dir.glob("*.jsonl")):
        session_id = session_file.stem
        steps = []
        total_duration_ms = 0.0

        try:
            with session_file.open() as f:
                for line in f:
                    if line.strip():
                        step = json.loads(line)
                        steps.append(step)
                        total_duration_ms += step.get("duration_ms", 0.0)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("session_list_read_failed session=%s: %s", session_id, e)
            continue

        if steps:
            sessions.append(
                {
                    "id": session_id,
                    "steps_count": len(steps),
                    "total_duration_ms": round(total_duration_ms, 2),
                    "first_step_at": steps[0].get("timestamp", ""),
                    "last_step_at": steps[-1].get("timestamp", ""),
                }
            )

    return {
        "sessions": sessions,
        "total_sessions": len(sessions),
    }
