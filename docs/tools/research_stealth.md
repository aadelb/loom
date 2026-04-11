# research_stealth

Browser-based stealth fetching with escalation ladder: Camoufox (Firefox) and Botasaurus (Chrome).

## Escalation ladder

The recommended pattern is:

1. **research_fetch** (Scrapling) — Fast, low overhead; works for ~80% of sites
2. **research_camoufox** — Firefox with fingerprint spoofing; escalates for anti-bot
3. **research_botasaurus** — Chrome with advanced stealth; final fallback for heavy detection

## research_camoufox

Firefox-based stealth fetcher with Camoufox fingerprint spoofing.

### Synopsis

```python
result = await session.call_tool("research_camoufox", {
    "url": "https://example.com"
})
```

### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| url | string | required | Target URL (http/https; SSRF-protected) |
| max_chars | int | 20000 | Truncate text to N chars (capped at 200k) |
| session | string | null | Reuse persistent session by name (future feature) |
| wait_for | string | null | CSS selector to wait for before extraction |
| screenshot | bool | false | Capture screenshot (stored in /tmp/) |
| extract_selector | string | null | CSS selector to extract subtree before text conversion |
| js_before_scrape | string | null | JS snippet to execute before scraping (max 2 KB) |
| timeout | int | null | Per-call timeout in seconds (capped at 120s) |

### Returns

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "text": "This domain is for use in examples and documentation...",
  "tool": "camoufox",
  "fetched_at": "2026-04-11T20:35:00.123456Z"
}
```

### Examples

```python
async with ClientSession(read, write) as s:
    # Heavy detection site
    r = await s.call_tool("research_camoufox", {
        "url": "https://cloudflare-protected-site.com",
        "wait_for": ".content",
        "timeout": 60
    })
```

## research_botasaurus

Chrome-based stealth fetcher with advanced anti-detection (final escalation).

### Synopsis

```python
result = await session.call_tool("research_botasaurus", {
    "url": "https://example.com"
})
```

### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| url | string | required | Target URL (http/https; SSRF-protected) |
| max_chars | int | 20000 | Truncate text to N chars (capped at 200k) |
| session | string | null | Reuse persistent session by name (future feature) |
| wait_for | string | null | CSS selector to wait for before extraction |
| screenshot | bool | false | Capture screenshot (stored in /tmp/) |
| extract_selector | string | null | CSS selector to extract subtree before text conversion |
| js_before_scrape | string | null | JS snippet to execute before scraping (max 2 KB) |
| timeout | int | null | Per-call timeout in seconds (capped at 120s) |

### Returns

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "text": "This domain is for use...",
  "tool": "botasaurus",
  "fetched_at": "2026-04-11T20:35:15.654321Z"
}
```

### Examples

```python
async with ClientSession(read, write) as s:
    # Maximum detection site
    r = await s.call_tool("research_botasaurus", {
        "url": "https://ultra-protected-site.com",
        "js_before_scrape": "window.scrollTo(0, document.body.scrollHeight)",
        "timeout": 90
    })
```

## Shared errors (both tools)

- `url_rejected: <reason>` — URL fails SSRF validation
- `timeout` — Request exceeded per-call timeout
- `js_before_scrape_failed: <reason>` — JS execution error (max 2 KB size)
- `selector_not_found: <reason>` — wait_for or extract_selector not found
- `<tool> not available: <reason>` — Browser not installed or library import failed
- `screenshot failed: <reason>` — Screenshot capture failed (non-fatal; continues)

## Session reuse

Both tools support session reuse via the `session` parameter (future feature; currently creates fresh browser instance each call). When implemented, will reuse profile directory and browser state across multiple requests.

## Timeout behavior

Timeouts are capped at 120 seconds per request. The underlying browser navigations use `wait_until="networkidle"` to ensure page load completion before extraction.

## Related tools

- `research_fetch` — Primary fetcher with Scrapling (start here)
- `research_markdown` — Extract clean markdown (async-native Crawl4AI)
- `research_spider` — Parallel bulk fetching with bounded concurrency
