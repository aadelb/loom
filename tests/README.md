# Loom Test Suite

Complete test suite for the Loom MCP server with 173+ test cases covering validators, cache, params, sessions, config, providers, tools, CLI, and integration tests.

## Test Files Organization

### Core Module Tests

- **test_validators.py** (18 tests)
  - 11 SSRF validation cases (public URLs, loopback, EC2 metadata, RFC1918, schemes)
  - 7 GitHub query allow-list cases (normal queries, flag injection, shell injection)
  - Tests ported verbatim from `/tmp/research-toolbox-staging/test_validators.py`

- **test_cache.py** (9 tests)
  - CacheStore atomic write with uuid-tmp + os.replace
  - SHA-256 prefix length validation (first 32 hex chars)
  - get() returns None for missing keys
  - put()/get() roundtrip data integrity
  - clear_older_than() TTL cleanup
  - Concurrent writes safety (10 writers, same key)

- **test_params.py** (51 tests)
  - FetchParams: URL validation, mode validation, header/proxy/auth validation
  - SearchParams: query validation, n bounds (1-50), provider validation
  - GitHubSearchParams: flag injection rejection, query length bounds
  - SessionOpenParams: session name allow-list (no uppercase, spaces, special chars, path traversal)
  - ConfigSetParams, LLMChatParams, LLMSummarizeParams, LLMExtractParams, LLMClassifyParams
  - LLMTranslateParams (preserves Arabic), LLMQueryExpandParams, DeepParams, SpiderParams, MarkdownParams

- **test_sessions.py** (22 tests)
  - Session open/list/close lifecycle
  - Session name allow-list rejection (reject `..`, `/`, spaces, too long names)
  - Profile directory creation & cleanup
  - LRU eviction at 9 sessions
  - Concurrent access semaphore prevents race conditions
  - Persistence across restart (SQLite DB serialization)

- **test_config.py** (20 tests)
  - ConfigModel field bounds validation
  - load_config() merges file over code defaults
  - save_config() atomic write with cleanup
  - research_config_set() validates before disk write
  - Unknown key returns error, out-of-range returns error
  - Environment variable support (LOOM_CONFIG_PATH)

### Provider Tests

- **test_providers/test_nvidia_nim.py** (5 tests)
  - available() returns False without key
  - available() returns True with key
  - Provider name validation
  - close() safe cleanup

- **test_providers/test_openai.py** (5 tests)
  - Same as NVIDIA NIM for OpenAI provider

### Tool Tests

- **test_tools/test_fetch.py** (6 tests)
  - URL SSRF rejection
  - Private IP rejection
  - Expected response fields (url, title, text, html_len, fetched_at, tool)
  - Cache hit on repeated calls
  - max_chars cap applied
  - bypass_cache=True ignores cache

- **test_tools/test_spider.py** (5 tests)
  - Empty URL list returns empty result
  - Parallel fetches up to concurrency limit
  - Concurrency limit enforced (max 3 concurrent checked)
  - Mixed ok/fail results handled gracefully
  - Deduplication with dedupe=True

- **test_tools/test_search.py** (5 tests)
  - Empty query rejected
  - Normalized output shape validation
  - Graceful fallback when API key not set
  - include_domains filtering
  - exclude_domains filtering

- **test_tools/test_github.py** (5 tests)
  - Flag injection rejection (`--owner`)
  - Shell injection rejection (`$()`)
  - Result parsed as JSON from subprocess
  - Cache on repeated queries
  - All kinds accepted (repos, code, issues)

- **test_tools/test_llm.py** (6 tests)
  - LLM chat returns expected structure (text, model, tokens, cost, latency)
  - Summarize respects max_length bounds
  - Extract validates against schema
  - Classify respects label allow-list
  - Translate preserves Arabic text
  - Query expand returns multiple queries

### CLI & Integration Tests

- **test_cli.py** (8 tests)
  - `loom --help` prints usage
  - `loom fetch --help`, `loom search --help`, etc.
  - `loom fetch http://localhost:8080` returns non-zero exit
  - `loom fetch https://example.com --json` with mocked response
  - `loom config set KEY VALUE` works
  - Exit codes validated

- **test_journey.py** (3 tests)
  - run_journey() completes all 23 steps with fixture data
  - report.json generation with step metadata
  - Fixture playback for deterministic offline testing

- **test_integration/test_mcp_roundtrip.py** (5 tests)
  - Marked with @pytest.mark.integration (requires live MCP server)
  - Stub tests for tools/list, fetch, search, session, error handling
  - Skip by default; enable with `pytest -m integration`

## Fixtures

### conftest.py Fixtures

- `tmp_cache_dir`: Isolated temp cache directory per test
- `tmp_sessions_dir`: Isolated temp sessions directory per test
- `tmp_config_path`: Isolated temp config.json path per test
- `mock_httpx_transport`: httpx MockTransport for HTTP testing
- `env_no_api_keys`: Clear API keys from environment
- `fixture_fanar_model_card`: Load/create minimal HTML model card
- `fixture_exa_search_response`: Minimal valid Exa search response
- `fixture_tavily_search_response`: Minimal valid Tavily response
- `fixture_nvidia_nim_chat_response`: Minimal valid NVIDIA NIM chat response
- `fixture_journey_dir`: Create journey fixtures directory with sample data

### Fixture Files

- `tests/fixtures/exa_search_response.json` — Sample Exa API response
- `tests/fixtures/tavily_search_response.json` — Sample Tavily API response
- `tests/fixtures/nvidia_nim_chat_response.json` — Sample NVIDIA NIM response
- `tests/fixtures/journey/exa_search_example.json` — Journey search fixture
- `tests/fixtures/journey/pages/example_model_card.html` — Example model card HTML

## Running Tests

### Install dependencies

```bash
cd /Users/aadel/projects/loom
pip install -e ".[dev]"
```

### Run all tests

```bash
pytest tests/
```

### Run with coverage

```bash
pytest tests/ --cov=src/loom --cov-report=html
```

### Run specific test class or function

```bash
pytest tests/test_validators.py::TestValidateUrl::test_ssrf_public_https
pytest tests/test_cache.py::TestCacheStore
```

### Run only integration tests

```bash
pytest tests/ -m integration
```

### Skip live network tests

```bash
pytest tests/ -m "not live"
```

## Test Coverage Target

Aim for **≥80% coverage** of `src/loom/` modules. The suite covers:

- Validators: SSRF, query sanitization
- Cache: atomic writes, concurrency
- Parameters: Pydantic validation
- Sessions: lifecycle, LRU, persistence
- Config: load/save, validation
- Providers: availability, basic structure
- Tools: SSRF rejection, caching, error handling
- CLI: command structure, exit codes
- Integration: MCP roundtrip (stubs for live testing)

## Key Testing Patterns

### 1. Parametrized SSRF Tests (11 cases)

```python
def test_ssrf_loopback_v4(self) -> None:
    """Block loopback IPv4."""
    with pytest.raises(UrlSafetyError):
        validate_url("http://127.0.0.1:8080")
```

### 2. Pydantic Validation with pytest.raises()

```python
def test_fetch_rejects_invalid_mode(self) -> None:
    """Invalid mode value raises ValidationError."""
    with pytest.raises(ValidationError):
        FetchParams(url="https://example.com", mode="invalid")
```

### 3. Mock HTTP Responses with pytest-mock

```python
def test_fetch_cache_hit(self, tmp_cache_dir: Path) -> None:
    """Fetch returns cached result on second call."""
    with patch("loom.tools.fetch.Fetcher") as mock_fetcher:
        mock_page = MagicMock()
        mock_fetcher.get.return_value = mock_page
        # ...
```

### 4. Async Tests with pytest-asyncio

```python
@pytest.mark.asyncio
async def test_session_open_creates_session(self) -> None:
    """open() creates a session and returns metadata."""
    result = await manager.open("test_session")
    assert result["name"] == "test_session"
```

### 5. Isolated Environment with Fixtures

```python
def test_config_with_file(self, tmp_config_path: Path) -> None:
    """load_config reads from isolated temp file."""
    tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_config_path.write_text(json.dumps({"key": "value"}))
    cfg = load_config(tmp_config_path)
```

## Notes

- All tests are deterministic (no real network calls)
- Tests use mocks and fixtures for external dependencies
- `pytest-asyncio` handles async test collection
- `pytest.importorskip()` prevents collection errors for optional modules
- Tests are organized by module (1 test file per code module)
- Fixtures isolated per test to prevent state leakage

## Test Status

- ✅ 173 test cases written
- ✅ SSRF validator tests ported from research-toolbox
- ✅ All major modules covered
- ✅ Fixtures for API responses and HTML pages
- ⏳ Full integration tests (marked skip, requires live MCP server)
