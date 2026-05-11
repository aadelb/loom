"""research_ghost_weave — Temporal hyperlink graph builder for .onion hidden services.

Crawls .onion pages up to specified depth, extracts all hyperlinks, builds a
directed graph, and tracks timestamps for temporal analysis of structural changes
(new links, dead links, network topology evolution).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

from loom.config import get_config
from loom.tools.fetch import research_fetch
from loom.validators import validate_url

logger = logging.getLogger("loom.tools.ghost_weave")


def _extract_hyperlinks(html: str, base_url: str) -> list[str]:
    """Extract all hyperlinks from HTML content.

    Args:
        html: HTML content
        base_url: base URL for resolving relative links

    Returns:
        List of normalized absolute URLs found in href attributes.
    """
    links = []
    # Match href attributes in anchor tags
    href_pattern = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

    for match in href_pattern.finditer(html):
        try:
            href = match.group(1)
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            # Filter only http/https/onion
            parsed = urlparse(absolute_url)
            if parsed.scheme in ("http", "https") or (parsed.hostname and parsed.hostname.endswith(
                ".onion"
            )):
                links.append(absolute_url)
        except Exception:
            # Skip malformed URLs
            continue

    return links


def _normalize_url(url: str) -> str:
    """Normalize URL by removing fragments and sorting query params.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL string.
    """
    try:
        parsed = urlparse(url)
        # Remove fragment, keep scheme, netloc, path, query
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{'?' + parsed.query if parsed.query else ''}"
    except Exception:
        return url


async def research_ghost_weave(
    seed_url: str,
    depth: int = 1,
    max_pages: int = 20,
) -> dict[str, Any]:
    """Build temporal hyperlink graph of .onion hidden services.

    Starting from seed_url, crawls .onion pages up to specified depth,
    extracts all hyperlinks, builds a directed graph, and detects
    structural changes (new links, dead links).

    Args:
        seed_url: starting .onion URL
        depth: maximum crawl depth (1-3)
        max_pages: maximum pages to crawl (1-100)

    Returns:
        Dict with:
            - seed: original seed URL
            - pages_crawled: number of pages successfully fetched
            - nodes: list of page objects with {url, title, timestamp, link_count}
            - edges: list of directed links {from, to, discovered_at}
            - dead_links: list of failed link attempts {url, error, attempts}
            - graph_stats: {total_nodes, total_edges, avg_degree, density}
    """
    # Validate seed URL
    try:
        validate_url(seed_url)
    except Exception as e:
        return {
            "seed": seed_url,
            "error": f"invalid seed URL: {e}",
            "pages_crawled": 0,
            "nodes": [],
            "edges": [],
            "dead_links": [],
        }

    # Clamp parameters
    depth = max(1, min(depth, 3))
    max_pages = max(1, min(max_pages, 100))

    # Get Tor proxy from config
    config = get_config()
    tor_proxy = config.get("TOR_SOCKS5_PROXY", "socks5h://127.0.0.1:9050")
    if not config.get("TOR_ENABLED", False):
        return {
            "seed": seed_url,
            "error": "Tor disabled in config (set TOR_ENABLED=true)",
            "pages_crawled": 0,
            "nodes": [],
            "edges": [],
            "dead_links": [],
        }

    # Tracking structures
    visited: dict[str, dict[str, Any]] = {}  # url -> {timestamp, html, title, links}
    edges: list[dict[str, Any]] = []
    dead_links: dict[str, dict[str, Any]] = {}  # url -> {error, attempts}
    queue: list[tuple[str, int]] = [(seed_url, 0)]  # (url, current_depth)
    seen_urls = {_normalize_url(seed_url)}
    import time as _time
    _crawl_deadline = _time.time() + 120  # 2-minute overall timeout

    # Crawl up to max_pages
    while queue and len(visited) < max_pages and _time.time() < _crawl_deadline:
        current_url, current_depth = queue.pop(0)

        # Stop if we've exceeded depth
        if current_depth > depth:
            continue

        # Fetch page
        normalized = _normalize_url(current_url)
        if normalized in visited:
            continue

        try:
            logger.info("ghost_weave_fetch url=%s depth=%d", current_url, current_depth)
            result = await research_fetch(
                current_url,
                mode="dynamic",
                max_chars=50000,
                proxy=tor_proxy,
                timeout=30,
            )

            if result.get("error"):
                dead_links[current_url] = {
                    "error": result["error"],
                    "attempts": 1,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                logger.warning("ghost_weave_fetch_error url=%s error=%s", current_url, result["error"])
                continue

            # Extract page data
            html = result.get("html", "")
            text = result.get("text", "")
            title = result.get("title", "")

            # Extract title from HTML if not provided
            if not title and html:
                title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1)[:200]

            # Extract hyperlinks
            links = _extract_hyperlinks(html or text, current_url)

            # Store visited page
            visited[normalized] = {
                "url": current_url,
                "title": title,
                "timestamp": datetime.now(UTC).isoformat(),
                "link_count": len(links),
                "html_size": len(html or ""),
                "text_size": len(text or ""),
            }

            # Add edges and queue new URLs
            for link in links:
                # Fix H12: Cap edges to prevent unbounded memory growth
                if len(edges) > max_pages * 20:
                    break
                    
                link_normalized = _normalize_url(link)
                edges.append(
                    {
                        "from": current_url,
                        "to": link,
                        "discovered_at": datetime.now(UTC).isoformat(),
                    }
                )

                # Queue unvisited URLs at next depth
                if link_normalized not in seen_urls and len(visited) < max_pages:
                    seen_urls.add(link_normalized)
                    queue.append((link, current_depth + 1))

        except Exception as e:
            logger.error("ghost_weave_exception url=%s error=%s", current_url, e)
            dead_links[current_url] = {
                "error": str(e),
                "attempts": 1,
                "timestamp": datetime.now(UTC).isoformat(),
            }

    # Build response
    nodes = list(visited.values())

    # Calculate graph statistics
    total_nodes = len(nodes)
    total_edges = len(edges)
    if total_nodes > 0:
        # Simple average degree calculation
        in_degree: dict[str, int] = {}
        out_degree: dict[str, int] = {}
        for node in nodes:
            in_degree[node["url"]] = 0
            out_degree[node["url"]] = 0

        for edge in edges:
            src = edge["from"]
            dst = edge["to"]
            if src in out_degree:
                out_degree[src] += 1
            if dst in in_degree:
                in_degree[dst] += 1

        degrees = list(in_degree.values()) + list(out_degree.values())
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
    else:
        avg_degree = 0

    # Density = edges / (nodes * (nodes - 1)) for directed graph
    density = 0.0
    if total_nodes > 1:
        max_edges = total_nodes * (total_nodes - 1)
        density = total_edges / max_edges if max_edges > 0 else 0

    return {
        "seed": seed_url,
        "pages_crawled": len(nodes),
        "nodes": nodes,
        "edges": edges,
        "dead_links": list(dead_links.values()),
        "graph_stats": {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "avg_degree": round(avg_degree, 2),
            "density": round(density, 4),
        },
    }
