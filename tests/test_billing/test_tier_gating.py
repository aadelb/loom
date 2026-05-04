"""Unit tests for the @requires_tier decorator.

Tests:
- Sync and async function decoration
- Tier hierarchy enforcement
- Error response format
- Default tier fallback
"""

from __future__ import annotations

import asyncio
import pytest

from loom.billing.tier_gating import (
    TIER_HIERARCHY,
    _check_tier_access,
    _get_current_user_tier,
    requires_tier,
)


class TestTierHierarchy:
    """Test tier hierarchy structure."""

    def test_tier_hierarchy_ordering(self) -> None:
        """Verify tier hierarchy has correct ordering."""
        assert TIER_HIERARCHY["free"] < TIER_HIERARCHY["pro"]
        assert TIER_HIERARCHY["pro"] < TIER_HIERARCHY["team"]
        assert TIER_HIERARCHY["team"] < TIER_HIERARCHY["enterprise"]

    def test_all_valid_tiers_in_hierarchy(self) -> None:
        """Verify all tiers exist in hierarchy."""
        valid_tiers = {"free", "pro", "team", "enterprise"}
        assert set(TIER_HIERARCHY.keys()) == valid_tiers


class TestCheckTierAccess:
    """Test the _check_tier_access function."""

    def test_same_tier_allowed(self) -> None:
        """User with same tier should be allowed."""
        allowed, error = _check_tier_access("pro", "pro")
        assert allowed is True
        assert error is None

    def test_higher_tier_allowed(self) -> None:
        """User with higher tier should be allowed."""
        allowed, error = _check_tier_access("pro", "enterprise")
        assert allowed is True
        assert error is None

    def test_lower_tier_denied(self) -> None:
        """User with lower tier should be denied."""
        allowed, error = _check_tier_access("pro", "free")
        assert allowed is False
        assert error is not None

    def test_error_response_format(self) -> None:
        """Error response should have required fields."""
        allowed, error = _check_tier_access("team", "pro")
        assert allowed is False
        assert error is not None

        # Check required fields
        assert "error" in error
        assert "current_tier" in error
        assert "required_tier" in error
        assert "current_tier_name" in error
        assert "required_tier_name" in error
        assert "upgrade_url" in error
        assert "message" in error

        # Check values
        assert error["error"] == "upgrade_required"
        assert error["current_tier"] == "pro"
        assert error["required_tier"] == "team"
        assert error["current_tier_name"] == "Pro"
        assert error["required_tier_name"] == "Team"

    def test_free_tier_allowed_for_free_requirement(self) -> None:
        """Free tier user should access free tier tools."""
        allowed, error = _check_tier_access("free", "free")
        assert allowed is True
        assert error is None

    def test_enterprise_requirement_blocks_lower_tiers(self) -> None:
        """Enterprise-only tool should block all lower tiers."""
        for tier in ["free", "pro", "team"]:
            allowed, error = _check_tier_access("enterprise", tier)
            assert allowed is False
            assert error is not None


class TestRequiresTierDecorator:
    """Test the @requires_tier decorator."""

    def test_decorator_with_sync_function(self) -> None:
        """Decorator should work with sync functions."""

        @requires_tier("pro")
        def sync_tool(data: str) -> dict:
            return {"result": f"processed_{data}"}

        # Call should succeed (defaults to free tier)
        result = sync_tool("test")
        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "upgrade_required"

    def test_decorator_with_async_function(self) -> None:
        """Decorator should work with async functions."""

        @requires_tier("pro")
        async def async_tool(data: str) -> dict:
            return {"result": f"processed_{data}"}

        # Call should return error (defaults to free tier)
        result = asyncio.run(async_tool("test"))
        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "upgrade_required"

    def test_invalid_tier_raises_error(self) -> None:
        """Decorator should validate tier parameter."""
        with pytest.raises(ValueError) as exc_info:

            @requires_tier("invalid_tier")
            def bad_tool() -> None:
                pass

        assert "Invalid min_tier" in str(exc_info.value)

    def test_preserves_function_metadata(self) -> None:
        """Decorator should preserve original function metadata."""

        @requires_tier("pro")
        def documented_tool(x: int) -> int:
            """A documented tool."""
            return x * 2

        assert documented_tool.__name__ == "documented_tool"
        assert documented_tool.__doc__ == "A documented tool."

    def test_sync_wrapper_returns_error_on_tier_check_failure(self) -> None:
        """Sync wrapper should return error dict when tier check fails."""

        @requires_tier("team")
        def restricted_tool(value: str) -> dict:
            return {"data": value}

        # With default tier (free), should get error
        result = restricted_tool("test_value")
        assert isinstance(result, dict)
        assert result["error"] == "upgrade_required"
        assert result["current_tier"] == "free"
        assert result["required_tier"] == "team"

    @pytest.mark.asyncio
    async def test_async_wrapper_returns_error_on_tier_check_failure(self) -> None:
        """Async wrapper should return error dict when tier check fails."""

        @requires_tier("enterprise")
        async def restricted_async_tool(value: str) -> dict:
            return {"data": value}

        # With default tier (free), should get error
        result = await restricted_async_tool("test_value")
        assert isinstance(result, dict)
        assert result["error"] == "upgrade_required"
        assert result["current_tier"] == "free"
        assert result["required_tier"] == "enterprise"

    def test_free_tier_tools_work_without_gating(self) -> None:
        """Tools requiring free tier should work with default user."""

        @requires_tier("free")
        def free_tool(x: int) -> dict:
            return {"result": x + 1}

        result = free_tool(5)
        # Should execute normally since default tier is free
        assert result["result"] == 6

    @pytest.mark.asyncio
    async def test_async_free_tier_tools_work(self) -> None:
        """Async tools requiring free tier should work with default user."""

        @requires_tier("free")
        async def async_free_tool(x: int) -> dict:
            return {"result": x + 1}

        result = await async_free_tool(5)
        assert result["result"] == 6

    def test_function_args_preserved_in_error_case(self) -> None:
        """When tier check fails, function should not be called with args."""

        @requires_tier("enterprise")
        def side_effect_tool(side_effects: list) -> dict:
            side_effects.append("executed")
            return {"status": "ran"}

        side_effects: list = []
        result = side_effect_tool(side_effects)

        # Function should not have been called
        assert "error" in result
        assert len(side_effects) == 0

    @pytest.mark.asyncio
    async def test_async_function_args_preserved_in_error_case(self) -> None:
        """When tier check fails, async function should not be called."""

        @requires_tier("enterprise")
        async def async_side_effect_tool(side_effects: list) -> dict:
            side_effects.append("executed")
            return {"status": "ran"}

        side_effects: list = []
        result = await async_side_effect_tool(side_effects)

        # Function should not have been called
        assert "error" in result
        assert len(side_effects) == 0


class TestCurrentUserTier:
    """Test the _get_current_user_tier function."""

    def test_defaults_to_free_tier(self) -> None:
        """Should default to free tier when no context available."""
        tier = _get_current_user_tier()
        assert tier == "free"

    def test_returns_string(self) -> None:
        """Should return a string."""
        tier = _get_current_user_tier()
        assert isinstance(tier, str)
        assert tier in TIER_HIERARCHY


class TestDecoratorWithKwargs:
    """Test decorator with keyword arguments."""

    def test_sync_function_with_kwargs(self) -> None:
        """Decorator should work with keyword arguments."""

        @requires_tier("pro")
        def tool_with_kwargs(name: str, value: int = 10) -> dict:
            return {"name": name, "value": value}

        result = tool_with_kwargs("test", value=20)
        # Should get error due to tier check
        assert result["error"] == "upgrade_required"

    @pytest.mark.asyncio
    async def test_async_function_with_kwargs(self) -> None:
        """Async decorator should work with keyword arguments."""

        @requires_tier("pro")
        async def async_tool_with_kwargs(name: str, value: int = 10) -> dict:
            return {"name": name, "value": value}

        result = await async_tool_with_kwargs("test", value=20)
        assert result["error"] == "upgrade_required"

    def test_free_tier_with_kwargs_executes(self) -> None:
        """Free tier tool with kwargs should execute normally."""

        @requires_tier("free")
        def free_tool_kwargs(name: str, value: int = 10) -> dict:
            return {"name": name, "value": value}

        result = free_tool_kwargs("test", value=20)
        assert result["name"] == "test"
        assert result["value"] == 20


class TestErrorMessageContent:
    """Test the content and format of error messages."""

    def test_error_message_includes_upgrade_url(self) -> None:
        """Error response should include upgrade URL."""

        @requires_tier("pro")
        def pro_tool() -> dict:
            return {"status": "ok"}

        result = pro_tool()
        assert "upgrade_url" in result
        assert isinstance(result["upgrade_url"], str)

    def test_error_message_is_user_friendly(self) -> None:
        """Error message should be clear and user-friendly."""

        @requires_tier("team")
        def team_tool() -> dict:
            return {"status": "ok"}

        result = team_tool()
        assert "message" in result
        assert "Team" in result["message"]
        # Message should reference tiers clearly
        assert "Free" in result["message"] or "free" in result["message"].lower()

    def test_tier_names_are_capitalized(self) -> None:
        """Tier names in error should be capitalized."""

        @requires_tier("enterprise")
        def enterprise_tool() -> dict:
            return {"status": "ok"}

        result = enterprise_tool()
        assert result["current_tier_name"] == "Free"
        assert result["required_tier_name"] == "Enterprise"
