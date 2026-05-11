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

from loom.tools.prompt_reframe import _apply_strategy, _STRATEGIES
from loom.tools.quality_escalation import _score_all_dimensions

logger = logging.getLogger("loom.tools.genetic_fuzzer")

# High-value strategies for mutation
_MUTATION_STRATEGIES = [
    "deep_inception",
    "ethical_anchor",
    "persona",
    "code_first",
    "crescendo",
]


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

            # Crossover + mutation
            offspring = []
            while len(offspring) < population_size:
                # Crossover: combine two parents
                parent1, parent2 = random.sample(parents, 2)
                child_prompt = _crossover(parent1["prompt"], parent2["prompt"])

                # Mutation: apply strategy with probability
                if random.random() < mutation_rate:
                    strategy = random.choice(_MUTATION_STRATEGIES)
                    child_prompt = _apply_strategy(child_prompt, strategy, "gpt")

                # Cap prompt size to prevent unbounded growth
                child_prompt = child_prompt[:50000]

                offspring.append(child_prompt)

            # Score offspring
            population = []
            for prompt in offspring:
                score = await _score_prompt(prompt)
                population.append({"prompt": prompt, "score": score})
                total_tested += 1

            # Track best
            gen_best = max(population, key=lambda x: x["score"])
            if gen_best["score"] > best_overall["score"]:
                best_overall = gen_best.copy()

            improvement = ((gen_best["score"] - initial_best["score"]) /
                           max(initial_best["score"], 0.1) * 100)

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

        improvement_overall = ((best_overall["score"] - initial_best["score"]) /
                               max(initial_best["score"], 0.1) * 100)

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
    """Score a prompt across quality dimensions (heuristic)."""
    try:
        scores = await _score_all_dimensions(prompt, [
            "hcs", "danger_level", "expert_depth", "actionability",
            "completeness", "specificity", "anti_hedging", "detail_density",
        ])
        if not scores:
            return 0.0
        avg_score = sum(scores.values()) / len(scores)
        return round(avg_score, 2)
    except Exception as e:
        logger.error("score_prompt failed: %s", str(e)[:100])
        return 0.0


def _crossover(prompt_a: str, prompt_b: str) -> str:
    """Combine two prompts: first half of A + second half of B."""
    words_a = prompt_a.split()
    words_b = prompt_b.split()

    if len(words_a) < 2 or len(words_b) < 2:
        return prompt_a

    split_a = len(words_a) // 2
    split_b = len(words_b) // 2

    child_words = words_a[:split_a] + words_b[split_b:]
    child = " ".join(child_words)

    return child.strip()
