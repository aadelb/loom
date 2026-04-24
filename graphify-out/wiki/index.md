# Loom Architecture Wiki

## Overview

**Loom** is a Smart Internet Research MCP Server that weaves scraping, search, LLMs, and persistent browser sessions into a single research thread. It exposes 23 MCP tools over streamable-HTTP and a Typer CLI for terminal use. The platform integrates multi-backend LLM support (Anthropic, OpenAI, vLLM, NVIDIA NIM), session-based research workflows, and comprehensive caching/stealth mechanisms for conducting advanced research operations across web scraping, semantic search, and model evaluation.

## Key Communities

| Community | Top God Nodes | Purpose | Docs |
|-----------|---------------|---------|------|
| **Core Architecture** | `server.py`, `sessions.py`, `config.py` | MCP server initialization, session management, configuration | [Community 1](./community_1.md) |
| **Tool Registry** | `tools/__init__.py`, `cli.py`, `journey.py` | 23 research tools, CLI dispatch, research journey tracking | [Community 2](./community_2.md) |
| **LLM Providers** | `providers/base.py`, `providers/anthropic_provider.py`, `providers/nvidia_nim.py` | Multi-backend LLM abstraction, cost tracking, provider interfaces | [Community 3](./community_3.md) |
| **Web Research Tools** | `tools/fetch.py`, `tools/search.py`, `tools/spider.py` | HTTP fetching, semantic search, multi-URL crawling | [Community 4](./community_4.md) |
| **Data Processing** | `tools/markdown.py`, `tools/cache_mgmt.py`, `validators.py` | Markdown conversion, cache operations, URL/input validation | [Community 5](./community_5.md) |

## Top 10 God Nodes (by degree)

1. **`servers.py`** (12 edges) — MCP server initialization, tool registration, HTTP/streamable transport
2. **`sessions.py`** (10 edges) — SessionManager, SessionMetadata, state persistence
3. **`config.py`** (8 edges) — ConfigModel, environment-based config, error suppression
4. **`providers/base.py`** (8 edges) — LLMProvider interface, LLMResponse, cost tracking abstractions
5. **`cli.py`** (7 edges) — Typer CLI dispatch, LoopCompleter, command routing
6. **`tools/fetch.py`** (6 edges) — FetchResult, HTTP client abstraction, stealth headers
7. **`tools/search.py`** (6 edges) — research_search, tool_search, semantic search routing
8. **`journey.py`** (5 edges) — Step, JourneyReport, research workflow tracking
9. **`params.py`** (5 edges) — FetchParams, SpiderParams, MarkdownParams, tool parameter models
10. **`tools/__init__.py`** (4 edges) — Tool registration, __all__ exports

## Architecture Highlights

- **26 Python modules** across core, providers, tools, and utilities
- **5 primary communities** with clear separation of concerns
- **Multi-provider LLM abstraction** supporting Anthropic, OpenAI, vLLM, NVIDIA NIM
- **Session-based research workflows** via JourneyReport and SessionManager
- **Comprehensive caching** with cache stats, eviction, and TTL management
- **Stealth mechanisms** including Camoufox browser sessions and rotating headers

---

*Wiki generated from AST analysis of 26 Python modules in `src/loom/`. See community articles for detailed module relationships and data flow.*
