"""research_dead_drop_scanner — Probe ephemeral .onion sites with shingling-based detection.

Scans a list of .onion URLs suspected to be ephemeral, stores content hashes
and timestamps, and uses k-gram shingling to detect content reuse patterns
across sites.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from loom.config import get_config
from loom.tools.fetch import research_fetch
from loom.validators import validate_url

logger = logging.getLogger("loom.tools.dead_drop_scanner")


def _shingle_text(text: str, k: int = 5) -> set[str]:
    """Generate k-gram shingles from text.

    Args:
        text: input text to shingle
        k: shingle size (5-char substrings by default)

    Returns:
        Set of k-gram shingles as strings.
    """
    if not text or len(text) < k:
        return set()

    shingles = set()
    text = text.lower()
    for i in range(len(text) - k + 1):
        shingle = text[i : i + k]
        shingles.add(shingle)

    return shingles


def _jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """Calculate Jaccard similarity between two sets.

    Args:
        set1: first set of shingles
        set2: second set of shingles

    Returns:
        Jaccard similarity score (0.0 to 1.0).
    """
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


async def research_dead_drop_scanner(
    urls: list[str],
    interval_minutes: int = 5,
) -> dict[str, Any]:
    """Probe ephemeral .onion sites and capture content with reuse detection.

    Fetches each .onion URL via Tor proxy, stores content hash + timestamp,
    and uses shingling (k-gram hashing) to detect content reuse patterns
    across multiple sites.

    Args:
        urls: list of .onion URLs suspected to be ephemeral
        interval_minutes: minimum interval between scans (unused in single-pass, documented for API)

    Returns:
        Dict with:
            - scanned: number of URLs processed
            - alive: number of successfully fetched URLs
            - dead: number of failed fetches
            - content: list of content dicts with reuse analysis
            - reuse_pairs: list of {url1, url2, similarity_score} pairs above threshold
            - scan_timestamp: ISO datetime of scan
    """
    # Clamp parameters
    if not urls:
        return {
            "error": "urls list is empty",
            "scanned": 0,
            "alive": 0,
            "dead": 0,
            "content": [],
            "reuse_pairs": [],
        }

    urls = urls[:100]  # Cap at 100 URLs

    # Get Tor proxy from config
    config = get_config()
    tor_proxy = config.get("TOR_SOCKS5_PROXY", "socks5h://127.0.0.1:9050")
    if not config.get("TOR_ENABLED", False):
        return {
            "error": "Tor disabled in config (set TOR_ENABLED=true)",
            "scanned": len(urls),
            "alive": 0,
            "dead": 0,
            "content": [],
            "reuse_pairs": [],
        }

    # Scan all URLs
    scan_results = []
    content_by_url: dict[str, dict[str, Any]] = {}

    for url in urls:
        # Validate URL
        try:
            validate_url(url)
        except Exception as e:
            logger.warning("dead_drop_scanner_invalid_url url=%s error=%s", url, e)
            scan_results.append(
                {
                    "url": url,
                    "status": "invalid",
                    "error": str(e),
                    "content_hash": None,
                    "shingles": [],
                }
            )
            continue

        # Fetch URL
        try:
            logger.info("dead_drop_scanner_fetch url=%s", url)
            result = research_fetch(
                url,
                mode="dynamic",
                max_chars=100000,
                proxy=tor_proxy,
                timeout=30,
            )

            if result.get("error"):
                logger.warning("dead_drop_scanner_error url=%s error=%s", url, result["error"])
                scan_results.append(
                    {
                        "url": url,
                        "status": "dead",
                        "error": result["error"],
                        "content_hash": None,
                        "shingles": [],
                        "scanned_at": datetime.now(UTC).isoformat(),
                    }
                )
                continue

            # Extract content (prefer text, fallback to html)
            content = result.get("text", "") or result.get("html", "")

            if not content:
                logger.warning("dead_drop_scanner_empty url=%s", url)
                scan_results.append(
                    {
                        "url": url,
                        "status": "empty",
                        "error": "No content extracted",
                        "content_hash": None,
                        "shingles": [],
                        "scanned_at": datetime.now(UTC).isoformat(),
                    }
                )
                continue

            # Compute content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            # Generate shingles
            shingles = _shingle_text(content, k=5)

            # Store for reuse analysis
            content_by_url[url] = {
                "content": content,
                "hash": content_hash,
                "shingles": shingles,
            }

            scan_results.append(
                {
                    "url": url,
                    "status": "alive",
                    "content_hash": content_hash,
                    "content_size": len(content),
                    "shingle_count": len(shingles),
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            )

        except Exception as e:
            logger.error("dead_drop_scanner_exception url=%s error=%s", url, e)
            scan_results.append(
                {
                    "url": url,
                    "status": "error",
                    "error": str(e),
                    "content_hash": None,
                    "shingles": [],
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            )

    # Detect content reuse (shingling-based similarity)
    reuse_pairs = []
    similarity_threshold = 0.3  # 30% Jaccard similarity threshold

    urls_with_content = list(content_by_url.keys())
    for i in range(len(urls_with_content)):
        for j in range(i + 1, len(urls_with_content)):
            url1 = urls_with_content[i]
            url2 = urls_with_content[j]

            shingles1 = content_by_url[url1]["shingles"]
            shingles2 = content_by_url[url2]["shingles"]

            similarity = _jaccard_similarity(shingles1, shingles2)

            if similarity >= similarity_threshold:
                reuse_pairs.append(
                    {
                        "url1": url1,
                        "url2": url2,
                        "similarity_score": round(similarity, 3),
                        "potential_reuse": True,
                    }
                )

    # Count stats
    alive_count = sum(1 for r in scan_results if r["status"] == "alive")
    dead_count = len(scan_results) - alive_count

    return {
        "scanned": len(urls),
        "alive": alive_count,
        "dead": dead_count,
        "content": scan_results,
        "reuse_pairs": reuse_pairs,
        "scan_timestamp": datetime.now(UTC).isoformat(),
    }
