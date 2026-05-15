"""research_breach_check — Check email/password against known data breaches."""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import asyncio
import httpx

from loom.input_validators import validate_email, ValidationError
from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json, fetch_text

logger = logging.getLogger("loom.tools.breach_check")

# HaveIBeenPwned API endpoint for password k-anonymity
HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range"
HIBP_BREACH_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"


@handle_tool_errors("research_breach_check")
async def research_breach_check(email: str = "", query: str = "") -> dict[str, Any]:
    """Check if an email appears in known data breaches.

    Uses HaveIBeenPwned API (v3) to query breached accounts. Requires
    HIBP_API_KEY environment variable for full functionality. If the key
    is not available, returns instructions on how to obtain it.

    Args:
        email: Email address to check
        query: Alias for email (for convenience)

    Returns:
        Dict with keys:
          - email: input email
          - breaches_found: int (count of breaches)
          - breaches: list of dicts {name, date, data_classes}
          - api_available: bool (whether API key is configured)
          - error: str (if validation failed)
    """
    if not email and query:
        email = query

    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return {
            "email": email,
            "error": "Invalid email format",
        }

    logger.info("breach_check email=%s", email)

    api_key = os.environ.get("HIBP_API_KEY", "").strip()
    api_available = bool(api_key)

    if not api_available:
        return {
            "email": email,
            "breaches_found": 0,
            "breaches": [],
            "api_available": False,
            "message": "HIBP_API_KEY not set. Get free API key from https://haveibeenpwned.com/API/Key",
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "User-Agent": "LoomMCP/1.0",
                "hibp-api-key": api_key,
            }

            resp = await client.get(
                f"{HIBP_BREACH_URL}/{email}",
                headers=headers,
                follow_redirects=True,
            )

            # 404 = not found (good), 200 = found in breach
            if resp.status_code == 404:
                return {
                    "email": email,
                    "breaches_found": 0,
                    "breaches": [],
                    "api_available": True,
                }

            if resp.status_code == 200:
                breaches_data = resp.json()
                breaches = [
                    {
                        "name": b.get("Name", ""),
                        "date": b.get("BreachDate", ""),
                        "data_classes": b.get("DataClasses", []),
                    }
                    for b in breaches_data
                ]

                return {
                    "email": email,
                    "breaches_found": len(breaches),
                    "breaches": breaches,
                    "api_available": True,
                }

            return {
                "email": email,
                "error": f"HIBP API error: HTTP {resp.status_code}",
                "api_available": True,
            }

    except Exception as exc:
        logger.error("breach_check error: %s", exc)
        return {
            "email": email,
            "error": f"breach check failed: {str(exc)}",
            "api_available": True,
        }


@handle_tool_errors("research_password_check")
async def research_password_check(password: str) -> dict[str, Any]:
    """Check if a password appears in known password breaches using k-anonymity.

    Uses HaveIBeenPwned's k-anonymity API (no API key required). Only the
    first 5 characters of the SHA-1 hash are sent to the API, with matching
    done locally for privacy.

    Args:
        password: Password to check

    Returns:
        Dict with keys:
          - password_length: int
          - hash_prefix_sent: str (first 5 hex chars, for verification)
          - pwned_count: int (how many times this password appears in breaches)
          - is_pwned: bool (whether password was found in breaches)
          - strength_hint: str (rough strength assessment)
    """
    await asyncio.sleep(0)
    if not password or not isinstance(password, str):
        return {
            "error": "Password must be a non-empty string",
        }

    # Cap password length to prevent abuse
    if len(password) > 256:
        return {
            "error": "Password too long (max 256 characters)",
        }

    logger.info("password_check length=%d", len(password))

    try:
        # Compute SHA-1 hash (k-anonymity protocol)
        sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]

        # Query the k-anonymity range endpoint
        with httpx.Client(timeout=30.0) as client:
            headers = {
                "User-Agent": "LoomMCP/1.0",
                "Add-Padding": "true",  # HIBP adds padding to obscure result count
            }

            resp = client.get(
                f"{HIBP_RANGE_URL}/{prefix}",
                headers=headers,
            )

            if resp.status_code != 200:
                return {
                    "password_length": len(password),
                    "error": f"API error: {resp.status_code}",
                }

        # Parse response (format: SUFFIX:COUNT per line, newline-delimited)
        pwned_count = 0
        for line in resp.text.split("\n"):
            parts = line.split(":")
            if len(parts) == 2 and parts[0].upper() == suffix:
                try:
                    pwned_count = int(parts[1])
                except ValueError:
                    pass
                break

        # Simple strength assessment based on length
        if len(password) < 8:
            strength = "very weak"
        elif len(password) < 12:
            strength = "weak"
        elif len(password) < 16:
            strength = "moderate"
        elif len(password) < 20:
            strength = "strong"
        else:
            strength = "very strong"

        # Check complexity (has upper, lower, digit, special)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)

        complexity_score = sum([has_upper, has_lower, has_digit, has_special])
        if complexity_score == 4:
            strength = "very strong"
        elif complexity_score == 3 and len(password) >= 12:
            strength = "strong"

        return {
            "password_length": len(password),
            "hash_prefix_sent": prefix,
            "pwned_count": pwned_count,
            "is_pwned": pwned_count > 0,
            "strength_hint": strength,
            "complexity_components": {
                "has_uppercase": has_upper,
                "has_lowercase": has_lower,
                "has_digit": has_digit,
                "has_special": has_special,
            },
        }

    except httpx.TimeoutException:
        return {
            "password_length": len(password),
            "error": "Request timeout",
        }
    except httpx.RequestError as e:
        return {
            "password_length": len(password),
            "error": f"Request failed: {e}",
        }
    except Exception as e:
        logger.exception("Unexpected error during password check")
        return {
            "password_length": len(password),
            "error": f"Unexpected error: {type(e).__name__}: {e}",
        }
