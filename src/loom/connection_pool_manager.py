"""Unified HTTP connection pool management.

Provides shared httpx.AsyncClient instances per base URL,
with proper lifecycle management and connection reuse.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.connection_pool_manager")

_pools: dict[str, httpx.AsyncClient] = {}
_pool_lock: asyncio.Lock | None = None


def _get_pool_lock() -> asyncio.Lock:
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock


def _make_pool_key(
    base_url: str,
    proxy: str | None,
    follow_redirects: bool,
) -> str:
    """Create a unique pool key based on client configuration."""
    parts = [base_url or "__default__"]
    if proxy:
        parts.append(f"proxy={proxy}")
    if not follow_redirects:
        parts.append("no_redirect")
    return "|".join(parts)


async def get_client(
    base_url: str = "",
    *,
    timeout: float = 30.0,
    max_connections: int = 20,
    max_keepalive: int = 10,
    headers: dict[str, str] | None = None,
    proxy: str | None = None,
    follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """Get or create a shared AsyncClient for a base URL.

    Clients are cached by (base_url, proxy, follow_redirects) for connection reuse.

    Args:
        base_url: Base URL for the client (empty string for no base URL)
        timeout: Request timeout in seconds
        max_connections: Maximum number of simultaneous connections
        max_keepalive: Maximum number of keep-alive connections
        headers: Default headers to include in all requests
        proxy: SOCKS5 or HTTP proxy URL (e.g., "socks5h://127.0.0.1:9050")
        follow_redirects: Whether to follow HTTP redirects

    Returns:
        A shared httpx.AsyncClient instance
    """
    key = _make_pool_key(base_url, proxy, follow_redirects)

    async with _get_pool_lock():
        if key in _pools and not _pools[key].is_closed:
            return _pools[key]

        client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive,
            ),
            headers=headers or {},
            proxy=proxy,
            follow_redirects=follow_redirects,
        )
        _pools[key] = client
        logger.debug("pool_created base_url=%s proxy=%s", base_url, proxy)
        return client


async def close_client(
    base_url: str = "",
    *,
    proxy: str | None = None,
    follow_redirects: bool = True,
) -> None:
    """Close a specific client pool."""
    key = _make_pool_key(base_url, proxy, follow_redirects)
    async with _get_pool_lock():
        client = _pools.pop(key, None)
        if client and not client.is_closed:
            await client.aclose()
            logger.debug("pool_closed key=%s", key)


async def close_all() -> None:
    """Close all client pools. Call during shutdown."""
    async with _get_pool_lock():
        for key, client in list(_pools.items()):
            if not client.is_closed:
                await client.aclose()
        count = len(_pools)
        _pools.clear()
        logger.info("all_pools_closed count=%d", count)


def pool_status() -> dict[str, bool]:
    """Return status of all pools."""
    return {key: not client.is_closed for key, client in _pools.items()}
