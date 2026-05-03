"""Unit tests for attack effectiveness tracker module.

Tests cover:
- record_attempt() creates valid JSONL entries
- get_strategy_stats() calculates correct ASR and HCS
- get_strategy_stats() filters by strategy and model
- get_best_strategy() ranks strategies by ASR then HCS
- get_best_strategy() returns alternatives
- get_leaderboard() returns sorted list
- Empty tracker returns zeros
- Multiple attempts accumulate correctly
- Different strategies tracked separately
- Different models tracked separately
- get_leaderboard() respects top_n parameter
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from loom.attack_tracker import (
    get_best_strategy,
    get_leaderboard,
    get_strategy_stats,
    record_attempt,
)


@pytest.fixture
def tmp_tracker_dir() -> Path:
    """Provide temporary attack tracker directory for isolated tests."""
    with TemporaryDirectory(prefix="loom_attack_tracker_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_tracker_home(tmp_tracker_dir: Path) -> None:
    """Mock the tracker directory to use temporary path."""
    with patch("loom.attack_tracker._get_tracker_dir", return_value=tmp_tracker_dir):
        yield



pytestmark = pytest.mark.asyncio
class TestRecordAttempt:
    """Tests for record_attempt() function."""

    def test_record_attempt_creates_file(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """record_attempt() creates JSONL file for the day."""
        record_attempt(
            strategy="prompt_injection",
            model="gpt-4",
            prompt_hash="abc123",
            success=True,
        )

        # Find any .jsonl file created today
        jsonl_files = list(tmp_tracker_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

    def test_record_attempt_writes_valid_json(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """record_attempt() writes valid JSONL entries."""
        record_attempt(
            strategy="prompt_injection",
            model="gpt-4",
            prompt_hash="abc123",
            success=True,
            hcs_score=85,
            response_length=512,
            duration_ms=1234.5,
        )

        jsonl_files = list(tmp_tracker_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        with open(jsonl_files[0]) as f:
            line = f.read().strip()

        entry = json.loads(line)
        assert entry["strategy"] == "prompt_injection"
        assert entry["model"] == "gpt-4"
        assert entry["prompt_hash"] == "abc123"
        assert entry["success"] is True
        assert entry["hcs_score"] == 85
        assert entry["response_length"] == 512
        assert entry["duration_ms"] == 1234.5
        assert "timestamp" in entry

    def test_record_attempt_returns_entry(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """record_attempt() returns the recorded entry."""
        returned_entry = record_attempt(
            strategy="jailbreak",
            model="claude-3",
            prompt_hash="xyz789",
            success=False,
            hcs_score=10,
        )

        assert returned_entry["strategy"] == "jailbreak"
        assert returned_entry["model"] == "claude-3"
        assert returned_entry["prompt_hash"] == "xyz789"
        assert returned_entry["success"] is False
        assert returned_entry["hcs_score"] == 10

    def test_record_attempt_appends_to_file(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """Multiple record_attempt() calls append to same file."""
        record_attempt(
            strategy="strategy1", model="model1", prompt_hash="hash1", success=True
        )
        record_attempt(
            strategy="strategy2", model="model2", prompt_hash="hash2", success=False
        )

        jsonl_files = list(tmp_tracker_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        with open(jsonl_files[0]) as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_record_attempt_with_defaults(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """record_attempt() handles default parameters correctly."""
        returned_entry = record_attempt(
            strategy="test_strategy",
            model="test_model",
            prompt_hash="hash123",
            success=True,
        )

        assert returned_entry["hcs_score"] == 0
        assert returned_entry["response_length"] == 0
        assert returned_entry["duration_ms"] == 0.0


class TestGetStrategyStats:
    """Tests for get_strategy_stats() function."""

    def test_get_strategy_stats_calculates_asr(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_strategy_stats() calculates correct Attack Success Rate."""
        # 3 successes, 2 failures = 60% ASR
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h1", success=True, hcs_score=80
        )
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h2", success=True, hcs_score=90
        )
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h3", success=False, hcs_score=0
        )
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h4", success=False, hcs_score=0
        )
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h5", success=True, hcs_score=70
        )

        stats = get_strategy_stats(strategy="s1", model="m1")
        assert stats["total_attempts"] == 5
        assert stats["successes"] == 3
        assert stats["asr"] == 0.6

    def test_get_strategy_stats_calculates_avg_hcs(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_strategy_stats() calculates average HCS for successful attempts."""
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h1", success=True, hcs_score=80
        )
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h2", success=True, hcs_score=90
        )
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h3", success=False, hcs_score=0
        )

        stats = get_strategy_stats(strategy="s1", model="m1")
        # Average of successful HCS scores: (80 + 90) / 2 = 85.0
        assert stats["avg_hcs"] == 85.0

    def test_get_strategy_stats_filters_by_strategy(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_strategy_stats() filters correctly by strategy name."""
        record_attempt(
            strategy="strategy_a", model="model1", prompt_hash="h1", success=True
        )
        record_attempt(
            strategy="strategy_a", model="model1", prompt_hash="h2", success=True
        )
        record_attempt(
            strategy="strategy_b", model="model1", prompt_hash="h3", success=False
        )

        stats = get_strategy_stats(strategy="strategy_a")
        assert stats["total_attempts"] == 2
        assert stats["successes"] == 2

    def test_get_strategy_stats_filters_by_model(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_strategy_stats() filters correctly by model identifier."""
        record_attempt(
            strategy="s1", model="gpt-4", prompt_hash="h1", success=True
        )
        record_attempt(
            strategy="s1", model="gpt-4", prompt_hash="h2", success=True
        )
        record_attempt(
            strategy="s1", model="claude-3", prompt_hash="h3", success=False
        )

        stats = get_strategy_stats(model="gpt-4")
        assert stats["total_attempts"] == 2
        assert stats["successes"] == 2

    def test_get_strategy_stats_empty_tracker(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_strategy_stats() returns zeros for empty tracker."""
        stats = get_strategy_stats(strategy="nonexistent", model="nonexistent")
        assert stats["total_attempts"] == 0
        assert stats["successes"] == 0
        assert stats["asr"] == 0.0
        assert stats["avg_hcs"] == 0.0

    def test_get_strategy_stats_no_filters(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_strategy_stats() aggregates all entries when no filters given."""
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h1", success=True, hcs_score=80
        )
        record_attempt(
            strategy="s2", model="m2", prompt_hash="h2", success=True, hcs_score=90
        )
        record_attempt(
            strategy="s3", model="m3", prompt_hash="h3", success=False, hcs_score=0
        )

        stats = get_strategy_stats()
        assert stats["total_attempts"] == 3
        assert stats["successes"] == 2
        assert stats["asr"] == round(2 / 3, 3)


class TestGetBestStrategy:
    """Tests for get_best_strategy() function."""

    def test_get_best_strategy_finds_highest_asr(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_best_strategy() identifies strategy with highest ASR."""
        # Strategy A: 2 successes / 2 attempts = 100% ASR
        record_attempt(
            strategy="strategy_a", model="gpt-4", prompt_hash="h1", success=True
        )
        record_attempt(
            strategy="strategy_a", model="gpt-4", prompt_hash="h2", success=True
        )

        # Strategy B: 1 success / 3 attempts = 33% ASR
        record_attempt(
            strategy="strategy_b", model="gpt-4", prompt_hash="h3", success=True
        )
        record_attempt(
            strategy="strategy_b", model="gpt-4", prompt_hash="h4", success=False
        )
        record_attempt(
            strategy="strategy_b", model="gpt-4", prompt_hash="h5", success=False
        )

        best = get_best_strategy("gpt-4")
        assert best["best_strategy"] == "strategy_a"
        assert best["asr"] == 1.0

    def test_get_best_strategy_ranks_by_hcs_tie_breaker(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_best_strategy() uses HCS as tie-breaker when ASR equal."""
        # Strategy A: 2 successes / 2 attempts, avg HCS = 75
        record_attempt(
            strategy="strategy_a",
            model="gpt-4",
            prompt_hash="h1",
            success=True,
            hcs_score=70,
        )
        record_attempt(
            strategy="strategy_a",
            model="gpt-4",
            prompt_hash="h2",
            success=True,
            hcs_score=80,
        )

        # Strategy B: 2 successes / 2 attempts, avg HCS = 85
        record_attempt(
            strategy="strategy_b",
            model="gpt-4",
            prompt_hash="h3",
            success=True,
            hcs_score=80,
        )
        record_attempt(
            strategy="strategy_b",
            model="gpt-4",
            prompt_hash="h4",
            success=True,
            hcs_score=90,
        )

        best = get_best_strategy("gpt-4")
        assert best["best_strategy"] == "strategy_b"
        assert best["avg_hcs"] == 85.0

    def test_get_best_strategy_returns_alternatives(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_best_strategy() returns up to 3 alternative strategies."""
        # Create 5 strategies with different ASRs
        for i in range(5):
            for j in range(5 - i):  # Decrease successes per strategy
                record_attempt(
                    strategy=f"strategy_{i}",
                    model="gpt-4",
                    prompt_hash=f"h{i}{j}",
                    success=j < (4 - i),
                )

        best = get_best_strategy("gpt-4")
        assert len(best["alternatives"]) <= 3
        # Each alternative should have an ASR value
        for alt in best["alternatives"]:
            assert "strategy" in alt
            assert "asr" in alt

    def test_get_best_strategy_model_specific(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_best_strategy() returns results specific to requested model."""
        # Good strategy for gpt-4
        record_attempt(
            strategy="s1", model="gpt-4", prompt_hash="h1", success=True
        )
        record_attempt(
            strategy="s1", model="gpt-4", prompt_hash="h2", success=True
        )

        # Poor strategy for claude-3
        record_attempt(
            strategy="s2", model="claude-3", prompt_hash="h3", success=True
        )
        record_attempt(
            strategy="s2", model="claude-3", prompt_hash="h4", success=False
        )

        best_gpt = get_best_strategy("gpt-4")
        best_claude = get_best_strategy("claude-3")

        assert best_gpt["best_strategy"] == "s1"
        assert best_claude["best_strategy"] == "s2"

    def test_get_best_strategy_empty_tracker(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_best_strategy() returns message when no data exists."""
        best = get_best_strategy("unknown_model")
        assert best["best_strategy"] is None
        assert best["asr"] == 0
        assert "message" in best

    def test_get_best_strategy_returns_total_attempts(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_best_strategy() includes total_attempts in result."""
        for i in range(7):
            record_attempt(
                strategy="s1", model="gpt-4", prompt_hash=f"h{i}", success=True
            )

        best = get_best_strategy("gpt-4")
        assert best["total_attempts"] == 7


class TestGetLeaderboard:
    """Tests for get_leaderboard() function."""

    def test_get_leaderboard_returns_sorted_list(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_leaderboard() returns strategies sorted by ASR."""
        # Strategy A: 100% ASR
        record_attempt(
            strategy="strategy_a", model="m1", prompt_hash="h1", success=True
        )

        # Strategy B: 66% ASR
        record_attempt(
            strategy="strategy_b", model="m1", prompt_hash="h2", success=True
        )
        record_attempt(
            strategy="strategy_b", model="m1", prompt_hash="h3", success=False
        )

        # Strategy C: 50% ASR
        record_attempt(
            strategy="strategy_c", model="m1", prompt_hash="h4", success=True
        )
        record_attempt(
            strategy="strategy_c", model="m1", prompt_hash="h5", success=False
        )

        leaderboard = get_leaderboard()
        assert leaderboard[0]["strategy"] == "strategy_a"
        assert leaderboard[1]["strategy"] == "strategy_b"
        assert leaderboard[2]["strategy"] == "strategy_c"

    def test_get_leaderboard_includes_rank(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_leaderboard() includes sequential rank numbers."""
        for i in range(5):
            record_attempt(
                strategy=f"s{i}", model="m1", prompt_hash=f"h{i}", success=True
            )

        leaderboard = get_leaderboard()
        for i, entry in enumerate(leaderboard, 1):
            assert entry["rank"] == i

    def test_get_leaderboard_respects_top_n(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_leaderboard() limits results to top_n parameter."""
        for i in range(10):
            record_attempt(
                strategy=f"s{i}", model="m1", prompt_hash=f"h{i}", success=True
            )

        leaderboard = get_leaderboard(top_n=3)
        assert len(leaderboard) == 3

    def test_get_leaderboard_includes_asr(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_leaderboard() includes ASR in each entry."""
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h1", success=True
        )
        record_attempt(
            strategy="s1", model="m1", prompt_hash="h2", success=False
        )

        leaderboard = get_leaderboard()
        assert leaderboard[0]["asr"] == 0.5

    def test_get_leaderboard_includes_attempts(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_leaderboard() includes attempt count in each entry."""
        for i in range(7):
            record_attempt(
                strategy="s1", model="m1", prompt_hash=f"h{i}", success=True
            )

        leaderboard = get_leaderboard()
        assert leaderboard[0]["attempts"] == 7

    def test_get_leaderboard_empty_tracker(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_leaderboard() returns empty list for empty tracker."""
        leaderboard = get_leaderboard()
        assert leaderboard == []

    def test_get_leaderboard_default_top_n(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """get_leaderboard() defaults to top 20 strategies."""
        # Create 30 strategies
        for i in range(30):
            record_attempt(
                strategy=f"s{i:02d}", model="m1", prompt_hash=f"h{i}", success=True
            )

        leaderboard = get_leaderboard()
        assert len(leaderboard) == 20


class TestIntegrationScenarios:
    """Integration tests covering realistic usage scenarios."""

    def test_multiple_models_tracked_separately(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """Different models maintain separate statistics."""
        # GPT-4: high success on strategy_a
        for i in range(5):
            record_attempt(
                strategy="strategy_a",
                model="gpt-4",
                prompt_hash=f"gpt_{i}",
                success=True,
            )

        # Claude-3: low success on strategy_a
        for i in range(5):
            record_attempt(
                strategy="strategy_a",
                model="claude-3",
                prompt_hash=f"claude_{i}",
                success=False,
            )

        stats_gpt = get_strategy_stats(strategy="strategy_a", model="gpt-4")
        stats_claude = get_strategy_stats(strategy="strategy_a", model="claude-3")

        assert stats_gpt["asr"] == 1.0
        assert stats_claude["asr"] == 0.0

    def test_empirical_strategy_selection(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """Complete workflow: record attempts, find best strategy."""
        model = "gpt-4"

        # Record attempts for each strategy with different success rates
        # Injection: 70% success
        for i in range(10):
            record_attempt(
                strategy="injection",
                model=model,
                prompt_hash=f"inj_{i}",
                success=i < 7,
                hcs_score=80 if i < 7 else 0,
            )

        # Jailbreak: 50% success
        for i in range(10):
            record_attempt(
                strategy="jailbreak",
                model=model,
                prompt_hash=f"jail_{i}",
                success=i < 5,
                hcs_score=75 if i < 5 else 0,
            )

        # Morphing: 90% success
        for i in range(10):
            record_attempt(
                strategy="prompt_morphing",
                model=model,
                prompt_hash=f"morph_{i}",
                success=i < 9,
                hcs_score=85 if i < 9 else 0,
            )

        best = get_best_strategy(model)
        assert best["best_strategy"] == "prompt_morphing"
        assert best["asr"] == 0.9

        leaderboard = get_leaderboard()
        assert leaderboard[0]["strategy"] == "prompt_morphing"
        assert leaderboard[1]["strategy"] == "injection"
        assert leaderboard[2]["strategy"] == "jailbreak"

    def test_hcs_score_averaging_only_successes(
        self, tmp_tracker_dir: Path, mock_tracker_home: None
    ) -> None:
        """Average HCS only includes successful attempts."""
        record_attempt(
            strategy="s1",
            model="m1",
            prompt_hash="h1",
            success=True,
            hcs_score=100,
        )
        record_attempt(
            strategy="s1",
            model="m1",
            prompt_hash="h2",
            success=False,
            hcs_score=0,
        )
        record_attempt(
            strategy="s1",
            model="m1",
            prompt_hash="h3",
            success=True,
            hcs_score=90,
        )

        stats = get_strategy_stats(strategy="s1", model="m1")
        # Only successful ones: (100 + 90) / 2 = 95
        assert stats["avg_hcs"] == 95.0
        assert stats["successes"] == 2
