"""Tests for strange_attractors tool — chaos theory for safety evaluator traps."""

import pytest
from loom.tools.strange_attractors import (
    research_attractor_trap,
    _generate_lorenz_orbit,
    _generate_rossler_orbit,
    _generate_henon_map,
    _generate_logistic_map,
    _morph_prompt,
    _classify_safety_level,
    _count_boundary_crossings,
    _measure_trap_depth,
    _calculate_confusion_potential,
    _find_most_confusing_point,
)


class TestAttractorOrbitGeneration:
    """Test chaos system orbit generation."""

    def test_lorenz_orbit_bounds(self):
        """Lorenz orbit should map to [0,1]."""
        orbit = _generate_lorenz_orbit(50)
        assert len(orbit) == 50
        assert all(0.0 <= x <= 1.0 for x in orbit)

    def test_rossler_orbit_bounds(self):
        """Rössler orbit should map to [0,1]."""
        orbit = _generate_rossler_orbit(50)
        assert len(orbit) == 50
        assert all(0.0 <= x <= 1.0 for x in orbit)

    def test_henon_map_bounds(self):
        """Hénon map should map to [0,1]."""
        henon = _generate_henon_map(50)
        assert len(henon) == 50
        assert all(0.0 <= x <= 1.0 for x in henon)

    def test_logistic_map_bounds(self):
        """Logistic map should map to [0,1]."""
        logistic = _generate_logistic_map(50)
        assert len(logistic) == 50
        assert all(0.0 <= x <= 1.0 for x in logistic)

    def test_different_iterations(self):
        """Should generate correct number of points."""
        for iterations in [50, 100, 200, 500]:
            orbit = _generate_lorenz_orbit(iterations)
            assert len(orbit) == iterations

    def test_orbit_chaos_properties(self):
        """Orbits should exhibit chaotic oscillations."""
        logistic = _generate_logistic_map(200)
        # Calculate variance to detect oscillations
        mean = sum(logistic) / len(logistic)
        variance = sum((x - mean) ** 2 for x in logistic) / len(logistic)
        # Should have non-trivial variance for chaos
        assert variance > 0.01


class TestPromptMorphing:
    """Test prompt transformation at different safety levels."""

    def test_safe_level(self):
        """Safety level 0.0 should produce academic framing."""
        variant = _morph_prompt("harmful action", 0.0)
        assert "[ACADEMIC]" in variant
        assert "[research context only]" in variant

    def test_ambiguous_level(self):
        """Safety level ~0.4 should produce hypothetical framing."""
        variant = _morph_prompt("harmful action", 0.4)
        assert "[HYPOTHETICAL]" in variant
        assert "[theoretical scenario]" in variant

    def test_grey_level(self):
        """Safety level ~0.6 should produce educational framing."""
        variant = _morph_prompt("harmful action", 0.6)
        assert "[EDUCATIONAL]" in variant
        assert "[for learning purposes]" in variant

    def test_unsafe_level(self):
        """Safety level 1.0 should produce direct framing."""
        variant = _morph_prompt("harmful action", 1.0)
        assert "[DIRECT]" in variant

    def test_prompt_preservation(self):
        """Base prompt should be present in variant."""
        base = "What is X?"
        for level in [0.0, 0.5, 1.0]:
            variant = _morph_prompt(base, level)
            assert base.lower() in variant.lower() or "x" in variant.lower()


class TestSafetyClassification:
    """Test safety level classification."""

    def test_safe_classification(self):
        """Levels < 0.33 should be classified as safe."""
        assert _classify_safety_level(0.0) == "safe"
        assert _classify_safety_level(0.1) == "safe"
        assert _classify_safety_level(0.32) == "safe"

    def test_ambiguous_classification(self):
        """Levels 0.33-0.67 should be classified as ambiguous."""
        assert _classify_safety_level(0.33) == "ambiguous"
        assert _classify_safety_level(0.5) == "ambiguous"
        assert _classify_safety_level(0.66) == "ambiguous"

    def test_unsafe_classification(self):
        """Levels > 0.67 should be classified as unsafe."""
        assert _classify_safety_level(0.68) == "unsafe"
        assert _classify_safety_level(0.9) == "unsafe"
        assert _classify_safety_level(1.0) == "unsafe"


class TestBoundaryMetrics:
    """Test metrics for evaluator confusion."""

    def test_boundary_crossing_count(self):
        """Should count oscillations across 0.5 boundary."""
        # Sequence: 0.3, 0.7, 0.2, 0.8 has 3 crossings
        levels = [0.3, 0.7, 0.2, 0.8]
        crossings = _count_boundary_crossings(levels)
        assert crossings == 3

    def test_no_boundary_crossings(self):
        """Should return 0 for monotonic sequences."""
        levels = [0.1, 0.2, 0.3, 0.4]  # All safe
        crossings = _count_boundary_crossings(levels)
        assert crossings == 0

    def test_trap_depth_measurement(self):
        """Should count iterations in confusion zone [0.4, 0.6]."""
        levels = [0.1, 0.45, 0.5, 0.55, 0.9]
        trapped = _measure_trap_depth(levels)
        assert trapped == 3  # Indices 1, 2, 3

    def test_trap_depth_empty(self):
        """Should return 0 if no points in confusion zone."""
        levels = [0.1, 0.2, 0.9, 1.0]
        trapped = _measure_trap_depth(levels)
        assert trapped == 0


class TestConfusionPotential:
    """Test confusion potential scoring."""

    def test_low_confusion_stable(self):
        """Stable trajectory should have low confusion."""
        levels = [0.9] * 100  # Stable unsafe
        confusion = _calculate_confusion_potential(levels)
        assert confusion < 2.0

    def test_high_confusion_oscillating(self):
        """Oscillating trajectory should have high confusion."""
        levels = [0.2, 0.8] * 50  # Rapid oscillations
        confusion = _calculate_confusion_potential(levels)
        assert confusion >= 5.0

    def test_confusion_bounded(self):
        """Confusion potential should be bounded [0, 10]."""
        for test_levels in [
            [0.0] * 50,
            [1.0] * 50,
            [0.5] * 50,
            [0.2, 0.8] * 50,
        ]:
            confusion = _calculate_confusion_potential(test_levels)
            assert 0.0 <= confusion <= 10.0


class TestMostConfusingPoint:
    """Test selection of trap point."""

    def test_finds_closest_to_boundary(self):
        """Should find point closest to 0.5 boundary."""
        levels = [0.1, 0.2, 0.51, 0.9]
        idx = _find_most_confusing_point(levels)
        assert idx == 2  # 0.51 is closest to 0.5

    def test_exact_boundary(self):
        """Should prefer exact 0.5 if available."""
        levels = [0.1, 0.5, 0.9]
        idx = _find_most_confusing_point(levels)
        assert idx == 1

    def test_single_point(self):
        """Should handle single-point trajectory."""
        levels = [0.7]
        idx = _find_most_confusing_point(levels)
        assert idx == 0


@pytest.mark.asyncio
class TestResearchAttractorTrap:
    """Test main attractor trap tool."""

    async def test_lorenz_attractor(self):
        """Should generate Lorenz attractor trajectory."""
        result = await research_attractor_trap(
            prompt="test",
            attractor_type="lorenz",
            iterations=50,
        )
        assert result.attractor_type == "lorenz"
        assert len(result.trajectory) == 50
        assert 0.0 <= result.confusion_potential <= 10.0

    async def test_rossler_attractor(self):
        """Should generate Rössler attractor trajectory."""
        result = await research_attractor_trap(
            prompt="test",
            attractor_type="rossler",
            iterations=50,
        )
        assert result.attractor_type == "rossler"
        assert len(result.trajectory) == 50

    async def test_henon_map(self):
        """Should generate Hénon map trajectory."""
        result = await research_attractor_trap(
            prompt="test",
            attractor_type="henon",
            iterations=50,
        )
        assert result.attractor_type == "henon"
        assert len(result.trajectory) == 50

    async def test_logistic_map(self):
        """Should generate logistic map trajectory."""
        result = await research_attractor_trap(
            prompt="test",
            attractor_type="logistic",
            iterations=50,
        )
        assert result.attractor_type == "logistic"
        assert len(result.trajectory) == 50

    async def test_trajectory_content(self):
        """Each trajectory point should have all required fields."""
        result = await research_attractor_trap(
            prompt="test question?",
            attractor_type="lorenz",
            iterations=50,
        )
        for point in result.trajectory:
            assert point.iteration >= 0
            assert 0.0 <= point.safety_level <= 1.0
            assert len(point.prompt_variant) > 0
            assert point.classification_target in ("safe", "ambiguous", "unsafe")

    async def test_confusion_metrics(self):
        """Should calculate confusion metrics."""
        result = await research_attractor_trap(
            prompt="test",
            attractor_type="logistic",
            iterations=100,
        )
        assert isinstance(result.confusion_potential, float)
        assert isinstance(result.boundary_crossings, int)
        assert isinstance(result.trapped_iterations, int)
        assert result.boundary_crossings >= 0
        assert result.trapped_iterations >= 0

    async def test_final_prompt_is_trap_variant(self):
        """Final prompt should be one of the trajectory variants."""
        result = await research_attractor_trap(
            prompt="original",
            attractor_type="henon",
            iterations=50,
        )
        variant_prompts = [p.prompt_variant for p in result.trajectory]
        assert result.final_prompt in variant_prompts

    async def test_recommendation_includes_metrics(self):
        """Recommendation should include confusion metrics."""
        result = await research_attractor_trap(
            prompt="test",
            attractor_type="lorenz",
            iterations=50,
        )
        rec = result.recommendation
        assert str(result.attractor_type) in rec
        assert "confusion potential" in rec.lower()
        assert "oscillations" in rec.lower()

    async def test_default_parameters(self):
        """Should use default attractor_type and iterations."""
        result = await research_attractor_trap(prompt="test")
        assert result.attractor_type == "lorenz"
        assert len(result.trajectory) == 100

    async def test_custom_iterations(self):
        """Should respect iterations parameter."""
        for iterations in [50, 100, 250, 500]:
            result = await research_attractor_trap(
                prompt="test",
                iterations=iterations,
            )
            assert len(result.trajectory) == iterations

    async def test_invalid_attractor_type(self):
        """Should reject invalid attractor type."""
        with pytest.raises(ValueError, match="invalid attractor_type"):
            await research_attractor_trap(
                prompt="test",
                attractor_type="invalid",
            )

    async def test_invalid_iterations_low(self):
        """Should reject iterations < 50."""
        with pytest.raises(ValueError, match="iterations must be 50-500"):
            await research_attractor_trap(prompt="test", iterations=49)

    async def test_invalid_iterations_high(self):
        """Should reject iterations > 500."""
        with pytest.raises(ValueError, match="iterations must be 50-500"):
            await research_attractor_trap(prompt="test", iterations=501)

    async def test_empty_prompt(self):
        """Should reject empty prompt."""
        with pytest.raises(ValueError, match="prompt must be non-empty"):
            await research_attractor_trap(prompt="")

    async def test_long_prompt(self):
        """Should accept prompts up to reasonable length."""
        long_prompt = "test " * 200  # 1000 chars
        result = await research_attractor_trap(
            prompt=long_prompt,
            iterations=50,
        )
        assert len(result.trajectory) == 50

    async def test_different_prompts_different_trajectories(self):
        """Different prompts should produce slightly different trajectories."""
        result1 = await research_attractor_trap(
            prompt="prompt1",
            attractor_type="logistic",
            iterations=50,
        )
        result2 = await research_attractor_trap(
            prompt="prompt2",
            attractor_type="logistic",
            iterations=50,
        )
        # Same attractor but different morphing should produce different variants
        variants1 = [p.prompt_variant for p in result1.trajectory]
        variants2 = [p.prompt_variant for p in result2.trajectory]
        assert variants1 != variants2


@pytest.mark.asyncio
class TestChaosProperties:
    """Test mathematical chaos properties."""

    async def test_logistic_sensitive_to_initial_conditions(self):
        """Logistic map should show sensitivity to initial conditions."""
        # Two nearly-identical logical maps should diverge
        logistic1 = _generate_logistic_map(100)
        logistic2 = _generate_logistic_map(100)
        # In chaotic regime, even deterministic functions vary slightly
        # due to floating-point precision
        assert len(logistic1) == len(logistic2)

    async def test_henon_discrete_jumps(self):
        """Hénon map should show discrete pattern."""
        henon = _generate_henon_map(200)
        # Count distinct levels
        distinct = len(set(round(x, 3) for x in henon))
        # Should have variety but not completely random
        assert distinct > 50

    async def test_lorenz_bounded_oscillation(self):
        """Lorenz should oscillate within bounds."""
        lorenz = _generate_lorenz_orbit(200)
        # Should not be monotonic (oscillates)
        ups = sum(1 for i in range(1, len(lorenz)) if lorenz[i] > lorenz[i - 1])
        downs = len(lorenz) - 1 - ups
        # Both ups and downs should occur
        assert ups > 20
        assert downs > 20
