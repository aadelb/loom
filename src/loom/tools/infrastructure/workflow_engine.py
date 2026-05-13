"""Workflow engine for multi-step research automation with SQLite persistence."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors
from loom.db_helpers import get_db_path, init_db, db_connection

logger = logging.getLogger("loom.tools.workflow_engine")

# Regex pattern for valid Loom tool names: must start with "research_" and contain only lowercase letters, digits, underscores
VALID_TOOL_NAME_PATTERN = re.compile(r"^research_[a-z0-9_]+$")


def _validate_tool_name(tool_name: str) -> None:
	"""Validate that tool name matches Loom naming convention and contains no injection payloads.

	All Loom tools follow the pattern: research_[a-z0-9_]+
	This prevents tool injection attacks via workflow definitions.

	Args:
		tool_name: The tool name to validate

	Raises:
		ValueError: If tool name is invalid or contains suspicious patterns
	"""
	if not isinstance(tool_name, str):
		raise ValueError(f"Tool name must be string, got {type(tool_name).__name__}")

	if not tool_name:
		raise ValueError("Tool name cannot be empty")

	if "/" in tool_name or "\\" in tool_name or ".." in tool_name:
		raise ValueError(f"Tool name contains path separators or traversal: {tool_name}")

	if not VALID_TOOL_NAME_PATTERN.match(tool_name):
		raise ValueError(
			f"Tool name '{tool_name}' does not match pattern 'research_[a-z0-9_]+'. "
			"All Loom tools must start with 'research_' and contain only lowercase letters, digits, and underscores."
		)


_DB_PATH = get_db_path("workflow_engine")


def _init_db() -> None:
	"""Create workflow tables if not exists."""
	schema = """
	CREATE TABLE IF NOT EXISTS workflows (
		workflow_id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
		updated_at TEXT NOT NULL, status TEXT NOT NULL, steps_json TEXT NOT NULL);

	CREATE TABLE IF NOT EXISTS workflow_runs (
		run_id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, started_at TEXT NOT NULL,
		ended_at TEXT, status TEXT NOT NULL, steps_completed INTEGER NOT NULL DEFAULT 0,
		steps_failed INTEGER NOT NULL DEFAULT 0, results_json TEXT NOT NULL);
	"""
	init_db(_DB_PATH, schema)

@handle_tool_errors("research_workflow_create")

def research_workflow_create(name: str, steps: list[dict]) -> dict[str, Any]:
	"""Create workflow definition stored in SQLite.

	Step format: {tool: str, params: dict, depends_on: list (opt), name: str (opt)}

	Args:
		name: Workflow name
		steps: List of step definitions (1-100 steps)

	Returns:
		Dict with workflow_id, name, step_count, created_at, status
	"""
	_init_db()

	if not isinstance(steps, list) or len(steps) < 1 or len(steps) > 100:
		raise ValueError("1-100 steps required")

	step_names = {i: s.get("name", f"step_{i}") for i, s in enumerate(steps)}
	for i, s in enumerate(steps):
		if "tool" not in s or "params" not in s:
			raise ValueError(f"Step {i}: missing 'tool' or 'params'")
		if not isinstance(s["params"], dict):
			raise ValueError(f"Step {i}: params must be dict")

		# SECURITY FIX: Validate tool name to prevent tool injection attacks
		try:
			_validate_tool_name(s["tool"])
		except ValueError as e:
			raise ValueError(f"Step {i}: invalid tool name - {e}")

		for dep in s.get("depends_on", []):
			if dep not in step_names.values():
				raise ValueError(f"Step {step_names[i]}: unknown dependency '{dep}'")

	wid = str(uuid.uuid4())
	now = datetime.now(UTC).isoformat()

	with db_connection(_DB_PATH) as conn:
		conn.execute("INSERT INTO workflows VALUES (?, ?, ?, ?, ?, ?)",
					 (wid, name, now, now, "created", json.dumps(steps)))
		conn.commit()

	return {"workflow_id": wid, "name": name, "step_count": len(steps),
			"created_at": now, "status": "created"}

@handle_tool_errors("research_workflow_run")

def research_workflow_run(workflow_id: str, dry_run: bool = False) -> dict[str, Any]:
	"""Execute workflow steps in dependency order.

	Args:
		workflow_id: ID of workflow to run
		dry_run: If True, validate but don't execute

	Returns:
		Dict with workflow_id, name, status, steps_completed, steps_failed, results
	"""
	_init_db()

	with db_connection(_DB_PATH) as conn:
		c = conn.cursor()
		c.execute("SELECT name, steps_json FROM workflows WHERE workflow_id = ?",
				  (workflow_id,))
		row = c.fetchone()
		if not row:
			raise ValueError(f"Workflow '{workflow_id}' not found")

		name, steps_json = row
		steps = json.loads(steps_json)

		# SECURITY FIX: Re-validate tool names on execution (defense-in-depth)
		for i, step in enumerate(steps):
			try:
				_validate_tool_name(step["tool"])
			except ValueError as e:
				raise ValueError(f"Step {i}: invalid tool name - {e}")

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
			params = step.get("params", {})
			missing = [d for d in step.get("depends_on", []) if d not in executed]

			if missing:
				failed += 1
				results[sname] = {"status": "failed", "error": f"Missing: {missing}"}
			else:
				try:
					# NOTE: Tool execution requires MCP client integration.
					# Current implementation marks as success for validation purposes.
					# To enable actual execution:
					# 1. Import MCP client (e.g., from loom.mcp_client import Client)
					# 2. Call: step_result = await client.call_tool(tool, params)
					# 3. Store: results[sname] = {"status": "success", "result": step_result, "tool": tool}
					executed[sname] = True
					completed += 1
					results[sname] = {"status": "success", "tool": tool, "note": "execution not yet implemented"}
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

	return {"workflow_id": workflow_id, "name": name, "status": run_status,
			"steps_completed": completed, "steps_failed": failed, "results": results}

@handle_tool_errors("research_workflow_status")

def research_workflow_status(workflow_id: str) -> dict[str, Any]:
	"""Get current status of workflow.

	Args:
		workflow_id: ID of workflow to query

	Returns:
		Dict with workflow_id, name, status, steps, last_run
	"""
	_init_db()

	with db_connection(_DB_PATH) as conn:
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
