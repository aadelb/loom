# Graph Report - .  (2026-04-12)

## Corpus Check
- 112 files · ~70,019 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1233 nodes · 3267 edges · 62 communities detected
- Extraction: 42% EXTRACTED · 58% INFERRED · 0% AMBIGUOUS · INFERRED: 1899 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `SessionOpenParams` - 119 edges
2. `UrlSafetyError` - 108 edges
3. `LLMResponse` - 103 edges
4. `FetchParams` - 100 edges
5. `MarkdownParams` - 90 edges
6. `SpiderParams` - 89 edges
7. `SearchParams` - 87 edges
8. `DeepParams` - 87 edges
9. `GitHubSearchParams` - 87 edges
10. `CamoufoxParams` - 87 edges

## Surprising Connections (you probably didn't know these)
- `SSRF validator tests — 11 cases.` --uses--> `UrlSafetyError`  [INFERRED]
  tests/test_validators.py → src/loom/validators.py
- `Allow public https URLs.` --uses--> `UrlSafetyError`  [INFERRED]
  tests/test_validators.py → src/loom/validators.py
- `Allow public http URLs.` --uses--> `UrlSafetyError`  [INFERRED]
  tests/test_validators.py → src/loom/validators.py
- `Block EC2 metadata endpoint.` --uses--> `UrlSafetyError`  [INFERRED]
  tests/test_validators.py → src/loom/validators.py
- `Block RFC1918 10.0.0.0/8.` --uses--> `UrlSafetyError`  [INFERRED]
  tests/test_validators.py → src/loom/validators.py

## Hyperedges (group relationships)
- **** — research_llm_summarize, research_llm_chat, research_llm_extract, research_llm_classify [INFERRED]
- **** — nvidia_nim_provider, openai_provider, anthropic_provider, vllm_provider [INFERRED]
- **** — research_fetch_tool, research_spider_tool, research_search_tool, research_github [INFERRED]
- **** — systemd_unit, dockerfile, docker_compose [INFERRED]
- **** — deep_research_example, harvest_example, bulk_arxiv_example, cloudflare_bypass_example, session_login_example [INFERRED]

## Communities

### Community 0 - "LLM Provider Cascade"
Cohesion: 0.02
Nodes (146): AnthropicProvider, Anthropic provider for Loom.  Uses the Anthropic Messages API for Claude models., Anthropic does not support embeddings.          Args:             texts: List of, Redact API keys from an error string., Anthropic provider using Claude models.      Attributes:         name: "anthropi, Initialize Anthropic provider., Lazy-initialize Anthropic client., Check if Anthropic is configured with a non-empty key AND importable.          R (+138 more)

### Community 1 - "Pydantic Param Models"
Cohesion: 0.11
Nodes (122): BaseModel, BotasaurusParams, CamoufoxParams, ConfigSetParams, DeepParams, FetchParams, GitHubSearchParams, LLMAnswerParams (+114 more)

### Community 2 - "Runtime Config System"
Cohesion: 0.04
Nodes (50): ConfigModel, _defaults_dict(), get_config(), load_config(), Runtime configuration for Loom MCP server.  Exposes a validated ``ConfigModel``, Return a fresh dict of code defaults from ConfigModel()., Load and validate config from a file, merging over code defaults.      Priority, Validate and atomically write a config dict to disk.      Uses the standard atom (+42 more)

### Community 3 - "Project Documentation"
Cohesion: 0.04
Nodes (68): Ahmed Adel Bakr Alderai, API Key Sanitization, arXiv Paper Classification Integration, Brave Search Provider, Bulk arXiv Crawler Example, Cache Management System, Claude Code Integration, Typer CLI Tool (+60 more)

### Community 4 - "Session Management"
Cohesion: 0.04
Nodes (40): Validate session name against allow-list regex.      Raises ValueError if:     -, Manages browser sessions with SQLite persistence and LRU eviction.      Singleto, Initialize SessionManager, creating DB if needed., Create sessions table if not exists., Get or create a semaphore for a session name (for serializing access)., Open or reuse a session, updating TTL. Creates profile_dir and DB entry., Close a session, delete profile_dir and DB row.          Args:             name:, List all sessions, sorted by last_used_at DESC (newest first).          Returns: (+32 more)

### Community 5 - "Content-Hash Cache"
Cohesion: 0.06
Nodes (30): CacheStore, get_cache(), Content-hash cache with atomic writes and daily directory structure.  Provides a, Return cache statistics.          Returns:             Dict with file_count, tot, Remove cache entries older than N days.          Args:             days: remove, Return the process-wide CacheStore singleton.      Honors LOOM_CACHE_DIR on firs, Return current UTC time in ISO 8601 format., Content-hash cache with atomic writes and daily directory structure.      Stores (+22 more)

### Community 6 - "Typer CLI Interface"
Cohesion: 0.07
Nodes (41): botasaurus(), cache(), _call_mcp_tool(), camoufox(), config(), deep(), fetch(), github() (+33 more)

### Community 7 - "CLI Smoke Tests"
Cohesion: 0.05
Nodes (24): cli_runner(), Comprehensive CLI smoke tests for Loom — all subcommands and functional scenario, loom llm --help shows help., loom journey-test --help shows help., loom install-browsers --help shows help., Functional tests with mocked MCP calls., loom config list invokes research_config_get MCP tool., loom cache stats invokes research_cache_stats MCP tool. (+16 more)

### Community 8 - "Browser Sessions Core"
Cohesion: 0.08
Nodes (41): _cleanup_expired(), cleanup_sessions(), close_session(), _delete_metadata(), _find_oldest_session(), _get_browser(), get_session(), _get_session_dir() (+33 more)

### Community 9 - "Validator Test Suite"
Cohesion: 0.05
Nodes (20): Unit tests for URL and input validators (SSRF prevention, gh query sanitization), Reject -o flag injection., Reject $() shell injection., Allow normal query with quotes., SSRF validator tests — 11 cases., Allow public https URLs., Allow public http URLs., Block EC2 metadata endpoint. (+12 more)

### Community 10 - "Journey Test Runner"
Cohesion: 0.1
Nodes (23): _format_duration(), JourneyReport, Smart deep end-to-end journey test for Loom.  Runs a realistic research scenario, Render journey as human-readable markdown transcript., Render journey as JSON for CI parsing., Run the complete journey test.      The journey simulates a researcher investiga, Return current UTC time in ISO 8601 format., Invoke the journey ``on_step`` callback with error containment.      A user-prov (+15 more)

### Community 11 - "URL Fetch Pipeline"
Cohesion: 0.13
Nodes (23): _extract_text(), _fetch_dynamic(), _fetch_http(), _fetch_http_httpx(), _fetch_http_scrapling(), _fetch_stealthy(), FetchResult, _make_cache_key() (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (3): LLMEmbedParams, Pydantic v2 parameter models for all MCP tool arguments.  Each tool has a dedica, Parameters for research_llm_embed tool.

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (21): env_no_api_keys(), fixture_exa_search_response(), fixture_fanar_model_card(), fixture_journey_dir(), fixture_nvidia_nim_chat_response(), fixture_tavily_search_response(), mock_httpx_transport(), Pytest fixtures for Loom test suite.  Provides:   - Temp directories (cache, ses (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.1
Nodes (12): cli_runner(), Unit tests for CLI — smoke tests with typer CliRunner., Provide a Typer CliRunner for CLI testing., loom --help prints usage., loom fetch --help prints subcommand usage., loom search --help prints subcommand usage., loom session --help prints subcommand usage., loom config --help prints subcommand usage. (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (11): mock_crawl4ai(), Unit tests for research_markdown tool — Crawl4AI async markdown extractor., Test research_markdown rejects private IPs (SSRF protection)., Inject mock crawl4ai module into sys.modules., Test research_markdown returns correct data structure., Test research_markdown gracefully handles Crawl4AI import failures., Test research_markdown respects max character limit., TestMarkdownHandlesImportError (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (9): Unit tests for research_search tool — mocked provider SDKs, normalized output., Unknown provider returns error dict., research_search tool tests with mocked provider SDKs., Exa provider returns normalized output with provider field., Tavily provider returns normalized output with provider field., Empty query returns error dict., n=100 is clamped to 50., include_domains and exclude_domains forwarded to provider. (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (9): Unit tests for research_fetch tool — URL validation, caching, scrapling.  NOTE:, Fetch respects max_chars parameter., Fetch with bypass_cache=True ignores cache., research_fetch tool tests., Fetch rejects URLs that fail SSRF validation., Fetch rejects private IPs., Fetch result has expected fields (url, title, text, html_len, fetched_at)., Fetch returns cached result on second call (same params). (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.19
Nodes (14): _mock_response(), Unit tests for LLM tools — chat, summarize, extract, classify, translate.  All 8, LLM query expand returns multiple expanded queries., LLM chat returns structure with text, model, tokens, cost, latency., LLM summarize respects max_tokens bounds., LLM extract validates result against provided schema., LLM classify returns a label from the allow-list., LLM translate returns a structured result for non-English input. (+6 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (8): Unit tests for loom.server — tool registration and app creation., create_app() initializes correctly., create_app() returns a FastMCP instance., create_app() registers exactly 23 tools., Every registered tool name starts with 'research_'., No duplicate tool names., All promised tool names are registered., TestServerCreateApp

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (8): Unit tests for research_github tool — query sanitization, subprocess mocking, ca, research_github tool tests., GitHub query rejects --flag injection., GitHub query rejects shell injection., GitHub result is parsed from JSON subprocess output., GitHub caches results for repeated queries., GitHub accepts all kinds: repos, code, issues., TestGitHub

### Community 21 - "Community 21"
Cohesion: 0.14
Nodes (9): Unit tests for stealth tools — camoufox and botasaurus., research_camoufox tool tests., ImportError on camoufox import returns error dict., Camoufox result includes url, title, text, tool keys., research_botasaurus tool tests., botasaurus delegates to research_fetch with mode='dynamic'., botasaurus result has tool='botasaurus'., TestBotasaurus (+1 more)

### Community 22 - "Community 22"
Cohesion: 0.14
Nodes (9): Unit tests for research_cache_stats and research_cache_clear., research_cache_stats returns expected shape and values., Stats on empty cache dir return zeros., Stats reflect files in the cache directory., research_cache_clear removes old entries., Entries older than threshold are deleted., Clear on empty dir returns zeros., TestCacheClear (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (11): Integration tests for MCP roundtrip — spawn server in-process, call tools.  Test, MCP server /tools/list returns all expected tools., Calling research_fetch through MCP returns expected response., Calling research_search through MCP returns expected response., Session management tools work through MCP roundtrip., MCP layer properly serializes errors from tools., test_mcp_error_handling(), test_mcp_server_lists_tools() (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (11): Unit tests for research_spider tool — parallel fetches, concurrency, mixed resul, Spider with empty URL list returns empty result., Spider with dedupe=True removes duplicate URLs., Spider fetches URLs in parallel up to concurrency limit., Spider respects concurrency parameter., Spider handles mixed ok/fail results gracefully., test_spider_deduplication(), test_spider_empty_urls_returns_empty() (+3 more)

### Community 25 - "Community 25"
Cohesion: 0.17
Nodes (11): Unit tests for research_deep tool — search + markdown chaining., research_deep handles empty query gracefully., research_deep returns dict with query, results list with url/title/markdown., research_deep returns error when search fails., research_deep returns partial results when markdown fetch fails., research_deep with depth=2 limits URL fetches., test_deep_handles_markdown_failure(), test_deep_handles_search_failure() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.17
Nodes (2): Unit tests for VllmLocalProvider., TestVllmLocalProvider

### Community 27 - "Community 27"
Cohesion: 0.21
Nodes (11): CamoufoxResult, _fetch_camoufox(), research_camoufox — Camoufox-based stealth browser for anti-bot websites.  Uses, Fetch a URL using Botasaurus stealth browser (second stealth escalation).      T, MCP wrapper for research_camoufox., Result from Camoufox scrape., Synchronous wrapper for Camoufox.      ``camoufox`` is an untyped third-party pa, Fetch a URL using Camoufox stealth browser.      Args:         url: URL to fetch (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (2): Unit tests for AnthropicProvider., TestAnthropicProvider

### Community 29 - "Community 29"
Cohesion: 0.2
Nodes (6): Unit tests for spider tool — validation, deduplication, concurrency., research_spider validation tests., Empty URL list returns error dict., Concurrency > SPIDER_CONCURRENCY is clamped., Duplicate URLs are fetched only once., TestSpiderValidation

### Community 30 - "Community 30"
Cohesion: 0.24
Nodes (9): Cache management tools for Loom — view stats, clear old entries., MCP wrapper for research_cache_stats., MCP wrapper for research_cache_clear., Return cache statistics.      Returns:         Dict with keys: size_mb, entry_co, Remove cache entries older than N days.      Args:         older_than_days: dele, research_cache_clear(), research_cache_stats(), tool_cache_clear() (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (4): ABC, _estimate_cost(), Base LLM provider interface and response model.  Defines the abstract LLMProvide, Estimate USD cost for an LLM call.      Cost table per model (as of Apr 2025):

### Community 32 - "Community 32"
Cohesion: 0.32
Nodes (7): create_app(), main(), FastMCP server entrypoint for Loom MCP service.  Exports the FastMCP instance wi, Console script entry point. Creates the app and runs the MCP server.      Invoke, Register all MCP tools from tool modules.      Dynamically discovers and registe, Create and configure the FastMCP server instance.      Loads runtime config, set, _register_tools()

### Community 33 - "Community 33"
Cohesion: 0.33
Nodes (5): cap_chars(), URL and input validation for SSRF prevention.  Provides SSRF-safe URL validation, Reject URLs that would allow SSRF into internal or cloud-metadata     endpoints., Clamp character count to [1, MAX_CHARS_HARD_CAP].      Args:         n: candidat, validate_url()

### Community 34 - "Community 34"
Cohesion: 0.4
Nodes (5): research_search — Unified search across multiple providers (Exa, Tavily, Firecra, MCP wrapper for research_search., Search the web using the configured provider.      Args:         query: search q, research_search(), tool_search()

### Community 35 - "Community 35"
Cohesion: 0.4
Nodes (5): research_github — GitHub API client for searching repos, code, issues., MCP wrapper for research_github., Search GitHub via public REST API.      Args:         kind: 'repo' | 'code' | 'i, research_github(), tool_github()

### Community 36 - "Community 36"
Cohesion: 0.67
Nodes (3): extract_arxiv_id(), main(), Extract arXiv ID from URL like https://arxiv.org/abs/2401.12345.

### Community 37 - "Community 37"
Cohesion: 0.67
Nodes (3): extract_title(), main(), Extract <title> tag content from HTML.

### Community 38 - "Community 38"
Cohesion: 0.5
Nodes (3): One-shot deep research: search → fetch → markdown.  Combines research_search (of, One-shot deep research: discover + fetch + extract markdown.      research_searc, research_deep()

### Community 39 - "Community 39"
Cohesion: 0.5
Nodes (3): research_spider — Parallelized bulk URL fetching with semaphore and per-fetch ti, Fetch multiple URLs with bounded concurrency and per-fetch timeout.      Uses as, research_spider()

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Loom entry point for 'python -m loom' invocation.  Delegates to the server main

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): research_markdown returns dict with url, title, markdown, tool, fetched_at.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): research_markdown returns error when Crawl4AI unavailable.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): research_markdown caps markdown output at 30000 chars.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): research_markdown rejects localhost URLs.

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): research_markdown rejects private IP addresses.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): research_markdown rejects loopback IP.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): research_markdown rejects link-local IPs.

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Accept a comma-separated string or a single provider name and coerce to list.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Calculate total duration in milliseconds.

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Send messages to the LLM and get a response.          Args:             messages

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Generate embeddings for a list of texts.          Args:             texts: List

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Check if provider is configured and reachable.          Returns:             Tru

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Clean up resources (e.g. close HTTP client connections).          Called when th

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): research_cache_stats Tool

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): research_cache_clear Tool

## Knowledge Gaps
- **277 isolated node(s):** `Pytest fixtures for Loom test suite.  Provides:   - Temp directories (cache, ses`, `Temporary cache directory for isolated tests.`, `Temporary sessions directory for isolated tests.`, `Temporary config file path for isolated tests.`, `Provide an httpx MockTransport for HTTP testing.      Caller can set responses v` (+272 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 40`** (2 nodes): `config_tuning.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (2 nodes): `session_login.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (2 nodes): `harvest_model_cards.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (2 nodes): `llm_translate.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (2 nodes): `quickstart.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (2 nodes): `deep_research.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (2 nodes): `__main__.py`, `Loom entry point for 'python -m loom' invocation.  Delegates to the server main`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `research_markdown returns dict with url, title, markdown, tool, fetched_at.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `research_markdown returns error when Crawl4AI unavailable.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `research_markdown caps markdown output at 30000 chars.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `research_markdown rejects localhost URLs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `research_markdown rejects private IP addresses.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `research_markdown rejects loopback IP.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `research_markdown rejects link-local IPs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Accept a comma-separated string or a single provider name and coerce to list.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Calculate total duration in milliseconds.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Send messages to the LLM and get a response.          Args:             messages`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Generate embeddings for a list of texts.          Args:             texts: List`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Check if provider is configured and reachable.          Returns:             Tru`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Clean up resources (e.g. close HTTP client connections).          Called when th`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `research_cache_stats Tool`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `research_cache_clear Tool`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `UrlSafetyError` connect `Pydantic Param Models` to `LLM Provider Cascade`, `Community 33`, `Validator Test Suite`?**
  _High betweenness centrality (0.232) - this node is a cross-community bridge._
- **Why does `LLM provider implementations for Loom's research_llm_* tools.` connect `LLM Provider Cascade` to `Pydantic Param Models`, `Content-Hash Cache`?**
  _High betweenness centrality (0.224) - this node is a cross-community bridge._
- **Why does `SessionOpenParams` connect `Pydantic Param Models` to `Browser Sessions Core`, `Community 12`, `Session Management`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 116 inferred relationships involving `SessionOpenParams` (e.g. with `TestFetchParams` and `TestSearchParams`) actually correct?**
  _`SessionOpenParams` has 116 INFERRED edges - model-reasoned connections that need verification._
- **Are the 104 inferred relationships involving `UrlSafetyError` (e.g. with `TestValidateUrl` and `TestGitHubQueryValidator`) actually correct?**
  _`UrlSafetyError` has 104 INFERRED edges - model-reasoned connections that need verification._
- **Are the 101 inferred relationships involving `LLMResponse` (e.g. with `TestBuildProviderChain` and `TestCallWithCascade`) actually correct?**
  _`LLMResponse` has 101 INFERRED edges - model-reasoned connections that need verification._
- **Are the 97 inferred relationships involving `FetchParams` (e.g. with `TestFetchParams` and `TestSearchParams`) actually correct?**
  _`FetchParams` has 97 INFERRED edges - model-reasoned connections that need verification._