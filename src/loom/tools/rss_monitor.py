"""RSS/Atom feed monitoring and search tools."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urljoin

import httpx

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.rss_monitor")

_HTTP_TIMEOUT = 30.0

# Safe XML parsing with XXE protection
try:
    from defusedxml.ElementTree import fromstring as safe_fromstring
except ImportError:
    from xml.etree.ElementTree import fromstring as _unsafe_fromstring

    def safe_fromstring(text: str) -> Any:
        """Fallback safe XML parsing by stripping DOCTYPE declarations."""
        text = re.sub(r"<!DOCTYPE[^>]*>", "", text, flags=re.IGNORECASE)
        return _unsafe_fromstring(text)


def _parse_feed(xml_content: str, url: str) -> dict[str, Any]:
    """Parse RSS 2.0 or Atom feed XML and extract feed metadata + items.

    Args:
        xml_content: Raw XML content from feed URL
        url: Original feed URL (used to resolve relative links)

    Returns:
        Dict with ``feed`` (title, description, link, language) and ``items`` list.
    """
    try:
        root = safe_fromstring(xml_content)
    except ET.ParseError as e:
        logger.warning("xml_parse_failed url=%s error=%s", url, e)
        return {"feed": {}, "items": [], "format": "unknown", "error": str(e)}

    # Detect format: RSS vs Atom
    is_atom = root.tag.endswith("}feed") or root.tag == "feed"
    is_rss = root.tag == "rss" or root.find(".//channel") is not None
    fmt = "atom" if is_atom else ("rss" if is_rss else "unknown")

    # Define namespace handling
    namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
    }

    # Extract feed metadata
    feed_data: dict[str, Any] = {"title": "", "description": "", "link": "", "language": ""}

    if is_atom:
        # Atom format
        feed_title_elem = root.find("atom:title", namespaces)
        if feed_title_elem is None:
            feed_title_elem = root.find("title")
        feed_data["title"] = (feed_title_elem.text or "").strip()

        feed_desc_elem = root.find("atom:subtitle", namespaces)
        if feed_desc_elem is None:
            feed_desc_elem = root.find("subtitle")
        feed_data["description"] = (feed_desc_elem.text or "").strip()

        feed_link_elem = root.find("atom:link", namespaces)
        if feed_link_elem is not None:
            feed_data["link"] = feed_link_elem.get("href", "")
        else:
            link_elem = root.find("link")
            if link_elem is not None:
                feed_data["link"] = link_elem.text or ""

        # Language from xml:lang attribute
        lang = root.get("{http://www.w3.org/XML/1998/namespace}lang")
        if lang:
            feed_data["language"] = lang
    else:
        # RSS format
        channel = root.find(".//channel")
        if channel is not None:
            feed_data["title"] = (channel.findtext("title") or "").strip()
            feed_data["description"] = (channel.findtext("description") or "").strip()
            feed_data["link"] = (channel.findtext("link") or "").strip()
            lang = channel.findtext("language")
            if lang:
                feed_data["language"] = lang

    # Extract items
    items = []
    if is_atom:
        item_elements = root.findall("atom:entry", namespaces)
    else:
        item_elements = root.findall(".//item")

    for item_elem in item_elements:
        if is_atom:
            title = (item_elem.findtext("atom:title", namespaces) or "").strip()
            if not title:
                title = (item_elem.findtext("title") or "").strip()

            link_elem = item_elem.find("atom:link", namespaces)
            link = link_elem.get("href", "") if link_elem is not None else ""
            if not link:
                link = (item_elem.findtext("link") or "").strip()

            summary = (item_elem.findtext("atom:summary", namespaces) or "").strip()
            if not summary:
                summary = (item_elem.findtext("summary") or "").strip()

            published = (item_elem.findtext("atom:published", namespaces) or "").strip()
            if not published:
                published = (item_elem.findtext("published") or "").strip()

            author = (item_elem.findtext("atom:author/atom:name", namespaces) or "").strip()
            if not author:
                author = (item_elem.findtext("author") or "").strip() or None

            categories = []
            for cat_elem in item_elem.findall("atom:category", namespaces):
                cat_term = cat_elem.get("term")
                if cat_term:
                    categories.append(cat_term)
        else:
            # RSS
            title = (item_elem.findtext("title") or "").strip()
            link = (item_elem.findtext("link") or "").strip()

            # Try content:encoded first, then description
            content_elem = item_elem.find("content:encoded", namespaces)
            summary = (content_elem.text or "").strip() if content_elem is not None else ""
            if not summary:
                summary = (item_elem.findtext("description") or "").strip()

            published = (item_elem.findtext("pubDate") or "").strip()
            author = (item_elem.findtext("author") or "").strip() or None

            categories = []
            for cat_elem in item_elem.findall("category"):
                cat_text = (cat_elem.text or "").strip()
                if cat_text:
                    categories.append(cat_text)

        # Clean HTML from summary
        summary = _strip_html(summary)
        if len(summary) > 500:
            summary = summary[:500] + "…"

        # Resolve relative links
        if link and not link.startswith(("http://", "https://", "ftp://")):
            link = urljoin(url, link)

        items.append(
            {
                "title": title,
                "link": link,
                "summary": summary,
                "published": published,
                "author": author,
                "categories": categories,
            }
        )

    return {
        "feed": feed_data,
        "items": items,
        "item_count": len(items),
        "format": fmt,
    }


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    # Remove script and style tags
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Clean up whitespace
    text = " ".join(text.split())
    return text


def research_rss_fetch(
    url: str,
    max_items: int = 20,
) -> dict[str, Any]:
    """Fetch and parse an RSS/Atom feed.

    Args:
        url: Feed URL (RSS 2.0 or Atom format)
        max_items: Maximum number of items to return

    Returns:
        Dict with ``feed`` (metadata), ``items`` (list), ``item_count``, ``format``.
    """
    try:
        url = validate_url(url)
    except ValueError as e:
        logger.warning("invalid_feed_url url=%s error=%s", url, e)
        return {"feed": {}, "items": [], "item_count": 0, "format": "unknown", "error": str(e)}

    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            resp = client.get(url)
            resp.raise_for_status()
            xml_content = resp.text
    except Exception as e:
        logger.warning("feed_fetch_failed url=%s error=%s", url, e)
        return {"feed": {}, "items": [], "item_count": 0, "format": "unknown", "error": str(e)}

    result = _parse_feed(xml_content, url)

    # Limit items
    if len(result["items"]) > max_items:
        result["items"] = result["items"][:max_items]
        result["item_count"] = max_items

    logger.info("feed_fetched url=%s item_count=%d format=%s", url, result.get("item_count", 0), result["format"])

    return result


def research_rss_search(
    urls: list[str],
    query: str,
    max_results: int = 20,
) -> dict[str, Any]:
    """Search across multiple RSS feeds for items matching a query.

    Fetches each feed and filters items where the query appears in the title
    or summary (case-insensitive).

    Args:
        urls: List of RSS/Atom feed URLs to search
        query: Search query (case-insensitive substring match)
        max_results: Maximum results to return

    Returns:
        Dict with ``query``, ``feeds_searched``, ``results`` (list), ``total_matches``.
    """
    if not query or len(query.strip()) < 1:
        return {"query": query, "feeds_searched": 0, "results": [], "total_matches": 0, "error": "query too short"}

    if not urls:
        return {"query": query, "feeds_searched": 0, "results": [], "total_matches": 0, "error": "no urls provided"}

    query_lower = query.lower()
    all_results: list[dict[str, Any]] = []
    feeds_searched = 0

    for url in urls:
        try:
            feed_result = research_rss_fetch(url, max_items=50)
            if feed_result.get("error"):
                logger.warning("skipping_feed url=%s error=%s", url, feed_result["error"])
                continue

            feeds_searched += 1
            feed_title = feed_result.get("feed", {}).get("title", "")

            for item in feed_result.get("items", []):
                title = item.get("title", "").lower()
                summary = item.get("summary", "").lower()

                if query_lower in title or query_lower in summary:
                    # Simple relevance: count query term occurrences
                    title_matches = title.count(query_lower)
                    summary_matches = summary.count(query_lower)
                    relevance = (title_matches * 2 + summary_matches) / max(
                        len(query_lower.split()),
                        1,
                    )

                    all_results.append(
                        {
                            "title": item["title"],
                            "link": item["link"],
                            "summary": item["summary"],
                            "published": item["published"],
                            "feed_title": feed_title,
                            "relevance": round(relevance, 2),
                        }
                    )
        except Exception as e:
            logger.warning("feed_search_error url=%s query=%s error=%s", url, query, e)
            continue

    # Sort by relevance (highest first) and limit results
    all_results.sort(key=lambda x: x["relevance"], reverse=True)
    results = all_results[:max_results]

    logger.info(
        "rss_search completed query=%s feeds=%d matches=%d results=%d",
        query,
        feeds_searched,
        len(all_results),
        len(results),
    )

    return {
        "query": query,
        "feeds_searched": feeds_searched,
        "results": results,
        "total_matches": len(all_results),
    }
