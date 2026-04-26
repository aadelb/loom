"""TorCrawl provider - Crawl .onion pages through Tor SOCKS5 proxy.

Inspired by MikeMeliz/TorCrawl.py. Crawls .onion pages and builds a simple
page graph showing discovered links and crawl depth.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger("loom.providers.torcrawl")

# Module-level client for Tor SOCKS5 (created per config)
_torcrawl_client: httpx.Client | None = None


def _get_torcrawl_client(socks5_proxy: str) -> httpx.Client:
    """Get or create TorCrawl client with SOCKS5 proxy."""
    global _torcrawl_client
    # Recreate client if proxy changed (or if first time)
    if _torcrawl_client is None:
        try:
            _torcrawl_client = httpx.Client(
                proxy=socks5_proxy,
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    ),
                },
                verify=False,  # Onion certs often self-signed
            )
        except Exception as exc:
            logger.error("torcrawl_client_init_failed: %s", type(exc).__name__)
            raise
    return _torcrawl_client


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract .onion links from HTML."""
    links: list[str] = []
    try:
        # Find all href attributes
        pattern = r'href=(["\'])([^"\']*)\1'
        matches = re.findall(pattern, html)

        for _, url in matches:
            # Resolve relative URLs
            try:
                full_url = urljoin(base_url, url)
                # Only include .onion URLs
                if ".onion" in full_url:
                    links.append(full_url)
            except Exception:
                continue
    except Exception as exc:
        logger.warning("extract_links_failed: %s", type(exc).__name__)

    return links


def crawl_onion(
    url: str,
    depth: int = 1,
    max_pages: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Crawl an .onion page and extract links (respecting depth limit).

    Requires TOR_SOCKS5_PROXY from config or environment.

    Args:
        url: .onion URL to start crawling from
        depth: crawl depth (1 = page + direct links, 2 = recursive one level)
        max_pages: max total pages to crawl
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Dict with ``pages`` (crawled pages), ``links`` (extracted links),
        ``depth`` (achieved depth), and ``query`` (original URL).
    """
    from loom.config import CONFIG

    socks5_proxy = CONFIG.get("TOR_SOCKS5_PROXY") or kwargs.get("socks5_proxy", "")
    if not socks5_proxy:
        return {
            "pages": [],
            "links": [],
            "depth": 0,
            "query": url,
            "error": "TOR_SOCKS5_PROXY not configured",
        }

    if not url or ".onion" not in url:
        return {
            "pages": [],
            "links": [],
            "depth": 0,
            "query": url,
            "error": "invalid or non-.onion URL",
        }

    try:
        client = _get_torcrawl_client(socks5_proxy)

        pages: list[dict[str, Any]] = []
        all_links: list[str] = []
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(url, 0)]  # (url, current_depth)

        while queue and len(pages) < max_pages:
            current_url, current_depth = queue.pop(0)

            # Skip if already visited or depth exceeded
            if current_url in visited or current_depth > depth:
                continue

            visited.add(current_url)

            try:
                resp = client.get(current_url, follow_redirects=True)
                resp.raise_for_status()

                # Extract page title
                title_match = re.search(r"<title>([^<]+)</title>", resp.text)
                title = title_match.group(1) if title_match else ""

                # Extract page info
                pages.append({
                    "url": current_url,
                    "status": resp.status_code,
                    "title": title,
                    "depth": current_depth,
                })

                # Extract links for next iteration
                links = _extract_links(resp.text, current_url)
                all_links.extend(links)

                # Add unvisited links to queue
                if current_depth < depth:
                    for link in links:
                        if link not in visited and len(queue) < max_pages:
                            queue.append((link, current_depth + 1))

            except httpx.HTTPError as exc:
                pages.append({
                    "url": current_url,
                    "status": exc.response.status_code if hasattr(exc, "response") else None,
                    "error": type(exc).__name__,
                    "depth": current_depth,
                })
            except Exception as exc:
                logger.warning("crawl_page_failed url=%s: %s", current_url[:50], type(exc).__name__)
                continue

        # Deduplicate links
        deduped_links = list(set(all_links))

        return {
            "pages": pages,
            "links": deduped_links[:100],  # Cap output
            "depth": max((p.get("depth", 0) for p in pages), default=0),
            "query": url,
        }

    except Exception as exc:
        logger.error("torcrawl_failed url=%s: %s", url[:50], type(exc).__name__)
        return {
            "pages": [],
            "links": [],
            "depth": 0,
            "query": url,
            "error": "crawl failed",
        }
