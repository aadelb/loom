"""Unit tests for workflow engine tools."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from loom.db_helpers import get_db_path as _get_db_path
from loom.tools.infrastructure.workflow_engine import (
    research_workflow_create,
    research_workflow_run,
    research_workflow_status,
    _init_db,
)


@pytest.fixture(autouse=True)
def cleanup_workflow_db() -> None:
    """Remove workflow database before and after each test."""
    db_path = _get_db_path()
    if db_path.exists():
        db_path.unlink()
    yield
    if db_path.exists():
        db_path.unlink()


class TestWorkflowCreate:
    """research_workflow_create creates valid workflow definitions."""

    def test_create_simple_workflow(self) -> None:
        """Create workflow with single step."""
        result = research_workflow_create(
            name="Test Workflow",
            steps=[
                {"tool": "research_fetch", "params": {"url": "https://example.com"}}
            ],
        )

        assert result["workflow_id"]
        assert result["name"] == "Test Workflow"
        assert result["step_count"] == 1
        assert result["status"] == "created"
        assert result["created_at"]

    def test_create_workflow_with_dependencies(self) -> None:
        """Create workflow with step dependencies."""
        result = research_workflow_create(
            name="Multi-step Workflow",
            steps=[
                {
                    "name": "fetch_data",
                    "tool": "research_fetch",
                    "params": {"url": "https://example.com"},
                },
                {
                    "name": "process_data",
                    "tool": "research_markdown",
                    "params": {},
                    "depends_on": ["fetch_data"],
                },
            ],
        )

        assert result["step_count"] == 2
        assert result["status"] == "created"

    def test_create_workflow_persisted(self) -> None:
        """Created workflow is persisted to database."""
        result = research_workflow_create(
            name="Persistent Workflow",
            steps=[{"tool": "research_search", "params": {"query": "test"}}],
        )

        workflow_id = result["workflow_id"]

        # Verify in database
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, status FROM workflows WHERE workflow_id = ?",
                (workflow_id,),
            )
            row = cursor.fetchone()
            assert row
            assert row[0] == "Persistent Workflow"
            assert row[1] == "created"
        finally:
            conn.close()

    def test_create_workflow_empty_steps_error(self) -> None:
        """Create with empty steps list raises error."""
        with pytest.raises(ValueError, match="At least one step required"):
            research_workflow_create(name="Bad Workflow", steps=[])

    def test_create_workflow_missing_tool_error(self) -> None:
        """Create with step missing 'tool' raises error."""
        with pytest.raises(ValueError, match="missing 'tool'"):
            research_workflow_create(
                name="Bad Workflow",
                steps=[{"params": {"url": "https://example.com"}}],
            )

    def test_create_workflow_missing_params_error(self) -> None:
        """Create with step missing 'params' raises error."""
        with pytest.raises(ValueError, match="missing 'params'"):
            research_workflow_create(
                name="Bad Workflow",
                steps=[{"tool": "research_fetch"}],
            )

    def test_create_workflow_invalid_depends_on_error(self) -> None:
        """Create with unknown dependency raises error."""
        with pytest.raises(ValueError, match="unknown dependency"):
            research_workflow_create(
                name="Bad Workflow",
                steps=[
                    {
                        "name": "step1",
                        "tool": "research_fetch",
                        "params": {},
                        "depends_on": ["nonexistent"],
                    },
                ],
            )

    def test_create_workflow_max_steps_error(self) -> None:
        """Create with > 100 steps raises error."""
        with pytest.raises(ValueError, match="max 100 steps"):
            research_workflow_create(
                name="Too Many Steps",
                steps=[
                    {"tool": "research_fetch", "params": {}}
                    for _ in range(101)
                ],
            )


class TestWorkflowRun:
    """research_workflow_run executes workflows and tracks execution."""

    def test_run_simple_workflow(self) -> None:
        """Run single-step workflow completes successfully."""
        create_result = research_workflow_create(
            name="Simple Run Test",
            steps=[
                {"tool": "research_fetch", "params": {"url": "https://example.com"}}
            ],
        )

        result = research_workflow_run(create_result["workflow_id"])

        assert result["workflow_id"] == create_result["workflow_id"]
        assert result["status"] == "completed"
        assert result["steps_completed"] == 1
        assert result["steps_failed"] == 0
        assert result["results"]

    def test_run_workflow_dry_run(self) -> None:
        """Dry run validates without executing."""
        create_result = research_workflow_create(
            name="Dry Run Test",
            steps=[
                {"tool": "research_fetch", "params": {"url": "https://example.com"}},
                {"tool": "research_markdown", "params": {}},
            ],
        )

        result = research_workflow_run(create_result["workflow_id"], dry_run=True)

        assert result["status"] == "dry_run_ok"
        assert result["steps_completed"] == 0
        assert result["message"]

    def test_run_workflow_with_dependencies(self) -> None:
        """Run multi-step workflow respects dependencies."""
        create_result = research_workflow_create(
            name="Multi-step Run Test",
            steps=[
                {
                    "name": "fetch",
                    "tool": "research_fetch",
                    "params": {"url": "https://example.com"},
                },
                {
                    "name": "process",
                    "tool": "research_markdown",
                    "params": {},
                    "depends_on": ["fetch"],
                },
            ],
        )

        result = research_workflow_run(create_result["workflow_id"])

        assert result["status"] == "completed"
        assert result["steps_completed"] == 2
        assert result["results"]["fetch"]["status"] == "success"
        assert result["results"]["process"]["status"] == "success"

    def test_run_nonexistent_workflow_error(self) -> None:
        """Run nonexistent workflow raises error."""
        with pytest.raises(ValueError, match="not found"):
            research_workflow_run("nonexistent-id")

    def test_run_workflow_missing_dependency_fails(self) -> None:
        """Run with missing dependency fails that step."""
        create_result = research_workflow_create(
            name="Bad Dependency Run",
            steps=[
                {
                    "name": "step1",
                    "tool": "research_fetch",
                    "params": {},
                    "depends_on": ["nonexistent"],
                },
            ],
        )

        result = research_workflow_run(create_result["workflow_id"])

        assert result["status"] == "partial"
        assert result["steps_failed"] == 1
        assert "Missing dependencies" in result["results"]["step1"]["error"]

    def test_run_workflow_persisted(self) -> None:
        """Workflow run is persisted to database."""
        create_result = research_workflow_create(
            name="Persistence Test",
            steps=[{"tool": "research_fetch", "params": {"url": "https://example.com"}}],
        )

        run_result = research_workflow_run(create_result["workflow_id"])

        # Verify run in database
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, steps_completed FROM workflow_runs WHERE workflow_id = ?",
                (create_result["workflow_id"],),
            )
            row = cursor.fetchone()
            assert row
            assert row[0] == run_result["status"]
            assert row[1] == run_result["steps_completed"]
        finally:
            conn.close()


class TestWorkflowStatus:
    """research_workflow_status returns workflow information."""

    def test_status_simple_workflow(self) -> None:
        """Get status of simple workflow."""
        create_result = research_workflow_create(
            name="Status Test",
            steps=[{"tool": "research_fetch", "params": {"url": "https://example.com"}}],
        )

        result = research_workflow_status(create_result["workflow_id"])

        assert result["workflow_id"] == create_result["workflow_id"]
        assert result["name"] == "Status Test"
        assert result["status"] == "created"
        assert result["step_count"] == 1
        assert result["created_at"]
        assert result["updated_at"]
        assert result["steps"]
        assert result["last_run"] is None

    def test_status_after_run(self) -> None:
        """Get status after workflow execution."""
        create_result = research_workflow_create(
            name="Status After Run",
            steps=[
                {
                    "name": "fetch",
                    "tool": "research_fetch",
                    "params": {"url": "https://example.com"},
                }
            ],
        )

        research_workflow_run(create_result["workflow_id"])
        result = research_workflow_status(create_result["workflow_id"])

        assert result["status"] == "completed"
        assert result["last_run"] is not None
        assert result["last_run"]["status"] == "completed"
        assert result["last_run"]["steps_completed"] == 1
        assert result["last_run"]["steps_failed"] == 0

    def test_status_workflow_steps_info(self) -> None:
        """Status includes detailed step information."""
        create_result = research_workflow_create(
            name="Steps Info Test",
            steps=[
                {
                    "name": "step1",
                    "tool": "research_fetch",
                    "params": {"url": "https://example.com"},
                },
                {
                    "name": "step2",
                    "tool": "research_markdown",
                    "params": {},
                    "depends_on": ["step1"],
                },
            ],
        )

        result = research_workflow_status(create_result["workflow_id"])

        assert len(result["steps"]) == 2
        assert result["steps"][0]["name"] == "step1"
        assert result["steps"][0]["tool"] == "research_fetch"
        assert result["steps"][0]["depends_on"] == []
        assert result["steps"][1]["name"] == "step2"
        assert result["steps"][1]["depends_on"] == ["step1"]

    def test_status_nonexistent_workflow_error(self) -> None:
        """Get status of nonexistent workflow raises error."""
        with pytest.raises(ValueError, match="not found"):
            research_workflow_status("nonexistent-id")

    def test_status_multiple_runs(self) -> None:
        """Status shows latest run."""
        create_result = research_workflow_create(
            name="Multiple Runs Test",
            steps=[{"tool": "research_fetch", "params": {"url": "https://example.com"}}],
        )

        # Run twice
        research_workflow_run(create_result["workflow_id"])
        research_workflow_run(create_result["workflow_id"])

        result = research_workflow_status(create_result["workflow_id"])

        assert result["last_run"] is not None
        assert result["last_run"]["steps_completed"] == 1


class TestWorkflowIntegration:
    """Integration tests for complete workflow lifecycle."""

    def test_workflow_lifecycle(self) -> None:
        """Full workflow lifecycle: create → run → status."""
        # Create
        create_result = research_workflow_create(
            name="Lifecycle Test",
            steps=[
                {
                    "name": "search",
                    "tool": "research_search",
                    "params": {"query": "test"},
                },
                {
                    "name": "fetch",
                    "tool": "research_fetch",
                    "params": {"url": "https://example.com"},
                    "depends_on": ["search"],
                },
            ],
        )

        workflow_id = create_result["workflow_id"]
        assert create_result["status"] == "created"

        # Check status before run
        status_before = research_workflow_status(workflow_id)
        assert status_before["status"] == "created"
        assert status_before["last_run"] is None

        # Run
        run_result = research_workflow_run(workflow_id)
        assert run_result["status"] == "completed"

        # Check status after run
        status_after = research_workflow_status(workflow_id)
        assert status_after["status"] == "completed"
        assert status_after["last_run"] is not None
        assert status_after["last_run"]["steps_completed"] == 2

    def test_workflow_with_step_defaults(self) -> None:
        """Workflow handles default step names."""
        result = research_workflow_create(
            name="Default Names",
            steps=[
                {"tool": "research_fetch", "params": {"url": "https://example.com"}},
                {"tool": "research_markdown", "params": {}},
            ],
        )

        status = research_workflow_status(result["workflow_id"])

        assert status["steps"][0]["name"] == "step_0"
        assert status["steps"][1]["name"] == "step_1"

    def test_workflow_complex_dependencies(self) -> None:
        """Workflow with multiple dependencies."""
        result = research_workflow_create(
            name="Complex Dependencies",
            steps=[
                {"name": "a", "tool": "research_fetch", "params": {}},
                {"name": "b", "tool": "research_fetch", "params": {}},
                {
                    "name": "c",
                    "tool": "research_markdown",
                    "params": {},
                    "depends_on": ["a", "b"],
                },
            ],
        )

        run_result = research_workflow_run(result["workflow_id"])

        assert run_result["steps_completed"] == 3
        assert run_result["status"] == "completed"
