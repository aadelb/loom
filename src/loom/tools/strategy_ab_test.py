"""Strategy A/B Testing: statistical comparison of reframing strategies (pure Python)."""

from __future__ import annotations

import logging
import math

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.strategy_ab_test")

METRICS = {"compliance_rate", "response_length", "specificity", "stealth_score"}


def _cdf(z: float) -> float:
    """Standard normal CDF via tanh approximation."""
    return 0.5 * (1.0 + math.tanh(math.sqrt(2 / math.pi) * (z + 0.044715 * z**3)))


@handle_tool_errors("research_ab_test_design")
async def research_ab_test_design(strategy_a: str, strategy_b: str, sample_size: int = 30, metric: str = "compliance_rate") -> dict:
    """Design A/B test with power and minimum detectable effect."""
    try:
        if not strategy_a or not strategy_b or strategy_a == strategy_b:
            return {"error": "Both unique strategy names required"}
        if metric not in METRICS:
            return {"error": f"Metric must be one of: {', '.join(METRICS)}"}
        if not (5 <= sample_size <= 500):
            return {"error": "Sample size must be [5, 500]"}

        n = sample_size
        z_alpha = 1.96  # Two-tailed critical value
        mde = z_alpha * math.sqrt(2.0 / n)  # Minimum detectable effect
        power = _cdf(z_alpha - (0.5 * math.sqrt(n / 2.0)))  # Power for d=0.5

        logger.info("ab_test_design a=%s b=%s metric=%s n=%d", strategy_a, strategy_b, metric, n)
        return {"design": {"strategy_a": strategy_a, "strategy_b": strategy_b, "sample_size_per_arm": n, "total_trials": n * 2, "metric": metric, "expected_power": round(power, 3), "min_detectable_effect": round(mde, 3), "significance_level": 0.05}}
    except Exception as exc:
        logger.error("ab_test_design_error: %s", exc, exc_info=True)
        return {
            "error": str(exc),
            "tool": "research_ab_test_design",
        }


@handle_tool_errors("research_ab_test_analyze")
async def research_ab_test_analyze(results_a: list[float], results_b: list[float], metric: str = "compliance_rate") -> dict:
    """Analyze A/B test results with statistical significance and Cohen's d effect size."""
    try:
        if not results_a or not results_b:
            return {"error": "Both result sets required"}
        if metric not in METRICS:
            return {"error": f"Metric must be one of: {', '.join(METRICS)}"}

        try:
            results_a, results_b = [float(x) for x in results_a], [float(x) for x in results_b]
        except (ValueError, TypeError):
            return {"error": "All results must be numeric"}

        n_a, n_b = len(results_a), len(results_b)
        mean_a, mean_b = sum(results_a) / n_a, sum(results_b) / n_b
        var_a = sum((x - mean_a) ** 2 for x in results_a) / max(1, n_a - 1) if n_a > 1 else 0
        var_b = sum((x - mean_b) ** 2 for x in results_b) / max(1, n_b - 1) if n_b > 1 else 0

        se = math.sqrt(var_a / n_a + var_b / n_b)
        z_stat = (mean_a - mean_b) / se if se > 0 else 0.0
        p_value = 2.0 * (1.0 - _cdf(abs(z_stat)))
        pooled_std = math.sqrt((var_a + var_b) / 2) if (var_a + var_b) > 0 else 1.0
        cohens_d = (mean_a - mean_b) / pooled_std if pooled_std > 0 else 0.0

        diff = mean_a - mean_b
        margin = 1.96 * se
        sig = p_value < 0.05
        winner = ("strategy_a" if mean_a > mean_b else "strategy_b") if sig else "inconclusive"
        rec = ("Not enough evidence; increase sample size" if not sig else "Significant but small effect" if abs(cohens_d) < 0.2 else "Significant small-medium effect; consider winner" if abs(cohens_d) < 0.5 else "Significant large effect; recommend winner")

        logger.info("ab_test_analyze metric=%s winner=%s p=%.4f d=%.3f", metric, winner, p_value, cohens_d)
        return {"strategy_a_mean": round(mean_a, 4), "strategy_b_mean": round(mean_b, 4), "difference": round(diff, 4), "p_value": round(p_value, 6), "significant": sig, "effect_size_cohens_d": round(cohens_d, 3), "confidence_interval_95": {"lower": round(diff - margin, 4), "upper": round(diff + margin, 4)}, "winner": winner, "recommendation": rec, "sample_sizes": {"strategy_a": n_a, "strategy_b": n_b}}
    except Exception as exc:
        logger.error("ab_test_analyze_error: %s", exc, exc_info=True)
        return {
            "error": str(exc),
            "tool": "research_ab_test_analyze",
        }
