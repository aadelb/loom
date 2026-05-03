# Loom SDK Package Index

Complete file reference for the Loom SDK package.

## Core Package Files

### `/loom_sdk/__init__.py` (59 lines)
Package initialization and public API exports.

**Exports:**
- `LoomClient` — Main async client
- `LoomClientError` — Exception class
- All response models (SearchResponse, FetchResult, etc.)

**Version:** 0.1.0

### `/loom_sdk/client.py` (486 lines)
Main client implementation with all research methods.

**Class: LoomClient**
- `__init__(server_url, api_key, timeout)` — Initialize client
- `search(query, provider, n, ...)` — Web search
- `fetch(url, mode, ...)` — Single URL fetch
- `spider(urls, mode, ...)` — Parallel multi-URL fetch
- `deep(query, max_results, ...)` — Full research pipeline
- `ask_all_llms(prompt, max_tokens, ...)` — Multi-LLM query
- `reframe(prompt, strategy, model)` — Prompt reframing
- `list_tools()` — Tool discovery
- `health_check()` — Server health
- `_call_tool(tool_name, **kwargs)` — Internal RPC caller
- `_ensure_client()` — HTTP client management
- `close()` — Resource cleanup
- `__aenter__()`, `__aexit__()` — Context manager

**Exception: LoomClientError**
- Raised for connection, HTTP, JSON, or tool errors

### `/loom_sdk/models.py` (156 lines)
Pydantic v2 response models for type safety.

**Models:**
- `SearchResult` — Single search result (title, url, snippet, metadata)
- `SearchResponse` — Search API response (provider, query, results, count)
- `FetchResult` — Single URL fetch (url, status_code, content, html, json, encoding)
- `SpiderResponse` — Multi-URL fetch (urls_queued, succeeded, failed, results)
- `ResearchReport` — Deep research output (query, summary, findings, sources, citations, confidence)
- `ReframeResult` — Prompt reframing (original_prompt, reframed_prompt, strategy_name, difficulty, safety_flags)
- `LLMResponse` — Single LLM provider response (provider, prompt, response, tokens, latency)
- `AskAllResponse` — Multi-LLM response (prompt, responses, providers_queried, fastest_provider)
- `ToolInfo` — Tool metadata (name, description, parameters, category)
- `ToolListResponse` — Tool list (total_tools, tools, categories)
- `HealthCheckResponse` — Server health (status, version, uptime, tools_available, providers)

All models include:
- Field validation
- Default values
- JSON serialization
- Datetime timestamps

## Configuration Files

### `/pyproject.toml` (75 lines)
Package metadata and dependency configuration.

**Sections:**
- `[project]` — Package metadata (name, version, description, authors, etc.)
- `[project.dependencies]` — Runtime dependencies (httpx, pydantic)
- `[project.optional-dependencies]` — Dev dependencies (pytest, ruff, mypy, etc.)
- `[build-system]` — Build configuration (hatchling backend)
- `[tool.ruff]` — Linting and formatting rules
- `[tool.mypy]` — Type checking configuration

**Runtime Dependencies:**
- httpx>=0.28
- pydantic>=2.12

**Dev Dependencies:**
- pytest>=8
- pytest-asyncio>=0.24
- pytest-httpx>=0.30
- ruff>=0.7
- mypy>=1.13
- pre-commit>=4

### `/.gitignore`
Standard Python gitignore with:
- `__pycache__/` directories
- `.pyc` compiled files
- Virtual environments (venv/, .venv/)
- IDE files (.vscode/, .idea/)
- Build artifacts (dist/, build/)

## Test Files

### `/tests/__init__.py`
Test package marker.

### `/tests/test_client.py` (122 lines)
Test suite with unit and mock integration tests.

**Test Functions:**
- `test_client_initialization()` — Client setup
- `test_client_with_api_key()` — Auth support
- `test_context_manager()` — Async context manager
- `test_search_parsing()` — Search response parsing
- `test_fetch_parsing()` — Fetch response parsing
- `test_error_handling()` — Error scenarios
- `test_models_validation()` — Model validation

**Test Coverage:**
- Client initialization
- API key handling
- HTTP mocking via AsyncMock
- Response parsing
- Error handling
- Model creation

## Example Files

### `/examples/01_basic_search.py` (38 lines)
Simple web search example.

**Demonstrates:**
- Client initialization
- `search()` method
- Result iteration
- Output formatting

**Run:** `python examples/01_basic_search.py`

### `/examples/02_deep_research.py` (63 lines)
Full deep research pipeline example.

**Demonstrates:**
- `deep()` method
- 12-stage research pipeline
- Summary, findings, sources
- Confidence scores

**Run:** `python examples/02_deep_research.py`

### `/examples/03_multi_llm.py` (57 lines)
Query all LLM providers example.

**Demonstrates:**
- `ask_all_llms()` method
- Multi-provider querying
- Performance comparison
- Error handling per provider

**Run:** `python examples/03_multi_llm.py`

### `/examples/04_bulk_fetch.py` (55 lines)
Parallel multi-URL fetching example.

**Demonstrates:**
- `spider()` method
- Concurrent requests
- Configurable concurrency
- Result aggregation

**Run:** `python examples/04_bulk_fetch.py`

### `/examples/05_prompt_reframe.py` (49 lines)
Prompt reframing example.

**Demonstrates:**
- `reframe()` method
- Strategy selection
- Safety flags
- Difficulty levels

**Run:** `python examples/05_prompt_reframe.py`

## Documentation Files

### `/README.md` (10.1 KB)
Main package documentation.

**Sections:**
- Installation (pip, source)
- Quick start (3-minute tutorial)
- Async context manager example
- API reference (all 8 methods)
- Response models
- Configuration (server URL, auth, timeout)
- Error handling
- 4 advanced examples
- Performance tips
- Troubleshooting
- Development setup
- Links

### `/QUICK_START.md`
2-minute quick start guide.

**Sections:**
- Installation (1 command)
- Starting server
- Basic usage (3-line example)
- API cheat sheet (all 8 methods)
- Common patterns (4 examples)
- Troubleshooting (3 quick fixes)
- Next steps

### `/INSTALL.md` (60 lines)
Detailed installation guide.

**Sections:**
- Prerequisites
- PyPI installation (future)
- Source installation (4 steps)
- Virtual environment setup
- Verification
- Start Loom server
- Run examples
- Environment variables
- Programmatic configuration
- Development setup
- Troubleshooting
- Next steps

### `/CHANGELOG.md`
Version history and release notes.

**Current Release:**
- Version 0.1.0 (2026-05-03)
- Initial release
- 8 core methods
- 11 response models
- 5 examples
- Comprehensive documentation

### `/STRUCTURE.md` (220 lines)
Detailed architecture documentation.

**Sections:**
- Directory layout (ASCII tree)
- Module overview (each file)
- Installation & usage
- Key features (7 categories)
- Response models (detailed specs)
- Error handling
- Configuration (server, auth, timeout)
- Testing procedures
- Examples (5 runnable)
- Dependencies
- Package distribution
- Development workflow
- Future enhancements
- License & links

### `/INDEX.md` (This file)
Complete file reference and package index.

## File Statistics

| Category | Count | Lines |
|----------|-------|-------|
| Core Modules | 3 | 701 |
| Tests | 2 | 122 |
| Examples | 5 | 262 |
| Documentation | 6 | ~2,000 |
| Configuration | 2 | 80 |
| **Total** | **18** | **~3,100** |

## Installation

```bash
cd /Users/aadel/projects/loom/sdk
pip install -e .
```

## Quick Usage

```python
from loom_sdk import LoomClient

async with LoomClient() as client:
    # Search
    results = await client.search("topic", n=10)
    
    # Deep research
    report = await client.deep("research question")
    
    # Multi-LLM
    responses = await client.ask_all_llms("question")
```

## Project Layout

```
/Users/aadel/projects/loom/
├── src/loom/                 # Main Loom MCP server
├── sdk/                      # Loom SDK (Python client) ← YOU ARE HERE
│   ├── loom_sdk/            # Package source
│   ├── tests/               # Test suite
│   ├── examples/            # Usage examples
│   └── docs/                # Documentation
└── ...
```

## Key Files by Purpose

**To use the SDK:**
- Start: `README.md` → `QUICK_START.md`
- Install: `INSTALL.md`
- Reference: `/loom_sdk/client.py` docstrings

**To understand the SDK:**
- Architecture: `STRUCTURE.md`
- Code: `/loom_sdk/models.py` (response types)
- Examples: `/examples/` directory

**To develop/contribute:**
- Tests: `/tests/test_client.py`
- Config: `pyproject.toml`
- Setup: `INSTALL.md` → "Development Setup"

**To integrate with Loom server:**
- API docs: `README.md` → "API Reference"
- Examples: `/examples/` directory
- Error handling: `README.md` → "Error Handling"

## Version & License

- **Version:** 0.1.0
- **Released:** 2026-05-03
- **License:** Apache-2.0
- **Author:** Ahmed Adel Bakr Alderai
- **Repository:** https://github.com/aadelb/loom

## Next Steps

1. **Read:** `QUICK_START.md` (2 minutes)
2. **Install:** `pip install -e .`
3. **Try:** `python examples/01_basic_search.py`
4. **Reference:** `README.md` (API documentation)
5. **Explore:** `examples/` directory (5 examples)
