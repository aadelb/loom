"""Maigret username OSINT backend — search for usernames across 2000+ social networks.

Maigret is an advanced open-source OSINT tool that searches for usernames
across 2000+ websites and social networks. This module provides a library wrapper
around the Maigret CLI with subprocess execution and JSON output parsing.

Uses Maigret as a subprocess since it's not easily pip-installable as a library.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
import time
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
        return False, "Maigret CLI not found. Install with: pip install maigret"
    except subprocess.TimeoutExpired:
        return False, "Maigret CLI timeout during version check"
    except Exception as exc:
        return False, f"Maigret availability check error: {str(exc)}"


def research_maigret(username: str, timeout: int = 60) -> dict[str, Any]:
    """Search for a username across 2000+ sites using Maigret.

    Searches for the given username across 2000+ websites and social networks
    and returns a list of where the account was found, along with direct URLs.

    Args:
        username: username to search for
        timeout: timeout in seconds for the lookup (default 60)

    Returns:
        Dict with:
        - username: the searched username
        - accounts_found: count of accounts discovered
        - accounts: list of dicts with {site, url, status}
        - duration_ms: execution time in milliseconds
        - maigret_available: bool indicating if Maigret CLI is available
        - error: error message if lookup failed (optional)
    """
    try:
        username = _validate_username(username)
    except ValueError as exc:
        return {
            "username": username,
            "error": str(exc),
            "maigret_available": False,
            "accounts_found": 0,
            "accounts": [],
            "duration_ms": 0,
        }

    # Check if maigret is available
    available, msg = _check_maigret_available()
    if not available:
        return {
            "username": username,
            "error": msg,
            "maigret_available": False,
            "accounts_found": 0,
            "accounts": [],
            "duration_ms": 0,
        }

    start_time = time.time()

    try:
        # Create temp file for JSON output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            output_file = tmp.name

        # Build maigret command
        # maigret outputs JSON with: maigret username --json
        # We need to capture the output to parse it
        cmd = ["maigret", username, "--json", "--timeout", str(timeout)]

        # Run maigret
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,  # Give subprocess extra time beyond maigret's timeout
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Parse the JSON output from stdout or file
        output: dict[str, Any] = {
            "username": username,
            "maigret_available": True,
            "duration_ms": duration_ms,
        }

        accounts_list: list[dict[str, Any]] = []
        accounts_found = 0

        try:
            # Try to parse from stdout first
            if result.stdout:
                try:
                    maigret_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    # If stdout is not valid JSON, try reading the file
                    maigret_output = None

                if maigret_output:
                    # Maigret output format: {username: {site: {url, status, ...}}}
                    if isinstance(maigret_output, dict):
                        # Handle both direct format and username-nested format
                        data_to_process = maigret_output
                        if username in maigret_output:
                            data_to_process = maigret_output[username]

                        if isinstance(data_to_process, dict):
                            for site, site_data in data_to_process.items():
                                if isinstance(site_data, dict):
                                    # Check if this is a found account
                                    url = site_data.get("url", "")
                                    status = site_data.get("status", "unknown")

                                    # Maigret uses status codes or 'found', 'not found', etc.
                                    # Consider it found if status is 'found' or 200
                                    if (
                                        status == "found"
                                        or status == 200
                                        or (isinstance(status, int) and 200 <= status < 300)
                                    ):
                                        accounts_found += 1
                                        accounts_list.append(
                                            {
                                                "site": site,
                                                "url": url,
                                                "status": status,
                                            }
                                        )
                                    elif url:
                                        # Include URL if present even without explicit found status
                                        accounts_list.append(
                                            {
                                                "site": site,
                                                "url": url,
                                                "status": status,
                                            }
                                        )
                                        accounts_found += 1

            output["accounts"] = accounts_list
            output["accounts_found"] = accounts_found

        except (json.JSONDecodeError, IOError, KeyError) as exc:
            output["error"] = f"Failed to parse Maigret output: {str(exc)}"
            output["accounts"] = []
            output["accounts_found"] = 0

        return output

    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "username": username,
            "error": f"Maigret lookup timed out after {timeout} seconds",
            "maigret_available": True,
            "accounts_found": 0,
            "accounts": [],
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "username": username,
            "error": f"Maigret lookup error: {str(exc)}",
            "maigret_available": True,
            "accounts_found": 0,
            "accounts": [],
            "duration_ms": duration_ms,
        }
