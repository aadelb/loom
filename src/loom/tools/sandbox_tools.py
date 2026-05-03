"""Sandbox tool implementations for isolated command execution.

Exposes two MCP tools:
  - research_sandbox_run() — Run command in isolated Docker container
  - research_sandbox_status() — Check Docker availability and sandbox status
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from loom.sandbox import SandboxResult, get_sandbox, is_docker_available

logger = logging.getLogger("loom.tools.sandbox_tools")


class SandboxRunParams(BaseModel):
    """Parameters for research_sandbox_run tool."""

    command: list[str] = Field(
        ..., description="Command to execute (list of strings, e.g., ['nmap', '-p', '80'])"
    )
    timeout: int = Field(300, description="Timeout in seconds (default: 300, max: 3600)")
    network: bool = Field(True, description="Enable network access (default: True)")
    memory: str = Field("512m", description="Memory limit (e.g., '512m', '1g')")
    cpus: int = Field(1, description="CPU limit in cores (default: 1, max: 4)")
    env: dict[str, str] | None = Field(
        None, description="Environment variables to pass to container"
    )
    working_dir: str | None = Field(
        None, description="Working directory inside container"
    )

    model_config = {"extra": "forbid", "strict": True}


async def research_sandbox_run(
    command: list[str],
    timeout: int = 300,
    network: bool = True,
    memory: str = "512m",
    cpus: int = 1,
    env: dict[str, str] | None = None,
    working_dir: str | None = None,
) -> TextContent:
    """Run command in isolated Docker container.

    Executes a command in an ephemeral Docker container with:
    - Filesystem isolation (prevents access to host filesystem)
    - Memory limit (default 512MB)
    - CPU limit (default 1 core)
    - Network isolation (optional, default enabled)
    - Auto-cleanup

    Falls back to direct subprocess if Docker is unavailable.

    Args:
        command: Command to execute (list of strings, e.g., ['nmap', '-p', '80'])
        timeout: Command timeout in seconds (default: 300, max: 3600)
        network: Enable network access (default: True, disable for safety)
        memory: Memory limit (default: "512m", e.g., "1g", "2048m")
        cpus: CPU limit in cores (default: 1, max: 4)
        env: Environment variables to pass to container
        working_dir: Working directory inside container

    Returns:
        TextContent with JSON containing:
          - success: bool
          - stdout: command output
          - stderr: error output
          - exit_code: int (0 = success)
          - duration_ms: int
          - container_id: str (empty if fallback)
          - mode: "docker" or "fallback"
          - warning: str (if any)

    Example:
        result = await research_sandbox_run(
            command=["nmap", "-p", "80", "example.com"],
            timeout=60,
            network=True,
            memory="512m"
        )
    """
    try:
        # Validate inputs
        if not command:
            return TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error_code": "VALIDATION_ERROR",
                        "message": "Command cannot be empty",
                        "success": False,
                    }
                ),
            )

        if timeout < 1 or timeout > 3600:
            return TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error_code": "VALIDATION_ERROR",
                        "message": "Timeout must be between 1 and 3600 seconds",
                        "success": False,
                    }
                ),
            )

        if cpus < 1 or cpus > 4:
            return TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error_code": "VALIDATION_ERROR",
                        "message": "CPUs must be between 1 and 4",
                        "success": False,
                    }
                ),
            )

        # Execute command
        sandbox = await get_sandbox()
        result: SandboxResult = await sandbox.run(
            command=command,
            timeout=timeout,
            network=network,
            memory=memory,
            cpus=cpus,
            env=env,
            working_dir=working_dir,
        )

        # Build response
        response: dict[str, Any] = {
            "success": result.success,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": result.duration_ms,
            "container_id": result.container_id,
            "mode": result.mode,
        }

        if not is_docker_available() and result.mode == "fallback":
            response["warning"] = (
                "Docker not available; command ran directly on host (less isolated)"
            )

        logger.info(
            "sandbox_run_completed command=%s exit_code=%d duration_ms=%d mode=%s",
            command[0] if command else "?",
            result.exit_code,
            result.duration_ms,
            result.mode,
        )

        return TextContent(type="text", text=json.dumps(response))

    except Exception as e:
        logger.error("sandbox_run_error error=%s", e)
        return TextContent(
            type="text",
            text=json.dumps(
                {
                    "error_code": "INTERNAL_ERROR",
                    "message": str(e),
                    "success": False,
                }
            ),
        )


async def research_sandbox_status() -> TextContent:
    """Check Docker availability and sandbox status.

    Returns system information about Docker and sandbox configuration.

    Returns:
        TextContent with JSON containing:
          - docker_available: bool
          - docker_version: str (if available)
          - sandbox_image: str
          - sandbox_timeout: int
          - sandbox_memory: str
          - sandbox_cpus: int

    Example:
        status = await research_sandbox_status()
    """
    try:
        sandbox = await get_sandbox()
        docker_available = is_docker_available()

        response: dict[str, Any] = {
            "docker_available": docker_available,
            "sandbox_image": sandbox.image,
            "sandbox_timeout": sandbox.timeout,
            "sandbox_memory": sandbox.memory,
            "sandbox_cpus": sandbox.cpus,
        }

        # Try to get Docker version
        if docker_available:
            try:
                client = await sandbox._get_docker_client()
                version_info = await client.version()
                response["docker_version"] = version_info.get("Version", "unknown")
            except Exception as e:
                logger.warning("sandbox_version_check_failed error=%s", e)
                response["docker_version"] = "unknown"
        else:
            response["docker_version"] = None

        logger.debug("sandbox_status_check docker_available=%s", docker_available)

        return TextContent(type="text", text=json.dumps(response))

    except Exception as e:
        logger.error("sandbox_status_error error=%s", e)
        return TextContent(
            type="text",
            text=json.dumps(
                {
                    "error_code": "INTERNAL_ERROR",
                    "message": str(e),
                }
            ),
        )
