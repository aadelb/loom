"""research_fact_check — Verify claims across multiple sources.

Cross-references claims against Google Fact Check API, Wikipedia, Semantic Scholar,
and aggregates fact-check sources (Snopes, PolitiFact, FactCheck.org).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.fact_checker")


async def _fetch_json(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> Any:
    """Fetch and parse JSON from URL, returns None on error."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("fact_checker fetch failed: %s", exc)
    return None


async def _fetch_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> str:
    """Fetch text from URL, returns empty string on error."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("fact_checker text fetch failed: %s", exc)
    return ""


async def _search_google_fact_check(
    client: httpx.AsyncClient, claim: str, api_key: str | None = None
) -> list[dict[str, Any]]:
    """Search Google Fact Check API for fact checks on claim."""
    if not api_key:
        # Try to get from config
        try:
            from loom.config import get_config
            api_key = get_config().get("GOOGLE_AI_KEY")
        except Exception:
            logger.debug("get_config failed")

    if not api_key:
        logger.debug("Google Fact Check API key not available")
        return []

    url = (
        f"https://factchecktools.googleapis.com/v1alpha1/claims:search?"
        f"query={quote(claim)}&key={api_key}"
    )
    data = await _fetch_json(client, url)
    if not data or "claims" not in data:
        return []

    sources = []
    for claim_result in data.get("claims", []):
        review_sources = claim_result.get("claimReview", [])
        for review in review_sources:
            sources.append({
                "source": review.get("publisher", {}).get("name", "Unknown"),
                "url": review.get("url", ""),
                "assessment": review.get("textualRating", "Unknown"),
                "snippet": claim_result.get("text", ""),
            })

    return sources


async def _search_snopes_politifact_factcheck(
    client: httpx.AsyncClient, claim: str
) -> list[dict[str, Any]]:
    """Search Snopes, PolitiFact, and FactCheck.org via DuckDuckGo."""
    url = (
        f"https://duckduckgo.com/html/?q={quote(claim)} "
        f"(site:snopes.com OR site:politifact.com OR site:factcheck.org)"
    )
    html = await _fetch_text(client, url, timeout=20.0)
    if not html:
        return []

    sources = []

    # Extract URLs from HTML (very basic parsing)
    url_pattern = re.compile(
        r'href=["\']?(https?://(?:snopes|politifact|factcheck)\.org[^\s"\'<>]+)',
        re.IGNORECASE,
    )
    for match in url_pattern.finditer(html):
        found_url = match.group(1)
        source_name = "Snopes"
        if "politifact" in found_url.lower():
            source_name = "PolitiFact"
        elif "factcheck.org" in found_url.lower():
            source_name = "FactCheck.org"

        sources.append({
            "source": source_name,
            "url": found_url,
            "assessment": "Fact-check source",
            "snippet": claim[:100],
        })

    return sources[:5]  # Limit to 5 results


async def _search_wikipedia_for_claim(
    client: httpx.AsyncClient, claim: str
) -> list[dict[str, Any]]:
    """Search Wikipedia for articles related to claim."""
    url = (
        f"https://en.wikipedia.org/w/api.php?"
        f"action=query&srsearch={quote(claim)}&"
        f"srnamespace=0&srlimit=3&format=json"
    )
    data = await _fetch_json(client, url)
    if not data or "query" not in data:
        return []

    sources = []
    search_results = data.get("query", {}).get("search", [])

    for result in search_results:
        title = result.get("title", "")
        snippet = result.get("snippet", "").replace("<span class='searchmatch'>", "")
        snippet = snippet.replace("</span>", "")
        snippet = re.sub(r"<[^>]+>", "", snippet)  # Remove HTML tags

        if title:
            sources.append({
                "source": f"Wikipedia: {title}",
                "url": f"https://en.wikipedia.org/wiki/{quote(title)}",
                "assessment": "Reference source",
                "snippet": snippet[:200],
            })

    return sources


async def _search_semantic_scholar_for_claim(
    client: httpx.AsyncClient, claim: str
) -> list[dict[str, Any]]:
    """Search Semantic Scholar for academic papers related to claim."""
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search?"
        f"query={quote(claim)}&limit=3&"
        f"fields=title,abstract,year,url"
    )
    data = await _fetch_json(client, url, timeout=20.0)
    if not data or "papers" not in data:
        return []

    sources = []
    for paper in data.get("papers", []):
        title = paper.get("title", "")
        url = paper.get("url", "")
        abstract = paper.get("abstract", "")[:200]

        if title:
            sources.append({
                "source": f"Semantic Scholar: {title}",
                "url": url or "",
                "assessment": "Academic source",
                "snippet": abstract,
            })

    return sources


def _aggregate_assessments(sources: list[dict[str, Any]]) -> tuple[str, float]:
    """Aggregate fact-check assessments into a single verdict and confidence.

    Returns:
        (verdict, confidence) where verdict is one of:
        - "supported": claim is supported by sources
        - "refuted": claim is refuted by sources
        - "mixed": conflicting assessments
        - "unverified": insufficient evidence
    """
    if not sources:
        return "unverified", 0.0

    # Count assessment types (case-insensitive, partial matching)
    supported_count = 0
    refuted_count = 0
    mixed_count = 0

    for source in sources:
        assessment = (source.get("assessment") or "").lower()

        # Match positive assessments
        if any(x in assessment for x in ["true", "correct", "yes", "support"]):
            supported_count += 1
        # Match negative assessments
        elif any(x in assessment for x in ["false", "incorrect", "no", "refut"]):
            refuted_count += 1
        # Match mixed/partial
        elif any(x in assessment for x in ["mixed", "partial", "mostly"]):
            mixed_count += 1

    total = supported_count + refuted_count + mixed_count
    if total == 0:
        return "unverified", 0.0

    # Calculate confidence (0-1 based on assessment clarity)
    if supported_count > 0 and refuted_count == 0 and mixed_count == 0:
        return "supported", min(1.0, supported_count / max(1, len(sources)))
    elif refuted_count > 0 and supported_count == 0 and mixed_count == 0:
        return "refuted", min(1.0, refuted_count / max(1, len(sources)))
    elif mixed_count > 0 or (supported_count > 0 and refuted_count > 0):
        return "mixed", min(1.0, (supported_count + refuted_count) / max(1, len(sources)))
    else:
        return "unverified", 0.5


async def research_fact_check(
    claim: str,
    max_sources: int = 10,
) -> dict[str, Any]:
    """Verify a claim across multiple fact-checking sources.

    Searches Google Fact Check API, Wikipedia, Semantic Scholar, and
    aggregates results from Snopes, PolitiFact, and FactCheck.org.

    Args:
        claim: the claim to fact-check (e.g., "The Earth is flat")
        max_sources: maximum number of source results to return (1-50)

    Returns:
        Dict with keys:
        - claim: original claim
        - verdict: one of supported, refuted, mixed, unverified
        - confidence: 0-1 confidence in the verdict
        - sources: list of {source, url, assessment, snippet}
        - total_sources_checked: count of unique sources consulted
    """
    max_sources = max(1, min(max_sources, 50))

    logger.info("fact_check claim=%s", claim[:50])

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Run all searches in parallel
            google_task = _search_google_fact_check(client, claim)
            snopes_task = _search_snopes_politifact_factcheck(client, claim)
            wiki_task = _search_wikipedia_for_claim(client, claim)
            scholar_task = _search_semantic_scholar_for_claim(client, claim)

            google_sources, snopes_sources, wiki_sources, scholar_sources = (
                await asyncio.gather(
                    google_task, snopes_task, wiki_task, scholar_task
                )
            )

            # Combine all sources and deduplicate by URL
            all_sources = (
                google_sources + snopes_sources + wiki_sources + scholar_sources
            )

            # Deduplicate by URL (keep first occurrence)
            seen_urls = set()
            dedup_sources: list[dict[str, Any]] = []
            for source in all_sources:
                url = source.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    dedup_sources.append(source)

            # Limit to max_sources
            final_sources = dedup_sources[:max_sources]

            # Aggregate assessments
            verdict, confidence = _aggregate_assessments(final_sources)

            return {
                "claim": claim,
                "verdict": verdict,
                "confidence": round(confidence, 2),
                "sources": final_sources,
                "total_sources_checked": len(final_sources),
            }

    return await _run()
