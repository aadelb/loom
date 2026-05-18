# Architecture vs Implementation Cross-Match Analysis

**Source:** `docs/architecture.md`  
**Implementation:** `src/loom/`  
**Generated:** 2026-05-18

## Methodology

Every component, tool, stage, subsystem, and configuration key mentioned in `docs/architecture.md` was searched for in `src/loom/` using `grep` and file inspection. The result for each item is:

- **EXISTS** — A concrete implementation (function, class, or module) was found.
- **PARTIAL** — An implementation exists but deviates from the architecture description (library choice, default value, location, or behavior).
- **MISSING** — No implementation was found.

---

## Summary

| Status | Count |
|--------|-------|
| **EXISTS** | 72 |
| **PARTIAL** | 5 |
| **MISSING** | 0 |

---

## 1. Core Research Tools (10)

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `research_search` | **EXISTS** | `src/loom/tools/core/search.py` | Unified search router with provider dispatch. |
| `research_fetch` | **EXISTS** | `src/loom/tools/core/fetch.py` | Unified URL fetcher with mode escalation. |
| `research_spider` | **EXISTS** | `src/loom/tools/core/spider.py` | Parallel bulk fetch with `asyncio.Semaphore`. |
| `research_markdown` | **EXISTS** | `src/loom/tools/core/markdown.py` | Crawl4AI async markdown extractor. |
| `research_deep` | **EXISTS** | `src/loom/tools/core/deep.py` | 12-stage orchestration entry point. |
| `research_github` | **EXISTS** | `src/loom/tools/core/github.py` | Repo/code search + readme/releases helpers. |
| `research_camoufox` | **EXISTS** | `src/loom/tools/adversarial/stealth.py` | Exists as a standalone tool; **not** wired into `research_fetch` escalation chain. |
| `research_botasaurus` | **EXISTS** | `src/loom/tools/adversarial/stealth.py` | Exists as a standalone tool; **not** wired into `research_fetch` escalation chain. |
| `research_cache_stats` | **EXISTS** | `src/loom/tools/core/cache_mgmt.py` | Returns file count, bytes, days present. |
| `research_cache_clear` | **EXISTS** | `src/loom/tools/core/cache_mgmt.py` | TTL cleanup driven by `CACHE_TTL_DAYS`. |

---

## 2. Optional LLM & Enrichment Tools (13+)

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `research_llm_chat` | **EXISTS** | `src/loom/tools/llm/llm.py` | LLM chat with cascade fallback. |
| `research_llm_embed` | **EXISTS** | `src/loom/tools/llm/llm.py` | Text embedding via provider cascade. |
| `research_llm_translate` | **EXISTS** | `src/loom/tools/llm/llm.py` | Translation wrapper. |
| `research_find_experts` | **EXISTS** | `src/loom/tools/llm/experts.py` | Expert discovery via search + embed. |
| `research_red_team` | **EXISTS** | `src/loom/tools/llm/creative.py` | Adversarial stress-test / claim challenge. |
| `research_misinfo_check` | **EXISTS** | `src/loom/tools/llm/creative.py` | Fact-checking via external search + LLM classify. |
| `research_community_sentiment` | **EXISTS** | `src/loom/tools/llm/creative.py` | HN + Reddit sentiment aggregation. |
| `research_detect_language` | **EXISTS** | `src/loom/tools/core/enrich.py` | Language detection via fasttext/LLM. |
| `research_wayback` | **EXISTS** | `src/loom/tools/core/enrich.py` | Wayback Machine fallback fetch. |
| `fetch_youtube_transcript` | **EXISTS** | `src/loom/providers/youtube_transcripts.py` | yt-dlp based transcript fetch. |

---

## 3. Session & Config Management

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `research_session_open` | **EXISTS** | `src/loom/sessions.py` | Opens browser context with TTL. |
| `research_session_close` | **EXISTS** | `src/loom/sessions.py` | Closes and cleans up session. |
| `research_session_list` | **EXISTS** | `src/loom/sessions.py` | Lists active sessions from SQLite. |
| `research_config_get` | **EXISTS** | `src/loom/config.py` | Runtime config reader. |
| `research_config_set` | **EXISTS** | `src/loom/config.py` | Runtime config writer. |

---

## 4. 12-Stage Deep Research Pipeline

| Stage | Component | Status | File Path | Notes |
|-------|-----------|--------|-----------|-------|
| 1 | Query Expansion (`research_llm_query_expand`) | **EXISTS** | `src/loom/tools/llm/llm.py` | Called by `research_deep`. |
| 2 | Query Type Detection (`_detect_query_type`) | **EXISTS** | `src/loom/tools/core/deep.py` | Academic / code / knowledge / finance / darkweb / news detection. |
| 3 | Multi-Provider Parallel Search (`research_search`) | **EXISTS** | `src/loom/tools/core/search.py` | Dispatches to configured providers. |
| 4 | Parallel Fetch with Auto-Escalation (`research_spider` / `research_fetch`) | **EXISTS** | `src/loom/tools/core/spider.py`, `src/loom/tools/core/fetch.py` | Bounded concurrency + escalation. |
| 5 | LLM-Powered Content Extraction (`research_llm_extract`) | **EXISTS** | `src/loom/tools/llm/llm.py` | Structured extraction with schema. |
| 6 | Relevance Ranking | **PARTIAL** | `src/loom/tools/core/deep.py` | No distinct tool call; ranking/dedup is inline inside `research_deep`. `research_llm_summarize` exists but is **not** invoked by the pipeline. |
| 7 | GitHub Enrichment (`research_github`, `research_github_readme`) | **EXISTS** | `src/loom/tools/core/github.py` | Optional enrichment based on `RESEARCH_GITHUB_ENRICHMENT`. |
| 8 | Language Detection (`research_detect_language`) | **EXISTS** | `src/loom/tools/core/enrich.py` | Optional stage. |
| 9 | Community Sentiment (`research_community_sentiment`) | **EXISTS** | `src/loom/tools/llm/creative.py` | Optional stage gated by `RESEARCH_COMMUNITY_SENTIMENT`. |
| 10 | Adversarial Red Team (`research_red_team`) | **EXISTS** | `src/loom/tools/llm/creative.py` | Optional stage gated by `RESEARCH_RED_TEAM`. |
| 11 | Misinformation Check (`research_misinfo_check`) | **EXISTS** | `src/loom/tools/llm/creative.py` | Optional stage gated by `RESEARCH_MISINFO_CHECK`. |
| 12 | Synthesize & Return (`research_llm_answer`) | **EXISTS** | `src/loom/tools/llm/llm.py` | Final synthesis with citations. |

---

## 5. Provider Cascade System

### 5.1 LLM Provider Cascade

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `provider_router.py` / cascade logic | **EXISTS** | `src/loom/provider_router.py` | `select_provider()`, `get_available_providers()`, `cascade_status()`. |
| `NvidiaNimProvider` | **EXISTS** | `src/loom/providers/nvidia_nim.py` | Inherits `OpenAICompatProvider`. |
| `OpenAIProvider` | **EXISTS** | `src/loom/providers/openai_provider.py` | Native OpenAI client wrapper. |
| `AnthropicProvider` | **EXISTS** | `src/loom/providers/anthropic_provider.py` | Native Anthropic client wrapper. |
| `VllmLocalProvider` | **EXISTS** | `src/loom/providers/vllm_local.py` | Local vLLM inference. |
| `_estimate_cost` | **EXISTS** | `src/loom/providers/base.py` | Cost estimation per provider/model. |
| `LLM_CASCADE_ORDER` default | **PARTIAL** | `src/loom/provider_router.py` | Docs say `[nvidia, openai, anthropic, vllm]`; code default is `[groq, nvidia, deepseek, gemini, moonshot, openai, anthropic, ollama, vllm]`. |

### 5.2 Search Provider Routing

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `search_exa` | **EXISTS** | `src/loom/providers/exa.py` | Neural semantic search. |
| `search_tavily` | **EXISTS** | `src/loom/providers/tavily.py` | LLM-optimized web search. |
| `search_firecrawl` | **EXISTS** | `src/loom/providers/firecrawl.py` | Full-page scrape + search. |
| `search_brave` | **EXISTS** | `src/loom/providers/brave.py` | Privacy-focused search. |
| `search_ddgs` | **EXISTS** | `src/loom/providers/ddgs.py` | DuckDuckGo (API-free). |
| `search_arxiv` | **EXISTS** | `src/loom/providers/arxiv_search.py` | Academic papers. |
| `search_wikipedia` | **EXISTS** | `src/loom/providers/wikipedia_search.py` | Encyclopedia search. |
| HN + Reddit | **EXISTS** | `src/loom/providers/hn_reddit.py` | HackerNews & Reddit search/sentiment. |

---

## 6. Fetch Auto-Escalation Strategy

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `research_fetch` dispatcher | **EXISTS** | `src/loom/tools/core/fetch.py` | Routes to HTTP / stealthy / dynamic. |
| HTTP mode (`_fetch_http`) | **PARTIAL** | `src/loom/tools/core/fetch.py` | Docs specify `httpx`; implementation uses `requests`. |
| Stealthy mode (`_fetch_stealthy`) | **EXISTS** | `src/loom/tools/core/fetch.py` | Uses `scrapling` with stealth headers. |
| Dynamic mode (`_fetch_dynamic`) | **PARTIAL** | `src/loom/tools/core/fetch.py` | Uses Playwright only; Camoufox is **not** used inside the fetch escalation chain (separate `research_camoufox` tool exists). |
| YouTube fallback (`fetch_youtube_transcript`) | **EXISTS** | `src/loom/providers/youtube_transcripts.py` | yt-dlp transcript extraction. |
| Wayback fallback (`research_wayback`) | **EXISTS** | `src/loom/tools/core/enrich.py` | Archive.org fallback. |

---

## 7. Caching Strategy

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `CacheStore` (SHA-256, daily dirs, atomic writes, gzip) | **EXISTS** | `src/loom/cache.py` | Key format: SHA-256 of `tool::provider::url::params`; stored under `~/.cache/loom/{DATE-ISO}/`. |
| `research_cache_stats` | **EXISTS** | `src/loom/tools/core/cache_mgmt.py` | File count, total bytes, days present. |
| `research_cache_clear` | **EXISTS** | `src/loom/tools/core/cache_mgmt.py` | Removes entries older than N days (default from `CACHE_TTL_DAYS`). |

---

## 8. Session Management

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `SessionManager` (singleton, SQLite-backed, TTL, LRU eviction) | **EXISTS** | `src/loom/sessions.py` | Enforces max 8 sessions, auto-evicts oldest. Profiles stored in `~/.loom/sessions/`. |

---

## 9. Security & Validation

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `validate_url` (SSRF protection) | **EXISTS** | `src/loom/validators.py` | Blocks private, loopback, link-local, multicast, reserved, unspecified IPs; validates DNS A/AAAA records; caches resolved IPs; supports `.onion` via `TOR_ENABLED`. |
| `LLM_DAILY_COST_CAP_USD` enforcement | **EXISTS** | `src/loom/tools/llm/llm.py` | Aborts if daily spend exceeds cap. |
| `RESEARCH_MAX_COST_USD` enforcement | **EXISTS** | `src/loom/tools/core/deep.py` | Per-research cost limit checked before LLM calls. |
| `MAX_SPIDER_URLS` limit | **EXISTS** | `src/loom/config.py`, `src/loom/validators.py` | Default 100. |
| `MAX_CHARS_HARD_CAP` limit | **EXISTS** | `src/loom/config.py`, `src/loom/validators.py` | Default 200K. |
| `SPIDER_CONCURRENCY` limit | **PARTIAL** | `src/loom/config.py`, `src/loom/tools/core/spider.py` | Docs say default 5; code default is **10** (`Field(default=10, ge=1, le=20)`). |
| Input validation (Pydantic v2) | **EXISTS** | `src/loom/params/` | `core.py`, `research.py`, `llm.py`, `security.py`, etc. |
| Session name validation | **EXISTS** | `src/loom/sessions.py` | Regex: lowercase alphanumeric, underscore, hyphen, max 32 chars. |
| Provider enum checking | **EXISTS** | `src/loom/tools/core/search.py` | Validates against known provider strings. |

---

## 10. Configuration Keys

All keys listed in `architecture.md` are present and validated in `src/loom/config.py` (Pydantic `ConfigModel`).

| Key | Status | File Path | Notes |
|-----|--------|-----------|-------|
| `SPIDER_CONCURRENCY` | **EXISTS** | `src/loom/config.py` | Default 10 (see discrepancy above). |
| `EXTERNAL_TIMEOUT_SECS` | **EXISTS** | `src/loom/config.py` | Default 30. |
| `MAX_CHARS_HARD_CAP` | **EXISTS** | `src/loom/config.py` | Default 200_000. |
| `MAX_SPIDER_URLS` | **EXISTS** | `src/loom/config.py` | Default 100. |
| `FETCH_AUTO_ESCALATE` | **EXISTS** | `src/loom/config.py` | Default `True`. |
| `CACHE_TTL_DAYS` | **EXISTS** | `src/loom/config.py` | Default 30. |
| `DEFAULT_SEARCH_PROVIDER` | **EXISTS** | `src/loom/config.py` | Default `exa`. |
| `DEFAULT_ACCEPT_LANGUAGE` | **EXISTS** | `src/loom/config.py` | Default `en-US,en;q=0.9,ar;q=0.8`. |
| `RESEARCH_SEARCH_PROVIDERS` | **EXISTS** | `src/loom/config.py` | Default `["exa", "brave"]`. |
| `LLM_DEFAULT_CHAT_MODEL` | **EXISTS** | `src/loom/config.py` | Default `meta/llama-4-maverick-17b-128e-instruct`. |
| `LLM_DEFAULT_EMBED_MODEL` | **EXISTS** | `src/loom/config.py` | Default `nvidia/nv-embed-v2`. |
| `LLM_DEFAULT_TRANSLATE_MODEL` | **EXISTS** | `src/loom/config.py` | Default `moonshotai/kimi-k2-instruct`. |
| `LLM_MAX_PARALLEL` | **EXISTS** | `src/loom/config.py` | Default 12. |
| `LLM_DAILY_COST_CAP_USD` | **EXISTS** | `src/loom/config.py` | Default 10.0. |
| `LLM_CASCADE_ORDER` | **EXISTS** | `src/loom/config.py` | Default list (see discrepancy above). |
| `RESEARCH_EXPAND_QUERIES` | **EXISTS** | `src/loom/config.py` | Default `True`. |
| `RESEARCH_EXTRACT` | **EXISTS** | `src/loom/config.py` | Default `True`. |
| `RESEARCH_SYNTHESIZE` | **EXISTS** | `src/loom/config.py` | Default `True`. |
| `RESEARCH_GITHUB_ENRICHMENT` | **EXISTS** | `src/loom/config.py` | Default `True`. |
| `RESEARCH_MAX_COST_USD` | **EXISTS** | `src/loom/config.py` | Default 0.50. |
| `RESEARCH_COMMUNITY_SENTIMENT` | **EXISTS** | `src/loom/config.py` | Default `False`. |
| `RESEARCH_RED_TEAM` | **EXISTS** | `src/loom/config.py` | Default `False`. |
| `RESEARCH_MISINFO_CHECK` | **EXISTS** | `src/loom/config.py` | Default `False`. |
| `LOG_LEVEL` | **EXISTS** | `src/loom/config.py` | Default `INFO`. |
| `LOOM_HOST` | **EXISTS** | `src/loom/config.py` | Default `127.0.0.1`. |
| `LOOM_PORT` | **EXISTS** | `src/loom/config.py` | Default 8787. |
| `LOOM_CONFIG_PATH` | **EXISTS** | `src/loom/config.py` | Default `./config.json`. |
| `LOOM_CACHE_DIR` | **EXISTS** | `src/loom/config.py`, `src/loom/cache.py` | Default `~/.cache/loom`. |
| `LOOM_SESSIONS_DIR` | **EXISTS** | `src/loom/config.py`, `src/loom/sessions.py` | Default `~/.loom/sessions`. |

---

## 11. Tool Dependency Graph

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `research_llm_query_expand` | **EXISTS** | `src/loom/tools/llm/llm.py` | Used by `research_deep` Stage 1. |
| `research_llm_extract` | **EXISTS** | `src/loom/tools/llm/llm.py` | Used by `research_deep` Stage 5. |
| `research_llm_summarize` | **EXISTS** | `src/loom/tools/llm/llm.py` | Defined but **not** invoked by `research_deep`. |
| `research_llm_answer` | **EXISTS** | `src/loom/tools/llm/llm.py` | Used by `research_deep` Stage 12. |
| `research_llm_classify` | **EXISTS** | `src/loom/tools/llm/llm.py` | Used indirectly by misinfo check path. |
| `research_github_readme` | **EXISTS** | `src/loom/tools/core/github.py` | Used by `research_deep` Stage 7. |
| `research_github_releases` | **EXISTS** | `src/loom/tools/core/github.py` | Available; not called by `research_deep`. |

---

## 12. Performance Notes

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| `asyncio.Semaphore` bounded concurrency | **EXISTS** | `src/loom/tools/core/spider.py` | Concurrency cap read from `SPIDER_CONCURRENCY`. |
| SHA-256 content-hash caching | **EXISTS** | `src/loom/cache.py` | Daily directory structure; gzip compression. |
| `EXTERNAL_TIMEOUT_SECS` enforcement | **EXISTS** | `src/loom/config.py`, `src/loom/validators.py`, `src/loom/tools/core/spider.py` | 30 s default; inner fetch timeout derived from it. |
| Cost tracking / abort on cap exceeded | **EXISTS** | `src/loom/tools/llm/llm.py`, `src/loom/tools/core/deep.py` | Real-time estimation; aborts if `RESEARCH_MAX_COST_USD` or `LLM_DAILY_COST_CAP_USD` exceeded. |

---

## 13. Deployment Topology & MCP Session Flow

| Component | Status | File Path | Notes |
|-----------|--------|-----------|-------|
| FastMCP `streamable-http` transport | **EXISTS** | `src/loom/server.py` | `app.run(transport="streamable-http")`. |
| `/` endpoint (server info) | **EXISTS** | `src/loom/routes.py` | Returns service name, version, tool count, endpoints. |
| `/health` endpoint | **EXISTS** | `src/loom/routes.py` | Returns uptime, tool count, validation status, memory. |
| `/mcp` endpoint (JSON-RPC over SSE) | **EXISTS** | `src/loom/server.py` | Handled natively by FastMCP. |
| `LOOM_API_KEY` auth | **EXISTS** | `src/loom/api_auth.py`, `src/loom/jwt_auth.py` | Bearer token validation middleware. |

---

## Discrepancies Summary (PARTIAL Items)

1. **HTTP fetch library** — Architecture specifies `httpx`; `research_fetch` uses `requests` (`src/loom/tools/core/fetch.py`).
2. **Dynamic fetch backend** — Architecture says "Playwright + Camoufox"; `research_fetch` dynamic mode only uses Playwright. Camoufox is exposed as a separate tool (`research_camoufox`) rather than an escalation step inside fetch.
3. **SPIDER_CONCURRENCY default** — Architecture says default `5`; code default is `10` (`src/loom/config.py`).
4. **LLM_CASCADE_ORDER default** — Architecture says `[nvidia, openai, anthropic, vllm]`; code default is `[groq, nvidia, deepseek, gemini, moonshot, openai, anthropic, ollama, vllm]` (`src/loom/provider_router.py`).
5. **Stage 6 Relevance Ranking** — Architecture describes a distinct ranking stage; `research_deep` performs inline result selection and does **not** call the existing `research_llm_summarize` tool for ranking.

---

*End of cross-match analysis.*
