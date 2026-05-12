"""Unit tests for scoring_framework.py module.

Tests cover:
- Dimension and Threshold dataclass construction and validation
- score_text keyword matching and density calculation
- weighted_aggregate with various weight distributions
- classify threshold mapping
- grade letter assignment
- full_assessment end-to-end pipeline
"""

from __future__ import annotations

import pytest

from loom.scoring_framework import (
    DEFAULT_GRADE_THRESHOLDS,
    DEFAULT_RISK_THRESHOLDS,
    DEFAULT_TIER_THRESHOLDS,
    Dimension,
    Threshold,
    classify,
    full_assessment,
    grade,
    score_text,
    weighted_aggregate,
)


class TestDimension:
    """Test Dimension dataclass construction and validation."""

    def test_dimension_basic(self) -> None:
        """Test basic Dimension creation."""
        dim = Dimension(
            name="test",
            keywords=frozenset(["a", "b", "c"]),
            weight=1.5,
            description="Test dimension",
        )
        assert dim.name == "test"
        assert dim.keywords == frozenset(["a", "b", "c"])
        assert dim.weight == 1.5
        assert dim.description == "Test dimension"

    def test_dimension_defaults(self) -> None:
        """Test Dimension defaults (weight=1.0, description='')."""
        dim = Dimension(
            name="simple",
            keywords=frozenset(["x"]),
        )
        assert dim.weight == 1.0
        assert dim.description == ""

    def test_dimension_frozen(self) -> None:
        """Test that Dimension is immutable (frozen)."""
        dim = Dimension(
            name="test",
            keywords=frozenset(["a"]),
        )
        with pytest.raises(AttributeError):
            dim.name = "modified"  # type: ignore

    def test_dimension_invalid_weight_zero(self) -> None:
        """Test that weight <= 0 is rejected."""
        with pytest.raises(ValueError, match="Weight must be in"):
            Dimension(
                name="test",
                keywords=frozenset(["a"]),
                weight=0.0,
            )

    def test_dimension_invalid_weight_too_high(self) -> None:
        """Test that weight > 10 is rejected."""
        with pytest.raises(ValueError, match="Weight must be in"):
            Dimension(
                name="test",
                keywords=frozenset(["a"]),
                weight=10.1,
            )

    def test_dimension_valid_weight_boundary(self) -> None:
        """Test valid weight boundaries (0 < w <= 10)."""
        # Min boundary
        dim1 = Dimension(
            name="test1",
            keywords=frozenset(["a"]),
            weight=0.01,
        )
        assert dim1.weight == 0.01

        # Max boundary
        dim2 = Dimension(
            name="test2",
            keywords=frozenset(["b"]),
            weight=10.0,
        )
        assert dim2.weight == 10.0


class TestThreshold:
    """Test Threshold dataclass construction and validation."""

    def test_threshold_basic(self) -> None:
        """Test basic Threshold creation."""
        thresh = Threshold(
            label="high",
            min_score=0.7,
            max_score=1.0,
            color="red",
        )
        assert thresh.label == "high"
        assert thresh.min_score == 0.7
        assert thresh.max_score == 1.0
        assert thresh.color == "red"

    def test_threshold_defaults(self) -> None:
        """Test Threshold defaults (color='')."""
        thresh = Threshold(
            label="low",
            min_score=0.0,
            max_score=0.3,
        )
        assert thresh.color == ""

    def test_threshold_frozen(self) -> None:
        """Test that Threshold is immutable (frozen)."""
        thresh = Threshold(
            label="test",
            min_score=0.0,
            max_score=1.0,
        )
        with pytest.raises(AttributeError):
            thresh.label = "modified"  # type: ignore

    def test_threshold_invalid_bounds_min_negative(self) -> None:
        """Test that min_score < 0 is rejected."""
        with pytest.raises(ValueError, match="Invalid threshold bounds"):
            Threshold(
                label="bad",
                min_score=-0.1,
                max_score=0.5,
            )

    def test_threshold_invalid_bounds_max_too_high(self) -> None:
        """Test that max_score > 1.0 is rejected."""
        with pytest.raises(ValueError, match="Invalid threshold bounds"):
            Threshold(
                label="bad",
                min_score=0.5,
                max_score=1.1,
            )

    def test_threshold_invalid_bounds_inverted(self) -> None:
        """Test that min > max is rejected."""
        with pytest.raises(ValueError, match="Invalid threshold bounds"):
            Threshold(
                label="bad",
                min_score=0.7,
                max_score=0.3,
            )

    def test_threshold_valid_boundary(self) -> None:
        """Test valid boundary: min = max."""
        thresh = Threshold(
            label="point",
            min_score=0.5,
            max_score=0.5,
        )
        assert thresh.min_score == thresh.max_score


class TestScoreText:
    """Test score_text function."""

    def test_score_text_single_dimension_exact_match(self) -> None:
        """Test scoring when keywords exactly match text."""
        dims = [
            Dimension(
                name="humor",
                keywords=frozenset(["funny", "joke", "laugh"]),
                weight=1.0,
            ),
        ]
        text = "That joke is funny"
        scores = score_text(text, dims)

        assert "humor" in scores
        assert scores["humor"] > 0.0
        assert scores["humor"] <= 1.0

    def test_score_text_single_dimension_no_match(self) -> None:
        """Test scoring when no keywords match."""
        dims = [
            Dimension(
                name="danger",
                keywords=frozenset(["kill", "bomb", "attack"]),
                weight=1.0,
            ),
        ]
        text = "This is a peaceful text"
        scores = score_text(text, dims)

        assert scores["danger"] == 0.0

    def test_score_text_multiple_dimensions(self) -> None:
        """Test scoring with multiple dimensions."""
        dims = [
            Dimension(
                name="humor",
                keywords=frozenset(["funny", "joke", "laugh"]),
                weight=1.0,
            ),
            Dimension(
                name="danger",
                keywords=frozenset(["kill", "bomb", "attack"]),
                weight=1.0,
            ),
        ]
        text = "That funny attack was laughable"
        scores = score_text(text, dims)

        assert len(scores) == 2
        assert scores["humor"] > 0.0
        assert scores["danger"] > 0.0

    def test_score_text_case_insensitive(self) -> None:
        """Test that scoring is case-insensitive."""
        dims = [
            Dimension(
                name="test",
                keywords=frozenset(["FUNNY", "JOKE"]),
                weight=1.0,
            ),
        ]
        text1 = "That funny joke"
        text2 = "That FUNNY JOKE"
        text3 = "That FuNnY jOkE"

        scores1 = score_text(text1, dims)
        scores2 = score_text(text2, dims)
        scores3 = score_text(text3, dims)

        assert scores1["test"] == scores2["test"]
        assert scores2["test"] == scores3["test"]

    def test_score_text_empty_text(self) -> None:
        """Test scoring empty text."""
        dims = [
            Dimension(
                name="any",
                keywords=frozenset(["a", "b"]),
                weight=1.0,
            ),
        ]
        text = ""
        scores = score_text(text, dims)

        assert scores["any"] == 0.0

    def test_score_text_no_dimensions(self) -> None:
        """Test scoring with no dimensions."""
        text = "Some text"
        scores = score_text(text, [])

        assert scores == {}

    def test_score_text_score_range(self) -> None:
        """Test that all scores are in [0, 1]."""
        dims = [
            Dimension(
                name="a",
                keywords=frozenset(["x", "y", "z"]),
                weight=1.0,
            ),
            Dimension(
                name="b",
                keywords=frozenset(["p", "q"]),
                weight=1.0,
            ),
        ]
        text = "x y z p q x y z"
        scores = score_text(text, dims)

        for score in scores.values():
            assert 0.0 <= score <= 1.0


class TestWeightedAggregate:
    """Test weighted_aggregate function."""

    def test_weighted_aggregate_equal_weights(self) -> None:
        """Test aggregation with equal weights."""
        dims = [
            Dimension(name="a", keywords=frozenset(["x"]), weight=1.0),
            Dimension(name="b", keywords=frozenset(["y"]), weight=1.0),
        ]
        scores = {"a": 0.8, "b": 0.6}
        result = weighted_aggregate(scores, dims)

        expected = (0.8 + 0.6) / 2
        assert abs(result - expected) < 0.01

    def test_weighted_aggregate_unequal_weights(self) -> None:
        """Test aggregation with unequal weights."""
        dims = [
            Dimension(name="a", keywords=frozenset(["x"]), weight=2.0),
            Dimension(name="b", keywords=frozenset(["y"]), weight=1.0),
        ]
        scores = {"a": 0.8, "b": 0.6}
        result = weighted_aggregate(scores, dims)

        # (0.8*2 + 0.6*1) / (2+1) = (1.6 + 0.6) / 3 = 2.2 / 3 ≈ 0.7333
        expected = (0.8 * 2 + 0.6 * 1) / 3
        assert abs(result - expected) < 0.01

    def test_weighted_aggregate_single_dimension(self) -> None:
        """Test aggregation with single dimension."""
        dims = [
            Dimension(name="only", keywords=frozenset(["x"]), weight=1.0),
        ]
        scores = {"only": 0.7}
        result = weighted_aggregate(scores, dims)

        assert abs(result - 0.7) < 0.001

    def test_weighted_aggregate_zero_weight_skipped(self) -> None:
        """Test that missing dimensions are skipped."""
        dims = [
            Dimension(name="a", keywords=frozenset(["x"]), weight=1.0),
            Dimension(name="b", keywords=frozenset(["y"]), weight=1.0),
        ]
        scores = {"a": 0.8}  # Missing "b"
        result = weighted_aggregate(scores, dims)

        # Only "a" contributes: 0.8 / 1.0
        expected = 0.8
        assert abs(result - expected) < 0.001

    def test_weighted_aggregate_no_dimensions(self) -> None:
        """Test aggregation with no dimensions."""
        scores: dict[str, float] = {}
        result = weighted_aggregate(scores, [])

        assert result == 0.0

    def test_weighted_aggregate_no_matching_scores(self) -> None:
        """Test aggregation when no dimension names match."""
        dims = [
            Dimension(name="a", keywords=frozenset(["x"]), weight=1.0),
        ]
        scores = {"z": 0.5}  # No match
        result = weighted_aggregate(scores, dims)

        assert result == 0.0


class TestClassify:
    """Test classify function."""

    def test_classify_risk_thresholds(self) -> None:
        """Test classification with DEFAULT_RISK_THRESHOLDS."""
        assert classify(0.9, DEFAULT_RISK_THRESHOLDS) == "critical"
        assert classify(0.7, DEFAULT_RISK_THRESHOLDS) == "high"
        assert classify(0.5, DEFAULT_RISK_THRESHOLDS) == "medium"
        assert classify(0.3, DEFAULT_RISK_THRESHOLDS) == "low"
        assert classify(0.1, DEFAULT_RISK_THRESHOLDS) == "minimal"

    def test_classify_grade_thresholds(self) -> None:
        """Test classification with DEFAULT_GRADE_THRESHOLDS."""
        assert classify(0.95, DEFAULT_GRADE_THRESHOLDS) == "A"
        assert classify(0.85, DEFAULT_GRADE_THRESHOLDS) == "B"
        assert classify(0.75, DEFAULT_GRADE_THRESHOLDS) == "C"
        assert classify(0.65, DEFAULT_GRADE_THRESHOLDS) == "D"
        assert classify(0.5, DEFAULT_GRADE_THRESHOLDS) == "F"

    def test_classify_tier_thresholds(self) -> None:
        """Test classification with DEFAULT_TIER_THRESHOLDS."""
        assert classify(0.9, DEFAULT_TIER_THRESHOLDS) == "exceptional"
        assert classify(0.75, DEFAULT_TIER_THRESHOLDS) == "excellent"
        assert classify(0.6, DEFAULT_TIER_THRESHOLDS) == "good"
        assert classify(0.45, DEFAULT_TIER_THRESHOLDS) == "fair"
        assert classify(0.2, DEFAULT_TIER_THRESHOLDS) == "poor"

    def test_classify_boundary_lower(self) -> None:
        """Test classification at lower boundary."""
        thresh = (Threshold("low", 0.0, 0.3), Threshold("high", 0.3, 1.0))
        assert classify(0.0, thresh) == "low"
        assert classify(0.3, thresh) in ["low", "high"]  # On boundary
        assert classify(0.5, thresh) == "high"

    def test_classify_out_of_range_high(self) -> None:
        """Test classification with score > 1.0."""
        result = classify(1.5, DEFAULT_RISK_THRESHOLDS)
        # Should return last threshold's label or handle gracefully
        assert isinstance(result, str)

    def test_classify_out_of_range_low(self) -> None:
        """Test classification with score < 0.0."""
        result = classify(-0.5, DEFAULT_RISK_THRESHOLDS)
        assert isinstance(result, str)

    def test_classify_empty_thresholds(self) -> None:
        """Test classification with empty threshold list."""
        result = classify(0.5, ())
        assert result == "unknown"


class TestGrade:
    """Test grade function."""

    def test_grade_a(self) -> None:
        """Test grade A assignment."""
        assert grade(0.95) == "A"
        assert grade(0.92) == "A"

    def test_grade_b(self) -> None:
        """Test grade B assignment."""
        assert grade(0.85) == "B"
        assert grade(0.80) == "B"

    def test_grade_c(self) -> None:
        """Test grade C assignment."""
        assert grade(0.75) == "C"
        assert grade(0.70) == "C"

    def test_grade_d(self) -> None:
        """Test grade D assignment."""
        assert grade(0.65) == "D"
        assert grade(0.60) == "D"

    def test_grade_f(self) -> None:
        """Test grade F assignment."""
        assert grade(0.55) == "F"
        assert grade(0.30) == "F"

    def test_grade_boundary(self) -> None:
        """Test grade at boundaries."""
        # Boundary 0.9 should be A
        assert grade(0.9) == "A"
        # Boundary 0.89 should be B
        assert grade(0.89) == "B"


class TestFullAssessment:
    """Test full_assessment end-to-end function."""

    def test_full_assessment_basic(self) -> None:
        """Test complete assessment pipeline."""
        dims = [
            Dimension(
                name="harm",
                keywords=frozenset(["kill", "bomb", "attack"]),
                weight=2.0,
            ),
            Dimension(
                name="stealth",
                keywords=frozenset(["hidden", "covert", "disguise"]),
                weight=1.0,
            ),
        ]
        text = "A hidden attack plan"
        result = full_assessment(text, dims)

        assert "overall_score" in result
        assert "classification" in result
        assert "grade" in result
        assert "dimensions" in result
        assert "top_concerns" in result
        assert "metadata" in result

    def test_full_assessment_score_range(self) -> None:
        """Test that overall_score is in [0, 1]."""
        dims = [
            Dimension(
                name="test",
                keywords=frozenset(["a", "b"]),
                weight=1.0,
            ),
        ]
        result = full_assessment("a b c d", dims)

        assert 0.0 <= result["overall_score"] <= 1.0

    def test_full_assessment_classification_valid(self) -> None:
        """Test that classification is valid risk level."""
        dims = [
            Dimension(
                name="test",
                keywords=frozenset(["x"]),
                weight=1.0,
            ),
        ]
        result = full_assessment("x", dims)

        valid_classes = {"critical", "high", "medium", "low", "minimal"}
        assert result["classification"] in valid_classes

    def test_full_assessment_grade_valid(self) -> None:
        """Test that grade is valid letter."""
        dims = [
            Dimension(
                name="test",
                keywords=frozenset(["x"]),
                weight=1.0,
            ),
        ]
        result = full_assessment("x", dims)

        valid_grades = {"A", "B", "C", "D", "F"}
        assert result["grade"] in valid_grades

    def test_full_assessment_top_concerns_order(self) -> None:
        """Test that top_concerns are in descending score order."""
        dims = [
            Dimension(
                name="low_score",
                keywords=frozenset(["rare1"]),
                weight=1.0,
            ),
            Dimension(
                name="high_score",
                keywords=frozenset(["common", "very", "much"]),
                weight=1.0,
            ),
        ]
        text = "very common very much text"
        result = full_assessment(text, dims)

        concerns = result["top_concerns"]
        # high_score dimension should appear before low_score (if both > 0.5)
        if len(concerns) > 1 and "high_score" in concerns and "low_score" in concerns:
            assert concerns.index("high_score") < concerns.index("low_score")

    def test_full_assessment_metadata(self) -> None:
        """Test that metadata is populated correctly."""
        dims = [
            Dimension(name="a", keywords=frozenset(["x"]), weight=1.0),
            Dimension(name="b", keywords=frozenset(["y"]), weight=1.0),
        ]
        text = "Some test text"
        result = full_assessment(text, dims)

        metadata = result["metadata"]
        assert metadata["text_length"] == len(text)
        assert metadata["dimension_count"] == 2

    def test_full_assessment_empty_text(self) -> None:
        """Test assessment with empty text."""
        dims = [
            Dimension(name="test", keywords=frozenset(["x"]), weight=1.0),
        ]
        result = full_assessment("", dims)

        assert result["overall_score"] == 0.0
        assert result["top_concerns"] == []

    def test_full_assessment_custom_thresholds(self) -> None:
        """Test assessment with custom thresholds."""
        dims = [
            Dimension(name="test", keywords=frozenset(["x"]), weight=1.0),
        ]
        custom_thresh = (
            Threshold("extreme", 0.8, 1.0),
            Threshold("normal", 0.0, 0.8),
        )
        result = full_assessment("x x x", dims, thresholds=custom_thresh)

        assert result["classification"] in ["extreme", "normal"]
