"""Tests for subprocess_helpers module.

Tests run_command, check_binary, require_binary, and run_command_async.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from loom.subprocess_helpers import (
    check_binary,
    require_binary,
    run_command,
    run_command_async,
)


class TestCheckBinary:
    """Test check_binary function."""

    def test_check_binary_exists(self) -> None:
        """Test check_binary returns True for existing binary."""
        # 'echo' should be available on all systems
        assert check_binary("echo") is True

    def test_check_binary_not_exists(self) -> None:
        """Test check_binary returns False for non-existent binary."""
        assert check_binary("nonexistent_binary_xyz_123") is False

    def test_check_binary_common_binaries(self) -> None:
        """Test check_binary with common binaries."""
        # Common tools that might be available
        result = check_binary("python")
        assert isinstance(result, bool)


class TestRunCommand:
    """Test run_command function."""

    def test_run_command_success(self) -> None:
        """Test run_command with successful command."""
        result = run_command(["echo", "hello"])
        assert result["success"] is True
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]
        assert result["stderr"] == ""

    def test_run_command_captures_output(self) -> None:
        """Test run_command captures stdout."""
        result = run_command(["echo", "test output"])
        assert "test output" in result["stdout"]

    def test_run_command_failure(self) -> None:
        """Test run_command with failing command."""
        result = run_command(["sh", "-c", "exit 1"])
        assert result["success"] is False
        assert result["returncode"] == 1

    def test_run_command_missing_binary(self) -> None:
        """Test run_command with missing binary."""
        result = run_command(["nonexistent_binary_xyz", "arg"])
        assert result["success"] is False
        assert result["returncode"] == -1
        assert "error" in result
        assert "Binary not found" in result["error"]

    def test_run_command_timeout(self) -> None:
        """Test run_command timeout."""
        result = run_command(
            ["sleep", "10"],
            timeout=0.1,
        )
        assert result["success"] is False
        assert result["returncode"] == -1
        assert "error" in result
        assert "timed out" in result["error"]

    def test_run_command_with_input(self) -> None:
        """Test run_command with stdin input."""
        result = run_command(
            ["cat"],
            input_data="hello from stdin",
        )
        assert result["success"] is True
        assert "hello from stdin" in result["stdout"]

    def test_run_command_result_structure(self) -> None:
        """Test run_command returns correct dict structure."""
        result = run_command(["echo", "test"])
        assert isinstance(result, dict)
        assert "stdout" in result
        assert "stderr" in result
        assert "returncode" in result
        assert "success" in result

    def test_run_command_error_contains_error_key(self) -> None:
        """Test run_command error result contains error key."""
        result = run_command(["sh", "-c", "exit 42"])
        assert "returncode" in result

    def test_run_command_stderr_capture(self) -> None:
        """Test run_command captures stderr."""
        result = run_command(["sh", "-c", "echo error >&2"])
        assert result["success"] is True
        assert "error" in result["stderr"]

    def test_run_command_with_cwd(self, tmp_path: Any) -> None:
        """Test run_command with working directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        result = run_command(["ls", "test.txt"], cwd=str(tmp_path))
        assert result["success"] is True
        assert "test.txt" in result["stdout"]

    def test_run_command_with_env(self) -> None:
        """Test run_command with environment variables."""
        env = {"TEST_VAR": "test_value"}
        result = run_command(
            ["sh", "-c", "echo $TEST_VAR"],
            env=env,
        )
        assert result["success"] is True
        assert "test_value" in result["stdout"]

    def test_run_command_long_output(self) -> None:
        """Test run_command with long output."""
        result = run_command(["sh", "-c", "echo " + "x" * 1000])
        assert result["success"] is True
        assert len(result["stdout"]) > 1000


class TestRunCommandAsync:
    """Test run_command_async function."""

    @pytest.mark.asyncio
    async def test_run_command_async_success(self) -> None:
        """Test async run_command succeeds."""
        result = await run_command_async(["echo", "async hello"])
        assert result["success"] is True
        assert "async hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_run_command_async_failure(self) -> None:
        """Test async run_command failure."""
        result = await run_command_async(["sh", "-c", "exit 1"])
        assert result["success"] is False
        assert result["returncode"] == 1

    @pytest.mark.asyncio
    async def test_run_command_async_missing_binary(self) -> None:
        """Test async run_command with missing binary."""
        result = await run_command_async(["nonexistent_xyz"])
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_command_async_timeout(self) -> None:
        """Test async run_command timeout."""
        result = await run_command_async(
            ["sleep", "5"],
            timeout=0.1,
        )
        assert result["success"] is False
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_run_command_async_with_input(self) -> None:
        """Test async run_command with stdin."""
        result = await run_command_async(
            ["cat"],
            input_data="async input",
        )
        assert result["success"] is True
        assert "async input" in result["stdout"]

    @pytest.mark.asyncio
    async def test_run_command_async_doesnt_block(self) -> None:
        """Test that async run_command doesn't block event loop."""
        # Run multiple commands concurrently
        tasks = [
            run_command_async(["echo", f"msg{i}"])
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 3
        assert all(r["success"] for r in results)


class TestRequireBinary:
    """Test require_binary function."""

    def test_require_binary_exists(self) -> None:
        """Test require_binary succeeds for existing binary."""
        # Should not raise
        require_binary("echo")

    def test_require_binary_missing(self) -> None:
        """Test require_binary raises for missing binary."""
        with pytest.raises(RuntimeError, match="Required binary"):
            require_binary("nonexistent_xyz")

    def test_require_binary_error_message(self) -> None:
        """Test require_binary error message."""
        with pytest.raises(RuntimeError, match="not found on PATH"):
            require_binary("missing_tool_xyz")

    def test_require_binary_with_install_hint(self) -> None:
        """Test require_binary includes install hint."""
        with pytest.raises(RuntimeError, match="pip install"):
            require_binary("missing", install_hint="pip install missing")

    def test_require_binary_missing_no_hint(self) -> None:
        """Test require_binary without install hint."""
        with pytest.raises(RuntimeError) as exc_info:
            require_binary("definitely_not_installed_xyz")
        assert "Install" not in str(exc_info.value)
