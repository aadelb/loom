# Loom SDK Package Structure

## Directory Layout

```
sdk/
├── loom_sdk/                # Main package
│   ├── __init__.py         # Package exports
│   ├── client.py           # LoomClient async client
│   └── models.py           # Pydantic response models
├── examples/               # Usage examples
│   ├── 01_basic_search.py
│   ├── 02_deep_research.py
│   ├── 03_multi_llm.py
│   ├── 04_bulk_fetch.py
│   └── 05_prompt_reframe.py
├── tests/                  # Test suite
│   ├── __init__.py
│   └── test_client.py
├── pyproject.toml         # Package configuration
├── README.md              # Main documentation
├── INSTALL.md             # Installation guide
├── CHANGELOG.md           # Version history
└── STRUCTURE.md           # This file
```

## Module Overview

### `loom_sdk/__init__.py`
Exports all public APIs:
- `LoomClient` — Async HTTP client for Loom MCP
- `LoomClientError` — Exception for SDK errors
- All model classes (SearchResponse, FetchResult, etc.)

### `loom_sdk/client.py`
Main client implementation with methods:
- `search()` — Web search
- `fetch()` — Single URL fetch
- `spider()` — Parallel multi-URL fetch
- `deep()` — Full research pipeline
- `ask_all_llms()` — Multi-LLM queries
- `reframe()` — Prompt reframing
- `list_tools()` — Tool discovery
- `health_check()` — Server monitoring
- Context manager support (`async with`)
- HTTP client management

### `loom_sdk/models.py`
Pydantic dataclasses for type-safe responses:
- `SearchResult` — Single search result
- `SearchResponse` — Search API response
- `FetchResult` — Single fetch result
- `SpiderResponse` — Multi-URL fetch response
- `ResearchReport` — Deep research output
- `ReframeResult` — Prompt reframing output
- `LLMResponse` — Single LLM provider response
- `AskAllResponse` — Multi-LLM response
- `ToolInfo` — Tool metadata
- `ToolListResponse` — Tool list response
- `HealthCheckResponse` — Server health status

## Installation & Usage

### Quick Install
```bash
cd sdk
pip install -e .
```

### Basic Usage
```python
from loom_sdk import LoomClient

async with LoomClient() as client:
    results = await client.search("topic", n=10)
    report = await client.deep("research query")
    responses = await client.ask_all_llms("What is X?")
```

## Key Features

1. **Type-Safe** — All responses are Pydantic models with validation
2. **Async-First** — Full async/await support via httpx
3. **Context Manager** — Automatic resource cleanup
4. **Error Handling** — Custom `LoomClientError` exception
5. **Timeout Control** — Configurable per request
6. **API Key Support** — Optional authentication
7. **Simple API** — Minimal, intuitive method signatures
8. **Well Documented** — Docstrings, examples, README

## Response Models

All methods return typed Pydantic models with:
- Field validation
- Default values
- JSON serialization
- IDE autocomplete support

### SearchResponse
```python
SearchResponse(
    provider="exa",
    query="search terms",
    results=[SearchResult(...), ...],
    count=10,
    error=None,
    timestamp=datetime.utcnow()
)
```

### ResearchReport
```python
ResearchReport(
    query="research question",
    summary="Overall findings...",
    findings=["Finding 1", "Finding 2", ...],
    sources=["https://source1.com", ...],
    citations={"source1": "https://...", ...},
    confidence=0.85,
    error=None
)
```

### AskAllResponse
```python
AskAllResponse(
    prompt="user query",
    responses=[
        LLMResponse(provider="groq", response="answer..."),
        LLMResponse(provider="openai", response="answer..."),
        ...
    ],
    providers_queried=7,
    providers_responded=6,
    providers_refused=1,
    fastest_provider="groq",
    fastest_latency_ms=150.0
)
```

## Error Handling

All methods may raise `LoomClientError` for:
- Connection errors
- HTTP errors
- JSON parsing errors
- Tool execution errors

```python
try:
    results = await client.search("query")
except LoomClientError as e:
    print(f"Loom error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Configuration

### Server URL
```python
client = LoomClient("http://custom-server:8787")
```

### Authentication
```python
client = LoomClient(api_key="your-api-key")
```

### Timeout
```python
client = LoomClient(timeout=600.0)
```

## Testing

```bash
# Run tests
pytest -v

# With coverage
pytest --cov=loom_sdk

# Type checking
mypy loom_sdk

# Linting
ruff check loom_sdk
```

## Examples

- `01_basic_search.py` — Simple web search
- `02_deep_research.py` — Full research pipeline
- `03_multi_llm.py` — Query all LLM providers
- `04_bulk_fetch.py` — Parallel URL fetching
- `05_prompt_reframe.py` — Prompt reframing strategies

## Dependencies

### Runtime
- `httpx>=0.28` — Async HTTP client
- `pydantic>=2.12` — Data validation

### Development
- `pytest>=8` — Testing framework
- `pytest-asyncio>=0.24` — Async test support
- `pytest-httpx>=0.30` — HTTP mocking
- `ruff>=0.7` — Linting & formatting
- `mypy>=1.13` — Type checking

## Package Distribution

### PyPI (Future)
```bash
pip install loom-sdk
```

### From Source
```bash
git clone https://github.com/aadelb/loom.git
cd loom/sdk
pip install -e .
```

## Development Workflow

1. **Install dev dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Make changes:**
   - Edit `loom_sdk/client.py` or `loom_sdk/models.py`
   - Add tests in `tests/`

3. **Test:**
   ```bash
   pytest -v
   mypy loom_sdk
   ruff check loom_sdk
   ```

4. **Format:**
   ```bash
   ruff format loom_sdk
   ```

5. **Submit PR**

## Future Enhancements

- [ ] Sync client wrapper (non-async)
- [ ] Streaming responses for large datasets
- [ ] Built-in caching layer
- [ ] Request retry with exponential backoff
- [ ] Rate limiting
- [ ] CLI tool wrapper
- [ ] Plugin system for custom tools

## License

Apache-2.0 — Same as Loom MCP server

## Links

- **Loom MCP:** https://github.com/aadelb/loom
- **MCP Specification:** https://modelcontextprotocol.io/
- **Pydantic:** https://docs.pydantic.dev/
- **httpx:** https://www.python-httpx.org/
