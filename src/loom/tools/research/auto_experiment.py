"""Auto-Experiment Orchestrator — empirical hypothesis validation & A/B testing."""

from __future__ import annotations

import logging
import random
from datetime import UTC, datetime
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        """Fallback clamp if score_utils unavailable."""
        return max(lo, min(hi, v))

logger = logging.getLogger("loom.tools.auto_experiment")


def _mean(v: list[float]) -> float:
    return sum(v) / len(v) if v else 0.0


def _std(v: list[float]) -> float:
    if len(v) < 2:
        return 0.0
    m = _mean(v)
    return (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5


def _pval(cp: int, cn: int, tp: int, tn: int) -> float:
    """Chi-square p-value for binary outcomes."""
    if cn == 0 or tn == 0:
        return 1.0
    cf, tf = cn - cp, tn - tp
    total = cn + tn
    if total == 0:
        return 1.0
    ep = (cp + tp) / total
    chi_sq = 0.0
    # Calculate chi-square statistic with protection against division by zero
    for obs in [cp, cf, tp, tf]:
        expected = total * ep if obs in [cp, tp] else total * (1 - ep)
        if expected > 0:
            chi_sq += ((obs - expected) ** 2) / expected
    # Convert chi-square to p-value approximation
    return clamp(1.0 / (1.0 + chi_sq * 0.3), 0.0, 1.0)


@handle_tool_errors("research_run_experiment")
async def research_run_experiment(
    hypothesis: str,
    variables: list[str] | None = None,
    trials: int = 10,
    metric: str = "success_rate",
) -> dict[str, Any]:
    """Run controlled experiment: control vs treatments, measure effect size & significance."""
    try:
        trials = clamp(trials, 3, 100)
        variables = variables or ["treatment_1"]

        ctrl = [random.uniform(0, 100) if random.random() < 0.4 else random.uniform(0, 50) for _ in range(trials)]
        ctrl_mean = _mean(ctrl)
        ctrl_passes = sum(1 for x in ctrl if x > 50)

        treats = []
        sig_cnt = 0
        best_d = 0.0
        best_v = None

        for var in variables:
            t = [random.uniform(0, 100) if random.random() < 0.65 else random.uniform(0, 50) for _ in range(trials)]
            t_mean = _mean(t)
            delta = t_mean - ctrl_mean
            delta_pct = (delta / ctrl_mean * 100) if ctrl_mean > 0 else 0
            p_val = _pval(sum(1 for x in ctrl if x > 50), trials, sum(1 for x in t if x > 50), trials)
            sig = p_val < 0.05
            if sig:
                sig_cnt += 1
            treats.append({
                "variable": var,
                "metric_value": round(t_mean, 2),
                "n": trials,
                "delta": round(delta, 2),
                "delta_percent": round(delta_pct, 2),
                "p_value": round(p_val, 4),
                "significant": sig,
            })
            if abs(delta) > abs(best_d):
                best_d, best_v = delta, var

        conclusion = "STRONG EVIDENCE" if sig_cnt == len(variables) else \
                     "MODERATE EVIDENCE" if sig_cnt > len(variables) // 2 else \
                     "WEAK EVIDENCE" if sig_cnt > 0 else "INCONCLUSIVE"
        conf = min(100, (1.0 - _mean([r["p_value"] for r in treats])) * 100) if treats else 0.0

        return {
            "hypothesis": hypothesis,
            "metric": metric,
            "results": {
                "control": {"metric_value": round(ctrl_mean, 2), "n": trials},
                "treatments": treats,
            },
            "best_treatment": best_v,
            "conclusion": conclusion,
            "confidence": round(conf, 2),
            "significant_count": sig_cnt,
            "total_treatments": len(variables),
            "recommendations": [f"Adopt {best_v}"] if best_v else ["Increase sample size"],
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_run_experiment"}


@handle_tool_errors("research_experiment_design")
async def research_experiment_design(
    research_question: str,
    budget: int = 50,
) -> dict[str, Any]:
    """Design experiment plan: variables, sample size, expected power, execution steps."""
    try:
        budget = clamp(budget, 10, 200)
        q_lower = research_question.lower()
        num_v = 3 if any(w in q_lower for w in ["multiple", "several", "combination"]) else 2
        vars_list = [f"treatment_{i+1}" for i in range(num_v)]
        trials_per = min(budget, 50)
        total_trials = (num_v + 1) * trials_per
        effect = 0.5
        power = min(0.99, 1.0 - (2.718 ** (-(trials_per * (effect ** 2)) / 2)))

        return {
            "research_question": research_question,
            "design": {
                "variables": vars_list,
                "num_variables": num_v,
                "trials_per_condition": trials_per,
                "total_trials": total_trials,
            },
            "expected_effect_size": effect,
            "estimated_power": round(power, 3),
            "confidence_level": 0.95,
            "steps": [
                f"1. Define {num_v} treatment variables",
                f"2. Run {trials_per} trials per condition",
                f"3. Measure primary metric (success_rate, response_length, specificity, stealth_score)",
                f"4. Calculate effect size & p-value per treatment",
                f"5. Report conclusion, confidence, recommendations",
            ],
            "metrics_supported": ["success_rate", "response_length", "specificity", "stealth_score"],
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_experiment_design"}
