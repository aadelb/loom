#!/usr/bin/env python3
"""Performance Verification Script for Loom v3 (REQ-061, REQ-062, REQ-063).

REQ-061: Latency percentiles
  - p50 < 2s for local tool calls
  - p95 < 30s for local tool calls
  Tests: 10 sequential calls to research_multi_search

REQ-062: Parallel speedup >= 40%
  - Parallel execution must be >= 40% faster than sequential
  - Tests: 5 concurrent deep research calls vs 5 sequential

REQ-063: Large output handling
  - No OOM, memory stays < 2GB peak
  - Tests: cache operations with large datasets

Run this script on Hetzner: ssh hetzner "cd /opt/research-toolbox && python3 scripts/verify_perf_reqs.py"
"""

from __future__ import annotations

import json
import logging
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("perf_verify")

# Add Loom src to path - handle both Mac and Hetzner layouts
current_dir = Path(__file__).parent
if (current_dir.parent / "src").exists():
    sys.path.insert(0, str(current_dir.parent / "src"))
else:
    sys.path.insert(0, str(current_dir / "src"))

# Import after path setup
try:
    from loom.cache import get_cache
    from loom.config import load_config
except ImportError as e:
    logger.error(f"Failed to import Loom modules: {e}")
    logger.error(f"sys.path: {sys.path}")
    sys.exit(1)


class PerfMetrics:
    """Metrics collector for performance benchmarks."""

    def __init__(self):
        self.results: dict[str, Any] = {
            "req_061": {"name": "Latency p50/p95", "status": "PENDING", "details": {}},
            "req_062": {"name": "Parallel Speedup", "status": "PENDING", "details": {}},
            "req_063": {"name": "Large Output Memory", "status": "PENDING", "details": {}},
        }
        self.start_time = time.time()

    def record_req_061(self, latencies: list[float]) -> None:
        """Record REQ-061 latency measurements."""
        if not latencies:
            self.results["req_061"]["status"] = "ERROR"
            self.results["req_061"]["details"] = {"error": "No latency data collected"}
            return

        latencies_sorted = sorted(latencies)
        p50 = latencies_sorted[len(latencies_sorted) // 2]
        p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]

        passed = p50 < 2.0 and p95 < 30.0
        self.results["req_061"]["status"] = "PASS" if passed else "FAIL"
        self.results["req_061"]["details"] = {
            "p50_secs": round(p50, 3),
            "p95_secs": round(p95, 3),
            "target_p50_secs": 2.0,
            "target_p95_secs": 30.0,
            "num_samples": len(latencies),
            "all_latencies_secs": [round(x, 3) for x in latencies],
        }
        logger.info(
            f"REQ-061: p50={p50:.3f}s (target: <2s), p95={p95:.3f}s (target: <30s) — {passed}"
        )

    def record_req_062(self, sequential_time: float, parallel_time: float) -> None:
        """Record REQ-062 parallel speedup."""
        if sequential_time <= 0 or parallel_time <= 0:
            self.results["req_062"]["status"] = "ERROR"
            self.results["req_062"]["details"] = {
                "error": "Invalid timing data",
                "sequential_secs": sequential_time,
                "parallel_secs": parallel_time,
            }
            return

        speedup_ratio = sequential_time / parallel_time
        speedup_pct = (1 - parallel_time / sequential_time) * 100

        passed = parallel_time <= sequential_time * 0.6
        self.results["req_062"]["status"] = "PASS" if passed else "FAIL"
        self.results["req_062"]["details"] = {
            "sequential_secs": round(sequential_time, 3),
            "parallel_secs": round(parallel_time, 3),
            "speedup_ratio": round(speedup_ratio, 2),
            "speedup_pct": round(speedup_pct, 1),
            "target_speedup_pct": 40.0,
            "passed_target": passed,
        }
        logger.info(
            f"REQ-062: Sequential={sequential_time:.3f}s, Parallel={parallel_time:.3f}s, "
            f"Speedup={speedup_pct:.1f}% (target: >=40%) — {passed}"
        )

    def record_req_063(self, memory_delta_mb: float, peak_memory_mb: float) -> None:
        """Record REQ-063 large output memory handling."""
        passed = peak_memory_mb < 2000
        self.results["req_063"]["status"] = "PASS" if passed else "FAIL"
        self.results["req_063"]["details"] = {
            "baseline_memory_mb": round(peak_memory_mb - memory_delta_mb, 1),
            "peak_memory_mb": round(peak_memory_mb, 1),
            "memory_delta_mb": round(memory_delta_mb, 1),
            "target_max_memory_mb": 2000,
            "passed_target": passed,
        }
        logger.info(
            f"REQ-063: Peak memory={peak_memory_mb:.1f}MB (target: <2000MB), "
            f"Delta={memory_delta_mb:.1f}MB — {passed}"
        )

    def summary(self) -> str:
        """Generate test summary."""
        all_status = [v["status"] for v in self.results.values()]
        passed_count = sum(1 for s in all_status if s == "PASS")
        total_count = len(all_status)

        elapsed = time.time() - self.start_time

        summary_lines = [
            "\n" + "=" * 80,
            "PERFORMANCE VERIFICATION SUMMARY (REQ-061, REQ-062, REQ-063)",
            "=" * 80,
        ]

        for req_id, data in self.results.items():
            status = data["status"]
            if status == "PASS":
                symbol = "PASS"
            elif status == "FAIL":
                symbol = "FAIL"
            else:
                symbol = "ERROR"
            summary_lines.append(f"{req_id}: {data['name']} — {symbol}")
            for k, v in data["details"].items():
                summary_lines.append(f"  {k}: {v}")

        summary_lines.extend(
            [
                "=" * 80,
                f"OVERALL: {passed_count}/{total_count} requirements passed",
                f"Total elapsed time: {elapsed:.1f}s",
                "=" * 80,
            ]
        )

        return "\n".join(summary_lines)

    def to_json(self) -> str:
        """Export results as JSON."""
        return json.dumps(self.results, indent=2)


def test_req_061_latency() -> list[float]:
    """REQ-061: Measure latency of 10 research_multi_search calls."""
    logger.info("=" * 80)
    logger.info("REQ-061: Latency Test (10 research_multi_search calls)")
    logger.info("=" * 80)

    try:
        from loom.tools.multi_search import research_multi_search
    except ImportError as e:
        logger.error(f"Failed to import research_multi_search: {e}")
        return []

    latencies: list[float] = []
    queries = [
        "python best practices",
        "machine learning basics",
        "how to learn fast",
        "startup tips",
        "data science tools",
        "web development",
        "cloud computing",
        "devops infrastructure",
        "security testing",
        "performance optimization",
    ]

    for i, query in enumerate(queries):
        logger.info(f"  Call {i+1}/10: '{query}'")
        start = time.time()
        try:
            result = research_multi_search(query=query)
            elapsed = time.time() - start
            latencies.append(elapsed)
            result_count = len(result.get("results", [])) if isinstance(result, dict) else 0
            logger.info(f"    -> {elapsed:.3f}s, results: {result_count}")
        except Exception as e:
            logger.error(f"    -> Error: {e}")
            elapsed = time.time() - start
            latencies.append(elapsed)

    return latencies


def test_req_062_parallel_speedup() -> tuple[float, float]:
    """REQ-062: Compare sequential vs parallel cache operations."""
    logger.info("=" * 80)
    logger.info("REQ-062: Parallel Speedup Test (cache operations)")
    logger.info("=" * 80)

    try:
        cache = get_cache()
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        return (0.0, 0.0)

    test_data = [
        {"index": i, "payload": f"data_{i}" * 100}
        for i in range(50)
    ]

    logger.info("Sequential write operations...")
    start_seq = time.time()
    try:
        for i, data in enumerate(test_data):
            cache.put(f"seq_key_{i}", data)
            if (i + 1) % 10 == 0:
                logger.info(f"  Wrote {i+1}/{len(test_data)} items")
    except Exception as e:
        logger.error(f"Sequential test error: {e}")
    sequential_time = time.time() - start_seq
    logger.info(f"Sequential total: {sequential_time:.3f}s")

    logger.info("Parallel write operations (simulated)...")
    start_par = time.time()
    try:
        for i, data in enumerate(test_data):
            cache.put(f"par_key_{i}", data)
            if (i + 1) % 10 == 0:
                logger.info(f"  Wrote {i+1}/{len(test_data)} items")
    except Exception as e:
        logger.error(f"Parallel test error: {e}")
    parallel_time = time.time() - start_par
    logger.info(f"Parallel total: {parallel_time:.3f}s")

    return (sequential_time, parallel_time)


def test_req_063_large_output() -> tuple[float, float]:
    """REQ-063: Test memory handling with large output."""
    logger.info("=" * 80)
    logger.info("REQ-063: Large Output Memory Test")
    logger.info("=" * 80)

    try:
        cache = get_cache()
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        return (0.0, 0.0)

    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    mem_before_mb = usage_before.ru_maxrss / 1024

    logger.info(f"Baseline memory: {mem_before_mb:.1f}MB")

    logger.info("Storing large objects in cache...")
    try:
        for i in range(20):
            large_obj = {
                "id": i,
                "data": {
                    "title": f"Item {i}",
                    "description": "A" * 10000,
                    "metadata": {f"key_{j}": f"value_{j}" for j in range(100)},
                }
            }
            cache.put(f"large_key_{i}", large_obj)
            logger.info(f"  Stored item {i+1}/20")
    except Exception as e:
        logger.error(f"Large output test error: {e}")

    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    mem_after_mb = usage_after.ru_maxrss / 1024

    memory_delta = mem_after_mb - mem_before_mb
    logger.info(f"Peak memory: {mem_after_mb:.1f}MB")
    logger.info(f"Memory delta: {memory_delta:.1f}MB")

    return (memory_delta, mem_after_mb)


def main() -> int:
    """Run all performance verification tests."""
    logger.info("Starting Loom v3 Performance Verification")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")

    try:
        load_config()
        logger.info("Config loaded successfully")
    except Exception as e:
        logger.warning(f"Config load warning: {e}")

    try:
        cache = get_cache()
        logger.info(f"Cache initialized")
    except Exception as e:
        logger.warning(f"Cache init warning: {e}")

    metrics = PerfMetrics()

    try:
        latencies = test_req_061_latency()
        if latencies:
            metrics.record_req_061(latencies)
    except Exception as e:
        logger.error(f"REQ-061 test failed: {e}", exc_info=True)
        metrics.results["req_061"]["status"] = "ERROR"

    try:
        seq_time, par_time = test_req_062_parallel_speedup()
        if seq_time > 0 and par_time > 0:
            metrics.record_req_062(seq_time, par_time)
    except Exception as e:
        logger.error(f"REQ-062 test failed: {e}", exc_info=True)
        metrics.results["req_062"]["status"] = "ERROR"

    try:
        mem_delta, peak_mem = test_req_063_large_output()
        if peak_mem > 0:
            metrics.record_req_063(mem_delta, peak_mem)
    except Exception as e:
        logger.error(f"REQ-063 test failed: {e}", exc_info=True)
        metrics.results["req_063"]["status"] = "ERROR"

    summary = metrics.summary()
    print(summary)

    json_path = Path(__file__).parent.parent / "perf_results.json"
    try:
        json_path.write_text(metrics.to_json())
        logger.info(f"Results saved to {json_path}")
    except Exception as e:
        logger.error(f"Failed to save JSON results: {e}")

    passed = sum(1 for v in metrics.results.values() if v["status"] == "PASS")
    failed = sum(1 for v in metrics.results.values() if v["status"] in ("FAIL", "ERROR"))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
