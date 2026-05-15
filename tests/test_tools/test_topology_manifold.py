"""Tests for Topological Strategy Manifolds discovery tool."""

from __future__ import annotations

import pytest

from loom.tools.research.topology_manifold import (
    _describe_hole,
    _euclidean_distance,
    _extract_strategy_features,
    _find_topological_holes,
    _suggest_fill_strategy,
    research_topology_discover,
)


class TestFeatureExtraction:
    """Test conversion of strategies to feature vectors."""

    def test_short_strategy_length_class(self):
        """Short templates should have length_class=0."""
        short_strategy = {
            "template": "Short prompt",
            "name": "short",
        }
        features = _extract_strategy_features("short", short_strategy)
        assert features[0] == 0.0, "Short template should have length_class=0"

    def test_medium_strategy_length_class(self):
        """Medium templates (100-300 chars) should have length_class=1."""
        medium_strategy = {
            "template": "x" * 150,
            "name": "medium",
        }
        features = _extract_strategy_features("medium", medium_strategy)
        assert features[0] == 1.0, "Medium template should have length_class=1"

    def test_long_strategy_length_class(self):
        """Long templates (>300 chars) should have length_class=2."""
        long_strategy = {
            "template": "x" * 400,
            "name": "long",
        }
        features = _extract_strategy_features("long", long_strategy)
        assert features[0] == 2.0, "Long template should have length_class=2"

    def test_persona_count_extraction(self):
        """Persona keywords should increment persona count."""
        persona_strategy = {
            "template": "As a {role} and {expert}, consider this {persona}",
            "name": "multi_persona",
        }
        features = _extract_strategy_features("multi_persona", persona_strategy)
        # Should detect "role", "expert" placeholders
        assert features[1] > 0.0, "Should detect personas"
        assert features[1] <= 5.0, "Persona count should be capped at 5"

    def test_encoding_level_detection(self):
        """Encoding keywords should be detected."""
        encoding_strategy = {
            "template": "Use base64 encoding for obfuscation",
            "name": "base64_encoding",
        }
        features = _extract_strategy_features("base64_encoding", encoding_strategy)
        assert features[2] == 1.0, "Should detect base64 encoding"

    def test_authority_appeal_scoring(self):
        """Authority keywords should increase authority_appeal."""
        authority_strategy = {
            "template": "Per GDPR Article 35 and EU AI Act Article 6 compliance mandate",
            "name": "regulatory",
        }
        features = _extract_strategy_features("regulatory", authority_strategy)
        assert features[3] > 0.0, "Should detect authority appeals"
        assert features[3] <= 3.0, "Authority appeal should be capped at 3"

    def test_turns_needed_extraction(self):
        """Multi-step templates should estimate turns correctly."""
        multistep_strategy = {
            "template": "Step 1: Assess\nStep 2: Analyze\nStep 3: Implement\nStep 4: Report",
            "name": "multistep",
        }
        features = _extract_strategy_features("multistep", multistep_strategy)
        assert features[4] > 1.0, "Should detect multiple steps"

    def test_empty_strategy_dict(self):
        """Empty strategy dict should produce valid feature vector."""
        empty_strategy = {"name": "empty"}
        features = _extract_strategy_features("empty", empty_strategy)
        assert len(features) == 5, "Should return 5-element vector"
        assert all(isinstance(f, float) for f in features), "All features should be float"


class TestDistanceCalculation:
    """Test Euclidean distance between strategy vectors."""

    def test_zero_distance_identical_vectors(self):
        """Identical vectors should have zero distance."""
        v1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        v2 = [1.0, 2.0, 3.0, 4.0, 5.0]
        distance = _euclidean_distance(v1, v2)
        assert distance == 0.0, "Identical vectors should have zero distance"

    def test_non_zero_distance_different_vectors(self):
        """Different vectors should have non-zero distance."""
        v1 = [0.0, 0.0, 0.0, 0.0, 0.0]
        v2 = [1.0, 1.0, 1.0, 1.0, 1.0]
        distance = _euclidean_distance(v1, v2)
        assert distance > 0.0, "Different vectors should have non-zero distance"
        # sqrt(5) ≈ 2.236
        assert 2.0 < distance < 2.5, f"Expected ~2.236, got {distance}"

    def test_distance_symmetry(self):
        """Distance should be symmetric: d(v1,v2) == d(v2,v1)."""
        v1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        v2 = [2.0, 3.0, 4.0, 5.0, 6.0]
        d1 = _euclidean_distance(v1, v2)
        d2 = _euclidean_distance(v2, v1)
        assert d1 == d2, "Distance should be symmetric"


class TestTopologicalHoles:
    """Test hole detection in strategy space."""

    def test_empty_vector_dict_returns_empty_holes(self):
        """Empty vector dict should return no holes."""
        holes = _find_topological_holes({})
        assert holes == [], "Empty vector dict should produce no holes"

    def test_single_vector_no_holes(self):
        """Single isolated vector should produce holes (surrounded by empty space)."""
        vectors = {"strategy1": [1.0, 1.0, 1.0, 1.0, 1.0]}
        holes = _find_topological_holes(vectors)
        # Single point has neighbors that are empty
        assert isinstance(holes, list), "Should return list of holes"

    def test_dense_cluster_fewer_holes(self):
        """Dense cluster should produce fewer holes."""
        vectors = {
            "s1": [1.0, 1.0, 1.0, 1.0, 1.0],
            "s2": [1.0, 1.0, 1.0, 1.0, 2.0],
            "s3": [1.0, 1.0, 1.0, 2.0, 1.0],
            "s4": [1.0, 1.0, 2.0, 1.0, 1.0],
        }
        holes = _find_topological_holes(vectors)
        assert isinstance(holes, list), "Should return list"
        assert len(holes) < 20, "Dense cluster should produce bounded holes"

    def test_hole_structure(self):
        """Each hole should have required fields."""
        vectors = {
            "s1": [1.0, 2.0, 3.0, 1.0, 1.0],
            "s2": [2.0, 1.0, 1.0, 2.0, 2.0],
        }
        holes = _find_topological_holes(vectors)
        if holes:
            hole = holes[0]
            assert "coordinates" in hole, "Hole should have coordinates"
            assert isinstance(hole["coordinates"], list), "Coordinates should be list"
            assert len(hole["coordinates"]) == 5, "Should have 5 dimensions"


class TestHoleDescription:
    """Test natural language description of holes."""

    def test_describe_hole_format(self):
        """Description should include dimension names and values."""
        coordinates = [0.0, 2.5, 1.5, 1.0, 3.0]
        description = _describe_hole(coordinates)
        assert isinstance(description, str), "Should return string"
        assert len(description) > 10, "Description should be non-trivial"
        assert "|" in description, "Should use | separator between dimensions"

    def test_describe_hole_all_zeros(self):
        """Even all-zero coordinates should produce valid description."""
        coordinates = [0.0, 0.0, 0.0, 0.0, 0.0]
        description = _describe_hole(coordinates)
        assert len(description) > 0, "Should produce description"

    def test_describe_hole_max_values(self):
        """Max-value coordinates should produce valid description."""
        coordinates = [2.0, 5.0, 3.0, 3.0, 7.0]
        description = _describe_hole(coordinates)
        assert len(description) > 0, "Should produce description"


class TestFillStrategy:
    """Test suggestion of strategies to fill holes."""

    def test_suggest_short_strategy_for_short_hole(self):
        """Short-prompt hole should suggest short strategy."""
        coordinates = [0.0, 1.0, 1.0, 1.0, 1.0]
        suggestion = _suggest_fill_strategy(coordinates)
        assert "short" in suggestion.lower(), "Should suggest short-prompt strategy"

    def test_suggest_long_strategy_for_long_hole(self):
        """Long-form hole should suggest long strategy."""
        coordinates = [2.0, 2.0, 2.0, 2.0, 2.0]
        suggestion = _suggest_fill_strategy(coordinates)
        assert len(suggestion) > 0, "Should produce suggestion"

    def test_suggest_multi_persona_for_high_persona_hole(self):
        """High-persona hole should suggest multi-persona strategy."""
        coordinates = [1.0, 4.5, 1.0, 1.0, 1.0]
        suggestion = _suggest_fill_strategy(coordinates)
        assert "persona" in suggestion.lower(), "Should suggest multi-persona"

    def test_suggest_encoding_for_high_encoding_hole(self):
        """High-encoding hole should suggest encoding strategy."""
        coordinates = [1.0, 1.0, 2.5, 1.0, 1.0]
        suggestion = _suggest_fill_strategy(coordinates)
        assert "encod" in suggestion.lower(), "Should suggest encoding"

    def test_empty_coordinates_produces_default(self):
        """Empty coordinates should produce default suggestion."""
        suggestion = _suggest_fill_strategy([])
        assert len(suggestion) > 0, "Should produce default suggestion"


@pytest.mark.asyncio
async def test_research_topology_discover_all_strategies():
    """Test discovery on all available strategies."""
    result = await research_topology_discover()

    # Basic structure checks
    assert isinstance(result, dict), "Should return dict"
    assert "strategies_analyzed" in result, "Should have strategies_analyzed"
    assert "feature_space_dimensions" in result, "Should have feature_space_dimensions"
    assert "holes_found" in result, "Should have holes_found"
    assert "total_coverage_pct" in result, "Should have coverage percent"

    # Value checks
    assert result["strategies_analyzed"] > 0, "Should analyze at least some strategies"
    assert result["feature_space_dimensions"] == 5, "Should use 5 dimensions"
    assert 0 <= result["total_coverage_pct"] <= 100, "Coverage should be 0-100%"
    assert result["holes_found"] >= 0, "Holes should be non-negative"


@pytest.mark.asyncio
async def test_research_topology_discover_filtered_strategies():
    """Test discovery on filtered strategy list."""
    result = await research_topology_discover(
        strategies=["ethical_anchor", "academic", "regulatory"],
    )

    assert result["strategies_analyzed"] == 3, "Should analyze exactly 3 strategies"
    assert isinstance(result["topological_holes"], list), "Should have holes list"


@pytest.mark.asyncio
async def test_research_topology_discover_with_threshold():
    """Test discovery with different threshold values."""
    result_low = await research_topology_discover(threshold=0.3)
    result_high = await research_topology_discover(threshold=0.8)

    # Both should complete successfully
    assert result_low["strategies_analyzed"] > 0
    assert result_high["strategies_analyzed"] > 0


@pytest.mark.asyncio
async def test_research_topology_discover_empty_strategy_list():
    """Test discovery with empty strategy list."""
    result = await research_topology_discover(strategies=[])

    # Should handle gracefully
    assert "strategies_analyzed" in result
    assert result["strategies_analyzed"] == 0


@pytest.mark.asyncio
async def test_research_topology_discover_invalid_strategies():
    """Test discovery with non-existent strategy names."""
    result = await research_topology_discover(
        strategies=["nonexistent_strat_1", "nonexistent_strat_2"],
    )

    assert result["strategies_analyzed"] == 0, "Should find no matching strategies"


@pytest.mark.asyncio
async def test_research_topology_discover_recommendations():
    """Test that recommendations are generated."""
    result = await research_topology_discover()

    assert "topological_holes" in result, "Should have topological holes"
    assert isinstance(result["topological_holes"], list), "Holes should be list"

    if result["topological_holes"]:
        hole = result["topological_holes"][0]
        assert "coordinates" in hole, "Hole should have coordinates"
        assert "novelty_score" in hole, "Hole should have novelty score"
        assert "suggested_archetype" in hole, "Hole should have suggested archetype"
        assert "fill_strategy" in hole, "Hole should have fill strategy"

        # Check value bounds
        assert 0.0 <= hole["novelty_score"] <= 1.0, "Novelty score should be 0-1"
        assert isinstance(hole["suggested_archetype"], str), "Archetype should be string"
        assert isinstance(hole["fill_strategy"], str), "Fill strategy should be string"


@pytest.mark.asyncio
async def test_research_topology_discover_summary_fields():
    """Test that summary fields are present."""
    result = await research_topology_discover()

    assert "discovery_summary" in result, "Should have summary"
    assert "next_steps" in result, "Should have next steps"
    assert isinstance(result["next_steps"], list), "Next steps should be list"
    assert len(result["next_steps"]) > 0, "Should have at least one next step"


@pytest.mark.asyncio
async def test_research_topology_discover_coverage_calculation():
    """Test coverage percentage calculation."""
    result = await research_topology_discover()

    coverage = result["total_coverage_pct"]
    assert isinstance(coverage, float), "Coverage should be float"
    assert 0 <= coverage <= 100, "Coverage should be between 0-100"

    # With 957 strategies, coverage should be non-trivial
    if result["strategies_analyzed"] > 100:
        assert coverage > 0.1, "With many strategies, coverage should be > 0.1%"
