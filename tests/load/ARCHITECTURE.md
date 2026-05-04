# Load Test Architecture

## Test Suite Overview

This load testing suite uses Locust to simulate realistic user workloads against the Loom MCP server.

## Components

### 1. locustfile.py
Main Locust configuration defining user behavior and task distribution.

**LoomUser class:**
- Simulates a single user interacting with the Loom server
- Wait time: 1-3 seconds between tasks (realistic user think time)
- Host: http://localhost:8787 (default, overridable)

**Tasks (weighted distribution):**
```
health_check(10)       → 48%  of requests
search(5)              → 24%  of requests
fetch(3)               → 14%  of requests
deep_research(2)       → 10%  of requests
analytics(1)           → 5%   of requests
                        -----
Total weight: 21       → 100%
```

### 2. config.py
Configuration data and performance targets.

**Key sections:**
- `TEST_QUERIES`: 20 sample research queries
- `TEST_URLS`: 10 test URLs for fetch operations
- `RESPONSE_TIME_THRESHOLDS`: SLA targets per endpoint
- `PERFORMANCE_TARGETS`: p50/p95/p99 percentile targets
- `LOAD_TEST_PARAMS`: Default test parameters
- `RATE_LIMIT_EXPECTATIONS`: Expected rate limit tolerances

### 3. run_load_test.sh
Bash wrapper script for running tests with convenience flags.

**Modes:**
- `headless`: CI/CD friendly, no web UI
- `ui`: Interactive web UI (port 8089)

**Test types:**
- `--quick`: 10 users, 30 seconds
- `--sustained`: 50 users, 5 minutes
- `--stress`: 200 users, 2 minutes

### 4. Documentation
- `README.md`: Comprehensive guide with all details
- `QUICKSTART.md`: Quick reference for common tasks
- `ARCHITECTURE.md`: This file, explaining the design

## Task Distribution Rationale

### Health Check (48%)
- Lightweight `/health` endpoint
- Measures baseline server performance
- Should be sub-100ms
- Tests don't rely on external services

### Search (24%)
- POST to `/tool` with `research_search` parameters
- Medium load, 5-second SLA
- Calls multiple search providers (Exa, Tavily, etc.)
- Realistic user workload for information discovery

### Fetch (14%)
- POST to `/tool` with `research_fetch` parameters
- Moderate load, 10-second SLA
- Includes Cloudflare escalation logic
- Tests network resilience and HTTP handling

### Deep Research (10%)
- POST to `/tool` with `research_deep` parameters
- Heavy operation, 30-second SLA
- Combines search + fetch + extraction + ranking
- Tests end-to-end pipeline under load

### Analytics (5%)
- GET `/analytics` dashboard data
- Light workload, 2-second SLA
- Tests metrics collection and aggregation
- Lower frequency (power-users only)

## Response Time Thresholds

| Endpoint | Threshold | Rationale |
|----------|-----------|-----------|
| health | 100ms | Baseline server responsiveness |
| search | 5000ms | Multi-provider aggregation |
| fetch | 10000ms | Network latency + parsing |
| deep_research | 30000ms | Full 12-stage pipeline |
| analytics | 2000ms | Database query + aggregation |

## Performance Metrics Collected

Locust tracks:
- **Throughput**: Requests per second
- **Response times**: Min, median, p95, p99, max
- **Failures**: Count and error messages
- **Request sizes**: Payload bytes
- **Response sizes**: Output bytes

## Load Curve Strategy

Default linear spawn:
- Start: 0 users
- Spawn rate: 10 users/second
- Target: 50 users
- Ramp-up time: 5 seconds
- Sustained: 55 more seconds
- Total: 60-second test

**Stress test** uses aggressive spawn:
- Target: 200 users
- Spawn rate: 50 users/second
- Ramp-up time: 4 seconds
- Sustained: 116 more seconds

## Output Artifacts

Generated in `tests/load/results/`:

```
load_test_stats.csv
├─ Name: Endpoint name
├─ # requests: Total requests sent
├─ # fails: Failed requests
├─ Median (ms): 50th percentile
├─ 95%ile (ms): 95th percentile
├─ 99%ile (ms): 99th percentile
└─ Requests/s: Throughput

load_test_stats_history.csv
├─ Timestamp: Per-second snapshots
├─ # requests: Cumulative
├─ # failures: Cumulative
└─ Response times

load_test_failures.csv
├─ Name: Failed endpoint
├─ # fails: Failure count
├─ Failure: Error message
└─ response_time (ms): When applicable
```

## Extension Points

### Custom Task Weights

Edit `locustfile.py`:
```python
@task(15)  # Increased from 10
def health_check(self):
    ...
```

### Custom Test Data

Edit `config.py`:
```python
TEST_QUERIES = [
    "your query",
    ...
]
```

### Custom Load Curve

Subclass HttpUser:
```python
class CustomLoomUser(HttpUser):
    def wait_time(self):
        # Exponential backoff, ramp-up, etc.
        return 1.0
```

### Custom Assertions

Add to any task method:
```python
with self.client.get(...) as response:
    assert response.json()["status"] == "ok"
```

## Integration with CI/CD

The load test can be embedded in pipelines:

```yaml
- name: Run load test
  run: ./tests/load/run_load_test.sh headless --quick
  
- name: Check results
  run: |
    # Parse CSV and fail if thresholds exceeded
    python3 scripts/check_load_test.py tests/load/results/
```

## Monitoring During Tests

Watch server metrics while test runs:

```bash
# Terminal 1: Start server
loom serve

# Terminal 2: Run load test
./tests/load/run_load_test.sh headless

# Terminal 3: Monitor
watch -n 1 'tail -5 ~/.loom/logs/server.log'
```

## References

- Locust Documentation: https://docs.locust.io/
- Loom Server: /Users/aadel/projects/loom/src/loom/server.py
- Tool Registry: /Users/aadel/projects/loom/src/loom/tools/
