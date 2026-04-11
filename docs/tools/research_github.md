# research_github

GitHub search via gh CLI with query sanitization and command-line flag injection prevention.

## Synopsis

```python
result = await session.call_tool("research_github", {
    "kind": "repos",
    "query": "python async web framework",
    "limit": 10
})
```

## Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| kind | string | required | Search kind: `repos` \| `code` \| `issues` |
| query | string | required | Search query (non-empty, ≤512 chars; validated against allow-list regex) |
| limit | int | 20 | Max results (clamped to 1-100) |
| sort | string | best-match | Sort order: `best-match` \| `stars` \| `forks` \| `updated` |
| order | string | desc | Sort direction: `asc` \| `desc` |
| language | string | null | Programming language (code search only; e.g., "python", "rust") |
| owner | string | null | Filter by owner (repos search) |
| repo | string | null | Filter by repo (code search) |

## Returns

```json
{
  "kind": "repos",
  "query": "python async web framework",
  "results": [
    {
      "name": "FastAPI",
      "description": "FastAPI is a modern, fast web framework for building APIs...",
      "url": "https://github.com/tiangolo/fastapi",
      "stargazersCount": 75231
    },
    {
      "name": "Quart",
      "description": "Quart is an async Python web framework...",
      "url": "https://github.com/pallets/quart",
      "stargazersCount": 3721
    }
  ],
  "fetched_at": "2026-04-11T20:34:00.123456Z"
}
```

On error:

```json
{
  "error": "query cannot start with '-' (looks like a flag)"
}
```

## Query validation

The query parameter is validated against a conservative allow-list regex to prevent `gh` CLI flag injection:

- Allowed: alphanumerics, space, `-`, `/`, `:`, `@`, `#`, `'`, `"`, `?`, `!`, `(`, `)`, `+`, `,`, `=`, `[`, `]`, `&`, `*`, `~`, `|`, `<`, `>`
- Blocked: queries starting with `-` (looks like a flag), length > 512 chars
- All queries are passed as command-line arguments (not shell-parsed) with `--` separator to stop flag parsing

## Errors

- `query must be non-empty string` — query is null, empty, or whitespace
- `query too long (max 512 chars)` — query exceeds length limit
- `query cannot start with '-'` — Potential flag injection attempt
- `query contains characters outside allow-list` — Query contains invalid characters
- `kind must be one of ['repos', 'code', 'issues']` — Invalid kind parameter
- `gh cli not found` — gh command not available in PATH
- `gh search failed: <reason>` — GitHub API error (e.g., authentication, rate limit)

## Examples

### Search for popular Python repos

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_github", {
        "kind": "repos",
        "query": "python async",
        "limit": 10,
        "sort": "stars",
        "order": "desc"
    })
    for repo in r["results"]:
        print(f"{repo['name']}: {repo['stargazersCount']} stars")
```

### Search code for specific function

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_github", {
        "kind": "code",
        "query": "def async_context_manager",
        "language": "python",
        "limit": 20,
        "owner": "python"
    })
```

### Search issues in a specific repo

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_github", {
        "kind": "issues",
        "query": "async timeout",
        "repo": "python/cpython",
        "sort": "updated",
        "limit": 5
    })
```

### Search repos by recent updates

```python
async with ClientSession(read, write) as s:
    r = await s.call_tool("research_github", {
        "kind": "repos",
        "query": "rust web framework",
        "sort": "updated",
        "order": "desc",
        "limit": 15
    })
```

## Related tools

- `research_search` — Web search across multiple providers (Exa, Tavily, Firecrawl, Brave)
- `research_fetch` — Fetch GitHub URL content
- `research_spider` — Fetch multiple GitHub URLs in parallel
