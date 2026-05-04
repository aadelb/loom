# SSE Progress Streaming for Long-Running Tools

## Overview

The Loom server now provides Server-Sent Events (SSE) progress streaming for long-running tools. Clients can subscribe to real-time progress updates via HTTP GET endpoints and receive JSON-formatted progress events as they occur.

## Architecture

### Components

1. **ProgressTracker** (`src/loom/progress.py`): Core progress tracking system
   - Stores per-job async queues for event streaming
   - Thread-safe via asyncio.Lock
   - Singleton instance via `get_progress_tracker()`

2. **ProgressEvent** (`src/loom/progress.py`): Immutable event dataclass
   - `job_id`: Unique job identifier (UUID)
   - `stage`: Pipeline stage name (e.g., "search", "fetch", "extract")
   - `percent`: Progress percentage (0-100, auto-clamped)
   - `message`: Human-readable status message
   - `timestamp`: ISO 8601 creation timestamp

3. **SSE Endpoints** (`src/loom/server.py`):
   - `GET /progress/{job_id}` — Stream SSE events for a job
   - `GET /progress` — List all active job IDs

4. **research_deep_with_progress** (`src/loom/tools/deep.py`): Example wrapper
   - Integrates progress reporting at each stage
   - Reports stages: initialize → expand → search → fetch → extract → synthesize → complete
   - Returns `job_id` in response for client reference

## HTTP Endpoints

### GET /progress/{job_id}

Stream Server-Sent Events for a specific job.

**Request:**
```bash
curl -N http://localhost:8787/progress/550e8400-e29b-41d4-a716-446655440000
```

**Response (SSE stream):**
```
data: {"job_id":"550e8400-e29b-41d4-a716-446655440000","stage":"search","percent":20,"message":"Searching across 3 providers","timestamp":"2025-05-04T10:30:45.123456+00:00"}

data: {"job_id":"550e8400-e29b-41d4-a716-446655440000","stage":"fetch","percent":50,"message":"Fetching and processing search results","timestamp":"2025-05-04T10:30:48.456789+00:00"}

data: {"job_id":"550e8400-e29b-41d4-a716-446655440000","stage":"extract","percent":75,"message":"Extracting key information with LLM","timestamp":"2025-05-04T10:30:52.789012+00:00"}
```

**Response Headers:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no` (disables nginx buffering)

### GET /progress

List all active job IDs being tracked.

**Request:**
```bash
curl http://localhost:8787/progress
```

**Response (JSON):**
```json
{
  "active_jobs": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ],
  "count": 2
}
```

## Client Implementation

### JavaScript (Browser)

```javascript
const jobId = "550e8400-e29b-41d4-a716-446655440000";
const eventSource = new EventSource(`/progress/${jobId}`);

eventSource.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(`[${progress.stage}] ${progress.percent}% - ${progress.message}`);
  
  // Update UI
  document.getElementById("progress").value = progress.percent;
  document.getElementById("status").textContent = progress.message;
  
  if (progress.stage === "complete" || progress.stage === "error") {
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error("Progress stream error:", error);
  eventSource.close();
};
```

### Python (asyncio)

```python
import aiohttp
import json
from typing import AsyncIterator

async def stream_progress(job_id: str) -> AsyncIterator[dict]:
    """Stream progress events for a job."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://localhost:8787/progress/{job_id}") as resp:
            async for line in resp.content:
                line_str = line.decode().strip()
                if line_str.startswith("data: "):
                    data_json = line_str[6:]
                    yield json.loads(data_json)

# Usage
async def main():
    async for progress_event in stream_progress("550e8400-e29b-41d4-a716-446655440000"):
        print(f"[{progress_event['stage']}] {progress_event['percent']}% - {progress_event['message']}")

asyncio.run(main())
```

### Python (httpx)

```python
import json
import httpx
from typing import Iterator

def stream_progress(job_id: str) -> Iterator[dict]:
    """Stream progress events for a job using httpx."""
    with httpx.stream("GET", f"http://localhost:8787/progress/{job_id}") as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_json = line[6:]
                yield json.loads(data_json)

# Usage
for progress_event in stream_progress("550e8400-e29b-41d4-a716-446655440000"):
    print(f"[{progress_event['stage']}] {progress_event['percent']}% - {progress_event['message']}")
```

### cURL (live monitoring)

```bash
# Stream events with -N flag (unbuffered)
curl -N http://localhost:8787/progress/550e8400-e29b-41d4-a716-446655440000

# Parse with jq
curl -N http://localhost:8787/progress/550e8400-e29b-41d4-a716-446655440000 | \
  while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      echo "${line:6:}" | jq .
    fi
  done
```

## Integration Guide

### Using research_deep_with_progress

The `research_deep_with_progress` function wraps `research_deep` with built-in progress tracking:

```python
from loom.tools.deep import research_deep_with_progress
from loom.progress import create_job_id

# Option 1: Auto-generate job_id
result = await research_deep_with_progress(
    query="Python asyncio patterns",
    depth=2,
)
job_id = result["job_id"]

# Option 2: Provide custom job_id
custom_job_id = create_job_id()
result = await research_deep_with_progress(
    query="Python asyncio patterns",
    job_id=custom_job_id,
    depth=2,
)

# Client subscribes via: GET /progress/{job_id}
```

### Implementing Progress in New Tools

To add progress tracking to any long-running tool:

```python
from loom.progress import get_progress_tracker, create_job_id

async def my_long_running_tool(query: str, job_id: str | None = None) -> dict:
    """Example tool with progress tracking."""
    if not job_id:
        job_id = create_job_id()
    
    tracker = get_progress_tracker()
    
    try:
        # Stage 1
        await tracker.report_progress(
            job_id=job_id,
            stage="stage1",
            percent=10,
            message="Starting processing...",
        )
        # ... do work ...
        
        # Stage 2
        await tracker.report_progress(
            job_id=job_id,
            stage="stage2",
            percent=50,
            message="Processing data...",
        )
        # ... do work ...
        
        # Complete
        await tracker.report_progress(
            job_id=job_id,
            stage="complete",
            percent=100,
            message="Done!",
        )
        
        result = {"status": "success", "job_id": job_id}
        return result
        
    except Exception as exc:
        await tracker.report_progress(
            job_id=job_id,
            stage="error",
            percent=0,
            message=f"Error: {str(exc)[:100]}",
        )
        raise
    finally:
        # Optional: clean up after delay
        await asyncio.sleep(5)
        await tracker.cleanup(job_id)
```

## Progress Stages

Standard pipeline stages for deep research:

| Stage | Percent | Description |
|-------|---------|-------------|
| `initialize` | 0 | Initializing pipeline |
| `expand` | 5 | Query expansion with LLM |
| `search` | 15 | Multi-provider search |
| `fetch` | 40 | Fetching URLs and extracting markdown |
| `extract` | 60 | LLM-powered content extraction |
| `synthesize` | 80 | Answer synthesis with citations |
| `complete` | 100 | Pipeline completed successfully |
| `error` | 0 | Pipeline failed |

## Event Format

Each SSE event is a single-line JSON object:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "stage": "search",
  "percent": 20,
  "message": "Searching across 3 providers",
  "timestamp": "2025-05-04T10:30:45.123456+00:00"
}
```

## Memory and Resource Management

### Automatic Cleanup

- Progress events are queued in memory per job
- After 5 minutes of completion, the job tracker is cleaned up
- Queues are thread-safe via asyncio.Lock

### Manual Cleanup

```python
from loom.progress import get_progress_tracker

tracker = get_progress_tracker()
await tracker.cleanup("job-id")
```

### Monitoring Active Jobs

```python
from loom.progress import get_progress_tracker

tracker = get_progress_tracker()
active_jobs = await tracker.list_jobs()
print(f"Currently tracking {len(active_jobs)} jobs")
```

## Testing

Unit tests are located in `tests/test_progress.py`:

```bash
pytest tests/test_progress.py -v
```

Key test coverage:

- Progress event creation and immutability
- Percent value clamping (0-100)
- Input validation (non-empty job_id and stage)
- Event streaming with timeout
- SSE format validation
- Job cleanup
- Singleton pattern
- End-to-end pipeline simulation

## Error Handling

### Client-side

```javascript
const eventSource = new EventSource(`/progress/${jobId}`);

eventSource.onerror = (error) => {
  if (eventSource.readyState === EventSource.CLOSED) {
    console.log("Stream closed");
  } else if (eventSource.readyState === EventSource.CONNECTING) {
    console.log("Reconnecting...");
  } else {
    console.error("Unexpected error:", error);
  }
};
```

### Server-side

The `finally` block in `research_deep_with_progress` ensures cleanup even on error:

```python
finally:
    # Clean up tracker after 5 minutes
    try:
        await asyncio.sleep(5)
        await tracker.cleanup(job_id)
    except Exception as exc:
        logger.warning("Cleanup error: %s", exc)
```

## Performance Considerations

1. **Async Queue Overhead**: Minimal — O(1) queue operations
2. **Memory Per Job**: ~1KB baseline + event queue size
3. **No External Dependencies**: Uses asyncio only
4. **Timeout Protection**: 300-second default timeout on stream
5. **Graceful Degradation**: Errors in reporting don't block main pipeline

## Limitations

- Events are queue-based, not persisted to disk
- Streams timeout after 300 seconds of inactivity
- No event deduplication (same stage/percent can be repeated)
- Queue size unbounded (assumes reasonable report frequency)

## Future Enhancements

Potential improvements for future versions:

1. **Redis Backend**: Persist events to Redis for cross-server support
2. **Webhook Callbacks**: Post progress to external endpoints
3. **Event Filtering**: Client-side filtering of stages/percent ranges
4. **Metrics Export**: Prometheus-compatible progress metrics
5. **History API**: Retrieve past progress for completed jobs
