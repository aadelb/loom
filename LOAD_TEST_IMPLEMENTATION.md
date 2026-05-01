# Loom MCP Load Test Implementation

## Summary

Created a comprehensive load testing suite for the Loom MCP server with 5 test categories, async HTTP client, detailed metrics collection, and JSON reporting.

**Files Created:**
1. `scripts/load_test.py` — Main load test runner (670 lines)
2. `scripts/LOAD_TEST_README.md` — Comprehensive documentation
3. `scripts/analyze_load_test.py` — Result analysis and comparison tool (280 lines)
4. `scripts/run_load_test_remote.sh` — Remote Hetzner execution helper

## Features

### Load Test Suite (load_test.py)

#### 5 Test Categories

1. **Concurrent Sessions** (10, 20, 50, 100 connections)
   - Tests MCP session management under concurrency
   - Measures connection overhead and multiplexing

2. **Throughput** (100 rapid requests)
   - Single session, maximum request rate
   - Latency percentiles: P50, P95, P99

3. **Heavy Tools** (11 concurrent operations)
   - 5x `research_fetch()` (network I/O)
   - 5x `research_search()` (API calls)
   - 5x `research_text_analyze()` (CPU + processing)

4. **Sustained Load** (10 req/sec for 60 seconds)
   - Continuous load stability
   - Latency degradation detection
   - Memory growth monitoring

5. **Large Payloads** (100KB text upload)
   - Handles chunked requests
   - Multiple concurrent large operations
   - Throughput measurement (MB/s)

#### Metrics Collected

Per test:
- **Request count** — Total requests executed
- **Success rate** — Percentage of successful completions
- **Throughput** — Requests per second (RPS)
- **Latency percentiles** — P50, P95, P99 (ms)
- **Error tracking** — Failed request reasons
- **Duration** — Total test execution time

#### Status Classification

- **PASS** — Exceeds thresholds (≥95% success, sufficient throughput)
- **WARN** — Acceptable range (80-95% success, marginal throughput)
- **FAIL** — Below minimum (>80% failures, insufficient throughput)

### HTTP Client (MCPClient)

```python
class MCPClient:
    async def health_check() -> dict
    async def cache_stats() -> dict
    async def config_get(key) -> dict
    async def fetch(url) -> dict
    async def search(query) -> dict
    async def text_analyze(text) -> dict
```

Uses `httpx.AsyncClient` for:
- Async concurrency
- Connection pooling
- Automatic retries (optional)
- Timeout handling (30s default)

### JSON Report Format

```json
{
  "timestamp": "2026-05-02T15:30:45.123456",
  "overall_status": "PASS",
  "total_duration_sec": 185.4,
  "test_results": [
    {
      "name": "Concurrent Sessions",
      "description": "Test opening multiple simultaneous MCP sessions",
      "status": "PASS",
      "duration_sec": 42.1,
      "request_count": 180,
      "success_rate": "98.3%",
      "throughput_rps": "4.27",
      "latency_ms": {
        "avg": "234.5",
        "p50": "210.2",
        "p95": "450.1",
        "p99": "890.3"
      },
      "error": null
    }
  ],
  "summary": {
    "total_tests": 5,
    "passed": 4,
    "warned": 1,
    "failed": 0
  }
}
```

### Analysis Tool (analyze_load_test.py)

**Single Report Analysis:**
```bash
python3 scripts/analyze_load_test.py load_test_results.json
```

Provides:
- Detailed per-test breakdown
- Recommendations for optimization
- Status and success rate trends
- Latency variance analysis

**Comparison Between Runs:**
```bash
python3 scripts/analyze_load_test.py baseline.json current.json
```

Shows:
- Regression detection
- Performance delta (%)
- Status changes
- Throughput changes
- Latency improvements/degradations

## Usage

### Local Testing
```bash
cd /Users/aadel/projects/loom
PYTHONPATH=src python3 scripts/load_test.py
```

### Quick Mode (Faster)
```bash
PYTHONPATH=src python3 scripts/load_test.py --quick
```

### Remote (Hetzner)
```bash
# Option 1: Direct SSH
ssh hetzner "cd /opt/loom && PYTHONPATH=src python3 scripts/load_test.py"

# Option 2: Helper script
./scripts/run_load_test_remote.sh
```

### Custom Output
```bash
PYTHONPATH=src python3 scripts/load_test.py --output /tmp/results.json
```

## Implementation Details

### Async Architecture

- **Event Loop:** `asyncio.run()` for top-level concurrency
- **Concurrent Tasks:** `asyncio.gather()` for parallel execution
- **Timing:** `time.time()` + statistics for latency metrics
- **Timeouts:** Per-request 30s, per-operation configurable

### Resource Management

- **Connection Pooling:** `httpx.AsyncClient` (reused across requests)
- **Memory:** Metrics collected in-memory, dumped to JSON after
- **Cleanup:** Proper `await client.close()` in finally blocks
- **Error Handling:** All exceptions caught, logged, converted to FAIL status

### Performance Considerations

**Why Hetzner?**
- Mac (24GB RAM) limited for concurrent load
- Hetzner (128GB RAM, strong CPU) can handle 100+ concurrent connections
- Proper MCP server deployed on Hetzner with API keys

**Tuning Parameters:**
- `session_counts = [10, 20, 50, 100]` — Adjust for your capacity
- `request_count = 100` — Rapid fire requests (set 50 for quick)
- `target_rps = 10` — Sustained load rate
- `httpx timeout = 30s` — Per-request timeout

## Success Criteria

### Healthy Server Baseline

| Metric | Target | Good | Warning |
|--------|--------|------|---------|
| Concurrent Sessions (100) | ≥95% success | ≥99% | 80-95% |
| Throughput (100 req) | ≥10 req/s | ≥20 req/s | 5-10 req/s |
| Heavy Tools (11 ops) | ≥90% success | ≥98% | 75-90% |
| Sustained (60s @ 10 req/s) | ≥95% success, stable | <200ms avg | <500ms avg |
| Large Payloads (100KB) | ≥90% success | ≥95% | 80-90% |

### When to Investigate

- **Success rate <80%** — Server errors, timeouts, or crashes
- **Throughput <5 req/s** — Severe bottleneck or misconfiguration
- **Latency P99 > 1000ms** — Queueing, resource contention, or GC pauses
- **Memory growth** — Leak during sustained load (check sustained load test)
- **Connection refused** — Server crashed or not running

## Integration Points

### CI/CD Pipeline

```yaml
# GitHub Actions
- name: Run load tests
  run: PYTHONPATH=src python3 scripts/load_test.py --quick

- name: Analyze results
  run: python3 scripts/analyze_load_test.py load_test_results.json

- name: Check status
  run: |
    STATUS=$(jq -r '.overall_status' load_test_results.json)
    if [ "$STATUS" != "PASS" ]; then exit 1; fi
```

### Pre-Push Hook

```bash
#!/bin/bash
# .git/hooks/pre-push
PYTHONPATH=src python3 scripts/load_test.py --quick || exit 1
```

## Dependencies

**Python Packages (already in loom dependencies):**
- `httpx` — Async HTTP client
- `asyncio` — Async concurrency

**No additional dependencies required.**

## Troubleshooting

### Connection Refused
```
Error: Connection refused (host: 127.0.0.1, port: 8787)
```
**Fix:** Start server: `loom serve`

### Timeouts
```
Timeout: Request did not complete within 30 seconds
```
**Fix:** Increase timeout or reduce load: `--quick` flag

### OOM on Mac
```
MemoryError: Unable to allocate 2GB for buffer
```
**Fix:** Run on Hetzner (128GB RAM) instead of Mac

### Slow Throughput
```
Throughput: 0.5 req/s (expected: 10+ req/s)
```
**Fix:** Check API keys, server logs, network connectivity

## File Locations

**Main Script:**
- `/Users/aadel/projects/loom/scripts/load_test.py`

**Supporting Files:**
- `/Users/aadel/projects/loom/scripts/LOAD_TEST_README.md` — Full documentation
- `/Users/aadel/projects/loom/scripts/analyze_load_test.py` — Result analyzer
- `/Users/aadel/projects/loom/scripts/run_load_test_remote.sh` — Remote runner

**Output Location:**
- `/opt/research-toolbox/tmp/load_test_results.json` (default)
- Configurable via `--output` flag

## Author

Ahmed Adel Bakr Alderai

## Next Steps

1. **Run locally** (quick mode): `PYTHONPATH=src python3 scripts/load_test.py --quick`
2. **Deploy on Hetzner**: `./scripts/run_load_test_remote.sh`
3. **Analyze results**: `python3 scripts/analyze_load_test.py load_test_results.json`
4. **Track over time**: Save results with timestamps, compare runs
5. **Integrate CI/CD**: Add to GitHub Actions workflow or pre-push hooks
