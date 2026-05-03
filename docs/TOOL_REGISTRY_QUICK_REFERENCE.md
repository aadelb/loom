# Tool Registry: Quick Reference Card

## The Decorator (3 lines to add)

```python
from loom.tool_registry import loom_tool

@loom_tool(category="intelligence", description="Brief description")
async def your_tool_name(param: str) -> dict:
    """Implementation here."""
    pass
```

## Registry Queries

```python
from loom.tool_registry import (
    get_all_registered_tools,      # All tools
    get_tools_by_category,          # Filter by category
    get_registered_tool,            # Get specific tool
    get_registry_stats,             # Stats (total, async, by_category)
    validate_registry,              # Check integrity
    print_registry,                 # Pretty print
)

# Usage
all_tools = get_all_registered_tools()
intel_tools = get_tools_by_category("intelligence")
tool = get_registered_tool("research_fetch")
stats = get_registry_stats()
is_valid, errors = validate_registry()
print_registry()
```

## Discovery & Registration

```python
from pathlib import Path
from loom.tool_registry import discover_tools, register_all_with_mcp

# Discover all tools with decorators
count = discover_tools(Path("src/loom/tools"))

# Register with MCP server
registered = register_all_with_mcp(mcp, wrap_tool)
```

## Common Categories

```
research            # Core research (fetch, search, etc.)
intelligence        # Threat intelligence
analysis            # Code/text/data analysis
infrastructure      # Networking, DNS, IP
data_processing     # ETL, transformation
security            # Security scanning
darkweb            # Tor, underground research
academic           # Academic integrity
```

## Testing Your Tool

```python
# Unit test
def test_my_tool():
    result = my_tool("test_param")
    assert result is not None

# Registry test
def test_my_tool_registered():
    from loom.tool_registry import get_registered_tool
    tool = get_registered_tool("my_tool_name")
    assert tool is not None
    assert tool["category"] == "intelligence"

# Run tests
pytest tests/test_tool_registry.py -v
pytest tests/test_tools/test_my_tool.py -v
```

## Validate Registry

```python
python3 << 'EOF'
from loom.tool_registry import validate_registry, get_registry_stats

# Check integrity
is_valid, errors = validate_registry()
if not is_valid:
    for error in errors:
        print(f"ERROR: {error}")
else:
    print("✓ Registry valid")

# Show stats
stats = get_registry_stats()
print(f"Total: {stats['total']} tools")
print(f"Async: {stats['async']}, Sync: {stats['sync']}")
EOF
```

## Before & After

### BEFORE (Manual)
```python
# Step 1: in server.py, import
with suppress(ImportError):
    from loom.tools import my_tool as my_tool_module
    _optional_tools["my_tool"] = my_tool_module

# Step 2: in _register_tools(), register
mcp.tool()(wrap_tool(my_tool_module.my_tool_func))

# Step 3: hope nothing breaks
```

### AFTER (Auto-Discovery)
```python
# Step 1: in tool file, decorate
@loom_tool(category="intelligence")
def my_tool_func(...): ...

# Step 2: in server.py, discover
discover_tools(Path("src/loom/tools"))
register_all_with_mcp(mcp, wrap_tool)

# Step 3: done! No registration lists to maintain
```

## API Functions Reference

| Function | Purpose | Returns |
|----------|---------|---------|
| `@loom_tool(category, desc)` | Decorator to register tool | Original function |
| `get_all_registered_tools()` | Get all tools | `{name: info}` dict |
| `get_tools_by_category(cat)` | Filter by category | `{name: info}` dict |
| `get_registered_tool(name)` | Get specific tool | Tool info dict or None |
| `get_registry_stats()` | Registry statistics | Stats dict |
| `discover_tools(path)` | Auto-import modules | Count of imported |
| `register_all_with_mcp(mcp, wrap)` | Register with server | Count of registered |
| `validate_registry()` | Check integrity | (is_valid, errors list) |
| `clear_registry()` | Empty registry | None |
| `print_registry()` | Pretty print | None |

## Parameters Object

```python
class ToolInfo:
    func: Callable              # The function
    category: str               # Category name
    description: str            # Human-readable description
    module: str                 # Module path (e.g., "loom.tools.fetch")
    is_async: bool              # True if async
    name: str                   # Function name
    
    def to_dict(self) -> dict:  # Convert to dictionary
        ...
```

## Tool Metadata Example

```python
{
    "func": <function research_fetch>,
    "category": "research",
    "description": "Unified URL fetcher with HTTP, stealth, and dynamic modes",
    "module": "loom.tools.fetch",
    "is_async": True,
    "name": "research_fetch"
}
```

## Performance Notes

| Operation | Complexity | Time |
|-----------|-----------|------|
| Discover all tools | O(n) | ~100ms for 154 modules |
| Get all tools | O(1) | <1ms |
| Get by category | O(n) | <10ms for 711 tools |
| Get specific tool | O(1) | <1ms |
| Validate registry | O(n) | ~50ms for 711 tools |

## Troubleshooting 1-2-3

**1. Tool not discovered?**
```bash
# Check decorator applied
grep "@loom_tool" src/loom/tools/my_tool.py

# Check module is there
ls src/loom/tools/my_tool.py

# Check for import errors
python3 -c "from loom.tools import my_tool; print('OK')"
```

**2. Tool not working?**
```bash
# Verify registry
python3 -c "
from loom.tool_registry import validate_registry
is_valid, errors = validate_registry()
print(f'Valid: {is_valid}')
for e in errors: print(f'  {e}')
"

# Test function directly
python3 -c "from loom.tools.my_tool import my_func; print(my_func('test'))"
```

**3. Registry broken?**
```bash
# Clear and rediscover
python3 -c "
from loom.tool_registry import clear_registry, discover_tools
from pathlib import Path
clear_registry()
discover_tools(Path('src/loom/tools'))
"

# Validate
python3 -c "from loom.tool_registry import validate_registry; print(validate_registry())"
```

## Common Commands

```bash
# Run registry tests
pytest tests/test_tool_registry.py -v

# Check tool is registered
python3 -c "from loom.tool_registry import get_registered_tool; \
print(get_registered_tool('research_fetch'))"

# List all tools by category
python3 << 'EOF'
from loom.tool_registry import get_registry_stats
stats = get_registry_stats()
for cat, count in sorted(stats['by_category'].items()):
    print(f"{cat}: {count}")
EOF

# Validate entire registry
python3 -c "from loom.tool_registry import validate_registry; \
is_valid, errors = validate_registry(); \
print(f'Valid: {is_valid}'); \
[print(f'  {e}') for e in errors]"

# Pretty print registry
python3 -c "from loom.tool_registry import print_registry; print_registry()"
```

## Migration Checklist

- [ ] Read TOOL_REGISTRY_ARCHITECTURE.md
- [ ] Read TOOL_REGISTRY_MIGRATION_GUIDE.md
- [ ] Review demo_decorator_usage.py examples
- [ ] Run test suite: `pytest tests/test_tool_registry.py`
- [ ] Add @loom_tool to first tool
- [ ] Verify tool still works
- [ ] Verify registry discovers it
- [ ] Run validation: `validate_registry()`
- [ ] Add to next batch of tools
- [ ] Repeat until all tools decorated
- [ ] Remove manual registration from server.py
- [ ] Final validation and testing

## Files Reference

| File | Purpose | Status |
|------|---------|--------|
| `src/loom/tool_registry.py` | Core implementation | ✓ Ready |
| `src/loom/tools/demo_decorator_usage.py` | Examples | ✓ Ready |
| `tests/test_tool_registry.py` | Tests | ✓ Ready |
| `docs/TOOL_REGISTRY_ARCHITECTURE.md` | Architecture | ✓ Ready |
| `docs/TOOL_REGISTRY_MIGRATION_GUIDE.md` | Migration | ✓ Ready |
| `docs/TOOL_REGISTRY_QUICK_REFERENCE.md` | This file | ✓ Ready |

---

**This is a reference card. For details, see the full documentation.**
