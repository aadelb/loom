# Loom MCP Architecture

Loom is a production-grade research orchestration server built on FastMCP. It combines 245+ research tools, a 12-stage deep research pipeline, intelligent provider cascading, and security-hardened fetch escalation.

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      FastMCP Server (Port 8787)                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Core Research Tools (10)                    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • research_search      - Multi-provider search routing  │   │
│  │ • research_fetch       - Unified URL fetcher            │   │
│  │ • research_spider      - Parallel bulk fetch            │   │
│  │ • research_markdown    - LLM-ready markdown extraction  │   │
│  │ • research_deep        - 12-stage orchestration         │   │
│  │ • research_github      - GitHub repo + code search      │   │
│  │ • research_camoufox    - Stealth browser (Camoufox)    │   │
│  │ • research_botasaurus  - Stealth browser (Botasaurus)  │   │
│  │ • research_cache_stats - Cache diagnostics             │   │
│  │ • research_cache_clear - Cache TTL cleanup             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │          Optional LLM & Enrichment Tools (13+)          │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • research_llm_*            - Chat, embed, translate    │   │
│  │ • research_find_experts     - Expert discovery          │   │
│  │ • research_red_team         - Adversarial stress test   │   │
│  │ • research_misinfo_check    - Misinformation detection  │   │
│  │ • research_community_sentiment - HN + Reddit sentiment  │   │
│  │ • research_detect_language  - Language detection        │   │
│  │ • research_wayback          - Wayback Machine fallback  │   │
│  │ • fetch_youtube_transcript  - YouTube transcript fetch │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Session & Config Management                   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • research_session_open/close/list - Browser sessions   │   │
│  │ • research_config_get/set - Runtime configuration       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
         │         │          │          │         │
         │         └──────────┼──────────┘         │
         │                    │                    │
         v                    v                    v
    ┌─────────┐          ┌─────────┐          ┌──────────┐
    │ Caching │          │ Session │          │Validators│
    │ (SHA256)│          │ Manager │          │(SSRF)    │
    └─────────┘          └─────────┘          └──────────┘
```

## 12-Stage Deep Research Pipeline

`research_deep()` orchestrates a comprehensive, multi-phase research workflow:

```
STAGE 1: Query Expansion via LLM
  Input: query (e.g. "latest ML architectures 2026")
  Action: LLM expands into N variants for broader coverage
  Output: [variant_1, variant_2, ...]

    ↓

STAGE 2: Query Type Detection & Provider Selection
  Input: expanded queries
  Detection: Academic | Code | Knowledge keywords
  Output: provider routing decision (arxiv, exa, hackernews, etc)

    ↓

STAGE 3: Multi-Provider Parallel Search
  Input: queries + provider config
  Routes:
    - Academic queries → arxiv, scholar
    - Code queries → GitHub (via research_github), npm registries
    - Knowledge queries → Wikipedia, Exa, Tavily
    - Default → ALL configured providers
  Output: merged + deduplicated search results (top N by score)

    ↓

STAGE 4: Parallel Fetch with Auto-Escalation
  Input: result URLs (up to MAX_SPIDER_URLS=100)
  Escalation Chain:
    http (httpx)
      ↓ (if blocked/timeout)
    stealthy (Scrapling with rotating proxies)
      ↓ (if JS-heavy)
    dynamic (Playwright/Camoufox)
  Fallbacks:
    - YouTube videos → fetch_youtube_transcript
    - Old/removed pages → Wayback Machine
  Output: {url, text, html, json, error} for each

    ↓

STAGE 5: LLM-Powered Content Extraction
  Input: raw page text from stage 4
  Action: Extract answer-relevant passages, metadata, claims
  Output: structured {extracted_text, passages, confidence}

    ↓

STAGE 6: Relevance Ranking
  Input: extracted content + original query
  Action: Score/rank by relevance, dedup, sort
  Output: ranked [{content, source, score}, ...]

    ↓

STAGE 7: GitHub Enrichment (optional)
  Input: ranked results (if include_github=True)
  Action: research_github_readme for related repos
  Output: {repo, stars, language, readme_snippet}

    ↓

STAGE 8: Language Detection (optional)
  Input: extracted text from stage 5
  Action: Detect primary language via fasttext/LLM
  Output: {lang_code, confidence, original_text}

    ↓

STAGE 9: Community Sentiment Analysis (optional, RESEARCH_COMMUNITY_SENTIMENT=True)
  Input: query
  Action: research_community_sentiment (HN + Reddit)
  Output: {sentiment, posts, engagement_score}

    ↓

STAGE 10: Adversarial Red Team (optional, RESEARCH_RED_TEAM=True)
  Input: draft synthesis from stage 6
  Action: research_red_team - challenge claims, find counterarguments
  Output: {weaknesses, counterarguments, confidence}

    ↓

STAGE 11: Misinformation Check (optional, RESEARCH_MISINFO_CHECK=True)
  Input: key claims extracted in stage 5
  Action: research_misinfo_check - fact check via external APIs
  Output: {claim, verdict, evidence, confidence}

    ↓

STAGE 12: Synthesize & Return
  Input: ranked results (stage 6) + optional enhancements (stages 7-11)
  Action: LLM synthesizes final answer with citations
  Output: {
      "answer": "...",
      "sources": [...],
      "citations": [...],
      "metadata": {
          "stages_completed": [...],
          "total_urls_fetched": N,
          "cost_usd": X.XX,
          "elapsed_ms": Y
      }
  }
```

## Provider Cascade System

### LLM Provider Cascade

When an LLM tool is called, Loom cascades through providers in configurable order:

```
LLM Request
    ↓
[LLM_CASCADE_ORDER: [nvidia, openai, anthropic, vllm] — configurable]
    ↓
    ├─→ NVIDIA NIM (default, fastest, self-hosted or cloud)
    │   └─→ Models: meta/llama-4-maverick-17b, nvidia/nv-embed-v2, etc.
    │
    ├─→ OpenAI (fallback 1)
    │   └─→ Models: gpt-4, gpt-4-turbo, etc.
    │
    ├─→ Anthropic (fallback 2)
    │   └─→ Models: claude-3-opus, claude-3-sonnet, etc.
    │
    └─→ vLLM (fallback 3, local)
        └─→ Models: configured local models
```

**Cost Tracking:**
- Per-request cost estimation via `_estimate_cost(model, prompt_tokens, completion_tokens)`
- Daily cap enforced: `LLM_DAILY_COST_CAP_USD` (default $10)
- Per-research cap: `RESEARCH_MAX_COST_USD` (default $0.50)

### Search Provider Routing

```
research_search(provider=None) or research_deep()
    ↓
Provider Routing Table (7 search providers + 2 special):

  ┌─ Routed Search Providers (query → results) ─┐
  │                                              │
  │  exa        → Neural semantic search        │
  │  tavily     → LLM-optimized web search      │
  │  firecrawl  → Full-page scrape + search     │
  │  brave      → Privacy-focused search        │
  │  ddgs       → DuckDuckGo (API-free)        │
  │  arxiv      → Academic papers               │
  │  wikipedia  → Encyclopedia search           │
  │                                              │
  │ [hackernews, reddit via creative tools]    │
  └──────────────────────────────────────────────┘
         ↓
    Fallback on error: DEFAULT_SEARCH_PROVIDER
         ↓
    Return: {provider, query, results: [...]}
```

**Query Auto-Detection (research_deep only):**
- **Academic** (keywords: paper, arxiv, research, neural, etc.) → arxiv
- **Code** (keywords: repo, github, library, package, npm, pypi, etc.) → GitHub + package registries
- **Knowledge** (patterns: "what is", "explain", "define", etc.) → Wikipedia + Exa + Tavily
- **Default** → ALL configured providers (de-duplicated by URL)

## Fetch Auto-Escalation Strategy

```
research_fetch(url, mode=...)  or  research_spider([urls], mode=...)
    ↓
[FETCH_AUTO_ESCALATE: True/False]
    ↓
    IF mode == "http":
        Try HTTP (httpx) with 30s timeout
          ├─ Success? Return {url, text, html, status_code}
          ├─ Timeout/Cloudflare/JS-heavy?
          │  └─→ Escalate to "stealthy"
          └─ Permanent error? Return {error}
    ↓
    IF mode == "stealthy" (or escalated):
        Try Scrapling (rotating proxies, realistic headers)
        Handles Cloudflare, JavaScript, anti-bot
          ├─ Success? Return {url, text, html}
          ├─ Still blocked / JS-dependent?
          │  └─→ Escalate to "dynamic"
          └─ Permanent error? Return {error}
    ↓
    IF mode == "dynamic" (or escalated):
        Try Playwright + Camoufox (real browser)
        Renders JS, handles login flows
          ├─ Success? Return {url, text, html, screenshot}
          └─ Error? Return {error}
    ↓
    Special Fallbacks:
        ├─ YouTube URLs → fetch_youtube_transcript (yt-dlp)
        └─ Missing/404 → Try Wayback Machine (research_wayback)
```

## Caching Strategy

**Content-Hash Caching with Daily TTL:**

```
Cache Key: SHA-256({tool}::{provider}::{url}::{params})
  └─ First 32 hex chars used

Cache Path: ~/.cache/loom/{DATE-ISO}/{KEY}.json
  Example: ~/.cache/loom/2026-04-24/abc123def456.json

Cache Value: {
    "url": "...",
    "text": "...",
    "cached_at": "2026-04-24T12:34:56Z",
    "elapsed_ms": 1234
}

TTL Cleanup:
  • research_cache_clear(days=30) removes entries older than N days
  • Automatic daily cron (if enabled): remove >30 days old
  • Stats: research_cache_stats returns file_count, total_bytes, days_present

Hit Rate:
  • Same query + provider + URL → cache hit (0ms fetch)
  • Different params → cache miss
```

## Session Management

Persistent browser contexts with TTL and LRU eviction:

```
research_session_open(name="my_session", browser="camoufox", ttl_seconds=3600)
    ↓
SessionManager (singleton, SQLite-backed)
    ├─ Create browser context (Camoufox | Chromium | Firefox)
    ├─ Store metadata: {name, browser, created_at, expires_at, profile_dir}
    ├─ Save to: ~/.loom/sessions/{name}/
    └─ Auto-cleanup: if len(sessions) > 8, evict oldest

Usage:
  1. research_session_open("login") → authenticate
  2. research_spider([urls], session="login") → use authenticated context
  3. research_session_close("login") → cleanup

TTL Behavior:
  • Session expires after ttl_seconds
  • Auto-removed on next access or cleanup_sessions() call
  • last_used timestamp updated on reuse
```

## Security & Validation

### SSRF Protection

**validate_url(url)** blocks requests to:
- Private IPs (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Loopback (127.0.0.1, ::1)
- Link-local (169.254.0.0/16)
- Multicast (224.0.0.0/4, ff00::/8)
- Reserved (0.0.0.0/8, 240.0.0.0/4)
- Unspecified (0.0.0.0, ::)
- Cloud metadata (via resolved IP check)

**DNS Resolution:**
- Validates all A and AAAA records
- Rejects if ANY resolves to blocked IP
- Prevents DNS rebind attacks

### Cost & Rate Limiting

**LLM Cost Caps:**
- `LLM_DAILY_COST_CAP_USD`: Stop processing if daily spend > cap
- `RESEARCH_MAX_COST_USD`: Per-research cost limit (default $0.50)
- Estimated before execution; actual used logged

**URL Limits:**
- `MAX_SPIDER_URLS`: Max 100 URLs per spider call
- `MAX_CHARS_HARD_CAP`: Max 200K chars per fetch
- `SPIDER_CONCURRENCY`: Max 5 parallel fetches (configurable 1-20)

### Input Validation

- GitHub queries validated against allow-list regex (no flag injection)
- Config keys validated against bounds (Pydantic v2)
- Session names: lowercase alphanumeric + underscore/hyphen, max 32 chars
- Provider names: enum-checked against known providers

## Configuration Keys

All keys in `config.json` or environment variables:

```
SCRAPING:
  SPIDER_CONCURRENCY        (1-20, default 5)
  EXTERNAL_TIMEOUT_SECS     (5-120, default 30)
  MAX_CHARS_HARD_CAP        (1K-2M, default 200K)
  MAX_SPIDER_URLS           (1-500, default 100)
  FETCH_AUTO_ESCALATE       (true/false, default true)

CACHE:
  CACHE_TTL_DAYS            (1-365, default 30)

SEARCH:
  DEFAULT_SEARCH_PROVIDER   (exa|tavily|firecrawl|brave|ddgs|arxiv|wikipedia)
  DEFAULT_ACCEPT_LANGUAGE   (default "en-US,en;q=0.9,ar;q=0.8")
  RESEARCH_SEARCH_PROVIDERS ([exa, brave] default)

LLM:
  LLM_DEFAULT_CHAT_MODEL    (default "meta/llama-4-maverick-17b-128e-instruct")
  LLM_DEFAULT_EMBED_MODEL   (default "nvidia/nv-embed-v2")
  LLM_DEFAULT_TRANSLATE_MODEL (default "moonshotai/kimi-k2-instruct")
  LLM_MAX_PARALLEL          (1-64, default 12)
  LLM_DAILY_COST_CAP_USD    (0-1000, default 10)
  LLM_CASCADE_ORDER         ([nvidia, openai, anthropic, vllm])

RESEARCH PIPELINE:
  RESEARCH_EXPAND_QUERIES   (true/false, default true)
  RESEARCH_EXTRACT          (true/false, default true)
  RESEARCH_SYNTHESIZE       (true/false, default true)
  RESEARCH_GITHUB_ENRICHMENT (true/false, default true)
  RESEARCH_MAX_COST_USD     (0-10, default 0.50)
  RESEARCH_COMMUNITY_SENTIMENT (true/false, default false)
  RESEARCH_RED_TEAM         (true/false, default false)
  RESEARCH_MISINFO_CHECK    (true/false, default false)

LOGGING:
  LOG_LEVEL                 (DEBUG|INFO|WARNING|ERROR, default INFO)

SERVER:
  LOOM_HOST                 (default 127.0.0.1)
  LOOM_PORT                 (default 8787)
  LOOM_CONFIG_PATH          (default ./config.json)
  LOOM_CACHE_DIR            (default ~/.cache/loom)
  LOOM_SESSIONS_DIR         (default ~/.loom/sessions)
```

## Tool Dependency Graph

```
research_deep
    ├─→ research_llm_query_expand
    ├─→ research_search (all configured providers)
    │   ├─→ search_exa / search_tavily / search_firecrawl / etc.
    │   └─→ [optional provider config routing]
    ├─→ research_spider
    │   └─→ research_fetch (per-URL)
    │       ├─→ HTTP (httpx)
    │       ├─→ Stealthy (Scrapling)
    │       ├─→ Dynamic (Playwright)
    │       └─→ [Special: YouTube transcripts, Wayback fallback]
    ├─→ research_markdown (parallel with spider)
    │   └─→ Crawl4AI async extractor
    ├─→ research_llm_extract
    ├─→ research_llm_summarize
    ├─→ research_github (optional)
    │   ├─→ research_github_readme
    │   └─→ research_github_releases
    ├─→ research_detect_language (optional)
    ├─→ research_community_sentiment (optional)
    │   ├─→ HackerNews sentiment
    │   └─→ Reddit sentiment
    ├─→ research_red_team (optional)
    ├─→ research_misinfo_check (optional)
    └─→ research_llm_answer (final synthesis)

research_spider
    └─→ research_fetch × N (bounded concurrency)

research_fetch
    ├─→ HTTP mode (httpx)
    ├─→ Stealthy mode (Scrapling)
    ├─→ Dynamic mode (Playwright + Camoufox)
    └─→ [Special fallbacks: YouTube, Wayback]

research_find_experts (independent)
    └─→ research_search + research_llm_embed

research_red_team (independent)
    └─→ research_llm_chat

research_misinfo_check (independent)
    └─→ research_search + research_llm_classify
```

## Performance Notes

- **Parallelization:** research_spider uses asyncio.Semaphore for bounded concurrency
- **Caching:** All fetches and markdown extractions are SHA-256 cached with 30-day TTL
- **Timeouts:** All external requests enforce EXTERNAL_TIMEOUT_SECS (default 30s)
- **Cost Tracking:** Real-time cost estimation; research aborts if cap exceeded
- **Memory:** Loom is designed to run on 24GB RAM (respects Mac constraints)

## Deployment Topology

```
Client (Claude, Kimi, etc.)
    ↓ (MCP Protocol)
Loom FastMCP Server (127.0.0.1:8787)
    ├─→ LLM Providers (NVIDIA NIM, OpenAI, Anthropic, vLLM)
    ├─→ Search APIs (Exa, Tavily, Firecrawl, Brave, etc.)
    ├─→ Web Fetching (httpx, Scrapling, Playwright, Camoufox)
    ├─→ Cache Store (SQLite, JSON blobs)
    └─→ Session Store (SQLite, browser profiles)
```

All external APIs are authenticated via environment variables (loaded at startup).
