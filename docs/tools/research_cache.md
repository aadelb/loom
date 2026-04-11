# research_cache

Cache management tools for statistics and cleanup.

## Cache overview

Loom maintains a content-hash cache for all fetch operations. Cache layout:

```
LOOM_CACHE_DIR/
├── YYYY-MM-DD/
│   ├── <sha256-hash-1>.json
│   ├── <sha256-hash-2>.json
│   └── ...
├── YYYY-MM-DD/
│   └── ...
└── screenshots/
    └── <screenshot-files>
```

- **Hash**: SHA256 of URL + content (content-addressable)
- **Atomic writes**: UUID tmp file → `os.replace()` → final location
- **TTL cleanup**: Automated daily cron pattern removes files older than CACHE_TTL_DAYS

## research_cache_stats

Get cache statistics.

### Synopsis

```python
result = await session.call_tool("research_cache_stats", {})
```

### Parameters

None.

### Returns

```json
{
  "file_count": 347,
  "total_bytes": 52847293,
  "days_present": ["2026-04-11", "2026-04-10", "2026-04-09", "2026-04-08"],
  "fetched_at": "2026-04-11T20:39:00.123456Z"
}
```

On error:

```json
{
  "file_count": 0,
  "total_bytes": 0,
  "days_present": [],
  "error": "failed to read cache directory"
}
```

## research_cache_clear

Delete cache files older than N days.

### Synopsis

```python
result = await session.call_tool("research_cache_clear", {
    "older_than_days": 30
})
```

### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| older_than_days | int | 30 | Delete files modified before this many days ago (0 = clear all) |

### Returns

```json
{
  "removed": 145,
  "cleaned_at": "2026-04-11T20:39:15.654321Z"
}
```

On error:

```json
{
  "removed": 0,
  "cleaned_at": "2026-04-11T20:39:15.654321Z",
  "error": "failed to delete cache files: permission denied"
}
```

## Examples

### Check cache size

```python
async with ClientSession(read, write) as s:
    stats = await s.call_tool("research_cache_stats", {})
    size_mb = stats["total_bytes"] / (1024 * 1024)
    print(f"Cache: {stats['file_count']} files, {size_mb:.1f} MB")
    print(f"Days: {', '.join(stats['days_present'][:7])}")
```

### Clean up old cache files

```python
async with ClientSession(read, write) as s:
    # Remove files older than 60 days
    result = await s.call_tool("research_cache_clear", {
        "older_than_days": 60
    })
    print(f"Cleaned up {result['removed']} files")
```

### Aggressive cleanup (keep only today's cache)

```python
async with ClientSession(read, write) as s:
    result = await s.call_tool("research_cache_clear", {
        "older_than_days": 1
    })
    print(f"Removed {result['removed']} files (kept today only)")
```

### Clear entire cache

```python
async with ClientSession(read, write) as s:
    result = await s.call_tool("research_cache_clear", {
        "older_than_days": 0  # Everything
    })
    print(f"Cleared {result['removed']} files")
```

## Cache behavior

- **Cache hit**: Identical URL fetched before → returns cached content
- **bypass_cache=true**: Ignores cache, always fetches fresh
- **Cache key**: SHA256(url + body), not just URL (handles redirects, content changes)
- **Daily layout**: Automatic segregation by fetch date aids cleanup
- **Screenshot storage**: Separate `screenshots/` directory for image files
- **Atomic writes**: All cache writes use UUID tmp + `os.replace()` for atomicity

## Configuration

Related config keys:

- **CACHE_TTL_DAYS** (default 30): Auto-cleanup removes files older than this
- **LOOM_CACHE_DIR** (env var): Override default cache location (~/.cache/loom/fetch)

## Related tools

- `research_config_get/set` — Adjust CACHE_TTL_DAYS without restart
- `research_fetch` — Uses cache (unless bypass_cache=true)
- `research_spider` — Uses cache for each URL
- `research_markdown` — Uses cache for extracted content
