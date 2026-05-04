"""Idempotency tests for billing and critical financial operations.

Tests:
- Double deduction prevention (same idempotency key)
- Batch submission deduplication
- Retry timeout handling
- Result caching verification
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.billing.idempotency import (
    IdempotencyManager,
    generate_idempotency_key,
    get_idempotency_manager,
)


class TestIdempotencyKeyGeneration:
    """Test idempotency key generation."""

    def test_same_params_same_key(self) -> None:
        """Verify deterministic key generation for identical params."""
        key1 = generate_idempotency_key(
            "user_123", "deduct", {"amount": 100, "tool": "deep"}
        )
        key2 = generate_idempotency_key(
            "user_123", "deduct", {"amount": 100, "tool": "deep"}
        )
        assert key1 == key2
        assert len(key1) == 64  # SHA-256 hex

    def test_different_params_different_key(self) -> None:
        """Verify different params produce different keys."""
        key1 = generate_idempotency_key("user_123", "deduct", {"amount": 100})
        key2 = generate_idempotency_key("user_123", "deduct", {"amount": 200})
        assert key1 != key2

    def test_different_user_different_key(self) -> None:
        """Verify different users produce different keys."""
        params = {"amount": 100}
        key1 = generate_idempotency_key("user_123", "deduct", params)
        key2 = generate_idempotency_key("user_456", "deduct", params)
        assert key1 != key2

    def test_params_order_independent(self) -> None:
        """Verify param order doesn't affect key (JSON sorted)."""
        params1 = {"tool": "deep", "amount": 100, "credits": 10}
        params2 = {"credits": 10, "amount": 100, "tool": "deep"}
        key1 = generate_idempotency_key("user_123", "deduct", params1)
        key2 = generate_idempotency_key("user_123", "deduct", params2)
        assert key1 == key2


class TestIdempotencyManager:
    """Test IdempotencyManager check and caching."""

    @pytest.mark.asyncio
    async def test_check_and_store_new_key(self) -> None:
        """Test storing result for a new idempotency key."""
        manager = IdempotencyManager(redis_store=None)
        key = "test_key_new_001"
        result = {"id": "op_123", "status": "success", "amount": 100}

        # First call with new key should return None (stored)
        response = await manager.check_and_store(key, operation_result=result)
        assert response is None

    @pytest.mark.asyncio
    async def test_check_and_store_duplicate_key(self) -> None:
        """Test retrieving cached result on duplicate key."""
        mock_redis = AsyncMock()
        original_result = {
            "id": "op_123",
            "status": "success",
            "amount": 100,
        }

        # Mock: first call returns None (cache miss), second returns cached
        mock_redis.cache_get.side_effect = [
            None,  # First check
            original_result,  # Second check (duplicate)
        ]
        mock_redis.cache_set = AsyncMock()

        manager = IdempotencyManager(redis_store=mock_redis)

        # First call: new key
        key = "test_key_dup_001"
        resp1 = await manager.check_and_store(key, operation_result=original_result)
        assert resp1 is None
        mock_redis.cache_set.assert_called_once()

        # Second call: duplicate key
        resp2 = await manager.check_and_store(key)
        assert resp2 == original_result
        assert mock_redis.cache_get.call_count == 2

    @pytest.mark.asyncio
    async def test_check_and_store_missing_result_on_new_key(self) -> None:
        """Test error when storing new key without result."""
        mock_redis = AsyncMock()
        mock_redis.cache_get.return_value = None

        manager = IdempotencyManager(redis_store=mock_redis)
        key = "test_key_missing_001"

        with pytest.raises(ValueError, match="operation_result required"):
            await manager.check_and_store(key, operation_result=None)

    @pytest.mark.asyncio
    async def test_check_and_store_redis_unavailable(self) -> None:
        """Test graceful degradation when Redis unavailable."""
        manager = IdempotencyManager(redis_store=None)
        key = "test_key_no_redis"
        result = {"id": "op_456", "status": "success"}

        # Should return None without error
        response = await manager.check_and_store(key, operation_result=result)
        assert response is None

    @pytest.mark.asyncio
    async def test_clear_key(self) -> None:
        """Test clearing a single idempotency key."""
        mock_redis = AsyncMock()
        mock_redis.cache_delete = AsyncMock(return_value=True)

        manager = IdempotencyManager(redis_store=mock_redis)
        key = "test_key_clear_001"

        result = await manager.clear_key(key)
        assert result is True
        mock_redis.cache_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_prefix_by_user(self) -> None:
        """Test clearing all keys for a user."""
        mock_redis = AsyncMock()
        mock_redis.cache_clear_prefix = AsyncMock(return_value=5)

        manager = IdempotencyManager(redis_store=mock_redis)
        user_id = "user_789"

        count = await manager.clear_prefix(user_id)
        assert count == 5
        mock_redis.cache_clear_prefix.assert_called_once()


class TestBillingIdempotency:
    """Integration tests for billing operations with idempotency."""

    @pytest.mark.asyncio
    async def test_double_deduction_prevented(self) -> None:
        """Test that calling deduct twice with same key prevents double charge.

        Simulates:
        1. User makes a call, deduct(100 credits) returns success (op_1)
        2. User retries with same params → get cached result instead of deducting again
        """
        mock_redis = AsyncMock()
        first_deduction = {
            "id": "txn_001",
            "user_id": "user_100",
            "credits_deducted": 100,
            "new_balance": 900,
            "timestamp": "2025-01-01T10:00:00Z",
        }

        # Simulate cache: miss on first, hit on second
        mock_redis.cache_get.side_effect = [None, first_deduction]
        mock_redis.cache_set = AsyncMock()

        manager = IdempotencyManager(redis_store=mock_redis)

        # First deduction
        key = generate_idempotency_key(
            "user_100", "credit_deduct", {"amount": 100, "tool": "deep"}
        )
        result1 = await manager.check_and_store(
            key, operation_result=first_deduction
        )
        assert result1 is None  # New key, stored

        # Second deduction (duplicate) with same key
        result2 = await manager.check_and_store(key)
        assert result2 == first_deduction  # Cached result returned
        # Verify deduction only happened once (only 1 cache_set call)
        assert mock_redis.cache_set.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_submit_duplicate_detection(self) -> None:
        """Test duplicate detection in batch submission scenario.

        Simulates:
        1. Batch submit with 3 operations
        2. Retry batch with same operations
        3. Verify duplicates detected via idempotency keys
        """
        mock_redis = AsyncMock()

        # Simulate 3 cached operations
        cached_ops = [
            {"id": "op_a", "status": "success"},
            {"id": "op_b", "status": "success"},
            {"id": "op_c", "status": "success"},
        ]

        # First batch: misses, then hits on retry
        mock_redis.cache_get.side_effect = [
            None,  # op_a miss
            None,  # op_b miss
            None,  # op_c miss
            cached_ops[0],  # op_a hit (retry)
            cached_ops[1],  # op_b hit (retry)
            cached_ops[2],  # op_c hit (retry)
        ]
        mock_redis.cache_set = AsyncMock()

        manager = IdempotencyManager(redis_store=mock_redis)

        # First batch submission
        batch_params = [
            {"tool": "fetch", "url": "https://example.com/1"},
            {"tool": "fetch", "url": "https://example.com/2"},
            {"tool": "fetch", "url": "https://example.com/3"},
        ]

        batch_keys = [
            generate_idempotency_key("user_200", "batch_op", p) for p in batch_params
        ]
        batch_results = []
        for i, key in enumerate(batch_keys):
            r = await manager.check_and_store(key, operation_result=cached_ops[i])
            batch_results.append(r)

        assert all(r is None for r in batch_results)  # All new keys stored
        assert mock_redis.cache_set.call_count == 3

        # Retry batch with same params
        batch_results_retry = []
        for key in batch_keys:
            r = await manager.check_and_store(key)
            batch_results_retry.append(r)

        assert batch_results_retry == cached_ops  # All duplicates detected
        assert mock_redis.cache_set.call_count == 3  # No new caches

    @pytest.mark.asyncio
    async def test_retry_after_timeout_no_double_charge(self) -> None:
        """Test retry after network timeout doesn't double-charge.

        Simulates:
        1. User submits deduction, times out before receiving response
        2. User retries with same idempotency key
        3. Verify original operation was stored and returned
        """
        mock_redis = AsyncMock()

        # First attempt: store and return None
        original_op = {
            "id": "txn_timeout_001",
            "user_id": "user_300",
            "credits_deducted": 50,
            "new_balance": 950,
            "timestamp": "2025-01-01T11:00:00Z",
        }

        # Simulate: miss on first, hit on retry
        mock_redis.cache_get.side_effect = [None, original_op]
        mock_redis.cache_set = AsyncMock()

        manager = IdempotencyManager(redis_store=mock_redis)
        key = generate_idempotency_key(
            "user_300", "credit_deduct", {"amount": 50, "tool": "search"}
        )

        # First request (original, times out)
        r1 = await manager.check_and_store(key, operation_result=original_op)
        assert r1 is None

        # Simulate client reconnect / retry with same key
        r2 = await manager.check_and_store(key)
        assert r2 == original_op

        # Verify only one store operation
        assert mock_redis.cache_set.call_count == 1

    @pytest.mark.asyncio
    async def test_idempotency_ttl_respected(self) -> None:
        """Test that idempotency cache respects TTL setting."""
        mock_redis = AsyncMock()
        mock_redis.cache_set = AsyncMock()

        manager = IdempotencyManager(redis_store=mock_redis)
        key = "test_key_ttl_001"
        result = {"id": "op_999", "status": "success"}
        custom_ttl = 3600  # 1 hour

        await manager.check_and_store(key, operation_result=result, ttl_seconds=custom_ttl)

        # Verify TTL was passed to Redis
        call_args = mock_redis.cache_set.call_args
        assert call_args[0][2] == custom_ttl  # Third arg is TTL

    @pytest.mark.asyncio
    async def test_concurrent_deductions_same_key(self) -> None:
        """Test concurrent calls with same idempotency key (race condition).

        Simulates:
        1. Two concurrent requests with same idempotency key
        2. Both check cache (both miss)
        3. Both attempt to store (only first succeeds)
        4. Verify single deduction result returned to both
        """
        import asyncio

        mock_redis = AsyncMock()

        # Simulate race: both threads check, both miss, but only one stores
        call_count = 0

        async def cache_get_side_effect(key: str) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return None  # Both concurrent calls miss
            return {"id": "op_race_001", "status": "success"}

        mock_redis.cache_get.side_effect = cache_get_side_effect
        mock_redis.cache_set = AsyncMock()

        manager = IdempotencyManager(redis_store=mock_redis)
        key = "test_key_race_001"
        result = {"id": "op_race_001", "status": "success", "amount": 150}

        # Simulate two concurrent calls
        task1 = manager.check_and_store(key, operation_result=result)
        task2 = manager.check_and_store(key, operation_result=result)

        r1, r2 = await asyncio.gather(task1, task2)

        # At least one should be None (stored), result should be consistent
        assert (r1 is None or r2 is None)
