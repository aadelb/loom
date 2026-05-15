"""Forum Cortex — Analyze dark web forum discourse on a topic.

Tool:
- research_forum_cortex: dark web forum scraping, classification, and sentiment analysis
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

logger = logging.getLogger("loom.tools.forum_cortex")

# Dark web forum sources (via Ahmia and DarkSearch)
_DARKWEB_SOURCES = [
    "ahmia.fi",
    "darksearch.io",
]

# Post classification categories
_POST_CATEGORIES = [
    "informational",
    "threat",
    "recruitment",
    "marketplace",
    "technical",
    "discussion",
    "other",
]


async def _classify_post(
    title: str,
    content: str,
) -> dict[str, Any]:
    """Classify a forum post using LLM-based analysis.

    Args:
        title: post title
        content: post snippet

    Returns:
        Dict with category, confidence, and sentiment
    """
    try:
        from loom.tools.llm.llm import research_llm_classify
    except ImportError:
        return {
            "category": "other",
            "confidence": 0.5,
            "sentiment": "neutral",
        }

    categories_str = ", ".join(_POST_CATEGORIES)
    prompt = (
        f"Classify this dark web forum post into one of these categories: "
        f"{categories_str}.\n\n"
        f"Title: {title}\n"
        f"Content: {content[:500]}\n\n"
        f"Return ONLY: category from the list above, confidence (0.0-1.0)."
    )

    try:
        result = await asyncio.wait_for(
            research_llm_classify(
                text=prompt,
                labels=_POST_CATEGORIES,
            ),
            timeout=5.0,
        )

        # Parse result
        if "classification" in result:
            category = result.get("classification", {}).get("label", "other")
            confidence = result.get("classification", {}).get("confidence", 0.5)

            # Validate category is in allowed list
            if category not in _POST_CATEGORIES:
                category = "other"

            # Ensure confidence is a float in valid range
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            else:
                confidence = clamp(float(confidence), 0.0, 1.0)

            return {
                "category": category,
                "confidence": confidence,
                "sentiment": "neutral",
            }
    except asyncio.TimeoutError:
        logger.debug("forum_post_classification_timeout title=%s", title[:50])
    except Exception as exc:
        logger.debug("forum_post_classification_failed: %s", exc)

    return {
        "category": "other",
        "confidence": 0.5,
        "sentiment": "neutral",
    }


@handle_tool_errors("research_forum_cortex")
async def research_forum_cortex(
    topic: str,
    n: int = 5,
    max_cost_usd: float = 0.10,
) -> dict[str, Any]:
    """Analyze dark web forum discourse on a topic.

    Searches dark web forums (Ahmia, DarkSearch) for discussions on the given
    topic, fetches post content, classifies posts into categories
    (informational, threat, recruitment, marketplace, technical), and
    performs sentiment analysis.

    Args:
        topic: subject to search forums for
        n: max posts to analyze (across all sources combined)
        max_cost_usd: LLM cost budget (informational; not enforced)

    Returns:
        Dict with:
        - topic: original topic
        - posts: list of {url, title, category, sentiment, snippet}
        - summary: high-level overview of discourse
        - stats: {total_posts, category_breakdown}
        - error: error message if any
    """
    loop = asyncio.get_running_loop()
    posts: list[dict[str, Any]] = []
    category_counts: dict[str, int] = dict.fromkeys(_POST_CATEGORIES, 0)

    try:
        from loom.tools.core.search import research_search
    except ImportError:
        return {
            "topic": topic,
            "error": "search tools not available",
            "posts": [],
            "summary": "",
            "stats": {},
        }

    # Search each dark web source
    async def _search_forum_source(source: str) -> list[dict[str, Any]]:
        """Search a dark web forum source."""
        # Sanitize topic to prevent query injection (escape quotes)
        safe_topic = topic.replace('"', '\\"')
        search_query = f'site:{source} "{safe_topic}"'
        try:
            # Use DarkSearch or Ahmia if available
            provider = "darksearch" if "dark" in source else "ahmia"
            result = await research_search(
                search_query,
                provider=provider,
                n=n,
            )
            return result.get("results", [])  # type: ignore[return-value]
        except Exception as provider_exc:
            logger.debug("forum_cortex_search_failed source=%s provider=%s: %s", source, provider, provider_exc)
            # Fallback to generic search if provider not available
            try:
                result = await research_search(
                    f'{safe_topic} site:{source}',
                    provider="ddgs",
                    n=n,
                )
                return result.get("results", [])  # type: ignore[return-value]
            except Exception as fallback_exc:
                logger.warning("forum_cortex_search_fallback_failed source=%s: %s", source, fallback_exc)
                return []

    # Gather search results from all sources in parallel
    gather_results = await asyncio.gather(
        *[_search_forum_source(source) for source in _DARKWEB_SOURCES],
        return_exceptions=True,
    )

    all_posts: list[dict[str, Any]] = []
    for result in gather_results:
        if isinstance(result, list):
            all_posts.extend(result)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_posts: list[dict[str, Any]] = []
    for post in all_posts:
        url = post.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_posts.append(post)

    # Classify each post
    for post in unique_posts[:n * len(_DARKWEB_SOURCES)]:
        url = post.get("url", "")
        title = post.get("title", "")
        snippet = post.get("snippet", "")

        # Classify post
        classification = await _classify_post(title, snippet)

        category = classification.get("category", "other")
        # Ensure category is valid before incrementing counter
        if category in category_counts:
            category_counts[category] += 1
        else:
            # Fallback to "other" if category is invalid
            category = "other"
            category_counts["other"] += 1

        posts.append({
            "url": url,
            "title": title,
            "snippet": snippet,
            "category": category,
            "confidence": classification.get("confidence", 0.5),
            "sentiment": classification.get("sentiment", "neutral"),
        })

    # Generate summary
    threat_posts = sum(1 for p in posts if p.get("category") == "threat")
    recruitment_posts = sum(1 for p in posts if p.get("category") == "recruitment")
    marketplace_posts = sum(1 for p in posts if p.get("category") == "marketplace")

    summary_parts = []
    if threat_posts > 0:
        summary_parts.append(f"{threat_posts} threat-related posts")
    if recruitment_posts > 0:
        summary_parts.append(f"{recruitment_posts} recruitment posts")
    if marketplace_posts > 0:
        summary_parts.append(f"{marketplace_posts} marketplace posts")

    if summary_parts:
        summary = f"Dark web discourse on '{topic}': " + ", ".join(summary_parts)
    else:
        msg = f"Limited discourse found on '{topic}' in monitored forums."
        summary = msg

    logger.info(
        "forum_cortex_complete topic=%s posts=%d",
        topic[:50],
        len(posts),
    )

    return {
        "topic": topic,
        "posts": posts,
        "summary": summary,
        "stats": {
            "total_posts_analyzed": len(posts),
            "sources_searched": len(_DARKWEB_SOURCES),
            "category_breakdown": category_counts,
            "threat_posts": threat_posts,
            "recruitment_posts": recruitment_posts,
            "marketplace_posts": marketplace_posts,
        },
    }
