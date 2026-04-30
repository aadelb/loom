# Loom Scraper Backend Integration Plan

## Overview

Integrate 5 open-source scraping backends into Loom's MCP server, creating an 8-level auto-escalation engine that can bypass virtually any anti-bot system.

## Current State

Loom has 3 scraping backends (all with issues):
- **Scrapling** (HTTP + stealth headers) — works for simple sites
- **Camoufox** (Firefox stealth) — broken (Playwright sync/async conflict)
- **Botasaurus** (Chrome stealth) — works but slow, last resort

## Target State: 8-Level Escalation Engine

```
Level 0: httpx              — Simple HTTP GET (fastest, 0 detection risk)
Level 1: scrapling          — HTTP with stealth headers + browser TLS
Level 2: crawl4ai           — Crawl4AI markdown extraction (existing)
Level 3: patchright          — Undetected Playwright fork (NEW - from CyberScraper-2077)
Level 4: nodriver            — Async undetected Chrome (NEW - 4.1K stars)
Level 5: crawlee             — Multi-backend framework with proxy rotation (NEW - 8.8K stars)
Level 6: zendriver           — Docker-optimized undetected Chrome (NEW - 1.3K stars)
Level 7: camoufox/botasaurus — Firefox/Chrome last resort (existing, fixed)
```

## Phase 1: CyberScraper-2077 Integration (Week 1)

### Source: github.com/itsOwen/CyberScraper-2077 (2.9K stars)

**What we take:**
1. `PlaywrightScraper` → Patchright-based stealth browser with:
   - Browser pooling + lock (`_browser_lock`)
   - Persistent context for max stealth
   - Human simulation (random scrolls, mouse moves, delays)
   - Cloudflare bypass with `cf_clearance` cookie detection
   - CAPTCHA handling with manual fallback
   - Concurrent page scraping (max 5)

2. `WebExtractor` → LLM-powered structured extraction:
   - HTML preprocessing (remove scripts/styles/nav/footer)
   - Token counting + chunking for large pages
   - Query caching (hash-based dedup)
   - Conversation history for multi-turn extraction
   - JSON extraction from LLM output (regex patterns)

3. `TorScraper` → .onion site support with circuit isolation

**What we adapt (NOT copy):**
- Replace langchain with Loom's native LLM cascade (Groq→NIM→DeepSeek→...)
- Replace Streamlit UI with MCP tool interface
- Replace model factory with Loom's provider system
- Add SSRF validation on all URLs
- Add Loom's caching layer

**New MCP Tools:**
| Tool | Function | Credit Weight |
|------|----------|--------------|
| `research_smart_extract` | URL + NL query → structured JSON | heavy (10) |
| `research_paginate_scrape` | Multi-page scraping with auto-pagination | heavy (10) |
| `research_stealth_browser` | Pure Patchright fetch (no LLM) | medium (3) |

**Files Created:**
- `src/loom/cyberscraper.py` — Main integration module (~400 lines)
- `src/loom/tools/cyberscraper_tools.py` — MCP tool wrappers
- `tests/test_cyberscraper.py` — 15+ tests

**Dependencies:**
```
pip install patchright beautifulsoup4 tiktoken
patchright install chromium
```

## Phase 2: nodriver Integration (Week 1)

### Source: github.com/ultrafunkamern/nodriver (4.1K stars)

**What we take:**
- Async-first undetected Chrome automation
- Zero configuration anti-detection
- Faster than Playwright (fewer overhead layers)
- Native async/await API

**New MCP Tools:**
| Tool | Function | Credit Weight |
|------|----------|--------------|
| `research_nodriver_fetch` | Async stealth Chrome fetch | medium (3) |
| `research_nodriver_extract` | CSS/XPath element extraction | medium (3) |
| `research_nodriver_session` | Persistent browser sessions | light (1) |

**Files Created:**
- `src/loom/nodriver_backend.py` — nodriver integration (~250 lines)
- `tests/test_nodriver_backend.py` — 15+ tests

**Dependencies:**
```
pip install nodriver
```

## Phase 3: Crawlee Python Integration (Week 2)

### Source: github.com/apify/crawlee-python (8.8K stars)

**What we take:**
- Multi-backend crawler (Playwright, HTTP, BeautifulSoup)
- Built-in proxy rotation
- Auto-scaling concurrency
- Request queue with dedup
- Sitemap discovery
- RAG-ready output formats

**New MCP Tools:**
| Tool | Function | Credit Weight |
|------|----------|--------------|
| `research_crawl` | Multi-page website crawl | heavy (10) |
| `research_sitemap_crawl` | Sitemap-based comprehensive crawl | heavy (10) |
| `research_structured_crawl` | Crawl + CSS selector extraction | heavy (10) |

**Files Created:**
- `src/loom/crawlee_backend.py` — Crawlee integration (~300 lines)
- `tests/test_crawlee_backend.py` — 15+ tests

**Dependencies:**
```
pip install crawlee[playwright,beautifulsoup]
```

## Phase 4: zendriver Integration (Week 2)

### Source: github.com/ABeens/zendriver (1.3K stars)

**What we take:**
- Docker-optimized browser automation
- nodriver wrapper with better defaults
- Batch URL processing
- Page interaction (click, fill, scroll)

**New MCP Tools:**
| Tool | Function | Credit Weight |
|------|----------|--------------|
| `research_zen_fetch` | Docker-friendly stealth fetch | medium (3) |
| `research_zen_batch` | Concurrent batch URL fetch | medium (3) |
| `research_zen_interact` | Page interaction (click, fill, scroll) | medium (3) |

**Files Created:**
- `src/loom/zendriver_backend.py` — zendriver integration (~200 lines)
- `tests/test_zendriver_backend.py` — 15+ tests

**Dependencies:**
```
pip install zendriver
```

## Phase 5: Unified Scraper Engine (Week 2)

### The crown jewel — auto-escalation across all 8 backends

**Architecture:**
```
ScraperEngine.fetch(url, mode="auto")
    │
    ├─ Level 0: httpx GET
    │   └─ Success? → Return content
    │   └─ Blocked? → Escalate ↓
    │
    ├─ Level 1: Scrapling (stealth headers)
    │   └─ Success? → Return + cache domain→level mapping
    │   └─ Blocked? → Escalate ↓
    │
    ├─ Level 2: Crawl4AI (markdown extraction)
    │   └─ Success? → Return markdown
    │   └─ Blocked? → Escalate ↓
    │
    ├─ Level 3: Patchright (CyberScraper)
    │   └─ Success? → Return + Cloudflare bypass
    │   └─ Blocked? → Escalate ↓
    │
    ├─ Level 4: nodriver (undetected Chrome)
    │   └─ Success? → Return
    │   └─ Blocked? → Escalate ↓
    │
    ├─ Level 5: Crawlee (proxy rotation)
    │   └─ Success? → Return
    │   └─ Blocked? → Escalate ↓
    │
    ├─ Level 6: zendriver (Docker Chrome)
    │   └─ Success? → Return
    │   └─ Blocked? → Escalate ↓
    │
    └─ Level 7: Camoufox/Botasaurus (last resort)
        └─ Success? → Return
        └─ All failed → Return error with escalation log
```

**Smart Domain Learning:**
- Cache which level works for each domain
- Next request to same domain starts at cached level
- Periodically retry lower levels (domains update their protection)

**New MCP Tools:**
| Tool | Function | Credit Weight |
|------|----------|--------------|
| `research_engine_fetch` | Auto-escalation fetch | varies by level |
| `research_engine_extract` | Fetch + LLM extraction | heavy (10) |
| `research_engine_batch` | Batch with per-URL escalation | heavy (10) |

**Files Created:**
- `src/loom/scraper_engine.py` — Unified engine (~500 lines)
- `tests/test_scraper_engine.py` — 20+ tests

## Deployment Plan

### Hetzner Server Setup
```bash
# Install all scraping dependencies
source /opt/research-toolbox/venv/bin/activate
pip install patchright nodriver zendriver crawlee[playwright,beautifulsoup]
pip install beautifulsoup4 tiktoken aiohttp aiohttp-socks

# Install browsers
patchright install chromium
playwright install chromium

# Restart
sudo systemctl restart research-toolbox
```

### Total New Tools: 15

| Category | Tools | Backends |
|----------|-------|----------|
| CyberScraper | 3 | Patchright + LLM extraction |
| nodriver | 3 | Undetected async Chrome |
| Crawlee | 3 | Multi-backend framework |
| zendriver | 3 | Docker-optimized Chrome |
| Scraper Engine | 3 | 8-level auto-escalation |

### Total Tool Count After: 260+ (from 245)

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Memory: 8 browser backends | Lazy loading — only import when called |
| Chrome conflicts | Each backend manages its own browser instance |
| Rate limiting by sites | Built-in delays + proxy support in Crawlee |
| Dependency bloat | All new backends are optional (ImportError → skip) |
| Hetzner disk space | Chrome binaries ~500MB total |

## Success Criteria

1. `research_engine_fetch` bypasses Cloudflare on first try (using cached level)
2. `research_smart_extract` returns structured JSON from any website
3. `research_crawl` crawls 50+ pages without being blocked
4. All 15 new tools registered and responding on Hetzner
5. Escalation engine tested against 10 known-difficult sites
