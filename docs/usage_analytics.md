# Tool Usage Analytics

Three MCP tools for recording, reporting, and analyzing tool usage patterns across the Loom MCP server.

## Overview

The usage analytics system provides real-time insight into:
- Which tools are being used most frequently
- Peak usage times
- Usage trends over time
- Per-tool usage statistics

All data is stored in-memory with a fixed-size deque (max 50,000 events), providing O(1) record operations and minimal memory footprint.

## Tools

### 1. `research_usage_record`

Records a single tool usage event.

**Parameters:**
- `tool_name` (str, required): Name of the tool being used (e.g., "fetch", "search", "deep")
- `caller` (str, optional): Source of the call. Default: `"mcp"`. Examples: `"api"`, `"cli"`, `"custom_agent"`

**Returns:**
```json
{
  "recorded": true,
  "tool": "fetch",
  "total_uses": 42
}
```

**Use Case:**
Instrument tool implementations to automatically log usage:
```python
# In a tool implementation
await research_usage_record("my_tool", caller="api")
```

**Example:**
```
research_usage_record(
  tool_name="research_fetch",
  caller="mcp"
)
→ {"recorded": true, "tool": "research_fetch", "total_uses": 1}
```

---

### 2. `research_usage_report`

Generate usage statistics for a specified time period.

**Parameters:**
- `period` (str, optional): Time window to analyze. Default: `"today"`
  - `"today"` - Current calendar day (UTC)
  - `"hour"` - Last 60 minutes
  - `"all"` - All recorded history (up to 50,000 events)

**Returns:**
```json
{
  "period": "today",
  "total_calls": 1284,
  "unique_tools_used": 42,
  "top_tools": [
    {
      "name": "research_fetch",
      "calls": 562,
      "pct": 43.8
    },
    {
      "name": "research_search",
      "calls": 421,
      "pct": 32.8
    },
    {
      "name": "research_deep",
      "calls": 301,
      "pct": 23.4
    }
  ],
  "calls_per_minute": 12.4,
  "peak_hour": "2026-05-02 14:00"
}
```

**Fields:**
- `total_calls` (int): Total number of tool invocations in the period
- `unique_tools_used` (int): Count of distinct tools called
- `top_tools` (list): Top 10 tools ranked by call frequency with percentages
- `calls_per_minute` (float): Average calls per minute across the period
- `peak_hour` (str): Hour (ISO format) with the most calls; `null` if no data

**Use Cases:**
- Monitor system load and usage patterns
- Identify which tools are most valuable
- Detect anomalies or unexpected tool combinations
- Generate usage reports for monitoring dashboards

**Examples:**
```
# Today's usage
research_usage_report(period="today")

# Last hour (real-time monitoring)
research_usage_report(period="hour")

# All-time statistics
research_usage_report(period="all")
```

---

### 3. `research_usage_trends`

Analyze usage trends over a time window (hourly aggregation).

**Parameters:**
- `tool_name` (str, optional): Specific tool to analyze. Default: `""` (all tools)
- `window_hours` (int, optional): Hours to look back. Default: `24`

**Returns:**
```json
{
  "tool": "all",
  "window_hours": 24,
  "hourly_buckets": [
    {
      "hour": "2026-05-01 14:00",
      "calls": 45
    },
    {
      "hour": "2026-05-01 15:00",
      "calls": 52
    },
    {
      "hour": "2026-05-01 16:00",
      "calls": 38
    }
  ],
  "trend": "stable",
  "peak_time": "2026-05-01 15:00"
}
```

**Trend Detection:**
- `"increasing"`: Second half of window > first half by >10%
- `"decreasing"`: Second half < first half by >10%
- `"stable"`: Change between +10% and -10%

**Fields:**
- `hourly_buckets` (list): Chronologically ordered hourly aggregations
- `trend` (str): Overall trend classification
- `peak_time` (str): Hour with maximum calls

**Use Cases:**
- Detect usage spikes or capacity issues
- Understand diurnal patterns (peak times)
- Monitor tool adoption over time
- Identify degradation or improvement trends

**Examples:**
```
# Overall trend (last 24 hours)
research_usage_trends()

# Specific tool trend
research_usage_trends(tool_name="research_fetch", window_hours=24)

# Wide window (72-hour trend)
research_usage_trends(window_hours=72)

# Narrow window (real-time, 3-hour)
research_usage_trends(window_hours=3)
```

---

## Implementation Details

### Storage Model

Two module-level data structures:

1. **`_usage_counter`** (collections.Counter)
   - Maintains cumulative counts per tool
   - O(1) lookups and increments
   - Never cleared (persistent across reports)

2. **`_usage_history`** (collections.deque, maxlen=50000)
   - Stores timestamped events: `{"tool", "caller", "timestamp"}`
   - FIFO with automatic overflow (oldest events discarded)
   - ISO 8601 UTC timestamps for precise ordering
   - ~50MB memory for 50,000 events (~1KB per event)

### Thread Safety

- No explicit locking (deque is thread-safe for append)
- Counter operations are atomic in CPython (GIL)
- Safe for concurrent async tool calls
- Guarantees "at-least-once" recording

### Time Complexity

- **Record**: O(1) average (Counter increment + deque append)
- **Report**: O(n) where n = events in period (linear scan + aggregation)
- **Trends**: O(n) where n = events in window (bucketing + trend analysis)

### Memory Usage

- Counter: ~100 bytes per unique tool
- Deque: ~1KB per event, capped at 50,000 → ~50MB maximum
- Total: <75MB for typical 40-tool, 50k-event scenarios

---

## Integration with Loom Tools

### Auto-Instrumentation

To instrument a tool, add this line:
```python
# At the end of your tool implementation
await research_usage_record(tool_name="your_tool_name", caller="api")
```

### Example: Instrumented Fetch Tool

```python
async def research_fetch(url: str, ...) -> dict[str, Any]:
    """Fetch a URL and analyze content."""
    # ... implementation ...
    
    # Record usage
    await research_usage_record("research_fetch", caller="mcp")
    
    return result
```

### Dashboard Integration

Display real-time metrics:
```python
# Get current hour usage
report = await research_usage_report(period="hour")
print(f"Calls this hour: {report['total_calls']}")
print(f"Top tool: {report['top_tools'][0]['name']}")

# Get 24-hour trend
trends = await research_usage_trends(window_hours=24)
print(f"Trend: {trends['trend']}")
print(f"Peak time: {trends['peak_time']}")
```

---

## Best Practices

1. **Instrument at tool boundaries**, not internal calls
   - Record once per user-initiated tool invocation
   - Avoid double-counting in pipelines

2. **Use meaningful tool names**
   - `"research_fetch"`, `"research_search"`, `"research_deep"`
   - Avoid generic names like `"tool"` or `"run"`

3. **Include caller context**
   - `"api"` for MCP/API calls
   - `"cli"` for CLI invocations
   - `"pipeline"` for orchestration calls
   - Enables caller-aware analytics

4. **Monitor peak hours regularly**
   - Check trends daily for capacity planning
   - Watch for sustained increases

5. **Export for archival**
   - Deque has 50k event limit
   - Periodically export `research_usage_report(period="all")` to external store
   - Use `research_usage_record` timestamps for offline analysis

---

## Limitations

- **In-memory only**: Data is lost on server restart
  - Use periodic export to persistent storage
  - Consider integration with audit log system

- **Fixed history**: Deque maxlen=50000
  - Roughly ~5-10 hours of usage at typical rates
  - Older events automatically discarded
  - Plan exports accordingly

- **No filtering**: Reports include all tools
  - Use tool_name parameter on `research_usage_trends` for per-tool analysis
  - Custom filtering requires post-processing report data

- **UTC only**: All timestamps in UTC
  - Periods ("today") based on UTC day boundaries
  - Adjust analysis client-side for local time

---

## Future Enhancements

- [ ] Persistent backend (SQLite/PostgreSQL)
- [ ] Cost tracking (token usage, API calls)
- [ ] Error rate tracking per tool
- [ ] Caller attribution and quotas
- [ ] Export to monitoring systems (Prometheus, DataDog)
- [ ] Configurable deque size and TTL
- [ ] Tool-to-tool call graph analysis
- [ ] Performance metrics (latency, success rates)
