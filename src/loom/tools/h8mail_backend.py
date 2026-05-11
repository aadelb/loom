"""research_email_breach — Email OSINT and password breach hunting via h8mail."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import uuid
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.h8mail_backend")

# Email validation regex
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# HaveIBeenPwned API endpoint (fallback if h8mail unavailable)
HIBP_BREACH_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"


async def research_email_breach(
    email: str,
    search_timeout: int = 60,
) -> dict[str, Any]:
    """Hunt for email in breach databases and paste sites.

    Checks multiple breach databases for exposed credentials associated
    with an email address. Uses h8mail CLI if installed, with fallback to
    free APIs (HaveIBeenPwned-style check via httpx).

    Args:
        email: Target email address
        search_timeout: Max search time in seconds (default 60)

    Returns:
        Dict with keys:
        - email: validated input email
        - breaches_found: int (count of breaches)
        - breach_details: list of dicts with {site, date, data_types}
        - paste_sites: list of paste site names where email was found
        - h8mail_available: bool (whether h8mail CLI was used)
        - error: str (if validation or API error occurred)
    """
    try:
        # Validate email format
        if not _is_valid_email(email):
            return {
                "email": email,
                "error": "Invalid email format",
            }

        logger.info("email_breach_start email=%s search_timeout=%d", email, search_timeout)

        # Try h8mail first if available
        h8mail_path = _find_h8mail()
        if h8mail_path:
            return await _search_with_h8mail(email, h8mail_path, search_timeout)

        # Fallback to free APIs
        logger.info("h8mail not found, falling back to free APIs")
        return await _search_with_free_apis(email, search_timeout)
    except Exception as exc:
        return {"error": str(exc), "tool": "research_email_breach"}


async def _search_with_h8mail(
    email: str,
    h8mail_path: str,
    search_timeout: int,
) -> dict[str, Any]:
    """Search email breaches using h8mail CLI tool.

    Args:
        email: Target email address
        h8mail_path: Full path to h8mail executable
        search_timeout: Command execution timeout in seconds

    Returns:
        Dict with breach results
    """
    try:
        # Generate unique temp file for JSON output (S108: acceptable use with UUID)
        tmp_file = f"/tmp/h8mail_{uuid.uuid4().hex[:8]}.json"  # noqa: S108

        # Build h8mail command
        cmd = [h8mail_path, "-t", email, "--json", tmp_file]

        logger.info("h8mail_start cmd=%s", " ".join(cmd))

        # Run h8mail with subprocess in executor (blocking call delegated to executor)
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: subprocess.run(  # noqa: ASYNC221
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=search_timeout,
                ),
            ),
            timeout=search_timeout + 5,  # Add buffer for process cleanup
        )

        logger.info("h8mail_completed returncode=%d", result.returncode)

        # Parse h8mail JSON output
        if not os.path.exists(tmp_file):  # noqa: ASYNC240
            return {
                "email": email,
                "error": f"h8mail failed with return code {result.returncode}",
                "h8mail_available": True,
                "h8mail_stderr": result.stderr[:500] if result.stderr else "",
            }

        try:
            with open(tmp_file) as f:  # noqa: ASYNC230
                h8mail_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("h8mail_json_parse_error error=%s", str(e))
            return {
                "email": email,
                "error": f"Failed to parse h8mail output: {type(e).__name__}",
                "h8mail_available": True,
            }
        finally:
            # Cleanup temp file
            try:
                if os.path.exists(tmp_file):  # noqa: ASYNC240
                    os.remove(tmp_file)
            except OSError:
                pass

        # Extract breach details from h8mail output
        breach_details = []
        paste_sites = []

        if isinstance(h8mail_data, dict):
            # Handle breaches
            breaches = h8mail_data.get("breaches", [])
            if isinstance(breaches, list):
                for breach in breaches:
                    if isinstance(breach, dict):
                        breach_details.append(
                            {
                                "site": breach.get("site", "Unknown"),
                                "date": breach.get("date", "Unknown"),
                                "data_types": breach.get("data_types", []),
                            }
                        )

            # Handle paste sites
            pastes = h8mail_data.get("pastes", [])
            if isinstance(pastes, list):
                for paste in pastes:
                    if isinstance(paste, dict):
                        paste_sites.append(paste.get("site", "Unknown"))
                    elif isinstance(paste, str):
                        paste_sites.append(paste)

        return {
            "email": email,
            "breaches_found": len(breach_details),
            "breach_details": breach_details,
            "paste_sites": paste_sites,
            "h8mail_available": True,
        }

    except TimeoutError:
        logger.error("h8mail_timeout")
        return {
            "email": email,
            "error": f"h8mail search timed out after {search_timeout} seconds",
            "h8mail_available": True,
        }
    except subprocess.TimeoutExpired:
        logger.error("h8mail_subprocess_timeout")
        return {
            "email": email,
            "error": f"h8mail process timed out after {search_timeout} seconds",
            "h8mail_available": True,
        }
    except Exception as e:
        logger.exception("h8mail_error")
        return {
            "email": email,
            "error": f"h8mail error: {type(e).__name__}: {str(e)[:200]}",
            "h8mail_available": True,
        }


async def _search_with_free_apis(
    email: str,
    search_timeout: int,
) -> dict[str, Any]:
    """Search email breaches using free APIs (fallback).

    Uses HaveIBeenPwned API for breach detection.

    Args:
        email: Target email address
        search_timeout: Request timeout in seconds

    Returns:
        Dict with breach results or empty result if not found
    """
    try:
        loop = asyncio.get_event_loop()

        # Query HaveIBeenPwned API in executor
        breaches = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: _query_hibp_api(email, search_timeout),
            ),
            timeout=search_timeout,
        )

        return {
            "email": email,
            "breaches_found": len(breaches),
            "breach_details": breaches,
            "paste_sites": [],
            "h8mail_available": False,
            "note": "Results from HaveIBeenPwned free API (paste sites unavailable)",
        }

    except TimeoutError:
        logger.error("free_api_timeout email=%s", email)
        return {
            "email": email,
            "error": f"API search timed out after {search_timeout} seconds",
            "h8mail_available": False,
        }
    except Exception as e:
        logger.exception("free_api_error")
        return {
            "email": email,
            "error": f"API error: {type(e).__name__}: {str(e)[:200]}",
            "h8mail_available": False,
        }


def _query_hibp_api(email: str, search_timeout: int) -> list[dict[str, Any]]:
    """Query HaveIBeenPwned API synchronously.

    Args:
        email: Target email address
        search_timeout: Request timeout in seconds

    Returns:
        List of breach dicts {site, date, data_types}
    """
    api_key = os.environ.get("HIBP_API_KEY", "").strip()

    try:
        with httpx.Client(timeout=float(search_timeout)) as client:
            headers = {
                "User-Agent": "LoomMCP/1.0",
            }

            # Add API key if available
            if api_key:
                headers["hibp-api-key"] = api_key

            resp = client.get(
                f"{HIBP_BREACH_URL}/{email}",
                headers=headers,
                follow_redirects=True,
            )

            # 404 = not found (good), 200 = found in breach
            if resp.status_code == 404:
                return []

            if resp.status_code == 200:
                breaches_data = resp.json()
                breaches = [
                    {
                        "site": b.get("Name", ""),
                        "date": b.get("BreachDate", ""),
                        "data_types": b.get("DataClasses", []),
                    }
                    for b in breaches_data
                    if isinstance(b, dict)
                ]
                return breaches

            # Rate limited or other error
            logger.warning("hibp_api_error status=%d", resp.status_code)
            return []

    except httpx.TimeoutException:
        logger.error("hibp_timeout")
        raise
    except httpx.RequestError as e:
        logger.error("hibp_request_error error=%s", str(e))
        raise
    except json.JSONDecodeError:
        logger.error("hibp_json_decode_error")
        return []
    except Exception:
        logger.exception("hibp_unexpected_error")
        raise


def _find_h8mail() -> str | None:
    """Find h8mail executable in PATH.

    Returns:
        Full path to h8mail if found, None otherwise
    """
    try:
        # Check if h8mail is in PATH
        result = subprocess.run(
            ["which", "h8mail"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            if os.path.isfile(path) and os.access(path, os.X_OK):
                logger.info("h8mail_found path=%s", path)
                return path
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    logger.debug("h8mail_not_found in PATH")
    return None


def _is_valid_email(email: str) -> bool:
    """Validate email format using regex.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    email = email.strip()
    if not email or len(email) > 254:
        return False

    # Simple regex: local@domain pattern
    return bool(re.match(EMAIL_PATTERN, email))
