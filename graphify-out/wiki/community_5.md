# Community 5: Data Processing & Utilities

**Modules:** `tools/markdown.py`, `tools/cache_mgmt.py`, `cache.py`, `validators.py`

## Purpose

This community handles data transformation, caching, and input validation—the utilities that enable efficient, safe research operations across all tools.

## Key Classes & Functions

### `tools/markdown.py`
- `research_markdown(html, **kwargs)` — Convert HTML to clean Markdown for LLM consumption
- `tool_markdown(html, **kwargs)` — CLI/MCP wrapper
- Uses html2text, BeautifulSoup, or Crawl4AI depending on complexity
- Optional LLM post-processing for readability

### `tools/cache_mgmt.py`
- `research_cache_stats()` — Aggregate cache statistics (entries, total size, oldest/newest)
- `research_cache_clear(pattern, **kwargs)` — Clear cache entries by age, pattern, or type
- `tool_cache_stats()`, `tool_cache_clear()` — CLI/MCP wrappers
- Per-tool cache inspection (fetch cache, search cache, spider cache, etc.)

### `cache.py`
- **`CacheStore`** — Persistent cache backend (SQLite or file-based)
  - Methods: `get(key)`, `set(key, value, ttl)`, `delete(key)`, `evict(max_age)`
  - Automatic expiration, compression (optional), size quotas
- Shared across all tools via `config.cache_dir`

### `validators.py`
- **`UrlSafetyError`** — Exception for unsafe URLs
- `validate_url(url)` — URL schema validation, domain whitelist/blacklist checks
- `cap_chars(text, max_len)` — Truncate long text for prompts/displays

## Data Flow

1. Research tool (fetch, search, spider) executes
2. Before making HTTP request, `validate_url()` checks against safety rules
3. Result stored in `CacheStore` with TTL (typically 7–30 days)
4. If HTML result, optionally convert to Markdown via `research_markdown()`
5. User can query cache stats via `research_cache_stats()`
6. User can evict stale entries via `research_cache_clear()`

## Dependencies

- **Inbound:** All tools (fetch, search, spider, deep), CLI cache management commands
- **Outbound:** → SQLite (cache backend), → html2text/BeautifulSoup (markdown conversion)
- **Key edges:** ← all tools, ← server.py (tool registration), ← config.py (cache_dir, cache_ttl settings)

## Module Paths

- `src/loom/tools/markdown.py` (100 LOC)
- `src/loom/tools/cache_mgmt.py` (80 LOC)
- `src/loom/cache.py` (150 LOC)
- `src/loom/validators.py` (60 LOC)
