# Tier Gating Guide

## Overview

The `@requires_tier` decorator gates premium tools based on subscription tier. Tools requiring higher tiers will return an upgrade error for free/lower-tier users.

## Tier Hierarchy

```
free (0) < pro (1) < team (2) < enterprise (3)
```

A user can access any tool that requires their tier or lower.

## Usage

### Basic Syntax

```python
from loom.billing import requires_tier

@requires_tier("pro")
def research_dark_recon(target: str) -> dict:
    """Premium dark web reconnaissance tool."""
    return {"results": "..."}

# Async functions also work
@requires_tier("enterprise")
async def research_sandbox_execute(code: str) -> dict:
    """Execute code in isolated sandbox (enterprise only)."""
    return {"output": "..."}
```

### Tier Requirements by Tool Category

#### Free Tier (No Gating)
- Basic search (single engine)
- Public OSINT
- Information gathering from public sources

#### Pro Tier
- Dark web reconnaissance (`research_torbot`, `research_amass_enum`)
- Advanced OSINT (multiple sources, deep discovery)
- Cloudflare bypass and anti-bot evasion
- Multiple LLM provider access

#### Team Tier
- Dark web forum access
- AI safety/compliance testing
- Career intelligence tools
- Extended strategy library (200+)

#### Enterprise Tier
- Sandbox code execution (`research_sandbox_execute`)
- System call monitoring
- Advanced persistent threat detection
- Full strategy library (826+)
- SLA/audit log compliance exports

## Error Response

When a user's tier is insufficient, the tool returns an error dict:

```python
{
    "error": "upgrade_required",
    "current_tier": "free",
    "required_tier": "pro",
    "current_tier_name": "Free",
    "required_tier_name": "Pro",
    "upgrade_url": "https://loom.local/upgrade",
    "message": "This tool requires Pro tier. You are on Free."
}
```

## Decorator Behavior

### Sync Functions

```python
@requires_tier("pro")
def my_tool(data: str) -> dict:
    return {"result": data}

# If user tier < pro:
result = my_tool("test")
# Returns: {"error": "upgrade_required", ...}

# If user tier >= pro:
result = my_tool("test")
# Returns: {"result": "test"}
```

### Async Functions

```python
@requires_tier("pro")
async def my_async_tool(data: str) -> dict:
    return {"result": data}

# Works with await
result = await my_async_tool("test")
# Returns error dict or {"result": "test"}
```

### Keyword Arguments

```python
@requires_tier("team")
def my_tool(name: str, value: int = 10) -> dict:
    return {"name": name, "value": value}

# Works with keyword args
result = my_tool("alice", value=20)
# Tier check applies before function is called
```

## Current User Tier Resolution

The decorator determines the current user's tier in this order:

1. **MCP Request Context** — Auth token metadata (production)
2. **FastAPI Request Context** — HTTP request user principal (web API)
3. **Environment Variable** — `LOOM_USER_TIER` (service-to-service)
4. **Default to Free** — Fail-open for development/unauthenticated access

Current implementation defaults to `"free"` tier when no context is available.

## Application to Existing Tools

### Dark Recon Tools (Pro Tier)

File: `src/loom/tools/dark_recon.py`

```python
@requires_tier("pro")
def research_torbot(url: str, depth: int = 2) -> dict[str, Any]:
    """Dark web OSINT crawling via TorBot."""
    # Implementation...

@requires_tier("pro")
def research_amass_enum(domain: str, passive: bool = True, timeout: int = 120) -> dict[str, Any]:
    """Attack surface mapping and asset discovery."""
    # Implementation...
```

### Sandbox Tools (Enterprise Tier)

File: `src/loom/tools/sandbox.py`

```python
@requires_tier("enterprise")
async def research_sandbox_execute(code: str, sandbox_type: str = "nix") -> dict[str, Any]:
    """Execute code in isolated sandbox (Docker/Nix)."""
    # Implementation...

@requires_tier("enterprise")
async def research_sandbox_monitor(code: str, event_types: list[str] | None = None) -> dict[str, Any]:
    """Monitor code execution for system calls."""
    # Implementation...
```

## Adding Tier Gating to New Tools

1. Import the decorator:
   ```python
   from loom.billing import requires_tier
   ```

2. Decorate the function with the minimum required tier:
   ```python
   @requires_tier("pro")
   def my_new_tool(params...) -> dict:
       # Implementation
   ```

3. Update docstring to note tier requirement:
   ```python
   """Tool description.
   
   Requires: Pro tier or higher
   
   Args:
       ...
   """
   ```

4. Test with `pytest tests/test_billing/test_tier_gating.py`

## Testing

Unit tests are in `tests/test_billing/test_tier_gating.py`:

- Tier hierarchy validation
- Access control logic
- Sync and async function support
- Error response format
- Function preservation (metadata, args, kwargs)

Run tests:
```bash
pytest tests/test_billing/test_tier_gating.py -v
```

## Logging

The decorator logs tier access denials:

```
tier_access_denied user_tier=free required_tier=pro tool=research_torbot
```

All tool access attempts (allowed or denied) are logged at INFO level.

## Future Enhancements

- [ ] Extract tier from MCP ServerRequest context in production
- [ ] Integrate with FastAPI request user principal
- [ ] Add context-local tier override for testing
- [ ] Support dynamic tier assignment per request
- [ ] Add rate limiting per tier (already in `tier_limiter.py`)
- [ ] Tie tool cost tracking to tier-gating
