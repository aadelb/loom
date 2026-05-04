# Auto-Retry Middleware with Exponential Backoff — Implementation Summary

## Overview

Created a comprehensive auto-retry middleware system for Loom that automatically retries flaky external calls with exponential backoff, jitter, and structured statistics tracking.

## Components Implemented

### 1. Core Retry Module (`src/loom/retry.py`)

**Features:**
- `@with_retry` decorator supporting both sync and async functions
- Exponential backoff: `delay = backoff_base * 2^attempt` with ±10% jitter
- Configurable retryable errors (default: TimeoutError, ConnectionError, OSError)
- Structured logging for each retry attempt
- Global statistics tracking per function
- Support for both `@with_retry` and `@with_retry(...)` syntax

**Key Functions:**
- `@with_retry(max_attempts=3, backoff_base=1.0, retryable_errors=(...))` — Main decorator
- `_get_backoff_delay(attempt, backoff_base)` — Calculate exponential backoff with jitter
- `get_retry_stats()` — Get cumulative retry statistics
- `reset_retry_stats()` — Clear all statistics (for testing)

**Configuration:**
- Respects `LOOM_MAX_RETRIES` environment variable (default: 3)
- Backoff base defaults to 1.0 second
- Jitter magnitude: ±10% of delay

### 2. Retry Statistics Tool (`src/loom/tools/retry_stats.py`)

**Tool: `research_retry_stats(reset: bool = False)`**

Returns comprehensive retry statistics:
```python
{
    "summary": {
        "total_retries": 42,
        "success_after_retry": 31,
        "permanent_failure": 11,
        "recovery_rate": 0.738  # successes / total_retries
    },
    "by_function": {
        "research_fetch": {
            "total_retries": 25,
            "success_after_retry": 20,
            "permanent_failure": 5
        },
        ...
    },
    "functions_tracked": 2,
    "timestamp": "2026-05-04T10:30:45.123456+00:00"
}
```

**Parameters:**
- `reset` (bool): If True, clears all statistics after returning them

### 3. Applied to Key External-Facing Tools

#### `research_fetch` (src/loom/tools/fetch.py)
- Decorated with `@with_retry(max_attempts=3, backoff_base=1.0)`
- Retries on network timeouts and connection errors
- Preserves original fetch behavior and parameters

#### `research_search` (src/loom/tools/search.py)
- Decorated with `@with_retry(max_attempts=3, backoff_base=1.0)`
- Retries on search API timeouts and transient failures
- Works with all search providers (Exa, Tavily, Firecrawl, Brave, etc.)

#### LLM Provider Calls (src/loom/tools/llm.py)
- Added `_call_provider_with_retry()` helper function
- Wraps individual provider.chat() calls with retry logic
- Works WITHIN a single provider attempt (before cascading)
- Complements existing circuit breaker (which works ACROSS providers)

### 4. Server Integration (src/loom/server.py)

- Registered `research_retry_stats` tool in MCP server
- Added graceful import with `suppress(ImportError)` pattern
- Tool is available in the MCP tool registry

## Architecture Decision: Retry vs. Circuit Breaker

The retry middleware is designed to work **within** a single provider/call attempt:

```
┌─────────────────────────────────────────────────────┐
│ _call_with_cascade (cascade across providers)        │
│                                                      │
│  For each provider:                                 │
│  ┌──────────────────────────────────────────────┐  │
│  │ _call_provider_with_retry (retry this call)   │  │
│  │                                               │  │
│  │  Attempt 1: Timeout → sleep 1s → Retry       │  │
│  │  Attempt 2: Timeout → sleep 2s → Retry       │  │
│  │  Attempt 3: Success ✓                         │  │
│  └──────────────────────────────────────────────┘  │
│     ↓ (or on permanent error)                      │
│  Try next provider with circuit breaker check      │
│                                                    │
└─────────────────────────────────────────────────────┘
```

- **Retry Decorator**: Handles transient errors (timeout, connection reset) within a single provider call
- **Circuit Breaker**: Handles persistent provider failures across multiple calls
- No conflict between the two — they work at different layers

## Statistics Tracking

The system automatically tracks:

1. **total_retries** — Total retry attempts across all decorated functions
2. **success_after_retry** — Calls that succeeded after failing initially
3. **permanent_failure** — Calls that exhausted all retries without success
4. **recovery_rate** — `success_after_retry / total_retries` (measure of effectiveness)

Tracked per function and globally, queryable via `research_retry_stats()`.

## Testing

Comprehensive test suite with 28+ tests:

### Unit Tests (`tests/test_retry.py`)
- Backoff calculation and jitter verification
- Sync function retry behavior
- Async function retry behavior
- Statistics tracking
- Decorator syntax variants
- Error message quality

### Integration Tests (`tests/test_retry_integration.py`)
- Statistics API (`research_retry_stats`)
- Decorator integration with tool functions
- Async function preservation
- Circuit breaker compatibility

**All tests pass: 28/28**

## Logging

Each retry attempt is logged with structured information:

```
logger.warning("retry_attempt func=research_fetch attempt=1 max_attempts=3 backoff_secs=1.05 error_type=TimeoutError error=Connection timeout")
logger.info("retry_success func=research_fetch attempts=2 max_attempts=3")
logger.error("retry_exhausted func=research_fetch max_attempts=3 error_type=ConnectionError error=Network unreachable")
```

## Usage Examples

### Basic Usage
```python
from loom.retry import with_retry

@with_retry(max_attempts=3, backoff_base=1.0)
async def fetch_with_retry(url: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.text

result = await fetch_with_retry("https://example.com")
```

### Custom Retryable Errors
```python
from loom.retry import with_retry

@with_retry(
    max_attempts=5,
    retryable_errors=(TimeoutError, requests.ConnectionError, CustomTransientError)
)
def custom_retry_func():
    ...
```

### Get Statistics
```python
from loom.tools.retry_stats import research_retry_stats

stats = research_retry_stats()
print(f"Recovery rate: {stats['summary']['recovery_rate']:.1%}")
print(f"Permanent failures: {stats['summary']['permanent_failure']}")

# Reset for next test cycle
stats_reset = research_retry_stats(reset=True)
```

## Files Modified/Created

### New Files
- `src/loom/retry.py` — Core retry middleware
- `src/loom/tools/retry_stats.py` — Statistics tool
- `tests/test_retry.py` — Unit tests
- `tests/test_retry_integration.py` — Integration tests

### Modified Files
- `src/loom/tools/fetch.py` — Added `@with_retry` decorator
- `src/loom/tools/search.py` — Added `@with_retry` decorator
- `src/loom/tools/llm.py` — Added `_call_provider_with_retry()` helper and integrated with cascade
- `src/loom/server.py` — Registered `research_retry_stats` tool

## Implementation Quality

- **Type-safe**: Full type hints on all signatures
- **Well-tested**: 28 tests covering core functionality and integration
- **Thread-safe**: Uses locks for global statistics
- **Async-ready**: Supports both sync and async functions
- **Configurable**: Environment variable support, customizable parameters
- **Observable**: Structured logging and statistics API
- **Non-breaking**: Decorator preserves function names and docstrings
- **Well-documented**: Comprehensive docstrings and examples

## Performance Impact

- **Memory**: Minimal — only tracks function names and integer counters
- **CPU**: Negligible for successful calls; backoff uses `sleep()` on transient errors
- **Logging**: Structured logs only on retry attempts (not on success)

## Future Enhancements

Possible future improvements:
1. Adaptive backoff based on historical success rates
2. Per-endpoint configuration (different timeouts for different services)
3. Metrics export (Prometheus format for monitoring)
4. Request batching with retry coordination
5. Partial success handling (for batch operations)
