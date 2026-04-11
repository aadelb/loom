# Changelog

All notable changes to Loom are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/aadelb/loom/compare/v0.1.0-alpha.1...HEAD
[0.1.0-alpha.1]: https://github.com/aadelb/loom/releases/tag/v0.1.0-alpha.1
