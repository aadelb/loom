"""Quota status tool for free-tier LLM providers.

Exposes quota usage and remaining limits for Groq, NVIDIA NIM, and Gemini
through a single MCP tool. Can return status for all providers or a specific one.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.quota_tracker import QUOTA_LIMITS, get_quota_tracker
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.quota_status")


@handle_tool_errors("research_quota_status")
def research_quota_status(provider: str | None = None) -> dict[str, Any]:
    """Get API quota usage and remaining limits for free-tier LLM providers.

    Returns current usage (requests and tokens) for each minute and day,
    plus remaining quota. Useful for monitoring when approaching limits
    and deciding whether to fallback to different providers.

    Args:
        provider: Optional provider name to get status for (groq, nvidia_nim, gemini).
                 If None, returns status for all providers.

    Returns:
        Dict with structure:
        {
            "timestamp_utc": "2026-05-04T15:30:45Z",
            "providers": {
                "groq": { ... QuotaStatus dict ... },
                "nvidia_nim": { ... QuotaStatus dict ... },
                "gemini": { ... QuotaStatus dict ... },
            },
            "summary": {
                "all_providers_healthy": bool,
                "providers_near_limit": [ list of provider names ],
                "providers_exhausted": [ list of provider names ],
            }
        }
        or if provider is specified:
        {
            "timestamp_utc": "2026-05-04T15:30:45Z",
            "provider": "groq",
            ... QuotaStatus dict ...
        }

    Raises:
        ValueError: If provider name is invalid
    """
    from datetime import UTC, datetime

    tracker = get_quota_tracker()

    # Validate provider if specified
    if provider is not None:
        if provider not in QUOTA_LIMITS:
            raise ValueError(
                f"unknown provider: {provider}. "
                f"Valid providers: {', '.join(QUOTA_LIMITS.keys())}"
            )

    timestamp = datetime.now(UTC).isoformat()

    # Single provider query
    if provider:
        try:
            status = tracker.get_status(provider)
            result = status.to_dict()
            result["timestamp_utc"] = timestamp
            result["is_near_limit"] = tracker.is_near_limit(provider)
            result["should_fallback"] = tracker.should_fallback(provider)
            logger.info("quota_status_queried provider=%s", provider)
            return result
        except ValueError as e:
            logger.error("quota_status_error provider=%s error=%s", provider, e)
            raise

    # All providers query
    all_statuses: dict[str, dict[str, Any]] = {}
    providers_near_limit: list[str] = []
    providers_exhausted: list[str] = []

    for prov_name in sorted(QUOTA_LIMITS.keys()):
        try:
            status = tracker.get_status(prov_name)
            status_dict = status.to_dict()
            status_dict["is_near_limit"] = tracker.is_near_limit(prov_name)
            status_dict["should_fallback"] = tracker.should_fallback(prov_name)
            all_statuses[prov_name] = status_dict

            if status_dict["should_fallback"]:
                providers_exhausted.append(prov_name)
            elif status_dict["is_near_limit"]:
                providers_near_limit.append(prov_name)
        except ValueError as e:
            logger.error("quota_status_error provider=%s error=%s", prov_name, e)
            # Include error in response but continue
            all_statuses[prov_name] = {"error": str(e)}

    result = {
        "timestamp_utc": timestamp,
        "providers": all_statuses,
        "summary": {
            "all_providers_healthy": len(providers_exhausted) == 0
            and len(providers_near_limit) == 0,
            "providers_near_limit": providers_near_limit,
            "providers_exhausted": providers_exhausted,
        },
    }

    logger.info(
        "quota_status_all_providers near_limit=%d exhausted=%d",
        len(providers_near_limit),
        len(providers_exhausted),
    )
    return result
