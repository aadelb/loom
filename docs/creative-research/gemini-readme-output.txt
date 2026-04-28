
--- FILE: /Users/aadel/projects/loom/CLAUDE.md ---

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Loom

Loom is a Python MCP (Model Context Protocol) server that exposes ~45 research tools over streamable-HTTP (port 8787). It wraps scraping (Scrapling with auto-escalation, Crawl4AI with Trafilatura fallback, Camoufox, Botasaurus, YouTube transcripts), search (9 providers including Exa, Tavily, Firecrawl, Brave, ddgs, arxiv, wikipedia, hackernews, reddit), LLM providers (NVIDIA NIM, OpenAI, Anthropic, vLLM), GitHub CLI, persistent browser sessions, 11 creative research tools, and a content-hash cache into a single MCP service. It also ships a Typer CLI (`loom`) that calls the MCP server as a client.

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
    fetch.py       research_fetch (Scrapling auto-escalation: http→stealthy→dynamic)
    spider.py      research_spider (concurrent multi-URL fetch)
    markdown.py    research_markdown (Crawl4AI HTML-to-markdown with Trafilatura fallback, YouTube transcript extraction)
    search.py      research_search (9 providers: exa, tavily, firecrawl, brave, ddgs, arxiv, wikipedia, hackernews, reddit)
    deep.py        research_deep (12-stage deep pipeline with query type detection, language detection, expertise finder, Wayback Machine recovery)
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
- Journey tests (`test_journey.py`) run the full ~45-tool scenario in mocked mode

## Code style

- Python 3.11+, type hints on all signatures
- Ruff for linting (rules: E, W, F, I, B, C4, UP, SIM, RUF, ASYNC, S) and formatting
- mypy strict mode with `pydantic.mypy` plugin
- Line length: 100
- Quote style: double
```

--- FILE: /Users/aadel/projects/loom/README.md ---

```markdown
# Loom

> Smart internet research MCP server — scraping, search, LLMs, and persistent browser sessions in one place.

[![PyPI](https://img.shields.io/pypi/v/loom-mcp)](https://pypi.org/project/loom-mcp/)
[![CI](https://github.com/aadelb/loom/actions/workflows/ci.yml/badge.svg)](https://github.com/aadelb/loom/actions)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## What Loom does

- **Scraping**: Scrapling auto-escalation fetcher (http→stealthy→dynamic), Crawl4AI markdown extraction with Trafilatura fallback, YouTube transcript extraction, Camoufox Firefox stealth mode, Botasaurus Chrome stealth mode
- **Search**: 9 providers: Exa semantic search, Tavily agent-native search, Firecrawl web intelligence, Brave independent index, ddgs (free), arxiv (free), wikipedia (free), hackernews (free), reddit (free)
- **Research Pipeline**: 12-stage deep pipeline (was 3-step) with query type detection (academic/knowledge/code), language detection, Wayback Machine recovery, and expertise finder
- **Creative**: 11 creative research tools
- **LLM**: NVIDIA NIM free tier, OpenAI, Anthropic, local vLLM via cascade routing
- **GitHub**: Wraps `gh` CLI for repository, code, and issues search

## Why

Built-in WebSearch and WebFetch in Claude Code and other MCP clients miss Cloudflare-protected pages, JavaScript-heavy vendor docs, bulk sweeps, and multi-language targets. Loom drops in as an MCP server that solves these cases out of the box, with URL validation, cost caps, and rich per-call parameters for headers, proxy, cookies, and persistent sessions.

## Quickstart

```bash
pip install loom-mcp
loom install-browsers
loom serve
```

## Docker

```bash
docker run -p 127.0.0.1:8787:8787 ghcr.io/aadelb/loom:latest
```

## Register with Claude Code

Add this to `~/.claude/settings.json` under `mcpServers`:

```json
"loom": {
  "type": "http",
  "url": "http://127.0.0.1:8787/mcp"
}
```

Then restart Claude Code. `claude mcp list` should show `loom` with ~45 tools.

## CLI examples

```bash
loom fetch https://example.com --mode stealthy
loom spider urls.txt --concurrency 5
loom search "open source MCP servers" --provider exa --n 20
loom deep "what is the MCP protocol" --depth 3
loom llm summarize article.txt
loom session open my-session --browser camoufox
loom config set SPIDER_CONCURRENCY 10
loom journey-test --fixtures tests/fixtures/journey
```

## MCP tools

<details>
<summary><strong>~45 tools exposed over streamable HTTP on port 8787</strong></summary>

**Scraping**
- research_fetch — fetch single URL with auto-escalation (http→stealthy→dynamic)
- research_spider — concurrent scrape multiple URLs
- research_markdown — extract markdown from HTML with Trafilatura fallback
- research_youtube — YouTube transcript extraction
- research_camoufox — Camoufox Firefox stealth browser
- research_botasaurus — Botasaurus Chrome stealth browser
- research_cache_stats — cache hit/miss statistics
- research_cache_clear — clear content-hash cache
- research_github — GitHub CLI wrapper

**Search & Research**
- research_search — multi-provider semantic search (9 providers)
- research_deep — recursive 12-stage deep pipeline with query type detection, language detection, Wayback Machine recovery, and expertise finder

**Creative (11)**
- 11 creative research tools for various analysis and ideation tasks

**Sessions (3)**
- research_session_open — open persistent browser session
- research_session_list — list active sessions
- research_session_close — close session

**Config (2)**
- research_config_get — read runtime configuration
- research_config_set — update configuration without restart

**LLM (8)**
- research_llm_summarize — summarize content
- research_llm_extract — extract structured data
- research_llm_classify — classify text
- research_llm_translate — translate to target language
- research_llm_query_expand — expand search queries
- research_llm_answer — answer questions from content
- research_llm_embed — generate embeddings
- research_llm_chat — chat with context window

</details>

## Configuration

See [deploy/.env.example](deploy/.env.example) for all environment variables and [docs/deployment/](docs/deployment/) for systemd, Docker, and Kubernetes guides.

## Security

Loom ships with URL validation by default — private IPs, loopback, link-local, metadata endpoints, and non-http schemes are all rejected. See [SECURITY.md](SECURITY.md) for the full threat model and how to report a vulnerability.

## Documentation

- [Quickstart](docs/quickstart.md)
- [Installation](docs/installation.md)
- [CLI reference](docs/cli.md)
- [Tool reference](docs/tools/)
- [Deployment guides](docs/deployment/)
- [Journey test](docs/journey-test.md)

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Author

Ahmed Adel Bakr Alderai
```
