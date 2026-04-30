# Structured Logging for Loom MCP Server

Loom implements production-grade structured logging with JSON format support for tool invocations, request tracing, and compliance auditing.

## Overview

Every tool invocation in Loom is logged with:
- **Timestamp** (ISO 8601 UTC)
- **Request ID** (unique per request, for correlation)
- **Tool name** (e.g., `research_fetch`, `research_spider`)
- **Duration** (milliseconds)
- **Status** (ok, error, timeout, etc.)
- **Cache hit** (boolean)
- **Client ID** (session ID, user ID, or API key)

## JSON Log Format

### Basic Tool Invocation Log
```json
{
  "timestamp": "2025-04-29T14:30:45.123456+00:00",
  "level": "INFO",
  "logger": "loom.tools.fetch",
  "message": "Tool invocation completed",
  "request_id": "a1b2c3d4e5f6g7h8",
  "tool_name": "research_fetch",
  "duration_ms": 1250,
  "status": "ok",
  "cache_hit": true,
  "client_id": "user-123"
}
```

### Error Log with Exception
```json
{
  "timestamp": "2025-04-29T14:30:46.234567+00:00",
  "level": "ERROR",
  "logger": "loom.tools.fetch",
  "message": "Tool invocation failed",
  "request_id": "a1b2c3d4e5f6g7h8",
  "tool_name": "research_fetch",
  "duration_ms": 250,
  "status": "error",
  "cache_hit": false,
  "client_id": "api_key",
  "exception": "Traceback (most recent call last):\n  ..."
}
```

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOOM_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOOM_LOG_FORMAT` | `text` | Log format (json or text) |

### Setup in Code

```python
from loom.logging_config import setup_logging, install_tracing

# Initialize logging
setup_logging(log_level="INFO", log_format="json")

# Install request ID tracing
install_tracing()
```

## Usage

### Basic Logging

```python
import logging
from loom.logging_config import log_tool_invocation

logger = logging.getLogger("loom.tools.custom")

# Log a tool invocation
log_tool_invocation(
    tool_name="research_custom",
    duration_ms=1250,
    status="ok",
    cache_hit=True,
    client_id="user-123",
    message="Custom tool completed successfully",
    logger=logger
)
```

### In Tool Wrapper

```python
import time
import logging
from loom.logging_config import log_tool_invocation
from loom.tracing import get_request_id

async def wrapped_tool_call(tool_func, tool_name, *args, **kwargs):
    """Wrap a tool with structured logging."""
    start_time = time.time()
    status = "ok"
    client_id = get_request_id()
    
    try:
        # Execute tool
        result = await tool_func(*args, **kwargs)
        # Check if result came from cache
        cache_hit = getattr(result, '_from_cache', False)
        return result
    except Exception as e:
        status = "error"
        logger.exception(f"Tool {tool_name} failed")
        raise
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        log_tool_invocation(
            tool_name=tool_name,
            duration_ms=duration_ms,
            status=status,
            cache_hit=cache_hit,
            client_id=client_id,
        )
```

## Request ID Correlation

Request IDs are automatically injected into all log records via `ContextVar`. Each request gets a unique 16-character hexadecimal ID.

### Reading Request ID

```python
from loom.tracing import get_request_id

request_id = get_request_id()  # Returns current request ID or empty string
```

### Setting Request ID (usually done by framework)

```python
from loom.tracing import new_request_id

rid = new_request_id()  # Generates and sets a new request ID
```

## Log Levels

| Level | Purpose |
|-------|---------|
| DEBUG | Detailed information for debugging (verbose output) |
| INFO | Tool invocations, successful operations |
| WARNING | Deprecated features, suspicious activity |
| ERROR | Errors, exceptions, failed operations |
| CRITICAL | System failures, unrecoverable errors |

### Examples by Level

```python
logger = logging.getLogger("loom.tools")

# DEBUG - detailed tracing
logger.debug("fetching_url url=https://example.com headers=%s", headers)

# INFO - successful operations
logger.info("Tool invocation completed")  # Use log_tool_invocation() for this

# WARNING - unusual but handled conditions
logger.warning("rate_limit_approaching rate_limit=95%")

# ERROR - failures
logger.error("fetch_failed url=%s error=%s", url, str(e))

# CRITICAL - unrecoverable
logger.critical("cache_corrupted path=%s", cache_path)
```

## Text vs JSON Output

### Text Format (Default)

Plain text format useful for local development and manual inspection:

```
2025-04-29 14:30:45,123 - loom.tools.fetch - INFO - [a1b2c3d4e5f6g7h8] Tool invocation completed
```

### JSON Format (Production)

Machine-parseable JSON format for log aggregation, analysis, and compliance:

```json
{"timestamp": "2025-04-29T14:30:45.123456+00:00", "level": "INFO", ...}
```

### Switching Formats

```python
# Use JSON in production
setup_logging(log_format="json", log_level="INFO")

# Use text for development
setup_logging(log_format="text", log_level="DEBUG")

# Or via environment variable
export LOOM_LOG_LEVEL=DEBUG
```

## Audit Integration

Tool invocations are logged both to:
1. **Structured logs** (this module) - for monitoring, debugging, and tracing
2. **Audit logs** (audit.py) - for compliance and tamper-proof records

Both systems are independent but complementary:

```python
from loom.logging_config import log_tool_invocation
from loom.audit import log_invocation

# Structured logging (for operations/monitoring)
log_tool_invocation(
    tool_name="research_fetch",
    duration_ms=1250,
    status="ok",
    cache_hit=True,
    client_id="user-123",
)

# Audit logging (for compliance)
log_invocation(
    client_id="user-123",
    tool_name="research_fetch",
    params={"url": "https://example.com"},
    result_summary="success: 5000 bytes",
    duration_ms=1250,
    status="success",
)
```

## Log Aggregation

For production deployments with log aggregation (ELK, Datadog, etc.):

1. Configure JSON format: `export LOOM_LOG_FORMAT=json`
2. Logs are automatically sent to stdout
3. Aggregation platform captures and indexes JSON
4. Query by request_id for full request trace

### Example Queries

```sql
-- Find all operations for a user
SELECT * FROM logs WHERE client_id = "user-123"

-- Find slow operations
SELECT * FROM logs WHERE duration_ms > 5000

-- Find errors
SELECT * FROM logs WHERE status = "error"

-- Trace a request end-to-end
SELECT * FROM logs WHERE request_id = "a1b2c3d4e5f6g7h8"
```

## Best Practices

### 1. Log at Appropriate Levels
- DEBUG: Detailed diagnostic info
- INFO: Successful operations
- WARNING: Potential issues
- ERROR: Failures
- CRITICAL: System emergencies

### 2. Include Context
```python
# GOOD: Includes relevant context
logger.info("search_completed", extra={
    "query": "ai safety",
    "results": 42,
    "duration_ms": 500,
})

# POOR: Vague
logger.info("done")
```

### 3. Use Tool Invocation Logging
```python
# GOOD: Structured tool logging
log_tool_invocation(
    tool_name="research_fetch",
    duration_ms=1250,
    status="ok",
    cache_hit=True,
    client_id="user-123",
)

# ACCEPTABLE: Generic logging (less structured)
logger.info("Tool %s completed in %dms", "research_fetch", 1250)
```

### 4. Request ID Correlation
Always ensure request ID is available for multi-step operations:

```python
from loom.tracing import get_request_id

request_id = get_request_id()
logger.info("step_completed step=fetch request_id=%s", request_id)
```

### 5. Error Logging with Context
```python
try:
    result = await fetch_url(url)
except Exception as e:
    logger.error(
        "fetch_failed url=%s error=%s request_id=%s",
        url, str(e), get_request_id(),
        exc_info=True  # Include full traceback
    )
    raise
```

## Troubleshooting

### Logs not appearing

1. Check log level: `export LOOM_LOG_LEVEL=DEBUG`
2. Verify setup_logging called: `from loom.logging_config import setup_logging; setup_logging()`
3. Check logger name matches: `logging.getLogger("loom.*")`

### JSON parsing errors

1. Check for non-serializable objects in extra fields
2. Ensure all tool fields are JSON-compatible types
3. Verify exception tracebacks are included, not objects

### Missing request IDs

1. Verify `install_tracing()` was called during startup
2. Check `new_request_id()` is called for each request
3. Ensure ContextVar is properly propagated in async code

## API Reference

### `setup_logging()`

Configure root logger with JSON or text formatting.

```python
def setup_logging(
    log_level: str = "INFO",
    log_format: str = "text",
    logger_name: str = "loom",
) -> None:
    """
    Args:
        log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_format: "json" or "text"
        logger_name: Target logger name (default: "loom")
    """
```

### `log_tool_invocation()`

Log a structured tool invocation record.

```python
def log_tool_invocation(
    tool_name: str,
    duration_ms: int,
    status: str,
    cache_hit: bool = False,
    client_id: str | None = None,
    message: str = "Tool invocation completed",
    logger: logging.Logger | None = None,
) -> None:
    """
    Args:
        tool_name: Name of tool invoked
        duration_ms: Execution time in milliseconds
        status: "ok", "error", "timeout", etc.
        cache_hit: Whether result came from cache
        client_id: Client identifier (session/user/API key)
        message: Log message
        logger: Logger instance (default: loom.tools)
    """
```

### `get_request_id()`

Get the current request ID.

```python
from loom.tracing import get_request_id

request_id = get_request_id()  # Returns hex string or ""
```

### `new_request_id()`

Generate and set a new request ID.

```python
from loom.tracing import new_request_id

rid = new_request_id()  # Returns 16-char hex string
```

### `install_tracing()`

Install request ID filter on all root logger handlers.

```python
from loom.tracing import install_tracing

install_tracing()  # Call once at startup
```

## See Also

- [audit.py](../src/loom/audit.py) - Tamper-proof compliance audit logs
- [tracing.py](../src/loom/tracing.py) - Request ID correlation via ContextVar
- [server.py](../src/loom/server.py) - Tool registration and wrapping
