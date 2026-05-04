# Tool Usage Analytics System

Comprehensive tool usage tracking, performance monitoring, and analytics dashboard for Loom MCP server.

## Overview

The analytics system provides real-time insight into:
- Which tools are being used most frequently
- Performance metrics (response times, slow tools)
- Error rates per tool
- Usage trends (hourly, daily)
- Tools never called
- Average response time across all tools

All data is stored in-memory with optional Redis backend for persistence and distributed deployments.

## Architecture

### Components

1. **ToolAnalytics Singleton** (`src/loom/analytics.py`)
   - Core analytics engine with dual-mode storage (Redis or in-memory)
   - Thread-safe recording and querying
   - Supports user attribution and timestamps

2. **Integrated Recording** (`src/loom/server.py`)
   - Automatic tool call recording via `_wrap_tool` wrapper
   - Records both success and error calls
   - Includes execution duration and user ID
   - Integrated with Prometheus metrics

3. **Analytics Dashboard Tool** (`research_analytics_dashboard`)
   - MCP tool for generating comprehensive reports
   - Aggregates all metrics into single endpoint
   - Supports listing unused tools
   - Returns ISO-formatted timestamps

4. **Parameter Models** (`src/loom/params/core.py`)
   - `AnalyticsDashboardParams`: Tool parameter validation

## Usage

### Recording Tool Calls

Automatic recording happens via the `_wrap_tool` wrapper in `server.py`:

```python
# In server.py _wrap_tool async_wrapper (lines ~1013-1020)
# Analytics: record tool call
try:
    analytics = ToolAnalytics.get_instance()
    duration_ms = duration * 1000
    user_id = os.getenv("LOOM_USER_ID", "anonymous")
    analytics.record_call(tool_name, duration_ms, True, user_id)
except Exception as e:
    log.debug(f"Analytics recording error: {e}")
```

All tool executions are automatically tracked without additional instrumentation.

### Querying Analytics

#### Get Top Tools

```python
analytics = ToolAnalytics.get_instance()
top_tools = analytics.get_top_tools(limit=20)

# Returns:
# [
#   {
#     "tool_name": "research_fetch",
#     "call_count": 562,
#     "percentage": 43.8
#   },
#   ...
# ]
```

#### Get Slow Tools

```python
slow_tools = analytics.get_slow_tools(threshold_ms=5000)

# Returns:
# [
#   {
#     "tool_name": "research_deep",
#     "avg_duration_ms": 6234.5,
#     "max_duration_ms": 12000.0,
#     "min_duration_ms": 5100.0,
#     "call_count": 42
#   },
#   ...
# ]
```

#### Get Error Rates

```python
error_rates = analytics.get_error_rates()

# Returns:
# {
#   "research_fetch": 2.3,
#   "research_search": 1.8,
#   "broken_tool": 45.0
# }
```

#### Get Unused Tools

```python
all_tools = ["fetch", "search", "deep", "unknown_new_tool"]
unused = analytics.get_unused_tools(all_tools)

# Returns: ["unknown_new_tool"]
```

#### Get Hourly Statistics

```python
hourly = analytics.get_hourly_stats()

# Returns:
# {
#   "hourly_buckets": [
#     {"hour": "2026-05-04 10:00", "calls": 145},
#     {"hour": "2026-05-04 11:00", "calls": 189},
#     ...
#   ],
#   "total_calls_24h": 3442,
#   "peak_hour": "2026-05-04 14:00",
#   "avg_calls_per_hour": 143.4
# }
```

#### Get Total Calls

```python
today = analytics.get_total_calls_today()  # Since midnight UTC
this_hour = analytics.get_total_calls_this_hour()
avg_response = analytics.get_average_response_time()  # in ms
```

### Using the Dashboard Tool

```bash
curl -X POST http://localhost:8787/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "research_analytics_dashboard",
      "arguments": {
        "include_unused": true,
        "all_tools": ["fetch", "search", "deep", "spider", "markdown"]
      }
    }
  }'
```

**Response:**

```json
{
  "top_tools": [
    {"tool_name": "research_fetch", "call_count": 562, "percentage": 43.8},
    {"tool_name": "research_search", "call_count": 421, "percentage": 32.8},
    {"tool_name": "research_deep", "call_count": 301, "percentage": 23.4}
  ],
  "slow_tools": [
    {
      "tool_name": "research_deep",
      "avg_duration_ms": 6234.5,
      "max_duration_ms": 12000.0,
      "min_duration_ms": 5100.0,
      "call_count": 301
    }
  ],
  "high_error_tools": [
    {"tool_name": "broken_tool", "error_rate": 45.0},
    {"tool_name": "network_tool", "error_rate": 12.3}
  ],
  "unused_tools_count": 1,
  "total_calls_today": 1284,
  "total_calls_this_hour": 45,
  "average_response_time_ms": 1523.8,
  "hourly_stats": {
    "hourly_buckets": [...],
    "total_calls_24h": 3442,
    "peak_hour": "2026-05-04 14:00",
    "avg_calls_per_hour": 143.4
  },
  "timestamp": "2026-05-04T16:32:42.123456+00:00"
}
```

## Storage Modes

### In-Memory Mode (Default)

- No external dependencies
- Module-level storage: `_call_records`, `_tool_usage`, `_tool_errors`, `_tool_durations`
- Maximum 100,000 records (configurable)
- Lost on server restart
- Suitable for single-instance deployments

**Activation:** Default if Redis is unavailable

### Redis Mode

For persistent, distributed analytics:

```bash
# Environment variables
LOOM_ANALYTICS_REDIS=true
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
```

**Data structures:**
- `loom:tools:calls` (sorted set) - Total calls per tool
- `loom:tools:errors` (sorted set) - Error counts per tool
- `loom:tools:durations:{tool_name}` (list) - Duration history
- `loom:stats:hourly` (sorted set) - Hourly aggregates
- `loom:call:{timestamp}:{tool_name}` (string) - Individual call records with 30-day TTL

### Benefits of Redis Mode

- **Persistence**: Survives server restarts
- **Distribution**: Shared across multiple Loom instances
- **Scalability**: No in-process memory limits
- **Integration**: Works with monitoring systems (Prometheus, DataDog)
- **TTL**: Automatic cleanup (30-day retention)

## Integration with Monitoring

### Prometheus Metrics

The system also records metrics via Prometheus (if available):

```
loom_tool_calls_total{tool_name="research_fetch",status="success"} 562
loom_tool_calls_total{tool_name="research_fetch",status="error"} 12
loom_tool_duration_seconds{tool_name="research_fetch"} histogram_buckets
loom_tool_errors_total{tool_name="research_fetch",error_type="timeout"} 5
```

### Dashboard Integration

Use the analytics dashboard in monitoring systems:

```python
# In a monitoring script
import httpx

async def monitor_tools():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8787/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "research_analytics_dashboard",
                    "arguments": {"include_unused": False}
                }
            }
        )
        data = response.json()
        
        # Send to monitoring system
        send_to_datadog({
            "top_tools": data["top_tools"],
            "avg_response_time": data["average_response_time_ms"],
            "error_tools": data["high_error_tools"]
        })
```

## Performance Characteristics

### Time Complexity

- **Record call**: O(1) (Counter increment + list append)
- **Get top tools**: O(n log n) where n = unique tools
- **Get slow tools**: O(n) where n = unique tools
- **Get error rates**: O(n) where n = unique tools
- **Get hourly stats**: O(n) where n = events in 24h window

### Memory Usage

**In-Memory Mode:**
- Per-tool overhead: ~100 bytes
- Per-record overhead: ~1KB
- Maximum: ~100MB for 100k records

**Redis Mode:**
- No local memory overhead
- Redis process memory (configurable via Redis settings)
- Network I/O for each recording (~1KB per call)

### Throughput

- **Recording**: ~10,000 calls/second (in-memory)
- **Recording**: ~1,000 calls/second (Redis with network latency)
- **Dashboard generation**: <100ms (in-memory, <500 tools)

## Testing

Run the comprehensive test suite:

```bash
# All analytics tests
pytest tests/test_analytics.py -v

# Specific test class
pytest tests/test_analytics.py::TestAnalyticsDashboard -v

# With coverage
pytest tests/test_analytics.py --cov=src/loom/analytics
```

**Test Coverage:**
- Singleton pattern
- Recording calls (success/failure)
- Top tools ranking
- Slow tools detection
- Error rate calculation
- Unused tool detection
- Hourly statistics
- Dashboard generation
- Memory fallback
- Concurrent recording

## Example: Monitoring Dashboard

```python
import asyncio
from loom.analytics import ToolAnalytics, research_analytics_dashboard

async def generate_monitoring_report():
    """Generate hourly monitoring report."""
    result = await research_analytics_dashboard(
        include_unused=True,
        all_tools=["fetch", "search", "deep", "spider", "markdown"]
    )
    
    print(f"=== Loom Tool Analytics - {result['timestamp']} ===")
    print(f"Total calls (24h): {result['total_calls_today']}")
    print(f"Average response: {result['average_response_time_ms']}ms")
    print(f"\nTop Tools:")
    for tool in result['top_tools'][:5]:
        print(f"  {tool['tool_name']}: {tool['call_count']} calls ({tool['percentage']}%)")
    
    print(f"\nSlow Tools (>5s):")
    for tool in result['slow_tools'][:5]:
        print(f"  {tool['tool_name']}: {tool['avg_duration_ms']}ms avg")
    
    print(f"\nHigh Error Rate:")
    for tool in result['high_error_tools'][:5]:
        print(f"  {tool['tool_name']}: {tool['error_rate']}%")
    
    print(f"\nUnused tools: {result['unused_tools_count']}")

asyncio.run(generate_monitoring_report())
```

## Best Practices

1. **Use the singleton pattern**
   ```python
   analytics = ToolAnalytics.get_instance()
   ```

2. **Enable Redis for production**
   - Provides persistence and distribution
   - Set retention policy based on storage capacity

3. **Monitor error rates**
   - Alert on tools exceeding 10% error rate
   - Investigate sudden increases

4. **Track peak hours**
   - Use hourly stats for capacity planning
   - Scale infrastructure during peak times

5. **Export data periodically**
   - Use the dashboard endpoint for archival
   - Store in data warehouse for long-term analysis

6. **Set up alerts**
   - Alert on tools with >5s average response time
   - Alert on unused tools (possible bugs)
   - Alert on sudden traffic changes

## Future Enhancements

- [ ] Custom retention policies per tool
- [ ] Per-user/caller analytics
- [ ] Cost tracking integration
- [ ] Alert rules engine
- [ ] Tool dependency analysis
- [ ] Correlation with resource usage
- [ ] Predictive scaling recommendations
- [ ] A/B testing framework
- [ ] Tool recommendation engine based on success rates
