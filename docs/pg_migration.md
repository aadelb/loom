# PostgreSQL Migration Guide

## Overview

Loom now supports PostgreSQL for billing and audit logging, moving away from SQLite and JSON-based storage. This provides better scalability, ACID compliance, and concurrent access for production deployments.

## Connection Setup

### Environment Variable

Set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
```

Default: `postgresql://loom:loom_secure_2026@localhost:5432/loom_db`

### On Hetzner

The database is pre-installed at:
- **Host**: localhost
- **Port**: 5432
- **Database**: loom_db
- **User**: loom
- **Password**: loom_secure_2026

Environment variable is already set in `/opt/research-toolbox/.env`.

## Schema

The PostgreSQL migration creates four tables:

### customers

Stores customer account information.

```sql
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    api_key_hash TEXT,
    tier TEXT DEFAULT 'free',           -- free, pro, team, enterprise
    credits INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### credits_ledger

Append-only ledger of all credit transactions.

```sql
CREATE TABLE credits_ledger (
    id SERIAL PRIMARY KEY,
    customer_id TEXT REFERENCES customers(customer_id),
    amount INTEGER NOT NULL,           -- positive for additions, negative for deductions
    reason TEXT,                        -- e.g., "tool_usage", "purchase", "refund"
    tool_name TEXT,                     -- e.g., "research_fetch"
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### usage_meter

Records every tool invocation with credits consumed.

```sql
CREATE TABLE usage_meter (
    id SERIAL PRIMARY KEY,
    customer_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,           -- e.g., "research_fetch"
    credits_used INTEGER NOT NULL,     -- e.g., 3
    duration_ms REAL,                  -- execution time in milliseconds
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meter_customer_date ON usage_meter(customer_id, created_at);
```

### audit_log

Tamper-proof audit trail for compliance (EU AI Act Article 15).

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    tool_name TEXT NOT NULL,           -- e.g., "research_fetch"
    customer_id TEXT,                  -- optional
    params_hash TEXT,                  -- SHA-256 hash of params
    result_status TEXT,                -- success, error, timeout, etc.
    duration_ms REAL,
    hmac_signature TEXT                -- HMAC-SHA256 for integrity
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_customer ON audit_log(customer_id);
```

## MCP Tools

### research_pg_migrate

Run database schema migration. Creates all required tables if they don't exist. Safe to run multiple times.

**Parameters**: None

**Returns**:
```json
{
    "status": "success",
    "reason": "Schema migration completed",
    "tables": ["customers", "credits_ledger", "usage_meter", "audit_log"]
}
```

**Example**:
```bash
loom research_pg_migrate
```

### research_pg_status

Check PostgreSQL connection and table status. Useful for diagnostics.

**Parameters**: None

**Returns**:
```json
{
    "status": "connected",
    "connection": "postgresql",
    "pool_size": 10,
    "pool_free": 8,
    "tables": ["customers", "credits_ledger", "usage_meter", "audit_log"],
    "row_counts": {
        "customers": 42,
        "credits_ledger": 1250,
        "usage_meter": 8934,
        "audit_log": 5231
    }
}
```

**Example**:
```bash
loom research_pg_status
```

## Python API

### PgStore Class

The `PgStore` class provides async methods for all database operations.

```python
from loom.pg_store import PgStore

store = PgStore()
await store.connect()

# Customers
customer = await store.create_customer(
    customer_id="cust_123",
    name="ACME Corp",
    email="admin@acme.com",
    tier="enterprise"
)

customer = await store.get_customer("cust_123")

# Credits
new_balance = await store.update_credits(
    customer_id="cust_123",
    amount=1000,
    reason="tier_upgrade"
)

# Usage
await store.record_usage(
    customer_id="cust_123",
    tool_name="research_fetch",
    credits=3,
    duration_ms=145.5
)

usage = await store.get_usage(customer_id="cust_123")
top_tools = await store.get_top_tools(customer_id="cust_123", limit=10)

# Audit
await store.log_audit(
    tool_name="research_fetch",
    customer_id="cust_123",
    params_hash="abc123def456",
    status="success",
    duration_ms=145.5,
    hmac_signature="sig_xxx"
)

logs = await store.query_audit(customer_id="cust_123", limit=100)

await store.close()
```

### Singleton Pattern

For convenience, use the global singleton:

```python
from loom.pg_store import get_store

store = await get_store()
customer = await store.get_customer("cust_123")
```

## Connection Pooling

The `PgStore` class uses asyncpg connection pooling:

- **min_size**: 2 connections
- **max_size**: 10 connections
- **command_timeout**: 30 seconds

Connection pool is created on first use and can be reused across requests.

## Graceful Fallback

If `DATABASE_URL` is not set or asyncpg is unavailable:

1. **MCP tools** return `status: "skipped"` or `status: "disabled"`
2. **Server startup** does NOT crash
3. **Billing/audit** logging is simply not written to PostgreSQL

This allows Loom to run in offline or development modes without a database.

## Migration from SQLite

If you have existing billing/audit data in SQLite:

1. Export from SQLite:
   ```bash
   sqlite3 ~/.loom/billing.db "SELECT * FROM customers" > customers.csv
   sqlite3 ~/.loom/audit/*.jsonl > audit.jsonl
   ```

2. Import to PostgreSQL:
   ```sql
   COPY customers(customer_id, name, email, tier, credits, created_at)
   FROM 'customers.csv' WITH (FORMAT csv);
   ```

3. Verify with:
   ```bash
   loom research_pg_status
   ```

## Production Considerations

### Backups

Backup the PostgreSQL database regularly:

```bash
pg_dump -U loom -h localhost loom_db > backup_$(date +%Y%m%d).sql
```

### Monitoring

Monitor connection pool usage:

```python
import asyncio
from loom.pg_store import get_store

async def monitor():
    store = await get_store()
    status = await store._pool.get_size()
    idle = await store._pool.get_idle_size()
    print(f"Pool: {idle}/{status} idle/total")

asyncio.run(monitor())
```

### Performance

Create additional indexes for your query patterns:

```sql
-- Query by customer tier
CREATE INDEX idx_customers_tier ON customers(tier);

-- Query usage in time range
CREATE INDEX idx_meter_created ON usage_meter(created_at DESC);

-- Audit by tool
CREATE INDEX idx_audit_tool ON audit_log(tool_name);
```

## Testing

Run PostgreSQL tests (requires live database):

```bash
# All tests
pytest tests/test_pg_store.py

# Skip live database tests
pytest tests/test_pg_store.py -m "not live"

# Run specific test
pytest tests/test_pg_store.py::test_create_customer -m live
```

## Troubleshooting

### Connection Refused

**Error**: `asyncpg.ProtocolError: connect() failed (Err #111)`

**Solution**:
```bash
# Check PostgreSQL is running
psql -U loom -h localhost -d loom_db -c "SELECT version();"

# Verify environment variable
echo $DATABASE_URL

# Test connection manually
python3 -c "import asyncpg; asyncio.run(asyncpg.connect('postgresql://loom:loom_secure_2026@localhost:5432/loom_db'))"
```

### Table Already Exists

**Error**: `asyncpg.IntegrityConstraintViolationError: table already exists`

**Solution**: This is normal when running `research_pg_migrate()` multiple times. The tool uses `CREATE TABLE IF NOT EXISTS`, so it's safe to re-run.

### Pool Exhausted

**Error**: `asyncpg.TooManyConnectionsError: too many connections`

**Solution**: Increase max_size in PgStore.connect():
```python
_pool = await asyncpg.create_pool(
    db_url,
    min_size=4,
    max_size=20,  # Increase from 10
)
```

## See Also

- [docs/architecture.md](./architecture.md) — Billing system design
- [src/loom/pg_store.py](../src/loom/pg_store.py) — Implementation
- [tests/test_pg_store.py](../tests/test_pg_store.py) — Test suite
