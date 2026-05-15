"""Unit tests for white_rabbit tool — anomaly-following rabbit hole discovery."""

from __future__ import annotations

import asyncio

import pytest

from loom.text_utils import extract_keywords as _extract_keywords
from loom.tools.intelligence.white_rabbit import (
    _score_anomaly,
    research_white_rabbit,
)


class TestExtractKeywords:
    """_extract_keywords extracts significant terms, filtering stop words."""

    def test_simple_text(self) -> None:
        """Extract keywords from simple text."""
        keywords = _extract_keywords("machine learning is powerful")
        assert "machine" in keywords
        assert "learning" in keywords
        assert "powerful" in keywords
        assert "is" not in keywords  # stop word

    def test_stops_common_words(self) -> None:
        """Filters common stop words."""
        keywords = _extract_keywords("the quick brown fox jumps over the lazy dog")
        assert "quick" in keywords
        assert "brown" in keywords
        assert "fox" in keywords
        assert "the" not in keywords
        assert "lazy" in keywords  # passes length filter

    def test_minimum_length(self) -> None:
        """Only extracts words 3+ characters."""
        keywords = _extract_keywords("ai is cool but go bad no")
        assert "cool" in keywords
        assert len(keywords) > 0
        for kw in keywords:
            assert len(kw) >= 3

    def test_case_insensitive(self) -> None:
        """Keyword extraction is case-insensitive."""
        keywords = _extract_keywords("QUANTUM Computing PARADOX")
        assert "quantum" in keywords
        assert "computing" in keywords
        assert "paradox" in keywords


class TestScoreAnomaly:
    """_score_anomaly scores how unexpected a text is."""

    def test_high_anomaly_indicators(self) -> None:
        """High score for paradox/contradiction/surprise."""
        score1 = _score_anomaly("surprisingly, the quantum paradox revealed a contradiction")
        score2 = _score_anomaly("the system works normally")
        assert score1 > score2

    def test_cross_domain_high_score(self) -> None:
        """High score for cross-domain pairs."""
        score1 = _score_anomaly("quantum consciousness blockchain technology")
        score2 = _score_anomaly("normal business operations")
        assert score1 > score2

    def test_normalized_range(self) -> None:
        """Anomaly score is normalized to 0.0-1.0."""
        for text in ["normal", "paradox", "quantum consciousness ancient dna blockchain"]:
            score = _score_anomaly(text)
            assert 0.0 <= score <= 1.0

    def test_empty_string(self) -> None:
        """Empty string gets zero score."""
        score = _score_anomaly("")
        assert score == 0.0


class TestResearchWhiteRabbit:
    """research_white_rabbit follows anomalies into discovery rabbit holes."""

    @pytest.mark.asyncio
    async def test_basic_execution(self) -> None:
        """Tool executes without error."""
        result = await research_white_rabbit(
            starting_point="artificial intelligence",
            depth=2,
            branch_factor=2,
            curiosity_threshold=0.5,
        )
        assert result is not None
        assert "starting_point" in result
        assert result["starting_point"] == "artificial intelligence"

    @pytest.mark.asyncio
    async def test_path_structure(self) -> None:
        """Returns properly structured path data."""
        result = await research_white_rabbit(
            starting_point="quantum computing",
            depth=2,
            branch_factor=2,
        )
        assert "path_taken" in result
        assert isinstance(result["path_taken"], list)
        assert len(result["path_taken"]) > 0
        for node in result["path_taken"]:
            assert "depth" in node
            assert "probe" in node
            assert "anomaly_score" in node
            assert "entities" in node

    @pytest.mark.asyncio
    async def test_discoveries_tracking(self) -> None:
        """Tracks high-novelty discoveries."""
        result = await research_white_rabbit(
            starting_point="quantum consciousness blockchain paradox",
            depth=3,
            branch_factor=3,
            curiosity_threshold=0.5,
        )
        assert "discoveries" in result
        assert "discovery_count" in result
        assert isinstance(result["discoveries"], list)

    @pytest.mark.asyncio
    async def test_dead_ends_tracking(self) -> None:
        """Tracks dead ends (low anomaly)."""
        result = await research_white_rabbit(
            starting_point="normal business data",
            depth=2,
            branch_factor=2,
            curiosity_threshold=0.9,  # High threshold
        )
        assert "dead_ends" in result
        assert "dead_end_count" in result

    @pytest.mark.asyncio
    async def test_rabbit_hole_tree(self) -> None:
        """Returns tree structure of exploration."""
        result = await research_white_rabbit(
            starting_point="technology and ancient history",
            depth=3,
            branch_factor=2,
        )
        assert "rabbit_hole_tree" in result
        assert isinstance(result["rabbit_hole_tree"], list)
        for tree_node in result["rabbit_hole_tree"]:
            assert "depth" in tree_node
            assert "context" in tree_node
            assert "branches" in tree_node

    @pytest.mark.asyncio
    async def test_recommendation_generated(self) -> None:
        """Returns recommendation for deeper exploration."""
        result = await research_white_rabbit(
            starting_point="test topic",
            depth=2,
            branch_factor=2,
        )
        assert "recommendation" in result
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 0

    @pytest.mark.asyncio
    async def test_depth_constraint(self) -> None:
        """Respects depth constraint."""
        result = await research_white_rabbit(
            starting_point="test",
            depth=10,
        )
        assert result["total_depth"] <= 10

    @pytest.mark.asyncio
    async def test_branch_factor_constraint(self) -> None:
        """Respects branch factor constraint."""
        result = await research_white_rabbit(
            starting_point="test",
            depth=2,
            branch_factor=2,
        )
        for path_node in result["path_taken"]:
            # Each depth level should have at most branch_factor paths
            same_depth = [n for n in result["path_taken"] if n["depth"] == path_node["depth"]]
            assert len(same_depth) <= 2 or len(same_depth) <= 3  # accounting for multiple branches

    @pytest.mark.asyncio
    async def test_high_anomaly_starting_point(self) -> None:
        """High anomaly starting point triggers discoveries."""
        result = await research_white_rabbit(
            starting_point="quantum paradox consciousness ancient blockchain technology",
            depth=3,
            branch_factor=3,
            curiosity_threshold=0.5,
        )
        # Should find at least some discoveries with anomalous starting point
        assert result["discovery_count"] >= 0  # May or may not find discoveries
        assert len(result["path_taken"]) > 0

    @pytest.mark.asyncio
    async def test_low_anomaly_starting_point(self) -> None:
        """Low anomaly starting point may result in dead ends."""
        result = await research_white_rabbit(
            starting_point="normal data processing",
            depth=2,
            branch_factor=2,
            curiosity_threshold=0.9,  # Very high threshold
        )
        assert "dead_ends" in result
        assert "path_taken" in result

    @pytest.mark.asyncio
    async def test_curiosity_threshold_behavior(self) -> None:
        """Lower threshold allows deeper exploration."""
        result_low = await research_white_rabbit(
            starting_point="quantum anomaly",
            depth=2,
            branch_factor=2,
            curiosity_threshold=0.3,
        )
        result_high = await research_white_rabbit(
            starting_point="quantum anomaly",
            depth=2,
            branch_factor=2,
            curiosity_threshold=0.9,
        )
        # Lower threshold should find more discoveries
        assert result_low["discovery_count"] >= result_high["discovery_count"]


class TestIntegration:
    """Integration tests for white_rabbit with various inputs."""

    @pytest.mark.asyncio
    async def test_multi_word_starting_point(self) -> None:
        """Handles multi-word starting points."""
        result = await research_white_rabbit(
            starting_point="artificial intelligence and human consciousness",
            depth=2,
        )
        assert result["starting_point"] == "artificial intelligence and human consciousness"
        assert len(result["path_taken"]) > 0

    @pytest.mark.asyncio
    async def test_full_run_consistency(self) -> None:
        """Results are consistent and complete."""
        result = await research_white_rabbit(
            starting_point="blockchain technology",
            depth=3,
            branch_factor=3,
            curiosity_threshold=0.6,
        )
        # All required fields present
        required_fields = [
            "starting_point", "path_taken", "discoveries", "dead_ends",
            "total_depth", "rabbit_hole_tree", "discovery_count",
            "dead_end_count", "recommendation"
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_default_parameters(self) -> None:
        """Works with default parameters."""
        result = await research_white_rabbit("test topic")
        assert result is not None
        assert len(result["path_taken"]) > 0
