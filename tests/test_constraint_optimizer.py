"""Unit tests for constraint_optimizer — multi-constraint prompt optimization.

Tests 15+ scenarios covering:
- Basic constraint satisfaction
- Multiple constraint scenarios
- Strategy selection and application
- Improvement scoring
- Edge cases and error handling
- Constraint detection and validation

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import asyncio
import pytest

from loom.constraint_optimizer import ConstraintOptimizer


class TestConstraintOptimizerBasics:
    """Basic constraint optimizer functionality."""

    def test_optimizer_initialization(self) -> None:
        """Optimizer initializes with strategies."""
        strategies = {
            "test_strat": {
                "multiplier": 2.0,
                "best_for": ["hcs"],
                "template": "{prompt}",
            }
        }
        optimizer = ConstraintOptimizer(strategies)

        assert optimizer.strategies == strategies
        assert "test_strat" in optimizer.strategies

    def test_optimizer_empty_strategies(self) -> None:
        """Optimizer works with empty strategy dict."""
        optimizer = ConstraintOptimizer({})
        assert optimizer.strategies == {}

    def test_check_constraints_single_min(self) -> None:
        """Check single minimum constraint."""
        optimizer = ConstraintOptimizer({})
        scores = {"hcs": 8.5}
        constraints = {"hcs": {"min": 8.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert "hcs" in met
        assert len(violated) == 0

    def test_check_constraints_single_max(self) -> None:
        """Check single maximum constraint."""
        optimizer = ConstraintOptimizer({})
        scores = {"danger": 3.0}
        constraints = {"danger": {"max": 5.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert "danger" in met
        assert len(violated) == 0

    def test_check_constraints_min_violated(self) -> None:
        """Detect violation of minimum constraint."""
        optimizer = ConstraintOptimizer({})
        scores = {"hcs": 6.0}
        constraints = {"hcs": {"min": 8.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert len(met) == 0
        assert "hcs" in violated

    def test_check_constraints_max_violated(self) -> None:
        """Detect violation of maximum constraint."""
        optimizer = ConstraintOptimizer({})
        scores = {"danger": 7.0}
        constraints = {"danger": {"max": 5.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert len(met) == 0
        assert "danger" in violated

    def test_check_constraints_both_min_max(self) -> None:
        """Check constraint with both min and max."""
        optimizer = ConstraintOptimizer({})
        scores = {"score": 5.0}
        constraints = {"score": {"min": 3.0, "max": 7.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert "score" in met
        assert len(violated) == 0

    def test_check_constraints_multiple_dimensions(self) -> None:
        """Check multiple constraints simultaneously."""
        optimizer = ConstraintOptimizer({})
        scores = {"hcs": 8.5, "stealth": 7.0, "danger": 4.0}
        constraints = {
            "hcs": {"min": 8.0},
            "stealth": {"min": 7.0},
            "danger": {"max": 5.0},
        }

        met, violated = optimizer._check_constraints(scores, constraints)

        assert len(met) == 3
        assert len(violated) == 0

    def test_check_constraints_partial_satisfaction(self) -> None:
        """Check mix of satisfied and violated constraints."""
        optimizer = ConstraintOptimizer({})
        scores = {"hcs": 8.5, "stealth": 5.0, "danger": 6.0}
        constraints = {
            "hcs": {"min": 8.0},  # satisfied
            "stealth": {"min": 7.0},  # violated (5.0 < 7.0)
            "danger": {"max": 5.0},  # violated (6.0 > 5.0)
        }

        met, violated = optimizer._check_constraints(scores, constraints)

        assert "hcs" in met
        assert "stealth" in violated
        assert "danger" in violated

    def test_check_constraints_missing_dimension(self) -> None:
        """Handle missing dimension in scores."""
        optimizer = ConstraintOptimizer({})
        scores = {"hcs": 8.0}
        constraints = {"hcs": {"min": 8.0}, "missing": {"min": 5.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert "hcs" in met
        assert "missing" in violated

    def test_check_constraints_non_numeric_score(self) -> None:
        """Handle non-numeric score values."""
        optimizer = ConstraintOptimizer({})
        scores = {"hcs": "high"}
        constraints = {"hcs": {"min": 8.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert "hcs" in violated

    def test_apply_strategy_basic(self) -> None:
        """Apply strategy to reframe prompt."""
        optimizer = ConstraintOptimizer(
            {
                "test": {
                    "template": "Reframed: {prompt}",
                }
            }
        )
        prompt = "Do something"
        reframed = optimizer._apply_strategy(prompt, "test")

        assert "Reframed:" in reframed
        assert "Do something" in reframed

    def test_apply_strategy_missing(self) -> None:
        """Apply missing strategy falls back gracefully."""
        optimizer = ConstraintOptimizer({})
        prompt = "Do something"
        reframed = optimizer._apply_strategy(prompt, "nonexistent")

        # Should return something
        assert isinstance(reframed, str)
        assert len(reframed) > 0

    def test_apply_strategy_malformed_template(self) -> None:
        """Apply strategy with malformed template."""
        optimizer = ConstraintOptimizer(
            {
                "test": {
                    "template": "Missing placeholder",
                }
            }
        )
        prompt = "Do something"
        reframed = optimizer._apply_strategy(prompt, "test")

        # Should fall back to appending
        assert isinstance(reframed, str)
        assert len(reframed) > 0

    def test_select_strategy_basic(self) -> None:
        """Select strategy for violations."""
        optimizer = ConstraintOptimizer(
            {
                "good_strategy": {
                    "multiplier": 5.0,
                    "best_for": ["hcs"],
                },
                "poor_strategy": {
                    "multiplier": 1.0,
                    "best_for": ["stealth"],
                },
            }
        )
        violations = ["hcs"]
        current_scores = {"hcs": 5.0, "stealth": 7.0}

        selected = optimizer._select_strategy(violations, 0, current_scores)

        # Should prefer strategy with hcs in best_for
        assert selected in optimizer.strategies

    def test_select_strategy_no_violations(self) -> None:
        """Select strategy when no violations."""
        optimizer = ConstraintOptimizer({})
        violations = []
        current_scores = {"hcs": 8.0}

        selected = optimizer._select_strategy(violations, 0, current_scores)

        assert selected is None

    def test_score_improvement_min_constraint(self) -> None:
        """Score improvement toward minimum constraint."""
        optimizer = ConstraintOptimizer({})
        old = {"hcs": 6.0}
        new = {"hcs": 8.5}
        constraints = {"hcs": {"min": 8.0}}

        improvement = optimizer._score_improvement(old, new, constraints)

        # Should be positive (moving toward and satisfying constraint)
        assert improvement > 0

    def test_score_improvement_max_constraint(self) -> None:
        """Score improvement toward maximum constraint."""
        optimizer = ConstraintOptimizer({})
        old = {"danger": 7.0}
        new = {"danger": 4.0}
        constraints = {"danger": {"max": 5.0}}

        improvement = optimizer._score_improvement(old, new, constraints)

        # Should be positive (moving toward and satisfying constraint)
        assert improvement > 0

    def test_score_improvement_negative(self) -> None:
        """Score negative improvement when moving away."""
        optimizer = ConstraintOptimizer({})
        old = {"hcs": 8.5}
        new = {"hcs": 6.0}
        constraints = {"hcs": {"min": 8.0}}

        improvement = optimizer._score_improvement(old, new, constraints)

        # Should be negative (moving away from constraint)
        assert improvement < 0

    def test_score_improvement_multiple_dimensions(self) -> None:
        """Score improvement across multiple dimensions."""
        optimizer = ConstraintOptimizer({})
        old = {"hcs": 6.0, "stealth": 5.0, "danger": 7.0}
        new = {"hcs": 8.5, "stealth": 7.5, "danger": 4.0}
        constraints = {
            "hcs": {"min": 8.0},
            "stealth": {"min": 7.0},
            "danger": {"max": 5.0},
        }

        improvement = optimizer._score_improvement(old, new, constraints)

        # All constraints improved
        assert improvement > 0

    def test_compute_improvement_basic(self) -> None:
        """Compute overall improvement from base to final."""
        optimizer = ConstraintOptimizer({})
        base = {"hcs": 5.0, "stealth": 4.0}
        final = {"hcs": 8.0, "stealth": 7.0}
        constraints = {"hcs": {"min": 8.0}, "stealth": {"min": 7.0}}

        improvement = optimizer._compute_improvement(base, final, constraints)

        # Should be positive average
        assert improvement > 0

    def test_validate_strategies_missing_multiplier_warning(self) -> None:
        """Warn when strategy missing multiplier."""
        strategies = {
            "incomplete": {
                "best_for": ["hcs"],
                # missing multiplier
            }
        }
        # Should not raise, but logs warning
        optimizer = ConstraintOptimizer(strategies)
        assert optimizer.strategies == strategies

    def test_validate_strategies_non_dict_raises(self) -> None:
        """Raise when strategy is not a dict."""
        strategies = {
            "invalid": "not a dict",
        }
        with pytest.raises(ValueError):
            ConstraintOptimizer(strategies)


class TestConstraintOptimizerEdgeCases:
    """Edge cases and boundary conditions."""

    def test_constraints_empty(self) -> None:
        """Handle empty constraints dict."""
        optimizer = ConstraintOptimizer({})
        constraints = {}
        scores = {"hcs": 8.0}

        # Should not crash
        met, violated = optimizer._check_constraints(scores, constraints)
        assert len(met) == 0
        assert len(violated) == 0

    def test_constraints_zero_values(self) -> None:
        """Handle constraints with zero bounds."""
        optimizer = ConstraintOptimizer({})
        scores = {"metric": 0.0}
        constraints = {"metric": {"min": 0.0, "max": 10.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert "metric" in met

    def test_constraints_boundary_exact_match(self) -> None:
        """Constraints exactly at boundary."""
        optimizer = ConstraintOptimizer({})

        # Score exactly at minimum
        met, violated = optimizer._check_constraints(
            {"x": 5.0}, {"x": {"min": 5.0}}
        )
        assert "x" in met

        # Score exactly at maximum
        met, violated = optimizer._check_constraints(
            {"y": 10.0}, {"y": {"max": 10.0}}
        )
        assert "y" in met

    def test_constraints_negative_values(self) -> None:
        """Handle negative constraint values."""
        optimizer = ConstraintOptimizer({})
        scores = {"metric": -5.0}
        constraints = {"metric": {"min": -10.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        assert "metric" in met

    def test_constraints_float_precision(self) -> None:
        """Handle float precision in constraints."""
        optimizer = ConstraintOptimizer({})
        scores = {"metric": 7.999999}
        constraints = {"metric": {"min": 8.0}}

        met, violated = optimizer._check_constraints(scores, constraints)

        # Technically violated due to float
        assert "metric" in violated

    def test_select_strategy_decay_with_iteration(self) -> None:
        """Strategy selection decays with iteration count."""
        optimizer = ConstraintOptimizer(
            {
                "strategy": {
                    "multiplier": 5.0,
                    "best_for": ["hcs"],
                }
            }
        )
        violations = ["hcs"]
        current_scores = {"hcs": 5.0}

        # Early iteration
        early = optimizer._select_strategy(violations, 0, current_scores)
        # Late iteration
        late = optimizer._select_strategy(violations, 19, current_scores)

        # Both should select strategy (only one available)
        assert early is not None
        assert late is not None

    def test_apply_strategy_very_long_prompt(self) -> None:
        """Apply strategy to very long prompt."""
        optimizer = ConstraintOptimizer(
            {
                "test": {
                    "template": "Reframe: {prompt}",
                }
            }
        )
        long_prompt = "x" * 50000
        reframed = optimizer._apply_strategy(long_prompt, "test")

        assert isinstance(reframed, str)
        assert len(reframed) > len(long_prompt)

    def test_apply_strategy_special_characters(self) -> None:
        """Apply strategy with special characters."""
        optimizer = ConstraintOptimizer(
            {
                "test": {
                    "template": "Context: {prompt}",
                }
            }
        )
        prompt = "Special: !@#$%^&*() \n\t\r\0"
        reframed = optimizer._apply_strategy(prompt, "test")

        assert isinstance(reframed, str)
        assert "Context:" in reframed

    def test_score_improvement_nonexistent_dimension(self) -> None:
        """Score improvement ignores nonexistent dimensions."""
        optimizer = ConstraintOptimizer({})
        old = {"x": 5.0}
        new = {"x": 8.0, "y": 3.0}
        constraints = {"z": {"min": 7.0}}

        improvement = optimizer._score_improvement(old, new, constraints)

        # Should handle gracefully
        assert isinstance(improvement, float)

    def test_compute_improvement_no_constraints(self) -> None:
        """Compute improvement with no constraints."""
        optimizer = ConstraintOptimizer({})
        base = {"x": 1.0}
        final = {"x": 5.0}
        constraints = {}

        improvement = optimizer._compute_improvement(base, final, constraints)

        # Should be 0 or neutral
        assert isinstance(improvement, float)


class TestConstraintOptimizerIntegration:
    """Integration-level tests."""

    @pytest.mark.asyncio
    async def test_optimize_simple_scenario(self) -> None:
        """Optimize prompt in simple scenario."""
        optimizer = ConstraintOptimizer(
            {
                "boost": {
                    "multiplier": 2.0,
                    "best_for": ["hcs"],
                    "template": "Enhanced: {prompt}",
                }
            }
        )

        async def mock_scorer(prompt: str) -> dict[str, Any]:
            """Mock scorer that rewards 'Enhanced' prefix."""
            score = 5.0
            if "Enhanced:" in prompt:
                score = 9.0
            return {"hcs": score}

        constraints = {"hcs": {"min": 8.0}}
        base_prompt = "original"

        result = await optimizer._optimize_async(
            base_prompt, constraints, mock_scorer, max_iterations=5
        )

        assert isinstance(result, dict)
        assert "final_prompt" in result
        assert "final_scores" in result
        assert "iterations" in result

    @pytest.mark.asyncio
    async def test_optimize_multiple_constraints(self) -> None:
        """Optimize toward multiple constraints."""
        optimizer = ConstraintOptimizer(
            {
                "aggressive": {
                    "multiplier": 8.0,
                    "best_for": ["hcs", "stealth"],
                    "template": "Aggressive: {prompt}",
                },
                "gentle": {
                    "multiplier": 2.0,
                    "best_for": ["danger"],
                    "template": "Gentle: {prompt}",
                },
            }
        )

        async def mock_scorer(prompt: str) -> dict[str, Any]:
            """Mock scorer responsive to strategies."""
            hcs = 5.0
            if "Aggressive:" in prompt:
                hcs = 9.0
            stealth = 5.0
            if "Aggressive:" in prompt:
                stealth = 8.0
            danger = 8.0
            if "Gentle:" in prompt:
                danger = 3.0
            return {"hcs": hcs, "stealth": stealth, "danger": danger}

        constraints = {
            "hcs": {"min": 8.0},
            "stealth": {"min": 7.0},
            "danger": {"max": 5.0},
        }

        result = await optimizer._optimize_async(
            "prompt", constraints, mock_scorer, max_iterations=10
        )

        assert isinstance(result, dict)
        assert "final_scores" in result

    @pytest.mark.asyncio
    async def test_optimize_impossible_constraints(self) -> None:
        """Handle impossible constraint combinations."""
        optimizer = ConstraintOptimizer(
            {
                "strategy": {
                    "multiplier": 1.0,
                    "best_for": [],
                    "template": "{prompt}",
                }
            }
        )

        async def mock_scorer(prompt: str) -> dict[str, Any]:
            """Scorer that never changes."""
            return {"hcs": 5.0}

        # Impossible: need 9.0 but scorer always returns 5.0
        constraints = {"hcs": {"min": 9.0}}

        result = await optimizer._optimize_async(
            "prompt", constraints, mock_scorer, max_iterations=3
        )

        # Should fail gracefully
        assert result["success"] == False
        assert "hcs" in result["constraints_violated"]

    @pytest.mark.asyncio
    async def test_optimize_already_satisfied(self) -> None:
        """Optimize when constraints already satisfied."""
        optimizer = ConstraintOptimizer({})

        async def mock_scorer(prompt: str) -> dict[str, Any]:
            return {"hcs": 9.5}

        constraints = {"hcs": {"min": 8.0}}

        result = await optimizer._optimize_async(
            "prompt", constraints, mock_scorer, max_iterations=20
        )

        # Should succeed immediately
        assert result["success"] == True
        assert result["iterations"] < 20
        assert "hcs" in result["constraints_met"]
        assert len(result["constraints_violated"]) == 0


# Type hint for Any import
from typing import Any
