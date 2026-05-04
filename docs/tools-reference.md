---
title: Loom MCP Tools Reference
---

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
- **Pipeline & Composition** (2 tools) — tool orchestration and pipeline DSL
- **Routing & Intelligence** (1 tool) — semantic tool matching
- **Verification** (2 tools) — cross-source fact verification and batch verification
- **Forecasting** (1 tool) — trend analysis via term frequency evolution
- **Reporting** (1 tool) — multi-stage intelligence report generation
- **Optimization** (1 tool) — prompt compression for cost reduction
- **Security** (1 tool) — security hardening audit
- **Monitoring & Quotas** (6 tools) — quota status, latency reports, DLQ stats, webhooks
- **Source Reputation** (1 tool) — URL reputation scoring
- **Backends** (3 tools) — Maigret, Harvest, SpiderFoot OSINT backends

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
  "synthesized_answer": "Transformers are neural network architectures...",
  "sources": [...],
  "confidence": 0.89,
  "estimated_cost_usd": 0.12
}
```

**API Key:** None (but LLM providers required: GROQ_API_KEY, NVIDIA_NIM_API_KEY, etc.)

**Example Usage:**

```python
result = await research_deep(
    query="What are the latest advances in retrieval-augmented generation?",
    depth=3,
    include_github=True,
    synthesize=True,
    max_cost_usd=0.50
)
print(result["synthesized_answer"])
```

---

## Pipeline & Composition Tools

### research_compose

Execute a composed pipeline of research tools using a declarative DSL syntax.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `pipeline` | string | required | Pipeline DSL string (e.g., `"search($) \| fetch($.urls[0]) \| markdown($)"`) |
| `initial_input` | string | `""` | Initial input value for first step |
| `continue_on_error` | boolean | `false` | Continue on step failure (default False = stop) |
| `timeout_ms` | integer | `null` | Optional timeout in milliseconds |

**Returns:**

```json
{
  "success": true,
  "output": "final result from last step",
  "steps": [
    {"tool_name": "search", "args": ["$"], "parallel_group": 0},
    {"tool_name": "fetch", "args": ["$.urls[0]"], "parallel_group": 0}
  ],
  "errors": [],
  "execution_time_ms": 1234.5,
  "step_results": [...]
}
```

**API Key:** None — free (depends on tools used)

**DSL Syntax Examples:**
- Sequential: `"tool1(arg) | tool2($)"`
- Parallel then merge: `"tool1($) & tool2($) | merge($)"`
- Field access: `"search($) | fetch($.urls[0]) | markdown($)"`
- Aliases: `"deep_research"`, `"osint_sweep"`, `"code_search"`

**Example Usage:**

```python
result = await research_compose(
    pipeline="search(python machine learning) | fetch($.urls[:3]) | markdown($) | llm_summarize($)",
    continue_on_error=False,
    timeout_ms=30000
)
print(f"Success: {result['success']}, Time: {result['execution_time_ms']}ms")
```

---

### research_compose_validate

Validate pipeline syntax without executing.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `pipeline` | string | required | Pipeline DSL string |

**Returns:**

```json
{
  "valid": true,
  "steps": [
    {"tool_name": "search", "args": ["$"], "parallel_group": 0}
  ],
  "errors": [],
  "expanded_pipeline": "expanded DSL string"
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_compose_validate(
    pipeline="search($) | fetch($.urls[0])"
)
if result["valid"]:
    print("Pipeline syntax valid")
else:
    print(f"Errors: {result['errors']}")
```

---

## Routing & Intelligence Tools

### research_semantic_route

Route query to optimal tools via semantic embeddings (sentence-transformers or TF-IDF fallback).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | string | required | Query or research intent |
| `top_k` | integer | 5 | Number of top tools to return (1-10) |

**Returns:**

```json
{
  "query": "Find information about Python async/await",
  "tools": [
    {
      "tool_name": "research_github",
      "score": 0.94,
      "reason": "High relevance for code examples"
    },
    {
      "tool_name": "research_search",
      "score": 0.89,
      "reason": "General search capability"
    }
  ],
  "top_k": 5,
  "method": "sentence-transformers"
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_semantic_route(
    query="Find breach databases and exposed credentials",
    top_k=5
)
for tool in result["tools"]:
    print(f"{tool['tool_name']}: {tool['score']:.2f}")
```

---

## Verification Tools

### research_fact_verify

Verify a claim across multiple sources via cross-source agreement analysis.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `claim` | string | required | Claim to verify (5-500 characters) |
| `sources` | integer | 3 | Number of search results per provider (1-20) |
| `min_confidence` | float | 0.6 | Minimum confidence threshold (0.0-1.0) |

**Returns:**

```json
{
  "claim": "Python 3.12 released in October 2023",
  "verdict": "supported",
  "confidence": 0.92,
  "supporting_sources": [
    {"url": "https://python.org/...", "evidence": "...", "title": "..."}
  ],
  "contradicting_sources": [],
  "evidence_summary": "3 sources confirm the claim...",
  "total_sources_analyzed": 9,
  "error": null
}
```

**Verdict Options:**
- `"supported"` — 3+ sources agree claim is true
- `"contradicted"` — 3+ sources refute claim
- `"mixed"` — conflicting evidence
- `"unverified"` — insufficient evidence

**API Key:** None — free (uses research_search internally)

**Example Usage:**

```python
result = await research_fact_verify(
    claim="ChatGPT was released by OpenAI in November 2022",
    sources=5,
    min_confidence=0.7
)
print(f"Verdict: {result['verdict']} (confidence: {result['confidence']})")
```

---

### research_batch_verify

Batch fact verification of multiple claims in parallel.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `claims` | list[string] | required | List of claims to verify (max 50 claims) |
| `sources` | integer | 3 | Number of search results per provider (1-20) |
| `min_confidence` | float | 0.6 | Minimum confidence threshold (0.0-1.0) |

**Returns:**

```json
{
  "results": [
    {
      "claim": "Claim 1",
      "verdict": "supported",
      "confidence": 0.92,
      "supporting_sources": [...],
      "contradicting_sources": [...]
    }
  ],
  "summary": {
    "total_claims": 3,
    "supported": 2,
    "contradicted": 0,
    "mixed": 1,
    "unverified": 0
  },
  "execution_time_ms": 5432.1
}
```

**API Key:** None — free (uses research_search internally)

**Example Usage:**

```python
results = await research_batch_verify(
    claims=[
        "Python was released in 1991",
        "React was created by Facebook",
        "Kubernetes is an orchestration platform"
    ],
    sources=3
)
for item in results["results"]:
    print(f"{item['claim']}: {item['verdict']}")
```

---

## Forecasting Tools

### research_trend_forecast

Analyze research directions via term frequency evolution to predict emerging trends.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | Research topic to analyze |
| `time_window_weeks` | integer | 4 | Number of weeks to analyze for recent vs older terms |
| `min_frequency` | integer | 2 | Minimum term frequency to consider |
| `limit` | integer | 20 | Maximum terms to return per category |

**Returns:**

```json
{
  "topic": "artificial intelligence",
  "emerging_terms": [
    {"term": "multimodal", "growth_rate": 0.82},
    {"term": "retrieval-augmented", "growth_rate": 0.76}
  ],
  "declining_terms": [
    {"term": "LSTM", "decline_rate": -0.45}
  ],
  "stable_terms": [
    {"term": "transformer", "stability": 0.95}
  ],
  "forecast": "Multimodal and retrieval-augmented approaches are rapidly gaining traction...",
  "confidence": 0.78,
  "time_window_weeks": 4
}
```

**API Key:** None — free (uses research_search internally)

**Example Usage:**

```python
result = await research_trend_forecast(
    topic="quantum computing applications",
    time_window_weeks=8,
    limit=15
)
print(f"Emerging: {result['emerging_terms']}")
print(f"Forecast: {result['forecast']}")
```

---

## Reporting Tools

### research_generate_report

Generate structured intelligence reports combining search, fetch, and synthesis.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | Research topic or question |
| `depth` | string | `"standard"` | Report depth: `"brief"` (1 page), `"standard"` (3-5 pages), `"comprehensive"` (10+ pages) |
| `format` | string | `"markdown"` | Output format: `"markdown"`, `"json"`, `"html"` |
| `search_provider` | string | `null` | Search provider (auto-selected if null) |
| `num_sources` | integer | `null` | Number of sources (auto-scaled by depth) |
| `include_methodology` | boolean | `true` | Include methodology section |
| `include_recommendations` | boolean | `true` | Include recommendations section |

**Returns:**

```json
{
  "title": "AI Safety Alignment: Current State and Challenges",
  "report": "# AI Safety Alignment\n\n## Executive Summary\n...",
  "sections": [
    {"title": "Executive Summary", "content": "..."},
    {"title": "Methodology", "content": "..."}
  ],
  "sources_used": 5,
  "confidence": 0.87,
  "generated_at": "2026-05-04T10:30:00Z",
  "word_count": 2847,
  "depth": "standard",
  "format": "markdown"
}
```

**API Key:** None — free (uses research_search and research_fetch internally)

**Example Usage:**

```python
result = await research_generate_report(
    topic="Zero-Trust Security Architecture",
    depth="comprehensive",
    format="markdown",
    include_recommendations=True
)
with open("report.md", "w") as f:
    f.write(result["report"])
```

---

## Optimization Tools

### research_compress_prompt

Compress prompt text to reduce token consumption while preserving meaning using LLMLingua 2.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `text` | string | required | Input text to compress (non-empty) |
| `target_ratio` | float | 0.5 | Target compression ratio (0.1-0.9) |

**Returns:**

```json
{
  "original_tokens": 5432,
  "compressed_tokens": 2716,
  "ratio": 0.50,
  "compressed_text": "Alice was born in 1990. She studied physics at MIT...",
  "method": "llmlingua",
  "reduction_percent": 50
}
```

**API Key:** None — free

**Compression Ratios:**
- `0.3` — aggressive (30% of original, high information loss)
- `0.5` — balanced (50% of original, good fidelity)
- `0.7` — conservative (70% of original, minimal loss)
- `0.9` — minimal (90% of original, best fidelity)

**Example Usage:**

```python
result = await research_compress_prompt(
    text="Long technical specification text here...",
    target_ratio=0.5
)
print(f"Saved {result['reduction_percent']}% tokens: {result['original_tokens']} -> {result['compressed_tokens']}")
```

---

## Security Tools

### research_security_audit

Run 15 security checks and return pass/fail report on hardening status.

**Parameters:** None

**Returns:**

```json
{
  "score": 87,
  "passed": 13,
  "failed": 2,
  "checks": [
    {"name": "auth_enabled", "status": "pass", "detail": "..."},
    {"name": "api_keys_set", "status": "pass", "detail": "..."},
    {"name": "no_debug_mode", "status": "fail", "detail": "Debug mode should be off in production"}
  ]
}
```

**Checks Include:**
- Authentication enabled
- API keys configured
- Debug mode off
- Redis password required
- PostgreSQL SSL enabled
- Rate limiting active
- PII scrubbing active
- Circuit breakers for cascading failures
- SSRF protection
- Input validation
- Audit logging
- Content sanitization
- Quota tracking
- Financial operation idempotency

**API Key:** None — free

**Example Usage:**

```python
result = await research_security_audit()
print(f"Security Score: {result['score']}%")
for check in result["checks"]:
    if check["status"] == "fail":
        print(f"FAIL: {check['name']} - {check['detail']}")
```

---

## Monitoring & Quota Tools

### research_quota_status

Get API quota usage and remaining limits for free-tier LLM providers (Groq, NVIDIA NIM, Gemini).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `provider` | string | `null` | Optional provider name (groq, nvidia_nim, gemini). If null, returns all. |

**Returns (single provider):**

```json
{
  "timestamp_utc": "2026-05-04T15:30:45Z",
  "provider": "groq",
  "minute_requests": 12,
  "minute_limit": 30,
  "day_requests": 245,
  "day_limit": 10000,
  "minute_tokens": 45000,
  "minute_token_limit": 120000,
  "day_tokens": 892000,
  "day_token_limit": 3000000,
  "is_near_limit": false,
  "should_fallback": false
}
```

**Returns (all providers):**

```json
{
  "timestamp_utc": "2026-05-04T15:30:45Z",
  "providers": {
    "groq": {...},
    "nvidia_nim": {...},
    "gemini": {...}
  },
  "summary": {
    "all_providers_healthy": true,
    "providers_near_limit": [],
    "providers_exhausted": []
  }
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_quota_status(provider="groq")
if result["should_fallback"]:
    print("Groq quota exhausted, switching provider...")
else:
    print(f"Groq: {result['minute_requests']}/{result['minute_limit']} requests/min")
```

---

### research_latency_report

Get latency statistics for one tool or all tools (percentiles, sample count, average, min, max).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `tool_name` | string | `""` | Specific tool name (e.g., 'research_fetch'). If empty, returns all tools. |

**Returns (single tool):**

```json
{
  "tool": "research_fetch",
  "stats": {
    "count": 342,
    "avg_ms": 487.3,
    "min_ms": 120,
    "max_ms": 8932,
    "p50": 420,
    "p75": 650,
    "p90": 1200,
    "p95": 1850,
    "p99": 4200
  },
  "is_slow": true,
  "slow_warning": "p95 exceeds 1000ms"
}
```

**Returns (all tools):**

```json
{
  "total_tools_tracked": 154,
  "total_tools_with_data": 98,
  "tools": [
    {
      "tool_name": "research_fetch",
      "stats": {...}
    }
  ],
  "slow_tools": [...],
  "slow_count": 5,
  "slow_threshold_ms": 1000
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_latency_report()
for tool in result["slow_tools"]:
    print(f"Slow tool: {tool['tool_name']} (p95: {tool['stats']['p95']}ms)")
```

---

### research_dlq_stats

Get deadletter queue statistics for monitoring tool reliability.

**Parameters:** None

**Returns:**

```json
{
  "status": "success",
  "stats": {
    "pending": 12,
    "failed": 3,
    "total_retried": 45,
    "avg_retry_count": 2.3,
    "oldest_pending": "2026-05-04T08:30:00Z"
  },
  "message": "DLQ has 12 pending and 3 failed items"
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_dlq_stats()
print(f"Pending retries: {result['stats']['pending']}")
print(f"Failed items: {result['stats']['failed']}")
```

---

### research_webhook_register

Register a new webhook for Loom tool events.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | Webhook URL (http:// or https://) |
| `events` | list[string] | required | Events to subscribe to |
| `secret` | string | `null` | HMAC secret (auto-generated if null) |

**Supported Events:**
- `"tool.completed"` — tool finishes successfully
- `"tool.failed"` — tool execution fails
- `"job.queued"` — job is queued
- `"job.finished"` — job finishes
- `"alert.error"` — error detected

**Returns:**

```json
{
  "webhook_id": "wh_abc123def456",
  "url": "https://example.com/webhook",
  "events": ["tool.completed", "tool.failed"],
  "secret": "whsec_abc123...",
  "created_at": "2026-05-04T10:30:00Z",
  "active": true
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_webhook_register(
    url="https://myapp.com/loom-webhook",
    events=["tool.completed", "tool.failed"]
)
print(f"Webhook registered: {result['webhook_id']}")
print(f"Secret: {result['secret']}")  # Store this securely!
```

---

### research_webhook_list

List all registered webhooks without revealing secrets.

**Parameters:** None

**Returns:**

```json
{
  "webhooks": [
    {
      "webhook_id": "wh_abc123",
      "url": "https://example.com/webhook",
      "events": ["tool.completed"],
      "secret": "***abc...",
      "created_at": "2026-05-04T10:30:00Z",
      "last_triggered": "2026-05-04T15:45:00Z",
      "success_count": 42,
      "failure_count": 2,
      "active": true
    }
  ],
  "total": 1,
  "supported_events": ["alert.error", "job.finished", "job.queued", "tool.completed", "tool.failed"]
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_webhook_list()
print(f"Total webhooks: {result['total']}")
for wh in result["webhooks"]:
    print(f"{wh['webhook_id']}: {wh['url']}")
```

---

### research_webhook_unregister

Unregister a webhook.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `webhook_id` | string | required | ID of webhook to unregister |

**Returns:**

```json
{
  "success": true,
  "webhook_id": "wh_abc123",
  "message": "Webhook unregistered successfully"
}
```

**API Key:** None — free

**Example Usage:**

```python
result = await research_webhook_unregister(webhook_id="wh_abc123")
if result["success"]:
    print(f"Unregistered {result['webhook_id']}")
```

---

## Source Reputation Tools

### research_source_reputation

Score a URL's source reputation on scale of 0-100.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | string | required | URL to score |

**Returns:**

```json
{
  "url": "https://arxiv.org/abs/2401.00001",
  "domain": "arxiv.org",
  "reputation_score": 95,
  "blocked": false,
  "high_quality": true,
  "risk_level": "low"
}
```

**Reputation Scoring:**
- 0 (blocked/spam)
- 10-20 (suspicious TLDs like .tk, .buzz)
- 30 (unknown/risky)
- 50 (generic .com/.net)
- 70 (.org domains)
- 85-95 (academic, high-quality)
- 95-100 (verified high-quality sources like arxiv.org, github.com, MIT.edu)

**API Key:** None — free

**Example Usage:**

```python
result = await research_source_reputation(url="https://arxiv.org/abs/2401.00001")
print(f"Reputation: {result['reputation_score']}/100")
print(f"High quality: {result['high_quality']}")
```

---

## LLM Circuit Status Tool

### research_circuit_status

Get health status of LLM provider circuit breakers and fallback cascade state.

**Parameters:** None

**Returns:**

```json
{
  "timestamp": "2026-05-04T15:30:45Z",
  "providers": {
    "groq": {
      "state": "closed",
      "failure_count": 0,
      "last_failure": null,
      "health": "healthy"
    },
    "nvidia_nim": {
      "state": "open",
      "failure_count": 5,
      "last_failure": "2026-05-04T15:25:00Z",
      "health": "degraded"
    }
  },
  "cascade_order": ["groq", "nvidia_nim", "deepseek", "gemini", "moonshot", "openai", "anthropic", "vllm"],
  "active_provider": "groq"
}
```

**Circuit States:**
- `"closed"` — healthy, accepting requests
- `"open"` — failed too many times, skipped
- `"half_open"` — recovering, allowing one attempt

**API Key:** None — free

**Example Usage:**

```python
result = await research_circuit_status()
for provider, info in result["providers"].items():
    print(f"{provider}: {info['state']} ({info['health']})")
```

---

## Overview Summary

| Category | Tool Count | Cost |
|----------|-----------|------|
| Core Research | 4 | Free |
| Pipeline & Composition | 2 | Free |
| Routing & Intelligence | 1 | Free |
| Verification | 2 | Free |
| Forecasting | 1 | Free |
| Reporting | 1 | Free |
| Optimization | 1 | Free |
| Security | 1 | Free |
| Monitoring & Quotas | 6 | Free |
| Source Reputation | 1 | Free |
| LLM Management | 1 | Free |

**Total New Tools This Session: 21**

All new tools integrate seamlessly with existing Loom infrastructure and follow established patterns for error handling, logging, and performance monitoring.
