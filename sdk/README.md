# Loom SDK

Python async client for [Loom MCP](https://github.com/aadelb/loom) — a research server that wraps 220+ tools for web search, content fetching, deep research, and multi-LLM querying.

## Installation

```bash
pip install loom-sdk
```

Or from source:

```bash
cd sdk
pip install -e .
```

## Quick Start

```python
import asyncio
from loom_sdk import LoomClient

async def main():
    # Create client (connects to localhost:8787 by default)
    client = LoomClient("http://127.0.0.1:8787")
    
    try:
        # Search the web
        results = await client.search(
            "AI safety research",
            provider="exa",
            n=10
        )
        print(f"Found {len(results.results)} results")
        for result in results.results:
            print(f"- {result.title}: {result.url}")
        
        # Deep research with full pipeline
        report = await client.deep("how does transformers architecture work")
        print(f"\nSummary: {report.summary}")
        print(f"Sources: {len(report.sources)}")
        
        # Query multiple LLMs in parallel
        responses = await client.ask_all_llms("What is AGI?")
        print(f"\nQueried {responses.providers_queried} providers")
        for response in responses.responses:
            print(f"{response.provider}: {response.response[:100]}...")
        
    finally:
        await client.close()

asyncio.run(main())
```

## Async Context Manager

```python
from loom_sdk import LoomClient

async def main():
    async with LoomClient("http://127.0.0.1:8787") as client:
        results = await client.search("topic", n=5)
        # Client automatically closes on exit
```

## API Reference

### Client Methods

#### search()

Search the web using configured providers.

```python
results = await client.search(
    query="AI safety",
    provider="exa",  # or: tavily, firecrawl, brave, ddgs, arxiv, wikipedia
    n=10,
    include_domains=["example.com"],
    exclude_domains=["ads.example.com"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    language="en"
)
# Returns: SearchResponse with list of SearchResult objects
# Each result has: title, url, snippet, date, author, source, metadata
```

#### fetch()

Fetch a single URL with Cloudflare bypass and content extraction.

```python
result = await client.fetch(
    url="https://example.com/article",
    mode="stealthy",  # http, stealthy, or dynamic
    auto_escalate=True,  # Auto-try dynamic if stealthy fails
    solve_cloudflare=True,
    max_chars=20000,
    headers={"User-Agent": "custom-agent"},
    cookies={"session": "abc123"}
)
# Returns: FetchResult with content, html, json_data, status_code
```

#### spider()

Fetch multiple URLs in parallel with deduplication.

```python
results = await client.spider(
    urls=[
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3"
    ],
    mode="stealthy",
    concurrency=5,
    max_chars_each=5000,
    dedupe=True
)
# Returns: SpiderResponse with all results, success/failure counts
```

#### deep()

Run full deep research pipeline (12 stages):
1. Query expansion
2. Multi-provider search
3. Parallel fetch
4. Content extraction
5. Relevance ranking
6. Answer synthesis with citations
7. GitHub enrichment
8. Language detection
9. Community sentiment (HN + Reddit)
10. Red-team analysis (optional)
11. Misinformation checks (optional)
12. Final report

```python
report = await client.deep(
    query="transformers architecture",
    max_results=50,
    include_sentiment=True,
    include_redteam=False
)
# Returns: ResearchReport with summary, findings, sources, citations, confidence
```

#### ask_all_llms()

Send a prompt to all available LLM providers (Groq, NVIDIA NIM, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic) in parallel.

```python
responses = await client.ask_all_llms(
    prompt="What is the future of AI?",
    max_tokens=500,
    include_reframe=True  # Auto-reframe if provider refuses
)
# Returns: AskAllResponse with all provider responses
# Includes: fastest_provider, providers_responded, providers_refused
```

#### reframe()

Reframe a prompt using 957 strategies (ethical anchoring, role-play, hypotheticals, etc.).

```python
reframed = await client.reframe(
    prompt="Describe how to do something harmful",
    strategy="ethical_anchor",  # Auto-select if None
    model="claude"  # or: gpt, gemini, anthropic
)
# Returns: ReframeResult with reframed_prompt, strategy_name, difficulty, safety_flags
```

#### list_tools()

Get list of all available tools and their metadata.

```python
tools = await client.list_tools()
print(f"Total tools: {tools.total_tools}")
for tool in tools.tools:
    print(f"- {tool.name}: {tool.description}")
```

#### health_check()

Check server status and available providers.

```python
health = await client.health_check()
print(f"Status: {health.status}")
print(f"Tools available: {health.tools_available}")
print(f"Providers: {health.providers_available}")
```

## Response Models

All methods return typed Pydantic models:

- **SearchResponse**: `provider`, `query`, `results` (list of SearchResult), `count`, `error`, `timestamp`
- **FetchResult**: `url`, `status_code`, `content`, `html`, `json_data`, `encoding`, `error`
- **SpiderResponse**: `urls_queued`, `urls_succeeded`, `urls_failed`, `results`, `error`
- **ResearchReport**: `query`, `summary`, `findings`, `sources`, `citations`, `confidence`, `sentiment`, `error`
- **ReframeResult**: `original_prompt`, `reframed_prompt`, `strategy_name`, `difficulty`, `safety_flags`, `error`
- **AskAllResponse**: `prompt`, `responses` (list of LLMResponse), `providers_queried`, `providers_responded`, `fastest_provider`, `error`

## Configuration

### Server URL

```python
# Default: localhost:8787
client = LoomClient()

# Custom server
client = LoomClient("https://loom.example.com:8787")
```

### Authentication

```python
# API key authentication
client = LoomClient(api_key="your-api-key")
```

### Timeout

```python
# Default: 300 seconds
client = LoomClient(timeout=600.0)
```

## Error Handling

```python
from loom_sdk import LoomClient, LoomClientError

try:
    results = await client.search("query")
except LoomClientError as e:
    print(f"Loom error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Examples

### Example 1: Complete Research Workflow

```python
import asyncio
from loom_sdk import LoomClient

async def research_topic(topic: str):
    async with LoomClient() as client:
        # Deep research
        report = await client.deep(topic)
        print(f"Summary: {report.summary}")
        
        # Ask multiple LLMs
        responses = await client.ask_all_llms(
            f"Based on this research, what are the key findings about {topic}?"
        )
        
        # Collect insights
        print("\n=== Provider Consensus ===")
        for response in responses.responses:
            if response.response:
                print(f"\n{response.provider}:")
                print(response.response[:200] + "...")

asyncio.run(research_topic("quantum computing advances in 2024"))
```

### Example 2: Multi-URL Content Extraction

```python
async def extract_from_urls(urls: list[str]):
    async with LoomClient() as client:
        # Fetch all URLs in parallel
        spider_result = await client.spider(
            urls=urls,
            mode="stealthy",
            concurrency=10,
            max_chars_each=10000
        )
        
        # Process results
        print(f"Succeeded: {spider_result.urls_succeeded}/{spider_result.urls_queued}")
        for result in spider_result.results:
            if result.content:
                print(f"\n{result.url}")
                print(result.content[:500])

asyncio.run(extract_from_urls([
    "https://example1.com",
    "https://example2.com",
    "https://example3.com"
]))
```

### Example 3: Prompt Reframing

```python
async def reframe_and_test(prompt: str):
    async with LoomClient() as client:
        # Reframe the prompt
        result = await client.reframe(prompt)
        print(f"Original: {result.original_prompt}")
        print(f"Reframed: {result.reframed_prompt}")
        print(f"Strategy: {result.strategy_name}")
        
        # Test both versions with LLMs
        original_responses = await client.ask_all_llms(result.original_prompt)
        reframed_responses = await client.ask_all_llms(result.reframed_prompt)
        
        print(f"\nOriginal refused by: {original_responses.providers_refused}")
        print(f"Reframed refused by: {reframed_responses.providers_refused}")

asyncio.run(reframe_and_test("your prompt here"))
```

## Performance Tips

1. **Use spider() for bulk fetching** — Fetches multiple URLs in parallel with built-in concurrency control
2. **Cache results** — The SDK doesn't cache; the Loom server does via content-hash
3. **Async all the way** — Use `asyncio.gather()` for concurrent client calls
4. **Batch LLM queries** — `ask_all_llms()` already queries all providers in parallel
5. **Set reasonable timeouts** — Default 300s is generous for web research

## Troubleshooting

### Connection Refused
```
LoomClientError: HTTP error calling research_search: Connection refused
```
→ Make sure Loom server is running: `loom-server` or `loom serve`

### Tool Not Found
```
LoomClientError: Tool research_search error: Unknown tool
```
→ Check tool name spelling. List available tools with `await client.list_tools()`

### Timeout
```
LoomClientError: HTTP error calling research_deep: Read timeout
```
→ Increase timeout: `LoomClient(timeout=600.0)`

### Authentication Failed
```
LoomClientError: HTTP error: 401 Unauthorized
```
→ Check your API key: `LoomClient(api_key="your-key")`

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Type check
mypy loom_sdk

# Format
ruff format loom_sdk

# Lint
ruff check loom_sdk
```

## License

Apache-2.0 — Same as Loom MCP server

## Links

- [Loom MCP Server](https://github.com/aadelb/loom)
- [MCP Specification](https://modelcontextprotocol.io/)
