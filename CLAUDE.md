# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Loom

Loom is a Python MCP (Model Context Protocol) server that exposes 94 research tools over streamable-HTTP (port 8787). It wraps scraping (Scrapling, Crawl4AI, Camoufox, Botasaurus), search across 21 providers (Exa, Tavily, Firecrawl, Brave, DuckDuckGo, Arxiv, Wikipedia, Hacker News, Reddit, NewsAPI, Binance, CoinMarketCap, CoinDesk, Ahmia, Darksearch, UMMRO RAG, OnionSearch, TorCrawl, DarkWeb CTI, Robin OSINT, and Investing), 8 LLM providers (Groq, NVIDIA NIM, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic, vLLM), infrastructure tools (VastAI, Stripe, Billing), communication tools (Email, Joplin notes), media tools (Audio transcription, Document conversion), Tor/darkweb tools (Tor status, new identity, cipher mirror, forum cortex, onion spectra, ghost weave, dead drop scanner), GitHub CLI, persistent browser sessions, 11 creative research tools, and a content-hash cache into a single MCP service. It also ships a Typer CLI (`loom`) that calls the MCP server as a client.

## Commands

```bash
# Install (editable, all extras)
pip install -e ".[all]"

# Run MCP server
loom serve                        # default: 127.0.0.1:8787
loom-server                       # alternative entry point

# Lint & format
ruff check src tests              # lint
ruff check --fix src tests        # lint + autofix
ruff format src tests             # format

# Type check
mypy src

# Tests (run on Hetzner, not local Mac)
pytest                            # full suite with coverage
pytest tests/test_config.py       # single file
pytest -k "test_validate_url"     # single test by name
pytest -m "not live"              # skip network-hitting tests
pytest --timeout=300 --maxfail=5  # safety flags for remote runs

# Journey tests
pytest tests/journey_e2e.py       # end-to-end journey test

# Pre-commit
pre-commit run --all-files
```

## Architecture

```
src/loom/
  server.py        FastMCP instance creation + tool registration (create_app / _register_tools)
  cli.py           Typer CLI; each subcommand calls MCP tools via streamable-http client
  config.py        Pydantic v2 ConfigModel + module-level CONFIG dict; atomic save/load
  params.py        Pydantic v2 parameter models per tool (FetchParams, SpiderParams, etc.)
  validators.py    SSRF-safe URL validation, character capping, GitHub query sanitization
  cache.py         Content-hash CacheStore (SHA-256, daily dirs, atomic writes, singleton)
  sessions.py      Persistent browser session management (in-memory registry + SQLite SessionManager)
  journey.py       End-to-end journey test runner (mocked/live/record modes)
  tools/           One module per tool family (94 tools total):
    fetch.py       research_fetch (Scrapling 3-tier: http/stealthy/dynamic + Cloudflare auto-escalation)
    spider.py      research_spider (concurrent multi-URL fetch)
    markdown.py    research_markdown (Crawl4AI + Trafilatura fallback for HTML-to-markdown)
    search.py      research_search (multi-provider: 21 search engines including exa/tavily/firecrawl/brave/ddgs/arxiv/wikipedia/hackernews/reddit/newsapi/crypto/ummro/onionsearch/torcrawl/darkweb_cti/robin_osint)
    deep.py        research_deep (12-stage pipeline: query detection → search → fetch → escalation → markdown → extraction)
    github.py      research_github (gh CLI wrapper)
    stealth.py     research_camoufox + research_botasaurus
    cache_mgmt.py  research_cache_stats + research_cache_clear
    creative.py    11 creative research tools (red_team, multilingual, consensus, misinfo_check, temporal_diff, citation_graph, ai_detect, curriculum, community_sentiment, wiki_ghost, semantic_sitemap)
    enrich.py      research_wayback (Wayback Machine recovery)
    experts.py     research_expertise (expertise finder)
    llm.py         8 LLM tools (summarize/extract/classify/translate/expand/answer/embed/chat)
    vastai.py      research_vastai_search + research_vastai_status (GPU compute marketplace)
    billing.py     research_usage_report + research_stripe_balance (billing and usage tracking)
    email_report.py research_email_report (email delivery)
    joplin.py      research_save_note + research_list_notebooks (note-taking)
    tor.py         research_tor_status + research_tor_new_identity (Tor network management)
    transcribe.py  research_transcribe (audio to text)
    document.py    research_convert_document (document format conversion)
    stylometry.py    research_stylometry (author fingerprinting)
    deception_detect.py  research_deception_detect (linguistic deception cues)
    persona_profile.py   research_persona_profile (Big Five personality)
    radicalization_detect.py  research_radicalization_detect (extremism NLP)
    sentiment_deep.py    research_sentiment_deep (8-emotion detection)
    network_persona.py   research_network_persona (forum social graph)
    domain_intel.py      research_whois + research_dns_lookup + research_nmap_scan
    pdf_extract.py       research_pdf_extract + research_pdf_search
    text_analyze.py      research_text_analyze (NLTK NER/keywords/readability)
    screenshot.py        research_screenshot (Playwright page capture)
    rss_monitor.py       research_rss_fetch + research_rss_search
    social_intel.py      research_social_search + research_social_profile
    cert_analyzer.py     research_cert_analyze (SSL/TLS inspection)
    security_headers.py  research_security_headers (HTTP header audit)
    breach_check.py      research_breach_check + research_password_check
    ip_intel.py          research_ip_reputation + research_ip_geolocation
    cve_lookup.py        research_cve_lookup + research_cve_detail
    urlhaus_lookup.py    research_urlhaus_check + research_urlhaus_search
    geoip_local.py       research_geoip_local (MaxMind offline)
    image_intel.py       research_exif_extract + research_ocr_extract
  providers/       8 LLM providers + 21 search providers + specialized data providers:
    base.py        Abstract LLMProvider + LLMResponse dataclass + _estimate_cost
    groq_provider.py GROQ API
    nvidia_nim.py  NVIDIA NIM free tier (integrate.api.nvidia.com)
    deepseek_provider.py DeepSeek API
    gemini_provider.py Google Gemini API
    moonshot_provider.py Moonshot (Kimi) API
    openai_provider.py OpenAI API
    anthropic_provider.py Anthropic Claude API
    vllm_local.py  Local vLLM endpoint
    exa.py, tavily.py, firecrawl.py, brave.py, ddgs.py - Search providers (5)
    arxiv_search.py, wikipedia_search.py, hn_reddit.py - Academic/community (3)
    newsapi_search.py, coindesk_search.py, coinmarketcap.py, binance_data.py - Data APIs (4)
    ahmia_search.py, darksearch_search.py, ummro_rag.py - Specialized search (3)
    onionsearch.py, torcrawl.py, darkweb_cti.py, robin_osint.py - Darkweb/OSINT (4)
    investing_data.py - Financial data
    youtube_transcripts.py - YouTube transcript extraction
```

### Key patterns

- **Tool registration**: `server.py:_register_tools()` explicitly registers each tool function with `mcp.tool()()`. LLM tools are optional (guarded by ImportError).
- **Parameter validation**: Every tool has a Pydantic model in `params.py` with `extra="forbid"` and `strict=True`. URL fields pass through `validators.validate_url()` for SSRF prevention.
- **LLM cascade**: Config key `LLM_CASCADE_ORDER` (default: groq -> nvidia_nim -> deepseek -> gemini -> moonshot -> openai -> anthropic -> vllm) controls provider fallback. Providers implement the `LLMProvider` ABC with `chat()`, `embed()`, `available()`, `close()`.
- **Cache**: SHA-256 content-hash keyed, stored in daily subdirectories (`~/.cache/loom/YYYY-MM-DD/`). Atomic writes via uuid tmp + `os.replace`. Singleton via `get_cache()`.
- **Sessions**: Two systems coexist — an in-memory async registry (global `_sessions` dict with asyncio.Lock) and a SQLite-backed `SessionManager` class with LRU eviction (max 8). Session names must match `^[a-z0-9_-]{1,32}$`.
- **Config**: `ConfigModel` in `config.py` provides validated bounds on all settings. `CONFIG` is a module-level dict updated by `load_config()`. Config file resolved via: explicit path > `$LOOM_CONFIG_PATH` > `./config.json`. All config keys are wired to code.
- **Query type auto-detection**: Deep research tool automatically detects query intent (academic → arxiv, knowledge → wikipedia, code → github, general → semantic search).
- **Fetch auto-escalation**: Single HTTP request fails on Cloudflare? Automatically escalate to stealthy mode (Scrapling custom headers), then dynamic mode (Playwright).
- **Language detection**: Multilingual and community sentiment tools auto-detect content language for accurate processing.

### 12-stage deep research pipeline

1. Query parsing & type detection
2. Provider selection (academic/knowledge/code/general)
3. Initial search across selected provider
4. Result filtering & deduplication
5. URL validation & SSRF check
6. Fetch with protocol-aware escalation
7. Markdown extraction (Crawl4AI → Trafilatura)
8. Content deduplication
9. Structured extraction (LLM-powered)
10. Citation & reference parsing
11. Community sentiment aggregation (HN + Reddit)
12. Final ranking & output formatting

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOOM_HOST` | `127.0.0.1` | Server bind address |
| `LOOM_PORT` | `8787` | Server port |
| `LOOM_CONFIG_PATH` | `./config.json` | Config file location |
| `LOOM_CACHE_DIR` | `~/.cache/loom` | Cache storage root |
| `LOOM_SESSIONS_DIR` | `~/.loom/sessions` | Session storage root |
| `TOR_ENABLED` | `false` | Enable Tor network features |
| `TOR_SOCKS5_PROXY` | `127.0.0.1:9050` | Tor SOCKS5 proxy address |
| **LLM Providers** | | |
| `GROQ_API_KEY` | - | Groq API key |
| `NVIDIA_NIM_API_KEY` | - | NVIDIA NIM API key |
| `DEEPSEEK_API_KEY` | - | DeepSeek API key |
| `GOOGLE_AI_KEY` | - | Google Gemini API key |
| `MOONSHOT_API_KEY` | - | Moonshot (Kimi) API key |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| **Search Providers** | | |
| `EXA_API_KEY` | - | Exa semantic search key |
| `TAVILY_API_KEY` | - | Tavily search key |
| `FIRECRAWL_API_KEY` | - | Firecrawl API key |
| `BRAVE_API_KEY` | - | Brave search key |
| `NEWS_API_KEY` | - | NewsAPI key |
| `UMMRO_RAG_URL` | - | UMMRO RAG endpoint |
| `COINMARKETCAP_API_KEY` | - | CoinMarketCap API key |
| `INVESTING_API_KEY` | - | Investing.com data key |
| **Infrastructure & Services** | | |
| `VASTAI_API_KEY` | - | VastAI API key |
| `STRIPE_LIVE_KEY` | - | Stripe live API key |
| `SMTP_USER` | - | Email service user |
| `SMTP_APP_PASSWORD` | - | Email service password |
| `JOPLIN_TOKEN` | - | Joplin API token |
| **Specialized** | | |
| `TOR_CONTROL_PASSWORD` | - | Tor control port password |

## Testing

- Framework: pytest with pytest-asyncio (`asyncio_mode = "auto"`)
- Coverage target: 80%+ (`--cov=src/loom`)
- Test count: 1260+ test functions across 80+ files
- Markers: `slow`, `live` (real network), `integration`
- Test structure mirrors source: `tests/test_tools/`, `tests/test_providers/`, `tests/test_integration/`
- Fixtures in `tests/conftest.py` provide temp dirs, mock HTTP transport, and sample API responses
- Journey tests (`tests/journey_e2e.py`) run the full 94 tool scenario in mocked/live/record modes

## Documentation

Four comprehensive documentation files in `docs/`:

- **tools-reference.md** — Complete reference for all 94 tools, parameters, and examples
- **api-keys.md** — API key setup for all 8 LLM providers + 21 search providers + infrastructure/communication/media services
- **architecture.md** — Deep dive into pipeline design, escalation strategy, and tool composition
- **help.md** — Troubleshooting, common patterns, and FAQ

## Code style

- Python 3.11+, type hints on all signatures
- Ruff for linting (rules: E, W, F, I, B, C4, UP, SIM, RUF, ASYNC, S) and formatting
- mypy strict mode with `pydantic.mypy` plugin
- Line length: 100
- Quote style: double

### Adding new tools

Every new tool requires ALL of:
1. Implementation in src/loom/tools/
2. Tests in tests/
3. Entry in docs/tools-reference.md with params, examples, cost
4. Entry in docs/help.md
5. Run scripts/verify_completeness.py to confirm 0 drift
