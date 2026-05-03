"""Tests for Redis store abstraction layer.

Tests both Redis backend and in-memory fallback modes.
"""

from __future__ import annotations

import pytest

from loom.redis_store import RedisStore, close_redis_store, get_redis_store


@pytest.fixture
async def redis_store_local() -> RedisStore:
    """Create a Redis store in local (in-memory) mode."""
    store = RedisStore(redis_url="")  # Empty URL forces local mode
    yield store
    await store.close()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_rate_limit_check(redis_store_local: RedisStore) -> None:
    """Test rate limiting with sliding window."""
    user_id = "test_user_1"
    category = "search"
    limit = 3

    # First 3 calls should pass
    assert await redis_store_local.rate_limit_check(user_id, category, limit) is True
    assert await redis_store_local.rate_limit_check(user_id, category, limit) is True
    assert await redis_store_local.rate_limit_check(user_id, category, limit) is True

    # Fourth call should fail
    assert await redis_store_local.rate_limit_check(user_id, category, limit) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_cache_operations(redis_store_local: RedisStore) -> None:
    """Test cache get/set/delete operations."""
    key = "test:cache:key"
    value = {"result": "success", "data": [1, 2, 3]}

    # Cache miss
    assert await redis_store_local.cache_get(key) is None

    # Cache set
    await redis_store_local.cache_set(key, value, ttl_seconds=3600)

    # Cache hit
    cached = await redis_store_local.cache_get(key)
    assert cached == value

    # Cache delete
    await redis_store_local.cache_delete(key)
    assert await redis_store_local.cache_get(key) is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_session_operations(redis_store_local: RedisStore) -> None:
    """Test session get/set/delete operations."""
    name = "test_session_1"
    data = {"user_id": "123", "token": "abc", "permissions": ["read", "write"]}

    # Session miss
    assert await redis_store_local.session_get(name) is None

    # Session set
    await redis_store_local.session_set(name, data, ttl_seconds=86400)

    # Session hit
    session = await redis_store_local.session_get(name)
    assert session == data

    # Session delete
    await redis_store_local.session_delete(name)
    assert await redis_store_local.session_get(name) is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_cost_tracking(redis_store_local: RedisStore) -> None:
    """Test cost tracking operations."""
    customer_id = "customer_123"

    # Initial cost should be 0
    assert await redis_store_local.cost_get(customer_id) == 0.0

    # Track cost
    await redis_store_local.cost_track(customer_id, 10.50)
    assert await redis_store_local.cost_get(customer_id) == 10.50

    # Track more cost (accumulate)
    await redis_store_local.cost_track(customer_id, 5.25)
    assert await redis_store_local.cost_get(customer_id) == 15.75

    # Reset cost
    await redis_store_local.cost_reset(customer_id)
    assert await redis_store_local.cost_get(customer_id) == 0.0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_locking(redis_store_local: RedisStore) -> None:
    """Test distributed locking."""
    lock_name = "test_lock"

    # Acquire lock
    assert await redis_store_local.lock_acquire(lock_name) is True

    # Second attempt should fail
    assert await redis_store_local.lock_acquire(lock_name) is False

    # Release lock
    await redis_store_local.lock_release(lock_name)

    # Now should be able to acquire again
    assert await redis_store_local.lock_acquire(lock_name) is True

    await redis_store_local.lock_release(lock_name)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_health_check(redis_store_local: RedisStore) -> None:
    """Test health check functionality."""
    health = await redis_store_local.health_check()

    assert "redis_available" in health
    assert "connected" in health
    assert "redis_url" in health


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_cache_clear_prefix(redis_store_local: RedisStore) -> None:
    """Test cache clearing by prefix."""
    # Set multiple cache entries
    await redis_store_local.cache_set("cache:search:1", {"data": 1})
    await redis_store_local.cache_set("cache:search:2", {"data": 2})
    await redis_store_local.cache_set("cache:fetch:1", {"data": 3})

    # Verify they exist
    assert await redis_store_local.cache_get("cache:search:1") is not None
    assert await redis_store_local.cache_get("cache:search:2") is not None
    assert await redis_store_local.cache_get("cache:fetch:1") is not None

    # Clear by prefix
    count = await redis_store_local.cache_clear_prefix("cache:search:")
    assert count == 2

    # Verify cleared
    assert await redis_store_local.cache_get("cache:search:1") is None
    assert await redis_store_local.cache_get("cache:search:2") is None

    # Others should remain
    assert await redis_store_local.cache_get("cache:fetch:1") is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_singleton() -> None:
    """Test singleton pattern for global store."""
    store1 = await get_redis_store()
    store2 = await get_redis_store()

    # Should be the same instance
    assert store1 is store2

    await close_redis_store()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_rate_limit_per_user(redis_store_local: RedisStore) -> None:
    """Test per-user rate limiting isolation."""
    category = "deep"
    limit = 2

    user1 = "user_1"
    user2 = "user_2"

    # User 1: 2 calls allowed
    assert await redis_store_local.rate_limit_check(user1, category, limit) is True
    assert await redis_store_local.rate_limit_check(user1, category, limit) is True

    # User 2: should have independent limit
    assert await redis_store_local.rate_limit_check(user2, category, limit) is True
    assert await redis_store_local.rate_limit_check(user2, category, limit) is True

    # User 1: should be exhausted
    assert await redis_store_local.rate_limit_check(user1, category, limit) is False

    # User 2: should be exhausted too
    assert await redis_store_local.rate_limit_check(user2, category, limit) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_store_cache_ttl(redis_store_local: RedisStore) -> None:
    """Test cache TTL (local in-memory mode only).

    Note: This test uses short TTLs and time-based checks on local storage.
    With actual Redis, this would be handled by Redis' native TTL mechanism.
    """
    import asyncio

    key = "cache:ttl:test"
    value = {"test": "data"}

    # Set with 1 second TTL
    await redis_store_local.cache_set(key, value, ttl_seconds=1)

    # Should exist immediately
    assert await redis_store_local.cache_get(key) is not None

    # Wait for expiry
    await asyncio.sleep(1.1)

    # Should be expired
    assert await redis_store_local.cache_get(key) is None
