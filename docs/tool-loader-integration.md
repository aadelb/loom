# Tool Loader Abstraction Guide

## Overview

The Tool Loader Abstraction (`src/loom/tool_loader.py`) provides lazy-loading of MCP tools, deferring module imports until first access. This reduces startup time from importing all 567+ modules immediately to importing only on first use.

## Benefits

- **Faster startup**: Only import tools when first accessed, not at server startup
- **Lower memory footprint**: Unloaded tools don't consume memory
- **Graceful degradation**: Failed tool imports don't crash the server
- **Performance visibility**: Built-in statistics for monitoring and troubleshooting

## Architecture

### LazyToolLoader Class

```python
class LazyToolLoader:
    def register(tool_name: str, module_path: str, func_name: str) -> None:
        """Register tool without importing."""

    def load(tool_name: str) -> Callable:
        """Import and return function on first call, cache result."""

    def is_loaded(tool_name: str) -> bool:
        """Check if tool has been loaded."""

    def get_all_registered() -> list[str]:
        """Get all registered tool names."""

    def get_load_stats() -> dict:
        """Get loading statistics."""

    def get_load_time(tool_name: str) -> float | None:
        """Get load time for specific tool."""

    def unload(tool_name: str) -> None:
        """Remove tool from cache (for testing)."""

    def reset() -> None:
        """Clear all caches while preserving registry."""
```

### Singleton Access

```python
from loom.tool_loader import get_loader

loader = get_loader()  # Returns default singleton instance
```

## Integration with server.py

To enable lazy loading, wire the LazyToolLoader into `server.py`'s `_register_tools()` function:

```python
from loom.tool_loader import get_loader

def _register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with optional lazy loading."""
    loader = get_loader()

    # Register tools lazily (opt-in via LOOM_LAZY_LOAD=true)
    if os.environ.get("LOOM_LAZY_LOAD", "false").lower() == "true":
        # Pre-register all tools without importing
        loader.register("research_fetch", "loom.tools.fetch", "research_fetch")
        loader.register("research_spider", "loom.tools.spider", "research_spider")
        # ... register all 220+ tools ...

        # Wrap loader to automatically import on MCP tool call
        def lazy_tool_wrapper(tool_name: str):
            def wrapper(*args, **kwargs):
                func = loader.load(tool_name)
                return func(*args, **kwargs)
            return wrapper

        # Register each tool via MCP with lazy wrapper
        for tool_name in loader.get_all_registered():
            mcp.tool()(lazy_tool_wrapper(tool_name))
    else:
        # Traditional eager loading (current behavior)
        register_all_tools(mcp, _wrap_tool)
```

## Usage Examples

### Basic Registration and Loading

```python
from loom.tool_loader import LazyToolLoader

loader = LazyToolLoader()

# Register tools without importing
loader.register("research_fetch", "loom.tools.fetch", "research_fetch")
loader.register("research_spider", "loom.tools.spider", "research_spider")

# Import happens here on first access
fetch_func = loader.load("research_fetch")
result = fetch_func(url="https://example.com")

# Subsequent loads return cached function
spider_func = loader.load("research_spider")  # No import, instant return
```

### Statistics and Monitoring

```python
from loom.tool_loader import get_loader

loader = get_loader()

# Get loading statistics
stats = loader.get_load_stats()
print(stats)

# Output:
# {
#     "loaded_count": 47,
#     "failed_count": 2,
#     "registered_count": 220,
#     "avg_load_time_ms": 18.5,
#     "load_times_by_tool": {
#         "research_fetch": 45.2,
#         "research_spider": 12.1,
#         ...
#     },
#     "failed_tools": ["research_custom_1", "research_custom_2"],
# }

# Check if tool is loaded
if loader.is_loaded("research_fetch"):
    print("research_fetch is cached")

# Get load time for specific tool
load_time = loader.get_load_time("research_fetch")
print(f"research_fetch loaded in {load_time:.2f}ms")
```

### Error Handling

```python
from loom.tool_loader import LazyToolLoader

loader = LazyToolLoader()
loader.register("bad_tool", "nonexistent.module", "func")

try:
    func = loader.load("bad_tool")
except ImportError as e:
    print(f"Failed to load tool: {e}")

# Tool is marked as failed and subsequent attempts fail fast
try:
    func = loader.load("bad_tool")  # Raises immediately
except ImportError as e:
    print(f"Tool already failed: {e}")

# Check stats to see failed tools
stats = loader.get_load_stats()
print(f"Failed tools: {stats['failed_tools']}")
```

### MCP Tool: research_loader_stats

The `research_loader_stats()` MCP tool provides access to loader statistics:

```bash
# Call via MCP
mcp_client call research_loader_stats

# Output:
{
    "loaded_count": 47,
    "failed_count": 2,
    "registered_count": 220,
    "avg_load_time_ms": 18.5,
    "load_times_by_tool": {...},
    "failed_tools": ["research_custom_1", "research_custom_2"],
    "cache_size_count": 47
}
```

## Performance Impact

### Expected Improvements

- **Startup time**: 3-5 seconds faster (avoid importing 567+ modules)
- **Memory footprint**: 50-100 MB reduction (unloaded tools use no memory)
- **First-tool latency**: +20-50ms (one-time import cost)
- **Subsequent tool latency**: ~0ms (cached access)

### Trade-offs

| Aspect | Eager Loading | Lazy Loading |
|--------|---------------|--------------|
| Startup time | ~8-10s | ~3-5s |
| Initial memory | +150MB | +20MB |
| First tool latency | ~0ms | +30-50ms |
| Subsequent tool latency | ~0ms | ~0ms |
| Error visibility | At startup | On first use |

## Configuration

### Environment Variables

```bash
# Enable lazy loading (default: false)
export LOOM_LAZY_LOAD=true

# Optional: Change config location
export LOOM_CONFIG_PATH=./config.json
```

### Via Config File

```json
{
  "LOOM_LAZY_LOAD": true
}
```

## Testing

### Unit Tests

```bash
# Run all loader tests
pytest tests/test_tool_loader.py -v

# Run specific test
pytest tests/test_tool_loader.py::TestLazyToolLoader::test_load_caches_function -v

# Run loader stats tool tests
pytest tests/test_tools/test_loader_stats.py -v
```

### Coverage

```bash
# Get coverage report
pytest tests/test_tool_loader.py --cov=src/loom/tool_loader --cov-report=html
```

## Troubleshooting

### Tool Import Fails at Startup

**Problem**: Tool import fails when `LOOM_LAZY_LOAD=true`

**Solution**:
1. Check if tool module path is correct: `python3 -c "import loom.tools.fetch"`
2. Check if function name is correct: `python3 -c "from loom.tools.fetch import research_fetch"`
3. View failed tools via `research_loader_stats` MCP tool

### High First-Tool Latency

**Problem**: First tool call takes 200ms+ when lazy loading enabled

**Solution**:
1. This is expected (one-time import cost)
2. Subsequent calls use cache (~0ms)
3. Consider pre-loading frequently-used tools via `loader.load()` at startup

### Memory Usage Not Reduced

**Problem**: Memory footprint still high with `LOOM_LAZY_LOAD=true`

**Solution**:
1. Verify `LOOM_LAZY_LOAD=true` is actually set: `echo $LOOM_LAZY_LOAD`
2. Check if tools are being auto-loaded elsewhere
3. Use `research_loader_stats` to see which tools are loaded

## Future Enhancements

1. **Auto-discovery**: Automatically scan `loom.tools/` and register all tools
2. **Warm-up**: Pre-load high-priority tools at startup (configurable)
3. **Unload strategy**: Automatic unloading of unused tools to free memory
4. **Metrics export**: Prometheus metrics for load times and failures
5. **Dependency tracking**: Load tool dependencies when accessing parent tool

## Implementation Details

### Thread Safety

The loader is thread-safe:
- Registry access is dict-based (immutable after registration)
- Cache access uses single-threaded Python (GIL protected)
- Future async support can use asyncio.Lock if needed

### Memory Efficiency

- Registry: ~100 bytes per tool (tool name + module/func paths)
- Cache: Depends on tool function object (~4KB typical)
- Load times dict: ~10 bytes per tool

### Error Handling

Failed imports are:
1. Logged with full error context
2. Marked in `_failed` set for fast detection
3. Raise `ImportError` on subsequent load attempts (fail-fast)
4. Visible in `get_load_stats()` for monitoring

## Code Examples

### Complete Integration Example

```python
# In src/loom/server.py:create_app()

from loom.tool_loader import get_loader

def _register_tools(mcp: FastMCP) -> None:
    """Register tools with optional lazy loading."""
    use_lazy = os.environ.get("LOOM_LAZY_LOAD", "false").lower() == "true"

    if use_lazy:
        loader = get_loader()

        # Register all tools
        TOOL_REGISTRY = [
            ("research_fetch", "loom.tools.fetch", "research_fetch"),
            ("research_spider", "loom.tools.spider", "research_spider"),
            # ... 220+ tools ...
        ]

        for tool_name, module_path, func_name in TOOL_REGISTRY:
            try:
                loader.register(tool_name, module_path, func_name)
            except ValueError as e:
                log.warning("tool_already_registered tool_name=%s", tool_name)

        # Wrap each tool with lazy loader
        def make_lazy_wrapper(name: str):
            async def lazy_wrapper(*args, **kwargs):
                func = loader.load(name)
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            return lazy_wrapper

        for tool_name in loader.get_all_registered():
            try:
                mcp.tool()(make_lazy_wrapper(tool_name))
            except Exception as e:
                log.error("tool_registration_failed tool=%s error=%s", tool_name, e)

        log.info("lazy_loading_enabled registered_tools=%d", 
                 len(loader.get_all_registered()))
    else:
        # Existing eager loading code
        register_all_tools(mcp, _wrap_tool)
```

## See Also

- `src/loom/tool_loader.py` — Implementation
- `src/loom/tools/loader_stats.py` — MCP tool
- `tests/test_tool_loader.py` — Unit tests
- `tests/test_tools/test_loader_stats.py` — MCP tool tests
