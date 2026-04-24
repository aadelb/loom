# Community 1: Core Architecture

**Modules:** `server.py`, `sessions.py`, `config.py`, `__init__.py`, `__main__.py`

## Purpose

This community forms the foundation of Loom—server initialization, session lifecycle management, and system-wide configuration. All MCP tools register through `server.py`, which manages the streamable-HTTP transport and tool dispatch.

## Key Classes & Functions

### `server.py`
- **`create_app()`** — Initializes MCP FastAPI server, registers 23 tools
- **`_register_tools(app)`** — Dynamically imports and registers all tool handlers
- **`main()`** — Entry point for `loom` CLI server mode

### `sessions.py`
- **`SessionManager`** — Manages persistent browser sessions, metadata, lifecycle
- **`SessionMetadata`** — Tracks session state, timestamps, request/response counts

### `config.py`
- **`ConfigModel`** — Pydantic-based config, reads env vars (LOOM_CACHE_DIR, LOOM_LOG_LEVEL, etc.)
- **`suppress_errors()`** — Decorator for error suppression in config loading

### `__init__.py`
- Exports public API: `CacheStore`, `validate_url`, `UrlSafetyError`, version info

## Data Flow

1. CLI invokes `main()` in `server.py`
2. `create_app()` loads `ConfigModel` from environment
3. Tool discovery via `_register_tools()` → each tool gets session context
4. `SessionManager` maintains lifecycle → used by fetch/search/spider tools
5. All operations logged and cached per `config.cache_dir`

## Dependencies

- **Inbound:** Entrypoint for all CLI commands
- **Outbound:** Uses `ConfigModel` (config), manages sessions, calls `_register_tools()` to wire up tool module
- **Key edges:** → `params.py` (tool params), → `providers/base.py` (LLM dispatch), → `tools/*` (all tools)

## Module Paths

- `src/loom/server.py` (100 LOC)
- `src/loom/sessions.py` (350 LOC)
- `src/loom/config.py` (250 LOC)
