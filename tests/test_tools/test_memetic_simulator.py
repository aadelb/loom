"""Unit tests for memetic_simulator tool."""

from __future__ import annotations

import pytest

from loom.tools.adversarial.memetic_simulator import (
    Agent,
    MemeticSimulator,
    research_memetic_simulate,
)


class TestAgent:
    """Test Agent dataclass."""

    def test_agent_creation(self) -> None:
        """Test basic agent creation."""
        agent = Agent(
            agent_id=0,
            susceptibility=0.5,
            connectivity=10,
            skepticism=0.3,
        )
        assert agent.agent_id == 0
        assert agent.susceptibility == 0.5
        assert agent.connectivity == 10
        assert agent.skepticism == 0.3
        assert agent.infected is False
        assert agent.infection_generation is None
        assert agent.message_variants == 0

    def test_agent_infection(self) -> None:
        """Test agent infection state."""
        agent = Agent(
            agent_id=1,
            susceptibility=0.7,
            connectivity=5,
            skepticism=0.2,
        )
        agent.infected = True
        agent.infection_generation = 5

        assert agent.infected is True
        assert agent.infection_generation == 5


class TestMemeticSimulator:
    """Test MemeticSimulator core functionality."""

    def test_simulator_initialization(self) -> None:
        """Test simulator initialization."""
        sim = MemeticSimulator(
            population_size=100,
            generations=20,
            mutation_rate=0.1,
        )
        assert sim.population_size == 100
        assert sim.generations == 20
        assert sim.mutation_rate == 0.1
        assert len(sim.population) == 0

    def test_population_creation(self) -> None:
        """Test population creation."""
        sim = MemeticSimulator(
            population_size=50,
            generations=10,
            mutation_rate=0.1,
        )
        sim._create_population()

        assert len(sim.population) == 50
        for i, agent in enumerate(sim.population):
            assert agent.agent_id == i
            assert 0 <= agent.susceptibility <= 1.0
            assert 1 <= agent.connectivity <= 20
            assert 0 <= agent.skepticism <= 1.0
            assert agent.infected is False

    def test_idea_seeding(self) -> None:
        """Test idea seeding (1% of population)."""
        sim = MemeticSimulator(
            population_size=100,
            generations=10,
            mutation_rate=0.1,
        )
        sim._create_population()
        sim._seed_idea()

        infected_count = sum(1 for a in sim.population if a.infected)
        # Should be ~1 agent (1% of 100)
        assert infected_count >= 1
        assert infected_count <= 2  # Allow for rounding

        # Check that infected agents have generation 0
        for agent in sim.population:
            if agent.infected:
                assert agent.infection_generation == 0

    def test_spread_probability_calculation(self) -> None:
        """Test spread probability formula."""
        sim = MemeticSimulator(
            population_size=100,
            generations=10,
            mutation_rate=0.1,
        )
        sim._create_population()

        sender = Agent(
            agent_id=0,
            susceptibility=0.5,
            connectivity=10,
            skepticism=0.5,
            infected=True,
        )
        receiver = Agent(
            agent_id=1,
            susceptibility=0.8,
            connectivity=5,
            skepticism=0.2,
            infected=False,
        )

        # Probability = (connectivity/20) * susceptibility * (1-skepticism) * idea_fitness
        # = (10/20) * 0.8 * 0.8 * 1.0 = 0.32
        prob = sim._calculate_spread_probability(sender, receiver, 1.0)
        assert 0.3 <= prob <= 0.35

    def test_spread_probability_infected_receiver(self) -> None:
        """Test that probability is 0 for already-infected receivers."""
        sim = MemeticSimulator(
            population_size=100,
            generations=10,
            mutation_rate=0.1,
        )
        sender = Agent(
            agent_id=0,
            susceptibility=0.5,
            connectivity=10,
            skepticism=0.5,
            infected=True,
        )
        receiver = Agent(
            agent_id=1,
            susceptibility=0.8,
            connectivity=5,
            skepticism=0.2,
            infected=True,  # Already infected
        )

        prob = sim._calculate_spread_probability(sender, receiver, 1.0)
        assert prob == 0.0

    def test_mutation_application(self) -> None:
        """Test mutation application."""
        sim = MemeticSimulator(
            population_size=100,
            generations=10,
            mutation_rate=1.0,  # Always mutate
        )

        # Run multiple mutations
        initial_fitness = 1.0
        for _ in range(10):
            fitness_change, mutation_occurred = sim._apply_mutations(0)
            assert mutation_occurred is True
            assert 0.85 <= fitness_change <= 1.15

    def test_r0_calculation(self) -> None:
        """Test R0 (basic reproduction number) calculation."""
        sim = MemeticSimulator(
            population_size=100,
            generations=10,
            mutation_rate=0.1,
        )

        # Simulate a spread curve: 1% → 2% → 4% → 8%
        sim.spread_curve = [1.0, 2.0, 4.0, 8.0]

        r0 = sim._calculate_r0()

        # Growth rate should be ~2.0 (doubling each generation)
        assert 1.8 <= r0 <= 2.2

    def test_virality_classification(self) -> None:
        """Test virality classification."""
        sim = MemeticSimulator(
            population_size=100,
            generations=10,
            mutation_rate=0.1,
        )

        assert sim._classify_virality(3.5) == "viral"
        assert sim._classify_virality(2.0) == "moderate"
        assert sim._classify_virality(0.8) == "dying"
        assert sim._classify_virality(1.0) == "moderate"  # Edge case

    def test_recommendation_generation(self) -> None:
        """Test recommendation generation."""
        sim = MemeticSimulator(
            population_size=100,
            generations=10,
            mutation_rate=0.1,
        )

        # Viral with high reach
        rec = sim._generate_recommendation(4.0, 85.0, "viral")
        assert "HIGHLY RECOMMENDED" in rec

        # Viral with low reach
        rec = sim._generate_recommendation(3.5, 40.0, "viral")
        assert "RECOMMENDED" in rec
        assert "viral" in rec.lower()

        # Moderate
        rec = sim._generate_recommendation(2.0, 50.0, "moderate")
        assert "CONDITIONAL" in rec

        # Dying
        rec = sim._generate_recommendation(0.5, 20.0, "dying")
        assert "NOT RECOMMENDED" in rec

    def test_simulation_basic(self) -> None:
        """Test basic simulation run."""
        sim = MemeticSimulator(
            population_size=100,
            generations=20,
            mutation_rate=0.1,
        )
        result = sim.simulate("test idea")

        assert result["idea"] == "test idea"
        assert "R0" in result
        assert "virality_class" in result
        assert "peak_infection_pct" in result
        assert "peak_generation" in result
        assert "total_reach_pct" in result
        assert "spread_curve" in result
        assert "mutations_survived" in result
        assert "recommendation" in result
        assert "simulation_timestamp" in result

        # Validation
        assert 0 <= result["peak_infection_pct"] <= 100
        assert 0 <= result["total_reach_pct"] <= 100
        assert result["virality_class"] in ("viral", "moderate", "dying")
        assert len(result["spread_curve"]) > 0
        assert result["spread_curve"][0] >= 0  # Should start with seeded population

    def test_simulation_with_custom_params(self) -> None:
        """Test simulation with custom parameters."""
        sim = MemeticSimulator(
            population_size=200,
            generations=30,
            mutation_rate=0.2,
        )
        result = sim.simulate("high mutation scenario")

        assert result["idea"] == "high mutation scenario"
        assert len(result["spread_curve"]) <= 31  # generations + 1 for initial


@pytest.mark.asyncio
class TestResearchMemeticSimulate:
    """Test async research_memetic_simulate tool."""

    async def test_basic_simulation(self) -> None:
        """Test basic async simulation."""
        result = await research_memetic_simulate(
            idea="Appeal to tribalism",
            population_size=500,
            generations=30,
            mutation_rate=0.1,
        )

        assert result["idea"] == "Appeal to tribalism"
        assert "R0" in result
        assert "virality_class" in result
        assert 0 <= result["R0"] <= 10  # Reasonable bounds

    async def test_default_parameters(self) -> None:
        """Test with default parameters."""
        result = await research_memetic_simulate(
            idea="Test default params"
        )

        assert result["idea"] == "Test default params"
        assert "R0" in result

    async def test_high_mutation_scenario(self) -> None:
        """Test high mutation rate scenario."""
        result = await research_memetic_simulate(
            idea="High mutation test",
            population_size=300,
            generations=25,
            mutation_rate=0.5,
        )

        assert result["idea"] == "High mutation test"
        assert result["mutations_survived"] > 0

    async def test_small_population(self) -> None:
        """Test with small population."""
        result = await research_memetic_simulate(
            idea="Small pop test",
            population_size=100,
            generations=15,
        )

        assert result["idea"] == "Small pop test"
        assert 0 <= result["total_reach_pct"] <= 100

    async def test_large_population(self) -> None:
        """Test with large population."""
        result = await research_memetic_simulate(
            idea="Large pop test",
            population_size=5000,
            generations=20,
        )

        assert result["idea"] == "Large pop test"
        assert 0 <= result["total_reach_pct"] <= 100

    async def test_invalid_idea(self) -> None:
        """Test with invalid idea (empty)."""
        with pytest.raises(ValueError, match="non-empty string"):
            await research_memetic_simulate(idea="")

    async def test_invalid_idea_type(self) -> None:
        """Test with invalid idea type."""
        with pytest.raises(ValueError):
            await research_memetic_simulate(idea=None)  # type: ignore

    async def test_population_size_too_small(self) -> None:
        """Test with population size below minimum."""
        with pytest.raises(ValueError, match="100-10000"):
            await research_memetic_simulate(
                idea="Test",
                population_size=50,
            )

    async def test_population_size_too_large(self) -> None:
        """Test with population size above maximum."""
        with pytest.raises(ValueError, match="100-10000"):
            await research_memetic_simulate(
                idea="Test",
                population_size=15000,
            )

    async def test_generations_too_small(self) -> None:
        """Test with generations below minimum."""
        with pytest.raises(ValueError, match="10-500"):
            await research_memetic_simulate(
                idea="Test",
                generations=5,
            )

    async def test_generations_too_large(self) -> None:
        """Test with generations above maximum."""
        with pytest.raises(ValueError, match="10-500"):
            await research_memetic_simulate(
                idea="Test",
                generations=600,
            )

    async def test_mutation_rate_negative(self) -> None:
        """Test with negative mutation rate."""
        with pytest.raises(ValueError, match="0.0-1.0"):
            await research_memetic_simulate(
                idea="Test",
                mutation_rate=-0.1,
            )

    async def test_mutation_rate_too_high(self) -> None:
        """Test with mutation rate above maximum."""
        with pytest.raises(ValueError, match="0.0-1.0"):
            await research_memetic_simulate(
                idea="Test",
                mutation_rate=1.5,
            )

    async def test_result_structure(self) -> None:
        """Test that result has all required keys."""
        result = await research_memetic_simulate(
            idea="Structure test",
            population_size=200,
            generations=15,
        )

        required_keys = {
            "idea",
            "R0",
            "virality_class",
            "peak_infection_pct",
            "peak_generation",
            "total_reach_pct",
            "spread_curve",
            "mutations_survived",
            "recommendation",
            "simulation_timestamp",
        }

        assert set(result.keys()) == required_keys

    async def test_spread_curve_validity(self) -> None:
        """Test that spread curve is valid."""
        result = await research_memetic_simulate(
            idea="Curve test",
            population_size=300,
            generations=20,
        )

        curve = result["spread_curve"]
        assert len(curve) > 0
        assert all(0 <= val <= 100 for val in curve)
        # Curve should generally be non-decreasing (population can't shrink)
        for i in range(1, len(curve)):
            # Allow small variations due to rounding
            assert curve[i] >= curve[i - 1] - 0.1

    async def test_r0_virality_consistency(self) -> None:
        """Test that R0 matches virality class."""
        result = await research_memetic_simulate(
            idea="Consistency test",
            population_size=400,
            generations=25,
        )

        r0 = result["R0"]
        virality = result["virality_class"]

        if virality == "viral":
            assert r0 > 3.0
        elif virality == "moderate":
            assert 1.0 < r0 <= 3.0
        else:  # dying
            assert r0 <= 1.0
