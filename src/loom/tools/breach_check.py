"""research_breach_check — Check email/password against known data breaches."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Any

import httpx

from loom.input_validators import validate_email, ValidationError
from loom.error_responses import handle_tool_errors

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
