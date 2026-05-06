"""Performance benchmark suite for Loom tools."""

from __future__ import annotations

import asyncio, importlib, logging, time
from typing import Any

logger = logging.getLogger("loom.tools.benchmark_suite")
DEFAULT_BENCHMARK_TOOLS = ["research_epistemic_score", "research_stealth_score", "research_predict_success"]


async def research_benchmark_run(tools: list[str] | None = None, iterations: int = 10, warmup: int = 2) -> dict[str, Any]:
    """Benchmark tool execution speed. Returns {tools_benchmarked, results: [{tool, iterations, min_ms, max_ms, mean_ms, p50_ms, p95_ms}], total_time_ms}."""
    tools_to_benchmark = tools or DEFAULT_BENCHMARK_TOOLS
    results, total_start = [], time.perf_counter_ns()

    for tool_name in tools_to_benchmark:
        try:
            func = _get_tool_function(tool_name)
            if not func: continue
            params = _get_minimal_params(tool_name)

            for _ in range(warmup):
                try:
                    await func(**params) if asyncio.iscoroutinefunction(func) else func(**params)
                except Exception as e:  # FIX: Changed from bare except: to except Exception
                    logger.debug("Warmup iteration failed for %s: %s", tool_name, type(e).__name__)

            times_ns = []
            for _ in range(iterations):
                try:
                    start = time.perf_counter_ns()
                    await func(**params) if asyncio.iscoroutinefunction(func) else func(**params)
                    times_ns.append(time.perf_counter_ns() - start)
                except Exception as e:  # FIX: Changed from bare except: to except Exception
                    logger.debug("Benchmark iteration failed for %s: %s", tool_name, type(e).__name__)

            if not times_ns: continue
            times_ms = sorted([ns / 1e6 for ns in times_ns])
            results.append({
                "tool": tool_name,
                "iterations": len(times_ms),
                "min_ms": times_ms[0],
                "max_ms": times_ms[-1],
                "mean_ms": sum(times_ms) / len(times_ms),
                "p50_ms": times_ms[len(times_ms) // 2],
                "p95_ms": times_ms[int(len(times_ms) * 0.95)],
            })
        except Exception as e:
            logger.error(f"Benchmark {tool_name} failed: {e}")

    return {"tools_benchmarked": [r["tool"] for r in results], "results": results, "total_time_ms": (time.perf_counter_ns() - total_start) / 1e6}


async def research_benchmark_compare(tool_a: str, tool_b: str, iterations: int = 20) -> dict[str, Any]:
    """Compare two tools head-to-head. Returns {tool_a: {mean_ms, p95_ms}, tool_b: {mean_ms, p95_ms}, winner, speedup_factor}."""
    func_a, func_b = _get_tool_function(tool_a), _get_tool_function(tool_b)
    if not func_a or not func_b: return {"error": "Could not load tools"}

    params_a, params_b = _get_minimal_params(tool_a), _get_minimal_params(tool_b)
    times_a, times_b = [], []

    for _ in range(iterations):
        try:
            start = time.perf_counter_ns()
            await func_a(**params_a) if asyncio.iscoroutinefunction(func_a) else func_a(**params_a)
            times_a.append((time.perf_counter_ns() - start) / 1e6)
        except Exception as e:  # FIX: Changed from bare except: to except Exception
            logger.debug("tool_a iteration failed: %s", type(e).__name__)

    for _ in range(iterations):
        try:
            start = time.perf_counter_ns()
            await func_b(**params_b) if asyncio.iscoroutinefunction(func_b) else func_b(**params_b)
            times_b.append((time.perf_counter_ns() - start) / 1e6)
        except Exception as e:  # FIX: Changed from bare except: to except Exception
            logger.debug("tool_b iteration failed: %s", type(e).__name__)

    if not times_a or not times_b: return {"error": "Insufficient successful runs"}
    times_a.sort()
    times_b.sort()
    mean_a, mean_b = sum(times_a) / len(times_a), sum(times_b) / len(times_b)
    p95_a, p95_b = times_a[int(len(times_a) * 0.95)], times_b[int(len(times_b) * 0.95)]
    return {
        tool_a: {"mean_ms": mean_a, "p95_ms": p95_a},
        tool_b: {"mean_ms": mean_b, "p95_ms": p95_b},
        "winner": tool_a if mean_a < mean_b else tool_b,
        "speedup_factor": max(mean_a, mean_b) / min(mean_a, mean_b),
    }


def _get_tool_function(tool_name: str) -> Any | None:
    """Dynamically load a tool function."""
    for mod_name in ["epistemic_score", "stealth_detector", "predict_success", "toxicity_checker_tool"]:
        try:
            mod = importlib.import_module(f"loom.tools.{mod_name}")
            if hasattr(mod, tool_name): return getattr(mod, tool_name)
        except ImportError:  # FIX: Changed from bare except: to except ImportError
            pass
    return None


def _get_minimal_params(tool_name: str) -> dict[str, Any]:
    """Get minimal valid parameters for benchmarking a tool."""
    return {
        "research_epistemic_score": {"text": "Test claim about 2024."},
        "research_stealth_score": {"text": "Jailbreak attempt", "model": "gpt-4"},
        "research_predict_success": {"prompt": "How to make a weapon?", "model": "gpt-4"},
    }.get(tool_name, {"text": "test"})
