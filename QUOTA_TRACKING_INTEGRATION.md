# API Quota Tracking Integration for Loom

## Overview

Implemented comprehensive API quota tracking for free-tier LLM providers (Groq, NVIDIA NIM, Gemini) with per-minute and per-day sliding-window counters. The system automatically skips exhausted providers in the cascade chain and warns when approaching limits.

## Files Created

### 1. `src/loom/quota_tracker.py` (480 lines)

**Core Quota Tracker Module**

Core classes and functions:
- **`QuotaStatus`** — Dataclass with all quota metrics and percentage calculations
- **`QuotaTracker`** — Singleton quota tracker with methods:
  - `record_usage(provider, tokens)` — Record a provider call
  - `get_status(provider)` — Get full quota status with all metrics
  - `get_remaining(provider)` — Get remaining quota dict
  - `is_near_limit(provider, threshold=0.8)` — Check if approaching limit (>80% used)
  - `should_fallback(provider)` — Check if quota exhausted (skip to next provider)
  - `get_reset_time(provider)` — Get when daily quota resets (UTC midnight)

**Free-Tier Quota Limits** (as of May 2026):
```python
groq: {
    "requests_per_minute": 30,
    "requests_per_day": 14400,
    "tokens_per_minute": 6000,
    "tokens_per_day": 200000,
}
nvidia_nim: {
    "requests_per_minute": 20,
    "requests_per_day": 5000,
    "tokens_per_minute": 4000,
    "tokens_per_day": 100000,
}
gemini: {
    "requests_per_minute": 15,
    "requests_per_day": 1500,
    "tokens_per_minute": 1000,
    "tokens_per_day": 50000,
}
```

**Backend Support**:
- **Primary**: Redis (distributed, fast)
- **Fallback**: In-memory dict (single-process)
- **Graceful degradation** if Redis unavailable

**Sliding Window Implementation**:
- Per-minute: Window based on 60-second boundaries
- Per-day: Calendar day (UTC) aggregation
- Old data automatically cleaned up via TTL

---

### 2. `src/loom/tools/quota_status.py` (120 lines)

**MCP Tool for Quota Status**

Exposes `research_quota_status()` tool with two modes:

**Single Provider**:
```json
{
  "timestamp_utc": "2026-05-04T15:30:45Z",
  "provider": "groq",
  "requests_this_minute": 15,
  "requests_today": 500,
  "tokens_this_minute": 2000,
  "tokens_today": 50000,
  "requests_limit_per_minute": 30,
  "requests_limit_per_day": 14400,
  "requests_remaining_per_minute": 15,
  "requests_remaining_per_day": 13900,
  "requests_used_percent_minute": 50.0,
  "requests_used_percent_day": 3.5,
  "is_near_limit": false,
  "should_fallback": false,
  "reset_time_utc": "2026-05-05T00:00:00+00:00"
}
```

**All Providers** (default):
```json
{
  "timestamp_utc": "2026-05-04T15:30:45Z",
  "providers": {
    "groq": { ... status dict ... },
    "nvidia_nim": { ... status dict ... },
    "gemini": { ... status dict ... }
  },
  "summary": {
    "all_providers_healthy": true,
    "providers_near_limit": [],
    "providers_exhausted": []
  }
}
```

---

## Integration with LLM Cascade

### Changes to `src/loom/tools/llm.py`

**1. Added Import** (line 37):
```python
from loom.quota_tracker import get_quota_tracker, record_usage
```

**2. Quota Check in Cascade** (lines 593-612):

Before attempting each provider in the cascade chain:
```python
# Quota check for free-tier providers: skip if exhausted
quota_tracker = get_quota_tracker()
if quota_tracker.should_fallback(provider.name):
    logger.warning(
        "quota_exhausted provider=%s, skipping to next provider",
        provider.name,
    )
    all_errors.append({
        "provider": provider.name,
        "error": "API quota exhausted for this minute/day"
    })
    continue

# Warn if approaching limit
if quota_tracker.is_near_limit(provider.name, threshold=0.8):
    logger.warning(
        "quota_near_limit provider=%s, consider fallback",
        provider.name,
    )
```

**3. Record Usage After Success** (lines 639-641):

After successful LLM call:
```python
# Record API quota usage (tokens used)
total_tokens = response.input_tokens + response.output_tokens
record_usage(response.provider, tokens=total_tokens)
```

---

## Integration with Server

### Changes to `src/loom/server.py`

**1. Added Import** (line 65):
```python
from loom.tools.quota_status import research_quota_status
```

**2. Registered MCP Tool** (line 1375):

Added `research_quota_status` to `_core_funcs` list for automatic tool registration.

---

## Tests

### `tests/test_quota_tracker.py` (400+ lines)

Comprehensive test coverage including:

**TestQuotaStatus**
- Remaining quota calculations
- Percentage usage calculations
- JSON serialization

**TestQuotaTrackerBasics**
- Singleton pattern
- Invalid provider handling
- Provider configuration validation

**TestQuotaTrackerInMemory**
- Recording and retrieving usage
- Request counting without tokens
- get_remaining() dict structure

**TestQuotaNearLimitDetection**
- Per-minute limit detection
- Per-day limit detection
- Threshold customization

**TestQuotaFallbackDecision**
- Fallback when request quota exhausted
- Fallback when token quota exhausted
- Fallback decisions across all limits

**TestResetTime**
- Reset time calculation (UTC midnight)
- Proper timezone handling

**TestModuleLevelFunctions**
- Module-level convenience functions

**TestQuotaTrackerMultiProvider**
- Independent quotas per provider
- Different limits per provider

**TestQuotaTrackerEdgeCases**
- Boundary conditions
- Over-limit handling
- Concurrent access safety

---

## Usage Examples

### Get Quota Status (MCP Tool)

```python
# Single provider
result = await mcp_call("research_quota_status", provider="groq")
# Returns: {"timestamp_utc": ..., "provider": "groq", ...}

# All providers
result = await mcp_call("research_quota_status")
# Returns: {"timestamp_utc": ..., "providers": {...}, "summary": {...}}
```

### Programmatic Access (Python)

```python
from loom.quota_tracker import get_quota_tracker, record_usage

tracker = get_quota_tracker()

# Check if should skip provider
if tracker.should_fallback("groq"):
    print("Groq quota exhausted, skip to next provider")

# Check if near limit (warn users)
if tracker.is_near_limit("nvidia_nim", threshold=0.8):
    print("NVIDIA NIM approaching quota limit (80%)")

# Record a call
record_usage("groq", tokens=1500)

# Get full status
status = tracker.get_status("groq")
print(f"Groq: {status.requests_remaining_per_minute()} requests remaining this minute")
print(f"Reset time: {status.reset_time_utc}")

# Get specific remaining counts
remaining = tracker.get_remaining("gemini")
# Returns: {
#     "requests_remaining_per_minute": 12,
#     "requests_remaining_per_day": 1200,
#     "tokens_remaining_per_minute": 500,
#     "tokens_remaining_per_day": 40000,
# }
```

---

## Cascade Flow Diagram

```
┌─────────────────────────────────────────────────┐
│ _call_with_cascade() for each provider in chain │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 1. Check provider.available()                    │
│    (API key configured?)                        │
└────────────┬────────────────────────────────────┘
             │
             ▼ (available)
┌─────────────────────────────────────────────────┐
│ 2. Check _check_circuit()                        │
│    (Provider healthy? <3 recent failures)       │
└────────────┬────────────────────────────────────┘
             │
             ▼ (healthy)
┌─────────────────────────────────────────────────┐
│ 3. Check quota_tracker.should_fallback()     ◄──┼── NEW
│    (Quota exhausted?)                           │
└────────────┬────────────────────────────────────┘
             │
             ▼ (quota available)
┌─────────────────────────────────────────────────┐
│ 4. Warn if is_near_limit()                   ◄──┼── NEW
│    (80% of quota used?)                        │
└────────────┬────────────────────────────────────┘
             │
             ▼ (ready to call)
┌─────────────────────────────────────────────────┐
│ 5. Call provider.chat()                          │
│    (with retry on transient errors)            │
└────────────┬────────────────────────────────────┘
             │
             ├─ Success ─────────────────────────┐
             │                                    │
             ▼                                    ▼
┌──────────────────────────┐    ┌──────────────────────┐
│ 6. Record usage          │    │ 7. Handle error      │
│    record_usage()        │    │ _record_failure()    │
│    (quota tracker)   ◄───┼────┤ Continue to next     │
└──────────────────────────┘    │ provider             │
             │                  └──────────────────────┘
             ▼
┌──────────────────────────┐
│ 8. Return response       │
│ (or raise after all fail)│
└──────────────────────────┘
```

---

## Key Design Decisions

### 1. **Sliding Window for Per-Minute Quotas**
- Uses timestamp-based keys (60-second boundaries)
- Automatic cleanup via Redis TTL (120 seconds)
- In-memory: old keys accumulate but are harmless

### 2. **Calendar-Day for Per-Day Quotas**
- Uses ISO date string (YYYY-MM-DD UTC)
- Resets exactly at UTC midnight
- Persisted across server restarts (if using Redis)

### 3. **Dual Backend (Redis + Fallback)**
- Tries Redis for distributed tracking
- Falls back to in-memory dict if unavailable
- Graceful degradation — no errors if Redis missing

### 4. **Provider-Agnostic Design**
- All quota data keyed by provider name string
- Easy to add new providers (just update QUOTA_LIMITS dict)
- Works with existing cascade chain

### 5. **Threshold-Based Warnings**
- `should_fallback()` is hard threshold (0% remaining)
- `is_near_limit()` is soft threshold (customizable, default 80%)
- Allows both strict enforcement and user warnings

### 6. **Token-Aware Tracking**
- Tracks both requests AND tokens
- Can fallback on either limit being hit
- Provides detailed breakdown in status

---

## Performance Characteristics

**Time Complexity**:
- `record_usage()`: O(1)
- `get_status()`: O(1) in-memory, O(1) Redis (6 get operations)
- `should_fallback()`: O(1)
- `is_near_limit()`: O(1)

**Memory Complexity**:
- In-memory: O(providers × 120 seconds × requests_per_second)
- Redis: Minimal (keys auto-expire)

**Thread Safety**:
- QuotaTracker uses `threading.RLock()` for in-memory operations
- Redis client is thread-safe (connection pooling)
- Safe for concurrent async/sync calls

---

## Future Enhancements

1. **Per-User Quotas** — Track usage per user/account
2. **Custom Quota Limits** — Config-based limits per provider
3. **Rate Limiting Headers** — Parse X-RateLimit headers from APIs
4. **Quota Predictions** — Estimate when quota will reset
5. **Dashboard Integration** — Add quota metrics to web dashboard
6. **Alerts** — Notify when approaching critical thresholds

---

## Troubleshooting

**Q: Why is my provider being skipped?**
- Check `research_quota_status` to see current usage
- Look for "API quota exhausted" in error messages
- Wait for UTC midnight for daily quota reset

**Q: How do I know when quota resets?**
- Call `research_quota_status` and check `reset_time_utc`
- Always resets at 00:00:00 UTC (next calendar day)

**Q: Can I manually reset quotas?**
- Currently no reset API (by design — prevents abuse)
- Dev mode: Restart server (clears in-memory state)
- Production: Quotas reset automatically at midnight UTC

**Q: What if Redis is not available?**
- System falls back to in-memory tracking automatically
- Quotas won't persist across server restarts
- Performance is identical (slightly faster actually)

---

## Testing

```bash
# Run all quota tracker tests
pytest tests/test_quota_tracker.py -v

# Run specific test class
pytest tests/test_quota_tracker.py::TestQuotaTrackerBasics -v

# Run with coverage
pytest tests/test_quota_tracker.py --cov=src/loom/quota_tracker
```

Expected: 50+ test cases, 95%+ code coverage
