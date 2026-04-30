# Loom MCP Research Server — Complete Help Guide

Loom is a comprehensive research orchestration system with 245+ tools, 21 search providers, intelligent provider cascading, and a 12-stage deep research pipeline.

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

## Tool Catalog (245+ Tools)

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

#### find_similar_exa
**Find semantically similar pages to a reference URL**

Uses Exa's semantic similarity to find pages semantically related to a given URL. Useful for finding competitors, related content, or similar resources.

Parameters:
- `url` (required, string): reference URL to find similar pages for
- `n` (optional, int, default 10): max results (1-100)
- Additional kwargs passed to Exa SDK

Returns:
```json
{
  "url": "https://reference-site.com",
  "similar_pages": [
    {
      "url": "...",
      "title": "...",
      "similarity_score": 0.92
    }
  ]
}
```

API key needed: **PAID** (Exa API key required)

Example:
```python
result = find_similar_exa(
    url="https://example.com",
    n=10
)
```

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

### Psychology & Behavioral Analysis (6 tools)

#### research_stylometry
**Author fingerprinting via writing style analysis**

Analyzes text for authorship patterns including vocabulary richness, sentence structure, function word frequencies, and stylistic markers. Useful for identifying ghostwritten content, literary attribution, or clustering similar authors.

Cost: **FREE**
Rate limit: No external API calls

Example:
```python
result = research_stylometry(
    text="Sample text to analyze",
    compare_texts=["comparison_text_1", "comparison_text_2"]
)
```

---

#### research_deception_detect
**Linguistic deception and fraud detection**

Detects fraudulent or deceptive content using linguistic cues including hedging language, distancing patterns, superlative overuse, and LLM-enhanced classification.

Cost: **FREE/PAID** (optional LLM)
Rate limit: None

---

#### research_persona_profile
**Cross-platform persona reconstruction from text**

Builds behavioral and linguistic profiles from text samples, identifying personality traits, communication style, interests, and platform behavior patterns.

Cost: **FREE**
Rate limit: No API

---

#### research_radicalization_detect
**Radicalization indicator detection in text**

Monitors text for indicators of radicalization including extremist rhetoric, ideological keywords, us-vs-them framing, and dehumanization language.

Cost: **FREE**
Rate limit: None

---

#### research_sentiment_deep
**Deep sentiment and emotion analysis with manipulation detection**

Provides nuanced emotion analysis beyond binary sentiment, detecting sarcasm, manipulation tactics, emotional manipulation patterns, and underlying sentiment drivers.

Cost: **FREE/PAID** (optional LLM enhancement)
Rate limit: None

---

#### research_network_persona
**Social network analysis and author interaction mapping**

Analyzes community and forum interaction graphs, identifying author network position, influence, interaction patterns, and social roles.

Cost: **FREE**
Rate limit: Depends on data source

---

### Domain & Network Intelligence (3 tools)

#### research_whois
**WHOIS domain registration lookup**

Retrieves domain registration information including registrant, registrar, nameservers, creation date, and expiration.

Cost: **FREE**
Rate limit: No API

Example:
```python
result = research_whois(domain="example.com")
```

---

#### research_dns_lookup
**DNS record resolution and analysis**

Performs DNS lookups for A, AAAA, MX, TXT, CNAME, NS, SOA records. Falls back to socket if dnspython unavailable.

Cost: **FREE**
Rate limit: System dependent

Parameters:
- `domain` (required): domain name
- `record_types` (optional): list of record types to query

---

#### research_nmap_scan
**Network port scanning via nmap**

Scans specified ports on target using nmap CLI. Supports basic port scan (SYN) and service version detection. Requires nmap binary installed.

Cost: **FREE**
Rate limit: None (local execution)

Parameters:
- `target`: host or IP to scan
- `ports`: comma-separated ports (default "80,443,8080,8443")
- `scan_type`: "basic"|"version"|"aggressive" (default "basic")

---

### Image Analysis (2 tools)

#### research_exif_extract
**Extract EXIF metadata from images**

Extracts EXIF, IPTC, XMP metadata including GPS coordinates, camera settings, timestamps, and embedded text.

Cost: **FREE**
Rate limit: None

Example:
```python
result = research_exif_extract(url_or_path="https://example.com/photo.jpg")
```

---

#### research_ocr_extract
**Optical character recognition (OCR) on images**

Extracts text from images using Tesseract OCR. Supports multi-language text detection and extraction from screenshots, documents, and photos.

Cost: **FREE** (requires Tesseract binary)
Rate limit: None (local)

---

#### research_image_analyze
**Image analysis using Google Cloud Vision API**

Analyzes images for labels, text, faces, landmarks, logos, objects, and safety attributes. Supports label detection, OCR, face detection, landmark recognition, logo detection, safe search scoring, and web detection.

Cost: **PAID** (Google Cloud Vision API)
Rate limit: Google Cloud rate limits

Parameters:
- `image_url` (required): public HTTPS URL or local file path
- `features` (optional): list of feature types
  - Default: ["LABEL_DETECTION", "TEXT_DETECTION"]
  - Options: LABEL_DETECTION, TEXT_DETECTION, FACE_DETECTION, LANDMARK_DETECTION, LOGO_DETECTION, SAFE_SEARCH_DETECTION, IMAGE_PROPERTIES, OBJECT_LOCALIZATION, WEB_DETECTION
- `max_results` (optional, int, default 10): max results per feature

Example:
```python
result = research_image_analyze(
    image_url="https://example.com/photo.jpg",
    features=["LABEL_DETECTION", "SAFE_SEARCH_DETECTION"]
)
```

---

### PDF Tools (2 tools)

#### research_pdf_extract
**Extract text from PDF documents**

Extracts structured text from PDF files with layout preservation, table detection, and optional section-level extraction.

Cost: **FREE**
Rate limit: None

Parameters:
- `url`: PDF document URL
- `include_images` (optional): extract image descriptions

---

#### research_pdf_search
**Full-text search within PDF content**

Searches for text, phrases, or keywords within a PDF document. Returns page numbers and context snippets.

Cost: **FREE**
Rate limit: None

Example:
```python
result = research_pdf_search(
    url="https://example.com/document.pdf",
    query="machine learning"
)
```

---

### Text & NLP Analysis (1 tool)

#### research_text_analyze
**NLP text analysis with entity extraction and readability metrics**

Performs named entity recognition (NER), keyword extraction, sentiment analysis, readability metrics (Flesch-Kincaid, Gunning Fog), and linguistic feature extraction.

Cost: **FREE**
Rate limit: None (local NLTK)

---

### Media & Screenshots (2 tools)

#### research_screenshot
**Capture webpage screenshots**

Captures full-page, element-level, or viewport-sized screenshots using Playwright with customizable viewport size, wait conditions, and format options.

Cost: **FREE** (requires Playwright)
Rate limit: None

Parameters:
- `url`: webpage URL
- `element_selector` (optional): CSS selector for specific element
- `viewport_width/height` (optional): custom viewport size
- `full_page` (optional): capture full page (default true)
- `format` (optional): "png"|"jpeg" (default "png")

---

#### research_text_to_speech
**Convert text to speech with multiple voices**

Synthesizes speech from text using multiple TTS providers and voices. Returns audio format selection.

Cost: **FREE/PAID** (provider dependent)
Rate limit: Provider dependent

---

### RSS & Feed Monitoring (2 tools)

#### research_rss_fetch
**Fetch and parse RSS/Atom feed entries**

Fetches RSS/Atom feeds and parses latest entries with optional filtering by date range or keyword.

Cost: **FREE**
Rate limit: None (feed provider dependent)

Parameters:
- `feed_url`: RSS or Atom feed URL
- `limit` (optional): max entries to return
- `parse_html_content` (optional): extract HTML from entries

---

#### research_rss_search
**Search RSS feeds by keyword and date**

Searches across multiple RSS feeds by keyword, date range, author, or category.

Cost: **FREE**
Rate limit: None

---

### Social Media Intelligence (2 tools)

#### research_social_search
**Discover social media profiles and usernames**

Searches for user profiles across social platforms (Twitter, LinkedIn, GitHub, etc.) by username, email, or name.

Cost: **FREE**
Rate limit: Platform dependent

---

#### research_social_profile
**Extract and analyze social media profiles**

Analyzes social profile pages including follower counts, engagement metrics, bio analysis, and linked accounts.

Cost: **FREE**
Rate limit: Platform rate limits

---

### Security & Vulnerability Analysis (5 tools)

#### research_cert_analyze
**SSL/TLS certificate extraction and analysis**

Extracts certificate information from remote servers including subject, issuer, validity dates, SANs, and expiry warnings.

Cost: **FREE**
Rate limit: None

Example:
```python
result = research_cert_analyze(hostname="example.com", port=443)
```

---

#### research_security_headers
**Analyze HTTP security headers**

Evaluates HTTP security headers (HSTS, CSP, X-Frame-Options, etc.) and provides security posture scoring.

Cost: **FREE**
Rate limit: None

---

#### research_breach_check
**Query data breach databases**

Checks if an email appears in known data breaches using HaveIBeenPwned API (requires API key for full results).

Cost: **FREE/PAID** (HIBP API key recommended)
Rate limit: HaveIBeenPwned rate limits

---

#### research_password_check
**Check password breach history**

Verifies if a password has been exposed in known breaches using k-anonymity (no password sent to server). Requires no API key.

Cost: **FREE**
Rate limit: HaveIBeenPwned free tier

---

### IP Intelligence (2 tools)

#### research_ip_reputation
**IP address reputation and threat scoring**

Queries IP reputation databases for malicious activity, blocklists, botnet associations, and threat scores.

Cost: **FREE**
Rate limit: No API required (local database or free tier)

---

#### research_ip_geolocation
**IP geolocation lookup with accuracy metrics**

Performs geolocation lookup returning country, city, coordinates, ISP, and ASN with accuracy information.

Cost: **FREE** (via MaxMind GeoLite2 or local database)
Rate limit: None

Example:
```python
result = research_ip_geolocation(ip="8.8.8.8")
```

---

### Vulnerability & Threat Research (2 tools)

#### research_cve_lookup
**CVE database search via NVD**

Searches National Vulnerability Database (NVD) by keyword for CVE entries with severity, vector, and affected product info.

Cost: **FREE**
Rate limit: NVD rate limited (free tier: ~120 req/min)

---

#### research_cve_detail
**Detailed CVE information retrieval**

Retrieves complete details for a specific CVE ID including CVSS scores, descriptions, affected versions, and fix information.

Cost: **FREE**
Rate limit: NVD rate limits

---

### Malware & URL Threat Intelligence (2 tools)

#### research_urlhaus_check
**URLhaus malware database lookup**

Checks if a URL appears in URLhaus malware database with threat classification and detection history.

Cost: **FREE**
Rate limit: URLhaus free API

---

#### research_urlhaus_search
**Search URLhaus for malicious URLs**

Searches URLhaus database by domain, date range, or malware family. Returns threat metadata.

Cost: **FREE**
Rate limit: URLhaus free tier

---

### GeoIP & Location (1 tool)

#### research_geoip_local
**Local GeoIP lookup using MaxMind database**

Performs offline GeoIP lookup using MaxMind GeoLite2 database. No API key required, instant local queries.

Cost: **FREE**
Rate limit: None (local)

Example:
```python
result = research_geoip_local(ip="1.1.1.1")
```

---

### Darkweb & Onion Intelligence (4 tools)

#### research_ghost_weave
**Build temporal hyperlink graph of .onion services**

Maps .onion site structure and link relationships over time using Tor. Returns network graph and temporal changes.

Cost: **FREE** (requires Tor)
Rate limit: Tor network dependent

---

#### research_onion_spectra
**Classify .onion sites by content and safety**

Analyzes .onion site content for language, classification (forums, markets, hosting), and safety scoring.

Cost: **FREE**
Rate limit: Tor network dependent

---

#### research_cipher_mirror
**Monitor paste sites for leaked credentials**

Monitors paste sites, GitHub pastes, and code repositories for exposed credentials, API keys, and private keys. Uses entropy analysis to detect leaks.

Cost: **FREE/PAID** (LLM optional for analysis)
Rate limit: Paste site dependent

---

#### research_dead_drop_scanner
**Probe ephemeral .onion sites with reuse detection**

Monitors ephemeral .onion sites for content changes using shingling-based content deduplication.

Cost: **FREE** (requires Tor)
Rate limit: Tor network dependent

---

### Communication & Notifications (2 tools)

#### research_email_report
**Send research results via email**

Sends structured reports via SMTP with optional HTML formatting.

Cost: **FREE** (requires SMTP configuration)
Rate limit: SMTP provider limits

Parameters:
- `to`: recipient email
- `subject`: email subject
- `body`: email body text
- `html` (optional): treat body as HTML

---

#### research_slack_notify
**Send notifications to Slack channel**

Posts research findings to Slack with formatting and threaded replies.

Cost: **FREE** (requires Slack webhook)
Rate limit: Slack rate limits

---

### Note-Taking Integration (2 tools)

#### research_save_note
**Save research to Joplin notes**

Saves text, markdown, or structured data to Joplin note-taking application.

Cost: **FREE** (requires Joplin + API token)
Rate limit: Joplin API limits

---

#### research_list_notebooks
**List Joplin notebooks and recent notes**

Lists available notebooks and recent notes from Joplin.

Cost: **FREE** (requires Joplin API)
Rate limit: None (local)

---

### Infrastructure & Monitoring (4 tools)

#### research_metrics
**Return Prometheus-compatible metrics**

Exports metrics in Prometheus format for monitoring dashboards (requests, latency, error rates, costs).

Cost: **FREE**
Rate limit: None

---

#### research_health_check
**System health status and API availability**

Returns health status of MCP server, external APIs, and resource usage.

Cost: **FREE**
Rate limit: None

---

#### research_vercel_status
**Check Vercel deployment status**

Returns deployment status and analytics from Vercel CI/CD platform.

Cost: **FREE** (requires Vercel API token)
Rate limit: Vercel API limits

---

#### research_vastai_status
**Check VastAI GPU compute status**

Queries VastAI API for current GPU availability, pricing, and machine status.

Cost: **FREE** (requires API key, read-only)
Rate limit: VastAI API limits

---

### Video & Audio (2 tools)

#### research_transcribe
**Audio transcription with speech-to-text**

Transcribes audio files or URLs to text using Whisper or configurable transcription engine.

Cost: **FREE/PAID** (provider dependent)
Rate limit: Provider dependent

Parameters:
- `audio_url`: URL or path to audio file
- `language` (optional): ISO language code
- `output_format` (optional): "text"|"json"|"vtt"

---

#### research_tts_voices
**List available text-to-speech voices**

Returns available voices for TTS synthesis including language, gender, and provider information.

Cost: **FREE**
Rate limit: None

---

### Document Conversion (1 tool)

#### research_convert_document
**Convert documents to markdown or text**

Converts PDF, DOCX, HTML, and other formats to markdown or plain text with formatting preservation.

Cost: **FREE**
Rate limit: None (local)

---

### GPU Compute & Infrastructure (1 tool)

#### research_vastai_search
**Search VastAI GPU compute marketplace**

Searches available GPUs on VastAI marketplace by specs, price, and availability. Returns machine listings with rental pricing.

Cost: **FREE** (read-only, requires API key)
Rate limit: VastAI API limits

---

### Analytics & Forum Analysis (2 tools)

#### research_forum_cortex
**Analyze dark web forum discourse**

Analyzes forum discussions on darknet markets for topic trends, sentiment, and key participants.

Cost: **PAID** (LLM required)
Rate limit: Tor network dependent

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

## Search Providers Guide (21 Providers)

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

### 10. NewsAPI (News articles)
- **Cost**: Free tier (500 req/day), Paid ($99+/mo)
- **Best for**: News articles, press releases, media coverage
- **Date range**: Supported
- **Domain filtering**: Supported
- **Rate limit**: 500 req/day (free tier)
- **Signup**: https://newsapi.org

### 11. CoinMarketCap (Cryptocurrency data)
- **Cost**: Free tier (monthly data), Paid ($99+/mo)
- **Best for**: Crypto price tracking, market data, coin rankings
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Free tier limits
- **Signup**: https://coinmarketcap.com/api

### 12. CoinDesk (Crypto news)
- **Cost**: Free
- **Best for**: Cryptocurrency news, blockchain articles
- **Date range**: Supported
- **Domain filtering**: Client-side
- **Rate limit**: Soft limits
- **Signup**: None (public API)

### 13. Binance (Crypto data)
- **Cost**: Free
- **Best for**: Trading data, market metrics, cryptocurrency prices
- **Date range**: Not applicable
- **Domain filtering**: N/A
- **Rate limit**: Binance API rate limits
- **Signup**: https://www.binance.com/api

### 14. Investing.com (Financial data)
- **Cost**: Free
- **Best for**: Stock prices, economic indicators, financial news
- **Date range**: Supported
- **Domain filtering**: Client-side
- **Rate limit**: Soft limits
- **Signup**: None (public data)

### 15. Ahmia (Darknet search)
- **Cost**: Free
- **Best for**: .onion site discovery, darknet content
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Soft limits
- **Signup**: None (Tor network)

### 16. Darksearch (Darknet search)
- **Cost**: Free
- **Best for**: .onion site search, darknet markets
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Tor network dependent
- **Signup**: None (Tor network)

### 17. UMMRO RAG (Custom knowledge base)
- **Cost**: Free/Paid (depends on deployment)
- **Best for**: Organization-specific knowledge retrieval
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Custom (configurable)
- **Signup**: https://ummro.alderai.uk (if deployed)

### 18. Onion Search (Tor multi-search)
- **Cost**: Free
- **Best for**: Multi-engine .onion search (Ahmia + Darksearch)
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Tor network dependent
- **Signup**: None (Tor network)

### 19. TorCrawl (Tor crawler)
- **Cost**: Free
- **Best for**: Deep crawling of .onion sites
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Tor network dependent
- **Signup**: None (Tor network)

### 20. Darkweb CTI (Darknet threat intelligence)
- **Cost**: Free
- **Best for**: Threat intelligence, breach data, malware tracking
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: API dependent
- **Signup**: Custom endpoint (self-hosted or hosted)

### 21. Robin OSINT (Multi-source OSINT)
- **Cost**: Free
- **Best for**: OSINT aggregation, multi-source intelligence
- **Date range**: Not supported
- **Domain filtering**: N/A
- **Rate limit**: Varies by source
- **Signup**: None (aggregates public sources)

---

### Billing & Usage (2 tools)

#### research_usage_report
**Aggregate LLM usage and costs from local logs**

Reads cost tracker JSON files and summarizes total cost, calls by provider, calls by day, and top models used over the past N days.

Cost: **FREE**
Rate limit: None (local logs)

Parameters:
- `days` (optional, int, default 7): number of days to aggregate

Example:
```python
result = research_usage_report(days=7)
```

---

#### research_stripe_balance
**Get Stripe account balance and usage**

Retrieves current Stripe account balance, pending charges, and available funds. Requires Stripe API key.

Cost: **FREE** (requires Stripe API key)
Rate limit: Stripe API limits

---

### Tor Network Tools (2 tools)

#### research_tor_status
**Check Tor network and connection status**

Returns current Tor connection status, exit node IP, country, and connection health metrics.

Cost: **FREE** (requires Tor daemon)
Rate limit: None (local)

Example:
```python
result = research_tor_status()
```

---

#### research_tor_new_identity
**Request new Tor identity and exit node**

Requests a new Tor identity from the control port, changing the exit node IP. Useful for anonymity rotation.

Cost: **FREE** (requires Tor daemon + control port password)
Rate limit: None (Tor daemon controls)

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
