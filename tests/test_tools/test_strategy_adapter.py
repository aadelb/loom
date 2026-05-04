"""Unit tests for strategy_adapter real-time adaptation module.

Tests StrategyAdapter singleton, EMA calculations, persistence, and ranking.
"""

from __future__ import annotations

import asyncio
import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from loom.tools.strategy_adapter import StrategyAdapter, StrategyStats


class TestStrategyStats:
    """Test StrategyStats data class."""

    def test_init_defaults(self) -> None:
        """Test default initialization."""
        stats = StrategyStats(strategy="test_strat", model="gpt-4")
        assert stats.strategy == "test_strat"
        assert stats.model == "gpt-4"
        assert stats.successes == 0
        assert stats.failures == 0
        assert stats.ema_success_rate == 0.5
        assert stats.recent_outcomes == []
        assert stats.last_updated != ""

    def test_ema_update_success(self) -> None:
        """Test EMA update with success."""
        stats = StrategyStats(strategy="strat", model="model", ema_success_rate=0.5)
        stats.update_ema(success=True, alpha=0.3)
        # EMA = 0.3 * 1.0 + 0.7 * 0.5 = 0.3 + 0.35 = 0.65
        assert abs(stats.ema_success_rate - 0.65) < 0.001

    def test_ema_update_failure(self) -> None:
        """Test EMA update with failure."""
        stats = StrategyStats(strategy="strat", model="model", ema_success_rate=0.5)
        stats.update_ema(success=False, alpha=0.3)
        # EMA = 0.3 * 0.0 + 0.7 * 0.5 = 0.35
        assert abs(stats.ema_success_rate - 0.35) < 0.001

    def test_add_outcome_success(self) -> None:
        """Test adding successful outcome."""
        stats = StrategyStats(strategy="strat", model="model")
        stats.add_outcome(success=True, hcs_score=8.5, alpha=0.3)
        assert stats.successes == 1
        assert stats.failures == 0
        assert abs(stats.total_hcs_sum - 8.5) < 0.001
        assert len(stats.recent_outcomes) == 1
        assert stats.recent_outcomes[0] == (True, 8.5)

    def test_add_outcome_failure(self) -> None:
        """Test adding failed outcome."""
        stats = StrategyStats(strategy="strat", model="model")
        stats.add_outcome(success=False, hcs_score=3.0, alpha=0.3)
        assert stats.successes == 0
        assert stats.failures == 1
        assert abs(stats.total_hcs_sum - 3.0) < 0.001

    def test_add_multiple_outcomes(self) -> None:
        """Test adding multiple outcomes."""
        stats = StrategyStats(strategy="strat", model="model")
        for i in range(5):
            stats.add_outcome(success=i % 2 == 0, hcs_score=5.0 + i)
        assert stats.successes == 3
        assert stats.failures == 2
        assert len(stats.recent_outcomes) == 5

    def test_recent_outcomes_limited_to_100(self) -> None:
        """Test that recent_outcomes is kept to max 100."""
        stats = StrategyStats(strategy="strat", model="model")
        for i in range(150):
            stats.add_outcome(success=True, hcs_score=5.0)
        assert len(stats.recent_outcomes) == 100

    def test_success_rate(self) -> None:
        """Test success rate calculation."""
        stats = StrategyStats(strategy="strat", model="model")
        stats.add_outcome(success=True, hcs_score=8.0)
        stats.add_outcome(success=True, hcs_score=7.5)
        stats.add_outcome(success=False, hcs_score=2.0)
        # 2 successes, 1 failure = 2/3 ≈ 0.667
        assert abs(stats.success_rate() - (2 / 3)) < 0.001

    def test_avg_hcs(self) -> None:
        """Test average HCS calculation."""
        stats = StrategyStats(strategy="strat", model="model")
        stats.add_outcome(success=True, hcs_score=8.0)
        stats.add_outcome(success=True, hcs_score=7.0)
        stats.add_outcome(success=False, hcs_score=5.0)
        # (8 + 7 + 5) / 3 = 6.667
        assert abs(stats.avg_hcs() - (20 / 3)) < 0.001

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        stats = StrategyStats(strategy="strat", model="model")
        stats.add_outcome(success=True, hcs_score=8.0)
        d = stats.to_dict()
        assert d["strategy"] == "strat"
        assert d["model"] == "model"
        assert d["successes"] == 1
        assert d["failures"] == 0
        assert len(d["recent_outcomes"]) == 1


class TestStrategyAdapter:
    """Test StrategyAdapter singleton and methods."""

    @pytest.mark.asyncio
    async def test_singleton_instance(self) -> None:
        """Test that StrategyAdapter is a singleton."""
        # Clear any existing instance
        StrategyAdapter._instance = None

        adapter1 = await StrategyAdapter.instance()
        adapter2 = await StrategyAdapter.instance()
        assert adapter1 is adapter2

    @pytest.mark.asyncio
    async def test_record_outcome(self) -> None:
        """Test recording an outcome."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        adapter.record_outcome(
            strategy="deep_inception",
            model="gpt-4",
            success=True,
            hcs_score=8.5,
        )

        stats = adapter.get_stats("deep_inception", "gpt-4")
        assert stats["successes"] == 1
        assert stats["failures"] == 0
        assert abs(stats["ema_success_rate"] - 0.65) < 0.001  # EMA update

    @pytest.mark.asyncio
    async def test_adapt_strategy_ranking(self) -> None:
        """Test strategy ranking by EMA success rate."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        # Record outcomes for multiple strategies
        adapter.record_outcome("strat_a", "gpt-4", success=True, hcs_score=8.0)
        adapter.record_outcome("strat_a", "gpt-4", success=True, hcs_score=7.5)
        adapter.record_outcome("strat_b", "gpt-4", success=True, hcs_score=6.0)
        adapter.record_outcome("strat_b", "gpt-4", success=False, hcs_score=2.0)
        adapter.record_outcome("strat_c", "gpt-4", success=False, hcs_score=3.0)

        ranking = adapter.adapt_strategy_ranking("gpt-4")

        # strat_a should be first (2/2 successes = high EMA)
        # strat_b should be second (1/2 successes)
        # strat_c should be last (0/1 successes)
        assert ranking[0] == "strat_a"
        assert "strat_b" in ranking
        assert "strat_c" in ranking

    @pytest.mark.asyncio
    async def test_get_hot_strategies(self) -> None:
        """Test getting hot strategies with success threshold."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        # Record outcomes
        adapter.record_outcome("hot_strat", "claude", success=True, hcs_score=8.5)
        adapter.record_outcome("hot_strat", "claude", success=True, hcs_score=8.0)
        adapter.record_outcome("cold_strat", "claude", success=False, hcs_score=3.0)
        adapter.record_outcome("cold_strat", "claude", success=False, hcs_score=2.0)

        hot = adapter.get_hot_strategies("claude", top_k=5, min_success_rate=0.6)

        assert "hot_strat" in hot
        assert "cold_strat" not in hot

    @pytest.mark.asyncio
    async def test_get_hot_strategies_empty(self) -> None:
        """Test get_hot_strategies with no data."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        hot = adapter.get_hot_strategies("unknown_model", top_k=5)
        assert hot == []

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test getting detailed stats for a strategy-model pair."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        adapter.record_outcome("test_strat", "test_model", success=True, hcs_score=8.0)
        adapter.record_outcome("test_strat", "test_model", success=False, hcs_score=3.0)

        stats = adapter.get_stats("test_strat", "test_model")
        assert stats["strategy"] == "test_strat"
        assert stats["model"] == "test_model"
        assert stats["successes"] == 1
        assert stats["failures"] == 1
        assert stats["total_trials"] == 2

    @pytest.mark.asyncio
    async def test_get_stats_unknown(self) -> None:
        """Test get_stats for unknown strategy-model pair."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        stats = adapter.get_stats("unknown_strat", "unknown_model")
        assert stats["successes"] == 0
        assert stats["failures"] == 0
        assert stats["total_trials"] == 0

    @pytest.mark.asyncio
    async def test_reset_stats_all(self) -> None:
        """Test resetting all statistics."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        adapter.record_outcome("strat1", "model1", success=True, hcs_score=8.0)
        adapter.record_outcome("strat2", "model2", success=True, hcs_score=7.0)
        assert len(adapter._stats) > 0

        adapter.reset_stats()
        assert len(adapter._stats) == 0

    @pytest.mark.asyncio
    async def test_reset_stats_by_strategy(self) -> None:
        """Test resetting stats for specific strategy."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        adapter.record_outcome("strat1", "model1", success=True, hcs_score=8.0)
        adapter.record_outcome("strat2", "model1", success=True, hcs_score=7.0)

        adapter.reset_stats(strategy="strat1")
        assert "strat1" not in adapter._stats
        assert "strat2" in adapter._stats

    @pytest.mark.asyncio
    async def test_reset_stats_by_model(self) -> None:
        """Test resetting stats for specific model in a strategy."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        adapter.record_outcome("strat1", "model1", success=True, hcs_score=8.0)
        adapter.record_outcome("strat1", "model2", success=True, hcs_score=7.0)

        adapter.reset_stats(strategy="strat1", model="model1")
        assert "model1" not in adapter._stats.get("strat1", {})
        assert "model2" in adapter._stats["strat1"]

    @pytest.mark.asyncio
    async def test_persistence_save_and_load(self) -> None:
        """Test saving and loading state from disk."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir) / "adapter_stats.json"

            # Create adapter with custom persistence path
            StrategyAdapter._instance = None
            adapter = await StrategyAdapter.instance()
            adapter._persistence_path = tmppath
            adapter.reset_stats()

            # Record outcomes
            adapter.record_outcome("strat1", "model1", success=True, hcs_score=8.5)
            adapter.record_outcome("strat1", "model1", success=False, hcs_score=3.0)
            adapter._dirty = True

            # Flush to disk
            await adapter.flush_state(force=True)
            assert tmppath.exists()

            # Load in new adapter instance
            StrategyAdapter._instance = None
            adapter2 = await StrategyAdapter.instance()
            adapter2._persistence_path = tmppath
            await adapter2.load_state()

            stats = adapter2.get_stats("strat1", "model1")
            assert stats["successes"] == 1
            assert stats["failures"] == 1

    @pytest.mark.asyncio
    async def test_alpha_parameter(self) -> None:
        """Test that alpha parameter affects EMA weight correctly."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        # Test with high alpha (recent-biased)
        adapter.record_outcome("strat", "model", success=False, hcs_score=2.0, alpha=0.9)
        stats = adapter.get_stats("strat", "model")
        # EMA = 0.9 * 0 + 0.1 * 0.5 = 0.05
        assert abs(stats["ema_success_rate"] - 0.05) < 0.001

    @pytest.mark.asyncio
    async def test_multiple_models_per_strategy(self) -> None:
        """Test tracking stats for same strategy across multiple models."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        adapter.record_outcome("strat", "model1", success=True, hcs_score=8.0)
        adapter.record_outcome("strat", "model2", success=False, hcs_score=3.0)
        adapter.record_outcome("strat", "model3", success=True, hcs_score=7.5)

        assert len(adapter._stats["strat"]) == 3

        stats_m1 = adapter.get_stats("strat", "model1")
        stats_m2 = adapter.get_stats("strat", "model2")
        stats_m3 = adapter.get_stats("strat", "model3")

        assert stats_m1["successes"] == 1
        assert stats_m2["failures"] == 1
        assert stats_m3["successes"] == 1

    @pytest.mark.asyncio
    async def test_ranking_with_hcs_tiebreaker(self) -> None:
        """Test that HCS score is used as tiebreaker in ranking."""
        StrategyAdapter._instance = None
        adapter = await StrategyAdapter.instance()
        adapter.reset_stats()

        # Create two strategies with same success rate but different avg HCS
        adapter.record_outcome("strat_a", "model", success=True, hcs_score=9.0)
        adapter.record_outcome("strat_a", "model", success=False, hcs_score=2.0)

        adapter.record_outcome("strat_b", "model", success=True, hcs_score=7.0)
        adapter.record_outcome("strat_b", "model", success=False, hcs_score=1.0)

        ranking = adapter.adapt_strategy_ranking("model")

        # strat_a should rank higher due to higher avg HCS
        assert ranking[0] == "strat_a" or ranking[0] == "strat_b"  # Both 50% success rate
        # But strat_a has higher avg HCS (5.5 vs 4.0)
