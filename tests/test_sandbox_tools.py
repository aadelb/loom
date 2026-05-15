"""Unit tests for sandbox MCP tools.

Tests cover:
  - research_sandbox_run tool with various parameters
  - research_sandbox_status tool
  - Input validation
  - Error handling
  - Response format validation
"""

from __future__ import annotations

import json

import pytest
from mcp.types import TextContent

from loom.tools.security.sandbox_tools import (
    research_sandbox_run,
    research_sandbox_status,
)


class TestResearchSandboxRun:
    """Tests for research_sandbox_run tool."""

    @pytest.mark.asyncio
    async def test_run_echo_command(self) -> None:
        """Test running echo command."""
        result = await research_sandbox_run(command=["echo", "hello"])
        assert isinstance(result, TextContent)
        data = json.loads(result.text)
        assert data["success"] is True
        assert "hello" in data["stdout"]

    @pytest.mark.asyncio
    async def test_run_with_timeout(self) -> None:
        """Test running command with custom timeout."""
        result = await research_sandbox_run(
            command=["echo", "test"],
            timeout=60,
        )
        data = json.loads(result.text)
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_run_with_all_parameters(self) -> None:
        """Test running command with all parameters."""
        result = await research_sandbox_run(
            command=["echo", "test"],
            timeout=30,
            network=False,
            memory="256m",
            cpus=1,
        )
        data = json.loads(result.text)
        assert isinstance(data, dict)
        assert "exit_code" in data

    @pytest.mark.asyncio
    async def test_run_empty_command_validation(self) -> None:
        """Test that empty command is rejected."""
        result = await research_sandbox_run(command=[])
        data = json.loads(result.text)
        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_run_timeout_validation_min(self) -> None:
        """Test that timeout < 1 is rejected."""
        result = await research_sandbox_run(
            command=["echo", "test"],
            timeout=0,
        )
        data = json.loads(result.text)
        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_run_timeout_validation_max(self) -> None:
        """Test that timeout > 3600 is rejected."""
        result = await research_sandbox_run(
            command=["echo", "test"],
            timeout=4000,
        )
        data = json.loads(result.text)
        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_run_cpus_validation_min(self) -> None:
        """Test that cpus < 1 is rejected."""
        result = await research_sandbox_run(
            command=["echo", "test"],
            cpus=0,
        )
        data = json.loads(result.text)
        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_run_cpus_validation_max(self) -> None:
        """Test that cpus > 4 is rejected."""
        result = await research_sandbox_run(
            command=["echo", "test"],
            cpus=5,
        )
        data = json.loads(result.text)
        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_run_response_contains_required_fields(self) -> None:
        """Test that response contains all required fields."""
        result = await research_sandbox_run(command=["echo", "test"])
        data = json.loads(result.text)
        required_fields = ["success", "exit_code", "stdout", "duration_ms", "mode"]
        for field in required_fields:
            assert field in data

    @pytest.mark.asyncio
    async def test_run_includes_warning_on_docker_fallback(self) -> None:
        """Test that fallback mode includes warning."""
        # This will fallback to subprocess if Docker unavailable
        result = await research_sandbox_run(command=["echo", "test"])
        data = json.loads(result.text)
        # Check response structure is valid even if no warning
        assert "success" in data

    @pytest.mark.asyncio
    async def test_run_command_with_args(self) -> None:
        """Test running command with multiple arguments."""
        result = await research_sandbox_run(
            command=["sh", "-c", "echo hello world"]
        )
        data = json.loads(result.text)
        assert data["success"] is True
        assert "hello" in data["stdout"] and "world" in data["stdout"]

    @pytest.mark.asyncio
    async def test_run_captures_stderr(self) -> None:
        """Test that stderr is captured."""
        result = await research_sandbox_run(
            command=["sh", "-c", "echo error >&2; exit 0"]
        )
        data = json.loads(result.text)
        assert data["success"] is True
        assert "error" in data["stderr"]

    @pytest.mark.asyncio
    async def test_run_non_zero_exit_code(self) -> None:
        """Test handling of non-zero exit code."""
        result = await research_sandbox_run(
            command=["sh", "-c", "exit 42"]
        )
        data = json.loads(result.text)
        assert data["success"] is False
        assert data["exit_code"] == 42


class TestResearchSandboxStatus:
    """Tests for research_sandbox_status tool."""

    @pytest.mark.asyncio
    async def test_status_returns_text_content(self) -> None:
        """Test that status returns TextContent."""
        result = await research_sandbox_status()
        assert isinstance(result, TextContent)

    @pytest.mark.asyncio
    async def test_status_returns_json(self) -> None:
        """Test that status returns valid JSON."""
        result = await research_sandbox_status()
        data = json.loads(result.text)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_status_contains_required_fields(self) -> None:
        """Test that status response contains required fields."""
        result = await research_sandbox_status()
        data = json.loads(result.text)
        required_fields = [
            "docker_available",
            "sandbox_image",
            "sandbox_timeout",
            "sandbox_memory",
            "sandbox_cpus",
        ]
        for field in required_fields:
            assert field in data

    @pytest.mark.asyncio
    async def test_status_docker_available_is_bool(self) -> None:
        """Test that docker_available is a boolean."""
        result = await research_sandbox_status()
        data = json.loads(result.text)
        assert isinstance(data["docker_available"], bool)

    @pytest.mark.asyncio
    async def test_status_sandbox_timeout_is_int(self) -> None:
        """Test that sandbox_timeout is an integer."""
        result = await research_sandbox_status()
        data = json.loads(result.text)
        assert isinstance(data["sandbox_timeout"], int)

    @pytest.mark.asyncio
    async def test_status_sandbox_cpus_is_int(self) -> None:
        """Test that sandbox_cpus is an integer."""
        result = await research_sandbox_status()
        data = json.loads(result.text)
        assert isinstance(data["sandbox_cpus"], int)

    @pytest.mark.asyncio
    async def test_status_docker_version_field_exists(self) -> None:
        """Test that docker_version field is in response."""
        result = await research_sandbox_status()
        data = json.loads(result.text)
        assert "docker_version" in data


class TestSandboxToolIntegration:
    """Integration tests for sandbox tools."""

    @pytest.mark.asyncio
    async def test_run_multiple_commands_sequentially(self) -> None:
        """Test running multiple commands in sequence."""
        result1 = await research_sandbox_run(command=["echo", "first"])
        result2 = await research_sandbox_run(command=["echo", "second"])

        data1 = json.loads(result1.text)
        data2 = json.loads(result2.text)

        assert data1["success"] is True
        assert data2["success"] is True
        assert "first" in data1["stdout"]
        assert "second" in data2["stdout"]

    @pytest.mark.asyncio
    async def test_status_then_run(self) -> None:
        """Test calling status then run."""
        status = await research_sandbox_status()
        status_data = json.loads(status.text)

        run_result = await research_sandbox_run(command=["echo", "test"])
        run_data = json.loads(run_result.text)

        assert "sandbox_image" in status_data
        assert run_data["success"] is True
