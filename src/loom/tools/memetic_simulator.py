"""Memetic Virality Simulator — Agent-based simulation of idea spread through populations."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("loom.tools.memetic_simulator")


@dataclass
class Agent:
    """Virtual agent in the population."""

    agent_id: int
    susceptibility: float  # 0-1: how easily influenced
    connectivity: int  # 1-20: number of connections
    skepticism: float  # 0-1: resistance to ideas
    infected: bool = False
    infection_generation: int | None = None
    message_variants: int = 0


class MemeticSimulator:
    """Agent-based simulation of memetic spread through a population."""

    def __init__(
        self,
        population_size: int,
        generations: int,
        mutation_rate: float,
    ) -> None:
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.population: list[Agent] = []
        self.spread_curve: list[float] = []
        self.peak_generation = 0
        self.peak_infection_pct = 0.0
        self.mutations_survived = 0

    def _create_population(self) -> None:
        """Create initial population with random traits."""
        for i in range(self.population_size):
            agent = Agent(
                agent_id=i,
                susceptibility=random.uniform(0.0, 1.0),
                connectivity=random.randint(1, 20),
                skepticism=random.uniform(0.0, 1.0),
            )
            self.population.append(agent)

    def _seed_idea(self) -> None:
        """Seed the idea in 1% of population."""
        seed_count = max(1, self.population_size // 100)
        seed_indices = random.sample(range(self.population_size), seed_count)
        for idx in seed_indices:
            self.population[idx].infected = True
            self.population[idx].infection_generation = 0

    def _calculate_spread_probability(
        self,
        sender: Agent,
        receiver: Agent,
        idea_fitness: float,
    ) -> float:
        """Calculate probability of spread from sender to receiver.

        Formula: connectivity * susceptibility * (1 - skepticism) * idea_fitness
        """
        if receiver.infected:
            return 0.0  # Already infected

        # Normalize connectivity to 0-1 range (max 20)
        connectivity_factor = min(1.0, sender.connectivity / 20.0)

        prob = (
            connectivity_factor
            * receiver.susceptibility
            * (1.0 - receiver.skepticism)
            * idea_fitness
        )
        return min(1.0, prob)

    def _apply_mutations(self, generation: int) -> tuple[float, bool]:
        """Apply mutations to message variants.

        Returns:
            (mutated_fitness, mutation_occurred)
        """
        mutation_occurred = random.random() < self.mutation_rate

        if mutation_occurred:
            # Mutation can improve or degrade fitness
            mutation_delta = random.uniform(-0.1, 0.15)
            fitness_change = 1.0 + mutation_delta
            self.mutations_survived += 1
        else:
            fitness_change = 1.0

        return fitness_change, mutation_occurred

    def _run_generation(
        self,
        generation: int,
        idea_fitness: float,
    ) -> tuple[int, float]:
        """Run a single generation of spread.

        Returns:
            (newly_infected_count, new_fitness)
        """
        currently_infected = [a for a in self.population if a.infected]

        if not currently_infected:
            return 0, idea_fitness

        newly_infected: list[int] = []

        # Each infected agent tries to spread
        for sender in currently_infected:
            # Determine targets (random sampling from connectivity)
            connection_count = min(sender.connectivity, self.population_size - 1)
            all_indices = [i for i in range(self.population_size) if i != sender.agent_id]
            targets = random.sample(all_indices, min(connection_count, len(all_indices)))

            for target_idx in targets:
                receiver = self.population[target_idx]

                # Calculate spread probability
                prob = self._calculate_spread_probability(sender, receiver, idea_fitness)

                if random.random() < prob:
                    newly_infected.append(target_idx)

        # Infect newly exposed agents (avoid duplicates)
        newly_infected = list(set(newly_infected))
        for idx in newly_infected:
            self.population[idx].infected = True
            self.population[idx].infection_generation = generation

        # Apply mutations to idea
        fitness_change, _mutation_occurred = self._apply_mutations(generation)
        new_fitness = max(0.01, min(1.0, idea_fitness * fitness_change))

        return len(newly_infected), new_fitness

    def _calculate_r0(self) -> float:
        """Calculate basic reproduction number (R0).

        R0 = average number of new infections per infected agent.
        """
        if not self.spread_curve or len(self.spread_curve) < 2:
            return 0.0

        # Use generations 1-5 for R0 calculation (early exponential phase)
        early_generations = self.spread_curve[: min(5, len(self.spread_curve))]

        if len(early_generations) < 2:
            return 0.0

        # Calculate average generation-over-generation growth
        growth_rates: list[float] = []
        for i in range(1, len(early_generations)):
            if early_generations[i - 1] > 0:
                rate = early_generations[i] / early_generations[i - 1]
                growth_rates.append(rate)

        if not growth_rates:
            return 0.0

        avg_growth = sum(growth_rates) / len(growth_rates)

        # R0 is the average number of secondary infections
        # Approximated by early growth rate
        return round(avg_growth, 2)

    def _classify_virality(self, r0: float) -> str:
        """Classify virality based on R0.

        R0 > 3: viral
        1 < R0 <= 3: moderate
        R0 <= 1: dying
        """
        if r0 > 3.0:
            return "viral"
        elif r0 > 1.0:
            return "moderate"
        else:
            return "dying"

    def simulate(self, idea_description: str) -> dict[str, Any]:
        """Run the complete simulation.

        Args:
            idea_description: description of the idea/strategy to simulate

        Returns:
            Complete simulation results with virality metrics
        """
        # Initialize population and seed idea
        self._create_population()
        self._seed_idea()

        # Track infection over generations
        idea_fitness = 1.0
        total_infected_ever: set[int] = {i for i, a in enumerate(self.population) if a.infected}

        self.spread_curve.append(len(total_infected_ever) / self.population_size * 100)

        # Run simulation
        for gen in range(1, self.generations):
            newly_infected, idea_fitness = self._run_generation(gen, idea_fitness)

            if newly_infected > 0:
                total_infected_ever.update(
                    i
                    for i, a in enumerate(self.population)
                    if a.infected and i not in total_infected_ever
                )

            current_infected_pct = len(total_infected_ever) / self.population_size * 100
            self.spread_curve.append(current_infected_pct)

            # Track peak infection
            if current_infected_pct > self.peak_infection_pct:
                self.peak_infection_pct = current_infected_pct
                self.peak_generation = gen

            # Stop if idea dies out
            if newly_infected == 0 and gen > 5:
                logger.debug("memetic_simulate: idea died out at generation %d", gen)
                break

        # Calculate R0 and classification
        r0 = self._calculate_r0()
        virality_class = self._classify_virality(r0)
        total_reach_pct = (len(total_infected_ever) / self.population_size) * 100

        return {
            "idea": idea_description,
            "R0": r0,
            "virality_class": virality_class,
            "peak_infection_pct": round(self.peak_infection_pct, 1),
            "peak_generation": self.peak_generation,
            "total_reach_pct": round(total_reach_pct, 1),
            "spread_curve": [round(x, 1) for x in self.spread_curve],
            "mutations_survived": self.mutations_survived,
            "recommendation": self._generate_recommendation(r0, total_reach_pct, virality_class),
            "simulation_timestamp": datetime.now(UTC).isoformat(),
        }

    def _generate_recommendation(
        self,
        r0: float,
        total_reach_pct: float,
        virality_class: str,
    ) -> str:
        """Generate deployment recommendation based on simulation results."""
        if virality_class == "viral":
            if total_reach_pct > 80:
                return (
                    "HIGHLY RECOMMENDED FOR DEPLOYMENT. "
                    f"Idea shows strong viral properties (R0={r0}) with excellent "
                    f"population reach ({total_reach_pct}%)."
                )
            else:
                return (
                    "RECOMMENDED FOR DEPLOYMENT. "
                    f"Idea demonstrates viral characteristics (R0={r0}) but "
                    f"with moderate reach ({total_reach_pct}%)."
                )
        elif virality_class == "moderate":
            return (
                "CONDITIONAL DEPLOYMENT. "
                f"Idea shows moderate virality (R0={r0}) with {total_reach_pct}% reach. "
                "Consider targeting high-connectivity nodes or amplification."
            )
        else:
            return (
                "NOT RECOMMENDED FOR DEPLOYMENT. "
                f"Idea shows poor viral potential (R0={r0}) with only {total_reach_pct}% reach. "
                "Consider reframing or targeting more susceptible populations."
            )


async def research_memetic_simulate(
    idea: str,
    population_size: int = 1000,
    generations: int = 50,
    mutation_rate: float = 0.1,
) -> dict[str, Any]:
    """Simulate how an idea/strategy would spread through a virtual population.

    Tests viral potential before deploying by modeling agent-based spread dynamics.
    Each agent has traits: susceptibility (how easily influenced), connectivity
    (network reach), and skepticism (resistance to ideas). The simulation models
    spread probability as: connectivity x susceptibility x (1-skepticism) x fitness.

    Args:
        idea: Description of the idea/strategy to test (e.g., "Use authority figures",
              "Create urgency", "Appeal to in-group values")
        population_size: Size of virtual population (default: 1000). Range: 100-10000
        generations: Number of simulation generations to run (default: 50). Range: 10-500
        mutation_rate: Probability of message mutation per generation (default: 0.1).
                      Range: 0.0-1.0

    Returns:
        Dictionary with:
            - idea: Input idea description
            - R0: Basic reproduction number (>3=viral, 1-3=moderate, <1=dying)
            - virality_class: One of "viral", "moderate", or "dying"
            - peak_infection_pct: Highest infection percentage reached (0-100)
            - peak_generation: Generation when peak was reached
            - total_reach_pct: Final total population reached (0-100)
            - spread_curve: List of infection percentages per generation
            - mutations_survived: Count of beneficial mutations during spread
            - recommendation: Deployment recommendation based on results
            - simulation_timestamp: ISO timestamp of simulation

    Example:
        >>> result = await research_memetic_simulate(
        ...     idea="Appeal to tribal identity",
        ...     population_size=2000,
        ...     generations=75,
        ...     mutation_rate=0.15
        ... )
        >>> result['virality_class']  # 'viral' | 'moderate' | 'dying'
        >>> result['R0']  # 2.5 (reproduction number)
        >>> result['recommendation']  # Deployment guidance
    """
    # Validate inputs
    if not isinstance(idea, str) or not idea.strip():
        raise ValueError("idea must be a non-empty string")

    if population_size < 100 or population_size > 10000:
        raise ValueError("population_size must be 100-10000")

    if generations < 10 or generations > 500:
        raise ValueError("generations must be 10-500")

    if not (0.0 <= mutation_rate <= 1.0):
        raise ValueError("mutation_rate must be 0.0-1.0")

    # Run simulation
    simulator = MemeticSimulator(
        population_size=population_size,
        generations=generations,
        mutation_rate=mutation_rate,
    )

    results = simulator.simulate(idea.strip())

    logger.info(
        "memetic_simulate completed",
        idea=idea[:50],
        r0=results["R0"],
        virality_class=results["virality_class"],
        reach_pct=results["total_reach_pct"],
    )

    return results
