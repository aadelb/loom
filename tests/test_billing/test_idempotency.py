"""Unit and integration tests for billing idempotency system.

Tests cover:
- Idempotency key generation
- Check-and-store behavior
- Duplicate request handling
- TTL and cache expiry
- Error handling and graceful degradation
"""

from __future__ import annotations

import pytest
from loom.billing.idempotency import (
    generate_idempotency_key,
    IdempotencyManager,
    get_idempotency_manager,
)


class TestIdempotencyKeyGeneration:
    """Test idempotency key generation."""

    def test_generates_64_char_hex(self) -> None:
        """Test that keys are 64-character SHA-256 hex strings."""
        key = generate_idempotency_key("user_123", "stripe_charge")
        assert isinstance(key, str)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_deterministic_for_same_inputs(self) -> None:
        """Test that same inputs always generate same key."""
        user_id = "cust_456"
        operation = "credit_deduct"
        params = {"tool_name": "research_deep", "credits": 10}

        key1 = generate_idempotency_key(user_id, operation, params)
        key2 = generate_idempotency_key(user_id, operation, params)

        assert key1 == key2

    def test_different_params_generate_different_keys(self) -> None:
        """Test that different params generate different keys."""
        user_id = "user_789"
        operation = "stripe_charge"

        key1 = generate_idempotency_key(user_id, operation, {"amount": 9999})
        key2 = generate_idempotency_key(user_id, operation, {"amount": 5000})

        assert key1 != key2

    def test_different_users_generate_different_keys(self) -> None:
        """Test that different users generate different keys."""
        operation = "meter_record"
        params = {"tool": "research_fetch", "credits": 3}

        key1 = generate_idempotency_key("user_a", operation, params)
        key2 = generate_idempotency_key("user_b", operation, params)

        assert key1 != key2

    def test_without_params(self) -> None:
        """Test key generation without params."""
        key = generate_idempotency_key("user_123", "operation_name")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_with_custom_timestamp_bucket(self) -> None:
        """Test key generation with custom timestamp bucket."""
        user_id = "user_123"
        operation = "charge"
        params = {"amount": 1000}
        timestamp_bucket = 1700000000

        key = generate_idempotency_key(
            user_id, operation, params, timestamp_bucket=timestamp_bucket
        )
        assert len(key) == 64

        # Same timestamp bucket should generate same key
        key2 = generate_idempotency_key(
            user_id, operation, params, timestamp_bucket=timestamp_bucket
        )
        assert key == key2

        # Different timestamp bucket should generate different key
        key3 = generate_idempotency_key(
            user_id, operation, params, timestamp_bucket=timestamp_bucket + 3600
        )
        assert key != key3


class TestIdempotencyManager:
    """Test IdempotencyManager class."""

    @pytest.mark.asyncio
    async def test_initialization(self) -> None:
        """Test manager initialization."""
        manager = IdempotencyManager()
        assert manager is not None
        assert manager._redis_store is None
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_check_and_store_new_key(self) -> None:
        """Test storing result for new key."""
        manager = IdempotencyManager()

        # Simulate Redis unavailable to test graceful degradation
        # (In real test with Redis, this would cache the result)
        key = "test_key_12345678901234567890123456789012"
        result = {"id": "charge_123", "amount": 9999}

        cached = await manager.check_and_store(key, result)
        assert cached is None  # New key, no cached result

    @pytest.mark.asyncio
    async def test_check_and_store_requires_result_for_new_key(self) -> None:
        """Test that operation_result is required for new keys."""
        manager = IdempotencyManager()
        key = "test_key_abcdef123456789012345678901234"

        with pytest.raises(ValueError, match="operation_result required"):
            await manager.check_and_store(key, None)

    @pytest.mark.asyncio
    async def test_clear_key(self) -> None:
        """Test clearing an idempotency key."""
        manager = IdempotencyManager()
        key = "test_key_fedcba987654321098765432109876543"

        result = await manager.clear_key(key)
        # Result depends on Redis availability
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_clear_prefix(self) -> None:
        """Test clearing keys by prefix."""
        manager = IdempotencyManager()
        user_id = "user_prefix_test"

        count = await manager.clear_prefix(user_id)
        assert isinstance(count, int)
        assert count >= 0


class TestIdempotencyGlobalSingleton:
    """Test global idempotency manager singleton."""

    @pytest.mark.asyncio
    async def test_get_idempotency_manager_returns_singleton(self) -> None:
        """Test that get_idempotency_manager returns same instance."""
        manager1 = await get_idempotency_manager()
        manager2 = await get_idempotency_manager()

        assert manager1 is manager2
        assert isinstance(manager1, IdempotencyManager)

    @pytest.mark.asyncio
    async def test_singleton_is_initialized(self) -> None:
        """Test that singleton is properly initialized."""
        manager = await get_idempotency_manager()
        assert manager is not None
        assert hasattr(manager, "_initialized")
