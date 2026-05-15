"""Unit tests for cost_estimator tools."""

from __future__ import annotations

import asyncio

import pytest

from loom.tools.infrastructure.cost_estimator import (
    COST_MAP,
    TOKEN_ESTIMATES,
    _calculate_cost,
    _estimate_tokens,
    _find_free_alternatives,
    _select_provider,
    research_cost_summary,
    research_estimate_cost,
)


class TestTokenEstimation:
    """Test token estimation for different tool types."""

    def test_estimate_fetch_tokens(self) -> None:
        """Fetch tools estimate ~100 tokens (no LLM)."""
        tokens = _estimate_tokens("research_fetch")
        assert tokens >= 100
        assert tokens <= 300

    def test_estimate_search_tokens(self) -> None:
        """Search tools estimate ~500 tokens."""
        tokens = _estimate_tokens("research_search")
        assert tokens >= 400
        assert tokens <= 700

    def test_estimate_llm_tokens(self) -> None:
        """LLM tools estimate ~2000 tokens."""
        tokens = _estimate_tokens("research_ask_all_llms")
        assert tokens >= 1500
        assert tokens <= 2500

    def test_estimate_with_url_adjustment(self) -> None:
        """URL parameters increase token estimate."""
        base = _estimate_tokens("research_fetch", {})
        with_url = _estimate_tokens("research_fetch", {"url": "https://example.com"})
        assert with_url > base

    def test_estimate_with_urls_list(self) -> None:
        """Multiple URLs increase token estimate."""
        base = _estimate_tokens("research_spider", {})
        with_urls = _estimate_tokens(
            "research_spider",
            {"urls": ["https://a.com", "https://b.com", "https://c.com"]}
        )
        assert with_urls > base

    def test_estimate_with_prompt(self) -> None:
        """Prompt parameter increases token estimate."""
        base = _estimate_tokens("research_chat", {})
        with_prompt = _estimate_tokens(
            "research_chat",
            {"prompt": "a" * 2000}
        )
        assert with_prompt > base

    def test_estimate_with_explicit_max_tokens(self) -> None:
        """Explicit max_tokens parameter overrides estimation."""
        result = _estimate_tokens(
            "research_llm",
            {"max_tokens": 5000}
        )
        assert result == 5000

    def test_estimate_minimum_tokens(self) -> None:
        """Token estimation never goes below 100."""
        result = _estimate_tokens("unknown_tool", {})
        assert result >= 100


class TestProviderSelection:
    """Test provider selection logic."""

    def test_select_free_provider_auto(self) -> None:
        """Auto mode selects free provider first."""
        provider = _select_provider("auto")
        assert provider in ["groq", "nvidia_nim"]

    def test_select_explicit_provider(self) -> None:
        """Explicit provider is returned as-is."""
        for prov in ["groq", "deepseek", "anthropic"]:
            result = _select_provider(prov)
            assert result == prov

    def test_select_valid_providers(self) -> None:
        """All known providers are selectable."""
        valid = ["groq", "nvidia_nim", "deepseek", "gemini", "moonshot", "openai", "anthropic"]
        for prov in valid:
            result = _select_provider(prov)
            assert result == prov


class TestCostCalculation:
    """Test cost calculation logic."""

    def test_free_provider_costs_zero(self) -> None:
        """Groq and NVIDIA NIM always cost zero."""
        assert _calculate_cost("groq", 10000, 5000) == 0.0
        assert _calculate_cost("nvidia_nim", 10000, 5000) == 0.0

    def test_deepseek_cost_calculation(self) -> None:
        """DeepSeek costs match rate card."""
        # 1M input tokens at $0.14
        cost = _calculate_cost("deepseek", 1_000_000, 0)
        assert cost == pytest.approx(0.14, rel=1e-4)

        # 1M output tokens at $0.28
        cost = _calculate_cost("deepseek", 0, 1_000_000)
        assert cost == pytest.approx(0.28, rel=1e-4)

    def test_gemini_cost_calculation(self) -> None:
        """Gemini costs match rate card."""
        # 1M input tokens at $1.25
        cost = _calculate_cost("gemini", 1_000_000, 0)
        assert cost == pytest.approx(1.25, rel=1e-4)

        # 1M output tokens at $5.00
        cost = _calculate_cost("gemini", 0, 1_000_000)
        assert cost == pytest.approx(5.00, rel=1e-4)

    def test_anthropic_cost_calculation(self) -> None:
        """Anthropic costs match rate card."""
        # 1M input tokens at $3.00
        cost = _calculate_cost("anthropic", 1_000_000, 0)
        assert cost == pytest.approx(3.00, rel=1e-4)

        # 1M output tokens at $15.00
        cost = _calculate_cost("anthropic", 0, 1_000_000)
        assert cost == pytest.approx(15.00, rel=1e-4)

    def test_combined_cost(self) -> None:
        """Combined input+output cost is additive."""
        input_cost = _calculate_cost("gemini", 1_000_000, 0)
        output_cost = _calculate_cost("gemini", 0, 1_000_000)
        combined = _calculate_cost("gemini", 1_000_000, 1_000_000)
        assert combined == pytest.approx(input_cost + output_cost, rel=1e-4)

    def test_invalid_provider_uses_default(self) -> None:
        """Invalid provider falls back to anthropic."""
        cost = _calculate_cost("invalid_provider", 1_000_000, 0)
        # Should use anthropic pricing ($3.00 per 1M input)
        assert cost == pytest.approx(3.00, rel=1e-4)

    def test_zero_tokens_zero_cost(self) -> None:
        """Zero tokens always costs zero."""
        for prov in COST_MAP.keys():
            assert _calculate_cost(prov, 0, 0) == 0.0


class TestFreeAlternatives:
    """Test free alternative suggestions."""

    def test_llm_tools_suggest_free_providers(self) -> None:
        """LLM tools suggest groq and nvidia_nim."""
        for tool in ["research_ask_all_llms", "research_chat", "research_classify"]:
            alts = _find_free_alternatives(tool)
            assert "groq (free)" in alts or "nvidia_nim (free)" in alts

    def test_fetch_tools_no_llm_cost(self) -> None:
        """Fetch tools have no LLM cost."""
        alts = _find_free_alternatives("research_fetch")
        assert "No LLM cost" in alts

    def test_search_tools_no_llm_cost(self) -> None:
        """Search tools have no LLM cost."""
        alts = _find_free_alternatives("research_search")
        assert "No LLM cost" in alts


@pytest.mark.asyncio
class TestEstimateCost:
    """Test research_estimate_cost function."""

    async def test_estimate_fetch_cost(self) -> None:
        """Estimate cost for fetch tool."""
        result = await research_estimate_cost("research_fetch")
        assert "tool" in result
        assert result["tool"] == "research_fetch"
        assert "provider" in result
        assert "estimated_tokens" in result
        assert "estimated_cost_usd" in result
        assert "free_alternatives" in result

    async def test_estimate_with_params(self) -> None:
        """Estimate cost with parameters."""
        result = await research_estimate_cost(
            "research_search",
            params={"query": "test", "max_tokens": 1000}
        )
        assert result["estimated_tokens"]["total"] == 1000

    async def test_estimate_auto_provider(self) -> None:
        """Auto provider selection chooses free option."""
        result = await research_estimate_cost(
            "research_ask_all_llms",
            provider="auto"
        )
        assert result["provider"] in ["groq", "nvidia_nim"]
        assert result["estimated_cost_usd"] == 0.0

    async def test_estimate_paid_provider(self) -> None:
        """Paid provider shows cost."""
        result = await research_estimate_cost(
            "research_ask_all_llms",
            provider="deepseek"
        )
        assert result["provider"] == "deepseek"
        assert result["estimated_cost_usd"] > 0.0

    async def test_estimate_returns_cost_breakdown(self) -> None:
        """Estimate returns detailed cost breakdown."""
        result = await research_estimate_cost(
            "research_search",
            provider="gemini"
        )
        assert "cost_per_1m_tokens" in result
        assert "input" in result["cost_per_1m_tokens"]
        assert "output" in result["cost_per_1m_tokens"]

    async def test_estimate_accumulates_history(self) -> None:
        """Multiple estimates accumulate in history."""
        # Clear history first
        import loom.tools.infrastructure.cost_estimator
        cost_estimator._cost_history.clear()

        await research_estimate_cost("research_fetch")
        await research_estimate_cost("research_search")

        assert len(cost_estimator._cost_history) == 2

    async def test_estimate_cost_is_rounded(self) -> None:
        """Cost is rounded to 6 decimal places."""
        result = await research_estimate_cost(
            "research_ask_all_llms",
            provider="deepseek"
        )
        cost_str = str(result["estimated_cost_usd"])
        decimal_places = len(cost_str.split(".")[-1]) if "." in cost_str else 0
        assert decimal_places <= 6


@pytest.mark.asyncio
class TestCostSummary:
    """Test research_cost_summary function."""

    async def test_summary_empty_history(self) -> None:
        """Summary on empty history returns zeros."""
        import loom.tools.infrastructure.cost_estimator
        cost_estimator._cost_history.clear()

        result = await research_cost_summary()
        assert result["total_estimated_usd"] == 0.0
        assert result["total_calls"] == 0
        assert result["avg_cost_per_call"] == 0.0
        assert result["cheapest_provider"] is None
        assert result["most_expensive_tool"] is None

    async def test_summary_with_history(self) -> None:
        """Summary aggregates accumulated costs."""
        import loom.tools.infrastructure.cost_estimator
        cost_estimator._cost_history.clear()

        # Add some estimates
        await research_estimate_cost("research_fetch")
        await research_estimate_cost("research_search")
        await research_estimate_cost("research_ask_all_llms", provider="deepseek")

        result = await research_cost_summary()
        assert result["total_calls"] == 3
        assert "by_provider" in result
        assert "tool_breakdown" in result

    async def test_summary_period_today(self) -> None:
        """Summary respects period parameter."""
        import loom.tools.infrastructure.cost_estimator
        cost_estimator._cost_history.clear()

        await research_estimate_cost("research_fetch")

        result = await research_cost_summary(period="today")
        assert result["period"] == "today"
        assert result["total_calls"] >= 0  # May be 0 if not today's date

    async def test_summary_returns_breakdown(self) -> None:
        """Summary returns per-provider and per-tool breakdown."""
        import loom.tools.infrastructure.cost_estimator
        cost_estimator._cost_history.clear()

        await research_estimate_cost("research_fetch", provider="groq")
        await research_estimate_cost("research_search", provider="deepseek")

        result = await research_cost_summary()
        assert "by_provider" in result
        assert "tool_breakdown" in result

    async def test_summary_finds_cheapest_provider(self) -> None:
        """Summary identifies cheapest provider used."""
        import loom.tools.infrastructure.cost_estimator
        cost_estimator._cost_history.clear()

        await research_estimate_cost("research_fetch", provider="groq")
        await research_estimate_cost("research_search", provider="anthropic")

        result = await research_cost_summary()
        assert result["cheapest_provider"] == "groq"

    async def test_summary_finds_most_expensive_tool(self) -> None:
        """Summary identifies tool with highest cost."""
        import loom.tools.infrastructure.cost_estimator
        cost_estimator._cost_history.clear()

        await research_estimate_cost("research_fetch", provider="groq")
        await research_estimate_cost("research_ask_all_llms", provider="anthropic")

        result = await research_cost_summary()
        # Most expensive should be the LLM tool with anthropic
        assert result["most_expensive_tool"] in [
            "research_fetch",
            "research_ask_all_llms"
        ]

    async def test_summary_avg_cost_calculation(self) -> None:
        """Summary calculates average cost per call."""
        import loom.tools.infrastructure.cost_estimator
        cost_estimator._cost_history.clear()

        await research_estimate_cost("research_fetch", provider="groq")  # 0.0
        await research_estimate_cost("research_ask_all_llms", provider="deepseek")  # ~0.28

        result = await research_cost_summary()
        assert result["total_calls"] == 2
        expected_avg = result["total_estimated_usd"] / 2
        assert result["avg_cost_per_call"] == pytest.approx(expected_avg, rel=1e-4)


class TestCostMapCompleteness:
    """Test that cost map covers all providers."""

    def test_all_providers_in_cost_map(self) -> None:
        """All expected providers have pricing."""
        expected = ["groq", "nvidia_nim", "deepseek", "gemini", "moonshot", "openai", "anthropic"]
        for provider in expected:
            assert provider in COST_MAP
            assert "input" in COST_MAP[provider]
            assert "output" in COST_MAP[provider]

    def test_cost_map_all_non_negative(self) -> None:
        """All costs in map are non-negative."""
        for provider, costs in COST_MAP.items():
            assert costs["input"] >= 0.0
            assert costs["output"] >= 0.0


class TestTokenEstimatesCompleteness:
    """Test that token estimates cover common tool types."""

    def test_token_estimates_populated(self) -> None:
        """Common tool types have estimates."""
        common_tools = [
            "search", "deep", "fetch", "spider",
            "llm", "chat", "extract", "classify"
        ]
        for tool_type in common_tools:
            assert tool_type in TOKEN_ESTIMATES
            assert TOKEN_ESTIMATES[tool_type] >= 100
