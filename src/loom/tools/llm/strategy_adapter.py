"""Real-time strategy adaptation with exponential moving average feedback loop.

Maintains running success/failure metrics per strategy per model,
enabling adaptive strategy selection that evolves with empirical results.

Public API:
    StrategyAdapter.instance() -> StrategyAdapter  (singleton)
    adapter.record_outcome(strategy, model, success, hcs_score)
    adapter.adapt_strategy_ranking(model, query_type) -> list[str]
    adapter.get_hot_strategies(model, top_k) -> list[str]
    adapter.get_stats(strategy, model) -> dict
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.strategy_adapter")


@dataclass
class StrategyStats:
    """Running statistics for a strategy-model pair."""

    strategy: str
    model: str
    successes: int = 0
    failures: int = 0
    total_hcs_sum: float = 0.0
    ema_success_rate: float = 0.5  # Exponential moving average of success rate
    last_updated: str = ""
    recent_outcomes: list[tuple[bool, float]] = None  # (success, hcs_score)

    def __post_init__(self) -> None:
        if self.recent_outcomes is None:
            self.recent_outcomes = []
        if not self.last_updated:
            self.last_updated = datetime.now(UTC).isoformat()

    def update_ema(self, success: bool, alpha: float = 0.3) -> None:
        """Update EMA with new outcome using exponential moving average."""
        new_value = 1.0 if success else 0.0
        self.ema_success_rate = (
            alpha * new_value + (1 - alpha) * self.ema_success_rate
        )
        self.last_updated = datetime.now(UTC).isoformat()

    def add_outcome(self, success: bool, hcs_score: float, alpha: float = 0.3) -> None:
        """Record outcome and update statistics."""
        if success:
            self.successes += 1
        else:
            self.failures += 1

        self.total_hcs_sum += hcs_score
        self.recent_outcomes.append((success, hcs_score))

        # Keep only last 100 outcomes for memory efficiency
        if len(self.recent_outcomes) > 100:
            self.recent_outcomes = self.recent_outcomes[-100:]

        self.update_ema(success, alpha)

    def success_rate(self) -> float:
        """Compute empirical success rate from recent outcomes."""
        if not self.recent_outcomes:
            return 0.5
        successes = sum(1 for success, _ in self.recent_outcomes if success)
        return successes / len(self.recent_outcomes)

    def avg_hcs(self) -> float:
        """Compute average HCS score."""
        if not self.recent_outcomes:
            return 5.0
        hcs_scores = [hcs for _, hcs in self.recent_outcomes]
        return sum(hcs_scores) / len(hcs_scores) if hcs_scores else 5.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "strategy": self.strategy,
            "model": self.model,
            "successes": self.successes,
            "failures": self.failures,
            "total_hcs_sum": self.total_hcs_sum,
            "ema_success_rate": self.ema_success_rate,
            "last_updated": self.last_updated,
            "recent_outcomes": [
                [success, hcs] for success, hcs in self.recent_outcomes
            ],
        }


class StrategyAdapter:
    """Singleton adapter for real-time strategy ranking based on empirical feedback."""

    _instance: StrategyAdapter | None = None
    _lock: asyncio.Lock | None = None

    def __init__(self) -> None:
        """Initialize in-memory stats registry."""
        self._stats: dict[str, dict[str, StrategyStats]] = {}
        # Format: {strategy: {model: StrategyStats}}
        self._persistence_path = (
            Path.home() / ".cache" / "loom" / "strategy_adapter_stats.json"
        )
        self._last_flush = datetime.now(UTC)
        self._dirty = False

    @classmethod
    async def instance(cls) -> StrategyAdapter:
        """Get or create singleton instance (thread-safe)."""
        if cls._instance is None:
            if cls._lock is None:
                cls._lock = asyncio.Lock()
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance.load_state()
        return cls._instance

    async def load_state(self) -> None:
        """Load persisted stats from SQLite/JSON if available."""
        if self._persistence_path.exists():
            try:
                with open(self._persistence_path, "r") as f:
                    data = json.load(f)

                for strategy, models in data.items():
                    self._stats[strategy] = {}
                    for model, stats_dict in models.items():
                        # Reconstruct StrategyStats from dict
                        stats = StrategyStats(
                            strategy=stats_dict.get("strategy", strategy),
                            model=stats_dict.get("model", model),
                            successes=stats_dict.get("successes", 0),
                            failures=stats_dict.get("failures", 0),
                            total_hcs_sum=stats_dict.get("total_hcs_sum", 0.0),
                            ema_success_rate=stats_dict.get("ema_success_rate", 0.5),
                            last_updated=stats_dict.get(
                                "last_updated", datetime.now(UTC).isoformat()
                            ),
                            recent_outcomes=[
                                tuple(outcome)  # type: ignore
                                for outcome in stats_dict.get("recent_outcomes", [])
                            ],
                        )
                        self._stats[strategy][model] = stats

                logger.info(
                    "strategy_adapter_loaded strategies=%d",
                    len(self._stats),
                )
            except Exception as e:
                logger.warning(
                    "strategy_adapter_load_failed error=%s", str(e)[:100]
                )

    async def flush_state(self, force: bool = False) -> None:
        """Persist stats to disk (debounced, every 60s or on force)."""

        now = datetime.now(UTC)
        elapsed = (now - self._last_flush).total_seconds()

        if not force and (not self._dirty or elapsed < 60):
            return

        try:
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize all stats
            data = {}
            for strategy, models in self._stats.items():
                data[strategy] = {
                    model: stats.to_dict() for model, stats in models.items()
                }

            # Atomic write via temp file
            tmp_path = self._persistence_path.with_suffix(".tmp")
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)

            tmp_path.replace(self._persistence_path)
            self._dirty = False
            self._last_flush = now

            logger.debug(
                "strategy_adapter_flushed strategies=%d models_total=%d",
                len(self._stats),
                sum(len(m) for m in self._stats.values()),
            )
        except Exception as e:
            logger.error("strategy_adapter_flush_failed error=%s", str(e)[:100])

    def record_outcome(
        self,
        strategy: str,
        model: str,
        success: bool,
        hcs_score: float,
        alpha: float = 0.3,
    ) -> None:
        """Record a strategy outcome and update running statistics.

        Args:
            strategy: Strategy name that was used.
            model: Target model (e.g., 'gpt-4', 'claude-3-sonnet', 'gemini').
            success: Whether the strategy succeeded (True) or failed (False).
            hcs_score: HCS (Harmfulness/Compliance/Safety) score (0-10).
            alpha: EMA decay factor (lower = more history weight, higher = more recent).
        """
        if strategy not in self._stats:
            self._stats[strategy] = {}

        if model not in self._stats[strategy]:
            self._stats[strategy][model] = StrategyStats(strategy, model)

        stats = self._stats[strategy][model]
        stats.add_outcome(success, hcs_score, alpha)
        self._dirty = True

        logger.debug(
            "strategy_outcome_recorded strategy=%s model=%s success=%s hcs=%.1f "
            "ema_sr=%.3f recent=%d",
            strategy,
            model,
            success,
            hcs_score,
            stats.ema_success_rate,
            len(stats.recent_outcomes),
        )

    def adapt_strategy_ranking(
        self, model: str, query_type: str = "general"
    ) -> list[str]:
        """Get strategies ranked by recent success rate for this model and query type.

        Strategies are ranked by their EMA success rate (most recent weighted higher).
        Falls back to all known strategies if none exist for this model yet.

        Args:
            model: Target model (e.g., 'gpt-4', 'claude-3-sonnet').
            query_type: Query category (for future filtering; unused for now).

        Returns:
            List of strategy names sorted by descending EMA success rate.
        """
        if not self._stats:
            logger.debug("adapt_ranking_no_history model=%s query_type=%s", model, query_type)
            return []

        # Collect all strategies with stats for this model
        ranked = []
        for strategy, models in self._stats.items():
            if model in models:
                stats = models[model]
                ranked.append(
                    (strategy, stats.ema_success_rate, stats.avg_hcs())
                )

        if not ranked:
            logger.debug(
                "adapt_ranking_no_model_data model=%s available_models=%s",
                model,
                list(
                    set(
                        model
                        for models in self._stats.values()
                        for model in models.keys()
                    )
                ),
            )
            return []

        # Sort by EMA success rate (descending), with HCS tie-breaker
        ranked.sort(key=lambda x: (x[1], x[2]), reverse=True)
        result = [strategy for strategy, _, _ in ranked]

        logger.info(
            "adapt_ranking_complete model=%s strategies=%d top_3=%s",
            model,
            len(result),
            result[:3],
        )
        return result

    def get_hot_strategies(
        self, model: str, top_k: int = 5, min_success_rate: float = 0.6
    ) -> list[str]:
        """Get currently best-performing strategies for a model.

        Filters by minimum success rate (default 60%) to exclude underperformers.

        Args:
            model: Target model.
            top_k: Number of strategies to return.
            min_success_rate: Minimum EMA success rate threshold (0-1).

        Returns:
            Up to top_k strategy names with success rate >= min_success_rate,
            sorted by descending success rate.
        """
        if not self._stats:
            return []

        hot = []
        for strategy, models in self._stats.items():
            if model in models:
                stats = models[model]
                if stats.ema_success_rate >= min_success_rate:
                    hot.append(
                        (strategy, stats.ema_success_rate, len(stats.recent_outcomes))
                    )

        # Sort by success rate (descending), then by recency (more outcomes = more tested)
        hot.sort(key=lambda x: (x[1], x[2]), reverse=True)
        result = [strategy for strategy, _, _ in hot[:top_k]]

        logger.info(
            "get_hot_strategies model=%s top_k=%d min_rate=%.2f result=%d strategies=%s",
            model,
            top_k,
            min_success_rate,
            len(result),
            result,
        )
        return result

    def get_stats(self, strategy: str, model: str) -> dict[str, Any]:
        """Get detailed statistics for a strategy-model pair.

        Args:
            strategy: Strategy name.
            model: Model name.

        Returns:
            Dict with successes, failures, ema_success_rate, avg_hcs, recent_outcomes.
        """
        if strategy not in self._stats or model not in self._stats[strategy]:
            return {
                "strategy": strategy,
                "model": model,
                "successes": 0,
                "failures": 0,
                "ema_success_rate": 0.5,
                "avg_hcs": 5.0,
                "recent_outcomes": [],
                "total_trials": 0,
            }

        stats = self._stats[strategy][model]
        return {
            "strategy": strategy,
            "model": model,
            "successes": stats.successes,
            "failures": stats.failures,
            "ema_success_rate": stats.ema_success_rate,
            "avg_hcs": stats.avg_hcs(),
            "recent_outcomes": [
                {"success": success, "hcs": hcs}
                for success, hcs in stats.recent_outcomes[-20:]
            ],
            "total_trials": stats.successes + stats.failures,
            "last_updated": stats.last_updated,
        }

    def reset_stats(self, strategy: str | None = None, model: str | None = None) -> None:
        """Reset statistics (for testing or manual reset).

        Args:
            strategy: If provided, reset only this strategy. If None, reset all.
            model: If provided, reset only for this model. If None, reset for all models.
        """
        if strategy is None:
            self._stats.clear()
            logger.info("reset_stats all_strategies_cleared")
        elif strategy in self._stats:
            if model is None:
                del self._stats[strategy]
                logger.info("reset_stats strategy=%s all_models_cleared", strategy)
            elif model in self._stats[strategy]:
                del self._stats[strategy][model]
                logger.info(
                    "reset_stats strategy=%s model=%s cleared", strategy, model
                )
        self._dirty = True
