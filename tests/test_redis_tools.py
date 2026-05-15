"""Tests for Redis management tools.

Tests research_redis_stats and research_redis_flush_cache tools.
"""

from __future__ import annotations

import pytest

from loom.redis_store import close_redis_store, get_redis_store
from loom.tools.infrastructure.redis_tools import research_redis_flush_cache, research_redis_stats


@pytest.mark.asyncio
@pytest.mark.unit
async def test_research_redis_stats() -> None:
    """Test redis stats tool."""
    result = await research_redis_stats()

    assert result["status"] in ["success", "error"]
    if result["status"] == "success":
        assert "data" in result
        data = result["data"]
        assert "redis_available" in data
        assert "connected" in data
        assert "redis_url" in data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_research_redis_flush_cache_success() -> None:
    """Test redis flush cache tool with valid prefix."""
    # First populate some cache
    store = await get_redis_store()
    await store.cache_set("cache:test:1", {"data": 1})
    await store.cache_set("cache:test:2", {"data": 2})

    # Clear with prefix
    result = await research_redis_flush_cache(prefix="cache:test:")

    assert result["status"] == "success"
    assert "keys_deleted" in result
    assert result["prefix"] == "cache:test:"

    await close_redis_store()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_research_redis_flush_cache_empty_prefix() -> None:
    """Test redis flush cache with empty prefix (should error)."""
    result = await research_redis_flush_cache(prefix="")

    assert result["status"] == "error"
    assert "error" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_research_redis_flush_cache_default_prefix() -> None:
    """Test redis flush cache with default prefix."""
    result = await research_redis_flush_cache()

    # Should use default prefix "cache:"
    assert result["status"] in ["success", "error"]
    if result["status"] == "success":
        assert result["prefix"] == "cache:"
