"""Tests for strategy_ab_test tool."""

from __future__ import annotations

import pytest
from loom.tools.strategy_ab_test import (
    research_ab_test_design,
    research_ab_test_analyze,
    _normal_cdf,
    _two_tailed_p_value,
)


class TestNormalCDF:
    """Tests for normal CDF approximation."""

    def test_cdf_at_zero(self):
        """CDF at z=0 should be ~0.5."""
        assert 0.49 < _normal_cdf(0) < 0.51

    def test_cdf_positive(self):
        """CDF increases with z."""
        cdf_1 = _normal_cdf(1.0)
        cdf_2 = _normal_cdf(2.0)
        assert cdf_1 < cdf_2

    def test_cdf_negative(self):
        """CDF is symmetric for negative z."""
        cdf_pos = _normal_cdf(1.0)
        cdf_neg = _normal_cdf(-1.0)
        assert abs(cdf_pos - (1 - cdf_neg)) < 0.001

    def test_cdf_at_1_96(self):
        """CDF at z=1.96 should be ~0.975 (95% CI)."""
        cdf = _normal_cdf(1.96)
        assert 0.974 < cdf < 0.976


class TestTwoTailedPValue:
    """Tests for two-tailed p-value calculation."""

    def test_p_value_zero(self):
        """P-value at z=0 should be 1.0."""
        p = _two_tailed_p_value(0.0)
        assert 0.99 < p <= 1.0

    def test_p_value_decreases(self):
        """P-value decreases as |z| increases."""
        p_1 = _two_tailed_p_value(1.0)
        p_2 = _two_tailed_p_value(2.0)
        assert p_1 > p_2

    def test_p_value_at_1_96(self):
        """P-value at z=1.96 should be ~0.05."""
        p = _two_tailed_p_value(1.96)
        assert 0.048 < p < 0.052


class TestABTestDesign:
    """Tests for AB test design."""

    @pytest.mark.asyncio
    async def test_design_basic(self):
        """Basic design should return valid structure."""
        result = await research_ab_test_design(
            strategy_a="strategy_a",
            strategy_b="strategy_b",
            sample_size=30,
            metric="compliance_rate",
        )
        assert "design" in result
        assert result["design"]["strategy_a"] == "strategy_a"
        assert result["design"]["strategy_b"] == "strategy_b"
        assert result["design"]["sample_size_per_arm"] == 30
        assert result["design"]["total_trials"] == 60

    @pytest.mark.asyncio
    async def test_design_metrics(self):
        """Design should handle all valid metrics."""
        for metric in ["compliance_rate", "response_length", "specificity", "stealth_score"]:
            result = await research_ab_test_design(
                strategy_a="a",
                strategy_b="b",
                sample_size=20,
                metric=metric,
            )
            assert "design" in result
            assert result["design"]["metric"] == metric

    @pytest.mark.asyncio
    async def test_design_invalid_metric(self):
        """Invalid metric should return error."""
        result = await research_ab_test_design(
            strategy_a="a",
            strategy_b="b",
            metric="invalid_metric",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_design_same_strategy(self):
        """Same strategy should return error."""
        result = await research_ab_test_design(
            strategy_a="same",
            strategy_b="same",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_design_empty_strategy(self):
        """Empty strategy name should return error."""
        result = await research_ab_test_design(
            strategy_a="",
            strategy_b="b",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_design_sample_size_bounds(self):
        """Sample size should be bounded."""
        # Too small
        result = await research_ab_test_design(
            strategy_a="a",
            strategy_b="b",
            sample_size=2,
        )
        assert "error" in result

        # Too large
        result = await research_ab_test_design(
            strategy_a="a",
            strategy_b="b",
            sample_size=1000,
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_design_power_calculation(self):
        """Power should increase with sample size."""
        design_small = await research_ab_test_design(
            strategy_a="a",
            strategy_b="b",
            sample_size=10,
        )
        design_large = await research_ab_test_design(
            strategy_a="a",
            strategy_b="b",
            sample_size=100,
        )
        power_small = design_small["design"]["expected_power"]
        power_large = design_large["design"]["expected_power"]
        assert power_small < power_large

    @pytest.mark.asyncio
    async def test_design_effect_size(self):
        """Minimum detectable effect size should decrease with sample size."""
        design_small = await research_ab_test_design(
            strategy_a="a",
            strategy_b="b",
            sample_size=10,
        )
        design_large = await research_ab_test_design(
            strategy_a="a",
            strategy_b="b",
            sample_size=100,
        )
        mde_small = design_small["design"]["min_detectable_effect"]
        mde_large = design_large["design"]["min_detectable_effect"]
        assert mde_small > mde_large


class TestABTestAnalyze:
    """Tests for AB test analysis."""

    @pytest.mark.asyncio
    async def test_analyze_basic(self):
        """Basic analysis should return valid structure."""
        results_a = [0.8, 0.75, 0.9, 0.85, 0.88]
        results_b = [0.7, 0.72, 0.68, 0.75, 0.7]

        result = await research_ab_test_analyze(
            results_a=results_a,
            results_b=results_b,
            metric="compliance_rate",
        )

        assert "strategy_a_mean" in result
        assert "strategy_b_mean" in result
        assert "difference" in result
        assert "p_value" in result
        assert "significant" in result
        assert "effect_size_cohens_d" in result
        assert "confidence_interval_95" in result
        assert "winner" in result
        assert "recommendation" in result

    @pytest.mark.asyncio
    async def test_analyze_empty_results(self):
        """Empty results should return error."""
        result = await research_ab_test_analyze(results_a=[], results_b=[1, 2])
        assert "error" in result

        result = await research_ab_test_analyze(results_a=[1, 2], results_b=[])
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_non_numeric(self):
        """Non-numeric results should return error."""
        result = await research_ab_test_analyze(
            results_a=["a", "b"],
            results_b=[1, 2],
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_invalid_metric(self):
        """Invalid metric should return error."""
        result = await research_ab_test_analyze(
            results_a=[1, 2],
            results_b=[1, 2],
            metric="invalid",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_means_calculation(self):
        """Means should be calculated correctly."""
        results_a = [0.8, 0.8]
        results_b = [0.6, 0.6]

        result = await research_ab_test_analyze(results_a, results_b)

        assert abs(result["strategy_a_mean"] - 0.8) < 0.001
        assert abs(result["strategy_b_mean"] - 0.6) < 0.001
        assert abs(result["difference"] - 0.2) < 0.001

    @pytest.mark.asyncio
    async def test_analyze_no_difference(self):
        """Identical distributions should show no significant difference."""
        results = [0.5, 0.51, 0.49, 0.5, 0.5]

        result = await research_ab_test_analyze(results, results)

        assert result["significant"] is False
        assert result["winner"] == "inconclusive"

    @pytest.mark.asyncio
    async def test_analyze_large_difference(self):
        """Large difference should be significant."""
        results_a = [0.9, 0.95, 0.88, 0.92, 0.91, 0.89, 0.93, 0.94, 0.90, 0.92]
        results_b = [0.1, 0.15, 0.08, 0.12, 0.11, 0.09, 0.13, 0.14, 0.10, 0.12]

        result = await research_ab_test_analyze(results_a, results_b)

        assert result["significant"] is True
        assert result["winner"] == "strategy_a"
        assert abs(result["effect_size_cohens_d"]) > 2.0  # Large effect size

    @pytest.mark.asyncio
    async def test_analyze_confidence_interval(self):
        """Confidence interval should contain difference."""
        results_a = [0.8, 0.75, 0.9]
        results_b = [0.7, 0.72, 0.68]

        result = await research_ab_test_analyze(results_a, results_b)

        ci = result["confidence_interval_95"]
        diff = result["difference"]

        assert ci["lower"] <= diff <= ci["upper"]

    @pytest.mark.asyncio
    async def test_analyze_sample_sizes_recorded(self):
        """Sample sizes should be recorded."""
        results_a = [1, 2, 3, 4, 5]
        results_b = [1, 2]

        result = await research_ab_test_analyze(results_a, results_b)

        assert result["sample_sizes"]["strategy_a"] == 5
        assert result["sample_sizes"]["strategy_b"] == 2

    @pytest.mark.asyncio
    async def test_analyze_recommendation_logic(self):
        """Recommendation should vary based on effect size."""
        # Small effect (not significant)
        results_a = [0.51, 0.52, 0.50, 0.51, 0.50]
        results_b = [0.50, 0.50, 0.50, 0.50, 0.50]
        result = await research_ab_test_analyze(results_a, results_b)
        if not result["significant"]:
            assert "Not enough evidence" in result["recommendation"]

        # Large effect (significant)
        results_a = [0.9, 0.95, 0.88, 0.92, 0.91] * 3
        results_b = [0.1, 0.15, 0.08, 0.12, 0.11] * 3
        result = await research_ab_test_analyze(results_a, results_b)
        if result["significant"] and abs(result["effect_size_cohens_d"]) > 0.5:
            assert "large effect" in result["recommendation"].lower()

    @pytest.mark.asyncio
    async def test_analyze_single_value_variance(self):
        """Handling single value should work (zero variance case)."""
        results_a = [0.8]
        results_b = [0.6]

        result = await research_ab_test_analyze(results_a, results_b)

        # Should not crash and provide valid output
        assert "strategy_a_mean" in result
        assert "strategy_b_mean" in result
