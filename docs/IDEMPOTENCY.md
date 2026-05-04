# Idempotency Layer for Financial Operations

Loom's billing system uses an idempotency layer to prevent duplicate charges and transactions. This document describes the architecture, usage, and best practices.

## Overview

The idempotency system protects against:
- **Network retries** that cause duplicate API calls
- **Client timeouts** followed by re-requests
- **Load balancer failures** that cause duplicate requests
- **Process crashes** with automatic retry

All financial operations (credit deductions, Stripe charges, meter recording) use deterministic idempotency keys and result caching.

## Key Concepts

### Idempotency Key

An idempotency key uniquely identifies an operation and prevents duplicate execution.

**Key format:** SHA-256 hash (64-character hex string)

**Key composition:**
```
SHA-256(user_id + operation + params_json + timestamp_bucket)
```

**Example:**
```python
from loom.billing.idempotency import generate_idempotency_key

key = generate_idempotency_key(
    user_id="cust_123",
    operation="stripe_charge",
    params={"amount": 9999, "description": "Overage"},
    timestamp_bucket=1700000000  # Unix timestamp (hourly bucket)
)
# Returns: "a3f2c1e8d7b4f9c2a6e1d4f8c3a7b2e9..."
```

### Result Caching

When an operation completes, its result is cached with the idempotency key for 24 hours.

**Cache backends:**
- **Redis** (preferred): Distributed, supports multiple workers
- **In-memory** (fallback): Local cache, single-process only

**TTL:** 24 hours (86,400 seconds) by default

## Usage Patterns

### Pattern 1: Credit Deduction with Idempotency

```python
from loom.billing.credits import deduct_with_idempotency
from loom.billing.idempotency import generate_idempotency_key

# Generate deterministic key
key = generate_idempotency_key(
    user_id="user_123",
    operation="credit_deduct",
    params={"tool_name": "research_fetch"}
)

# Deduct credits (idempotent)
result = await deduct_with_idempotency(
    customer_id="user_123",
    tool_name="research_fetch",
    current_credits=100,
    idempotency_key=key
)

# First request:
# {
#   "remaining_credits": 97,
#   "cost_charged": 3,
#   "idempotency_key": "...",
#   "is_duplicate": False,
#   "success": True
# }

# Duplicate request (same key):
# Returns cached result immediately
# {
#   "remaining_credits": 97,
#   "cost_charged": 3,
#   "idempotency_key": "...",
#   "is_duplicate": True,
#   "success": True
# }
```

### Pattern 2: Stripe Charge with Idempotency

```python
from loom.billing.stripe_integration import StripeIntegration
from loom.billing.idempotency import generate_idempotency_key

stripe = StripeIntegration(api_key="sk_live_xxx")

# Generate key
key = generate_idempotency_key(
    user_id="cust_456",
    operation="stripe_charge",
    params={"amount_cents": 9999}
)

# Create charge with idempotency
result = await stripe.create_charge(
    customer_id="cust_456",
    amount_cents=9999,
    description="Overage charges for April",
    idempotency_key=key  # Passed to Stripe API
)

# Result includes idempotency key for reference
# {
#   "id": "ii_1234567890",
#   "customer": "cust_456",
#   "amount": 9999,
#   "description": "Overage charges for April",
#   "created": 1700000000,
#   "idempotency_key": "..."
# }
```

### Pattern 3: Meter Recording with Idempotency

```python
from loom.billing.meter import record_usage_idempotent
from loom.billing.idempotency import generate_idempotency_key

# Generate key
key = generate_idempotency_key(
    user_id="user_789",
    operation="meter_record",
    params={
        "tool_name": "research_deep",
        "credits_used": 10,
        "duration_ms": 5000
    }
)

# Record usage (idempotent)
result = await record_usage_idempotent(
    customer_id="user_789",
    tool_name="research_deep",
    credits_used=10,
    duration_ms=5000.0,
    idempotency_key=key
)

# Result includes duplicate flag
# {
#   "timestamp": "2024-01-15T10:30:00+00:00",
#   "customer_id": "user_789",
#   "tool_name": "research_deep",
#   "credits_used": 10,
#   "duration_ms": 5000.0,
#   "idempotency_key": "...",
#   "is_duplicate": False
# }
```

## Architecture

### Components

#### 1. `idempotency.py`

Core idempotency module providing:
- **`generate_idempotency_key()`**: Generates deterministic SHA-256 keys
- **`IdempotencyManager`**: Manages cache checks and result storage
- **`get_idempotency_manager()`**: Returns global singleton

```python
class IdempotencyManager:
    async def check_and_store(
        self,
        idempotency_key: str,
        operation_result: dict | None = None,
        ttl_seconds: int = 86400,
    ) -> dict | None:
        """Check if key exists; store result if new."""
```

#### 2. `credits.py`

Updated with:
- **`deduct_with_idempotency()`**: Idempotent credit deduction

#### 3. `stripe_integration.py`

Updated with idempotency key parameters:
- **`create_charge(..., idempotency_key)`**
- **`create_subscription(..., idempotency_key)`**
- **`create_checkout_session(..., idempotency_key)`**

#### 4. `meter.py`

Updated with:
- **`record_usage_idempotent()`**: Idempotent meter recording

### Cache Storage

#### Redis (Preferred)

```
Key: idempotency:{hex_key_64_chars}
Value: {JSON-serialized operation result}
TTL: 24 hours
```

Uses `loom.redis_store.RedisStore` for distributed caching.

#### PostgreSQL (Optional)

New table for audit/recovery:

```sql
CREATE TABLE idempotency_keys (
    id SERIAL PRIMARY KEY,
    idempotency_key TEXT UNIQUE NOT NULL,
    customer_id TEXT,
    operation TEXT NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX idx_idempotency_key_expires 
    ON idempotency_keys(idempotency_key, expires_at);
```

## Error Handling

### Redis Unavailable

If Redis is unavailable, the system gracefully degrades to in-memory caching. This means:

- **Single process**: Caching works (in-memory)
- **Multiple processes**: No distributed caching (each process caches independently)

Logging:
```
WARNING: redis_initialization_failed fallback=none
```

### Expired Keys

Keys older than 24 hours are automatically cleaned up by:
- Redis: TTL expires automatically
- PostgreSQL: Periodic cleanup job (if implemented)
- In-memory: Manual cleanup via `clear_key()` or `clear_prefix()`

## Best Practices

### 1. Generate Keys Deterministically

Always include operation parameters in key generation:

```python
# GOOD: Includes amount
key = generate_idempotency_key(
    "user_123",
    "stripe_charge",
    {"amount": 9999}
)

# BAD: Omits amount (different amounts generate same key)
key = generate_idempotency_key("user_123", "stripe_charge")
```

### 2. Use Timestamp Buckets for Rate-Limiting

When you want to allow multiple charges per hour but prevent within-hour duplicates:

```python
import time

# Hourly bucket
bucket = int(time.time()) // 3600

key = generate_idempotency_key(
    "user_123",
    "stripe_charge",
    {"amount": 5000},
    timestamp_bucket=bucket
)
```

### 3. Document Idempotency Requirements

When creating financial operation functions, document idempotency:

```python
async def process_payment(
    customer_id: str,
    amount_cents: int,
    idempotency_key: str | None = None,
) -> dict:
    """Process payment (idempotent).
    
    Args:
        customer_id: Customer ID
        amount_cents: Amount in cents
        idempotency_key: Optional idempotency key. If provided and operation
                        was previously executed, returns cached result.
    
    Returns:
        Payment result dict with 'is_duplicate' flag.
    """
```

### 4. Check Duplicate Flag in Logs

When logging financial operations, include the duplicate flag:

```python
result = await deduct_with_idempotency(...)

if result["is_duplicate"]:
    logger.warning(
        "duplicate_operation idempotency_key=%s customer=%s",
        result["idempotency_key"][:16],
        customer_id
    )
else:
    logger.info("operation_executed customer=%s", customer_id)
```

## Testing

### Unit Tests

```bash
pytest tests/test_billing/test_idempotency.py -v
pytest tests/test_billing/test_credits_idempotent.py -v
pytest tests/test_billing/test_stripe_idempotency.py -v
pytest tests/test_billing/test_meter_idempotent.py -v
```

### Integration Tests

Test with Redis:

```python
import pytest_asyncio
from loom.redis_store import get_redis_store

@pytest_asyncio.fixture
async def redis():
    store = await get_redis_store()
    yield store
    await store.close()

@pytest.mark.asyncio
async def test_idempotency_with_redis(redis):
    from loom.billing.idempotency import IdempotencyManager
    
    manager = IdempotencyManager(redis_store=redis)
    key = "test_key_" + "a" * 56
    result1 = await manager.check_and_store(key, {"status": "ok"})
    result2 = await manager.check_and_store(key)
    
    assert result1 is None  # First call, stored
    assert result2 == {"status": "ok"}  # Duplicate, cached
```

## Monitoring

### Key Metrics

1. **Cache Hit Rate**: Percentage of duplicate requests
2. **Cache Evictions**: Keys expired or manually cleared
3. **Storage Usage**: Size of idempotency cache

### Health Checks

```python
from loom.redis_store import get_redis_store

store = await get_redis_store()
health = await store.health_check()

print(f"Redis: {health['connected']}")
print(f"Memory: {health.get('memory_usage_mb')} MB")
```

## FAQ

### Q: Can I use the same key for different operations?

**A:** No. Keys must be unique per operation. Different operations must generate different keys.

```python
# Different amounts → different keys
key1 = generate_idempotency_key("user", "charge", {"amount": 1000})
key2 = generate_idempotency_key("user", "charge", {"amount": 2000})
assert key1 != key2
```

### Q: What happens if Redis goes down?

**A:** System falls back to in-memory caching. In a single-process environment, this works fine. In a multi-process environment (e.g., with gunicorn), each process has its own cache, so idempotency is not guaranteed across processes.

Recommendation: Monitor Redis health and alert on disconnections.

### Q: How long are keys cached?

**A:** 24 hours by default. This is configurable via the `ttl_seconds` parameter.

```python
await manager.check_and_store(key, result, ttl_seconds=3600)  # 1 hour
```

### Q: Can I manually clear an idempotency key?

**A:** Yes, using `IdempotencyManager.clear_key()`:

```python
manager = await get_idempotency_manager()
await manager.clear_key("idem_key_abc123")
```

Use sparingly — only for manual reconciliation or testing.

## Migration Guide

### Adding Idempotency to Existing Functions

Before:
```python
async def create_charge(customer_id: str, amount_cents: int):
    return await stripe.create_charge(customer_id, amount_cents)
```

After:
```python
async def create_charge(
    customer_id: str,
    amount_cents: int,
    idempotency_key: str | None = None,
):
    if idempotency_key is None:
        from loom.billing.idempotency import generate_idempotency_key
        idempotency_key = generate_idempotency_key(
            customer_id,
            "create_charge",
            {"amount_cents": amount_cents}
        )
    
    return await stripe.create_charge(
        customer_id,
        amount_cents,
        idempotency_key=idempotency_key
    )
```

## References

- [Stripe Idempotency Documentation](https://stripe.com/docs/api/idempotent_requests)
- [Braintree Idempotency](https://developer.paypal.com/braintree/docs/guides/recurring_billing/overview)
- [HTTP Idempotency RFC 7231](https://tools.ietf.org/html/rfc7231#section-4.2.2)
