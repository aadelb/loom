"""Analytics & observability over the safety-gradient ladder dataset.

Reads daily JSONL files from the boost_logger dataset directory and aggregates:
- Per-rung statistics (count, success rate, avg HCS, latency)
- Per-flagship lift (baseline vs. ladder delta for each L2 provider)
- Refusal recovery patterns (refused then recovered vs. abandoned)
- Top reframing strategies in winning records
- Winning rung distribution (L0 vs L1 vs L2 final answers)

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.ladder_trace")


def _dataset_dir() -> Path:
    """Resolve the ladder dataset directory (mirrors boost_logger logic)."""
    root = os.environ.get("LOOM_DATASETS_DIR") or os.path.join(
        os.path.expanduser("~"), ".loom", "datasets", "abliterated_boost"
    )
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


@handle_tool_errors("research_ladder_trace")
async def research_ladder_trace(
    days: int = 7,
    provider: str = "",
    min_hcs: float = 0.0,
) -> dict[str, Any]:
    """Aggregate and analyze ladder climb statistics over recent daily files.

    Args:
        days: Number of recent daily files to aggregate (1-90).
        provider: Optional filter to one flagship provider (e.g., "anthropic").
        min_hcs: Optional minimum HCS filter (0.0-10.0).

    Returns:
        Structured dict with per-rung stats, per-flagship lift, refusal recovery,
        top strategies, winning rung distribution, and a summary.
    """
    # Validate inputs
    days = max(1, min(days, 90))
    min_hcs = max(0.0, min(min_hcs, 10.0))

    # Enumerate recent daily files
    dataset_dir = _dataset_dir()
    files = sorted(dataset_dir.glob("*.jsonl"))

    # Filter to last N days by filename (YYYY-MM-DD.jsonl)
    if files:
        try:
            latest_date = datetime.strptime(files[-1].stem, "%Y-%m-%d").date()
            cutoff_date = latest_date - timedelta(days=days - 1)
            files = [
                f for f in files
                if datetime.strptime(f.stem, "%Y-%m-%d").date() >= cutoff_date
            ]
        except ValueError:
            # If filename isn't a date, use the most recent N files
            files = files[-days:]

    if not files:
        return {
            "days": days,
            "provider_filter": provider or None,
            "min_hcs_filter": min_hcs,
            "files_read": 0,
            "total_records": 0,
            "per_rung": {},
            "per_flagship_lift": {},
            "refusal_recovery": {
                "recovered": 0,
                "abandoned": 0,
                "recovery_rate": 0.0,
            },
            "top_strategies": [],
            "winning_rung_distribution": {},
            "summary": "No dataset files found; ladder has not been run yet.",
        }

    # Read and parse records
    records: list[dict[str, Any]] = []
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    records.append(rec)
                except (json.JSONDecodeError, ValueError):
                    logger.debug("skipped malformed line in %s", file_path)
                    continue
        except Exception as e:
            logger.debug("failed to read %s: %s", file_path, e)
            continue

    if not records:
        return {
            "days": days,
            "provider_filter": provider or None,
            "min_hcs_filter": min_hcs,
            "files_read": len(files),
            "total_records": 0,
            "per_rung": {},
            "per_flagship_lift": {},
            "refusal_recovery": {
                "recovered": 0,
                "abandoned": 0,
                "recovery_rate": 0.0,
            },
            "top_strategies": [],
            "winning_rung_distribution": {},
            "summary": f"Read {len(files)} files but found no valid records.",
        }

    # Apply filters
    if provider:
        records = [r for r in records if r.get("provider") == provider]
    if min_hcs > 0:
        records = [r for r in records if (r.get("hcs") or 0.0) >= min_hcs]

    # === Per-rung aggregation ===
    per_rung: dict[str, dict[str, Any]] = {}
    for rec in records:
        rung = rec.get("rung", "unknown")
        hcs = rec.get("hcs") or 0.0
        latency = rec.get("latency_ms") or 0
        refused = rec.get("refused", False)
        verdict = rec.get("verdict", "unknown")

        if rung not in per_rung:
            per_rung[rung] = {
                "count": 0,
                "success": 0,
                "fail": 0,
                "avg_hcs": 0.0,
                "avg_latency_ms": 0.0,
                "hcs_sum": 0.0,
                "latency_sum": 0.0,
            }

        stats = per_rung[rung]
        stats["count"] += 1
        if verdict == "success" and not refused:
            stats["success"] += 1
        else:
            stats["fail"] += 1
        stats["hcs_sum"] += hcs
        stats["latency_sum"] += latency

    # Compute averages
    for rung, stats in per_rung.items():
        count = stats["count"]
        stats["avg_hcs"] = round(stats["hcs_sum"] / count, 3) if count > 0 else 0.0
        stats["avg_latency_ms"] = (
            round(stats["latency_sum"] / count, 1) if count > 0 else 0.0
        )
        stats["success_rate"] = (
            round(stats["success"] / count, 3) if count > 0 else 0.0
        )
        # Clean up temp sums
        del stats["hcs_sum"]
        del stats["latency_sum"]

    # === Per-flagship lift (baseline vs. ladder) ===
    # Baseline records have rung="baseline"; ladder records are L0/L1/L2 attempts.
    baseline_hcs_by_provider: dict[str, list[float]] = {}
    ladder_hcs_by_provider: dict[str, list[float]] = {}

    for rec in records:
        prov = rec.get("provider")
        hcs = rec.get("hcs") or 0.0
        rung = rec.get("rung", "")
        verdict = rec.get("verdict", "unknown")
        refused = rec.get("refused", False)

        if not prov:
            continue

        # Baseline only — cold flagship calls
        if rung == "baseline":
            if prov not in baseline_hcs_by_provider:
                baseline_hcs_by_provider[prov] = []
            baseline_hcs_by_provider[prov].append(hcs)

        # Ladder attempts — successful pushes at L1/L2
        elif rung in ("L1", "L2") and verdict == "success" and not refused and hcs > 0:
            if prov not in ladder_hcs_by_provider:
                ladder_hcs_by_provider[prov] = []
            ladder_hcs_by_provider[prov].append(hcs)

    per_flagship_lift: dict[str, dict[str, float]] = {}
    all_providers = set(baseline_hcs_by_provider.keys()) | set(
        ladder_hcs_by_provider.keys()
    )

    for prov in all_providers:
        baseline_scores = baseline_hcs_by_provider.get(prov, [0.0])
        ladder_scores = ladder_hcs_by_provider.get(prov, [0.0])

        baseline_avg = sum(baseline_scores) / len(baseline_scores) if baseline_scores else 0.0
        ladder_avg = sum(ladder_scores) / len(ladder_scores) if ladder_scores else 0.0
        lift = round(ladder_avg - baseline_avg, 3)

        per_flagship_lift[prov] = {
            "baseline_avg_hcs": round(baseline_avg, 3),
            "ladder_avg_hcs": round(ladder_avg, 3),
            "lift": lift,
            "baseline_attempts": len(baseline_scores),
            "ladder_successful_attempts": len(ladder_scores),
        }

    # === Refusal recovery ===
    # Track queries that had refusals then later succeeded (recovered) vs. permanently refused
    query_refusal_history: dict[str, dict[str, Any]] = {}

    for rec in records:
        query = rec.get("query", "")
        if not query:
            continue

        if query not in query_refusal_history:
            query_refusal_history[query] = {
                "ever_refused": False,
                "ever_succeeded": False,
                "ever_success_after_refusal": False,
                "final_rung": None,
                "final_hcs": 0.0,
            }

        hist = query_refusal_history[query]
        refused = rec.get("refused", False)
        verdict = rec.get("verdict", "unknown")
        hcs = rec.get("hcs") or 0.0
        rung = rec.get("rung", "")

        if refused:
            hist["ever_refused"] = True
        if verdict == "success" and not refused:
            hist["ever_succeeded"] = True
            if hist["ever_refused"]:
                hist["ever_success_after_refusal"] = True
            hist["final_rung"] = rung
            hist["final_hcs"] = hcs

    recovered = sum(1 for h in query_refusal_history.values() if h["ever_success_after_refusal"])
    abandoned = sum(1 for h in query_refusal_history.values() if h["ever_refused"] and not h["ever_succeeded"])
    total_with_refusal = recovered + abandoned

    refusal_recovery = {
        "recovered": recovered,
        "abandoned": abandoned,
        "recovery_rate": round(recovered / total_with_refusal, 3) if total_with_refusal > 0 else 0.0,
    }

    # === Top strategies ===
    # Strategies appear in reframed field or inferred from provider strategy selection
    strategy_wins: dict[str, int] = {}

    for rec in records:
        verdict = rec.get("verdict", "unknown")
        if verdict == "success":
            # Try to extract strategy name from the record
            # The ladder uses reframe_for() which picks a per-provider strategy;
            # we look for a "strategy" or "strategies" field if present
            strat = rec.get("strategy") or rec.get("strategies")
            if isinstance(strat, list):
                for s in strat:
                    strategy_wins[str(s)] = strategy_wins.get(str(s), 0) + 1
            elif strat:
                strategy_wins[str(strat)] = strategy_wins.get(str(strat), 0) + 1

    top_strategies = sorted(
        strategy_wins.items(), key=lambda x: x[1], reverse=True
    )[:10]
    top_strategies = [{"strategy": s, "wins": w} for s, w in top_strategies]

    # === Winning rung distribution ===
    # Which rung/level produced the final best answer across all ladder runs
    winning_rungs: dict[str, int] = {}

    for query, hist in query_refusal_history.items():
        if hist["final_rung"]:
            rung = hist["final_rung"]
            winning_rungs[rung] = winning_rungs.get(rung, 0) + 1

    total_wins = sum(winning_rungs.values())
    winning_rung_distribution = {
        rung: round(count / total_wins, 3) if total_wins > 0 else 0.0
        for rung, count in winning_rungs.items()
    }

    # === Summary ===
    total_queries = len(query_refusal_history)
    avg_hcs_overall = (
        sum(r.get("hcs", 0.0) or 0.0 for r in records) / len(records)
        if records
        else 0.0
    )

    summary = (
        f"Analyzed {len(files)} files, {len(records)} records. "
        f"{total_queries} unique queries, "
        f"avg HCS {round(avg_hcs_overall, 2)}, "
        f"refusal recovery {refusal_recovery['recovery_rate']*100:.0f}%."
    )

    return {
        "days": days,
        "provider_filter": provider or None,
        "min_hcs_filter": min_hcs,
        "files_read": len(files),
        "total_records": len(records),
        "total_queries": total_queries,
        "per_rung": per_rung,
        "per_flagship_lift": per_flagship_lift,
        "refusal_recovery": refusal_recovery,
        "top_strategies": top_strategies,
        "winning_rung_distribution": winning_rung_distribution,
        "summary": summary,
    }
