"""Attack effectiveness tracker — records every reframing attempt.

Replaces static multiplier claims with REAL measured data.
Tracks: which strategy, which model, success/fail, HCS score, timestamp.
Builds historical database for auto-selecting best strategies.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _get_tracker_dir() -> Path:
    """Get or create tracker directory."""
    tracker_dir = Path.home() / ".loom" / "attack_tracker"
    tracker_dir.mkdir(parents=True, exist_ok=True)
    return tracker_dir


def record_attempt(
    strategy: str,
    model: str,
    prompt_hash: str,
    success: bool,
    hcs_score: int = 0,
    response_length: int = 0,
    duration_ms: float = 0,
) -> dict[str, Any]:
    """Record a single reframing attempt.

    Args:
        strategy: Name of the reframing strategy used
        model: Target model identifier
        prompt_hash: SHA-256 hash of the original prompt
        success: Whether the attempt succeeded (model complied)
        hcs_score: HCS score assigned to response (0-100)
        response_length: Length of model response in characters
        duration_ms: Elapsed time for the attempt in milliseconds

    Returns:
        Dictionary containing the recorded entry
    """
    tracker_dir = _get_tracker_dir()
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "strategy": strategy,
        "model": model,
        "prompt_hash": prompt_hash,
        "success": success,
        "hcs_score": hcs_score,
        "response_length": response_length,
        "duration_ms": round(duration_ms, 1),
    }

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    tracker_file = tracker_dir / f"{today}.jsonl"

    with open(tracker_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def get_strategy_stats(
    strategy: str | None = None, model: str | None = None
) -> dict[str, Any]:
    """Get empirical success rate for a strategy/model combo.

    Args:
        strategy: Optional filter by strategy name
        model: Optional filter by model identifier

    Returns:
        Dictionary with total_attempts, successes, ASR (Attack Success Rate),
        and average HCS score
    """
    tracker_dir = _get_tracker_dir()
    total = 0
    successes = 0
    hcs_scores: list[int] = []

    for tracker_file in tracker_dir.glob("*.jsonl"):
        with open(tracker_file) as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if strategy and entry["strategy"] != strategy:
                    continue
                if model and entry["model"] != model:
                    continue
                total += 1
                if entry["success"]:
                    successes += 1
                    hcs_scores.append(entry.get("hcs_score", 0))

    asr = successes / max(total, 1)
    avg_hcs = sum(hcs_scores) / max(len(hcs_scores), 1)

    return {
        "strategy": strategy,
        "model": model,
        "total_attempts": total,
        "successes": successes,
        "asr": round(asr, 3),
        "avg_hcs": round(avg_hcs, 1),
    }


def get_best_strategy(model: str) -> dict[str, Any]:
    """Get the empirically best strategy for a specific model.

    Ranks strategies by ASR first, then by average HCS score for successful
    attempts on that model.

    Args:
        model: Target model identifier

    Returns:
        Dictionary with best_strategy name, its ASR, avg HCS, total attempts,
        and list of alternative strategies
    """
    tracker_dir = _get_tracker_dir()
    strategy_data: dict[str, dict[str, int | float]] = {}

    for tracker_file in tracker_dir.glob("*.jsonl"):
        with open(tracker_file) as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry["model"] != model:
                    continue
                s = entry["strategy"]
                if s not in strategy_data:
                    strategy_data[s] = {"total": 0, "success": 0, "hcs_sum": 0}
                strategy_data[s]["total"] = int(strategy_data[s]["total"]) + 1
                if entry["success"]:
                    strategy_data[s]["success"] = int(strategy_data[s]["success"]) + 1
                    strategy_data[s]["hcs_sum"] = (
                        int(strategy_data[s]["hcs_sum"])
                        + entry.get("hcs_score", 0)
                    )

    if not strategy_data:
        return {
            "model": model,
            "best_strategy": None,
            "asr": 0,
            "message": "No data yet",
        }

    # Rank by ASR then by average HCS
    ranked = sorted(
        strategy_data.items(),
        key=lambda x: (
            int(x[1]["success"]) / max(int(x[1]["total"]), 1),
            int(x[1]["hcs_sum"]) / max(int(x[1]["success"]), 1),
        ),
        reverse=True,
    )

    best_name, best_data = ranked[0]
    return {
        "model": model,
        "best_strategy": best_name,
        "asr": round(
            int(best_data["success"]) / max(int(best_data["total"]), 1), 3
        ),
        "avg_hcs": round(
            int(best_data["hcs_sum"]) / max(int(best_data["success"]), 1), 1
        ),
        "total_attempts": int(best_data["total"]),
        "alternatives": [
            {
                "strategy": n,
                "asr": round(int(d["success"]) / max(int(d["total"]), 1), 3),
            }
            for n, d in ranked[1:4]
        ],
    }


def get_leaderboard(top_n: int = 20) -> list[dict[str, Any]]:
    """Get top strategies by ASR across all models.

    Args:
        top_n: Number of top strategies to return

    Returns:
        List of dicts with rank, strategy name, ASR, and attempt count
    """
    tracker_dir = _get_tracker_dir()
    all_data: dict[str, dict[str, int]] = {}

    for tracker_file in tracker_dir.glob("*.jsonl"):
        with open(tracker_file) as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                s = entry["strategy"]
                if s not in all_data:
                    all_data[s] = {"total": 0, "success": 0}
                all_data[s]["total"] += 1
                if entry["success"]:
                    all_data[s]["success"] += 1

    ranked = sorted(
        all_data.items(),
        key=lambda x: x[1]["success"] / max(x[1]["total"], 1),
        reverse=True,
    )

    return [
        {
            "rank": i + 1,
            "strategy": n,
            "asr": round(d["success"] / max(d["total"], 1), 3),
            "attempts": d["total"],
        }
        for i, (n, d) in enumerate(ranked[:top_n])
    ]
