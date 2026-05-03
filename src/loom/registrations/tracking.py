"""Registration tracking system — monitors tool loading success/failure rates.

Provides per-category statistics on which tools loaded vs failed during
server startup. Used by the /health endpoint for diagnostics.
"""
from __future__ import annotations

import threading
from typing import Any

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


def record_success(category: str, tool_name: str) -> None:
    """Record successful tool registration."""
    with _stats_lock:
        if category in _registration_stats:
            _registration_stats[category]["loaded"] += 1


def record_failure(category: str, tool_name: str, error: str) -> None:
    """Record failed tool registration."""
    with _stats_lock:
        if category in _registration_stats:
            _registration_stats[category]["failed"] += 1
            # Keep last 10 errors per category for debugging
            errors = _registration_stats[category]["errors"]
            if len(errors) < 10:
                errors.append(f"{tool_name}: {error[:100]}")


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


def get_registration_stats() -> dict[str, Any]:
    """Get complete registration statistics.

    Returns:
        Dict with:
        - registration_stats: Per-category stats (loaded/failed/errors)
        - optional_modules_loaded: Count of successfully loaded optional modules
        - import_failures: List of import failure messages (up to 20)
        - total_loaded: Sum of all loaded tools across categories
        - total_failed: Sum of all failed tools across categories
    """
    with _stats_lock:
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
            "total_loaded": sum(v["loaded"] for v in _registration_stats.values()),
            "total_failed": sum(v["failed"] for v in _registration_stats.values()),
        }
    return stats


def reset_stats() -> None:
    """Reset all statistics (for testing)."""
    global _optional_modules_loaded, _import_failures
    with _stats_lock:
        for category in _registration_stats:
            _registration_stats[category] = {"loaded": 0, "failed": 0, "errors": []}
        _optional_modules_loaded = 0
        _import_failures = []
