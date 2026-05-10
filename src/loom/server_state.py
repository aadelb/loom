"""Shared server state — imported by scheduler, health_deep, middleware, shutdown.

This module breaks the circular import between loom.scheduler and loom.server
by providing a stable import target for server state that doesn't depend on
the full server module.
"""
from __future__ import annotations

import time

_health_status: str = "unknown"
_start_time: float = time.time()
_shutting_down: bool = False
_shutdown_grace_start: float = 0.0
_validation_error_count: int = 0
_startup_validation_result: dict | None = None
_prometheus_enabled: bool = False


def get_health_status() -> str:
    return _health_status


def set_health_status(status: str) -> None:
    global _health_status
    _health_status = status


def get_start_time() -> float:
    return _start_time


def set_start_time(t: float) -> None:
    global _start_time
    _start_time = t


def is_shutting_down() -> bool:
    return _shutting_down


def set_shutting_down() -> None:
    global _shutting_down, _shutdown_grace_start
    _shutting_down = True
    _shutdown_grace_start = time.time()


def shutdown_grace_time_remaining() -> float:
    if not _shutting_down:
        return 30.0
    return max(0.0, 30.0 - (time.time() - _shutdown_grace_start))


def get_validation_error_count() -> int:
    return _validation_error_count


def set_validation_error_count(count: int) -> None:
    global _validation_error_count
    _validation_error_count = count


def get_startup_validation_result() -> dict | None:
    return _startup_validation_result


def set_startup_validation_result(result: dict) -> None:
    global _startup_validation_result
    _startup_validation_result = result


def set_prometheus_enabled(enabled: bool) -> None:
    global _prometheus_enabled
    _prometheus_enabled = enabled


def is_prometheus_enabled() -> bool:
    return _prometheus_enabled
