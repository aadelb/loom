# research_markdown

Crawl4AI async markdown extractor for LLM-ready content with CSS selection and JS execution.

## Synopsis

```python
result = await session.call_tool("research_markdown", {
    "url": "https://example.com",
    "bypass_cache": False
})
```

## Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| url | string | required | Target URL (http/https; SSRF-protected) |
| bypass_cache | bool | false | Force refetch even if cached |
| css_selector | string | null | Extract only this CSS subtree before markdown conversion |
| js_before_scrape | string | null | Small JS snippet to execute before scraping (max 2 KB) |
| screenshot | bool | false | Capture screenshot and store in cache/screenshots/ |
| remove_selectors | array | null | List of CSS selectors to remove before extraction (e.g., `["script", "style"]`) |
| headers | dict | null | Custom HTTP headers |
| user_agent | string | null | Override User-Agent |
| proxy | string | null | HTTP proxy URL |
| cookies | dict | null | Cookies dict |
| accept_language | string | en-US,en;q=0.9,ar;q=0.8 | Accept-Language header value |
| timeout | int | null | Per-call timeout in seconds (1-120, capped at EXTERNAL_TIMEOUT_SECS=30) |
| extract_selector | string | null | Alias for css_selector (if both provided, css_selector takes precedence) |
| wait_for | string | null | CSS selector to wait for before scraping |

## Returns

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "markdown": "# Example Domain\n\nThis domain is for use in examples and documentation.\n\n...",
  "tool": "crawl4ai",
  "fetched_at": "2026-04-11T20:32:10.654321Z"
}
```

On error:

```json
{
  "url": "https://example.com",
  "error": "js_before_scrape failed: syntax error",
  "tool": "crawl4ai"
}
```

## Errors

- `url_rejected: <reason>` — URL fails SSRF validation
- `timeout` — Request exceeded per-call timeout
- `js_before_scrape_failed: <reason>` — JS execution error (max 2 KB size limit)
- `selector_not_found: <reason>` — css_selector or wait_for selector not found in DOM
- `cache_error: <reason>` — Cache read/write failed

## Examples

### Basic markdown extraction

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_markdown", {
        "url": "https://en.wikipedia.org/wiki/Python",
        "bypass_cache": False
    })
    print(r["markdown"][:1000])
```

### Extract main content area with selector and remove script/style

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_markdown", {
        "url": "https://news.ycombinator.com",
        "css_selector": ".hnmain",
        "remove_selectors": ["script", "style", ".votearrow"],
        "wait_for": ".titleline"
    })
```

### Execute JS before scraping (e.g., expand collapsed sections)

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_markdown", {
        "url": "https://example.com/docs",
        "js_before_scrape": "document.querySelectorAll('[aria-expanded=false]').forEach(el => el.click())",
        "timeout": 45
    })
```

### Capture screenshot with markdown

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_markdown", {
        "url": "https://example.com",
        "screenshot": true,
        "headers": {"X-Custom": "value"}
    })
```

## Related tools

- `research_fetch` — Raw HTML/text fetcher with multiple rendering modes
- `research_spider` — Parallel markdown extraction from multiple URLs (uses research_fetch under hood)
- `research_deep` — Search + fetch + markdown in one pipeline
