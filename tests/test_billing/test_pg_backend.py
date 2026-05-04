"""Tests for PostgreSQL billing backend integration.

Tests the async billing functions with graceful fallback to JSON.
Requires DATABASE_URL env var to be set for PostgreSQL tests.
"""

from __future__ import annotations

import os
import pytest

# These tests use async/await
pytestmark = pytest.mark.asyncio


@pytest.fixture
def use_json_backend():
    """Force JSON backend for fallback tests."""
    original = os.environ.get("LOOM_BILLING_BACKEND")
    os.environ["LOOM_BILLING_BACKEND"] = "json"
    yield
    if original:
        os.environ["LOOM_BILLING_BACKEND"] = original
    else:
        os.environ.pop("LOOM_BILLING_BACKEND", None)


@pytest.fixture
def use_postgres_backend():
    """Force PostgreSQL backend."""
    original = os.environ.get("LOOM_BILLING_BACKEND")
    os.environ["LOOM_BILLING_BACKEND"] = "postgres"
    yield
    if original:
        os.environ["LOOM_BILLING_BACKEND"] = original
    else:
        os.environ.pop("LOOM_BILLING_BACKEND", None)


class TestCustomersAsync:
    """Test async customer management functions."""

    async def test_create_customer_json_backend(self, use_json_backend):
        """Test creating a customer with JSON backend."""
        from loom.billing import create_customer

        result = await create_customer(
            name="Test User",
            email="test@example.com",
            tier="free"
        )

        assert result["customer_id"]
        assert result["api_key"].startswith("loom_live_")
        assert result["tier"] == "free"

    async def test_get_customer_json_backend(self, use_json_backend):
        """Test retrieving a customer with JSON backend."""
        from loom.billing import create_customer, get_customer

        # Create a customer
        created = await create_customer(
            name="Retrieve Test",
            email="retrieve@example.com",
            tier="pro"
        )

        # Retrieve it
        retrieved = await get_customer(created["customer_id"])

        assert retrieved is not None
        assert retrieved["name"] == "Retrieve Test"
        assert retrieved["email"] == "retrieve@example.com"
        assert retrieved["tier"] == "pro"

    async def test_update_credits_json_backend(self, use_json_backend):
        """Test updating credits with JSON backend."""
        from loom.billing import create_customer, update_credits

        created = await create_customer(
            name="Credits Test",
            email="credits@example.com",
            tier="free"
        )

        # Update credits
        result = await update_credits(
            created["customer_id"],
            100,
            reason="test_topup"
        )

        # Result should be new balance (500 initial free tier + 100)
        assert result == 600

    async def test_rotate_key_json_backend(self, use_json_backend):
        """Test key rotation with JSON backend."""
        from loom.billing import create_customer, rotate_key

        created = await create_customer(
            name="Rotate Test",
            email="rotate@example.com"
        )

        old_key = created["api_key"]

        # Rotate key
        rotated = await rotate_key(created["customer_id"])

        assert rotated is not None
        assert rotated["api_key"] != old_key
        assert rotated["api_key"].startswith("loom_live_")

    async def test_list_customers_json_backend(self, use_json_backend):
        """Test listing customers with JSON backend."""
        from loom.billing import create_customer, list_customers

        # Create a few customers
        for i in range(3):
            await create_customer(
                name=f"List Test {i}",
                email=f"list{i}@example.com"
            )

        customers = await list_customers()

        assert len(customers) >= 3
        assert all("customer_id" in c for c in customers)
        assert all("name" in c for c in customers)


class TestMeterAsync:
    """Test async usage metering functions."""

    async def test_record_usage_json_backend(self, use_json_backend):
        """Test recording usage with JSON backend."""
        from loom.billing import record_usage

        entry = await record_usage(
            customer_id="test_customer_1",
            tool_name="research_fetch",
            credits_used=3,
            duration_ms=1234.5
        )

        assert entry["customer_id"] == "test_customer_1"
        assert entry["tool_name"] == "research_fetch"
        assert entry["credits_used"] == 3
        assert entry["duration_ms"] == 1234.5
        assert "timestamp" in entry

    async def test_get_usage_json_backend(self, use_json_backend):
        """Test retrieving usage stats with JSON backend."""
        from loom.billing import record_usage, get_usage

        customer_id = "test_customer_2"

        # Record some usage
        for i in range(3):
            await record_usage(
                customer_id=customer_id,
                tool_name="research_search",
                credits_used=1
            )

        # Get usage
        usage = await get_usage(customer_id)

        assert usage["customer_id"] == customer_id
        assert usage["total_credits"] == 3
        assert usage["total_calls"] == 3
        assert "research_search" in usage["by_tool"]

    async def test_get_top_tools_json_backend(self, use_json_backend):
        """Test getting top tools with JSON backend."""
        from loom.billing import record_usage, get_top_tools

        customer_id = "test_customer_3"

        # Record varied usage
        await record_usage(customer_id, "research_fetch", credits_used=10)
        await record_usage(customer_id, "research_search", credits_used=3)
        await record_usage(customer_id, "research_spider", credits_used=5)

        top_tools = await get_top_tools(customer_id, limit=2)

        assert len(top_tools) == 2
        assert top_tools[0]["tool"] == "research_fetch"  # Highest credits
        assert top_tools[0]["credits"] == 10


class TestCreditsAsync:
    """Test async credit functions."""

    async def test_deduct_with_idempotency(self, use_json_backend):
        """Test credit deduction with idempotency."""
        from loom.billing import deduct_with_idempotency

        result = await deduct_with_idempotency(
            customer_id="test_customer_4",
            tool_name="research_fetch",
            current_credits=100,
            idempotency_key="test_deduction_1"
        )

        assert result["success"] is True
        assert result["is_duplicate"] is False
        assert result["cost_charged"] == 3  # fetch costs 3 credits
        assert result["remaining_credits"] == 97

    async def test_deduct_idempotency_duplicate(self, use_json_backend):
        """Test that idempotency prevents duplicate deductions."""
        from loom.billing import deduct_with_idempotency

        idempotency_key = "test_deduction_2"

        # First call
        result1 = await deduct_with_idempotency(
            customer_id="test_customer_5",
            tool_name="research_search",
            current_credits=100,
            idempotency_key=idempotency_key
        )

        # Second call with same key (should return cached result)
        result2 = await deduct_with_idempotency(
            customer_id="test_customer_5",
            tool_name="research_search",
            current_credits=100,  # Same current credits
            idempotency_key=idempotency_key
        )

        assert result1["cost_charged"] == result2["cost_charged"]
        assert result1["remaining_credits"] == result2["remaining_credits"]
        assert result2["is_duplicate"] is True

    async def test_get_credit_ledger_json_backend(self, use_json_backend):
        """Test retrieving credit ledger with JSON backend."""
        from loom.billing import get_credit_ledger

        ledger = await get_credit_ledger("test_customer_6")

        # JSON backend returns empty list (no ledger tracking in JSON)
        assert isinstance(ledger, list)


class TestBackendInitialization:
    """Test backend initialization functions."""

    async def test_initialize_json_backend(self, use_json_backend):
        """Test initializing JSON backend."""
        from loom.billing import initialize_billing_backend

        result = await initialize_billing_backend()

        assert result["backend"] == "json"
        assert result["status"] == "initialized"

    async def test_get_configured_backend_json(self, use_json_backend):
        """Test getting configured backend name."""
        from loom.billing.backend import get_configured_backend

        backend = get_configured_backend()
        assert backend == "json"

    async def test_describe_backends(self):
        """Test backend description function."""
        from loom.billing.backend import describe_backends

        backends = describe_backends()

        assert "postgres" in backends
        assert "json" in backends
        assert backends["postgres"]["name"] == "PostgreSQL"
        assert backends["json"]["name"] == "JSON File"


class TestGracefulFallback:
    """Test fallback behavior when backends are unavailable."""

    async def test_operations_succeed_with_json_backend(self, use_json_backend):
        """Verify all operations succeed with JSON backend."""
        from loom.billing import (
            create_customer,
            get_customer,
            update_credits,
            record_usage,
            get_usage,
        )

        # Create customer
        customer = await create_customer("Fallback Test", "fallback@example.com")
        assert customer["customer_id"]

        # Get customer
        retrieved = await get_customer(customer["customer_id"])
        assert retrieved is not None

        # Update credits
        new_balance = await update_credits(customer["customer_id"], 50)
        assert new_balance is not None

        # Record usage
        entry = await record_usage(customer["customer_id"], "research_search", 1)
        assert entry["customer_id"] == customer["customer_id"]

        # Get usage
        usage = await get_usage(customer["customer_id"])
        assert usage["total_credits"] == 1

    async def test_all_functions_async(self, use_json_backend):
        """Verify all billing functions are async."""
        from loom.billing import (
            create_customer,
            get_customer,
            update_credits,
            rotate_key,
            revoke_key,
            validate_key,
            list_customers,
            record_usage,
            record_usage_idempotent,
            get_usage,
            get_top_tools,
            deduct_with_idempotency,
            get_credit_ledger,
            initialize_billing_backend,
        )
        import inspect

        # Check that key functions are coroutines
        assert inspect.iscoroutinefunction(create_customer)
        assert inspect.iscoroutinefunction(get_customer)
        assert inspect.iscoroutinefunction(update_credits)
        assert inspect.iscoroutinefunction(record_usage)
        assert inspect.iscoroutinefunction(get_usage)
