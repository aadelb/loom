# Error Wrapper Usage Guide

## Quick Start

The error wrapper prevents uncaught exceptions from crashing the MCP server by catching all exceptions and returning structured error responses.

## 1. Apply to a Tool

```python
from loom.tools.error_wrapper import safe_tool_call

@safe_tool_call
async def research_fetch(url: str) -> dict:
    """Fetch and parse URL content."""
    # If any exception occurs here, it will be caught
    # and returned as a structured error dict
    response = await fetch_url(url)
    return {"url": url, "content": response.text}
```

## 2. Check Error Statistics

```python
from loom.tools.error_wrapper import research_error_stats

# In MCP client:
stats = await research_error_stats()

print(stats)
# Output:
# {
#     "status": "ok",
#     "total_errors": 3,
#     "total_tools_with_errors": 2,
#     "error_data": {
#         "research_fetch": {
#             "count": 2,
#             "last_error": "Connection timeout",
#             "last_timestamp": "2026-05-02T11:09:29...",
#             "error_types": {"TimeoutError": 2}
#         },
#         "research_search": {
#             "count": 1,
#             "last_error": "Invalid API key",
#             "last_timestamp": "2026-05-02T11:08:15...",
#             "error_types": {"ValueError": 1}
#         }
#     }
# }
```

## 3. Clear Error History

```python
from loom.tools.error_wrapper import research_error_clear

# Clear all accumulated errors
result = await research_error_clear()

print(result)
# Output:
# {
#     "status": "ok",
#     "cleared": True,
#     "previous_error_count": 3,
#     "timestamp": "2026-05-02T11:10:00..."
# }
```

## Error Response Format

When an exception is caught, the tool returns a structured dict instead of raising:

```python
{
    "error": "Connection timeout after 30s",
    "error_type": "TimeoutError",
    "tool": "research_fetch",
    "timestamp": "2026-05-02T11:09:29.377211+00:00",
    "traceback": "Traceback (most recent call last):\n  ..."
}
```

## Supported Function Types

### Async Functions
```python
@safe_tool_call
async def async_tool() -> dict:
    # Exceptions here are caught and returned
    pass
```

### Sync Functions
```python
@safe_tool_call
def sync_tool() -> dict:
    # Exceptions here are also caught and returned
    pass
```

## What Gets Tracked

The error wrapper automatically tracks:

- **Error count per tool** - Total exceptions caught
- **Error types** - Breakdown by exception class (ValueError, TimeoutError, etc.)
- **Last error** - Most recent error message
- **Last timestamp** - When the most recent error occurred

## MCP Client Usage

In your MCP client, the error wrapper tools are available as standard tools:

```python
# List available tools
tools = client.list_tools()
# You'll see:
# - research_error_stats
# - research_error_clear

# Call statistics tool
result = await client.call_tool("research_error_stats", {})

# Call clear tool
result = await client.call_tool("research_error_clear", {})
```

## Monitoring Strategy

### During Development
Use error tracking to identify problematic tools:

```python
# Check stats regularly
stats = await research_error_stats()

# Find tools with most errors
for tool, data in stats["error_data"].items():
    print(f"{tool}: {data['count']} errors")
    print(f"  Types: {data['error_types']}")
```

### In Production
Monitor error rates:

```python
# Before fix
stats_before = await research_error_stats()
errors_before = stats_before["total_errors"]

# Apply fix

# After fix
stats_after = await research_error_stats()
errors_after = stats_after["total_errors"]

# Verify improvement
assert errors_after < errors_before
```

### After Troubleshooting
Reset statistics to get a clean baseline:

```python
# Clear old errors
await research_error_clear()

# Now monitor new error patterns
```

## Common Patterns

### Gradual Rollout
Apply the decorator to critical tools first, then expand:

```python
# Phase 1: Core tools
@safe_tool_call
async def research_fetch(...): ...  # Critical

@safe_tool_call
async def research_search(...): ...  # Critical

# Phase 2: Extended tools
@safe_tool_call
async def research_markdown(...): ...  # Extended

# Phase 3: Optional tools
@safe_tool_call
async def research_metadata(...): ...  # Optional
```

### Error Categorization
Use error tracking to categorize issues:

```python
stats = await research_error_stats()

# Network errors
network_errors = sum(
    v['error_types'].get('TimeoutError', 0) 
    + v['error_types'].get('ConnectionError', 0)
    for v in stats['error_data'].values()
)

# Input errors
input_errors = sum(
    v['error_types'].get('ValueError', 0)
    + v['error_types'].get('KeyError', 0)
    for v in stats['error_data'].values()
)

# Other errors
other_errors = stats['total_errors'] - network_errors - input_errors
```

### Alerting
Set up alerts based on error thresholds:

```python
stats = await research_error_stats()

# Alert if error rate exceeds threshold
if stats['total_errors'] > 100:
    send_alert(f"High error rate: {stats['total_errors']} errors")

# Alert if specific tool is failing
for tool, data in stats['error_data'].items():
    if data['count'] > 10:
        send_alert(f"Tool {tool} has {data['count']} errors")
```

## Integration with Existing Tools

The decorator can be applied retroactively to existing tools without changing their logic:

### Before
```python
async def research_fetch(url: str) -> dict:
    # Exceptions propagate to MCP transport layer
    response = await httpx.get(url)
    return {"content": response.text}
```

### After
```python
@safe_tool_call
async def research_fetch(url: str) -> dict:
    # Exceptions are caught and returned as dicts
    response = await httpx.get(url)
    return {"content": response.text}
```

The function logic doesn't change - only exception handling behavior improves.

## Troubleshooting

### "Tool returned error dict but should return result"
This is expected behavior. The error dict is a valid return value indicating what went wrong. Handle it in your client:

```python
result = await client.call_tool("research_fetch", {"url": "..."})

if "error" in result:
    print(f"Tool failed: {result['error']}")
    print(f"Error type: {result['error_type']}")
else:
    print(f"Success: {result}")
```

### "Too many errors accumulating"
Clear the error statistics:

```python
await research_error_clear()
```

### "Can't find error tracking tools"
Ensure `error_wrapper` is imported in `server.py`:

```python
from loom.tools import error_wrapper
```

And registered in `_register_tools()`:

```python
mcp.tool()(_wrap_tool(error_wrapper.research_error_stats))
mcp.tool()(_wrap_tool(error_wrapper.research_error_clear))
```

## Best Practices

1. **Apply early** - Use the decorator on new tools immediately
2. **Monitor regularly** - Check `research_error_stats()` weekly
3. **Clear strategically** - Reset stats before major changes
4. **Log failures** - Examine tracebacks to fix root causes
5. **Gradual adoption** - Start with critical tools, expand over time
6. **Document patterns** - Record common error types and causes
7. **Set alerts** - Monitor error rates in production

## Performance Impact

- Minimal overhead: ~1-2ms per tool call
- Memory usage: ~100 bytes per error entry
- No external dependencies
- Thread-safe and async-safe

## Further Reading

- **Implementation**: `/src/loom/tools/error_wrapper.py`
- **Tests**: `/tests/test_tools/test_error_wrapper.py`
- **Demo**: `/examples/error_wrapper_demo.py`
