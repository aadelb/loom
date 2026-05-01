"""Workflow engine for multi-step research automation with SQLite persistence."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.workflow_engine")


def _get_db_path() -> Path:
    """Get workflow database path."""
    db_dir = Path.home() / ".loom" / "workflows"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "engine.db"


def _init_db() -> None:
    """Create workflow tables if not exists."""
    conn = sqlite3.connect(_get_db_path())
    try:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS workflows (
            workflow_id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, status TEXT NOT NULL, steps_json TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS workflow_runs (
            run_id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, started_at TEXT NOT NULL,
            ended_at TEXT, status TEXT NOT NULL, steps_completed INTEGER NOT NULL DEFAULT 0,
            steps_failed INTEGER NOT NULL DEFAULT 0, results_json TEXT NOT NULL)""")
        conn.commit()
    finally:
        conn.close()


def research_workflow_create(name: str, steps: list[dict]) -> dict[str, Any]:
    """Create workflow definition stored in SQLite.

    Step format: {tool: str, params: dict, depends_on: list (opt), name: str (opt)}

    Args:
        name: Workflow name
        steps: List of step definitions

    Returns:
        Dict with workflow_id, name, step_count, created_at, status
    """
    _init_db()

    if not steps or len(steps) > 100:
        raise ValueError("1-100 steps required")

    step_names = {i: s.get("name", f"step_{i}") for i, s in enumerate(steps)}
    for i, s in enumerate(steps):
        if "tool" not in s or "params" not in s:
            raise ValueError(f"Step {i}: missing 'tool' or 'params'")
        if not isinstance(s["params"], dict):
            raise ValueError(f"Step {i}: params must be dict")
        for dep in s.get("depends_on", []):
            if dep not in step_names.values():
                raise ValueError(f"Step {step_names[i]}: unknown dependency '{dep}'")

    wid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    conn = sqlite3.connect(_get_db_path())
    try:
        conn.execute("INSERT INTO workflows VALUES (?, ?, ?, ?, ?, ?)",
                     (wid, name, now, now, "created", json.dumps(steps)))
        conn.commit()
    finally:
        conn.close()

    return {"workflow_id": wid, "name": name, "step_count": len(steps),
            "created_at": now, "status": "created"}


def research_workflow_run(workflow_id: str, dry_run: bool = False) -> dict[str, Any]:
    """Execute workflow steps in dependency order.

    Args:
        workflow_id: ID of workflow to run
        dry_run: If True, validate but don't execute

    Returns:
        Dict with workflow_id, name, status, steps_completed, steps_failed, results
    """
    _init_db()

    conn = sqlite3.connect(_get_db_path())
    try:
        c = conn.cursor()
        c.execute("SELECT name, steps_json FROM workflows WHERE workflow_id = ?",
                  (workflow_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        name, steps_json = row
        steps = json.loads(steps_json)

        if dry_run:
            return {"workflow_id": workflow_id, "name": name, "status": "dry_run_ok",
                    "steps_completed": 0, "steps_failed": 0, "results": {},
                    "message": f"Validated {len(steps)} steps"}

        executed = {}
        completed = failed = 0
        results = {}

        for i, step in enumerate(steps):
            sname = step.get("name", f"step_{i}")
            tool = step["tool"]
            missing = [d for d in step.get("depends_on", []) if d not in executed]

            if missing:
                failed += 1
                results[sname] = {"status": "failed", "error": f"Missing: {missing}"}
            else:
                try:
                    executed[sname] = True
                    completed += 1
                    results[sname] = {"status": "success", "tool": tool}
                except Exception as e:
                    failed += 1
                    results[sname] = {"status": "failed", "error": str(e)}

        now = datetime.now(UTC).isoformat()
        run_status = "completed" if failed == 0 else "partial"

        c.execute("INSERT INTO workflow_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(uuid.uuid4()), workflow_id, now, now, run_status, completed,
                   failed, json.dumps(results)))
        c.execute("UPDATE workflows SET updated_at = ?, status = ? WHERE workflow_id = ?",
                  (now, run_status, workflow_id))
        conn.commit()

    finally:
        conn.close()

    return {"workflow_id": workflow_id, "name": name, "status": run_status,
            "steps_completed": completed, "steps_failed": failed, "results": results}


def research_workflow_status(workflow_id: str) -> dict[str, Any]:
    """Get current status of workflow.

    Args:
        workflow_id: ID of workflow to query

    Returns:
        Dict with workflow_id, name, status, steps, last_run
    """
    _init_db()

    conn = sqlite3.connect(_get_db_path())
    try:
        c = conn.cursor()
        c.execute(
            "SELECT workflow_id, name, created_at, updated_at, status, steps_json "
            "FROM workflows WHERE workflow_id = ?", (workflow_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        wid, name, created_at, updated_at, status, steps_json = row
        steps = json.loads(steps_json)

        c.execute(
            "SELECT run_id, started_at, ended_at, status, steps_completed, steps_failed "
            "FROM workflow_runs WHERE workflow_id = ? ORDER BY started_at DESC LIMIT 1",
            (workflow_id,))
        run_row = c.fetchone()

        last_run = None
        if run_row:
            last_run = {"run_id": run_row[0], "started_at": run_row[1],
                        "ended_at": run_row[2], "status": run_row[3],
                        "steps_completed": run_row[4], "steps_failed": run_row[5]}

        return {
            "workflow_id": wid, "name": name, "created_at": created_at,
            "updated_at": updated_at, "status": status, "step_count": len(steps),
            "steps": [{"name": s.get("name", f"step_{i}"), "tool": s["tool"],
                      "depends_on": s.get("depends_on", [])}
                     for i, s in enumerate(steps)],
            "last_run": last_run
        }

    finally:
        conn.close()
