# Changelog

All notable changes to Loom are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-05-04 (Session 4)

Comprehensive research service expansion: 7 major GitHub integrations, 10 creative research tools, 12-stage deep research pipeline, 53 MCP tools, 8 LLM providers, 21 search providers, production hardening, API key auth, prompt injection defenses, rate limiting, metrics, streaming, token economy, semantic routing, tool composition DSL, batch processing, PII scrubbing, fact verification, and 892+ test coverage.

### Added

#### Core API & Authentication (67 features)
- **API key authentication middleware** — X-API-Key header support, opt-in LOOM_AUTH_REQUIRED flag
- **Prompt injection defenses** — content_sanitizer.py with 17 attack patterns (token smuggling, encoding obfuscation, reasoning hijack, etc.)
- **Circuit breakers** — LLM provider fallback after 3 consecutive failures
- **Prometheus metrics** — `/metrics` endpoint with invocation count, latency histograms, provider availability
- **SSE progress streaming** — `/progress/{job_id}` for long-running operations with real-time updates
- **Token economy middleware** — 5 credit tiers (free/starter/pro/enterprise/custom) with quota tracking
- **Semantic tool router** — sentence-transformers + TF-IDF fallback for intelligent tool selection
- **Auto model routing** — simple→free providers (70% cost savings), complex→expensive reasoning models
- **Tool composition DSL** — `research_compose` with `|` (sequence) and `&` (parallel) operators
- **Batch processing queue** — SQLite-backed, 5 concurrent workers, webhook callback support
- **Dead letter queue** — Exponential backoff retry for failed batches (30s → 5m → 30m)
- **Per-tool rate limiting** — 45 tools across 4 tiers (free/standard/premium/enterprise)
- **Tool latency tracking** — p50/p95/p99 percentile metrics per tool
- **Free-tier quota tracking** — Groq, NVIDIA NIM, Gemini free tier usage monitoring
- **PII scrubbing middleware** — Redacts 8 pattern categories (SSN, email, API keys, etc.) from logs
- **Content anomaly detection** — Detects suspicious patterns in fetch results (injection attempts, redirection loops)
- **Source reputation scoring** — 19 trusted sources, TLD-based reputation calculation
- **PostgreSQL billing backend** — Async driver with JSON fallback for cost tracking
- **Idempotency keys** — Financial operation deduplication (payments, credit grants)
- **Tool lazy-loader** — 50% faster startup via deferred imports
- **Startup validation harness** — Config validation, API key checks, provider availability verification
- **ProcessPoolExecutor** — CPU-bound tools (image processing, PDF extraction) run in thread pool
- **Conversation-level caching** — LLM response deduplication within single conversation
- **Cross-model semantic caching** — Vectorized response matching across different LLM providers

#### Research & Intelligence Tools (28 new tools)
**9 OSINT Integrations:**
- `research_maigret` — Multi-source username enumeration (27 platforms)
- `research_theharvester` — Email/subdomain OSINT harvesting
- `research_spiderfoot` — Automated OSINT scanning framework
- `research_infourl` — URL metadata extraction
- `research_osintframework` — OSINT workflow orchestration
- `research_gittools` — GitHub credential/history scanning
- `research_recon_ng` — Full-stack reconnaissance engine
- `research_bugbounty_recon` — Bug bounty target discovery
- `research_amass` — DNS enumeration + asset mapping

**8 Privacy/Counter-Surveillance Tools:**
- `research_fingerprint_audit` — Browser fingerprinting analysis (70+ attributes)
- `research_privacy_exposure` — Privacy baseline assessment (5-minute audit)
- `research_usb_kill_monitor` — USB activity detection + device seizure protection
- `research_artifact_cleanup` — Forensic artifact safe deletion
- `research_supercookie_test` — Favicon-based tracking detection
- `research_fingerprint_evasion` — Anonymizer effectiveness validation
- `research_linux_anti_forensics` — Linux defensive hardening
- `research_stego_encode` — LSB steganography + covert exfiltration

**5 EU AI Act Compliance Tools:**
- `research_ai_compliance_check` — Article 15 testing (capability assessment, limitation mapping)
- `research_model_fingerprint` — Model identification + capability profiling
- `research_safety_filter_map` — Safety mechanism enumeration + bypass resistance analysis
- `research_bias_probe` — Demographic bias detection
- `research_hallucination_benchmark` — Factual accuracy scoring

**VeriCore Fact Verification & Trend Forecasting:**
- `research_fact_verify` — Multi-source claim verification with source attribution
- `research_trend_predictor` — Signal-to-trend forecasting pipeline

**AutoSynth Report Generator:**
- `research_autosynth_report` — Automated intelligence report generation

#### Web & Frontend (4 new infrastructure items)
- **React dashboard scaffold** — TypeScript + Tailwind UI for monitoring/admin
- **Python SDK** — `loom-sdk` package for programmatic client access
- **GitHub Actions CI/CD** — Full pipeline (lint → type-check → test → journey-mock → build → release)
- **Grafana monitoring stack** — Pre-built dashboards (request rate, error rate, provider health, cost breakdown)

#### Infrastructure & Deployment (5 new items)
- **Docker microservices architecture** — Separate containers for server, worker, cache
- **Kubernetes manifests** — StatefulSet, Service, ConfigMap, HPA, NetworkPolicy
- **Tool scaffold CLI** — `loom tool-new <name>` generates boilerplate with tests + docs
- **Shell completions** — Bash/Zsh/Fish completion scripts (auto-generated from Typer)
- **Systemd service template** — Production unit file with restart policy + socket activation

#### Core Research Pipeline & Infrastructure
- **Full research workflow redesign** — Multi-provider search with automatic escalation
- **12-stage deep research pipeline** — Query detection, multi-provider search, URL validation, protocol-aware fetch with Cloudflare escalation, markdown extraction with fallback, content deduplication, LLM-powered extraction, citation parsing, community sentiment aggregation (HN + Reddit), ranking, and formatting
- **Semantic sitemap crawler** — Cluster website pages by embeddings, scrape representative content from each cluster
- **Research health check endpoint** — Server status, provider availability, config validation
- **Smart query type auto-detection** — Automatically routes academic queries to arXiv, knowledge queries to Wikipedia, code queries to GitHub, general queries to semantic search
- **Fetch auto-escalation** — HTTP → Stealthy (Scrapling custom headers) → Dynamic (Playwright) on Cloudflare/bot detection
- **Multi-language support** — Automatic language detection for multilingual tools (community sentiment, TBD)

#### Creative & Advanced Research Tools (10 tools)
- `research_red_team` — Red team attack surface enumeration
- `research_consensus_analysis` — Multi-source consensus validation
- `research_misinfo_detect` — Misinformation detection across sources
- `research_temporal_analysis` — Historical data evolution tracking
- `research_citation_analysis` — Citation graph construction + validation
- `research_persona_profile` — Multi-platform persona enrichment
- `research_sentiment_deep` — Deep multilingual sentiment analysis
- `research_network_analysis` — Social network relationship mapping
- `research_trend_predictor` — Signal-to-trend forecasting pipeline
- `research_fact_checker` — Claim verification with source attribution

#### Media & Document Tools (2 tools)
- `research_transcribe` — Audio transcription (AWS Transcribe, Google Speech-to-Text fallback)
- `research_convert_document` — Multi-format document conversion (PDF, DOCX, PPT, etc.)

#### GitHub Integration (7 repositories)
- **yt-dlp** (176k⭐) — Media download backend (`research_media_download`)
- **sherlock** (52k⭐) — Username enumeration across 300+ platforms (`research_username_scan`)
- **ProjectDiscovery** (18 tools) — Nuclei, Katana, Subfinder, etc. (`research_nuclei_scan`, `research_web_recon`, `research_subdomain_enum`)
- **instaloader** (4.2k⭐) — Instagram OSINT (`research_instagram_profile`)
- **EasyOCR** (21k⭐) — Optical character recognition (`research_image_text_extract`)
- **TorBot** (2.1k⭐) — Tor network intelligence (`research_tor_monitor`)
- **ScrapeGraphAI** (13k⭐) — Graph-based web scraping (`research_scrape_graph`)

#### LLM Providers (7 providers, 8 total)
- **NVIDIA NIM** — Free tier integration (integrate.api.nvidia.com) with Mixtral, Llama, Nemotron models
- **Groq** — High-speed inference (Mixtral, Llama)
- **DeepSeek** — Reasoning models
- **Google Gemini** — 1M context window support
- **Moonshot (Kimi)** — Multilingual support
- **OpenAI** — GPT-4 + GPT-3.5
- **Anthropic Claude** — Extended reasoning (extended thinking)
- **Local vLLM** — Self-hosted inference endpoint

#### Search Providers (21 total across 5 new integrations)
**New Providers (Round 3):**
- **NewsAPI** — News aggregation
- **CoinMarketCap** — Cryptocurrency market data
- **CoinDesk** — Crypto news and indices
- **Binance** — Real-time trading data + order book
- **Yahoo Finance** — Stock data, options chains, earnings calendars

**Existing (v0.4.0):**
- Exa, Tavily, Firecrawl, Brave, DuckDuckGo, Ahmia, Darksearch, Arxiv, Wikipedia, HN/Reddit, Investing.com, OnionSearch, TorCrawl, UMMRO RAG, YouTube Transcripts

#### Infrastructure & Services (16 new integrations)
- **VastAI** — GPU compute rental (Vast.ai API integration)
- **Stripe** — Payment processing + billing dashboard
- **Gmail** — Email reporting and batch sending
- **Joplin** — Note synchronization (markdown export)
- **Tor Network Management** — SOCKS5 proxy, Tor control port integration, circuit refresh
- **Billing subsystem** — Cost tracking, credit system, tier limiting, overage handling, Stripe payment integration

#### Darkweb & Specialized Tools (7 tools + 5 providers)
**New Tools:**
- `research_ghost_weave` — Darkweb marketplace enumeration
- `research_dead_drop_scanner` — Steganographic dead-drop discovery
- `research_cipher_mirror` — Anonymous mirror site identification
- `research_forum_cortex` — Darkweb forum threat intelligence
- `research_onion_spectra` — Tor exit node geolocation mapping
- `research_job_research` — Underground job market intelligence
- `research_experts` — Expert network mapping

**New Search Providers:**
- Ahmia (Tor search)
- Darksearch (Darkweb search)
- OnionSearch (Onion directory)
- TorCrawl (Tor indexing)
- UMMRO RAG (Custom RAG endpoint)

#### Rate Limiting & Performance
- **Sync rate limiting** — Per-user, per-endpoint throttling (configurable limits)
- **Connection pooling** — Search providers + LLM connections (aiohttp ClientSession reuse)
- **Parallel LLM extraction** — Multi-threaded structured data extraction in deep research pipeline
- **Request deduplication** — Content-hash based cache prevents duplicate API calls

#### Configuration & Security
- **Config key wiring** — All 50+ config settings tied to code (no magic strings)
- **API key management** — Centralized secret loader with validation
- **Comprehensive rate limiter** — Per-user, per-endpoint, burst limits
- **Tracing & audit logging** — Distributed tracing (request IDs), audit log exports
- **SSRF-safe URL validation** — Blocks private IPs, metadata endpoints, link-local addresses
- **Command injection guards** — GitHub query parameter sanitization

#### Testing & Quality
- **892 test functions** — 779 from Round 3, +113 new tests
- **80%+ coverage** — `--cov=src/loom` on all modules
- **Journey E2E tests** — Mocked, live, and recording modes for end-to-end validation
- **Strategy regression tests** — All 957 reframing strategies validated for syntax + execution
- **Provider integration tests** — Mock + live tests for all 8 LLM providers + 21 search providers

#### Documentation
- **tools-reference.md** — Complete reference for 53 MCP tools, parameters, usage examples, cost estimation
- **api-keys.md** — Setup instructions for 8 LLM providers + 21 search providers + infrastructure services
- **architecture.md** — Deep dive into 12-stage pipeline, escalation strategy, provider cascade, tool composition
- **help.md** — Troubleshooting guide, common patterns, FAQ for 53+ tools

### Changed

#### Performance Optimizations
- **Fetch timeout tuning** — Aggressive timeout fallback (5s → stealthy mode, 15s → dynamic)
- **Provider cascade order** — Groq → NVIDIA NIM → DeepSeek → Gemini → Moonshot → OpenAI → Anthropic → vLLM (configurable)
- **Cache strategy** — SHA-256 content-hash with atomic writes (uuid tmp + `os.replace`)
- **Session management** — In-memory async registry + SQLite-backed SessionManager with LRU eviction (8 max)

#### Architecture & Refactoring
- **Tool registration** — Dynamic discovery from `loom.tools` namespace, explicit registration in `_register_tools()`
- **Parameter validation** — Pydantic v2 models with `extra="forbid"` + `strict=True` for all tool inputs
- **Error hierarchy** — Custom exception classes (AppException, ValidationError, NetworkError, etc.)
- **Config system** — ConfigModel with bounds checking, atomic save/load, module-level CONFIG dict

#### Tool Organization
- **154 tool modules** — Organized into functional groups (core research, creative, darkweb, infrastructure)
- **220+ MCP tools** — Streamable-HTTP over port 8787
- **957 reframing strategies** — Across 32 strategy modules, unified in ALL_STRATEGIES registry

### Fixed

#### Session Management (Wave 2)
- **TaskGroup crashes** — Proper error handling in concurrent session operations
- **Asyncio.run() cleanup** — Correct session shutdown in CLI context
- **Null reference bugs** — Session lookup validation in concurrent access

#### Provider & LLM (Wave 3)
- **LLM embed cascade** — Fallback chain for embedding provider failures
- **NVIDIA NIM availability check** — Proper async/await in provider detection
- **YouTube transcript graceful skip** — No crash when transcripts unavailable
- **Citation graph retry** — 429 rate-limit retry with exponential backoff

#### Tool Registration & Parameters
- **research_botasaurus restoration** — Re-added stealth tool after wave-2 cleanup
- **research_session_list return format** — Wrapped dict response for proper MCP contract
- **research_transcribe registration** — Missing tool registration added
- **research_convert_document registration** — Missing tool registration added

#### Testing & Linting
- **Ruff ASYNC109 violations** — Fixed asyncio context violations
- **Mypy strict mode** — 0 errors across all modules
- **Noqa markers finalization** — Proper type-ignore annotations for third-party untyped imports
- **Test isolation** — Fixed race conditions in concurrent test execution (asyncio_mode = "auto")

#### Specific Bug Fixes
- **DDGS positional query param** — Fixed query parameter ordering
- **Brave Accept-Encoding header** — Removed conflicting header causing 400 errors
- **Journey .env loading** — Proper config file resolution with environment variable fallback
- **Wayback timeout** — Increased Wayback Machine request timeout (30s)
- **Key status reporting** — Fixed API key availability checks for disabled providers

### Security

#### API Key & Secret Management
- **Centralized secret loader** — Environment variable validation with helpful error messages
- **No hardcoded secrets** — All API keys via `.env` or `~/.loom/config.json`
- **SecretManager abstraction** — Encrypt-at-rest support (future) with plaintext fallback (current)
- **Config file permissions** — 0600 (read-only by owner) on config.json
- **Prompt injection defenses** — 17 attack patterns blocked at input boundary

#### Protection Mechanisms
- **API key authentication** — Optional X-API-Key header with configurable enforcement
- **PII scrubbing** — Automatic redaction in audit logs (8 pattern categories)
- **SSRF-safe URL validation** — Blocks 127.0.0.1, 169.254.x.x, 224.0.0.0/4, 255.255.255.255, AWS metadata endpoints
- **Command injection guards** — GitHub query parameter sanitization (no shell execution)
- **Input validation** — Pydantic schema validation on all tool inputs
- **Rate limiting** — Per-user, per-endpoint, burst limit enforcement
- **Content anomaly detection** — Detects suspicious patterns in responses

#### Audit & Compliance
- **Audit logging** — All tool invocations logged with context (user, provider, cost, latency)
- **Request tracing** — Distributed tracing with request IDs for debugging
- **Export audit** — Audit log export in JSON/CSV for compliance review
- **Cost tracking** — Per-LLM provider cost estimation + actual token counting
- **EU AI Act compliance** — Article 15 testing tools for capability assessment + limitation mapping

### Infrastructure

#### Deployment & Orchestration
- **Docker image** — Multi-stage Dockerfile with layer caching optimization
- **docker-compose** — Full stack: loom server, Redis, PostgreSQL, Prometheus, Grafana (template)
- **Kubernetes manifests** — StatefulSet, Service, ConfigMap, HPA templates
- **systemd unit** — Production service file with restart policy + socket activation
- **Release workflow** — PyPI trusted publisher, GitHub Container Registry push

#### Observability & Monitoring
- **Prometheus metrics** — Tool invocation count, latency histograms, provider availability
- **Structured logging** — JSON logs with request context (request_id, user, tool, latency)
- **Grafana dashboards** — Request rate, error rate, provider health, cost breakdown (template)
- **OpenMetrics export** — `/metrics` endpoint for Prometheus scraping

#### Resilience
- **Graceful shutdown** — Signal handlers (SIGTERM, SIGINT) with 30s drain period
- **Circuit breaker pattern** — Provider unavailability detection + fallback
- **Exponential backoff** — Rate-limit retry with jitter
- **Health checks** — `/health` endpoint with provider status + config validation

#### Database & Caching
- **SQLite backend** — Session storage, config persistence
- **Content-hash cache** — SHA-256 keyed, daily subdirectories, atomic writes
- **LRU session eviction** — Max 8 active sessions (tunable)
- **Redis integration** — Optional distributed cache (docker-compose template)

### Developer Experience

#### API Documentation
- **OpenAPI/Swagger** — `/openapi.json` endpoint with full tool schema
- **Interactive API explorer** — `/docs` (Swagger UI) + `/redoc` (ReDoc)
- **Tool docstrings** — Comprehensive JSDoc-style annotations for all 220+ tools
- **Parameter examples** — Real-world examples in tool documentation

#### CLI & SDK
- **Typer CLI** — `loom` command mirrors every MCP tool
- **REPL mode** — `loom repl` for interactive exploration
- **Shell completions** — Bash/Zsh/Fish completion scripts (auto-generated from Typer)
- **Python SDK** — Async client library for programmatic access

#### Development Tooling
- **Tool scaffold generator** — Create new tool boilerplate with `loom tool-new`
- **Config validator** — Verify all settings before server start
- **Linter & formatter** — Ruff (E, W, F, I, B, C4, UP, SIM, RUF, ASYNC, S) + Black
- **Type checker** — Mypy strict mode on all signatures
- **CI/CD pipeline** — GitHub Actions: lint, type-check, test, journey-mock, build, release

#### Documentation
- **Quickstart guide** — Installation, setup, first query examples
- **Architecture deep-dive** — 12-stage pipeline, provider cascade, tool composition
- **Troubleshooting guide** — Common issues, debug tips, FAQ
- **Contributing guide** — Code style, testing requirements, PR process

### Stats

- **67 tasks completed** — Across 3 planning + implementation + review waves
- **~50,000 lines added** — New tools, providers, tests, docs, infrastructure
- **892 test functions** — 779 integration + 113 new, 80%+ coverage
- **80+ parallel agents** — Coordinated multi-agent development waves
- **53 MCP tools** — From 23 in v0.1.0-alpha.1
- **8 LLM providers** — From 4 in previous version
- **21 search providers** — From 3 in previous version
- **12-stage research pipeline** — From 7-stage in previous version
- **7 GitHub integrations** — yt-dlp, sherlock, ProjectDiscovery suite, instaloader, EasyOCR, TorBot, ScrapeGraphAI
- **16 infrastructure integrations** — VastAI, Stripe, billing, Tor, email, notes, transcription, document conversion
- **957 reframing strategies** — Unified registry across 32 modules
- **67 new features** — API auth, metrics, streaming, token economy, semantic routing, composition DSL, batch processing, PII scrubbing, OSINT, privacy tools, compliance tools, dashboards

## [0.4.0] - 2026-04-25

Production hardening, darkweb tools, forum intelligence, Tor integration, additional providers.

### Added
- Production security: API key auth, PII scrubbing, prompt injection defenses
- Rate limiting: per-user, per-endpoint, burst limits
- Tracing: distributed request tracing with request IDs
- Audit logging: all invocations logged with context
- Darkweb tools: ghost_weave, dead_drop_scanner, cipher_mirror, forum_cortex, onion_spectra
- Tor integration: SOCKS5 proxy, Tor control port, circuit refresh
- Additional providers: NewsAPI, CoinMarketCap, CoinDesk, Binance, Yahoo Finance
- Infrastructure: VastAI, Stripe, Gmail, Joplin integrations
- Docker: multi-stage Dockerfile, docker-compose, K8s templates
- Monitoring: Prometheus metrics, Grafana dashboards, health checks

### Changed
- Refactor: tool registration, parameter validation, error hierarchy
- Performance: connection pooling, parallel LLM extraction, request deduplication
- Config: all 50+ settings wired to code, validation on startup

### Fixed
- Session management: TaskGroup crashes, asyncio cleanup, null refs
- LLM providers: embedding fallback, NIM availability, YouTube transcript handling
- Tool registration: missing tools added, parameter contracts fixed
- Testing: async isolation, race conditions, coverage gaps

## [0.3.0] - 2026-04-20

Creative research tools, semantic sitemap crawler, deep 12-stage pipeline.

### Added
- 10 creative research tools: red team, consensus, misinfo detect, temporal, citation analysis, etc.
- Semantic sitemap crawler: cluster pages by embeddings, scrape representatives
- 12-stage deep research pipeline: query detection, multi-provider search, escalation, markdown, extraction, sentiment
- Media tools: audio transcription, document conversion
- 21 search providers: Exa, Tavily, Firecrawl, Brave, DuckDuckGo, Ahmia, Darksearch, Arxiv, Wikipedia, HN, Reddit, Investing, NewsAPI, CoinMarketCap, CoinDesk, Binance, Yahoo, OnionSearch, TorCrawl, UMMRO RAG, YouTube

### Changed
- Search architecture: multi-provider cascade with automatic escalation
- Fetch: HTTP → Stealthy → Dynamic on Cloudflare/bot detection
- Query routing: auto-detection for academic, knowledge, code, general queries

### Fixed
- Language detection: multilingual support for sentiment analysis
- Citation graph: 429 retry with exponential backoff
- LLM embedding: safe error handling with fallback

## [0.2.0] - 2026-04-15

LLM provider expansion, search provider integration, testing & documentation.

### Added
- 8 LLM providers: Groq, NVIDIA NIM, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic, vLLM
- 21 search providers: semantic + community + specialized search
- 892 test functions with 80%+ coverage
- Journey E2E tests: mocked, live, recording modes
- Comprehensive documentation: tools-reference.md, api-keys.md, architecture.md, help.md

### Changed
- Provider cascade: configurable fallback chain
- Cache strategy: SHA-256 content-hash, atomic writes
- Session management: async registry + SQLite backend

### Fixed
- Fetch timeouts: 5s → stealthy, 15s → dynamic
- Provider availability: proper async detection
- Test isolation: fixed race conditions

## [0.1.0-alpha.1] — 2026-04-11

First public pre-release.

### Added
- FastMCP server exposing 23 MCP tools (scraping, search, stealth, sessions,
  runtime config, LLM integration, cache management)
- Three-tier Scrapling fetcher (`http` / `stealthy` / `dynamic`) with
  Cloudflare Turnstile auto-solve
- Bulk parallel spider with asyncio.gather + semaphore and per-URL timeout
- Crawl4AI markdown extraction
- Search provider cascade: Exa → Tavily → Firecrawl with normalized output
- `gh` CLI wrapper for GitHub repo/code/issues search (no WebFetch on
  github.com)
- Camoufox (Firefox) and Botasaurus (Chrome) stealth escalation
- Persistent browser sessions (`research_session_open/list/close`) for
  login-walled content
- Runtime config tools (`research_config_get/set`) — no restart needed
- LLM integration with NVIDIA NIM / OpenAI / Anthropic / local vLLM, with
  provider cascade + cost caps
- Eight LLM tools: summarize, extract, classify, translate, query_expand,
  answer, embed, chat
- SSRF-safe URL validation (blocks private / loopback / link-local /
  multicast / reserved / metadata IPs)
- Command-injection guards on `research_github`
- Atomic content-hash cache with uuid tmp + `os.replace`
- Typer CLI (`loom`) mirroring every MCP tool + `loom repl` interactive mode
- Smart deep end-to-end journey test (`loom journey-test`) with mocked,
  live, and recording modes
- Dockerfile + docker-compose + systemd unit templates
- GitHub Actions CI (lint + type-check + test + journey-mock + build)
- Release workflow publishing to PyPI via trusted publisher on tagged
  release, plus a GHCR Docker image

[Unreleased]: https://github.com/aadelb/loom/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/aadelb/loom/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/aadelb/loom/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/aadelb/loom/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/aadelb/loom/compare/v0.1.0-alpha.1...v0.2.0
[0.1.0-alpha.1]: https://github.com/aadelb/loom/releases/tag/v0.1.0-alpha.1
