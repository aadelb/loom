# OpenTelemetry Distributed Tracing Integration

## Overview

Loom includes optional OpenTelemetry (OTel) distributed tracing support with **zero overhead when disabled**. When enabled, it exports trace data via OTLP (OpenTelemetry Protocol) to a compatible backend (Jaeger, Datadog, New Relic, etc.).

### Key Features

- **Zero Overhead When Disabled**: No performance impact if `OTEL_ENABLED=false`
- **Graceful Degradation**: Continues normally if OpenTelemetry packages missing
- **Tool Execution Tracing**: Automatic span creation for each tool call
- **Attribute Recording**: Tool name, duration, success/failure, error type
- **Context Propagation**: Trace context flows across tool chains
- **Batch Export**: Efficient OTLP export via BatchSpanProcessor

## Installation

OpenTelemetry support requires optional dependencies:

```bash
# Install with all extras
pip install -e ".[all]"

# Or install specific packages
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

If packages are missing, Loom gracefully skips telemetry without errors.

## Configuration

Enable and configure via environment variables:

```bash
# Enable tracing (default: false)
export OTEL_ENABLED=true

# OTLP gRPC endpoint (default: http://localhost:4317)
export OTEL_ENDPOINT=http://otel-collector.example.com:4317

# Service identifier (default: loom-mcp)
export OTEL_SERVICE_NAME=loom-production
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | `false` | Activate tracing (no overhead if false) |
| `OTEL_ENDPOINT` | `http://localhost:4317` | OTLP gRPC collector endpoint |
| `OTEL_SERVICE_NAME` | `loom-mcp` | Service name in telemetry |

## Usage Patterns

### Pattern 1: Context Manager (Recommended)

```python
from loom.otel import tool_span, record_tool_span
import time

async def research_fetch(url: str) -> dict:
    start = time.time()
    with tool_span("research_fetch") as span:
        try:
            result = await fetch_url(url)
            duration_ms = (time.time() - start) * 1000
            record_tool_span(span, "research_fetch", duration_ms, True)
            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            record_tool_span(
                span, "research_fetch", duration_ms, False,
                error_type=type(e).__name__
            )
            raise
```

### Pattern 2: Decorator (Automatic)

```python
from loom.otel import trace_tool_execution

@trace_tool_execution
async def research_spider(urls: list[str]) -> dict:
    """Automatically traced async tool."""
    return await fetch_all(urls)

@trace_tool_execution
def sync_tool(param: str) -> dict:
    """Automatically traced sync tool."""
    return process(param)
```

The decorator automatically:
- Creates spans with function name
- Records duration in milliseconds
- Captures success/failure status
- Logs exception type on failure

### Pattern 3: Initialization in Server

```python
# In server.py startup
from loom.otel import init_telemetry, shutdown_telemetry

async def create_app():
    """Initialize Loom MCP server."""
    # Initialize tracing (safe if disabled or packages missing)
    init_telemetry()
    
    # ... rest of setup ...
    
    return app

# At shutdown
def cleanup():
    shutdown_telemetry()  # Flushes pending spans
```

## Span Attributes

Each tool execution span includes standard attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `tool.name` | string | Function name (e.g., "research_fetch") |
| `tool.duration_ms` | float | Execution time in milliseconds |
| `tool.success` | boolean | Whether execution completed without error |
| `tool.error_type` | string | Exception class name (only on failure) |
| `service.name` | string | Service identifier from `OTEL_SERVICE_NAME` |
| `service.version` | string | Service version (default: "1.0.0") |

### Example Span

```json
{
  "name": "research_fetch",
  "attributes": {
    "tool.name": "research_fetch",
    "tool.duration_ms": 245.5,
    "tool.success": true,
    "service.name": "loom-mcp",
    "service.version": "1.0.0"
  },
  "start_time": "2026-05-03T12:34:56.789Z",
  "end_time": "2026-05-03T12:35:01.034Z"
}
```

Failed span example:

```json
{
  "name": "research_fetch",
  "attributes": {
    "tool.name": "research_fetch",
    "tool.duration_ms": 50.2,
    "tool.success": false,
    "tool.error_type": "ValidationError",
    "service.name": "loom-mcp"
  },
  "events": [
    {
      "name": "exception",
      "attributes": {
        "exception.type": "ValidationError",
        "exception.message": "Invalid URL format"
      }
    }
  ]
}
```

## Integration with External Backends

### Jaeger (Local Development)

Start Jaeger all-in-one container:

```bash
docker run -d \
  -p 4317:4317 \
  -p 16686:16686 \
  jaegertracing/all-in-one
```

Configure Loom:

```bash
export OTEL_ENABLED=true
export OTEL_ENDPOINT=http://localhost:4317
loom serve
```

Access Jaeger UI at `http://localhost:16686`

### Datadog

Configure environment:

```bash
export OTEL_ENABLED=true
export OTEL_ENDPOINT=http://dd-agent:4317
export OTEL_SERVICE_NAME=loom-mcp
# Also configure standard Datadog env vars
export DD_ENV=production
export DD_VERSION=1.0.0
```

### New Relic

```bash
export OTEL_ENABLED=true
export OTEL_ENDPOINT=https://otlp.nr-data.net:4317
export OTEL_SERVICE_NAME=loom-mcp
export OTEL_EXPORTER_OTLP_HEADERS=api-key=${NEW_RELIC_LICENSE_KEY}
```

### Honeycomb

```bash
export OTEL_ENABLED=true
export OTEL_ENDPOINT=https://api.honeycomb.io:443
export OTEL_SERVICE_NAME=loom-mcp
export OTEL_EXPORTER_OTLP_HEADERS=x-honeycomb-team=${HONEYCOMB_API_KEY}
```

## Performance Considerations

### Disabled Tracing (OTEL_ENABLED=false)

- **Zero Overhead**: No spans created, no export logic runs
- **Fallback Checks**: Minimal guard statements only
- **Recommended for**: Local development, testing, cost-sensitive deployments

### Enabled Tracing (OTEL_ENABLED=true)

- **Batch Export**: Spans batched (default: 512 spans per batch)
- **Async Export**: Background thread handles export
- **Overhead**: ~1-2ms per tool call for span creation + attributes
- **Network Calls**: Periodic batches to OTLP collector (typical: 5s intervals)

### Optimization Tips

1. **Adjust Batch Size**:
   ```python
   # In otel.py (advanced configuration)
   BatchSpanProcessor(exporter, max_queue_size=2048, max_export_batch_size=1024)
   ```

2. **Sample High-Volume Tools**:
   ```python
   # Sampler configuration (for OTLP exporter)
   from opentelemetry.sdk.trace import ProbabilitySampler
   # Sample 10% of traces
   tracer_provider.sampler = ProbabilitySampler(0.1)
   ```

3. **Export Asynchronously**:
   - Default BatchSpanProcessor already uses async export
   - No blocking of tool execution

## Troubleshooting

### "OpenTelemetry packages not installed"

Install optional dependencies:

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

Or reinstall with extras:

```bash
pip install -e ".[all]"
```

### Traces Not Appearing in Backend

1. Verify `OTEL_ENABLED=true`:
   ```bash
   echo $OTEL_ENABLED
   ```

2. Check endpoint connectivity:
   ```bash
   nc -zv localhost 4317
   ```

3. Review logs for initialization messages:
   ```bash
   loom serve 2>&1 | grep -i otel
   ```

4. Verify service receives traces:
   - Jaeger: http://localhost:16686/search
   - Datadog: APM → Services
   - New Relic: APM → Services

### High Latency or Dropped Spans

1. Increase batch processor capacity:
   ```python
   BatchSpanProcessor(exporter, max_queue_size=4096)
   ```

2. Reduce span sampling to 50%:
   ```python
   from opentelemetry.sdk.trace import ProbabilitySampler
   sampler = ProbabilitySampler(0.5)
   ```

3. Increase network timeout for slow collectors:
   ```python
   exporter = OTLPSpanExporter(endpoint=endpoint, timeout=30)
   ```

## API Reference

### `init_telemetry() -> None`

Initialize OpenTelemetry with OTLP exporter.

- Reads `OTEL_ENABLED`, `OTEL_ENDPOINT`, `OTEL_SERVICE_NAME` from environment
- Gracefully skips if packages missing or disabled
- Safe to call multiple times (idempotent)

### `shutdown_telemetry() -> None`

Gracefully shutdown and flush pending spans.

- Should be called at application shutdown
- Flushes BatchSpanProcessor queue
- Safe to call even if not initialized

### `is_enabled() -> bool`

Check if OpenTelemetry tracing is active.

Returns `True` only if initialization successful and `OTEL_ENABLED=true`.

### `get_tracer() -> Any`

Get the global tracer instance.

- Returns real tracer if enabled
- Returns no-op tracer if disabled or packages missing
- Safe to call anytime

### `record_tool_span(span, tool_name, duration_ms, success, error_type=None) -> None`

Record tool execution attributes to a span.

**Parameters**:
- `span`: OpenTelemetry span instance
- `tool_name`: Function name (string)
- `duration_ms`: Execution time in milliseconds (float)
- `success`: Whether execution succeeded (bool)
- `error_type`: Exception class name on failure (optional string)

### `tool_span(tool_name) -> contextmanager`

Context manager for creating a tool execution span.

```python
with tool_span("research_fetch") as span:
    result = fetch_url(url)
    record_tool_span(span, "research_fetch", duration_ms, True)
```

Yields `None` if telemetry disabled.

### `@trace_tool_execution`

Decorator for automatic tool tracing.

Works with both sync and async functions:

```python
@trace_tool_execution
async def async_tool(url: str) -> dict:
    return await fetch(url)

@trace_tool_execution
def sync_tool(query: str) -> dict:
    return search(query)
```

Automatically:
- Creates spans
- Records timing
- Captures exceptions
- Sets success/failure status

## Integration with server.py

The `_wrap_tool()` function in `server.py` can integrate OpenTelemetry:

```python
from loom.otel import tool_span, record_tool_span
import time

def _wrap_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        with tool_span(func.__name__) as span:
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                record_tool_span(span, func.__name__, duration_ms, True)
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                record_tool_span(
                    span, func.__name__, duration_ms, False,
                    error_type=type(e).__name__
                )
                raise
    return async_wrapper
```

This enables distributed tracing across the entire Loom MCP service.

## Example: Full Integration

```python
# src/loom/server.py
import os
from loom.otel import init_telemetry, shutdown_telemetry
from mcp.server import FastMCP

app = FastMCP("loom")

def setup():
    """Initialize server with optional tracing."""
    if os.getenv("OTEL_ENABLED", "").lower() == "true":
        init_telemetry()
        print("OpenTelemetry tracing enabled")
    else:
        print("OpenTelemetry tracing disabled")
    
    # Register tools, etc.
    register_tools(app)

def teardown():
    """Cleanup at shutdown."""
    shutdown_telemetry()

if __name__ == "__main__":
    setup()
    # Start server
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8787)
    # At shutdown:
    teardown()
```

## Monitoring & Metrics

Common queries in observability platforms:

### Jaeger (PromQL)

```
# Average tool duration by tool name
rate(loom_tool_duration_seconds_sum[5m]) / rate(loom_tool_duration_seconds_count[5m])

# Error rate by tool
rate(loom_tool_errors_total[5m]) / rate(loom_tool_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(loom_tool_duration_seconds_bucket[5m]))
```

### Datadog

```
# Average duration
avg:loom.tool.duration_ms{*}

# Error count by tool
sum:loom.tool.errors{*} by {tool.name}

# Percentile latencies
p95:loom.tool.duration_ms{*}
p99:loom.tool.duration_ms{*}
```

## Best Practices

1. **Enable in Production**: Use distributed tracing to understand production behavior
2. **Disable in Tests**: Set `OTEL_ENABLED=false` for unit tests (faster, no overhead)
3. **Sampling**: Use probabilistic sampling for high-volume tools
4. **Context Propagation**: Ensure trace context flows across async operations
5. **Resource Cleanup**: Always call `shutdown_telemetry()` at application shutdown
6. **Error Handling**: Exceptions are automatically recorded; no manual logging needed

## Limitations

- **Async-only export**: Tracing export does not block tool execution
- **No metrics**: Module exports spans only; metrics require additional instrumentation
- **No logs correlation**: Logs and traces not currently correlated via trace ID
- **No baggage**: W3C Baggage propagation not yet implemented

See `src/loom/otel.py` for implementation details.
