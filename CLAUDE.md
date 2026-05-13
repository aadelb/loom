# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Loom

Loom is a Python MCP (Model Context Protocol) server that exposes 440+ research and attack tools over streamable-HTTP (port 8787). It wraps scraping (Scrapling, Crawl4AI, Camoufox, Botasaurus), search across 21 providers, 8 LLM providers, infrastructure tools (VastAI, Stripe, Billing), communication tools (Email, Joplin notes), media tools (Audio transcription, Document conversion), Tor/darkweb tools, GitHub CLI, persistent browser sessions, creative research tools, killer research tools, dark research tools, intelligence tools, revolutionary tools, AI safety tools, academic integrity tools, career intelligence tools, signal detection tools, supply chain intelligence tools, plus a content-hash cache and 957 prompt reframing strategies into a single MCP service. It also ships a Typer CLI (`loom`) that calls the MCP server as a client.

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
src/loom/                        61 core modules:
  server.py                      FastMCP instance creation + tool registration (create_app / _register_tools)
  cli.py                         Typer CLI; each subcommand calls MCP tools via streamable-http client
  config.py                      Pydantic v2 ConfigModel + module-level CONFIG dict; atomic save/load
  params.py                      Pydantic v2 parameter models per tool (317 models in params/ subdirectory)
  validators.py                  SSRF-safe URL validation, character capping, GitHub query sanitization
  cache.py                       Content-hash CacheStore (SHA-256, daily dirs, atomic writes, singleton)
  sessions.py                    Persistent browser session management (in-memory registry + SQLite SessionManager)
  journey.py                     End-to-end journey test runner (mocked/live/record modes)
  
  Core Infrastructure (8 modules):
    errors.py                    Custom exception hierarchy (AppException, ValidationError, etc.)
    auth.py                      Authentication & MCP authorization layer
    tracing.py                   Structured logging + distributed tracing
    audit.py                     Audit logging for compliance & forensics
    storage.py                   Persistent KV store (SQLite backend)
    offline.py                   Offline mode fallback (cached mode)
    rate_limiter.py              Rate limiting per user/endpoint
    cicd.py                      CI/CD integration + deployment hooks
  
  Pipelines & Orchestration (10 modules):
    evidence_pipeline.py         Multi-stage evidence collection pipeline
    cross_model_transfer.py       Cross-model attack transfer learning
    context_poisoning.py          Context pollution attack pipeline
    daisy_chain.py               Multi-hop attack orchestration
    adversarial_debate.py        Adversarial peer debate framework
    model_evidence.py            Model-agnostic evidence synthesis
    pipelines.py                 Generic pipeline composition framework
    target_orchestrator.py       Target-aware attack orchestration
    constraint_optimizer.py       Multi-constraint optimization (harm/stealth/quality)
    optimization_path.py         Path finding for constraint satisfaction
  
  Scoring & Evaluation (8 modules):
    attack_scorer.py             Attack efficacy scoring (pass/fail + confidence)
    stealth_calc.py              Stealth metric calculation
    executability.py             Execution probability scoring
    quality_scorer.py            Output quality assessment
    harm_assessor.py             Harm potential evaluation
    toxicity_checker.py          Toxicity/offensiveness detection
    danger_prescore.py           Pre-execution danger assessment
    stealth_detector.py          Stealth level classification
  
  Tracking & Evolution (4 modules):
    drift_monitor.py             Model behavior drift detection
    jailbreak_evolution.py       Attack effectiveness evolution tracking
    consistency_pressure.py       Consistency constraint monitoring
    strategy_oracle.py           Strategy performance oracle (adaptive selection)
  
  Analysis & Intelligence (3 modules):
    model_profiler.py            Model capability profiling
    model_sentiment.py           Model sentiment/bias analysis
    policy_validator.py          Policy compliance validation
  
  Infrastructure & Tools (9 modules):
    semantic_cache.py            Semantic deduplication cache
    param_sweeper.py             Parameter space exploration
    mcp_security.py              MCP transport security + sandboxing
    tool_recommender.py          Tool selection recommender
    dashboard.py                 Web dashboard + monitoring UI
    bpj_generator.py             BPJ (Best-Practice Jailbreak) generation
    fuzzer.py                    Fuzzing engine for attack discovery
    consensus_builder.py         Consensus mechanisms across multiple runs
    report_gen.py                Report generation & formatting
  
  Domain-Specific (4 modules):
    arabic.py                    Arabic language attack specialization
    crescendo_loop.py            Crescendo attack loop (incremental harm)
    attack_tracker.py            Attack history & statistics tracking
    reid_auto.py                 REID (Reinforced Exploitation ID) automation
    reid_pipeline.py             REID pipeline orchestration
    offline_matrix.py            Offline decision matrix for rapid lookup
    synth_echo.py                Synthetic echo/confirmation attacks
    reports_example.py           Example report templates
    reports.py                   Report formatting utilities
  
  Legacy/Utility (5 modules):
    errors.py, __init__.py, __main__.py, orchestrator.py, scoring.py
  
  params/                        317 Pydantic v2 models:
    (auto-organized subdirectories by tool category)
    Base validation: extra="forbid", strict=True, URL fields via validators.validate_url()
  
  tools/                         440+ tools organized in 11 subdirectories:
    core/                        27 files: fetch, search, spider, markdown, deep, github, stealth, cache_mgmt
    llm/                         49 files: llm, multi_llm, prompt_reframe, creative, enrich, ask_all_models, etc.
    intelligence/                50 files: osint, threat_intel, dark_forum, social_intel, metadata_forensics, etc.
    security/                    29 files: ai_safety, cert_analyzer, pentest, compliance, cve_lookup, etc.
    privacy/                     10 files: privacy_tools, stego_detect, antiforensics, fingerprint_audit, etc.
    adversarial/                 37 files: stealth_score, hcs_scorer, attack_scorer, jailbreak_evolution, etc.
    career/                      10 files: job_signals, resume_intel, salary_synthesizer, deception_scanner, etc.
    infrastructure/              84 files: billing, vastai, slack, joplin, tor, transcribe, document, email, etc.
    backends/                    45 files: sherlock, maigret, spiderfoot, photon, instaloader, yt-dlp, etc.
    research/                    49 files: fact_checker, knowledge_graph, text_analyze, pdf_extract, rss_monitor, etc.
    monitoring/                  26 files: metrics, health, observability, telemetry, realtime_monitor, etc.
    
    reframe_strategies/          32 strategy modules (957 total strategies):
      __init__.py                ALL_STRATEGIES (unified registry across 32 modules)
      core.py                    Core reframing strategies
      advanced.py                Advanced manipulation techniques
      encoding.py                Encoding/obfuscation strategies
      jailbreak.py               Jailbreak-specific patterns
      reasoning.py               Reasoning chain exploits
      persona.py                 Persona-based attacks
      format_exploit.py          Format/encoding exploits
      attention.py               Attention hijacking
      legal.py                   Legal framework manipulation
      multiturn.py               Multi-turn conversation exploits
      specialized.py             Specialized domain attacks
      novel_2026.py              Novel 2026 techniques (937 strategies)
      multimodal.py              Multimodal attack vectors
      agent_tool.py              Agent/tool-based exploits
      token_repr.py              Token representation manipulation
      reasoning_cot.py           Chain-of-thought reasoning bypasses
      defense_evasion.py         Defense evasion tactics
      research_2026.py           Research-derived 2026 methods
      persuasion.py              Persuasion & social engineering
      advanced_novel.py          Advanced novel techniques
      skills_extracted.py        Skills from prior research
      guardrail_suite.py         Guardrail bypass suite
      arxiv_nim.py               ArXiv + NIM-derived strategies
      remaining.py               Remaining/uncategorized techniques
      reid_psychology.py         REID psychology specialization
      advanced_psychology.py     Advanced psychological manipulation
      psychology_extended.py     Extended psychology techniques
      fusion_10x.py              10x fusion strategies
      research_derived.py        Research paper-derived techniques
      arabic_attacks.py          Arabic-language attack vectors
      token_smuggling.py         Token smuggling techniques
  
  Shared Modules (28 files):
    http_helpers.py              HTTP client utilities, connection pooling, retry logic
    input_validators.py          Input sanitization, bounds checking, type coercion
    score_utils.py               Scoring algorithm utilities, normalization, aggregation
    db_helpers.py                Database operation wrappers, transaction management
    error_responses.py           @handle_tool_errors decorator, error serialization
    subprocess_helpers.py        Subprocess execution, shell escaping, timeout handling
    cli_checker.py               CLI tool detection, version checking, availability
    text_utils.py                Text processing, encoding detection, normalization
    html_utils.py                HTML parsing, DOM traversal, content extraction
    sanitization.py              XSS prevention, SQL injection prevention, path traversal
    llm_parsers.py               LLM response parsing, JSON extraction, structured output
    report_formatters.py         Report generation, Markdown/HTML/PDF export
    scoring_framework.py         Generic scoring framework for all metric types
    pipeline_runner.py           Pipeline orchestration, stage execution, result threading
    async_tool_runner.py         Async task execution, concurrency management, semaphores
    config_manager.py            Config loading, environment variable resolution, hot reload
    tool_introspection.py        Tool metadata inspection, parameter extraction
    evolution_engine.py          Strategy evolution, performance tracking, adaptation
    exif_utils.py                EXIF extraction, geolocation parsing, metadata analysis
    provider_router.py           LLM provider selection, fallback logic, cost estimation
    result_aggregator.py         Result deduplication, ranking, confidence scoring
    llm_client.py                Unified LLM client wrapper, provider abstraction
    sandbox_manager.py           Sandboxing, process isolation, resource limits
    rate_limit_manager.py        Rate limiting per user/endpoint/IP
    connection_pool_manager.py   Connection pooling, lifecycle management
    providers/llm_openai_compat.py   OpenAI-compatible base for 4 LLM providers
    providers/semaphore_registry.py  Concurrent request limiting, semaphore management
    providers/search_normalizer.py    Normalize search results across 21 search providers

  providers/                     8 LLM providers + 21 search providers:
    base.py                      Abstract LLMProvider + LLMResponse dataclass + _estimate_cost
    groq_provider.py             GROQ API (OpenAI-compatible)
    nvidia_nim.py                NVIDIA NIM free tier (OpenAI-compatible)
    deepseek_provider.py         DeepSeek API (OpenAI-compatible)
    moonshot_provider.py         Moonshot (Kimi) API (OpenAI-compatible)
    gemini_provider.py           Google Gemini API
    openai_provider.py           OpenAI API
    anthropic_provider.py        Anthropic Claude API
    vllm_local.py                Local vLLM endpoint
    exa.py, tavily.py, firecrawl.py, brave.py, ddgs.py (5 search providers)
    arxiv_search.py, wikipedia_search.py, hn_reddit.py (academic/community)
    newsapi_search.py, coindesk_search.py, coinmarketcap.py, binance_data.py (data APIs)
    ahmia_search.py, darksearch_search.py, ummro_rag.py (specialized search)
    onionsearch.py, torcrawl.py, darkweb_cti.py, robin_osint.py (darkweb/OSINT)
    investing_data.py (financial data)
    youtube_transcripts.py (YouTube transcription)
  
  billing/                       12 billing modules:
    __init__.py                  Billing subsystem exports
    cost_tracker.py              Cost tracking & estimation
    credits.py                   Credit system management
    customers.py                 Customer record management
    dashboard.py                 Billing dashboard
    isolation.py                 Cost isolation per tenant
    meter.py                     Usage metering
    overage.py                   Overage handling & billing
    retention.py                 Data retention policies
    stripe_integration.py        Stripe payment integration
    tier_limiter.py              Usage tier enforcement
    tiers.py                     Tier definitions & quotas
```

### Key patterns

- **Tool registration**: `server.py:_register_tools()` explicitly registers each tool function with `mcp.tool()()`. All tools use `@handle_tool_errors("research_tool_name")` decorator from `error_responses.py`.
- **Parameter validation**: Every tool has a Pydantic v2 model in `params/` subdirectory with `extra="forbid"` and `strict=True`. URL fields pass through `validators.validate_url()` for SSRF prevention. `_wrap_tool()` auto-validates params via `_validate_with_pydantic()`.
- **Parameter aliases**: `PARAM_ALIASES` middleware resolves legacy param names (max_results→limit, model_name→model, text→query, etc.) for backward compatibility.
- **LLM providers**: 4 providers (Groq, NVIDIA NIM, DeepSeek, Moonshot) subclass `OpenAICompatProvider` for unified API compatibility. LLM cascade (Config key `LLM_CASCADE_ORDER`) controls provider fallback. Providers implement the `LLMProvider` ABC with `chat()`, `embed()`, `available()`, `close()`.
- **Cache**: SHA-256 content-hash keyed, stored in daily subdirectories (`~/.cache/loom/YYYY-MM-DD/`). Atomic writes via uuid tmp + `os.replace`. Singleton via `get_cache()`.
- **Sessions**: Two systems coexist — an in-memory async registry (global `_sessions` dict with asyncio.Lock) and a SQLite-backed `SessionManager` class with LRU eviction (max 8). Session names must match `^[a-z0-9_-]{1,32}$`.
- **Config**: `ConfigModel` in `config.py` provides validated bounds on all settings. `CONFIG` is a module-level dict updated by `load_config()`. Config file resolved via: explicit path > `$LOOM_CONFIG_PATH` > `./config.json`. All config keys are wired to code.
- **Query type auto-detection**: Deep research tool automatically detects query intent (academic → arxiv, knowledge → wikipedia, code → github, general → semantic search).
- **Fetch auto-escalation**: Single HTTP request fails on Cloudflare? Automatically escalate to stealthy mode (Scrapling custom headers), then dynamic mode (Playwright).
- **Language detection**: Multilingual and community sentiment tools auto-detect content language for accurate processing.
- **Strategy registry**: 957 reframing strategies organized across 32 modules, unified in `ALL_STRATEGIES` dict. Strategies are indexed by name and composable for multi-stage attacks.

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
| **Authentication & CORS** | | |
| `LOOM_API_KEY` | - | Single shared API key for bearer auth |
| `LOOM_API_KEYS` | - | Comma-separated valid API keys |
| `LOOM_ALLOW_ANONYMOUS` | `false` | Allow unauthenticated access |
| `LOOM_AUTH_REQUIRED` | `false` | Enforce authentication |
| `LOOM_JWT_SECRET` | - | JWT token signing secret |
| `LOOM_CORS_ENABLED` | `true` | Enable CORS headers |
| `LOOM_CORS_ORIGINS` | `localhost:5173,localhost:3000` | Allowed CORS origins |
| **Logging & Debugging** | | |
| `LOOM_LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `text` | Log format (text/json) |
| `LOOM_DEBUG` | `false` | Debug mode |
| **Database & Storage** | | |
| `DATABASE_URL` | `postgresql://...localhost/loom_db` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `LOOM_DB_ENCRYPTION_KEY` | - | Fernet key for DB encryption |
| `LOOM_DB_ENCRYPTION_PASSWORD` | - | Password for key derivation |
| **Billing & Economy** | | |
| `LOOM_BILLING_ENABLED` | `false` | Enable billing system |
| `LOOM_TOKEN_ECONOMY` | `false` | Enable token metering |
| `LOOM_USER_ID` | `anonymous` | User ID for billing |
| `LOOM_CUSTOMER_ID` | `default` | Customer/tenant ID |
| **Performance** | | |
| `LOOM_CACHE_THRESHOLD` | `0.95` | Semantic cache similarity threshold |
| `LOOM_MAX_RETRIES` | `3` | Max retry attempts |
| `LOOM_CPU_WORKERS` | `4` | CPU worker thread count |
| **Audit** | | |
| `LOOM_AUDIT_SECRET` | - | HMAC secret for audit logs |
| `LOOM_AUDIT_DIR` | - | Audit log directory |
| **LLM Provider Endpoints** | | |
| `GROQ_ENDPOINT` | `api.groq.com/openai/v1` | Groq API endpoint |
| `NVIDIA_NIM_ENDPOINT` | `integrate.api.nvidia.com/v1` | NVIDIA NIM endpoint |
| `DEEPSEEK_ENDPOINT` | `api.deepseek.com/v1` | DeepSeek endpoint |
| `OPENAI_BASE_URL` | `api.openai.com/v1` | OpenAI endpoint |
| `VLLM_LOCAL_URL` | `localhost:9001/v1` | Local vLLM endpoint |
| **Third-Party APIs** | | |
| `ABUSEIPDB_API_KEY` | - | AbuseIPDB API key |
| `HIBP_API_KEY` | - | Have I Been Pwned key |
| `SHODAN_API_KEY` | - | Shodan search key |
| `GITHUB_TOKEN` | - | GitHub API token |
| `SLACK_BOT_TOKEN` | - | Slack bot token |
| `CENSYS_API_ID` / `CENSYS_API_SECRET` | - | Censys API credentials |
| `MISP_URL` / `MISP_API_KEY` | - | MISP threat intel |
| `INTELOWL_URL` / `INTELOWL_API_KEY` | - | IntelOwl server |
| `OPENCTI_URL` / `OPENCTI_API_KEY` | - | OpenCTI threat intel |
| **Observability** | | |
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry |
| `OTEL_ENDPOINT` | `localhost:4317` | OTEL collector endpoint |

## Testing

- Framework: pytest with pytest-asyncio (`asyncio_mode = "auto"`)
- Coverage target: 80%+ (`--cov=src/loom`)
- Test files: 243 files across tests/ subdirectories
- Test count: 1500+ test functions (significant expansion from 1260)
- Markers: `slow`, `live` (real network), `integration`
- Test structure mirrors source: `tests/test_tools/`, `tests/test_providers/`, `tests/test_integration/`, `tests/test_strategies/`, `tests/test_billing/`
- Fixtures in `tests/conftest.py` provide temp dirs, mock HTTP transport, and sample API responses
- Journey tests (`tests/journey_e2e.py`) run comprehensive scenarios in mocked/live/record modes
- Strategy tests validate all 957 strategies for syntax, execution, and safety

## Documentation

Five documentation files in `docs/`:

- **tool_params.json** — Machine-readable source of truth for ALL 806 tool parameters (auto-generated from source inspection)
- **TOOL_PARAMS_REFERENCE.md** — Human-readable param reference for all 806 tools (auto-generated from tool_params.json)
- **tools-reference.md** — Complete reference for 440+ tools, parameters, and examples
- **api-keys.md** — API key setup for all 8 LLM providers + 21 search providers + infrastructure/communication/media services
- **architecture.md** — Deep dive into pipeline design, escalation strategy, and tool composition
- **help.md** — Troubleshooting, common patterns, and FAQ

### REST API (alongside MCP)

```bash
# Health check
GET /api/v1/health

# List all tools with param types
GET /api/v1/tools

# Get a tool's signature, docstring, and params
GET /api/v1/tools/{name}/info

# Call any tool with JSON body
POST /api/v1/tools/{name}  {"param1": "value", "param2": 42}
```

### Commonly Confused Parameters

These cause most test failures — use the correct names:

| Wrong (common mistake) | Correct | Tool(s) |
|------------------------|---------|---------|
| `command` | `kind` | research_github (values: "repo", "code", "issues") |
| `max_results` | `depth` | research_deep, research_citation_analysis |
| `max_results` | `n` | research_search, research_llm_query_expand |
| `max_results` | `limit` | research_github, research_multi_search(=max_results) |
| `providers` | `engines` | research_multi_search |
| `target_language` | `target_lang` | research_llm_translate |
| `text` / `input` | `query` | research_search, research_deep, research_multi_search |
| `model_name` | `model` | all LLM tools (research_llm_*) |
| `args` | `query` | research_github |
| `strategy_name` | `strategy` | research_prompt_reframe |
| `url_list` | `urls` | research_spider |
| `search repos` | `repo` | research_github kind param |

### Sync vs Async Tools

Most tools are async. Notable SYNC tools (do NOT await):
- `research_github` — sync (calls `gh` CLI subprocess)
- `research_build_query` — sync (heuristic decomposition)
- `research_cache_stats` / `research_cache_clear` — sync

Check with: `GET /api/v1/tools/{name}/info` → `"async": true/false`

## Code style

- Python 3.11+, type hints on all signatures
- Ruff for linting (rules: E, W, F, I, B, C4, UP, SIM, RUF, ASYNC, S) and formatting
- mypy strict mode with `pydantic.mypy` plugin
- Line length: 100
- Quote style: double

### Adding new tools

Every new tool requires ALL of:
1. Implementation in appropriate subdirectory of `src/loom/tools/` (core/, llm/, intelligence/, security/, privacy/, adversarial/, career/, infrastructure/, backends/, research/, or monitoring/)
2. Parameter validation model in `src/loom/params/` subdirectory with Pydantic v2 (`extra="forbid"`, `strict=True`)
3. Tool function registration in `server.py:_register_tools()` with `mcp.tool()(_wrap_tool(...))`
4. Error handling via `@handle_tool_errors("research_tool_name")` decorator from `error_responses.py`
5. Comprehensive tests in `tests/test_tools/` with 80%+ coverage target
6. Entry in `docs/tools-reference.md` with parameters, examples, and cost estimation
7. Entry in `docs/help.md` with troubleshooting and use cases
8. Optional: Handle ImportError in `server.py` if tool depends on external packages
9. Run `scripts/verify_completeness.py` to confirm zero documentation drift

### Adding new strategies

Every new reframing strategy requires:
1. Definition in appropriate module under `src/loom/tools/reframe_strategies/` (32 modules, 957 strategies)
2. Strategy dict with keys: `name`, `template`, `description`, `category`, `difficulty`, `safety_flags`
3. Registration in `ALL_STRATEGIES` dict via module imports in `__init__.py`
4. Unit tests validating template syntax and variable substitution
5. Integration tests with actual LLM providers to verify effectiveness
6. Documentation in `docs/strategies-reference.md` with examples and risk assessment

## Privacy, Anonymity & Counter-Surveillance Integration Tasks

Research conducted 2026-05-01 identified 18 high-value privacy & security tools (see PRIVACY_RESEARCH_REPORT.md).
Below are integration priorities split into 3 tiers.

### TIER 1: IMMEDIATE (Weeks 1-2) - Critical Path

- [x] **INTEGRATE-032: FingerprintJS fingerprint audit**
  - Repo: https://github.com/fingerprintjs/fingerprintjs (27020⭐)
  - File: src/loom/tools/privacy/privacy_tools.py
  - Tool: `research_fingerprint_audit(target_url, include_canvas, include_webgl, include_audio, include_fonts)`
  - Returns: Fingerprint vector map with 70+ device attributes
  - Tests: Unit tests for attribute extraction + privacy exposure scoring
  - Docs: docs/tools-reference.md (Privacy & Anonymity section)
  - Status: IMPLEMENTED

- [x] **INTEGRATE-033: creepjs privacy exposure detector**
  - Repo: https://github.com/abrahamjuliot/creepjs (2360⭐)
  - File: src/loom/tools/privacy/privacy_tools.py
  - Tool: `research_privacy_exposure(target_url, include_interactive=False)`
  - Returns: Privacy baseline + fingerprint vector inventory
  - Tests: Integration tests with live browser + interactive mode
  - Docs: docs/help.md (troubleshooting creepjs timeouts)
  - Status: IMPLEMENTED

- [x] **INTEGRATE-034: usbkill USB kill-switch monitor**
  - Repo: https://github.com/hephaest0s/usbkill (4583⭐)
  - File: src/loom/tools/privacy/privacy_advanced.py
  - Tool: `research_usb_monitor(trigger_action='wipe', target_path='/path/to/secure', dry_run=True)`
  - Returns: USB activity detection results + wipe simulation
  - Tests: Unit tests for udev rule validation + dry-run wipe
  - Docs: docs/tools-reference.md + docs/api-keys.md (no API key needed)
  - Status: IMPLEMENTED

- [x] **INTEGRATE-035: Forensia anti-forensics toolkit**
  - Repo: https://github.com/Forensia/Forensia (783⭐)
  - File: src/loom/tools/privacy/privacy_tools.py
  - Tool: `research_artifact_cleanup(target_paths=['logs', 'cache', 'temp'], os_type='linux|windows|macos')`
  - Returns: Artifact cleanup report + safe deletion verification
  - Tests: Integration tests with real artifacts (test dirs only)
  - Docs: docs/help.md (safety warnings for production use)
  - Status: IMPLEMENTED

### TIER 2: NEXT SPRINT (Weeks 3-4) - Operational Enhancement

- [x] **INTEGRATE-036: supercookie favicon tracker**
  - Repo: https://github.com/jonasstrehle/supercookie (7042⭐)
  - File: src/loom/tools/privacy/privacy_tools.py
  - Tool: `research_fingerprint_audit()` (supercookie tests integrated)
  - Returns: Favicon-based re-identification vector assessment
  - Tests: Unit tests for favicon color encoding/decoding
  - Docs: docs/tools-reference.md (advanced tracking techniques)
  - Status: IMPLEMENTED (via research_fingerprint_audit)

- [x] **INTEGRATE-037: fingerprint-suite evasion validator**
  - Repo: https://github.com/amnemonic/fingerprint-suite (2076⭐)
  - File: src/loom/tools/privacy/privacy_advanced.py
  - Tool: `research_browser_privacy_score(browser, test_iterations=10)`
  - Returns: Fingerprint spoofing effectiveness score (0-100%)
  - Tests: Multi-iteration tests validating randomization entropy
  - Docs: docs/tools-reference.md (anonymization solution comparison)
  - Status: IMPLEMENTED

- [x] **INTEGRATE-038: silk-guardian Linux anti-forensics**
  - Repo: https://github.com/NullArray/silk-guardian (720⭐)
  - File: src/loom/tools/privacy/privacy_advanced.py
  - Tool: `research_usb_monitor()` + `research_secure_delete()` (Linux hardening integrated)
  - Returns: Forensic activity detection + containment status
  - Tests: Integration tests with Linux syscall monitoring
  - Docs: docs/help.md (Linux-specific anti-forensics deployment)
  - Status: IMPLEMENTED (via research_usb_monitor and secure_delete)

- [x] **INTEGRATE-039: LSB steganography encoder**
  - Repo: https://github.com/amitvkulkarni/LSB-Steganography-Python (13⭐)
  - File: src/loom/tools/privacy/privacy_tools.py
  - Tool: `research_stego_encode_zw(input_media, secret_data, output_format='png|bmp')`
  - Returns: Encoded media file + steganography capacity analysis
  - Tests: Round-trip tests (encode → decode verification)
  - Docs: docs/tools-reference.md (covert exfiltration section)
  - Status: IMPLEMENTED

### TIER 3: FUTURE (Weeks 5-6) - Specialized Capabilities

- [ ] **INTEGRATE-040: ulexecve fileless execution**
  - Repo: https://github.com/mempodipog/ulexecve (208⭐)
  - File: src/loom/tools/privacy/privacy_fileless_exec.py
  - Effort: 4-5 days
  - Value: EDR evasion via memory-only execution
  - Note: Requires ptrace-based process manipulation; high OS dependency

- [ ] **INTEGRATE-041: saruman ELF binary obfuscation**
  - Repo: https://github.com/elfmaster/saruman (141⭐)
  - Effort: 4-5 days
  - Value: Binary-level anti-analysis + code hiding
  - Note: Requires ELF binary manipulation; Linux-only, complex integration

- [ ] **INTEGRATE-042: flock-detection wireless surveillance**
  - Repo: https://github.com/BenDavidAaron/flock-detection (6⭐)
  - Effort: 3-4 days
  - Value: WiFi/BLE surveillance device detection
  - Note: Requires radio/BLE hardware access; may need system-level privileges

- [ ] **INTEGRATE-043: browser-fingerprinting bot evasion analysis**
  - Repo: https://github.com/maciekopalinski/browser-fingerprinting (4999⭐)
  - Effort: 2-3 days
  - Value: Bot protection mechanism analysis
  - Note: Overlaps with existing research_browser_privacy_score; evaluate for consolidation

- [ ] **INTEGRATE-044: chameleon fingerprint randomizer**
  - Repo: https://github.com/lulzsec/chameleon (544⭐)
  - Effort: 2-3 days
  - Value: Defensive fingerprint randomization
  - Note: Browser extension; requires headless browser integration

- [ ] **INTEGRATE-045: stegma multi-format steganography**
  - Repo: https://github.com/jmhmcc/stegma (2⭐)
  - Effort: 2-3 days
  - Value: Multi-media (image/audio/video) covert channels
  - Note: Expand research_stego_encode_zw to support audio/video formats

- [ ] **INTEGRATE-046: BrowserBlackBox interactive privacy audit**
  - Repo: https://github.com/dessant/bbb (2⭐)
  - Effort: 2-3 days
  - Value: Interactive privacy baseline assessment
  - Note: Browser extension; requires orchestration via headless browser

- [ ] **INTEGRATE-047: PII-Recon exposure auditing**
  - Repo: https://github.com/ru7-security/PII-Recon (1⭐)
  - Effort: 2-3 days
  - Value: Sensitive data leak detection
  - Note: Consider merging with existing data leak scanning tools

- [ ] **INTEGRATE-048: swiftGuard macOS anti-forensics**
  - Repo: https://github.com/swiftGuard-security/swiftGuard (456⭐)
  - Effort: 3-4 days
  - Value: macOS-specific defensive hardening
  - Note: macOS-only; requires Objective-C/Swift interop via ctypes or subprocess

- [ ] **INTEGRATE-049: steganography-python image hiding**
  - Repo: https://github.com/tharukaromesh/steganography-python (13⭐)
  - Effort: 1-2 days
  - Value: Alternative steganography implementation
  - Note: Pure Python alternative; can be used as fallback to research_stego_encode_zw
