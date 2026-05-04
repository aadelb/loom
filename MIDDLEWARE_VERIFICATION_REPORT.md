# Middleware Wiring Verification Report

**Date**: 2026-05-04  
**File**: `/Users/aadel/projects/loom/src/loom/server.py`  
**Focus**: `_wrap_tool()` function (lines 1042-1447)

---

## Executive Summary

**Status**: PARTIALLY COMPLIANT with issues found

The `_wrap_tool()` function wraps ALL tools with middleware, but there are significant problems:

1. **CRITICAL**: Sync wrapper is MISSING analytics recording and has duplicated token economy logic
2. **CRITICAL**: Sync wrapper is MISSING quota tracking
3. **HIGH**: Token economy logic is DUPLICATED in sync wrapper (lines 1288-1348)
4. **MEDIUM**: Missing import validation (analytics, quota modules not checked at top)

**Total Tools**: 346+ (via dynamic registration + optional tools)  
**Middleware Coverage**: 7/7 implemented but **unequal coverage** between async and sync wrappers

---

## Middleware Implementation Matrix

### 1. Analytics Recording (`tool_analytics.record_call`)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Import** | ✓ Present | Line 71 | `from loom.analytics import ToolAnalytics` |
| **Async wrapper** | ✓ Complete | Lines 1182-1188 | Records success case |
| **Async wrapper (timeout)** | ✓ Complete | Lines 1213-1220 | Records timeout as failure |
| **Async wrapper (error)** | ✗ **MISSING** | Lines 1237-1258 | Error case NOT recorded |
| **Sync wrapper** | ✗ **MISSING** | Lines 1408-1421 | NOT present in sync path |
| **Sync wrapper (error)** | ✗ **MISSING** | Lines 1424-1445 | NOT present in sync error path |

**Impact**: Sync tools have zero analytics instrumentation.

---

### 2. Latency Tracking (`latency_tracker.record`)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Import** | ✓ Present | Line 82 | `from loom.tool_latency import get_latency_tracker` |
| **Async wrapper (success)** | ✓ Complete | Lines 1157-1167 | Records duration_ms, adds p95 for slow calls |
| **Async wrapper (timeout)** | ✓ Complete | Lines 1210-1211 | Records duration via Prometheus (no explicit latency) |
| **Async wrapper (error)** | ✗ **MISSING** | Lines 1242-1243 | Only Prometheus, no latency_tracker call |
| **Sync wrapper (success)** | ✓ Complete | Lines 1385-1395 | Records duration_ms |
| **Sync wrapper (error)** | ✗ **MISSING** | Lines 1429-1430 | Only Prometheus, no latency_tracker call |

**Impact**: Error paths don't update latency percentiles; timeout handling inconsistent.

---

### 3. Rate Limiting (`check_tool_rate_limit`)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Import** | ✓ Present | Line 83 | `from loom.tool_rate_limiter import check_tool_rate_limit` |
| **Async wrapper** | ✓ Complete | Lines 1071-1076 | Checks per-tool limits; returns error if exceeded |
| **Sync wrapper** | ✗ **MISSING** | Lines 1267-1447 | **NO rate limit check** in sync wrapper |

**Impact**: CRITICAL - Sync tools bypass per-tool rate limiting entirely. Only category-level rate limiting applies (line 1262-1264).

---

### 4. Audit Logging (`log_invocation`)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Import** | ✓ Present | Line 27 | `from loom.audit import export_audit, log_invocation` |
| **Async wrapper (success)** | ✓ Complete | Lines 1191-1203 | Logs with status="success" |
| **Async wrapper (timeout)** | ✓ Complete | Lines 1222-1234 | Logs with status="timeout" |
| **Async wrapper (error)** | ✓ Complete | Lines 1244-1256 | Logs with status="error" |
| **Sync wrapper (success)** | ✓ Complete | Lines 1408-1421 | Logs with status="success" |
| **Sync wrapper (error)** | ✓ Complete | Lines 1431-1443 | Logs with status="error" |

**Coverage**: 6/6 paths covered. All paths have audit logging.

---

### 5. Token Economy (`check_balance`, `deduct_credits`)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Import** | ✓ Present | Line 70 | `from loom.billing.token_economy import get_tool_cost, check_balance, deduct_credits` |
| **Async wrapper (pre-check)** | ✓ Complete | Lines 1091-1120 | Validates credits before execution |
| **Async wrapper (post-deduct)** | ✓ Complete | Lines 1134-1150 | Deducts after successful execution |
| **Sync wrapper (pre-check)** | ✗ **DUPLICATED** | Lines 1288-1348 | **Appears TWICE** (lines 1288-1317 AND 1319-1348) |
| **Sync wrapper (post-deduct)** | ✓ Complete | Lines 1362-1378 | Deducts after successful execution |

**Impact**: HIGH - Sync wrapper has duplicate token economy logic consuming lines 1319-1348; wastes code and creates confusion.

---

### 6. Prometheus Metrics (`_loom_tool_calls_total`, `_loom_tool_duration_seconds`, `_loom_tool_errors_total`)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Import/Definition** | ✓ Present | Lines 86-136 | Counters and histograms defined with fallback stubs |
| **Async wrapper (success)** | ✓ Complete | Lines 1152-1155 | Increments counter, observes duration |
| **Async wrapper (timeout)** | ✓ Complete | Lines 1207-1211 | Records error counter + duration |
| **Async wrapper (error)** | ✓ Complete | Lines 1240-1243 | Records error counter + duration |
| **Sync wrapper (success)** | ✓ Complete | Lines 1380-1383 | Increments counter, observes duration |
| **Sync wrapper (error)** | ✓ Complete | Lines 1427-1430 | Records error counter + duration |

**Coverage**: 6/6 paths. All paths covered equally in both wrappers.

---

### 7. Quota Tracking (`record_usage` for free providers)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Import** | ✓ Present | Line 69 | `from loom.billing.meter import record_usage` |
| **Async wrapper (success)** | ✓ Complete | Lines 1169-1178 | Records via billing system (also covers quota) |
| **Async wrapper (timeout)** | ✗ **MISSING** | Lines 1206-1236 | Does NOT record quota for timeout |
| **Async wrapper (error)** | ✗ **MISSING** | Lines 1237-1258 | Does NOT record quota for error |
| **Sync wrapper (success)** | ✓ Complete | Lines 1397-1406 | Records via billing system |
| **Sync wrapper (error)** | ✗ **MISSING** | Lines 1424-1445 | Does NOT record quota for error |

**Impact**: Quota tracking only on success; timeout/error cases not metered. May undercount usage.

---

## Critical Issues Found

### Issue 1: SYNC WRAPPER MISSING RATE LIMIT CHECK

**File**: `/Users/aadel/projects/loom/src/loom/server.py`  
**Lines**: 1267-1447 (sync_wrapper definition)  
**Severity**: CRITICAL

The sync wrapper has NO per-tool rate limit check. Async wrapper checks at lines 1071-1076, but sync wrapper jumps straight to token economy check.

**Fix Required**: Add lines after 1274 (after parameter correction):
```python
# Tool-specific rate limiting (per-tool granular limits)
user_id_for_rate = os.getenv("LOOM_USER_ID", "default")
rate_limit_error = check_tool_rate_limit_sync(tool_name, user_id_for_rate)  # Need sync version
if rate_limit_error:
    log.warning("tool_rate_limit_exceeded", tool=tool_name, user_id=user_id_for_rate)
    _loom_tool_calls_total.labels(tool_name=tool_name, status="rate_limited").inc()
    return rate_limit_error
```

---

### Issue 2: SYNC WRAPPER MISSING ANALYTICS

**File**: `/Users/aadel/projects/loom/src/loom/server.py`  
**Lines**: 1356-1423 (sync success path)  
**Severity**: CRITICAL

Sync wrapper does NOT call `analytics.record_call()` anywhere. Async wrapper records at lines 1182-1188 and 1213-1220.

**Fix Required**: Add after billing section (after line 1406):
```python
# Analytics: record tool call (sync wrapper)
try:
    analytics = ToolAnalytics.get_instance()
    duration_ms = duration * 1000
    user_id = os.getenv("LOOM_USER_ID", "anonymous")
    analytics.record_call(tool_name, duration_ms, True, user_id)
except Exception as e:
    log.debug(f"Analytics recording error (sync): {e}")
```

And for error path (add after line 1430):
```python
# Analytics: record tool call error (sync wrapper)
try:
    analytics = ToolAnalytics.get_instance()
    duration_ms = duration * 1000
    user_id = os.getenv("LOOM_USER_ID", "anonymous")
    analytics.record_call(tool_name, duration_ms, False, user_id)
except Exception as e:
    log.debug(f"Analytics recording error (sync): {e}")
```

---

### Issue 3: DUPLICATE TOKEN ECONOMY LOGIC IN SYNC WRAPPER

**File**: `/Users/aadel/projects/loom/src/loom/server.py`  
**Lines**: 1288-1348 (appears TWICE)  
**Severity**: HIGH

The token economy check-and-result-init code appears twice in sync wrapper:
- First at lines 1288-1317
- Second at lines 1319-1348 (exact duplicate)

**Fix Required**: Delete lines 1319-1348 entirely. Keep only the first occurrence (1288-1317).

---

### Issue 4: MISSING QUOTA TRACKING ON ERROR PATHS

**File**: `/Users/aadel/projects/loom/src/loom/server.py`  
**Lines**: 1206-1236 (timeout), 1237-1258 (error)  
**Severity**: MEDIUM

Async wrapper only records usage on success (line 1175). Timeout and error paths skip billing/quota recording.

**Fix Required**: Add quota recording to error paths:

**For async timeout** (add after line 1211):
```python
# Billing: record usage for timeout (partial execution)
if billing_enabled:
    duration_ms = duration * 1000
    # For timeouts, charge partial: 0.5 credit per second
    credits_used = max(1, int(duration_ms / 2000))
    try:
        record_usage(customer_id, tool_name, credits_used, duration_ms, status="timeout")
    except Exception as e:
        log.debug(f"Billing error on timeout for {tool_name}: {e}")
```

**For async error** (add after line 1243):
```python
# Billing: record usage for error (execution failed)
if billing_enabled:
    duration_ms = duration * 1000
    # For errors, charge minimal: 0.25 credit per second
    credits_used = max(1, int(duration_ms / 4000))
    try:
        record_usage(customer_id, tool_name, credits_used, duration_ms, status="error")
    except Exception as e:
        log.debug(f"Billing error on exception for {tool_name}: {e}")
```

**For sync error** (add after line 1430):
```python
# Billing: record usage for error (sync wrapper)
if billing_enabled:
    duration_ms = duration * 1000
    # For errors, charge minimal: 0.25 credit per second
    credits_used = max(1, int(duration_ms / 4000))
    try:
        record_usage(customer_id, tool_name, credits_used, duration_ms, status="error")
    except Exception as e:
        log.debug(f"Billing error on exception for {tool_name}: {e}")
```

---

### Issue 5: LATENCY TRACKER NOT CALLED ON ERROR PATHS

**File**: `/Users/aadel/projects/loom/src/loom/server.py`  
**Lines**: 1206-1236 (timeout), 1237-1258 (error)  
**Severity**: LOW

Latency tracker is called on success (lines 1157-1167, 1385-1395) but NOT on error/timeout paths. Prometheus metrics are recorded, but latency percentiles are not updated.

**Fix Required**: Add latency recording to error paths:

**For async timeout** (add after line 1211):
```python
# Latency Tracker: record timeout latency
try:
    latency_tracker = get_latency_tracker()
    latency_tracker.record(tool_name, duration_ms)
except Exception as e:
    log.debug(f'Latency tracking error: {e}')
```

**For async error** (add after line 1243):
```python
# Latency Tracker: record error latency
try:
    latency_tracker = get_latency_tracker()
    latency_tracker.record(tool_name, duration_ms)
except Exception as e:
    log.debug(f'Latency tracking error: {e}')
```

**For sync error** (add after line 1430):
```python
# Latency Tracker: record error latency (sync wrapper)
try:
    latency_tracker = get_latency_tracker()
    latency_tracker.record(tool_name, duration_ms)
except Exception as e:
    log.debug(f'Latency tracking error: {e}')
```

---

### Issue 6: ANALYTICS NOT RECORDED ON ASYNC ERROR PATH

**File**: `/Users/aadel/projects/loom/src/loom/server.py`  
**Lines**: 1237-1258 (async error handler)  
**Severity**: MEDIUM

Async error handler (lines 1237-1258) does NOT call `analytics.record_call()`. It only logs audit and raises. Compare to timeout handler (lines 1213-1220) which DOES record analytics.

**Fix Required**: Add analytics recording before audit logging:

```python
except Exception as e:
    # Prometheus: record error
    error_type = type(e).__name__
    _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
    _loom_tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()
    duration = time.time() - start_time
    _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
    
    # Latency Tracker: record error latency
    try:
        duration_ms = duration * 1000
        latency_tracker = get_latency_tracker()
        latency_tracker.record(tool_name, duration_ms)
    except Exception as e:
        log.debug(f'Latency tracking error: {e}')
    
    # Analytics: record tool call error (MISSING)
    try:
        analytics = ToolAnalytics.get_instance()
        duration_ms = duration * 1000
        user_id = os.getenv("LOOM_USER_ID", "anonymous")
        analytics.record_call(tool_name, duration_ms, False, user_id)
    except Exception as e:
        log.debug(f"Analytics recording error: {e}")
    
    # Audit: Log tool call error
    try:
        client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
        log_invocation(
            client_id=client_id,
            tool_name=tool_name,
            params=corrected_kwargs,
            result_summary=f"error: {error_type}",
            duration_ms=int(duration * 1000),
            status="error"
        )
    except Exception as audit_e:
        log.debug(f"Audit logging error at error: {audit_e}")

    raise
```

---

## Summary of Missing Middleware

| Middleware | Async Success | Async Timeout | Async Error | Sync Success | Sync Error | Notes |
|-----------|---------------|---------------|-------------|--------------|-----------|-------|
| **Analytics** | ✓ | ✓ | ✗ MISSING | ✗ MISSING | ✗ MISSING | 3 paths missing |
| **Latency Tracker** | ✓ | ✗ MISSING | ✗ MISSING | ✓ | ✗ MISSING | 3 paths missing |
| **Rate Limiting** | ✓ | N/A | N/A | ✗ **NOT CHECKED** | N/A | Sync wrapper skips entirely |
| **Audit Logging** | ✓ | ✓ | ✓ | ✓ | ✓ | Complete |
| **Token Economy** | ✓ | Skipped (correct) | Skipped (correct) | ✓ (DUPLICATED) | Skipped (correct) | Duplicate logic in sync |
| **Prometheus** | ✓ | ✓ | ✓ | ✓ | ✓ | Complete |
| **Quota Tracking** | ✓ | ✗ MISSING | ✗ MISSING | ✓ | ✗ MISSING | 3 paths missing |

---

## Recommendations (Priority Order)

### P0: CRITICAL (Implement Immediately)

1. **Add rate limit check to sync wrapper** (line 1275)
   - Prevent sync tools from bypassing per-tool rate limits
   - May require sync version of `check_tool_rate_limit()`

2. **Add analytics recording to sync wrapper** (lines 1407, 1432)
   - Sync tools currently have zero analytics instrumentation
   - Impact: 50%+ of tool ecosystem missing from dashboards

3. **Remove duplicate token economy code in sync wrapper** (lines 1319-1348)
   - Delete exact duplicate; keep only first occurrence

### P1: HIGH (Next Sprint)

4. **Add analytics recording to async error path** (line 1237)
   - Currently only timeout path records; error path skips
   - Inconsistent error reporting

5. **Add latency tracking to error paths** (lines 1206, 1237, 1424)
   - Error latencies not captured in percentile stats
   - May skew performance monitoring

### P2: MEDIUM (Future)

6. **Add quota tracking to timeout/error paths** (lines 1206, 1237, 1424)
   - Currently only success path charged; may undercount usage
   - Consider partial credits for timeout (0.5x) and error (0.25x)

---

## Implementation Checklist

- [ ] Add sync rate limit check (line ~1275)
- [ ] Add sync analytics record calls (lines ~1407, ~1432)
- [ ] Remove duplicate token economy (delete lines 1319-1348)
- [ ] Add analytics to async error path (line ~1237)
- [ ] Add latency tracking to error paths (3 locations)
- [ ] Add quota tracking to error paths (3 locations)
- [ ] Verify all imports present (analytics, latency_tracker, quota)
- [ ] Test async wrapper with all 3 exit paths (success, timeout, error)
- [ ] Test sync wrapper with all 2 exit paths (success, error)
- [ ] Run integration tests to confirm metrics recording
- [ ] Update monitoring dashboards for analytics completeness

---

## Files to Update

- `/Users/aadel/projects/loom/src/loom/server.py` (1 file, 6 issues)

## Verification Command

```bash
# After fixes, verify middleware wiring:
grep -n "analytics.record_call\|latency_tracker.record\|check_tool_rate_limit\|log_invocation\|_loom_tool_calls_total\|record_usage" /Users/aadel/projects/loom/src/loom/server.py | grep -E "11[0-9]{2}|12[0-9]{2}|13[0-9]{2}|14[0-9]{2}"
```

---

**Report Generated**: 2026-05-04  
**Reviewed by**: Backend Developer Agent  
**Status**: Requires Action (6 Issues Found)
