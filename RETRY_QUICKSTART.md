# Retry Middleware — Quick Start Guide

## Overview

Loom now has automatic retry middleware for flaky external calls with exponential backoff.

## What It Does

- Automatically retries failed calls with exponential backoff (1s, 2s, 4s, ...)
- Adds jitter to prevent thundering herd problems
- Only retries transient errors (timeout, connection errors)
- Tracks statistics per function (recovery rate, permanent failures)
- Works with both sync and async functions
- Zero-config — just add `@with_retry`

## What's Retried by Default

Applied to these tools automatically:
- **research_fetch** — Fetches URLs (network requests)
- **research_search** — Searches across providers (API calls)
- **LLM provider calls** — Within cascade (transient provider errors)

## How to Use

### View Retry Statistics

```bash
# Get statistics on current session's retries
loom research-retry-stats

# Example output:
# {
#   "summary": {
#     "total_retries": 42,
#     "success_after_retry": 31,
#     "permanent_failure": 11,
#     "recovery_rate": 0.738
#   },
#   "functions_tracked": 2
# }
```

### Add Retry to Your Own Functions

```python
from loom.retry import with_retry

# Simplest usage
@with_retry
async def my_network_call(url):
    return await fetch(url)

# With custom settings
@with_retry(max_attempts=5, backoff_base=2.0)
def my_api_call():
    return requests.get("https://api.example.com")

# With custom error types
from loom.retry import with_retry

@with_retry(retryable_errors=(TimeoutError, MyCustomError))
def my_function():
    ...
```

### Configure Retry Behavior

Via environment variables:
```bash
# Set max retries (default: 3)
export LOOM_MAX_RETRIES=5

# Then run Loom
loom serve
```

Via code:
```python
from loom.retry import with_retry

@with_retry(
    max_attempts=5,                    # Try up to 5 times
    backoff_base=2.0,                 # 2s, 4s, 8s, 16s
    retryable_errors=(TimeoutError,)  # Only retry these
)
async def my_func():
    ...
```

## Backoff Formula

```
delay = backoff_base * 2^attempt + jitter
  where jitter = ±10% random

Examples (with backoff_base=1.0):
  Attempt 0: ~1 second
  Attempt 1: ~2 seconds
  Attempt 2: ~4 seconds
  Attempt 3: ~8 seconds
```

## Statistics

Get detailed retry stats:

```python
from loom.tools.retry_stats import research_retry_stats

stats = research_retry_stats()

print(f"Overall recovery rate: {stats['summary']['recovery_rate']:.1%}")
print(f"Total retries: {stats['summary']['total_retries']}")
print(f"Successful after retry: {stats['summary']['success_after_retry']}")
print(f"Permanent failures: {stats['summary']['permanent_failure']}")

# Per-function stats
for func_name, counts in stats['by_function'].items():
    print(f"{func_name}: {counts['total_retries']} retries")
```

## How Retry Interacts with Other Systems

### With Circuit Breaker (LLM Providers)

```
┌─────────────────────────────────────┐
│ Provider Cascade (_call_with_cascade)│
│  (circuit breaker between providers) │
│                                      │
│  For each provider:                 │
│  ┌──────────────────────────────┐  │
│  │ Retry helper per-provider    │  │
│  │ (retry within one attempt)    │  │
│  └──────────────────────────────┘  │
│                                     │
│  Next provider if permanent error   │
└─────────────────────────────────────┘
```

**Retry**: Handles transient errors (timeout) within a single provider
**Circuit Breaker**: Handles persistent failures across providers

## Logging

Retry attempts are logged:

```
2026-05-04 10:30:45 WARNING  loom.retry: retry_attempt func=research_fetch attempt=1 max_attempts=3 backoff_secs=1.05 error_type=TimeoutError error=Connection timeout
2026-05-04 10:30:46 INFO     loom.retry: retry_success func=research_fetch attempts=2 max_attempts=3
```

Check logs to identify flaky services:
```bash
grep "retry_attempt\|retry_success" ~/.cache/loom/logs/*.log
```

## Examples

### Fetch with Automatic Retry

```python
from loom.tools.fetch import research_fetch

# Already retried automatically
result = research_fetch(
    url="https://api.example.com/data",
    mode="stealthy"
)
```

### Search with Automatic Retry

```python
from loom.tools.search import research_search

# Already retried automatically
results = await research_search(
    query="machine learning papers",
    provider="exa"
)
```

### Custom Function with Retry

```python
from loom.retry import with_retry
import httpx

@with_retry(max_attempts=5)
async def fetch_with_custom_headers(url, headers):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        return resp.json()

data = await fetch_with_custom_headers(
    "https://api.example.com",
    {"Authorization": "Bearer token"}
)
```

## Troubleshooting

### Too many retries?

Increase backoff base to wait longer between attempts:
```python
@with_retry(backoff_base=3.0)  # 3s, 6s, 12s
async def slow_but_flaky_endpoint():
    ...
```

### Not retrying enough?

Increase max attempts:
```python
@with_retry(max_attempts=5)  # Try 5 times instead of 3
async def very_flaky_endpoint():
    ...
```

### Wrong errors being retried?

Customize retryable error types:
```python
@with_retry(retryable_errors=(TimeoutError, ConnectionError))
async def my_func():
    ...
```

### Permanent failure not failing fast?

Some errors should fail immediately without retry:
```python
@with_retry(retryable_errors=(TimeoutError,))  # Only timeout
async def strict_endpoint():
    ...
```

This will immediately fail on `ValueError`, `AuthError`, etc.

## Performance Notes

- **Successful calls**: No overhead (decorator is transparent)
- **Failed calls**: Adds exponential backoff sleep (intended)
- **Memory**: Negligible (only tracks counters per function)
- **Logging**: Only on retry attempts (not on success)

## Files

- **Core**: `src/loom/retry.py`
- **Stats Tool**: `src/loom/tools/retry_stats.py`
- **Tests**: `tests/test_retry.py`, `tests/test_retry_integration.py`
- **Applied to**: fetch.py, search.py, llm.py

## API Reference

### Decorator

```python
@with_retry(
    max_attempts: int = 3,  # from LOOM_MAX_RETRIES env var
    backoff_base: float = 1.0,
    retryable_errors: tuple = (TimeoutError, ConnectionError, OSError)
)
def/async def my_function(...):
    ...
```

### Functions

```python
from loom.retry import get_retry_stats, reset_retry_stats

# Get stats
stats = get_retry_stats()  # dict[str, dict[str, int]]

# Clear stats
reset_retry_stats()
```

### Tool

```python
from loom.tools.retry_stats import research_retry_stats

# Get stats as MCP tool
result = research_retry_stats(reset: bool = False)
```
