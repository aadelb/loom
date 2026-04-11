# Runtime Configuration Management

Loom supports runtime configuration changes without restarting the server. Use `research_config_get` and `research_config_set` to view and modify settings dynamically.

## How It Works

### Architecture

1. **On Disk:** Configuration lives in `config.json` (default location: `~/.config/loom/config.json`, or `LOOM_CONFIG_PATH` env var)
2. **In Memory:** A module-level `CONFIG` dict in `loom.config` is loaded at startup
3. **Updates:** `research_config_set(key, value)` validates the value against Pydantic schema, writes atomically to disk (uuid temp file + os.replace), and updates the in-memory dict
4. **Propagation:** All tools use lazy imports from `loom.config.CONFIG`, so changes take effect immediately

### Atomic Writes

When you call `research_config_set("SPIDER_CONCURRENCY", 10)`:

1. New value is validated by Pydantic (must be int, 1–20)
2. Entire config is read from disk
3. Value is updated
4. New config is written to a temporary file with a UUID-based name
5. Temporary file is atomically renamed to `config.json` (os.replace)
6. In-memory CONFIG dict is updated

This prevents corruption if multiple processes or threads call `research_config_set` concurrently.

## Mutable Configuration Keys

All keys listed below can be modified at runtime. Values are validated before write.

| Key | Type | Default | Min | Max | Purpose |
|-----|------|---------|-----|-----|---------|
| `SPIDER_CONCURRENCY` | int | 5 | 1 | 20 | Max parallel HTTP fetches in spider |
| `EXTERNAL_TIMEOUT_SECS` | int | 30 | 5 | 120 | Timeout for external HTTP requests |
| `MAX_CHARS_HARD_CAP` | int | 200000 | 1000 | 2000000 | Max characters per response |
| `MAX_SPIDER_URLS` | int | 100 | 1 | 500 | Max URLs per spider call |
| `CACHE_TTL_DAYS` | int | 30 | 1 | 365 | Cache time-to-live in days |
| `DEFAULT_SEARCH_PROVIDER` | str | "exa" | — | — | Default search provider (exa, tavily, firecrawl, brave) |
| `DEFAULT_ACCEPT_LANGUAGE` | str | "en-US,en;q=0.9,ar;q=0.8" | — | — | Accept-Language header for fetches |
| `LOG_LEVEL` | str | "INFO" | — | — | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LLM_PROVIDER_CASCADE` | str | "nvidia,openai" | — | — | Comma-separated list of LLM providers to try in order |
| `LLM_DAILY_COST_CAP_USD` | float | 10.0 | 0.0 | 1000.0 | Max daily spend on LLM calls (soft limit) |
| `SESSION_TTL_MINUTES` | int | 480 | 1 | 10080 | Session idle timeout in minutes |

For the complete, up-to-date list with descriptions, see `docs/tools/research_config.md`.

## Usage Examples

### Get All Configuration

```python
config = research_config_get()
# Returns dict like:
# {
#     "SPIDER_CONCURRENCY": 5,
#     "EXTERNAL_TIMEOUT_SECS": 30,
#     "MAX_CHARS_HARD_CAP": 200000,
#     "CACHE_TTL_DAYS": 30,
#     ...
# }

for key, value in config.items():
    print(f"{key}: {value}")
```

### Get a Single Key

```python
result = research_config_get("SPIDER_CONCURRENCY")
# Returns:
# {
#     "key": "SPIDER_CONCURRENCY",
#     "value": 5,
#     "type": "int",
#     "min": 1,
#     "max": 20,
#     "allowed_values": None
# }

print(f"Current concurrency: {result['value']}")
print(f"Range: {result['min']} - {result['max']}")
```

### Set a Value

```python
result = research_config_set("SPIDER_CONCURRENCY", 10)
# Returns:
# {
#     "key": "SPIDER_CONCURRENCY",
#     "old_value": 5,
#     "new_value": 10,
#     "persisted_at": "2025-04-11T10:30:45.123456Z",
#     "message": "Config updated and persisted"
# }

print(f"Updated from {result['old_value']} to {result['new_value']}")
```

### Invalid Value (Validation Error)

```python
result = research_config_set("SPIDER_CONCURRENCY", 100)
# Returns:
# {
#     "error": "Validation error",
#     "message": "SPIDER_CONCURRENCY must be between 1 and 20; got 100"
# }
```

## Use Cases

### Scale Up for a Bulk Research Task

Before running a large batch of research tasks:

```python
# Increase concurrency for faster fetching
research_config_set("SPIDER_CONCURRENCY", 15)
research_config_set("EXTERNAL_TIMEOUT_SECS", 60)  # Longer timeout for heavy sites

# Run your research tasks...

# Reset to defaults when done
research_config_set("SPIDER_CONCURRENCY", 5)
research_config_set("EXTERNAL_TIMEOUT_SECS", 30)
```

### Switch Search Providers

```python
# Try Tavily instead of Exa
research_config_set("DEFAULT_SEARCH_PROVIDER", "tavily")

# Perform your search...
results = research_search(query="...", provider_override=None)  # Uses DEFAULT_SEARCH_PROVIDER

# Switch back
research_config_set("DEFAULT_SEARCH_PROVIDER", "exa")
```

### Tighten Cost Controls

If you're concerned about LLM spend:

```python
# Set daily cap to $5
research_config_set("LLM_DAILY_COST_CAP_USD", 5.0)

# All LLM calls will track against this cap
# (Note: this is advisory; Loom logs warnings but doesn't strictly enforce)
```

### Enable Debug Logging

```python
research_config_set("LOG_LEVEL", "DEBUG")

# Now Loom logs verbose output to help diagnose issues

# Reset when done
research_config_set("LOG_LEVEL", "INFO")
```

### Clean Up Cache

```python
# Reduce cache TTL to clean up old entries faster
research_config_set("CACHE_TTL_DAYS", 7)

# Loom will start evicting cache entries older than 7 days on startup
```

## Config File Format

The `config.json` file is plain JSON:

```json
{
  "SPIDER_CONCURRENCY": 5,
  "EXTERNAL_TIMEOUT_SECS": 30,
  "MAX_CHARS_HARD_CAP": 200000,
  "CACHE_TTL_DAYS": 30,
  "DEFAULT_SEARCH_PROVIDER": "exa",
  "DEFAULT_ACCEPT_LANGUAGE": "en-US,en;q=0.9,ar;q=0.8",
  "LOG_LEVEL": "INFO",
  "LLM_PROVIDER_CASCADE": "nvidia,openai",
  "LLM_DAILY_COST_CAP_USD": 10.0,
  "SESSION_TTL_MINUTES": 480
}
```

You can edit it manually if needed, but use the MCP tools for safety (validation + atomic writes).

## Environment Variables

Configuration can also be set via environment variables, which take precedence over `config.json`:

```bash
export SPIDER_CONCURRENCY=10
export LOG_LEVEL=DEBUG
export LLM_DAILY_COST_CAP_USD=5.0

python -m loom.server
```

Environment variables are **not persisted**; they only apply to the current process.

## Defaults

If a key is missing from `config.json` or environment, Loom uses built-in defaults from `loom.config.ConfigModel`. These are defined in the source code and cannot be modified without code changes.

## Persistence

Configuration changes are written to disk and persist across server restarts. However:

- If you delete `config.json`, Loom uses all built-in defaults
- If you pass an environment variable, it overrides both `config.json` and built-in defaults
- Once set via `research_config_set`, the value is **permanently** in `config.json` until you change it again or delete the file

## Concurrency

Multiple concurrent calls to `research_config_set` are safe due to atomic writes. The last write wins.

## Validation

All values are validated by Pydantic before write:

- **Type checks:** Value must match the declared type (int, str, float, etc.)
- **Range checks:** Numeric values must be within min/max bounds
- **Enum checks:** String values must be in the allowed list (if defined)
- **Custom validators:** Some fields have special logic (e.g., `LLM_PROVIDER_CASCADE` must be a comma-separated list of known providers)

If validation fails, `research_config_set` returns an error and **does not** update `config.json`.

## Related Documentation

- [docs/tools/research_config.md](../tools/research_config.md) — Tool reference (research_config_get, research_config_set)
- [deploy/.env.example](../../deploy/.env.example) — Environment variable template
