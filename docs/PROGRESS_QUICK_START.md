# SSE Progress Streaming - Quick Start Guide

## 30-Second Setup

### 1. Start the Loom server

```bash
loom serve
# Server starts on http://localhost:8787
```

### 2. Subscribe to a job's progress (in another terminal)

```bash
# Replace job-id with an actual UUID from your research task
curl -N http://localhost:8787/progress/550e8400-e29b-41d4-a716-446655440000
```

You'll see SSE events streaming:

```
data: {"job_id":"550e8400-e29b-41d4-a716-446655440000","stage":"search","percent":20,...}

data: {"job_id":"550e8400-e29b-41d4-a716-446655440000","stage":"fetch","percent":50,...}
```

## Using research_deep_with_progress

### Python Example

```python
import asyncio
from loom.tools.deep import research_deep_with_progress

async def main():
    # Start research with automatic job_id generation
    result = await research_deep_with_progress(
        query="best practices for Python asyncio",
        depth=2,
    )
    
    # Get the job_id from response
    job_id = result["job_id"]
    print(f"Job ID: {job_id}")
    
    # In another process/terminal, subscribe with:
    # curl -N http://localhost:8787/progress/{job_id}

asyncio.run(main())
```

### Custom Job ID

```python
from loom.progress import create_job_id
from loom.tools.deep import research_deep_with_progress

async def main():
    job_id = create_job_id()
    
    result = await research_deep_with_progress(
        query="asyncio tutorial",
        job_id=job_id,
    )
    
    return job_id

my_job_id = asyncio.run(main())
```

## JavaScript Browser Client

```html
<!DOCTYPE html>
<html>
<head>
    <title>Loom Progress Streaming</title>
    <style>
        #progress-bar { width: 100%; height: 20px; background: #ddd; }
        #progress-fill { height: 100%; width: 0%; background: #4CAF50; transition: width 0.3s; }
    </style>
</head>
<body>
    <h1>Research Progress</h1>
    <div id="progress-bar">
        <div id="progress-fill"></div>
    </div>
    <p>Status: <span id="status">Waiting...</span></p>
    
    <script>
        const jobId = "550e8400-e29b-41d4-a716-446655440000"; // From research task
        const eventSource = new EventSource(`/progress/${jobId}`);
        
        eventSource.onmessage = (event) => {
            const progress = JSON.parse(event.data);
            
            // Update progress bar
            document.getElementById("progress-fill").style.width = progress.percent + "%";
            document.getElementById("status").textContent = 
                `${progress.stage}: ${progress.message}`;
            
            // Stop listening on completion
            if (progress.stage === "complete" || progress.stage === "error") {
                eventSource.close();
                console.log("Stream closed");
            }
        };
        
        eventSource.onerror = (error) => {
            console.error("Connection error:", error);
            eventSource.close();
        };
    </script>
</body>
</html>
```

## Python Async Client (httpx)

```python
import json
import httpx

def stream_progress(job_id: str) -> None:
    """Stream progress events for a job."""
    with httpx.stream("GET", f"http://localhost:8787/progress/{job_id}") as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])  # Remove "data: " prefix
                percent = event["percent"]
                stage = event["stage"]
                message = event["message"]
                
                # Print with progress bar
                bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
                print(f"[{bar}] {percent}% - {stage}: {message}")
                
                if stage in ("complete", "error"):
                    break

# Usage
stream_progress("550e8400-e29b-41d4-a716-446655440000")
```

## List Active Jobs

```bash
# Get list of all currently-tracked jobs
curl http://localhost:8787/progress
```

Response:

```json
{
  "active_jobs": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ],
  "count": 2
}
```

## Progress Stages

The standard pipeline reports these stages:

| Stage | % | Meaning |
|-------|---|---------|
| initialize | 0 | Starting up |
| expand | 5 | Query expansion |
| search | 15 | Searching for content |
| fetch | 40 | Downloading URLs |
| extract | 60 | LLM extraction |
| synthesize | 80 | Answer synthesis |
| complete | 100 | Done! |
| error | 0 | Failed |

## Common Patterns

### Pattern 1: Fire-and-Forget with Monitoring

```python
# Start task
result = await research_deep_with_progress(query="topic")
job_id = result["job_id"]

# Return job_id to client for monitoring
return {"job_id": job_id, "status": "processing"}

# Client polls: GET /progress/{job_id}
```

### Pattern 2: Wait and Stream

```python
# Start task
result = await research_deep_with_progress(query="topic")

# Results already available, but client could monitor if it started earlier
return result
```

### Pattern 3: Custom Progress Reporting

```python
from loom.progress import get_progress_tracker

async def my_long_task(job_id: str = None):
    if not job_id:
        from loom.progress import create_job_id
        job_id = create_job_id()
    
    tracker = get_progress_tracker()
    
    # Stage 1
    await tracker.report_progress(job_id, "stage1", 25, "Processing...")
    # ... do work ...
    
    # Stage 2
    await tracker.report_progress(job_id, "stage2", 75, "Almost done...")
    # ... do work ...
    
    return {"result": "data", "job_id": job_id}
```

## Troubleshooting

### "Connection refused" (server not running)

```bash
loom serve
# Server should start on port 8787
```

### No events appearing

1. Make sure the job_id is correct
2. Verify the task is actually running
3. Check `/progress` endpoint to list active jobs

### Connection times out after 300 seconds

This is expected. The stream closes if no events are sent for 5 minutes. This is a safety feature to prevent hung connections.

### How to test locally

```bash
# Terminal 1: Start server
loom serve

# Terminal 2: Start a research task (if MCP client available)
python3 -c "
import asyncio
from loom.tools.deep import research_deep_with_progress

async def test():
    result = await research_deep_with_progress(
        query='test query',
        depth=1
    )
    print('Job ID:', result['job_id'])

asyncio.run(test())
"

# Terminal 3: Stream progress
# Copy the Job ID from Terminal 2 and use it:
curl -N http://localhost:8787/progress/PASTE_JOB_ID_HERE
```

## Next Steps

1. Read [SSE_PROGRESS_STREAMING.md](./SSE_PROGRESS_STREAMING.md) for detailed docs
2. Check [examples/progress_streaming_demo.py](../examples/progress_streaming_demo.py)
3. Run tests: `pytest tests/test_progress.py -v`
4. Integrate into your own tools following the "Custom Progress Reporting" pattern above
