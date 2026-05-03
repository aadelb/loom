# Loom Job Queue System

## Overview

The job queue system enables asynchronous execution of long-running Loom tools without blocking uvicorn workers. Tools like `research_expert`, `research_full_pipeline`, and custom analyzers can now run in the background while returning a job ID immediately for status polling.

## Architecture

### Components

1. **JobQueue** (`src/loom/job_queue.py`)
   - SQLite-backed persistence at `~/.loom/jobs.db`
   - Async execution with semaphore limiting (max 3 concurrent jobs)
   - Job lifecycle management: pending → running → completed/failed
   - Auto-expiration of jobs after 24 hours
   - Optional webhook callbacks on completion

2. **Job Tools** (`src/loom/tools/job_tools.py`)
   - Five MCP tools for job management
   - Direct integration with FastMCP server

3. **Parameters** (`src/loom/params.py`)
   - Pydantic v2 validation models for all job tools
   - Input sanitization and bounds checking

## MCP Tools

### 1. research_job_submit

Submit a long-running job to the queue.

**Parameters:**
- `tool_name` (string): Name of the tool to execute (e.g., "research_expert")
- `params` (dict): Parameters to pass to the tool
- `callback_url` (string, optional): Webhook URL for completion notification

**Returns:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job submitted. Use research_job_status('550e...') to poll."
}
```

**Example:**
```python
result = await research_job_submit(
    tool_name="research_expert",
    params={"query": "AI safety", "depth": "deep"},
    callback_url="https://webhook.example.com/job-complete"
)
job_id = result["job_id"]
```

### 2. research_job_status

Get the current status of a job without fetching results.

**Parameters:**
- `job_id` (string): Job ID from research_job_submit

**Returns:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "research_expert",
  "status": "running",
  "created_at": "2026-05-03T10:30:45.123456+00:00",
  "started_at": "2026-05-03T10:30:46.789012+00:00",
  "completed_at": null,
  "error": null
}
```

**Status values:**
- `pending`: Job is queued, waiting to execute
- `running`: Job is currently executing
- `completed`: Job finished successfully
- `failed`: Job encountered an error

### 3. research_job_result

Retrieve the result of a completed job.

**Parameters:**
- `job_id` (string): Job ID from research_job_submit

**Returns (when completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "output": "AI safety research findings...",
    "sources": [...]
  }
}
```

**Returns (when pending/running):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "job still in progress"
}
```

**Returns (when failed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": "Connection timeout after 30 seconds"
}
```

### 4. research_job_list

List jobs in the queue with optional status filtering.

**Parameters:**
- `status` (string, optional): Filter by status (pending/running/completed/failed)
- `limit` (integer): Max results to return (default: 20, max: 100)

**Returns:**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "tool_name": "research_expert",
      "status": "completed",
      "created_at": "2026-05-03T10:30:45.123456+00:00",
      "started_at": "2026-05-03T10:30:46.789012+00:00",
      "completed_at": "2026-05-03T10:35:12.345678+00:00",
      "error": null
    }
  ],
  "count": 1,
  "status_filter": "completed"
}
```

### 5. research_job_cancel

Cancel a pending or running job.

**Parameters:**
- `job_id` (string): Job ID from research_job_submit

**Returns (success):**
```json
{
  "success": true,
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 has been cancelled"
}
```

**Returns (failure):**
```json
{
  "success": false,
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 not found or already completed"
}
```

## Usage Patterns

### Pattern 1: Fire-and-Forget with Status Polling

```python
# Submit job
result = await research_job_submit(
    tool_name="research_expert",
    params={"query": "quantum computing"}
)
job_id = result["job_id"]

# Poll status in a loop
import time
for i in range(60):  # Poll for up to 5 minutes
    status = await research_job_status(job_id)
    print(f"Status: {status['status']}")
    
    if status["status"] in ("completed", "failed"):
        break
    
    time.sleep(5)  # Wait 5 seconds between polls

# Get result when done
result = await research_job_result(job_id)
if result["status"] == "completed":
    print(result["result"])
else:
    print(f"Error: {result['error']}")
```

### Pattern 2: Webhook Callback

```python
# Submit job with webhook
result = await research_job_submit(
    tool_name="research_full_pipeline",
    params={"targets": ["target1", "target2"]},
    callback_url="https://myapp.com/webhooks/job-complete"
)
job_id = result["job_id"]
# Return job_id to client
# Webhook will POST job data when complete
```

Your webhook endpoint will receive:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": { ... }
}
```

### Pattern 3: Batch Job Management

```python
# Submit multiple jobs
job_ids = []
for query in ["AI safety", "AGI", "alignment"]:
    result = await research_job_submit(
        tool_name="research_expert",
        params={"query": query}
    )
    job_ids.append(result["job_id"])

# List running jobs
running = await research_job_list(status="running")
print(f"Currently processing: {len(running['jobs'])} jobs")

# Wait for all to complete
completed = []
for job_id in job_ids:
    result = await research_job_result(job_id)
    if result["status"] == "completed":
        completed.append(result)

print(f"Completed: {len(completed)}/{len(job_ids)}")
```

## Database Schema

The SQLite database stores jobs with the following schema:

```sql
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    params TEXT NOT NULL,              -- JSON string
    status TEXT NOT NULL,              -- pending, running, completed, failed
    result TEXT,                       -- JSON string (nullable)
    error TEXT,                        -- Error message (nullable)
    callback_url TEXT,                 -- Webhook URL (nullable)
    created_at TEXT,                   -- ISO 8601 timestamp
    started_at TEXT,                   -- ISO 8601 timestamp (nullable)
    completed_at TEXT                  -- ISO 8601 timestamp (nullable)
);

CREATE INDEX idx_status ON jobs(status);
CREATE INDEX idx_created_at ON jobs(created_at);
```

## Configuration

The job queue uses these environment variables:

- `LOOM_CONFIG_PATH`: Path to config.json (inherited from main Loom config)
- Default database location: `~/.loom/jobs.db`

The SQLite database is created automatically with WAL (Write-Ahead Logging) enabled for concurrent access.

## Concurrency Limits

- **Max concurrent jobs**: 3 (configurable via asyncio.Semaphore in job_queue.py)
- **Job timeout**: Tool-dependent (enforced by individual tool implementations)
- **Queue size**: Unlimited (limited only by SQLite performance)
- **Job lifetime**: 24 hours (auto-expires and can be cleaned up)

To modify the concurrency limit, update `_job_semaphore` in `src/loom/job_queue.py`:

```python
_job_semaphore = asyncio.Semaphore(5)  # Increase to 5 concurrent jobs
```

## Cleanup and Maintenance

### Automatic Cleanup

Jobs are not automatically deleted from the database. To remove old jobs:

```python
queue = get_job_queue()
deleted = await queue.cleanup_expired(older_than_hours=24)
print(f"Deleted {deleted} expired jobs")
```

This removes completed/failed jobs older than 24 hours.

### Manual Inspection

```python
# List all completed jobs
completed = await queue.list_jobs(status="completed", limit=100)

# Get specific job
job = queue._load_job("job-id-here")
print(job.to_dict())
```

## Error Handling

All job tools return descriptive error messages:

```python
result = await research_job_status("invalid-id")
# Returns: {"error": "job not found"}

result = await research_job_result("pending-job-id")
# Returns: {"status": "pending", "message": "job still in progress"}
```

## Testing

Run the comprehensive test suite:

```bash
# Run all job queue tests
pytest tests/test_job_queue.py -v

# Run specific test class
pytest tests/test_job_queue.py::TestJobQueueCore -v

# Run with coverage
pytest tests/test_job_queue.py --cov=src/loom/job_queue --cov-report=term-missing
```

## Integration with Existing Tools

The job queue is independent and does not require modification to existing tools. Any tool can be submitted:

```python
# Submit any existing Loom tool
result = await research_job_submit(
    tool_name="research_spider",
    params={
        "urls": ["https://example.com", "https://example.org"],
        "max_chars_each": 10000,
        "concurrency": 5
    }
)
```

## Limitations and Future Improvements

### Current Limitations

1. **In-memory task tracking**: Job tasks are stored in a global dict (`_job_tasks`). If the server restarts, tasks are lost but DB records remain.
2. **No distributed execution**: Jobs run on the same server instance.
3. **No job priorities**: All jobs execute in FIFO order within concurrency limits.
4. **Webhook delivery**: Currently just logs the callback (no actual HTTP request).

### Planned Enhancements

1. **Webhook HTTP delivery** via aiohttp/httpx with retries
2. **Job priority queues** for urgent tasks
3. **Distributed execution** via message queue (Redis, RabbitMQ)
4. **Job progress updates** for long-running tasks
5. **Scheduled jobs** (cron-like execution)
6. **Job grouping** (related jobs, dependencies)

## Logging

Job queue operations are logged to `loom.job_queue`:

```
job_queue_initialized db_path=~/.loom/jobs.db
job_submitted job_id=550e... tool=research_expert
job_started job_id=550e...
job_completed job_id=550e...
job_cancelled job_id=550e...
job_cleanup deleted=15 older_than_hours=24
```

Enable debug logging:

```python
import logging
logging.getLogger("loom.job_queue").setLevel(logging.DEBUG)
```

## Security Considerations

1. **Job ID validation**: All job IDs are validated as UUIDs (36-char format)
2. **Parameter validation**: Tool parameters are validated by Pydantic models
3. **No access control**: Currently no per-user job isolation (can be added)
4. **Webhook URL validation**: Callback URLs are validated as valid HTTP/HTTPS URLs

For production use with multi-tenant scenarios:

1. Add user/API key tracking to Job records
2. Enforce ACLs when accessing job status/results
3. Implement rate limiting per user
4. Add audit logging for sensitive operations

## Support

For issues or questions:

1. Check the logs: `tail -f ~/.cache/loom/loom.log`
2. Inspect the database: `sqlite3 ~/.loom/jobs.db "SELECT * FROM jobs;"`
3. Run tests: `pytest tests/test_job_queue.py -v`
4. Review source code: `src/loom/job_queue.py`, `src/loom/tools/job_tools.py`
