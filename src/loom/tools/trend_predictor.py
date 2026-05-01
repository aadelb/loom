"""Trend prediction tool — analyze research publication patterns to predict emerging trends."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.trend_predictor")

_ARXIV_API = "http://export.arxiv.org/api/query"
_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_GITHUB_API = "https://api.github.com/search/repositories"
_HN_API = "https://hn.algolia.com/api/v1/search"


async def _fetch_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> Any:
    """Fetch JSON with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("trend_predictor fetch failed url=%s: %s", url[:80], exc)
    return None


async def _fetch_text(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> str:
    """Fetch text with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("trend_predictor text fetch failed url=%s: %s", url[:80], exc)
    return ""


async def _arxiv_publication_rate(
    client: httpx.AsyncClient, topic: str
) -> dict[str, Any]:
    """Analyze arXiv publication rate by month."""
    try:
        query = f"all:{quote(topic)}"
        url = f"{_ARXIV_API}?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results=100"
        text = await _fetch_text(client, url, timeout=25.0)

        if not text:
            return {"papers_per_month": {}, "total_papers": 0}

        # Parse arXiv XML response for publication dates
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(text)
            namespace = {"atom": "http://www.w3.org/2005/Atom"}

            papers_by_month: dict[str, int] = {}
            total = 0

            for entry in root.findall("atom:entry", namespace):
                published = entry.find("atom:published", namespace)
                if published is not None and published.text:
                    date_str = published.text[:7]  # YYYY-MM
                    papers_by_month[date_str] = papers_by_month.get(date_str, 0) + 1
                    total += 1

            return {"papers_per_month": papers_by_month, "total_papers": total}
        except Exception as exc:
            logger.debug("arxiv_publication_rate parse failed: %s", exc)
            return {"papers_per_month": {}, "total_papers": 0}
    except Exception as exc:
        logger.debug("arxiv_publication_rate failed: %s", exc)
        return {"papers_per_month": {}, "total_papers": 0}


async def _semantic_scholar_citations(
    client: httpx.AsyncClient, topic: str
) -> dict[str, Any]:
    """Analyze citation velocity from Semantic Scholar."""
    try:
        url = f"{_SEMANTIC_SCHOLAR_API}?query={quote(topic)}&limit=50&fields=year,citationCount"
        data = await _fetch_json(client, url, timeout=20.0)

        if not data or "data" not in data:
            return {"citations_per_year": {}, "avg_citations": 0, "max_citations": 0}

        citations_by_year: dict[int, list[int]] = {}
        all_citations: list[int] = []

        for paper in data.get("data", []):
            year = paper.get("year")
            citations = paper.get("citationCount", 0)

            if year and citations:
                if year not in citations_by_year:
                    citations_by_year[year] = []
                citations_by_year[year].append(citations)
                all_citations.append(citations)

        # Compute average and max
        avg_citations = (
            sum(all_citations) / len(all_citations) if all_citations else 0
        )
        max_citations = max(all_citations) if all_citations else 0

        # Convert to dict of year -> avg citations
        avg_by_year = {
            year: sum(cits) / len(cits)
            for year, cits in citations_by_year.items()
        }

        return {
            "citations_per_year": avg_by_year,
            "avg_citations": round(avg_citations, 2),
            "max_citations": max_citations,
        }
    except Exception as exc:
        logger.debug("semantic_scholar_citations failed: %s", exc)
        return {"citations_per_year": {}, "avg_citations": 0, "max_citations": 0}


async def _github_repo_momentum(
    client: httpx.AsyncClient, topic: str
) -> dict[str, Any]:
    """Analyze GitHub repository growth momentum."""
    try:
        url = f"{_GITHUB_API}?q={quote(topic)}&sort=stars&order=desc&per_page=20"
        data = await _fetch_json(client, url, timeout=20.0)

        if not data or "items" not in data:
            return {"repos": 0, "avg_stars": 0, "avg_forks": 0, "total_stars": 0}

        repos = data.get("items", [])
        if not repos:
            return {"repos": 0, "avg_stars": 0, "avg_forks": 0, "total_stars": 0}

        stars = [r.get("stargazers_count", 0) for r in repos]
        forks = [r.get("forks_count", 0) for r in repos]

        avg_stars = sum(stars) / len(stars) if stars else 0
        avg_forks = sum(forks) / len(forks) if forks else 0
        total_stars = sum(stars)

        return {
            "repos": len(repos),
            "avg_stars": round(avg_stars, 0),
            "avg_forks": round(avg_forks, 0),
            "total_stars": total_stars,
        }
    except Exception as exc:
        logger.debug("github_repo_momentum failed: %s", exc)
        return {"repos": 0, "avg_stars": 0, "avg_forks": 0, "total_stars": 0}


async def _hackernews_discussion(
    client: httpx.AsyncClient, topic: str
) -> dict[str, Any]:
    """Analyze HackerNews discussion frequency and engagement."""
    try:
        url = f"{_HN_API}?query={quote(topic)}&tags=story&hitsPerPage=50"
        data = await _fetch_json(client, url, timeout=20.0)

        if not data or "hits" not in data:
            return {"stories": 0, "avg_points": 0, "avg_comments": 0}

        hits = data.get("hits", [])
        if not hits:
            return {"stories": 0, "avg_points": 0, "avg_comments": 0}

        points = [h.get("points", 0) for h in hits]
        comments = [h.get("num_comments", 0) for h in hits]

        avg_points = sum(points) / len(points) if points else 0
        avg_comments = sum(comments) / len(comments) if comments else 0

        return {
            "stories": len(hits),
            "avg_points": round(avg_points, 1),
            "avg_comments": round(avg_comments, 1),
        }
    except Exception as exc:
        logger.debug("hackernews_discussion failed: %s", exc)
        return {"stories": 0, "avg_points": 0, "avg_comments": 0}


def _compute_trend_direction(
    arxiv_data: dict[str, Any],
    semantic_data: dict[str, Any],
    github_data: dict[str, Any],
    hackernews_data: dict[str, Any],
) -> tuple[str, float]:
    """Compute trend direction (rising/stable/declining) with confidence.

    Returns:
        (trend_direction, confidence_0_to_1)
    """
    signals: list[float] = []  # Trend scores: 1.0 = rising, 0.0 = declining

    # Signal 1: arXiv publication rate (last 3 months vs previous 3 months)
    papers_by_month = arxiv_data.get("papers_per_month", {})
    if papers_by_month:
        sorted_months = sorted(papers_by_month.keys())
        if len(sorted_months) >= 6:
            recent_3 = sorted(sorted_months)[-3:]
            previous_3 = sorted(sorted_months)[-6:-3]
            recent_sum = sum(
                papers_by_month.get(m, 0) for m in recent_3
            )
            previous_sum = sum(
                papers_by_month.get(m, 0) for m in previous_3
            )
            if previous_sum > 0:
                growth = (recent_sum - previous_sum) / previous_sum
                signals.append(min(1.0, max(0.0, 0.5 + growth)))

    # Signal 2: Citation velocity (increasing citations)
    avg_citations = semantic_data.get("avg_citations", 0)
    if avg_citations > 10:
        signals.append(0.8)  # High citation = rising trend
    elif avg_citations > 5:
        signals.append(0.6)
    elif avg_citations > 0:
        signals.append(0.4)
    else:
        signals.append(0.2)

    # Signal 3: GitHub momentum (more stars = rising)
    total_stars = github_data.get("total_stars", 0)
    if total_stars > 10000:
        signals.append(0.9)  # Massive adoption
    elif total_stars > 1000:
        signals.append(0.7)
    elif total_stars > 100:
        signals.append(0.5)
    elif total_stars > 0:
        signals.append(0.3)
    else:
        signals.append(0.1)

    # Signal 4: HackerNews engagement
    hn_stories = hackernews_data.get("stories", 0)
    hn_engagement = hackernews_data.get("avg_points", 0) * 0.5 + hackernews_data.get(
        "avg_comments", 0
    ) * 0.5
    if hn_stories > 20 and hn_engagement > 100:
        signals.append(0.85)  # Strong community interest
    elif hn_stories > 10:
        signals.append(0.65)
    elif hn_stories > 5:
        signals.append(0.45)
    elif hn_stories > 0:
        signals.append(0.3)
    else:
        signals.append(0.1)

    if not signals:
        return ("stable", 0.0)

    avg_signal = sum(signals) / len(signals)
    confidence = len(signals) / 4.0  # Max confidence with 4 signals

    if avg_signal >= 0.65:
        trend = "rising"
    elif avg_signal <= 0.35:
        trend = "declining"
    else:
        trend = "stable"

    return (trend, min(1.0, confidence))


def _predict_next_3_months(
    arxiv_data: dict[str, Any], trend: str
) -> dict[str, Any]:
    """Predict trend for next 3 months based on historical pattern."""
    papers_by_month = arxiv_data.get("papers_per_month", {})

    if not papers_by_month:
        return {"predicted_papers": 0, "growth_rate": 0.0}

    sorted_months = sorted(papers_by_month.keys())
    if len(sorted_months) < 3:
        return {"predicted_papers": 0, "growth_rate": 0.0}

    recent_3 = sorted(sorted_months)[-3:]
    recent_avg = sum(papers_by_month.get(m, 0) for m in recent_3) / 3.0

    # Apply trend multiplier
    trend_multiplier = {"rising": 1.2, "stable": 1.0, "declining": 0.8}
    predicted = int(recent_avg * trend_multiplier.get(trend, 1.0))

    # Calculate growth rate
    oldest_month = sorted_months[0]
    oldest_count = papers_by_month.get(oldest_month, 1)
    growth_rate = ((recent_avg - oldest_count) / oldest_count) if oldest_count > 0 else 0.0

    return {"predicted_papers": predicted, "growth_rate": round(growth_rate, 3)}


async def research_trend_predict(topic: str, time_range_days: int = 90) -> dict[str, Any]:
    """Predict research trends by analyzing publication patterns.

    Analyzes arXiv publication rates, Semantic Scholar citation velocity,
    GitHub repository momentum, and HackerNews discussion frequency to
    determine if a research topic is trending up, stable, or declining.

    Args:
        topic: research topic or keyword (e.g., "transformers", "quantum computing")
        time_range_days: historical window for trend analysis (default: 90 days)

    Returns:
        Dict with ``topic``, ``trend_direction`` (rising/stable/declining),
        ``confidence`` (0-1), ``publication_rate``, ``citation_velocity``,
        ``github_momentum``, ``community_buzz``, ``prediction_next_3_months``,
        and ``analysis_timestamp``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0 (trend analysis)"},
        ) as client:
            # Run all data collection tasks in parallel
            arxiv_task = _arxiv_publication_rate(client, topic)
            semantic_task = _semantic_scholar_citations(client, topic)
            github_task = _github_repo_momentum(client, topic)
            hn_task = _hackernews_discussion(client, topic)

            (arxiv_data, semantic_data, github_data, hn_data) = await asyncio.gather(
                arxiv_task, semantic_task, github_task, hn_task, return_exceptions=True
            )

            # Handle any exceptions
            if isinstance(arxiv_data, Exception):
                arxiv_data = {"papers_per_month": {}, "total_papers": 0}
            if isinstance(semantic_data, Exception):
                semantic_data = {"citations_per_year": {}, "avg_citations": 0, "max_citations": 0}
            if isinstance(github_data, Exception):
                github_data = {"repos": 0, "avg_stars": 0, "avg_forks": 0, "total_stars": 0}
            if isinstance(hn_data, Exception):
                hn_data = {"stories": 0, "avg_points": 0, "avg_comments": 0}

            # Compute trend direction
            trend_direction, confidence = _compute_trend_direction(
                arxiv_data, semantic_data, github_data, hn_data
            )

            # Predict next 3 months
            prediction = _predict_next_3_months(arxiv_data, trend_direction)

            return {
                "topic": topic,
                "trend_direction": trend_direction,
                "confidence": round(confidence, 2),
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "publication_rate": {
                    "total_papers": arxiv_data.get("total_papers", 0),
                    "papers_per_month": arxiv_data.get("papers_per_month", {}),
                },
                "citation_velocity": {
                    "avg_citations": semantic_data.get("avg_citations", 0),
                    "max_citations": semantic_data.get("max_citations", 0),
                    "citations_per_year": semantic_data.get("citations_per_year", {}),
                },
                "github_momentum": {
                    "total_repos": github_data.get("repos", 0),
                    "avg_stars": github_data.get("avg_stars", 0),
                    "avg_forks": github_data.get("avg_forks", 0),
                    "total_stars": github_data.get("total_stars", 0),
                },
                "community_buzz": {
                    "hackernews_stories": hn_data.get("stories", 0),
                    "avg_points": hn_data.get("avg_points", 0),
                    "avg_comments": hn_data.get("avg_comments", 0),
                },
                "prediction_next_3_months": {
                    "predicted_papers": prediction.get("predicted_papers", 0),
                    "growth_rate": prediction.get("growth_rate", 0.0),
                },
            }

    return await _run()
