# Loom MCP Research Server — Complete Help Guide

Loom is a comprehensive research orchestration system with 42+ tools, 9 search providers, intelligent provider cascading, and a 12-stage deep research pipeline.

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/loom
cd loom
pip install -e ".[dev]"

# Or with optional browser tools
pip install -e ".[dev,browsers]"
```

### Configuration

Create `~/.loom/config.json` or set environment variables:

```json
{
  "DEFAULT_SEARCH_PROVIDER": "exa",
  "SPIDER_CONCURRENCY": 5,
  "EXTERNAL_TIMEOUT_SECS": 30,
  "CACHE_TTL_DAYS": 30,
  "LLM_CASCADE_ORDER": ["nvidia", "openai", "anthropic", "vllm"],
  "LLM_DAILY_COST_CAP_USD": 10.0,
  "RESEARCH_MAX_COST_USD": 0.50,
  "RESEARCH_EXPAND_QUERIES": true,
  "RESEARCH_EXTRACT": true,
  "RESEARCH_SYNTHESIZE": true,
  "RESEARCH_GITHUB_ENRICHMENT": true
}
```

### API Keys (via environment)

```bash
export EXA_API_KEY="..."
export TAVILY_API_KEY="..."
export FIRECRAWL_API_KEY="..."
export BRAVE_API_KEY="..."
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export NVIDIA_NIM_API_KEY="..."
export GITHUB_TOKEN="..."
```

### Start the Server

```bash
loom-server

# Or from source
python -m loom.server

# Verify on localhost:8787
curl http://127.0.0.1:8787/mcp/status
```

---

## Tool Catalog (42+ Tools)

### Core Search & Fetch (8 tools)

#### research_search
**Multi-provider web search with auto-routing**

Parameters:
- `query` (required, string): search query
- `provider` (optional, string): exa|tavily|firecrawl|brave|ddgs|arxiv|wikipedia|hackernews|reddit
- `n` (optional, int, default 10): max results (1-50)
- `include_domains` (optional, list): restrict to these domains
- `exclude_domains` (optional, list): exclude these domains
- `start_date` (optional, string): ISO yyyy-mm-dd start date
- `end_date` (optional, string): ISO yyyy-mm-dd end date
- `language` (optional, string): language hint (ISO 639-1)
- `provider_config` (optional, dict): provider-specific kwargs

Returns:
```json
{
  "provider": "exa",
  "query": "...",
  "results": [
    {
      "url": "...",
      "title": "...",
      "snippet": "...",
      "score": 0.95,
      "published_date": "2026-04-24"
    }
  ]
}
```

API key needed: **Depends on provider** (see Search Providers Guide)

Example:
```python
result = research_search(
    query="latest transformer architectures 2026",
    provider="exa",
    n=10
)
```

---

#### research_fetch
**Single URL retrieval with HTTP, stealthy, and dynamic modes**

Parameters:
- `url` (required, string): target URL
- `mode` (optional, string, default "stealthy"): http|stealthy|dynamic
- `max_chars` (optional, int): max response size (default 50000, max 200000)
- `solve_cloudflare` (optional, bool, default true): attempt CF bypass
- `headers` (optional, dict): custom HTTP headers
- `user_agent` (optional, string): override User-Agent
- `proxy` (optional, string): proxy URL
- `cookies` (optional, dict): cookies dict
- `accept_language` (optional, string): Accept-Language header
- `wait_for` (optional, string): CSS selector to wait for (dynamic mode)
- `return_format` (optional, string): text|json|html
- `timeout` (optional, int): per-call timeout in seconds
- `bypass_cache` (optional, bool): force refetch

Returns:
```json
{
  "url": "...",
  "status_code": 200,
  "content_type": "text/html",
  "title": "...",
  "text": "...",
  "html": "...",
  "json": {...},
  "screenshot": "base64_encoded_image",
  "tool": "scrapling.stealthy",
  "elapsed_ms": 2500
}
```

API key needed: **Free** (uses Scrapling internally)

Example:
```python
# HTTP mode (fast, open pages)
result = research_fetch(
    url="https://example.com",
    mode="http",
    max_chars=50000
)

# Stealthy mode (anti-bot)
result = research_fetch(
    url="https://protected-site.com",
    mode="stealthy"
)

# Dynamic mode (JavaScript)
result = research_fetch(
    url="https://spa-app.com",
    mode="dynamic",
    wait_for=".results"
)
```

---

#### research_spider
**Parallel bulk URL fetching with bounded concurrency**

Parameters:
- `urls` (required, list): list of URLs to fetch
- `mode` (optional, string, default "stealthy"): http|stealthy|dynamic
- `max_chars_each` (optional, int, default 5000): max chars per URL
- `concurrency` (optional, int, default 5): concurrent fetches (1-20)
- `fail_fast` (optional, bool): stop on first error
- `dedupe` (optional, bool, default true): remove duplicate URLs
- `order` (optional, string): result ordering (input|domain|size)
- `solve_cloudflare` (optional, bool, default true): attempt CF bypass
- `headers` (optional, dict): custom headers
- `user_agent` (optional, string): override UA
- `proxy` (optional, string): proxy URL
- `cookies` (optional, dict): cookies dict
- `accept_language` (optional, string): Accept-Language header
- `timeout` (optional, int): per-fetch timeout override

Returns:
```json
[
  {
    "url": "...",
    "status_code": 200,
    "title": "...",
    "text": "...",
    "tool": "scrapling.stealthy",
    "elapsed_ms": 1500
  },
  ...
]
```

API key needed: **Free**

Example:
```python
results = research_spider(
    urls=[
        "https://site1.com",
        "https://site2.com",
        "https://site3.com"
    ],
    mode="stealthy",
    concurrency=5,
    max_chars_each=10000
)
```

---

#### research_markdown
**LLM-ready markdown extraction via Crawl4AI**

Parameters:
- `url` (required, string): target URL
- `bypass_cache` (optional, bool): force refetch
- `css_selector` (optional, string): extract CSS subtree
- `js_before_scrape` (optional, string): JavaScript to execute
- `screenshot` (optional, bool): capture screenshot
- `remove_selectors` (optional, list): CSS selectors to remove
- `headers` (optional, dict): custom headers
- `user_agent` (optional, string): override UA
- `proxy` (optional, string): proxy URL
- `cookies` (optional, dict): cookies dict
- `accept_language` (optional, string): Accept-Language header
- `timeout` (optional, int): per-call timeout
- `extract_selector` (optional, string): alias for css_selector
- `wait_for` (optional, string): CSS selector to wait for

Returns:
```json
{
  "url": "...",
  "title": "...",
  "markdown": "# Heading\n\nContent...",
  "tool": "crawl4ai",
  "fetched_at": "2026-04-24T12:34:56Z"
}
```

API key needed: **Free**

Example:
```python
result = research_markdown(
    url="https://example.com",
    css_selector=".main-content",
    remove_selectors=["nav", ".sidebar"],
    screenshot=False
)
```

---

#### research_github
**GitHub API search for repos, code, and issues**

Parameters:
- `kind` (required, string): repo|code|issues
- `query` (required, string): GitHub search query
- `sort` (optional, string, default "stars"): sort field
- `order` (optional, string, default "desc"): asc|desc
- `limit` (optional, int, default 20): max results (1-100)
- `language` (optional, string): programming language filter
- `owner` (optional, string): repository owner
- `repo` (optional, string): repository name

Returns:
```json
{
  "kind": "repo",
  "query": "...",
  "total_count": 1250,
  "results": [
    {
      "name": "user/repo",
      "url": "https://github.com/...",
      "description": "...",
      "stars": 5200,
      "forks": 320,
      "language": "Python",
      "updated_at": "2026-04-20T..."
    }
  ]
}
```

API key needed: **Free** (optional GITHUB_TOKEN for higher rate limits)

Example:
```python
result = research_github(
    kind="repo",
    query="pytorch attention implementation",
    language="python",
    sort="stars",
    limit=10
)
```

---

#### research_github_readme
**Extract README content from GitHub repository**

Parameters:
- `repo` (required, string): repository in format "owner/name"

Returns:
```json
{
  "repo": "torch/pytorch",
  "readme": "# PyTorch\n...",
  "stars": 78000,
  "language": "C++",
  "description": "..."
}
```

API key needed: **Free**

Example:
```python
result = research_github_readme(repo="torch/pytorch")
```

---

#### research_github_releases
**List releases and tags from a GitHub repository**

Parameters:
- `repo` (required, string): repository in format "owner/name"
- `limit` (optional, int, default 10): max releases

Returns:
```json
{
  "repo": "owner/name",
  "releases": [
    {
      "tag": "v1.0.0",
      "name": "Release 1.0.0",
      "url": "https://github.com/...",
      "created_at": "2026-01-15T...",
      "assets": [...]
    }
  ]
}
```

API key needed: **Free**

---

### Deep Research Pipeline (1 tool)

#### research_deep
**Full 12-stage orchestrated research with all tools**

Parameters:
- `query` (required, string): search query
- `depth` (optional, int, default 2): result volume scaling (1-10)
- `include_domains` (optional, list): restrict domains
- `exclude_domains` (optional, list): exclude domains
- `start_date` (optional, string): ISO yyyy-mm-dd
- `end_date` (optional, string): ISO yyyy-mm-dd
- `language` (optional, string): language hint
- `provider_config` (optional, dict): provider-specific kwargs
- `search_providers` (optional, list): providers to use (default from config)
- `expand_queries` (optional, bool, default true): Stage 1
- `extract` (optional, bool, default true): Stage 5 LLM extract
- `synthesize` (optional, bool, default true): Stage 12 synthesis
- `include_github` (optional, bool, default true): Stage 7
- `include_community` (optional, bool, default false): Stage 9
- `include_red_team` (optional, bool, default false): Stage 10
- `include_misinfo_check` (optional, bool, default false): Stage 11
- `max_cost_usd` (optional, float): total cost cap

Returns:
```json
{
  "query": "Machine Learning for healthcare 2026",
  "search_variations": ["...", "..."],
  "providers_used": ["exa", "arxiv"],
  "pages_searched": 45,
  "pages_fetched": 28,
  "top_pages": [...],
  "synthesis": "...",
  "github_repos": [...],
  "total_cost_usd": 0.32,
  "elapsed_ms": 125000,
  "stages_completed": [1, 2, 3, 4, 5, 6, 7, 12]
}
```

API key needed: **Depends on search providers and LLM cascade**

Example:
```python
result = research_deep(
    query="Machine Learning for healthcare 2026",
    depth=2,
    expand_queries=True,
    extract=True,
    synthesize=True,
    include_github=True,
    max_cost_usd=0.50
)
```

---

### LLM Tools (8 tools)

#### research_llm_summarize
**Summarize long text into bullets, paragraphs, or key points**

Parameters:
- `text` (required, string): text to summarize
- `style` (optional, string): bullet_points|paragraphs|key_points (default "bullet_points")
- `max_length` (optional, int, default 500): max summary length
- `max_cost_usd` (optional, float): cost cap

Returns:
```json
{
  "text": "...",
  "summary": "...",
  "provider": "nvidia",
  "model": "meta/llama-4-maverick-17b-128e-instruct",
  "cost_usd": 0.002
}
```

API key needed: **Free** (vLLM cascade), or requires OpenAI/Anthropic/NVIDIA NIM

Example:
```python
result = research_llm_summarize(
    text="...(long document)...",
    style="bullet_points",
    max_length=500
)
```

---

#### research_llm_extract
**Extract structured data from text using a schema**

Parameters:
- `text` (required, string): text to extract from
- `schema` (required, dict): JSON schema for extraction
- `max_cost_usd` (optional, float): cost cap

Returns:
```json
{
  "extracted": {
    "author": "...",
    "date": "...",
    "key_claims": ["...", "..."]
  },
  "provider": "nvidia",
  "cost_usd": 0.003
}
```

API key needed: **Free/Paid** (provider dependent)

Example:
```python
result = research_llm_extract(
    text="...",
    schema={
        "author": "str",
        "date": "str",
        "key_claims": ["str"]
    }
)
```

---

#### research_llm_classify
**Classify text into predefined categories**

Parameters:
- `text` (required, string): text to classify
- `categories` (required, list): list of possible categories
- `max_cost_usd` (optional, float): cost cap

Returns:
```json
{
  "text": "...",
  "category": "category_name",
  "confidence": 0.92,
  "provider": "nvidia",
  "cost_usd": 0.001
}
```

API key needed: **Free/Paid**

---

#### research_llm_translate
**Translate text to target language**

Parameters:
- `text` (required, string): text to translate
- `target_language` (required, string): target language name or ISO 639-1 code
- `source_language` (optional, string): source language (auto-detect if not provided)
- `max_cost_usd` (optional, float): cost cap

Returns:
```json
{
  "original": "...",
  "translated": "...",
  "source_language": "fr",
  "target_language": "en",
  "provider": "nvidia",
  "cost_usd": 0.001
}
```

API key needed: **Free/Paid**

Example:
```python
result = research_llm_translate(
    text="Bonjour le monde",
    target_language="en"
)
```

---

#### research_llm_query_expand
**Generate query variations for broader search coverage**

Parameters:
- `query` (required, string): original query
- `n` (optional, int, default 3): number of variations
- `max_cost_usd` (optional, float): cost cap

Returns:
```json
{
  "original_query": "...",
  "expanded_queries": ["...", "...", "..."],
  "provider": "nvidia",
  "cost_usd": 0.002
}
```

API key needed: **Free/Paid**

---

#### research_llm_answer
**Generate an answer to a query using LLM**

Parameters:
- `query` (required, string): question
- `context` (optional, string): background context
- `style` (optional, string): brief|detailed|academic
- `max_tokens` (optional, int, default 500): max response length
- `max_cost_usd` (optional, float): cost cap

Returns:
```json
{
  "query": "...",
  "answer": "...",
  "provider": "nvidia",
  "model": "meta/llama-4-maverick-17b-128e-instruct",
  "cost_usd": 0.003
}
```

API key needed: **Free/Paid**

---

#### research_llm_embed
**Generate semantic embeddings for text (768-dim vectors)**

Parameters:
- `text` (required, string): text to embed
- `model` (optional, string): embedding model (default "nvidia/nv-embed-v2")

Returns:
```json
{
  "text": "...",
  "embedding": [0.123, 0.456, ...],  // 768 dimensions
  "model": "nvidia/nv-embed-v2",
  "dimension": 768
}
```

API key needed: **Free** (via NVIDIA NIM)

Example:
```python
result = research_llm_embed(
    text="machine learning is cool",
    model="nvidia/nv-embed-v2"
)
# Returns: 768-dim vector
```

---

#### research_llm_chat
**Raw chat API for conversational LLM interaction**

Parameters:
- `messages` (required, list): conversation history
- `max_tokens` (optional, int, default 500): max response length
- `temperature` (optional, float, default 0.7): 0.0-1.0
- `max_cost_usd` (optional, float): cost cap

Returns:
```json
{
  "text": "...",
  "provider": "nvidia",
  "model": "meta/llama-4-maverick-17b-128e-instruct",
  "cost_usd": 0.002
}
```

API key needed: **Free/Paid**

---

### Stealth & Browser Tools (2 tools)

#### research_camoufox
**Camoufox anti-detection browser (Firefox-based)**

Parameters:
- `url` (required, string): URL to fetch
- `session` (optional, string): session name (unused)
- `screenshot` (optional, bool): capture screenshot
- `timeout` (optional, int, default 120): operation timeout

Returns:
```json
{
  "url": "...",
  "title": "...",
  "html": "...",
  "text": "...",
  "screenshot": "base64_encoded_image",
  "tool": "camoufox"
}
```

API key needed: **Free** (requires camoufox package)

Example:
```python
result = research_camoufox(
    url="https://site-with-bot-detection.com",
    screenshot=True
)
```

---

#### research_botasaurus
**Botasaurus stealth browser (Chrome-based, second escalation)**

Parameters:
- `url` (required, string): URL to fetch
- `session` (optional, string): session name (unused)
- `screenshot` (optional, bool): capture screenshot
- `timeout` (optional, int): operation timeout

Returns:
```json
{
  "url": "...",
  "title": "...",
  "text": "...",
  "tool": "botasaurus"
}
```

API key needed: **Free** (requires botasaurus package)

---

### Content Enrichment (2 tools)

#### research_detect_language
**Language detection (free, 55+ languages)**

Parameters:
- `text` (required, string): text to analyze (min 10 chars)

Returns:
```json
{
  "language": "en",
  "confidence": 0.95,
  "alternatives": [
    {"lang": "en", "prob": 0.95},
    {"lang": "fr", "prob": 0.03}
  ]
}
```

API key needed: **Free** (no API key required)

---

#### research_wayback
**Wayback Machine archived versions (free)**

Parameters:
- `url` (required, string): original URL
- `limit` (optional, int, default 1): max snapshots

Returns:
```json
{
  "original_url": "...",
  "snapshots": [
    {
      "timestamp": "20260420120000",
      "archive_url": "https://web.archive.org/web/20260420120000/...",
      "status_code": 200,
      "mimetype": "text/html"
    }
  ]
}
```

API key needed: **Free**

---

### Expert Discovery (1 tool)

#### research_find_experts
**Discover thought leaders on a topic**

Parameters:
- `query` (required, string): topic
- `n` (optional, int, default 5): max experts

Returns:
```json
{
  "query": "AI Safety",
  "experts": [
    {
      "name": "expert_name",
      "sources": ["github", "arxiv"],
      "repos": [{"name": "...", "stars": 1200, "url": "..."}],
      "papers": [{"title": "...", "url": "...", "date": "..."}],
      "mentions": 5
    }
  ]
}
```

API key needed: **Free**

---

### Creative Research Tools (11 tools)

#### research_red_team
**Generate and search for counter-arguments to claims**

Parameters:
- `claim` (required, string): claim to challenge
- `n_counter` (optional, int, default 3): counter-arguments
- `max_cost_usd` (optional, float, default 0.10): LLM cost cap

Returns:
```json
{
  "claim": "...",
  "counter_arguments": [
    {
      "counter_claim": "...",
      "evidence_found": 5,
      "sources": [{"title": "...", "url": "..."}]
    }
  ],
  "total_cost_usd": 0.05
}
```

API key needed: **Paid** (requires LLM + search)

---

#### research_multilingual
**Cross-lingual search for information arbitrage**

Parameters:
- `query` (required, string): query in any language
- `languages` (optional, list): ISO codes (default [ar, es, de, zh, ru])
- `n_per_lang` (optional, int, default 3): results per language
- `max_cost_usd` (optional, float, default 0.10): cost cap

Returns:
```json
{
  "query": "...",
  "per_language_results": {
    "ar": [...],
    "es": [...],
    "de": [...]
  },
  "overlap_analysis": {...}
}
```

API key needed: **Paid** (requires translation)

---

#### research_consensus
**Multi-engine voting and consensus scoring**

Parameters:
- `query` (required, string): query
- `providers` (optional, list): providers to vote (default all)
- `n_per_provider` (optional, int): results per provider

Returns:
```json
{
  "query": "...",
  "consensus_results": [
    {
      "url": "...",
      "title": "...",
      "consensus_score": 0.85,
      "voted_by": ["exa", "tavily", "brave"]
    }
  ]
}
```

API key needed: **Depends on providers**

---

#### research_misinfo_check
**Fact-checking against known false claims**

Parameters:
- `claims` (required, list): claims to verify

Returns:
```json
{
  "claims": [...],
  "verdicts": [
    {
      "claim": "...",
      "verdict": "true|false|mixed|unverifiable",
      "confidence": 0.92,
      "evidence": [{"source": "...", "snippet": "..."}]
    }
  ]
}
```

API key needed: **Free/Paid**

---

#### research_temporal_diff
**Wayback Machine content comparison over time**

Parameters:
- `url` (required, string): URL to track
- `snapshots` (optional, int, default 2): number to compare

Returns:
```json
{
  "url": "...",
  "changes": [
    {
      "from_date": "2026-01-15",
      "to_date": "2026-04-20",
      "added": "...",
      "removed": "...",
      "modified": "..."
    }
  ]
}
```

API key needed: **Free**

---

#### research_citation_graph
**Academic citation network traversal**

Parameters:
- `paper_id` (required, string): arXiv or Semantic Scholar ID
- `direction` (optional, string): forward|backward (default backward)
- `depth` (optional, int, default 1): traversal depth

Returns:
```json
{
  "paper_id": "...",
  "title": "...",
  "citations": [
    {
      "id": "...",
      "title": "...",
      "authors": [...],
      "year": 2026
    }
  ]
}
```

API key needed: **Free** (Semantic Scholar)

---

#### research_ai_detect
**Detect AI-generated content in text**

Parameters:
- `text` (required, string): text to analyze
- `threshold` (optional, float, default 0.5): confidence threshold

Returns:
```json
{
  "text": "...",
  "is_ai_generated": true,
  "confidence": 0.87,
  "indicators": ["repetitive patterns", "lack of nuance"]
}
```

API key needed: **Free/Paid**

---

#### research_curriculum
**ELI5-to-PhD learning path generator**

Parameters:
- `topic` (required, string): topic
- `start_level` (optional, string): eli5|beginner|intermediate|advanced|phd

Returns:
```json
{
  "topic": "Transformers",
  "path": [
    {
      "level": "eli5",
      "title": "What are Transformers?",
      "description": "...",
      "resources": [...]
    },
    {
      "level": "beginner",
      "title": "Transformer Basics",
      ...
    }
  ]
}
```

API key needed: **Free/Paid** (LLM)

---

#### research_community_sentiment
**HN + Reddit practitioner sentiment analysis**

Parameters:
- `topic` (required, string): topic
- `include_comments` (optional, bool, default true): include discussion

Returns:
```json
{
  "topic": "OpenAI's latest model",
  "overall_sentiment": 0.72,
  "posts": [
    {
      "title": "...",
      "score": 450,
      "sentiment": 0.85,
      "url": "..."
    }
  ],
  "trending_claims": [...]
}
```

API key needed: **Free**

---

#### research_wiki_ghost
**Wikipedia talk pages and edit history mining**

Parameters:
- `article` (required, string): article title
- `include_edits` (optional, bool, default true): include edit history

Returns:
```json
{
  "article": "...",
  "talk_page_discussions": [...],
  "edit_history": [
    {
      "date": "2026-04-20",
      "editor": "...",
      "change": "..."
    }
  ]
}
```

API key needed: **Free**

---

#### research_semantic_sitemap
**Hierarchical page clustering by semantic similarity**

Parameters:
- `urls` (required, list): URLs to cluster
- `max_depth` (optional, int, default 3): clustering depth

Returns:
```json
{
  "clusters": [
    {
      "theme": "Machine Learning Basics",
      "urls": [...],
      "subtopics": [...]
    }
  ]
}
```

API key needed: **Free/Paid** (embeddings)

---

### YouTube & Media (1 tool)

#### fetch_youtube_transcript
**Extract auto-generated subtitles from YouTube (free)**

Parameters:
- `url` (required, string): YouTube video URL
- `language` (optional, string, default "en"): subtitle language code

Returns:
```json
{
  "url": "https://youtube.com/watch?v=...",
  "title": "Video Title",
  "transcript": "00:00:00 Speaker: This is...",
  "duration": 3600
}
```

API key needed: **Free** (requires yt-dlp)

Example:
```python
result = fetch_youtube_transcript(
    url="https://youtube.com/watch?v=dQw4w9WgXcQ",
    language="en"
)
```

---

### Session Management (3 tools)

#### research_session_open
**Create persistent browser context with optional login**

Parameters:
- `name` (required, string): unique session name
- `browser` (optional, string): camoufox|chromium|firefox (default camoufox)
- `ttl_seconds` (optional, int, default 3600): time-to-live
- `login_url` (optional, string): URL to navigate after opening
- `login_script` (optional, string): JavaScript to run for login

Returns:
```json
{
  "name": "authenticated_session",
  "status": "open",
  "browser": "camoufox",
  "created_at": "2026-04-24T12:34:56Z",
  "ttl_seconds": 3600
}
```

API key needed: **Free**

Example:
```python
result = research_session_open(
    name="authenticated_session",
    browser="camoufox",
    login_url="https://example.com/login",
    login_script="document.getElementById('username').value='user'; ...",
    ttl_seconds=3600
)
```

---

#### research_session_list
**List active browser sessions**

Parameters: (none)

Returns:
```json
{
  "sessions": [
    {
      "name": "authenticated_session",
      "browser": "camoufox",
      "created_at": "2026-04-24T12:34:56Z",
      "last_used": "2026-04-24T13:00:00Z",
      "ttl_seconds": 3600
    }
  ],
  "count": 1
}
```

API key needed: **Free**

Example:
```python
sessions = research_session_list()
```

---

#### research_session_close
**Close and cleanup browser session**

Parameters:
- `name` (required, string): session name to close

Returns:
```json
{
  "name": "authenticated_session",
  "status": "closed",
  "message": "Session cleaned up"
}
```

API key needed: **Free**

---

### Cache Management (2 tools)

#### research_cache_stats
**View cache statistics and disk usage**

Parameters: (none)

Returns:
```json
{
  "size_mb": 125.5,
  "entry_count": 1245,
  "oldest": "2026-03-25T10:00:00Z",
  "newest": "2026-04-24T14:30:00Z",
  "cache_dir": "/home/user/.cache/loom"
}
```

API key needed: **Free**

Example:
```python
stats = research_cache_stats()
```

---

#### research_cache_clear
**Remove cache entries older than N days**

Parameters:
- `older_than_days` (optional, int): days threshold (default from CACHE_TTL_DAYS config)

Returns:
```json
{
  "deleted_count": 342,
  "freed_mb": 45.3
}
```

API key needed: **Free**

Example:
```python
result = research_cache_clear(older_than_days=30)
```

---

### Configuration (2 tools)

#### research_config_get
**Read current configuration**

Parameters:
- `key` (optional, string): specific config key (returns all if not provided)

Returns:
```json
{
  "SPIDER_CONCURRENCY": 5,
  "EXTERNAL_TIMEOUT_SECS": 30,
  "DEFAULT_SEARCH_PROVIDER": "exa",
  ...
}
```

API key needed: **Free**

---

#### research_config_set
**Validated update to configuration**

Parameters:
- `key` (required, string): config key
- `value` (required, any): new value

Returns:
```json
{
  "key": "SPIDER_CONCURRENCY",
  "old_value": 5,
  "new_value": 10,
  "persisted_at": "2026-04-24T12:34:56Z"
}
```

API key needed: **Free**

---

## Search Providers Guide (9 Providers)

### 1. Exa (Recommended for semantic search)
- **Cost**: Paid ($1 per 10,000 requests for basic)
- **Best for**: Semantic/AI-native search, code/technical queries, general web
- **Date range**: Supported (start_date, end_date)
- **Domain filtering**: Supported (include_domains, exclude_domains)
- **Rate limit**: 100 req/min (paid tier)
- **Signup**: https://exa.ai

### 2. Tavily (Recommended for agents)
- **Cost**: Free tier (100 queries/month), Paid ($10/month and up)
- **Best for**: Agent-native search, real-time data, includes LLM answer synthesis
- **Date range**: Not supported
- **Domain filtering**: Supported (include_domains, exclude_domains)
- **Rate limit**: 120 req/min (free tier)
- **Signup**: https://tavily.com

### 3. Firecrawl (Web intelligence)
- **Cost**: Paid ($10/month basic, $100/month pro)
- **Best for**: Deep scraping, crawling, full page content extraction
- **Date range**: Not supported
- **Domain filtering**: Client-side only
- **Rate limit**: 10,000 credits/month
- **Signup**: https://www.firecrawl.dev

### 4. Brave (Privacy-focused search)
- **Cost**: Paid ($10/month)
- **Best for**: Privacy-respecting search, news results, general web
- **Date range**: Not supported
- **Domain filtering**: Not supported (client-side)
- **Rate limit**: 20 results per request (free tier capped)
- **Signup**: https://api.search.brave.com

### 5. DuckDuckGo/DDGS (Free general search)
- **Cost**: Free (no API key)
- **Best for**: Quick searches, news, fallback when API keys exhausted
- **Date range**: Supported (timelimit: d|w|m|y)
- **Domain filtering**: Client-side
- **Rate limit**: Soft limits
- **Signup**: None (uses ddgs Python library)

### 6. arXiv (Academic papers)
- **Cost**: Free (no API key)
- **Best for**: Academic papers, research, preprints
- **Date range**: Not directly supported
- **Domain filtering**: N/A (papers only)
- **Rate limit**: 3 requests/second
- **Signup**: None (uses arxiv Python library)

### 7. Wikipedia (Encyclopedic knowledge)
- **Cost**: Free (no API key)
- **Best for**: Definitions, overviews, background context
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Soft limits
- **Signup**: None (uses MediaWiki REST API)

### 8. HackerNews (Tech community)
- **Cost**: Free (no API key)
- **Best for**: Tech news, discussion sentiment, trending topics
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Soft limits
- **Signup**: None (built-in provider)

### 9. Reddit (Community discussion)
- **Cost**: Free (no API key, but Reddit scraping is discouraged)
- **Best for**: Community sentiment, user discussions
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Dependent on Reddit's robots.txt
- **Signup**: None (built-in provider)

---

## LLM Tools Guide (8 Tools with Cascade)

All LLM tools support provider cascading in this order: **nvidia → openai → anthropic → vllm**

### Input/Output Format

**Input**:
- All text-based (strings or lists of strings)
- No binary data
- UTF-8 encoding assumed

**Output**:
```json
{
  "text": "response text",
  "provider": "nvidia|openai|anthropic|vllm",
  "model": "model_id",
  "cost_usd": 0.002,
  "tokens": {"input": 100, "output": 50}
}
```

### Cost Estimates (USD per 1000 tokens)

| Provider | Model | Input | Output |
|----------|-------|-------|--------|
| NVIDIA NIM | llama-4-maverick-17b | $0.0001 | $0.0002 |
| OpenAI | gpt-4-turbo | $0.01 | $0.03 |
| Anthropic | claude-3-sonnet | $0.003 | $0.015 |
| vLLM (local) | any | $0.00 | $0.00 |

### Cascade Behavior

1. Attempts first provider in LLM_CASCADE_ORDER
2. On API error/timeout, moves to next provider
3. Repeats until success or all providers exhausted
4. Returns error if all fail
5. Cost is cumulative across all attempted providers

---

## Creative Research Tools Guide (11 Tools)

These tools implement advanced research strategies combining multiple APIs:

### research_red_team
- Generates 3-N counter-arguments using LLM
- Searches for evidence supporting each counter-claim
- Returns weaknesses in original thesis
- Cost: ~$0.05-0.10 per call

### research_multilingual
- Translates query to 5 languages (ar, es, de, zh, ru)
- Searches each language region independently
- Highlights information gaps by region
- Useful for: Global product research, multilingual bias analysis
- Cost: ~$0.10-0.20 per call

### research_consensus
- Queries multiple providers (exa, tavily, brave, ddgs)
- Votes results by URL (normalized)
- Returns consensus-ranked results
- Useful for: Fact verification, consensus signals
- Cost: Aggregate of all providers

### research_misinfo_check
- Verifies claims against fact-checking databases
- Returns verdicts: true|false|mixed|unverifiable
- Provides evidence snippets for each
- Useful for: Claim validation, misinformation detection
- Cost: Free to $0.10

### research_temporal_diff
- Compares Wayback Machine snapshots over time
- Highlights added/removed/modified content
- Useful for: Tracking website changes, historical analysis
- Cost: Free

### research_citation_graph
- Traverses arXiv/Semantic Scholar citation networks
- Forward references (who cites this) or backward (what does this cite)
- Returns full citation metadata
- Useful for: Literature reviews, tracing research lineages
- Cost: Free (Semantic Scholar)

### research_ai_detect
- Analyzes text for AI generation patterns
- Returns confidence score + indicators
- Useful for: Content authenticity, bot detection
- Cost: Free to $0.05

### research_curriculum
- Generates learning path from ELI5 to PhD
- Each level has: title, description, resources
- Useful for: Onboarding research, knowledge mapping
- Cost: $0.05-0.20 per path

### research_community_sentiment
- Scrapes HN + Reddit for topic discussion
- Aggregates sentiment scores
- Returns trending claims from community
- Useful for: Product sentiment, trend detection
- Cost: Free (scraping)

### research_wiki_ghost
- Mines Wikipedia talk pages and edit history
- Shows discussion context for contentious topics
- Useful for: Understanding debate/consensus on topics
- Cost: Free

### research_semantic_sitemap
- Clusters URLs by semantic similarity
- Returns hierarchical topic structure
- Useful for: Website organization, content mapping
- Cost: $0.01-0.05 (embeddings)

---

## Research Workflows (8 Common Recipes)

### Workflow 1: Quick Fact Check (5-10 seconds, <$0.05)
```
1. research_search(query, provider="tavily", n=5)
2. research_spider(top_5_urls, mode="http", max_chars_each=2000)
3. research_llm_extract(results, schema={key_facts})
4. Done
```

**When to use**: Rapid verification, time-sensitive queries

---

### Workflow 2: In-Depth Research Report (5 minutes, ~$0.50)
```
1. research_deep(
     query=query,
     depth=2,
     include_github=True,
     expand_queries=True
   )
2. Stages auto-run:
   - Stage 1: Query expansion (3 variants)
   - Stage 2: Auto-detect academic/code/knowledge
   - Stage 3: Multi-provider search
   - Stage 4-6: Parallel fetch + markdown + extract
   - Stage 7: GitHub enrichment
   - Stage 12: Synthesis with citations
3. Done
```

**When to use**: Comprehensive research, reports, presentations

---

### Workflow 3: Academic Literature Review (10-15 minutes, ~$0.30)
```
1. research_deep(
     query=query,
     search_providers=["arxiv"],
     depth=3,
     expand_queries=True
   )
2. For top 10 papers:
   - research_citation_graph(paper_id, direction="backward")
3. research_llm_summarize(all_abstracts, style="bullet_points")
4. research_consensus(main_finding) # verify key claims
5. Output: Structured literature map
```

**When to use**: Academic research, grant proposals, surveys

---

### Workflow 4: Code/Library Evaluation (5-10 minutes, ~$0.40)
```
1. research_deep(
     query="library_name comparison AND github",
     search_providers=["exa", "github"],
     include_github=True
   )
2. For each top repo:
   - research_github_readme(repo)
   - research_github_releases(repo, limit=5)
3. research_llm_extract(
     text=readmes+releases,
     schema={version, features, maturity}
   )
4. research_consensus([top_urls]) # github stars + downloads
5. Output: Feature matrix, maturity assessment
```

**When to use**: Technology selection, library evaluation

---

### Workflow 5: Competitive Analysis (15-20 minutes, ~$0.60)
```
1. research_multilingual(
     query="competitor_name features",
     languages=["en", "es", "de", "fr"]
   )
2. research_community_sentiment(competitor_name)
3. research_red_team(claim="competitor_x is best at y")
4. research_consensus([competitor_urls])
5. research_llm_extract(
     all_results,
     schema={features: [], pricing: {}, reviews: []}
   )
6. Output: Competitive intelligence matrix
```

**When to use**: Market research, product positioning

---

### Workflow 6: Fact-Checking with Verification (8-12 minutes, ~$0.50)
```
1. research_deep(
     query=claim,
     include_red_team=True,
     include_misinfo_check=True
   )
2. Stages:
   - Stage 10: research_red_team(claim)
   - Stage 11: research_misinfo_check([extracted_claims])
3. research_wayback(top_source_url, limit=3) # historical context
4. Output: Verified claim with confidence score
```

**When to use**: Fact-checking, claim verification, journalism

---

### Workflow 7: Expert Discovery & Outreach (10 minutes, ~$0.20)
```
1. research_find_experts(topic, n=10)
2. For each expert:
   - research_spider([expert_websites], mode="stealthy")
3. research_llm_embed(expert_bios)
4. Cluster by topic using embeddings
5. Rank by: papers + repos + mentions
6. Output: Expert roster with contact info
```

**When to use**: Thought leader research, expert interviews, advisory boards

---

### Workflow 8: Multilingual Global Research (15-20 minutes, ~$0.80)
```
1. research_multilingual(
     query=query,
     languages=["ar", "es", "de", "zh", "ru", "ja"]
   )
2. For each language:
   - research_detect_language(top_snippets)
   - research_llm_translate(non_english, target_language="en")
3. research_consensus(deduplicated_urls)
4. Highlight regional info gaps
5. Output: Global perspective with attribution by region
```

**When to use**: International markets, multilingual products, global events

---

## 12-Stage Pipeline Reference

The `research_deep` tool orchestrates these stages:

| Stage | Name | Tool | Optional |
|-------|------|------|----------|
| 1 | Query Expansion | research_llm_query_expand | expand_queries=True |
| 2 | Type Detection | Auto-detect (internal) | - |
| 3 | Multi-Provider Search | research_search (parallelized) | - |
| 4 | URL Deduplication | Internal dedup | - |
| 5 | Content Extraction | research_llm_extract | extract=True |
| 6 | Markdown Processing | research_markdown | - |
| 7 | GitHub Enrichment | research_github | include_github=True |
| 8 | Language Detection | research_detect_language | - |
| 9 | Community Sentiment | research_community_sentiment | include_community=True |
| 10 | Red Team Analysis | research_red_team | include_red_team=True |
| 11 | Misinformation Check | research_misinfo_check | include_misinfo_check=True |
| 12 | Answer Synthesis | research_llm_answer | synthesize=True |

---

## Configuration Reference (24 Config Keys)

### Scraping (4 keys)
```json
{
  "SPIDER_CONCURRENCY": 5,           // 1-20, default 5
  "EXTERNAL_TIMEOUT_SECS": 30,       // 5-120, default 30
  "MAX_CHARS_HARD_CAP": 200000,      // 1k-2M, default 200k
  "MAX_SPIDER_URLS": 100             // 1-500, default 100
}
```

### Cache (1 key)
```json
{
  "CACHE_TTL_DAYS": 30               // 1-365, default 30
}
```

### Search (2 keys)
```json
{
  "DEFAULT_SEARCH_PROVIDER": "exa",  // exa|tavily|firecrawl|brave|ddgs|arxiv|wikipedia
  "DEFAULT_ACCEPT_LANGUAGE": "en-US,en;q=0.9,ar;q=0.8"
}
```

### Logging (1 key)
```json
{
  "LOG_LEVEL": "INFO"                // DEBUG|INFO|WARNING|ERROR
}
```

### LLM (4 keys)
```json
{
  "LLM_DEFAULT_CHAT_MODEL": "meta/llama-4-maverick-17b-128e-instruct",
  "LLM_DEFAULT_EMBED_MODEL": "nvidia/nv-embed-v2",
  "LLM_DEFAULT_TRANSLATE_MODEL": "moonshotai/kimi-k2-instruct",
  "LLM_MAX_PARALLEL": 12,            // 1-64, default 12
  "LLM_DAILY_COST_CAP_USD": 10.0,    // 0-1000, default 10
  "LLM_CASCADE_ORDER": ["nvidia", "openai", "anthropic", "vllm"]
}
```

### Research Pipeline (6 keys)
```json
{
  "RESEARCH_SEARCH_PROVIDERS": ["exa", "brave"],
  "RESEARCH_EXPAND_QUERIES": true,
  "RESEARCH_EXTRACT": true,
  "RESEARCH_SYNTHESIZE": true,
  "RESEARCH_GITHUB_ENRICHMENT": true,
  "RESEARCH_MAX_COST_USD": 0.50,    // 0-10, default 0.50
  
  // Advanced (off by default)
  "RESEARCH_COMMUNITY_SENTIMENT": false,
  "RESEARCH_RED_TEAM": false,
  "RESEARCH_MISINFO_CHECK": false
}
```

### Fetch (1 key)
```json
{
  "FETCH_AUTO_ESCALATE": true        // auto escalate on failure
}
```

---

## API Keys Reference (8 Keys)

| Key | Service | Cost | Signup URL | Used By |
|-----|---------|------|-----------|---------|
| EXA_API_KEY | Exa | $1/10k req | https://exa.ai | research_search (exa) |
| TAVILY_API_KEY | Tavily | Free (100/mo) | https://tavily.com | research_search (tavily) |
| FIRECRAWL_API_KEY | Firecrawl | $10+/mo | https://www.firecrawl.dev | research_search (firecrawl) |
| BRAVE_API_KEY | Brave Search | $10/mo | https://api.search.brave.com | research_search (brave) |
| OPENAI_API_KEY | OpenAI | $0.01-0.03/1k tokens | https://platform.openai.com | LLM tools (cascade) |
| ANTHROPIC_API_KEY | Anthropic | $0.003-0.015/1k tokens | https://console.anthropic.com | LLM tools (cascade) |
| NVIDIA_NIM_API_KEY | NVIDIA NIM | $0.0001-0.0002/1k tokens | https://build.nvidia.com/nim | LLM tools (cascade) |
| GITHUB_TOKEN | GitHub | Free (optional) | https://github.com/settings/tokens | research_github (higher rate limits) |

**Note**: DDGS, arXiv, Wikipedia, HackerNews, Reddit require no API keys (free/open).

---

## Troubleshooting

### Issue: "SSRF Error: host resolves to blocked address"
**Cause**: URL resolves to private IP (127.0.0.1, 10.x.x.x, 192.168.x.x, etc.)

**Solution**:
```bash
# Verify URL is public-facing
ping example.com

# Check it doesn't resolve locally
nslookup example.com

# Whitelist if needed (contact admin)
```

---

### Issue: "Cost cap exceeded"
**Cause**: LLM spending hit RESEARCH_MAX_COST_USD or daily limit

**Solution**:
```python
# Reduce per-call cap
research_deep(query, max_cost_usd=0.10)

# Or disable expensive stages
research_config_set("RESEARCH_RED_TEAM", False)
research_config_set("RESEARCH_MISINFO_CHECK", False)
research_config_set("RESEARCH_EXTRACT", False)

# Check daily spending
research_cache_stats()  # Check cost logs in ~/.cache/loom/logs/
```

---

### Issue: "Fetch timeout after 30s"
**Cause**: Page took >30s to load or escalation chain failed

**Solution**:
```python
# Increase timeout
research_config_set("EXTERNAL_TIMEOUT_SECS", 60)

# Or use manual fetch with escalation
result = research_fetch(url, mode="stealthy", timeout=120)

# Or try browser-based fetch
result = research_camoufox(url, timeout=180)
```

---

### Issue: "Missing API key for provider X"
**Cause**: Provider API key not set in environment

**Solution**:
```bash
# Set key
export EXA_API_KEY="sk-..."

# Verify
echo $EXA_API_KEY

# Or use fallback provider
research_config_set("DEFAULT_SEARCH_PROVIDER", "tavily")
```

---

### Issue: "Cache growing too large (>1GB)"
**Cause**: Cache TTL not enforced or disabled

**Solution**:
```python
# Clear old entries
research_cache_clear(older_than_days=7)

# Reduce TTL
research_config_set("CACHE_TTL_DAYS", 7)

# Check usage
stats = research_cache_stats()
print(f"Cache: {stats['size_mb']} MB, {stats['entry_count']} entries")
```

---

### Issue: "research_deep returns empty answer"
**Cause**: No search results or extraction failed

**Solution**:
```python
# 1. Check query is specific
query = "specific query with details not 'general info'"

# 2. Verify search provider has API key
import os
assert os.environ.get("EXA_API_KEY"), "EXA_API_KEY not set"

# 3. Try manual search + fetch
results = research_search(query, provider="exa", n=10)
print(f"Found {len(results['results'])} results")

for r in results['results'][:3]:
    text = research_fetch(r['url'], mode="stealthy")
    print(f"Fetched {len(text['text'])} chars from {r['url']}")

# 4. Enable debug logging
research_config_set("LOG_LEVEL", "DEBUG")

# 5. Check logs
# tail -f ~/.cache/loom/loom.log
```

---

### Issue: "Session expired" on research_spider
**Cause**: Browser session TTL exceeded (default 1 hour)

**Solution**:
```python
# Increase session TTL
research_session_open(name="my_session", ttl_seconds=7200)

# Keep session alive with periodic access
research_session_list()  # Refreshes last_used timestamp

# Or use ephemeral sessions (no session needed)
research_spider(urls, mode="dynamic")  # Creates temp browser
```

---

### Issue: "Stealth mode detected as bot"
**Cause**: Site uses advanced bot detection; Camoufox rejected

**Solution**:
```python
# 1. Try Chrome-based stealth (second escalation)
result = research_botasaurus(url)

# 2. Add custom headers (referer, user-agent)
result = research_fetch(
    url,
    mode="dynamic",
    headers={"Referer": "https://google.com/search?q=..."}
)

# 3. Use authenticated session (if possible)
research_session_open(name="auth", login_url="https://site.com/login")
# Then use fetch with session

# 4. Report to Camoufox/Scrapling with details
# https://github.com/astromild/camoufox/issues
```

---

### Issue: "Provider returned 0 results"
**Cause**: Query too broad, provider out of API quota, or no matches

**Solution**:
```python
# 1. Make query more specific
research_search(
    query="pytorch attention layer implementation 2026 github",
    provider="exa"
)

# 2. Try different provider
result = research_search(query, provider="tavily")

# 3. Check provider API quota
# Log in to provider dashboard (exa.ai, tavily.com, etc.)

# 4. Use fallback to free provider
result = research_search(query, provider="ddgs")  # free
```

---

### Issue: "LLM cost cap exceeded mid-research"
**Cause**: LLM pipeline exceeded per-call or daily limit

**Solution**:
```python
# 1. Disable expensive stages
result = research_deep(
    query,
    expand_queries=False,  # Skip stage 1
    extract=False,         # Skip stage 5
    synthesize=False,      # Skip stage 12
    include_github=False   # Skip stage 7
)

# 2. Switch to free LLM tier (vLLM)
research_config_set("LLM_CASCADE_ORDER", ["vllm"])

# 3. Increase cost cap (if budget allows)
research_config_set("LLM_DAILY_COST_CAP_USD", 50.0)

# 4. Check cost logs
# Check ~/.cache/loom/logs/llm_cost_*.json for daily spending
```

---

### Issue: "research_multilingual not translating"
**Cause**: Translation LLM not configured or API keys missing

**Solution**:
```python
# 1. Verify translate model is set
config = research_config_get()
print(config["LLM_DEFAULT_TRANSLATE_MODEL"])

# 2. Ensure LLM cascade keys are set
import os
assert os.environ.get("NVIDIA_NIM_API_KEY") or os.environ.get("OPENAI_API_KEY")

# 3. Try explicit translate tool
result = research_llm_translate(
    text="Bonjour le monde",
    target_language="en"
)
```

---

## Performance Tips

1. **Use caching**: Same query within TTL = cache hit (0ms)
2. **Set provider explicitly**: Avoid auto-detection overhead
3. **Parallel spider**: Increase SPIDER_CONCURRENCY if network permits (1-20)
4. **Skip expensive stages**: Disable red_team, misinfo_check, community_sentiment for speed
5. **Use vLLM for local**: Fastest (free) LLM tier in cascade
6. **Dedupe URLs**: research_spider with dedupe=True (default)
7. **Limit per-URL chars**: research_spider with max_chars_each=2000 (default 5000)
8. **Use markdown mode**: research_markdown faster than dynamic fetch for static pages

---

## See Also

- **[architecture.md](./architecture.md)** — System design and internal pipeline
- **[API docs](./api.md)** — OpenAPI specification (if generated)

For additional help, check logs:
```bash
tail -f ~/.cache/loom/loom.log
```

Or enable debug mode:
```python
research_config_set("LOG_LEVEL", "DEBUG")
```
