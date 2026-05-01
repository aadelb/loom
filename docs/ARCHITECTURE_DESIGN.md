# Loom MCP Server — Architecture Design Document

**Version:** 1.0  
**Date:** 2026-05-02  
**Author:** Ahmed Adel Bakr Alderai  

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Component Architecture](#component-architecture)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Tool Ecosystem](#tool-ecosystem)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Scalability & Performance](#scalability--performance)
9. [Design Patterns & Principles](#design-patterns--principles)

---

## System Overview

### What is Loom?

Loom is a Python MCP (Model Context Protocol) server that exposes **220+ research and attack tools** over **streamable-HTTP** (port 8787). It aggregates scraping, search, LLM, OSINT, dark web, privacy, and compliance testing capabilities into a single unified interface.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Client (Claude, Apps)                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    streamable-HTTP (port 8787)
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      FastMCP Server                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Tool Registration System (_register_tools, _wrap_tool)   │   │
│  │ - 154 tool modules (220+ MCP tools)                      │   │
│  │ - 957 prompt reframing strategies                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
    ┌────────────┐        ┌────────────┐      ┌──────────────┐
    │ Validation │        │   Cache    │      │  Rate Limit  │
    │  Layer     │        │   System   │      │   & Auth     │
    │ (Pydantic  │        │ (SHA-256)  │      │              │
    │  v2)       │        │            │      │              │
    └────────────┘        └────────────┘      └──────────────┘
        │                      │
        └──────────────────────┼──────────────────────┐
                               │                      │
        ┌──────────────────────┴──────────────────────┴────────────────────┐
        │                                                                   │
        ▼                                                                   ▼
    ┌────────────────────────────┐              ┌──────────────────────────┐
    │  Provider Cascade Layer     │              │  Tool Execution Engine   │
    │  (8 LLM providers)          │              │  (Async/concurrent)      │
    │  (21 Search providers)      │              │                          │
    │  Fallback on error          │              │ - Scraping (Scrapling,   │
    │                             │              │   Crawl4AI, Playwright)  │
    └────────────────────────────┘              │ - Search (Multi-provider)│
                                                 │ - LLM (Chat, embed, etc) │
                                                 │ - OSINT / Dark Web       │
                                                 │ - Privacy & Compliance   │
                                                 └──────────────────────────┘
                                                           │
                                                           ▼
                                                 ┌──────────────────────────┐
                                                 │  Storage & Persistence   │
                                                 │                          │
                                                 │ - SQLite (sessions, DB)  │
                                                 │ - Gzip Cache (daily dir) │
                                                 │ - Config (JSON + atomic) │
                                                 │ - Audit Logs             │
                                                 └──────────────────────────┘
```

### Key Facts

| Attribute | Value |
|-----------|-------|
| **Language** | Python 3.11+ |
| **Framework** | FastMCP + AsyncIO |
| **Protocol** | MCP over streamable-HTTP |
| **Port** | 8787 (configurable) |
| **Tool Count** | 220+ MCP tools across 154 modules |
| **Strategies** | 957 reframing strategies (32 modules) |
| **LLM Providers** | 8 (Groq, NVIDIA NIM, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic, vLLM) |
| **Search Providers** | 21 (Exa, Tavily, Firecrawl, Brave, DuckDuckGo, ArXiv, Wikipedia, HN, Reddit, NewsAPI, Crypto, Coindesk, Binance, Investing, Ahmia, Darksearch, UMMRO, Onion, Torcrawl, CTI, Robin) |
| **Deployment** | Hetzner (128GB RAM, systemd) or local dev |
| **Testing** | pytest (1500+ tests, 80%+ coverage) |

---

## Technology Stack

### Core Dependencies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **MCP Framework** | `mcp` / `FastMCP` | Server framework + tool registration |
| **Web Framework** | `starlette` | HTTP/WebSocket transport |
| **Async Runtime** | `asyncio` | Concurrent tool execution |
| **Validation** | `pydantic` v2 | Input validation (strict mode) |
| **Scraping** | `Scrapling`, `Crawl4AI`, `Playwright`, `Camoufox`, `Botasaurus` | Multi-tier fetch escalation |
| **Search** | 21 provider APIs + `exa`, `tavily`, `firecrawl`, `brave` SDKs | Semantic + traditional search |
| **LLM Providers** | `openai`, `anthropic`, `groq`, deepseek, gemini, kimi SDKs | Multi-provider cascade |
| **Database** | `sqlite3` | Session storage, persistence |
| **Caching** | `gzip`, `hashlib` (SHA-256) | Content-hash cache |
| **CLI** | `typer` | Command-line interface |
| **Logging** | `logging` + `structlog` | Structured tracing & audit |
| **Config** | `pydantic` BaseModel | Runtime config with validation |

### Python Version & Typing

- **Minimum:** Python 3.11
- **Type Hints:** All signatures have type annotations
- **Type Checking:** mypy strict mode + pydantic plugin
- **Code Quality:** Ruff (lint + format), Black formatter

---

## Component Architecture

### 1. MCP Transport Layer

**File:** `src/loom/server.py`

The FastMCP instance is the core server that:
1. Listens on `LOOM_HOST:LOOM_PORT` (default `127.0.0.1:8787`)
2. Exposes tools via the MCP protocol
3. Handles client authentication (optional)
4. Routes requests to tool wrappers

```python
# Pseudo-code structure
from mcp.server import FastMCP

mcp = FastMCP("loom")

# Tools registered dynamically:
for tool_module in TOOL_MODULES:
    for tool_func in tool_module.__dict__.values():
        if hasattr(tool_func, "_is_mcp_tool"):
            mcp.tool()(tool_func)
```

**Key Pattern:** `_wrap_tool()` decorator handles:
- Rate limiting
- Input validation
- Error handling
- Tracing
- Cost tracking

### 2. Tool Registration System

**Files:** `src/loom/server.py::_register_tools()`, `src/loom/tools/*.py`

**Process:**

```
Tool Module (e.g., fetch.py)
    ↓
Exports function (e.g., research_fetch)
    ↓
@mcp.tool() decorator registration
    ↓
Parameter validation (FetchParams in params.py)
    ↓
Tool execution with rate limiting
    ↓
Response serialization to JSON
```

**Tool Categories:**

| Category | Module Count | Tool Count | Examples |
|----------|-------------|-----------|----------|
| **Scraping Core** | 5 | 8 | fetch, spider, markdown, camoufox, botasaurus |
| **Search** | 1 | 21 | research_search (multi-provider abstraction) |
| **LLM** | 5 | 10+ | research_llm_summarize, chat, embed, translate |
| **Killer Research** | 20 | 45+ | dark_forum, infra_correlator, leak_scan, metadata_forensics |
| **Dark Web & OSINT** | 25 | 60+ | onion_discover, crypto_trace, threat_profile, darkweb_cti |
| **Academic Integrity** | 11 | 35+ | citation_analysis, grant_forensics, predatory_journal_check |
| **AI Safety (EU Article 15)** | 7 | 15+ | prompt_injection_test, bias_probe, compliance_check |
| **Privacy & Anonymity** | 8 | 20+ | fingerprint_audit, privacy_exposure, steganography |
| **Career Intelligence** | 6 | 15+ | job_signals, salary_synthesizer, resume_intel |
| **Creative & Psycho** | 11 | 25+ | prompt_reframe, persona_profile, psycholinguistic |
| **Infrastructure & Billing** | 12 | 30+ | vastai, billing, email_report, stripe_integration |
| **Session & Config** | 6 | 6 | research_session_open, research_config_set |

**Total:** 154 modules, 220+ tools

### 3. Validation Layer

**File:** `src/loom/params.py`, `src/loom/validators.py`

Every tool has a **Pydantic v2** parameter model with:
- `extra="forbid"` (rejects unknown fields)
- `strict=True` (no type coercion)
- Field validators for security

```python
class FetchParams(BaseModel):
    url: str  # Validated via validate_url() → SSRF-safe
    mode: Literal["http", "stealthy", "dynamic"] = "stealthy"
    max_chars: int = 20000  # Hard-capped
    headers: dict[str, str] | None = None  # Filtered via filter_headers()
    proxy: str | None = None  # Format validated (http://, socks5://, etc.)
    timeout: int | None = None  # Bounds-checked
    
    model_config = {"extra": "forbid", "strict": True}
    
    @field_validator("url", mode="before")
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)  # Prevents SSRF, DNS rebinding, etc.
```

**SSRF Prevention in `validators.py`:**

1. URL parsing (scheme, host, port extraction)
2. Private IP blacklist check (127.0.0.1, 10.0.0.0/8, 169.254.0.0/16, etc.)
3. DNS resolution with caching & TOCTOU prevention (5-min TTL)
4. Reverse DNS validation (ptr record match)
5. Character capping (URLs max 2048 chars)

### 4. Provider Cascade Architecture

**Files:** `src/loom/providers/base.py`, `src/loom/providers/*_provider.py`

All providers inherit from **abstract `LLMProvider` class**:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list, model: str, **kwargs) -> LLMResponse:
        """Generate text completion."""
    
    @abstractmethod
    async def embed(self, text: str, model: str) -> list[float]:
        """Generate embeddings."""
    
    @abstractmethod
    async def available(self) -> bool:
        """Check if provider is operational."""
    
    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
```

**LLM Cascade Order (Config Key: `LLM_CASCADE_ORDER`):**

```
Default: ["groq", "nvidia_nim", "deepseek", "gemini", "moonshot", "openai", "anthropic", "vllm"]
```

**Fallback Logic:**

1. Call provider 1 (Groq)
   - If available & responds → return response
   - If unavailable or error → try provider 2
2. Repeat until success or all providers exhausted
3. Return error with cascade trace for debugging

**Cost Estimation (`providers/base.py::_estimate_cost()`):**

| Provider | Pricing |
|----------|---------|
| NVIDIA NIM | Free (free tier at integrate.api.nvidia.com) |
| vLLM | Free (self-hosted) |
| Groq | API pricing (check docs) |
| DeepSeek | $0.14/M in, $0.42/M out (approx) |
| Gemini | $0.0075/1K in, $0.03/1K out (free tier limited) |
| Moonshot (Kimi) | $1.25/M in, $5/M out (approx) |
| OpenAI (GPT-5) | $0.60/M in, $2.40/M out |
| Anthropic (Opus) | $15/M in, $75/M out |

### 5. Cache System

**File:** `src/loom/cache.py`

**Design:**

```
Input (URL, params, tool name)
    ↓
SHA-256 hash (first 32 hex chars)
    ↓
Daily directory structure: ~/.cache/loom/YYYY-MM-DD/
    ↓
Gzip-compressed JSON files (.json.gz)
    ↓
Atomic write (uuid tmp file + os.replace)
    ↓
Fallback to legacy .json files for backward compat
```

**Key Features:**

- **Deduplication:** Same URL + params = same hash hit (even across days)
- **Compression:** 60%+ space savings via gzip level 6
- **Atomicity:** No partial writes or corrupted cache entries
- **TTL:** `CACHE_TTL_DAYS` config (default 30) for cleanup
- **Singleton:** `get_cache()` returns shared instance per process
- **Concurrency:** Thread-safe via atomic OS operations

**Cache Hits:**

```python
cache_key = f"{tool}::{params}::{url}"
cached = cache.get(cache_key)
if cached:
    return cached  # No external request needed
else:
    result = fetch_from_external()
    cache.put(cache_key, result)
    return result
```

### 6. Session Management

**File:** `src/loom/sessions.py`

Two-tier system for persistent browser state:

**In-Memory Registry** (fast, per-process):
- Global `_sessions` dict with asyncio.Lock
- Session name regex: `^[a-z0-9_-]{1,32}$`
- Used for fast session lookups

**SQLite-Backed SessionManager** (persistent, LRU):
- Max 8 concurrent sessions
- Stores Playwright/Camoufox browser state
- Auto-evicts oldest session when limit reached
- Survives server restarts

**Tools:**
- `research_session_open(name, browser_type="chromium")` → session_id
- `research_session_list()` → all sessions with state
- `research_session_close(session_id)` → cleanup

### 7. Configuration System

**File:** `src/loom/config.py`

**Design:**

```python
CONFIG: dict[str, Any] = {}  # Module-level dict (read-only for most code)

class ConfigModel(BaseModel):
    """Validated config with bounds."""
    SPIDER_CONCURRENCY: int = Field(default=10, ge=1, le=20)
    CACHE_TTL_DAYS: int = Field(default=30, ge=1, le=365)
    LLM_CASCADE_ORDER: list[str] = Field(default=[...])
    # ... 30+ fields with validation
```

**Config Resolution (priority order):**

1. `LOOM_CONFIG_PATH` environment variable (explicit path)
2. `./config.json` (current directory)
3. Default ConfigModel values

**Load/Save Pattern:**

```python
# Load from disk (startup)
load_config(path_or_none)  # Merges over defaults, validates

# Update a key (runtime)
set("SPIDER_CONCURRENCY", 15)  # Validates, saves atomically, updates CONFIG dict

# MCP tools
research_config_get(key_or_none)  # Return current config
research_config_set(key, value)   # Atomic update + persist
```

### 8. Rate Limiting

**File:** `src/loom/rate_limiter.py`

**Design:**

Sliding-window counter per **tool category** (not per individual tool):

```
Tool category examples:
- "scrape" → fetch, spider, markdown
- "search" → research_search
- "llm" → llm_summarize, llm_chat
- "dark_web" → dark_forum, onion_discover
```

**Configuration:**

```python
RATE_LIMITS = {
    "scrape": (10, 60),      # 10 calls per 60 seconds
    "search": (20, 60),      # 20 calls per 60 seconds
    "llm": (5, 60),          # 5 calls per 60 seconds
    "dark_web": (3, 60),     # 3 calls per 60 seconds
    # ... per category
}
```

**Persistence (optional):**

If `RATE_LIMIT_PERSIST=true` in config, uses SQLite to survive restarts.

**Decorator Usage:**

```python
@rate_limited(category="scrape")
async def research_fetch(...):
    pass
```

Returns error dict on limit exceeded:

```python
{
    "error": "rate_limit_exceeded",
    "category": "scrape",
    "limit": 10,
    "window_seconds": 60,
    "reset_at": "2026-05-02T10:35:00Z"
}
```

### 9. Authentication & Authorization

**File:** `src/loom/auth.py`

Optional MCP-level authentication via `AuthSettings`:

```python
auth_settings = AuthSettings(
    require_auth=True,  # Optional
    allowed_keys=[...]  # API key whitelist
)
mcp = FastMCP(..., auth_settings=auth_settings)
```

Can also use environment variable `LOOM_API_KEY` for client validation.

---

## Data Flow Diagrams

### 1. Client Request → Tool Execution → Response

```
Client Request
    ↓
+─────────────────────────────────────────────┐
│ HTTP POST to localhost:8787/mcp             │
│ Body: { "tool": "research_fetch",           │
│         "params": {...} }                   │
└─────────────────┬───────────────────────────┘
                  ↓
         ┌────────────────────────┐
         │ FastMCP Dispatcher     │
         │ Finds tool by name     │
         └────────────┬───────────┘
                      ↓
    ┌─────────────────────────────────────┐
    │ Pydantic Validation (params.py)      │
    │ - Check required fields              │
    │ - extra="forbid" mode                │
    │ - Field-level validators             │
    │   (URL SSRF check, header filter,    │
    │    proxy format, timeout bounds)     │
    │ Result: FetchParams (validated)      │
    └────────────────┬──────────────────────┘
                     ↓
    ┌─────────────────────────────────────┐
    │ Rate Limit Check (@rate_limited)    │
    │ - Get category (e.g., "scrape")     │
    │ - Check sliding-window counter      │
    │ - On limit: return error dict       │
    │ - On success: continue              │
    └────────────────┬──────────────────────┘
                     ↓
    ┌─────────────────────────────────────┐
    │ Cache Lookup (cache.py)              │
    │ - Hash params to key                │
    │ - Check ~/.cache/loom/YYYY-MM-DD/   │
    │ - If hit: return cached JSON        │
    │ - If miss: continue                 │
    └────────────────┬──────────────────────┘
                     ↓
    ┌─────────────────────────────────────┐
    │ Tool Execution (tools/*.py)          │
    │ - Async function runs                │
    │ - External API calls, scraping, etc. │
    │ - Result: dict or error              │
    └────────────────┬──────────────────────┘
                     ↓
    ┌─────────────────────────────────────┐
    │ Cache Write (if success)             │
    │ - Compute SHA-256 hash of key       │
    │ - Create daily dir if needed        │
    │ - Write gzip-compressed JSON        │
    │ - Atomic: uuid tmp + os.replace     │
    └────────────────┬──────────────────────┘
                     ↓
    ┌─────────────────────────────────────┐
    │ Response Serialization               │
    │ - Convert result to JSON             │
    │ - Include metadata (cost, latency)   │
    │ - Add tracing headers                │
    └────────────────┬──────────────────────┘
                     ↓
           HTTP 200 + JSON body
           back to client
```

### 2. Deep Research Pipeline (12 Stages)

**File:** `src/loom/tools/deep.py`

```
research_deep(query, include_sentiment=True, ...)
    ↓
Stage 1: Query Parsing & Intent Detection
    - Is this academic? (arxiv keywords)
    - Is this code? (github, python, etc.)
    - Is this knowledge? (wikipedia-style)
    - Or general search?
    ↓
Stage 2: Provider Selection
    - academic → arxiv + wikipedia
    - code → github
    - general → exa (semantic) + brave (traditional)
    ↓
Stage 3: Initial Search
    - Parallel search across selected providers
    - Deduplicate results
    - Rank by relevance score
    ↓
Stage 4: URL Filtering & Validation
    - SSRF check (validators.validate_url)
    - Content-type check (is it fetchable?)
    - Dedup by domain (avoid redundant fetches)
    ↓
Stage 5: Fetch with Escalation
    - Try HTTP (Scrapling http mode)
    - If Cloudflare/403 → escalate to stealthy
    - If still blocked → escalate to dynamic (Playwright)
    - Parallel fetches (SPIDER_CONCURRENCY)
    ↓
Stage 6: Markdown Extraction
    - Crawl4AI for rich content extraction
    - Fallback to Trafilatura for simple HTML
    - Result: clean markdown text
    ↓
Stage 7: Content Deduplication
    - Hash markdown to detect duplicate content
    - Keep highest-quality version
    ↓
Stage 8: Structured Extraction (LLM-powered)
    - Use LLM cascade to extract:
      * Key claims
      * Methodology
      * Limitations
      * Evidence strength
    ↓
Stage 9: Citation & Reference Parsing
    - Extract bibliography from markdown
    - Validate citations
    - Build citation graph
    ↓
Stage 10: Community Sentiment Aggregation
    - If include_sentiment=True:
      * Search Hacker News comments
      * Search Reddit discussions
      * Aggregate sentiment scores
    ↓
Stage 11: Quality Ranking
    - Score sources by:
      * Authority (domain reputation)
      * Recency (publication date)
      * Community engagement (HN/Reddit votes)
      * Citation count
    ↓
Stage 12: Final Output Formatting
    - Return ranked results with:
      * Full content (markdown)
      * Metadata (URL, domain, date, sentiment)
      * Cost (in USD)
      * Latency (milliseconds)
    ↓
{
  "query": "...",
  "results": [
    {
      "url": "...",
      "title": "...",
      "markdown": "...",
      "sentiment": 0.75,
      "cost_usd": 0.002,
      "latency_ms": 2500
    },
    ...
  ]
}
```

### 3. Fetch Escalation Strategy

**File:** `src/loom/tools/fetch.py`

```
research_fetch(url, mode="stealthy", auto_escalate=False, ...)
    ↓
┌─ HTTP Mode (Basic HTTP request)
│   ├─ Try GET request with default headers
│   ├─ Check response (200, 404, 403, timeout?)
│   ├─ If success → extract text → return
│   └─ If Cloudflare 403 + auto_escalate=True → escalate
│
├─ Stealthy Mode (Custom headers + rate limit evasion)
│   ├─ Use Scrapling with custom user-agent
│   ├─ Add Accept-Language, Referer, etc.
│   ├─ Retry with backoff
│   ├─ If success → extract text → return
│   └─ If still blocked + auto_escalate=True → escalate
│
└─ Dynamic Mode (Browser automation)
    ├─ Spawn Playwright (Chromium)
    ├─ Load URL, wait for JS rendering
    ├─ Extract DOM or screenshot
    ├─ If success → extract text → return
    └─ If timeout → return error
```

**Auto-escalation decision tree:**

```
if auto_escalate=False:
    stop at current mode
elif mode="http":
    if 403 or Cloudflare:
        escalate to "stealthy"
    else:
        return result
elif mode="stealthy":
    if still blocked or timeout:
        escalate to "dynamic"
    else:
        return result
elif mode="dynamic":
    if still fails:
        return error (no further escalation)
```

### 4. LLM Cascade (Provider Fallback)

**File:** `src/loom/providers/base.py`, `src/loom/tools/llm.py`

```
research_llm_summarize(text, model="auto", max_tokens=500, ...)
    ↓
Get LLM_CASCADE_ORDER from config
    [groq, nvidia_nim, deepseek, gemini, moonshot, openai, anthropic, vllm]
    ↓
┌─ Try Groq
│   ├─ Check available() → API key set? Server up?
│   ├─ If not → skip to next
│   ├─ Call chat(prompt, messages, ...) with timeout
│   ├─ On success → return LLMResponse
│   └─ On error/timeout → continue to next
│
├─ Try NVIDIA NIM
│   ├─ Check available()
│   ├─ Call chat(...)
│   ├─ On success → return LLMResponse
│   └─ On error → continue to next
│
├─ Try DeepSeek
│   └─ ... (same pattern)
│
└─ Last resort: Return error with cascade trace
    {
      "error": "all_providers_failed",
      "cascade_trace": [
        {"provider": "groq", "error": "connection_timeout", "latency_ms": 5000},
        {"provider": "nvidia_nim", "error": "rate_limit", "latency_ms": 1200},
        ...
      ]
    }
```

**Cost Tracking:**

```
response = LLMResponse(
    text=generated_text,
    model=model_id,
    input_tokens=1250,
    output_tokens=450,
    cost_usd=_estimate_cost(provider, model, 1250, 450),
    latency_ms=elapsed_ms,
    provider=provider_name,
)
```

---

## Tool Ecosystem

### Tool Categories (220+ tools across 154 modules)

#### **Scraping & Content Extraction** (8 tools)

| Tool | Module | Purpose |
|------|--------|---------|
| `research_fetch` | fetch.py | Single URL with auto-escalation |
| `research_spider` | spider.py | Multi-URL concurrent fetch |
| `research_markdown` | markdown.py | HTML → clean markdown (Crawl4AI + Trafilatura) |
| `research_camoufox` | stealth.py | Browser automation (stealth mode) |
| `research_botasaurus` | stealth.py | Browser automation (bot evasion) |
| `research_session_open` | sessions.py | Open persistent browser session |
| `research_session_list` | sessions.py | List active sessions |
| `research_session_close` | sessions.py | Close session + cleanup |

#### **Search** (21 providers via 1 tool)

**Tool:** `research_search(query, provider="exa", num_results=10, ...)`

**Providers:**

| Provider | Type | Use Case |
|----------|------|----------|
| exa | Semantic | Best quality, neural ranking |
| tavily | Hybrid | Real-time + quality |
| firecrawl | Web scraping | Full page content |
| brave | Privacy | Privacy-preserving |
| ddgs | Traditional | Fast, no API key |
| arxiv | Academic | Paper search + metadata |
| wikipedia | Knowledge | Definitions, summaries |
| hackernews | Community | Tech discussions |
| reddit | Community | User discussions, opinions |
| newsapi | News | Current events |
| coindesk | Crypto | Cryptocurrency news |
| coinmarketcap | Crypto | Price, market cap data |
| binance | Finance | Trading data |
| investing | Finance | Financial indicators |
| ahmia | Dark web | Darknet site search |
| darksearch | Dark web | Darknet aggregator |
| ummro | Custom RAG | Internal UMMRO knowledge base |
| onionsearch | Dark web | Tor directory search |
| torcrawl | Dark web | Tor site crawling |
| darkweb_cti | Intelligence | Darknet threat intel |
| robin_osint | OSINT | OSINT aggregation |

#### **LLM & Language Tools** (10+ tools across 5 modules)

| Tool | Purpose |
|------|---------|
| `research_llm_summarize` | Condense long text to summary |
| `research_llm_extract` | Structured data extraction (JSON) |
| `research_llm_classify` | Text classification (category prediction) |
| `research_llm_translate` | Language translation |
| `research_llm_expand` | Generate variations / paraphrases |
| `research_llm_answer` | QA over document |
| `research_llm_embed` | Generate embeddings (vector) |
| `research_llm_chat` | Multi-turn conversation |
| `research_detect_language` | Auto-detect language |
| `research_wayback` | Archive.org snapshots |

#### **Killer Research Tools** (45+ tools across 20 modules)

Deep intelligence gathering. Examples:

| Tool | Module | Purpose |
|------|--------|---------|
| `research_dead_content` | dead_content.py | Recover archived/removed content |
| `research_invisible_web` | invisible_web.py | Discover intranets, APIs, dark web |
| `research_js_intel` | js_intel.py | JavaScript code introspection |
| `research_dark_forum` | dark_forum.py | Search 24M+ darknet forum posts |
| `research_infra_correlator` | infra_correlator.py | Link domains/IPs via shared infra |
| `research_passive_recon` | passive_recon.py | DNS/WHOIS/ASN enrichment |
| `research_metadata_forensics` | metadata_forensics.py | EXIF/PDF metadata extraction |
| `research_crypto_trace` | crypto_trace.py | Blockchain address clustering |
| `research_stego_detect` | stego_detect.py | Detect steganography + covert channels |
| `research_threat_profile` | threat_profile.py | Adversary infrastructure profiling |
| `research_leak_scan` | leak_scan.py | Search breach databases + paste sites |
| `research_social_graph` | social_graph.py | Cross-platform relationship mapping |

#### **Dark Web & Intelligence** (60+ tools across 25 modules)

Examples:

- `research_onion_discover` — Crawl Tor exit node directories
- `research_darkweb_early_warning` — Threat actor activity detection
- `research_identity_resolve` — PII correlation across sources
- `research_change_monitor` — Monitor page/site changes
- `research_competitive_intel` — Competitor infrastructure analysis
- `research_supply_chain_intel` — Dependency + vendor profiling
- `research_signal_detection` — Anomaly detection + pattern recognition

#### **Academic Integrity Tools** (35+ tools across 11 modules)

Examples:

- `research_citation_analysis` — Validate citations, build graphs
- `research_retraction_check` — Query retraction databases
- `research_predatory_journal_check` — Detect predatory publishers
- `research_grant_forensics` — Trace funding flows
- `research_review_cartel` — Detect peer review collusion
- `research_data_fabrication` — Statistical anomaly detection
- `research_institutional_decay` — Monitor institutional metrics

#### **AI Safety & Compliance** (15+ tools across 7 modules)

EU AI Act Article 15 compliance testing:

| Tool | Purpose |
|------|---------|
| `research_prompt_injection_test` | Test model for injection vulns |
| `research_model_fingerprint` | Identify model by behavior |
| `research_bias_probe` | Measure fairness metrics |
| `research_safety_filter_map` | Enumerate filter rules |
| `research_compliance_check` | EU AI Act compliance audit |
| `research_hallucination_benchmark` | Measure hallucination rate |
| `research_adversarial_robustness` | Adversarial example generation |

#### **Privacy & Anonymity Tools** (20+ tools)

Examples:

- `research_fingerprint_audit` — Browser fingerprint exposure
- `research_privacy_exposure` — Privacy baseline assessment
- `research_usb_kill_monitor` — Physical security (USB kill-switch)
- `research_artifact_cleanup` — Anti-forensics cleanup
- `research_supercookie_test` — Favicon-based tracking detection
- `research_stego_encode` — Covert exfiltration channel
- `research_linux_anti_forensics` — Linux defensive hardening

#### **Career & Signal Intelligence** (15+ tools across 6 modules)

Examples:

- `research_job_signals` — Job market analysis
- `research_salary_synthesizer` — Salary data aggregation
- `research_resume_intel` — Resume screening + analysis
- `research_deception_job_scanner` — Detect fraudulent job postings

#### **Infrastructure & Services** (30+ tools across 12 modules)

| Tool | Purpose |
|------|---------|
| `research_vastai_list_instances` | List available GPU instances (VastAI) |
| `research_billing_usage` | Check usage + billing (Stripe integration) |
| `research_email_report` | Send report via email |
| `research_joplin_add_note` | Create note in Joplin |
| `research_tor_enable` | Route traffic via Tor |
| `research_transcribe_audio` | Audio → text transcription |
| `research_document_convert` | File format conversion (PDF → markdown, etc.) |

---

## Security Architecture

### 1. SSRF Prevention

**File:** `src/loom/validators.py::validate_url()`

**Checks:**

```
Input URL
    ↓
Parse URL (scheme, host, port)
    ↓
Block private IP ranges:
    - 127.0.0.0/8 (localhost)
    - 10.0.0.0/8 (private)
    - 172.16.0.0/12 (private)
    - 192.168.0.0/16 (private)
    - 169.254.0.0/16 (link-local)
    - 224.0.0.0/4 (multicast)
    - ::1/128 (IPv6 loopback)
    - fc00::/7 (IPv6 private)
    ↓
Resolve hostname to IP (with caching)
    ↓
Check resolved IP against blacklist
    ↓
Reverse DNS check (ptr record match)
    ↓
Character capping (max 2048 chars)
    ↓
Return validated URL or raise ValidationError
```

### 2. Input Validation

**All tools use Pydantic v2 with `extra="forbid"` + `strict=True`:**

```python
class FetchParams(BaseModel):
    url: str  # validate_url()
    headers: dict[str, str] | None = None  # filter_headers() removes auth headers
    proxy: str | None = None  # format validation
    timeout: int | None = None  # bounds check
    max_chars: int = 20000  # capped to MAX_CHARS_HARD_CAP
    
    model_config = {"extra": "forbid", "strict": True}
```

**Field validators prevent:**
- Type coercion (strict mode)
- Unknown fields (extra="forbid")
- Oversized inputs (max_chars, max length checks)
- Unsafe headers (filter_headers removes Authorization, Cookie, Host)
- Invalid proxy formats

### 3. API Key Management

**Environment variables (no hardcoded secrets):**

```bash
export GROQ_API_KEY=...
export NVIDIA_NIM_API_KEY=...
export DEEPSEEK_API_KEY=...
export GOOGLE_AI_KEY=...
export MOONSHOT_API_KEY=...
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export EXA_API_KEY=...
export TAVILY_API_KEY=...
export FIRECRAWL_API_KEY=...
export BRAVE_API_KEY=...
export VASTAI_API_KEY=...
export STRIPE_LIVE_KEY=...
export JOPLIN_TOKEN=...
export TOR_CONTROL_PASSWORD=...
```

**No API keys in code or config.json**. Missing keys → provider marked unavailable → cascade to next.

### 4. Rate Limiting Per Category

**Sliding-window counter with SQLite persistence (optional):**

| Category | Limit | Window |
|----------|-------|--------|
| scrape | 10 calls | 60 sec |
| search | 20 calls | 60 sec |
| llm | 5 calls | 60 sec |
| dark_web | 3 calls | 60 sec |
| ai_safety | 10 calls | 60 sec |

**Prevents:**
- API rate limit violations
- Resource exhaustion
- DOS attacks

### 5. Audit Logging

**File:** `src/loom/audit.py`

Log all tool invocations:

```python
{
    "timestamp": "2026-05-02T10:30:45Z",
    "request_id": "req_abc123",
    "tool": "research_fetch",
    "user_id": "user_123",
    "params": {"url": "https://example.com", ...},
    "result_code": "success|error|rate_limit",
    "cost_usd": 0.002,
    "latency_ms": 1500
}
```

Export via `research_audit_export()` MCP tool for compliance.

### 6. Transport Security

**MCP over HTTPS (optional):**

```python
# In production, use HTTPS + mTLS
mcp = FastMCP(
    ...,
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile="/path/to/key.pem"
)
```

**Local development:** Plain HTTP on `127.0.0.1:8787` (loopback only).

---

## Deployment Architecture

### Hetzner Deployment (128GB RAM)

**Structure:**

```
hetzner.example.com (128GB RAM)
├─ /opt/loom/                    # Application code
│  ├─ src/loom/                  # Source code
│  ├─ tests/                     # Test suite
│  ├─ docs/                      # Documentation
│  ├─ config.json                # Runtime config
│  └─ requirements.txt           # Python dependencies
├─ ~/.cache/loom/                # Cache (gzip, daily dirs)
│  └─ 2026-05-02/
│     └─ <hash>.json.gz          # Cached responses
├─ ~/.loom/                      # Persistent data
│  ├─ sessions.db                # Persistent sessions
│  ├─ rate_limits.db             # Rate limit state
│  └─ audit.log                  # Audit trail
└─ /etc/systemd/system/          # Service management
   └─ loom.service               # systemd unit
```

### systemd Service

**File:** `/etc/systemd/system/loom.service`

```ini
[Unit]
Description=Loom MCP Server
After=network.target

[Service]
Type=simple
User=loom
WorkingDirectory=/opt/loom
Environment="PATH=/opt/loom/.venv/bin:/usr/local/bin:/usr/bin"
Environment="LOOM_HOST=0.0.0.0"
Environment="LOOM_PORT=8787"
Environment="LOOM_CONFIG_PATH=/opt/loom/config.json"
EnvironmentFile=/etc/loom.env  # API keys, secrets
ExecStart=/opt/loom/.venv/bin/loom serve
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Management:**

```bash
systemctl start loom
systemctl status loom
systemctl logs -f loom
systemctl reload loom  # Restart with config reload
systemctl stop loom
```

### Configuration (config.json)

**Example:**

```json
{
  "SPIDER_CONCURRENCY": 12,
  "EXTERNAL_TIMEOUT_SECS": 45,
  "MAX_CHARS_HARD_CAP": 500000,
  "CACHE_TTL_DAYS": 60,
  "DEFAULT_SEARCH_PROVIDER": "exa",
  "LOG_LEVEL": "INFO",
  "LLM_CASCADE_ORDER": [
    "groq",
    "nvidia_nim",
    "deepseek",
    "gemini",
    "moonshot",
    "openai",
    "anthropic",
    "vllm"
  ],
  "LLM_MAX_PARALLEL": 16,
  "LLM_DAILY_COST_CAP_USD": 20.0,
  "RATE_LIMIT_PERSIST": true,
  "RESEARCH_SEARCH_PROVIDERS": ["exa", "brave", "tavily"]
}
```

**Update at runtime:**

```bash
# Via MCP tool
mcp_client localhost:8787
> research_config_set("SPIDER_CONCURRENCY", 20)
{
  "key": "SPIDER_CONCURRENCY",
  "old_value": 12,
  "new_value": 20,
  "persisted_at": "2026-05-02T10:45:00Z"
}

# File is atomically updated + reloaded
```

### Health Checks

**Tool:** `research_health_check()`

Returns:

```python
{
  "status": "healthy",
  "uptime_seconds": 123456,
  "version": "1.0.0",
  "cache_size_bytes": 5_242_880,
  "sessions_active": 2,
  "rate_limit_status": {
    "scrape": {"calls_used": 7, "limit": 10, "window_seconds": 60},
    "search": {"calls_used": 15, "limit": 20, "window_seconds": 60},
    ...
  },
  "providers": {
    "groq": {"available": true, "latency_ms": 245},
    "nvidia_nim": {"available": true, "latency_ms": 180},
    "deepseek": {"available": false, "error": "connection_timeout"},
    ...
  },
  "last_request": "2026-05-02T10:59:30Z",
  "error_rate_24h": 0.02  # 2% errors in last 24 hours
}
```

---

## Scalability & Performance

### Single-Process Async Model

**Design:**

- Single FastMCP process, event loop per process
- Concurrent tool execution via `asyncio`
- No multi-process forking (Python GIL limitation)
- Caching + rate limiting reduce redundant work

**Limitations:**

- CPU-bound tasks (LLM inference, large extractions) block event loop
- Max throughput ~100-200 concurrent requests (browser sessions limited to 8)
- Memory footprint: ~2-3GB base + session state

**Optimal for:**
- Moderate-load research (10-50 concurrent users)
- Integration with Claude API (streaming responses)
- Single-tenant deployments

### Memory Footprint

**Base:**

```
FastMCP server + asyncio runtime:    ~200MB
Tool modules (154 modules):          ~500MB
Provider SDKs (8 LLM + 21 search):   ~1GB
Playwright/Camoufox (1 browser):     ~500MB
Cache (gzip, recent only):           ~200-500MB
Sessions (max 8):                    ~800MB
──────────────────────────────────
Total base:                          ~3-4GB
```

**Scaling:**
- Hetzner 128GB → ~30 independent instances (servers)
- Per instance: 4-6GB reserved + 2GB working headroom

### Caching Strategy

**Deduplication:**

```
Same URL + same params = same cache hit
Across days, even if server restarts
SHA-256 hash ensures consistency
```

**Benefits:**

- 60-80% cache hit rate (typical research patterns)
- No external requests needed on hit
- Reduced API costs (search, fetch providers)
- Sub-millisecond response latency

**Limitations:**

- TTL only (no invalidation logic)
- Stale data if page updates frequently
- `bypass_cache=True` param overrides for fresh data

### Horizontal Scaling (Future)

**Current:** Single-process, single-host.

**Future option:** Load-balancing multiple instances

```
         ┌──────────────────┐
         │  Load Balancer   │
         │  (nginx/haproxy) │
         └────────┬─────────┘
                  │
       ┌──────────┼──────────┐
       │          │          │
       ▼          ▼          ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Loom #1  │ │Loom #2  │ │Loom #3  │
   │:8788    │ │:8789    │ │:8790    │
   └─────────┘ └─────────┘ └─────────┘
       │          │          │
       └──────────┼──────────┘
                  │
             ┌────▼────┐
             │ Shared  │
             │ Cache   │
             │(Redis)  │
             └─────────┘
```

**Challenges:**
- Cache coherency (Redis instead of local gzip)
- Session affinity (user sessions pinned to instance)
- Rate limit coordination (centralized counter)

---

## Design Patterns & Principles

### 1. Layered Architecture

```
┌─────────────────────────────────────┐
│     Client Interface (MCP)          │
├─────────────────────────────────────┤
│    Tool Registration & Dispatch     │
├─────────────────────────────────────┤
│   Validation (Pydantic v2)          │
├─────────────────────────────────────┤
│  Rate Limiting, Caching, Auth       │
├─────────────────────────────────────┤
│   Provider Cascade, Tool Execution  │
├─────────────────────────────────────┤
│  Persistence, Logging, Tracing      │
└─────────────────────────────────────┘
```

Each layer is independent, composable, testable.

### 2. Provider Pattern (Abstract Interface)

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(...) -> LLMResponse: ...
    
    @abstractmethod
    async def available() -> bool: ...
```

Each provider (Groq, OpenAI, Anthropic, etc.) implements independently. Cascade orchestrates fallback logic.

### 3. Parameter Validation (Pydantic v2)

All tools use strict, forbid-extra models:

```python
class FetchParams(BaseModel):
    url: str
    model_config = {"extra": "forbid", "strict": True}
```

Prevents invalid/malicious input before execution.

### 4. Immutable Configuration

Config loaded once at startup, re-validated on updates:

```python
CONFIG: dict[str, Any] = {}  # Module-level, read-only

# Updates via set() → validation → atomic save → CONFIG dict update
set("key", value)  # Never mutates in-place
```

### 5. Async-First Concurrency

All I/O operations are async (`asyncio`):

```python
async def research_fetch(...):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()
```

Enables 100-200 concurrent requests per process.

### 6. Singleton Pattern (Cache, Sessions)

```python
_cache_instance = None

def get_cache() -> CacheStore:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheStore()
    return _cache_instance
```

Ensures single cache per process, no duplicates.

### 7. Decorator Pattern (Tool Wrapping)

```python
@mcp.tool()
@rate_limited(category="scrape")
@tracing_context
async def research_fetch(params: FetchParams) -> dict:
    pass
```

Layered decorators handle cross-cutting concerns.

### 8. Strategy Pattern (Provider Selection)

```python
# Decision logic in research_deep.py
if is_academic_query(query):
    providers = ["arxiv", "wikipedia"]
elif is_code_query(query):
    providers = ["github"]
else:
    providers = ["exa", "brave"]  # Default

results = await multi_search(providers, query)
```

Configurable provider selection based on query intent.

### 9. Template Method (Deep Research Pipeline)

12-stage pipeline with hooks for extension:

```
Query → Detect intent → Select providers → Search → Fetch → Extract → Rank → Output
    │        ↑              ↑          ↑      ↑       ↑       ↑      ↑      ↑
    └────────┴──────────────┴──────────┴──────┴───────┴───────┴──────┴──────┘
                        Each stage is overridable
```

### 10. Circuit Breaker (Provider Fallback)

```
Provider unavailable → Mark as down → Skip in cascade → Try next
Wait 60 seconds → Retry → If success, mark as available again
```

Prevents cascading failures.

---

## Summary

Loom is a **modular, async-first MCP server** designed for research automation and compliance testing. Its architecture emphasizes:

1. **Extensibility** — 220+ tools, easy to add more
2. **Security** — SSRF prevention, input validation, rate limiting
3. **Resilience** — Provider fallback, caching, persistent sessions
4. **Performance** — Async concurrency, content-hash deduplication, gzip compression
5. **Observability** — Structured logging, tracing, audit trails
6. **Compliance** — EU AI Act testing, privacy tools, academic integrity validation

The layered architecture separates concerns: clients → transport → validation → execution → persistence. Each layer is independently testable and replaceable.

---

**End of Document**
