# Tool Registry Migration Guide

## Executive Summary

This guide shows how to migrate from manual tool registration to the auto-discovery decorator system. The migration is **non-breaking** - existing code continues to work while new code uses the decorator system.

## Before and After Comparison

### BEFORE: Manual Registration (Current)

**Step 1: Import in server.py**
```python
# src/loom/server.py (lines 100+)
with suppress(ImportError):
    from loom.tools import billing as billing_tools
    _optional_tools["billing"] = billing_tools
    record_optional_module_loaded("billing")

with suppress(ImportError):
    from loom.tools import email_report as email_tools
    _optional_tools["email"] = email_tools
    record_optional_module_loaded("email")

# ... 700+ more lines of this pattern ...
```

**Step 2: Register functions in _register_tools()**
```python
# In server.py:_register_tools()
if "billing" in _optional_tools:
    billing_module = _optional_tools["billing"]
    for func in [billing_module.research_billing_check, ...]:
        mcp.tool()(wrap_tool(func))
```

**Step 3: (Often forgotten) Update documentation**
```python
# docs/tools-reference.md
# Must manually list all tools and parameters
```

### AFTER: Auto-Discovery Registration

**Step 1: Apply decorator in tool file**
```python
# src/loom/tools/billing.py
from loom.tool_registry import loom_tool

@loom_tool(
    category="infrastructure",
    description="Check billing account status and usage"
)
async def research_billing_check(account_id: str) -> dict:
    """Check Stripe account balance and usage."""
    ...
```

**Step 2: Auto-discover and register in server.py**
```python
# src/loom/server.py:create_app()
from loom.tool_registry import discover_tools, register_all_with_mcp
from pathlib import Path

async def create_app() -> FastMCP:
    mcp = FastMCP("loom")
    
    # Discover all tools with decorators
    discover_tools(Path("src/loom/tools"))
    
    # Register with MCP
    register_all_with_mcp(mcp, wrap_tool)
    
    return mcp
```

**Step 3: Documentation is automatic**
```python
# Via registry inspection
from loom.tool_registry import get_registry_stats, print_registry

print_registry()  # Shows all registered tools
stats = get_registry_stats()  # Get metadata for docs
```

## Migration Path: Three Approaches

### Approach 1: Big Bang (Not Recommended)

Convert all 711 tools at once.

**Pros:**
- Quick, one-time effort
- Complete migration immediately

**Cons:**
- High risk - could break multiple tools
- Hard to debug if something goes wrong
- No validation of approach before large scale

### Approach 2: Gradual per Module (Recommended)

Convert one module at a time.

**Benefits:**
- Low risk - easy to rollback
- Can validate approach on small scale
- Parallel development continues
- Easy to identify issues

**Timeline:**
```
Week 1: 10-20 tools (high-value: fetch, search, llm)
Week 2: 50 tools (analysis, infrastructure)
Week 3: 100 tools (provider tools, utilities)
Week 4: 200+ tools (remaining tools)
Total: ~4 weeks for full migration
```

### Approach 3: Parallel Operation (Most Flexible)

Keep both systems working simultaneously.

**Benefits:**
- Zero disruption
- Can migrate at own pace
- Old code continues working
- Easy rollback if needed

**Implementation:**
```python
# In server.py:_register_tools()

# Old system (manual imports) - still works
if "billing" in _optional_tools:
    # ... register manually ...
    pass

# New system (auto-discovery) - runs in parallel
from loom.tool_registry import discover_tools, register_all_with_mcp
discover_tools(Path("src/loom/tools"))
register_all_with_mcp(mcp, wrap_tool)  # Registers new tools only

# Result: Both old and new tools registered
```

**Cleanup:** After migration complete, remove manual registration code.

## Step-by-Step Migration: Approach 2 (Gradual)

### Phase 1: Core Infrastructure Tools (Week 1)

#### Step 1.1: Convert first tool

**File:** `src/loom/tools/fetch.py`

Before:
```python
"""research_fetch — Unified URL fetcher with HTTP, stealth, and dynamic modes."""

async def research_fetch(url: str, mode: str = "http") -> dict:
    """Fetch URL content."""
    ...
```

After:
```python
"""research_fetch — Unified URL fetcher with HTTP, stealth, and dynamic modes."""

from loom.tool_registry import loom_tool

@loom_tool(
    category="research",
    description="Unified URL fetcher with HTTP, stealth, and dynamic modes"
)
async def research_fetch(url: str, mode: str = "http") -> dict:
    """Fetch URL content."""
    ...
```

#### Step 1.2: Update server.py to discover

**File:** `src/loom/server.py`

Add near top:
```python
from loom.tool_registry import discover_tools, register_all_with_mcp
from pathlib import Path
```

In `create_app()`:
```python
async def create_app() -> FastMCP:
    mcp = FastMCP("loom")
    
    # New auto-discovery system
    try:
        discovered = discover_tools(Path("src/loom/tools"))
        log.info(f"Discovered {discovered} tool modules")
        register_all_with_mcp(mcp, _wrap_tool)
    except Exception as e:
        log.error(f"Tool discovery failed: {e}", exc_info=True)
    
    # ... rest of setup ...
```

#### Step 1.3: Validate

Run tests:
```bash
# Verify tool still works
pytest tests/test_tools/test_fetch.py

# Verify decorator applied
python3 -c "
from loom.tool_registry import get_registered_tool
tool = get_registered_tool('research_fetch')
assert tool is not None
assert tool['category'] == 'research'
print('✓ Tool registered correctly')
"

# Verify registry integrity
python3 -c "
from loom.tool_registry import validate_registry
is_valid, errors = validate_registry()
assert is_valid, errors
print('✓ Registry valid')
"
```

#### Step 1.4: Keep old registration (parallel)

In server.py, keep the old manual registration to avoid breaking anything:

```python
# Old system - remove this after migration complete
with suppress(ImportError):
    from loom.tools import fetch as fetch_tools
    _optional_tools["fetch"] = fetch_tools
    record_optional_module_loaded("fetch")
```

#### Step 1.5: Commit and verify

```bash
git add src/loom/tools/fetch.py src/loom/server.py
git commit -m "feat(tool_registry): add @loom_tool decorator to research_fetch

- Apply decorator with category and description
- Tool auto-registers via discovery system
- Maintains backward compatibility with manual registration
- Verified in tests

Closes INTEGRATE-???
"
```

### Phase 2: Batch Convert Similar Tools (Week 2)

#### Step 2.1: Group tools by category

```python
# Search tools (10-15 tools)
- research_search
- research_spider
- research_deep
- research_github

# LLM tools (5-10 tools)
- research_llm_summarize
- research_llm_extract
- research_llm_classify

# Analysis tools (20-30 tools)
- research_code_analysis
- research_threat_profile
- research_sentiment
```

#### Step 2.2: Convert in batches

Apply decorator to all tools in a group:

```python
# src/loom/tools/search.py
from loom.tool_registry import loom_tool

@loom_tool(category="research", description="Web search via multiple providers")
async def research_search(query: str, provider: str = "exa") -> dict:
    ...

@loom_tool(category="research", description="Multi-URL spider")
async def research_spider(urls: list[str]) -> dict:
    ...

@loom_tool(category="research", description="Deep research pipeline")
async def research_deep(query: str) -> dict:
    ...
```

#### Step 2.3: Test and validate

```bash
# Test all search tools
pytest tests/test_tools/test_search.py

# Verify discovery
python3 -c "
from loom.tool_registry import get_tools_by_category
search_tools = get_tools_by_category('research')
assert len(search_tools) >= 3
print(f'✓ Found {len(search_tools)} research tools')
"
```

### Phase 3: Convert Large Tool Categories (Week 3-4)

Repeat the pattern for:
- Infrastructure tools (IP, DNS, cert analysis)
- Provider wrappers (Groq, Claude, etc.)
- Analysis tools (text, sentiment, code)
- Utility tools (cache, config, sessions)

### Phase 4: Remove Manual Registration (Week 5)

Once all tools are converted:

```python
# src/loom/server.py - DELETE all manual imports

# ✗ DELETE THESE:
# with suppress(ImportError):
#     from loom.tools import fetch as fetch_tools
#     _optional_tools["fetch"] = fetch_tools
#     record_optional_module_loaded("fetch")

# ✓ KEEP ONLY THIS:
from loom.tool_registry import discover_tools, register_all_with_mcp

async def create_app() -> FastMCP:
    mcp = FastMCP("loom")
    discover_tools(Path("src/loom/tools"))
    register_all_with_mcp(mcp, _wrap_tool)
    # ... rest of setup ...
```

## Testing During Migration

### Test 1: Verify Decorator Applied

```python
def test_tool_has_decorator():
    from loom.tool_registry import get_registered_tool
    tool = get_registered_tool("research_fetch")
    assert tool is not None
    assert tool["is_async"] is True
    assert tool["category"] == "research"
```

### Test 2: Verify Auto-Discovery

```python
def test_tools_discovered():
    from loom.tool_registry import discover_tools
    count = discover_tools(Path("src/loom/tools"))
    assert count > 0
```

### Test 3: Verify MCP Registration

```python
def test_tools_register_with_mcp():
    from unittest.mock import MagicMock
    from loom.tool_registry import register_all_with_mcp
    
    mock_mcp = MagicMock()
    count = register_all_with_mcp(mock_mcp, lambda x: x)
    assert count > 0
```

### Test 4: Verify Tool Still Works

Existing tests should still pass:

```bash
# Tool functionality unchanged
pytest tests/test_tools/test_fetch.py::test_research_fetch_http_mode

# Registry knows about it
pytest tests/test_tool_registry.py::TestDemoDecoratorUsage
```

## Backward Compatibility

The migration is **fully backward compatible**:

1. **Existing manual imports still work** - can run both systems in parallel
2. **No breaking changes** - decorated functions behave identically
3. **Gradual deprecation** - can remove manual registration when ready
4. **Easy rollback** - just revert commits if needed

## Validation Checklist

Before declaring migration complete:

- [ ] All 711 tools have `@loom_tool` decorator
- [ ] `validate_registry()` returns no errors
- [ ] `get_registry_stats()` shows all tools categorized
- [ ] Server starts without manual imports
- [ ] All existing tests pass
- [ ] New tests for registry system pass
- [ ] Documentation updated
- [ ] Manual registration code removed from `server.py`
- [ ] Performance benchmarks acceptable

## Rollback Plan

If issues occur during migration:

```bash
# Revert to last good commit
git revert <commit-hash>

# Or reset to before migration started
git reset --hard <pre-migration-commit>

# Re-enable manual registration temporarily
git checkout HEAD -- src/loom/server.py
```

## Performance Impact

Expected performance changes:

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Startup time | N/A | ~100-150ms | +100ms discovery |
| Memory per tool | N/A | ~1KB | +700KB total |
| Tool lookup | Manual | O(1) dict | Better |
| Registry validation | None | O(n) | Built-in |

**Recommendation:** Discovery overhead is acceptable for benefits gained.

## Success Criteria

Migration is successful when:

1. ✓ All tools discovered and registered
2. ✓ Server starts without manual imports
3. ✓ All tests pass
4. ✓ No functional changes to tools
5. ✓ Documentation updated
6. ✓ Zero user impact

## Troubleshooting

### Issue: Tool not discovered

**Solution:**
1. Check `@loom_tool` decorator applied
2. Check module is in `src/loom/tools/`
3. Check module name doesn't start with `_`
4. Check for import errors in logs

### Issue: Duplicate registration

**Solution:**
1. If running parallel system, keep both running
2. Remove manual registration once decorator applied
3. Use `validate_registry()` to check for dupes

### Issue: Tests failing after migration

**Solution:**
1. Run with old system only to verify
2. Check function signatures unchanged
3. Verify test imports updated
4. Check for timing issues (async vs sync)

## Questions & Answers

**Q: Do I need to remove manual registration immediately?**
A: No - can run both systems in parallel indefinitely.

**Q: Will this break existing tools?**
A: No - decorator is transparent, function works unchanged.

**Q: How long does discovery take?**
A: ~100-150ms for 154 modules - acceptable for startup.

**Q: Can I selectively enable tools?**
A: Yes - future enhancement to discover specific categories.

**Q: What about external tools?**
A: They can still be manually imported; discovery finds `src/loom/tools` only.

## Contact & Support

Questions about migration? See:
- Architecture: `docs/TOOL_REGISTRY_ARCHITECTURE.md`
- Tests: `tests/test_tool_registry.py`
- Demo: `src/loom/tools/demo_decorator_usage.py`

For issues: Check logs for import errors, run validation tests.

---

**Status:** Migration path documented and ready for execution
**Created:** 2026-05-03
**Target Completion:** Week 5-6
**Effort:** ~40 hours for full migration
