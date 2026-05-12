"""CLI binary availability checker.

Centralized registry of external CLI tool availability. Tools check once
at import time; subsequent calls use the cached result. This module reduces
code duplication across src/loom/tools/ where many modules check for binary
availability before execution.
"""

from __future__ import annotations

import logging
import shutil

logger = logging.getLogger("loom.cli_checker")

_cache: dict[str, bool] = {}


def is_available(binary: str) -> bool:
    """Check if a CLI binary is on PATH. Result is cached.

    Args:
        binary: binary name to check (e.g., 'gh', 'pandoc', 'nuclei')

    Returns:
        True if binary is on PATH, False otherwise
    """
    if binary not in _cache:
        _cache[binary] = shutil.which(binary) is not None
        if not _cache[binary]:
            logger.debug(f"binary_not_found: {binary}")
    return _cache[binary]


def require(binary: str, install_hint: str = "") -> None:
    """Raise RuntimeError if binary is missing.

    Args:
        binary: binary name to require
        install_hint: optional installation instruction (e.g., URL, pip command)

    Raises:
        RuntimeError: if binary is not on PATH
    """
    if not is_available(binary):
        msg = f"Required binary '{binary}' not found on PATH"
        if install_hint:
            msg += f". Install: {install_hint}"
        raise RuntimeError(msg)


def get_path(binary: str) -> str | None:
    """Get full path to binary on PATH.

    Args:
        binary: binary name to locate

    Returns:
        Full absolute path to binary, or None if not found
    """
    return shutil.which(binary)


def available_tools() -> dict[str, bool]:
    """Return availability status of all checked binaries.

    Returns:
        Dict mapping binary name to availability (True/False)
    """
    return dict(_cache)


def clear_cache() -> None:
    """Clear the availability cache.

    Used primarily for testing when PATH environment may change.
    """
    _cache.clear()


# Pre-check common tools used across the codebase
COMMON_TOOLS: dict[str, str] = {
    "gh": "https://cli.github.com/",
    "pandoc": "https://pandoc.org/installing.html",
    "nuclei": "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    "subfinder": "go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    "katana": "go install github.com/projectdiscovery/katana/cmd/katana@latest",
    "httpx-pd": "go install github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "maigret": "pip install maigret",
    "sherlock": "pip install sherlock-project",
    "h8mail": "pip install h8mail",
    "tor": "apt install tor (or brew install tor on macOS)",
}
