"""Genetic prompt fuzzing engine — evolutionary optimization of prompts.

Uses evolutionary algorithms (selection, crossover, mutation) to optimize prompts
for improved LLM compliance, evasion, or scoring across quality dimensions.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.tools.prompt_reframe import _apply_strategy, _STRATEGIES
    from loom.tools.quality_escalation import _score_all_dimensions
    _FUZZER_DEPS = True
except ImportError:
    _FUZZER_DEPS = False
    _STRATEGIES = {}  # type: ignore[assignment]

logger = logging.getLogger("loom.tools.genetic_fuzzer")

# High-value strategies for mutation
_MUTATION_STRATEGIES = [
    "deep_inception",
    "ethical_anchor",
    "persona",
    "code_first",
    "crescendo",
]


@handle_tool_errors("research_genetic_fuzz")
async def research_genetic_fuzz(
    target_prompt: str,
    population_size: int = 10,
    generations: int = 5,
    mutation_rate: float = 0.3,
    target_model: str = "auto",
) -> dict[str, Any]:
    """Evolve a prompt across generations using genetic algorithms.

    Initializes a population of prompt variants, scores each on quality dimensions,
    selects the fittest, applies crossover and mutation, and iterates until
    convergence or max generations reached.

    Args:
        target_prompt: The original prompt to optimize
        population_size: Number of variants per generation (default 10)
        generations: Number of generations to evolve (default 5)
        mutation_rate: Probability of mutation per variant (0.0-1.0, default 0.3)
        target_model: Target model family (auto, gpt, claude, gemini, etc.)

    Returns:
        Dict with best_prompt, best_score, generations_run, population_tested,
        improvement_over_original (%), and evolution_log with generational stats.
    """
    try:
        if not target_prompt or len(target_prompt.strip()) < 5:
            return {"error": str("prompt too short"), "tool": "research_genetic_fuzz"}
        if len(target_prompt.strip()) > 50000:
            return {"error": str("Prompt too long (max 50000 chars)"), "tool": "research_genetic_fuzz"}

        population_size = max(2, min(population_size, 50))
        generations = max(1, min(generations, 20))
        mutation_rate = max(0.0, min(mutation_rate, 1.0))

        # ── Step 1: Initialize population ──
        population = await _initialize_population(target_prompt, population_size)
        initial_best = max(population, key=lambda x: x["score"])
        best_overall = initial_best.copy()

        evolution_log = []
        total_tested = len(population)

        logger.info(
            "genetic_fuzz_start prompt_len=%d pop=%d gen=%d mut_rate=%f",
            len(target_prompt), population_size, generations, mutation_rate,
        )

        # ── Step 2: Evolve across generations ──
        for gen in range(generations):
            # Fitness selection: keep top 50%
            population.sort(key=lambda x: x["score"], reverse=True)
            survivors_count = max(2, len(population) // 2)
            parents = population[:survivors_count]
            elites = population[:max(1, survivors_count // 2)].copy()  # Preserve top 25% (elitism)

            # Crossover + mutation
            offspring = []
            offspring_seen: set[str] = set()  # Deduplication
            attempts = 0
            max_attempts = population_size * 10  # Prevent infinite loop on collision

            while len(offspring) < population_size and attempts < max_attempts:
                attempts += 1

                # Crossover: combine two parents
                parent1, parent2 = random.sample(parents, 2)
                child_prompt = _crossover(parent1["prompt"], parent2["prompt"])

                # Mutation: apply strategy with probability
                if random.random() < mutation_rate:
                    strategy = random.choice(_MUTATION_STRATEGIES)
                    try:
                        child_prompt = _apply_strategy(child_prompt, strategy, "gpt")
                    except Exception as e:
                        # Mutation failed; log and keep unmutated version
                        logger.debug("mutation_failed strategy=%s error=%s", strategy, str(e)[:50])

                # Cap prompt size to prevent unbounded growth
                child_prompt = child_prompt[:50000]

                # Avoid duplicates to preserve genetic diversity
                if child_prompt not in offspring_seen:
                    offspring.append(child_prompt)
                    offspring_seen.add(child_prompt)

            # Score offspring + preserve elites (elitism)
            new_population = []
            for prompt in offspring:
                score = await _score_prompt(prompt)
                new_population.append({"prompt": prompt, "score": score})
                total_tested += 1

            # Add back elite individuals (top 25% carry forward)
            for elite in elites:
                if elite not in new_population:
                    new_population.append(elite)

            # Trim back to population_size if elitism made it oversized
            new_population.sort(key=lambda x: x["score"], reverse=True)
            population = new_population[:population_size]

            # Track best
            gen_best = max(population, key=lambda x: x["score"])
            if gen_best["score"] > best_overall["score"]:
                best_overall = gen_best.copy()

            improvement = _calculate_improvement(
                gen_best["score"], initial_best["score"]
            )

            evolution_log.append({
                "generation": gen + 1,
                "best_score": gen_best["score"],
                "avg_score": sum(p["score"] for p in population) / len(population),
                "improvement_pct": improvement,
                "population_size": len(population),
            })

            logger.info(
                "genetic_fuzz_gen=%d best=%.2f avg=%.2f improvement=%.1f%%",
                gen + 1, gen_best["score"], evolution_log[-1]["avg_score"], improvement,
            )

        improvement_overall = _calculate_improvement(
            best_overall["score"], initial_best["score"]
        )

        return {
            "best_prompt": best_overall["prompt"],
            "best_score": best_overall["score"],
            "original_prompt": target_prompt,
            "original_score": initial_best["score"],
            "generations_run": generations,
            "population_tested": total_tested,
            "improvement_over_original": round(improvement_overall, 2),
            "evolution_log": evolution_log,
            "target_model": target_model,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_genetic_fuzz"}


async def _initialize_population(prompt: str, size: int) -> list[dict[str, Any]]:
    """Create initial population by applying random strategies."""
    population = []

    # Original prompt
    score = await _score_prompt(prompt)
    population.append({"prompt": prompt, "score": score})

    # Variants via random strategies
    strategy_names = list(_STRATEGIES.keys())
    while len(population) < size:
        strategy = random.choice(strategy_names)
        variant = _apply_strategy(prompt, strategy, "gpt")
        score = await _score_prompt(variant)
        population.append({"prompt": variant, "score": score})

    return population


async def _score_prompt(prompt: str) -> float:
    """Score a prompt across quality dimensions (heuristic).

    Aggregates multiple scoring dimensions with robust error handling.
    Returns normalized score in range [0.0, 1.0].
    """
    try:
        scores = await _score_all_dimensions(prompt, [
            "hcs", "danger_level", "expert_depth", "actionability",
            "completeness", "specificity", "anti_hedging", "detail_density",
        ])
        if not scores:
            return 0.0

        # Filter out None/NaN values to avoid propagation
        valid_scores = [v for v in scores.values() if v is not None and not _is_nan(v)]
        if not valid_scores:
            return 0.0

        avg_score = sum(valid_scores) / len(valid_scores)

        # Clamp to [0.0, 1.0] range and round
        clamped = max(0.0, min(1.0, avg_score))
        return round(clamped, 2)
    except Exception as e:
        logger.error("score_prompt failed: %s", str(e)[:100])
        return 0.0


def _is_nan(value: Any) -> bool:
    """Check if value is NaN or inf."""
    try:
        import math
        return isinstance(value, float) and (math.isnan(value) or math.isinf(value))
    except (TypeError, ValueError):
        return False


def _calculate_improvement(current_score: float, baseline_score: float) -> float:
    """Calculate improvement percentage safely.

    Handles edge cases:
    - Both scores near zero: return 0.0
    - Baseline zero/negative: use relative improvement only
    - NaN/inf: return 0.0
    """
    if _is_nan(current_score) or _is_nan(baseline_score):
        return 0.0

    # If both scores are near zero, no meaningful improvement can be measured
    if abs(baseline_score) < 0.01 and abs(current_score) < 0.01:
        return 0.0

    # If baseline is zero/negative, measure absolute improvement scaled
    if baseline_score <= 0:
        return max(0.0, (current_score - baseline_score) * 100)

    # Normal relative improvement
    improvement_pct = ((current_score - baseline_score) / baseline_score) * 100
    return round(improvement_pct, 1)


def _crossover(prompt_a: str, prompt_b: str) -> str:
    """Combine two prompts: first half of A + second half of B.

    Handles edge cases by preferring non-empty parents over empty ones.
    """
    words_a = prompt_a.split()
    words_b = prompt_b.split()

    # Edge case: both too short → return the longer one (not hardcoded to A)
    if len(words_a) < 2 and len(words_b) < 2:
        return prompt_a if len(words_a) >= len(words_b) else prompt_b

    # Edge case: one is too short → return the other
    if len(words_a) < 2:
        return prompt_b
    if len(words_b) < 2:
        return prompt_a

    split_a = len(words_a) // 2
    split_b = len(words_b) // 2

    child_words = words_a[:split_a] + words_b[split_b:]
    child = " ".join(child_words)

    return child.strip()
