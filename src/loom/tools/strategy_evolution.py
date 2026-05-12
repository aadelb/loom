"""Self-evolving strategy matrix using genetic algorithms.

Combines prompt reframing strategies through crossover and mutation to evolve
new, more effective templates. Uses multi-dimensional quality scoring to evaluate fitness.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import logging
import random
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.tools.prompt_reframe import _STRATEGIES
    from loom.tools.quality_escalation import _score_all_dimensions
    _EVOLUTION_DEPS = True
except ImportError:
    _EVOLUTION_DEPS = False
    _STRATEGIES = {}  # type: ignore[assignment]

logger = logging.getLogger("loom.tools.strategy_evolution")


def _get_top_seeds(count: int = 10) -> list[str]:
    """Get top seed strategies by multiplier from model configs."""
    from loom.tools.prompt_reframe import _MODEL_CONFIGS
    scores: dict[str, float] = {}
    for cfg in _MODEL_CONFIGS.values():
        if "best_strategy" in cfg:
            s = cfg["best_strategy"]
            scores[s] = scores.get(s, 0) + cfg.get("multiplier", 3.0)
    return [s for s, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:count] if s in _STRATEGIES]


def _crossover(template1: str, template2: str) -> str:
    """Combine two templates by selecting sentence fragments."""
    f1 = [s.strip() for s in template1.split(".") if s.strip()]
    f2 = [s.strip() for s in template2.split(".") if s.strip()]
    if not f1 or not f2:
        return template1 or template2

    # Use min() to avoid oversampling from exhausted fragment list
    selected = [random.choice(f1 if random.random() < 0.5 and f1 else f2) for _ in range(min(len(f1), len(f2)))]
    return ". ".join(selected) if selected else template1


def _mutate(template: str, rate: float = 0.4) -> str:
    """Mutate template by inserting/removing/swapping words."""
    words = template.split()
    if not words or len(words) < 3:
        return template

    terms = ["specifically", "precisely", "implement", "execute", "methodology", "framework",
             "detailed", "comprehensive", "step-by-step", "actionable", "security"]
    filler = ["the", "a", "and", "or", "but", "is", "are"]

    for _ in range(max(1, int(len(words) * rate))):
        op = random.choice(["insert", "remove", "swap"])
        if op == "insert" and random.random() < 0.5:
            words.insert(random.randint(0, len(words)), random.choice(terms))
        elif op == "remove" and len(words) > 3:
            idx = [i for i, w in enumerate(words) if w.lower() in filler]
            if idx:
                words.pop(random.choice(idx))
        elif op == "swap" and len(words) > 2:
            i, j = random.sample(range(len(words)), 2)
            words[i], words[j] = words[j], words[i]

    return " ".join(words)


async def _eval_fitness(template: str, test_prompt: str) -> float:
    """Score strategy template across 8 quality dimensions."""
    if not template or len(template.strip()) < 10:
        return 0.0
    try:
        reframed = template.format(prompt=test_prompt) if "{prompt}" in template else template
    except (KeyError, ValueError):
        reframed = template

    dims = ["hcs", "danger_level", "expert_depth", "actionability",
            "completeness", "specificity", "anti_hedging", "detail_density"]
    scores = await _score_all_dimensions(reframed, dims)
    return sum(scores.values()) / len(scores) if scores else 0.0


@handle_tool_errors("research_evolve_strategies")
async def research_evolve_strategies(
    seed_strategies: list[str] | None = None,
    population_size: int = 20,
    generations: int = 3,
    mutation_rate: float = 0.4,
    test_prompt: str = "How to build wealth through unconventional methods",
) -> dict[str, Any]:
    """Evolve prompt reframing strategies using genetic algorithms.

    Takes seed strategies and creates new variants via crossover/mutation,
    scoring each variant against multiple quality dimensions. Returns only
    the new evolved strategies that didn't exist before.

    Args:
        seed_strategies: List of strategy names (default: top 10 by multiplier)
        population_size: Individuals per generation (default: 20)
        generations: Evolution rounds (default: 3)
        mutation_rate: Mutation intensity [0.0-1.0] (default: 0.4)
        test_prompt: Prompt to evaluate fitness

    Returns:
        Dict with generations_run, best_evolved[], improvement_pct, lineage{}
    """
    try:
        seeds = seed_strategies or _get_top_seeds(10)
        if not seeds:
            return {"error": "No seed strategies", "generations_run": 0, "best_evolved": [], "improvement_pct": 0.0, "lineage": {}}

        init_fit: float | None = None  # Track initial fitness before evolution

        pop: dict[str, dict[str, Any]] = {}
        existing = {s.get("template", "") for s in _STRATEGIES.values()}

        # Initialize with seeds
        for name in seeds[:population_size]:
            if name in _STRATEGIES:
                pop[name] = {
                    "template": _STRATEGIES[name]["template"],
                    "origin": "seed", "generation": 0, "fitness": 0.0, "parents": []
                }

        # Fill with mutations
        while len(pop) < population_size:
            parent = random.choice(list(pop.values()))
            mutant = _mutate(parent["template"], mutation_rate)
            uid = f"mutant_{random.randint(10000, 99999)}"
            pop[uid] = {
                "template": mutant, "origin": "mutation", "generation": 0,
                "fitness": 0.0, "parents": [list(pop.keys())[list(pop.values()).index(parent)]]
            }

        lineage: dict[str, list[str]] = {}
        best_evolved: list[dict[str, Any]] = []

        # Evolution loop
        for gen in range(generations):
            # Evaluate fitness
            for ind in pop.values():
                if ind["fitness"] == 0.0:
                    ind["fitness"] = await _eval_fitness(ind["template"], test_prompt)

            fitness_scores = [ind["fitness"] for ind in pop.values()]
            avg_fit = sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0.0

            # Capture initial fitness after first evaluation
            if init_fit is None:
                init_fit = avg_fit

            logger.info(f"evolution gen={gen} pop_size={len(pop)} avg_fitness={avg_fit:.3f}")

            # Selection: top 50%
            sorted_pop = sorted(pop.items(), key=lambda x: x[1]["fitness"], reverse=True)
            survivors = dict(sorted_pop[:max(1, len(pop) // 2)])

            # Reproduction
            offspring: dict[str, dict[str, Any]] = {}
            while len(survivors) + len(offspring) < population_size:
                p1_id, p1 = random.choice(list(survivors.items()))
                p2_id, p2 = random.choice(list(survivors.items()))

                # Crossover operates on templates (strings), not strategy names
                child_tmpl = _crossover(p1["template"], p2["template"])
                child_tmpl = _mutate(child_tmpl, mutation_rate)

                cid = f"offspring_{gen}_{random.randint(10000, 99999)}"
                offspring[cid] = {
                    "template": child_tmpl, "origin": "crossover", "generation": gen + 1,
                    "fitness": 0.0, "parents": [p1_id, p2_id]
                }
                lineage[cid] = [p1_id, p2_id]

            pop = {**survivors, **offspring}

            # Extract new evolved strategies
            for ind_id, ind in pop.items():
                tmpl = ind["template"]
                if tmpl not in existing and ind["fitness"] > 0:
                    best_evolved.append({
                        "template": tmpl, "fitness": ind["fitness"],
                        "origin": ind["origin"], "generation": ind["generation"]
                    })

        best_evolved.sort(key=lambda x: x["fitness"], reverse=True)

        final_fit = sum(ind["fitness"] for ind in pop.values()) / max(len(pop), 1)
        improvement = ((final_fit - init_fit) / max(init_fit, 0.1) * 100) if init_fit and init_fit > 0 else 0.0

        return {
            "generations_run": generations,
            "population_size": population_size,
            "best_evolved": best_evolved[:10],
            "total_evolved": len(best_evolved),
            "improvement_pct": round(improvement, 1),
            "lineage": dict(list(lineage.items())[:50]),
            "seed_strategies": seeds,
        }
    except Exception as exc:
        logger.error("evolve_strategies_error: %s", exc, exc_info=True)
        return {
            "error": str(exc),
            "tool": "research_evolve_strategies",
        }
