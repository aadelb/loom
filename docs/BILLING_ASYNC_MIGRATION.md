# Billing API Async Migration Guide

## Summary

All billing functions are now **async** (return coroutines). This is a straightforward change:

**Before**:
```python
result = create_customer("Alice", "alice@example.com")
```

**After**:
```python
result = await create_customer("Alice", "alice@example.com")
```

## Quick Reference

### Customer Management Functions

```python
from loom.billing import (
    create_customer,
    get_customer,
    update_credits,
    validate_key,
    revoke_key,
    rotate_key,
    list_customers,
)

# All require 'await'
customer = await create_customer("name", "email")
info = await get_customer(customer_id)
balance = await update_credits(customer_id, amount)
valid = await validate_key(api_key)
revoked = await revoke_key(customer_id)
new_key = await rotate_key(customer_id)
all_customers = await list_customers()
```

### Usage Metering Functions

```python
from loom.billing import (
    record_usage,
    record_usage_idempotent,
    get_usage,
    get_top_tools,
)

# All require 'await'
entry = await record_usage(customer_id, tool_name, credits_used)
entry = await record_usage_idempotent(customer_id, tool_name, credits_used, idempotency_key)
stats = await get_usage(customer_id, date)
tools = await get_top_tools(customer_id, limit=10)
```

### Credit Functions

```python
from loom.billing import (
    deduct,
    deduct_with_idempotency,
    get_credit_ledger,
    check_balance,
    get_tool_cost,
)

# Synchronous (unchanged)
cost = get_tool_cost(tool_name)
has_balance = check_balance(credits, tool_name)
new_balance, cost = deduct(credits, tool_name)

# Async (changed - requires await)
result = await deduct_with_idempotency(customer_id, tool_name, current_credits)
ledger = await get_credit_ledger(customer_id)
```

### Backend Initialization

```python
from loom.billing import initialize_billing_backend

# Required during server startup - must be awaited
result = await initialize_billing_backend()
# Returns: {"backend": "postgres" or "json", "status": "initialized"}
```

## Usage Patterns

### In Async Functions

```python
async def create_and_initialize_customer(name: str, email: str):
    """Create a new customer and set up their account."""
    from loom.billing import create_customer, update_credits
    
    # Create customer
    customer = await create_customer(name, email, tier="pro")
    
    # Grant bonus credits
    balance = await update_credits(
        customer["customer_id"],
        1000,
        reason="signup_bonus"
    )
    
    return {
        "customer_id": customer["customer_id"],
        "api_key": customer["api_key"],
        "balance": balance,
    }
```

### In FastAPI Endpoints

```python
from fastapi import APIRouter, Depends
from loom.billing import create_customer

router = APIRouter()

@router.post("/customers")
async def create_new_customer(name: str, email: str):
    """Create a new customer (async endpoint)."""
    customer = await create_customer(name, email, tier="free")
    return customer
```

### In Synchronous Code

If you're in synchronous code and need to call async functions:

```python
import asyncio
from loom.billing import get_customer

# Option 1: Use asyncio.run() (for scripts)
def get_customer_sync(customer_id: str):
    return asyncio.run(get_customer(customer_id))

# Option 2: Use event loop if already running
async def wrapper():
    return await get_customer(customer_id)

asyncio.get_event_loop().run_until_complete(wrapper())
```

## Migration Checklist

### For Existing Code Using Billing Functions

- [ ] Find all calls to `create_customer()`
- [ ] Add `await` before the call
- [ ] Ensure the containing function is `async def`
- [ ] Repeat for all other billing functions

### Example Diff

```python
# BEFORE
def setup_new_customer(name: str, email: str):
    customer = create_customer(name, email)  # ❌ Error: not awaiting
    credits = update_credits(customer["customer_id"], 100)
    return customer

# AFTER
async def setup_new_customer(name: str, email: str):
    customer = await create_customer(name, email)  # ✓ Correct
    credits = await update_credits(customer["customer_id"], 100)
    return customer
```

## Functions That Are Still Synchronous

These have **NOT** changed and do NOT require `await`:

```python
from loom.billing import (
    # Cost checking (sync)
    get_tool_cost,
    check_balance,
    deduct,
    get_tool_cost,
    
    # Constants (sync)
    CREDIT_WEIGHTS,
    DEFAULT_WEIGHT,
    CREDIT_WEIGHTS,
    
    # Cost estimation (sync)
    estimate_call_cost,
    estimate_revenue,
    compute_margin,
)

# These are still sync - NO await needed
cost = get_tool_cost("research_fetch")
has_balance = check_balance(100, "research_search")
margin = compute_margin("pro", 1000, 50.0)
```

## Common Pitfalls

### ❌ Forgetting `await`

```python
# This creates a coroutine but doesn't execute it!
customer = create_customer("name", "email")  # ❌ Wrong
print(customer)  # Prints: <coroutine object create_customer at 0x...>

# Fix: add await
customer = await create_customer("name", "email")  # ✓ Right
```

### ❌ Calling from Non-Async Context

```python
# This will fail - can't await in synchronous function
def sync_function():
    customer = await create_customer("name", "email")  # ❌ SyntaxError

# Fix: make it async
async def async_function():
    customer = await create_customer("name", "email")  # ✓ Correct
```

### ❌ Missing Asyncio Event Loop

```python
# This fails if event loop isn't running
result = await create_customer("name", "email")  # ❌ RuntimeError

# Fix: use asyncio.run() for scripts
asyncio.run(create_customer("name", "email"))  # ✓ Correct
```

## Testing Async Billing Functions

### With Pytest

```python
import pytest

@pytest.mark.asyncio
async def test_create_customer():
    """Test creating a customer."""
    from loom.billing import create_customer
    
    customer = await create_customer("Test", "test@example.com")
    assert customer["customer_id"]
    assert customer["api_key"].startswith("loom_live_")
```

### Marker Configuration (pytest.ini)

```ini
[tool:pytest]
asyncio_mode = auto
```

## Performance Notes

**No performance impact** from async change:
- Same underlying operations
- Operations still take same time (~5-20ms)
- But now can handle concurrent requests
- Better resource utilization

## Support

For issues or questions:
1. Check `docs/BILLING_POSTGRES_INTEGRATION.md` for backend details
2. Check test examples in `tests/test_billing/test_pg_backend.py`
3. Review function docstrings in `src/loom/billing/`
