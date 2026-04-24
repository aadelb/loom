# Community 2: Tool Registry & Research Workflows

**Modules:** `tools/__init__.py`, `cli.py`, `journey.py`, `params.py`

## Purpose

This community implements the 23 MCP research tools, their parameter models, CLI routing, and research journey tracking. It bridges user intent (CLI commands or MCP calls) to execution (fetch, search, spider, markdown, LLM, etc.).

## Key Classes & Functions

### `tools/__init__.py`
- **Tool registry** — Exports all 23 tools with their handlers
- Lazy imports for fetch, search, spider, markdown, GitHub, deep, stealth, cache management
- `__all__` defines public MCP tool interface

### `cli.py`
- **`LoopCompleter`** — Interactive CLI auto-completion for tool names/flags
- **`@app.command()` functions** — Each Typer command maps to a tool (e.g., `loom fetch`, `loom search`)
- Command dispatch to tool handlers with param validation

### `journey.py`
- **`Step`** — Single research operation (tool, params, result, duration)
- **`JourneyReport`** — Tracks multi-step research workflows, aggregates results, timeline
- Used for audit trails and research reproducibility

### `params.py`
- **`FetchParams`** — URL, timeout, headers, cache behavior, stealth mode
- **`SpiderParams`** — Seed URLs, depth, filter patterns, concurrency
- **`MarkdownParams`** — HTML→Markdown conversion options
- **`SearchParams`** — Query, limit, filters, backend selection
- **`DeepParams`** — Full research pipeline (search + fetch + markdown)

## Data Flow

1. User calls `loom fetch <url>` or invokes MCP tool
2. CLI parses args → `FetchParams` instance
3. Typer command handler calls tool function from `tools/*`
4. Tool executes, returns result
5. `JourneyReport` optionally logs step (timestamp, params, output, cost)
6. Result returned to user or streamed over MCP

## Dependencies

- **Inbound:** User input via CLI or MCP calls
- **Outbound:** → `tools/*` modules (fetch, search, spider, etc.), → `providers/base.py` (LLM dispatch), → `validators.py` (input validation)
- **Key edges:** ← server.py (tool registration), → sessions.py (session context)

## Module Paths

- `src/loom/tools/__init__.py` (50 LOC)
- `src/loom/cli.py` (300+ LOC)
- `src/loom/journey.py` (350+ LOC)
- `src/loom/params.py` (200 LOC)
