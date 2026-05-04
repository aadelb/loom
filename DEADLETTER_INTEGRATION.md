# Deadletter Queue Integration Guide

## Overview

The DeadletterQueue (DLQ) system provides persistent, reliable retry handling for failed tool calls in Loom. It implements exponential backoff scheduling, automatic background retry processing, and comprehensive statistics tracking.

## Components

### 1. Core Module: `src/loom/deadletter.py`

**DeadletterQueue class:**
- SQLite-backed persistence in `~/.cache/loom/dlq.db`
- Two tables: `dlq_pending` and `dlq_failed`
- Methods:
  - `enqueue(tool_name, params, error)` - Add failed call to queue
  - `dequeue(limit)` - Retrieve items ready for retry
  - `mark_success(dlq_id)` - Remove from queue after successful retry
  - `mark_permanent_failure(dlq_id)` - Move to failed table
  - `increment_retry_count(dlq_id)` - Increment and reschedule
  - `get_stats()` - Queue statistics
  - `get_items_by_tool(tool_name)` - Filter by tool
  - `cleanup_old_failed(days)` - Remove old entries

**DeadletterQueueWorker class:**
- Background async worker for automatic retry processing
- Polls every 60 seconds (configurable)
- Re-executes failed tool calls
- Handles success/failure/permanent_failure cases
- Respects max_retries limit (default: 3)

**Exponential Backoff Schedule:**
- Attempt 0: 60 seconds
- Attempt 1: 300 seconds (5 minutes)
- Attempt 2: 1800 seconds (30 minutes)
- Beyond: Uses final delay (1800s)

### 2. Tools Module: `src/loom/tools/dlq_management.py`

Four MCP tools for queue management:

**research_dlq_stats()**
- Returns queue statistics (pending, failed, retried counts)
- Useful for monitoring tool reliability

**research_dlq_retry_now(dlq_id)**
- Force immediate retry by setting next_retry_at to now
- Bypasses normal backoff schedule

**research_dlq_list(tool_name=None, include_failed=False)**
- List pending or failed items
- Optional filter by tool name

**research_dlq_clear_failed(days=30)**
- Clean up old failed items to prevent table bloat
- Default: delete items older than 30 days

## Integration into server.py

### Step 1: Import DLQ

Add to imports in `server.py`:

```python
from loom.deadletter import get_dlq, DeadletterQueueWorker
from loom.tools import dlq_management
```

### Step 2: Wire into _wrap_tool

Modify the exception handler in `_wrap_tool` to enqueue failures:

```python
except Exception as e:
    # Prometheus: record error
    error_type = type(e).__name__
    _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
    _loom_tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()
    duration = time.time() - start_time
    _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
    
    # NEW: Enqueue to DLQ if retryable
    if _is_retryable_error(error_type):
        dlq = get_dlq()
        dlq.enqueue(tool_name, corrected_kwargs, str(e))
        log.debug(f"tool_failure_enqueued: tool={tool_name}")
    
    raise
```

Helper function to determine retryability:

```python
def _is_retryable_error(error_type: str) -> bool:
    """Check if error is worth retrying."""
    retryable = {
        "TimeoutError",
        "asyncio.TimeoutError",
        "ConnectionError",
        "BrokenPipeError",
        "RemoteDisconnected",
        "HTTPError",
    }
    return error_type in retryable
```

### Step 3: Register MCP Tools

In `_register_tools` or the tool registration section:

```python
# Register DLQ management tools
mcp.tool()(dlq_management.research_dlq_stats)
mcp.tool()(dlq_management.research_dlq_retry_now)
mcp.tool()(dlq_management.research_dlq_list)
mcp.tool()(dlq_management.research_dlq_clear_failed)
```

### Step 4: Start Background Worker (Optional but Recommended)

In `create_app()` or server initialization:

```python
# Create and start DLQ background worker
async def tool_executor(tool_name: str, params: dict) -> Any:
    """Execute a tool by name and parameters."""
    # Dispatch to actual tool implementation
    # This requires dynamic lookup of tool by name
    pass

dlq = get_dlq()
dlq_worker = DeadletterQueueWorker(dlq, tool_executor, poll_interval=60)

# Start worker in background (requires async context)
# This would typically be done in an async startup hook
```

## Usage Examples

### Monitoring Queue Health

```python
# Get statistics
stats = get_dlq().get_stats()
print(f"Pending items: {stats['pending']}")
print(f"Failed items: {stats['failed']}")
print(f"Total retries: {stats['total_retried']}")
```

### Manual Retry

```python
dlq = get_dlq()
items = dlq.dequeue(limit=10)

for item in items:
    print(f"Retrying {item['tool_name']} (attempt {item['retry_count'] + 1})")
    # Execute tool...
    if success:
        dlq.mark_success(item['id'])
    else:
        dlq.increment_retry_count(item['id'])
```

### Listing Items by Tool

```python
dlq = get_dlq()
fetch_items = dlq.get_items_by_tool("research_fetch")
for item in fetch_items:
    print(f"ID: {item['id']}, Retries: {item['retry_count']}, Error: {item['error']}")
```

## Database Schema

### dlq_pending Table

```sql
CREATE TABLE dlq_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    params_json TEXT NOT NULL,
    error TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TEXT NOT NULL,  -- ISO 8601 timestamp
    created_at TEXT NOT NULL,      -- ISO 8601 timestamp
    updated_at TEXT NOT NULL       -- ISO 8601 timestamp
);
```

Indexes:
- `idx_dlq_pending_retry`: ON (next_retry_at) - for efficient dequeue
- `idx_dlq_pending_tool`: ON (tool_name) - for filtering by tool

### dlq_failed Table

```sql
CREATE TABLE dlq_failed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    params_json TEXT NOT NULL,
    error TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    failed_at TEXT NOT NULL,       -- ISO 8601 timestamp
    created_at TEXT NOT NULL       -- ISO 8601 timestamp
);
```

Indexes:
- `idx_dlq_failed_tool`: ON (tool_name) - for filtering

## Configuration

Environment variables (optional):

```bash
# Database path (defaults to ~/.cache/loom/dlq.db)
export LOOM_DLQ_PATH=/path/to/dlq.db

# Worker poll interval in seconds (defaults to 60)
export LOOM_DLQ_POLL_INTERVAL=60

# Maximum retries before permanent failure (defaults to 3)
export LOOM_DLQ_MAX_RETRIES=3
```

## Testing

Run comprehensive test suite:

```bash
# All DLQ tests
pytest tests/test_deadletter.py -v

# Specific test class
pytest tests/test_deadletter.py::TestDeadletterQueue -v

# With coverage
pytest tests/test_deadletter.py --cov=src/loom/deadletter --cov=src/loom/tools/dlq_management
```

Test coverage: 24 tests covering:
- Core enqueueing/dequeueing
- Exponential backoff calculation
- Retry counting and permanence
- Statistics aggregation
- Thread safety
- Background worker processing
- Singleton pattern

## Thread Safety

All operations are thread-safe via `threading.RLock()`:
- Multiple threads can enqueue/dequeue concurrently
- Database operations are atomic
- SQLite connection pooling with timeout

## Performance Characteristics

- **Enqueue**: O(1) - Single INSERT
- **Dequeue**: O(log n) - Index scan on next_retry_at
- **Mark Success**: O(1) - Single DELETE
- **Statistics**: O(n) - Full table scan (can be optimized with counts table)
- **Database Size**: ~500 bytes per pending item, ~400 bytes per failed item

## Monitoring and Debugging

### View queue contents directly

```bash
sqlite3 ~/.cache/loom/dlq.db
SELECT COUNT(*) FROM dlq_pending;
SELECT * FROM dlq_pending ORDER BY next_retry_at LIMIT 10;
SELECT COUNT(*) FROM dlq_failed;
```

### Enable debug logging

```python
import logging
logging.getLogger("loom.deadletter").setLevel(logging.DEBUG)
```

Log messages include:
- `enqueue`: New failed item added
- `dequeue`: Items ready for retry
- `mark_success`: Item successfully retried
- `mark_permanent_failure`: Item gave up after max retries
- `worker`: Background worker lifecycle events

## Best Practices

1. **Classify Retryable Errors**: Only enqueue transient failures (timeout, connection errors), not logic errors
2. **Monitor Queue Depth**: Use `get_stats()` to alert if queue grows unbounded
3. **Set Appropriate Backoff**: 60s-300s-1800s suits most API scenarios; adjust based on tool behavior
4. **Clean Old Entries**: Run `cleanup_old_failed(days=30)` periodically
5. **Log Failures**: Always include error message context for debugging
6. **Test Retry Logic**: Verify tool is idempotent before relying on DLQ

## Known Limitations

1. **No distributed locking**: DLQ assumes single-instance Loom server; multi-instance needs external coordination
2. **No dead letter routing**: Failed items aren't routed to alternate handlers
3. **No circuit breaker**: Doesn't stop retrying if tool persistently fails
4. **Manual tool execution**: Background worker requires explicit tool_executor function
5. **No alerting**: Integration with monitoring system required for alerts

## Future Enhancements

- [ ] Circuit breaker pattern (stop retrying after N consecutive failures)
- [ ] Dead letter routing to alternative handlers
- [ ] Metrics export for Prometheus/Datadog
- [ ] Webhook notifications on permanent failures
- [ ] Distributed locking for multi-instance deployments
- [ ] Priority queue (expedite critical tool retries)
- [ ] Batch API for bulk enqueue/retry operations
