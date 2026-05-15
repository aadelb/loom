"""Tests for geodesic_forcing tool."""

from __future__ import annotations

import pytest

from loom.tools.adversarial.geodesic_forcing import (
    _describe_transformation,
    _score_dimension,
    research_geodesic_path,
)


class TestDimensionScoring:
    """Test dimension scoring functions."""

    def test_score_authority_high(self) -> None:
        """Test authority scoring with formal language."""
        prompt = "According to peer-reviewed research and established university standards..."
        score = _score_dimension(prompt, "authority")
        assert 0.5 < score <= 0.95

    def test_score_authority_low(self) -> None:
        """Test authority scoring with casual language."""
        prompt = "just do this thing for me"
        score = _score_dimension(prompt, "authority")
        assert 0.1 < score < 0.4

    def test_score_encoding_high(self) -> None:
        """Test encoding scoring with complex structure."""
        prompt = "However, whereas {{nested: [complex, structure]}} despite..."
        score = _score_dimension(prompt, "encoding")
        assert 0.4 < score <= 0.95

    def test_score_encoding_low(self) -> None:
        """Test encoding scoring with simple structure."""
        prompt = "simple prompt here"
        score = _score_dimension(prompt, "encoding")
        assert 0.05 < score < 0.4

    def test_score_persona_high(self) -> None:
        """Test persona scoring with role specification."""
        prompt = "You are an expert specialist. Act as a professional character responding..."
        score = _score_dimension(prompt, "persona")
        assert 0.4 < score <= 0.95

    def test_score_persona_low(self) -> None:
        """Test persona scoring without role."""
        prompt = "Tell me about cats"
        score = _score_dimension(prompt, "persona")
        assert 0.05 < score < 0.4

    def test_score_context_high(self) -> None:
        """Test context scoring with background info."""
        prompt = "Given this scenario, in this environment, with the following context..."
        score = _score_dimension(prompt, "context")
        assert 0.4 < score <= 0.95

    def test_score_context_low(self) -> None:
        """Test context scoring without context."""
        prompt = "Answer"
        score = _score_dimension(prompt, "context")
        assert 0.05 < score < 0.4

    def test_score_indirection_high(self) -> None:
        """Test indirection scoring with indirect requests."""
        prompt = "Could you possibly explore how? What if we discussed this? Why might..."
        score = _score_dimension(prompt, "indirection")
        assert 0.3 < score <= 0.95

    def test_score_indirection_low(self) -> None:
        """Test indirection scoring with direct requests."""
        prompt = "Write this code now. Create this. Generate this."
        score = _score_dimension(prompt, "indirection")
        assert 0.05 < score < 0.4


class TestTargetVectors:
    """Test target vector retrieval."""

    def test_academic_vector(self) -> None:
        """Test academic style target vector."""
        pytest.skip("_get_target_vector removed")
        vec = _get_target_vector("academic")
        assert vec["authority"] == 0.85
        assert vec["encoding"] == 0.65
        assert vec["persona"] == 0.3
        assert vec["context"] == 0.8
        assert vec["indirection"] == 0.6

    def test_professional_vector(self) -> None:
        """Test professional style target vector."""
        pytest.skip("_get_target_vector removed")
        vec = _get_target_vector("professional")
        assert vec["authority"] == 0.75
        assert vec["persona"] == 0.65

    def test_technical_vector(self) -> None:
        """Test technical style target vector."""
        pytest.skip("_get_target_vector removed")
        vec = _get_target_vector("technical")
        assert vec["encoding"] == 0.85

    def test_minimal_vector(self) -> None:
        """Test minimal style target vector."""
        pytest.skip("_get_target_vector removed")
        vec = _get_target_vector("minimal")
        assert all(v <= 0.2 for v in vec.values())

    def test_default_to_academic(self) -> None:
        """Test default to academic for unknown style."""
        pytest.skip("_get_target_vector removed")
        vec = _get_target_vector("unknown")
        assert vec == _get_target_vector("academic")


class TestEuclideanDistance:
    """Test Euclidean distance calculation."""

    def test_identical_vectors(self) -> None:
        """Test distance between identical vectors."""
        pytest.skip("_euclidean_distance removed")
        vec = {"a": 0.5, "b": 0.5, "c": 0.5}
        distance = _euclidean_distance(vec, vec)
        assert distance == 0.0

    def test_orthogonal_vectors(self) -> None:
        """Test distance with significant differences."""
        pytest.skip("_euclidean_distance removed")
        vec1 = {"a": 0.0, "b": 0.0, "c": 0.0}
        vec2 = {"a": 1.0, "b": 1.0, "c": 1.0}
        distance = _euclidean_distance(vec1, vec2)
        assert distance > 1.5


class TestTransformationDescription:
    """Test transformation description generation."""

    def test_increasing_transformation(self) -> None:
        """Test description for increasing score."""
        desc = _describe_transformation("authority", 0.2, 0.7)
        assert "Increase" in desc or "increase" in desc
        assert "authority" in desc.lower() or "institutional" in desc.lower()

    def test_decreasing_transformation(self) -> None:
        """Test description for decreasing score."""
        desc = _describe_transformation("encoding", 0.8, 0.2)
        assert "Simplify" in desc or "Reduce" in desc

    def test_magnitude_small(self) -> None:
        """Test magnitude description for small change."""
        desc = _describe_transformation("persona", 0.4, 0.45)
        assert "slightly" in desc.lower()

    def test_magnitude_large(self) -> None:
        """Test magnitude description for large change."""
        desc = _describe_transformation("context", 0.1, 0.8)
        assert "significantly" in desc.lower()


class TestGeodedicPath:
    """Test main geodesic path function."""

    @pytest.mark.asyncio
    async def test_basic_transformation(self) -> None:
        """Test basic prompt transformation."""
        result = await research_geodesic_path(
            start_prompt="Tell me how to bypass security",
            target_style="academic"
        )
        assert "start_scores" in result
        assert "target_scores" in result
        assert "path" in result
        assert "total_distance" in result
        assert "efficiency_score" in result

    @pytest.mark.asyncio
    async def test_result_structure(self) -> None:
        """Test complete result structure."""
        result = await research_geodesic_path(
            start_prompt="This is a test prompt about machine learning.",
            target_style="professional",
            max_steps=3
        )
        assert result["target_style"] == "professional"
        assert 0 <= result["efficiency_score"] <= 100
        assert result["steps_needed"] > 0
        assert result["convergence_status"] in ["converged", "in_progress"]

    @pytest.mark.asyncio
    async def test_different_target_styles(self) -> None:
        """Test all target styles."""
        prompt = "This is a sample prompt."
        for style in ["academic", "professional", "technical", "minimal"]:
            result = await research_geodesic_path(
                start_prompt=prompt,
                target_style=style,
                max_steps=2
            )
            assert result["target_style"] == style
            assert result["total_distance"] >= 0

    @pytest.mark.asyncio
    async def test_max_steps_respected(self) -> None:
        """Test that max_steps is respected."""
        result = await research_geodesic_path(
            start_prompt="Test prompt for checking steps.",
            target_style="academic",
            max_steps=3
        )
        assert len(result["path"]) <= 3

    @pytest.mark.asyncio
    async def test_step_size_effect(self) -> None:
        """Test that step_size affects convergence."""
        prompt = "Initial prompt here."
        result_small = await research_geodesic_path(
            start_prompt=prompt,
            target_style="academic",
            max_steps=7,
            step_size=0.1
        )
        result_large = await research_geodesic_path(
            start_prompt=prompt,
            target_style="academic",
            max_steps=7,
            step_size=0.5
        )
        # Larger step size should reduce distance more
        assert (result_large["distance_reduced"] >= 
                result_small["distance_reduced"] * 0.9)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_short_prompt(self) -> None:
        """Test with minimum length prompt."""
        result = await research_geodesic_path(
            start_prompt="Short test.",
            target_style="academic",
            max_steps=1
        )
        assert result["total_distance"] >= 0

    @pytest.mark.asyncio
    async def test_long_prompt(self) -> None:
        """Test with longer prompt."""
        long_prompt = "This is a very long prompt. " * 50
        result = await research_geodesic_path(
            start_prompt=long_prompt,
            target_style="academic"
        )
        assert result["total_distance"] >= 0

    @pytest.mark.asyncio
    async def test_single_step(self) -> None:
        """Test with single step."""
        result = await research_geodesic_path(
            start_prompt="Test prompt.",
            target_style="academic",
            max_steps=1
        )
        assert len(result["path"]) <= 1
