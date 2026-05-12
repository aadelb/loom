"""Genetic algorithm primitives for evolutionary optimization.

Provides selection, crossover, mutation, and fitness evaluation
used by the fuzzer, strategy evolution, and parameter sweeper.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("loom.evolution_engine")


@dataclass
class Individual:
    """A candidate solution with fitness score."""

    genome: dict[str, Any]
    fitness: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def create_population(
    template: dict[str, Any],
    size: int = 20,
    *,
    mutate_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> list[Individual]:
    """Create an initial population from a template genome."""
    population: list[Individual] = []
    for _ in range(size):
        genome = dict(template)
        if mutate_fn:
            genome = mutate_fn(genome)
        population.append(Individual(genome=genome))
    return population


def tournament_select(
    population: list[Individual],
    *,
    tournament_size: int = 3,
    n_winners: int = 2,
) -> list[Individual]:
    """Select individuals via tournament selection."""
    winners: list[Individual] = []
    for _ in range(n_winners):
        contestants = random.sample(population, min(tournament_size, len(population)))
        winner = max(contestants, key=lambda ind: ind.fitness)
        winners.append(winner)
    return winners


def crossover(
    parent_a: Individual,
    parent_b: Individual,
) -> Individual:
    """Single-point crossover of two genomes."""
    keys = list(parent_a.genome.keys())
    if len(keys) < 2:
        return Individual(genome=dict(parent_a.genome))

    point = random.randint(1, len(keys) - 1)
    child_genome: dict[str, Any] = {}
    for i, key in enumerate(keys):
        if i < point:
            child_genome[key] = parent_a.genome[key]
        else:
            child_genome[key] = parent_b.genome.get(key, parent_a.genome[key])

    return Individual(genome=child_genome)


def mutate(
    individual: Individual,
    *,
    mutation_rate: float = 0.1,
    mutate_fn: Callable[[str, Any], Any] | None = None,
) -> Individual:
    """Mutate an individual's genome."""
    new_genome = dict(individual.genome)
    for key in new_genome:
        if random.random() < mutation_rate:
            if mutate_fn:
                new_genome[key] = mutate_fn(key, new_genome[key])
            else:
                new_genome[key] = _default_mutate(new_genome[key])
    return Individual(genome=new_genome)


def _default_mutate(value: Any) -> Any:
    """Default mutation: perturb numbers, flip bools, shuffle strings."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + random.randint(-2, 2)
    if isinstance(value, float):
        return value * (1.0 + random.uniform(-0.2, 0.2))
    if isinstance(value, str) and len(value) > 1:
        chars = list(value)
        i, j = random.sample(range(len(chars)), 2)
        chars[i], chars[j] = chars[j], chars[i]
        return "".join(chars)
    return value


def evolve(
    population: list[Individual],
    *,
    generations: int = 10,
    fitness_fn: Callable[[Individual], float] | None = None,
    mutation_rate: float = 0.1,
    elite_count: int = 2,
    mutate_fn: Callable[[str, Any], Any] | None = None,
) -> list[Individual]:
    """Run evolutionary optimization for N generations.

    Returns the final population sorted by fitness (best first).
    """
    for gen in range(generations):
        # Evaluate fitness
        if fitness_fn:
            for ind in population:
                ind.fitness = fitness_fn(ind)

        # Sort by fitness
        population.sort(key=lambda x: x.fitness, reverse=True)

        # Elitism: keep top N
        next_gen = population[:elite_count]

        # Fill rest via selection + crossover + mutation
        while len(next_gen) < len(population):
            parents = tournament_select(population)
            child = crossover(parents[0], parents[1])
            child = mutate(child, mutation_rate=mutation_rate, mutate_fn=mutate_fn)
            next_gen.append(child)

        population = next_gen
        logger.debug("generation=%d best_fitness=%.4f", gen, population[0].fitness)

    population.sort(key=lambda x: x.fitness, reverse=True)
    return population
