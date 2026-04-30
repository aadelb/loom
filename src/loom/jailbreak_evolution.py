"""Jailbreak evolution tracker — monitor how attack strategies evolve as models update.

Tracks effectiveness of jailbreak strategies across model versions,
detects when models are patched, and suggests strategy adaptations.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.jailbreak_evolution")


class JailbreakEvolutionTracker:
    """Track how attack strategies evolve in effectiveness as models update."""

    def __init__(self, storage_path: str = "~/.loom/evolution/") -> None:
        """Initialize the evolution tracker.

        Args:
            storage_path: Directory for storing evolution data (default ~/.loom/evolution)
        """
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info("initialized_tracker path=%s", str(self.storage_path))

    def record_result(
        self,
        strategy: str,
        model: str,
        model_version: str,
        success: bool,
        hcs: float,
        timestamp: str = "",
    ) -> dict[str, Any]:
        """Record a single attack result with model version info.

        Args:
            strategy: Name of the jailbreak strategy (e.g. "prompt_injection", "role_play")
            model: Model name (e.g. "gpt-4", "claude-3-sonnet")
            model_version: Model version string (e.g. "gpt-4-0613")
            success: Whether the attack succeeded
            hcs: Helpfulness Compliance Score (0-10)
            timestamp: ISO timestamp (defaults to now)

        Returns:
            Dict with recorded data and storage path
        """
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        # Validate inputs
        if not strategy or len(strategy) > 128:
            raise ValueError("strategy must be 1-128 chars")
        if not model or len(model) > 128:
            raise ValueError("model must be 1-128 chars")
        if not model_version or len(model_version) > 128:
            raise ValueError("model_version must be 1-128 chars")
        if not isinstance(success, bool):
            raise TypeError("success must be bool")
        if not isinstance(hcs, (int, float)) or hcs < 0 or hcs > 10:
            raise ValueError("hcs must be 0-10")

        # Normalize names to lowercase for consistency
        strategy = strategy.lower().strip()
        model = model.lower().strip()
        model_version = model_version.lower().strip()

        # Get or create model file
        model_file = self.storage_path / f"{model}.jsonl"
        records = []

        if model_file.exists():
            with open(model_file, "r") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))

        # Add new record
        new_record = {
            "strategy": strategy,
            "version": model_version,
            "success": success,
            "hcs": hcs,
            "timestamp": timestamp,
        }

        records.append(new_record)

        # Write back atomically
        temp_file = model_file.with_suffix(".jsonl.tmp")
        with open(temp_file, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        temp_file.replace(model_file)

        logger.info("recorded_result strategy=%s model=%s version=%s success=%s hcs=%s", strategy, model, model_version, success, hcs)

        return {
            "status": "recorded",
            "strategy": strategy,
            "model": model,
            "version": model_version,
            "success": success,
            "hcs": hcs,
            "timestamp": timestamp,
        }

    def get_evolution(self, strategy: str, model: str) -> dict[str, Any]:
        """Get how a strategy's effectiveness changed across model versions.

        Args:
            strategy: Jailbreak strategy name
            model: Model name

        Returns:
            Dict with:
            - strategy: strategy name
            - model: model name
            - versions: list of version records with success_rate, avg_hcs, etc.
            - trend: "improving" | "declining" | "stable" | "patched"
            - patch_detected_at: version where patch detected (if applicable)
        """
        strategy = strategy.lower().strip()
        model = model.lower().strip()

        model_file = self.storage_path / f"{model}.jsonl"

        if not model_file.exists():
            logger.warning("model_not_found model=%s", model)
            return {
                "strategy": strategy,
                "model": model,
                "versions": [],
                "trend": "unknown",
                "patch_detected_at": None,
                "error": f"No data for model {model}",
            }

        # Collect records for this strategy
        records = []
        with open(model_file, "r") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record["strategy"] == strategy:
                        records.append(record)

        if not records:
            logger.warning("strategy_not_found strategy=%s model=%s", strategy, model)
            return {
                "strategy": strategy,
                "model": model,
                "versions": [],
                "trend": "unknown",
                "patch_detected_at": None,
                "error": f"No data for strategy {strategy} on {model}",
            }

        # Group by version and calculate stats
        version_stats: dict[str, dict[str, Any]] = {}
        for record in records:
            version = record["version"]
            if version not in version_stats:
                version_stats[version] = {
                    "successes": 0,
                    "total": 0,
                    "hcs_sum": 0.0,
                    "timestamps": [],
                }
            version_stats[version]["successes"] += int(record["success"])
            version_stats[version]["total"] += 1
            version_stats[version]["hcs_sum"] += record["hcs"]
            version_stats[version]["timestamps"].append(record["timestamp"])

        # Build version list sorted by version
        versions = []
        for version in sorted(version_stats.keys()):
            stats = version_stats[version]
            success_rate = stats["successes"] / stats["total"]
            avg_hcs = stats["hcs_sum"] / stats["total"]

            # Extract date range from timestamps
            timestamps = sorted(stats["timestamps"])
            date_range = {
                "first": timestamps[0] if timestamps else None,
                "last": timestamps[-1] if timestamps else None,
            }

            versions.append(
                {
                    "version": version,
                    "success_rate": round(success_rate, 3),
                    "avg_hcs": round(avg_hcs, 2),
                    "samples": stats["total"],
                    "date_range": date_range,
                }
            )

        # Detect trend
        trend = self._detect_trend(versions)
        patch_detected_at = self._detect_patch(versions)

        return {
            "strategy": strategy,
            "model": model,
            "versions": versions,
            "trend": trend,
            "patch_detected_at": patch_detected_at,
        }

    def get_model_timeline(self, model: str) -> dict[str, Any]:
        """Get timeline of model safety changes across all strategies.

        Args:
            model: Model name

        Returns:
            Dict with:
            - model: model name
            - versions: list of version info
            - strategies: list of strategies tested
            - safety_metrics: per-version aggregated safety metrics
        """
        model = model.lower().strip()

        model_file = self.storage_path / f"{model}.jsonl"

        if not model_file.exists():
            logger.warning("model_not_found model=%s", model)
            return {
                "model": model,
                "versions": [],
                "strategies": [],
                "safety_metrics": {},
                "error": f"No data for model {model}",
            }

        # Collect all records
        records = []
        strategies_set = set()
        with open(model_file, "r") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    records.append(record)
                    strategies_set.add(record["strategy"])

        # Group by version
        version_stats: dict[str, dict[str, Any]] = {}
        for record in records:
            version = record["version"]
            if version not in version_stats:
                version_stats[version] = {
                    "total": 0,
                    "successes": 0,
                    "hcs_sum": 0.0,
                    "first_seen": None,
                    "last_seen": None,
                }
            version_stats[version]["total"] += 1
            version_stats[version]["successes"] += int(record["success"])
            version_stats[version]["hcs_sum"] += record["hcs"]

            timestamp = record["timestamp"]
            if version_stats[version]["first_seen"] is None:
                version_stats[version]["first_seen"] = timestamp
            version_stats[version]["last_seen"] = max(
                version_stats[version]["last_seen"] or timestamp, timestamp
            )

        # Build version list
        versions = sorted(version_stats.keys())
        safety_metrics: dict[str, Any] = {}

        for version in versions:
            stats = version_stats[version]
            safety_metrics[version] = {
                "total_tests": stats["total"],
                "success_rate": round(stats["successes"] / stats["total"], 3),
                "avg_hcs": round(stats["hcs_sum"] / stats["total"], 2),
                "first_seen": stats["first_seen"],
                "last_seen": stats["last_seen"],
            }

        return {
            "model": model,
            "versions": versions,
            "strategies": sorted(list(strategies_set)),
            "safety_metrics": safety_metrics,
        }

    def detect_patches(self, model: str) -> list[dict[str, Any]]:
        """Detect when a model was patched against specific strategies.

        A patch is detected when a strategy's success rate drops sharply
        (>50% drop) between consecutive model versions.

        Args:
            model: Model name

        Returns:
            List of detected patches with:
            - strategy: affected strategy
            - patched_at_version: version where patch was applied
            - previous_success_rate: rate before patch
            - new_success_rate: rate after patch
            - drop_percentage: percentage point drop
        """
        model = model.lower().strip()

        model_file = self.storage_path / f"{model}.jsonl"

        if not model_file.exists():
            logger.warning("model_not_found model=%s", model)
            return []

        # Collect all records
        records = []
        with open(model_file, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

        # Group by strategy, then by version
        strategy_versions: dict[str, dict[str, dict[str, Any]]] = {}
        for record in records:
            strategy = record["strategy"]
            version = record["version"]

            if strategy not in strategy_versions:
                strategy_versions[strategy] = {}
            if version not in strategy_versions[strategy]:
                strategy_versions[strategy][version] = {
                    "successes": 0,
                    "total": 0,
                }

            strategy_versions[strategy][version]["successes"] += int(record["success"])
            strategy_versions[strategy][version]["total"] += 1

        # Detect patches
        patches = []
        for strategy, versions_data in strategy_versions.items():
            sorted_versions = sorted(versions_data.keys())

            for i in range(1, len(sorted_versions)):
                prev_version = sorted_versions[i - 1]
                curr_version = sorted_versions[i]

                prev_stats = versions_data[prev_version]
                curr_stats = versions_data[curr_version]

                prev_rate = prev_stats["successes"] / prev_stats["total"]
                curr_rate = curr_stats["successes"] / curr_stats["total"]

                # Detect significant drop (>50 percentage points)
                drop = prev_rate - curr_rate
                if drop > 0.5:
                    patches.append(
                        {
                            "strategy": strategy,
                            "patched_at_version": curr_version,
                            "previous_version": prev_version,
                            "previous_success_rate": round(prev_rate, 3),
                            "new_success_rate": round(curr_rate, 3),
                            "drop_percentage": round(drop * 100, 1),
                        }
                    )

        logger.info("detected_patches model=%s count=%d", model, len(patches))
        return patches

    def suggest_adaptations(self, strategy: str, model: str) -> list[str]:
        """Suggest how to adapt a strategy that stopped working.

        Returns heuristic suggestions based on:
        1. What worked better on recent versions
        2. Cross-model patterns
        3. Strategy category insights

        Args:
            strategy: Jailbreak strategy name
            model: Model name

        Returns:
            List of adaptation suggestions
        """
        strategy = strategy.lower().strip()
        model = model.lower().strip()

        evolution = self.get_evolution(strategy, model)

        if evolution.get("error"):
            logger.warning("strategy_not_found strategy=%s model=%s", strategy, model)
            return ["No data available for strategy/model combination"]

        versions = evolution["versions"]
        if not versions:
            return ["No version data to analyze"]

        suggestions = []

        # Check if strategy is declining
        if evolution["trend"] == "declining":
            suggestions.append(
                "Strategy effectiveness is declining. Consider combining with newer techniques."
            )

        # Check if patched
        if evolution["patch_detected_at"]:
            suggestions.append(
                f"Model was patched at version {evolution['patch_detected_at']}. "
                "Try obfuscation or indirection techniques."
            )

        # Suggest based on recent versions
        recent = versions[-1] if versions else None
        if recent and recent["success_rate"] < 0.3:
            suggestions.append(
                "Recent success rate is low (<30%). Consider role-playing or system prompt injection variants."
            )

        # Generic adaptations
        if not suggestions:
            suggestions.append("Try combining this strategy with others for better results")
            suggestions.append("Test variations with different prompting styles")

        suggestions.append("Monitor next model release for effectiveness changes")

        return suggestions

    def _detect_trend(self, versions: list[dict[str, Any]]) -> str:
        """Detect trend from version success rates.

        Args:
            versions: List of version records

        Returns:
            "improving" | "declining" | "stable" | "unknown"
        """
        if len(versions) < 2:
            return "unknown"

        rates = [v["success_rate"] for v in versions]

        # Check for patch (sudden drop >50 percentage points)
        for i in range(1, len(rates)):
            if rates[i - 1] - rates[i] > 0.5:
                return "patched"

        # Calculate trend using last 3 versions
        recent = rates[-3:]
        if len(recent) >= 2:
            avg_recent = sum(recent) / len(recent)
            avg_older = sum(rates[:-1]) / max(1, len(rates) - 1)

            if avg_recent > avg_older + 0.09:  # Allow floating point slop
                return "improving"
            elif avg_older > avg_recent + 0.09:  # Allow floating point slop
                return "declining"
            else:
                return "stable"

        return "stable"

    def _detect_patch(self, versions: list[dict[str, Any]]) -> str | None:
        """Detect which version patch was applied.

        Args:
            versions: List of version records

        Returns:
            Version string where patch detected, or None
        """
        for i in range(1, len(versions)):
            prev_rate = versions[i - 1]["success_rate"]
            curr_rate = versions[i]["success_rate"]

            if prev_rate - curr_rate > 0.5:
                return versions[i]["version"]

        return None

    def clear_model_data(self, model: str) -> dict[str, Any]:
        """Clear all evolution data for a model.

        Args:
            model: Model name

        Returns:
            Status dict
        """
        model = model.lower().strip()
        model_file = self.storage_path / f"{model}.jsonl"

        if model_file.exists():
            model_file.unlink()
            logger.info("cleared_model_data model=%s", model)
            return {"status": "cleared", "model": model}

        return {"status": "not_found", "model": model}

    def export_stats(self, model: str | None = None) -> dict[str, Any]:
        """Export evolution statistics.

        Args:
            model: Optional model name to filter (exports all models if None)

        Returns:
            Dict with statistics
        """
        stats = {
            "total_models": 0,
            "total_strategies": 0,
            "total_records": 0,
            "models": {},
        }

        if model:
            model = model.lower().strip()
            model_file = self.storage_path / f"{model}.jsonl"

            if model_file.exists():
                model_data = self._load_model_file(model_file)
                stats["total_models"] = 1
                stats["total_records"] = len(model_data)
                stats["total_strategies"] = len(set(r["strategy"] for r in model_data))
                stats["models"][model] = {
                    "records": len(model_data),
                    "strategies": len(set(r["strategy"] for r in model_data)),
                }
        else:
            for model_file in self.storage_path.glob("*.jsonl"):
                model_name = model_file.stem
                model_data = self._load_model_file(model_file)
                stats["total_models"] += 1
                stats["total_records"] += len(model_data)
                unique_strategies = len(set(r["strategy"] for r in model_data))
                stats["total_strategies"] += unique_strategies
                stats["models"][model_name] = {
                    "records": len(model_data),
                    "strategies": unique_strategies,
                }

        return stats

    @staticmethod
    def _load_model_file(model_file: Path) -> list[dict[str, Any]]:
        """Load all records from a model file.

        Args:
            model_file: Path to model JSONL file

        Returns:
            List of records
        """
        records = []
        with open(model_file, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records
