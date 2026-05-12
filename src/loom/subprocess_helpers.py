"""Safe subprocess execution helpers for MCP tools.

Provides both sync and async subprocess runners with:
- Consistent timeout handling
- Binary availability checks
- Safe argument construction (no shell=True)
- Proper error capture and logging
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from typing import Any

logger = logging.getLogger("loom.subprocess_helpers")


def check_binary(name: str) -> bool:
    """Check if a CLI binary is available on PATH.

    Args:
        name: Binary name to search for on PATH

    Returns:
        True if binary exists and is executable, False otherwise
    """
    return shutil.which(name) is not None


def run_command(
    cmd: list[str],
    *,
    timeout: float = 60.0,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_data: str | None = None,
) -> dict[str, Any]:
    """Run a subprocess synchronously with consistent error handling.

    Never raises subprocess exceptions — all errors are captured and returned
    in the result dict. This allows calling code to handle errors gracefully.

    Args:
        cmd: List of command and arguments (e.g., ["git", "status"])
        timeout: Timeout in seconds (default 60.0)
        cwd: Working directory for subprocess
        env: Environment variables dict (if None, inherits parent)
        input_data: String to pass to stdin

    Returns:
        Dict with keys:
        - stdout: str (command output, empty on error)
        - stderr: str (error output, empty on error)
        - returncode: int (0 on success, -1 on exception)
        - success: bool (True if returncode == 0)
        - error: str (set only on exception, describes what went wrong)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            input=input_data,
            check=False,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "success": False,
            "error": f"Command timed out after {timeout}s: {cmd[0]}",
        }
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "success": False,
            "error": f"Binary not found on PATH: {cmd[0]}",
        }
    except OSError as exc:
        return {
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "success": False,
            "error": f"OS error executing {cmd[0]}: {exc}",
        }


async def run_command_async(
    cmd: list[str],
    *,
    timeout: float = 60.0,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_data: str | None = None,
) -> dict[str, Any]:
    """Run a subprocess from async context without blocking the event loop.

    Delegates to run_in_executor internally, allowing async code to call
    blocking subprocess operations safely.

    Args:
        cmd: List of command and arguments
        timeout: Timeout in seconds (default 60.0)
        cwd: Working directory for subprocess
        env: Environment variables dict (if None, inherits parent)
        input_data: String to pass to stdin

    Returns:
        Dict with same structure as run_command()
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: run_command(cmd, timeout=timeout, cwd=cwd, env=env, input_data=input_data),
    )


def require_binary(
    name: str,
    install_hint: str = "",
) -> None:
    """Raise RuntimeError if a CLI binary is not available on PATH.

    Useful for early validation in tool functions that require a specific
    binary. Provides a clear error message with optional installation hints.

    Args:
        name: Binary name to check
        install_hint: Optional installation instructions for error message

    Raises:
        RuntimeError: If binary is not found on PATH
    """
    if not check_binary(name):
        msg = f"Required binary '{name}' not found on PATH"
        if install_hint:
            msg += f". Install: {install_hint}"
        raise RuntimeError(msg)
