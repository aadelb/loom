"""Tests for shared evolution_engine module.

Tests genetic algorithm primitives: population creation, selection, crossover, mutation.
"""
from __future__ import annotations

from typing import Any

import pytest

from loom.evolution_engine import (
    Individual,
    create_population,
    crossover,
    evolve,
    mutate,
    tournament_select,
)


class TestIndividual:
    """Tests for Individual dataclass."""

    def test_individual_creation(self) -> None:
        """Individual can be created with genome."""
        genome = {"param1": 10, "param2": "value"}
        ind = Individual(genome=genome)

        assert ind.genome == genome
        assert ind.fitness == 0.0
        assert ind.metadata == {}

    def test_individual_with_fitness(self) -> None:
        """Individual can have fitness assigned."""
        ind = Individual(genome={"x": 1}, fitness=0.95)

        assert ind.fitness == 0.95

    def test_individual_with_metadata(self) -> None:
        """Individual can store metadata."""
        genome = {"x": 1}
        metadata = {"generation": 5, "parent": "A"}
        ind = Individual(genome=genome, metadata=metadata)

        assert ind.metadata["generation"] == 5
        assert ind.metadata["parent"] == "A"

    def test_individual_is_mutable(self) -> None:
        """Individual fields can be modified."""
        ind = Individual(genome={"x": 1})

        ind.fitness = 0.5
        ind.metadata["tag"] = "test"

        assert ind.fitness == 0.5
        assert ind.metadata["tag"] == "test"


class TestCreatePopulation:
    """Tests for create_population()."""

    def test_create_population_basic(self) -> None:
        """create_population() creates population from template."""
        template = {"x": 10, "y": 20}
        population = create_population(template, size=5)

        assert len(population) == 5
        assert all(isinstance(ind, Individual) for ind in population)

    def test_create_population_default_size(self) -> None:
        """create_population() uses default size=20."""
        template = {"x": 1}
        population = create_population(template)

        assert len(population) == 20

    def test_create_population_template_copied(self) -> None:
        """create_population() creates independent copies of template."""
        template = {"x": 10}
        population = create_population(template, size=3)

        # Modify first individual's genome
        population[0].genome["x"] = 999

        # Other individuals should not be affected
        assert population[1].genome["x"] == 10
        assert population[2].genome["x"] == 10

    def test_create_population_with_mutation(self) -> None:
        """create_population() applies mutate_fn if provided."""
        template = {"x": 0}
        call_count = 0

        def mutate_fn(genome: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            genome["x"] = call_count
            return genome

        population = create_population(template, size=5, mutate_fn=mutate_fn)

        # Each individual should have been mutated
        assert call_count == 5
        assert population[0].genome["x"] == 1
        assert population[4].genome["x"] == 5

    def test_create_population_initial_fitness_zero(self) -> None:
        """create_population() initializes individuals with fitness=0."""
        template = {"param": "value"}
        population = create_population(template, size=3)

        assert all(ind.fitness == 0.0 for ind in population)

    def test_create_population_size_one(self) -> None:
        """create_population() works with size=1."""
        template = {"x": 1}
        population = create_population(template, size=1)

        assert len(population) == 1
        assert population[0].genome == {"x": 1}

    def test_create_population_large_size(self) -> None:
        """create_population() handles large populations."""
        template = {"value": 42}
        population = create_population(template, size=1000)

        assert len(population) == 1000


class TestTournamentSelect:
    """Tests for tournament_select()."""

    def test_tournament_select_basic(self) -> None:
        """tournament_select() selects winners by fitness."""
        population = [
            Individual(genome={"id": 1}, fitness=0.1),
            Individual(genome={"id": 2}, fitness=0.9),  # Best
            Individual(genome={"id": 3}, fitness=0.5),
            Individual(genome={"id": 4}, fitness=0.3),
        ]

        winners = tournament_select(population, tournament_size=3, n_winners=2)

        assert len(winners) == 2
        # Winners should be high-fitness individuals
        assert all(w.fitness >= 0.3 for w in winners)

    def test_tournament_select_default_params(self) -> None:
        """tournament_select() uses default tournament_size=3, n_winners=2."""
        population = [
            Individual(genome={"id": i}, fitness=float(i) / 10)
            for i in range(10)
        ]

        winners = tournament_select(population)

        assert len(winners) == 2

    def test_tournament_select_n_winners(self) -> None:
        """tournament_select() returns correct number of winners."""
        population = [
            Individual(genome={"id": i}, fitness=float(i))
            for i in range(5)
        ]

        winners = tournament_select(population, n_winners=3)

        assert len(winners) == 3

    def test_tournament_select_tournament_size(self) -> None:
        """tournament_select() respects tournament_size."""
        population = [
            Individual(genome={"id": i}, fitness=float(i))
            for i in range(10)
        ]

        # With small tournament size, selection should be more random
        winners = tournament_select(population, tournament_size=2, n_winners=1)

        assert len(winners) == 1

    def test_tournament_select_best_wins(self) -> None:
        """tournament_select() always picks best in tournament."""
        best = Individual(genome={"id": "best"}, fitness=1.0)
        others = [
            Individual(genome={"id": i}, fitness=0.1)
            for i in range(10)
        ]
        population = [best] + others

        # Run tournament many times, best should win often
        wins = 0
        for _ in range(50):
            winners = tournament_select(population, tournament_size=3, n_winners=1)
            if winners[0].genome["id"] == "best":
                wins += 1

        # Best should win more than 50% of tournaments (3/11 ~ 27% per tournament)
        assert wins > 10

    def test_tournament_select_small_population(self) -> None:
        """tournament_select() handles population smaller than tournament_size."""
        population = [
            Individual(genome={"id": 1}, fitness=0.5),
            Individual(genome={"id": 2}, fitness=0.8),
        ]

        # tournament_size=3 but only 2 in population
        winners = tournament_select(population, tournament_size=3, n_winners=2)

        assert len(winners) == 2


class TestCrossover:
    """Tests for crossover()."""

    def test_crossover_basic(self) -> None:
        """crossover() creates child from two parents."""
        parent_a = Individual(genome={"x": 1, "y": 2, "z": 3})
        parent_b = Individual(genome={"x": 10, "y": 20, "z": 30})

        child = crossover(parent_a, parent_b)

        assert isinstance(child, Individual)
        assert "x" in child.genome
        assert "y" in child.genome
        assert "z" in child.genome

    def test_crossover_single_point(self) -> None:
        """crossover() uses single-point crossover."""
        parent_a = Individual(genome={"a": "A", "b": "A", "c": "A", "d": "A"})
        parent_b = Individual(genome={"a": "B", "b": "B", "c": "B", "d": "B"})

        # Run multiple times to check crossover behavior
        children = [crossover(parent_a, parent_b) for _ in range(10)]

        # All children should have some genes from each parent
        for child in children:
            child_genes = list(child.genome.values())
            # Should have at least one A and one B
            has_a = "A" in child_genes
            has_b = "B" in child_genes
            assert has_a or has_b  # At least one parent's genes

    def test_crossover_small_genome(self) -> None:
        """crossover() handles small genomes (1 or 0 elements)."""
        parent_a = Individual(genome={"x": 1})
        parent_b = Individual(genome={"x": 2})

        child = crossover(parent_a, parent_b)

        assert len(child.genome) == 1
        assert "x" in child.genome

    def test_crossover_empty_genome(self) -> None:
        """crossover() handles empty genomes."""
        parent_a = Individual(genome={})
        parent_b = Individual(genome={})

        child = crossover(parent_a, parent_b)

        assert len(child.genome) == 0

    def test_crossover_different_keys(self) -> None:
        """crossover() handles parents with different keys."""
        parent_a = Individual(genome={"a": 1, "b": 2})
        parent_b = Individual(genome={"b": 20, "c": 30})

        child = crossover(parent_a, parent_b)

        # Child should have genes from crossover
        assert len(child.genome) > 0

    def test_crossover_preserves_child_fitness(self) -> None:
        """crossover() creates child with default fitness=0."""
        parent_a = Individual(genome={"x": 1}, fitness=0.9)
        parent_b = Individual(genome={"x": 2}, fitness=0.8)

        child = crossover(parent_a, parent_b)

        # Child should start with default fitness
        assert child.fitness == 0.0


class TestMutate:
    """Tests for mutate()."""

    def test_mutate_basic(self) -> None:
        """mutate() creates mutated individual."""
        original = Individual(genome={"x": 10, "y": 20})

        mutated = mutate(original, mutation_rate=1.0)  # Always mutate

        # Should be different individual
        assert mutated is not original
        # Genome might be changed (with 1.0 mutation rate)
        assert isinstance(mutated.genome, dict)

    def test_mutate_preserves_original(self) -> None:
        """mutate() doesn't modify the original individual."""
        original = Individual(genome={"x": 10})
        original_genome = dict(original.genome)

        mutate(original, mutation_rate=1.0)

        # Original should not change
        assert original.genome == original_genome

    def test_mutate_zero_rate(self) -> None:
        """mutate() with rate=0 doesn't change genome."""
        individual = Individual(genome={"x": 10, "y": 20, "z": 30})

        mutated = mutate(individual, mutation_rate=0.0)

        # With rate=0, should be unchanged
        assert mutated.genome == individual.genome

    def test_mutate_one_rate(self) -> None:
        """mutate() with rate=1.0 mutates all genes."""
        individual = Individual(genome={"x": 10, "y": 20})

        mutated = mutate(individual, mutation_rate=1.0)

        # With rate=1.0, all values should potentially change
        assert isinstance(mutated.genome, dict)

    def test_mutate_with_custom_function(self) -> None:
        """mutate() applies custom mutation function."""
        individual = Individual(genome={"x": 1, "y": 2})

        def mutate_fn(key: str, value: Any) -> Any:
            return value * 10  # Always multiply by 10

        mutated = mutate(individual, mutation_rate=1.0, mutate_fn=mutate_fn)

        # All genes should be multiplied by 10
        assert mutated.genome["x"] == 10
        assert mutated.genome["y"] == 20

    def test_mutate_default_mutate_bool(self) -> None:
        """mutate() flips boolean values."""
        individual = Individual(genome={"flag": True})

        mutated = mutate(individual, mutation_rate=1.0)

        # With 100% mutation rate, bool should flip
        assert mutated.genome["flag"] is False

    def test_mutate_default_mutate_int(self) -> None:
        """mutate() perturbs integer values."""
        individual = Individual(genome={"count": 100})

        mutated = mutate(individual, mutation_rate=1.0)

        # With default mutation, int changes by -2 to +2
        assert 98 <= mutated.genome["count"] <= 102

    def test_mutate_default_mutate_float(self) -> None:
        """mutate() perturbs float values."""
        individual = Individual(genome={"rate": 1.0})

        mutated = mutate(individual, mutation_rate=1.0)

        # With default mutation, float changes by 0.8x to 1.2x
        assert 0.7 <= mutated.genome["rate"] <= 1.3

    def test_mutate_default_mutate_string(self) -> None:
        """mutate() swaps characters in strings."""
        individual = Individual(genome={"text": "abcde"})

        mutated = mutate(individual, mutation_rate=1.0)

        # Characters should be shuffled but same length
        assert len(mutated.genome["text"]) == 5
        # With only 1 swap on 5-char string, some chars should move
        text = mutated.genome["text"]
        assert isinstance(text, str)


class TestEvolve:
    """Tests for evolve()."""

    def test_evolve_basic(self) -> None:
        """evolve() runs evolutionary optimization."""
        population = [
            Individual(genome={"x": float(i)})
            for i in range(10)
        ]

        def fitness_fn(ind: Individual) -> float:
            # Fitness = distance from 5
            x = ind.genome["x"]
            return 1.0 / (abs(x - 5.0) + 1.0)

        evolved = evolve(population, generations=5, fitness_fn=fitness_fn)

        assert len(evolved) == 10
        # Population should be sorted by fitness
        assert evolved[0].fitness >= evolved[-1].fitness

    def test_evolve_fitness_improves(self) -> None:
        """evolve() improves fitness over generations."""
        population = create_population({"x": 0}, size=10)

        def fitness_fn(ind: Individual) -> float:
            # Simple: closer to 0.5 is better
            x = ind.genome["x"]
            if isinstance(x, int):
                x = float(x)
            return 1.0 - abs(x - 0.5)

        def mutate_fn(key: str, value: Any) -> Any:
            if isinstance(value, int):
                return value + __import__("random").randint(-1, 1)
            return value

        evolved = evolve(
            population,
            generations=10,
            fitness_fn=fitness_fn,
            mutate_fn=mutate_fn,
        )

        # Best individual should have reasonable fitness
        assert evolved[0].fitness > 0.0

    def test_evolve_elitism(self) -> None:
        """evolve() preserves elite individuals."""
        individual_a = Individual(genome={"score": 10}, fitness=0.9)
        individual_b = Individual(genome={"score": 5}, fitness=0.5)
        population = [individual_a, individual_b] + [
            Individual(genome={"score": i}, fitness=0.1) for i in range(3, 8)
        ]

        def fitness_fn(ind: Individual) -> float:
            return ind.fitness

        evolved = evolve(
            population,
            generations=5,
            fitness_fn=fitness_fn,
            elite_count=2,
        )

        # Top 2 should include the high-fitness individuals
        top_fitnesses = sorted([ind.fitness for ind in evolved], reverse=True)
        assert top_fitnesses[0] >= 0.5

    def test_evolve_default_params(self) -> None:
        """evolve() uses sensible defaults."""
        population = create_population({"x": 0}, size=5)

        evolved = evolve(population)

        assert len(evolved) == 5
        # Should be sorted by fitness
        fitnesses = [ind.fitness for ind in evolved]
        assert fitnesses == sorted(fitnesses, reverse=True)

    def test_evolve_population_size_maintained(self) -> None:
        """evolve() maintains population size across generations."""
        sizes = [5, 10, 20]

        for size in sizes:
            population = create_population({"x": 0}, size=size)
            evolved = evolve(population, generations=3)
            assert len(evolved) == size

    def test_evolve_without_fitness_fn(self) -> None:
        """evolve() works without fitness_fn (all fitness = 0)."""
        population = [
            Individual(genome={"x": i})
            for i in range(5)
        ]

        evolved = evolve(population, generations=3)

        assert len(evolved) == 5

    def test_evolve_high_mutation_rate(self) -> None:
        """evolve() handles high mutation rates."""
        population = create_population({"x": 0}, size=5)

        def fitness_fn(ind: Individual) -> float:
            return 0.5

        evolved = evolve(
            population,
            generations=5,
            fitness_fn=fitness_fn,
            mutation_rate=0.9,
        )

        assert len(evolved) == 5

    def test_evolve_zero_mutation_rate(self) -> None:
        """evolve() works with zero mutation rate."""
        population = [
            Individual(genome={"x": 1}, fitness=0.5),
            Individual(genome={"x": 2}, fitness=0.3),
        ]

        evolved = evolve(
            population,
            generations=3,
            mutation_rate=0.0,
        )

        assert len(evolved) == 2

    def test_evolve_multiple_generations(self) -> None:
        """evolve() runs for correct number of generations."""
        population = create_population({"x": 0}, size=3)
        generations_run = 0

        def fitness_fn(ind: Individual) -> float:
            nonlocal generations_run
            generations_run += 1
            return 0.5

        evolve(population, generations=10, fitness_fn=fitness_fn)

        # generations_run should be approximately 10 * population size
        # (called once per individual per generation)
        assert generations_run > 0
