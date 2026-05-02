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

REPLAY_DIR = Path.home() / ".loom" / "sessions" / "replay"


def _get_replay_dir() -> Path:
    """Get directory for session replay storage."""
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    return REPLAY_DIR


def _load_jsonl_steps(session_file: Path) -> list[dict]:
    """Load all steps from a JSONL file."""
    steps = []
    if session_file.exists():
        try:
            with session_file.open() as f:
                steps = [json.loads(line) for line in f if line.strip()]
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("load_jsonl_failed: %s", e)
    return steps


async def research_session_record(
    session_id: str,
    tool_name: str,
    params: dict[str, Any],
    result_summary: str = "",
    duration_ms: float = 0.0,
) -> dict[str, Any]:
    """Record a tool call as part of a named session.

    Appends to ~/.loom/sessions/replay/{session_id}.jsonl in append-only mode.

    Returns:
        {recorded: bool, session_id, step_number, timestamp}
    """
    session_file = _get_replay_dir() / f"{session_id}.jsonl"
    step_number = len(_load_jsonl_steps(session_file)) + 1

    step = {
        "step": step_number,
        "tool": tool_name,
        "params_summary": str(params)[:200],
        "result_summary": result_summary[:500],
        "duration_ms": duration_ms,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        with session_file.open("a") as f:
            f.write(json.dumps(step) + "\n")
        return {
            "recorded": True,
            "session_id": session_id,
            "step_number": step_number,
            "timestamp": step["timestamp"],
        }
    except OSError as e:
        logger.error("session_record_failed: %s", e)
        return {"recorded": False, "session_id": session_id, "error": str(e)}


async def research_session_replay(
    session_id: str,
) -> dict[str, Any]:
    """Load and return the full session timeline.

    Returns:
        {session_id, steps: [step dicts], total_steps, total_duration_ms}
    """
    session_file = _get_replay_dir() / f"{session_id}.jsonl"
    steps = _load_jsonl_steps(session_file)

    if not steps and not session_file.exists():
        return {
            "session_id": session_id,
            "steps": [],
            "total_steps": 0,
            "total_duration_ms": 0.0,
            "error": f"Session not found: {session_id}",
        }

    total_duration = sum(s.get("duration_ms", 0) for s in steps)
    return {
        "session_id": session_id,
        "steps": steps,
        "total_steps": len(steps),
        "total_duration_ms": round(total_duration, 2),
    }


async def research_session_list() -> dict[str, Any]:
    """List all recorded sessions with metadata.

    Returns:
        {sessions: [{id, steps_count, total_duration_ms, first_step_at, last_step_at}], total_sessions}
    """
    replay_dir = _get_replay_dir()
    sessions = []

    for session_file in sorted(replay_dir.glob("*.jsonl")):
        steps = _load_jsonl_steps(session_file)
        if steps:
            total_duration = sum(s.get("duration_ms", 0) for s in steps)
            sessions.append({
                "id": session_file.stem,
                "steps_count": len(steps),
                "total_duration_ms": round(total_duration, 2),
                "first_step_at": steps[0].get("timestamp", ""),
                "last_step_at": steps[-1].get("timestamp", ""),
            })

    return {
        "sessions": sessions,
        "total_sessions": len(sessions),
    }
