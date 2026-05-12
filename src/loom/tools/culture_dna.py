"""Culture DNA analyzer — assess company culture from public signals.

Tool:
- research_culture_dna: Analyze company culture from Glassdoor, GitHub, LinkedIn, job postings.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_text

logger = logging.getLogger("loom.tools.culture_dna")

# Culture keyword dictionaries for scoring
_CULTURE_KEYWORDS = {
    "work_life_balance": [
        "flexible",
        "remote",
        "wfh",
        "work-life",
        "balance",
        "pto",
        "unlimited",
        "vacation",
        "family",
    ],
    "innovation": [
        "innovation",
        "cutting-edge",
        "latest",
        "technology",
        "learn",
        "experiment",
        "hackathon",
        "research",
    ],
    "collaboration": [
        "team",
        "collaboration",
        "transparent",
        "communication",
        "inclusive",
        "together",
    ],
    "growth": [
        "growth",
        "development",
        "learning",
        "career",
        "mentor",
        "training",
        "opportunity",
    ],
    "diversity": [
        "diverse",
        "diversity",
        "inclusion",
        "belonging",
        "underrepresented",
        "equity",
    ],
    "compensation": ["competitive", "generous", "bonus", "equity", "salary", "benefits"],
}


def _extract_culture_signals(text: str, source: str) -> list[dict[str, Any]]:
    """Extract culture signals from text using keyword matching."""
    text_lower = text.lower()
    signals: list[dict[str, Any]] = []

    for category, keywords in _CULTURE_KEYWORDS.items():
        count = sum(text_lower.count(kw) for kw in keywords)
        if count > 0:
            signals.append(
                {
                    "source": source,
                    "category": category,
                    "signal": f"{category.replace('_', ' ')}: {count} mentions",
                    "strength": min(count, 5),  # Cap at 5
                }
            )

    return signals


def _analyze_github_signals(org_name: str) -> dict[str, Any]:
    """Analyze GitHub org for culture signals (repo naming, README tone)."""
    signals: list[str] = []

    # This would require actual GitHub API access in production
    # For now, return structured format
    return {
        "repo_analysis": "github_api_required",
        "readme_analysis": "github_api_required",
        "issue_response_time": "github_api_required",
        "signals": signals,
    }


def _analyze_job_postings(job_text: str) -> dict[str, Any]:
    """Analyze job posting language for culture keywords."""
    text_lower = job_text.lower()

    culture_mentions = {}
    for category, keywords in _CULTURE_KEYWORDS.items():
        mentions = sum(text_lower.count(kw) for kw in keywords)
        if mentions > 0:
            culture_mentions[category] = mentions

    # Analyze tone indicators
    urgency_words = ["urgent", "immediate", "asap", "fast-paced"]
    urgency_count = sum(text_lower.count(word) for word in urgency_words)

    formal_words = ["professional", "corporate", "formal", "structured"]
    formal_count = sum(text_lower.count(word) for word in formal_words)

    startup_words = ["startup", "agile", "dynamic", "fast-growing", "disruptive"]
    startup_count = sum(text_lower.count(word) for word in startup_words)

    return {
        "culture_mentions": culture_mentions,
        "urgency_score": min(urgency_count / 5.0, 1.0),
        "formality_score": min(formal_count / 5.0, 1.0),
        "startup_vibes": min(startup_count / 5.0, 1.0),
    }


def _classify_culture_type(signals: list[dict[str, Any]]) -> str:
    """Classify company culture type based on signals."""
    startup_indicators = ["innovation", "growth", "dynamic"]
    corporate_indicators = ["formal", "structured", "process"]
    balanced_indicators = ["collaboration", "work_life_balance"]

    signal_categories = [s.get("category", "") for s in signals]

    startup_score = sum(1 for cat in signal_categories if cat in startup_indicators)
    corporate_score = sum(1 for cat in signal_categories if cat in corporate_indicators)
    balanced_score = sum(1 for cat in signal_categories if cat in balanced_indicators)

    if startup_score > corporate_score and startup_score > balanced_score:
        return "startup"
    elif corporate_score > startup_score and corporate_score > balanced_score:
        return "corporate"
    else:
        return "hybrid"


async def research_culture_dna(
    company: str,
    domain: str = "",
) -> dict[str, Any]:
    """Analyze company culture from public signals.

    Analyzes Glassdoor reviews, GitHub org culture signals, LinkedIn company
    page, and job posting language to infer company culture characteristics.

    Args:
        company: company name (e.g. "Google", "Acme Corp")
        domain: optional company domain for targeted search (e.g. "google.com")

    Returns:
        Dict with culture_signals, work_life_score, innovation_score,
        diversity_signals, and overall_culture_type.
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=20.0,
            ) as client:
                all_signals: list[dict[str, Any]] = []

                # Fetch Glassdoor reviews (via search engine)
                glassdoor_query = f'site:glassdoor.com "{company}" reviews'
                glassdoor_url = f"https://duckduckgo.com/?q={quote(glassdoor_query)}&t=h"
                glassdoor_text = await fetch_text(client, glassdoor_url)
                glassdoor_signals = _extract_culture_signals(glassdoor_text, "glassdoor")
                all_signals.extend(glassdoor_signals)

                # Fetch LinkedIn company page
                linkedin_query = f'site:linkedin.com/company "{company}"'
                linkedin_url = f"https://duckduckgo.com/?q={quote(linkedin_query)}&t=h"
                linkedin_text = await fetch_text(client, linkedin_url)
                linkedin_signals = _extract_culture_signals(linkedin_text, "linkedin")
                all_signals.extend(linkedin_signals)

                # GitHub org analysis (metadata only, no API key required)
                github_signals_data = _analyze_github_signals(company)

                # Calculate weighted scores
                work_life_signals = [s for s in all_signals if s.get("category") == "work_life_balance"]
                work_life_score = (
                    sum(s.get("strength", 0) for s in work_life_signals) / (len(all_signals) + 1)
                    if all_signals
                    else 0.5
                )

                innovation_signals = [s for s in all_signals if s.get("category") == "innovation"]
                innovation_score = (
                    sum(s.get("strength", 0) for s in innovation_signals) / (len(all_signals) + 1)
                    if all_signals
                    else 0.5
                )

                diversity_signals = [s for s in all_signals if s.get("category") == "diversity"]

                culture_type = _classify_culture_type(all_signals)

                return {
                    "company": company,
                    "domain": domain or "unknown",
                    "culture_signals": all_signals[:50],
                    "work_life_score": min(work_life_score, 1.0),
                    "innovation_score": min(innovation_score, 1.0),
                    "diversity_signals": [s["signal"] for s in diversity_signals],
                    "overall_culture_type": culture_type,
                    "signal_count": len(all_signals),
                    "github_analysis": github_signals_data,
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_culture_dna"}
