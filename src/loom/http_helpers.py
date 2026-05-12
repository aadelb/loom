"""Shared HTTP helper functions for Loom tool modules.

Consolidates _fetch_json, _get_json, _fetch_text, _get_text patterns
duplicated across 30+ tool files into one reusable module.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.http_helpers")


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 20.0,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    """Fetch JSON from URL with timeout and error handling.

    Args:
        client: httpx.AsyncClient instance for making the request
        url: Target URL to fetch
        timeout: Request timeout in seconds (default: 20.0)
        headers: Optional custom HTTP headers
        params: Optional query string parameters

    Returns:
        Parsed JSON object on success (dict, list, str, int, float, bool, or None).
        Returns None on failure (timeout, HTTP error, parse error).
    """
    try:
        resp = await client.get(
            url, timeout=timeout, headers=headers, params=params, follow_redirects=True
        )
        if resp.status_code == 200:
            try:
                return resp.json()
            except (ValueError, httpx.ResponseNotRead):
                logger.debug("fetch_json decode error: %s", url)
                return None
        else:
            logger.debug("fetch_json non_200 url=%s status=%d", url, resp.status_code)
            return None
    except httpx.TimeoutException:
        logger.debug("fetch_json timeout: %s", url)
    except Exception as exc:
        logger.debug("fetch_json failed: %s: %s", type(exc).__name__, exc)
    return None


async def fetch_text(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> str:
    """Fetch text content from URL with timeout and error handling.

    Args:
        client: httpx.AsyncClient instance for making the request
        url: Target URL to fetch
        timeout: Request timeout in seconds (default: 15.0)
        headers: Optional custom HTTP headers
        params: Optional query string parameters

    Returns:
        Response text on success.
        Returns empty string "" on failure (timeout, HTTP error, etc).
    """
    try:
        resp = await client.get(
            url, timeout=timeout, headers=headers, params=params, follow_redirects=True
        )
        if resp.status_code == 200:
            return resp.text
    except httpx.TimeoutException:
        logger.debug("fetch_text timeout: %s", url)
    except httpx.HTTPStatusError as e:
        logger.debug("fetch_text HTTP %d: %s", e.response.status_code, url)
    except Exception as exc:
        logger.debug("fetch_text failed: %s: %s", type(exc).__name__, exc)
    return ""


async def fetch_bytes(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> bytes:
    """Fetch raw bytes from URL with timeout and error handling.

    Args:
        client: httpx.AsyncClient instance for making the request
        url: Target URL to fetch
        timeout: Request timeout in seconds (default: 15.0)
        headers: Optional custom HTTP headers
        params: Optional query string parameters

    Returns:
        Response bytes on success.
        Returns empty bytes b"" on failure (timeout, HTTP error, etc).
    """
    try:
        resp = await client.get(
            url, timeout=timeout, headers=headers, params=params, follow_redirects=True
        )
        if resp.status_code == 200:
            return resp.content
    except httpx.TimeoutException:
        logger.debug("fetch_bytes timeout: %s", url)
    except httpx.HTTPStatusError as e:
        logger.debug("fetch_bytes HTTP %d: %s", e.response.status_code, url)
    except Exception as exc:
        logger.debug("fetch_bytes failed: %s: %s", type(exc).__name__, exc)
    return b""
