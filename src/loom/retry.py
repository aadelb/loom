"""Auto-retry middleware with exponential backoff for flaky external calls.

Provides a @with_retry decorator for wrapping both sync and async functions
with configurable exponential backoff, jitter, and structured logging.

Designed to work within a single provider attempt (not across providers like
the circuit breaker in llm.py). Tracks statistics for analysis.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
import random
import time
from typing import Any, Callable, TypeVar, cast, overload

logger = logging.getLogger("loom.retry")

# Global statistics tracking
_retry_stats: dict[str, dict[str, int]] = {}
_stats_lock = __import__("threading").Lock()

# Configuration
_DEFAULT_MAX_ATTEMPTS = int(os.getenv("LOOM_MAX_RETRIES", "3"))
_DEFAULT_BACKOFF_BASE = 1.0  # seconds
_DEFAULT_JITTER = 0.1  # fraction of delay for random jitter

# Retryable errors by default: transient network errors
_DEFAULT_RETRYABLE_ERRORS = (
    TimeoutError,
    ConnectionError,
    OSError,  # Includes socket.error on some platforms
)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def _record_retry_stat(func_name: str, stat_type: str) -> None:
    """Record a retry statistic for analysis.

    Args:
        func_name: Name of the function being retried
        stat_type: Type of stat ('total_retries', 'success_after_retry', 'permanent_failure')
    """
    with _stats_lock:
        if func_name not in _retry_stats:
            _retry_stats[func_name] = {
                "total_retries": 0,
                "success_after_retry": 0,
                "permanent_failure": 0,
            }
        _retry_stats[func_name][stat_type] += 1


def _get_backoff_delay(attempt: int, backoff_base: float) -> float:
    """Calculate exponential backoff with jitter.

    Formula: delay = backoff_base * 2^attempt * (1 + random jitter)

    Args:
        attempt: 0-indexed attempt number (0 = first retry, 1 = second retry, etc.)
        backoff_base: Base delay in seconds (typically 1.0)

    Returns:
        Delay in seconds with jitter applied
    """
    # Exponential: 2^attempt = 1, 2, 4, 8, ...
    exp_delay = backoff_base * (2 ** attempt)
    # Add jitter: ±10% of delay
    jitter = exp_delay * _DEFAULT_JITTER * random.uniform(-1, 1)
    return max(0.01, exp_delay + jitter)


@overload
def with_retry(
    *,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    backoff_base: float = _DEFAULT_BACKOFF_BASE,
    retryable_errors: tuple[type[Exception], ...] = _DEFAULT_RETRYABLE_ERRORS,
) -> Callable[[F], F]:
    ...


@overload
def with_retry(func: F) -> F:
    ...


def with_retry(
    func: F | None = None,
    *,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    backoff_base: float = _DEFAULT_BACKOFF_BASE,
    retryable_errors: tuple[type[Exception], ...] = _DEFAULT_RETRYABLE_ERRORS,
) -> F | Callable[[F], F]:
    """Decorator for auto-retrying flaky functions with exponential backoff.

    Supports both sync and async functions. Works within a single provider
    attempt (complements circuit breaker which works across providers).

    Args:
        max_attempts: Maximum number of attempts (default from LOOM_MAX_RETRIES env var)
        backoff_base: Base delay in seconds for exponential backoff (default: 1.0)
        retryable_errors: Tuple of exception types to retry on (default: TimeoutError, ConnectionError, OSError)

    Returns:
        Decorated function that retries on transient errors

    Example:
        @with_retry(max_attempts=3, backoff_base=1.0)
        async def fetch_with_retry(url: str) -> str:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                return resp.text

        result = await fetch_with_retry("https://example.com")
    """

    def decorator(fn: F) -> F:
        import inspect

        is_async = inspect.iscoroutinefunction(fn)
        fn_name = fn.__name__

        if is_async:

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Async wrapper with retry logic."""
                last_error: Exception | None = None

                for attempt in range(max_attempts):
                    try:
                        result = await fn(*args, **kwargs)
                        if attempt > 0:
                            _record_retry_stat(fn_name, "success_after_retry")
                            logger.info("retry_success func=%s attempts=%d max_attempts=%d", fn_name, attempt + 1, max_attempts)
                        return result

                    except Exception as exc:
                        last_error = exc

                        # If not retryable, raise immediately
                        if not isinstance(exc, retryable_errors):
                            logger.error("retry_non_retryable func=%s error_type=%s error=%s attempt=%d", fn_name, type(exc).__name__, str(exc), attempt + 1)
                            raise

                        # If last attempt, give up
                        if attempt == max_attempts - 1:
                            _record_retry_stat(fn_name, "total_retries")
                            _record_retry_stat(fn_name, "permanent_failure")
                            logger.error("retry_exhausted func=%s max_attempts=%d error_type=%s error=%s", fn_name, max_attempts, type(exc).__name__, str(exc))
                            raise

                        # Calculate backoff and sleep
                        delay = _get_backoff_delay(attempt, backoff_base)
                        _record_retry_stat(fn_name, "total_retries")
                        logger.warning("retry_attempt func=%s attempt=%d max_attempts=%d backoff_secs=%.2f error_type=%s error=%s", fn_name, attempt + 1, max_attempts, delay, type(exc).__name__, str(exc))
                        await asyncio.sleep(delay)

                # Should not reach here, but be defensive
                if last_error is not None:
                    raise last_error
                raise RuntimeError(f"{fn_name} failed after {max_attempts} attempts")

            return cast(F, async_wrapper)

        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Sync wrapper with retry logic."""
                last_error: Exception | None = None

                for attempt in range(max_attempts):
                    try:
                        result = fn(*args, **kwargs)
                        if attempt > 0:
                            _record_retry_stat(fn_name, "success_after_retry")
                            logger.info("retry_success func=%s attempts=%d max_attempts=%d", fn_name, attempt + 1, max_attempts)
                        return result

                    except Exception as exc:
                        last_error = exc

                        # If not retryable, raise immediately
                        if not isinstance(exc, retryable_errors):
                            logger.error("retry_non_retryable func=%s error_type=%s error=%s attempt=%d", fn_name, type(exc).__name__, str(exc), attempt + 1)
                            raise

                        # If last attempt, give up
                        if attempt == max_attempts - 1:
                            _record_retry_stat(fn_name, "total_retries")
                            _record_retry_stat(fn_name, "permanent_failure")
                            logger.error("retry_exhausted func=%s max_attempts=%d error_type=%s error=%s", fn_name, max_attempts, type(exc).__name__, str(exc))
                            raise

                        # Calculate backoff and sleep
                        delay = _get_backoff_delay(attempt, backoff_base)
                        _record_retry_stat(fn_name, "total_retries")
                        logger.warning("retry_attempt func=%s attempt=%d max_attempts=%d backoff_secs=%.2f error_type=%s error=%s", fn_name, attempt + 1, max_attempts, delay, type(exc).__name__, str(exc))
                        time.sleep(delay)

                # Should not reach here, but be defensive
                if last_error is not None:
                    raise last_error
                raise RuntimeError(f"{fn_name} failed after {max_attempts} attempts")

            return cast(F, sync_wrapper)

    # Support both @with_retry and @with_retry(...) syntax
    if func is None:
        # Called with arguments: @with_retry(max_attempts=5)
        return decorator
    else:
        # Called without arguments: @with_retry
        return decorator(func)


def get_retry_stats() -> dict[str, dict[str, int]]:
    """Get cumulative retry statistics across all decorated functions.

    Returns:
        Dict mapping function names to stats dicts with keys:
            - total_retries: Total number of retries attempted
            - success_after_retry: Successful after at least one retry
            - permanent_failure: Failed after all attempts exhausted

    Example:
        stats = get_retry_stats()
        for func_name, counts in stats.items():
            print(f"{func_name}: {counts['total_retries']} retries, "
                  f"{counts['success_after_retry']} recovered, "
                  f"{counts['permanent_failure']} failed")
    """
    with _stats_lock:
        return dict(_retry_stats)


def reset_retry_stats() -> None:
    """Reset all retry statistics. Useful for testing."""
    with _stats_lock:
        _retry_stats.clear()
