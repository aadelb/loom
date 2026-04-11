# research_search

Web search via Exa, Tavily, Firecrawl, or Brave with provider cascade fallback.

## Synopsis

```python
result = await session.call_tool("research_search", {
    "query": "AI safety research 2026",
    "provider": "exa",
    "n": 10
})
```

## Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| query | string | required | Search query (non-empty, trimmed) |
| provider | string | exa | Preferred provider: `exa` \| `tavily` \| `firecrawl` \| `brave` |
| n | int | 10 | Number of results (clamped to 1-50) |
| include_domains | array | null | Only search within these domains (provider-specific behavior) |
| exclude_domains | array | null | Exclude these domains (provider-specific) |
| start_date | string | null | Filter results from ISO date (yyyy-mm-dd, provider-specific) |
| end_date | string | null | Filter results until ISO date (yyyy-mm-dd, provider-specific) |
| language | string | null | Language hint (provider-specific; e.g., "en", "ar") |
| provider_config | dict | null | Pass-through provider-specific kwargs (e.g., `{"semantic": true}` for Exa) |

## Returns

Normalized response shape across all providers:

```json
{
  "provider": "exa",
  "results": [
    {
      "title": "AI Safety Research at DeepMind",
      "url": "https://deepmind.google/research/ai-safety/",
      "score": 0.92
    },
    {
      "title": "Safety-focused AI Development",
      "url": "https://example.com/ai-safety",
      "score": 0.87
    }
  ]
}
```

On error (all providers exhausted):

```json
{
  "provider": null,
  "results": [],
  "error": "no providers available (missing API keys: EXA_API_KEY, TAVILY_API_KEY, FIRECRAWL_API_KEY, BRAVE_API_KEY)"
}
```

## Provider cascade fallback

If the preferred provider lacks an API key or fails, the tool automatically cascades through:
1. Preferred provider (from `provider` parameter)
2. Remaining providers in order: exa, tavily, firecrawl, brave

The first provider to succeed is returned. If all fail or lack API keys, error is returned with no results.

## Errors

- `query must be non-empty string` — query is null, empty, or whitespace-only
- `n must be 1-50` — result count outside valid range
- `no providers available (missing API keys: ...)` — All providers lack credentials or all failed
- Provider-specific errors logged but cascade continues (e.g., "exa api rate limit exceeded")

## Examples

### Simple search with Exa (semantic)

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_search", {
        "query": "climate change 2026",
        "provider": "exa",
        "n": 5
    })
    for hit in r["results"]:
        print(f"{hit['title']} ({hit['score']})")
```

### Search with domain filters and date range

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_search", {
        "query": "Python machine learning",
        "include_domains": ["github.com", "github.io"],
        "start_date": "2025-01-01",
        "end_date": "2026-04-11",
        "n": 20
    })
```

### Tavily (agent-native) with provider-specific config

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_search", {
        "query": "latest AI news",
        "provider": "tavily",
        "language": "en",
        "provider_config": {"include_domains": ["news.ycombinator.com"]}
    })
```

### Cascade automatically through providers

```python
async with ClientSession(read, write) as s:
    # Will try: exa -> tavily -> firecrawl -> brave
    r = await s.call_tool("research_search", {
        "query": "rare topic",
        "provider": "exa"
    })
    print(f"Results from: {r['provider']}")
```

## Related tools

- `research_deep` — Search + fetch + markdown in one pipeline
- `research_fetch` — Fetch a single discovered URL
- `research_spider` — Fetch multiple URLs in parallel
