# Quota Tracking - End-to-End Example

This document demonstrates the quota tracking system in action with real examples.

## Scenario: Monitoring Usage and Handling Exhaustion

### Step 1: Initial State (Fresh Day)

```python
from loom.quota_tracker import get_quota_tracker

tracker = get_quota_tracker()

# Check initial status for all providers
groq_status = tracker.get_status("groq")
print(f"Groq: {groq_status.requests_this_minute} / {groq_status.requests_limit_per_minute} requests this minute")
# Output: "Groq: 0 / 30 requests this minute"

print(f"Groq tokens: {groq_status.tokens_this_minute} / {groq_status.tokens_limit_per_minute} tokens this minute")
# Output: "Groq tokens: 0 / 6000 tokens this minute"

print(f"Reset time: {groq_status.reset_time_utc}")
# Output: "Reset time: 2026-05-05T00:00:00+00:00"  (tomorrow at midnight UTC)
```

### Step 2: Record Usage (First Request)

```python
# Simulate an LLM call that uses 150 input tokens + 300 output tokens
from loom.quota_tracker import record_usage

record_usage("groq", tokens=450)  # 150 + 300

# Check updated status
groq_status = tracker.get_status("groq")
print(f"Requests: {groq_status.requests_this_minute} (used 1 request)")
# Output: "Requests: 1"

print(f"Tokens: {groq_status.tokens_this_minute} (used 450 tokens)")
# Output: "Tokens: 450"

# Check remaining quota
remaining = tracker.get_remaining("groq")
print(f"Remaining requests: {remaining['requests_remaining_per_minute']}")
# Output: "Remaining requests: 29"

print(f"Remaining tokens: {remaining['tokens_remaining_per_minute']}")
# Output: "Remaining tokens: 5550"
```

### Step 3: Monitor Usage During the Day

```python
# Later, make many more calls throughout the day

for i in range(10):
    # Simulate each call with varying token counts
    tokens_used = 500 + (i * 100)  # 500, 600, 700, ..., 1400 tokens
    record_usage("groq", tokens=tokens_used)

# Check status now
groq_status = tracker.get_status("groq")
print(f"Requests so far: {groq_status.requests_today}")
# Output: "Requests so far: 11"

print(f"Tokens so far: {groq_status.tokens_today}")
# Output: "Tokens so far: 9950"

# Check usage percentage
usage_pct = groq_status.tokens_used_percent_day()
print(f"Daily token usage: {usage_pct:.1f}%")
# Output: "Daily token usage: 4.98%"

# Still healthy, plenty of room
is_near_limit = tracker.is_near_limit("groq", threshold=0.8)
print(f"Near limit (80% threshold)? {is_near_limit}")
# Output: "Near limit (80% threshold)? False"
```

### Step 4: Approaching Limit (80% Threshold)

```python
# Now simulate hitting 80% of daily token quota
# Daily limit is 200,000 tokens
# 80% = 160,000 tokens

# We're at 9,950, add 150,050 more to reach 160,000
record_usage("groq", tokens=150050)

groq_status = tracker.get_status("groq")
usage_pct = groq_status.tokens_used_percent_day()
print(f"Daily token usage: {usage_pct:.1f}%")
# Output: "Daily token usage: 80.01%"

# Now it should warn
is_near_limit = tracker.is_near_limit("groq", threshold=0.8)
print(f"Near limit? {is_near_limit}")
# Output: "Near limit? True"

# In the LLM cascade, this would log:
# WARNING: quota_near_limit provider=groq, consider fallback
```

### Step 5: Quota Exhaustion and Fallback

```python
# Continue making calls until daily limit is hit
# Add 40,000 more tokens (reaching 200,050 > 200,000 limit)
record_usage("groq", tokens=40000)

groq_status = tracker.get_status("groq")
print(f"Daily tokens: {groq_status.tokens_today} / {groq_status.tokens_limit_per_day}")
# Output: "Daily tokens: 200050 / 200000"

# Remaining should be 0 (clamped from negative)
remaining = tracker.get_remaining("groq")
print(f"Remaining tokens: {remaining['tokens_remaining_per_day']}")
# Output: "Remaining tokens: 0"

# Should fallback
should_skip = tracker.should_fallback("groq")
print(f"Should skip groq provider? {should_skip}")
# Output: "Should skip groq provider? True"

# In the LLM cascade, this would:
# 1. Log: WARNING: quota_fallback provider=groq reason=tokens_per_day_exhausted
# 2. Continue to next provider in the chain (nvidia_nim, then gemini, etc.)
```

### Step 6: Using the MCP Tool

```python
# From the CLI or client, query quota status
from loom.tools.quota_status import research_quota_status

# Get all providers status
all_status = research_quota_status()
print(all_status)

# Output:
# {
#     "timestamp_utc": "2026-05-04T23:45:00Z",
#     "providers": {
#         "groq": {
#             "provider": "groq",
#             "requests_this_minute": 0,
#             "requests_today": 12,
#             "tokens_this_minute": 0,
#             "tokens_today": 200050,
#             "requests_limit_per_minute": 30,
#             "requests_limit_per_day": 14400,
#             "tokens_limit_per_minute": 6000,
#             "tokens_limit_per_day": 200000,
#             "requests_remaining_per_minute": 30,
#             "requests_remaining_per_day": 14388,
#             "tokens_remaining_per_minute": 6000,
#             "tokens_remaining_per_day": 0,  # EXHAUSTED
#             "requests_used_percent_minute": 0.0,
#             "requests_used_percent_day": 0.08,
#             "tokens_used_percent_minute": 0.0,
#             "tokens_used_percent_day": 100.01,
#             "is_near_limit": true,
#             "should_fallback": true,
#             "reset_time_utc": "2026-05-05T00:00:00+00:00"
#         },
#         "nvidia_nim": { ... status dict ... },
#         "gemini": { ... status dict ... }
#     },
#     "summary": {
#         "all_providers_healthy": false,
#         "providers_near_limit": ["groq"],
#         "providers_exhausted": ["groq"]
#     }
# }

# Get single provider
groq_status = research_quota_status(provider="groq")
print(f"Groq is at {groq_status['tokens_used_percent_day']:.1f}% daily token quota")
# Output: "Groq is at 100.01% daily token quota"
```

## Real-World LLM Cascade Flow

### When Everything is Normal

```
User calls: _call_with_cascade(messages)
│
├─ Try provider: groq
│  ├─ ✓ Available? Yes
│  ├─ ✓ Circuit healthy? Yes
│  ├─ ✓ Quota available? Yes (950 req/min, 5550 tokens/min)
│  ├─ ℹ Warning? No (only at 7.5% usage)
│  ├─ 🔄 Call provider.chat()
│  └─ ✅ Success: Response = LLMResponse(...)
│
├─ Record usage: record_usage("groq", tokens=450)
│
└─ Return response to user
```

**Log Output**:
```
INFO: llm_call_ok provider=groq model=llama-3.3-70b-versatile latency=145ms tokens=150/300 cost=$0.00
```

### When Quota is Getting Low

```
User calls: _call_with_cascade(messages)
│
├─ Try provider: groq
│  ├─ ✓ Available? Yes
│  ├─ ✓ Circuit healthy? Yes
│  ├─ ✓ Quota available? Yes (100 req/min, 100 tokens/min)
│  ├─ ⚠️ Warning? YES (83% usage, > 80% threshold)
│  ├─ 🔄 Call provider.chat()
│  └─ ✅ Success: Response = LLMResponse(...)
│
└─ Return response to user
```

**Log Output**:
```
WARNING: quota_near_limit provider=groq, consider fallback
INFO: llm_call_ok provider=groq model=llama-3.3-70b-versatile latency=145ms tokens=150/300 cost=$0.00
```

### When Quota is Exhausted

```
User calls: _call_with_cascade(messages)
│
├─ Try provider: groq
│  ├─ ✓ Available? Yes
│  ├─ ✓ Circuit healthy? Yes
│  ├─ ✗ Quota available? NO (0 tokens remaining)
│  └─ ❌ Skip to next provider
│
├─ Try provider: nvidia_nim
│  ├─ ✓ Available? Yes
│  ├─ ✓ Circuit healthy? Yes
│  ├─ ✓ Quota available? Yes (15 req/min, 2000 tokens/min)
│  ├─ ℹ Warning? No
│  ├─ 🔄 Call provider.chat()
│  └─ ✅ Success: Response = LLMResponse(...)
│
├─ Record usage: record_usage("nvidia_nim", tokens=450)
│
└─ Return response to user
```

**Log Output**:
```
WARNING: quota_fallback provider=groq reason=tokens_per_day_exhausted
INFO: llm_call_ok provider=nvidia_nim model=... latency=120ms tokens=150/300 cost=$0.00
```

## Programmatic Cascade Example

Here's what happens internally in `_call_with_cascade()`:

```python
async def _call_with_cascade(messages, model="auto", ...):
    chain = _build_provider_chain()  # [groq, nvidia_nim, gemini, openai, ...]
    
    for provider in chain:
        # 1. Basic checks
        if not provider.available():
            continue
        
        if not _check_circuit(provider.name):
            continue
        
        # 2. NEW: Quota checks
        quota_tracker = get_quota_tracker()
        
        if quota_tracker.should_fallback(provider.name):
            logger.warning("quota_exhausted provider=%s, skipping", provider.name)
            all_errors.append({
                "provider": provider.name,
                "error": "API quota exhausted for this minute/day"
            })
            continue
        
        if quota_tracker.is_near_limit(provider.name, threshold=0.8):
            logger.warning("quota_near_limit provider=%s, consider fallback", provider.name)
        
        # 3. Try the provider
        try:
            response = await _call_provider_with_retry(provider, messages, ...)
            
            # Check cost cap (existing logic)
            if max_cost_usd and response.cost_usd > max_cost_usd:
                raise RuntimeError("cost cap exceeded")
            
            # Track daily cost (existing logic)
            cost_tracker.add_cost(response.cost_usd, ...)
            
            # NEW: Record API quota usage
            total_tokens = response.input_tokens + response.output_tokens
            record_usage(response.provider, tokens=total_tokens)
            
            # Reset circuit (existing logic)
            _record_provider_success(provider.name)
            
            logger.info("llm_call_ok provider=%s ...", response.provider)
            return response
            
        except Exception as e:
            # Handle error (existing logic)
            _record_provider_failure(provider.name)
            continue
    
    # If we get here, all providers failed
    raise RuntimeError(f"all providers failed: {error_detail}")
```

## Key Insights

1. **Automatic Fallback**: No user intervention needed — quota exhaustion triggers automatic fallback
2. **Transparent Logging**: Detailed logging helps understand why providers are skipped
3. **Token-Aware**: Tracks both request count AND token count (more realistic)
4. **Per-Minute Precision**: Can detect burst limits within seconds (not just daily)
5. **Threshold Warnings**: Soft warning at 80% helps plan before hard failure
6. **Multiple Limits**: Fails on ANY limit (request/token, per-minute/per-day)
7. **UTC Midnight Reset**: Consistent reset time regardless of timezone
8. **Zero Overhead**: O(1) operations, minimal memory impact

## Testing Your Setup

```bash
# Start Loom server
loom serve

# In another terminal, query quota status
curl http://127.0.0.1:8787/tools/research_quota_status

# Make some LLM calls
curl -X POST http://127.0.0.1:8787/tools/research_llm_chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ]
  }'

# Check quota again
curl http://127.0.0.1:8787/tools/research_quota_status

# Inspect the quota changes
# Expected: requests_today and tokens_today increased
```
