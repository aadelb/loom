"""Tests for token economy middleware.

Tests credit checking, deduction, and balance queries.
"""

import pytest

from loom.billing.token_economy import (
    TOOL_COSTS,
    DEFAULT_COST,
    check_balance,
    deduct_credits,
    get_balance,
    get_tool_cost,
)


class TestGetToolCost:
    """Test tool cost lookup."""

    def test_free_tools(self) -> None:
        """Free tools cost 0 credits."""
        assert get_tool_cost("cache_stats") == 0
        assert get_tool_cost("health_check") == 0
        assert get_tool_cost("config_get") == 0
        assert get_tool_cost("session_list") == 0

    def test_basic_tools(self) -> None:
        """Basic tools cost 1 credit."""
        assert get_tool_cost("search") == 1
        assert get_tool_cost("text_analyze") == 1
        assert get_tool_cost("detect_language") == 1
        assert get_tool_cost("llm_embed") == 1

    def test_medium_tools(self) -> None:
        """Medium tools cost 5 credits."""
        assert get_tool_cost("fetch") == 5
        assert get_tool_cost("spider") == 5
        assert get_tool_cost("markdown") == 5
        assert get_tool_cost("github") == 5

    def test_heavy_tools(self) -> None:
        """Heavy tools cost 10 credits."""
        assert get_tool_cost("deep") == 10
        assert get_tool_cost("ask_all_models") == 10
        assert get_tool_cost("multi_search") == 10

    def test_research_prefix_stripped(self) -> None:
        """research_ prefix is stripped during lookup."""
        assert get_tool_cost("research_fetch") == 5
        assert get_tool_cost("research_deep") == 10
        assert get_tool_cost("research_search") == 1

    def test_unknown_tool_uses_default(self) -> None:
        """Unknown tools use DEFAULT_COST."""
        assert get_tool_cost("unknown_tool_xyz") == DEFAULT_COST
        assert get_tool_cost("research_unknown_abc") == DEFAULT_COST



    def test_premium_tools(self) -> None:
        """Premium tools cost 20 credits."""
        assert get_tool_cost("dark_forum") == 20
        assert get_tool_cost("onion_discover") == 20
        assert get_tool_cost("sandbox_run") == 20

class TestCheckBalance:
    """Test balance checking before execution."""

    def test_sufficient_balance(self) -> None:
        """Check passes when balance >= cost."""
        result = check_balance("user1", 10, "fetch")
        assert result["sufficient"] is True
        assert result["required"] == 5
        assert result["balance"] == 10
        assert result["shortfall"] == 0

    def test_insufficient_balance(self) -> None:
        """Check fails when balance < cost."""
        result = check_balance("user1", 3, "fetch")
        assert result["sufficient"] is False
        assert result["required"] == 5
        assert result["balance"] == 3
        assert result["shortfall"] == 2

    def test_exact_balance(self) -> None:
        """Check passes when balance == cost."""
        result = check_balance("user1", 5, "fetch")
        assert result["sufficient"] is True
        assert result["shortfall"] == 0

    def test_free_tool_always_sufficient(self) -> None:
        """Free tools always have sufficient balance."""
        result = check_balance("user1", 0, "cache_stats")
        assert result["sufficient"] is True
        assert result["required"] == 0
        assert result["shortfall"] == 0


class TestDeductCredits:
    """Test credit deduction after execution."""

    def test_basic_deduction(self) -> None:
        """Deduction reduces balance by tool cost."""
        result = deduct_credits("user1", 100, "fetch")
        assert result["success"] is True
        assert result["balance_before"] == 100
        assert result["cost_charged"] == 5
        assert result["balance_after"] == 95

    def test_deduction_with_exact_balance(self) -> None:
        """Deduction with exact balance leaves 0."""
        result = deduct_credits("user1", 5, "fetch")
        assert result["success"] is True
        assert result["balance_before"] == 5
        assert result["cost_charged"] == 5
        assert result["balance_after"] == 0

    def test_free_tool_deduction(self) -> None:
        """Free tools don't reduce balance."""
        result = deduct_credits("user1", 50, "cache_stats")
        assert result["success"] is True
        assert result["cost_charged"] == 0
        assert result["balance_after"] == 50

    def test_multiple_deductions(self) -> None:
        """Track balance through multiple deductions."""
        balance = 100

        # Fetch (5 credits)
        result1 = deduct_credits("user1", balance, "fetch")
        balance = result1["balance_after"]
        assert balance == 95

        # Deep search (10 credits)
        result2 = deduct_credits("user1", balance, "deep")
        balance = result2["balance_after"]
        assert balance == 85

        # Search (1 credit)
        result3 = deduct_credits("user1", balance, "search")
        balance = result3["balance_after"]
        assert balance == 84

    def test_zero_balance_stays_zero(self) -> None:
        """Balance never goes negative."""
        result = deduct_credits("user1", 2, "fetch")
        assert result["balance_after"] == 0  # Not negative


class TestGetBalance:
    """Test balance query."""

    def test_get_balance(self) -> None:
        """Balance query returns user_id and current balance."""
        result = get_balance("user1", 75)
        assert result["user_id"] == "user1"
        assert result["balance"] == 75

    def test_zero_balance_query(self) -> None:
        """Can query zero balance."""
        result = get_balance("user_broke", 0)
        assert result["user_id"] == "user_broke"
        assert result["balance"] == 0


class TestToolCostMapping:
    """Test TOOL_COSTS dictionary consistency."""

    def test_all_tools_have_valid_costs(self) -> None:
        """All entries in TOOL_COSTS are non-negative integers."""
        for tool, cost in TOOL_COSTS.items():
            assert isinstance(cost, int), f"Tool {tool} cost is not int: {type(cost)}"
            assert cost >= 0, f"Tool {tool} has negative cost: {cost}"

    def test_free_tools_zero_cost(self) -> None:
        """All 'free' category tools cost 0."""
        free_tools = ["cache_stats", "cache_clear", "health_check", "config_get", "session_list"]
        for tool in free_tools:
            assert TOOL_COSTS.get(tool, -1) == 0, f"Free tool {tool} should cost 0"

    def test_cost_tiers_exist(self) -> None:
        """Cost tiers for basic, medium, heavy, premium tools exist."""
        basic_exists = any(cost == 1 for cost in TOOL_COSTS.values())
        medium_exists = any(cost == 5 for cost in TOOL_COSTS.values())
        heavy_exists = any(cost == 10 for cost in TOOL_COSTS.values())
        premium_exists = any(cost == 20 for cost in TOOL_COSTS.values())

        assert basic_exists, "No tools with cost 1 found"
        assert medium_exists, "No tools with cost 5 found"
        assert heavy_exists, "No tools with cost 10 found"
        assert premium_exists, "No tools with cost 20 found"


class TestScenarios:
    """Integration test scenarios."""

    def test_user_runs_tools_until_exhausted(self) -> None:
        """Simulate user running tools until balance exhausted."""
        user_id = "test_user"
        balance = 20

        # Run cheap tool (1 credit)
        check = check_balance(user_id, balance, "search")
        assert check["sufficient"]
        deduct = deduct_credits(user_id, balance, "search")
        balance = deduct["balance_after"]
        assert balance == 19

        # Run medium tool (5 credits)
        check = check_balance(user_id, balance, "fetch")
        assert check["sufficient"]
        deduct = deduct_credits(user_id, balance, "fetch")
        balance = deduct["balance_after"]
        assert balance == 14

        # Try expensive tool (10 credits) - should fail
        check = check_balance(user_id, balance, "deep")
        assert check["sufficient"]  # Still enough
        deduct = deduct_credits(user_id, balance, "deep")
        balance = deduct["balance_after"]
        assert balance == 4

        # Try expensive tool again - should fail
        check = check_balance(user_id, balance, "deep")
        assert not check["sufficient"]
        assert check["shortfall"] == 6

    def test_free_tier_with_free_tools(self) -> None:
        """Free tier can use unlimited free tools."""
        user_id = "free_user"
        balance = 0  # No credits

        # Can use all free tools
        for _ in range(100):
            check = check_balance(user_id, balance, "cache_stats")
            assert check["sufficient"]
            deduct = deduct_credits(user_id, balance, "cache_stats")
            assert deduct["balance_after"] == 0

    def test_premium_tool_access_control(self) -> None:
        """Premium tools require significant credit balance."""
        user_id = "power_user"

        # Not enough for premium tool
        balance = 15
        check = check_balance(user_id, balance, "sandbox_run")
        assert not check["sufficient"]
        assert check["required"] == 20

        # Enough for premium tool
        balance = 50
        check = check_balance(user_id, balance, "sandbox_run")
        assert check["sufficient"]
        deduct = deduct_credits(user_id, balance, "sandbox_run")
        assert deduct["balance_after"] == 30
