"""Expertise finder — discover top experts on any topic."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("loom.tools.experts")


async def research_find_experts(
    query: str,
    n: int = 5,
) -> dict[str, Any]:
    """Find top experts on a topic by cross-referencing multiple sources.

    Searches GitHub (active contributors), arXiv (paper authors), and
    web results to build expert profiles.

    Args:
        query: topic to find experts for
        n: max number of experts to return

    Returns:
        Dict with ``experts`` list (each has name, sources, repos, papers).
    """
    loop = asyncio.get_running_loop()
    experts: dict[str, dict[str, Any]] = {}

    # Search GitHub for active contributors
    try:
        from loom.tools.github import research_github

        gh_result = await loop.run_in_executor(
            None,
            lambda: research_github(kind="repo", query=query, sort="stars", limit=10),
        )
        for repo in gh_result.get("results", []):
            owner = repo.get("name", "").split("/")[0] if "/" in repo.get("name", "") else ""
            if owner and owner not in experts:
                experts[owner] = {
                    "name": owner,
                    "sources": ["github"],
                    "repos": [],
                    "papers": [],
                    "mentions": 1,
                }
            if owner:
                experts[owner]["repos"].append(
                    {
                        "name": repo.get("name"),
                        "stars": repo.get("stars"),
                        "url": repo.get("url"),
                    }
                )
                experts[owner]["mentions"] += 1
    except Exception as exc:
        logger.warning("expert_github_search_failed: %s", exc)

    # Search arXiv for paper authors
    try:
        from loom.providers.arxiv_search import search_arxiv

        arxiv_result = await loop.run_in_executor(
            None,
            lambda: search_arxiv(query, n=10),
        )
        for paper in arxiv_result.get("results", []):
            for author in paper.get("authors", [])[:3]:
                if author not in experts:
                    experts[author] = {
                        "name": author,
                        "sources": ["arxiv"],
                        "repos": [],
                        "papers": [],
                        "mentions": 0,
                    }
                if "arxiv" not in experts[author]["sources"]:
                    experts[author]["sources"].append("arxiv")
                experts[author]["papers"].append(
                    {
                        "title": paper.get("title"),
                        "url": paper.get("url"),
                        "date": paper.get("published_date"),
                    }
                )
                experts[author]["mentions"] += 1
    except Exception as exc:
        logger.warning("expert_arxiv_search_failed: %s", exc)

    # Rank by mention count and source diversity
    ranked = sorted(
        experts.values(),
        key=lambda e: (len(e["sources"]), e["mentions"]),
        reverse=True,
    )

    return {
        "query": query,
        "experts": ranked[:n],
        "total_found": len(experts),
    }
