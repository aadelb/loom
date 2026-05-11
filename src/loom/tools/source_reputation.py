"""Source reputation scoring for search result filtering."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.source_reputation")

BLOCKLIST = frozenset({
    "spam-site.com",
    "malware-domain.xyz",
    "phishing-example.tk",
    "clickbait-farm.buzz",
    "seo-spam.info",
})

HIGH_QUALITY = frozenset({
    "arxiv.org",
    "github.com",
    "wikipedia.org",
    "nature.com",
    "sciencedirect.com",
    "ieee.org",
    "acm.org",
    "scholar.google.com",
    "ncbi.nlm.nih.gov",
    "nist.gov",
    "owasp.org",
    "mit.edu",
    "stanford.edu",
    "microsoft.com",
    "google.com",
    "anthropic.com",
    "openai.com",
    "huggingface.co",
    "stackoverflow.com",
})

TLD_SCORES = {
    ".edu": 85,
    ".gov": 90,
    ".org": 70,
    ".com": 50,
    ".net": 45,
    ".io": 55,
    ".xyz": 20,
    ".tk": 10,
    ".buzz": 15,
}


def score_source(url: str) -> int:
    """Score a URL's source reputation (0-100).

    Args:
        url: The URL to score

    Returns:
        Integer score from 0 (blocked/spam) to 100 (high-quality)
    """
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # Remove www prefix properly
        if netloc.startswith("www."):
            netloc = netloc[4:]
        domain = netloc
    except Exception:
        logger.warning("failed to parse url=%s", url)
        return 30

    # Check blocklist
    if not domain:  # empty domain from invalid URL
        return 30
    if domain in BLOCKLIST:
        return 0

    # Check high-quality domains
    if domain in HIGH_QUALITY or any(
        domain.endswith(f".{hq}") for hq in HIGH_QUALITY
    ):
        return 95

    # Score by TLD
    tld = "." + domain.rsplit(".", 1)[-1] if "." in domain else ""
    return TLD_SCORES.get(tld, 50)


def filter_by_reputation(
    results: list[dict[str, Any]], min_score: int = 20
) -> list[dict[str, Any]]:
    """Filter search results by source reputation score.

    Args:
        results: List of search result dicts (must contain 'url' or 'link' key)
        min_score: Minimum reputation score to include (0-100)

    Returns:
        Filtered list with reputation_score added to each result
    """
    filtered = []
    for result in results:
        url = result.get("url", result.get("link", ""))
        score = score_source(url)
        result["reputation_score"] = score
        if score >= min_score:
            filtered.append(result)
    return filtered


async def research_source_reputation(url: str) -> dict[str, Any]:
    """Score a URL's source reputation.

    Args:
        url: The URL to score

    Returns:
        Dict with url, domain, reputation_score, blocked, high_quality flags
    """
    validate_url(url)
    score = score_source(url)
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    domain = netloc
    return {
        "url": url,
        "domain": domain,
        "reputation_score": score,
        "blocked": domain in BLOCKLIST,
        "high_quality": domain in HIGH_QUALITY or score >= 80,
    }
