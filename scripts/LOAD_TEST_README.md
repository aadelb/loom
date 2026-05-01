# Loom MCP Load Test Suite

## Overview

`load_test.py` is a comprehensive load testing suite that stress-tests the Loom MCP server to identify performance limits and bottlenecks. It exercises the server with concurrent sessions, rapid requests, resource-intensive operations, sustained load, and large payloads.

## Test Categories

### 1. Concurrent Sessions Test
**Purpose:** Verify server handles multiple simultaneous MCP session connections

- Opens 10, 20, 50, and 100 concurrent clients
- Each calls `research_health_check()`
- Measures: Response time, success rate, connection overhead

**Success Criteria:**
- PASS: ≥95% success rate
- WARN: 80-95% success rate
- FAIL: <80% success rate

### 2. Throughput Test
**Purpose:** Identify maximum request-per-second capacity

- Fires 100 rapid requests on a single session
- Calls `research_cache_stats()` repeatedly (fast operation)
- Measures: Requests/second, P50/P95/P99 latencies

**Success Criteria:**
- PASS: ≥95% success + ≥10 req/s
- WARN: ≥80% success + ≥5 req/s
- FAIL: Otherwise

### 3. Heavy Tools Test
**Purpose:** Stress server with resource-intensive operations

Concurrent operations:
- 5x `research_fetch()` (network I/O)
- 5x `research_search()` (API calls + network)
- 5x `research_text_analyze()` (CPU + processing)

Measures: Memory usage, response times, completion rates

**Success Criteria:**
- PASS: ≥90% success rate
- WARN: 70-90% success rate
- FAIL: <70% success rate

### 4. Sustained Load Test
**Purpose:** Verify server stability under continuous load

- Maintains 10 requests/second for 60 seconds (600 total requests)
- Cycles through: `cache_stats`, `config_get`, `search`
- Tracks: Error rate over time, latency degradation, memory growth

**Success Criteria:**
- PASS: ≥95% success + actual RPS ≥90% of target
- WARN: ≥80% success + actual RPS ≥70% of target
- FAIL: Otherwise

### 5. Large Payload Test
**Purpose:** Verify handling of large request/response data

- Sends 100KB text to `research_text_analyze()`
- Multiple concurrent 50KB payloads
- Measures: Throughput (MB/s), success rate

**Success Criteria:**
- PASS: ≥90% success rate
- WARN: 70-90% success rate
- FAIL: <70% success rate

## Usage

### Basic (Local)
```bash
cd /Users/aadel/projects/loom
PYTHONPATH=src python3 scripts/load_test.py
```

### Quick Test (Subset)
```bash
PYTHONPATH=src python3 scripts/load_test.py --quick
```

### On Hetzner (Remote)
```bash
ssh hetzner "cd /opt/loom && PYTHONPATH=src python3 scripts/load_test.py --remote"
```

### Custom Server URL
```bash
PYTHONPATH=src python3 scripts/load_test.py --url http://custom-host:8787
```

### Custom Output Path
```bash
PYTHONPATH=src python3 scripts/load_test.py --output /tmp/results.json
```

## Output Format

Results are saved to JSON at `/opt/research-toolbox/tmp/load_test_results.json` (or custom path):

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
    },
    ...
  ],
  "summary": {
    "total_tests": 5,
    "passed": 4,
    "warned": 1,
    "failed": 0
  }
}
```

### Metrics Explanation

| Metric | Meaning |
|--------|---------|
| `success_rate` | % of requests that completed successfully |
| `throughput_rps` | Average requests per second |
| `latency_ms.avg` | Mean response time in milliseconds |
| `latency_ms.p50` | Median response time (50th percentile) |
| `latency_ms.p95` | 95th percentile response time |
| `latency_ms.p99` | 99th percentile response time |

## Performance Benchmarks

Expected baseline performance (on Hetzner 128GB RAM, strong CPU):

| Test | Target | Good | Acceptable |
|------|--------|------|------------|
| Concurrent Sessions (100) | ≥95% success | ≥99% | ≥90% |
| Throughput (100 req) | ≥10 req/s | ≥20 req/s | ≥5 req/s |
| Heavy Tools (11 ops) | ≥90% success | ≥98% | ≥75% |
| Sustained Load (60s, 10 req/s) | ≥95% success, stable latency | <200ms avg | <500ms avg |
| Large Payloads (100KB+) | ≥90% success | ≥95% | ≥80% |

## Troubleshooting

### Connection Refused
**Problem:** `Error: Connection refused`

**Solution:**
1. Verify server is running: `loom serve`
2. Check host/port: Default is `http://127.0.0.1:8787`
3. On Hetzner: Use SSH tunnel: `ssh -L 8787:localhost:8787 hetzner`

### Timeouts
**Problem:** Many `RequestMetrics` with errors

**Solution:**
1. Reduce concurrent load: Use `--quick` flag
2. Increase timeout in code (default 30s): Edit `MCPClient.__init__`
3. Check server logs for errors: `tail -f ~/.loom/logs/`

### Memory Issues
**Problem:** `MemoryError` or OOM kill

**Solution:**
- Run on Hetzner (128GB RAM) instead of Mac (24GB)
- Use `--quick` to reduce test scope
- Lower concurrent session counts in `test_concurrent_sessions()`

### Slow Performance
**Problem:** Latencies >1000ms or throughput <5 req/s

**Solution:**
1. Check server load: `top` on Hetzner
2. Verify network connectivity: `ping -c 5 127.0.0.1`
3. Check API key configuration: `echo $GROQ_API_KEY`
4. Review server logs: `tail -100 ~/.loom/logs/loom.log`

## Integration with CI/CD

### GitHub Actions
```yaml
- name: Run load tests
  run: |
    PYTHONPATH=src python3 scripts/load_test.py --quick --output test-results.json

- name: Check results
  run: |
    python3 -c "
    import json
    with open('test-results.json') as f:
        report = json.load(f)
    if report['overall_status'] != 'PASS':
        print(f\"Load test failed: {report['overall_status']}\")
        exit(1)
    "
```

### Local Pre-Commit
```bash
#!/bin/bash
# .git/hooks/pre-push
PYTHONPATH=src python3 scripts/load_test.py --quick || exit 1
```

## Interpreting Results

### Good Results (PASS)
- All test statuses are PASS
- Success rates ≥95%
- Latencies are consistent (P99 < 2x P50)
- No memory growth over sustained load
- Actual RPS meets or exceeds target

### Warning Results (WARN)
- Some tests are WARN status (80-95% success)
- Latencies show high variance (P99 >> P50)
- Throughput is lower than expected but functional
- Occasional timeouts in heavy load
- Memory grows during sustained load

**Action:** Monitor closely, may indicate capacity limits or resource exhaustion under peak load.

### Failure Results (FAIL)
- One or more FAIL status
- Success rates <80%
- Many timeout or error responses
- Server crashes or connection drops

**Action:** Investigate immediately. Review server logs, check resource availability, verify API key configuration.

## Extending the Tests

To add custom test cases:

1. Add method to `LoadTester`:
```python
async def test_custom(self, quick: bool = False) -> None:
    result = TestResult(
        name="Custom Test",
        description="Your test description",
    )
    # Implementation
    self.results.append(result)
```

2. Call from `run_all_tests()`:
```python
await self.test_custom(quick)
```

3. Helper for timed execution:
```python
async def _timed_custom_tool(self, client: MCPClient, param: str) -> RequestMetrics:
    start = time.time()
    try:
        result = await client._call_tool("research_custom", {"param": param})
        latency = (time.time() - start) * 1000
        success = "error" not in result
        return RequestMetrics(
            status=200 if success else 500,
            latency_ms=latency,
            timestamp=start,
            success=success,
            error=result.get("error") if not success else None,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return RequestMetrics(
            status=500,
            latency_ms=latency,
            timestamp=start,
            success=False,
            error=str(e),
        )
```

## Advanced: Distributed Load Testing

For testing with load from multiple machines:

```python
# distributed_load.py
import asyncio
from scripts.load_test import LoadTester

async def main():
    testers = [
        LoadTester(base_url="http://server:8787", output_path=f"/tmp/results_{i}.json")
        for i in range(10)  # 10 parallel load clients
    ]
    await asyncio.gather(*[t.run_all_tests() for t in testers])

asyncio.run(main())
```

## Author

Ahmed Adel Bakr Alderai

## License

MIT
