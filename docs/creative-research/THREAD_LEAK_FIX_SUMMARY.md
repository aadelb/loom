# Thread Leak Fix: Spider Fetch Timeouts

## Problem Statement

**Issue**: When `asyncio.wait_for()` times out while wrapping `loop.run_in_executor()`, the asyncio task is cancelled but the underlying executor thread continues running, creating an orphaned thread leak.

**Root Cause**: In `/src/loom/tools/spider.py`, the timeout hierarchy was inverted:
- `asyncio.wait_for(timeout=60s)` ← outer timeout (task cancellation)
- `loop.run_in_executor(research_fetch(..., timeout=None))` ← no inner timeout
- The executor thread could run indefinitely even after the asyncio task was cancelled

**Impact**: Long-running fetches (Camoufox, Botasaurus) could hang, exhaust thread pool, and leak system resources.

## Solution: Enforce Timeout Hierarchy

**Key Insight**: Inner timeout must be **strictly less than** outer timeout. This ensures:
1. The executor thread terminates naturally (via inner timeout)
2. Before asyncio can cancel the task (via outer timeout)
3. No orphaned threads left running

### Changes Made to `/src/loom/tools/spider.py`

#### 1. Added Timeout Constants
```python
INNER_FETCH_TIMEOUT = max(1, EXTERNAL_TIMEOUT_SECS - 10)  # 20s
OUTER_WAIT_FOR_TIMEOUT = EXTERNAL_TIMEOUT_SECS * 2      # 60s
```

- **INNER_FETCH_TIMEOUT** (20s): Passed to `research_fetch()` in executor thread
- **OUTER_WAIT_FOR_TIMEOUT** (60s): Passed to `asyncio.wait_for()` for task cancellation
- **Gap** (40s): Buffer ensures thread cleanup before task cancellation

#### 2. Updated Timeout Handling in `_one()` Function
```python
# Clamp user-provided timeout to INNER_FETCH_TIMEOUT
inner_timeout = INNER_FETCH_TIMEOUT
if params.timeout is not None and params.timeout > 0:
    inner_timeout = min(params.timeout, INNER_FETCH_TIMEOUT)

# Pass clamped timeout to research_fetch
return await asyncio.wait_for(
    loop.run_in_executor(
        None,
        lambda: research_fetch(
            u,
            # ... other params ...
            timeout=inner_timeout,  # ← NOW ENFORCED
        ),
    ),
    timeout=OUTER_WAIT_FOR_TIMEOUT,  # ← Outer guard
)
```

#### 3. Enhanced Documentation
- Added comprehensive docstring explaining the timeout hierarchy
- Documented the critical invariant: `inner_timeout < outer_timeout`
- Explained how clamping prevents thread leaks

## Verification

### 1. Unit Tests Pass
All 5 existing spider tests pass with the fix:
- `test_spider_empty_urls_returns_empty` ✓
- `test_spider_parallel_fetches` ✓
- `test_spider_respects_concurrency_limit` ✓
- `test_spider_mixed_ok_fail` ✓
- `test_spider_deduplication` ✓

Coverage: 70% for spider.py

### 2. Timeout Hierarchy Verification
```
INNER_FETCH_TIMEOUT: 20s
OUTER_WAIT_FOR_TIMEOUT: 60s
Gap: 40s ✓ (ensures thread cleanup)
Hierarchy: 20s < 60s ✓
```

### 3. Timeout Propagation Verified
- User-provided timeout is clamped to INNER_FETCH_TIMEOUT
- research_fetch receives the clamped timeout
- Outer asyncio.wait_for provides fallback cancellation

## Implementation Details

### Before (Vulnerable)
```
asyncio.wait_for(60s)
  └─ loop.run_in_executor(
       └─ research_fetch(..., timeout=None)  # NO INNER TIMEOUT
  
Timeout fires after 60s → task cancelled → thread still running (LEAK!)
```

### After (Fixed)
```
asyncio.wait_for(60s)  ← Outer guard (never fires if inner works)
  └─ loop.run_in_executor(
       └─ research_fetch(..., timeout=20s)  # INNER TIMEOUT ENFORCED
  
Timeout fires after 20s → thread exits cleanly (NO LEAK!)
```

## Code Quality

- ✓ Type hints preserved (Mypy strict mode compatible)
- ✓ Ruff linting passes
- ✓ No breaking changes to API
- ✓ Backward compatible (timeout parameter optional)
- ✓ All existing tests pass

## Files Modified

- `/src/loom/tools/spider.py` (53 lines added/modified, comprehensive timeout hierarchy)

## References

- **Python docs**: asyncio.wait_for() and loop.run_in_executor()
- **Issue**: Thread pool exhaustion from orphaned executor threads
- **Preventive measure**: Enforced timeout hierarchy prevents resource leaks
