"""Invisible web discovery — find unindexed content behind robots.txt, sitemaps, hidden paths."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.invisible_web")

_HIDDEN_PATHS = [
    "/.env", "/.env.local", "/.env.production",
    "/.git/config", "/.git/HEAD",
    "/.DS_Store",
    "/wp-config.php.bak", "/wp-config.php.old",
    "/admin", "/admin/", "/administrator/",
    "/debug", "/debug/", "/_debug",
    "/status", "/status.json", "/health", "/healthz",
    "/metrics", "/prometheus",
    "/graphql", "/api/graphql",
    "/swagger.json", "/openapi.json", "/api-docs",
    "/sitemap.xml", "/sitemap_index.xml",
    "/.well-known/security.txt",
    "/server-status", "/server-info",
    "/phpinfo.php", "/info.php",
    "/crossdomain.xml", "/clientaccesspolicy.xml",
    "/humans.txt", "/security.txt",
    "/package.json", "/composer.json",
    "/.htaccess", "/web.config",
]


async def _fetch_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> tuple[int, str]:
    try:
        resp = await client.get(url, timeout=timeout, follow_redirects=True)
        return resp.status_code, resp.text if resp.status_code == 200 else ""
    except Exception:
        return 0, ""


def _parse_robots(content: str) -> list[str]:
    paths: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path and path != "/":
                paths.append(path)
    return paths


def _parse_sitemap_urls(content: str) -> list[str]:
    urls: list[str] = []
    for match in re.findall(r"<loc>\s*(https?://[^<]+)\s*</loc>", content):
        urls.append(match)
    return urls


def _extract_sitemaps_from_robots(content: str) -> list[str]:
    sitemaps: list[str] = []
    for line in content.splitlines():
        if line.lower().startswith("sitemap:"):
            url = line.split(":", 1)[1].strip()
            if url:
                sitemaps.append(url)
    return sitemaps


def research_invisible_web(
    domain: str,
    check_robots: bool = True,
    check_sitemap: bool = True,
    check_hidden_paths: bool = True,
    max_hidden_paths: int = 40,
) -> dict[str, Any]:
    """Discover unindexed web content by exploring robots.txt forbidden paths,
    sitemap ghost pages, and common hidden/exposed configuration files.

    Args:
        domain: target domain (e.g. "example.com")
        check_robots: parse robots.txt for Disallow paths
        check_sitemap: check sitemap URLs for 404 ghost pages
        check_hidden_paths: probe common hidden paths
        max_hidden_paths: max number of hidden paths to check

    Returns:
        Dict with ``disallowed_paths``, ``sitemap_urls``, ``ghost_pages``
        (sitemap URLs returning 404), ``exposed_paths`` (hidden paths
        that are accessible), and ``sitemaps_found``.
    """
    base_url = f"https://{domain}"

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            result: dict[str, Any] = {
                "domain": domain,
                "base_url": base_url,
                "disallowed_paths": [],
                "sitemaps_found": [],
                "sitemap_urls_total": 0,
                "ghost_pages": [],
                "exposed_paths": [],
                "hidden_paths_checked": 0,
            }

            robots_text = ""
            if check_robots:
                status, robots_text = await _fetch_text(
                    client, f"{base_url}/robots.txt"
                )
                if status == 200:
                    result["disallowed_paths"] = _parse_robots(robots_text)
                    result["sitemaps_found"] = _extract_sitemaps_from_robots(
                        robots_text
                    )

            if check_sitemap:
                sitemap_urls_to_check = list(result["sitemaps_found"])
                if not sitemap_urls_to_check:
                    sitemap_urls_to_check = [
                        f"{base_url}/sitemap.xml",
                        f"{base_url}/sitemap_index.xml",
                    ]

                all_page_urls: list[str] = []
                for sm_url in sitemap_urls_to_check[:5]:
                    status, content = await _fetch_text(client, sm_url)
                    if status == 200:
                        all_page_urls.extend(_parse_sitemap_urls(content))

                result["sitemap_urls_total"] = len(all_page_urls)

                sample = all_page_urls[:30]
                if sample:
                    checks = await asyncio.gather(
                        *[_fetch_text(client, u) for u in sample],
                        return_exceptions=True,
                    )
                    for url, check in zip(sample, checks, strict=False):
                        if isinstance(check, tuple):
                            status_code, _ = check
                            if status_code in (404, 410, 0):
                                result["ghost_pages"].append(
                                    {"url": url, "status": status_code}
                                )

            if check_hidden_paths:
                paths_to_check = _HIDDEN_PATHS[:max_hidden_paths]
                result["hidden_paths_checked"] = len(paths_to_check)
                checks = await asyncio.gather(
                    *[
                        _fetch_text(client, f"{base_url}{path}")
                        for path in paths_to_check
                    ],
                    return_exceptions=True,
                )
                for path, check in zip(paths_to_check, checks, strict=False):
                    if isinstance(check, tuple):
                        status_code, content = check
                        if status_code == 200 and len(content) > 10:
                            result["exposed_paths"].append(
                                {
                                    "path": path,
                                    "url": f"{base_url}{path}",
                                    "status": status_code,
                                    "size": len(content),
                                    "preview": content[:200],
                                }
                            )

            return result

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
