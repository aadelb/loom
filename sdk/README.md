# Loom SDK

Official Python SDK client for the Loom MCP research server.

Provides async/await support for:
- **search** - Multi-provider semantic search across 21 providers
- **fetch** - Extract content from URLs with auto-escalation
- **deep_research** - 12-stage research pipeline with auto-detection
- **llm_summarize** - LLM-powered text summarization with provider cascade
- **health** - Server status and metrics
- **call_tool** - Generic interface for any Loom tool

## Installation

```bash
pip install loom-sdk
```

## Quick Start

```python
import asyncio
from loom_sdk import LoomClient

async def main():
    async with LoomClient("http://localhost:8787") as client:
        # Search
        results = await client.search("climate change impacts", n=10)
        for result in results.results:
            print(f"{result.title}: {result.url}")

        # Fetch URL content
        content = await client.fetch("https://example.com")
        print(f"Title: {content.title}")
        print(f"Content length: {content.body_length}")

        # Deep research
        research = await client.deep_research("machine learning trends 2025")
        print(f"Found {len(research.sources)} sources")
        print(f"Key findings: {research.key_findings}")

        # Summarize text
        text = "..."
        summary = await client.llm_summarize(text, max_words=100)
        print(f"Summary: {summary.summary}")

        # Check server health
        health = await client.health()
        print(f"Server status: {health.status}")

asyncio.run(main())
```

## Usage Examples

### Search Multiple Providers

```python
async with LoomClient() as client:
    # Auto-select best provider
    results = await client.search("quantum computing", provider="auto", n=20)

    # Use specific provider
    results = await client.search("quantum computing", provider="exa", n=10)
```

### Extract Content from URL

```python
async with LoomClient() as client:
    # Auto-escalate if needed (http → stealthy → dynamic)
    result = await client.fetch("https://example.com", mode="auto")

    print(f"Status: {result.status_code}")
    print(f"Title: {result.title}")
    print(f"Markdown: {result.markdown}")
```

### Research Pipeline

```python
async with LoomClient() as client:
    # Auto-detects query type
    # Academic → arXiv
    # Knowledge → Wikipedia
    # Code → GitHub
    # General → multi-provider
    research = await client.deep_research("blockchain scalability", max_results=20)

    for source in research.sources:
        print(f"- {source.title} ({source.provider})")

    print(f"\nKey findings:")
    for finding in research.key_findings:
        print(f"- {finding}")

    if research.summary:
        print(f"\nSummary: {research.summary}")
```

### Text Summarization

```python
async with LoomClient() as client:
    long_text = "..."
    result = await client.llm_summarize(
        long_text,
        max_words=150,
        model=None  # Auto-select best provider
    )

    print(f"Model: {result.model}")
    print(f"Summary: {result.summary}")
    print(f"Latency: {result.execution_time_ms}ms")
```

### Generic Tool Invocation

```python
async with LoomClient() as client:
    # Call any tool by name
    result = await client.call_tool(
        "research_github",
        query="async python",
        sort="stars",
        per_page=10
    )

    if result.success:
        print(f"Results: {result.data}")
    else:
        print(f"Error: {result.error}")
```

## Configuration

### Basic Setup

```python
from loom_sdk import LoomClient

# Default (localhost:8787, no auth)
client = LoomClient()

# Custom endpoint with API key
client = LoomClient(
    base_url="https://api.loom.example.com",
    api_key="sk_live_...",
    timeout=120.0,
    max_retries=3
)
```

### Environment Variables

```bash
# Optional: Configure via environment
export LOOM_BASE_URL="http://localhost:8787"
export LOOM_API_KEY="sk_live_..."
export LOOM_TIMEOUT="60"
```

## API Reference

### LoomClient

Main client class for interacting with Loom server.

#### Constructor

```python
LoomClient(
    base_url: str = "http://localhost:8787",
    api_key: str | None = None,
    timeout: float = 60.0,
    max_retries: int = 3
)
```

**Parameters:**
- `base_url` - Server endpoint URL
- `api_key` - Optional API authentication key
- `timeout` - Request timeout in seconds (default: 60)
- `max_retries` - Retry attempts on 5xx errors (default: 3)

**Raises:**
- `ValueError` - If base_url is invalid or timeout <= 0

#### Methods

##### search()

Multi-provider semantic search.

```python
async def search(
    query: str,
    provider: str = "auto",
    n: int = 10
) -> SearchResponse:
```

**Parameters:**
- `query` - Search query string (required)
- `provider` - Provider name or "auto" (default: auto)
- `n` - Number of results (1-100, default: 10)

**Returns:** `SearchResponse` with ranked results

**Providers:**
- `auto` - Best provider selection
- `exa` - Exa neural search
- `tavily` - Tavily semantic search
- `brave` - Brave search
- `ddgs` - DuckDuckGo
- `arxiv` - Academic papers
- `wikipedia` - Knowledge articles
- `github` - Code repositories
- `hacker_news` - HN discussion
- And 12+ more

##### fetch()

Extract content from URL.

```python
async def fetch(
    url: str,
    mode: str = "auto"
) -> FetchResult:
```

**Parameters:**
- `url` - URL to fetch (required)
- `mode` - Fetch mode: http, stealthy, dynamic, auto (default: auto)

**Returns:** `FetchResult` with extracted content

**Modes:**
- `http` - Standard HTTP request
- `stealthy` - Custom headers, cookie handling
- `dynamic` - JavaScript rendering via Playwright
- `auto` - Try http → stealthy → dynamic

##### deep_research()

12-stage research pipeline.

```python
async def deep_research(
    query: str,
    max_results: int = 10
) -> DeepResearchResult:
```

**Parameters:**
- `query` - Research query (required)
- `max_results` - Maximum results (1-50, default: 10)

**Returns:** `DeepResearchResult` with sources, findings, citations

**Auto-Detection:**
- Academic queries → arXiv
- Knowledge queries → Wikipedia
- Code queries → GitHub
- General → multi-provider semantic search

##### llm_summarize()

LLM-powered text summarization.

```python
async def llm_summarize(
    text: str,
    max_words: int = 200,
    model: str | None = None
) -> LLMSummarizeResult:
```

**Parameters:**
- `text` - Text to summarize (required)
- `max_words` - Max summary length (50-2000, default: 200)
- `model` - Optional specific model

**Returns:** `LLMSummarizeResult` with summary

**Provider Cascade:**
1. Groq (fastest, free)
2. NVIDIA NIM (high throughput)
3. DeepSeek (reasoning)
4. Google Gemini (knowledge)
5. Moonshot/Kimi (multilingual)
6. OpenAI (reliable)
7. Anthropic Claude (best reasoning)
8. Local vLLM (fallback)

##### health()

Server health check.

```python
async def health() -> HealthStatus:
```

**Returns:** `HealthStatus` with server metrics

##### call_tool()

Generic tool invocation.

```python
async def call_tool(
    tool_name: str,
    **params: Any
) -> ToolResponse:
```

**Parameters:**
- `tool_name` - Tool name (required)
- `**params` - Tool-specific parameters

**Returns:** `ToolResponse` with execution result

### Response Models

All methods return frozen dataclasses for immutability.

#### SearchResult

```python
@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str
    provider: str
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### SearchResponse

```python
@dataclass(frozen=True)
class SearchResponse:
    query: str
    results: list[SearchResult]
    total_count: int
    provider: str
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### FetchResult

```python
@dataclass(frozen=True)
class FetchResult:
    url: str
    content_type: str
    status_code: int
    body_length: int
    title: str | None = None
    markdown: str | None = None
    extraction_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### DeepResearchResult

```python
@dataclass(frozen=True)
class DeepResearchResult:
    query: str
    sources: list[SearchResult]
    key_findings: list[str]
    summary: str | None = None
    citations: list[str] = field(default_factory=list)
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### LLMSummarizeResult

```python
@dataclass(frozen=True)
class LLMSummarizeResult:
    input_text: str
    summary: str
    word_count: int
    model: str | None = None
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### HealthStatus

```python
@dataclass(frozen=True)
class HealthStatus:
    status: str
    version: str | None = None
    uptime_seconds: float | None = None
    tools_available: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### ToolResponse

```python
@dataclass(frozen=True)
class ToolResponse:
    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

## Error Handling

```python
import httpx
from loom_sdk import LoomClient

async with LoomClient() as client:
    try:
        results = await client.search("query")
    except ValueError as e:
        # Invalid parameter
        print(f"Invalid input: {e}")
    except httpx.ConnectError:
        # Cannot reach server
        print("Server unreachable")
    except httpx.HTTPStatusError as e:
        # HTTP error (4xx, 5xx)
        print(f"HTTP {e.response.status_code}")
    except httpx.TimeoutException:
        # Request timeout
        print("Request timed out")
```

## Context Manager (Recommended)

Always use async context manager to ensure proper cleanup:

```python
async with LoomClient() as client:
    results = await client.search("query")
    # Client closes automatically
```

Or manual management:

```python
client = LoomClient()
try:
    results = await client.search("query")
finally:
    await client.close()
```

## Performance

- **Connection pooling**: Reuses HTTP connections
- **Exponential backoff**: Auto-retries on 5xx errors (2^n seconds)
- **Timeout handling**: 60s default, configurable
- **Concurrent requests**: Uses httpx AsyncClient for efficient concurrency

## License

Apache License 2.0

## Contributing

Contributions welcome! See main Loom repository for guidelines.

## Support

- GitHub: https://github.com/aadelb/loom
- Issues: https://github.com/aadelb/loom/issues
