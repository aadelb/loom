# Offline Capability Matrix

Loom provides offline-first capabilities for research and attack tools, enabling graceful degradation when external providers are unavailable. This document describes the offline mode architecture, supported tools, and fallback strategies.

## Architecture Overview

### Three-Layer Fallback Strategy

1. **Live Mode** (Online)
   - Direct calls to external providers (Scrapling, Search engines, LLMs, etc.)
   - Full freshness and completeness guaranteed
   - Primary execution path when network is available

2. **Offline Fallback** (Provider Down)
   - Automatic cache retrieval on provider failure
   - Stale data indicators included with response
   - Allows consumer to make informed decisions
   - Graceful error handling for cache misses

3. **Offline-First Mode** (Network Down)
   - Pre-configured mode for offline environments
   - Exclusively serves cached data
   - Returns structured errors when cache unavailable
   - Suitable for air-gapped research scenarios

### Cache System

The cache infrastructure supports offline mode:

- **Storage**: Content-hash based (SHA-256), daily directory structure
- **Format**: Gzip-compressed JSON (.json.gz) with fallback to legacy .json
- **Freshness**: ISO 8601 timestamps, 24-hour staleness threshold
- **Capacity**: Configurable via `LOOM_CACHE_DIR`, typically ~/.cache/loom
- **Compression**: ~60% space savings with gzip level 6
- **Atomicity**: UUID-suffixed temp files + os.replace for crash safety

## Tool Offline Support Matrix

### Tier 1: Full Offline Support (Cached)

These tools support offline mode natively via the cache system:

| Tool | Offline Mode | Notes |
|------|--------------|-------|
| `research_fetch` | ✓ | Caches fetched content; serves stale on provider failure |
| `research_spider` | ✓ | Multi-URL fetches cached individually |
| `research_markdown` | ✓ | HTML-to-markdown conversion cached |
| `research_search` | ✓ | Search results cached per provider |
| `research_deep` | ✓ | Entire pipeline cached per query |
| `research_github` | ✓ | GitHub CLI results cached |
| `research_llm_*` | ✓ | LLM responses cached; fallback to previous responses |

### Tier 2: Partial Offline Support (Some Features)

| Tool | Offline Mode | Notes |
|------|--------------|-------|
| `research_session_*` | ⚠ | Sessions cache state; browser playback unavailable offline |
| `research_config_*` | ✓ | Config stored locally; no network dependency |
| `research_health_check` | ⚠ | Can report cached provider status |

### Tier 3: No Offline Support (Real-Time Only)

| Tool | Offline Mode | Notes |
|------|--------------|-------|
| `vastai_*` | ✗ | Real-time GPU pricing and availability |
| `billing_*` | ✗ | Stripe integration requires live API |
| `transcribe_*` | ✗ | Processing requires service API |
| `joplin_*` | ✗ | Local sync only; no offline processing |
| `slack_*` | ✗ | Message delivery requires live API |

## Offline Mode API

### Automatic Offline Fallback

When a tool provider fails (timeout, 5xx error, connection refused), Loom automatically attempts to serve cached data:

```python
from loom.offline import serve_stale_or_error
from loom.cache import get_cache

# When provider fails:
try:
    result = await provider.fetch(url)
except ConnectionError as e:
    # Automatic fallback
    response = serve_stale_or_error(cache_key=url, error=e)
    # Returns: {
    #   "data": <cached_content>,
    #   "cached_at": "2026-05-01T10:00:00+00:00",
    #   "freshness_hours": 24.5,
    #   "is_stale": True,
    #   "source": "cache_fallback",
    #   "original_error": "Connection timeout",
    # } OR {
    #   "data": None,
    #   "error": "provider_unavailable",
    #   "message": "Provider failed and no cache available: ...",
    #   "source": "error",
    # }
```

### Cache State Tracking

Check cache freshness with metadata:

```python
from loom.cache import get_cache

cache = get_cache()

# Retrieve with staleness indicators
cached = cache.get_with_metadata("research_fetch::url_key")
if cached:
    if cached["is_stale"]:
        print(f"Stale: {cached['freshness_hours']} hours old")
        print(f"Cached at: {cached['cached_at']}")
    else:
        print("Fresh data available")
else:
    print("No cached data")
```

### Direct Offline Mode

For air-gapped scenarios, enable offline mode globally:

```python
from loom.offline import serve_stale_or_error
from loom.cache import get_cache

# Fetch from cache only
cache = get_cache()
data = cache.get("your_cache_key")

if data:
    print("Using cached data (offline)")
else:
    print("No cached data available")
```

## Storage Tiers and Retention

Loom uses a 3-tier storage system optimized for cost and access speed:

### Hot Tier (≤ 30 days)
- **Storage**: SSD/instant access (prod database)
- **Use case**: Active research sessions
- **Example**: Today's fetches, current search results

### Warm Tier (31-365 days)
- **Storage**: HDD/slower access (archive)
- **Use case**: Reference data, completed research
- **Example**: Archived search results, historical intel

### Cold Tier (> 365 days)
- **Storage**: Archive/compressed
- **Use case**: Long-term retention, compliance
- **Example**: Year-old datasets, audit trails

Monitor tier distribution:

```python
from loom.storage import get_tier_breakdown
from pathlib import Path

breakdown = get_tier_breakdown(Path.home() / ".cache/loom")
# Returns: {
#   "hot": {"count": 125, "size_bytes": ..., "size_mb": 1.5},
#   "warm": {"count": 45, "size_bytes": ..., "size_mb": 0.8},
#   "cold": {"count": 10, "size_bytes": ..., "size_mb": 0.3},
# }
```

## Storage Dashboard and Alerts

Monitor cache usage with the storage dashboard:

```python
from loom.storage import get_storage_dashboard
from pathlib import Path

dashboard = get_storage_dashboard(Path.home() / ".cache/loom", max_size_gb=50.0)

# dashboard["stats"]: aggregate usage
print(f"Total: {dashboard['stats']['total_size_mb']} MB")

# dashboard["tiers"]: per-tier breakdown
for tier, stats in dashboard["tiers"].items():
    print(f"{tier}: {stats['size_mb']} MB ({stats['count']} files)")

# dashboard["alerts"]: threshold warnings
for alert in dashboard["alerts"]:
    print(f"{alert['level']}: {alert['message']}")
```

Alert levels:
- **info**: 50-80% of max capacity
- **warning**: 80-90% of max capacity
- **critical**: ≥ 90% of max capacity

## Offline Workflows

### Scenario 1: Provider Temporarily Down

```
User requests research_fetch(url)
  ↓
Provider API fails (5xx error)
  ↓
serve_stale_or_error() called
  ↓
Cache hit with metadata
  ↓
Return: {"data": <cached>, "is_stale": True, "freshness_hours": 48.2}
  ↓
User sees data + warning: "Data from 2 days ago"
```

### Scenario 2: Air-Gapped Research

```
Configure: {"LOOM_OFFLINE_MODE": "enabled"}
  ↓
User imports research tools
  ↓
All tool calls check cache first
  ↓
On cache hit: serve immediately
  ↓
On cache miss: return structured error
  ↓
No network calls attempted
```

### Scenario 3: Scheduled Bulk Offline Research

```
1. Live session: Fetch 100 URLs, cache all
2. Schedule daily refresh: update hot tier
3. Offline session: Serve 100 cached results
4. Compare live vs offline: detect changes
5. Archive to cold tier after 1 year
```

## Configuration

### Environment Variables

```bash
# Cache directory
export LOOM_CACHE_DIR=~/.cache/loom

# Offline mode (optional)
export LOOM_OFFLINE_MODE=disabled  # or "enabled" for air-gapped
```

### Config File (config.json)

```json
{
  "cache": {
    "max_size_gb": 50.0,
    "ttl_days": 30,
    "compression": "gzip"
  },
  "offline": {
    "enabled": false,
    "fallback_on_error": true,
    "stale_threshold_hours": 24
  }
}
```

## Best Practices

### 1. Check Staleness in UI/Logs
Always inspect the `is_stale` flag when serving cached data:

```python
if response.get("is_stale"):
    logger.warning(f"Stale data ({response['freshness_hours']}h old)")
```

### 2. Monitor Cache Growth
Run storage dashboard periodically:

```bash
loom research-cache-stats  # Get stats
loom research-cache-clear --older-than 30  # Cleanup
```

### 3. Tier Data Strategically
- Hot: active research projects
- Warm: completed projects, reference data
- Cold: compliance archives

### 4. Test Offline Scenarios
Before deploying to air-gapped environment:

```python
# Simulate offline
from unittest.mock import patch
with patch("requests.get", side_effect=ConnectionError):
    result = await tool.fetch(url)
    assert result["is_stale"] or result["error"]
```

## Limitations

| Scenario | Supported | Notes |
|----------|-----------|-------|
| Offline without cache | ✗ | No data available; returns error |
| Cross-origin requests offline | ✗ | Cache keyed per URL; no aggregation |
| Real-time data offline | ✗ | Stock prices, traffic data, etc. |
| Interactive sessions offline | ⚠ | Playback from logs only |
| LLM provider changes offline | ✗ | Cached responses keyed per model |

## Troubleshooting

### Cache Hit Not Working

1. Check cache directory exists:
   ```bash
   ls ~/.cache/loom/
   ```

2. Verify cache key matches:
   ```python
   from loom.cache import get_cache
   cache = get_cache()
   print(cache.stats())
   ```

3. Check file permissions:
   ```bash
   ls -la ~/.cache/loom/
   ```

### Stale Data Warnings

If seeing `"freshness_hours": 48.2` warnings:

1. Intentional: Use for reference data
2. Unexpected: Consider re-fetching live:
   ```bash
   loom research-fetch --refresh-cache URL
   ```

### Storage Growing Too Large

1. Identify largest files:
   ```python
   from loom.storage import get_storage_stats
   stats = get_storage_stats(Path.home() / ".cache/loom")
   print(stats["by_extension"])  # GB per file type
   ```

2. Clean old entries:
   ```python
   from loom.cache import get_cache
   cache = get_cache()
   removed = cache.clear_older_than(days=30)
   print(f"Removed {removed} files")
   ```

## See Also

- [Architecture Guide](./architecture.md) - System design and pipelines
- [Tools Reference](./tools-reference.md) - Complete tool capabilities
- [Help & Troubleshooting](./help.md) - Common issues and solutions
