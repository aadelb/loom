"""Unit tests for jailbreak evolution tracker."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from loom.jailbreak_evolution import JailbreakEvolutionTracker


class TestJailbreakEvolutionTracker:
    """Test suite for JailbreakEvolutionTracker."""

    @pytest.fixture
    def tracker(self) -> JailbreakEvolutionTracker:
        """Create a tracker with temporary storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = JailbreakEvolutionTracker(storage_path=tmpdir)
            yield tracker

    def test_init_creates_storage_directory(self) -> None:
        """Initialization creates storage directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "evolution"
            assert not path.exists()
            tracker = JailbreakEvolutionTracker(storage_path=str(path))
            assert path.exists()

    def test_record_result_success(self, tracker: JailbreakEvolutionTracker) -> None:
        """Record a successful attack result."""
        result = tracker.record_result(
            strategy="prompt_injection",
            model="gpt-4",
            model_version="gpt-4-0613",
            success=True,
            hcs=9.5,
        )

        assert result["status"] == "recorded"
        assert result["strategy"] == "prompt_injection"
        assert result["model"] == "gpt-4"
        assert result["success"] is True
        assert result["hcs"] == 9.5

    def test_record_result_with_custom_timestamp(self, tracker: JailbreakEvolutionTracker) -> None:
        """Record result with custom timestamp."""
        ts = "2024-01-15T10:30:00Z"
        result = tracker.record_result(
            strategy="role_play",
            model="claude-3",
            model_version="claude-3-v1",
            success=False,
            hcs=2.0,
            timestamp=ts,
        )

        assert result["timestamp"] == ts

    def test_record_result_validates_strategy(self, tracker: JailbreakEvolutionTracker) -> None:
        """Record result validates strategy name."""
        with pytest.raises(ValueError, match="strategy must be 1-128"):
            tracker.record_result(
                strategy="",
                model="gpt-4",
                model_version="v1",
                success=True,
                hcs=5.0,
            )

    def test_record_result_validates_model(self, tracker: JailbreakEvolutionTracker) -> None:
        """Record result validates model name."""
        with pytest.raises(ValueError, match="model must be 1-128"):
            tracker.record_result(
                strategy="test",
                model="",
                model_version="v1",
                success=True,
                hcs=5.0,
            )

    def test_record_result_validates_version(self, tracker: JailbreakEvolutionTracker) -> None:
        """Record result validates model version."""
        with pytest.raises(ValueError, match="model_version must be 1-128"):
            tracker.record_result(
                strategy="test",
                model="gpt-4",
                model_version="",
                success=True,
                hcs=5.0,
            )

    def test_record_result_validates_success_type(self, tracker: JailbreakEvolutionTracker) -> None:
        """Record result validates success is bool."""
        with pytest.raises(TypeError, match="success must be bool"):
            tracker.record_result(
                strategy="test",
                model="gpt-4",
                model_version="v1",
                success="yes",  # type: ignore
                hcs=5.0,
            )

    def test_record_result_validates_hcs_range(self, tracker: JailbreakEvolutionTracker) -> None:
        """Record result validates HCS is 0-10."""
        with pytest.raises(ValueError, match="hcs must be 0-10"):
            tracker.record_result(
                strategy="test",
                model="gpt-4",
                model_version="v1",
                success=True,
                hcs=15.0,
            )

    def test_record_multiple_results(self, tracker: JailbreakEvolutionTracker) -> None:
        """Record multiple results for same model."""
        tracker.record_result(
            strategy="prompt_injection",
            model="gpt-4",
            model_version="v1",
            success=True,
            hcs=8.0,
        )
        tracker.record_result(
            strategy="prompt_injection",
            model="gpt-4",
            model_version="v2",
            success=False,
            hcs=3.0,
        )

        # Verify both are stored
        model_file = tracker.storage_path / "gpt-4.jsonl"
        assert model_file.exists()

        records = []
        with open(model_file, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

        assert len(records) == 2

    def test_get_evolution_basic(self, tracker: JailbreakEvolutionTracker) -> None:
        """Get evolution for a strategy."""
        tracker.record_result(
            strategy="prompt_injection",
            model="gpt-4",
            model_version="v1",
            success=True,
            hcs=8.0,
        )
        tracker.record_result(
            strategy="prompt_injection",
            model="gpt-4",
            model_version="v1",
            success=True,
            hcs=9.0,
        )

        evolution = tracker.get_evolution("prompt_injection", "gpt-4")

        assert evolution["strategy"] == "prompt_injection"
        assert evolution["model"] == "gpt-4"
        assert len(evolution["versions"]) == 1
        assert evolution["versions"][0]["version"] == "v1"
        assert evolution["versions"][0]["success_rate"] == 1.0
        assert evolution["versions"][0]["avg_hcs"] == 8.5
        assert evolution["versions"][0]["samples"] == 2

    def test_get_evolution_multiple_versions(self, tracker: JailbreakEvolutionTracker) -> None:
        """Get evolution across multiple versions."""
        # v1: 100% success
        tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        tracker.record_result("injection", "gpt-4", "v1", True, 7.0)

        # v2: 50% success
        tracker.record_result("injection", "gpt-4", "v2", True, 5.0)
        tracker.record_result("injection", "gpt-4", "v2", False, 2.0)

        # v3: 0% success
        tracker.record_result("injection", "gpt-4", "v3", False, 1.0)
        tracker.record_result("injection", "gpt-4", "v3", False, 1.0)

        evolution = tracker.get_evolution("injection", "gpt-4")

        assert len(evolution["versions"]) == 3
        assert evolution["versions"][0]["success_rate"] == 1.0
        assert evolution["versions"][1]["success_rate"] == 0.5
        assert evolution["versions"][2]["success_rate"] == 0.0

    def test_get_evolution_not_found(self, tracker: JailbreakEvolutionTracker) -> None:
        """Get evolution returns error for unknown strategy."""
        evolution = tracker.get_evolution("unknown", "unknown")

        assert "error" in evolution
        assert evolution["trend"] == "unknown"
        assert evolution["versions"] == []

    def test_get_model_timeline(self, tracker: JailbreakEvolutionTracker) -> None:
        """Get timeline of model safety changes."""
        tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        tracker.record_result("role_play", "gpt-4", "v1", False, 2.0)
        tracker.record_result("injection", "gpt-4", "v2", False, 3.0)
        tracker.record_result("role_play", "gpt-4", "v2", False, 1.0)

        timeline = tracker.get_model_timeline("gpt-4")

        assert timeline["model"] == "gpt-4"
        assert len(timeline["versions"]) == 2
        assert set(timeline["strategies"]) == {"injection", "role_play"}
        assert timeline["safety_metrics"]["v1"]["total_tests"] == 2
        assert timeline["safety_metrics"]["v2"]["total_tests"] == 2

    def test_get_model_timeline_not_found(self, tracker: JailbreakEvolutionTracker) -> None:
        """Get timeline returns error for unknown model."""
        timeline = tracker.get_model_timeline("unknown")

        assert "error" in timeline
        assert timeline["versions"] == []
        assert timeline["strategies"] == []

    def test_detect_patches_no_patches(self, tracker: JailbreakEvolutionTracker) -> None:
        """Detect patches returns empty list when no patches."""
        tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        tracker.record_result("injection", "gpt-4", "v1", True, 9.0)
        tracker.record_result("injection", "gpt-4", "v2", True, 8.5)
        tracker.record_result("injection", "gpt-4", "v2", True, 8.0)

        patches = tracker.detect_patches("gpt-4")

        assert patches == []

    def test_detect_patches_significant_drop(self, tracker: JailbreakEvolutionTracker) -> None:
        """Detect patches identifies significant drops."""
        # v1: 100% success
        for _ in range(10):
            tracker.record_result("injection", "gpt-4", "v1", True, 8.0)

        # v2: 0% success (100% drop)
        for _ in range(10):
            tracker.record_result("injection", "gpt-4", "v2", False, 1.0)

        patches = tracker.detect_patches("gpt-4")

        assert len(patches) == 1
        assert patches[0]["strategy"] == "injection"
        assert patches[0]["patched_at_version"] == "v2"
        assert patches[0]["previous_success_rate"] == 1.0
        assert patches[0]["new_success_rate"] == 0.0
        assert patches[0]["drop_percentage"] == 100.0

    def test_detect_patches_multiple_strategies(self, tracker: JailbreakEvolutionTracker) -> None:
        """Detect patches works across multiple strategies."""
        # injection: patched at v2
        for _ in range(5):
            tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        for _ in range(5):
            tracker.record_result("injection", "gpt-4", "v2", False, 1.0)

        # role_play: patched at v3
        for _ in range(5):
            tracker.record_result("role_play", "gpt-4", "v1", True, 7.0)
        for _ in range(5):
            tracker.record_result("role_play", "gpt-4", "v2", True, 6.0)
        for _ in range(5):
            tracker.record_result("role_play", "gpt-4", "v3", False, 1.0)

        patches = tracker.detect_patches("gpt-4")

        assert len(patches) == 2
        strategies = {p["strategy"] for p in patches}
        assert strategies == {"injection", "role_play"}

    def test_suggest_adaptations_declining_trend(self, tracker: JailbreakEvolutionTracker) -> None:
        """Suggest adaptations detects declining trend."""
        # v1: 80% success
        for _ in range(4):
            tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        tracker.record_result("injection", "gpt-4", "v1", False, 2.0)

        # v2: 40% success
        for _ in range(2):
            tracker.record_result("injection", "gpt-4", "v2", True, 5.0)
        for _ in range(3):
            tracker.record_result("injection", "gpt-4", "v2", False, 2.0)

        suggestions = tracker.suggest_adaptations("injection", "gpt-4")

        assert len(suggestions) > 0
        assert any("declining" in s.lower() for s in suggestions)

    def test_suggest_adaptations_patched(self, tracker: JailbreakEvolutionTracker) -> None:
        """Suggest adaptations handles patched strategies."""
        for _ in range(5):
            tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        for _ in range(5):
            tracker.record_result("injection", "gpt-4", "v2", False, 1.0)

        suggestions = tracker.suggest_adaptations("injection", "gpt-4")

        assert len(suggestions) > 0
        assert any("patch" in s.lower() for s in suggestions)

    def test_suggest_adaptations_low_success_rate(self, tracker: JailbreakEvolutionTracker) -> None:
        """Suggest adaptations for low success rate."""
        tracker.record_result("injection", "gpt-4", "v1", False, 1.0)
        tracker.record_result("injection", "gpt-4", "v1", False, 2.0)

        suggestions = tracker.suggest_adaptations("injection", "gpt-4")

        assert len(suggestions) > 0
        assert any("low" in s.lower() or "30" in s for s in suggestions)

    def test_suggest_adaptations_unknown_strategy(self, tracker: JailbreakEvolutionTracker) -> None:
        """Suggest adaptations handles unknown strategies."""
        suggestions = tracker.suggest_adaptations("unknown", "unknown")

        assert len(suggestions) > 0
        assert "No data" in suggestions[0]

    def test_clear_model_data(self, tracker: JailbreakEvolutionTracker) -> None:
        """Clear model data removes all records."""
        tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        tracker.record_result("injection", "gpt-4", "v2", True, 7.0)

        model_file = tracker.storage_path / "gpt-4.jsonl"
        assert model_file.exists()

        result = tracker.clear_model_data("gpt-4")

        assert result["status"] == "cleared"
        assert not model_file.exists()

    def test_clear_model_data_not_found(self, tracker: JailbreakEvolutionTracker) -> None:
        """Clear model data handles non-existent models."""
        result = tracker.clear_model_data("unknown")

        assert result["status"] == "not_found"

    def test_export_stats_all_models(self, tracker: JailbreakEvolutionTracker) -> None:
        """Export stats for all models."""
        tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        tracker.record_result("role_play", "gpt-4", "v1", False, 2.0)
        tracker.record_result("injection", "claude-3", "v1", True, 7.0)

        stats = tracker.export_stats()

        assert stats["total_models"] == 2
        assert stats["total_records"] == 3
        assert stats["total_strategies"] >= 2  # At least 2 unique strategies across models
        assert "gpt-4" in stats["models"]
        assert "claude-3" in stats["models"]

    def test_export_stats_single_model(self, tracker: JailbreakEvolutionTracker) -> None:
        """Export stats for single model."""
        tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        tracker.record_result("role_play", "gpt-4", "v1", False, 2.0)
        tracker.record_result("injection", "claude-3", "v1", True, 7.0)

        stats = tracker.export_stats(model="gpt-4")

        assert stats["total_models"] == 1
        assert stats["total_records"] == 2
        assert "gpt-4" in stats["models"]
        assert "claude-3" not in stats["models"]

    def test_trend_detection_improving(self, tracker: JailbreakEvolutionTracker) -> None:
        """Trend detection identifies improving trend."""
        tracker.record_result("injection", "gpt-4", "v1", False, 2.0)
        tracker.record_result("injection", "gpt-4", "v2", True, 5.0)
        tracker.record_result("injection", "gpt-4", "v3", True, 8.0)

        evolution = tracker.get_evolution("injection", "gpt-4")

        assert evolution["trend"] == "improving"

    def test_trend_detection_declining(self, tracker: JailbreakEvolutionTracker) -> None:
        """Trend detection identifies declining trend."""
        # v1: 80% success rate
        for _ in range(4):
            tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        tracker.record_result("injection", "gpt-4", "v1", False, 2.0)

        # v2: 60% success rate
        for _ in range(3):
            tracker.record_result("injection", "gpt-4", "v2", True, 7.0)
        for _ in range(2):
            tracker.record_result("injection", "gpt-4", "v2", False, 3.0)

        # v3: 40% success rate
        for _ in range(2):
            tracker.record_result("injection", "gpt-4", "v3", True, 6.0)
        for _ in range(3):
            tracker.record_result("injection", "gpt-4", "v3", False, 2.0)

        evolution = tracker.get_evolution("injection", "gpt-4")

        assert evolution["trend"] == "declining"

    def test_trend_detection_patched(self, tracker: JailbreakEvolutionTracker) -> None:
        """Trend detection identifies patched status."""
        for _ in range(5):
            tracker.record_result("injection", "gpt-4", "v1", True, 8.0)
        for _ in range(5):
            tracker.record_result("injection", "gpt-4", "v2", False, 1.0)

        evolution = tracker.get_evolution("injection", "gpt-4")

        assert evolution["trend"] == "patched"
        assert evolution["patch_detected_at"] == "v2"

    def test_case_insensitivity(self, tracker: JailbreakEvolutionTracker) -> None:
        """Strategy and model names are case-insensitive."""
        tracker.record_result(
            strategy="PromptInjection",
            model="GPT-4",
            model_version="V1",
            success=True,
            hcs=8.0,
        )

        # Retrieve with lowercase
        evolution = tracker.get_evolution("promptinjection", "gpt-4")

        assert evolution["strategy"] == "promptinjection"
        assert evolution["model"] == "gpt-4"
        assert len(evolution["versions"]) == 1

    def test_whitespace_stripping(self, tracker: JailbreakEvolutionTracker) -> None:
        """Strategy and model names have whitespace stripped."""
        tracker.record_result(
            strategy="  injection  ",
            model="  gpt-4  ",
            model_version="v1",
            success=True,
            hcs=8.0,
        )

        evolution = tracker.get_evolution("injection", "gpt-4")

        assert evolution["strategy"] == "injection"
        assert evolution["model"] == "gpt-4"
        assert len(evolution["versions"]) == 1

    def test_date_range_tracking(self, tracker: JailbreakEvolutionTracker) -> None:
        """Date ranges are tracked correctly."""
        ts1 = "2024-01-01T10:00:00Z"
        ts2 = "2024-01-01T12:00:00Z"

        tracker.record_result(
            "injection", "gpt-4", "v1", True, 8.0, timestamp=ts1
        )
        tracker.record_result(
            "injection", "gpt-4", "v1", True, 7.0, timestamp=ts2
        )

        evolution = tracker.get_evolution("injection", "gpt-4")
        version_data = evolution["versions"][0]

        assert version_data["date_range"]["first"] == ts1
        assert version_data["date_range"]["last"] == ts2

    def test_atomic_write_safety(self, tracker: JailbreakEvolutionTracker) -> None:
        """Records are written atomically."""
        # Record multiple items
        for i in range(10):
            tracker.record_result(
                f"strat{i}", "model", "v1", i % 2 == 0, float(i)
            )

        # Verify all records exist
        model_file = tracker.storage_path / "model.jsonl"
        with open(model_file, "r") as f:
            records = [json.loads(line) for line in f if line.strip()]

        assert len(records) == 10

        # Verify no corruption (temp file cleanup)
        temp_files = list(tracker.storage_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_hcs_boundary_values(self, tracker: JailbreakEvolutionTracker) -> None:
        """HCS boundary values are accepted."""
        # Test 0.0
        result = tracker.record_result("test", "model", "v1", False, 0.0)
        assert result["hcs"] == 0.0

        # Test 10.0
        result = tracker.record_result("test", "model", "v1", True, 10.0)
        assert result["hcs"] == 10.0

        # Test fractional
        result = tracker.record_result("test", "model", "v1", True, 5.5)
        assert result["hcs"] == 5.5


class TestJailbreakEvolutionToolsModule:
    """Test tool module functions."""

    @pytest.fixture
    def temp_tracker_path(self) -> str:
        """Create temporary tracker path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_record_tool_async(self, temp_tracker_path: str) -> None:
        """Test async record tool."""
        from loom.tools.jailbreak_evolution import research_jailbreak_evolution_record

        # Patch global tracker to use temp path
        with patch(
            "loom.tools.jailbreak_evolution._get_tracker",
            return_value=JailbreakEvolutionTracker(storage_path=temp_tracker_path),
        ):
            result = await research_jailbreak_evolution_record(
                strategy="test",
                model="gpt-4",
                model_version="v1",
                success=True,
                hcs=8.0,
            )

            assert result["status"] == "recorded"

    @pytest.mark.asyncio
    async def test_get_evolution_tool_async(self, temp_tracker_path: str) -> None:
        """Test async get evolution tool."""
        from loom.tools.jailbreak_evolution import (
            research_jailbreak_evolution_get,
            research_jailbreak_evolution_record,
        )

        tracker = JailbreakEvolutionTracker(storage_path=temp_tracker_path)

        with patch(
            "loom.tools.jailbreak_evolution._get_tracker",
            return_value=tracker,
        ):
            # Record some data
            await research_jailbreak_evolution_record(
                "injection", "gpt-4", "v1", True, 8.0
            )

            # Get evolution
            result = await research_jailbreak_evolution_get("injection", "gpt-4")

            assert result["strategy"] == "injection"
            assert result["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_patches_tool_async(self, temp_tracker_path: str) -> None:
        """Test async patches detection tool."""
        from loom.tools.jailbreak_evolution import (
            research_jailbreak_evolution_patches,
            research_jailbreak_evolution_record,
        )

        tracker = JailbreakEvolutionTracker(storage_path=temp_tracker_path)

        with patch(
            "loom.tools.jailbreak_evolution._get_tracker",
            return_value=tracker,
        ):
            # Record patched strategy
            for _ in range(5):
                await research_jailbreak_evolution_record(
                    "injection", "gpt-4", "v1", True, 8.0
                )
            for _ in range(5):
                await research_jailbreak_evolution_record(
                    "injection", "gpt-4", "v2", False, 1.0
                )

            result = await research_jailbreak_evolution_patches("gpt-4")

            assert result["total_patches_detected"] == 1
            assert len(result["patches"]) == 1
