# Circuit Breaker Pattern for Loom

A lightweight Circuit Breaker implementation for external API calls that prevents cascading failures when providers go down.

## Overview

**Location:** `src/loom/tools/circuit_breaker.py` (77 lines)

**3 MCP Tools:**
1. `research_breaker_status()` — Check circuit state for all providers
2. `research_breaker_trip(provider, error)` — Record a failure
3. `research_breaker_reset(provider="all")` — Manually reset circuit(s)

## How It Works

### States

- **CLOSED** (normal) — All requests pass through
- **OPEN** (failing) — Requests are blocked to prevent cascading failures
- **HALF_OPEN** (testing recovery) — One request allowed to test if service recovered

### Thresholds

- **FAILURE_THRESHOLD = 5** — Circuit opens after 5 consecutive failures
- **COOLDOWN_SECONDS = 60** — Time circuit stays open before attempting HALF_OPEN

### State Transitions

```
CLOSED → [5 failures] → OPEN → [60s cooldown] → HALF_OPEN → [success] → CLOSED
                                                            → [failure] → OPEN
```

## Usage

### Example 1: Monitor Provider Status

```python
import asyncio
from loom.tools.circuit_breaker import research_breaker_status

async def check_providers():
    status = await research_breaker_status()
    for circuit in status["circuits"]:
        print(f"{circuit['provider']}: {circuit['state']} (failures: {circuit['failures']})")

asyncio.run(check_providers())
```

Output:
```
groq: closed (failures: 0)
deepseek: open (failures: 5)
gemini: half_open (failures: 0)
...
```

### Example 2: Record a Provider Failure

```python
from loom.tools.circuit_breaker import research_breaker_trip

async def handle_provider_failure():
    result = await research_breaker_trip("groq", error="Connection timeout")
    if result["tripped"]:
        print(f"⚠️ Circuit OPENED for {result['provider']} after {result['failures']} failures")
    else:
        print(f"Failure recorded: {result['failures']}/{result['threshold']}")
```

### Example 3: Reset a Provider Circuit

```python
from loom.tools.circuit_breaker import research_breaker_reset

async def reset_after_deployment():
    # Reset specific provider
    result = await research_breaker_reset("groq")
    print(f"Reset: {result['reset']}")  # ["groq"]
    
    # Reset all providers
    result = await research_breaker_reset("all")
    print(f"Reset {result['count']} circuits")
```

## Integration with Providers

### LLM Provider Usage

Integrate with LLM cascading logic:

```python
from loom.providers.base import LLMProvider
from loom.tools.circuit_breaker import research_breaker_can_call, research_breaker_trip, research_breaker_mark_success

async def call_llm_with_circuit_breaker(provider_name: str, messages: list) -> str:
    # Check if circuit allows calls
    if not await research_breaker_can_call(provider_name):
        return None  # Skip this provider
    
    try:
        provider = get_provider(provider_name)
        response = await provider.chat(messages)
        # Mark success if we were in HALF_OPEN
        await research_breaker_mark_success(provider_name)
        return response
    except Exception as e:
        # Record the failure
        await research_breaker_trip(provider_name, str(e))
        return None
```

### Search Provider Usage

```python
async def search_with_circuit_breaker(provider_name: str, query: str):
    if not await research_breaker_can_call(provider_name):
        print(f"Circuit OPEN for {provider_name}, skipping")
        return []
    
    try:
        results = await search_provider.search(query)
        await research_breaker_mark_success(provider_name)
        return results
    except Exception as e:
        await research_breaker_trip(provider_name, f"search_failed: {e}")
        return []
```

## Monitored Providers

Circuit breaker tracks these providers:

**LLM Providers:**
- groq, nvidia_nim, deepseek, gemini, moonshot, openai, anthropic, vllm

**Search Providers:**
- exa, tavily, firecrawl, brave, ddgs

## Response Formats

### research_breaker_status()

```json
{
  "circuits": [
    {
      "provider": "groq",
      "state": "closed",
      "failures": 0,
      "last_failure": null,
      "cooldown_remaining_s": 0.0
    },
    {
      "provider": "deepseek",
      "state": "open",
      "failures": 5,
      "last_failure": "2026-05-02T14:30:00+00:00",
      "cooldown_remaining_s": 45.2
    }
  ]
}
```

### research_breaker_trip()

```json
{
  "provider": "groq",
  "state": "closed",
  "failures": 2,
  "threshold": 5,
  "tripped": false,
  "error": "timeout"
}
```

After 5th failure:
```json
{
  "provider": "groq",
  "state": "open",
  "failures": 5,
  "threshold": 5,
  "tripped": true,
  "error": "connection reset"
}
```

### research_breaker_reset()

```json
{
  "reset": ["groq", "deepseek", "gemini"],
  "new_state": "closed",
  "count": 3
}
```

## Testing

Run tests with:

```bash
pytest tests/test_tools/test_circuit_breaker.py -v
```

**Test Coverage:**
- Status reporting for all provider states
- Circuit opening at threshold (5 failures)
- Auto-transition to HALF_OPEN after cooldown
- Manual reset for single/all providers
- Concurrent operation safety
- Full failure→recovery→success cycle

## Thread Safety

All circuit breaker operations use `asyncio.Lock()` for safe concurrent access:
- Multiple tasks can check circuit state simultaneously
- Failure recording is atomic
- State transitions are serialized
