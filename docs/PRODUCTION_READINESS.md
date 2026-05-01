# Loom MCP Server — Production Readiness Assessment

**Assessment Date:** 2026-05-02  
**Target Deployment:** Hetzner (128GB RAM, Linux)  
**Current Status:** **PARTIAL READINESS** (70%)  

---

## Executive Summary

Loom is an **ambitious, well-architected Python MCP server** exposing 375+ research tools with intelligent provider cascading, multi-stage fetch escalation, and comprehensive caching. The foundation is solid, but several production-grade gaps must be addressed before high-traffic deployment:

| Area | Status | Confidence |
|------|--------|-----------|
| **Architecture** | SOLID | HIGH |
| **Performance** | UNCERTAIN | MEDIUM |
| **Security** | STRONG | HIGH |
| **Reliability** | PARTIAL | MEDIUM |
| **Scalability** | LIMITED | MEDIUM |
| **Operations** | MINIMAL | LOW |

---

## 1. Architecture Assessment

### Current State

**Strengths:**
- ✅ **Clean separation of concerns**: Core modules (server.py, config.py, validators.py, cache.py, sessions.py) are focused and well-named
- ✅ **Async/await architecture**: Proper asyncio usage with `async_playwright`, `asyncio.Semaphore` for concurrency control
- ✅ **Dependency injection pattern**: Config, cache, and sessions are singletons accessible globally; avoids tight coupling
- ✅ **Pydantic v2 validation**: All tool parameters validated with strict bounds (`extra="forbid"`, `strict=True`)
- ✅ **Provider abstraction**: LLM and search providers implement ABC, enabling easy fallback cascading
- ✅ **MCP transport**: FastMCP with streamable-HTTP is well-suited for long-running tools

**Weaknesses:**

#### 1.1 Single-File Server Scalability Risk (P1)

**Gap:** `server.py` is 2100+ lines with:
- 140+ tool module imports (lines 51-142)
- 50+ optional tool imports with try/suppress blocks (lines 148-485)
- Tool registration function `_register_tools()` inlined (not shown but referenced)
- Massive tool registry potentially causing slow initialization

**Issue:**
- Loading 375 tools into memory at startup = O(n) initialization cost (~10-50ms per tool = 3-18 seconds startup)
- A single file makes it hard to parallelize tool loading or lazy-load tools by category
- Circular import risk if any tool imports from server.py

**Risk Level:** P1 (directly impacts startup time and memory layout)

**Recommendation:**
```
Phase 1 (Week 1): Create tool loader abstraction
  src/loom/tool_registry.py
    - class ToolRegistry (manages registration, discovery, lazy-loading)
    - load_from_module(module_path) → discovers tool functions via introspection
    - group_by_category(tools) → groups tools into research/scraping/llm/etc
    - async initialize() → parallel loader with semaphore

Phase 2 (Week 2): Modularize server.py
  server.py (reduce to 300 lines)
    - create_app() calls tool_registry.initialize() instead of importing 140 modules
    - Tool discovery: loop through src/loom/tools/*.py, auto-register via naming convention
    - Lazy-load optional tools on first use (not at startup)
```

**Estimated Effort:** 3-4 days  
**Priority:** P1

---

#### 1.2 Circular Import & Optional Dependency Risk (P1)

**Gap:** Lines 148-485 use 50+ `with suppress(ImportError)` blocks for optional tools.

**Issue:**
- If any optional tool imports from server.py (e.g., `from loom.server import create_app`), a circular import crash is silent (swallowed by suppress)
- No validation that optional tools are syntactically correct — they're only validated if `import` succeeds
- Server boots successfully even if 40% of optional tools are broken

**Risk Level:** P1 (hidden failures, silent degradation)

**Recommendation:**
```python
# src/loom/tool_loader.py
class ToolLoadResult:
    name: str
    status: Literal["loaded", "import_error", "syntax_error"]
    error: str | None

async def load_and_validate_tools() -> dict[str, ToolLoadResult]:
    """Load all tools, report failures, validate syntax."""
    results = {}
    for tool_module in discover_tool_modules():
        try:
            mod = importlib.import_module(tool_module)
            # Introspect for tool functions
            results[tool_module] = ToolLoadResult("loaded", None)
        except ImportError as e:
            results[tool_module] = ToolLoadResult("import_error", str(e))
        except SyntaxError as e:
            results[tool_module] = ToolLoadResult("syntax_error", str(e))
    return results

# In server.py main():
load_results = asyncio.run(load_and_validate_tools())
errors = {k: v for k, v in load_results.items() if v.status != "loaded"}
if errors:
    log.warning(f"Failed to load {len(errors)} tool modules:\n{errors}")
    # Expose results via /health endpoint
```

**Estimated Effort:** 2-3 days  
**Priority:** P1

---

### Architecture Recommendation Summary

| Item | Action | Effort | Impact |
|------|--------|--------|--------|
| Tool loader abstraction | Create tool_registry.py | 3-4d | HIGH |
| Lazy-load optional tools | Defer non-core tools | 2d | MEDIUM |
| Validate tool syntax at startup | Load validation harness | 2-3d | HIGH |
| **Subtotal** | **Modularize server** | **7-10 days** | **Production-Ready** |

---

## 2. Performance Assessment

### Current State

**Measured Baselines (from architecture.md):**
- HTTP fetch: 30s timeout (configurable 5-120s)
- Spider concurrency: 10 parallel fetches (configurable 1-20)
- Cache key: SHA-256 content-hash (fast)
- Markdown extraction: Crawl4AI async (parallelizable)

**Unknowns (NOT documented):**
- ❌ p50/p95/p99 latency for individual tools
- ❌ Concurrent session capacity (design supports ~10 browser sessions max)
- ❌ RAM footprint under load (375 tools in memory = ?)
- ❌ CPU-bound tool distribution (are there blocking calls in event loop?)
- ❌ Database connection pooling (SQLite has no built-in pooling)

### Gap 2.1: No Latency Telemetry (P2)

**Issue:** Cannot answer:
- "What's the p95 latency of research_deep()?"
- "Is research_spider() CPU-bound on the markdown extraction step?"
- "How much time is spent in LLM cascade fallbacks?"

**Recommendation:**
```python
# src/loom/telemetry.py
@dataclass
class ToolLatency:
    tool_name: str
    elapsed_ms: int
    stage: str  # "search" | "fetch" | "extract" | "synthesize"
    provider: str  # "exa" | "nvidia" | etc.
    error: bool
    timestamp: datetime

_telemetry_buffer: list[ToolLatency] = []

async def record_tool(
    tool_name: str, elapsed_ms: int, stage: str, provider: str, error: bool
) -> None:
    """Record tool execution metrics."""
    _telemetry_buffer.append(
        ToolLatency(tool_name, elapsed_ms, stage, provider, error, datetime.now(UTC))
    )
    # Flush to disk every 1000 entries or 1 hour

async def get_percentiles(
    tool_name: str, window_hours: int = 24
) -> dict[str, float]:
    """Return {p50, p95, p99, max} ms for tool over window."""
    ...
```

**Impact:** Enable SLA monitoring, identify bottlenecks  
**Effort:** 4-5 days (add to all tool calls, create aggregator, expose via /metrics)  
**Priority:** P2

---

### Gap 2.2: Memory Footprint Unknown (P2)

**Issue:** Loading 375 tools + 957 strategies = ?

**Estimates (speculative):**
- Base FastMCP instance: ~50MB
- Tool module imports: ~30-50MB (140 modules, assume 200-300KB per)
- Strategy registry (32 modules × 30 strategies): ~5-10MB
- Caches, sessions, LLM client objects: ~20-30MB
- **Estimated baseline: 150-200MB**

But **actual measurement needed** because:
- Some tools wrap large libraries (Playwright, Scrapling, CrawlAI)
- Playwright browser instances can be 400MB+ each
- LLM providers hold HTTP connection pools

**Recommendation:**
```bash
# Run memory profiler on startup
pip install memory-profiler
python -m memory_profiler loom/server.py

# Monitor at runtime
import tracemalloc
tracemalloc.start()
# ... startup complete ...
current, peak = tracemalloc.get_traced_memory()
print(f"Memory: {current / 1e6:.1f} MB (peak: {peak / 1e6:.1f} MB)")
```

**Action:**
1. Measure startup memory usage (baseline)
2. Measure after opening N browser sessions
3. Measure after 1000 tool calls
4. Identify largest consumers via `getsizeof()` introspection
5. Set target: <500MB baseline + <100MB per browser session

**Effort:** 2-3 days (measurement) + 5-7 days (optimization if needed)  
**Priority:** P2

---

### Gap 2.3: Event Loop Blocking (P3)

**Issue:** Are there sync calls in async code paths?

**Checklist (manual code review needed):**
- [ ] All file I/O in cache.py wrapped in `run_in_executor()`?
- [ ] All subprocess calls (e.g., GitHub CLI) wrapped in `run_in_executor()`?
- [ ] Any `socket.gethostbyname()` calls (validators.py line 13 imports socket)?
- [ ] Any `time.sleep()` instead of `await asyncio.sleep()`?

**Example Risk:**
```python
# src/loom/validators.py (line 68-70 approx)
_dns_cache_lock = threading.Lock()  # Thread lock, not asyncio.Lock
def _get_dns_cache(...):
    with _dns_cache_lock:
        # ... blocking DNS lookup? ...
```

**Recommendation:**
```python
# Audit all tool entry points for blocking calls
# src/loom/audit_blocking.py
import ast
import sys

def find_blocking_calls(file_path: str) -> list[str]:
    """Find likely blocking calls in async functions."""
    with open(file_path) as f:
        tree = ast.parse(f.read())
    
    blocking_names = {
        "time.sleep", "socket.gethostbyname", "requests.get",
        "open(", "json.load", "sqlite3.connect"
    }
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for child in ast.walk(node):
                # Check for Calls to blocking functions
                ...
    return issues

# Run in CI: pytest scripts/audit_blocking.py
```

**Effort:** 3-4 days (audit + fixes)  
**Priority:** P3

---

### Performance Recommendation Summary

| Gap | Action | Effort | Deadline |
|-----|--------|--------|----------|
| Latency telemetry | Implement ToolLatency + aggregator | 4-5d | Week 2 (P2) |
| Memory profiling | Measure baseline & per-session | 2-3d | Week 1 (P2) |
| Event loop audit | Scan for blocking calls | 3-4d | Week 1 (P3) |
| Load testing | Simulate 100 concurrent sessions | 5-7d | Week 3 (P2) |
| **Subtotal** | **Perf Analysis & Optimization** | **14-19 days** | **Production-Ready** |

---

## 3. Security Assessment

### Current State

**Strengths:**
- ✅ **SSRF Protection (validators.py):** Blocks private IPs, metadata IPs, DNS rebind attacks
- ✅ **Input Validation:** Pydantic v2 with `strict=True`, `extra="forbid"` on all tool params
- ✅ **URL Allowlist:** GitHub query regex prevents flag injection (GH_QUERY_RE, line 65)
- ✅ **Header Filtering:** SAFE_REQUEST_HEADERS allowlist prevents header injection
- ✅ **JavaScript Sandbox:** Blocks dangerous APIs (eval, fetch, WebSocket) in login_script
- ✅ **API Key Management:** `.env` files, environment variable loading (no hardcoding in code)
- ✅ **Rate Limiting:** Per-tool category with optional SQLite persistence
- ✅ **Cost Capping:** Daily LLM spend cap ($10/day default) enforces budget

**Weaknesses:**

#### 3.1 Missing API Key Rotation & Expiration (P2)

**Gap:** API keys (Groq, Anthropic, OpenAI, etc.) are loaded once at startup, never validated or rotated.

**Issue:**
- If an API key is compromised, no way to detect or revoke without restarting
- Expired keys are not refreshed (e.g., OAuth tokens)
- No audit trail of key changes

**Recommendation:**
```python
# src/loom/secrets.py
class SecretManager:
    """Manages API keys with validation, rotation, and audit logging."""
    
    def __init__(self):
        self._secrets = {}
        self._last_validated = {}
    
    async def load_and_validate(self):
        """Load from .env, validate each key with provider."""
        for provider_name in ["groq", "openai", "anthropic", ...]:
            key = os.environ.get(f"{provider_name.upper()}_API_KEY")
            if key:
                is_valid = await self._test_key(provider_name, key)
                if not is_valid:
                    log.error(f"Invalid/expired key for {provider_name}")
                    raise RuntimeError(...)
                self._secrets[provider_name] = key
                self._last_validated[provider_name] = datetime.now(UTC)
    
    async def refresh_key(self, provider_name: str):
        """Refresh OAuth tokens or rotate keys."""
        ...
    
    def get(self, provider_name: str, validate=False) -> str:
        """Get key, optionally re-validating if stale."""
        ...
```

**Effort:** 5-7 days (implement per-provider validation, test with sandboxed keys)  
**Priority:** P2 (not critical for initial deployment, but essential for production)

---

#### 3.2 No Authentication on MCP Endpoint (P1)

**Gap:** MCP endpoint (`/mcp`) accepts requests from anyone IF `LOOM_API_KEY` is not set.

**Issue:** (from architecture.md, line 503)
> If `LOOM_API_KEY` is set, all requests must include `Authorization: Bearer <key>`.

But this is optional. If not set:
- MCP endpoint is **unauthenticated**
- Anyone on the network can call `research_deep()`, drain LLM budgets, exfiltrate data
- No rate limiting at the HTTP layer (only at tool level)

**Recommendation:**
```python
# src/loom/auth.py
class MtlsAuth(AuthSettings):
    """Enforce mutual TLS + API key."""
    
    def __init__(self):
        self.api_key = os.environ.get("LOOM_API_KEY")
        self.client_cert = os.environ.get("LOOM_CLIENT_CERT_PATH")
        self.client_key = os.environ.get("LOOM_CLIENT_KEY_PATH")
        
        if not self.api_key:
            log.warning("LOOM_API_KEY not set; MCP endpoint is unauthenticated!")
    
    async def verify_request(self, request: Request) -> bool:
        """Verify API key + mTLS cert."""
        if self.api_key:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return False
            token = auth_header[7:]
            if not self.constant_time_compare(token, self.api_key):
                return False
        
        if self.client_cert:
            # Verify mTLS cert from request.client.cert
            ...
        
        return True

# In server.py create_app():
app = FastMCP()
auth = MtlsAuth()
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    if not await auth.verify_request(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    ...
```

**Effort:** 3-4 days (implement auth, test with curl/Python client)  
**Priority:** P1 (CRITICAL for production deployment on shared network)

---

#### 3.3 Audit Logging Incomplete (P2)

**Gap:** audit.py exists but coverage is unclear.

**Issue:**
- Which tool calls are audited? (fetch, spider, or all?)
- Are API key usage patterns logged? (e.g., "consumed $5.00 from Groq today")
- Can you reconstruct "who called which tool when" for forensics?

**Recommendation:**
```python
# Ensure comprehensive audit logging
audit_events = [
    "tool_call_started",      # tool_name, user/api_key, params hash
    "tool_call_completed",    # tool_name, elapsed_ms, status, cost
    "tool_call_error",        # tool_name, error_type, error_msg
    "config_changed",         # key, old_value, new_value, actor
    "api_key_used",          # provider, tokens_consumed, cost
    "rate_limit_exceeded",    # category, limit, current_count
    "session_created",        # session_name, browser, ttl
    "session_destroyed",      # session_name, reason
]

# Every tool call must emit tool_call_started and tool_call_completed
# Expose via research_audit_export() tool (already in server.py, line 489)
```

**Effort:** 2-3 days (audit all tool calls, ensure complete coverage)  
**Priority:** P2

---

### Security Recommendation Summary

| Gap | Action | Effort | Impact |
|-----|--------|--------|--------|
| mTLS + API key auth | Enforce LOOM_API_KEY | 3-4d | CRITICAL |
| Secret rotation | Implement SecretManager | 5-7d | HIGH |
| Audit coverage | Verify all events logged | 2-3d | MEDIUM |
| **Subtotal** | **Security Hardening** | **10-14 days** | **Production-Ready** |

---

## 4. Reliability Assessment

### Current State

**Strengths:**
- ✅ **Error Handling Patterns:** Custom exception hierarchy (errors.py) with clean propagation
- ✅ **Graceful Degradation:** Optional tool imports via try/suppress; missing LLM providers fall back
- ✅ **Health Check (server.py, line 522):** Comprehensive health endpoint checking all providers
- ✅ **Session Cleanup (sessions.py, line 93):** TTL-based eviction prevents resource leaks
- ✅ **Cache Cleanup:** TTL-based (30 days default) via research_cache_clear()

**Weaknesses:**

#### 4.1 Fetch Auto-Escalation Lacks Timeout Backoff (P2)

**Gap:** Fetch auto-escalation (architecture.md, line 230-260) escalates:
```
http (30s) → stealthy (??s) → dynamic (??s)
```

**Issue:**
- No timeout for stealthy mode (Scrapling)
- No timeout for dynamic mode (Playwright)
- If a URL is unreachable, all 3 attempts timeout in series = 90+ seconds per URL
- With 100 concurrent URLs: potential for 5000+ seconds (80+ minutes) wall time

**Recommendation:**
```python
# src/loom/tools/fetch.py (or tools/deep.py if multi-step)
async def fetch_with_escalation(
    url: str,
    mode: str = "auto",
    timeout_http_secs: int = 30,
    timeout_stealthy_secs: int = 45,  # NEW
    timeout_dynamic_secs: int = 60,   # NEW
    max_retries: int = 1,
    backoff_factor: float = 2.0,
) -> dict[str, Any]:
    """Escalate with exponential backoff."""
    
    if mode == "auto":
        timeouts = [
            ("http", timeout_http_secs),
            ("stealthy", timeout_stealthy_secs),
            ("dynamic", timeout_dynamic_secs),
        ]
    else:
        timeouts = [(mode, timeout_http_secs)]
    
    last_error = None
    for attempt in range(max_retries + 1):
        for mode_name, timeout in timeouts:
            try:
                result = await fetch_single(
                    url, mode=mode_name, timeout=timeout
                )
                return result
            except (TimeoutError, ConnectionError) as e:
                last_error = e
                if mode_name == "http":
                    break  # Escalate
                else:
                    sleep_time = timeout_http_secs * (backoff_factor ** attempt)
                    await asyncio.sleep(min(sleep_time, 10))  # Max 10s backoff
    
    return {"url": url, "error": str(last_error)}
```

**Impact:** Prevents runaway timeouts in high-concurrency scenarios  
**Effort:** 2-3 days (add params, test with slow URLs)  
**Priority:** P2

---

#### 4.2 No Deadletter Queue for Failed Tools (P2)

**Gap:** If a tool call fails (network error, API down, etc.), the failure is returned to the client but not persisted.

**Issue:**
- If research_deep() is called with 100 URLs and 10 fail, there's no "retry later" mechanism
- Failed tools are not distinguished from user errors
- Debugging production issues requires scanning logs

**Recommendation:**
```python
# src/loom/deadletter.py
@dataclass
class DeadletterEntry:
    tool_name: str
    params: dict[str, Any]
    error: str
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: datetime | None = None

class DeadletterQueue:
    """Persistent queue for failed tool calls."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def enqueue(self, entry: DeadletterEntry) -> None:
        """Add failed call to queue."""
        ...
    
    async def retry_eligible(self) -> list[DeadletterEntry]:
        """Return entries ready for retry."""
        ...
    
    async def auto_retry(self):
        """Background task: retry failed calls."""
        while True:
            entries = await self.retry_eligible()
            for entry in entries:
                try:
                    result = await self._retry_tool(entry)
                    self.mark_success(entry.id)
                except Exception:
                    self.increment_retry(entry.id)
            await asyncio.sleep(60)  # Retry every minute

# In server.py:
dlq = DeadletterQueue(Path.home() / ".loom" / "deadletter.db")
asyncio.create_task(dlq.auto_retry())
```

**Benefit:** Improves reliability for transient failures  
**Effort:** 5-7 days (implement queue, background retry, expose via tool)  
**Priority:** P2 (nice-to-have, not critical)

---

#### 4.3 Uncaught Exceptions in Tool Functions (P3)

**Gap:** Tool functions may raise unexpected exceptions that bypass error handling.

**Issue:**
- If a tool raises `RuntimeError` but error handler expects `ValueError`, it propagates uncaught
- No universal error wrapping → different error formats from different tools
- MCP clients may crash on malformed error responses

**Recommendation:**
```python
# src/loom/tool_wrapper.py
async def _wrap_tool(func: Callable, *args, **kwargs) -> dict[str, Any]:
    """Universal wrapper for all tool functions."""
    try:
        result = await func(*args, **kwargs) if iscoroutinefunction(func) else func(*args, **kwargs)
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except ValidationError as e:
        return {
            "status": "validation_error",
            "error": str(e),
            "details": e.errors(),
        }
    except TimeoutError as e:
        return {
            "status": "timeout",
            "error": str(e),
            "timeout_seconds": ...,
        }
    except Exception as e:
        log.exception(f"Uncaught exception in {func.__name__}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
        }

# In server.py _register_tools():
mcp.tool()(_wrap_tool(research_fetch))
```

**Effort:** 3-4 days (wrap all 375 tools, test error paths)  
**Priority:** P3

---

### Reliability Recommendation Summary

| Gap | Action | Effort | Impact |
|-----|--------|--------|--------|
| Timeout backoff | Add exponential backoff to fetch escalation | 2-3d | MEDIUM |
| Deadletter queue | Implement persistent retry queue | 5-7d | LOW |
| Universal error wrapper | Wrap all tool functions | 3-4d | MEDIUM |
| **Subtotal** | **Reliability Hardening** | **10-14 days** | **Production-Ready** |

---

## 5. Scalability Assessment

### Current State

**Design Limits:**
- Browser sessions: max 10 (hardcoded in sessions.py line 628)
- Spider concurrency: max 20 (config bound, line 50)
- LLM parallelism: max 64 (config bound, line 87)
- Cache: unbounded (30-day TTL cleanup via cron)
- Database: SQLite (single-file, no replication)

### Gap 5.1: Single-Process Server Cannot Scale (P1)

**Issue:** Loom runs as a single uvicorn process (port 8787).

**Limitations:**
- 100 concurrent HTTP connections → GIL contention (Python async helps, but not perfect)
- 10 browser sessions × 400MB each = 4GB memory for sessions alone
- Cannot leverage multi-core (all CPU-bound work serialized)

**Current Topology:**
```
Client → Loom (single process, 1 port 8787)
```

**Target Topology:**
```
Client → Load Balancer (round-robin)
           ├─→ Loom Instance 1 (port 8787)
           ├─→ Loom Instance 2 (port 8787)
           └─→ Loom Instance 3 (port 8787)
                (shared cache via Redis / shared DB)
```

**Recommendation:**

**Phase 1: Deploy Multiple Instances**
```bash
# Systemd socket activation + multiple instances
# /etc/systemd/system/loom@.service (template unit)
[Service]
ExecStart=/usr/bin/python -m loom.server --port=%(i)d
Environment=LOOM_PORT=%(i)d

# Start 3 instances:
systemctl start loom@8787
systemctl start loom@8788
systemctl start loom@8789

# Nginx reverse proxy
upstream loom_backends {
    server localhost:8787;
    server localhost:8788;
    server localhost:8789;
}

server {
    listen 8080;
    location / {
        proxy_pass http://loom_backends;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";  # WebSocket
    }
}
```

**Phase 2: Distribute Cache**
```python
# src/loom/cache.py (add Redis backend)
class CacheStore:
    """Abstract cache with SQLite (local) or Redis (distributed)."""
    
    def __init__(self, backend: Literal["sqlite", "redis"] = "sqlite"):
        if backend == "redis":
            self.client = aioredis.from_url("redis://localhost:6379")
        else:
            self.client = None
    
    async def get(self, key: str):
        if self.client:
            return await self.client.get(key)
        else:
            # Local SQLite
            ...
```

**Impact:** Enable 3-5x throughput via horizontal scaling  
**Effort:** 7-10 days (Nginx config, Redis backend, distributed session store)  
**Priority:** P1 (for >100 concurrent clients)

---

### Gap 5.2: SQLite Session Storage Not Distributed (P2)

**Gap:** Browser sessions stored in `~/.loom/sessions/` (local SQLite).

**Issue:**
- If session opened on Instance 1, cannot be used by Instance 2
- No session affinity = every HTTP request must route to same instance

**Recommendation:**
```python
# src/loom/sessions.py (add Redis backend)
class SessionManager:
    """Manage sessions with optional distributed store."""
    
    def __init__(self, backend: Literal["sqlite", "redis"] = "sqlite"):
        self.backend = backend
        if backend == "redis":
            self.store = aioredis.from_url("redis://...")
        else:
            self.store = None
    
    async def create_session(self, name: str, browser: str, ttl: int):
        """Create session; store metadata in Redis."""
        meta = {
            "name": name,
            "browser": browser,
            "created_at": datetime.now(UTC).isoformat(),
            "ttl_seconds": ttl,
        }
        if self.store:
            await self.store.set(f"session:{name}", json.dumps(meta), ex=ttl)
        else:
            # Local SQLite
            ...
```

**Impact:** Enable session mobility across instances  
**Effort:** 4-5 days (Redis backend, test failover)  
**Priority:** P2 (needed for multi-instance deployment)

---

### Gap 5.3: No Load Metrics (P2)

**Issue:** No way to determine when to add more instances.

**Recommendation:**
```python
# Expose Prometheus metrics at /metrics
from prometheus_client import Counter, Histogram, Gauge

tool_calls = Counter("loom_tool_calls_total", "Total tool calls", ["tool"])
tool_duration_ms = Histogram("loom_tool_duration_ms", "Tool duration", ["tool"])
active_sessions = Gauge("loom_active_sessions", "Active browser sessions")
cache_size_bytes = Gauge("loom_cache_size_bytes", "Cache size")
llm_costs_usd = Counter("loom_llm_costs_usd", "LLM costs", ["provider"])

# In each tool:
start = time.time()
try:
    result = await tool(...)
    tool_duration_ms.labels(tool="research_fetch").observe(time.time() - start)
    tool_calls.labels(tool="research_fetch").inc()
finally:
    ...
```

**Impact:** Enable Grafana dashboards, alerting, autoscaling  
**Effort:** 3-4 days (add instrumentation to 375 tools, test Prometheus scrape)  
**Priority:** P2

---

### Scalability Recommendation Summary

| Gap | Action | Effort | Deadline |
|-----|--------|--------|----------|
| Multi-instance deployment | Systemd + Nginx reverse proxy | 7-10d | Week 3 (P1) |
| Distributed cache | Redis backend for CacheStore | 4-5d | Week 3 (P2) |
| Distributed sessions | Redis backend for SessionManager | 4-5d | Week 3 (P2) |
| Load metrics | Prometheus instrumentation | 3-4d | Week 2 (P2) |
| **Subtotal** | **Horizontal Scaling** | **18-24 days** | **Production-Ready** |

---

## 6. Operational Assessment

### Current State

**Minimal Deployment Story:**
- No systemd service file
- No logging rotation
- No backup strategy for cache/sessions
- No monitoring/alerting
- No deployment automation

### Gap 6.1: No Systemd Service Template (P1)

**Gap:** How to run Loom on production?

**Recommendation:**
```ini
# /etc/systemd/system/loom.service
[Unit]
Description=Loom MCP Server
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=loom
Group=loom
WorkingDirectory=/opt/loom
ExecStart=/usr/bin/python -m loom.server \
    --host=127.0.0.1 --port=8787 \
    --config=/etc/loom/config.json
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=LOOM_CONFIG_PATH=/etc/loom/config.json

# Resource limits
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target

# Enable + start:
sudo systemctl daemon-reload
sudo systemctl enable loom
sudo systemctl start loom
sudo systemctl status loom
```

**Effort:** 1-2 days (create service, test startup/shutdown, create loom user)  
**Priority:** P1

---

### Gap 6.2: No Log Rotation (P2)

**Gap:** Logs to journald (good) but no pruning.

**Recommendation:**
```ini
# /etc/logrotate.d/loom
/var/log/loom/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 640 loom loom
    sharedscripts
    postrotate
        systemctl reload loom > /dev/null 2>&1 || true
    endscript
}
```

**Effort:** 1 day  
**Priority:** P2

---

### Gap 6.3: No Backup Strategy (P2)

**Gap:** Cache and sessions are ephemeral but valuable.

**Recommendation:**
```bash
#!/bin/bash
# /usr/local/bin/loom-backup.sh

BACKUP_DIR=/opt/loom/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup cache
tar -czf $BACKUP_DIR/cache_$TIMESTAMP.tar.gz ~/.cache/loom/

# Backup sessions
tar -czf $BACKUP_DIR/sessions_$TIMESTAMP.tar.gz ~/.loom/sessions/

# Keep 7 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/ s3://loom-backups/daily/ --recursive
```

**Cron job:**
```
0 2 * * * /usr/local/bin/loom-backup.sh
```

**Effort:** 1-2 days  
**Priority:** P2

---

### Gap 6.4: No Deployment Automation (P2)

**Gap:** How to update Loom on production without downtime?

**Recommendation:**
```bash
#!/bin/bash
# /usr/local/bin/deploy-loom.sh

set -euo pipefail

VERSION=$1
REPO=github.com/aadelb/loom
PORT1=8787
PORT2=8788

echo "Deploying $VERSION..."

# Clone/update code
cd /opt/loom
git fetch origin
git checkout $VERSION

# Install dependencies (in venv)
source venv/bin/activate
pip install -e ".[all]"

# Swap systemd instances (blue-green deploy)
# Currently on PORT1, bring up PORT2
LOOM_PORT=$PORT2 systemctl start loom@$PORT2

# Health check
sleep 5
curl http://localhost:$PORT2/health || { echo "Health check failed"; exit 1; }

# Switch Nginx upstream
# sed -i "s/localhost:$PORT1/localhost:$PORT2/g" /etc/nginx/sites-enabled/loom
# nginx -s reload

# Stop old instance
systemctl stop loom@$PORT1

echo "Deployed $VERSION successfully"
```

**Effort:** 2-3 days (script, test, document)  
**Priority:** P2

---

### Gap 6.5: Minimal Observability (P1)

**Gap:** Limited visibility into production issues.

**Checklist:**
- ❌ No structured logging (logs are free-form strings)
- ❌ No distributed tracing (requests not correlated)
- ❌ No SLI/SLO (no uptime guarantees)
- ❌ No alerting rules

**Recommendation:**
```python
# src/loom/observability.py
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()

# Use in tools:
log.info("tool_start", tool_name="research_fetch", url=url)
log.info("tool_end", tool_name="research_fetch", elapsed_ms=123, status="success")

# In /health endpoint:
return {
    "status": "healthy",
    "uptime_seconds": ...,
    "sli": {
        "availability": 0.9999,  # 99.99% uptime
        "latency_p95_ms": 1234,  # p95 latency < 2000ms
        "error_rate": 0.001,     # <0.1% errors
    }
}
```

**Alerting Rules (Prometheus):**
```yaml
groups:
  - name: loom
    rules:
      - alert: LoomDown
        expr: up{job="loom"} == 0
        for: 5m
      - alert: HighErrorRate
        expr: rate(loom_tool_calls_error[5m]) > 0.01
      - alert: HighLatency
        expr: histogram_quantile(0.95, loom_tool_duration_ms) > 2000
```

**Effort:** 4-5 days (structured logging, tracing, alerting rules)  
**Priority:** P1

---

### Operational Recommendation Summary

| Item | Action | Effort | Deadline |
|------|--------|--------|----------|
| Systemd service | Create loom.service | 1-2d | Week 1 (P1) |
| Log rotation | Setup logrotate | 1d | Week 1 (P2) |
| Backup strategy | Daily tar.gz + S3 upload | 1-2d | Week 1 (P2) |
| Deployment automation | Blue-green deploy script | 2-3d | Week 2 (P2) |
| Observability | Structured logs + Prometheus + alerting | 4-5d | Week 2 (P1) |
| Documentation | Runbook, troubleshooting guide | 3-4d | Week 2 (P2) |
| **Subtotal** | **Operational Readiness** | **12-17 days** | **Production-Ready** |

---

## 7. Summary Table: Production Readiness Gaps & Recommendations

| Area | Gap | Priority | Effort | Deadline | Owner |
|------|-----|----------|--------|----------|-------|
| **Architecture** | Single-file server scalability | P1 | 7-10d | Week 1-2 | Arch |
| | Circular imports, silent failures | P1 | 2-3d | Week 1 | Dev |
| **Performance** | No latency telemetry | P2 | 4-5d | Week 2 | Eng |
| | Memory footprint unknown | P2 | 2-3d | Week 1 | Eng |
| | Event loop blocking audit | P3 | 3-4d | Week 1-2 | Dev |
| | Load testing | P2 | 5-7d | Week 3 | QA |
| **Security** | mTLS + API key auth | P1 | 3-4d | Week 1 | SecEng |
| | API key rotation | P2 | 5-7d | Week 2 | SecEng |
| | Audit logging coverage | P2 | 2-3d | Week 1 | Dev |
| **Reliability** | Fetch timeout backoff | P2 | 2-3d | Week 1 | Dev |
| | Deadletter queue | P2 | 5-7d | Week 2 | Dev |
| | Universal error wrapper | P3 | 3-4d | Week 1 | Dev |
| **Scalability** | Multi-instance deployment | P1 | 7-10d | Week 3 | Arch |
| | Distributed cache (Redis) | P2 | 4-5d | Week 3 | Dev |
| | Distributed sessions | P2 | 4-5d | Week 3 | Dev |
| | Load metrics (Prometheus) | P2 | 3-4d | Week 2 | Ops |
| **Operations** | Systemd service | P1 | 1-2d | Week 1 | Ops |
| | Log rotation | P2 | 1d | Week 1 | Ops |
| | Backup strategy | P2 | 1-2d | Week 1 | Ops |
| | Deployment automation | P2 | 2-3d | Week 2 | Ops |
| | Observability (logs + tracing + alerts) | P1 | 4-5d | Week 2 | Ops |
| **Docs** | Operational runbook | P2 | 3-4d | Week 2 | Tech Writer |

---

## 8. Recommended Implementation Roadmap

### Week 1: Foundation (P1 Items)

**Monday-Tuesday:**
1. Modularize server.py (tool registry abstraction)
2. Validate tool syntax at startup (catch import errors)
3. Add mTLS + API key auth

**Wednesday-Thursday:**
4. Memory profiling (baseline, per-session)
5. Event loop audit (check for blocking calls)
6. Add timeout backoff to fetch escalation

**Friday:**
7. Create systemd service
8. Set up log rotation
9. Backup strategy

**Deliverable:** Secure, self-hosting server with basic operations

---

### Week 2: Visibility & Reliability (P2 Items)

**Monday-Tuesday:**
10. Structured logging + distributed tracing
11. Prometheus metrics instrumentation
12. Alerting rules (Prometheus + email/Slack)

**Wednesday-Thursday:**
13. Latency telemetry (per-tool aggregation)
14. Load testing (100 concurrent sessions)
15. API key rotation (SecretManager)

**Friday:**
16. Deployment automation (blue-green script)
17. Operations runbook + troubleshooting guide

**Deliverable:** Observable, monitorable production server

---

### Week 3: Scale (P1 for scalability)

**Monday-Tuesday:**
18. Multi-instance deployment (Nginx reverse proxy)
19. Redis cache backend
20. Redis session backend

**Wednesday-Thursday:**
21. Distributed rate limiting (Redis backend)
22. Load test 3-5 instances
23. Failover testing

**Friday:**
24. Capacity planning doc
25. Documentation finalization

**Deliverable:** Horizontally scalable server (3+ instances, 300+ RPS)

---

### Week 4+: Polish & Integration (P3 Items, Optional)

- Deadletter queue for failed tools
- Universal error wrapper for all 375 tools
- Advanced feature: Cost attribution per caller
- Advanced feature: Request tracing (OpenTelemetry)

---

## 9. Success Criteria for Production Readiness

### Must-Have (Blocking)

- [ ] **Security:** mTLS + API key auth enforced on /mcp endpoint
- [ ] **Architecture:** Tool loader abstraction; no silent import failures
- [ ] **Operations:** Systemd service + documented startup/shutdown procedure
- [ ] **Reliability:** Timeout backoff on fetch escalation (prevents 80+ minute hangs)
- [ ] **Observability:** Structured logs, Prometheus metrics, alerting rules

### Should-Have (Non-Blocking)

- [ ] **Performance:** Latency telemetry for all tools; p95 <2000ms
- [ ] **Scalability:** Multi-instance deployment tested (3+ instances)
- [ ] **Reliability:** Deadletter queue for transient failures
- [ ] **Operations:** Blue-green deployment automation

### Nice-to-Have

- [ ] **Performance:** Load testing with 1000+ concurrent sessions
- [ ] **Reliability:** Universal error wrapper + consistent error formats
- [ ] **Documentation:** Advanced troubleshooting guide, runbooks

---

## 10. Estimated Total Effort & Timeline

| Phase | Duration | Effort | Status |
|-------|----------|--------|--------|
| **Current** | — | — | **PARTIAL (70%)** |
| Week 1 (Foundation P1) | 5d | 20d | Blocking |
| Week 2 (Visibility P2) | 5d | 18d | Critical |
| Week 3 (Scale P1) | 5d | 20d | High |
| **Subtotal for MVP** | **15 days** | **58 days** | → **95% ready** |
| Week 4+ (Polish P3) | — | 15-20d | Optional |
| **Total for Full Ready** | **20 days** | **75+ days** | → **100% ready** |

---

## 11. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Tool import failures go silent | HIGH | MEDIUM | Implement validation harness (done Week 1) |
| Memory leak in browser sessions | HIGH | MEDIUM | Memory profiling + monitoring (Week 1-2) |
| p95 latency >5000ms on production | HIGH | MEDIUM | Load testing + latency instrumentation (Week 2) |
| Unauthorized access to /mcp endpoint | CRITICAL | HIGH | Enforce auth immediately (Week 1, blocking) |
| Single-instance cannot handle load | MEDIUM | MEDIUM | Horizontal scaling (Week 3) |
| Cache grows unbounded | MEDIUM | LOW | TTL cleanup exists; monitor sizes |
| SQLite corruption under write contention | MEDIUM | LOW | Switch to Redis for sessions (Week 3) |

---

## 12. Conclusion

**Loom MCP Server is architecturally sound but operationally immature.** The core research pipeline, provider cascading, and security controls are well-designed. However, before production deployment at scale, the following **critical blockers** must be addressed:

1. **Authentication** (P1 BLOCKING) — Enforce API key auth on /mcp endpoint
2. **Architecture** (P1 BLOCKING) — Modularize server.py; validate tool syntax at startup
3. **Operations** (P1 BLOCKING) — Create systemd service, observability, alerting

**Recommended approach:**
- **MVP (Week 1):** Address all P1 items (authentication, architecture, operations)
- **Beta (Weeks 2-3):** Add observability, scalability, load testing
- **Production (Week 4+):** Polish, documentation, advanced features

**Estimated effort:** 3 weeks (20d effort, 15d timeline with parallelization) for MVP → Production-Ready.

Once completed, Loom will be **secure, observable, reliable, and scalable** for enterprise deployment.

---

## Appendix: File Locations for Implementation

### Architecture Refactoring
- New file: `src/loom/tool_registry.py` (tool loader abstraction)
- New file: `src/loom/audit_blocking.py` (event loop audit script)
- Modify: `src/loom/server.py` (reduce from 2100 to 300 lines)

### Performance Instrumentation
- New file: `src/loom/telemetry.py` (ToolLatency + aggregator)
- New file: `src/loom/memory_profiler.py` (memory usage tracking)
- Modify: All tool functions (add timing/telemetry calls)

### Security Hardening
- New file: `src/loom/secrets.py` (SecretManager)
- New file: `src/loom/auth.py` (mTLS + API key)
- Modify: `src/loom/server.py` (add auth middleware)

### Reliability Improvements
- New file: `src/loom/deadletter.py` (failed tool queue)
- New file: `src/loom/tool_wrapper.py` (universal error handler)
- Modify: `src/loom/tools/fetch.py` (timeout backoff)

### Scalability
- New file: `src/loom/cache_redis.py` (Redis cache backend)
- New file: `src/loom/sessions_redis.py` (Redis session backend)
- Modify: `src/loom/cache.py` (abstract backend)
- Modify: `src/loom/sessions.py` (abstract backend)

### Operations
- New file: `deploy/loom.service` (systemd service)
- New file: `deploy/loom-backup.sh` (backup script)
- New file: `deploy/deploy-loom.sh` (blue-green deploy)
- New file: `docs/OPERATIONS.md` (runbook)
- New file: `docs/TROUBLESHOOTING.md` (diagnostics guide)
