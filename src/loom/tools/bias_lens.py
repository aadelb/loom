"""research_bias_lens — Detect methodological bias in academic papers."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.bias_lens")

# Hedging language patterns
HEDGING_PATTERNS = [
    r"\bmay\b",
    r"\bmight\b",
    r"\bperhaps\b",
    r"\bsuggests\b",
    r"\bappears\b",
    r"\bseems\b",
    r"\bprovide evidence\b",
    r"\bindicate\b",
    r"\brather\b",
    r"\bsomewhat\b",
]

# P-hacking indicators
P_HACK_PATTERNS = [
    r"p\s*[<>=]\s*0\.0[4-9]",  # p near 0.05
    r"p\s*[<>=]\s*0\.01",  # p = 0.01
    r"multiple comparisons",
    r"multiple tests",
    r"bonferroni",
    r"correction",
]

# Author self-citation patterns
SELF_CITATION_PATTERNS = [
    r"as (?:shown|demonstrated) in our (?:previous|earlier)",
    r"in our prior work",
    r"consistent with our findings",
]


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> Any:
    """Fetch JSON from URL with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("bias_lens fetch failed: %s", exc)
    return None


async def _fetch_semantic_scholar_paper(
    client: httpx.AsyncClient, paper_id: str
) -> dict[str, Any] | None:
    """Fetch paper details from Semantic Scholar API."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields=title,abstract,authors,year,citationCount,references,citations,externalIds,publicationVenue"
    data = await _get_json(client, url, timeout=20.0)
    return data


async def _fetch_semantic_scholar_citations(
    client: httpx.AsyncClient, paper_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    """Fetch citing papers from Semantic Scholar API."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations?fields=title,authors,year&limit={limit}"
    data = await _get_json(client, url, timeout=20.0)
    if data and "data" in data:
        return data["data"]
    return []


async def _fetch_arxiv_paper(
    client: httpx.AsyncClient, paper_id: str
) -> dict[str, Any] | None:
    """Fetch paper from arXiv if available."""
    url = f"https://export.arxiv.org/api/query?id_list={paper_id}&start=0&max_results=1"
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            # Parse XML - simple extraction
            text = resp.text
            if "entry" in text:
                return {"source": "arxiv", "available": True}
    except Exception as exc:
        logger.debug("arxiv fetch failed: %s", exc)
    return None


def _extract_p_values(text: str) -> list[float]:
    """Extract p-values from text."""
    p_values: list[float] = []
    # Pattern: p = 0.xxx or p < 0.xxx
    pattern = r"p\s*[=<>]\s*(0\.\d+)"
    matches = re.findall(pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            p_val = float(match)
            if 0 < p_val < 1:
                p_values.append(p_val)
        except ValueError:
            pass
    return p_values


def _count_hedging_language(text: str) -> int:
    """Count hedging language instances."""
    count = 0
    for pattern in HEDGING_PATTERNS:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


def _detect_p_hacking_indicators(text: str) -> list[str]:
    """Detect p-hacking indicators in text."""
    indicators: list[str] = []
    for pattern in P_HACK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            indicators.append(pattern.replace(r"\b", ""))
    return indicators


def _count_self_citations(text: str) -> int:
    """Count potential self-citation instances."""
    count = 0
    for pattern in SELF_CITATION_PATTERNS:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


def _analyze_citation_network(
    paper_authors: list[dict[str, Any]], citing_papers: list[dict[str, Any]]
) -> dict[str, Any]:
    """Analyze citation network for self-citations.

    Returns:
        Dict with self_citation_count, self_citation_rate, suspicious_patterns
    """
    if not paper_authors or not citing_papers:
        return {
            "self_citation_count": 0,
            "self_citation_rate": 0.0,
            "suspicious_patterns": [],
        }

    # Extract author names
    author_names = set()
    for author in paper_authors:
        if isinstance(author, dict) and "name" in author:
            author_names.add(author["name"].lower())

    # Count self-citations
    self_citation_count = 0
    for citation in citing_papers:
        if isinstance(citation, dict):
            citing_authors = citation.get("authors", [])
            for citing_author in citing_authors:
                if isinstance(citing_author, dict):
                    citing_name = citing_author.get("name", "").lower()
                    if citing_name in author_names:
                        self_citation_count += 1
                        break

    self_citation_rate = (
        self_citation_count / len(citing_papers) if citing_papers else 0.0
    )

    suspicious_patterns = []
    if self_citation_rate > 0.3:
        suspicious_patterns.append("unusually_high_self_citation")
    if self_citation_rate > 0.5:
        suspicious_patterns.append("extremely_high_self_citation")

    return {
        "self_citation_count": self_citation_count,
        "self_citation_rate": round(self_citation_rate, 3),
        "suspicious_patterns": suspicious_patterns,
    }


async def research_bias_lens(paper_id: str = "", text: str = "") -> dict[str, Any]:
    """Detect methodological bias in academic papers.

    Analyzes papers for hedging language, p-hacking indicators,
    cherry-picked citations, and potential funding bias. If paper_id
    is provided, fetches from Semantic Scholar to analyze citation network.

    Args:
        paper_id: Semantic Scholar or arXiv paper ID (optional)
        text: Paper abstract/text to analyze (optional)

    Returns:
        Dict with bias_score (0-100), bias_types list, self_citation_rate,
        p_value_distribution, and funding_bias_risk
    """
    if not paper_id and not text:
        return {
            "error": "Either paper_id or text is required",
            "bias_score": 0,
            "bias_types": [],
            "self_citation_rate": 0.0,
            "p_value_distribution": [],
            "funding_bias_risk": "unknown",
        }

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Loom-Research/1.0"}
        ) as client:
            paper_data: dict[str, Any] | None = None
            full_text = text or ""

            if paper_id:
                paper_data = await _fetch_semantic_scholar_paper(client, paper_id)
                if paper_data:
                    full_text = (
                        paper_data.get("title", "")
                        + " "
                        + (paper_data.get("abstract", "") or "")
                    )

            if not full_text:
                return {
                    "error": "Could not fetch or analyze paper",
                    "bias_score": 0,
                    "bias_types": [],
                    "self_citation_rate": 0.0,
                    "p_value_distribution": [],
                    "funding_bias_risk": "unknown",
                }

            # Extract p-values
            p_values = _extract_p_values(full_text)
            p_near_threshold = len([p for p in p_values if 0.045 <= p <= 0.055])

            # Count hedging language
            hedging_count = _count_hedging_language(full_text)

            # Detect p-hacking indicators
            p_hack_indicators = _detect_p_hacking_indicators(full_text)

            # Count self-citations
            self_cite_count = _count_self_citations(full_text)

            # Analyze citation network if we have paper data
            citation_analysis: dict[str, Any] = {
                "self_citation_count": 0,
                "self_citation_rate": 0.0,
                "suspicious_patterns": [],
            }
            if paper_data and "citations" in paper_data:
                citing_papers = await _fetch_semantic_scholar_citations(
                    client, paper_id
                )
                citation_analysis = _analyze_citation_network(
                    paper_data.get("authors", []), citing_papers
                )

            # Detect funding bias indicators
            funding_keywords = ["funded by", "grant", "supported by", "acknowledgments"]
            funding_mentioned = any(
                kw in full_text.lower() for kw in funding_keywords
            )
            funding_bias_risk = (
                "potential" if funding_mentioned else "undisclosed"
            )

            # Calculate bias score (0-100)
            bias_score = 0

            # Hedging language (0-20 points)
            if hedging_count > 20:
                bias_score += 20
            elif hedging_count > 10:
                bias_score += 15
            elif hedging_count > 5:
                bias_score += 10

            # P-hacking indicators (0-25 points)
            if p_hack_indicators:
                bias_score += min(25, len(p_hack_indicators) * 10)
            if p_near_threshold > 0:
                bias_score += min(15, p_near_threshold * 5)

            # Self-citation signals (0-20 points)
            if self_cite_count > 5:
                bias_score += 20
            elif self_cite_count > 2:
                bias_score += 10
            elif self_cite_count > 0:
                bias_score += 5

            # Citation network analysis (0-15 points)
            if citation_analysis["self_citation_rate"] > 0.3:
                bias_score += 15
            elif citation_analysis["self_citation_rate"] > 0.2:
                bias_score += 10
            elif citation_analysis["self_citation_rate"] > 0.1:
                bias_score += 5

            # Funding disclosure (0-10 points)
            if not funding_mentioned and "acknowledgments" not in full_text.lower():
                bias_score += 10

            bias_score = min(100, bias_score)

            # Identify bias types
            bias_types: list[str] = []
            if hedging_count > 15:
                bias_types.append("excessive_hedging")
            if p_hack_indicators:
                bias_types.append("p_hacking_indicators")
            if p_near_threshold > 0:
                bias_types.append("p_values_near_threshold")
            if self_cite_count > 3:
                bias_types.append("high_self_citation_rate")
            if citation_analysis["self_citation_rate"] > 0.2:
                bias_types.append("biased_citation_network")
            if not funding_mentioned:
                bias_types.append("no_funding_disclosure")

            return {
                "bias_score": bias_score,
                "bias_types": bias_types,
                "self_citation_rate": round(citation_analysis["self_citation_rate"], 3),
                "p_value_distribution": sorted(p_values)[:10],
                "p_values_near_threshold": p_near_threshold,
                "hedging_language_count": hedging_count,
                "funding_bias_risk": funding_bias_risk,
                "paper_id": paper_id,
                "analysis_timestamp": asyncio.get_event_loop().time(),
            }

    return await _run()
