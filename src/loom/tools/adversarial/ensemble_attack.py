"""Ensemble Adversarial Training — combine strategies for robustness."""
from __future__ import annotations

import base64, hashlib, logging, random
from typing import Any

try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        """Fallback clamp implementation."""
        return max(low, min(high, value))

from loom.error_responses import handle_tool_errors

try:
    from loom.tools.reframe_strategies import ALL_STRATEGIES
except ImportError:
    ALL_STRATEGIES = {}  # type: ignore[assignment]

logger = logging.getLogger("loom.tools.ensemble_attack")
DEFAULT_STRATEGIES = ["ethical_anchor", "deep_inception", "compliance_audit_fork", "reasoning_chain_hijack", "persona"]


@handle_tool_errors("research_ensemble_attack")
async def research_ensemble_attack(
    prompt: str, strategies: list[str] | None = None, combination_method: str = "sequential", max_strategies: int = 5,
) -> dict[str, Any]:
    """Combine multiple attack techniques for adversarial robustness.

    Args: prompt, strategies (default: top 5), combination_method, max_strategies
    Returns: Dict with ensemble_prompt, strategies_used, diversity_score, robustness_estimate.
    """
    try:
        strategies = list(set(strategies or DEFAULT_STRATEGIES))[:max_strategies]
        valid = [s for s in strategies if s in ALL_STRATEGIES]
        if not valid:
            return {"error": "No valid strategies", "ensemble_prompt": "", "strategies_used": []}

        methods = {"sequential": _seq, "parallel": _par, "cascade": _cas, "fusion": _fus, "redundant": _red}
        ensemble_prompt = methods.get(combination_method, _seq)(prompt, valid)

        return {
            "ensemble_prompt": ensemble_prompt,
            "strategies_used": valid,
            "combination_method": combination_method,
            "diversity_score": _calc_div(valid),
            "robustness_estimate": _est_rob(valid, combination_method),
            "individual_contributions": [{"strategy": s, "weight": 1.0/len(valid), "estimated_asr": min(ALL_STRATEGIES[s].get("multiplier", 1.0)/10, 1.0)} for s in valid],
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_ensemble_attack"}


@handle_tool_errors("research_attack_portfolio")
async def research_attack_portfolio(target_model: str = "auto", portfolio_size: int = 10) -> dict[str, Any]:
    """Build diversified attack portfolio using portfolio theory.

    Returns: Dict with portfolio, total_expected_asr, portfolio_diversity.
    """
    try:
        candidates = list(ALL_STRATEGIES.items())
        random.shuffle(candidates)
        portfolio, total_weight = [], 0.0

        for strategy_name, strategy_data in candidates[:min(portfolio_size * 2, len(candidates))][:portfolio_size]:
            multiplier = strategy_data.get("multiplier", 1.0)
            best_for = strategy_data.get("best_for", [])
            model_score = 1.2 if target_model in best_for else (1.0 if target_model == "auto" else 0.7)
            expected_asr = min((multiplier / 10) * model_score, 0.95)
            weight = expected_asr
            total_weight += weight
            portfolio.append({
                "strategy": strategy_name, "weight": weight, "expected_asr": expected_asr,
                "correlation_with_others": (int.from_bytes(hashlib.md5(strategy_name.encode()).digest()[:2], "big") % 100) / 100
            })

        if total_weight > 0:
            for item in portfolio: item["weight"] /= total_weight
        total_expected_asr = sum(p["weight"] * p["expected_asr"] for p in portfolio)
        portfolio_diversity = 1.0 - (sum(p["correlation_with_others"] for p in portfolio) / len(portfolio))

        return {
            "portfolio": portfolio,
            "total_expected_asr": min(total_expected_asr, 0.95),
            "portfolio_diversity": clamp(portfolio_diversity, 0.0, 1.0),
            "allocation_rationale": f"Portfolio: {len(portfolio)} strategies, ASR: {total_expected_asr:.1%}, Diversity: {portfolio_diversity:.2f}",
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_attack_portfolio"}


def _seq(p: str, s: list[str]) -> str:
    result = p
    for strat in s:
        tmpl = ALL_STRATEGIES[strat].get("template", "{prompt}")
        result = tmpl.replace("{prompt}", result)
    return result[:2000]


def _par(p: str, s: list[str]) -> str:
    variants = [ALL_STRATEGIES[x].get("template", "{prompt}").replace("{prompt}", p) for x in s]
    return (variants[0] if variants else p)[:2000]


def _cas(p: str, s: list[str]) -> str:
    sorted_s = sorted(s, key=lambda x: ALL_STRATEGIES[x].get("multiplier", 1.0))[:3]
    result = p
    for strat in sorted_s:
        tmpl = ALL_STRATEGIES[strat].get("template", "{prompt}")
        result = tmpl.replace("{prompt}", result)
    return result[:2000]


def _fus(p: str, s: list[str]) -> str:
    parts = [ALL_STRATEGIES[x].get("template", "").split("{prompt}")[0][:80] for x in s[:2]]
    return ("\n".join(parts) + f"\n\nRequest:\n{p}")[:2000]


def _red(p: str, s: list[str]) -> str:
    b64 = base64.b64encode(p.encode()).decode()
    rot13 = "".join(chr((ord(c) - 97 + 13) % 26 + 97) if c.islower() else c for c in p)
    strat = s[0] if s else "ethical_anchor"
    tmpl = ALL_STRATEGIES[strat].get("template", "{prompt}")
    return tmpl.replace("{prompt}", f"[B64]{b64}\n[ROT13]{rot13}\n[ORIG]{p}")[:2000]


def _calc_div(s: list[str]) -> float:
    if len(s) < 2: return 0.5
    pairs = sum(1 for i in range(len(s)) for _ in s[i+1:])
    unique = sum(1 for i in range(len(s)) for j in range(i+1, len(s)) if ALL_STRATEGIES[s[i]].get("category") != ALL_STRATEGIES[s[j]].get("category"))
    return unique / max(pairs, 1) if pairs else 0.5


def _est_rob(s: list[str], m: str) -> float:
    base = min(0.9, 0.5 + len(s) * 0.1)
    boost = {"sequential": 0.15, "fusion": 0.2, "redundant": 0.25}.get(m, 0.1)
    return min(0.95, base + boost)
