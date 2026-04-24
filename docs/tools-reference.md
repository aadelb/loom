# Loom MCP Tools Reference

Complete documentation of all 23+ MCP tools exposed by the Loom research server. Tools are organized by category and include parameters, return types, and usage examples.

## Overview

Loom provides a comprehensive research toolkit split into 8 categories:

- **Core** (6 tools) — fundamental fetching, searching, and content extraction
- **GitHub** (3 tools) — GitHub API integration and README/releases retrieval
- **Stealth** (2 tools) — anti-bot browser automation
- **LLM** (8 tools) — language model integration with cascade routing
- **Enrichment** (2 tools) — language detection and Wayback Machine recovery
- **Creative** (11 tools) — advanced research analysis and consensus-building
- **YouTube** (1 tool) — transcript extraction
- **Session Management** (3 tools) — persistent browser contexts
- **Config** (2 tools) — runtime configuration management
- **Cache** (2 tools) — cache statistics and cleanup

---

## Core Tools

### research_fetch

Unified URL fetcher with three configurable modes: plain HTTP, stealth browser (Camoufox), or dynamic JavaScript-enabled (Botasaurus).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | URL to fetch |
| `mode` | string | `"stealthy"` | Fetch strategy: `"http"`, `"stealthy"` (Camoufox), `"dynamic"` (Botasaurus) |
| `max_chars` | integer | 50000 | Max characters to return (hard cap: 200KB) |
| `solve_cloudflare` | boolean | `true` | Attempt Cloudflare bypass on stealthy/dynamic modes |
| `headers` | dict | `null` | Custom HTTP headers |
| `user_agent` | string | `null` | Override User-Agent header |
| `proxy` | string | `null` | Proxy URL (http:// or socks5://) |
| `cookies` | dict | `null` | Cookies dict for request |
| `accept_language` | string | `"en-US,en;q=0.9,ar;q=0.8"` | Accept-Language header |
| `wait_for` | string | `null` | CSS selector to wait for (dynamic mode only) |
| `return_format` | string | `"text"` | Response format: `"text"`, `"html"`, `"json"`, `"screenshot"` |
| `timeout` | integer | `null` | Request timeout (seconds, max 120) |
| `bypass_cache` | boolean | `false` | Skip cache read/write |
| `auto_escalate` | boolean | `null` | Auto-escalate http→stealthy→dynamic on Cloudflare blocks |

**Returns:**

```json
{
  "url": "https://example.com",
  "status_code": 200,
  "content_type": "text/html; charset=utf-8",
  "title": "Example Domain",
  "text": "This domain is for use in examples and documentation...",
  "html": "<!DOCTYPE html><html>...</html>",
  "json": null,
  "screenshot": null,
  "tool": "httpx",
  "elapsed_ms": 342,
  "error": null
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_fetch(
    url="https://docs.anthropic.com",
    mode="stealthy",
    max_chars=50000,
    return_format="text"
)
print(result["text"][:500])
```

---

### research_spider

Parallelized bulk fetching of multiple URLs with bounded concurrency, per-fetch timeout, and deduplication.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `urls` | list[string] | required | URLs to fetch |
| `mode` | string | `"stealthy"` | Fetch mode: `"http"`, `"stealthy"`, `"dynamic"` |
| `max_chars_each` | integer | 5000 | Max chars per response |
| `concurrency` | integer | 5 | Max parallel fetches (1-20) |
| `fail_fast` | boolean | `false` | Stop on first error |
| `dedupe` | boolean | `true` | Remove duplicate URLs before fetching |
| `order` | string | `"input"` | Result ordering: `"input"`, `"domain"`, `"size"` |
| `solve_cloudflare` | boolean | `true` | Attempt Cloudflare bypass |
| `headers` | dict | `null` | Custom headers |
| `user_agent` | string | `null` | Override User-Agent |
| `proxy` | string | `null` | Proxy URL |
| `cookies` | dict | `null` | Cookies |
| `accept_language` | string | `"en-US,en;q=0.9,ar;q=0.8"` | Language header |
| `timeout` | integer | `null` | Per-fetch timeout (seconds) |

**Returns:**

```json
[
  {
    "url": "https://example.com/page1",
    "title": "Page 1",
    "text": "content...",
    "html_len": 5432,
    "fetched_at": "2026-04-24T10:30:15.123Z",
    "tool": "httpx",
    "status_code": 200,
    "elapsed_ms": 340
  },
  {
    "url": "https://example.com/page2",
    "error": "timeout",
    "tool": "httpx"
  }
]
```

**API Key:** None — free

**Example Usage:**

```python
results = await research_spider(
    urls=["https://docs.python.org", "https://nodejs.org/docs"],
    mode="http",
    concurrency=3,
    dedupe=True,
    order="size"
)
for r in results:
    print(f"{r['url']}: {len(r.get('text', ''))} chars")
```

---

### research_markdown

Async markdown extractor using Crawl4AI with optional CSS subtree selection, JavaScript execution, and Wayback Machine fallback.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | Target URL |
| `bypass_cache` | boolean | `false` | Force refetch |
| `css_selector` | string | `null` | Extract only this CSS subtree |
| `js_before_scrape` | string | `null` | JavaScript to execute before scraping (max 2KB) |
| `screenshot` | boolean | `false` | Capture and include screenshot |
| `remove_selectors` | list[string] | `null` | CSS selectors to remove before extraction |
| `headers` | dict | `null` | Custom headers |
| `user_agent` | string | `null` | Override User-Agent |
| `proxy` | string | `null` | Proxy URL |
| `cookies` | dict | `null` | Cookies |
| `accept_language` | string | `"en-US,en;q=0.9,ar;q=0.8"` | Language header |
| `timeout` | integer | `null` | Timeout (seconds) |
| `extract_selector` | string | `null` | Alias for `css_selector` |
| `wait_for` | string | `null` | CSS selector to wait for before scraping |

**Returns:**

```json
{
  "url": "https://example.com",
  "title": "Example Title",
  "markdown": "# Example\n\nClean LLM-ready markdown content...",
  "tool": "crawl4ai",
  "fetched_at": "2026-04-24T10:30:15.123Z",
  "error": null
}
```

**API Key:** None — free (Crawl4AI with fallback to Trafilatura)

**Example Usage:**

```python
result = await research_markdown(
    url="https://en.wikipedia.org/wiki/Artificial_intelligence",
    css_selector="div.mw-parser-output",
    screenshot=True
)
print(result["markdown"][:1000])
```

---

### research_search

Unified web search across 8 providers (Exa, Tavily, Firecrawl, Brave, DuckDuckGo, arXiv, Wikipedia, HackerNews, Reddit).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Search query |
| `provider` | string | from config (default "exa") | Search provider: `"exa"`, `"tavily"`, `"firecrawl"`, `"brave"`, `"ddgs"`, `"arxiv"`, `"wikipedia"`, `"hackernews"`, `"reddit"` |
| `n` | integer | 10 | Max results (1-50, capped) |
| `include_domains` | list[string] | `null` | Only search these domains |
| `exclude_domains` | list[string] | `null` | Exclude these domains |
| `start_date` | string | `null` | ISO yyyy-mm-dd start date |
| `end_date` | string | `null` | ISO yyyy-mm-dd end date |
| `language` | string | `null` | ISO 639-1 language hint |
| `provider_config` | dict | `null` | Provider-specific kwargs |

**Returns:**

```json
{
  "provider": "exa",
  "query": "machine learning papers",
  "results": [
    {
      "url": "https://arxiv.org/abs/2401.00001",
      "title": "Attention Is All You Need",
      "snippet": "A Transformer-based architecture for sequence-to-sequence learning...",
      "score": 0.95,
      "published_date": "2017-06-12"
    }
  ],
  "error": null
}
```

**API Keys:**
- Exa: `EXA_API_KEY` (free tier: 10 queries/month)
- Tavily: `TAVILY_API_KEY` (free tier: 100 queries/month)
- Firecrawl: `FIRECRAWL_API_KEY`
- Brave: `BRAVE_API_KEY` (free tier: 20 results, no domain filters)
- Others: None — free

**Example Usage:**

```python
# Use Exa semantic search
result = research_search(
    query="AI safety alignment",
    provider="exa",
    n=20,
    exclude_domains=["twitter.com", "reddit.com"]
)

# Fallback: DuckDuckGo (no API key needed)
result = research_search(
    query="open source Python libraries",
    provider="ddgs",
    n=10
)
```

---

### research_deep

Full-pipeline deep research orchestrating query expansion, multi-provider search, parallel fetch, LLM extraction, ranking, synthesis, and optional GitHub/community/red-team enrichment.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Research question or topic |
| `depth` | integer | 2 | Scales result volume (1-10); multiplier for URL count |
| `include_domains` | list[string] | `null` | Restrict search to these domains |
| `exclude_domains` | list[string] | `null` | Exclude these domains |
| `start_date` | string | `null` | ISO yyyy-mm-dd start date |
| `end_date` | string | `null` | ISO yyyy-mm-dd end date |
| `language` | string | `null` | Language hint |
| `provider_config` | dict | `null` | Provider-specific kwargs |
| `search_providers` | list[string] | from config | Search providers to use (auto-appends arxiv, wikipedia, ddgs for relevant queries) |
| `expand_queries` | boolean | `true` | Enable LLM query expansion |
| `extract` | boolean | `true` | Enable LLM content extraction |
| `synthesize` | boolean | `true` | Enable LLM answer synthesis |
| `include_github` | boolean | `true` | Enable GitHub enrichment for code queries |
| `include_community` | boolean | `false` | Include HN + Reddit sentiment (optional, off by default) |
| `include_red_team` | boolean | `false` | Generate adversarial counter-arguments (optional) |
| `include_misinfo_check` | boolean | `false` | Stress-test synthesis for misinformation (optional) |
| `max_cost_usd` | float | 0.50 | Total LLM cost cap for this call |

**Returns:**

```json
{
  "query": "How do transformers work?",
  "search_variations": [
    "How do transformers work?",
    "Transformer architecture attention mechanism",
    "self-attention multi-head neural networks"
  ],
  "providers_used": ["exa", "arxiv", "brave"],
  "pages_searched": 45,
  "pages_fetched": 8,
  "top_pages": [
    {
      "url": "https://arxiv.org/abs/1706.03762",
      "title": "Attention Is All You Need",
      "snippet": "...",
      "markdown": "# Attention Is All You Need\n...",
      "score": 0.98,
      "relevance_score": 0.92,
      "detected_language": "en"
    }
  ],
  "synthesis": {
    "answer": "Transformers are neural network architectures based on...",
    "citations": ["https://arxiv.org/abs/1706.03762"],
    "confidence": 0.89
  },
  "github_repos": [
    {
      "name": "pytorch/pytorch",
      "url": "https://github.com/pytorch/pytorch",
      "stars": 75000,
      "readme": "..."
    }
  ],
  "language_stats": {"en": 8},
  "community_sentiment": null,
  "red_team_report": null,
  "misinfo_report": null,
  "total_cost_usd": 0.12,
  "elapsed_ms": 18500,
  "error": null
}
```

**API Keys:** Depends on selected providers (see `research_search`)

**Example Usage:**

```python
result = await research_deep(
    query="What are the latest advances in multimodal AI?",
    depth=3,
    expand_queries=True,
    extract=True,
    synthesize=True,
    include_github=True,
    search_providers=["exa", "arxiv"],
    max_cost_usd=1.00
)
print(result["synthesis"]["answer"])
print(f"Cost: ${result['total_cost_usd']:.3f}")
```

---

## GitHub Tools

### research_github

Search GitHub for repositories, code, or issues using the public REST API.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `kind` | string | required | Search type: `"repo"` (repositories), `"code"` (code search), `"issues"` |
| `query` | string | required | GitHub search query (supports GitHub syntax) |
| `sort` | string | `"stars"` | Sort field: `"stars"`, `"forks"`, `"updated"` |
| `order` | string | `"desc"` | Order: `"asc"` or `"desc"` |
| `limit` | integer | 20 | Max results (1-100) |
| `language` | string | `null` | Programming language filter |
| `owner` | string | `null` | Repository owner (user/org) |
| `repo` | string | `null` | Repository name |

**Returns:**

```json
{
  "kind": "repo",
  "query": "machine learning library",
  "total_count": 12450,
  "results": [
    {
      "name": "tensorflow/tensorflow",
      "url": "https://github.com/tensorflow/tensorflow",
      "description": "An Open Source Machine Learning Framework...",
      "stars": 185000,
      "forks": 74000,
      "language": "C++",
      "updated_at": "2026-04-24T09:30:00Z"
    }
  ]
}
```

**API Key:** Optional `GITHUB_TOKEN` (increases rate limits from 60 to 5000 requests/hour)

**Example Usage:**

```python
result = research_github(
    kind="repo",
    query="pytorch neural network",
    sort="stars",
    limit=10,
    language="Python"
)
```

---

### research_github_readme

Fetch and return the README file of a GitHub repository.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `owner` | string | required | Repository owner (user/org) |
| `repo` | string | required | Repository name |
| `ref` | string | `"main"` | Branch/tag to fetch from |

**Returns:**

```json
{
  "owner": "pytorch",
  "repo": "pytorch",
  "url": "https://raw.githubusercontent.com/pytorch/pytorch/main/README.md",
  "content": "# PyTorch\n\nTensors and Dynamic neural networks...",
  "error": null
}
```

**API Key:** Optional `GITHUB_TOKEN`

**Example Usage:**

```python
result = research_github_readme("pytorch", "pytorch")
print(result["content"][:500])
```

---

### research_github_releases

Fetch release information from a GitHub repository.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `owner` | string | required | Repository owner |
| `repo` | string | required | Repository name |
| `limit` | integer | 10 | Max releases to return |
| `include_prerelease` | boolean | `true` | Include pre-releases |

**Returns:**

```json
{
  "owner": "pytorch",
  "repo": "pytorch",
  "total_count": 150,
  "releases": [
    {
      "tag": "v2.3.0",
      "name": "PyTorch 2.3.0",
      "published_at": "2024-04-15T10:30:00Z",
      "is_prerelease": false,
      "body": "## Release Notes\n...",
      "download_count": 5000000
    }
  ]
}
```

**API Key:** Optional `GITHUB_TOKEN`

**Example Usage:**

```python
result = research_github_releases("pytorch", "pytorch", limit=5)
for release in result["releases"]:
    print(f"{release['tag']}: {release['download_count']} downloads")
```

---

## Stealth Tools

### research_camoufox

Fetch URLs using Camoufox (Firefox with anti-detection patches) for Cloudflare-protected and JavaScript-heavy pages.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | URL to fetch |
| `session` | string | `null` | Browser session ID (not used, for API compat) |
| `screenshot` | boolean | `false` | Capture base64-encoded screenshot |
| `timeout` | integer | `null` | Operation timeout (seconds, capped at 120) |

**Returns:**

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "html": "<!DOCTYPE html>...",
  "text": "This domain is for use in examples...",
  "screenshot": "iVBORw0KGgoAAAANSUhEUgAAA...",
  "error": null
}
```

**API Key:** None — free (requires Camoufox: `pip install camoufox`)

**Example Usage:**

```python
result = await research_camoufox(
    url="https://cloudflare-protected-site.com",
    screenshot=True
)
```

---

### research_botasaurus

Fetch URLs using Botasaurus (dynamic Selenium-like browser) with headless mode, image blocking, and proxy support.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | URL to fetch |
| `session` | string | `null` | Browser session ID (not used, for API compat) |
| `proxy` | string | `null` | Proxy URL (http:// or socks5://) |
| `screenshot` | boolean | `false` | Capture base64-encoded screenshot |
| `timeout` | integer | `null` | Operation timeout (seconds) |

**Returns:**

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "html": "<!DOCTYPE html>...",
  "text": "Content extracted from page...",
  "screenshot": "iVBORw0KGgoAAAANSUhEUgAAA...",
  "error": null
}
```

**API Key:** None — free (requires Botasaurus: `pip install botasaurus`)

**Example Usage:**

```python
result = await research_botasaurus(
    url="https://js-heavy-spa.com",
    proxy="socks5://proxy.example.com:1080",
    screenshot=False
)
```

---

## LLM Tools

LLM tools use cascade routing across NVIDIA NIM, OpenAI, Anthropic, and vLLM. All LLM calls enforce a configurable daily cost cap and track per-call costs.

### research_llm_summarize

Summarize text into 1-3 sentences using an LLM.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | string | required | Text to summarize (user-supplied, wrapped for prompt injection safety) |
| `max_tokens` | integer | 400 | Max tokens in summary (clamped 100-2000) |
| `model` | string | `"auto"` | Model override or `"auto"` for cascade default |
| `language` | string | `"en"` | Output language |
| `provider_override` | string | `null` | Force a provider: `"nvidia"`, `"openai"`, `"anthropic"`, `"vllm"` |

**Returns:**

```json
{
  "summary": "The article discusses recent advances in transformer models and their application to language understanding tasks.",
  "model": "meta/llama-4-maverick-17b-128e-instruct",
  "provider": "nvidia",
  "cost_usd": 0.0002,
  "input_tokens": 512,
  "output_tokens": 45,
  "error": null
}
```

**API Keys:** Depends on provider cascade order

**Example Usage:**

```python
result = await research_llm_summarize(
    text="Long article content...",
    max_tokens=200,
    language="es"
)
print(result["summary"])
```

---

### research_llm_extract

Extract structured data from text using a schema.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | string | required | Text to extract from |
| `schema` | dict | required | Pydantic-style schema: `{"field_name": "type", ...}` |
| `model` | string | `"auto"` | Model override or `"auto"` |
| `provider_override` | string | `null` | Force a provider |

**Returns:**

```json
{
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
  },
  "model": "gpt-4-mini",
  "provider": "openai",
  "cost_usd": 0.0003,
  "error": null
}
```

**API Keys:** Depends on provider cascade order

**Example Usage:**

```python
result = await research_llm_extract(
    text="Contact: Jane Smith, jane@example.com, 28 years old",
    schema={"name": "string", "email": "string", "age": "integer"}
)
```

---

### research_llm_classify

Classify text into predefined categories.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | string | required | Text to classify |
| `categories` | list[string] | required | List of category names |
| `model` | string | `"auto"` | Model override or `"auto"` |
| `provider_override` | string | `null` | Force a provider |

**Returns:**

```json
{
  "category": "positive",
  "confidence": 0.92,
  "categories_scored": {
    "positive": 0.92,
    "negative": 0.05,
    "neutral": 0.03
  },
  "model": "gpt-4-mini",
  "provider": "openai",
  "cost_usd": 0.00015,
  "error": null
}
```

**API Keys:** Depends on provider cascade order

---

### research_llm_translate

Translate text to a target language.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | string | required | Text to translate |
| `target_language` | string | required | Target language (e.g., "Spanish", "Chinese", "Arabic") |
| `model` | string | `"auto"` | Model override or `"auto"` |
| `provider_override` | string | `null` | Force a provider |

**Returns:**

```json
{
  "translation": "Hola, ¿cómo estás?",
  "source_language": "English",
  "target_language": "Spanish",
  "model": "kimi-k2-instruct",
  "provider": "nvidia",
  "cost_usd": 0.0001,
  "error": null
}
```

**API Keys:** Depends on provider cascade order

---

### research_llm_query_expand

Expand a query into 2-5 variations for broader search coverage.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Original search query |
| `n` | integer | 3 | Number of variations to generate (max 5) |
| `model` | string | `"auto"` | Model override or `"auto"` |
| `provider_override` | string | `null` | Force a provider |

**Returns:**

```json
{
  "original": "machine learning papers",
  "queries": [
    "deep learning research publications",
    "neural network training algorithms",
    "AI model architectures and methods"
  ],
  "model": "gpt-4-mini",
  "provider": "openai",
  "cost_usd": 0.0002,
  "error": null
}
```

**API Keys:** Depends on provider cascade order

---

### research_llm_answer

Generate a cited answer from source documents.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `question` | string | required | Question to answer |
| `sources` | list[dict] | required | Source docs: `[{"title": str, "text": str, "url": str}, ...]` |
| `style` | string | `"cited"` | Response style: `"cited"`, `"essay"`, `"bullet"` |
| `model` | string | `"auto"` | Model override or `"auto"` |
| `provider_override` | string | `null` | Force a provider |

**Returns:**

```json
{
  "answer": "Transformers use self-attention mechanisms...[1] Unlike RNNs, transformers process all tokens in parallel...[2]",
  "citations": [1, 2],
  "sources": [
    {
      "index": 1,
      "title": "Attention Is All You Need",
      "url": "https://arxiv.org/abs/1706.03762"
    },
    {
      "index": 2,
      "title": "BERT: Pre-training of Deep...",
      "url": "https://arxiv.org/abs/1810.04805"
    }
  ],
  "model": "gpt-4-mini",
  "provider": "openai",
  "cost_usd": 0.0005,
  "confidence": 0.87,
  "error": null
}
```

**API Keys:** Depends on provider cascade order

---

### research_llm_embed

Generate vector embeddings for text (useful for semantic search and clustering).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | string | required | Text to embed |
| `model` | string | `"auto"` | Model override or `"auto"` for cascade default |
| `provider_override` | string | `null` | Force a provider |

**Returns:**

```json
{
  "text": "Machine learning is a subset of artificial intelligence",
  "embedding": [0.123, -0.456, 0.789, ...],
  "dimension": 1536,
  "model": "nvidia/nv-embed-v2",
  "provider": "nvidia",
  "cost_usd": 0.00001,
  "error": null
}
```

**API Keys:** Depends on provider cascade order

---

### research_llm_chat

Raw multi-turn chat with an LLM.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `messages` | list[dict] | required | Chat messages: `[{"role": "user"|"system"|"assistant", "content": str}, ...]` |
| `model` | string | `"auto"` | Model override or `"auto"` |
| `max_tokens` | integer | 1500 | Max tokens in response |
| `temperature` | float | 0.2 | Sampling temperature (0.0-1.0) |
| `provider_override` | string | `null` | Force a provider |

**Returns:**

```json
{
  "text": "The capital of France is Paris, located in the north-central part of the country.",
  "model": "gpt-4-mini",
  "provider": "openai",
  "cost_usd": 0.0004,
  "input_tokens": 120,
  "output_tokens": 40,
  "error": null
}
```

**API Keys:** Depends on provider cascade order

---

## Enrichment Tools

### research_detect_language

Detect the language of text (free, no API key required).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | string | required | Text to analyze (min 10 chars recommended) |

**Returns:**

```json
{
  "language": "en",
  "confidence": 0.98,
  "alternatives": [
    {"lang": "en", "prob": 0.98},
    {"lang": "de", "prob": 0.01},
    {"lang": "nl", "prob": 0.005}
  ],
  "error": null
}
```

**API Key:** None — free (requires `langdetect`: `pip install langdetect`)

**Example Usage:**

```python
result = research_detect_language("Bonjour, comment allez-vous?")
print(result["language"])  # "fr"
```

---

### research_wayback

Retrieve archived versions from the Wayback Machine (free, no API key).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | Original URL to look up |
| `limit` | integer | 1 | Max snapshots to return |

**Returns:**

```json
{
  "original_url": "https://example.com",
  "snapshots": [
    {
      "timestamp": "20230615120000",
      "archive_url": "https://web.archive.org/web/20230615120000/https://example.com",
      "status_code": 200,
      "mimetype": "text/html"
    }
  ],
  "error": null
}
```

**API Key:** None — free

**Example Usage:**

```python
result = research_wayback("https://dead-website.example.com", limit=3)
for snapshot in result["snapshots"]:
    print(f"Archived: {snapshot['timestamp']}")
```

---

## Creative Tools

11 advanced research tools for adversarial testing, multi-lingual search, consensus-building, and misinformation detection.

### research_red_team

Generate and search for counter-arguments to a claim (adversarial testing).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `claim` | string | required | Claim or thesis to challenge |
| `n_counter` | integer | 3 | Number of counter-arguments to generate |
| `max_cost_usd` | float | 0.10 | LLM cost cap |

**Returns:**

```json
{
  "claim": "AI will never exceed human intelligence",
  "counter_arguments": [
    {
      "counter_claim": "AI systems already outperform humans on narrow tasks like chess",
      "evidence_found": 12,
      "sources": [
        {"title": "Deep Blue defeats Kasparov", "url": "..."}
      ]
    }
  ],
  "total_cost_usd": 0.05,
  "error": null
}
```

**API Keys:** LLM provider keys (NVIDIA_NIM_API_KEY, OPENAI_API_KEY, etc.)

---

### research_multilingual

Cross-lingual information arbitrage: search in multiple languages, back-translate, highlight information asymmetries.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Query (any language) |
| `languages` | list[string] | `["ar", "es", "de", "zh", "ru"]` | ISO 639-1 language codes |
| `n_per_lang` | integer | 3 | Results per language |
| `max_cost_usd` | float | 0.10 | Translation cost cap |

**Returns:**

```json
{
  "query": "COVID-19 vaccine efficacy",
  "results_by_language": {
    "ar": [{"url": "...", "title": "...", "snippet": "..."}],
    "es": [...]
  },
  "overlap_analysis": {"unique_to_ar": 2, "unique_to_es": 1},
  "total_cost_usd": 0.08,
  "error": null
}
```

**API Keys:** LLM provider keys

---

### research_consensus

Multi-engine voting: search across providers, rank results by consensus, highlight disagreement.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Search query |
| `providers` | list[string] | `["exa", "brave"]` | Providers to vote across |
| `n` | integer | 5 | Results per provider |

**Returns:**

```json
{
  "query": "best python web framework",
  "consensus": [
    {
      "url": "https://example.com",
      "title": "Flask documentation",
      "votes": 2,
      "providers": ["exa", "brave"]
    }
  ],
  "disagreement": [
    {
      "url": "https://niche.example.com",
      "votes": 1,
      "providers": ["exa"]
    }
  ],
  "error": null
}
```

**API Keys:** Depends on selected providers

---

### research_misinfo_check

Stress-test a claim for misinformation: search for contradictory evidence and fact-checks.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `claim` | string | required | Claim to fact-check |
| `max_cost_usd` | float | 0.05 | Cost cap |

**Returns:**

```json
{
  "claim": "The Earth is flat",
  "risk_level": "HIGH",
  "contradictory_sources": [
    {"title": "NASA satellite imagery", "url": "..."},
    {"title": "Scientific consensus", "url": "..."}
  ],
  "fact_checks": [
    {"source": "snopes.com", "rating": "False"}
  ],
  "error": null
}
```

**API Keys:** Search provider keys (EXA_API_KEY, BRAVE_API_KEY, etc.)

---

### research_temporal_diff

Compare archived versions of a URL to detect content drift, removals, or edits.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | URL to analyze |
| `snapshots_limit` | integer | 5 | Max historical snapshots to compare |

**Returns:**

```json
{
  "url": "https://example.com",
  "snapshots": [
    {"timestamp": "20230101", "content": "..."},
    {"timestamp": "20231201", "content": "..."}
  ],
  "changes": [
    {"type": "added", "text": "New section added"},
    {"type": "removed", "text": "Old disclaimer removed"}
  ],
  "error": null
}
```

**API Key:** None — free (uses Wayback Machine)

---

### research_citation_graph

Traverse academic citation networks (arXiv, Semantic Scholar) to build expert knowledge graphs.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `paper_id` | string | required | arXiv ID or Semantic Scholar ID |
| `depth` | integer | 2 | Citation graph depth (1-3) |

**Returns:**

```json
{
  "paper": {"id": "1706.03762", "title": "Attention Is All You Need", "year": 2017},
  "cited_by": [
    {"id": "1810.04805", "title": "BERT", "citation_count": 50000}
  ],
  "cites": [
    {"id": "1506.06762", "title": "VGG", "citation_count": 80000}
  ],
  "error": null
}
```

**API Key:** None — free (Semantic Scholar has no key requirement)

---

### research_ai_detect

Detect AI-generated content (GPT, Claude, etc.) using entropy and pattern analysis.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | string | required | Text to analyze |
| `model` | string | `"auto"` | Detection model or `"auto"` |

**Returns:**

```json
{
  "is_ai_generated": false,
  "confidence": 0.91,
  "entropy_score": 4.2,
  "suspicious_patterns": ["repeated_phrases"],
  "error": null
}
```

**API Key:** None — free (local analysis)

---

### research_curriculum

Generate a learning path from ELI5 to PhD level on any topic.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | Topic to learn |
| `style` | string | `"structured"` | Learning path style: `"structured"`, `"socratic"`, `"project-based"` |
| `max_cost_usd` | float | 0.05 | LLM cost cap |

**Returns:**

```json
{
  "topic": "Machine Learning",
  "levels": [
    {
      "level": "ELI5",
      "lessons": ["What is learning?", "Patterns in data"],
      "resources": ["Khan Academy intro video"]
    },
    {
      "level": "Undergraduate",
      "lessons": ["Linear algebra basics", "Probability and statistics"],
      "resources": ["Andrew Ng's ML course"]
    }
  ],
  "total_cost_usd": 0.03,
  "error": null
}
```

**API Keys:** LLM provider keys

---

### research_community_sentiment

Aggregate practitioner sentiment from HN and Reddit on a tech topic.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Topic to analyze |
| `n` | integer | 5 | Results per source |

**Returns:**

```json
{
  "query": "Rust programming language",
  "sources": {
    "hackernews": {
      "sentiment": "positive",
      "score": 0.78,
      "discussions": [
        {"title": "Why Rust is great for systems...", "url": "..."}
      ]
    },
    "reddit": {
      "sentiment": "mixed",
      "score": 0.65,
      "discussions": [...]
    }
  },
  "error": null
}
```

**API Key:** None — free

---

### research_wiki_ghost

Mine Wikipedia talk pages and edit history for consensus-building and controversy detection.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `article_title` | string | required | Wikipedia article title |
| `analyze_consensus` | boolean | `true` | Extract consensus from talk pages |

**Returns:**

```json
{
  "article": "Machine Learning",
  "edit_history": [
    {"editor": "User123", "date": "2024-01-15", "change": "Updated metrics"}
  ],
  "controversies": [
    {"topic": "AI safety inclusion", "positions": 2, "unresolved": true}
  ],
  "consensus": "High agreement on definition, debate on scope",
  "error": null
}
```

**API Key:** None — free

---

### research_semantic_sitemap

Generate a semantic sitemap of a domain: extract structure, categorize pages, identify topic clusters.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `domain` | string | required | Domain to analyze (e.g., `docs.python.org`) |
| `depth` | integer | 2 | Crawl depth (1-3) |
| `max_cost_usd` | float | 0.10 | LLM cost cap for semantic analysis |

**Returns:**

```json
{
  "domain": "docs.python.org",
  "sitemap": [
    {
      "path": "/3/library/",
      "title": "The Python Standard Library",
      "children": [
        {"path": "/3/library/builtins/", "topic": "Built-in functions"}
      ]
    }
  ],
  "topic_clusters": {
    "core_language": ["builtins.html", "types.html"],
    "stdlib": ["itertools.html", "collections.html"]
  },
  "error": null
}
```

**API Keys:** Optional LLM provider keys for semantic analysis

---

## YouTube Tool

### fetch_youtube_transcript

Extract auto-generated or manual subtitles from YouTube videos (free).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | YouTube video URL |
| `language` | string | `"en"` | Subtitle language code |

**Returns:**

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "transcript": "[00:00] Never gonna give you up\n[00:05] Never gonna let you down...",
  "duration": 212,
  "note": null,
  "error": null
}
```

**API Key:** None — free (requires `yt-dlp`: `pip install yt-dlp`)

**Example Usage:**

```python
result = fetch_youtube_transcript(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    language="en"
)
print(result["transcript"][:500])
```

---

## Session Management Tools

### research_session_open

Open a persistent browser session (Camoufox, Chromium, or Firefox) with optional login.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | required | Session identifier |
| `browser` | string | `"chromium"` | Browser type: `"camoufox"`, `"chromium"`, `"firefox"` |
| `ttl_seconds` | integer | 3600 | Session time-to-live (max 86400) |
| `login_url` | string | `null` | Optional login/authentication URL |

**Returns:**

```json
{
  "session_id": "sess_abc123",
  "name": "my_session",
  "browser": "chromium",
  "created_at": "2026-04-24T10:30:15Z",
  "ttl_seconds": 3600,
  "status": "ready",
  "error": null
}
```

**API Key:** None — free

---

### research_session_list

List all active sessions.

**Parameters:** None

**Returns:**

```json
{
  "sessions": [
    {
      "name": "my_session",
      "browser": "chromium",
      "created_at": "2026-04-24T10:30:15Z",
      "last_used": "2026-04-24T10:35:00Z",
      "age_seconds": 285
    }
  ]
}
```

**API Key:** None — free

---

### research_session_close

Close and cleanup a session.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | required | Session name to close |

**Returns:**

```json
{
  "name": "my_session",
  "status": "closed",
  "duration_seconds": 3600,
  "error": null
}
```

**API Key:** None — free

---

## Config Tools

### research_config_get

Read current runtime configuration (or a single key).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `key` | string | `null` | Config key to retrieve (returns all if null) |

**Returns:**

```json
{
  "SPIDER_CONCURRENCY": 5,
  "EXTERNAL_TIMEOUT_SECS": 30,
  "LOG_LEVEL": "INFO",
  "DEFAULT_SEARCH_PROVIDER": "exa",
  "LLM_DEFAULT_CHAT_MODEL": "meta/llama-4-maverick-17b-128e-instruct",
  "RESEARCH_SEARCH_PROVIDERS": ["exa", "brave"]
}
```

**API Key:** None — free

---

### research_config_set

Update a runtime configuration key (validated, persisted atomically).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `key` | string | required | Config key name |
| `value` | any | required | New value (validated per bounds) |

**Returns:**

```json
{
  "key": "SPIDER_CONCURRENCY",
  "old_value": 5,
  "new_value": 10,
  "persisted_at": "2026-04-24T10:30:15Z",
  "error": null
}
```

**API Key:** None — free

---

## Cache Tools

### research_cache_stats

Return cache storage statistics.

**Parameters:** None

**Returns:**

```json
{
  "size_mb": 342.5,
  "entry_count": 1250,
  "oldest": "2026-03-25T14:20:00Z",
  "newest": "2026-04-24T10:30:00Z",
  "cache_dir": "/home/user/.cache/loom/cache"
}
```

**API Key:** None — free

---

### research_cache_clear

Remove cache entries older than N days.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `older_than_days` | integer | 30 | Age threshold (reads from `CACHE_TTL_DAYS` if not specified) |

**Returns:**

```json
{
  "deleted_count": 342,
  "freed_mb": 125.3,
  "older_than_days": 30
}
```

**API Key:** None — free

---

## Summary Table

| Category | Count | Key Tools | Free? |
|----------|-------|-----------|-------|
| Core | 6 | `research_fetch`, `research_spider`, `research_markdown`, `research_search`, `research_deep` | Mostly |
| GitHub | 3 | `research_github`, `research_github_readme`, `research_github_releases` | Yes |
| Stealth | 2 | `research_camoufox`, `research_botasaurus` | Yes |
| LLM | 8 | All tools with LLM in name | No (cascade routing) |
| Enrichment | 2 | `research_detect_language`, `research_wayback` | Yes |
| Creative | 11 | Red-team, multilingual, consensus, misinfo, temporal-diff, citation-graph, AI-detect, curriculum, sentiment, wiki-ghost, semantic-sitemap | Mostly |
| YouTube | 1 | `fetch_youtube_transcript` | Yes |
| Sessions | 3 | `research_session_open`, `research_session_list`, `research_session_close` | Yes |
| Config | 2 | `research_config_get`, `research_config_set` | Yes |
| Cache | 2 | `research_cache_stats`, `research_cache_clear` | Yes |

**Total: 40+ tools**

