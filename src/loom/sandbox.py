"""Docker sandbox system for isolating dangerous subprocess tools.

Runs commands in ephemeral Docker containers to prevent filesystem access
by compromised tools. Supports network isolation, memory limits, CPU limits,
and fallback to direct subprocess when Docker is unavailable.

Public API:
  DockerSandbox — async class for running commands in isolated containers
  get_sandbox() — singleton getter
  is_docker_available() — check Docker availability
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiodocker
from aiodocker.exceptions import DockerError

logger = logging.getLogger("loom.sandbox")

# Module-level singleton
_sandbox_instance: DockerSandbox | None = None
_sandbox_lock = asyncio.Lock()


def is_docker_available() -> bool:
    """Check if Docker is available on the system.

    Attempts to find docker in PATH and verify it's executable.

    Returns:
        True if Docker is available, False otherwise
    """
    return shutil.which("docker") is not None


@dataclass
class SandboxResult:
    """Result from a sandboxed command execution.

    Attributes:
        stdout: Standard output from the command
        stderr: Standard error from the command
        exit_code: Exit code of the command (0 = success)
        duration_ms: Total execution time in milliseconds
        container_id: ID of the Docker container (empty if fallback)
        success: True if exit_code == 0
        mode: "docker" or "fallback" (direct subprocess)
    """

    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    container_id: str
    success: bool
    mode: str


class DockerSandbox:
    """Isolate dangerous subprocess tools in ephemeral Docker containers.

    Manages lifecycle of sandboxed command execution with configurable
    resource limits, network isolation, and file I/O.

    Attributes:
        image: Docker image to use (default: loom-sandbox:latest)
        timeout: Default command timeout in seconds (default: 300)
        memory: Default memory limit (default: "512m")
        cpus: Default CPU limit (default: 1)
        auto_remove: Auto-remove container after execution (default: True)
    """

    def __init__(
        self,
        image: str = "loom-sandbox:latest",
        timeout: int = 300,
        memory: str = "512m",
        cpus: int = 1,
        auto_remove: bool = True,
    ):
        """Initialize DockerSandbox.

        Args:
            image: Docker image name (must exist)
            timeout: Default command timeout in seconds
            memory: Default memory limit (e.g., "512m", "1g")
            cpus: Default CPU limit in cores
            auto_remove: Whether to auto-remove containers
        """
        self.image = image
        self.timeout = timeout
        self.memory = memory
        self.cpus = cpus
        self.auto_remove = auto_remove
        self._docker: aiodocker.Docker | None = None
        self._has_docker = is_docker_available()

    async def _get_docker_client(self) -> aiodocker.Docker:
        """Get or create Docker client.

        Raises:
            DockerError: If Docker is not available or client fails to connect

        Returns:
            Connected Docker client
        """
        if self._docker is None:
            try:
                self._docker = aiodocker.Docker()
                # Test connection
                await self._docker.version()
            except Exception as e:
                logger.error("docker_client_connect_failed error=%s", e)
                raise DockerError(f"Failed to connect to Docker: {e}")
        return self._docker

    async def close(self) -> None:
        """Close Docker client connection.

        Safe to call multiple times.
        """
        if self._docker is not None:
            try:
                await self._docker.close()
            except Exception as e:
                logger.warning("docker_client_close_error error=%s", e)
            finally:
                self._docker = None

    async def run(
        self,
        command: list[str],
        timeout: int | None = None,
        network: bool = True,
        memory: str | None = None,
        cpus: int | None = None,
        env: dict[str, str] | None = None,
        working_dir: str | None = None,
    ) -> SandboxResult:
        """Run command in isolated Docker container.

        Args:
            command: Command to execute (list of strings, e.g., ["nmap", "-p", "80"])
            timeout: Command timeout in seconds (uses default if None)
            network: Enable network access (default: True, disable for dangerous tools)
            memory: Memory limit (uses default if None)
            cpus: CPU limit in cores (uses default if None)
            env: Environment variables to pass to container
            working_dir: Working directory inside container

        Returns:
            SandboxResult with stdout, stderr, exit_code, duration_ms, container_id
        """
        start_time = time.time()
        timeout_secs = timeout or self.timeout
        memory_limit = memory or self.memory
        cpu_limit = cpus or self.cpus

        # Fallback to direct subprocess if Docker not available
        if not self._has_docker:
            logger.warning(
                "docker_not_available falling_back_to_subprocess command=%s",
                command[0] if command else "?",
            )
            return await self._run_subprocess_fallback(command, timeout_secs, start_time)

        try:
            client = await self._get_docker_client()
            return await self._run_docker(
                client,
                command,
                timeout_secs,
                network,
                memory_limit,
                cpu_limit,
                env,
                working_dir,
                start_time,
            )
        except DockerError as e:
            logger.error(
                "docker_execution_failed falling_back_to_subprocess error=%s",
                e,
            )
            # Fallback to subprocess
            return await self._run_subprocess_fallback(command, timeout_secs, start_time)

    async def _run_docker(
        self,
        client: aiodocker.Docker,
        command: list[str],
        timeout_secs: int,
        network: bool,
        memory: str,
        cpus: int,
        env: dict[str, str] | None,
        working_dir: str | None,
        start_time: float,
    ) -> SandboxResult:
        """Execute command in Docker container.

        Args:
            client: Docker client
            command: Command to execute
            timeout_secs: Timeout in seconds
            network: Enable network
            memory: Memory limit
            cpus: CPU limit
            env: Environment variables
            working_dir: Working directory
            start_time: Command start time

        Returns:
            SandboxResult
        """
        container_id = ""
        container = None

        try:
            # Build container config
            config: dict[str, Any] = {
                "Cmd": command,
                "Image": self.image,
                "HostConfig": {
                    "Memory": _parse_memory_limit(memory),
                    "CpuShares": cpus * 1024,  # 1024 units per CPU
                    "AutoRemove": self.auto_remove,
                    "NetworkMode": "none" if not network else "bridge",
                },
            }

            if env:
                config["Env"] = [f"{k}={v}" for k, v in env.items()]

            if working_dir:
                config["WorkingDir"] = working_dir

            # Create container
            container = await client.containers.create_or_replace(
                name=f"loom-sandbox-{int(time.time() * 1000)}",
                config=config,
            )
            container_id = container["Id"][:12]  # Short ID for logging

            logger.debug(
                "sandbox_container_created container_id=%s command=%s",
                container_id,
                command[0] if command else "?",
            )

            # Start container
            await container.start()

            # Wait for completion with timeout
            try:
                exit_code = await asyncio.wait_for(
                    container.wait(), timeout=timeout_secs
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "sandbox_container_timeout container_id=%s timeout=%d",
                    container_id,
                    timeout_secs,
                )
                await container.kill()
                elapsed_ms = int((time.time() - start_time) * 1000)
                return SandboxResult(
                    stdout="",
                    stderr=f"Command timed out after {timeout_secs} seconds",
                    exit_code=124,  # Timeout exit code
                    duration_ms=elapsed_ms,
                    container_id=container_id,
                    success=False,
                    mode="docker",
                )

            # Get logs
            logs = await container.log(stdout=True, stderr=True)
            stdout_logs = logs[0] if logs else ""
            stderr_logs = logs[1] if len(logs) > 1 else ""

            elapsed_ms = int((time.time() - start_time) * 1000)

            logger.debug(
                "sandbox_container_completed container_id=%s exit_code=%d duration_ms=%d",
                container_id,
                exit_code,
                elapsed_ms,
            )

            return SandboxResult(
                stdout=stdout_logs,
                stderr=stderr_logs,
                exit_code=exit_code,
                duration_ms=elapsed_ms,
                container_id=container_id,
                success=exit_code == 0,
                mode="docker",
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "sandbox_container_error container_id=%s error=%s", container_id, e
            )
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                duration_ms=elapsed_ms,
                container_id=container_id,
                success=False,
                mode="docker",
            )
        finally:
            # Cleanup container if not auto-removed
            if container is not None and not self.auto_remove:
                try:
                    await container.delete()
                except Exception as e:
                    logger.warning("sandbox_container_cleanup_failed error=%s", e)

    async def _run_subprocess_fallback(
        self,
        command: list[str],
        timeout_secs: int,
        start_time: float,
    ) -> SandboxResult:
        """Fallback to direct subprocess execution (less isolated).

        Args:
            command: Command to execute
            timeout_secs: Timeout in seconds
            start_time: Command start time

        Returns:
            SandboxResult
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_secs
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                elapsed_ms = int((time.time() - start_time) * 1000)
                return SandboxResult(
                    stdout="",
                    stderr=f"Command timed out after {timeout_secs} seconds",
                    exit_code=124,
                    duration_ms=elapsed_ms,
                    container_id="",
                    success=False,
                    mode="fallback",
                )

            elapsed_ms = int((time.time() - start_time) * 1000)
            exit_code = process.returncode or 0

            return SandboxResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=exit_code,
                duration_ms=elapsed_ms,
                container_id="",
                success=exit_code == 0,
                mode="fallback",
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error("sandbox_subprocess_fallback_error error=%s", e)
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                duration_ms=elapsed_ms,
                container_id="",
                success=False,
                mode="fallback",
            )

    async def run_with_files(
        self,
        command: list[str],
        input_files: dict[str, str] | None = None,
        input_dir: str | None = None,
        output_dir: str = "/output",
        timeout: int | None = None,
        network: bool = True,
        memory: str | None = None,
    ) -> SandboxResult:
        """Run command with file I/O (mount input files, collect output).

        Creates temporary input/output directories, mounts them in container,
        and copies results back to host.

        Args:
            command: Command to execute
            input_files: Dict mapping destination path → file content
            input_dir: Host directory to mount as /input (takes precedence)
            output_dir: Container directory to mount as /output
            timeout: Command timeout in seconds
            network: Enable network access
            memory: Memory limit

        Returns:
            SandboxResult with output files collected

        Note:
            Requires Docker to be available (no subprocess fallback for file I/O)
        """
        if not self._has_docker:
            return SandboxResult(
                stdout="",
                stderr="Docker required for file I/O mode",
                exit_code=1,
                duration_ms=0,
                container_id="",
                success=False,
                mode="fallback",
            )

        import tempfile

        start_time = time.time()
        temp_input_dir = None
        temp_output_dir = None

        try:
            # Create temp directories
            temp_input_dir = Path(tempfile.mkdtemp(prefix="loom-sandbox-input-"))
            temp_output_dir = Path(tempfile.mkdtemp(prefix="loom-sandbox-output-"))

            # Write input files
            if input_files:
                for dest_path, content in input_files.items():
                    file_path = temp_input_dir / dest_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)
                    logger.debug(
                        "sandbox_input_file_created path=%s size=%d",
                        dest_path,
                        len(content),
                    )

            # Run container with mounted volumes
            client = await self._get_docker_client()

            # Build config with volume mounts
            input_mount = input_dir or str(temp_input_dir)
            config: dict[str, Any] = {
                "Cmd": command,
                "Image": self.image,
                "HostConfig": {
                    "Binds": [
                        f"{input_mount}:/input",
                        f"{str(temp_output_dir)}:{output_dir}",
                    ],
                    "Memory": _parse_memory_limit(memory or self.memory),
                    "CpuShares": (memory or self.cpus) * 1024,
                    "AutoRemove": self.auto_remove,
                    "NetworkMode": "none" if not network else "bridge",
                },
            }

            container = await client.containers.create_or_replace(
                name=f"loom-sandbox-files-{int(time.time() * 1000)}",
                config=config,
            )
            container_id = container["Id"][:12]

            await container.start()

            # Wait for completion
            timeout_secs = timeout or self.timeout
            try:
                exit_code = await asyncio.wait_for(
                    container.wait(), timeout=timeout_secs
                )
            except asyncio.TimeoutError:
                await container.kill()
                exit_code = 124

            logs = await container.log(stdout=True, stderr=True)
            stdout_logs = logs[0] if logs else ""
            stderr_logs = logs[1] if len(logs) > 1 else ""

            # Collect output files
            output_files = {}
            if temp_output_dir.exists():
                for file_path in temp_output_dir.rglob("*"):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(temp_output_dir)
                        try:
                            output_files[str(rel_path)] = file_path.read_text()
                        except Exception as e:
                            logger.warning(
                                "sandbox_output_file_read_failed path=%s error=%s",
                                rel_path,
                                e,
                            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Append output files summary to stdout
            if output_files:
                stdout_logs += f"\n[Output files: {len(output_files)} files]"

            return SandboxResult(
                stdout=stdout_logs,
                stderr=stderr_logs,
                exit_code=exit_code,
                duration_ms=elapsed_ms,
                container_id=container_id,
                success=exit_code == 0,
                mode="docker",
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error("sandbox_file_io_error error=%s", e)
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                duration_ms=elapsed_ms,
                container_id="",
                success=False,
                mode="fallback",
            )
        finally:
            # Cleanup temp directories
            if temp_input_dir and temp_input_dir.exists():
                import shutil as sh

                try:
                    sh.rmtree(temp_input_dir)
                except Exception as e:
                    logger.warning("sandbox_input_cleanup_failed error=%s", e)

            if temp_output_dir and temp_output_dir.exists():
                import shutil as sh

                try:
                    sh.rmtree(temp_output_dir)
                except Exception as e:
                    logger.warning("sandbox_output_cleanup_failed error=%s", e)


def _parse_memory_limit(memory_str: str) -> int:
    """Parse memory limit string to bytes.

    Args:
        memory_str: Memory limit (e.g., "512m", "1g", "2048")

    Returns:
        Memory in bytes

    Examples:
        "512m" -> 536870912 (512 * 1024 * 1024)
        "1g" -> 1073741824 (1 * 1024 * 1024 * 1024)
        "2048" -> 2048 (bytes)
    """
    memory_str = memory_str.lower().strip()

    # Try to parse numeric value with suffix
    multipliers = {
        "b": 1,
        "k": 1024,
        "m": 1024 * 1024,
        "g": 1024 * 1024 * 1024,
    }

    for suffix, multiplier in multipliers.items():
        if memory_str.endswith(suffix):
            try:
                value = int(memory_str[:-1])
                return value * multiplier
            except ValueError:
                break

    # Try pure numeric
    try:
        return int(memory_str)
    except ValueError:
        logger.warning("invalid_memory_limit using_default memory_str=%s", memory_str)
        return 512 * 1024 * 1024  # Default to 512MB


async def get_sandbox() -> DockerSandbox:
    """Get singleton DockerSandbox instance.

    Lazily initializes on first call. Thread-safe via asyncio.Lock.

    Returns:
        Singleton DockerSandbox instance
    """
    global _sandbox_instance

    if _sandbox_instance is not None:
        return _sandbox_instance

    async with _sandbox_lock:
        # Double-check pattern
        if _sandbox_instance is not None:
            return _sandbox_instance

        _sandbox_instance = DockerSandbox()
        return _sandbox_instance
