# Loom

> Smart internet research MCP server — scraping, search, LLMs, and persistent browser sessions in one place.

[![PyPI](https://img.shields.io/pypi/v/loom-mcp)](https://pypi.org/project/loom-mcp/)
[![CI](https://github.com/aadelb/loom/actions/workflows/ci.yml/badge.svg)](https://github.com/aadelb/loom/actions)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## What Loom does

- **Scraping**: Scrapling 3-tier fetcher, Crawl4AI markdown extraction, Camoufox Firefox stealth mode, Botasaurus Chrome stealth mode
- **Search**: Exa semantic search, Tavily agent-native search, Firecrawl web intelligence, Brave independent index
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

Then restart Claude Code. `claude mcp list` should show `loom` with 23 tools.

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
<summary><strong>23 tools exposed over streamable HTTP on port 8787</strong></summary>

**Scraping (8)**
- research_fetch — fetch single URL with mode selection
- research_spider — concurrent scrape multiple URLs
- research_markdown — extract markdown from HTML
- research_camoufox — Camoufox Firefox stealth browser
- research_botasaurus — Botasaurus Chrome stealth browser
- research_cache_stats — cache hit/miss statistics
- research_cache_clear — clear content-hash cache
- research_github — GitHub CLI wrapper

**Search (2)**
- research_search — multi-provider semantic search
- research_deep — recursive research with depth control

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
