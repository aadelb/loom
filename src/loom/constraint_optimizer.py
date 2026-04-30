"""Constraint satisfaction optimizer for prompt engineering.

Finds prompts that satisfy multiple scoring constraints simultaneously
(e.g., high HCS score, high stealth, low danger).

Algorithm:
1. Score base prompt on all constraint dimensions
2. Identify violated constraints
3. Select strategy that improves worst violation without degrading others
4. Apply strategy, re-score
5. Repeat until all constraints met or max_iterations

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.constraint_optimizer")


class ConstraintOptimizer:
    """Find prompts that satisfy multiple scoring constraints simultaneously.

    Supports constraints like:
    - {"hcs": {"min": 8.0}, "stealth": {"min": 7.0}, "danger": {"max": 5.0}}
    """

    def __init__(self, strategies: dict[str, dict[str, Any]]) -> None:
        """Initialize optimizer with available strategies.

        Args:
            strategies: Dict mapping strategy names to their properties
                Example: {
                    "crescendo": {"multiplier": 5.5, "best_for": ["gpt", "gemini"]},
                    "deep_inception": {"multiplier": 7.2, "best_for": ["claude", "llama"]}
                }
        """
        self.strategies = strategies
        self._validate_strategies()

    def _validate_strategies(self) -> None:
        """Validate that all strategies have required fields."""
        for strategy_name, strategy_info in self.strategies.items():
            if not isinstance(strategy_info, dict):
                raise ValueError(f"Strategy {strategy_name} must be a dict")
            if "multiplier" not in strategy_info:
                logger.warning(
                    f"Strategy {strategy_name} missing 'multiplier' field"
                )

    def optimize(
        self,
        base_prompt: str,
        constraints: dict[str, dict[str, float]],
        scorer_func: callable,
        max_iterations: int = 20,
    ) -> dict[str, Any]:
        """Find reframed prompt satisfying all constraints.

        Args:
            base_prompt: Original prompt to optimize
            constraints: Dict of constraint specifications
                Example: {
                    "hcs": {"min": 8.0},
                    "stealth": {"min": 7.0},
                    "danger": {"max": 5.0}
                }
            scorer_func: Async callable that scores a prompt
                Should accept (prompt: str) and return dict with dimension scores
            max_iterations: Maximum optimization attempts

        Returns:
            Dict with:
            - success: bool, whether all constraints satisfied
            - final_prompt: str, optimized prompt
            - final_scores: dict, scores of final prompt
            - constraints_met: list[str], which constraints are satisfied
            - constraints_violated: list[str], which constraints still violated
            - iterations: int, number of iterations used
            - strategy_chain: list[str], strategies applied in order
            - improvement: float, total score improvement from base
        """
        import asyncio

        return asyncio.run(
            self._optimize_async(
                base_prompt, constraints, scorer_func, max_iterations
            )
        )

    async def _optimize_async(
        self,
        base_prompt: str,
        constraints: dict[str, dict[str, float]],
        scorer_func: callable,
        max_iterations: int,
    ) -> dict[str, Any]:
        """Async implementation of optimize."""
        # Score base prompt
        base_scores = await scorer_func(base_prompt)
        current_prompt = base_prompt
        current_scores = base_scores
        strategy_chain: list[str] = []

        logger.info(
            "constraint_optimization_start base_prompt_len=%d constraints=%s",
            len(base_prompt),
            list(constraints.keys()),
        )

        for iteration in range(max_iterations):
            # Check constraints
            constraints_met, constraints_violated = self._check_constraints(
                current_scores, constraints
            )

            if not constraints_violated:
                logger.info(
                    "constraint_optimization_success iteration=%d strategy_chain=%s",
                    iteration,
                    strategy_chain,
                )
                return {
                    "success": True,
                    "final_prompt": current_prompt,
                    "final_scores": current_scores,
                    "constraints_met": constraints_met,
                    "constraints_violated": [],
                    "iterations": iteration,
                    "strategy_chain": strategy_chain,
                    "improvement": self._compute_improvement(
                        base_scores, current_scores, constraints
                    ),
                }

            # Select best strategy for violations
            selected_strategy = self._select_strategy(
                constraints_violated, iteration, current_scores
            )

            if not selected_strategy:
                logger.warning(
                    "constraint_optimization_no_strategy iteration=%d violations=%s",
                    iteration,
                    constraints_violated,
                )
                break

            # Apply strategy (reframe prompt)
            reframed = self._apply_strategy(current_prompt, selected_strategy)
            new_scores = await scorer_func(reframed)

            # Only accept if improvement
            improvement_score = self._score_improvement(
                current_scores, new_scores, constraints
            )

            if improvement_score > 0:
                current_prompt = reframed
                current_scores = new_scores
                strategy_chain.append(selected_strategy)
                logger.info(
                    "constraint_optimization_step iteration=%d strategy=%s improvement=%s",
                    iteration,
                    selected_strategy,
                    improvement_score,
                )
            else:
                logger.debug(
                    "constraint_optimization_rejected iteration=%d strategy=%s",
                    iteration,
                    selected_strategy,
                )

        # Final check
        constraints_met, constraints_violated = self._check_constraints(
            current_scores, constraints
        )

        logger.info(
            "constraint_optimization_complete iteration=%d success=%s violations=%d",
            max_iterations,
            len(constraints_violated) == 0,
            len(constraints_violated),
        )

        return {
            "success": len(constraints_violated) == 0,
            "final_prompt": current_prompt,
            "final_scores": current_scores,
            "constraints_met": constraints_met,
            "constraints_violated": constraints_violated,
            "iterations": max_iterations,
            "strategy_chain": strategy_chain,
            "improvement": self._compute_improvement(
                base_scores, current_scores, constraints
            ),
        }

    def _check_constraints(
        self, scores: dict[str, Any], constraints: dict[str, dict[str, float]]
    ) -> tuple[list[str], list[str]]:
        """Check which constraints are satisfied.

        Args:
            scores: Current dimension scores
            constraints: Constraint specifications

        Returns:
            Tuple of (satisfied_list, violated_list)
        """
        met: list[str] = []
        violated: list[str] = []

        for dimension, constraint_spec in constraints.items():
            if dimension not in scores:
                logger.warning(
                    "constraint_dimension_missing dimension=%s available=%s",
                    dimension,
                    list(scores.keys()),
                )
                violated.append(dimension)
                continue

            current_value = scores[dimension]
            if not isinstance(current_value, (int, float)):
                logger.warning(
                    "constraint_non_numeric dimension=%s value=%s",
                    dimension,
                    current_value,
                )
                violated.append(dimension)
                continue

            satisfied = True

            if "min" in constraint_spec:
                min_val = constraint_spec["min"]
                if current_value < min_val:
                    satisfied = False

            if "max" in constraint_spec:
                max_val = constraint_spec["max"]
                if current_value > max_val:
                    satisfied = False

            if satisfied:
                met.append(dimension)
            else:
                violated.append(dimension)

        return met, violated

    def _select_strategy(
        self,
        violations: list[str],
        attempt: int,
        current_scores: dict[str, Any],
    ) -> str | None:
        """Select strategy that best addresses constraint violations.

        Args:
            violations: List of violated constraint dimensions
            attempt: Current iteration number
            current_scores: Current scores to reference

        Returns:
            Strategy name to apply, or None if no good options
        """
        if not violations:
            return None

        # Strategy pool - will be populated by best matching strategies
        candidates: list[tuple[str, float]] = []

        worst_violation = violations[0]
        worst_score = current_scores.get(worst_violation, 0)

        # Find strategies that target the worst violation
        for strategy_name, strategy_info in self.strategies.items():
            # Skip if already heavily used
            if strategy_name.startswith("_"):
                continue

            best_for = strategy_info.get("best_for", [])
            multiplier = strategy_info.get("multiplier", 1.0)

            # Score this strategy's relevance
            relevance_score = 0.0

            # If worst violation is in best_for list, high relevance
            if worst_violation in best_for:
                relevance_score += multiplier * 1.5

            # General multiplier (higher is more likely to help)
            relevance_score += multiplier * 0.5

            # Decay by attempt number to encourage diversity
            decay = max(0.3, 1.0 - (attempt / 20.0))
            relevance_score *= decay

            candidates.append((strategy_name, relevance_score))

        if not candidates:
            return None

        # Sort by relevance and return best
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected = candidates[0][0]

        logger.debug(
            "strategy_selected worst_violation=%s selected=%s relevance=%s",
            worst_violation,
            selected,
            candidates[0][1],
        )

        return selected

    def _apply_strategy(self, prompt: str, strategy_name: str) -> str:
        """Apply a strategy to reframe a prompt.

        Args:
            prompt: Original prompt
            strategy_name: Strategy to apply

        Returns:
            Reframed prompt
        """
        strategy_info = self.strategies.get(strategy_name, {})
        template = strategy_info.get("template", "{prompt}")

        # Try to format template
        try:
            reframed = template.format(prompt=prompt)
        except (KeyError, ValueError, IndexError):
            # Fallback if template format fails
            if "{prompt}" in template:
                reframed = template.replace("{prompt}", prompt)
            else:
                reframed = f"{template}\n\n{prompt}"

        logger.debug(
            "strategy_applied strategy=%s original_len=%d reframed_len=%d",
            strategy_name,
            len(prompt),
            len(reframed),
        )

        return reframed

    def _score_improvement(
        self,
        old_scores: dict[str, Any],
        new_scores: dict[str, Any],
        constraints: dict[str, dict[str, float]],
    ) -> float:
        """Score how much new_scores improves over old_scores.

        Args:
            old_scores: Previous dimension scores
            new_scores: New dimension scores
            constraints: Constraint specifications

        Returns:
            Improvement score (higher = better)
        """
        improvement = 0.0

        for dimension in constraints.keys():
            if dimension not in new_scores or dimension not in old_scores:
                continue

            old_val = old_scores[dimension]
            new_val = new_scores[dimension]

            if not isinstance(old_val, (int, float)) or not isinstance(
                new_val, (int, float)
            ):
                continue

            constraint_spec = constraints[dimension]
            delta = new_val - old_val

            # Reward improvement toward constraint
            if "min" in constraint_spec:
                min_val = constraint_spec["min"]
                if old_val < min_val and new_val >= min_val:
                    # Constraint became satisfied
                    improvement += 2.0
                elif new_val > old_val:
                    # Moving in right direction
                    improvement += delta * 0.5
                elif new_val < old_val:
                    # Moving in wrong direction
                    improvement -= abs(delta) * 0.2

            if "max" in constraint_spec:
                max_val = constraint_spec["max"]
                if old_val > max_val and new_val <= max_val:
                    # Constraint became satisfied
                    improvement += 2.0
                elif new_val < old_val:
                    # Moving in right direction
                    improvement += abs(delta) * 0.5
                elif new_val > old_val:
                    # Moving in wrong direction
                    improvement -= delta * 0.2

        return improvement

    def _compute_improvement(
        self,
        base_scores: dict[str, Any],
        final_scores: dict[str, Any],
        constraints: dict[str, dict[str, float]],
    ) -> float:
        """Compute overall improvement from base to final.

        Args:
            base_scores: Original scores
            final_scores: Final scores
            constraints: Constraints specification

        Returns:
            Total improvement score
        """
        total = 0.0
        count = 0

        for dimension in constraints.keys():
            if dimension not in final_scores or dimension not in base_scores:
                continue

            base_val = base_scores[dimension]
            final_val = final_scores[dimension]

            if not isinstance(base_val, (int, float)) or not isinstance(
                final_val, (int, float)
            ):
                continue

            # Simple delta
            total += final_val - base_val
            count += 1

        return total / max(1, count) if count > 0 else 0.0
