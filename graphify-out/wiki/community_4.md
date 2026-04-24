# Community 4: Web Research Tools

**Modules:** `tools/fetch.py`, `tools/search.py`, `tools/spider.py`, `tools/deep.py`, `tools/github.py`, `tools/stealth.py`

## Purpose

This community implements the core research operations—fetching single URLs, conducting semantic searches, multi-URL crawling, and advanced operations like GitHub querying and stealthy Camoufox browser sessions.

## Key Classes & Functions

### `tools/fetch.py`
- **`FetchResult`** — Structured HTTP response (content, status, headers, URL, timestamp)
- `research_fetch(url, **kwargs)` — Single-URL fetch with optional caching, timeout, stealth headers
- `tool_fetch(url, **kwargs)` — CLI/MCP wrapper

### `tools/search.py`
- `research_search(query, limit, backend, **kwargs)` — Semantic search via Exa, Tavily, Brave, or Firecrawl
- `tool_search(query, limit, **kwargs)` — CLI/MCP wrapper
- Backend selection logic, result ranking, optional LLM reranking

### `tools/spider.py`
- `research_spider(seed_urls, depth, **kwargs)` — Multi-URL bulk crawl
- BFS traversal, filter patterns (include/exclude), concurrency control
- Aggregate results into JSON/CSV

### `tools/deep.py`
- `research_deep(query, **kwargs)` — Full research pipeline (search → fetch top URLs → markdown → optional LLM analysis)
- Single-shot comprehensive research operation

### `tools/github.py`
- `research_github(query, type, **kwargs)` — GitHub API search (repos, code, issues)
- `tool_github(query, type, **kwargs)` — CLI/MCP wrapper

### `tools/stealth.py`
- **`CamoufoxResult`** — Browser session result (page content, screenshots, HTML, timing)
- `research_camoufox(url, **kwargs)` — Camoufox stealth browser for anti-bot pages
- Browser fingerprinting, rotating user agents

## Data Flow

1. User initiates research via `research_fetch`, `research_search`, `research_spider`, or `research_deep`
2. Fetch tools hit URLs with optional stealth (rotating headers, Camoufox)
3. Results cached in `CacheStore` (with TTL)
4. Optional LLM post-processing (e.g., summarization, reranking)
5. Structured result returned to user
6. Journey step logged if tracking enabled

## Dependencies

- **Inbound:** User CLI/MCP commands, JourneyReport tracking
- **Outbound:** → HTTP clients (httpx, Playwright), → search backends (Exa, Tavily, Brave, Firecrawl), → providers (LLM post-processing), → cache.py
- **Key edges:** ← server.py (tool registration), ← sessions.py (browser session context for Camoufox)

## Module Paths

- `src/loom/tools/fetch.py` (120 LOC)
- `src/loom/tools/search.py` (150 LOC)
- `src/loom/tools/spider.py` (180 LOC)
- `src/loom/tools/deep.py` (100 LOC)
- `src/loom/tools/github.py` (80 LOC)
- `src/loom/tools/stealth.py` (140 LOC)
