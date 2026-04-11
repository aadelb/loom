# research_deep

One-shot deep research pipeline: search → fetch → extract markdown.

## Synopsis

```python
result = await session.call_tool("research_deep", {
    "query": "latest AI research",
    "depth": 2
})
```

## Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| query | string | required | Search query string (non-empty) |
| depth | int | 2 | Number of pages to fetch (multiplied by 5 internally for search result count; 1-10) |
| provider | string | exa | Preferred search provider: `exa` \| `tavily` \| `firecrawl` \| `brave` |
| include_domains | array | null | Only search within these domains |
| exclude_domains | array | null | Exclude these domains |
| start_date | string | null | Filter results from ISO date (yyyy-mm-dd) |
| end_date | string | null | Filter results until ISO date (yyyy-mm-dd) |
| language | string | null | Language hint (e.g., "en", "ar") |
| provider_config | dict | null | Pass-through provider-specific kwargs |

## Returns

```json
{
  "query": "latest AI research",
  "provider": "exa",
  "hit_count": 10,
  "pages": [
    {
      "title": "DeepMind's Latest AI Safety Paper",
      "url": "https://example.com/paper1",
      "markdown": "# DeepMind's Latest AI Safety Paper\n\n...",
      "fetched_at": "2026-04-11T20:33:15.123456Z"
    },
    {
      "title": "Anthropic Research on Constitutional AI",
      "url": "https://example.com/paper2",
      "markdown": "# Anthropic Research on Constitutional AI\n\n...",
      "fetched_at": "2026-04-11T20:33:17.456789Z"
    }
  ]
}
```

On search failure:

```json
{
  "query": "rare topic",
  "provider": null,
  "hit_count": 0,
  "pages": [],
  "error": "no providers available"
}
```

## Implementation notes

The tool offloads `research_search` (sync HTTP) to a thread executor to avoid blocking the FastMCP event loop. The markdown extraction is native async and awaited directly. Fetch errors are logged but do not stop the pipeline.

## Errors

- `query must be non-empty` — query is null, empty, or whitespace
- `depth must be 1-10` — depth outside valid range
- `search_timeout: <seconds>` — Search request exceeded EXTERNAL_TIMEOUT_SECS (30s)
- `no providers available (...)` — All search providers lack credentials
- `fetch_timeout` — Individual URL fetch exceeded timeout (logged, continues pipeline)

## Examples

### Discover and fetch 2 pages of AI research

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_deep", {
        "query": "AI alignment 2026",
        "depth": 2,
        "provider": "exa"
    })
    print(f"Found {r['hit_count']} results, fetched {len(r['pages'])} pages")
    for page in r["pages"]:
        print(f"- {page['title']}")
```

### Deep dive into specific domain

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_deep", {
        "query": "machine learning frameworks",
        "depth": 3,
        "include_domains": ["github.io", "pytorch.org"],
        "language": "en"
    })
```

### Research with date filter and cascade through providers

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_deep", {
        "query": "recent safety incidents",
        "depth": 1,
        "provider": "tavily",
        "start_date": "2026-01-01",
        "end_date": "2026-04-11"
    })
    if r.get("error"):
        print(f"Error: {r['error']}")
    else:
        print(f"Provider used: {r['provider']}")
```

## Related tools

- `research_search` — Search only (no fetch)
- `research_fetch` — Fetch single URL
- `research_spider` — Fetch multiple URLs in parallel
- `research_markdown` — Extract markdown from single URL
