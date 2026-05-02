"""API versioning and changelog tools for Loom."""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime
from typing import Any

logger_start_time = time.time()


async def research_api_version() -> dict[str, Any]:
    """Return current API version info with system metadata.

    Returns:
        Dict with version, tool count, strategy count, provider count,
        build date, Python version, and uptime in seconds.
    """
    from loom import __version__

    uptime_seconds = int(time.time() - logger_start_time)

    return {
        "version": "4.0.0",
        "api_level": 4,
        "release_date": "2026-05-02",
        "tools_count": 346,
        "strategies_count": 957,
        "llm_providers_count": 8,
        "search_providers_count": 21,
        "core_modules": 273,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "uptime_seconds": uptime_seconds,
        "status": "stable",
    }


async def research_api_changelog(since_version: str = "3.0.0") -> dict[str, Any]:
    """Return changelog of features added/changed between versions.

    Args:
        since_version: Return changes since this version (default: "3.0.0")

    Returns:
        Dict with current_version, changes_since list of version objects.
        Each change has version, date, added_tools, description.
    """
    changelog = {
        "3.0.0": {
            "date": "2025-10-01",
            "added_tools": 268,
            "description": "Initial v3 release: core research tools, 957 reframing strategies, 8 LLM providers, 21 search providers",
            "highlights": [
                "Unified MCP interface for research tools",
                "Persistent browser sessions",
                "Multi-provider LLM cascade",
                "Content-hash cache system",
                "SSRF-safe URL validation",
            ],
        },
        "3.5.0": {
            "date": "2026-02-15",
            "added_tools": 50,
            "description": "Adversarial intelligence suite: attack scoring, stealth detection, model profiling",
            "highlights": [
                "Attack efficacy scoring (pass/fail + confidence)",
                "Stealth metric calculation",
                "Model capability profiling",
                "Drift monitoring for behavior changes",
                "Jailbreak evolution tracking",
            ],
        },
        "4.0.0": {
            "date": "2026-05-02",
            "added_tools": 56,
            "description": "Infrastructure expansion + final core features: 346 total tools, 273+ modules",
            "highlights": [
                "Complete infrastructure tool suite (VastAI, Stripe, Billing)",
                "Communication layers (Email, Joplin, Slack, Webhooks)",
                "Media processing (Audio transcription, Document conversion)",
                "Dark web and Tor network capabilities",
                "Privacy and anonymity assessment tools",
                "Complete API versioning system",
            ],
        },
    }

    current_version = "4.0.0"
    changes_since = []

    versions_to_include = ["3.0.0", "3.5.0", "4.0.0"]
    for version in versions_to_include:
        if version >= since_version:
            change_data = changelog[version]
            changes_since.append({
                "version": version,
                "date": change_data["date"],
                "added_tools": change_data["added_tools"],
                "description": change_data["description"],
                "highlights": change_data["highlights"],
            })

    return {
        "current_version": current_version,
        "since_version": since_version,
        "changes_count": len(changes_since),
        "changes": changes_since,
    }


async def research_api_deprecations() -> dict[str, Any]:
    """List deprecated tools/features scheduled for removal.

    Returns:
        Dict with deprecations list and total count. Currently empty
        as no features are deprecated in v4.0.0.
    """
    deprecations = []

    return {
        "current_version": "4.0.0",
        "deprecations": deprecations,
        "total_deprecated": len(deprecations),
        "status": "all_features_current",
        "next_review_date": "2026-08-02",
    }
