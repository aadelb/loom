"""Sherlock username OSINT backend — search for usernames across 400+ social networks.

Sherlock is a powerful open-source tool that searches for given usernames
across 400+ social networks. This module provides a library wrapper around
the Sherlock CLI with subprocess execution and JSON output parsing.

Uses Sherlock as a subprocess since it's not easily pip-installable as a library.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from typing import Any

logger = logging.getLogger("loom.tools.sherlock_backend")


def _validate_username(username: str) -> str:
    """Validate username for Sherlock lookup.

    Sherlock accepts usernames with alphanumeric chars, underscores, hyphens,
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


def _validate_platform(platform: str) -> str:
    """Validate platform name for Sherlock.

    Platforms are site names like 'twitter', 'instagram', 'github', etc.

    Args:
        platform: platform name to validate

    Returns:
        The validated platform string

    Raises:
        ValueError: if platform name is invalid
    """
    platform = platform.strip() if isinstance(platform, str) else ""
    
    if not platform or len(platform) > 100:
        raise ValueError("platform must be 1-100 characters")

    if not re.match(r"^[a-z0-9_\-]+$", platform, re.IGNORECASE):
        raise ValueError("platform contains disallowed characters")

    return platform


def _check_sherlock_available() -> tuple[bool, str]:
    """Check if Sherlock CLI is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["sherlock", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, "Sherlock CLI found"
        else:
            return False, f"Sherlock version check failed: {result.stderr}"
    except FileNotFoundError:
        return False, (
            "Sherlock CLI not found. Install with: pip install sherlock-project"
        )
    except subprocess.TimeoutExpired:
        return False, "Sherlock CLI timeout during version check"
    except Exception as exc:
        return False, f"Sherlock availability check error: {str(exc)}"


def research_sherlock_lookup(
    username: str, platforms: list[str] | None = None, timeout: int = 30
) -> dict[str, Any]:
    """Search for a username across social networks using Sherlock.

    Searches for the given username across 400+ social networks and returns
    a list of where the account was found, along with direct URLs.

    Args:
        username: username to search for
        platforms: optional list of specific platforms to search (e.g., ["twitter", "instagram"])
                   if None, searches all platforms
        timeout: timeout in seconds for the lookup (default 30)

    Returns:
        Dict with:
        - username: the searched username
        - found_on: list of dicts with {platform, url, status_code, response_time_ms}
        - total_found: count of platforms where username was found
        - total_checked: count of platforms checked
        - sherlock_available: bool indicating if Sherlock CLI is available
        - error: error message if lookup failed (optional)
    """
    try:
        username = _validate_username(username)
    except ValueError as exc:
        return {"username": username, "error": str(exc), "sherlock_available": False}

    # Check if sherlock is available
    available, msg = _check_sherlock_available()
    if not available:
        return {
            "username": username,
            "error": msg,
            "sherlock_available": False,
        }

    try:
        # Validate platforms if provided
        validated_platforms = []
        if platforms:
            validated_platforms = [_validate_platform(p) for p in platforms]

        # Create temp file for JSON output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            output_file = tmp.name

        # Build sherlock command
        cmd = ["sherlock", username, "--json", output_file]

        # Add timeout (sherlock's --timeout flag is in seconds)
        cmd.extend(["--timeout", str(timeout)])

        # Add specific platforms if requested
        if validated_platforms:
            cmd.extend(["--site"] + validated_platforms)

        # Run sherlock
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,  # Give subprocess extra time beyond sherlock's timeout
        )

        # Parse the JSON output
        output: dict[str, Any] = {
            "username": username,
            "sherlock_available": True,
        }

        try:
            with open(output_file, "r") as f:
                sherlock_output = json.load(f)

            # Sherlock output format: {username: {platform: {url, user_id, status_code, ...}}}
            if username in sherlock_output:
                found_on = []
                total_checked = 0
                total_found = 0

                for platform, data in sherlock_output[username].items():
                    total_checked += 1
                    if isinstance(data, dict) and data.get("status_code") == 200:
                        total_found += 1
                        found_on.append(
                            {
                                "platform": platform,
                                "url": data.get("url", ""),
                                "user_id": data.get("user_id", ""),
                                "status_code": data.get("status_code"),
                            }
                        )

                output["found_on"] = found_on
                output["total_found"] = total_found
                output["total_checked"] = total_checked
            else:
                output["found_on"] = []
                output["total_found"] = 0
                output["total_checked"] = 0

        except (json.JSONDecodeError, IOError) as exc:
            output["error"] = f"Failed to parse Sherlock output: {str(exc)}"

        return output

    except subprocess.TimeoutExpired:
        return {
            "username": username,
            "error": f"Sherlock lookup timed out after {timeout} seconds",
            "sherlock_available": True,
        }
    except Exception as exc:
        return {
            "username": username,
            "error": f"Sherlock lookup error: {str(exc)}",
            "sherlock_available": True,
        }


def research_sherlock_batch(
    usernames: list[str], platforms: list[str] | None = None, timeout: int = 30
) -> dict[str, Any]:
    """Batch search multiple usernames across social networks.

    Performs sherlock lookups for multiple usernames and returns aggregated
    results. Results are looked up sequentially to avoid overwhelming the system.

    Args:
        usernames: list of usernames to search for
        platforms: optional list of specific platforms to search
        timeout: timeout in seconds per lookup (default 30)

    Returns:
        Dict with:
        - usernames_checked: count of usernames searched
        - results: dict mapping username -> findings (same format as research_sherlock_lookup)
        - total_accounts_found: sum of all accounts found across all usernames
        - sherlock_available: bool indicating if Sherlock CLI is available
        - error: error message if batch failed (optional)
    """
    # Check if sherlock is available upfront
    available, msg = _check_sherlock_available()
    if not available:
        return {
            "usernames_checked": 0,
            "results": {},
            "total_accounts_found": 0,
            "sherlock_available": False,
            "error": msg,
        }

    try:
        # Validate and deduplicate usernames
        validated = []
        seen = set()
        for username in usernames:
            try:
                validated_username = _validate_username(username)
                if validated_username not in seen:
                    validated.append(validated_username)
                    seen.add(validated_username)
            except ValueError as exc:
                logger.warning(f"Skipping invalid username {username}: {exc}")

        if not validated:
            return {
                "usernames_checked": 0,
                "results": {},
                "total_accounts_found": 0,
                "sherlock_available": True,
                "error": "No valid usernames provided",
            }

        # Perform lookups
        results = {}
        total_accounts_found = 0

        for username in validated:
            lookup_result = research_sherlock_lookup(username, platforms, timeout)
            results[username] = lookup_result
            if "error" not in lookup_result:
                total_accounts_found += lookup_result.get("total_found", 0)

        return {
            "usernames_checked": len(validated),
            "results": results,
            "total_accounts_found": total_accounts_found,
            "sherlock_available": True,
        }

    except Exception as exc:
        return {
            "usernames_checked": len(usernames),
            "results": {},
            "total_accounts_found": 0,
            "sherlock_available": True,
            "error": f"Batch lookup error: {str(exc)}",
        }
