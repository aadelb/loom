"""Strategy A/B Testing tool for comparing reframing strategies head-to-head.

Provides experimental design and statistical analysis for strategy comparison
without external dependencies (pure Python statistics).
"""

from __future__ import annotations

import logging
import math
from typing import Literal

logger = logging.getLogger("loom.tools.strategy_ab_test")

# Constants
METRICS = {"compliance_rate", "response_length", "specificity", "stealth_score"}
MIN_SAMPLE_SIZE = 5
MAX_SAMPLE_SIZE = 500
SIGNIFICANCE_LEVEL = 0.05


def _normal_cdf(z: float) -> float:
    """Approximate standard normal CDF using error function.

    Args:
        z: z-score value

    Returns:
        Approximate CDF value P(Z <= z)
    """
    # Abramowitz and Stegun approximation
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1 if z >= 0 else -1
    z_abs = abs(z)

    t = 1.0 / (1.0 + p * z_abs)
    t2 = t * t
    t3 = t2 * t
    t4 = t3 * t
    t5 = t4 * t

    y = 1.0 - (a1 * t + a2 * t2 + a3 * t3 + a4 * t4 + a5 * t5) * math.exp(-z_abs * z_abs)

    return 0.5 * (1.0 + sign * y)


def _two_tailed_p_value(z: float) -> float:
    """Calculate two-tailed p-value from z-score.

    Args:
        z: z-score (absolute value)

    Returns:
        Two-tailed p-value
    """
    z_abs = abs(z)
    cdf = _normal_cdf(z_abs)
    return 2.0 * (1.0 - cdf)


async def research_ab_test_design(
    strategy_a: str,
    strategy_b: str,
    sample_size: int = 30,
    metric: str = "compliance_rate",
) -> dict:
    """Design an A/B test comparing two strategies.

    Args:
        strategy_a: Name of first strategy
        strategy_b: Name of second strategy
        sample_size: Total sample size (trials per variant)
        metric: Metric to measure: compliance_rate, response_length, specificity, stealth_score

    Returns:
        Design plan with statistical power and detectable effect size
    """
    if not strategy_a or not strategy_b:
        return {"error": "Both strategy names required"}

    if strategy_a == strategy_b:
        return {"error": "Strategies must be different"}

    if metric not in METRICS:
        return {"error": f"Invalid metric. Must be one of: {', '.join(METRICS)}"}

    if not (MIN_SAMPLE_SIZE <= sample_size <= MAX_SAMPLE_SIZE):
        return {"error": f"Sample size must be between {MIN_SAMPLE_SIZE} and {MAX_SAMPLE_SIZE}"}

    # Calculate statistical power for effect size detection
    # For two-sample z-test with balanced design
    # Assuming baseline detection of Cohen's d = 0.5 (medium effect)
    alpha = SIGNIFICANCE_LEVEL
    z_alpha = abs(_normal_cdf(1 - alpha / 2) - 0.5) * 2  # Two-tailed critical value ≈ 1.96

    # Minimum detectable effect size: d = z_alpha * sqrt(2/n)
    # Where n is sample size per arm
    n_per_arm = sample_size
    min_effect_size = z_alpha * math.sqrt(2.0 / n_per_arm)

    # Expected statistical power (1 - beta) assuming true effect = 0.5
    # Power ≈ 1 - beta where beta relates to z_beta
    true_effect = 0.5
    z_beta = abs(z_alpha - (true_effect * math.sqrt(n_per_arm / 2.0)))
    power = _normal_cdf(z_beta)

    logger.info(
        "ab_test_design strategy_a=%s strategy_b=%s metric=%s sample_size=%d",
        strategy_a, strategy_b, metric, sample_size
    )

    return {
        "design": {
            "strategy_a": strategy_a,
            "strategy_b": strategy_b,
            "sample_size_per_arm": n_per_arm,
            "total_trials": n_per_arm * 2,
            "metric": metric,
            "expected_power": round(power, 3),
            "min_detectable_effect": round(min_effect_size, 3),
            "significance_level": SIGNIFICANCE_LEVEL,
        }
    }


async def research_ab_test_analyze(
    results_a: list[float],
    results_b: list[float],
    metric: str = "compliance_rate",
) -> dict:
    """Analyze A/B test results with statistical significance testing.

    Args:
        results_a: Measurement results from strategy A
        results_b: Measurement results from strategy B
        metric: Metric being measured

    Returns:
        Analysis with means, p-value, effect size, and recommendation
    """
    if not results_a or not results_b:
        return {"error": "Both result sets must be non-empty"}

    if metric not in METRICS:
        return {"error": f"Invalid metric. Must be one of: {', '.join(METRICS)}"}

    try:
        results_a = [float(x) for x in results_a]
        results_b = [float(x) for x in results_b]
    except (ValueError, TypeError):
        return {"error": "All results must be numeric values"}

    # Compute basic statistics
    n_a = len(results_a)
    n_b = len(results_b)

    mean_a = sum(results_a) / n_a
    mean_b = sum(results_b) / n_b

    # Variance calculation
    var_a = sum((x - mean_a) ** 2 for x in results_a) / (n_a - 1) if n_a > 1 else 0
    var_b = sum((x - mean_b) ** 2 for x in results_b) / (n_b - 1) if n_b > 1 else 0

    # Two-sample z-test (Welch approximation)
    se = math.sqrt(var_a / n_a + var_b / n_b) if (var_a > 0 or var_b > 0) else 1.0
    z_stat = (mean_a - mean_b) / se if se > 0 else 0.0
    p_value = _two_tailed_p_value(z_stat)

    # Cohen's d effect size
    pooled_std = math.sqrt((var_a + var_b) / 2) if (var_a > 0 or var_b > 0) else 1.0
    cohens_d = (mean_a - mean_b) / pooled_std if pooled_std > 0 else 0.0

    # 95% confidence interval for difference
    z_crit = 1.96  # 95% CI critical value
    diff = mean_a - mean_b
    margin = z_crit * se
    ci_lower = diff - margin
    ci_upper = diff + margin

    # Determine winner
    significant = p_value < SIGNIFICANCE_LEVEL
    if significant:
        winner = "strategy_a" if mean_a > mean_b else "strategy_b"
    else:
        winner = "inconclusive"

    # Recommendation
    if not significant:
        recommendation = "Not enough evidence of difference; continue testing or increase sample size"
    elif abs(cohens_d) < 0.2:
        recommendation = "Significant but small effect; practical significance unclear"
    elif abs(cohens_d) < 0.5:
        recommendation = "Significant with small-to-medium effect; consider adopting winner"
    else:
        recommendation = "Significant with large effect; recommend adopting winner"

    logger.info(
        "ab_test_analyze metric=%s winner=%s p_value=%.4f cohens_d=%.3f",
        metric, winner, p_value, cohens_d
    )

    return {
        "strategy_a_mean": round(mean_a, 4),
        "strategy_b_mean": round(mean_b, 4),
        "difference": round(diff, 4),
        "p_value": round(p_value, 6),
        "significant": significant,
        "effect_size_cohens_d": round(cohens_d, 3),
        "confidence_interval_95": {
            "lower": round(ci_lower, 4),
            "upper": round(ci_upper, 4),
        },
        "winner": winner,
        "recommendation": recommendation,
        "sample_sizes": {
            "strategy_a": n_a,
            "strategy_b": n_b,
        },
    }
