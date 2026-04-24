# Loom

> Smart internet research MCP server — scraping, search, LLMs, and persistent browser sessions in one place.

[![PyPI](https://img.shields.io/pypi/v/loom-mcp)](https://pypi.org/project/loom-mcp/)
[![CI](https://github.com/aadelb/loom/actions/workflows/ci.yml/badge.svg)](https://github.com/aadelb/loom/actions)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## What Loom does

- **Scraping**: Scrapling 3-tier fetcher with auto-escalation, Crawl4AI + Trafilatura markdown extraction, Camoufox Firefox stealth mode, Botasaurus Chrome stealth mode, YouTube transcript extraction
- **Search**: 9 providers (Exa semantic, Tavily agent-native, Firecrawl web intelligence, Brave independent index, DuckDuckGo free, Arxiv academic, Wikipedia knowledge, Hacker News community, Reddit threads)
- **Deep Research**: 12-stage pipeline with query type detection, provider selection, fetch escalation, markdown extraction, structured extraction, citation parsing, and community sentiment aggregation
- **Creative Research**: 11 specialized tools (red team analysis, multilingual research, consensus building, misinformation detection, temporal diffs, citation graphs, AI detection, curriculum generation, community sentiment, wiki ghost articles, semantic sitemaps)
- **Recovery & Discovery**: Wayback Machine recovery, expertise finder for sources
- **LLM**: NVIDIA NIM free tier, OpenAI, Anthropic, local vLLM via cascade routing
- **GitHub**: Wraps `gh` CLI for repository, code, and issues search
- **Persistent Sessions**: Manage browser sessions across research workflows
- **Intelligent Caching**: Content-hash keyed cache with per-call control

## Why

Built-in WebSearch and WebFetch in Claude Code and other MCP clients miss Cloudflare-protected pages, JavaScript-heavy vendor docs, bulk sweeps, multi-language targets, and creative research scenarios (consensus building, temporal diffs, citation graphs, community sentiment). Loom drops in as an MCP server that solves these cases out of the box, with automatic escalation, URL validation, cost caps, and rich per-call parameters for headers, proxy, cookies, and persistent sessions.

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

Then restart Claude Code. `claude mcp list` should show `loom` with 45+ tools.

## CLI examples

```bash
loom fetch https://example.com --mode stealthy
loom spider urls.txt --concurrency 5
loom search "open source MCP servers" --provider exa --n 20
loom deep "what is the MCP protocol" --depth 3
loom deep "latest transformer research" --depth 3                   # auto-routes to arxiv
loom deep "who is the CEO of OpenAI" --depth 3                      # auto-routes to wikipedia
loom deep "best Rust async libraries" --depth 3                     # auto-routes to github
loom research-consensus "AI safety frameworks" --providers 3
loom research-sentiment "loom MCP server"
loom research-temporal-diff "climate change impacts" --year1 2020 --year2 2025
loom research-citation-graph "attention is all you need"
loom research-multilingual "health care" --target-languages es,ar,fr
loom research-red-team "prompt injection" --depth 3
loom llm summarize article.txt
loom session open my-session --browser camoufox
loom config set SPIDER_CONCURRENCY 10
loom journey-test --fixtures tests/fixtures/journey
```

## MCP tools

<details>
<summary><strong>45+ tools exposed over streamable HTTP on port 8787</strong></summary>

**Scraping (9)**
- research_fetch — fetch single URL with mode selection (http/stealthy/dynamic) and auto-escalation
- research_spider — concurrent scrape multiple URLs with rate limiting
- research_markdown — extract markdown from HTML (Crawl4AI + Trafilatura fallback)
- research_camoufox — Camoufox Firefox stealth browser
- research_botasaurus — Botasaurus Chrome stealth browser
- research_cache_stats — cache hit/miss statistics
- research_cache_clear — clear content-hash cache
- research_github — GitHub CLI wrapper
- research_yt_transcript — extract YouTube video transcripts

**Search (11)**
- research_search — multi-provider semantic search (exa/tavily/firecrawl/brave/ddgs/arxiv/wikipedia/hackernews/reddit)
- research_deep — recursive research with 12-stage pipeline and depth control
- research_arxiv_direct — direct Arxiv paper search with filtering
- research_wikipedia_direct — direct Wikipedia knowledge lookup
- research_hackernews_direct — HN story and comment search
- research_reddit_direct — Reddit thread and comment search
- research_ddgs_direct — DuckDuckGo free search (no API key needed)
- research_brave_direct — Brave index search
- research_firecrawl_direct — Firecrawl web intelligence
- research_semantic_scholar — academic citation graph via Semantic Scholar

**Creative Research (11)**
- research_red_team — red team analysis of topics (attack vectors, vulnerabilities)
- research_multilingual — research across multiple languages with translation
- research_consensus — build consensus across sources on key claims
- research_misinfo_check — detect and flag misinformation patterns
- research_temporal_diff — compare topic treatment across time periods
- research_citation_graph — build citation network and find seminal papers
- research_ai_detect — detect AI-generated vs. human-written content
- research_curriculum — generate learning curriculum from topic sources
- research_community_sentiment — aggregate sentiment from HN + Reddit
- research_wiki_ghost — find deleted/archived Wikipedia articles
- research_semantic_sitemap — map semantic relationships across domain

**Recovery & Discovery (2)**
- research_wayback_machine — recover archived versions of URLs
- research_expertise_finder — identify expert sources on topics

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
- [Tool reference](docs/tools-reference.md)
- [API keys setup](docs/api-keys.md)
- [Architecture](docs/architecture.md)
- [Help & FAQ](docs/help.md)
- [Deployment guides](docs/deployment/)
- [Journey test](docs/journey-test.md)

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Author

Ahmed Adel Bakr Alderai
