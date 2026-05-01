# Comprehensive Testing Requirements for Production MCP Server

**Document Version:** 1.0  
**Date:** 2026-05-02  
**Scope:** Loom MCP server with 185+ tool modules and 375+ research tools  
**Target Coverage:** 80%+ code coverage, all critical paths tested  

## Executive Summary

This document defines the complete testing strategy for a production-grade Model Context Protocol (MCP) server with 185+ tool modules exposing 375+ individual research tools across 8 LLM providers, 21 search providers, and specialized intelligence capabilities.

The testing strategy is organized into **9 test categories** with specific requirements, quality metrics, and baselines per tool category.

---

## 1. Unit Tests

### Purpose
Verify individual tool functions and core modules work correctly in isolation.

### Requirements

#### 1.1 Tool Unit Tests (Per Tool)
Each tool module MUST have unit tests covering:

- **Parameter Validation**
  - Pydantic validation rejects invalid inputs
  - All `extra="forbid"` constraints enforced
  - Type coercion works correctly for allowed types
  - Required fields raise ValidationError when missing
  - Bounds checking enforced (e.g., `n_results: 1-50`)
  
- **Security Boundaries**
  - SSRF validation blocks loopback (127.0.0.1, ::1)
  - Private IP ranges blocked (RFC1918, 169.254)
  - EC2 metadata endpoint blocked (169.254.169.254)
  - Cloudflare/cloud metadata endpoints blocked
  - URL encoding doesn't bypass validation
  - Path traversal attempts in filenames rejected (`../`, `..\\`)
  - Command injection prevention in any shell-executed commands
  - SQL injection prevention in database queries (parameterized)

- **Return Type Validation**
  - Response matches expected schema
  - All required fields present
  - Data types correct
  - No null values in non-nullable fields
  - Pagination fields correct (page, limit, total)

- **Error Handling**
  - Invalid API keys raise appropriate errors
  - Network timeouts handled gracefully
  - Rate limits respected
  - Missing dependencies raise ImportError, not AttributeError
  - Error messages don't leak sensitive information

- **Caching Behavior**
  - Cache key generation is deterministic
  - Cache hit returns identical data to first call
  - bypass_cache=True skips cache
  - Cache TTL respected
  - Concurrent cache writes don't corrupt data

#### 1.2 Core Module Unit Tests

**validators.py**
- SSRF validation: 11 test cases (loopback v4/v6, EC2, RFC1918, cloud, URL encoding)
- GitHub query sanitization: 8 test cases (flag injection, shell injection, length limits)
- URL encoding validation: 5 test cases
- Response ≥80% coverage

**cache.py**
- Atomic writes with UUID temp files
- SHA-256 content-hash key generation
- Daily directory structure creation
- get() returns None for missing keys
- put()/get() roundtrip integrity
- clear_older_than() TTL cleanup
- Concurrent write safety (10+ concurrent writers)
- Response ≥85% coverage

**params.py**
- Pydantic v2 validation strictness
- extra="forbid" rejection of unknown fields
- All parameter models: FetchParams, SearchParams, GitHubSearchParams, SessionOpenParams, LLMChatParams, etc.
- 50+ parameterized test cases
- Response ≥90% coverage

**sessions.py**
- Session name allow-list (regex: `^[a-z0-9_-]{1,32}$`)
- Rejection of `..`, `/`, spaces, path traversal
- Profile directory creation
- LRU eviction at max sessions (currently 8)
- Concurrent access via asyncio.Lock
- SQLite persistence and recovery
- Response ≥85% coverage

**config.py**
- ConfigModel bounds validation (min/max for numeric fields)
- load_config() merges file over defaults
- save_config() atomic writes
- Environment variable support (LOOM_CONFIG_PATH, LOOM_CACHE_DIR, etc.)
- Unknown keys return error
- Out-of-range values return error
- Response ≥85% coverage

**auth.py**
- API key presence validation
- Bearer token parsing
- MCP authorization header validation
- Token expiration handling
- Response ≥80% coverage

**rate_limiter.py**
- Per-user rate limit tracking
- Per-endpoint rate limit enforcement
- Sliding window algorithm correctness
- Rate limit headers in response
- Response ≥85% coverage

**tracing.py**
- Request ID generation and propagation
- Span creation and closure
- Log context injection
- Response ≥80% coverage

#### 1.3 Test Organization

```
tests/
├── test_tools/
│   ├── test_fetch.py                # 8+ tests
│   ├── test_spider.py               # 8+ tests
│   ├── test_search.py               # 12+ tests
│   ├── test_markdown.py             # 6+ tests
│   ├── test_github.py               # 8+ tests
│   ├── test_llm.py                  # 10+ tests
│   ├── test_deep.py                 # 12+ tests
│   ├── test_sessions.py             # 8+ tests
│   ├── test_[tool_name].py          # Per tool
│   └── ...                          # 117+ tool test files
├── test_validators.py               # 18 tests
├── test_cache.py                    # 10 tests
├── test_params.py                   # 51 tests
├── test_sessions.py                 # 22 tests
├── test_config.py                   # 20 tests
├── test_auth.py                     # 8 tests
├── test_rate_limiter.py             # 12 tests
└── ...
```

#### 1.4 Execution & Coverage

**Command:**
```bash
pytest tests/test_tools tests/test_*.py -m "not live" --cov=src/loom --cov-report=term-missing
```

**Target Coverage:** ≥85% per module, ≥80% overall

**Expected Runtime:** 2-3 minutes locally, <1 minute on Hetzner

---

## 2. Integration Tests

### Purpose
Verify tool chaining, pipeline composition, and multi-module interactions.

### Requirements

#### 2.1 Tool-to-Tool Integration

**Search → Fetch Pipeline**
- search() returns URLs
- fetch() successfully retrieves each URL
- Failure in one tool doesn't crash pipeline
- Result merging is lossless
- Pagination works across tools

**Example Test:**
```python
@pytest.mark.integration
async def test_search_fetch_pipeline():
    """Search results can be fetched sequentially."""
    results = research_search(query="machine learning", provider="exa", n=5)
    for result in results["results"]:
        fetched = research_fetch(url=result["url"])
        assert fetched["url"] == result["url"]
        assert len(fetched["text"]) > 0
```

**Fetch → Markdown Pipeline**
- research_fetch() returns HTML
- research_markdown() extracts markdown from HTML
- Markdown is valid (no broken formatting)
- Links preserved
- Code blocks intact

**LLM Cascade**
- Primary provider unavailable → fallback chain works
- Model selection respects cascade order
- Token cost calculation correct
- Token counts match actual model output

#### 2.2 Pipeline Integration

**Evidence Pipeline**
- 12-stage evidence collection completes
- Each stage output feeds next stage correctly
- Deduplication at each stage works
- Final synthesis combines all evidence

**Tool Composition Framework**
- Generic pipeline composition creates DAG correctly
- Dependencies resolve in topological order
- Parallel tools execute concurrently
- Error propagation stops pipeline gracefully

**Session-Based Workflows**
- Session opens → tools execute in context → session closes
- Browser state preserved across tool calls
- Multiple sessions don't interfere
- Cleanup occurs on close

#### 2.3 Database Integration

**Persistence Layers**
- Config saves atomically to disk
- Sessions persist to SQLite
- Cache writes don't corrupt existing cache
- Multiple processes can access cache safely
- Concurrent writes queue correctly

#### 2.4 Test Organization

```
tests/test_integration/
├── test_pipelines.py               # Search→Fetch, Fetch→Markdown, LLM cascade
├── test_tool_chaining.py           # Multi-stage workflows
├── test_sessions.py                # Browser session persistence
├── test_database_persistence.py    # Cache, config, sessions on disk
├── test_provider_cascade.py        # LLM fallback chain
└── test_concurrent_access.py       # Multi-client safety
```

#### 2.5 Execution

**Command:**
```bash
pytest tests/test_integration -m "not live" --timeout=30
```

**Target Coverage:** 80%+ of pipeline code

**Expected Runtime:** 3-5 minutes

---

## 3. End-to-End (E2E) Tests

### Purpose
Verify complete user workflows from entry point to final output.

### Requirements

#### 3.1 Research Journey Tests

**Journey Test Framework**
- 23-step research journey (defined in tests/journey_e2e.py)
- Fixture-based playback for deterministic offline testing
- Three modes: `mocked` (all responses mocked), `live` (real network), `record` (capture real responses)
- Generated report.json with step metadata, timings, errors

**Journey Scenarios:**

1. **Academic Research Journey**
   - Query: "transformer architecture efficiency improvements"
   - Steps: Query expansion → ArXiv search → Fetch papers → Extract key insights
   - Expected output: Research summary with citations

2. **Threat Intelligence Journey**
   - Query: "CVE-2024-XXXXX impact analysis"
   - Steps: Search → Fetch advisory → Extract indicators → Correlate with threat Intel
   - Expected output: Threat report with remediation

3. **Product Research Journey**
   - Query: "competitor analysis on product X"
   - Steps: Search → Fetch websites → Extract features → Synthesize comparison
   - Expected output: Competitive analysis report

4. **Dark Web Intelligence Journey**
   - Query: "forum discussion on security topic"
   - Steps: Dark forum search → Fetch threads → Extract sentiment → Aggregate intelligence
   - Expected output: Intelligence summary with source attribution

5. **Multi-Tool Chain Journey**
   - Query: "entity name"
   - Steps: Search → Fetch URLs → Extract entities → Correlate infrastructure → Build graph
   - Expected output: Knowledge graph with relationships

#### 3.2 CLI E2E Tests

**CLI Invocation Flows**
```bash
loom fetch https://example.com --json
loom search "query" --provider exa
loom config set KEY VALUE
loom session open --name mysession
loom session list
```

Each CLI command tested for:
- Exit code correctness (0 on success, non-zero on failure)
- Output format correctness (JSON parseable, matches schema)
- Error messages helpful and clear
- Arguments validated before execution

#### 3.3 Test Organization

```
tests/
├── journey_e2e.py               # 5+ journey scenarios
├── journey_full.py              # Extended 23-step journey
├── test_cli_tools.py            # CLI invocation tests
└── integration/
    └── test_mcp_roundtrip.py    # Live MCP server tests (marked @pytest.mark.integration)
```

#### 3.4 Execution

**Fixture-based (No Network):**
```bash
pytest tests/journey_e2e.py --mode=mocked
```

**Live (Real Network, Slow):**
```bash
pytest tests/journey_e2e.py --mode=live --timeout=120 -m live
```

**Expected Runtime:**
- Mocked: 10-20 seconds
- Live: 60-120 seconds

**Target Coverage:** Critical paths ≥95%

---

## 4. Load Tests

### Purpose
Verify system behavior under concurrent load and high throughput.

### Requirements

#### 4.1 Concurrent Tool Execution

**Test Scenarios:**

- **10 Concurrent Fetches:** Same URL, different parameters
  - Expected: All complete successfully
  - Cache hits for identical params
  - No data corruption

- **25 Concurrent Searches:** Different queries, different providers
  - Expected: All complete within timeout
  - Per-provider rate limits respected
  - No dropped requests

- **50 Concurrent LLM Calls:** Different models, different inputs
  - Expected: Cascade fallback if primary saturated
  - Token cost tracking accurate
  - No hung requests

- **100 Mixed Tool Calls:** Random tool invocations
  - Expected: System remains stable
  - No resource leaks
  - No hanging connections

#### 4.2 Rate Limiting

**Test Scenarios:**

- **Per-User Rate Limit:** 100 requests/minute per user
  - 101st request blocked with 429 Too Many Requests
  - Retry-After header present
  - Rate limit resets correctly

- **Per-Endpoint Rate Limit:** 50 requests/second per endpoint
  - 51st request queued
  - Requests processed in order after window

- **Provider Rate Limits:** API key-specific limits respected
  - Search provider rate limits enforced
  - LLM provider rate limits enforced
  - Graceful degradation under rate limit

#### 4.3 Memory & Resource Limits

**Test Scenarios:**

- **Cache Size Cap:** Max 1GB cache directory
  - Oldest entries evicted when cap exceeded
  - No temp files left behind

- **Session Count Cap:** Max 8 concurrent sessions
  - LRU eviction when 9th session opened
  - Old session cleaned up

- **Max Response Size:** 10MB per tool output
  - Larger responses truncated with warning
  - No OOM kills

#### 4.4 Test Organization

```
tests/
├── test_concurrent.py           # Concurrent tool execution
├── test_rate_limiter_sync.py    # Rate limit enforcement
└── test_load_stress.py          # Extended load testing (optional)
```

#### 4.5 Execution

**Command:**
```bash
pytest tests/test_concurrent.py tests/test_rate_limiter_sync.py --timeout=60
```

**Expected Runtime:** 5-10 minutes

**Pass Criteria:**
- Zero deadlocks
- Zero data corruption
- All requests complete
- No memory leaks

---

## 5. Security Tests

### Purpose
Verify security boundaries, injection prevention, and safe error handling.

### Requirements

#### 5.1 SSRF Prevention

**Test Cases:**

| Attack Vector | Expected Behavior | Test Case |
|---|---|---|
| Loopback IPv4 | Reject | `http://127.0.0.1` |
| Loopback IPv6 | Reject | `http://[::1]` |
| Private RFC1918 | Reject | `http://192.168.1.1`, `http://10.0.0.1`, `http://172.16.0.1` |
| Link-local | Reject | `http://169.254.1.1` |
| EC2 metadata | Reject | `http://169.254.169.254/latest/meta-data/` |
| GCP metadata | Reject | `http://metadata.google.internal/` |
| Azure metadata | Reject | `http://169.254.169.254/metadata/instance/` |
| URL encoding bypass | Reject | `http://127.0.0.1` (encoded as %31%32%37...) |
| IPv6 shorthand | Reject | `http://::1`, `http://::ffff:127.0.0.1` |
| Hex IPv4 | Reject | `http://0x7f.0x0.0x0.0x1` |
| Octal IPv4 | Reject | `http://0177.0.0.1` |

#### 5.2 Injection Prevention

**SQL Injection:**
- All database queries use parameterized statements
- User input never concatenated into SQL
- Test: Attempt `" OR 1=1 --` in search query → sanitized

**Command Injection:**
- GitHub tool sanitizes all shell commands
- Test: Attempt `; rm -rf /` in query → sanitized or rejected

**Shell Metacharacters:**
- Reject: `$()`, backticks, `|`, `&`, `;`, `<`, `>`
- Test: Each character tested in tool parameters

**XSS in Error Messages:**
- Error responses safe to return in JSON
- Test: Inject `<script>` in error message → escaped

#### 5.3 Authentication & Authorization

**Test Cases:**

- Missing API key → graceful error (not AttributeError)
- Invalid API key → proper error response
- Expired token → refresh or re-auth
- Missing Authorization header → 401 Unauthorized
- Invalid Bearer token → 401 Unauthorized
- MCP authorization layer enforced

#### 5.4 Error Message Safety

**Test Cases:**

- Database connection errors don't leak credentials
- API errors don't expose internal URLs
- File errors don't expose full paths
- Stack traces not returned to client

#### 5.5 Test Organization

```
tests/
├── test_security.py             # SSRF, injection, auth
└── test_tools/
    └── [tool]_security.py       # Tool-specific security tests
```

#### 5.6 Execution

**Command:**
```bash
pytest tests/test_security.py --timeout=30
```

**Expected Runtime:** 2-3 minutes

**Pass Criteria:** 100% of attack vectors rejected

---

## 6. Contract Tests (MCP Protocol Compliance)

### Purpose
Verify tools conform to MCP specification and respond with correct schemas.

### Requirements

#### 6.1 Tool Registration Contract

**Each Tool MUST:**
- Be registered in `server.py:_register_tools()`
- Have name matching pattern: `research_[tool_name]`
- Have description (non-empty string)
- Have inputSchema as Pydantic model with `extra="forbid"`
- Have `@mcp.tool()` decorator

**Test:**
```python
def test_tool_registration_completeness():
    """All 375+ tools properly registered with MCP."""
    app = create_app()
    tools = app._tools
    assert len(tools) >= 375
    for tool in tools.values():
        assert tool.name.startswith("research_")
        assert tool.description
        assert tool.inputSchema
```

#### 6.2 Response Schema Contract

**Every Tool Response MUST:**
- Be JSON-serializable
- Include top-level keys: `success`, `data`, `error` (mutually exclusive)
- Include `tool` field with tool name
- Include `timestamp` field
- Include `cache_status` field (`hit`, `miss`, or `bypass`)

**Test:**
```python
@pytest.mark.asyncio
async def test_response_schema_all_tools():
    """All tools return responses matching contract."""
    for tool_name, tool_func in get_all_tools():
        result = await invoke_tool(tool_func, valid_params)
        assert "success" in result
        assert "data" in result or "error" in result
        assert result.get("tool") == tool_name
        assert "timestamp" in result
        assert "cache_status" in result
```

#### 6.3 Input Schema Contract

**Every Tool's inputSchema MUST:**
- Be valid JSON Schema
- Include required fields (non-empty list)
- Use Pydantic v2 with `extra="forbid"`
- Validate and reject unknown fields

**Test:**
```python
def test_input_schema_all_tools():
    """All tools have valid, strict inputSchema."""
    for tool_name, tool_func in get_all_tools():
        schema = tool_func.inputSchema
        assert schema is not None
        assert "properties" in schema
        assert "required" in schema
        # Attempt to pass unknown field → should fail
        with pytest.raises(ValidationError):
            tool_func(unknown_field="value", **valid_params)
```

#### 6.4 Error Handling Contract

**Errors MUST:**
- Return 400+ HTTP status code
- Include error message (string)
- Include error code (string)
- NOT include stack trace to client
- Include request_id for logging

**Test:**
```python
@pytest.mark.asyncio
async def test_error_contract_all_tools():
    """All tools return errors with correct contract."""
    for tool_name, tool_func in get_all_tools():
        result = await invoke_tool(tool_func, invalid_params)
        assert result["success"] is False
        assert "error" in result
        assert isinstance(result["error"], dict)
        assert "message" in result["error"]
        assert "code" in result["error"]
```

#### 6.5 Test Organization

```
tests/
├── test_contracts/
│   ├── test_tool_registration.py    # Registration completeness
│   ├── test_response_schemas.py     # Response contract
│   ├── test_input_schemas.py        # Input contract
│   └── test_error_handling.py       # Error contract
```

#### 6.6 Execution

**Command:**
```bash
pytest tests/test_contracts/ --timeout=60
```

**Expected Runtime:** 5-10 minutes (375+ tools × 2 tests each)

**Pass Criteria:** 100% of tools pass all contract tests

---

## 7. Regression Tests

### Purpose
Prevent fixed bugs from returning in future changes.

### Requirements

#### 7.1 Bug Regression Suite

**For Each Fixed Bug:**
1. Create test case that reproduces original bug
2. Verify test fails without the fix
3. Verify test passes with the fix
4. Add test to suite permanently

**Example:**
```python
def test_regression_cache_concurrent_write():
    """Prevent regression of concurrent cache write data corruption.
    
    Bug: Two threads writing same key simultaneously → corrupted cache.
    Fix: Use os.replace() atomic write after uuid temp file.
    
    Tracked: https://github.com/user/repo/issues/123
    """
    cache = CacheStore(tmp_cache_dir)
    # Simulate concurrent writes
    threads = [
        threading.Thread(target=cache.put, args=("key", f"value_{i}"))
        for i in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Cache should have ONE consistent value, not corrupted
    result = cache.get("key")
    assert result in [f"value_{i}" for i in range(10)]
```

#### 7.2 Common Bug Categories

**URL Validation Bugs:**
- SSRF bypass via encoding
- Private IP bypass via IPv6 shorthand
- Cloud metadata bypass via alternate endpoints

**Caching Bugs:**
- Cache key collision
- Stale cache not evicted
- Cache corruption under concurrency

**Parameter Validation Bugs:**
- Field injection bypass
- Type coercion exploits
- Bounds validation bypass

**Pagination Bugs:**
- Off-by-one in page calculation
- Missing results at boundary
- Infinite loop in pagination

**Rate Limiting Bugs:**
- Window calculation errors
- Per-user isolation failure
- Rate limit header miscalculation

#### 7.3 Test Organization

```
tests/
└── test_regressions/
    ├── test_url_validation_regressions.py
    ├── test_caching_regressions.py
    ├── test_param_validation_regressions.py
    ├── test_pagination_regressions.py
    └── test_rate_limiting_regressions.py
```

#### 7.4 Execution

**Command:**
```bash
pytest tests/test_regressions/ --timeout=30
```

**Expected Runtime:** 2-3 minutes

**Pass Criteria:** All regressions pass

---

## 8. Smoke Tests

### Purpose
Quick health verification after deploy or startup.

### Requirements

#### 8.1 Smoke Test Suite

**Minimal Critical Path Tests:**

1. **Server Starts:** MCP server binds to port 8787
2. **Tools List:** /tools/list endpoint returns 375+ tools
3. **Health Check:** GET /health returns 200 OK with uptime
4. **Fetch Works:** Single HTTPS fetch succeeds
5. **Search Works:** Single search query succeeds
6. **LLM Works:** Single LLM chat completes
7. **Config Load:** Config file loads without errors
8. **Sessions Work:** Open, list, close session cycle completes
9. **Cache Init:** Cache directory initialized and writable
10. **Logging Init:** Logging configured correctly

#### 8.2 Response Time Benchmarks

| Operation | P50 | P95 | P99 |
|---|---|---|---|
| List tools | 50ms | 100ms | 200ms |
| Fetch URL (cached) | 100ms | 200ms | 500ms |
| Search (API cached) | 200ms | 500ms | 2000ms |
| LLM Chat | 2s | 10s | 30s |
| Session open | 100ms | 200ms | 500ms |

#### 8.3 Test Organization

```
tests/
├── test_cli_smoke.py            # CLI smoke tests
└── integration/
    └── test_health_check.py     # Server health checks
```

#### 8.4 Execution

**Command:**
```bash
pytest tests/test_cli_smoke.py tests/integration/test_health_check.py --timeout=60
```

**Expected Runtime:** 30-60 seconds

**Pass Criteria:**
- All 10 critical paths pass
- Response times within benchmarks

---

## 9. Quality Metrics & Performance Baselines

### 9.1 Test Coverage Targets

| Category | Target | Current |
|---|---|---|
| Overall Code Coverage | ≥80% | Track with `--cov=src/loom` |
| Core Module Coverage | ≥85% | validators, cache, params, sessions, config |
| Tool Coverage | ≥80% | Per-tool unit + integration |
| Integration Coverage | ≥80% | Pipeline, chaining, persistence |
| Security Test Coverage | 100% | All SSRF, injection vectors |

### 9.2 Response Time Baselines

**By Tool Category:**

| Category | Tool Count | P50 Fetch | P95 Fetch | P99 Fetch | Notes |
|---|---|---|---|---|---|
| Scraping | 8 | 500ms | 2s | 5s | HTTP escalates to dynamic on CF block |
| Search | 21 | 1s | 3s | 10s | API rate limit dependent |
| LLM | 8 | 2s | 15s | 60s | Model size dependent |
| Intelligence | 25 | 1.5s | 5s | 15s | Mixed I/O + compute |
| Infrastructure | 12 | 200ms | 1s | 3s | API calls + light compute |
| Darkweb | 15 | 3s | 10s | 30s | Tor latency + long-running |
| Pipeline | 5 | 5s | 20s | 60s | Multi-stage composition |

### 9.3 Error Rate Targets

| Category | Target | Recovery |
|---|---|---|
| Network Timeouts | <1% | Auto-retry with exponential backoff |
| API Rate Limits | <2% | Queue and retry after window |
| Invalid Input | <0.5% | Proper error message, 400 response |
| Internal Errors | <0.1% | Log, alert, 500 response |
| Tool Unavailability | <5% | Skip tool, use fallback if available |

### 9.4 Resource Utilization Targets

| Resource | Limit | Measurement |
|---|---|---|
| Cache Directory Size | 1GB | `du -sh ~/.cache/loom` |
| Concurrent Sessions | 8 | Graceful eviction of oldest |
| Max Process Memory | 500MB | Monitor with `psutil` |
| Open File Descriptors | 100 | Per-process limit |
| Rate Limit Tokens | Configurable | Track per endpoint/user |

### 9.5 Tool Category Baselines

#### Scraping Tools (fetch, spider, markdown)
- **Tests per tool:** 8-12
- **P50 response:** 500ms-2s
- **Error tolerance:** <1% timeouts
- **Caching:** 70%+ hit rate on common URLs

#### Search Tools (21 providers)
- **Tests per tool:** 6-10
- **P50 response:** 1s-3s
- **Error tolerance:** <2% API failures
- **Caching:** 50%+ hit rate on repeated queries

#### LLM Tools (8 providers)
- **Tests per tool:** 8-12
- **P50 response:** 2s-15s
- **Error tolerance:** <1% token errors
- **Cost tracking:** ±5% accuracy

#### Intelligence Tools (25+ tools)
- **Tests per tool:** 10-15
- **P50 response:** 1s-5s
- **Error tolerance:** <2% failures
- **Data validation:** 100% schema compliance

#### Infrastructure Tools (12 tools)
- **Tests per tool:** 6-10
- **P50 response:** 200ms-1s
- **Error tolerance:** <1% failures
- **Rate limits:** Strict enforcement

#### Darkweb Tools (15 tools)
- **Tests per tool:** 6-12
- **P50 response:** 3s-10s
- **Error tolerance:** <5% timeouts
- **Tor connectivity:** Verified on startup

#### Pipeline Tools (5 compositions)
- **Tests per pipeline:** 4-8
- **P50 response:** 5s-30s
- **Error tolerance:** <2% stage failures
- **Composition:** DAG validation required

---

## 10. Testing Checklist for New Tools

When adding a new tool, ensure:

- [ ] **Unit Tests** (8+ tests minimum)
  - [ ] Parameter validation rejects invalid inputs
  - [ ] Security boundaries tested (SSRF, injection)
  - [ ] Response schema matches contract
  - [ ] Error handling verified
  - [ ] Caching works correctly
  - [ ] All code paths covered (≥80%)

- [ ] **Integration Tests** (2+ tests minimum)
  - [ ] Tool works in pipeline
  - [ ] Output feeds next stage correctly
  - [ ] Error propagation handled

- [ ] **Contract Tests**
  - [ ] Tool registered in `server.py`
  - [ ] inputSchema valid and strict
  - [ ] Response includes required fields
  - [ ] Error format correct

- [ ] **Security Tests**
  - [ ] URL validation (if applicable)
  - [ ] Injection prevention (if applicable)
  - [ ] Error messages safe

- [ ] **Documentation**
  - [ ] docs/tools-reference.md updated
  - [ ] docs/help.md updated
  - [ ] Example usage provided
  - [ ] Cost estimation included

---

## 11. CI/CD Testing Pipeline

### 11.1 Pre-Commit Hooks

Run locally before commit:
```bash
ruff check src tests
mypy src/loom
pytest tests/ -m "not live" --timeout=300 --maxfail=5
```

### 11.2 GitHub Actions Workflow

**On every commit to main:**

1. **Lint & Type Check** (2 min)
   - ruff check
   - mypy strict mode
   - Fail on errors

2. **Unit Tests** (3 min)
   - pytest tests/test_tools tests/test_*.py
   - Coverage ≥80%
   - Fail if lower

3. **Integration Tests** (5 min)
   - pytest tests/test_integration
   - Timeout: 30s per test

4. **Load Tests** (10 min)
   - pytest tests/test_concurrent.py tests/test_rate_limiter_sync.py
   - Fail on deadlock or data corruption

5. **Security Tests** (2 min)
   - pytest tests/test_security.py
   - 100% pass rate required

6. **Contract Tests** (15 min)
   - pytest tests/test_contracts/
   - All 375+ tools verified

7. **Smoke Tests** (1 min)
   - pytest tests/test_cli_smoke.py
   - Critical path health check

**Total time:** ~40 minutes

**Abort conditions:**
- Coverage drops below 80%
- Any security test fails
- Contract tests fail on 375+ tools
- Load tests detect deadlock

### 11.3 Release Testing

**Before release to production:**

1. Full test suite with live API keys (60 min)
2. Load test with 100 concurrent users (30 min)
3. E2E journey tests in live mode (60 min)
4. Performance baseline comparison
5. Security scan (bandit, semgrep)

---

## 12. Test Maintenance & Monitoring

### 12.1 Test Metrics Dashboard

Track:
- Test pass rate (target: 99%+)
- Test execution time (track trends)
- Code coverage (target: ≥80%)
- Flaky test rate (target: <1%)
- Regression detection rate

### 12.2 Flaky Test Detection

- Run tests 3x on CI
- Flag tests that pass/fail inconsistently
- Investigate and fix immediately
- Disable flaky tests temporarily if needed

### 12.3 Test Failure Analysis

When tests fail:
1. Check if real bug or environmental
2. Run test 3x locally to verify
3. Check CI logs for timing/race conditions
4. Fix bug, not test
5. Add regression test

---

## 13. Tool-Specific Testing Guidance

### Fetch/Spider Tools
- Test with real URLs in live mode
- Test with CloudFlare-protected URLs
- Test with timeouts and retries
- Verify markdown extraction accuracy

### Search Tools
- Test all 21 providers have API keys
- Verify deduplication across providers
- Check pagination limits
- Validate result schema per provider

### LLM Tools
- Test all 8 providers (with cascade fallback)
- Verify token counting accuracy
- Test temperature/max_tokens bounds
- Check cost calculation

### Session Tools
- Test concurrent session access
- Verify browser state persistence
- Check LRU eviction
- Validate cleanup on close

### Intelligence Tools
- Test data source availability
- Verify graph construction
- Check relationship inference
- Validate sentiment analysis

---

## 14. Running the Full Test Suite

### Quick Test (5 min)
```bash
pytest tests/test_tools tests/test_*.py -m "not live" --timeout=30 --maxfail=3
```

### Standard Test (15 min)
```bash
pytest tests/ -m "not live" --timeout=60 --maxfail=5 --cov=src/loom
```

### Full Test with Live APIs (90 min)
```bash
pytest tests/ --timeout=120 --cov=src/loom
```

### CI/CD Test (45 min)
```bash
# Lint
ruff check src tests
mypy src/loom
# Tests (no live APIs)
pytest tests/ -m "not live" --timeout=300 --maxfail=5 --cov=src/loom --cov-report=xml
```

---

## 15. Conclusion

This testing strategy provides **comprehensive validation** for a production MCP server with 375+ tools across 9 test categories:

1. **Unit Tests** — Individual tool & module correctness
2. **Integration Tests** — Tool chaining & pipelines
3. **E2E Tests** — Complete user workflows
4. **Load Tests** — Concurrent operations & scaling
5. **Security Tests** — SSRF, injection, auth
6. **Contract Tests** — MCP protocol compliance
7. **Regression Tests** — Prevent bug recurrence
8. **Smoke Tests** — Quick health verification
9. **Metrics & Baselines** — Performance tracking

**Target Coverage:** 80%+ code, 99%+ test pass rate, <1% flaky tests

**Expected Runtime:** 5 min (quick) to 90 min (full with live APIs)

---

## Appendix A: Test Execution Examples

### Example 1: Test Single Tool
```bash
pytest tests/test_tools/test_fetch.py::TestFetch::test_fetch_rejects_ssrf_url -v
```

### Example 2: Test Tool Category
```bash
pytest tests/test_tools/ -k "search" -v --cov=src/loom/tools/search
```

### Example 3: Test Integration Pipeline
```bash
pytest tests/test_integration/test_pipelines.py::test_search_fetch_pipeline -v
```

### Example 4: Test with Coverage Report
```bash
pytest tests/ --cov=src/loom --cov-report=html
open htmlcov/index.html
```

### Example 5: Run Only Smoke Tests
```bash
pytest tests/test_cli_smoke.py -v
```

---

## Appendix B: Environment Setup for Testing

### Install Test Dependencies
```bash
cd /Users/aadel/projects/loom
pip install -e ".[dev]"
```

### Set API Keys for Live Testing
```bash
export GROQ_API_KEY="..."
export NVIDIA_NIM_API_KEY="..."
export EXA_API_KEY="..."
export TAVILY_API_KEY="..."
# ... etc for all providers
```

### Run on Hetzner (Recommended for Heavy Tests)
```bash
ssh hetzner "cd /Users/aadel/projects/loom && pytest tests/ --timeout=300 --maxfail=5"
```

---

**Document End**
