# New Features Added

## Task 1: Structured JSON Logging (#388)

### Summary
Implemented structured JSON logging for the Loom MCP server with optional text format fallback.

### Files Modified
- **src/loom/logging_config.py** (NEW) - Provides `JsonFormatter` class and `setup_logging()` function
- **src/loom/server.py** - Updated `create_app()` to use new logging setup with `LOG_FORMAT` configuration
- **tests/test_logging_config.py** (NEW) - Comprehensive tests for JSON and text logging

### Configuration
The logging format can be configured via:
1. Environment variable: `LOG_FORMAT=json` or `LOG_FORMAT=text`
2. Config file: `LOG_FORMAT` setting in config.json
3. Default: `text` (plain text format for development)

### JSON Log Format
When `LOG_FORMAT=json`, logs are emitted as JSON objects with the following fields:
```json
{
  "timestamp": "2026-04-28 12:34:56,789",
  "level": "INFO",
  "logger": "loom.server",
  "message": "User action completed",
  "request_id": "abc123def456"
}
```

Fields included (when available):
- `timestamp`: ISO format timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `logger`: Logger name
- `message`: Formatted log message
- `request_id`: Context variable from tracing (if set)
- `exception`: Full exception traceback (only for ERROR/EXCEPTION level logs)

### Usage
```python
# In server.py
log_level = config.get("LOG_LEVEL", "INFO")
log_format = os.environ.get("LOG_FORMAT", config.get("LOG_FORMAT", "text"))
setup_logging(log_level=log_level, log_format=log_format)

# Start server with JSON logging
LOG_FORMAT=json python -m loom serve
```

---

## Task 2: Rate Limit Persistence (#391)

### Summary
Implemented optional SQLite persistence for rate limiter state, allowing rate limits to survive application restarts.

### Files Modified
- **src/loom/rate_limiter.py** - Enhanced with SQLite persistence layer
- **src/loom/config.py** - Added `RATE_LIMIT_PERSIST` configuration option
- **tests/test_rate_limiter_persistence.py** (NEW) - 12 tests for persistence functionality

### How It Works
When enabled, the rate limiter saves timestamps of rate-limited calls to `~/.loom/rate_limits.db`:

1. **Storage**: SQLite database with a single `rate_limits` table:
   ```sql
   CREATE TABLE rate_limits (
     category TEXT NOT NULL,      -- "async" or "sync"
     key TEXT NOT NULL,           -- API key or identifier
     timestamp REAL NOT NULL,     -- Unix timestamp of the call
     PRIMARY KEY (category, key, timestamp)
   )
   ```

2. **Load on Startup**: When a RateLimiter is instantiated, it loads recent timestamps from the DB
3. **Save on Check**: Each rate limit check saves the timestamp to persist state
4. **Cleanup**: Old entries (>window_seconds) are automatically cleaned up

### Configuration
Enable persistence via:
1. Environment variable: `RATE_LIMIT_PERSIST=true`
2. Config file: `RATE_LIMIT_PERSIST: true` in config.json
3. Default: `false` (in-memory only, for backward compatibility)

### Benefits
- **Resilience**: Rate limits survive process restarts/crashes
- **Consistency**: Multiple worker processes can share state via SQLite
- **Performance**: Cleanup routine removes old entries automatically
- **Backward Compatible**: Off by default, doesn't affect existing installations

### Implementation Details
- **Thread-safe**: Uses `sqlite3.connect()` with timeout for concurrent access
- **Async-compatible**: Both `RateLimiter` (async) and `SyncRateLimiter` (sync) support persistence
- **Error handling**: Database errors are logged as warnings, doesn't block rate limiting
- **Automatic cleanup**: On each check, entries older than `window_seconds` are removed

### API Unchanged
The public interfaces remain identical:
```python
# Existing code continues to work without changes
@rate_limited("search")
async def research_search(query: str) -> dict:
    ...

# When RATE_LIMIT_PERSIST=true, state persists across restarts
```

### Troubleshooting
- Database location: `~/.loom/rate_limits.db`
- If corrupted: Delete the file and restart (state resets)
- Permissions issues: Ensure `~/.loom/` directory is writable
- Performance: SQLite connection timeout is 5 seconds per operation

---

## Testing

Run tests locally:
```bash
PYTHONPATH=src pytest tests/test_logging_config.py -v
PYTHONPATH=src pytest tests/test_rate_limiter_persistence.py -v
```

Both test suites pass with comprehensive coverage of:
- JSON formatter behavior
- Log level configuration
- Request ID injection
- Exception logging
- Rate limit persistence across restarts
- Concurrent access patterns
- Cleanup of old entries
