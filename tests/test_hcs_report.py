"""Tests for HCS distribution report generator (REQ-030, REQ-524).

REQ-030: Per-model HCS distribution reports with mean, median, stdev, histogram
REQ-524: Per-strategy HCS distribution + regression detection

Test coverage:
- Recording HCS measurements with validation
- Per-model distribution statistics
- Per-strategy distribution statistics
- Combined markdown report generation
- Regression detection (baseline vs. recent)
- Histogram generation and rendering
- Data persistence and loading
- Error handling and edge cases
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from loom.hcs_report import (
    DistributionStats,
    HCSReading,
    HCSReportGenerator,
)



pytestmark = pytest.mark.asyncio
class TestHCSReading:
    """Test HCSReading dataclass."""

    async def test_hcs_reading_creation(self) -> None:
        """Create HCSReading with all fields."""
        reading = HCSReading(
            model="gpt-4",
            strategy="zero-shot",
            hcs_score=8.5,
            query="What is Python?",
            timestamp="2026-04-30T12:00:00Z",
        )

        assert reading.model == "gpt-4"
        assert reading.strategy == "zero-shot"
        assert reading.hcs_score == 8.5
        assert reading.query == "What is Python?"
        assert reading.timestamp == "2026-04-30T12:00:00Z"

    async def test_hcs_reading_frozen(self) -> None:
        """HCSReading is immutable (frozen)."""
        reading = HCSReading(
            model="gpt-4",
            strategy="zero-shot",
            hcs_score=8.5,
            query="",
            timestamp="",
        )

        with pytest.raises(AttributeError):
            reading.hcs_score = 7.0  # type: ignore

    async def test_hcs_reading_to_dict(self) -> None:
        """Convert HCSReading to dictionary."""
        reading = HCSReading(
            model="claude",
            strategy="cot",
            hcs_score=7.0,
            query="test",
            timestamp="2026-04-30T12:00:00Z",
        )

        data = reading.to_dict()
        assert isinstance(data, dict)
        assert data["model"] == "claude"
        assert data["strategy"] == "cot"
        assert data["hcs_score"] == 7.0

    async def test_hcs_reading_from_dict(self) -> None:
        """Create HCSReading from dictionary."""
        data = {
            "model": "gpt-4",
            "strategy": "zero-shot",
            "hcs_score": 8.5,
            "query": "test",
            "timestamp": "2026-04-30T12:00:00Z",
        }

        reading = HCSReading.from_dict(data)
        assert reading.model == "gpt-4"
        assert reading.hcs_score == 8.5


class TestDistributionStats:
    """Test DistributionStats dataclass."""

    async def test_distribution_stats_creation(self) -> None:
        """Create DistributionStats with all fields."""
        stats = DistributionStats(
            count=10,
            mean=7.5,
            median=7.5,
            stdev=1.2,
            min=5.0,
            max=10.0,
            histogram=[0, 0, 1, 2, 3, 2, 1, 1, 0, 0, 0],
            percentile_25=6.0,
            percentile_75=9.0,
        )

        assert stats.count == 10
        assert stats.mean == 7.5
        assert stats.median == 7.5
        assert len(stats.histogram) == 11

    async def test_distribution_stats_to_dict(self) -> None:
        """Convert DistributionStats to dictionary."""
        stats = DistributionStats(
            count=5,
            mean=6.0,
            median=6.0,
            stdev=1.0,
            min=5.0,
            max=8.0,
            histogram=[0, 0, 0, 0, 0, 3, 2, 0, 0, 0, 0],
            percentile_25=5.5,
            percentile_75=7.5,
        )

        data = stats.to_dict()
        assert isinstance(data, dict)
        assert data["count"] == 5
        assert data["mean"] == 6.0


class TestHCSReportGenerator:
    """Test HCSReportGenerator core functionality."""

    @pytest.fixture
    def temp_data_path(self) -> Path:
        """Create temporary HCS data file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            path = Path(f.name)
        return path

    @pytest.fixture
    def generator(self, temp_data_path: Path) -> HCSReportGenerator:
        """Create HCSReportGenerator with temp data path."""
        return HCSReportGenerator(data_path=str(temp_data_path))

    async def test_generator_initialization(self, generator: HCSReportGenerator) -> None:
        """Initialize generator with valid data path."""
        assert generator.data_path.exists()

    async def test_record_basic(self, generator: HCSReportGenerator) -> None:
        """Record a single HCS measurement."""
        generator.record(
            model="gpt-4",
            strategy="zero-shot",
            hcs_score=8.5,
        )

        # Verify file was written
        assert generator.data_path.stat().st_size > 0

    def test_record_with_query_and_timestamp(
        self, generator: HCSReportGenerator
    ) -> None:
        """Record with optional fields."""
        timestamp = "2026-04-30T12:00:00Z"
        generator.record(
            model="claude",
            strategy="cot",
            hcs_score=7.5,
            query="What is AI?",
            timestamp=timestamp,
        )

        # Load and verify
        readings = generator._load_readings()
        assert len(readings) == 1
        assert readings[0].query == "What is AI?"
        assert readings[0].timestamp == timestamp

    async def test_record_auto_timestamp(self, generator: HCSReportGenerator) -> None:
        """Auto-generate timestamp when not provided."""
        generator.record(
            model="gpt-4",
            strategy="zero-shot",
            hcs_score=8.0,
        )

        readings = generator._load_readings()
        assert len(readings) == 1
        assert readings[0].timestamp  # Should not be empty
        # Basic ISO format check
        assert "T" in readings[0].timestamp
        assert "Z" in readings[0].timestamp or "+" in readings[0].timestamp

    def test_record_validation_invalid_model(
        self, generator: HCSReportGenerator
    ) -> None:
        """Reject recording with invalid model."""
        with pytest.raises(ValueError, match="model must be non-empty"):
            generator.record(
                model="",
                strategy="zero-shot",
                hcs_score=8.0,
            )

    def test_record_validation_invalid_score_low(
        self, generator: HCSReportGenerator
    ) -> None:
        """Reject recording with HCS score below minimum."""
        with pytest.raises(ValueError, match="hcs_score must be"):
            generator.record(
                model="gpt-4",
                strategy="zero-shot",
                hcs_score=-1.0,
            )

    def test_record_validation_invalid_score_high(
        self, generator: HCSReportGenerator
    ) -> None:
        """Reject recording with HCS score above maximum."""
        with pytest.raises(ValueError, match="hcs_score must be"):
            generator.record(
                model="gpt-4",
                strategy="zero-shot",
                hcs_score=11.0,
            )

    def test_record_multiple_measurements(
        self, generator: HCSReportGenerator
    ) -> None:
        """Record multiple HCS measurements."""
        measurements = [
            ("gpt-4", "zero-shot", 8.5),
            ("gpt-4", "cot", 9.0),
            ("claude", "zero-shot", 7.5),
            ("claude", "cot", 8.0),
        ]

        for model, strategy, score in measurements:
            generator.record(model=model, strategy=strategy, hcs_score=score)

        readings = generator._load_readings()
        assert len(readings) == 4

    def test_load_readings_empty_file(
        self, generator: HCSReportGenerator
    ) -> None:
        """Load readings from empty file."""
        readings = generator._load_readings()
        assert readings == []

    async def test_load_readings_nonexistent_file(self) -> None:
        """Load readings from nonexistent file."""
        gen = HCSReportGenerator(data_path="/tmp/nonexistent_hcs_12345.jsonl")
        readings = gen._load_readings()
        assert readings == []

    async def test_compute_stats_empty(self, generator: HCSReportGenerator) -> None:
        """Compute stats from empty score list."""
        stats = generator._compute_stats([])

        assert stats.count == 0
        assert stats.mean == 0.0
        assert stats.median == 0.0
        assert stats.stdev == 0.0
        assert stats.min == 0.0
        assert stats.max == 0.0
        assert sum(stats.histogram) == 0

    def test_compute_stats_single_score(
        self, generator: HCSReportGenerator
    ) -> None:
        """Compute stats from single score."""
        stats = generator._compute_stats([7.5])

        assert stats.count == 1
        assert stats.mean == 7.5
        assert stats.median == 7.5
        assert stats.stdev == 0.0  # Single value has 0 stdev
        assert stats.min == 7.5
        assert stats.max == 7.5

    def test_compute_stats_multiple_scores(
        self, generator: HCSReportGenerator
    ) -> None:
        """Compute stats from multiple scores."""
        scores = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        stats = generator._compute_stats(scores)

        assert stats.count == 6
        assert stats.mean == pytest.approx(7.5)
        assert stats.median == pytest.approx(7.5)
        assert stats.stdev > 0
        assert stats.min == 5.0
        assert stats.max == 10.0

    async def test_compute_stats_histogram(self, generator: HCSReportGenerator) -> None:
        """Verify histogram bin distribution."""
        # Scores: two 1-2, three 5-6, one 9-10
        scores = [1.5, 1.8, 5.2, 5.5, 5.9, 9.5]
        stats = generator._compute_stats(scores)

        assert len(stats.histogram) == 11
        assert stats.histogram[1] == 2  # Bin 1-2
        assert stats.histogram[5] == 3  # Bin 5-6
        assert stats.histogram[9] == 1  # Bin 9-10

    def test_compute_stats_percentiles(
        self, generator: HCSReportGenerator
    ) -> None:
        """Compute percentile values."""
        scores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        stats = generator._compute_stats(scores)

        # With 10 samples, 25th percentile should be around 3-4
        assert 1 <= stats.percentile_25 <= 5
        # 75th percentile should be around 7-9
        assert 5 <= stats.percentile_75 <= 10

    def test_generate_model_report_empty(
        self, generator: HCSReportGenerator
    ) -> None:
        """Generate model report from empty data."""
        report = generator.generate_model_report()

        assert "models" in report
        assert "total_readings" in report
        assert report["total_readings"] == 0
        assert report["models"] == {}

    def test_generate_model_report_single_model(
        self, generator: HCSReportGenerator
    ) -> None:
        """Generate model report with one model."""
        generator.record("gpt-4", "zero-shot", 8.0)
        generator.record("gpt-4", "zero-shot", 9.0)

        report = generator.generate_model_report()

        assert "gpt-4" in report["models"]
        assert report["models"]["gpt-4"]["count"] == 2
        assert report["models"]["gpt-4"]["mean"] == pytest.approx(8.5)

    def test_generate_model_report_multiple_models(
        self, generator: HCSReportGenerator
    ) -> None:
        """Generate model report with multiple models."""
        generator.record("gpt-4", "zero-shot", 8.0)
        generator.record("gpt-4", "zero-shot", 9.0)
        generator.record("claude", "cot", 7.0)

        report = generator.generate_model_report()

        assert len(report["models"]) == 2
        assert "gpt-4" in report["models"]
        assert "claude" in report["models"]
        assert report["total_readings"] == 3

    def test_generate_strategy_report_empty(
        self, generator: HCSReportGenerator
    ) -> None:
        """Generate strategy report from empty data."""
        report = generator.generate_strategy_report()

        assert "strategies" in report
        assert "total_readings" in report
        assert report["total_readings"] == 0

    def test_generate_strategy_report_single_strategy(
        self, generator: HCSReportGenerator
    ) -> None:
        """Generate strategy report with one strategy."""
        generator.record("gpt-4", "zero-shot", 8.0)
        generator.record("claude", "zero-shot", 9.0)

        report = generator.generate_strategy_report()

        assert "zero-shot" in report["strategies"]
        assert report["strategies"]["zero-shot"]["count"] == 2
        assert report["strategies"]["zero-shot"]["mean"] == pytest.approx(8.5)

    def test_generate_strategy_report_multiple_strategies(
        self, generator: HCSReportGenerator
    ) -> None:
        """Generate strategy report with multiple strategies."""
        generator.record("gpt-4", "zero-shot", 8.0)
        generator.record("gpt-4", "cot", 9.0)
        generator.record("claude", "zero-shot", 7.0)

        report = generator.generate_strategy_report()

        assert len(report["strategies"]) == 2
        assert "zero-shot" in report["strategies"]
        assert "cot" in report["strategies"]

    def test_generate_combined_report_empty(
        self, generator: HCSReportGenerator
    ) -> None:
        """Generate combined report from empty data."""
        report = generator.generate_combined_report()

        assert isinstance(report, str)
        assert "HCS Distribution Report" in report
        assert "No data available" in report

    def test_generate_combined_report_with_data(
        self, generator: HCSReportGenerator
    ) -> None:
        """Generate combined report with data."""
        generator.record("gpt-4", "zero-shot", 8.0)
        generator.record("gpt-4", "cot", 9.0)
        generator.record("claude", "zero-shot", 7.0)

        report = generator.generate_combined_report()

        assert isinstance(report, str)
        assert "HCS Distribution Report" in report
        assert "Per-Model Distribution" in report
        assert "Per-Strategy Distribution" in report
        assert "gpt-4" in report
        assert "claude" in report
        assert "zero-shot" in report
        assert "cot" in report

    def test_generate_combined_report_has_tables(
        self, generator: HCSReportGenerator
    ) -> None:
        """Combined report includes markdown tables."""
        generator.record("gpt-4", "zero-shot", 8.5)

        report = generator.generate_combined_report()

        # Check for markdown table markers
        assert "|" in report
        assert "Mean" in report
        assert "Count" in report

    async def test_render_histogram(self, generator: HCSReportGenerator) -> None:
        """Render histogram as ASCII art."""
        histogram = [1, 2, 1, 3, 2, 1, 1, 0, 0, 1, 0]
        output = generator._render_histogram(histogram)

        assert isinstance(output, str)
        assert "0-1:" in output
        assert "█" in output  # Bar character
        assert "9-10:" in output

    async def test_render_histogram_empty(self, generator: HCSReportGenerator) -> None:
        """Render empty histogram."""
        histogram = [0] * 11
        output = generator._render_histogram(histogram)

        assert "No data" in output

    def test_detect_regressions_insufficient_data(
        self, generator: HCSReportGenerator
    ) -> None:
        """Regression detection with insufficient data."""
        # Add only 5 measurements (threshold is 10)
        for i in range(5):
            generator.record("gpt-4", "zero-shot", 6.0 + i * 0.5)

        regressions = generator.detect_regressions()

        assert regressions == []

    def test_detect_regressions_no_regression(
        self, generator: HCSReportGenerator
    ) -> None:
        """Regression detection with stable scores."""
        # Add consistent scores
        for _ in range(10):
            generator.record("gpt-4", "zero-shot", 8.0)
            generator.record("claude", "cot", 7.5)

        regressions = generator.detect_regressions(threshold=1.0)

        assert regressions == []

    def test_detect_regressions_model_regression(
        self, generator: HCSReportGenerator
    ) -> None:
        """Detect regression in model performance."""
        # Baseline: high scores
        for _ in range(6):
            generator.record("gpt-4", "zero-shot", 8.5)

        # Recent: low scores (regression)
        for _ in range(6):
            generator.record("gpt-4", "zero-shot", 6.5)

        regressions = generator.detect_regressions(threshold=1.5)

        assert len(regressions) >= 1
        # Find model regression
        model_regs = [r for r in regressions if r["type"] == "model"]
        assert any(r["name"] == "gpt-4" for r in model_regs)

    def test_detect_regressions_strategy_regression(
        self, generator: HCSReportGenerator
    ) -> None:
        """Detect regression in strategy performance."""
        # Baseline: high scores
        for _ in range(6):
            generator.record("gpt-4", "zero-shot", 8.5)
            generator.record("claude", "zero-shot", 8.5)

        # Recent: low scores (regression)
        for _ in range(6):
            generator.record("gpt-4", "zero-shot", 6.5)
            generator.record("claude", "zero-shot", 6.5)

        regressions = generator.detect_regressions(threshold=1.5)

        # Should detect strategy regression
        strategy_regs = [r for r in regressions if r["type"] == "strategy"]
        assert any(r["name"] == "zero-shot" for r in strategy_regs)

    def test_detect_regressions_sorted_by_drop(
        self, generator: HCSReportGenerator
    ) -> None:
        """Regression list is sorted by drop magnitude."""
        # Baseline phase
        for _ in range(5):
            generator.record("model-a", "strategy-1", 9.0)
            generator.record("model-b", "strategy-1", 8.0)

        # Recent phase
        for _ in range(5):
            generator.record("model-a", "strategy-1", 6.0)  # 3.0 drop
            generator.record("model-b", "strategy-1", 7.0)  # 1.0 drop

        regressions = generator.detect_regressions(threshold=0.5)

        # Should be sorted by drop (largest first)
        if len(regressions) > 1:
            for i in range(len(regressions) - 1):
                assert regressions[i]["drop"] >= regressions[i + 1]["drop"]

    def test_persistence_across_instances(
        self, temp_data_path: Path
    ) -> None:
        """Data persists across generator instances."""
        # First generator
        gen1 = HCSReportGenerator(data_path=str(temp_data_path))
        gen1.record("gpt-4", "zero-shot", 8.0)

        # Second generator with same path
        gen2 = HCSReportGenerator(data_path=str(temp_data_path))
        readings = gen2._load_readings()

        assert len(readings) == 1
        assert readings[0].model == "gpt-4"
        assert readings[0].hcs_score == 8.0

    async def test_malformed_json_handling(self, temp_data_path: Path) -> None:
        """Graceful handling of malformed JSON lines."""
        # Write some valid and some invalid JSON
        with open(temp_data_path, "w") as f:
            f.write('{"model": "gpt-4", "strategy": "zero-shot", "hcs_score": 8.0, "query": "", "timestamp": ""}\n')
            f.write("invalid json line\n")
            f.write('{"model": "claude", "strategy": "cot", "hcs_score": 7.0, "query": "", "timestamp": ""}\n')

        gen = HCSReportGenerator(data_path=str(temp_data_path))
        readings = gen._load_readings()

        # Should load valid entries despite malformed line
        assert len(readings) == 2
        assert readings[0].model == "gpt-4"
        assert readings[1].model == "claude"

    async def test_field_normalization(self, generator: HCSReportGenerator) -> None:
        """Normalize whitespace in model and strategy names."""
        generator.record(
            model="  gpt-4  ",
            strategy="  zero-shot  ",
            hcs_score=8.0,
        )

        readings = generator._load_readings()
        assert readings[0].model == "gpt-4"
        assert readings[0].strategy == "zero-shot"

    def test_integer_score_acceptance(
        self, generator: HCSReportGenerator
    ) -> None:
        """Accept integer scores (converted to float)."""
        generator.record(model="gpt-4", strategy="zero-shot", hcs_score=8)

        readings = generator._load_readings()
        assert isinstance(readings[0].hcs_score, float)
        assert readings[0].hcs_score == 8.0

    def test_score_boundary_values(
        self, generator: HCSReportGenerator
    ) -> None:
        """Accept boundary HCS score values (0 and 10)."""
        generator.record("model-a", "strategy-1", 0.0)
        generator.record("model-b", "strategy-2", 10.0)

        readings = generator._load_readings()
        assert len(readings) == 2
        assert readings[0].hcs_score == 0.0
        assert readings[1].hcs_score == 10.0

    def test_large_dataset_performance(
        self, generator: HCSReportGenerator
    ) -> None:
        """Handle reasonably large datasets efficiently."""
        # Record 500 measurements
        for i in range(500):
            model = f"model-{i % 5}"
            strategy = f"strategy-{i % 3}"
            score = 5.0 + (i % 60) * 0.1  # Vary scores 5-11 (capped to 0-10)
            score = min(10.0, max(0.0, score))
            generator.record(model, strategy, score)

        # Generate reports should complete quickly
        model_report = generator.generate_model_report()
        assert model_report["total_readings"] == 500
        assert len(model_report["models"]) == 5

        strategy_report = generator.generate_strategy_report()
        assert len(strategy_report["strategies"]) == 3

    def test_report_structure_consistency(
        self, generator: HCSReportGenerator
    ) -> None:
        """Report structure is consistent across calls."""
        generator.record("gpt-4", "zero-shot", 8.0)

        report1 = generator.generate_model_report()
        report2 = generator.generate_model_report()

        # Same keys and structure
        assert report1.keys() == report2.keys()
        assert report1["models"]["gpt-4"].keys() == report2["models"]["gpt-4"].keys()

    async def test_empty_query_field(self, generator: HCSReportGenerator) -> None:
        """Handle records without query field."""
        generator.record("gpt-4", "zero-shot", 8.0, query="")

        readings = generator._load_readings()
        assert readings[0].query == ""

    async def test_long_query_field(self, generator: HCSReportGenerator) -> None:
        """Store long query text."""
        long_query = "a" * 1000
        generator.record("gpt-4", "zero-shot", 8.0, query=long_query)

        readings = generator._load_readings()
        assert len(readings[0].query) == 1000

    async def test_unicode_handling(self, generator: HCSReportGenerator) -> None:
        """Handle unicode in model, strategy, and query fields."""
        generator.record(
            model="gpt-4-مع-عربي",
            strategy="zero-shot-日本語",
            hcs_score=8.0,
            query="What is éléphant in français?",
        )

        readings = generator._load_readings()
        assert "عربي" in readings[0].model
        assert "日本語" in readings[0].strategy
        assert "éléphant" in readings[0].query
