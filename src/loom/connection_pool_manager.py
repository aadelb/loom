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


async def get_client(
    base_url: str = "",
    *,
    timeout: float = 30.0,
    max_connections: int = 20,
    max_keepalive: int = 10,
    headers: dict[str, str] | None = None,
) -> httpx.AsyncClient:
    """Get or create a shared AsyncClient for a base URL.

    Clients are cached by base_url for connection reuse.
    """
    key = base_url or "__default__"

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
            follow_redirects=True,
        )
        _pools[key] = client
        logger.debug("pool_created base_url=%s", base_url)
        return client


async def close_client(base_url: str = "") -> None:
    """Close a specific client pool."""
    key = base_url or "__default__"
    async with _get_pool_lock():
        client = _pools.pop(key, None)
        if client and not client.is_closed:
            await client.aclose()


async def close_all() -> None:
    """Close all client pools. Call during shutdown."""
    async with _get_pool_lock():
        for key, client in list(_pools.items()):
            if not client.is_closed:
                await client.aclose()
        _pools.clear()
        logger.info("all_pools_closed count=%d", len(_pools))


def pool_status() -> dict[str, bool]:
    """Return status of all pools."""
    return {key: not client.is_closed for key, client in _pools.items()}
