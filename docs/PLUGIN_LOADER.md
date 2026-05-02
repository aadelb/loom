# Plugin Loader

The Plugin Loader (`research_plugin_*`) provides a dynamic mechanism to load external tool modules at runtime without modifying the core Loom codebase.

## Overview

The plugin loader system allows you to:

- Load Python modules as Loom plugins from any filesystem path
- Automatically discover `research_*` async functions in plugins
- List all loaded plugins and their tools
- Unload plugins when no longer needed
- Store plugin metadata for tracking and management

## Tools

### research_plugin_load

Load a Python file as a Loom plugin.

**Parameters:**
- `path` (string, required): Absolute path to a `.py` plugin file

**Returns:**
```json
{
  "loaded": true,
  "path": "/path/to/plugin.py",
  "tools_found": ["research_custom_tool", "research_another_tool"],
  "plugin_id": "plugin_abc123def456"
}
```

**Validation:**
- File must exist at the specified path
- File must have `.py` extension
- File must contain at least one `research_*` async function
- Invalid Python syntax will be reported in the error field

**Example:**

```bash
loom research_plugin_load /path/to/my_plugin.py
```

---

### research_plugin_list

List all currently loaded plugins and their metadata.

**Parameters:** None

**Returns:**
```json
{
  "plugins": [
    {
      "id": "plugin_abc123def456",
      "path": "/path/to/plugin.py",
      "tools": ["research_custom_tool"],
      "loaded_at": "2026-05-02T15:30:45.123456"
    }
  ],
  "total": 1
}
```

**Example:**

```bash
loom research_plugin_list
```

---

### research_plugin_unload

Remove a plugin from the registry.

**Parameters:**
- `plugin_id` (string, required): Plugin ID returned from `research_plugin_load`

**Returns:**
```json
{
  "unloaded": true,
  "plugin_id": "plugin_abc123def456"
}
```

**Example:**

```bash
loom research_plugin_unload plugin_abc123def456
```

---

## Creating a Plugin

A Loom plugin is a Python file containing one or more `research_*` async functions.

### Minimal Plugin Example

**File: `my_plugin.py`**

```python
"""Custom Loom plugin for domain-specific research."""

from __future__ import annotations

from typing import Any


async def research_custom_lookup(query: str) -> dict[str, Any]:
    """Perform a custom lookup operation.
    
    Args:
        query: Search query string
        
    Returns:
        Dictionary with results
    """
    return {
        "query": query,
        "result": f"Custom result for: {query}",
        "source": "custom_plugin"
    }


async def research_custom_analyze(data: str) -> dict[str, Any]:
    """Analyze custom data.
    
    Args:
        data: Data to analyze
        
    Returns:
        Dictionary with analysis results
    """
    return {
        "input": data,
        "analysis": "analysis results",
        "score": 0.95
    }
```

Load the plugin:

```bash
loom research_plugin_load /absolute/path/to/my_plugin.py
```

Response:

```json
{
  "loaded": true,
  "path": "/absolute/path/to/my_plugin.py",
  "tools_found": ["research_custom_lookup", "research_custom_analyze"],
  "plugin_id": "plugin_a1b2c3d4e5f6"
}
```

---

## Plugin Architecture

### File Structure

```
plugins/
├── my_plugin.py          # Custom plugin
├── advanced_plugin.py    # Advanced plugin with dependencies
└── specialized_plugin.py # Domain-specific plugin
```

### Implementation Pattern

```python
"""Plugin module docstring."""

from __future__ import annotations

import asyncio
from typing import Any


async def research_tool_one(param1: str) -> dict[str, Any]:
    """Tool implementation."""
    # Your implementation here
    return {"status": "success"}


async def research_tool_two(param1: str, param2: int) -> dict[str, Any]:
    """Another tool implementation."""
    # Your implementation here
    return {"status": "success"}


# Non-research functions are ignored by the loader
def helper_function():
    """This function won't be registered as a Loom tool."""
    pass
```

### Function Requirements

- Must be async (coroutine)
- Name must start with `research_`
- Must be callable with keyword arguments
- Should return a dictionary

---

## Error Handling

### File Not Found

```bash
$ loom research_plugin_load /nonexistent/path.py
```

Response:

```json
{
  "loaded": false,
  "path": "/nonexistent/path.py",
  "tools_found": [],
  "error": "File does not exist"
}
```

### Invalid File Extension

```bash
$ loom research_plugin_load /path/to/plugin.txt
```

Response:

```json
{
  "loaded": false,
  "path": "/path/to/plugin.txt",
  "tools_found": [],
  "error": "File must be .py extension"
}
```

### No Research Functions

```bash
$ loom research_plugin_load /path/to/regular_module.py
```

Response:

```json
{
  "loaded": false,
  "path": "/path/to/regular_module.py",
  "tools_found": [],
  "error": "No research_* async functions found"
}
```

### Invalid Python Syntax

```bash
$ loom research_plugin_load /path/to/broken_syntax.py
```

Response:

```json
{
  "loaded": false,
  "path": "/path/to/broken_syntax.py",
  "tools_found": [],
  "error": "invalid syntax (<unknown>, line 1)"
}
```

---

## Use Cases

### 1. Custom Research Tools

Create specialized tools for your organization's research needs without modifying Loom core.

```python
# compliance_plugin.py
async def research_compliance_check(domain: str) -> dict[str, Any]:
    """Check domain for compliance violations."""
    # Your custom compliance checking logic
    return {"domain": domain, "compliant": True}
```

### 2. Integration Extensions

Add integrations with internal systems without changing the main codebase.

```python
# internal_api_plugin.py
async def research_internal_api_query(endpoint: str, method: str = "GET") -> dict[str, Any]:
    """Query internal API endpoint."""
    # Integration with internal APIs
    return {"endpoint": endpoint, "method": method, "status": "success"}
```

### 3. Specialized Analysis

Implement domain-specific analysis tools for particular use cases.

```python
# nlp_plugin.py
async def research_nlp_sentiment(text: str) -> dict[str, Any]:
    """Analyze sentiment using custom NLP model."""
    # Your NLP implementation
    return {"text": text, "sentiment": "positive", "score": 0.85}
```

---

## Best Practices

1. **Use Type Hints**: All functions should have complete type annotations
2. **Document Functions**: Include docstrings explaining parameters and return values
3. **Handle Errors**: Return appropriate error information in responses
4. **Keep Functions Pure**: Avoid side effects where possible
5. **Use Absolute Paths**: Always use absolute paths when loading plugins
6. **Name Consistently**: Follow the `research_*` naming convention
7. **Test Thoroughly**: Test plugins locally before deploying

---

## Limitations

- Plugins are loaded into the same Python process as Loom
- No sandboxing or isolation between plugins
- Plugins cannot be hot-reloaded; must unload and reload to update
- File must exist and be readable from the Loom server process
- No automatic dependency resolution; manage dependencies manually

---

## Registry

The plugin registry is stored in memory and cleared when the Loom server restarts. For persistent plugins:

1. Store plugin files in a known location
2. Load them via initialization scripts
3. Or manage them via configuration files

---

## See Also

- [Tools Reference](tools-reference.md)
- [Architecture Guide](architecture.md)
