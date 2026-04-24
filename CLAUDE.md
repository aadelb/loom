# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Loom

Loom is a Python MCP (Model Context Protocol) server that exposes 23 research tools over streamable-HTTP (port 8787). It wraps scraping (Scrapling, Crawl4AI, Camoufox, Botasaurus), search (Exa, Tavily, Firecrawl, Brave), LLM providers (NVIDIA NIM, OpenAI, Anthropic, vLLM), GitHub CLI, persistent browser sessions, and a content-hash cache into a single MCP service. It also ships a Typer CLI (`loom`) that calls the MCP server as a client.

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
  tools/           One module per tool family:
    fetch.py       research_fetch (Scrapling 3-tier: http/stealthy/dynamic)
    spider.py      research_spider (concurrent multi-URL fetch)
    markdown.py    research_markdown (Crawl4AI HTML-to-markdown)
    search.py      research_search (multi-provider: exa/tavily/firecrawl/brave)
    deep.py        research_deep (chained: search -> fetch -> markdown -> extract)
    github.py      research_github (gh CLI wrapper)
    stealth.py     research_camoufox + research_botasaurus
    cache_mgmt.py  research_cache_stats + research_cache_clear
    llm.py         8 LLM tools (summarize/extract/classify/translate/expand/answer/embed/chat)
  providers/       LLM provider abstraction:
    base.py        Abstract LLMProvider + LLMResponse dataclass + _estimate_cost
    nvidia_nim.py  NVIDIA NIM free tier (integrate.api.nvidia.com)
    openai_provider.py
    anthropic_provider.py
    vllm_local.py  Local vLLM endpoint
```

### Key patterns

- **Tool registration**: `server.py:_register_tools()` explicitly registers each tool function with `mcp.tool()()`. LLM tools are optional (guarded by ImportError).
- **Parameter validation**: Every tool has a Pydantic model in `params.py` with `extra="forbid"` and `strict=True`. URL fields pass through `validators.validate_url()` for SSRF prevention.
- **LLM cascade**: Config key `LLM_CASCADE_ORDER` (default: nvidia -> openai -> anthropic -> vllm) controls provider fallback. Providers implement the `LLMProvider` ABC with `chat()`, `embed()`, `available()`, `close()`.
- **Cache**: SHA-256 content-hash keyed, stored in daily subdirectories (`~/.cache/loom/YYYY-MM-DD/`). Atomic writes via uuid tmp + `os.replace`. Singleton via `get_cache()`.
- **Sessions**: Two systems coexist — an in-memory async registry (global `_sessions` dict with asyncio.Lock) and a SQLite-backed `SessionManager` class with LRU eviction (max 8). Session names must match `^[a-z0-9_-]{1,32}$`.
- **Config**: `ConfigModel` in `config.py` provides validated bounds on all settings. `CONFIG` is a module-level dict updated by `load_config()`. Config file resolved via: explicit path > `$LOOM_CONFIG_PATH` > `./config.json`.

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOOM_HOST` | `127.0.0.1` | Server bind address |
| `LOOM_PORT` | `8787` | Server port |
| `LOOM_CONFIG_PATH` | `./config.json` | Config file location |
| `LOOM_CACHE_DIR` | `~/.cache/loom` | Cache storage root |
| `LOOM_SESSIONS_DIR` | `~/.loom/sessions` | Session storage root |
| `NVIDIA_NIM_API_KEY` | - | NVIDIA NIM API key |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `EXA_API_KEY` | - | Exa search API key |
| `TAVILY_API_KEY` | - | Tavily search API key |

## Testing

- Framework: pytest with pytest-asyncio (`asyncio_mode = "auto"`)
- Coverage target: 80%+ (`--cov=src/loom`)
- Markers: `slow`, `live` (real network), `integration`
- Test structure mirrors source: `tests/test_tools/`, `tests/test_providers/`, `tests/test_integration/`
- Fixtures in `tests/conftest.py` provide temp dirs, mock HTTP transport, and sample API responses
- Journey tests (`test_journey.py`) run the full 23-tool scenario in mocked mode

## Code style

- Python 3.11+, type hints on all signatures
- Ruff for linting (rules: E, W, F, I, B, C4, UP, SIM, RUF, ASYNC, S) and formatting
- mypy strict mode with `pydantic.mypy` plugin
- Line length: 100
- Quote style: double
