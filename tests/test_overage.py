"""Unit tests for billing overage handling.

Tests:
- Sufficient credits → allowed=True, action=proceed
- Insufficient + hard_stop → error with INSUFFICIENT_CREDITS code
- Insufficient + auto_topup → allowed=True, action=topup
- Auto topup adds correct credits (2000)
- Topup amount is correct ($20)
- Default mode is hard_stop
- Remaining balance calculated correctly after topup
- Zero credits + hard_stop → error
- Zero credits + auto_topup → allowed with topup
- Overage mode retrieval from customer config
- Invalid overage mode defaults to hard_stop
- Apply topup returns correct balance and amount
"""

from __future__ import annotations

import pytest

from loom.billing.overage import (
    DEFAULT_OVERAGE_MODE,
    TOPUP_AMOUNT_USD,
    TOPUP_CREDITS,
    apply_topup,
    check_overage,
    get_overage_mode,
)



pytestmark = pytest.mark.asyncio
class TestCheckOverageSufficientCredits:
    """Tests for check_overage when credits are sufficient."""

    async def test_sufficient_credits_returns_allowed_true(self) -> None:
        """check_overage returns allowed=True when credits >= cost."""
        result = check_overage(credits_remaining=100, tool_cost=50)

        assert result["allowed"] is True
        assert result["action"] == "proceed"

    async def test_sufficient_credits_deducts_cost_from_remaining(self) -> None:
        """check_overage calculates remaining = credits - cost."""
        result = check_overage(credits_remaining=100, tool_cost=30)

        assert result["remaining"] == 70

    async def test_sufficient_credits_exact_match(self) -> None:
        """check_overage returns proceed when credits exactly equal cost."""
        result = check_overage(credits_remaining=50, tool_cost=50)

        assert result["allowed"] is True
        assert result["remaining"] == 0

    async def test_sufficient_credits_large_balance(self) -> None:
        """check_overage handles large credit balances."""
        result = check_overage(credits_remaining=1_000_000, tool_cost=100)

        assert result["allowed"] is True
        assert result["remaining"] == 999_900


class TestCheckOverageHardStop:
    """Tests for check_overage in hard_stop mode."""

    async def test_insufficient_hard_stop_returns_error_dict(self) -> None:
        """check_overage returns error dict when insufficient + hard_stop."""
        result = check_overage(
            credits_remaining=10,
            tool_cost=50,
            overage_mode="hard_stop",
            tool_name="research_fetch",
        )

        assert isinstance(result, dict)
        assert result["error_code"] == "INSUFFICIENT_CREDITS"

    async def test_insufficient_hard_stop_includes_required_available(self) -> None:
        """check_overage error includes required and available credits."""
        result = check_overage(
            credits_remaining=25,
            tool_cost=100,
            overage_mode="hard_stop",
            tool_name="research_deep",
        )

        assert result["required"] == 100
        assert result["available"] == 25

    async def test_insufficient_hard_stop_zero_credits(self) -> None:
        """check_overage returns error when credits are zero."""
        result = check_overage(
            credits_remaining=0,
            tool_cost=10,
            overage_mode="hard_stop",
            tool_name="research_search",
        )

        assert result["error_code"] == "INSUFFICIENT_CREDITS"
        assert result["available"] == 0

    async def test_insufficient_hard_stop_includes_tool_name(self) -> None:
        """check_overage error includes the tool name."""
        result = check_overage(
            credits_remaining=5,
            tool_cost=20,
            overage_mode="hard_stop",
            tool_name="research_spider",
        )

        assert result["tool_name"] == "research_spider"


class TestCheckOverageAutoTopup:
    """Tests for check_overage in auto_topup mode."""

    async def test_insufficient_auto_topup_returns_allowed_true(self) -> None:
        """check_overage returns allowed=True with auto_topup."""
        result = check_overage(
            credits_remaining=10,
            tool_cost=50,
            overage_mode="auto_topup",
        )

        assert result["allowed"] is True
        assert result["action"] == "topup"

    async def test_insufficient_auto_topup_adds_topup_credits(self) -> None:
        """check_overage adds TOPUP_CREDITS to balance."""
        result = check_overage(
            credits_remaining=100,
            tool_cost=200,
            overage_mode="auto_topup",
        )

        # 100 + 2000 - 200 = 1900
        assert result["remaining"] == 1900

    async def test_insufficient_auto_topup_amount_is_20_usd(self) -> None:
        """check_overage topup_amount_usd is exactly $20."""
        result = check_overage(
            credits_remaining=50,
            tool_cost=100,
            overage_mode="auto_topup",
        )

        assert result["topup_amount_usd"] == 20

    async def test_insufficient_auto_topup_credits_is_2000(self) -> None:
        """check_overage topup_credits is exactly 2000."""
        result = check_overage(
            credits_remaining=50,
            tool_cost=100,
            overage_mode="auto_topup",
        )

        assert result["topup_credits"] == 2000

    async def test_insufficient_auto_topup_zero_credits(self) -> None:
        """check_overage auto_topup works when credits are zero."""
        result = check_overage(
            credits_remaining=0,
            tool_cost=100,
            overage_mode="auto_topup",
        )

        assert result["allowed"] is True
        assert result["remaining"] == 2000 - 100  # 1900

    async def test_insufficient_auto_topup_includes_message(self) -> None:
        """check_overage topup returns explanatory message."""
        result = check_overage(
            credits_remaining=10,
            tool_cost=50,
            overage_mode="auto_topup",
        )

        assert "message" in result
        assert "2000" in result["message"]
        assert "$20" in result["message"]

    async def test_insufficient_auto_topup_large_tool_cost(self) -> None:
        """check_overage auto_topup handles tool cost > topup_credits."""
        result = check_overage(
            credits_remaining=500,
            tool_cost=3000,
            overage_mode="auto_topup",
        )

        # 500 + 2000 - 3000 = -500 (negative balance, but still allowed)
        assert result["allowed"] is True
        assert result["remaining"] == -500


class TestCheckOverageDefaults:
    """Tests for check_overage default parameters."""

    async def test_default_mode_is_hard_stop(self) -> None:
        """check_overage defaults to hard_stop when mode not specified."""
        result = check_overage(
            credits_remaining=10,
            tool_cost=50,
            # Omit overage_mode parameter
        )

        assert result["error_code"] == "INSUFFICIENT_CREDITS"

    async def test_default_tool_name_is_unknown(self) -> None:
        """check_overage uses 'unknown' tool name when not specified."""
        result = check_overage(
            credits_remaining=10,
            tool_cost=50,
            overage_mode="hard_stop",
            # Omit tool_name parameter
        )

        assert result["tool_name"] == "unknown"


class TestGetOverageMode:
    """Tests for get_overage_mode configuration retrieval."""

    async def test_get_overage_mode_hard_stop(self) -> None:
        """get_overage_mode returns hard_stop from config."""
        config = {"overage_mode": "hard_stop"}
        result = get_overage_mode(config)

        assert result == "hard_stop"

    async def test_get_overage_mode_auto_topup(self) -> None:
        """get_overage_mode returns auto_topup from config."""
        config = {"overage_mode": "auto_topup"}
        result = get_overage_mode(config)

        assert result == "auto_topup"

    async def test_get_overage_mode_missing_key_defaults(self) -> None:
        """get_overage_mode defaults when key missing from config."""
        config = {"some_other_key": "value"}
        result = get_overage_mode(config)

        assert result == DEFAULT_OVERAGE_MODE

    async def test_get_overage_mode_empty_config(self) -> None:
        """get_overage_mode defaults when config is empty dict."""
        result = get_overage_mode({})

        assert result == DEFAULT_OVERAGE_MODE

    async def test_get_overage_mode_none_config(self) -> None:
        """get_overage_mode defaults when config is None."""
        result = get_overage_mode(None)

        assert result == DEFAULT_OVERAGE_MODE

    async def test_get_overage_mode_invalid_mode_defaults(self) -> None:
        """get_overage_mode defaults when mode is invalid."""
        config = {"overage_mode": "invalid_mode"}
        result = get_overage_mode(config)

        assert result == DEFAULT_OVERAGE_MODE

    async def test_get_overage_mode_case_sensitive(self) -> None:
        """get_overage_mode is case-sensitive and defaults on mismatch."""
        config = {"overage_mode": "HARD_STOP"}
        result = get_overage_mode(config)

        assert result == DEFAULT_OVERAGE_MODE


class TestApplyTopup:
    """Tests for apply_topup helper function."""

    async def test_apply_topup_default_amount(self) -> None:
        """apply_topup adds TOPUP_CREDITS by default."""
        new_balance, amount_added = apply_topup(credits_remaining=100)

        assert new_balance == 100 + TOPUP_CREDITS
        assert amount_added == TOPUP_CREDITS

    async def test_apply_topup_custom_amount(self) -> None:
        """apply_topup can use custom topup amount."""
        new_balance, amount_added = apply_topup(
            credits_remaining=100,
            topup_credits=5000,
        )

        assert new_balance == 100 + 5000
        assert amount_added == 5000

    async def test_apply_topup_zero_balance(self) -> None:
        """apply_topup works with zero starting balance."""
        new_balance, amount_added = apply_topup(credits_remaining=0)

        assert new_balance == TOPUP_CREDITS
        assert amount_added == TOPUP_CREDITS

    async def test_apply_topup_large_balance(self) -> None:
        """apply_topup handles large starting balances."""
        new_balance, amount_added = apply_topup(credits_remaining=1_000_000)

        assert new_balance == 1_000_000 + TOPUP_CREDITS
        assert amount_added == TOPUP_CREDITS


class TestIntegration:
    """Integration tests combining multiple overage features."""

    async def test_workflow_insufficient_hard_stop_flow(self) -> None:
        """End-to-end: insufficient credits, hard_stop mode, get error."""
        config = {"overage_mode": "hard_stop"}
        mode = get_overage_mode(config)

        result = check_overage(
            credits_remaining=50,
            tool_cost=100,
            overage_mode=mode,
            tool_name="research_fetch",
        )

        assert result["error_code"] == "INSUFFICIENT_CREDITS"
        assert result["available"] == 50

    async def test_workflow_insufficient_auto_topup_flow(self) -> None:
        """End-to-end: insufficient credits, auto_topup mode, allows + topup."""
        config = {"overage_mode": "auto_topup"}
        mode = get_overage_mode(config)

        result = check_overage(
            credits_remaining=500,
            tool_cost=1000,
            overage_mode=mode,
            tool_name="research_deep",
        )

        assert result["allowed"] is True
        assert result["action"] == "topup"
        assert result["remaining"] == 500 + 2000 - 1000

    async def test_workflow_sufficient_both_modes(self) -> None:
        """End-to-end: sufficient credits works in both modes."""
        for mode in ["hard_stop", "auto_topup"]:
            config = {"overage_mode": mode}
            overage_mode = get_overage_mode(config)

            result = check_overage(
                credits_remaining=200,
                tool_cost=100,
                overage_mode=overage_mode,
                tool_name="research_search",
            )

            assert result["allowed"] is True
            assert result["action"] == "proceed"
            assert result["remaining"] == 100

    async def test_workflow_topup_then_deduct(self) -> None:
        """End-to-end: topup balance, then simulate deduction."""
        # Start with 100 credits, need 200
        initial_balance = 100
        tool_cost = 200

        # First check triggers topup
        topup_result = check_overage(
            credits_remaining=initial_balance,
            tool_cost=tool_cost,
            overage_mode="auto_topup",
        )

        assert topup_result["allowed"] is True
        new_balance_after_topup = topup_result["remaining"]

        # Apply topup to customer
        customer_balance, amount_added = apply_topup(initial_balance)
        assert customer_balance == initial_balance + TOPUP_CREDITS
        # Deduct tool cost
        final_balance = customer_balance - tool_cost
        assert final_balance == new_balance_after_topup
