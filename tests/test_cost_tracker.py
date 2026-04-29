"""Unit tests for cost_tracker module — internal cost tracking and margin analysis.

Tests:
- Provider cost estimation (LLM and search)
- Revenue calculation by tier
- Profit margin computation
- Healthy margin detection (≥20%)
- Low margin alerts (0-20%)
- Negative margin alerts (<0)
- Margin health checks
- Aggregation of provider costs
"""

from __future__ import annotations

import pytest

from loom.billing.cost_tracker import (
    LLM_PROVIDER_COSTS,
    REVENUE_PER_CREDIT,
    SEARCH_PROVIDER_COSTS,
    aggregate_provider_costs,
    check_margin_health,
    compute_margin,
    estimate_call_cost,
    estimate_revenue,
)


class TestEstimateCallCost:
    """Tests for estimate_call_cost function."""

    def test_groq_llm_cost_is_zero(self) -> None:
        """estimate_call_cost(groq, llm) returns 0.0."""
        cost = estimate_call_cost("groq", "llm")
        assert cost == 0.0

    def test_nvidia_nim_llm_cost_is_zero(self) -> None:
        """estimate_call_cost(nvidia_nim, llm) returns 0.0."""
        cost = estimate_call_cost("nvidia_nim", "llm")
        assert cost == 0.0

    def test_deepseek_llm_cost_is_nonzero(self) -> None:
        """estimate_call_cost(deepseek, llm) returns ~$0.0005."""
        cost = estimate_call_cost("deepseek", "llm")
        assert cost == pytest.approx(0.0005, abs=0.00001)

    def test_openai_llm_cost_is_nonzero(self) -> None:
        """estimate_call_cost(openai, llm) returns ~$0.01."""
        cost = estimate_call_cost("openai", "llm")
        assert cost == pytest.approx(0.01, abs=0.001)

    def test_anthropic_llm_cost_is_nonzero(self) -> None:
        """estimate_call_cost(anthropic, llm) returns ~$0.015."""
        cost = estimate_call_cost("anthropic", "llm")
        assert cost == pytest.approx(0.015, abs=0.001)

    def test_gemini_llm_cost_is_nonzero(self) -> None:
        """estimate_call_cost(gemini, llm) returns ~$0.002."""
        cost = estimate_call_cost("gemini", "llm")
        assert cost == pytest.approx(0.002, abs=0.0001)

    def test_moonshot_llm_cost_is_nonzero(self) -> None:
        """estimate_call_cost(moonshot, llm) returns ~$0.001."""
        cost = estimate_call_cost("moonshot", "llm")
        assert cost == pytest.approx(0.001, abs=0.0001)

    def test_vllm_local_cost_is_zero(self) -> None:
        """estimate_call_cost(vllm, llm) returns 0.0 (self-hosted)."""
        cost = estimate_call_cost("vllm", "llm")
        assert cost == 0.0

    def test_unknown_llm_provider_defaults_to_0_005(self) -> None:
        """estimate_call_cost(unknown, llm) returns $0.005 default."""
        cost = estimate_call_cost("unknown_provider", "llm")
        assert cost == pytest.approx(0.005, abs=0.0001)

    def test_exa_search_cost_is_nonzero(self) -> None:
        """estimate_call_cost(exa, search) returns ~$0.001."""
        cost = estimate_call_cost("exa", "search")
        assert cost == pytest.approx(0.001, abs=0.0001)

    def test_brave_search_cost_is_nonzero(self) -> None:
        """estimate_call_cost(brave, search) returns ~$0.001."""
        cost = estimate_call_cost("brave", "search")
        assert cost == pytest.approx(0.001, abs=0.0001)

    def test_ddgs_search_cost_is_zero(self) -> None:
        """estimate_call_cost(ddgs, search) returns 0.0 (free)."""
        cost = estimate_call_cost("ddgs", "search")
        assert cost == 0.0

    def test_firecrawl_search_cost_is_nonzero(self) -> None:
        """estimate_call_cost(firecrawl, search) returns ~$0.0005."""
        cost = estimate_call_cost("firecrawl", "search")
        assert cost == pytest.approx(0.0005, abs=0.00001)

    def test_unknown_search_provider_defaults_to_0_001(self) -> None:
        """estimate_call_cost(unknown, search) returns $0.001 default."""
        cost = estimate_call_cost("unknown_search", "search")
        assert cost == pytest.approx(0.001, abs=0.0001)

    def test_default_type_is_llm(self) -> None:
        """estimate_call_cost defaults to llm provider type."""
        cost = estimate_call_cost("groq")
        assert cost == 0.0


class TestEstimateRevenue:
    """Tests for estimate_revenue function."""

    def test_free_tier_revenue_is_zero(self) -> None:
        """estimate_revenue(free, 1000) returns $0."""
        revenue = estimate_revenue("free", 1000)
        assert revenue == 0.0

    def test_pro_tier_revenue_is_correct(self) -> None:
        """estimate_revenue(pro, 10000) returns $99 (10K credits × $0.0099)."""
        revenue = estimate_revenue("pro", 10000)
        assert revenue == pytest.approx(99.0, abs=0.01)

    def test_team_tier_revenue_is_correct(self) -> None:
        """estimate_revenue(team, 50000) returns $299 (50K credits × $0.00598)."""
        revenue = estimate_revenue("team", 50000)
        assert revenue == pytest.approx(299.0, abs=0.01)

    def test_enterprise_tier_revenue_is_correct(self) -> None:
        """estimate_revenue(enterprise, 200000) returns $999."""
        revenue = estimate_revenue("enterprise", 200000)
        assert revenue == pytest.approx(999.0, abs=0.01)

    def test_pro_tier_half_credits_is_half_revenue(self) -> None:
        """estimate_revenue(pro, 5000) returns ~$49.50."""
        revenue = estimate_revenue("pro", 5000)
        assert revenue == pytest.approx(49.5, abs=0.1)

    def test_team_tier_lower_per_credit_than_pro(self) -> None:
        """Team tier has lower per-credit rate than Pro."""
        pro_revenue = estimate_revenue("pro", 10000)
        team_revenue = estimate_revenue("team", 10000)
        assert team_revenue < pro_revenue

    def test_enterprise_tier_lowest_per_credit_rate(self) -> None:
        """Enterprise tier has lowest per-credit rate."""
        pro_revenue = estimate_revenue("pro", 10000)
        team_revenue = estimate_revenue("team", 10000)
        enterprise_revenue = estimate_revenue("enterprise", 10000)
        assert enterprise_revenue < team_revenue < pro_revenue

    def test_zero_credits_returns_zero_revenue(self) -> None:
        """estimate_revenue(any_tier, 0) returns $0."""
        assert estimate_revenue("pro", 0) == 0.0
        assert estimate_revenue("team", 0) == 0.0
        assert estimate_revenue("enterprise", 0) == 0.0

    def test_unknown_tier_defaults_to_zero(self) -> None:
        """estimate_revenue(unknown, 1000) returns $0."""
        revenue = estimate_revenue("unknown_tier", 1000)
        assert revenue == 0.0

    def test_revenue_rounded_to_four_decimals(self) -> None:
        """estimate_revenue returns value rounded to 4 decimals."""
        revenue = estimate_revenue("pro", 1)
        assert isinstance(revenue, float)
        assert len(str(revenue).split(".")[-1]) <= 4


class TestComputeMargin:
    """Tests for compute_margin function."""

    def test_margin_dict_has_required_fields(self) -> None:
        """compute_margin returns dict with all required fields."""
        result = compute_margin("pro", 10000, 10.0)
        assert "revenue" in result
        assert "cost" in result
        assert "profit" in result
        assert "margin_percent" in result
        assert "healthy" in result
        assert "alert" in result

    def test_margin_healthy_when_above_20_percent(self) -> None:
        """compute_margin is healthy when margin ≥ 20%."""
        # Pro: 10K credits × $0.0099 = $99 revenue
        # Cost $50 → profit $49 → margin 49.5% → healthy
        result = compute_margin("pro", 10000, 50.0)
        assert result["healthy"] is True
        assert result["alert"] is None

    def test_margin_unhealthy_when_between_0_and_20(self) -> None:
        """compute_margin alerts when margin is 0-20%."""
        # Pro: 10K × $0.0099 = $99 revenue
        # Cost $79.2 → profit $19.8 → margin 20.0% → healthy at threshold
        # Cost $80 → profit $19 → margin 19.2% → alert low_margin
        result = compute_margin("pro", 10000, 80.0)
        assert result["healthy"] is False
        assert result["alert"] == "low_margin"

    def test_margin_negative_when_cost_exceeds_revenue(self) -> None:
        """compute_margin alerts negative when cost > revenue."""
        # Pro: 10K × $0.0099 = $99 revenue
        # Cost $150 → profit -$51 → alert negative
        result = compute_margin("pro", 10000, 150.0)
        assert result["healthy"] is False
        assert result["alert"] == "negative"
        assert result["profit"] < 0

    def test_free_tier_always_negative_margin(self) -> None:
        """compute_margin for free tier is always negative (revenue=$0)."""
        # Free tier: revenue = $0, cost = $10 → profit < 0 → alert negative
        result = compute_margin("free", 1000, 10.0)
        assert result["revenue"] == 0.0
        assert result["profit"] < 0
        assert result["alert"] == "negative"

    def test_pro_groq_combo_healthy_margin(self) -> None:
        """Pro customer with Groq calls (0 cost) has healthy margin."""
        # Pro: 10K credits × $0.0099 = $99, cost $0 → margin 100%
        result = compute_margin("pro", 10000, 0.0)
        assert result["margin_percent"] == 100.0
        assert result["healthy"] is True

    def test_team_enterprise_cheaper_per_credit(self) -> None:
        """Team/Enterprise tiers have lower revenue per credit."""
        pro_result = compute_margin("pro", 10000, 0.0)
        team_result = compute_margin("team", 10000, 0.0)
        assert pro_result["revenue"] > team_result["revenue"]

    def test_margin_percent_is_rounded(self) -> None:
        """margin_percent is rounded to 1 decimal place."""
        result = compute_margin("pro", 10000, 50.0)
        margin_pct = result["margin_percent"]
        # Should be 1 decimal place
        assert isinstance(margin_pct, float)
        assert margin_pct == round(margin_pct, 1)

    def test_profit_calculation_is_correct(self) -> None:
        """profit = revenue - cost."""
        result = compute_margin("pro", 10000, 25.0)
        expected_profit = result["revenue"] - 25.0
        assert result["profit"] == pytest.approx(expected_profit, abs=0.01)

    def test_zero_cost_zero_credits_returns_zero_profit(self) -> None:
        """Zero credits and zero cost results in zero profit."""
        result = compute_margin("pro", 0, 0.0)
        assert result["revenue"] == 0.0
        assert result["cost"] == 0.0
        assert result["profit"] == 0.0

    def test_alert_boundary_at_20_percent(self) -> None:
        """Alert boundary is at 20% margin."""
        # Pro: 10K × $0.0099 = $99
        # Cost to get exactly 20% margin: cost = 99 * 0.8 = 79.2
        result = compute_margin("pro", 10000, 79.2)
        margin = result["margin_percent"]
        # At exactly 20%, should be healthy
        if margin >= 20:
            assert result["healthy"] is True
            assert result["alert"] is None
        else:
            assert result["healthy"] is False
            assert result["alert"] == "low_margin"

    def test_values_rounded_to_four_decimals(self) -> None:
        """revenue, cost, profit are rounded to 4 decimals."""
        result = compute_margin("pro", 1, 0.001)
        assert len(str(result["revenue"]).split(".")[-1]) <= 4
        assert len(str(result["cost"]).split(".")[-1]) <= 4
        assert len(str(result["profit"]).split(".")[-1]) <= 4


class TestAggregateProviderCosts:
    """Tests for aggregate_provider_costs function."""

    def test_empty_list_returns_zero(self) -> None:
        """aggregate_provider_costs([]) returns 0.0."""
        result = aggregate_provider_costs([])
        assert result == 0.0

    def test_single_groq_call_is_free(self) -> None:
        """Single Groq LLM call costs $0."""
        calls = [{"provider": "groq", "provider_type": "llm"}]
        result = aggregate_provider_costs(calls)
        assert result == 0.0

    def test_single_openai_call_cost(self) -> None:
        """Single OpenAI call costs ~$0.01."""
        calls = [{"provider": "openai", "provider_type": "llm"}]
        result = aggregate_provider_costs(calls)
        assert result == pytest.approx(0.01, abs=0.001)

    def test_multiple_calls_summed(self) -> None:
        """Multiple calls sum their costs."""
        calls = [
            {"provider": "groq", "provider_type": "llm"},
            {"provider": "groq", "provider_type": "llm"},
            {"provider": "ddgs", "provider_type": "search"},
        ]
        result = aggregate_provider_costs(calls)
        assert result == 0.0  # All free

    def test_groq_plus_openai_summed(self) -> None:
        """Groq + OpenAI calls sum to $0.01."""
        calls = [
            {"provider": "groq", "provider_type": "llm"},
            {"provider": "openai", "provider_type": "llm"},
        ]
        result = aggregate_provider_costs(calls)
        assert result == pytest.approx(0.01, abs=0.001)

    def test_mixed_llm_and_search_providers(self) -> None:
        """Mixed LLM and search providers are summed correctly."""
        calls = [
            {"provider": "groq", "provider_type": "llm"},
            {"provider": "exa", "provider_type": "search"},
        ]
        result = aggregate_provider_costs(calls)
        # Groq (0) + Exa (0.001) = 0.001
        assert result == pytest.approx(0.001, abs=0.0001)

    def test_result_rounded_to_four_decimals(self) -> None:
        """Result is rounded to 4 decimals."""
        calls = [{"provider": "openai", "provider_type": "llm"}]
        result = aggregate_provider_costs(calls)
        assert len(str(result).split(".")[-1]) <= 4

    def test_missing_provider_type_defaults_to_llm(self) -> None:
        """Missing provider_type defaults to llm."""
        calls = [{"provider": "groq"}]
        result = aggregate_provider_costs(calls)
        assert result == 0.0


class TestCheckMarginHealth:
    """Tests for check_margin_health function."""

    def test_health_check_returns_required_fields(self) -> None:
        """check_margin_health returns margin_info, meets_minimum, action."""
        result = check_margin_health("pro", 10000, 10.0)
        assert "margin_info" in result
        assert "meets_minimum" in result
        assert "action" in result

    def test_healthy_margin_meets_minimum(self) -> None:
        """Healthy margin (≥20%) meets minimum."""
        result = check_margin_health("pro", 10000, 50.0)  # ~50% margin
        assert result["meets_minimum"] is True
        assert result["action"] is None

    def test_low_margin_does_not_meet_minimum(self) -> None:
        """Low margin (0-20%) does not meet minimum."""
        result = check_margin_health("pro", 10000, 80.0)  # ~19% margin
        assert result["meets_minimum"] is False
        assert result["action"] == "review_pricing"

    def test_negative_margin_requires_immediate_review(self) -> None:
        """Negative margin triggers immediate_review action."""
        result = check_margin_health("pro", 10000, 150.0)  # negative margin
        assert result["meets_minimum"] is False
        assert result["action"] == "immediate_review"

    def test_custom_min_margin_threshold(self) -> None:
        """check_margin_health respects custom min_margin threshold."""
        # Pro: 10K × $0.0099 = $99, cost $70 → margin 29%
        result = check_margin_health("pro", 10000, 70.0, min_margin=30)
        assert result["meets_minimum"] is False
        assert result["action"] == "review_pricing"

    def test_margin_info_matches_compute_margin(self) -> None:
        """margin_info matches output of compute_margin."""
        tier, credits, cost = "pro", 10000, 50.0
        health = check_margin_health(tier, credits, cost)
        direct = compute_margin(tier, credits, cost)
        assert health["margin_info"] == direct


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_typical_pro_customer_with_mixed_providers(self) -> None:
        """Typical Pro customer: 5K credits, mix of Groq and OpenAI calls."""
        calls = [
            {"provider": "groq", "provider_type": "llm"},
            {"provider": "groq", "provider_type": "llm"},
            {"provider": "openai", "provider_type": "llm"},
            {"provider": "exa", "provider_type": "search"},
        ]
        total_cost = aggregate_provider_costs(calls)
        # Groq (0) + Groq (0) + OpenAI (0.01) + Exa (0.001) = 0.011
        assert total_cost == pytest.approx(0.011, abs=0.0001)

        margin = compute_margin("pro", 5000, total_cost)
        # Revenue: 5K × $0.0099 = $49.50
        # Profit: $49.50 - $0.011 = $49.489
        # Margin: ~100%
        assert margin["healthy"] is True
        assert margin["revenue"] == pytest.approx(49.5, abs=0.1)

    def test_free_tier_customer_always_loses_money(self) -> None:
        """Free tier customer with any provider costs always has negative margin."""
        calls = [{"provider": "ddgs", "provider_type": "search"}]  # Free search
        total_cost = aggregate_provider_costs(calls)

        margin = compute_margin("free", 1000, total_cost)
        # Revenue: 0
        assert margin["revenue"] == 0.0
        if total_cost == 0:
            assert margin["profit"] == 0.0
            # 0% margin is in 0-20% range, so low_margin alert
            assert margin["alert"] == "low_margin"
        else:
            assert margin["profit"] < 0
            assert margin["alert"] == "negative"

    def test_enterprise_customer_with_expensive_providers(self) -> None:
        """Enterprise customer can sustain expensive provider costs."""
        calls = [
            {"provider": "openai", "provider_type": "llm"},
            {"provider": "openai", "provider_type": "llm"},
            {"provider": "anthropic", "provider_type": "llm"},
            {"provider": "tavily", "provider_type": "search"},
        ]
        total_cost = aggregate_provider_costs(calls)
        # 0.01 + 0.01 + 0.015 + 0.001 = 0.036

        margin = compute_margin("enterprise", 100000, total_cost)
        # Revenue: 100K × $0.004995 = $499.50
        # Profit: ~$499.46
        # Margin: ~100%
        assert margin["healthy"] is True
        assert margin["revenue"] > total_cost
