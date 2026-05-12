"""Invisible web discovery — find unindexed content behind robots.txt, sitemaps, hidden paths, and JS endpoints."""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.invisible_web")

# Common sensitive paths to probe for exposure
_HIDDEN_PATHS = [
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.git/config",
    "/.git/HEAD",
    "/admin",
    "/debug",
    "/status",
    "/health",
    "/api/docs",
    "/swagger.json",
    "/openapi.json",
    "/graphql",
    "/.well-known/security.txt",
    "/.well-known/openid-configuration",
    "/wp-admin",
    "/wp-login.php",
    "/.htaccess",
    "/server-status",
    "/actuator",
    "/actuator/health",
    "/metrics",
    "/info",
]


def _parse_robots_disallowed(content: str) -> list[str]:
    """Extract Disallow paths from robots.txt."""
    paths = []
    for line in content.splitlines():
        line = line.strip()
        if line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path and path != "/":
                paths.append(path)
    return paths


def _extract_sitemaps_from_robots(content: str) -> list[str]:
    """Extract Sitemap URLs from robots.txt."""
    sitemaps = []
    for line in content.splitlines():
        if line.lower().startswith("sitemap:"):
            url = line.split(":", 1)[1].strip()
            if url:
                sitemaps.append(url)
    return sitemaps


def _parse_sitemap_urls(content: str) -> list[str]:
    """Extract <loc> URLs from sitemap XML."""
    urls = []
    for match in re.findall(r"<loc>\s*(https?://[^<]+)\s*</loc>", content):
        urls.append(match)
    return urls


def _extract_js_endpoints(html_content: str) -> list[str]:
    """Extract API route patterns from HTML script tags."""
    endpoints = set()

    # Find all script src attributes
    for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html_content):
        if src.startswith(("/", "http")):
            endpoints.add(src)

    # Find API route patterns in inline scripts
    # Look for /api/*, /v1/*, /graphql, etc.
    for match in re.findall(
        r'["\'](?:/(?:api|v\d+|graphql|rest)/[a-z0-9/_-]*)["\']', html_content
    ):
        endpoints.add(match.strip('"\''))

    return sorted(list(endpoints))


@handle_tool_errors("research_invisible_web")
def research_invisible_web(
    domain: str,
    check_robots: bool = True,
    check_sitemap: bool = True,
    check_hidden_paths: bool = True,
    check_js_endpoints: bool = True,
    max_paths: int = 50,
) -> dict[str, Any]:
    """Discover unindexed web content by exploring robots.txt, sitemaps, hidden paths, and JS endpoints.

    Uses HEAD requests for minimal footprint. Checks for robots.txt forbidden paths,
    sitemap URLs, exposed config files, and API endpoints in JavaScript.

    Args:
        domain: Target domain (e.g., "example.com")
        check_robots: Parse robots.txt for Disallow paths
        check_sitemap: Fetch and parse sitemap URLs
        check_hidden_paths: Probe common sensitive paths with HEAD requests
        check_js_endpoints: Extract API endpoints from homepage JavaScript
        max_paths: Maximum hidden paths to probe (1-100)

    Returns:
        Dict containing:
        - domain: The queried domain
        - robots_disallowed: List of Disallow paths from robots.txt
        - sitemap_urls: Count of unique URLs found in sitemaps
        - hidden_paths_found: List of accessible sensitive paths
        - js_endpoints: API endpoints found in JavaScript
        - exposed_configs: Accessible config files
        - risk_level: "critical", "high", "medium", or "low"
        - total_findings: Total number of findings
    """
    base_url = f"https://{domain}"
    max_paths = min(max(max_paths, 1), 100)
    robots_sitemaps = []

    result: dict[str, Any] = {
        "domain": domain,
        "robots_disallowed": [],
        "sitemap_urls": 0,
        "hidden_paths_found": [],
        "js_endpoints": [],
        "exposed_configs": [],
        "risk_level": "low",
        "total_findings": 0,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            # 1. Fetch and parse robots.txt
            if check_robots:
                try:
                    resp = client.head(f"{base_url}/robots.txt")
                    if resp.status_code == 200:
                        resp = client.get(f"{base_url}/robots.txt")
                        if resp.status_code == 200:
                            result["robots_disallowed"] = _parse_robots_disallowed(resp.text)
                            # Also extract sitemaps from robots.txt
                            robots_sitemaps = _extract_sitemaps_from_robots(resp.text)
                except (httpx.RequestError, httpx.TimeoutException):
                    pass

            # 2. Fetch sitemap URLs
            if check_sitemap:
                sitemap_urls = []
                sitemaps_to_check = [
                    f"{base_url}/sitemap.xml",
                    f"{base_url}/sitemap_index.xml",
                    f"{base_url}/sitemap-news.xml",
                ] + robots_sitemaps

                for sm_url in sitemaps_to_check:
                    try:
                        resp = client.get(sm_url)
                        if resp.status_code == 200:
                            sitemap_urls.extend(_parse_sitemap_urls(resp.text))
                    except (httpx.RequestError, httpx.TimeoutException):
                        pass

                result["sitemap_urls"] = len(set(sitemap_urls))

            # 3. Probe hidden paths with HEAD requests
            if check_hidden_paths:
                paths_to_check = _HIDDEN_PATHS[: int(max_paths)]
                for path in paths_to_check:
                    try:
                        resp = client.head(f"{base_url}{path}", follow_redirects=True)
                        if resp.status_code in (200, 301, 302, 403):
                            content_type = resp.headers.get("content-type", "unknown")
                            finding = {
                                "path": path,
                                "status_code": resp.status_code,
                                "content_type": content_type,
                            }
                            result["hidden_paths_found"].append(finding)

                            # Track exposed configs
                            if resp.status_code == 200 and any(
                                x in path for x in [".env", ".git", ".htaccess"]
                            ):
                                result["exposed_configs"].append(path)

                    except (httpx.RequestError, httpx.TimeoutException):
                        pass

            # 4. Extract JS endpoints from homepage
            if check_js_endpoints:
                try:
                    resp = client.get(f"{base_url}/", follow_redirects=True)
                    if resp.status_code == 200:
                        result["js_endpoints"] = _extract_js_endpoints(resp.text)
                except (httpx.RequestError, httpx.TimeoutException):
                    pass

            # 5. Calculate risk level
            risk_level = "low"
            if result["exposed_configs"]:
                risk_level = "critical"
            elif any(
                p["status_code"] in (200, 403)
                for p in result["hidden_paths_found"]
                if any(x in p["path"] for x in ["/admin", "/debug"])
            ):
                risk_level = "high"
            elif any(
                p["path"] in ["/api/docs", "/swagger.json", "/openapi.json", "/graphql"]
                for p in result["hidden_paths_found"]
                if p["status_code"] == 200
            ):
                risk_level = "medium"

            result["risk_level"] = risk_level
            result["total_findings"] = (
                len(result["robots_disallowed"])
                + result["sitemap_urls"]
                + len(result["hidden_paths_found"])
                + len(result["js_endpoints"])
            )

    except Exception as e:
        logger.error(f"invisible_web error for {domain}: {e}")
        result["error"] = str(e)

    return result
