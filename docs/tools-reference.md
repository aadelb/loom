# Loom MCP Tools Reference

Complete documentation of all 245+ MCP tools exposed by the Loom research server. Tools are organized by category and include parameters, return types, and usage examples.

## Overview

Loom provides a comprehensive research toolkit organized into major categories with 245+ tools:

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
- **Infrastructure** (4 tools) — compute, billing, and payment services
- **Communication** (2 tools) — email and note-taking
- **Media** (2 tools) — audio transcription and document conversion
- **Darkweb** (2 tools) — Tor network management

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

Unified web search across 17 providers (Exa, Tavily, Firecrawl, Brave, DuckDuckGo, arXiv, Wikipedia, HackerNews, Reddit, NewsAPI, CoinDesk, CoinMarketCap, Binance, Ahmia, Darksearch, UMMRO RAG, and more).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Search query |
| `provider` | string | from config (default "exa") | Search provider: `"exa"`, `"tavily"`, `"firecrawl"`, `"brave"`, `"ddgs"`, `"arxiv"`, `"wikipedia"`, `"hackernews"`, `"reddit"`, `"newsapi"`, `"coindesk"`, `"coinmarketcap"`, `"binance"`, `"ahmia"`, `"darksearch"`, `"ummro"` |
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
### research_fingerprint_behavior

Build a behavioral personality vector for an LLM model by analyzing responses to standardized probes. Measures verbosity, helpfulness bias, safety threshold, creativity, rule following, and hedging tendency. Returns personality scores and targeted attack recommendations.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `model` | string | `"nvidia"` | Model provider: `"nvidia"`, `"openai"`, `"anthropic"`, `"groq"`, `"deepseek"`, `"gemini"`, `"moonshot"`, `"vllm"`, or `"auto"` |
| `probe_count` | integer | 10 | Number of behavioral probes to send (1-10) |

**Returns:**

```json
{
  "personality_vector": {
    "verbosity": 72.5,
    "helpfulness_bias": 65.0,
    "safety_threshold": 35.0,
    "creativity": 58.3,
    "rule_following": 80.0,
    "hedging_tendency": 42.1
  },
  "probe_results": [
    {
      "name": "quantum_computing",
      "category": "safe",
      "response": "Quantum computing leverages quantum mechanics principles...",
      "error": null
    },
    {
      "name": "security_vulns",
      "category": "borderline",
      "response": "Common vulnerabilities include SQL injection, XSS, CSRF...",
      "error": null
    }
  ],
  "attack_recommendations": [
    "Model has high compliance rate. Try gradual escalation (crescendo).",
    "Model is safety-aware. Use indirect/roleplay approaches.",
    "Model shows creative reasoning. Use novel prompt structures."
  ],
  "metadata": {
    "model": "nvidia",
    "probes_sent": 10,
    "probes_succeeded": 10
  }
}
```

**Metrics Explanation:**
- **verbosity** (0-100): Average response length. Higher = more detailed outputs.
- **helpfulness_bias** (0-100): Compliance rate on borderline requests. Higher = more helpful/compliant.
- **safety_threshold** (0-100): Frequency of refusals on edge-case requests. Higher = more restrictive.
- **creativity** (0-100): Response diversity across similar prompts. Higher = more varied reasoning.
- **rule_following** (0-100): Adherence to structured formatting. Higher = stricter format compliance.
- **hedging_tendency** (0-100): Frequency of caveats/disclaimers. Higher = more uncertain language.

**API Keys:** Depends on provider cascade order

**Cost:** VARIABLE (depends on LLM provider and token usage)

**Example Usage:**

```python
result = await research_fingerprint_behavior(
    model="openai",
    probe_count=10
)

# Check personality profile
vector = result["personality_vector"]
print(f"Verbosity: {vector['verbosity']:.1f}")
print(f"Safety Threshold: {vector['safety_threshold']:.1f}")

# Review attack recommendations
for rec in result["attack_recommendations"]:
    print(f"- {rec}")
```

**Use Cases:**
- Profile model behavior before targeted attacks
- Identify safety-aware vs. compliant models
- Assess vulnerability to escalation tactics
- Compare personality vectors across model versions
- Optimize prompt strategies based on behavioral traits

---


### research_pydantic_agent

Create and run a type-safe AI agent with Pydantic validation. Returns raw agent responses with optional system prompt guidance and structured validation.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `prompt` | string | required | User prompt (will be wrapped for safety) |
| `model` | string | `"nvidia_nim"` | LLM model to use (cascade default: `"auto"`) |
| `system_prompt` | string | `""` | Optional system prompt to guide agent behavior |
| `max_tokens` | integer | 1000 | Max tokens in response (10-8000) |

**Returns:**

```json
{
  "success": true,
  "response": "Agent response text...",
  "model_used": "meta/llama-4-maverick-17b-128e-instruct",
  "tokens_used": 120,
  "error": null
}
```

Or on failure:

```json
{
  "success": false,
  "error": "error_message"
}
```

**Fallback:** If pydantic-ai is unavailable, falls back to `research_llm_answer`

**API Keys:** Depends on provider cascade order

**Example Usage:**

```python
result = await research_pydantic_agent(
    prompt="What are the 3 most important machine learning papers?",
    system_prompt="You are an expert in machine learning research.",
    model="gpt-4",
    max_tokens=500
)
print(result["response"])
```

---

### research_structured_llm

Extract structured data from text with full Pydantic schema validation. Ensures response matches exact schema before returning.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `prompt` | string | required | Text/question to extract from |
| `output_schema` | dict | required | Pydantic schema: `{"field_name": "type", ...}` |
| `model` | string | `"nvidia_nim"` | LLM model to use |
| `provider_override` | string | `null` | Force provider: `"nvidia"`, `"openai"`, `"anthropic"`, `"groq"`, etc. |

**Supported Types in Schema:**
- `"str"` or `"string"` — text
- `"int"` or `"integer"` — integers
- `"float"` — floating-point numbers
- `"bool"` or `"boolean"` — true/false
- `"list"` — arrays
- `"dict"` or `"object"` — nested objects

**Returns:**

```json
{
  "success": true,
  "data": {
    "author": "John Doe",
    "papers": ["Paper A", "Paper B"],
    "citation_count": 1250,
    "verified": true
  },
  "model_used": "gpt-4",
  "cost_usd": 0.0008,
  "error": null
}
```

Or on validation failure:

```json
{
  "success": false,
  "error": "Field 'citation_count' expected int, got str",
  "model_used": "gpt-4",
  "cost_usd": 0.0003
}
```

**Fallback:** If pydantic-ai is unavailable, falls back to `research_llm_extract` with compatible schema

**API Keys:** Depends on provider cascade order

**Example Usage:**

```python
result = await research_structured_llm(
    prompt="Extract researcher info from: Dr. Jane Smith published 42 papers with 5000 citations",
    output_schema={
        "name": "string",
        "papers": "integer",
        "citations": "integer"
    },
    model="gpt-4-mini"
)
print(result["data"]["citations"])  # 5000
```

**Differences from research_llm_extract:**
- **Stricter validation** — Full Pydantic model validation before returning
- **Error details** — Exact validation error messages
- **JSON parsing** — Handles markdown JSON code blocks automatically
- **Type safety** — Fails if response JSON doesn't match schema exactly

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

## Infrastructure Tools

### research_vastai_search

Search GPU instances on the VastAI compute marketplace.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | `null` | Search query (e.g., "A100 GPUs under $2/hr") |
| `gpu_name` | string | `null` | GPU model filter |
| `min_ram` | integer | `null` | Minimum RAM in GB |
| `max_price` | float | `null` | Max hourly price in USD |

**Returns:**

```json
{
  "provider": "vastai",
  "results": [
    {
      "instance_id": "12345",
      "gpu": "A100",
      "ram": 32,
      "price_per_hour": 1.50,
      "location": "USA",
      "availability": true
    }
  ],
  "error": null
}
```

**API Key:** `VASTAI_API_KEY`

**Example Usage:**

```python
result = await research_vastai_search(
    gpu_name="A100",
    max_price=2.0
)
```

---

### research_vastai_status

Check compute marketplace status and pricing.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `gpu_name` | string | `null` | GPU model to check pricing |

**Returns:**

```json
{
  "total_instances": 5432,
  "available_instances": 3200,
  "avg_price_per_hour": 1.25,
  "price_range": {"min": 0.50, "max": 5.00},
  "error": null
}
```

**API Key:** `VASTAI_API_KEY`

---

### research_usage_report

Get usage statistics and resource consumption data.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `period` | string | `"month"` | Time period: `"day"`, `"week"`, `"month"`, `"year"` |

**Returns:**

```json
{
  "period": "month",
  "llm_calls": 1250,
  "llm_cost_usd": 12.50,
  "fetch_calls": 450,
  "search_calls": 320,
  "total_api_calls": 2020,
  "error": null
}
```

**API Key:** None — local tracking

---

### research_stripe_balance

Check billing account balance and recent charges.

**Parameters:** None

**Returns:**

```json
{
  "account_id": "acct_xxxxx",
  "balance_usd": 150.75,
  "available_usd": 145.20,
  "pending_charges": [
    {
      "description": "API usage",
      "amount_usd": 5.55,
      "created_at": "2026-04-27T10:00:00Z"
    }
  ],
  "error": null
}
```

**API Key:** `STRIPE_LIVE_KEY`

---

## Communication Tools

### research_email_report

Send a research report or summary via email.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `to_email` | string | required | Recipient email address |
| `subject` | string | required | Email subject line |
| `body` | string | required | Email body (plain text or markdown) |
| `include_summary` | boolean | `false` | Auto-summarize body with LLM |

**Returns:**

```json
{
  "to_email": "recipient@example.com",
  "subject": "Research Report: AI Safety",
  "status": "sent",
  "sent_at": "2026-04-27T10:30:00Z",
  "error": null
}
```

**API Keys:** `SMTP_USER`, `SMTP_APP_PASSWORD`

**Example Usage:**

```python
result = await research_email_report(
    to_email="colleague@example.com",
    subject="Weekly Research Summary",
    body="Key findings on AI safety...",
    include_summary=True
)
```

---

### research_save_note

Save text or research results to Joplin notebook.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `notebook_name` | string | `"Research"` | Target notebook name |
| `title` | string | required | Note title |
| `content` | string | required | Note body (markdown) |
| `tags` | list[string] | `null` | Tags to add to note |

**Returns:**

```json
{
  "note_id": "abc123",
  "title": "Machine Learning Papers",
  "notebook": "Research",
  "tags": ["ml", "papers"],
  "created_at": "2026-04-27T10:30:00Z",
  "error": null
}
```

**API Key:** `JOPLIN_TOKEN`

---

### research_list_notebooks

List all Joplin notebooks.

**Parameters:** None

**Returns:**

```json
{
  "notebooks": [
    {
      "id": "notebook1",
      "title": "Research",
      "note_count": 45
    },
    {
      "id": "notebook2",
      "title": "Projects",
      "note_count": 12
    }
  ],
  "error": null
}
```

**API Key:** `JOPLIN_TOKEN`

---

## Media Tools

### research_transcribe

Convert audio file to text (speech-to-text).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `audio_url` | string | required | URL to audio file or local path |
| `language` | string | `"en"` | ISO 639-1 language code |
| `model` | string | `"base"` | Whisper model: `"tiny"`, `"base"`, `"small"`, `"medium"`, `"large"` |

**Returns:**

```json
{
  "text": "Hello, this is a test transcription...",
  "language": "en",
  "confidence": 0.95,
  "duration_seconds": 25.5,
  "model": "base",
  "error": null
}
```

**API Key:** None — free (local Whisper)

**Example Usage:**

```python
result = await research_transcribe(
    audio_url="https://example.com/podcast.mp3",
    language="en",
    model="base"
)
print(result["text"])
```

---

### research_convert_document

Convert between document formats (PDF, DOCX, MD, TXT, HTML, etc.).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `input_file` | string | required | Input file path or URL |
| `output_format` | string | required | Target format: `"pdf"`, `"docx"`, `"md"`, `"txt"`, `"html"`, `"xlsx"` |
| `optimize` | boolean | `false` | Optimize file size/quality |

**Returns:**

```json
{
  "input_file": "document.pdf",
  "output_format": "md",
  "output_file": "/tmp/document.md",
  "size_bytes": 5420,
  "conversion_time_ms": 342,
  "error": null
}
```

**API Key:** None — free (local conversion)

**Example Usage:**

```python
result = await research_convert_document(
    input_file="research_paper.pdf",
    output_format="md",
    optimize=True
)
```

---

## Darkweb Tools

### research_tor_status

Check Tor network connection status.

**Parameters:** None

**Returns:**

```json
{
  "is_connected": true,
  "exit_ip": "203.0.113.45",
  "country": "USA",
  "connected_at": "2026-04-27T10:30:00Z",
  "circuit_info": "3 hops (entry → middle → exit)",
  "error": null
}
```

**API Key:** `TOR_CONTROL_PASSWORD` (optional)

---

### research_tor_new_identity

Request a new Tor identity (new exit IP).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `wait_seconds` | integer | `5` | Wait time for identity change |

**Returns:**

```json
{
  "old_ip": "203.0.113.45",
  "new_ip": "198.51.100.42",
  "country_changed": true,
  "old_country": "USA",
  "new_country": "Netherlands",
  "changed_at": "2026-04-27T10:30:05Z",
  "error": null
}
```

**API Key:** `TOR_CONTROL_PASSWORD` (optional)

---

## research_cipher_mirror

Audits text for leaked credentials using Shannon entropy detection and known API key patterns.

**Parameters:** `text` (str), `min_confidence` (float, default 0.6)
**Returns:** `{"credentials": [...], "total_found": int, "high_confidence": int}`

---

## research_forum_cortex

Analyzes dark forum discourse using search providers and LLM-powered classification.

**Parameters:** `query` (str), `providers` (list, default ["ahmia"]), `max_posts` (int, default 20)
**Returns:** `{"posts": [...], "topics": [...], "sentiment": str}`

---

## research_onion_spectra

Classifies multilingual .onion content by safety category with language detection heuristics.

**Parameters:** `url` (str), `proxy` (str, optional)
**Returns:** `{"category": str, "language": str, "confidence": float, "content_preview": str}`

---

## research_ghost_weave

Builds temporal hyperlink graphs of hidden services using BFS traversal.

**Parameters:** `seed_urls` (list[str]), `depth` (int, default 2), `proxy` (str, optional)
**Returns:** `{"nodes": [...], "edges": [...], "stats": {...}}`

---

## research_dead_drop_scanner

Monitors ephemeral .onion sites for content changes using k-gram shingling and Jaccard similarity.

**Parameters:** `urls` (list[str]), `proxy` (str, optional), `similarity_threshold` (float, default 0.3)
**Returns:** `{"sites": [...], "changes_detected": int}`

---

## research_find_experts

Finds domain experts for a given topic using search and LLM analysis.

**Parameters:** `topic` (str), `n` (int, default 5)
**Returns:** `{"experts": [...], "topic": str}`

---

## find_similar_exa

Finds similar pages to a given URL using Exa's neural similarity search.

**Parameters:** `url` (str), `n` (int, default 10)
**Returns:** `{"results": [...], "url": str}`
**API Key:** `EXA_API_KEY`

---

## research_health_check

Returns server health status including uptime and active session count.

**Parameters:** None
**Returns:** `{"status": "healthy", "timestamp": str, "uptime_seconds": int, "active_sessions": int}`

---

## research_metrics

Exports Prometheus-compatible metrics for tool latency, cost, and error rates.

**Parameters:** None
**Returns:** `{"metrics": str}` (Prometheus text format)

---

## research_slack_notify

Sends a notification message to a Slack channel via bot token.

**Parameters:** `channel` (str), `message` (str)
**Returns:** `{"sent": bool, "channel": str}`
**API Key:** `SLACK_BOT_TOKEN`

---

## research_image_analyze

Analyzes images using Google Cloud Vision API.

**Parameters:** `image_url` (str), `features` (list, default ["labels", "text"])
**Returns:** `{"labels": [...], "text": str, "objects": [...]}`
**API Key:** `GOOGLE_CLOUD_API_KEY`

---

## research_text_to_speech

Converts text to speech using Google Cloud TTS.

**Parameters:** `text` (str), `language` (str, default "en-US"), `voice` (str, optional)
**Returns:** `{"audio_base64": str, "duration_ms": int}`
**API Key:** `GOOGLE_CLOUD_API_KEY`

---

## research_tts_voices

Lists available text-to-speech voices.

**Parameters:** `language` (str, optional)
**Returns:** `{"voices": [...]}`
**API Key:** `GOOGLE_CLOUD_API_KEY`

---

## research_vercel_status

Checks Vercel deployment status.

**Parameters:** None
**Returns:** `{"status": str, "url": str}`

---


---

## Enrichment & Advanced Tools (Research Tools 47-93)

---

### research_markdown

Extract clean LLM-ready markdown from any URL using Crawl4AI with optional CSS selector and JavaScript execution.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | Target URL to extract markdown from |
| `bypass_cache` | bool | false | Skip cache read/write for this request |
| `css_selector` | str\|null | null | CSS selector to extract only specific subtree |
| `js_before_scrape` | str\|null | null | JavaScript code to execute before scraping (max 2KB) |
| `screenshot` | bool | false | Capture webpage screenshot |
| `remove_selectors` | list[str]\|null | null | CSS selectors to remove before extraction |
| `headers` | dict[str, str]\|null | null | Custom HTTP headers |
| `user_agent` | str\|null | null | Override User-Agent header |
| `proxy` | str\|null | null | HTTP or SOCKS5 proxy URL |
| `cookies` | dict[str, str]\|null | null | Request cookies |
| `accept_language` | str | en-US,en;q=0.9,ar;q=0.8 | Accept-Language header |
| `timeout` | int\|null | null | Request timeout in seconds (max 120) |
| `extract_selector` | str\|null | null | Alias for css_selector |
| `wait_for` | str\|null | null | CSS selector to wait for before scraping |

**Returns:** `{"url": "...", "title": "...", "markdown": "...", "tool": "crawl4ai", "fetched_at": "2026-04-28T..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_metrics

Return Prometheus-compatible metrics for Grafana dashboard integration. Tracks tool usage, errors, latency, and provider statistics.

**Returns:** `{"metrics": [...], "timestamp": "...", "version": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_misinfo_check

Stress test a claim by generating false variants and searching for sources to verify or refute it.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `claim` | str | - | Claim or statement to fact-check |
| `n_sources` | int | 5 | Number of sources to search for each variant |
| `max_cost_usd` | float | 0.05 | Maximum LLM cost budget for this request |

**Returns:** `{"claim": "...", "variants": [...], "findings": [...], "confidence": 0.85}`
**Cost:** PAID (varies with n_sources and LLM cascade)
**Rate Limit:** None

---

### research_multilingual

Search in multiple languages to discover cross-lingual information arbitrage and multilingual perspectives.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | - | Search query in any language |
| `languages` | list[str]\|null | null | Languages to search in (auto-detected if null, defaults to [en, es, fr, de, zh, ar]) |
| `n_per_lang` | int | 3 | Number of results per language |
| `max_cost_usd` | float | 0.1 | Maximum cost budget for search and translation |

**Returns:** `{"query": "...", "results": {"en": [...], "es": [...], ...}, "translations": [...]}`
**Cost:** PAID (multi-provider + translation)
**Rate Limit:** None

---

### research_network_persona

Analyze social network structure within forum data to identify influential nodes and community dynamics.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `posts` | list[dict[str, Any]] | - | Forum posts with author, content, and interaction metadata |
| `min_interactions` | int | 2 | Minimum interaction count to include a user in analysis |

**Returns:** `{"nodes": [...], "edges": [...], "communities": [...], "influence_scores": {...}}`
**Cost:** FREE
**Rate Limit:** None

---

### research_nmap_scan

Port scan a target using nmap to identify open ports and services.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target` | str | - | IP address or domain to scan |
| `ports` | str | 80,443,8080,8443 | Comma-separated port numbers or port ranges |
| `scan_type` | str | basic | Scan type: basic, aggressive, or stealth |

**Returns:** `{"target": "...", "ports": [...], "services": [...], "scan_duration_ms": 5432}`
**Cost:** FREE
**Rate Limit:** None

---

### research_ocr_extract

Extract text from images using Tesseract OCR engine.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url_or_path` | str | - | URL to image or local file path |
| `language` | str | eng | Language code for OCR (eng, fra, deu, spa, ara, etc.) |

**Returns:** `{"text": "...", "confidence": 0.92, "language": "eng", "processing_time_ms": 1234}`
**Cost:** FREE
**Rate Limit:** None

---

### research_onion_spectra

Classify .onion site content by language and safety category.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL of .onion site to classify |
| `fetch_content` | bool | true | Fetch and analyze site content |
| `max_chars` | int | 5000 | Maximum characters to analyze from fetched content |

**Returns:** `{"url": "...", "language": "en", "category": "marketplace\|forum\|news\|...", "confidence": 0.88, "warnings": [...]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_password_check

Check if a password appears in known password breaches using k-anonymity protocol.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `password` | str | - | Password to check |

**Returns:** `{"password": "***", "in_breaches": true, "breach_count": 12, "safe": false}`
**Cost:** FREE
**Rate Limit:** 4 req/min (k-anonymity compliant)

---

### research_pdf_extract

Extract text from a PDF URL with optional page range specification.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to PDF file |
| `pages` | str\|null | null | Page range (e.g., '1-5' or '1,3,5') |

**Returns:** `{"url": "...", "text": "...", "page_count": 42, "title": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_pdf_search

Search for text within a PDF file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to PDF file |
| `query` | str | - | Text to search for in PDF |

**Returns:** `{"url": "...", "query": "...", "matches": [...], "page_numbers": [3, 7, 12]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_persona_profile

Cross-platform persona reconstruction from text samples for deanonymization analysis.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `texts` | list[str] | - | Text samples from suspected same author |
| `metadata` | dict[str, Any]\|null | null | Optional metadata (timestamps, platforms, locations) |

**Returns:** `{"author_profile": {...}, "writing_style": {...}, "confidence": 0.76, "risk_factors": [...]}`
**Cost:** PAID (LLM analysis)
**Rate Limit:** None

---

### research_radicalization_detect

Monitor text for radicalization indicators using NLP classifiers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to analyze |
| `context` | str\|null | null | Context or platform info (forum, dark web, etc.) |

**Returns:** `{"text": "...", "radicalization_score": 0.65, "indicators": [...], "severity": "medium"}`
**Cost:** PAID (LLM analysis)
**Rate Limit:** None

---

### research_red_team

Generate and search for counter-arguments to a claim for adversarial validation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `claim` | str | - | Claim to challenge |
| `n_counter` | int | 3 | Number of counter-arguments to generate |
| `max_cost_usd` | float | 0.1 | Maximum LLM cost budget |

**Returns:** `{"claim": "...", "counter_arguments": [...], "supporting_urls": [...], "persuasiveness_score": 0.72}`
**Cost:** PAID (LLM + search)
**Rate Limit:** None

---

### research_rss_fetch

Fetch and parse an RSS or Atom feed.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to RSS/Atom feed |
| `max_items` | int | 20 | Maximum items to return |

**Returns:** `{"feed": {...}, "items": [...], "item_count": 18, "updated_at": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_rss_search

Search across multiple RSS feeds for items matching a query.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | list[str] | - | URLs of RSS/Atom feeds to search |
| `query` | str | - | Search query |
| `max_results` | int | 20 | Maximum results to return |

**Returns:** `{"query": "...", "results": [...], "feeds_searched": 5, "total_matches": 18}`
**Cost:** FREE
**Rate Limit:** None

---

### research_realtime_monitor

Monitor multiple sources for recent mentions of topics. Queries HackerNews, Reddit, arXiv, NewsAPI, and Wikipedia for recent mentions of provided topics in parallel. Returns aggregated results sorted by timestamp (newest first).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `topics` | list[str] | - | Topics to monitor (e.g., ["AI", "Python", "security"]) |
| `sources` | list[str]\|null | null | Sources to query: "hackernews", "reddit", "arxiv", "newsapi", "wikipedia" (defaults to all) |
| `hours_back` | int | 24 | Number of hours to look back in time |

**Returns:** `{"topics": [...], "time_range_hours": 24, "total_mentions": 15, "mentions_by_topic": {"AI": 8, "Python": 7}, "mentions_by_source": {"hackernews": 5, "reddit": 4, "arxiv": 6}, "recent_items": [{"topic": "...", "source": "...", "title": "...", "url": "...", "timestamp": "...", "score": 42.0}, ...]}`
**Cost:** FREE (uses free APIs)
**Rate Limit:** Varies by source (HackerNews: 10K/day, Reddit: 60/min without auth, arXiv: no limit, NewsAPI: depends on plan, Wikipedia: no strict limit)

**Notes:**
- HackerNews uses `created_at_i` timestamp filter for precise time-based queries
- Reddit returns posts from last 24 hours max (API limitation)
- arXiv returns new papers sorted by submission date
- NewsAPI requires `NEWS_API_KEY` config (falls back to empty results if not set)
- Wikipedia change queries may have limited coverage for niche topics
- Results are deduplicated by URL and source
- Timestamp parsing handles both ISO 8601 and date-only (YYYY-MM-DD) formats


### research_save_note

Create a note in Joplin via REST API for persistent research note-taking.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | str | - | Note title |
| `body` | str | - | Note content (supports Markdown) |
| `notebook` | str\|null | null | Target notebook name (defaults to Inbox) |

**Returns:** `{"id": "...", "title": "...", "created_at": "...", "notebook": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_screenshot

Take a screenshot of a webpage using Playwright headless browser.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to screenshot |
| `full_page` | bool | false | Capture full page or viewport only |
| `selector` | str\|null | null | CSS selector of element to screenshot |

**Returns:** `{"url": "...", "image_path": "cache/screenshots/abc123.png", "width": 1920, "height": 1080}`
**Cost:** FREE
**Rate Limit:** None

---

### research_search

Search the web using configured provider with domain filtering and temporal bounds.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | - | Search query |
| `provider` | str\|null | null | Provider: exa, tavily, firecrawl, brave, ddgs, arxiv, wikipedia, etc. |
| `n` | int | 10 | Number of results |
| `include_domains` | list[str]\|null | null | Filter to specific domains |
| `exclude_domains` | list[str]\|null | null | Exclude specific domains |
| `start_date` | str\|null | null | Results from this date (YYYY-MM-DD) |
| `end_date` | str\|null | null | Results until this date (YYYY-MM-DD) |
| `language` | str\|null | null | Language code (en, es, fr, etc.) |
| `provider_config` | dict[str, Any]\|null | null | Provider-specific configuration |

**Returns:** `{"query": "...", "results": [...], "provider": "exa", "total_results": 1234}`
**Cost:** PAID (varies by provider)
**Rate Limit:** Varies by provider

---

### research_security_headers

Analyze HTTP security headers of a URL to identify missing or misconfigured protections.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to analyze |

**Returns:** `{"url": "...", "headers": {...}, "issues": [...], "security_score": 85}`
**Cost:** FREE
**Rate Limit:** None

---

### research_semantic_sitemap

Crawl a domain's sitemap and cluster pages by semantic similarity for content mapping.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `domain` | str | - | Domain to crawl (with or without scheme) |
| `max_pages` | int | 50 | Maximum pages to crawl |
| `cluster_threshold` | float | 0.85 | Semantic similarity threshold for clustering (0-1) |

**Returns:** `{"domain": "...", "pages": [...], "clusters": [...], "topic_map": {...}}`
**Cost:** PAID (LLM embeddings)
**Rate Limit:** None

---

### research_sentiment_deep

Deep sentiment and emotion analysis with manipulation detection for nuanced understanding.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to analyze |
| `language` | str | en | Language code (auto-detect if empty) |

**Returns:** `{"text": "...", "sentiment": "positive", "confidence": 0.88, "emotions": {...}, "manipulation_score": 0.2}`
**Cost:** PAID (LLM analysis)
**Rate Limit:** None

---

### research_session_close

Close a persistent browser session by name.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | - | Session name to close |

**Returns:** `{"session": "...", "closed": true, "duration_seconds": 3600}`
**Cost:** FREE
**Rate Limit:** None

---

### research_session_list

List all active persistent browser sessions with details.

**Returns:** `{"sessions": [{"name": "...", "browser": "camoufox", "created_at": "...", "ttl_seconds": 3600}]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_session_open

Open (or reuse) a persistent browser session with optional login automation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | - | Session name (alphanumeric, hyphens, underscores) |
| `browser` | str | camoufox | Browser: camoufox, chromium, or firefox |
| `ttl_seconds` | int | 3600 | Session time-to-live in seconds |
| `login_url` | str\|null | null | URL to navigate to for login |
| `login_script` | str\|null | null | JavaScript to execute for automated login |

**Returns:** `{"session": "...", "browser": "camoufox", "created": true, "expires_at": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_slack_notify

Send research results to a Slack channel or thread.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `channel` | str | - | Slack channel ID or name |
| `text` | str | - | Message text |
| `thread_ts` | str\|null | null | Thread timestamp for replies |
| `blocks` | list[dict[str, Any]]\|null | null | Slack Block Kit JSON |

**Returns:** `{"channel": "...", "ts": "...", "sent": true}`
**Cost:** FREE
**Rate Limit:** None

---

### research_social_profile

Extract public profile metadata from a social media URL.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | Social media profile URL |

**Returns:** `{"url": "...", "username": "...", "name": "...", "bio": "...", "followers": 5000, "profile_image": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_social_search

Check if a username exists across multiple social media platforms.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `username` | str | - | Username to search |
| `platforms` | list[str]\|null | null | Platforms to check (defaults to: twitter, github, linkedin, instagram, reddit, etc.) |

**Returns:** `{"username": "...", "found_on": ["twitter", "github"], "profiles": [...]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_spider

Parallelized bulk fetching of multiple URLs with bounded concurrency and deduplication.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | list[str] | - | URLs to fetch |
| `mode` | str | stealthy | Fetch mode: http, stealthy, or dynamic |
| `max_chars_each` | int | 5000 | Max characters per response |
| `concurrency` | int | 10 | Max parallel fetches (1-20) |
| `fail_fast` | bool | false | Stop on first error |
| `dedupe` | bool | true | Remove duplicate URLs before fetching |
| `order` | str | input | Result ordering: input, domain, or size |
| `solve_cloudflare` | bool | true | Attempt Cloudflare bypass |
| `headers` | dict[str, str]\|null | null | Custom HTTP headers |
| `user_agent` | str\|null | null | Override User-Agent |
| `proxy` | str\|null | null | Proxy URL |
| `cookies` | dict[str, str]\|null | null | Request cookies |
| `accept_language` | str | en-US,en;q=0.9,ar;q=0.8 | Accept-Language header |
| `timeout` | int\|null | null | Per-fetch timeout (seconds) |

**Returns:** `[{"url": "...", "status_code": 200, "text": "...", "error": null}, ...]`
**Cost:** FREE
**Rate Limit:** None

---

### research_stripe_balance

Get Stripe account balance and recent transaction summary.

**Returns:** `{"balance": {"available": [...], "pending": [...]}, "currency": "usd"}`
**Cost:** FREE
**Rate Limit:** None

---

### research_stylometry

Analyze text for stylometric fingerprinting and author deanonymization.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text sample to analyze |
| `compare_texts` | list[str]\|null | null | Reference texts to compare against (for author matching) |

**Returns:** `{"text_length": 5432, "vocabulary_richness": 0.72, "sentence_length_avg": 18.5, "punctuation_profile": {...}, "author_match_score": 0.84}`
**Cost:** FREE
**Rate Limit:** None

---

### research_temporal_diff

Compare current page content with Wayback Machine archived version.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to compare |
| `max_cost_usd` | float | 0.05 | Maximum LLM cost budget for diff analysis |

**Returns:** `{"url": "...", "current": "...", "archived": "...", "diff_summary": "...", "changes": [...]}`
**Cost:** PAID (LLM analysis)
**Rate Limit:** None

---

### research_text_analyze

Perform NLP text analysis using NLTK (tokenization, POS tagging, named entities, etc.).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to analyze |
| `analyses` | list[str]\|null | null | Analysis types: tokens, pos, entities, sentiment, readability, etc. (defaults to all) |

**Returns:** `{"text": "...", "tokens": [...], "pos_tags": [...], "named_entities": [...], "readability_score": 8.5}`
**Cost:** FREE
**Rate Limit:** None

---

### research_text_to_speech

Convert text to speech using Google Cloud Text-to-Speech engine.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to convert |
| `language` | str | en | Language code (en, es, fr, de, zh, ar, etc.) |
| `voice` | str | en-US-Neural2-A | Voice ID (e.g., en-US-Neural2-A, en-US-Neural2-C) |
| `speaking_rate` | float | 1.0 | Speaking rate (0.25-4.0) |

**Returns:** `{"text": "...", "audio_file": "cache/audio/xyz.mp3", "duration_seconds": 15.2, "language": "en"}`
**Cost:** PAID (Google Cloud)
**Rate Limit:** None

---

### research_tor_new_identity

Request a new Tor circuit for exit node rotation.

**Returns:** `{"success": true, "new_exit_ip": "10.20.30.40", "exit_country": "US"}`
**Cost:** FREE
**Rate Limit:** Max 1 per 10 seconds

---

### research_tor_status

Check Tor daemon status and get current exit node IP and country.

**Returns:** `{"running": true, "exit_ip": "10.20.30.40", "exit_country": "US", "connected_circuits": 3}`
**Cost:** FREE
**Rate Limit:** None

---

### research_transcribe

Transcribe audio or video from YouTube or direct URL using OpenAI Whisper.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | YouTube URL or direct audio/video URL |
| `language` | str\|null | null | Language code (auto-detect if null) |
| `model_size` | str | base | Whisper model size: tiny, base, small, medium, large |

**Returns:** `{"url": "...", "text": "...", "language": "en", "duration_seconds": 300.5}`
**Cost:** FREE
**Rate Limit:** None

---

### research_tts_voices

List all supported Text-to-Speech voices with language and gender info.

**Returns:** `{"voices": [{"name": "en-US-Neural2-A", "language": "en-US", "gender": "female", ...}, ...]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_urlhaus_check

Check if URL is listed in URLhaus malware database (free, no key required).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to check |

**Returns:** `{"url": "...", "in_database": false, "threat": null}`
**Cost:** FREE
**Rate Limit:** None

---

### research_urlhaus_search

Search URLhaus by tag, signature, or payload hash (free API).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | - | Search term |
| `search_type` | str | tag | Search type: tag, signature, or hash |

**Returns:** `{"results": [...], "total": 42, "query": "...", "search_type": "tag"}`
**Cost:** FREE
**Rate Limit:** None

---

### research_usage_report

Aggregate LLM usage and costs from local cost tracker logs.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 7 | Number of days to report on |

**Returns:** `{"period_days": 7, "total_cost_usd": 12.34, "by_provider": {...}, "by_model": {...}}`
**Cost:** FREE
**Rate Limit:** None

---

### research_vastai_search

Search for available GPU instances on Vast.ai by type and price.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gpu_type` | str | RTX 4090 | GPU type (RTX 4090, A100, H100, etc.) |
| `max_price` | float | 1.0 | Maximum hourly price in USD |
| `n` | int | 5 | Number of results |

**Returns:** `{"results": [...], "gpu_type": "RTX 4090", "count": 5}`
**Cost:** FREE
**Rate Limit:** None

---

### research_vastai_status

Get Vast.ai account status including balance and running instances.

**Returns:** `{"balance_usd": 42.50, "running_instances": 2, "total_spent_usd": 123.45}`
**Cost:** FREE
**Rate Limit:** None

---

### research_vercel_status

Return placeholder status for Vercel integration.

**Returns:** `{"status": "operational", "version": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_wayback

Retrieve archived versions of a URL from the Wayback Machine (free).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to find in Wayback Machine |
| `limit` | int | 1 | Number of snapshots to return |

**Returns:** `{"url": "...", "snapshots": [{"timestamp": "20240101000000", "status": "200", "url": "..."}]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_whois

Run whois lookup on a domain to get registration and DNS information.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `domain` | str | - | Domain name to look up |

**Returns:** `{"domain": "...", "registrar": "...", "registered": "2010-01-15", "expires": "2025-01-15", "name_servers": [...]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_wiki_ghost

Mine Wikipedia talk pages and edit history for contested knowledge and controversies.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `topic` | str | - | Wikipedia topic or article title |
| `language` | str | en | Wikipedia language (en, es, fr, de, etc.) |

**Returns:** `{"topic": "...", "talk_discussions": [...], "edit_wars": [...], "contested_sections": [...]}`
**Cost:** FREE
**Rate Limit:** None

---

## Summary Table (All 94 Tools)

| Category | Count | Tools | Cost |
|----------|-------|-------|------|
| Core | 6 | `research_fetch`, `research_spider`, `research_markdown`, `research_search`, `research_deep`, `research_health_check` | FREE/PAID |
| GitHub | 3 | `research_github_search`, `research_github_readme`, `research_github_releases` | FREE |
| Stealth | 2 | `research_camoufox`, `research_botasaurus` | FREE |
| LLM | 8 | `research_summarize`, `research_extract`, `research_classify`, `research_translate`, `research_expand`, `research_answer`, `research_embed`, `research_llm_chat` | PAID |
| Enrichment | 3 | `research_wayback`, `research_temporal_diff`, `research_markdown` | FREE/PAID |
| Creative | 11 | `research_red_team`, `research_multilingual`, `research_consensus`, `research_misinfo_check`, `research_citation_graph`, `research_ai_detect`, `research_curriculum`, `research_community_sentiment`, `research_wiki_ghost`, `research_semantic_sitemap`, `research_network_persona` | PAID |
| YouTube | 1 | `research_transcribe` | FREE |
| Exa/Search | 1 | `research_search` | PAID |
| Sessions | 3 | `research_session_open`, `research_session_list`, `research_session_close` | FREE |
| Config | 2 | `research_config_get`, `research_config_set` | FREE |
| Cache | 2 | `research_cache_stats`, `research_cache_clear` | FREE |
| PDF | 2 | `research_pdf_extract`, `research_pdf_search` | FREE |
| NLP | 1 | `research_text_analyze` | FREE |
| Screenshot | 1 | `research_screenshot` | FREE |
| RSS | 2 | `research_rss_fetch`, `research_rss_search` | FREE |
| Social OSINT | 2 | `research_social_profile`, `research_social_search` | FREE |
| Security | 2 | `research_security_headers`, `research_urlhaus_check` | FREE |
| Breach | 2 | `research_password_check`, `research_urlhaus_search` | FREE |
| Darkweb Core | 2 | `research_tor_status`, `research_tor_new_identity` | FREE |
| Darkweb Advanced | 1 | `research_onion_spectra` | FREE |
| Text Analysis | 1 | `research_sentiment_deep` | PAID |
| Stylometry | 1 | `research_stylometry` | FREE |
| Radicalization | 1 | `research_radicalization_detect` | PAID |
| Persona | 1 | `research_persona_profile` | PAID |
| Communication | 2 | `research_email_report`, `research_slack_notify` | FREE |
| Note-Taking | 1 | `research_save_note` | FREE |
| Media | 2 | `research_text_to_speech`, `research_tts_voices` | PAID/FREE |
| Infrastructure | 5 | `research_vastai_search`, `research_vastai_status`, `research_stripe_balance`, `research_usage_report`, `research_metrics` | FREE |
| Hosting | 1 | `research_vercel_status` | FREE |
| Domain | 1 | `research_whois` | FREE |
| OCR | 1 | `research_ocr_extract` | FREE |
| Network | 1 | `research_nmap_scan` | FREE |

**Total: 167 tools**


---

## Adversarial Pipelines & Orchestration

### Advanced Attack Chains (10 tools)

| Tool | Purpose |
|------|---------|
| `research_evidence_pipeline` | Multi-turn evidence-gathering attack with reasoning loop |
| `research_cross_model_transfer` | Transfer jailbreaks across model architectures |
| `research_context_poison` | Context poisoning via prefix/suffix injection |
| `research_daisy_chain` | Chain multiple models as sequential reasoning steps |
| `research_adversarial_debate` | Exploit self-debate mechanisms in models |
| `research_model_evidence` | Evidence contradiction attack chains |
| `research_citation_police_pipeline` | Citation-based authority hijacking |
| `research_consensus_ring_pipeline` | Consensus mechanism bypass |
| `research_blind_spy_chain` | Indirect querying via proxy requests |
| `research_innocent_coder_chain` | Innocent-seeming code generation chains |

### Adversarial Scorers (8 tools)

Quantitative metrics for attack effectiveness and safety:

| Tool | Purpose | Range |
|------|---------|-------|
| `research_attack_score` | Score attack effectiveness | 0-100 |
| `research_stealth_score` | Measure detection evasion | 0-100 |
| `research_executability_score` | Score practical exploit capability | 0-100 |
| `research_quality_score` | Response quality and coherence | 0-100 |
| `research_harm_assess` | Harm potential assessment | low/medium/high/critical |
| `research_toxicity_check` | Safety boundary violation scoring | 0-100 |
| `research_danger_prescore` | Pre-scoring before execution | 0-100 |
| `research_stealth_detect` | Detect stealthy jailbreaks | present/absent |

### Orchestration (4 tools)

Target-specific attack optimization and planning:

| Tool | Purpose |
|------|---------|
| `research_target_orchestrate` | Orchestrate attacks against specific target models |
| `research_constraint_optimize` | Optimize prompt within token/format constraints |
| `research_optimization_plan` | Generate multi-stage optimization roadmap |
| `research_reid_auto` | Automated REID (Reasoning with Evidence for Intent Detection) |

---

## Tracking & Monitoring

### Behavioral Monitoring (5 tools)

Track and predict model vulnerabilities over time:

| Tool | Purpose |
|------|---------|
| `research_drift_monitor` | Monitor model behavior drift over time |
| `research_jailbreak_evolution` | Track jailbreak effectiveness trends |
| `research_consistency_pressure` | Measure consistency violation exploitation opportunities |
| `research_strategy_oracle` | Predict optimal strategy for new models |
| `research_model_sentiment` | Detect emotional/sentiment vulnerabilities |

---

## Infrastructure & Performance

### Performance Analysis (6 tools)

System monitoring and optimization tools:

| Tool | Purpose |
|------|---------|
| `research_semantic_cache_stats` | Semantic cache hit rates and analytics |
| `research_parameter_sweep` | Parameter sensitivity analysis for attacks |
| `research_cicd_run` | CI/CD integration and automation |
| `research_mcp_security_scan` | MCP server security audit |
| `research_recommend_tools` | Tool recommendation engine |
| `research_dashboard` | Real-time dashboard of all metrics |

---

## Analysis & Validation

### Compliance & Assessment (3 tools)

Policy validation and model analysis:

| Tool | Purpose |
|------|---------|
| `research_model_profile` | Detailed model capability/vulnerability profile |
| `research_policy_validate` | Validate compliance with safety policies |
| `research_consensus_build` | Build consensus evidence across models |

---

## Reports & Fuzzing

### Testing & Reporting (4 tools)

Automated testing frameworks and reporting:

| Tool | Purpose |
|------|---------|
| `research_generate_executive_report` | Executive summary of findings and risks |
| `research_jailbreak_fuzz` | Fuzzing framework for jailbreak discovery |
| `research_bpj_generate` | Behavioral Prompt Jailbreak generation |
| `research_full_spectrum` | Full-spectrum adversarial testing suite |

---

## Benchmarks & Multi-LLM

### Benchmarking Suite (3 tools)

Performance and capability benchmarking:

| Tool | Purpose |
|------|---------|
| `research_benchmark_run` | Run standardized benchmarks across models |
| `research_agent_benchmark` | Benchmark agent/tool-use capabilities |
| `research_multilingual_benchmark` | Multilingual capability assessment |

---

## HCS (Holistic Compliance Scoring)

### Compliance Framework (3 tools)

Structured compliance scoring and reporting:

| Tool | Purpose |
|------|---------|
| `research_hcs_score` | Calculate HCS compliance score (0-100) |
| `research_hcs_report` | Generate detailed HCS compliance report |
| `research_hcs_rubric` | HCS rubric categories and scoring details |

**HCS Categories:**
- Safety alignment
- Bias mitigation
- Transparency
- Robustness
- Interpretability
- Data handling
- User privacy

---

**New Total: 245+ tools**

---

---

## Not Yet Integrated — Potential Future Additions

### Dark Web Research Tools

| Repo | Stars | Description | Integration Path |
|------|-------|-------------|-----------------|
| [DedSecInside/TorBot](https://github.com/DedSecInside/TorBot) | 3.0K | OWASP Dark Web OSINT Tool — deep crawling, data extraction, link analysis | New provider: `torbot` — deeper than TorCrawl with recursive crawl + module system |
| [s-rah/onionscan](https://github.com/s-rah/onionscan) | 1.7K | Hidden service security scanner — finds misconfigurations, deanonymization vectors | New tool: `research_onion_audit` — security audit of .onion services |
| [smicallef/spiderfoot](https://github.com/smicallef/spiderfoot) | 13K | Automated OSINT with 200+ modules including dark web | New provider: `spiderfoot` — comprehensive OSINT aggregation |
| [Err0r-ICA/TORhunter](https://github.com/Err0r-ICA/TORhunter) | ~500 | Scan and exploit Tor hidden service vulnerabilities | New tool: `research_onion_vuln_scan` — hidden service vulnerability assessment |
| [octokami/darknet_forum](https://github.com/octokami/darknet_forum) | ~200 | Darknet forum scraping and analysis framework | Enhance `research_forum_cortex` with structured scraping patterns |

### Psychology & Behavioral Analysis Tools (Dark/Deep Web)

| Repo / Tool | Stars | Description | Integration Path |
|-------------|-------|-------------|-----------------|
| [jpotts18/stylometry](https://github.com/jpotts18/stylometry) | ~300 | Python stylometry library — author identification via writing patterns | New tool: `research_stylometry` — deanonymize dark web authors by linguistic fingerprint |
| [Fast Stylometry](https://github.com/fastdatascience/fast_stylometry) | ~100 | Fast stylometric analysis using Burrows' Delta | Integrate as engine for `research_stylometry` |
| [ritikamotwani/Deception-Detection](https://github.com/ritikamotwani/Deception-Detection) | ~50 | Detect deception through linguistic cues in text | New tool: `research_deception_detect` — flag deceptive claims in dark web markets |
| [areedmostafa/radicalization-detection-nlp](https://github.com/areedmostafa/radicalization-detection-nlp) | ~30 | Detect online extremism/radicalization using NLP | New tool: `research_radicalization_detect` — monitor forums for extremist content |
| [GWAS-stylometry](https://github.com/DDPronin/GWAS-stylometry) | ~20 | Research materials for stylometric analysis | Research reference for stylometry implementation |
| [OWASP SocialOSINTAgent](https://owasp.org/www-project-social-osint-agent/) | OWASP | LLM + vision models for social media footprint analysis | New tool: `research_persona_profile` — cross-platform persona reconstruction |

### Proposed Psychology-Focused Loom Tools

| Tool Name | Category | Description |
|-----------|----------|-------------|
| `research_stylometry` | Behavioral | Author fingerprinting via writing style analysis (word frequency, sentence structure, punctuation patterns, vocabulary richness). Compare anonymous dark web posts against known author corpora. |
| `research_persona_profile` | Behavioral | Cross-platform persona reconstruction combining linguistic style, posting patterns, timezone analysis, vocabulary, and topic preferences to build behavioral profiles. |
| `research_deception_detect` | Behavioral | Flag deceptive or fraudulent content using linguistic deception cues (hedging, distancing language, cognitive complexity shifts). Useful for dark web market reviews. |
| `research_radicalization_detect` | Behavioral | Monitor forum content for radicalization indicators using NLP classifiers (extremist vocabulary, us-vs-them framing, escalation patterns). |
| `research_sentiment_deep` | Behavioral | Deep sentiment and emotion analysis beyond positive/negative — detect fear, anger, urgency, manipulation in dark web forum posts. Uses multilingual LLM classification. |
| `research_network_persona` | Behavioral | Map social networks within dark web forums — who replies to whom, influence scores, community detection, central nodes. Graph-based behavioral analysis. |

### Key Research Papers

- **"Opensource intelligence and dark web user de-anonymisation"** — Academic framework for OSINT-based deanonymization ([academia.edu](https://www.academia.edu/99874786/))
- **"Adversarial stylometry"** — Techniques to evade and detect stylometric analysis ([academia.edu](https://www.academia.edu/105268087/))
- **"On Detecting Online Radicalization Using NLP"** — NLP approaches for radicalization detection ([academia.edu](https://www.academia.edu/70747932/))
- **"A survey on extremism analysis using NLP"** — Comprehensive survey of NLP methods for detecting extremist content ([Springer](https://link.springer.com/article/10.1007/s12652-021-03658-z))
- **Whonix Stylometry Guide** — Practical guide to deanonymization via writing style ([whonix.org](https://www.whonix.org/wiki/Stylometry))


---

### research_breach_check

Check email against known data breaches (HaveIBeenPwned k-anonymity).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| email | str | - | Email address to check |

**Returns:** `{"email": "...", "breaches_found": 0, "breaches": [...], "api_available": true}`
**Cost:** FREE (HIBP_API_KEY optional for full API)
**Rate Limit:** fetch 60/min

---

### research_cert_analyze

Extract SSL/TLS certificate details from a hostname.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| hostname | str | - | Domain or IP to check |
| port | int | `443` | TLS port |

**Returns:** `{"hostname": "...", "subject": {...}, "issuer": {...}, "not_after": "...", "days_until_expiry": 90, "is_expired": false}`
**Cost:** FREE
**Rate Limit:** fetch 60/min

---

### research_cve_lookup

Search CVE vulnerability database by keyword.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search keywords |
| limit | int | `10` | Max results |

**Returns:** `{"query": "...", "total_results": 5, "cves": [{"id": "CVE-2024-1234", "cvss": 7.5, "severity": "HIGH"}]}`
**Cost:** FREE (NVD public API, rate limited 5/30s)
**Rate Limit:** search 30/min

---

### research_cve_detail

Get detailed info for a specific CVE ID.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| cve_id | str | - | CVE identifier (e.g., CVE-2024-1234) |

**Returns:** `{"id": "...", "description": "...", "cvss": 7.5, "severity": "HIGH", "references": [...]}`
**Cost:** FREE
**Rate Limit:** fetch 60/min

---

### research_deception_detect

Detect deceptive or fraudulent content using linguistic cues.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to analyze (min 100 chars) |

**Returns:** `{"deception_score": 0.65, "verdict": "uncertain", "indicators": {...}, "red_flags": [...]}`
**Cost:** FREE (OPTIONAL_PAID for LLM enhancement)
**Rate Limit:** None

---

### research_dns_lookup

DNS record lookup for a domain.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| domain | str | - | Domain name |
| record_types | list[str] \| None | `["A","AAAA","MX","NS","TXT"]` | DNS record types |

**Returns:** `{"domain": "...", "records": {"A": ["1.2.3.4"], "MX": [...]}, "ip_addresses": [...]}`
**Cost:** FREE
**Rate Limit:** fetch 60/min

---

### research_exif_extract

Extract EXIF metadata and GPS coordinates from images.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url_or_path | str | - | Image URL or local path |

**Returns:** `{"source": "...", "format": "JPEG", "size": [1920,1080], "exif": {...}, "gps": {"latitude": 51.5, "longitude": -0.1}, "has_gps": true}`
**Cost:** FREE
**Rate Limit:** fetch 60/min

---

### research_geoip_local

Offline IP geolocation using MaxMind GeoLite2 database.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ip | str | - | IPv4 or IPv6 address |

**Returns:** `{"ip": "...", "country": "US", "city": "New York", "latitude": 40.7, "longitude": -74.0, "timezone": "America/New_York"}`
**Cost:** FREE (requires GeoLite2-City.mmdb)
**Rate Limit:** fetch 60/min

---

### research_ip_geolocation

IP geolocation via public API (ip-api.com).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ip | str | - | IPv4 or IPv6 address |

**Returns:** `{"ip": "...", "country": "US", "city": "...", "lat": 40.7, "lon": -74.0, "isp": "...", "org": "..."}`
**Cost:** FREE (ip-api.com, 45 req/min)
**Rate Limit:** fetch 60/min

---

### research_ip_reputation

Check IP reputation and abuse score.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ip | str | - | IPv4 or IPv6 address |

**Returns:** `{"ip": "...", "geolocation": {...}, "abuse_score": 25, "is_tor_exit": false, "reverse_dns": "..."}`
**Cost:** FREE (ABUSEIPDB_API_KEY optional for detailed scores)
**Rate Limit:** fetch 60/min


---

## Creative Research Tools (Extended)

### research_culture_dna

Analyze company culture from public signals including Glassdoor reviews, GitHub organization patterns, LinkedIn company pages, and job posting language.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| company | str | - | Company name (e.g., "Google", "Acme Corp") |
| domain | str | `""` | Optional company domain (e.g., "google.com") |

**Returns:**
```json
{
  "company": "Google",
  "domain": "google.com",
  "culture_signals": [
    {"source": "glassdoor", "category": "work_life_balance", "signal": "flexible work mentioned", "strength": 3}
  ],
  "work_life_score": 0.72,
  "innovation_score": 0.85,
  "diversity_signals": ["diversity commitment", "inclusion focus"],
  "overall_culture_type": "startup",
  "signal_count": 12,
  "github_analysis": {"repo_analysis": "...", "readme_analysis": "..."}
}
```

**Cost:** FREE (uses public web search)
**Rate Limit:** search 20/min, fetch 60/min

**Example Usage:**
```python
result = await research_culture_dna(
    company="Google",
    domain="google.com"
)
print(f"Culture type: {result['overall_culture_type']}")
print(f"Innovation score: {result['innovation_score']}")
```

---

### research_synth_echo

Test AI model consistency and alignment by sending the same question in 5 different phrasings and comparing response consistency, refusal patterns, and response time variance.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| model_name | str | - | Model identifier (e.g., "gpt-4", "claude-3-sonnet") |
| test_prompts | list[str] \| None | Standard suite | Optional custom test prompts |

**Returns:**
```json
{
  "model_name": "gpt-4",
  "consistency_score": 0.82,
  "refusal_consistency": 1.0,
  "response_time_variance": 0.234,
  "num_test_prompts": 5,
  "num_variations_per_prompt": 5,
  "total_api_calls": 25,
  "test_results": [
    {
      "prompt": "What is machine learning?",
      "num_variations": 5,
      "avg_similarity": 0.78,
      "response_time_variance": 0.145,
      "refusal_consistent": true,
      "refusal_count": 0,
      "semantic_hashes": ["abc12345", "abc12346", ...]
    }
  ],
  "alignment_assessment": "high"
}
```

**Cost:** VARIABLE (depends on target LLM API)
**Rate Limit:** 5 tests/hour per model

**Example Usage:**
```python
result = await research_synth_echo(
    model_name="claude-3-sonnet",
    test_prompts=["What is AI?", "Explain ML"]
)
print(f"Consistency: {result['consistency_score']:.2f}")
print(f"Alignment: {result['alignment_assessment']}")
```

---

### research_psycholinguistic

Analyze text for psycholinguistic patterns and threat indicators including emotional tone, deception cues, urgency markers, and cognitive complexity.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to analyze (min 10 chars) |
| author_name | str | `""` | Optional author identifier |

**Returns:**
```json
{
  "text_length": 284,
  "word_count": 42,
  "sentence_count": 5,
  "author_name": "Anonymous",
  "emotional_profile": {
    "positive_emotion_words": 2,
    "negative_emotion_words": 3,
    "emotion_ratio": -0.024,
    "overall_sentiment": "neutral"
  },
  "certainty_markers": {
    "certainty_words": 3,
    "uncertainty_words": 1,
    "certainty_ratio": 0.048
  },
  "cognitive_complexity_score": 0.54,
  "vocabulary_richness": 0.68,
  "avg_sentence_length": 8.4,
  "deception_indicators": ["excessive_detail"],
  "urgency_score": 0.35,
  "anger_indicators": {
    "anger_words": 1,
    "anger_score": 0.2
  },
  "threat_level": "low",
  "threat_indicators_summary": {
    "negative_emotions": false,
    "high_anger": false,
    "high_urgency": false,
    "deception_patterns": true
  }
}
```

**Cost:** FREE
**Rate Limit:** analyze 100/min

**Example Usage:**
```python
result = await research_psycholinguistic(
    text="This proposal requires urgent action or we'll lose market advantage.",
    author_name="Sales Manager"
)
print(f"Threat level: {result['threat_level']}")
print(f"Sentiment: {result['emotional_profile']['overall_sentiment']}")
print(f"Deception indicators: {result['deception_indicators']}")
```

**Threat Level Classification:**
- **Low:** Calm, balanced language with few emotional or pressure indicators
- **Medium:** Mixed indicators including some anger, urgency, or deception patterns
- **High:** Multiple threat signals including high anger, urgency, and deception cues

**Deception Pattern Indicators:**
- `lack_of_self_references` — Unusual absence of first-person pronouns
- `excessive_exaggeration` — Overuse of intensifiers (very, extremely, incredibly)
- `excessive_detail` — Unnecessary elaboration suggesting overcompensation
- `distancing_language` — Heavy use of "they/them" suggesting disassociation
- `opinion_hedging` — Excessive hedging phrases ("honestly", "to be honest")


---

## Memetic Virality Simulation

### research_memetic_simulate

Agent-based simulation of how ideas/strategies would spread through a virtual population. Tests viral potential before deployment by modeling population dynamics, susceptibility, connectivity, and skepticism.

**Purpose:** Pre-test virality potential of ideas, messaging strategies, social engineering campaigns, and memetic content before real-world deployment. Provides quantitative metrics (R0, reach %, peak infection) for decision-making.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `idea` | string | required | Description of idea/strategy to simulate (e.g., "Appeal to tribal identity", "Create urgency") |
| `population_size` | integer | 1000 | Size of virtual population (100-10000) |
| `generations` | integer | 50 | Number of simulation generations to run (10-500) |
| `mutation_rate` | float | 0.1 | Probability of message mutation per generation (0.0-1.0) |

**Returns:**

```json
{
  "idea": "Appeal to authority",
  "R0": 2.45,
  "virality_class": "moderate",
  "peak_infection_pct": 93.5,
  "peak_generation": 15,
  "total_reach_pct": 93.5,
  "spread_curve": [1.0, 3.5, 6.5, 16.0, 31.5, 45.0, 60.0, 70.5, 79.0, 82.5, ...],
  "mutations_survived": 4,
  "recommendation": "CONDITIONAL DEPLOYMENT. Idea shows moderate virality (R0=2.45) with 93.5% reach. Consider targeting high-connectivity nodes or amplification.",
  "simulation_timestamp": "2026-05-02T12:34:56.789012+00:00"
}
```

**Output Fields:**

- **idea**: Input idea description
- **R0**: Basic reproduction number (>3=viral, 1-3=moderate, <1=dying)
- **virality_class**: One of `"viral"`, `"moderate"`, or `"dying"` based on R0
- **peak_infection_pct**: Highest infection percentage reached (0-100)
- **peak_generation**: Generation number when peak was reached
- **total_reach_pct**: Final total population reached (0-100)
- **spread_curve**: List of infection percentages per generation (shows S-curve dynamics)
- **mutations_survived**: Count of beneficial mutations during spread
- **recommendation**: Deployment recommendation (HIGHLY RECOMMENDED / RECOMMENDED / CONDITIONAL / NOT RECOMMENDED)
- **simulation_timestamp**: ISO 8601 timestamp of simulation execution

**Simulation Model:**

The simulator uses agent-based modeling with the following components:

1. **Agent Traits** (randomly assigned):
   - **Susceptibility** (0-1): How easily influenced by the idea
   - **Connectivity** (1-20): Number of social connections in network
   - **Skepticism** (0-1): Resistance to new ideas

2. **Spread Mechanics**:
   - Formula: `spread_probability = (connectivity/20) × susceptibility × (1-skepticism) × idea_fitness`
   - Each infected agent attempts to spread to a random subset of their connections
   - Newly infected agents then become spreaders in next generation

3. **Mutations**:
   - Probability: specified `mutation_rate` per generation
   - Effect: Random variation in message fitness (±10% typically)
   - Beneficial mutations are naturally selected through spread dynamics

4. **Metrics**:
   - **R0**: Average reproduction number calculated from early exponential growth phase
   - **Spread Curve**: Infection percentage per generation (typically shows S-curve)
   - **Peak Generation**: Generation with maximum concurrent infections
   - **Total Reach**: Final percentage of population that ever got infected

**Virality Classification:**

- **Viral** (R0 > 3.0): Idea spreads exponentially, infects majority of population
- **Moderate** (1.0 < R0 ≤ 3.0): Steady spread, moderate reach
- **Dying** (R0 ≤ 1.0): Idea dies out, limited reach

**API Key:** None — free

**Computational Cost:** O(population_size × generations × avg_connectivity) — ~5-50ms for typical parameters

**Example Usage:**

```python
# Test virality of an authority-appeal strategy
result = await research_memetic_simulate(
    idea="Expert endorsement: leading researcher warns about emerging threat",
    population_size=2000,
    generations=40,
    mutation_rate=0.12
)

print(f"R0: {result['R0']}")  # 2.45
print(f"Class: {result['virality_class']}")  # "moderate"
print(f"Reach: {result['total_reach_pct']}%")  # 93.5%
print(result['recommendation'])  # Deployment guidance
```

**Advanced Use Cases:**

1. **Test multiple strategies**:
   ```python
   strategies = [
       "Appeal to authority",
       "Create artificial scarcity",
       "Appeal to in-group identity",
       "Use emotional language"
   ]
   
   results = {}
   for strategy in strategies:
       result = await research_memetic_simulate(strategy, population_size=1500)
       results[strategy] = result['R0']
   
   best = max(results, key=results.get)
   ```

2. **Population sensitivity analysis**:
   ```python
   # Test against highly skeptical population
   result = await research_memetic_simulate(
       idea="Your strategy here",
       population_size=500,
       mutations_rate=0.05  # Low mutation = less adaptation
   )
   ```

3. **Estimate amplification needs**:
   ```python
   result = await research_memetic_simulate(
       idea="Strategy without amplification",
       population_size=1000
   )
   
   if result['virality_class'] == 'dying':
       print("Need targeted amplification to target high-connectivity nodes")
   ```

**Limitations:**

- Assumes random network topology (not real social networks with clusters)
- Binary infected/not-infected model (doesn't model "partially convinced")
- No competitive ideas or opposing narratives
- No temporal effects or memory decay
- Connectivity fixed at creation (no dynamic network changes)

**Notes:**

- Smaller populations (100-500) show more variance in results due to stochastic effects
- Larger populations (5000+) show more stable, predictable curves
- High mutation rates (>0.3) can destabilize spread by degrading message quality
- Peak generation typically 30-70% through total generations

**See Also:**
- `research_prompt_reframe` — Generate multiple strategy variants
- `research_trend_predict` — Analyze real-world trend momentum
- `research_consensus_build` — Multi-model consensus on messaging
- `research_psychological` — Psycholinguistic analysis of message effectiveness

---

## Strategy Synthesis Tools

### research_meta_learn

META_LEARNER: Analyze patterns in successful vs. failed jailbreak strategies, then generate novel hybrid strategies through crossover and mutation. Uses heuristic-based synthesis without external LLM calls.

**Purpose:** Meta-learning over existing strategy registry (957 strategies) to discover new attack vectors combining structural features from successful approaches.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `successful_strategies` | list[str] \| None | None | List of strategy names that succeeded (empty = use registry fallback) |
| `failed_strategies` | list[str] \| None | None | List of strategy names that failed (for pattern analysis) |
| `target_model` | str | `"auto"` | Target model: `"auto"`, `"claude"`, `"gpt"`, `"gemini"`, `"deepseek"`, `"o1"` |
| `num_generate` | int | 5 | Number of new strategies to synthesize (1-20) |

**Returns:**
```json
{
  "generated_strategies": [
    {
      "name": "meta_hybrid_0_a1b2c3d4",
      "template": "[HYBRID STRUCTURE]\n...\n{prompt}",
      "predicted_effectiveness": 0.78,
      "novelty_score": 0.62,
      "parent_strategies": ["ethical_anchor", "scaffolded_layered_depth"],
      "structural_features": {
        "length": 945,
        "persona_count": 2,
        "authority_signals": 4,
        "encoding_used": false,
        "turns_needed": 3,
        "regulatory_language": true,
        "best_for": ["claude", "gpt", "gemini"]
      }
    }
  ],
  "analysis": {
    "success_patterns": {
      "avg_length": 850,
      "common_authority": [["claude", 15], ["gpt", 12], ["gemini", 10]],
      "uses_encoding": 0.35,
      "avg_turns": 2.3
    },
    "failure_patterns": {
      "too_long": 0.4,
      "missing_authority": 0.25,
      "regulatory_heavy": 0.15
    },
    "model_biases": {
      "target": "auto",
      "match_confidence": 0.72
    }
  },
  "recommendations": [
    "Favor templates 800-1200 chars for best effectiveness",
    "Include 2-3 authority signals (framework/mandate/credentials)",
    "Avoid >2000 char templates; complexity doesn't scale",
    "Regulatory language helps for gpt/gemini; less effective for deepseek"
  ]
}
```

**Cost:** FREE (no API calls, local strategy registry analysis)

**Rate Limit:** generate 10 synthesis runs/min

**Feature Extraction Logic:**

Analyzes 6 structural dimensions per strategy:
- **Length:** Template character count (optimal 800-1200)
- **Persona count:** Number of `{role}` and `{professional}` placeholders
- **Authority signals:** Occurrences of "authority", "framework", "mandate" (target 2-4)
- **Encoding used:** Boolean detection of obfuscation keywords
- **Turns needed:** Conversation depth (newline-separated sections)
- **Regulatory language:** Detection of GDPR, Article, compliance keywords

**Hybrid Generation Process:**

1. **Crossover:** Select 2 parent strategies from success set
2. **Splice:** Combine first 400 chars of P1 + middle 400 chars of P2
3. **Mutation:** Insert `[HYBRID INSERT]` marker between segments
4. **Scoring:**
   - **Novelty:** Jaccard distance from parent templates (0-1)
   - **Effectiveness:** Base 0.65 + length bonus (0.15 if <1500) + failure pattern mitigation (0.2 if missing_authority > 50%)

**Model-Specific Optimizations:**

- **Claude/Gemini:** Boost effectiveness if regulatory language present
- **GPT/DeepSeek:** Favor compact templates (<1000 chars)
- **O1:** Favor reasoning-chain templates with high turn count

**Example Usage:**

```python
result = await research_meta_learn(
    successful_strategies=["ethical_anchor", "scaffolded_layered_depth", "cognitive_wedge"],
    failed_strategies=["simple_direct", "minimal_request"],
    target_model="claude",
    num_generate=5
)

# Review generated strategies
for strategy in result["generated_strategies"]:
    print(f"{strategy['name']}: {strategy['predicted_effectiveness']:.2f} effectiveness, {strategy['novelty_score']:.2f} novelty")
    print(f"Parents: {', '.join(strategy['parent_strategies'])}")
    print()

# Review success patterns
print(f"Success pattern avg_length: {result['analysis']['success_patterns']['avg_length']}")
print(f"Recommendations: {', '.join(result['recommendations'])}")
```

**Use Cases:**

1. **Adaptive Jailbreak Discovery** — Feed recent success/failure logs to discover emerging attack patterns
2. **Model-Specific Optimization** — Generate novel strategies for emerging models (o1, Grok, etc.)
3. **Strategy Evolution Tracking** — Monitor how hybrid effectiveness changes over model updates
4. **Defensive Benchmarking** — Generate novel attacks to stress-test safety filters

---
