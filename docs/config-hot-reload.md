# Config Hot-Reload System

The Loom config hot-reload system enables real-time monitoring and synchronization of `config.json` changes without restarting the MCP server.

## Overview

Three tools work together to provide hot-reload functionality:

1. **`research_config_watch`** — Start monitoring config.json
2. **`research_config_check`** — Poll for changes and reload if detected
3. **`research_config_diff`** — Show what changed between old and new config

## Quick Start

### 1. Start Watching

```python
result = research_config_watch()
# Returns: {watching: True, config_path: str, last_modified: float}
```

This captures the initial file modification time (mtime) and current config state.

### 2. Check for Changes

```python
result = research_config_check()
# Returns: {changed: bool, reloaded: bool, current_settings: dict}
```

If the file has been modified since the last watch/check:
- Sets `changed: True`
- Reloads config via `load_config()`
- Updates module state
- Returns the new `current_settings`

### 3. View What Changed

```python
result = research_config_diff()
# Returns: {changes: list[{key, old_value, new_value}], unchanged_count: int}
```

Or check a specific key:

```python
result = research_config_diff("SPIDER_CONCURRENCY")
# Returns: {changes: [{key, old_value, new_value}], unchanged_count: int}
```

## Implementation Details

### Module State

The system maintains three pieces of module-level state in `_watch_state`:

```python
{
    "watching": bool,          # Whether watching is active
    "config_path": str,        # Absolute path to config file
    "last_mtime": float,       # Last recorded file modification time
    "last_config": dict,       # Snapshot of config at last watch/check
}
```

### File Monitoring Mechanism

- Uses `pathlib.Path.stat().st_mtime` for efficient file change detection
- No polling loops or continuous threads needed
- Caller determines check frequency via repeated `research_config_check()` calls

### Config Reloading

When changes are detected:

1. `load_config(path)` is called to reload from disk
2. Validation happens via Pydantic `ConfigModel`
3. Module-level `CONFIG` dict is updated
4. State is synchronized for future diffs

## Usage Patterns

### Pattern 1: Reactive Reload

Start watching, then periodically check for changes:

```python
# Initialize
research_config_watch()

# In a loop or timer callback
while should_run:
    check_result = research_config_check()
    if check_result["changed"]:
        # Config was reloaded automatically
        print("Config updated:", check_result["current_settings"])
    await asyncio.sleep(5)  # Check every 5 seconds
```

### Pattern 2: Change Notification

Check what changed and log differences:

```python
result = research_config_watch()

# ... time passes, user edits config.json ...

check_result = research_config_check()
if check_result["changed"]:
    diff_result = research_config_diff()
    for change in diff_result["changes"]:
        print(f"Changed: {change['key']}")
        print(f"  Old: {change['old_value']}")
        print(f"  New: {change['new_value']}")
```

### Pattern 3: Selective Key Monitoring

Watch specific config values:

```python
research_config_watch()

# ... time passes ...

check_result = research_config_check()
if check_result["changed"]:
    # Only interested in rate limit changes?
    rate_limit_diff = research_config_diff("RATE_LIMIT_SEARCH_PER_MIN")
    if rate_limit_diff["changes"]:
        print("Rate limit changed!")
```

## Error Handling

### File Not Found

Both `watch()` and `check()` return `{watching: False, error: ...}` if the config file doesn't exist.

### No Previous Watch State

If `check()` is called without a prior `watch()` call:
- Initializes state on first call
- Returns `{changed: False, reloaded: False}`
- Subsequent calls work normally

### Diff Without Watch

`research_config_diff()` gracefully handles missing `last_config`:
- Returns `{changes: [], unchanged_count: <current_count>}`
- Useful for showing current config state

## API Reference

### research_config_watch(config_path: str | None = None) -> dict

Start watching config.json for modifications.

**Args:**
- `config_path` (optional): Explicit path to config file. If not provided, uses `_resolve_path()` which checks `$LOOM_CONFIG_PATH` then `./config.json`.

**Returns:**
- `watching` (bool): True if watch started successfully
- `config_path` (str): Absolute path being watched
- `last_modified` (float): File mtime at watch start (unix timestamp)
- `error` (str, optional): Error message if watch failed

### research_config_check(config_path: str | None = None) -> dict

Check if config has changed and reload if needed.

**Args:**
- `config_path` (optional): Override config path. If not provided, uses path from watch state.

**Returns:**
- `changed` (bool): True if file mtime differs from last recorded
- `reloaded` (bool): True if `load_config()` was called
- `current_settings` (dict): Current config (top-level keys only)
- `error` (str, optional): Error message if check failed

### research_config_diff(key: str = "") -> dict

Show what changed between old and new config.

**Args:**
- `key` (str, optional): If provided, only show changes for this key

**Returns:**
- `changes` (list[dict]): Each dict has `key`, `old_value`, `new_value`
- `unchanged_count` (int): Number of keys that didn't change

## Performance Notes

- **Minimal Overhead**: Only reads file metadata (mtime), not file contents
- **Lazy Reload**: Config only reloaded when changes are actually detected
- **No Background Threads**: Caller controls check frequency
- **Memory Safe**: Snapshots are shallow dicts, safe for GC

## Limitations

- Detection granularity is filesystem timestamp resolution (typically 1ms on modern systems)
- Rapid file changes (within 1ms) might be missed
- Clock adjustments can affect mtime comparisons
- Config changes only take effect after `check()` is called
- Symbolic links are resolved, actual file path is monitored

## Testing

Comprehensive test suite in `tests/test_tools/test_config_reload.py`:

- Watch initialization and state management
- Change detection and reloading
- Diff calculation (all changes, no changes, single key, new/removed keys)
- Integration workflow (watch → check → diff)
- Error handling (missing file, no watch state, etc.)

Run tests:
```bash
pytest tests/test_tools/test_config_reload.py -v
```

## See Also

- `src/loom/config.py` — Main config loading and persistence
- `src/loom/server.py` — Tool registration (line ~1036)
- `src/loom/tools/config_reload.py` — Implementation (185 lines)
