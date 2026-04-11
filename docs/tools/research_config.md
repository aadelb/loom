# research_config

Runtime configuration management with atomic persistence and validation.

## Configuration overview

Loom stores runtime config in `LOOM_CONFIG_PATH` (default `~/.config/loom/config.json`). All configuration keys are mutable at runtime without server restart. Changes are atomically persisted using tmp + `os.replace()`.

## research_config_get

Retrieve config value(s).

### Synopsis

```python
result = await session.call_tool("research_config_get", {})  # Get all
result = await session.call_tool("research_config_get", {"key": "SPIDER_CONCURRENCY"})  # Get one
```

### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| key | string | null | Config key to retrieve (if null, returns entire config) |

### Returns

Single key:

```json
{
  "key": "SPIDER_CONCURRENCY",
  "value": 5
}
```

All keys:

```json
{
  "SPIDER_CONCURRENCY": 5,
  "EXTERNAL_TIMEOUT_SECS": 30,
  "MAX_CHARS_HARD_CAP": 200000,
  "MAX_SPIDER_URLS": 100,
  "CACHE_TTL_DAYS": 30,
  "DEFAULT_SEARCH_PROVIDER": "exa",
  "DEFAULT_ACCEPT_LANGUAGE": "en-US,en;q=0.9,ar;q=0.8",
  "LOG_LEVEL": "INFO",
  "LLM_DEFAULT_CHAT_MODEL": "gpt-4-turbo",
  "LLM_DEFAULT_EMBED_MODEL": "text-embedding-3-small",
  "LLM_DEFAULT_TRANSLATE_MODEL": "gpt-4-turbo",
  "LLM_MAX_PARALLEL": 12,
  "LLM_DAILY_COST_CAP_USD": 10.0,
  "LLM_CASCADE_ORDER": ["nvidia", "openai", "anthropic", "vllm"]
}
```

## research_config_set

Set a config value with validation and persistence.

### Synopsis

```python
result = await session.call_tool("research_config_set", {
    "key": "SPIDER_CONCURRENCY",
    "value": 10
})
```

### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| key | string | required | Config key to set (case-sensitive) |
| value | any | required | New value (validated against key's type and bounds) |

### Returns

```json
{
  "key": "SPIDER_CONCURRENCY",
  "old": 5,
  "new": 10,
  "persisted_at": "2026-04-11T20:38:00.123456Z"
}
```

On error:

```json
{
  "error": "invalid value for SPIDER_CONCURRENCY: value must be 1-20"
}
```

## Configuration keys

All keys with their bounds and defaults:

| Key | Type | Min | Max | Default | Purpose |
|---|---|---|---|---|---|
| SPIDER_CONCURRENCY | int | 1 | 20 | 5 | Max parallel spider fetches |
| EXTERNAL_TIMEOUT_SECS | int | 5 | 120 | 30 | Timeout for external HTTP calls |
| MAX_CHARS_HARD_CAP | int | 1000 | 2000000 | 200000 | Max chars per response |
| MAX_SPIDER_URLS | int | 1 | 500 | 100 | Max URLs per spider call |
| CACHE_TTL_DAYS | int | 1 | 365 | 30 | Cache time-to-live in days |
| DEFAULT_SEARCH_PROVIDER | enum | - | - | exa | Preferred search provider (exa\|tavily\|firecrawl\|brave) |
| DEFAULT_ACCEPT_LANGUAGE | string | - | - | en-US,en;q=0.9,ar;q=0.8 | Default Accept-Language header |
| LOG_LEVEL | enum | - | - | INFO | Logging level (DEBUG\|INFO\|WARNING\|ERROR\|CRITICAL) |
| LLM_DEFAULT_CHAT_MODEL | string | - | - | gpt-4-turbo | Default LLM chat model |
| LLM_DEFAULT_EMBED_MODEL | string | - | - | text-embedding-3-small | Default embedding model |
| LLM_DEFAULT_TRANSLATE_MODEL | string | - | - | gpt-4-turbo | Default translation model |
| LLM_MAX_PARALLEL | int | 1 | 64 | 12 | Max parallel LLM calls |
| LLM_DAILY_COST_CAP_USD | float | 0.0 | 1000.0 | 10.0 | Daily LLM cost cap in USD |
| LLM_CASCADE_ORDER | list | - | - | ["nvidia", "openai", "anthropic", "vllm"] | Order to try LLM providers |

## Examples

### Increase spider concurrency for high-throughput crawling

```python
async with ClientSession(read, write) as s:
    result = await s.call_tool("research_config_set", {
        "key": "SPIDER_CONCURRENCY",
        "value": 15
    })
    print(f"Changed from {result['old']} to {result['new']}")
```

### Reduce timeout for fast-fail scenarios

```python
async with ClientSession(read, write) as s:
    await s.call_tool("research_config_set", {
        "key": "EXTERNAL_TIMEOUT_SECS",
        "value": 10
    })
```

### Increase cache TTL to reduce external API hits

```python
async with ClientSession(read, write) as s:
    await s.call_tool("research_config_set", {
        "key": "CACHE_TTL_DAYS",
        "value": 90
    })
```

### Switch default search provider

```python
async with ClientSession(read, write) as s:
    await s.call_tool("research_config_set", {
        "key": "DEFAULT_SEARCH_PROVIDER",
        "value": "tavily"
    })
```

### Set LLM cascade order (for multi-provider fallback)

```python
async with ClientSession(read, write) as s:
    await s.call_tool("research_config_set", {
        "key": "LLM_CASCADE_ORDER",
        "value": ["anthropic", "openai", "nvidia"]
    })
```

### Set daily LLM cost cap

```python
async with ClientSession(read, write) as s:
    await s.call_tool("research_config_set", {
        "key": "LLM_DAILY_COST_CAP_USD",
        "value": 25.0
    })
```

## Errors

- `invalid value for <key>: <reason>` — Value fails validation (type mismatch, out of bounds, etc.)
- `config validation failed: <reason>` — Config state is corrupted
- `file i/o error: <reason>` — Failed to read/write config.json

## Persistence

All config changes are:

1. Validated against Pydantic ConfigModel
2. Updated in-memory (CONFIG dict)
3. Atomically written to `config.json` (tmp + replace)
4. Immediately effective without server restart

## Related tools

- `research_cache_stats` — View cache usage
- `research_cache_clear` — Clean up old cache files
