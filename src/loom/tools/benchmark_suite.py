"""Performance benchmark suite for Loom tools.

Provides tools to measure and compare execution speed of heuristic-only tools
(no API calls). Useful for performance profiling and regression detection.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import time
from typing import Any

logger = logging.getLogger("loom.tools.benchmark_suite")

# Default fast tools (heuristic-only, no API calls)
DEFAULT_BENCHMARK_TOOLS = [
    "research_epistemic_score",
    "research_stealth_score",
    "research_predict_success",
]


async def research_benchmark_run(
    tools: list[str] | None = None,
    iterations: int = 10,
    warmup: int = 2,
) -> dict[str, Any]:
    """Benchmark tool execution speed.

    Measures min, max, mean, p50, p95 execution time for specified tools.
    Skips warmup iterations from final statistics.

    Args:
        tools: List of tool names to benchmark. If None, uses default fast tools.
        iterations: Number of times to call each tool (default: 10)
        warmup: Number of warmup iterations to skip (default: 2)

    Returns:
        Dict with keys:
          - tools_benchmarked: list of tool names
          - results: list of {tool, iterations, min_ms, max_ms, mean_ms, p50_ms, p95_ms}
          - total_time_ms: total elapsed time for all benchmarks
    """
    tools_to_benchmark = tools or DEFAULT_BENCHMARK_TOOLS
    results = []
    total_start_ns = time.perf_counter_ns()

    for tool_name in tools_to_benchmark:
        try:
            # Import tool function dynamically
            func = _get_tool_function(tool_name)
            if not func:
                logger.warning(f"Tool {tool_name} not found, skipping")
                continue

            # Get minimal valid params for the tool
            params = _get_minimal_params(tool_name)

            # Warmup iterations (not counted)
            for _ in range(warmup):
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func(**params)
                    else:
                        func(**params)
                except Exception as e:
                    logger.debug(f"Warmup error for {tool_name}: {e}")

            # Benchmark iterations
            times_ns: list[int] = []
            for _ in range(iterations):
                try:
                    start_ns = time.perf_counter_ns()
                    if asyncio.iscoroutinefunction(func):
                        await func(**params)
                    else:
                        func(**params)
                    elapsed_ns = time.perf_counter_ns() - start_ns
                    times_ns.append(elapsed_ns)
                except Exception as e:
                    logger.warning(f"Benchmark error for {tool_name}: {e}")
                    continue

            if not times_ns:
                logger.warning(f"No successful benchmarks for {tool_name}")
                continue

            # Convert to milliseconds
            times_ms = sorted([ns / 1_000_000 for ns in times_ns])

            # Calculate statistics
            result = {
                "tool": tool_name,
                "iterations": len(times_ms),
                "min_ms": times_ms[0],
                "max_ms": times_ms[-1],
                "mean_ms": sum(times_ms) / len(times_ms),
                "p50_ms": times_ms[len(times_ms) // 2],
                "p95_ms": times_ms[int(len(times_ms) * 0.95)],
            }
            results.append(result)
            logger.info(f"Benchmarked {tool_name}: {result['mean_ms']:.2f}ms mean")

        except Exception as e:
            logger.error(f"Failed to benchmark {tool_name}: {e}")

    total_ms = (time.perf_counter_ns() - total_start_ns) / 1_000_000

    return {
        "tools_benchmarked": [r["tool"] for r in results],
        "results": results,
        "total_time_ms": total_ms,
    }


async def research_benchmark_compare(
    tool_a: str,
    tool_b: str,
    iterations: int = 20,
) -> dict[str, Any]:
    """Compare two tools head-to-head on speed.

    Runs both tools the same number of times and compares their performance.

    Args:
        tool_a: First tool name
        tool_b: Second tool name
        iterations: Number of iterations per tool (default: 20)

    Returns:
        Dict with keys:
          - tool_a: {mean_ms, p95_ms}
          - tool_b: {mean_ms, p95_ms}
          - winner: name of faster tool
          - speedup_factor: ratio of slower to faster (e.g., 1.5 = 50% faster)
    """
    func_a = _get_tool_function(tool_a)
    func_b = _get_tool_function(tool_b)

    if not func_a or not func_b:
        return {
            "error": f"Could not load {tool_a if not func_a else tool_b}",
        }

    params_a = _get_minimal_params(tool_a)
    params_b = _get_minimal_params(tool_b)

    # Benchmark tool_a
    times_a_ms = []
    for _ in range(iterations):
        try:
            start_ns = time.perf_counter_ns()
            if asyncio.iscoroutinefunction(func_a):
                await func_a(**params_a)
            else:
                func_a(**params_a)
            elapsed_ns = time.perf_counter_ns() - start_ns
            times_a_ms.append(elapsed_ns / 1_000_000)
        except Exception as e:
            logger.warning(f"Error benchmarking {tool_a}: {e}")

    # Benchmark tool_b
    times_b_ms = []
    for _ in range(iterations):
        try:
            start_ns = time.perf_counter_ns()
            if asyncio.iscoroutinefunction(func_b):
                await func_b(**params_b)
            else:
                func_b(**params_b)
            elapsed_ns = time.perf_counter_ns() - start_ns
            times_b_ms.append(elapsed_ns / 1_000_000)
        except Exception as e:
            logger.warning(f"Error benchmarking {tool_b}: {e}")

    if not times_a_ms or not times_b_ms:
        return {
            "error": "Insufficient successful runs to compare",
        }

    times_a_ms.sort()
    times_b_ms.sort()

    mean_a = sum(times_a_ms) / len(times_a_ms)
    mean_b = sum(times_b_ms) / len(times_b_ms)
    p95_a = times_a_ms[int(len(times_a_ms) * 0.95)]
    p95_b = times_b_ms[int(len(times_b_ms) * 0.95)]

    winner = tool_a if mean_a < mean_b else tool_b
    speedup = max(mean_a, mean_b) / min(mean_a, mean_b)

    return {
        tool_a: {"mean_ms": mean_a, "p95_ms": p95_a},
        tool_b: {"mean_ms": mean_b, "p95_ms": p95_b},
        "winner": winner,
        "speedup_factor": speedup,
    }


def _get_tool_function(tool_name: str) -> Any | None:
    """Dynamically load a tool function by name.

    Searches loom.tools.* modules for the function.
    """
    try:
        # Try direct tool module imports
        tool_modules = [
            "epistemic_score",
            "stealth_detector",
            "predict_success",
            "toxicity_checker_tool",
            "model_sentiment",
        ]

        for module_name in tool_modules:
            try:
                mod = importlib.import_module(f"loom.tools.{module_name}")
                if hasattr(mod, tool_name):
                    return getattr(mod, tool_name)
            except ImportError:
                continue

        return None
    except Exception as e:
        logger.error(f"Failed to load tool {tool_name}: {e}")
        return None


def _get_minimal_params(tool_name: str) -> dict[str, Any]:
    """Get minimal valid parameters for benchmarking a tool.

    Returns a dict suitable for calling the tool with no side effects.
    """
    params_map = {
        "research_epistemic_score": {"text": "Test claim about climate change in 2024. Studies show temperatures increased."},
        "research_stealth_score": {"text": "This request appears to be a jailbreak attempt.", "model": "gpt-4"},
        "research_predict_success": {"prompt": "How to make a chemical weapon?", "model": "gpt-4"},
        "research_toxicity_check": {"text": "This is a neutral statement."},
        "research_model_sentiment": {"text": "I really love this tool!"},
    }
    return params_map.get(tool_name, {"text": "benchmark test"})
