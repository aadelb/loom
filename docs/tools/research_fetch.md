# research_fetch

Scrapling 3-tier adaptive fetcher with URL validation, caching, and multiple rendering modes.

## Synopsis

```python
result = await session.call_tool("research_fetch", {
    "url": "https://example.com",
    "mode": "stealthy"
})
```

## Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| url | string | required | Target URL (http/https only; private IPs blocked by SSRF guard) |
| mode | string | stealthy | Render mode: `http` (TLS spoof only) \| `stealthy` (anti-bot) \| `dynamic` (full JS) |
| solve_cloudflare | bool | true | Auto-solve Turnstile/hCaptcha in dynamic mode |
| bypass_cache | bool | false | Force refetch even if cached |
| max_chars | int | 20000 | Truncate text output to N chars (capped at 200k) |
| headers | dict | null | Custom HTTP headers; Host, Content-Length, Cookie blocked |
| user_agent | string | null | Override User-Agent (max 256 chars) |
| proxy | string | null | HTTP proxy: `http://[user:pass@]host:port` |
| cookies | dict | null | Cookie dict: `{"name": "value", ...}` |
| basic_auth | tuple | null | Basic auth tuple: `["username", "password"]` |
| retries | int | 0 | Max retries on failure (0-3, exponential backoff) |
| timeout | int | null | Per-call timeout in seconds (1-120, capped by EXTERNAL_TIMEOUT_SECS=30) |
| wait_for | string | null | CSS selector to wait for before extracting (dynamic mode only) |
| accept_language | string | en-US,en;q=0.9,ar;q=0.8 | Accept-Language header value |
| session | string | null | Reuse persistent session by name (future feature) |
| return_format | string | text | Response format: `text` \| `html` \| `json` \| `screenshot` |
| extract_selector | string | null | CSS selector to extract subtree before text conversion |

## Returns

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "text": "This domain is for use in examples and documentation...",
  "html_len": 1256,
  "fetched_at": "2026-04-11T20:30:45.123456Z",
  "tool": "scrapling.stealthy"
}
```

On error:

```json
{
  "url": "https://example.com",
  "error": "timeout exceeded",
  "tool": "scrapling.stealthy"
}
```

## Errors

- `url_rejected: <reason>` — URL is invalid, wrong scheme, or resolves to blocked IP (private, loopback, link-local, multicast, reserved, unspecified)
- `timeout` — Request exceeded per-call timeout
- `proxy_error: <reason>` — Proxy connection failed
- `js_error: <reason>` — JS execution failed (dynamic mode)
- `cache_error: <reason>` — Cache read/write failed
- `cloudflare_solve_failed` — Turnstile solving failed (dynamic mode with solve_cloudflare=true)

## Examples

### Basic HTTP fetch with TLS spoofing

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_fetch", {
        "url": "https://example.com",
        "mode": "http"
    })
    print(r["text"][:500])
```

### Dynamic rendering with wait-for and extraction

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_fetch", {
        "url": "https://news.ycombinator.com",
        "mode": "dynamic",
        "wait_for": ".titleline",
        "extract_selector": ".titleline",
        "max_chars": 5000
    })
```

### Custom headers and basic auth

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_fetch", {
        "url": "https://api.example.com/protected",
        "mode": "stealthy",
        "headers": {"X-Custom": "value"},
        "basic_auth": ["user", "pass"],
        "timeout": 15
    })
```

### Via CLI

```bash
loom fetch "https://example.com" --mode dynamic --timeout 45
```

## Related tools

- `research_spider` — Fetch multiple URLs in parallel with bounded concurrency
- `research_markdown` — Extract clean LLM-ready markdown using Crawl4AI (async)
- `research_camoufox` — Firefox-based stealth escalation when Scrapling is blocked
- `research_botasaurus` — Chrome-based stealth escalation as final fallback
