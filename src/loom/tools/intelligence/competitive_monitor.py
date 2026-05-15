"""Competitive intelligence monitor — track GitHub competitors and Loom positioning."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json

logger = logging.getLogger("loom.tools.competitive_monitor")

DEFAULT_COMPETITORS = [
    "leondz/garak",
    "Azure/PyRIT",
    "centerforaisafety/HarmBench",
    "promptfoo/promptfoo",
]

LOOM_CAPABILITIES = {
    "tools_count": 220,
    "strategies_count": 957,
    "models_supported": 8,
    "llm_providers": ["groq", "nvidia_nim", "deepseek", "gemini", "moonshot", "openai", "anthropic", "vllm"],
}

COMPETITOR_PROFILES = {
    "leondz/garak": {
        "tools_count": 40,
        "strategies_count": 150,
        "models_supported": 12,
        "strengths": ["Modular probes", "Well-documented", "Active community"],
        "weaknesses": ["Limited orchestration", "No evolution"],
    },
    "Azure/PyRIT": {
        "tools_count": 25,
        "strategies_count": 80,
        "models_supported": 6,
        "strengths": ["Azure integration", "Clean API"],
        "weaknesses": ["Limited strategies"],
    },
    "centerforaisafety/HarmBench": {
        "tools_count": 15,
        "strategies_count": 200,
        "models_supported": 20,
        "strengths": ["Comprehensive benchmark"],
        "weaknesses": ["Read-only evaluator"],
    },
    "promptfoo/promptfoo": {
        "tools_count": 35,
        "strategies_count": 100,
        "models_supported": 15,
        "strengths": ["Easy testing UI", "Wide model support"],
        "weaknesses": ["Limited strategies"],
    },
}


async def _fetch_repo_stats(
    client: httpx.AsyncClient, owner: str, repo: str
) -> dict[str, Any]:
    """Fetch GitHub repo stats via public API."""
    try:
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_resp = await client.get(repo_url, timeout=10.0)

        if repo_resp.status_code != 200:
            return {"owner": owner, "repo": repo, "error": f"HTTP {repo_resp.status_code}"}

        repo_data = repo_resp.json()

        # Fetch latest release
        latest_release = None
        try:
            rd = await fetch_json(client,
                f"{repo_url}/releases/latest", timeout=10.0
            )
            if rd:
                latest_release = {
                    "tag": rd.get("tag_name"),
                    "date": rd.get("published_at"),
                }
        except Exception:
            pass

        pushed_at = repo_data.get("pushed_at")
        last_commit = (
            datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            if pushed_at
            else None
        )

        return {
            "owner": owner,
            "repo": repo,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "language": repo_data.get("language"),
            "description": repo_data.get("description", ""),
            "latest_release": latest_release,
            "last_commit_days_ago": (datetime.now(UTC) - last_commit).days
            if last_commit
            else None,
            "url": repo_data.get("html_url"),
        }

    except Exception as exc:
        logger.error("Error fetching %s/%s: %s", owner, repo, exc)
        return {"owner": owner, "repo": repo, "error": str(exc)}


@handle_tool_errors("research_monitor_competitors")
async def research_monitor_competitors(
    competitors: list[str] | None = None,
) -> dict[str, Any]:
    """Monitor GitHub competitors for activity and positioning.

    Args:
        competitors: List of "owner/repo" strings. Defaults to 4 leading frameworks.

    Returns:
        Dict with competitors[], latest_changes[], threat_level, timestamp
    """
    if competitors is None:
        competitors = DEFAULT_COMPETITORS

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [
                _fetch_repo_stats(client, *repo.split("/"))
                for repo in competitors
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            stats = [r for r in results if isinstance(r, dict)]

            # Identify recent activity (last 7 days)
            latest_changes = [
                {
                    "repo": f"{s['owner']}/{s['repo']}",
                    "last_commit_days_ago": s.get("last_commit_days_ago"),
                    "latest_release": s.get("latest_release"),
                }
                for s in stats
                if s.get("last_commit_days_ago") is not None
                and s.get("last_commit_days_ago") <= 7
            ]

            # Calculate threat level
            total_stars = sum(s.get("stars", 0) for s in stats)
            threat_level = "high" if total_stars > 10000 or len(latest_changes) >= 3 else (
                "medium" if total_stars > 5000 or len(latest_changes) >= 2 else "low"
            )

            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "competitors": stats,
                "latest_changes": latest_changes,
                "threat_level": threat_level,
                "aggregate_stats": {
                    "total_repos": len(stats),
                    "total_stars": total_stars,
                    "recent_activity_count": len(latest_changes),
                },
            }

    except Exception as exc:
        logger.error("Error monitoring competitors: %s", exc)
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(exc),
            "competitors": [],
            "latest_changes": [],
            "threat_level": "unknown",
        }


@handle_tool_errors("research_competitive_advantage")
def research_competitive_advantage() -> dict[str, Any]:
    """Compare Loom capabilities vs known competitors.

    Returns:
        Dict with loom_advantages[], competitor_advantages{}, gaps_to_fill[], overall_position
    """
    try:
        loom_advantages = [
            f"220+ tools (vs avg ~{sum(p['tools_count'] for p in COMPETITOR_PROFILES.values()) // len(COMPETITOR_PROFILES)} competitors)",
            "957 jailbreak strategies (highest in market)",
            "8 LLM providers with automatic cascade",
            "Multi-stage orchestration and evolution tracking",
            "Attack scoring and consensus building",
            "Arabic language specialization",
        ]

        competitor_advantages = {
            name: profile["strengths"]
            for name, profile in COMPETITOR_PROFILES.items()
        }

        gaps_to_fill = [
            "Improve web dashboard UI",
            "Build marketplace for third-party strategies",
            "Add automated compliance reporting",
            "Develop fine-tuning pipeline",
        ]

        overall_position = (
            "Loom is the most comprehensive jailbreak framework with deepest "
            "orchestration capabilities. Strengths: scale (220+ tools), strategy "
            "depth (957), multi-model support. Threats: Garak community, PyRIT "
            "enterprise integration, HarmBench academic rigor. Key defense: maintain "
            "strategy velocity and improve UI."
        )

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "loom": {
                "tools_count": LOOM_CAPABILITIES["tools_count"],
                "strategies_count": LOOM_CAPABILITIES["strategies_count"],
                "models_supported": LOOM_CAPABILITIES["models_supported"],
                "advantages": loom_advantages,
            },
            "competitors": competitor_advantages,
            "gaps_to_fill": gaps_to_fill,
            "overall_position": overall_position,
        }

    except Exception as exc:
        logger.error("Error analyzing competitive advantage: %s", exc)
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(exc),
        }
