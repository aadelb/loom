# Batch Queue Quick Start

## What is it?

A background job queue for non-time-sensitive Loom tool calls. Submit jobs, they get processed asynchronously in SQLite-backed FIFO order.

## Key Files

- **`src/loom/batch_queue.py`** — BatchQueue class + MCP tools (850 lines)
- **`tests/test_batch_queue.py`** — Comprehensive test suite (50+ tests)
- **`BATCH_QUEUE_GUIDE.md`** — Full documentation

## Quick API Reference

### Submit a Job
```python
await research_batch_submit(
    tool_name="research_fetch",
    params={"url": "https://example.com"},
    callback_url="https://yourserver.com/callback",  # optional
    max_retries=3  # 0-10
)
# Returns: {"batch_id": "uuid", "status": "pending", ...}
```

### Check Status
```python
await research_batch_status(batch_id="550e8400-...")
# Returns: {"status": "done|pending|failed", "result": {...}, ...}
```

### List Recent Jobs
```python
await research_batch_list(limit=20, status_filter="all")
# Returns: {"items": [...], "count": N, ...}
```

## How It Works

1. **Submit** → Job stored in SQLite as `pending`
2. **Background Worker** → Processes `pending` → `done` or `failed` (every 10s)
3. **Webhook** → Optional callback on completion
4. **Retrieve** → Check status via batch_status or batch_list

## Configuration

### Concurrency
Default: 5 concurrent jobs (max 20)
```python
from loom.batch_queue import BatchQueue
queue = BatchQueue(concurrency=10)
```

### Database
Default: `~/.cache/loom/batch_queue.db`
```python
queue = BatchQueue(db_path="/custom/path/batch.db")
```

## Features

✓ ACID transactions (SQLite)  
✓ FIFO ordering  
✓ Automatic retries (0-10)  
✓ Webhook callbacks  
✓ Parameter validation (Pydantic v2)  
✓ Async/sync handler support  
✓ Background worker (10s poll)  
✓ Status tracking  
✓ Error logging  

## Integration with Loom Server

**Automatic:**
- ✓ Imports in `server.py`
- ✓ Tools registered as MCP endpoints
- ✓ Background worker starts on `create_app()`
- ✓ Background worker stops on `_shutdown()`

## Job Status Flow

```
┌─────────┐    process_pending()    ┌────────────┐    complete    ┌──────┐
│ pending ├──────────────────────────┤ processing ├───────────────┤ done │
└─────────┘                          └────────────┘               └──────┘
                                            │
                                      on failure
                                            │
                                       if retries
                                       remain
                                            │
                                            v
                                      ┌─────────┐
                                      │ pending │ (retry_count++)
                                      └─────────┘
                                            │
                                      no retries left
                                            │
                                            v
                                      ┌────────┐
                                      │ failed │
                                      └────────┘
```

## Parameters

### BatchSubmitParams
| Field | Type | Rules |
|-------|------|-------|
| tool_name | str | Required, 1-256 chars, alphanumeric+_ |
| params | dict | Required, any tool params |
| callback_url | str | Optional, must start http(s):// |
| max_retries | int | 0-10, default 3 |

### BatchStatusParams
| Field | Type | Rules |
|-------|------|-------|
| batch_id | str | Required, valid UUID4 |

### BatchListParams
| Field | Type | Rules |
|-------|------|-------|
| limit | int | 1-100, default 20 |
| status_filter | str | all/pending/processing/done/failed |
| offset | int | ≥0, default 0 |

## Webhook Payload

**Request (POST to callback_url):**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done",
  "result": {...},
  "error_message": null,
  "timestamp": "2026-05-04T10:30:15+00:00"
}
```

**Required Response:** Status 200-299

## Testing

```bash
# All tests
pytest tests/test_batch_queue.py -v

# Specific test class
pytest tests/test_batch_queue.py::TestBatchQueue -v

# Specific test
pytest tests/test_batch_queue.py::TestBatchQueue::test_submit_job -v

# With coverage
pytest tests/test_batch_queue.py --cov=src/loom/batch_queue
```

## Common Use Cases

### Large Bulk Fetch
```python
urls = [...]
for url in urls:
    await research_batch_submit(
        tool_name="research_fetch",
        params={"url": url}
    )
# Check status later
```

### Search + Extract
```python
batch_id = await research_batch_submit(
    tool_name="research_deep",
    params={"query": "machine learning"},
    callback_url="https://myapp.com/webhook"
)
# Webhook fires when done
```

### Scheduled Processing
```python
# Submit job, user polls status periodically
batch_id = await research_batch_submit(...)
# Later: await research_batch_status(batch_id)
```

## Monitoring

### Check queue health
```python
from loom.batch_queue import get_batch_queue

queue = get_batch_queue()
items = queue.list_items(limit=1000)

# Count by status
pending = sum(1 for i in items if i['status'] == 'pending')
processing = sum(1 for i in items if i['status'] == 'processing')
done = sum(1 for i in items if i['status'] == 'done')
failed = sum(1 for i in items if i['status'] == 'failed')

print(f"Queue: {pending} pending, {processing} processing, "
      f"{done} done, {failed} failed")
```

## Logs

Enable debug logging:
```python
import logging
logging.getLogger("loom.batch_queue").setLevel(logging.DEBUG)
```

## Limitations & Notes

- **No auto-cleanup**: Completed jobs stay in DB (implement separate cleanup if needed)
- **SQLite**: Good for <100K jobs/day. Use PostgreSQL if larger.
- **Max concurrency**: 20 (hardcoded upper limit)
- **Polling interval**: 10 seconds (hardcoded)
- **No job cancellation**: Can't cancel after submit
- **No priority queue**: FIFO only
- **Webhook timeout**: 10 seconds

## See Also

- Full guide: `BATCH_QUEUE_GUIDE.md`
- Module: `src/loom/batch_queue.py`
- Tests: `tests/test_batch_queue.py`
- Integration: `src/loom/server.py` (lines 51-57, 1434-1436, 2091-2095, 2135-2139)
