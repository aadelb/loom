"""Unit tests for shared score_utils module.

Tests cover score conversion, normalization, clamping, grade assignment,
and weighted averaging with comprehensive edge case coverage.
"""

from __future__ import annotations

import pytest

from loom.score_utils import (
    clamp,
    score_to_10,
    score_to_100,
    score_to_probability,
    score_to_grade,
    weighted_average,
)


class TestClamp:
    """Tests for clamp() function — 8 test cases."""

    def test_clamp_value_within_range(self) -> None:
        """Clamp a value already within range."""
        assert clamp(0.5, 0.0, 1.0) == 0.5

    def test_clamp_value_below_low(self) -> None:
        """Clamp a value below the low boundary."""
        assert clamp(-5.0, 0.0, 10.0) == 0.0

    def test_clamp_value_above_high(self) -> None:
        """Clamp a value above the high boundary."""
        assert clamp(15.0, 0.0, 10.0) == 10.0

    def test_clamp_default_range(self) -> None:
        """Use default 0.0-1.0 range."""
        assert clamp(0.5) == 0.5
        assert clamp(-1.0) == 0.0
        assert clamp(2.0) == 1.0

    def test_clamp_equal_boundaries(self) -> None:
        """Clamp with equal low and high (edge case)."""
        assert clamp(5.0, 3.0, 3.0) == 3.0

    def test_clamp_negative_range(self) -> None:
        """Clamp with negative boundaries."""
        assert clamp(-5.0, -10.0, -1.0) == -5.0
        assert clamp(-15.0, -10.0, -1.0) == -10.0

    def test_clamp_float_precision(self) -> None:
        """Clamp with floating point values."""
        result = clamp(0.3333, 0.0, 1.0)
        assert 0.3333 == result

    def test_clamp_zero(self) -> None:
        """Clamp zero value."""
        assert clamp(0.0, 0.0, 1.0) == 0.0


class TestScoreTo10:
    """Tests for score_to_10() function — 10 test cases."""

    def test_score_to_10_from_100_scale(self) -> None:
        """Convert 50 from 0-100 scale to 0-10 scale."""
        result = score_to_10(50.0, min_val=0.0, max_val=100.0)
        assert result == 5.0

    def test_score_to_10_default_scale(self) -> None:
        """Convert using default 0-100 scale."""
        result = score_to_10(75.0)
        assert result == 7.5

    def test_score_to_10_minimum_value(self) -> None:
        """Convert minimum value (0 from 0-100)."""
        result = score_to_10(0.0, min_val=0.0, max_val=100.0)
        assert result == 0.0

    def test_score_to_10_maximum_value(self) -> None:
        """Convert maximum value (100 from 0-100)."""
        result = score_to_10(100.0, min_val=0.0, max_val=100.0)
        assert result == 10.0

    def test_score_to_10_equal_min_max(self) -> None:
        """Handle equal min and max (division by zero case)."""
        result = score_to_10(50.0, min_val=50.0, max_val=50.0)
        assert result == 5.0

    def test_score_to_10_clamping(self) -> None:
        """Clamp result to 0-10 range."""
        result = score_to_10(150.0, min_val=0.0, max_val=100.0)
        assert result == 10.0

    def test_score_to_10_negative_scale(self) -> None:
        """Convert from negative scale."""
        result = score_to_10(-5.0, min_val=-10.0, max_val=0.0)
        assert result == 5.0

    def test_score_to_10_rounding(self) -> None:
        """Check rounding to 2 decimals."""
        result = score_to_10(33.333, min_val=0.0, max_val=100.0)
        assert result == 3.33

    def test_score_to_10_custom_range(self) -> None:
        """Convert from custom 1-10 scale."""
        result = score_to_10(5.5, min_val=1.0, max_val=10.0)
        assert result == 5.0

    def test_score_to_10_below_minimum(self) -> None:
        """Convert value below minimum."""
        result = score_to_10(-10.0, min_val=0.0, max_val=100.0)
        assert result == 0.0


class TestScoreTo100:
    """Tests for score_to_100() function — 10 test cases."""

    def test_score_to_100_from_10_scale(self) -> None:
        """Convert 5 from 0-10 scale to 0-100 scale."""
        result = score_to_100(5.0, min_val=0.0, max_val=10.0)
        assert result == 50.0

    def test_score_to_100_default_scale(self) -> None:
        """Convert using default 0-10 scale."""
        result = score_to_100(7.5)
        assert result == 75.0

    def test_score_to_100_minimum_value(self) -> None:
        """Convert minimum value (0 from 0-10)."""
        result = score_to_100(0.0, min_val=0.0, max_val=10.0)
        assert result == 0.0

    def test_score_to_100_maximum_value(self) -> None:
        """Convert maximum value (10 from 0-10)."""
        result = score_to_100(10.0, min_val=0.0, max_val=10.0)
        assert result == 100.0

    def test_score_to_100_equal_min_max(self) -> None:
        """Handle equal min and max (division by zero case)."""
        result = score_to_100(5.0, min_val=5.0, max_val=5.0)
        assert result == 50.0

    def test_score_to_100_clamping(self) -> None:
        """Clamp result to 0-100 range."""
        result = score_to_100(15.0, min_val=0.0, max_val=10.0)
        assert result == 100.0

    def test_score_to_100_negative_scale(self) -> None:
        """Convert from negative scale."""
        result = score_to_100(0.0, min_val=-10.0, max_val=10.0)
        assert result == 50.0

    def test_score_to_100_rounding(self) -> None:
        """Check rounding to 2 decimals."""
        result = score_to_100(3.333, min_val=0.0, max_val=10.0)
        assert result == 33.33

    def test_score_to_100_fractional_value(self) -> None:
        """Convert fractional value."""
        result = score_to_100(2.5, min_val=0.0, max_val=10.0)
        assert result == 25.0

    def test_score_to_100_below_minimum(self) -> None:
        """Convert value below minimum."""
        result = score_to_100(-5.0, min_val=0.0, max_val=10.0)
        assert result == 0.0


class TestScoreToProbability:
    """Tests for score_to_probability() function — 10 test cases."""

    def test_score_to_probability_midpoint(self) -> None:
        """Convert midpoint value (5 from 0-10)."""
        result = score_to_probability(5.0, min_val=0.0, max_val=10.0)
        assert result == 0.5

    def test_score_to_probability_default_scale(self) -> None:
        """Convert using default 0-10 scale."""
        result = score_to_probability(7.5)
        assert result == 0.75

    def test_score_to_probability_minimum(self) -> None:
        """Convert minimum value (0 from 0-10)."""
        result = score_to_probability(0.0, min_val=0.0, max_val=10.0)
        assert result == 0.0

    def test_score_to_probability_maximum(self) -> None:
        """Convert maximum value (10 from 0-10)."""
        result = score_to_probability(10.0, min_val=0.0, max_val=10.0)
        assert result == 1.0

    def test_score_to_probability_equal_min_max(self) -> None:
        """Handle equal min and max (division by zero case)."""
        result = score_to_probability(5.0, min_val=5.0, max_val=5.0)
        assert result == 0.5

    def test_score_to_probability_clamping(self) -> None:
        """Clamp result to 0.0-1.0 range."""
        result = score_to_probability(15.0, min_val=0.0, max_val=10.0)
        assert result == 1.0

    def test_score_to_probability_negative_scale(self) -> None:
        """Convert from negative scale."""
        result = score_to_probability(-5.0, min_val=-10.0, max_val=0.0)
        assert result == 0.5

    def test_score_to_probability_rounding(self) -> None:
        """Check rounding to 3 decimals."""
        result = score_to_probability(3.3333, min_val=0.0, max_val=10.0)
        assert result == 0.333

    def test_score_to_probability_quarter_value(self) -> None:
        """Convert quarter value (2.5 from 0-10)."""
        result = score_to_probability(2.5, min_val=0.0, max_val=10.0)
        assert result == 0.25

    def test_score_to_probability_below_minimum(self) -> None:
        """Convert value below minimum."""
        result = score_to_probability(-5.0, min_val=0.0, max_val=10.0)
        assert result == 0.0


class TestScoreToGrade:
    """Tests for score_to_grade() function — 12 test cases."""

    def test_score_to_grade_a(self) -> None:
        """Convert score >= 90 to grade A."""
        assert score_to_grade(90, scale=100) == "A"
        assert score_to_grade(95, scale=100) == "A"
        assert score_to_grade(100, scale=100) == "A"

    def test_score_to_grade_b(self) -> None:
        """Convert score 80-89 to grade B."""
        assert score_to_grade(80, scale=100) == "B"
        assert score_to_grade(85, scale=100) == "B"
        assert score_to_grade(89, scale=100) == "B"

    def test_score_to_grade_c(self) -> None:
        """Convert score 70-79 to grade C."""
        assert score_to_grade(70, scale=100) == "C"
        assert score_to_grade(75, scale=100) == "C"
        assert score_to_grade(79, scale=100) == "C"

    def test_score_to_grade_d(self) -> None:
        """Convert score 60-69 to grade D."""
        assert score_to_grade(60, scale=100) == "D"
        assert score_to_grade(65, scale=100) == "D"
        assert score_to_grade(69, scale=100) == "D"

    def test_score_to_grade_f(self) -> None:
        """Convert score < 60 to grade F."""
        assert score_to_grade(0, scale=100) == "F"
        assert score_to_grade(50, scale=100) == "F"
        assert score_to_grade(59, scale=100) == "F"

    def test_score_to_grade_custom_scale_10(self) -> None:
        """Convert from 0-10 scale."""
        assert score_to_grade(9, scale=10) == "A"
        assert score_to_grade(8, scale=10) == "B"
        assert score_to_grade(7, scale=10) == "C"
        assert score_to_grade(6, scale=10) == "D"
        assert score_to_grade(5, scale=10) == "F"

    def test_score_to_grade_invalid_scale_zero(self) -> None:
        """Handle zero scale gracefully."""
        assert score_to_grade(50, scale=0) == "F"

    def test_score_to_grade_invalid_scale_negative(self) -> None:
        """Handle negative scale gracefully."""
        assert score_to_grade(50, scale=-100) == "F"

    def test_score_to_grade_above_max_clamped(self) -> None:
        """Clamp scores above max to A."""
        assert score_to_grade(150, scale=100) == "A"

    def test_score_to_grade_below_min_clamped(self) -> None:
        """Clamp scores below min to F."""
        assert score_to_grade(-50, scale=100) == "F"

    def test_score_to_grade_boundary_90(self) -> None:
        """Test boundary at 90."""
        assert score_to_grade(89.9, scale=100) == "B"
        assert score_to_grade(90.0, scale=100) == "A"

    def test_score_to_grade_default_scale(self) -> None:
        """Test with default scale=100."""
        assert score_to_grade(85) == "B"


class TestWeightedAverage:
    """Tests for weighted_average() function — 12 test cases."""

    def test_weighted_average_simple(self) -> None:
        """Compute weighted average of scores."""
        scores = {"a": 10.0, "b": 20.0}
        weights = {"a": 1.0, "b": 1.0}
        result = weighted_average(scores, weights)
        assert result == 15.0

    def test_weighted_average_unequal_weights(self) -> None:
        """Compute weighted average with unequal weights."""
        scores = {"a": 10.0, "b": 20.0}
        weights = {"a": 1.0, "b": 2.0}
        result = weighted_average(scores, weights)
        # (10*1 + 20*2) / (1+2) = 50/3 = 16.67
        assert result == 16.67

    def test_weighted_average_single_score(self) -> None:
        """Compute weighted average with single score."""
        scores = {"a": 50.0}
        weights = {"a": 1.0}
        result = weighted_average(scores, weights)
        assert result == 50.0

    def test_weighted_average_missing_key(self) -> None:
        """Handle case where weight key is not in scores."""
        scores = {"a": 10.0}
        weights = {"a": 1.0, "b": 1.0}
        result = weighted_average(scores, weights)
        # Only 'a' is considered
        assert result == 10.0

    def test_weighted_average_empty_scores(self) -> None:
        """Handle empty scores dict."""
        scores: dict[str, float] = {}
        weights = {"a": 1.0}
        result = weighted_average(scores, weights)
        assert result == 0.0

    def test_weighted_average_empty_weights(self) -> None:
        """Handle empty weights dict."""
        scores = {"a": 10.0}
        weights: dict[str, float] = {}
        result = weighted_average(scores, weights)
        assert result == 0.0

    def test_weighted_average_zero_weight(self) -> None:
        """Skip weights with value 0."""
        scores = {"a": 10.0, "b": 20.0}
        weights = {"a": 1.0, "b": 0.0}
        result = weighted_average(scores, weights)
        assert result == 10.0

    def test_weighted_average_negative_weight(self) -> None:
        """Skip negative weights."""
        scores = {"a": 10.0, "b": 20.0}
        weights = {"a": 1.0, "b": -1.0}
        result = weighted_average(scores, weights)
        assert result == 10.0

    def test_weighted_average_rounding(self) -> None:
        """Check rounding to 2 decimals."""
        scores = {"a": 10.0, "b": 15.0}
        weights = {"a": 1.0, "b": 1.0}
        result = weighted_average(scores, weights)
        assert result == 12.5

    def test_weighted_average_floating_point(self) -> None:
        """Handle floating point scores and weights."""
        scores = {"a": 3.33, "b": 6.67}
        weights = {"a": 2.0, "b": 1.0}
        result = weighted_average(scores, weights)
        # (3.33*2 + 6.67*1) / (2+1) = 13.33/3 = 4.44
        assert abs(result - 4.44) < 0.01

    def test_weighted_average_three_scores(self) -> None:
        """Compute weighted average with three scores."""
        scores = {"a": 10.0, "b": 20.0, "c": 30.0}
        weights = {"a": 1.0, "b": 1.0, "c": 1.0}
        result = weighted_average(scores, weights)
        assert result == 20.0

    def test_weighted_average_large_weights(self) -> None:
        """Handle large weight values."""
        scores = {"a": 10.0, "b": 20.0}
        weights = {"a": 1000.0, "b": 1.0}
        result = weighted_average(scores, weights)
        # Should heavily favor 'a'
        assert result > 10.0
        assert result < 10.1
