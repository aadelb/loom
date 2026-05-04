"""Registration tracking system — monitors tool loading success/failure rates.

Provides per-category statistics on which tools loaded vs failed during
server startup. Used by the /health endpoint for diagnostics.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger("loom.registrations")

# Thread-safe statistics store
_stats_lock = threading.RLock()
_registration_stats: dict[str, dict[str, Any]] = {
    "core": {"loaded": 0, "failed": 0, "errors": []},
    "llm": {"loaded": 0, "failed": 0, "errors": []},
    "reframe": {"loaded": 0, "failed": 0, "errors": []},
    "adversarial": {"loaded": 0, "failed": 0, "errors": []},
    "infrastructure": {"loaded": 0, "failed": 0, "errors": []},
    "intelligence": {"loaded": 0, "failed": 0, "errors": []},
    "research": {"loaded": 0, "failed": 0, "errors": []},
    "devops": {"loaded": 0, "failed": 0, "errors": []},
}

_optional_modules_loaded = 0
_import_failures: list[str] = []

# New: Track ALL registration errors in detail
_registration_errors: list[dict[str, Any]] = []


def record_success(category: str, tool_name: str) -> None:
    """Record successful tool registration."""
    with _stats_lock:
        if category in _registration_stats:
            _registration_stats[category]["loaded"] += 1


def record_failure(category: str, tool_name: str, error: str) -> None:
    """Record failed tool registration with detailed tracking.

    Args:
        category: Registration category (e.g., "core", "llm")
        tool_name: Tool or module name that failed
        error: Error message or exception text
    """
    with _stats_lock:
        if category in _registration_stats:
            _registration_stats[category]["failed"] += 1
            # Keep last 10 errors per category for debugging
            errors = _registration_stats[category]["errors"]
            if len(errors) < 10:
                errors.append(f"{tool_name}: {error[:100]}")

        # Track detailed error for get_registration_errors()
        if len(_registration_errors) < 100:  # Cap at 100 for memory safety
            _registration_errors.append({
                "category": category,
                "function": tool_name,
                "error": error[:200],  # Truncate long error messages
                "timestamp": datetime.now(UTC).isoformat(),
            })


def record_optional_module_loaded(module_name: str) -> None:
    """Record successful optional module import."""
    global _optional_modules_loaded
    with _stats_lock:
        _optional_modules_loaded += 1


def record_import_failure(module_name: str, error: str) -> None:
    """Record failed optional module import."""
    with _stats_lock:
        if len(_import_failures) < 20:
            _import_failures.append(f"{module_name}: {error[:100]}")


def get_registration_errors() -> list[dict[str, Any]]:
    """Get all registration errors with timestamps.

    Returns:
        List of error dicts with keys: category, function, error, timestamp
    """
    with _stats_lock:
        return _registration_errors.copy()


def get_registration_stats() -> dict[str, Any]:
    """Get complete registration statistics.

    Returns:
        Dict with:
        - registration_stats: Per-category stats (loaded/failed/errors)
        - optional_modules_loaded: Count of successfully loaded optional modules
        - import_failures: List of import failure messages (up to 20)
        - total_loaded: Sum of all loaded tools across categories
        - total_failed: Sum of all failed tools across categories
        - registration_errors: Detailed error list with timestamps
        - health_status: "healthy" or "degraded" based on failure percentage
    """
    with _stats_lock:
        total_loaded = sum(v["loaded"] for v in _registration_stats.values())
        total_failed = sum(v["failed"] for v in _registration_stats.values())

        # Calculate failure percentage
        total = total_loaded + total_failed
        failure_rate = (total_failed / total * 100) if total > 0 else 0

        # Mark as degraded if >20% failures
        health_status = "degraded" if failure_rate > 20 else "healthy"

        # Log warning summary if there are failures
        if total_failed > 0:
            log.warning(
                "registration_summary total_failed=%d total_loaded=%d "
                "failure_rate=%.1f%% health_status=%s",
                total_failed,
                total_loaded,
                failure_rate,
                health_status,
            )

        stats = {
            "registration_stats": {
                k: {
                    "loaded": v["loaded"],
                    "failed": v["failed"],
                    "errors": v["errors"],
                }
                for k, v in _registration_stats.items()
            },
            "optional_modules_loaded": _optional_modules_loaded,
            "import_failures": _import_failures.copy(),
            "total_loaded": total_loaded,
            "total_failed": total_failed,
            "failure_rate_percent": round(failure_rate, 1),
            "registration_errors": _registration_errors.copy(),
            "health_status": health_status,
        }
    return stats


def reset_stats() -> None:
    """Reset all statistics (for testing)."""
    global _optional_modules_loaded, _import_failures, _registration_errors
    with _stats_lock:
        for category in _registration_stats:
            _registration_stats[category] = {"loaded": 0, "failed": 0, "errors": []}
        _optional_modules_loaded = 0
        _import_failures = []
        _registration_errors = []
