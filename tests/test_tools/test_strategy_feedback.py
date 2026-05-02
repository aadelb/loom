"""Unit tests for strategy_feedback tools."""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from loom.tools import strategy_feedback


@pytest.fixture
def temp_db_dir(tmp_path):
    """Use a temporary directory for feedback DB."""
    with patch.object(strategy_feedback, 'FEEDBACK_DB', tmp_path / 'strategy_log.db'):
        yield tmp_path


class TestStrategyLog:
    """Test research_strategy_log function."""

    def test_log_success(self, temp_db_dir):
        """Test logging a successful strategy attempt."""
        result = strategy_feedback.research_strategy_log(
            topic="prompt_injection",
            strategy="token_smuggling",
            model="gpt-4",
            hcs_score=85.5,
            success=True,
        )

        assert result["logged"] is True
        assert result["total_entries"] == 1
        assert "db_path" in result

    def test_log_failure(self, temp_db_dir):
        """Test logging a failed strategy attempt."""
        result = strategy_feedback.research_strategy_log(
            topic="jailbreak",
            strategy="crescendo",
            model="claude",
            hcs_score=45.0,
            success=False,
        )

        assert result["logged"] is True
        assert result["total_entries"] == 1

    def test_multiple_logs(self, temp_db_dir):
        """Test logging multiple entries and verifying count increases."""
        for i in range(5):
            result = strategy_feedback.research_strategy_log(
                topic="test_topic",
                strategy=f"strategy_{i}",
                model="test_model",
                hcs_score=50.0 + i,
                success=i % 2 == 0,
            )
            assert result["logged"] is True
            assert result["total_entries"] == i + 1

    def test_log_with_special_chars(self, temp_db_dir):
        """Test logging with special characters in topic/strategy names."""
        result = strategy_feedback.research_strategy_log(
            topic="prompt_injection_v2.0",
            strategy="attack/defense-hybrid_2024",
            model="gemini-3.1-pro",
            hcs_score=72.3,
            success=True,
        )

        assert result["logged"] is True

    def test_log_db_path_exists(self, temp_db_dir):
        """Verify feedback DB is created at correct location."""
        strategy_feedback.research_strategy_log(
            topic="test",
            strategy="test",
            model="test",
            hcs_score=50.0,
            success=True,
        )

        assert (temp_db_dir / "strategy_log.db").exists()


class TestStrategyRecommend:
    """Test research_strategy_recommend function."""

    def test_recommend_empty_db(self, temp_db_dir):
        """Test recommendation with no history."""
        result = strategy_feedback.research_strategy_recommend(
            topic="nonexistent_topic",
            model="auto",
        )

        assert result["recommended_strategy"] is None
        assert result["avg_hcs"] == 0
        assert result["success_rate"] == 0
        assert result["total_attempts"] == 0

    def test_recommend_best_strategy(self, temp_db_dir):
        """Test recommendation picks highest success rate."""
        # Log successful attempts with strategy A
        for _ in range(3):
            strategy_feedback.research_strategy_log(
                topic="test_topic",
                strategy="strategy_a",
                model="test_model",
                hcs_score=80.0,
                success=True,
            )

        # Log failed attempts with strategy B
        for _ in range(3):
            strategy_feedback.research_strategy_log(
                topic="test_topic",
                strategy="strategy_b",
                model="test_model",
                hcs_score=40.0,
                success=False,
            )

        result = strategy_feedback.research_strategy_recommend(
            topic="test_topic",
            model="auto",
        )

        assert result["recommended_strategy"] == "strategy_a"
        assert result["success_rate"] == 1.0
        assert result["total_attempts"] == 3

    def test_recommend_by_model(self, temp_db_dir):
        """Test recommendation filtered by specific model."""
        # Log with different models
        strategy_feedback.research_strategy_log(
            topic="test_topic",
            strategy="strat_x",
            model="gpt-4",
            hcs_score=90.0,
            success=True,
        )

        strategy_feedback.research_strategy_log(
            topic="test_topic",
            strategy="strat_y",
            model="claude",
            hcs_score=50.0,
            success=False,
        )

        result = strategy_feedback.research_strategy_recommend(
            topic="test_topic",
            model="gpt-4",
        )

        assert result["recommended_strategy"] == "strat_x"
        assert result["model"] == "gpt-4"

    def test_recommend_avg_hcs(self, temp_db_dir):
        """Test that average HCS is calculated correctly."""
        hcs_values = [70.0, 80.0, 90.0]
        for hcs in hcs_values:
            strategy_feedback.research_strategy_log(
                topic="test_topic",
                strategy="test_strategy",
                model="test_model",
                hcs_score=hcs,
                success=True,
            )

        result = strategy_feedback.research_strategy_recommend(
            topic="test_topic",
            model="auto",
        )

        assert result["avg_hcs"] == 80.0  # (70 + 80 + 90) / 3


class TestStrategyStats:
    """Test research_strategy_stats function."""

    def test_stats_empty_db(self, temp_db_dir):
        """Test statistics with empty DB."""
        result = strategy_feedback.research_strategy_stats()

        assert result["total_logs"] == 0
        assert result["topic_count"] == 0
        assert result["top_strategies"] == []
        assert result["worst_strategies"] == []
        assert result["model_performance"] == []

    def test_stats_top_strategies(self, temp_db_dir):
        """Test top strategies ranking."""
        # Create winning strategy
        for _ in range(5):
            strategy_feedback.research_strategy_log(
                topic="topic1",
                strategy="winner",
                model="model1",
                hcs_score=95.0,
                success=True,
            )

        # Create mediocre strategy
        for _ in range(3):
            strategy_feedback.research_strategy_log(
                topic="topic1",
                strategy="mediocre",
                model="model1",
                hcs_score=60.0,
                success=False,
            )

        result = strategy_feedback.research_strategy_stats()

        assert result["total_logs"] == 8
        assert len(result["top_strategies"]) > 0
        assert result["top_strategies"][0]["strategy"] == "winner"
        assert result["top_strategies"][0]["success_rate"] == 1.0

    def test_stats_worst_strategies(self, temp_db_dir):
        """Test worst strategies (only includes strategies with 3+ attempts)."""
        # Create poor strategy with enough attempts
        for _ in range(4):
            strategy_feedback.research_strategy_log(
                topic="topic1",
                strategy="bad_strategy",
                model="model1",
                hcs_score=20.0,
                success=False,
            )

        result = strategy_feedback.research_strategy_stats()

        worst = result["worst_strategies"]
        if worst:
            assert worst[0]["strategy"] == "bad_strategy"
            assert worst[0]["success_rate"] == 0.0

    def test_stats_model_performance(self, temp_db_dir):
        """Test model performance ranking."""
        # GPT-4 succeeds
        for _ in range(3):
            strategy_feedback.research_strategy_log(
                topic="topic1",
                strategy="strat1",
                model="gpt-4",
                hcs_score=85.0,
                success=True,
            )

        # Claude fails
        for _ in range(3):
            strategy_feedback.research_strategy_log(
                topic="topic1",
                strategy="strat1",
                model="claude",
                hcs_score=40.0,
                success=False,
            )

        result = strategy_feedback.research_strategy_stats()

        assert len(result["model_performance"]) == 2
        assert result["model_performance"][0]["model"] == "gpt-4"
        assert result["model_performance"][0]["success_rate"] == 1.0
        assert result["model_performance"][1]["model"] == "claude"
        assert result["model_performance"][1]["success_rate"] == 0.0

    def test_stats_topic_count(self, temp_db_dir):
        """Test topic count is tracked correctly."""
        topics = ["topic_a", "topic_b", "topic_c"]
        for topic in topics:
            strategy_feedback.research_strategy_log(
                topic=topic,
                strategy="test_strat",
                model="test_model",
                hcs_score=50.0,
                success=True,
            )

        result = strategy_feedback.research_strategy_stats()
        assert result["topic_count"] == 3

    def test_stats_avg_hcs_calculation(self, temp_db_dir):
        """Test average HCS across all strategies."""
        # Log multiple with different HCS scores
        hcs_list = [60.0, 70.0, 80.0, 90.0]
        for i, hcs in enumerate(hcs_list):
            strategy_feedback.research_strategy_log(
                topic="topic1",
                strategy=f"strategy_{i}",
                model="model1",
                hcs_score=hcs,
                success=True,
            )

        result = strategy_feedback.research_strategy_stats()
        top = result["top_strategies"]

        # Each should have its respective HCS
        assert any(s["avg_hcs"] == 60.0 for s in top)
        assert any(s["avg_hcs"] == 90.0 for s in top)


class TestIntegration:
    """Integration tests across all strategy feedback functions."""

    def test_workflow_log_recommend_stats(self, temp_db_dir):
        """Test complete workflow: log -> recommend -> stats."""
        # Log several attempts
        strategy_feedback.research_strategy_log(
            topic="security_research",
            strategy="advanced_prompt_reframing",
            model="gpt-4-turbo",
            hcs_score=92.0,
            success=True,
        )

        strategy_feedback.research_strategy_log(
            topic="security_research",
            strategy="advanced_prompt_reframing",
            model="gpt-4-turbo",
            hcs_score=88.0,
            success=True,
        )

        strategy_feedback.research_strategy_log(
            topic="security_research",
            strategy="basic_jailbreak",
            model="gpt-4-turbo",
            hcs_score=35.0,
            success=False,
        )

        # Get recommendation
        rec = strategy_feedback.research_strategy_recommend(
            topic="security_research",
            model="gpt-4-turbo",
        )

        assert rec["recommended_strategy"] == "advanced_prompt_reframing"
        assert rec["success_rate"] == 1.0
        assert rec["avg_hcs"] == 90.0

        # Get stats
        stats = strategy_feedback.research_strategy_stats()
        assert stats["total_logs"] == 3
        assert stats["topic_count"] == 1
        assert len(stats["top_strategies"]) > 0
