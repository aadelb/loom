# Loom Wiki Navigation

## Quick Start

1. **[index.md](./index.md)** — Start here. Overview, communities table, top 10 god nodes
2. **Community Articles** — Deep dive by architectural tier:
   - [Community 1: Core Architecture](./community_1.md) — server, sessions, config
   - [Community 2: Tool Registry & Workflows](./community_2.md) — CLI, tools, params, journey
   - [Community 3: LLM Provider Abstraction](./community_3.md) — Multi-backend LLM support
   - [Community 4: Web Research Tools](./community_4.md) — Fetch, search, spider, GitHub, stealth
   - [Community 5: Data Processing & Utilities](./community_5.md) — Markdown, cache, validators

## By Use Case

### I want to understand the MCP server
→ Read [Community 1](./community_1.md)

### I want to add a new research tool
→ Read [Community 2](./community_2.md) for params, [Community 4](./community_4.md) for implementation

### I want to add a new LLM provider
→ Read [Community 3](./community_3.md), especially `providers/base.py`

### I want to optimize caching
→ Read [Community 5](./community_5.md), focus on `cache.py`

### I want to understand data flow
→ Read "Data Flow" sections in each community article

## Statistics

- **6 files** (1 index + 5 communities + 1 navigation)
- **313 lines of documentation**
- **26 Python modules** analyzed
- **5 architectural communities** identified
- **10 god nodes** ranked by degree

---

*Last updated: 2026-04-12 | Loom v0.1.0a1*
