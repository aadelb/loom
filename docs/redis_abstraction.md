# Redis Abstraction Layer

## Overview

The Redis abstraction layer (`src/loom/redis_store.py`) provides a unified interface for distributed state management across multiple uvicorn workers. It enables:

- **Shared rate limiting** across 4+ worker processes
- **Distributed caching** with TTL and prefix-based clearing
- **Session management** with automatic expiry
- **Cost tracking** for billing integration
- **Distributed locking** for coordinating shared resources

### Key Features

1. **Seamless Fallback**: If Redis is unavailable, automatically falls back to in-memory storage
2. **Connection Pooling**: Max 20 connections for efficient resource usage
3. **Type-Safe**: Full type hints and mypy strict mode compliance
4. **Async-First**: Built on `redis.asyncio` for async/await patterns
5. **Zero Configuration**: Works with defaults; configure via `REDIS_URL` env var

## Architecture

### When to Use Redis vs In-Memory

| Scenario | Storage | Why |
|----------|---------|-----|
| Single worker (dev) | In-memory | No need for IPC overhead |
| Multi-worker production | Redis | Shared state across processes |
| Redis unavailable | In-memory (fallback) | Graceful degradation |
| Testing | In-memory | Forced via `redis_url=""` |

### Data Structures

Redis uses these key structures:

- **Rate Limits**: Sorted sets (`ratelimit:{user}:{category}`) with timestamps as scores
- **Cache**: Strings with TTL (`cache:*`) storing JSON
- **Sessions**: Strings with TTL (`session:*`) storing JSON
- **Costs**: Strings with TTL (`cost:{customer}`) storing floats
- **Locks**: Strings with NX and expiry (`lock:*`)

## Installation

Redis is an optional dependency:

```bash
# Install with Redis support
pip install -e ".[all]"  # or
pip install redis[hiredis]>=5.0
```

The `hiredis` extra provides faster C-based parsing.

## Configuration

### Environment Variables

```bash
# Default: redis://localhost:6379
export REDIS_URL="redis://localhost:6379"

# Or with auth
export REDIS_URL="redis://:password@localhost:6379/0"

# Force in-memory mode
export REDIS_URL=""
```

### Programmatic Configuration

```python
from loom.redis_store import RedisStore

# Custom configuration
store = RedisStore(
    redis_url="redis://production.example.com:6379",
    max_connections=50
)

await store.connect()
```

## API Reference

### Rate Limiting

Implements sliding window counters for distributed rate limiting:

```python
store = await get_redis_store()

# Check if call is allowed
allowed = await store.rate_limit_check(
    user_id="user_123",
    category="search",
    limit=30,  # max calls
    window_seconds=60
)

if not allowed:
    return {"error": "rate_limit_exceeded"}
```

**Use Case**: Replace `rate_limiter.py` with Redis backend for multi-worker scenarios.

### Caching

Key-value storage with TTL:

```python
# Get cached value
value = await store.cache_get("cache:research_123")

# Set with TTL
await store.cache_set(
    "cache:research_123",
    {"results": [1, 2, 3]},
    ttl_seconds=3600
)

# Delete
await store.cache_delete("cache:research_123")

# Clear by prefix
count = await store.cache_clear_prefix("cache:fetch:")
print(f"Deleted {count} entries")
```

**Use Case**: Accelerate repeated queries; share cache across workers.

### Sessions

Browser session storage with TTL:

```python
# Get session
session = await store.session_get("browser_session_abc123")

# Store session
await store.session_set(
    "browser_session_abc123",
    {
        "cookies": {"session_id": "xyz"},
        "user_agent": "Mozilla/5.0...",
        "created_at": "2025-05-03T..."
    },
    ttl_seconds=86400  # 24 hours
)

# Cleanup
await store.session_delete("browser_session_abc123")
```

**Use Case**: Maintain persistent browser sessions across worker restarts.

### Cost Tracking

Accumulate costs per customer:

```python
# Track cost (accumulates)
await store.cost_track("customer_456", 10.50)
await store.cost_track("customer_456", 5.25)

# Get total
total = await store.cost_get("customer_456")  # 15.75

# Reset
await store.cost_reset("customer_456")
```

**Use Case**: Billing integration; cost per API call.

### Distributed Locking

Coordinate resource access across workers:

```python
# Try to acquire lock
acquired = await store.lock_acquire(
    "expensive_operation",
    timeout_seconds=30
)

if acquired:
    try:
        # Do exclusive work
        await perform_exclusive_operation()
    finally:
        await store.lock_release("expensive_operation")
else:
    # Another worker has the lock
    print("Skipping; another worker is running")
```

**Use Case**: Prevent concurrent execution of expensive operations (e.g., model downloads).

### Health & Monitoring

```python
health = await store.health_check()
print(f"""
Redis Status:
  Available: {health['redis_available']}
  Connected: {health['connected']}
  Memory: {health.get('memory_usage_mb', 'N/A')} MB
  Pool Size: {health.get('connection_pool_size', 'N/A')}
  URL: {health['redis_url']}
""")
```

## Singleton Pattern

Use the global singleton for consistent store access:

```python
from loom.redis_store import get_redis_store, close_redis_store

# Get store (creates if needed)
store = await get_redis_store()

# Use it
await store.cache_set("key", {"data": 123})

# Cleanup (at shutdown)
await close_redis_store()
```

## Graceful Fallback

If Redis is unavailable, the store silently switches to in-memory mode:

```python
store = RedisStore(redis_url="redis://unavailable:6379")
await store.connect()  # Logs warning, returns False

# Still works! Uses in-memory dict instead
await store.cache_set("key", {"value": 456})

# Check status
health = await store.health_check()
assert health["connected"] is False
assert health["redis_available"] is True  # module available
```

## MCP Tools

Two tools for Redis management:

### `research_redis_stats`

Get connection pool and memory statistics:

```json
{
  "status": "success",
  "data": {
    "redis_available": true,
    "connected": true,
    "redis_url": "localhost:6379",
    "memory_usage_mb": 45.2,
    "memory_usage_bytes": 47385600,
    "connection_pool_size": 20
  }
}
```

### `research_redis_flush_cache`

Clear cache by prefix:

```json
{
  "status": "success",
  "keys_deleted": 42,
  "prefix": "cache:fetch:"
}
```

Use with caution — this is destructive:

```python
# Clear all fetch cache
await research_redis_flush_cache(prefix="cache:fetch:")

# Clear all cache
await research_redis_flush_cache(prefix="cache:")
```

## Testing

All tests use in-memory mode for isolation:

```python
@pytest.fixture
async def redis_store_local() -> RedisStore:
    store = RedisStore(redis_url="")  # Force local mode
    yield store
    await store.close()

@pytest.mark.asyncio
async def test_cache(redis_store_local: RedisStore) -> None:
    await redis_store_local.cache_set("key", {"data": 1})
    assert await redis_store_local.cache_get("key") == {"data": 1}
```

Run tests:

```bash
pytest tests/test_redis_store.py -v
pytest tests/test_redis_tools.py -v
```

## Integration with Existing Code

### Replacing File Locks

Current `rate_limiter.py` uses SQLite. To integrate:

```python
# Before: SQLite + file locks
from loom.rate_limiter import check_rate_limit

error = await check_rate_limit(category="search")

# After: Redis store
from loom.redis_store import get_redis_store

store = await get_redis_store()
allowed = await store.rate_limit_check(
    user_id=request.user_id,
    category="search",
    limit=30
)
```

### Replacing In-Memory Cache

Current `cache.py` uses filesystem. To integrate:

```python
# Before: File-based cache
from loom.cache import get_cache

cache = get_cache()
value = cache.get("key")

# After: Redis cache
from loom.redis_store import get_redis_store

store = await get_redis_store()
value = await store.cache_get("cache:key")
```

## Performance Characteristics

| Operation | Local (Dict) | Redis |
|-----------|------------|-------|
| cache_get | O(1) | O(1) + network |
| cache_set | O(1) | O(1) + network |
| rate_limit_check | O(window_size) | O(window_size) + network |
| cache_clear_prefix | O(keys) | O(keys) + network + scan |

For local dev (single process), use in-memory. For production (multi-worker), Redis overhead is worth the shared state.

## Troubleshooting

### "redis module not installed"

```bash
pip install redis[hiredis]>=5.0
```

### Connection Refused

Check Redis is running:

```bash
redis-cli ping
# Should return: PONG
```

Or force in-memory fallback:

```bash
export REDIS_URL=""
```

### Memory Usage

Monitor with `research_redis_stats()`:

```python
stats = await research_redis_stats()
print(f"Memory: {stats['memory_usage_mb']} MB")
```

Set memory limits in Redis config:

```
maxmemory 1gb
maxmemory-policy allkeys-lru
```

### Key Expiry Not Working

Redis handles TTL automatically. For in-memory, check TTL manually:

```python
health = await store.health_check()
if not health["connected"]:
    # In-memory mode; TTL is soft (not enforced on get)
    # Clean up manually if needed
    pass
```

## Security Considerations

1. **Auth**: Use Redis AUTH for production:
   ```
   export REDIS_URL="redis://:mypassword@localhost:6379"
   ```

2. **Network**: Run Redis only on localhost or private networks

3. **Data**: Cache/sessions may contain sensitive data; use TLS:
   ```
   export REDIS_URL="rediss://localhost:6380"  # Note: rediss with SSL
   ```

## References

- **Module**: `/Users/aadel/projects/loom/src/loom/redis_store.py`
- **Tools**: `/Users/aadel/projects/loom/src/loom/tools/redis_tools.py`
- **Tests**: `/Users/aadel/projects/loom/tests/test_redis_store.py`
- **Dependencies**: `pyproject.toml` (redis[hiredis]>=5.0)
