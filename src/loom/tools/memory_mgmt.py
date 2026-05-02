"""Memory management and monitoring tools for Loom server process.

Provides: memory status reporting, garbage collection, and object profiling.
"""

from __future__ import annotations

import gc
import json
import logging
import os
try:
    import psutil
except ImportError:
    psutil = None
import sys
from typing import Any

logger = logging.getLogger("loom.tools.memory_mgmt")


def research_memory_status() -> dict[str, Any]:
    """Report current memory usage of the Loom server process.

    Tracks: RSS, VMS, shared memory, open file descriptors.
    Compares against threshold (warn at 80% of available RAM).

    Returns:
        Dict with keys: pid, rss_mb, vms_mb, open_fds, percent_used,
        threshold_mb, status ("ok"|"warning"|"critical"), recommendations
    """
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        mem_percent = process.memory_percent()

        # Available system RAM
        system_mem = psutil.virtual_memory()
        threshold_mb = system_mem.available / (1024 * 1024) * 0.8

        # Open file descriptors
        try:
            open_fds = len(process.open_files())
        except (psutil.AccessDenied, OSError):
            open_fds = -1

        rss_mb = mem_info.rss / (1024 * 1024)
        vms_mb = mem_info.vms / (1024 * 1024)

        # Determine status
        if mem_percent >= 90:
            status = "critical"
            recommendations = [
                "Call research_memory_gc() to force garbage collection",
                "Consider restarting the server to clear memory",
                "Check for memory leaks in long-running tasks",
            ]
        elif mem_percent >= 80:
            status = "warning"
            recommendations = [
                "Monitor memory usage closely",
                "Consider running research_memory_gc()",
                "Review active sessions and caches",
            ]
        else:
            status = "ok"
            recommendations = []

        return {
            "pid": os.getpid(),
            "rss_mb": round(rss_mb, 2),
            "vms_mb": round(vms_mb, 2),
            "open_fds": open_fds,
            "percent_used": round(mem_percent, 2),
            "threshold_mb": round(threshold_mb, 2),
            "status": status,
            "recommendations": recommendations,
        }
    except Exception as e:
        logger.error("memory_status_error: %s", e)
        return {
            "error": str(e),
            "status": "error",
            "pid": os.getpid(),
        }


def research_memory_gc() -> dict[str, Any]:
    """Force garbage collection and report freed memory.

    Clears module-level caches if they exist.

    Returns:
        Dict with keys: before_mb, after_mb, freed_mb, gc_collected_objects,
        caches_cleared (list of cache names)
    """
    try:
        process = psutil.Process(os.getpid())
        before_mb = process.memory_info().rss / (1024 * 1024)

        # Force garbage collection
        collected = gc.collect()

        # Clear common module-level caches
        caches_cleared = []

        # Clear strategy cache if it exists
        try:
            from loom.tools.reframe_strategies import ALL_STRATEGIES
            if hasattr(ALL_STRATEGIES, "clear"):
                ALL_STRATEGIES.clear()
                caches_cleared.append("strategy_cache")
        except (ImportError, AttributeError):
            pass

        # Clear semantic cache if it exists
        try:
            from loom.semantic_cache import clear_cache
            clear_cache()
            caches_cleared.append("semantic_cache")
        except (ImportError, AttributeError):
            pass

        after_mb = process.memory_info().rss / (1024 * 1024)
        freed_mb = before_mb - after_mb

        return {
            "before_mb": round(before_mb, 2),
            "after_mb": round(after_mb, 2),
            "freed_mb": round(freed_mb, 2),
            "gc_collected_objects": collected,
            "caches_cleared": caches_cleared,
        }
    except Exception as e:
        logger.error("memory_gc_error: %s", e)
        return {
            "error": str(e),
            "status": "error",
        }


def research_memory_profile(top_n: int = 10) -> dict[str, Any]:
    """Profile which objects are using the most memory.

    Samples first 10000 objects to avoid slowness.
    Groups by type, sorts by total size.

    Args:
        top_n: Number of top types to return (default 10)

    Returns:
        Dict with keys: top_types (list of {type, count, total_bytes}),
        total_objects, total_tracked_bytes
    """
    try:
        # Get objects, limiting sample size
        all_objects = gc.get_objects()
        sample_size = min(len(all_objects), 10000)
        objects_sample = all_objects[:sample_size]

        # Group by type and sum sizes
        type_sizes: dict[str, tuple[int, int]] = {}  # type_name -> (count, bytes)
        total_bytes = 0

        for obj in objects_sample:
            obj_type = type(obj).__name__
            obj_size = sys.getsizeof(obj)
            total_bytes += obj_size

            if obj_type not in type_sizes:
                type_sizes[obj_type] = (0, 0)
            count, size = type_sizes[obj_type]
            type_sizes[obj_type] = (count + 1, size + obj_size)

        # Sort by total bytes descending
        sorted_types = sorted(
            type_sizes.items(),
            key=lambda x: x[1][1],
            reverse=True,
        )

        top_types = [
            {
                "type": type_name,
                "count": count,
                "total_bytes": size,
                "total_mb": round(size / (1024 * 1024), 2),
            }
            for type_name, (count, size) in sorted_types[:top_n]
        ]

        return {
            "top_types": top_types,
            "total_objects": len(all_objects),
            "sample_size": sample_size,
            "total_tracked_bytes": total_bytes,
            "total_tracked_mb": round(total_bytes / (1024 * 1024), 2),
        }
    except Exception as e:
        logger.error("memory_profile_error: %s", e)
        return {
            "error": str(e),
            "status": "error",
        }
