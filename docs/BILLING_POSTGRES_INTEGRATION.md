# Billing System PostgreSQL Integration

## Overview

The Loom billing system now supports **PostgreSQL as the primary backend** while maintaining **graceful fallback to JSON/JSONL** when PostgreSQL is unavailable.

This document explains:
1. How to enable PostgreSQL for billing
2. Table structure and schemas
3. Fallback behavior and error handling
4. Migration from JSON to PostgreSQL
5. Configuration and initialization

## Quick Start

### Prerequisites

- PostgreSQL 13+ running
- `asyncpg` library installed (already in Loom's dependencies)
- DATABASE_URL environment variable set

### Enable PostgreSQL Backend

```bash
# Set backend to PostgreSQL
export LOOM_BILLING_BACKEND=postgres

# Configure database connection (defaults shown)
export DATABASE_URL="postgresql://loom:loom_secure_2026@localhost:5432/loom_db"

# Start Loom server
loom serve
```

### Verify Setup

```python
from loom.billing import initialize_billing_backend

# During startup, call once to initialize:
result = await initialize_billing_backend()
print(result)  # {"backend": "postgres", "status": "initialized"}
```

## Architecture

### Backend Selection

```python
LOOM_BILLING_BACKEND = os.environ.get("LOOM_BILLING_BACKEND", "json")
```

Valid values:
- `"postgres"` — Use PostgreSQL (with JSON fallback on connection failure)
- `"json"` — Use JSON files (default, no external dependencies)

### Lazy Initialization

Each billing module (`customers.py`, `meter.py`, `credits.py`) lazily initializes the PgStore:

```python
async def _get_pg_store():
    """Lazy-load PostgreSQL store, or return None if unavailable."""
    global _pg_store
    if _pg_store is None:
        try:
            from loom.pg_store import get_store
            _pg_store = await get_store()  # Connects and ensures schema
        except Exception as e:
            log.warning(f"pg_store unavailable, falling back to JSON: {e}")
            _pg_store = False  # Mark permanently unavailable
    return _pg_store if _pg_store is not False else None
```

### Graceful Fallback Pattern

All async functions follow this pattern:

```python
async def some_operation(customer_id: str) -> dict:
    """Operation that uses PostgreSQL with JSON fallback."""
    
    # Try PostgreSQL first
    if _BILLING_BACKEND == "postgres":
        store = await _get_pg_store()
        if store:
            try:
                # PG operation
                result = await store.do_something()
                log.info("Operation in PG succeeded")
                return result
            except Exception as e:
                log.error(f"PG operation failed: {e}, falling back to JSON")
    
    # Fall back to JSON (always succeeds)
    result = do_something_json()
    log.info("Operation in JSON succeeded")
    return result
```

## PostgreSQL Schema

### Table: `customers`

Stores customer records with tier and credits.

```sql
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    api_key_hash TEXT,           -- Hash of API key
    tier TEXT DEFAULT 'free',     -- free, pro, team, enterprise
    credits INTEGER DEFAULT 0,    -- Current credit balance
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Table: `credits_ledger`

Audit trail of all credit adjustments.

```sql
CREATE TABLE credits_ledger (
    id SERIAL PRIMARY KEY,
    customer_id TEXT REFERENCES customers(customer_id),
    amount INTEGER NOT NULL,     -- Positive (topup) or negative (usage)
    reason TEXT,                 -- 'account_creation', 'tool_usage_*', 'manual_adjustment', etc.
    tool_name TEXT,              -- Optional: which tool caused the adjustment
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Table: `usage_meter`

Per-tool usage records for analytics.

```sql
CREATE TABLE usage_meter (
    id SERIAL PRIMARY KEY,
    customer_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    credits_used INTEGER NOT NULL,
    duration_ms REAL,             -- Execution time in milliseconds
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meter_customer_date
    ON usage_meter(customer_id, created_at);
```

### Table: `audit_log`

Complete audit trail of all tool invocations (for compliance).

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    tool_name TEXT NOT NULL,
    customer_id TEXT,
    params_hash TEXT,            -- SHA-256 of tool parameters
    result_status TEXT,          -- 'success', 'error', 'timeout', etc.
    duration_ms REAL,
    hmac_signature TEXT          -- Optional HMAC signature
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_customer ON audit_log(customer_id);
```

### Table: `idempotency_keys`

Prevents duplicate operations (for safe retries).

```sql
CREATE TABLE idempotency_keys (
    id SERIAL PRIMARY KEY,
    idempotency_key TEXT UNIQUE NOT NULL,
    customer_id TEXT,
    operation TEXT NOT NULL,     -- 'credit_deduct', 'meter_record', etc.
    result JSONB NOT NULL,       -- Cached operation result
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX idx_idempotency_key_expires
    ON idempotency_keys(idempotency_key, expires_at);
CREATE INDEX idx_idempotency_customer_created
    ON idempotency_keys(customer_id, created_at);
```

## Module Changes

### `billing/customers.py`

**Async functions** (changed from sync):
- `create_customer(name, email, tier) → dict`
- `validate_key(api_key) → dict | None`
- `revoke_key(customer_id) → bool`
- `rotate_key(customer_id) → dict | None`
- `get_customer(customer_id) → dict | None`
- `update_credits(customer_id, amount, reason) → int | None`
- `list_customers() → list[dict]`
- `initialize_billing_backend() → dict`

**Behavior**:
- Uses `pg_store.create_customer()`, `update_credits()` when PG is available
- Falls back to `_load_customers()` / `_save_customers()` JSON functions
- All operations succeed (either via PG or JSON)

### `billing/meter.py`

**Async functions** (changed from sync):
- `record_usage(customer_id, tool_name, credits_used, duration_ms) → dict`
- `record_usage_idempotent(...) → dict`
- `get_usage(customer_id, date) → dict`
- `get_top_tools(customer_id, date, limit) → list[dict]`

**Behavior**:
- Uses `pg_store.record_usage()`, `get_usage()`, `get_top_tools()` when PG is available
- Falls back to JSONL functions (`record_usage_json`, `get_usage_json`, etc.)
- Maintains 100% backward compatibility with JSONL format

### `billing/credits.py`

**New async function**:
- `deduct_with_idempotency(customer_id, tool_name, current_credits, idempotency_key) → dict`
- `get_credit_ledger(customer_id) → list[dict]`

**Behavior**:
- Logs credit deductions to `pg_store.update_credits()` for audit trail
- Falls back gracefully if PG unavailable
- Idempotency via `idempotency_keys` table

### `billing/backend.py` (New)

Helper module for backend initialization:
- `get_configured_backend() → str` — Read LOOM_BILLING_BACKEND env var
- `initialize_billing() → dict` — Initialize both JSON and PG on startup
- `verify_backend() → dict` — Health check for configured backend
- `describe_backends() → dict` — Documentation on each backend

## Migration Path

### Step 1: Enable PostgreSQL Backend

```bash
# Create PostgreSQL database (if not exists)
psql -h localhost -U postgres -c "CREATE DATABASE loom_db;"
psql -h localhost -U postgres -d loom_db -c "CREATE USER loom WITH PASSWORD 'loom_secure_2026';"
psql -h localhost -U postgres -d loom_db -c "GRANT ALL PRIVILEGES ON DATABASE loom_db TO loom;"

# Export environment variable
export LOOM_BILLING_BACKEND=postgres
export DATABASE_URL="postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
```

### Step 2: Start Server (Tables Auto-Created)

```bash
loom serve
# Tables are created automatically on first connection
```

### Step 3: Migrate Existing Data (Optional)

If you have existing JSON billing data, copy to PostgreSQL:

```python
import asyncio
from loom.billing.customers import _load_customers
from loom.pg_store import get_store

async def migrate_customers():
    """Migrate from JSON to PostgreSQL."""
    store = await get_store()
    customers = _load_customers()
    
    for customer_id, data in customers.items():
        await store.create_customer(
            customer_id=customer_id,
            name=data["name"],
            email=data["email"],
            tier=data["tier"]
        )
        # Set credits to match JSON
        current_credits = data.get("credits", 0)
        await store.update_credits(
            customer_id=customer_id,
            amount=current_credits,
            reason="migration_from_json"
        )
    
    print(f"Migrated {len(customers)} customers")

asyncio.run(migrate_customers())
```

## Testing

### Test with PostgreSQL

```bash
# Set backend to PostgreSQL
export LOOM_BILLING_BACKEND=postgres
export DATABASE_URL="postgresql://test:test@localhost:5432/loom_test"

# Run billing tests
pytest tests/test_billing/ -v
```

### Test JSON Fallback

```bash
# Unset PostgreSQL vars to force JSON fallback
unset LOOM_BILLING_BACKEND
unset DATABASE_URL

# Tests should still pass with JSON backend
pytest tests/test_billing/ -v
```

### Test Failure Recovery

```python
# Simulate PG unavailable
async def test_postgres_unavailable():
    """Test graceful fallback when PG is down."""
    import os
    os.environ["LOOM_BILLING_BACKEND"] = "postgres"
    # Don't set DATABASE_URL
    
    # Should fall back to JSON automatically
    result = await create_customer("test", "test@example.com")
    assert result["customer_id"]
    
    # Verify data was written to JSON
    customers = _load_customers()
    assert result["customer_id"] in customers
```

## Monitoring & Operations

### Check Backend Status

```python
from loom.billing.backend import verify_backend

status = await verify_backend()
print(status)
# Output:
# {
#   "backend": "postgres",
#   "status": "healthy",
#   "details": {
#     "status": "connected",
#     "pool_size": 10,
#     "pool_free": 8,
#     "tables": ["customers", "credits_ledger", "usage_meter", "audit_log"],
#     "row_counts": {"customers": 42, "credits_ledger": 1337, ...}
#   }
# }
```

### Query Audit Trail

```python
# Get all credit adjustments for a customer
ledger = await get_credit_ledger("customer_123")
for entry in ledger:
    print(f"{entry['created_at']}: {entry['reason']} ({entry['amount']} credits)")
```

### Monitor Usage

```python
# Get top tools for a customer
top_tools = await get_top_tools("customer_123")
for tool in top_tools:
    print(f"{tool['tool']}: {tool['credits']} credits")
```

## Performance Characteristics

### PostgreSQL Backend

- **Write latency**: ~5-20ms per operation (connection pool)
- **Read latency**: ~5-15ms per operation
- **Scalability**: 100+ concurrent customers
- **Audit trail**: Complete, queryable
- **Consistency**: ACID transactions

### JSON Backend

- **Write latency**: ~1-5ms per operation (file I/O)
- **Read latency**: ~1-5ms per operation
- **Scalability**: Single-machine only
- **Audit trail**: JSONL files (grep-able)
- **Consistency**: File-level atomic writes

## Troubleshooting

### PostgreSQL Connection Fails

```
ERROR: pg_store unavailable, falling back to JSON
```

**Solution**: Check `DATABASE_URL` env var:

```bash
echo $DATABASE_URL  # Should be set
psql $DATABASE_URL -c "SELECT 1"  # Should connect successfully
```

### Tables Not Created

If tables don't auto-create, call manually:

```python
from loom.pg_store import get_store

store = await get_store()
await store.ensure_schema()
```

### Data Not Persisting

If using JSON backend by mistake:

```bash
# Verify backend
echo $LOOM_BILLING_BACKEND  # Should be "postgres" or empty (defaults to json)

# Check files
ls -la ~/.loom/customers.json ~/.loom/meters/
```

## Future Enhancements

- [ ] Automatic daily balance snapshots (cost tracking)
- [ ] Real-time usage alerts via PostgreSQL triggers
- [ ] Data retention policies (archive old audit logs)
- [ ] Replication for HA (PostgreSQL replicas)
- [ ] Time-series compression for usage_meter table
