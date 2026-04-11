# research_spider

Parallel bulk URL fetcher with bounded concurrency, deduplication, and flexible result ordering.

## Synopsis

```python
result = await session.call_tool("research_spider", {
    "urls": ["https://example.com", "https://google.com"],
    "concurrency": 3
})
```

## Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| urls | array | required | List of URLs to fetch (max 100 by default, configurable MAX_SPIDER_URLS) |
| mode | string | stealthy | Render mode passed to each fetch: `http` \| `stealthy` \| `dynamic` |
| max_chars_each | int | 5000 | Truncate each response to N chars (capped at 200k) |
| concurrency | int | 5 | Max concurrent fetches (1-20; clamped by SPIDER_CONCURRENCY config) |
| fail_fast | bool | false | Stop on first error; if false, continue and include error in results |
| dedupe | bool | true | Drop duplicate URLs before fetching |
| order | string | input | Result ordering: `input` (original order) \| `domain` (alphabetical) \| `size` (by response size) |
| solve_cloudflare | bool | true | Auto-solve challenges on each fetch (dynamic mode) |
| headers | dict | null | Custom headers passed to each fetch |
| user_agent | string | null | Override User-Agent on each fetch |
| proxy | string | null | Proxy URL passed to each fetch |
| cookies | dict | null | Cookies passed to each fetch |
| accept_language | string | en-US,en;q=0.9,ar;q=0.8 | Accept-Language header for each fetch |
| timeout | int | null | Per-fetch timeout override (1-120 seconds, capped at EXTERNAL_TIMEOUT_SECS=30) |

## Returns

```json
[
  {
    "url": "https://example.com",
    "title": "Example Domain",
    "text": "This domain is for use...",
    "html_len": 1256,
    "fetched_at": "2026-04-11T20:31:00.123456Z",
    "tool": "scrapling.stealthy"
  },
  {
    "url": "https://google.com",
    "title": "Google",
    "text": "Search the world's information...",
    "html_len": 18234,
    "fetched_at": "2026-04-11T20:31:02.456789Z",
    "tool": "scrapling.stealthy"
  },
  {
    "url": "https://blocked.example.com",
    "error": "timeout exceeded",
    "tool": "scrapling.stealthy"
  }
]
```

## Errors

- `urls list is empty` — After deduplication and filtering, no URLs remain
- `url_rejected: <reason>` — URL fails SSRF validation (private IP, wrong scheme, etc.)
- `timeout` — Individual fetch exceeded per-fetch timeout
- `concurrency_invalid: <reason>` — Concurrency outside 1-20 range
- `max_spider_urls_exceeded` — More than MAX_SPIDER_URLS URLs provided

## Examples

### Fetch multiple URLs with 3 concurrent workers

```python
async with ClientSession(read, write) as s:
    results = await s.call_tool("research_spider", {
        "urls": [
            "https://example.com",
            "https://google.com",
            "https://github.com"
        ],
        "concurrency": 3,
        "mode": "stealthy"
    })
    for r in results:
        if "error" not in r:
            print(f"{r['url']}: {len(r['text'])} chars")
```

### Dynamic rendering with custom headers and ordered by size

```python
async with ClientSession(read, write) as s:
    results = await s.call_tool("research_spider", {
        "urls": ["https://site1.com", "https://site2.com"],
        "mode": "dynamic",
        "headers": {"X-Custom": "value"},
        "order": "size",
        "dedupe": true
    })
```

### Fail fast on first error with custom timeout

```python
async with ClientSession(read, write) as s:
    results = await s.call_tool("research_spider", {
        "urls": ["https://a.com", "https://b.com", "https://c.com"],
        "fail_fast": true,
        "timeout": 20,
        "concurrency": 2
    })
```

## Related tools

- `research_fetch` — Single URL fetcher (underlying implementation for each spider fetch)
- `research_markdown` — Extract clean markdown from URL(s)
- `research_deep` — Search + multi-fetch + markdown in one pipeline
