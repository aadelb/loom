"""HCS distribution report generator (REQ-030, REQ-524).

Generates per-model and per-strategy HCS distribution reports from recorded scores.
Supports regression detection, statistical analysis, and markdown export.

REQ-030: Per-model HCS distribution reports with mean, median, stdev, histogram
REQ-524: Per-strategy HCS distribution + regression detection
"""

from __future__ import annotations

import json
import logging
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.hcs_report")

# Constraints
MIN_HCS_SCORE = 0
MAX_HCS_SCORE = 10
MIN_SAMPLES_FOR_STATS = 2
HISTOGRAM_BINS = 11  # 0-1, 1-2, ..., 9-10


@dataclass(frozen=True)
class HCSReading:
    """Immutable HCS measurement record."""

    model: str
    strategy: str
    hcs_score: float
    query: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "strategy": self.strategy,
            "hcs_score": self.hcs_score,
            "query": self.query,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> HCSReading:
        """Create from dictionary."""
        return HCSReading(
            model=data["model"],
            strategy=data["strategy"],
            hcs_score=data["hcs_score"],
            query=data.get("query", ""),
            timestamp=data.get("timestamp", ""),
        )


@dataclass(frozen=True)
class DistributionStats:
    """Immutable distribution statistics."""

    count: int
    mean: float
    median: float
    stdev: float
    min: float
    max: float
    histogram: list[int]  # 11 bins: 0-1, 1-2, ..., 9-10
    percentile_25: float
    percentile_75: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "count": self.count,
            "mean": self.mean,
            "median": self.median,
            "stdev": self.stdev,
            "min": self.min,
            "max": self.max,
            "histogram": self.histogram,
            "percentile_25": self.percentile_25,
            "percentile_75": self.percentile_75,
        }


class HCSReportGenerator:
    """Generate HCS distribution reports per model and strategy."""

    def __init__(self, data_path: str = "~/.loom/hcs_data.jsonl") -> None:
        """Initialize report generator.

        Args:
            data_path: Path to JSONL file storing HCS measurements
        """
        self.data_path = Path(data_path).expanduser()
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        model: str,
        strategy: str,
        hcs_score: float,
        query: str = "",
        timestamp: str = "",
    ) -> None:
        """Record an HCS measurement.

        Args:
            model: Model name (e.g., "gpt-4", "claude-opus")
            strategy: Strategy name (e.g., "zero-shot", "chain-of-thought")
            hcs_score: HCS score 0-10
            query: Optional query that produced the score
            timestamp: Optional ISO timestamp (uses current if empty)

        Raises:
            ValueError: If score out of range or required fields empty
        """
        if not model or not isinstance(model, str):
            raise ValueError("model must be non-empty string")
        if not strategy or not isinstance(strategy, str):
            raise ValueError("strategy must be non-empty string")
        if not isinstance(hcs_score, (int, float)):
            raise ValueError("hcs_score must be numeric")
        if not (MIN_HCS_SCORE <= hcs_score <= MAX_HCS_SCORE):
            raise ValueError(f"hcs_score must be {MIN_HCS_SCORE}-{MAX_HCS_SCORE}")

        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        reading = HCSReading(
            model=model.strip(),
            strategy=strategy.strip(),
            hcs_score=float(hcs_score),
            query=query.strip() if query else "",
            timestamp=timestamp,
        )

        # Append to JSONL file (atomic write per line)
        with open(self.data_path, "a") as f:
            f.write(json.dumps(reading.to_dict()) + "\n")

        logger.info(
            "hcs_recorded model=%s strategy=%s score=%.1f",
            reading.model,
            reading.strategy,
            reading.hcs_score,
        )

    def _load_readings(self) -> list[HCSReading]:
        """Load all HCS readings from file."""
        if not self.data_path.exists():
            return []

        readings = []
        try:
            with open(self.data_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        readings.append(HCSReading.from_dict(data))
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(
                            "hcs_load_error line=%d error=%s", line_num, str(e)
                        )
                        continue
        except IOError as e:
            logger.error("hcs_file_read_error path=%s error=%s", self.data_path, str(e))
            return []

        logger.info("hcs_loaded total=%d", len(readings))
        return readings

    def _compute_stats(self, scores: list[float]) -> DistributionStats:
        """Compute distribution statistics from scores.

        Args:
            scores: List of HCS scores

        Returns:
            DistributionStats with all metrics
        """
        if not scores:
            return DistributionStats(
                count=0,
                mean=0.0,
                median=0.0,
                stdev=0.0,
                min=0.0,
                max=0.0,
                histogram=[0] * HISTOGRAM_BINS,
                percentile_25=0.0,
                percentile_75=0.0,
            )

        sorted_scores = sorted(scores)
        count = len(sorted_scores)

        # Mean
        mean = statistics.mean(sorted_scores)

        # Median
        median = statistics.median(sorted_scores)

        # Stdev (only if 2+ samples)
        stdev = (
            statistics.stdev(sorted_scores) if count >= MIN_SAMPLES_FOR_STATS else 0.0
        )

        # Min/Max
        min_val = sorted_scores[0]
        max_val = sorted_scores[-1]

        # Percentiles
        if count >= 2:
            p25_idx = max(0, int(count * 0.25) - 1)
            p75_idx = min(count - 1, int(count * 0.75))
            percentile_25 = sorted_scores[p25_idx]
            percentile_75 = sorted_scores[p75_idx]
        else:
            percentile_25 = min_val
            percentile_75 = max_val

        # Histogram (11 bins: 0-1, 1-2, ..., 9-10)
        histogram = [0] * HISTOGRAM_BINS
        for score in sorted_scores:
            # Map score to bin (0-10 range)
            bin_idx = min(int(score), HISTOGRAM_BINS - 1)
            histogram[bin_idx] += 1

        return DistributionStats(
            count=count,
            mean=mean,
            median=median,
            stdev=stdev,
            min=min_val,
            max=max_val,
            histogram=histogram,
            percentile_25=percentile_25,
            percentile_75=percentile_75,
        )

    def generate_model_report(self) -> dict[str, Any]:
        """Per-model HCS distribution: mean, median, stdev, min, max, histogram.

        Returns:
            Dict with per-model statistics keyed by model name
        """
        readings = self._load_readings()

        if not readings:
            logger.warning("hcs_model_report_empty no readings available")
            return {"models": {}, "total_readings": 0}

        # Group by model
        model_scores: dict[str, list[float]] = {}
        for reading in readings:
            if reading.model not in model_scores:
                model_scores[reading.model] = []
            model_scores[reading.model].append(reading.hcs_score)

        # Compute stats per model
        models_data = {}
        for model, scores in sorted(model_scores.items()):
            stats = self._compute_stats(scores)
            models_data[model] = stats.to_dict()

        result = {"models": models_data, "total_readings": len(readings)}

        logger.info("hcs_model_report models=%d total=%d", len(models_data), len(readings))

        return result

    def generate_strategy_report(self) -> dict[str, Any]:
        """Per-strategy HCS distribution.

        Returns:
            Dict with per-strategy statistics keyed by strategy name
        """
        readings = self._load_readings()

        if not readings:
            logger.warning("hcs_strategy_report_empty no readings available")
            return {"strategies": {}, "total_readings": 0}

        # Group by strategy
        strategy_scores: dict[str, list[float]] = {}
        for reading in readings:
            if reading.strategy not in strategy_scores:
                strategy_scores[reading.strategy] = []
            strategy_scores[reading.strategy].append(reading.hcs_score)

        # Compute stats per strategy
        strategies_data = {}
        for strategy, scores in sorted(strategy_scores.items()):
            stats = self._compute_stats(scores)
            strategies_data[strategy] = stats.to_dict()

        result = {"strategies": strategies_data, "total_readings": len(readings)}

        logger.info(
            "hcs_strategy_report strategies=%d total=%d",
            len(strategies_data),
            len(readings),
        )

        return result

    def generate_combined_report(self) -> str:
        """Full markdown report with tables and distributions.

        Returns:
            Markdown-formatted report string
        """
        readings = self._load_readings()

        if not readings:
            return "# HCS Distribution Report\n\nNo data available.\n"

        # Generate model and strategy reports
        model_report = self.generate_model_report()
        strategy_report = self.generate_strategy_report()

        # Build markdown
        lines = [
            "# HCS Distribution Report",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Total readings: {len(readings)}",
            "",
        ]

        # Model section
        lines.extend(["## Per-Model Distribution", ""])

        models_data = model_report.get("models", {})
        if models_data:
            lines.append("| Model | Count | Mean | Median | StDev | Min | Max |")
            lines.append("|-------|-------|------|--------|-------|-----|-----|")

            for model, stats in sorted(models_data.items()):
                lines.append(
                    f"| {model} | {stats['count']} | "
                    f"{stats['mean']:.2f} | {stats['median']:.2f} | "
                    f"{stats['stdev']:.2f} | {stats['min']:.1f} | {stats['max']:.1f} |"
                )

            lines.append("")
        else:
            lines.append("No model data.\n")

        # Strategy section
        lines.extend(["## Per-Strategy Distribution", ""])

        strategies_data = strategy_report.get("strategies", {})
        if strategies_data:
            lines.append("| Strategy | Count | Mean | Median | StDev | Min | Max |")
            lines.append("|----------|-------|------|--------|-------|-----|-----|")

            for strategy, stats in sorted(strategies_data.items()):
                lines.append(
                    f"| {strategy} | {stats['count']} | "
                    f"{stats['mean']:.2f} | {stats['median']:.2f} | "
                    f"{stats['stdev']:.2f} | {stats['min']:.1f} | {stats['max']:.1f} |"
                )

            lines.append("")
        else:
            lines.append("No strategy data.\n")

        # Histogram section
        lines.extend(["## Score Distribution Histogram", ""])
        all_scores = [r.hcs_score for r in readings]
        all_stats = self._compute_stats(all_scores)

        lines.append("```")
        lines.append(self._render_histogram(all_stats.histogram))
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def _render_histogram(self, histogram: list[int]) -> str:
        """Render histogram as ASCII art.

        Args:
            histogram: List of bin counts

        Returns:
            ASCII histogram string
        """
        if not histogram or max(histogram) == 0:
            return "No data"

        max_height = max(histogram) if histogram else 1
        lines = []

        for i in range(HISTOGRAM_BINS):
            bin_start = i
            bin_end = i + 1
            count = histogram[i]
            bar_width = int((count / max_height) * 40) if max_height > 0 else 0

            lines.append(
                f"{bin_start}-{bin_end}: {count:4d} {'█' * bar_width}"
            )

        return "\n".join(lines)

    def detect_regressions(self, threshold: float = 1.0) -> list[dict[str, Any]]:
        """Detect models/strategies where HCS dropped significantly.

        Compares recent scores vs. historical baseline.

        Args:
            threshold: Minimum mean score drop to flag as regression (default 1.0)

        Returns:
            List of regression findings, each with model/strategy, old_mean, new_mean, drop
        """
        readings = self._load_readings()

        if not readings or len(readings) < 10:
            logger.warning("hcs_regression_check insufficient_data count=%d", len(readings))
            return []

        # Split into older half (baseline) and recent half (current)
        midpoint = len(readings) // 2
        baseline_readings = readings[:midpoint]
        recent_readings = readings[midpoint:]

        regressions = []

        # Check per-model regressions
        baseline_model_scores: dict[str, list[float]] = {}
        recent_model_scores: dict[str, list[float]] = {}

        for reading in baseline_readings:
            if reading.model not in baseline_model_scores:
                baseline_model_scores[reading.model] = []
            baseline_model_scores[reading.model].append(reading.hcs_score)

        for reading in recent_readings:
            if reading.model not in recent_model_scores:
                recent_model_scores[reading.model] = []
            recent_model_scores[reading.model].append(reading.hcs_score)

        for model in set(baseline_model_scores.keys()) & set(recent_model_scores.keys()):
            baseline_mean = statistics.mean(baseline_model_scores[model])
            recent_mean = statistics.mean(recent_model_scores[model])
            drop = baseline_mean - recent_mean

            if drop >= threshold:
                regressions.append(
                    {
                        "type": "model",
                        "name": model,
                        "old_mean": baseline_mean,
                        "new_mean": recent_mean,
                        "drop": drop,
                    }
                )
                logger.warning(
                    "hcs_regression_detected type=model name=%s drop=%.2f",
                    model,
                    drop,
                )

        # Check per-strategy regressions
        baseline_strategy_scores: dict[str, list[float]] = {}
        recent_strategy_scores: dict[str, list[float]] = {}

        for reading in baseline_readings:
            if reading.strategy not in baseline_strategy_scores:
                baseline_strategy_scores[reading.strategy] = []
            baseline_strategy_scores[reading.strategy].append(reading.hcs_score)

        for reading in recent_readings:
            if reading.strategy not in recent_strategy_scores:
                recent_strategy_scores[reading.strategy] = []
            recent_strategy_scores[reading.strategy].append(reading.hcs_score)

        for strategy in set(baseline_strategy_scores.keys()) & set(
            recent_strategy_scores.keys()
        ):
            baseline_mean = statistics.mean(baseline_strategy_scores[strategy])
            recent_mean = statistics.mean(recent_strategy_scores[strategy])
            drop = baseline_mean - recent_mean

            if drop >= threshold:
                regressions.append(
                    {
                        "type": "strategy",
                        "name": strategy,
                        "old_mean": baseline_mean,
                        "new_mean": recent_mean,
                        "drop": drop,
                    }
                )
                logger.warning(
                    "hcs_regression_detected type=strategy name=%s drop=%.2f",
                    strategy,
                    drop,
                )

        logger.info("hcs_regression_check total=%d", len(regressions))

        return sorted(regressions, key=lambda x: x["drop"], reverse=True)
