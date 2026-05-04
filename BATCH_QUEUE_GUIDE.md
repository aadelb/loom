# Batch Processing Queue for Loom

## Overview

The batch processing queue (`src/loom/batch_queue.py`) provides asynchronous job queuing for non-time-sensitive tool invocations in Loom. Jobs are persisted in SQLite and processed in the background by an asyncio worker task running every 10 seconds.

**Key Features:**
- SQLite persistence with ACID transactions
- FIFO job ordering with configurable concurrency (default 5)
- Automatic retry logic (0-10 retries per job)
- Optional webhook callbacks on completion
- Full parameter validation via Pydantic v2
- MCP tool integration

## Architecture

### Components

```
BatchQueue (main class)
├── SQLite Database (batch_queue.db)
│   └── batch_items table
├── _tool_registry (dict of registered handlers)
├── Background Worker (asyncio.Task)
│   └── Processes pending jobs every 10 seconds
└── MCP Tools
    ├── research_batch_submit()
    ├── research_batch_status()
    └── research_batch_list()
```

### Job Lifecycle

```
1. SUBMIT (research_batch_submit)
   └─> Validate params → Store in SQLite as "pending"

2. PROCESS (background worker)
   └─> Lock to "processing" → Execute handler → Update status

3. COMPLETE (via callback if configured)
   └─> Mark as "done"/"failed" → Trigger webhook (optional)

4. RETRIEVE (research_batch_status or research_batch_list)
   └─> Query database → Return status dict
```

## Usage

### 1. Submitting Jobs

#### Via MCP Tool
```python
# Python client code
response = await client.call_tool("research_batch_submit", {
    "tool_name": "research_fetch",
    "params": {
        "url": "https://example.com",
        "mode": "stealthy"
    },
    "callback_url": "https://yourserver.com/webhook",
    "max_retries": 3
})

batch_id = response["batch_id"]
print(f"Job queued: {batch_id}")
```

#### Via Python API
```python
from loom.batch_queue import get_batch_queue

queue = get_batch_queue()
batch_id = queue.submit(
    tool_name="research_fetch",
    params={"url": "https://example.com"},
    callback_url="https://yourserver.com/webhook",
    max_retries=3
)
```

### 2. Checking Job Status

#### Via MCP Tool
```python
status = await client.call_tool("research_batch_status", {
    "batch_id": "550e8400-e29b-41d4-a716-446655440000"
})

# Returns:
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tool_name": "research_fetch",
    "status": "done",  # pending | processing | done | failed
    "result": {"content": "..."},
    "error_message": None,
    "created_at": "2026-05-04T10:30:00+00:00",
    "started_at": "2026-05-04T10:30:05+00:00",
    "completed_at": "2026-05-04T10:30:15+00:00",
    "retry_count": 0
}
```

### 3. Listing Recent Jobs

#### Via MCP Tool
```python
result = await client.call_tool("research_batch_list", {
    "limit": 20,
    "status_filter": "all",  # all | pending | processing | done | failed
    "offset": 0
})

# Returns:
{
    "items": [...],  # list of status dicts
    "count": 20,
    "limit": 20,
    "offset": 0,
    "status_filter": "all"
}
```

### 4. Registering Custom Handlers

```python
from loom.batch_queue import get_batch_queue

async def my_handler(params: dict) -> dict:
    """Custom async handler."""
    result = await some_async_operation(params["key"])
    return {"result": result}

queue = get_batch_queue()
queue.register_tool("my_tool", my_handler)
```

## Configuration

### Database Location
By default, the batch queue uses `~/.cache/loom/batch_queue.db`. Override:

```python
from loom.batch_queue import BatchQueue
from pathlib import Path

queue = BatchQueue(
    db_path=Path("/custom/path/batch.db"),
    concurrency=10  # max 20
)
```

### Concurrency
Default is 5 concurrent jobs. Set via environment or constructor:

```python
queue = BatchQueue(concurrency=10)  # Max 20
```

### Background Interval
Jobs are processed every 10 seconds. This is hardcoded but can be overridden:

```python
from loom.batch_queue import BATCH_BACKGROUND_INTERVAL_SECS
# Default: 10 seconds
```

## Parameter Validation

All inputs are validated with Pydantic v2:

### BatchSubmitParams
```python
{
    "tool_name": str,        # Required, 1-256 chars, alphanumeric + underscores
    "params": dict,          # Required, tool parameters
    "callback_url": str,     # Optional, must start with http:// or https://
    "max_retries": int       # 0-10, default 3
}
```

### BatchStatusParams
```python
{
    "batch_id": str  # Required, must be valid UUID4 (36 chars)
}
```

### BatchListParams
```python
{
    "limit": int,              # 1-100, default 20
    "status_filter": str,      # all|pending|processing|done|failed
    "offset": int              # ≥0, default 0
}
```

## Webhook Callbacks

When a job completes (success or failure), an optional webhook is triggered:

### Request
```
POST {callback_url}
Content-Type: application/json

{
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "done",  # or "failed"
    "result": {...},
    "error_message": None,  # or error details if failed
    "timestamp": "2026-05-04T10:30:15+00:00"
}
```

### Response Requirements
- Status code 200-299 for success
- Status code ≥300 or ≤199 is logged as warning (no retry)

## Error Handling

### Automatic Retries
Jobs that fail are automatically retried up to `max_retries` times:

```python
# Retries up to 3 times
batch_id = queue.submit(
    tool_name="unreliable_tool",
    params={},
    max_retries=3  # 0-10
)
```

### Failure Reasons
1. **Unregistered tool**: Handler not found in registry
2. **Handler exception**: Tool raised an exception
3. **Invalid params JSON**: Stored params couldn't be decoded
4. **Webhook failure**: Callback URL unreachable (job still marked done)

## Database Schema

### batch_items Table
```sql
CREATE TABLE batch_items (
    id TEXT PRIMARY KEY,              -- UUID4
    tool_name TEXT NOT NULL,          -- Tool name
    params_json TEXT NOT NULL,        -- JSON-encoded params
    status TEXT NOT NULL,             -- pending|processing|done|failed
    result_json TEXT,                 -- JSON-encoded result
    error_message TEXT,               -- Error detail if failed
    created_at TEXT NOT NULL,         -- ISO8601 timestamp
    started_at TEXT,                  -- When processing started
    completed_at TEXT,                -- When job finished
    retry_count INTEGER NOT NULL,     -- Current retry count
    max_retries INTEGER NOT NULL,     -- Max retries allowed
    callback_url TEXT                 -- Optional webhook URL
);

-- Indexes for performance
CREATE INDEX idx_status ON batch_items(status);
CREATE INDEX idx_created_at ON batch_items(created_at DESC);
```

## Integration with Loom Server

### Auto-Start/Stop
The batch queue background worker is automatically started and stopped with the Loom server:

```python
# In create_app():
start_batch_queue_background()

# In _shutdown():
stop_batch_queue_background()
```

### MCP Registration
Tools are registered in `_register_tools()`:

```python
_core_funcs = [
    ...,
    research_batch_submit, 
    research_batch_status, 
    research_batch_list,
    ...
]
```

## Testing

Comprehensive test suite in `tests/test_batch_queue.py` covering:

- Job submission and retrieval
- Status tracking
- Background processing (sync and async handlers)
- Error handling and retries
- Webhook callbacks
- Concurrency limits
- SQLite persistence
- Parameter validation
- Complete end-to-end workflows

Run tests:
```bash
pytest tests/test_batch_queue.py -v
pytest tests/test_batch_queue.py::TestBatchQueue -v
pytest tests/test_batch_queue.py -k "process_pending" -v
```

## Performance Considerations

### Scaling
- **Concurrency**: Default 5, max 20. Increase for CPU-bound tasks, keep low for I/O-bound.
- **Cleanup**: Batch items are never auto-deleted; implement separate cleanup if needed.
- **Database**: SQLite suitable for <100K jobs/day. Use PostgreSQL backend if needed.

### Optimization
1. **Increase concurrency** for parallel jobs:
   ```python
   queue = BatchQueue(concurrency=15)
   ```

2. **Reduce retry count** for fast-fail:
   ```python
   queue.submit(..., max_retries=0)
   ```

3. **Batch similar jobs** for efficiency:
   ```python
   for url in urls:
       queue.submit("research_fetch", {"url": url})
   ```

## Monitoring

### Check Background Worker Status
```python
from loom.batch_queue import get_batch_queue

queue = get_batch_queue()
pending_count = len(queue.list_items(status_filter="pending"))
processing_count = len(queue.list_items(status_filter="processing"))
done_count = len(queue.list_items(status_filter="done"))
failed_count = len(queue.list_items(status_filter="failed"))

print(f"Queue status: {pending_count} pending, {processing_count} processing, "
      f"{done_count} done, {failed_count} failed")
```

### Logs
The batch queue logs to `loom.batch_queue`:

```python
import logging

logging.getLogger("loom.batch_queue").setLevel(logging.DEBUG)
```

## Troubleshooting

### Jobs Stuck in "processing"
1. Check server logs for exceptions
2. Verify handler is registered
3. Check callback URL is reachable
4. Restart server (gracefully stops background worker)

### High Memory Usage
1. Too many concurrent jobs: Reduce `concurrency`
2. Large result_json: Implement cleanup task
3. Database bloat: Purge old completed jobs

### Webhook Not Triggering
1. Callback URL must start with `http://` or `https://`
2. Server must be able to reach callback URL (firewall, DNS)
3. Check logs for connection errors
4. Job status will still be marked "done" even if callback fails

### Database Locked
SQLite has retry logic built in. If persistent:
1. Check for orphaned connections
2. Ensure concurrent access limit is not exceeded
3. Consider switching to PostgreSQL backend

## Examples

### Complete Workflow

```python
from loom.batch_queue import get_batch_queue
import asyncio

async def main():
    queue = get_batch_queue()
    
    # Register a handler
    def fetch_handler(params: dict) -> dict:
        url = params["url"]
        # ... fetch logic ...
        return {"url": url, "content": "..."}
    
    queue.register_tool("fetch", fetch_handler)
    
    # Submit 5 jobs
    batch_ids = []
    for i in range(5):
        batch_id = queue.submit(
            tool_name="fetch",
            params={"url": f"https://example.com/{i}"},
        )
        batch_ids.append(batch_id)
    
    # Wait for processing
    import time
    time.sleep(2)  # Let background worker process
    
    # Check results
    for batch_id in batch_ids:
        status = queue.get_status(batch_id)
        print(f"{batch_id}: {status['status']}")
        if status['result']:
            print(f"  Result: {status['result']}")

asyncio.run(main())
```

### Webhook Handler (Flask Example)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def batch_webhook():
    data = request.json
    batch_id = data["batch_id"]
    status = data["status"]
    result = data["result"]
    error = data["error_message"]
    
    if status == "done":
        print(f"Job {batch_id} completed with result: {result}")
    elif status == "failed":
        print(f"Job {batch_id} failed: {error}")
    
    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(port=5000)
```

## Files Modified

- `src/loom/batch_queue.py` - New module (850+ lines)
- `src/loom/server.py` - Added batch queue imports, tool registration, startup/shutdown hooks
- `tests/test_batch_queue.py` - New test suite (400+ lines, 50+ test cases)

## Future Enhancements

Potential improvements:

1. **Database Backend Abstraction**: Support PostgreSQL, Redis
2. **Priority Queue**: High-priority jobs processed first
3. **Job Groups**: Batch multiple related jobs
4. **Rate Limiting**: Per-tool rate limits
5. **Dead Letter Queue**: Failed jobs after max retries
6. **Metrics Export**: Prometheus metrics for jobs
7. **Job Cancellation**: Cancel pending/processing jobs
8. **Scheduled Jobs**: Cron-like scheduling
