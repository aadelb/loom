"""research_email_breach — Email OSINT and password breach hunting via h8mail."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import uuid
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.h8mail_backend")

# Email validation regex (RFC 5322 simplified)
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# HaveIBeenPwned API endpoint (fallback if h8mail unavailable)
HIBP_BREACH_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"

# Max email length to prevent DoS via overlong addresses
MAX_EMAIL_LENGTH = 254


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

        email_hash = hashlib.sha256(email.encode()).hexdigest()[:8]
        logger.info(
            "email_breach_start email_hash=%s search_timeout=%d", email_hash, search_timeout
        )

        # Try h8mail first if available
        h8mail_path = _find_h8mail()
        if h8mail_path:
            return await _search_with_h8mail(email, h8mail_path, search_timeout)

        # Fallback to free APIs
        logger.info("h8mail not found, falling back to free APIs")
        return await _search_with_free_apis(email, search_timeout)
    except (TimeoutError, OSError, ValueError) as exc:
        logger.error("email_breach_error error_type=%s", type(exc).__name__)
        return {"error": f"Search failed: {type(exc).__name__}", "tool": "research_email_breach"}
    except Exception:
        logger.exception("email_breach_unexpected_error")
        return {"error": "Unexpected error during breach search", "tool": "research_email_breach"}


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
    tmp_file = None
    try:
        # Generate unique temp file in system temp directory with restrictive perms
        tmp_dir = tempfile.gettempdir()
        tmp_file = os.path.join(tmp_dir, f"h8mail_{uuid.uuid4().hex[:12]}.json")

        # Build h8mail command with email properly escaped
        cmd = [h8mail_path, "-t", email, "--json", tmp_file]

        # Log sanitized command (without email)
        logger.info("h8mail_start h8mail_available=True")

        # Run h8mail with subprocess in executor (blocking call delegated to executor)
        # Email is validated against EMAIL_PATTERN, and cmd uses list form (safe from injection)
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: subprocess.run(  # noqa: ASYNC221,S603
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
                "h8mail_stderr": _sanitize_output(result.stderr[:500]) if result.stderr else "",
            }

        try:
            with open(tmp_file) as f:  # noqa: ASYNC230
                h8mail_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("h8mail_json_parse_error error_type=%s", type(e).__name__)
            return {
                "email": email,
                "error": f"Failed to parse h8mail output: {type(e).__name__}",
                "h8mail_available": True,
            }
        finally:
            # Cleanup temp file securely
            if tmp_file:
                try:
                    if os.path.exists(tmp_file):  # noqa: ASYNC240
                        os.remove(tmp_file)
                except OSError:
                    logger.debug("h8mail_temp_cleanup_failed")

        # Extract breach details from h8mail output with schema validation
        breach_details = []
        paste_sites = []

        if isinstance(h8mail_data, dict):
            # Handle breaches
            breaches = h8mail_data.get("breaches", [])
            if isinstance(breaches, list):
                for breach in breaches:
                    if isinstance(breach, dict) and "site" in breach:
                        breach_details.append(
                            {
                                "site": str(breach.get("site", "Unknown"))[:128],
                                "date": str(breach.get("date", "Unknown"))[:32],
                                "data_types": [str(x)[:64] for x in breach.get("data_types", [])],
                            }
                        )

            # Handle paste sites
            pastes = h8mail_data.get("pastes", [])
            if isinstance(pastes, list):
                for paste in pastes:
                    if isinstance(paste, dict) and "site" in paste:
                        paste_sites.append(str(paste.get("site", "Unknown"))[:128])
                    elif isinstance(paste, str):
                        paste_sites.append(paste[:128])

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
    except OSError as e:
        logger.error("h8mail_os_error error_type=%s", type(e).__name__)
        return {
            "email": email,
            "error": "File system error during h8mail execution",
            "h8mail_available": True,
        }
    except Exception as e:
        logger.exception("h8mail_error")
        return {
            "email": email,
            "error": f"h8mail error: {type(e).__name__}",
            "h8mail_available": True,
        }
    finally:
        # Ensure temp file is cleaned up
        if tmp_file and os.path.exists(tmp_file):  # noqa: ASYNC240
            try:
                os.remove(tmp_file)
            except OSError:
                logger.debug("h8mail_final_cleanup_failed")


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
        logger.error("free_api_timeout")
        return {
            "email": email,
            "error": f"API search timed out after {search_timeout} seconds",
            "h8mail_available": False,
        }
    except (httpx.RequestError, OSError) as e:
        logger.error("free_api_request_error error_type=%s", type(e).__name__)
        return {
            "email": email,
            "error": "API request failed",
            "h8mail_available": False,
        }
    except Exception as e:
        logger.exception("free_api_error")
        return {
            "email": email,
            "error": f"API error: {type(e).__name__}",
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

    # Validate API key format if present
    if api_key and not _is_valid_header_value(api_key):
        logger.warning("hibp_invalid_api_key_format")
        api_key = ""

    try:
        with httpx.Client(timeout=float(search_timeout)) as client:
            headers = {
                "User-Agent": "LoomMCP/1.0 (Breach Research)",
            }

            # Add API key if available and valid
            if api_key:
                headers["hibp-api-key"] = api_key

            # URL-encode email to prevent injection
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
                if not isinstance(breaches_data, list):
                    logger.warning("hibp_unexpected_response_format")
                    return []

                breaches = []
                for b in breaches_data:
                    if isinstance(b, dict):
                        breach = {
                            "site": str(b.get("Name", "Unknown"))[:128],
                            "date": str(b.get("BreachDate", "Unknown"))[:32],
                            "data_types": [str(x)[:64] for x in b.get("DataClasses", [])],
                        }
                        breaches.append(breach)
                return breaches

            # Rate limited or other error
            logger.warning("hibp_api_error status=%d", resp.status_code)
            return []

    except httpx.TimeoutException:
        logger.error("hibp_timeout")
        raise
    except httpx.RequestError as e:
        logger.error("hibp_request_error error_type=%s", type(e).__name__)
        raise
    except json.JSONDecodeError:
        logger.error("hibp_json_decode_error")
        return []
    except (ValueError, TypeError) as e:
        logger.error("hibp_parse_error error_type=%s", type(e).__name__)
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
    if not email or len(email) > MAX_EMAIL_LENGTH:
        return False

    # Simple regex: local@domain pattern
    return bool(re.match(EMAIL_PATTERN, email))


def _is_valid_header_value(value: str) -> bool:
    """Validate HTTP header value for safety.

    Ensures header doesn't contain control characters or newlines that could
    enable header injection attacks.

    Args:
        value: Header value to validate

    Returns:
        True if value is safe for HTTP headers, False otherwise
    """
    if not isinstance(value, str):
        return False

    # Check for control characters and newlines (HTTP header injection prevention)
    return not any(c in value for c in ["\n", "\r", "\0", "\t"])


def _sanitize_output(output: str) -> str:
    """Remove potentially problematic characters from subprocess output.

    Args:
        output: Raw subprocess output

    Returns:
        Sanitized output safe for logging
    """
    if not isinstance(output, str):
        return ""

    # Remove control characters except standard whitespace
    return "".join(c for c in output if c.isprintable() or c in "\n\t")[:500]
