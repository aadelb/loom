# Changelog

All notable changes to the Loom SDK project are documented in this file.

## [0.1.0] - 2026-05-03

### Added

- Initial release of Loom SDK
- `LoomClient` async client for Loom MCP server
- Core methods:
  - `search()` — Web search across 21+ providers
  - `fetch()` — Single URL fetching with Cloudflare bypass
  - `spider()` — Parallel multi-URL fetching
  - `deep()` — Full 12-stage research pipeline
  - `ask_all_llms()` — Query 7+ LLM providers in parallel
  - `reframe()` — Prompt reframing with 957+ strategies
  - `list_tools()` — Discover available tools
  - `health_check()` — Server status monitoring
- Comprehensive Pydantic models for all responses
- Full async/await support with context managers
- Authentication support via API keys
- Error handling with `LoomClientError` exception
- Type hints on all functions and methods
- Examples for all major use cases
- Full documentation with API reference
- Test suite with unit and mock integration tests
