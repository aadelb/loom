"""Tests for idempotent credit deduction.

Tests cover:
- Credit deduction with idempotency
- Duplicate request handling
- Balance calculations
"""

from __future__ import annotations

import pytest
from loom.billing.credits import get_tool_cost, check_balance, deduct, deduct_with_idempotency


class TestCreditCosts:
    """Test credit cost calculation."""

    def test_get_tool_cost_light_tools(self) -> None:
        """Test light tools cost 1 credit."""
        assert get_tool_cost("research_search") == 1
        assert get_tool_cost("search") == 1
        assert get_tool_cost("text_analyze") == 1

    def test_get_tool_cost_medium_tools(self) -> None:
        """Test medium tools cost 3 credits."""
        assert get_tool_cost("research_fetch") == 3
        assert get_tool_cost("fetch") == 3
        assert get_tool_cost("spider") == 3

    def test_get_tool_cost_heavy_tools(self) -> None:
        """Test heavy tools cost 10 credits."""
        assert get_tool_cost("research_deep") == 10
        assert get_tool_cost("deep") == 10
        assert get_tool_cost("dark_forum") == 10

    def test_get_tool_cost_unknown_tool(self) -> None:
        """Test unknown tools default to 2 credits."""
        assert get_tool_cost("unknown_tool_xyz") == 2
        assert get_tool_cost("research_nonexistent") == 2

    def test_get_tool_cost_strips_prefix(self) -> None:
        """Test that research_ prefix is stripped."""
        assert get_tool_cost("research_search") == get_tool_cost("search")
        assert get_tool_cost("research_fetch") == get_tool_cost("fetch")


class TestCreditBalance:
    """Test balance checking."""

    def test_check_balance_sufficient(self) -> None:
        """Test check_balance returns True when balance sufficient."""
        assert check_balance(100, "research_search") is True
        assert check_balance(10, "research_fetch") is True
        assert check_balance(20, "research_deep") is True

    def test_check_balance_exact(self) -> None:
        """Test check_balance with exact balance."""
        assert check_balance(1, "research_search") is True
        assert check_balance(3, "research_fetch") is True
        assert check_balance(10, "research_deep") is True

    def test_check_balance_insufficient(self) -> None:
        """Test check_balance returns False when balance insufficient."""
        assert check_balance(0, "research_search") is False
        assert check_balance(2, "research_fetch") is False
        assert check_balance(5, "research_deep") is False


class TestCreditDeduction:
    """Test basic credit deduction."""

    def test_deduct_light_tool(self) -> None:
        """Test deducting credits for light tool."""
        remaining, cost = deduct(100, "research_search")
        assert cost == 1
        assert remaining == 99

    def test_deduct_medium_tool(self) -> None:
        """Test deducting credits for medium tool."""
        remaining, cost = deduct(100, "research_fetch")
        assert cost == 3
        assert remaining == 97

    def test_deduct_heavy_tool(self) -> None:
        """Test deducting credits for heavy tool."""
        remaining, cost = deduct(100, "research_deep")
        assert cost == 10
        assert remaining == 90

    def test_deduct_no_negative_balance(self) -> None:
        """Test that balance never goes negative."""
        remaining, cost = deduct(2, "research_fetch")
        assert cost == 3
        assert remaining == 0  # Not -1


class TestIdempotentCreditDeduction:
    """Test idempotent credit deduction."""

    @pytest.mark.asyncio
    async def test_deduct_with_idempotency_new_key(self) -> None:
        """Test deduction with new idempotency key."""
        result = await deduct_with_idempotency(
            "cust_123",
            "research_fetch",
            100,
        )

        assert result["success"] is True
        assert result["cost_charged"] == 3
        assert result["remaining_credits"] == 97
        assert result["is_duplicate"] is False
        assert "idempotency_key" in result
        assert len(result["idempotency_key"]) == 64

    @pytest.mark.asyncio
    async def test_deduct_with_idempotency_provided_key(self) -> None:
        """Test deduction with provided idempotency key."""
        key = "a" * 64  # Valid 64-char key
        result = await deduct_with_idempotency(
            "cust_456",
            "research_search",
            50,
            idempotency_key=key,
        )

        assert result["success"] is True
        assert result["idempotency_key"] == key
        assert result["is_duplicate"] is False

    @pytest.mark.asyncio
    async def test_deduct_with_idempotency_light_tool(self) -> None:
        """Test idempotent deduction for light tool."""
        result = await deduct_with_idempotency(
            "user_light",
            "research_search",
            100,
        )

        assert result["cost_charged"] == 1
        assert result["remaining_credits"] == 99

    @pytest.mark.asyncio
    async def test_deduct_with_idempotency_heavy_tool(self) -> None:
        """Test idempotent deduction for heavy tool."""
        result = await deduct_with_idempotency(
            "user_heavy",
            "research_deep",
            100,
        )

        assert result["cost_charged"] == 10
        assert result["remaining_credits"] == 90

    @pytest.mark.asyncio
    async def test_deduct_with_idempotency_zero_balance(self) -> None:
        """Test idempotent deduction when balance would go negative."""
        result = await deduct_with_idempotency(
            "user_low",
            "research_fetch",
            2,  # Only 2 credits, but fetch costs 3
        )

        assert result["cost_charged"] == 3
        assert result["remaining_credits"] == 0
        assert result["is_duplicate"] is False
