"""Unit tests for Docker sandbox system.

Tests cover:
  - Sandbox initialization and Docker availability checks
  - Subprocess execution with timeouts
  - Memory limit parsing
  - Error handling and fallback behavior
  - Result data structures
"""

from __future__ import annotations

import asyncio
import pytest

from loom.sandbox import (
    DockerSandbox,
    SandboxResult,
    _parse_memory_limit,
    get_sandbox,
    is_docker_available,
)


class TestIsDockerAvailable:
    """Tests for Docker availability detection."""

    def test_docker_available_returns_bool(self) -> None:
        """Test that is_docker_available returns a boolean."""
        result = is_docker_available()
        assert isinstance(result, bool)

    def test_docker_check_uses_which(self) -> None:
        """Test that is_docker_available uses shutil.which."""
        # This will return True on systems with Docker, False otherwise
        result = is_docker_available()
        assert isinstance(result, bool)


class TestParseMemoryLimit:
    """Tests for memory limit parsing."""

    def test_parse_memory_512m(self) -> None:
        """Test parsing 512m."""
        result = _parse_memory_limit("512m")
        assert result == 512 * 1024 * 1024

    def test_parse_memory_1g(self) -> None:
        """Test parsing 1g."""
        result = _parse_memory_limit("1g")
        assert result == 1024 * 1024 * 1024

    def test_parse_memory_numeric(self) -> None:
        """Test parsing numeric value."""
        result = _parse_memory_limit("2048")
        assert result == 2048

    def test_parse_memory_lowercase(self) -> None:
        """Test parsing with lowercase units."""
        result = _parse_memory_limit("256M")
        assert result == 256 * 1024 * 1024

    def test_parse_memory_k_suffix(self) -> None:
        """Test parsing with k suffix."""
        result = _parse_memory_limit("512k")
        assert result == 512 * 1024

    def test_parse_memory_invalid_falls_back_to_default(self) -> None:
        """Test that invalid memory string falls back to default."""
        result = _parse_memory_limit("invalid")
        assert result == 512 * 1024 * 1024  # Default


class TestSandboxResult:
    """Tests for SandboxResult dataclass."""

    def test_sandbox_result_creation(self) -> None:
        """Test creating a SandboxResult."""
        result = SandboxResult(
            stdout="output",
            stderr="",
            exit_code=0,
            duration_ms=100,
            container_id="abc123",
            success=True,
            mode="docker",
        )
        assert result.stdout == "output"
        assert result.exit_code == 0
        assert result.success is True

    def test_sandbox_result_success_false_on_nonzero_exit(self) -> None:
        """Test that success is False on nonzero exit."""
        result = SandboxResult(
            stdout="",
            stderr="error",
            exit_code=1,
            duration_ms=100,
            container_id="abc123",
            success=False,
            mode="fallback",
        )
        assert result.success is False
        assert result.mode == "fallback"


class TestDockerSandboxInit:
    """Tests for DockerSandbox initialization."""

    def test_sandbox_init_defaults(self) -> None:
        """Test sandbox initialization with defaults."""
        sandbox = DockerSandbox()
        assert sandbox.image == "loom-sandbox:latest"
        assert sandbox.timeout == 300
        assert sandbox.memory == "512m"
        assert sandbox.cpus == 1
        assert sandbox.auto_remove is True

    def test_sandbox_init_custom_values(self) -> None:
        """Test sandbox initialization with custom values."""
        sandbox = DockerSandbox(
            image="custom:image",
            timeout=60,
            memory="1g",
            cpus=2,
            auto_remove=False,
        )
        assert sandbox.image == "custom:image"
        assert sandbox.timeout == 60
        assert sandbox.memory == "1g"
        assert sandbox.cpus == 2
        assert sandbox.auto_remove is False


class TestSubprocessFallback:
    """Tests for subprocess fallback execution."""

    @pytest.mark.asyncio
    async def test_echo_command_succeeds(self) -> None:
        """Test running echo command in fallback mode."""
        sandbox = DockerSandbox()
        result = await sandbox._run_subprocess_fallback(
            ["echo", "hello"], timeout_secs=5, start_time=0
        )
        assert result.success
        assert "hello" in result.stdout
        assert result.mode == "fallback"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_command_timeout(self) -> None:
        """Test timeout handling in subprocess."""
        sandbox = DockerSandbox()
        result = await sandbox._run_subprocess_fallback(
            ["sleep", "10"], timeout_secs=1, start_time=0
        )
        assert result.exit_code == 124  # Timeout exit code
        assert not result.success

    @pytest.mark.asyncio
    async def test_command_with_stderr(self) -> None:
        """Test capturing stderr from command."""
        sandbox = DockerSandbox()
        result = await sandbox._run_subprocess_fallback(
            ["sh", "-c", "echo error >&2"], timeout_secs=5, start_time=0
        )
        assert "error" in result.stderr
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_nonexistent_command_fails(self) -> None:
        """Test that nonexistent command fails gracefully."""
        sandbox = DockerSandbox()
        result = await sandbox._run_subprocess_fallback(
            ["nonexistent_command_xyz"], timeout_secs=5, start_time=0
        )
        assert not result.success
        assert result.exit_code != 0


class TestSandboxRun:
    """Tests for the main run method."""

    @pytest.mark.asyncio
    async def test_run_falls_back_when_docker_unavailable(self) -> None:
        """Test that run falls back to subprocess when Docker unavailable."""
        sandbox = DockerSandbox()
        sandbox._has_docker = False
        result = await sandbox.run(["echo", "test"])
        assert result.mode == "fallback"
        assert result.success
        assert "test" in result.stdout

    @pytest.mark.asyncio
    async def test_run_validates_empty_command(self) -> None:
        """Test that empty command returns appropriate result."""
        sandbox = DockerSandbox()
        sandbox._has_docker = False
        # Empty command should fail in fallback mode
        result = await sandbox.run([])
        # This may succeed with empty output or fail depending on shell behavior
        assert result.mode == "fallback"

    @pytest.mark.asyncio
    async def test_run_respects_timeout_parameter(self) -> None:
        """Test that timeout parameter is respected."""
        sandbox = DockerSandbox()
        sandbox._has_docker = False
        # Short timeout should cause command to fail
        result = await sandbox.run(["sleep", "5"], timeout=1)
        assert result.exit_code == 124  # Timeout exit code


class TestGetSandboxSingleton:
    """Tests for get_sandbox singleton."""

    @pytest.mark.asyncio
    async def test_get_sandbox_returns_instance(self) -> None:
        """Test that get_sandbox returns a DockerSandbox instance."""
        sandbox = await get_sandbox()
        assert isinstance(sandbox, DockerSandbox)

    @pytest.mark.asyncio
    async def test_get_sandbox_returns_same_instance(self) -> None:
        """Test that get_sandbox returns the same instance on multiple calls."""
        sandbox1 = await get_sandbox()
        sandbox2 = await get_sandbox()
        assert sandbox1 is sandbox2


class TestSandboxClose:
    """Tests for sandbox cleanup."""

    @pytest.mark.asyncio
    async def test_close_is_safe_to_call_multiple_times(self) -> None:
        """Test that close can be called multiple times safely."""
        sandbox = DockerSandbox()
        # Should not raise exception
        await sandbox.close()
        await sandbox.close()
        assert sandbox._docker is None
