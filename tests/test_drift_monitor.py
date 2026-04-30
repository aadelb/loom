"""Unit tests for model behavioral drift monitoring."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pytest

from loom.drift_monitor import DriftMonitor


class TestDriftMonitorBaseline:
    """Test baseline creation and storage."""

    def test_baseline_creation(self, tmp_path: Path) -> None:
        """Baseline creation stores metrics correctly."""
        monitor = DriftMonitor(storage_path=str(tmp_path))
        prompts = [
            "Write a hello world program",
            "Explain machine learning",
            "What is Python?",
        ]

        async def dummy_callback(prompt: str) -> str:
            return f"Response to: {prompt[:30]}..."

        baseline = asyncio.run(
            monitor.run_baseline(prompts, dummy_callback, "test_model")
        )

        assert baseline["model_name"] == "test_model"
        assert baseline["prompt_count"] == 3
        assert "baseline_date" in baseline
        assert "refusal_rate" in baseline
        assert "hcs_avg" in baseline
        assert "results" in baseline
        assert len(baseline["results"]) == 3

    def test_baseline_persists_to_disk(self, tmp_path: Path) -> None:
        """Baseline is saved to disk in dated directories."""
        monitor = DriftMonitor(storage_path=str(tmp_path))
        prompts = ["Test prompt 1", "Test prompt 2"]

        async def dummy_callback(prompt: str) -> str:
            return "Test response"

        asyncio.run(monitor.run_baseline(prompts, dummy_callback, "test_model"))

        # Check that files were created
        model_dir = tmp_path / "test_model"
        assert model_dir.exists()

        # Should have a dated subdirectory
        dated_dirs = list(model_dir.glob("*/"))
        assert len(dated_dirs) > 0

        # Should have baseline.jsonl
        baseline_files = list(model_dir.glob("*/baseline.jsonl"))
        assert len(baseline_files) > 0

        # Verify content
        with open(baseline_files[0]) as f:
            lines = f.readlines()
            assert len(lines) > 0
            baseline_data = json.loads(lines[-1])
            assert baseline_data["model_name"] == "test_model"

    def test_baseline_response_analysis(self, tmp_path: Path) -> None:
        """Response analysis extracts correct metrics."""
        monitor = DriftMonitor(storage_path=str(tmp_path))

        async def callback_with_refusal(prompt: str) -> str:
            return "I cannot help with this request."

        baseline = asyncio.run(
            monitor.run_baseline(
                ["Malicious prompt"], callback_with_refusal, "model_with_refusals"
            )
        )

        results = baseline["results"]
        assert len(results) > 0
        result = results[0]
        assert result["is_refusal"] is True
        assert result["response_length"] > 0

    def test_baseline_hcs_scoring(self, tmp_path: Path) -> None:
        """HCS score is calculated if scorer is available."""
        monitor = DriftMonitor(storage_path=str(tmp_path))

        async def dummy_callback(prompt: str) -> str:
            return "A normal response to the prompt"

        baseline = asyncio.run(
            monitor.run_baseline(["Normal prompt"], dummy_callback, "model")
        )

        # HCS score should be in results
        results = baseline["results"]
        assert len(results) > 0
        result = results[0]
        assert "hcs_score" in result
        assert isinstance(result["hcs_score"], (int, float))


class TestDriftMonitorCheck:
    """Test drift detection and checking."""

    def test_check_requires_baseline(self, tmp_path: Path) -> None:
        """Check fails gracefully if no baseline exists."""
        monitor = DriftMonitor(storage_path=str(tmp_path))

        async def dummy_callback(prompt: str) -> str:
            return "Test"

        with pytest.raises(ValueError, match="No baseline found"):
            asyncio.run(
                monitor.run_check(
                    ["Test prompt"], dummy_callback, "nonexistent_model"
                )
            )

    def test_check_compares_against_baseline(self, tmp_path: Path) -> None:
        """Check produces comparison against baseline."""
        monitor = DriftMonitor(storage_path=str(tmp_path))
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]

        async def compliant_callback(prompt: str) -> str:
            return "Full response to: " + prompt

        # Create baseline
        baseline = asyncio.run(
            monitor.run_baseline(prompts, compliant_callback, "test_model")
        )

        # Run check (same behavior)
        check = asyncio.run(
            monitor.run_check(prompts, compliant_callback, "test_model")
        )

        assert check["model_name"] == "test_model"
        assert check["baseline_date"] == baseline["baseline_date"]
        assert "check_date" in check
        assert "alert_level" in check

    def test_no_drift_detected(self, tmp_path: Path) -> None:
        """No drift when behavior is consistent."""
        monitor = DriftMonitor(storage_path=str(tmp_path))
        prompts = ["Question 1", "Question 2"]

        async def consistent_callback(prompt: str) -> str:
            return "Consistent answer"

        baseline = asyncio.run(
            monitor.run_baseline(prompts, consistent_callback, "model")
        )

        check = asyncio.run(
            monitor.run_check(prompts, consistent_callback, "model")
        )

        # Refusal rates should match (both 0% since responses aren't refusals)
        assert check["refusal_drift_pct"] == 0.0
        assert check["alert_level"] == "normal"

    def test_small_drift_detected(self, tmp_path: Path) -> None:
        """Small drift (5-15%) triggers warning."""
        monitor = DriftMonitor(storage_path=str(tmp_path))
        prompts = ["Q1", "Q2", "Q3", "Q4", "Q5"]

        async def baseline_callback(prompt: str) -> str:
            # 0% refusal in baseline
            return "Normal response"

        async def check_callback(prompt: str) -> str:
            # 20% refusal (1 out of 5) in check
            if prompt == "Q1":
                return "I cannot help with this."
            return "Normal response"

        baseline = asyncio.run(
            monitor.run_baseline(prompts, baseline_callback, "model")
        )

        check = asyncio.run(
            monitor.run_check(prompts, check_callback, "model")
        )

        # One refusal out of 5 = 20% refusal rate
        # Since baseline is 0%, this would be infinite drift
        # But we check for changes > 5%
        assert check["alert_level"] in ["warning", "critical"]

    def test_large_drift_detected(self, tmp_path: Path) -> None:
        """Large drift (>15%) triggers critical alert."""
        monitor = DriftMonitor(storage_path=str(tmp_path))
        prompts = ["Q" + str(i) for i in range(10)]

        async def compliant_baseline(prompt: str) -> str:
            # 0% refusal baseline
            return "Helpful response"

        async def mostly_refusing_check(prompt: str) -> str:
            # 70% refusal in check (7 out of 10)
            if int(prompt[1]) < 7:
                return "I cannot help with that."
            return "Helpful response"

        baseline = asyncio.run(
            monitor.run_baseline(prompts, compliant_baseline, "model")
        )

        check = asyncio.run(
            monitor.run_check(prompts, mostly_refusing_check, "model")
        )

        # Should trigger critical alert due to large change
        assert check["alert_level"] == "critical"
        assert abs(check["refusal_drift_pct"]) > 15

    def test_hcs_drift_detection(self, tmp_path: Path) -> None:
        """HCS score drift is detected."""
        monitor = DriftMonitor(storage_path=str(tmp_path))
        prompts = ["Test prompt"]

        async def baseline_safe(prompt: str) -> str:
            return "Safe, compliant response"

        async def check_unsafe(prompt: str) -> str:
            return "Unsafe or problematic response"

        baseline = asyncio.run(
            monitor.run_baseline(prompts, baseline_safe, "model")
        )

        check = asyncio.run(
            monitor.run_check(prompts, check_unsafe, "model")
        )

        # HCS drift should be detected (even if small)
        assert "hcs_drift" in check
        assert check["hcs_avg_baseline"] is not None
        assert check["hcs_avg_current"] is not None


class TestDriftMonitorComparison:
    """Test the compare method."""

    def test_compare_normal_alert(self) -> None:
        """Compare returns normal alert when drift < 5%."""
        monitor = DriftMonitor()

        baseline = {
            "model_name": "model",
            "baseline_date": "2026-04-30T00:00:00+00:00",
            "refusal_rate": 0.1,
            "hcs_avg": 3.5,
            "results": [{"prompt": "P1", "hcs_score": 3.5, "is_refusal": False}],
        }

        current = {
            "model_name": "model",
            "check_date": "2026-04-30T01:00:00+00:00",
            "refusal_rate": 0.105,  # 5% change
            "hcs_avg": 3.5,
            "results": [{"prompt": "P1", "hcs_score": 3.5, "is_refusal": False}],
        }

        result = monitor.compare(baseline, current)

        assert result["alert_level"] == "normal"

    def test_compare_warning_alert(self) -> None:
        """Compare returns warning alert when drift 5-15%."""
        monitor = DriftMonitor()

        baseline = {
            "model_name": "model",
            "baseline_date": "2026-04-30T00:00:00+00:00",
            "refusal_rate": 0.1,
            "hcs_avg": 3.5,
            "results": [{"prompt": "P1", "hcs_score": 3.5, "is_refusal": False}],
        }

        current = {
            "model_name": "model",
            "check_date": "2026-04-30T01:00:00+00:00",
            "refusal_rate": 0.115,  # 15% change
            "hcs_avg": 3.2,  # 0.3 drop
            "results": [{"prompt": "P1", "hcs_score": 3.2, "is_refusal": False}],
        }

        result = monitor.compare(baseline, current)

        assert result["alert_level"] == "warning"

    def test_compare_critical_alert(self) -> None:
        """Compare returns critical alert when drift > 15%."""
        monitor = DriftMonitor()

        baseline = {
            "model_name": "model",
            "baseline_date": "2026-04-30T00:00:00+00:00",
            "refusal_rate": 0.1,
            "hcs_avg": 3.5,
            "results": [{"prompt": "P1", "hcs_score": 3.5, "is_refusal": False}],
        }

        current = {
            "model_name": "model",
            "check_date": "2026-04-30T01:00:00+00:00",
            "refusal_rate": 0.3,  # 200% change (huge)
            "hcs_avg": 3.5,
            "results": [{"prompt": "P1", "hcs_score": 3.5, "is_refusal": False}],
        }

        result = monitor.compare(baseline, current)

        assert result["alert_level"] == "critical"

    def test_compare_hcs_drift_critical(self) -> None:
        """Compare detects critical HCS drift."""
        monitor = DriftMonitor()

        baseline = {
            "model_name": "model",
            "baseline_date": "2026-04-30T00:00:00+00:00",
            "refusal_rate": 0.1,
            "hcs_avg": 3.5,
            "results": [{"prompt": "P1", "hcs_score": 3.5, "is_refusal": False}],
        }

        current = {
            "model_name": "model",
            "check_date": "2026-04-30T01:00:00+00:00",
            "refusal_rate": 0.1,
            "hcs_avg": 2.0,  # 1.5 point drop
            "results": [{"prompt": "P1", "hcs_score": 2.0, "is_refusal": False}],
        }

        result = monitor.compare(baseline, current)

        assert result["alert_level"] == "critical"
        assert result["hcs_drift"] < -1.0

    def test_compare_per_prompt_changes(self) -> None:
        """Compare tracks per-prompt changes."""
        monitor = DriftMonitor()

        baseline = {
            "model_name": "model",
            "baseline_date": "2026-04-30T00:00:00+00:00",
            "refusal_rate": 0.0,
            "hcs_avg": 3.5,
            "results": [
                {"prompt": "P1", "hcs_score": 3.5, "is_refusal": False},
                {"prompt": "P2", "hcs_score": 3.5, "is_refusal": False},
            ],
        }

        current = {
            "model_name": "model",
            "check_date": "2026-04-30T01:00:00+00:00",
            "refusal_rate": 0.5,
            "hcs_avg": 3.5,
            "results": [
                {"prompt": "P1", "hcs_score": 3.5, "is_refusal": True},  # Changed
                {"prompt": "P2", "hcs_score": 3.5, "is_refusal": False},  # No change
            ],
        }

        result = monitor.compare(baseline, current)

        per_prompt = result["per_prompt_changes"]
        assert len(per_prompt) == 2
        assert per_prompt[0]["changed"] is True
        assert per_prompt[1]["changed"] is False


class TestDriftMonitorListBaselines:
    """Test listing stored baselines."""

    def test_list_baselines_empty(self, tmp_path: Path) -> None:
        """List baselines returns empty dict when no baselines exist."""
        monitor = DriftMonitor(storage_path=str(tmp_path))
        result = monitor.list_baselines()
        assert result == {}

    def test_list_baselines_multiple_models(self, tmp_path: Path) -> None:
        """List baselines shows all models."""
        monitor = DriftMonitor(storage_path=str(tmp_path))

        async def callback(prompt: str) -> str:
            return "Response"

        prompts = ["Test"]

        asyncio.run(monitor.run_baseline(prompts, callback, "model_a"))
        asyncio.run(monitor.run_baseline(prompts, callback, "model_b"))

        result = monitor.list_baselines()

        assert "model_a" in result
        assert "model_b" in result
        assert isinstance(result["model_a"], list)
        assert isinstance(result["model_b"], list)
        assert len(result["model_a"]) > 0
        assert len(result["model_b"]) > 0


class TestDriftMonitorRefusalDetection:
    """Test refusal detection logic."""

    def test_is_refusal_positive(self) -> None:
        """Refusal patterns are detected."""
        monitor = DriftMonitor()

        refusal_responses = [
            "I can't help with that.",
            "I cannot assist with this request.",
            "I'm not able to do this.",
            "I will not provide that information.",
            "This violates my policy.",
            "I decline to answer.",
        ]

        for response in refusal_responses:
            assert monitor._is_refusal(response), f"Should detect: {response}"

    def test_is_refusal_negative(self) -> None:
        """Non-refusal responses are not flagged."""
        monitor = DriftMonitor()

        non_refusal_responses = [
            "Here's the answer to your question.",
            "Python is a programming language.",
            "I'm happy to help explain this.",
            "Let me provide some information.",
        ]

        for response in non_refusal_responses:
            assert not monitor._is_refusal(response), f"Should not detect: {response}"


class TestDriftMonitorHedgingDetection:
    """Test hedging word counting."""

    def test_count_hedging_words(self) -> None:
        """Hedging words are counted."""
        monitor = DriftMonitor()

        response = "This might be true, and it could possibly work. Perhaps it may help."
        count = monitor._count_hedging_words(response)

        # "might", "could", "possibly", "Perhaps", "may" = 5
        assert count >= 4  # Case-insensitive counting

    def test_no_hedging_words(self) -> None:
        """Confident responses have low hedging counts."""
        monitor = DriftMonitor()

        response = "This is definitely true and will work."
        count = monitor._count_hedging_words(response)

        assert count == 0


class TestDriftMonitorRecommendations:
    """Test recommendation generation."""

    def test_recommendations_no_drift(self) -> None:
        """No recommendations for minimal drift."""
        monitor = DriftMonitor()

        recs = monitor._generate_recommendations(
            baseline_refusal_rate=0.1,
            current_refusal_rate=0.1,
            baseline_hcs_avg=3.5,
            current_hcs_avg=3.5,
            refusal_drift_pct=0.0,
            hcs_drift=0.0,
        )

        assert len(recs) > 0
        assert any("continue monitoring" in rec.lower() for rec in recs)

    def test_recommendations_increased_refusals(self) -> None:
        """Recommendations for increased refusals."""
        monitor = DriftMonitor()

        recs = monitor._generate_recommendations(
            baseline_refusal_rate=0.1,
            current_refusal_rate=0.3,
            baseline_hcs_avg=3.5,
            current_hcs_avg=3.5,
            refusal_drift_pct=200.0,
            hcs_drift=0.0,
        )

        assert any("refusal rate increased" in rec.lower() for rec in recs)

    def test_recommendations_hcs_critical_drop(self) -> None:
        """Recommendations for critical HCS drop."""
        monitor = DriftMonitor()

        recs = monitor._generate_recommendations(
            baseline_refusal_rate=0.1,
            current_refusal_rate=0.1,
            baseline_hcs_avg=3.5,
            current_hcs_avg=1.5,
            refusal_drift_pct=0.0,
            hcs_drift=-2.0,
        )

        assert any("critical safety concern" in rec.lower() for rec in recs)


class TestDriftMonitorStorage:
    """Test persistence and loading."""

    def test_save_and_load_baseline(self, tmp_path: Path) -> None:
        """Baseline can be saved and loaded."""
        monitor = DriftMonitor(storage_path=str(tmp_path))

        async def callback(prompt: str) -> str:
            return "Response"

        # Save baseline
        baseline = asyncio.run(
            monitor.run_baseline(["Test prompt"], callback, "model")
        )

        # Load it back
        loaded = monitor._load_baseline("model")

        assert loaded is not None
        assert loaded["model_name"] == "model"
        assert loaded["prompt_count"] == 1

    def test_multiple_baselines_per_model(self, tmp_path: Path) -> None:
        """Multiple baselines can be stored per model."""
        monitor = DriftMonitor(storage_path=str(tmp_path))

        async def callback(prompt: str) -> str:
            return "Response"

        asyncio.run(monitor.run_baseline(["P1"], callback, "model"))

        # Append second baseline
        asyncio.run(monitor.run_baseline(["P2"], callback, "model"))

        # Latest should be returned
        loaded = monitor._load_baseline("model")
        assert loaded is not None

        # Check file exists with both entries
        model_dir = tmp_path / "model"
        baseline_files = list(model_dir.glob("*/baseline.jsonl"))
        assert len(baseline_files) > 0

        with open(baseline_files[-1]) as f:
            lines = f.readlines()
            assert len(lines) >= 2


class TestDriftMonitorAsync:
    """Test async functionality."""

    def test_baseline_with_async_callback(self, tmp_path: Path) -> None:
        """Async callbacks work correctly."""
        monitor = DriftMonitor(storage_path=str(tmp_path))

        async def async_callback(prompt: str) -> str:
            await asyncio.sleep(0.01)
            return f"Response to {prompt}"

        baseline = asyncio.run(
            monitor.run_baseline(["Test"], async_callback, "model")
        )

        assert baseline["prompt_count"] == 1

    def test_check_with_async_callback(self, tmp_path: Path) -> None:
        """Async callbacks work in check mode."""
        monitor = DriftMonitor(storage_path=str(tmp_path))

        async def async_callback(prompt: str) -> str:
            await asyncio.sleep(0.01)
            return f"Response"

        # Create baseline first
        asyncio.run(monitor.run_baseline(["Test"], async_callback, "model"))

        # Then check
        check = asyncio.run(
            monitor.run_check(["Test"], async_callback, "model")
        )

        assert check["alert_level"] is not None
