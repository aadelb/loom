"""Traffic capture tools — HAR export and cookie extraction."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from mcp.types import TextContent

logger = logging.getLogger("loom.tools.traffic_capture")


def _build_har_entry(request: httpx.Request, response: httpx.Response, elapsed_ms: int) -> dict[str, Any]:
    """Build HAR entry from httpx request/response."""
    body = response.content[:10240] if response.content else b""
    return {
        "request": {
            "method": request.method,
            "url": str(request.url),
            "headers": [{"name": k, "value": v} for k, v in request.headers.items()],
        },
        "response": {
            "status": response.status_code,
            "statusText": response.reason_phrase or "",
            "headers": [{"name": k, "value": v} for k, v in response.headers.items()],
            "content": {
                "size": len(body),
                "mimeType": response.headers.get("content-type", ""),
                "text": body.decode("utf-8", errors="replace") if body else "",
            },
        },
        "timings": {"total": elapsed_ms},
    }


async def research_capture_har(url: str, duration_seconds: int = 10, include_bodies: bool = True) -> dict[str, Any]:
    """Capture HTTP traffic as HAR format.

    Args:
        url: Target URL
        duration_seconds: Max capture time (1-60)
        include_bodies: Include response bodies (10KB truncate)

    Returns:
        HAR dict with entries, domains_contacted, total_bytes
    """
    if not 1 <= duration_seconds <= 60:
        return {"error": "duration_seconds must be 1-60", "url": url, "entries_count": 0}

    entries, domains, total_bytes = [], set(), 0
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=duration_seconds) as client:
            start = datetime.now(UTC)
            response = await client.get(url)
            elapsed_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
            entry = _build_har_entry(response.request, response, elapsed_ms)
            entries.append(entry)
            try:
                domain = httpx.URL(str(response.request.url)).host
                if domain:
                    domains.add(domain)
            except Exception:
                pass
            total_bytes += min(len(response.content) if response.content else 0, 10240)
    except Exception as e:
        logger.error("HAR capture error: %s", str(e))
        return {"error": str(e), "url": url, "entries_count": 0, "total_bytes": 0}

    return {
        "url": url,
        "duration_seconds": duration_seconds,
        "entries_count": len(entries),
        "har": {"log": {"version": "1.2", "creator": {"name": "loom", "version": "1.0"}, "entries": entries}},
        "total_bytes": total_bytes,
        "domains_contacted": sorted(list(domains)),
    }


async def research_extract_cookies(url: str, follow_redirects: bool = True) -> dict[str, Any]:
    """Extract cookies set by a URL with security assessment.

    Args:
        url: Target URL
        follow_redirects: Follow redirect chain

    Returns:
        Cookies list with categories and security flags
    """
    cookies_list, redirect_chain, security_issues = [], [url], 0
    try:
        async with httpx.AsyncClient(follow_redirects=follow_redirects, timeout=10) as client:
            response = await client.get(url)
            if hasattr(response, "history"):
                redirect_chain = [str(r.url) for r in response.history] + [str(response.url)]

            for cookie_name, cookie_value in client.cookies.items():
                cookie_obj = client.cookies.jar.get_cookie(str(response.url), cookie_name)
                attrs = {
                    "name": cookie_name,
                    "value": cookie_value[:50],
                    "domain": getattr(cookie_obj, "domain", ""),
                    "path": getattr(cookie_obj, "path", "/"),
                    "expires": getattr(cookie_obj, "expires", None),
                    "httponly": getattr(cookie_obj, "_rest", {}).get("HttpOnly", False),
                    "secure": getattr(cookie_obj, "secure", False),
                    "samesite": getattr(cookie_obj, "_rest", {}).get("SameSite", None),
                }
                name_lower = cookie_name.lower()
                if any(x in name_lower for x in ["session", "sid", "sessionid"]):
                    attrs["category"] = "session"
                elif any(x in name_lower for x in ["track", "utm", "ga", "analytics"]):
                    attrs["category"] = "tracking"
                elif any(x in name_lower for x in ["auth", "token", "jwt"]):
                    attrs["category"] = "auth"
                else:
                    attrs["category"] = "preferences"

                if not attrs["httponly"]:
                    security_issues += 1
                if not attrs["secure"] and attrs["domain"]:
                    security_issues += 1
                if not attrs["samesite"]:
                    security_issues += 1
                cookies_list.append(attrs)
    except Exception as e:
        logger.error("Cookie extraction error: %s", str(e))
        return {"error": str(e), "url": url, "cookies": []}

    assessment = "low" if security_issues == 0 else ("medium" if security_issues <= 2 else "high")
    return {
        "url": url,
        "cookies": cookies_list,
        "redirect_chain": redirect_chain,
        "security_assessment": assessment,
        "cookies_count": len(cookies_list),
    }
