"""Maigret username OSINT backend — search for usernames across 2000+ services.

Maigret is a powerful open-source tool that searches for given usernames
across 2000+ services including social networks, forums, code repositories,
and more. This module provides a library wrapper around the Maigret CLI
with subprocess execution and JSON output parsing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import tempfile
from typing import Any

logger = logging.getLogger("loom.tools.maigret_backend")


def _validate_username(username: str) -> str:
    """Validate username for Maigret lookup.

    Maigret accepts usernames with alphanumeric chars, underscores, hyphens,
    periods, and some special chars. We'll be permissive but cap length.

    Args:
        username: username to validate

    Returns:
        The validated username string

    Raises:
        ValueError: if username is invalid
    """
    username = username.strip() if isinstance(username, str) else ""

    if not username or len(username) > 255:
        raise ValueError("username must be 1-255 characters")

    # Allow alphanumeric, underscore, hyphen, period, plus (common in usernames)
    # Disallow only command-injection chars
    if not re.match(r"^[a-z0-9._\-+]+$", username, re.IGNORECASE):
        raise ValueError("username contains disallowed characters")

    return username


def _validate_timeout(timeout: int) -> int:
    """Validate timeout value.

    Args:
        timeout: timeout in seconds

    Returns:
        The validated timeout value

    Raises:
        ValueError: if timeout is invalid
    """
    if not isinstance(timeout, int):
        raise ValueError("timeout must be an integer")

    if timeout < 1 or timeout > 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds")

    return timeout


def _check_maigret_available() -> tuple[bool, str]:
    """Check if Maigret CLI is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["maigret", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, "Maigret CLI found"
        else:
            return False, f"Maigret version check failed: {result.stderr}"
    except FileNotFoundError:
        return False, (
            "Maigret CLI not found. Install with: pip install maigret"
        )
    except subprocess.TimeoutExpired:
        return False, "Maigret CLI timeout during version check"
    except Exception as exc:
        return False, f"Maigret availability check error: {str(exc)}"


async def research_maigret(
    username: str, timeout: int = 120
) -> dict[str, Any]:
    """Search for a username across 2000+ services using Maigret.

    Searches for the given username across social networks, forums, code
    repositories, and other services. Returns a list of where the account
    was found, along with direct URLs.

    Args:
        username: username to search for
        timeout: timeout in seconds for the lookup (default 120)

    Returns:
        Dict with:
        - username: the searched username
        - sites_found: list of dicts with {site, url, found, verified}
        - total_checked: count of sites checked
        - total_found: count of sites where username was found
        - maigret_available: bool indicating if Maigret CLI is available
        - error: error message if lookup failed (optional)
    """
    try:
        username = _validate_username(username)
        timeout = _validate_timeout(timeout)
    except ValueError as exc:
        return {
            "username": username,
            "error": str(exc),
            "maigret_available": False,
        }

    # Check if maigret is available
    available, msg = _check_maigret_available()
    if not available:
        return {
            "username": username,
            "error": msg,
            "maigret_available": False,
        }

    try:
        # Create temp file for JSON output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            output_file = tmp.name

        # Build maigret command with ndjson output
        cmd = [
            "maigret",
            username,
            "--json",
            output_file,
            "--timeout",
            str(timeout),
        ]

        # Run maigret asynchronously
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 30,
        )

        # Parse the JSON output
        output: dict[str, Any] = {
            "username": username,
            "maigret_available": True,
        }

        try:
            with open(output_file, "r") as f:
                maigret_output = json.load(f)

            # Maigret output format: {site: {username: {url, found, verified, ...}}}
            sites_found = []
            total_checked = 0

            if isinstance(maigret_output, dict):
                for site, data in maigret_output.items():
                    total_checked += 1
                    if isinstance(data, dict):
                        site_entry = {
                            "site": site,
                            "found": data.get("found", False),
                            "verified": data.get("verified", False),
                            "url": data.get("url", ""),
                            "status": data.get("status", "unknown"),
                        }
                        if site_entry["found"]:
                            sites_found.append(site_entry)

            output["sites_found"] = sites_found
            output["total_found"] = len(sites_found)
            output["total_checked"] = total_checked

        except (json.JSONDecodeError, IOError) as exc:
            output["error"] = f"Failed to parse Maigret output: {str(exc)}"

        return output

    except subprocess.TimeoutExpired:
        return {
            "username": username,
            "error": f"Maigret lookup timed out after {timeout} seconds",
            "maigret_available": True,
        }
    except Exception as exc:
        logger.exception("Maigret lookup failed")
        return {
            "username": username,
            "error": f"Maigret lookup error: {str(exc)}",
            "maigret_available": True,
        }
