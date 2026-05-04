# Loom Load Testing Guide

Load testing for the Loom MCP server using Locust, a distributed load testing framework.

## Overview

This load testing suite simulates realistic user workloads with weighted task distributions:

- **Health checks** (10%): Lightweight endpoints, expect <100ms
- **Search** (5%): Multi-provider semantic search, expect <5s
- **Fetch** (30%): Single-URL content fetching, expect <10s
- **Deep Research** (20%): Heavy 12-stage pipeline, expect <30s
- **Analytics** (10%): Dashboard queries, expect <2s

## Installation

Install Locust alongside Loom's test dependencies:

```bash
# Via pip
pip install locust>=2.0.0

# Via pyproject.toml (add to [project.optional-dependencies])
pip install -e ".[test,load]"
```

## Quick Start

### Headless Mode (CI/CD, Automated Tests)

```bash
# Default test: 50 users over 60 seconds
./run_load_test.sh headless

# Quick test: 10 users over 30 seconds
./run_load_test.sh headless --quick

# Sustained test: 50 users over 5 minutes
./run_load_test.sh headless --sustained

# Stress test: 200 users over 2 minutes
./run_load_test.sh headless --stress
```

### Web UI Mode (Interactive Testing)

```bash
# Launch Locust web UI (opens http://localhost:8089)
./run_load_test.sh ui

# With stress test parameters
./run_load_test.sh ui --stress
```

## Configuration

### Test Data

Located in `config.py`:

- **TEST_QUERIES**: 20 sample research queries for search/deep_research tasks
- **TEST_URLS**: 10 test URLs for fetch operations
- **RESPONSE_TIME_THRESHOLDS**: Maximum acceptable response times per endpoint
- **PERFORMANCE_TARGETS**: p50/p95/p99 percentile targets

### Response Time Thresholds

```python
RESPONSE_TIME_THRESHOLDS = {
    "health": 100.0,          # ms
    "search": 5000.0,         # ms
    "fetch": 10000.0,         # ms
    "deep_research": 30000.0, # ms
    "analytics": 2000.0,      # ms
}
```

## Understanding Results

### CSV Output

Locust generates CSV files in `tests/load/results/`:

```
load_test_stats.csv
load_test_stats_history.csv
load_test_failures.csv
```

### Key Metrics

| Metric | Meaning | Target |
|--------|---------|--------|
| **Name** | Endpoint name | — |
| **# requests** | Total requests sent | high (ideally 1000+) |
| **# fails** | Failed requests | 0 |
| **Median (ms)** | 50th percentile response time | < threshold |
| **95%ile (ms)** | 95th percentile response time | < threshold |
| **99%ile (ms)** | 99th percentile response time | < threshold |
| **Average (ms)** | Mean response time | reasonable |
| **Min (ms)** | Fastest response | baseline |
| **Max (ms)** | Slowest response | <= threshold |
| **Average size (bytes)** | Mean response payload | reasonable |
| **Requests/s** | Throughput | high |
| **Failures/s** | Error rate | 0 |

### Example Output

```
GET /health            1000  0    50    95     150    60        0      250    1248  1000.0
POST /tool (search)     500  2   2000   4000   5000   2200      100    8500   524   500.0
POST /tool (fetch)      200  1   5000   8000   10000  6000      500    15000  201   200.0
POST /tool (deep)       100  0  15000  25000   30000 18000     2000    35000  101   100.0
GET /analytics          300  1    800   1500    2000    950      200    3500   300   300.0
```

## Interpreting Performance

### Good Performance

- **All failures = 0**: No errors under load
- **p99 < threshold**: 99% of requests meet target time
- **Consistent median/p95**: Stable response times
- **Linear throughput scaling**: Requests/sec increases proportionally

### Performance Issues

#### Slow Health Checks (>100ms)

- Server processing is bottlenecked
- Check CPU/memory usage
- Verify no unoptimized startup routines

#### Slow Search (<5s SLA broken)

- Multi-provider search taking too long
- Check provider API response times
- Consider provider-specific timeouts

#### Growing Response Times

- Database connection pool exhausted
- Memory leaks in tool execution
- Cascading failures (one slow tool blocks others)

#### High Error Rate

```
POST /tool (search) ... 500  150  ...
                              ↑ 150 failures
```

Check server logs:
```bash
# In another terminal while load test runs
tail -f loom.log | grep ERROR
```

## Running Locally

### Prerequisites

1. Loom server running:
   ```bash
   # Terminal 1
   loom serve
   ```

2. Locust installed:
   ```bash
   pip install locust>=2.0.0
   ```

### Execute Load Test

```bash
# Terminal 2
cd /Users/aadel/projects/loom
./tests/load/run_load_test.sh headless
```

### Monitor Server

```bash
# Terminal 3
watch -n 1 'ps aux | grep "loom serve"'
```

## Custom Load Profiles

### Modify User Count

Edit `run_load_test.sh`:

```bash
USERS=100        # Increase to 100 concurrent users
SPAWN_RATE=25    # Spawn 25 new users/sec
RUN_TIME=300     # Run for 5 minutes
```

### Adjust Task Weights

Edit `locustfile.py`:

```python
@task(20)  # Changed from 10 to 20 (doubled frequency)
def health_check(self):
    ...
```

Weight ratios determine task distribution:
- Health: 10 → 10/21 ≈ 48%
- Search: 5 → 5/21 ≈ 24%
- Fetch: 3 → 3/21 ≈ 14%
- Deep: 2 → 2/21 ≈ 9%
- Analytics: 1 → 1/21 ≈ 5%

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Test
on: [push]
jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[all,test]"
      - run: loom serve &
      - run: sleep 5 && ./tests/load/run_load_test.sh headless --quick
      - uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: tests/load/results/
```

## Troubleshooting

### "Server not accessible at http://localhost:8787"

**Problem**: The server isn't running or not bound to localhost:8787.

**Solution**:
```bash
# Verify server is running
curl http://localhost:8787/health

# Check if port is in use
lsof -i :8787

# Start server explicitly
loom serve --host 127.0.0.1 --port 8787
```

### "Connection refused" or "timeout" during load test

**Problem**: Server can't handle concurrent connections.

**Solutions**:
- Reduce user count: `./run_load_test.sh headless --quick`
- Check server logs for errors
- Verify database connection pool size
- Monitor system resources (CPU, memory, file descriptors)

### "All requests failing (500 errors)"

**Problem**: Server crashed or application error.

**Solution**:
```bash
# Check server output
# Kill any hung processes
pkill -f "loom serve"

# Restart with debug logging
LOOM_LOG_LEVEL=DEBUG loom serve

# Re-run load test with fewer users
./run_load_test.sh headless --quick
```

### High memory usage during test

**Problem**: Memory leak in tool execution.

**Solution**:
```bash
# Monitor memory in separate terminal
while true; do
  ps aux | grep loom | grep -v grep | awk '{print $6}'
  sleep 2
done

# Check for connection leaks (database, HTTP)
# Review tool cleanup code
```

## Performance Baselines

Expected baseline performance on a mid-range machine:

```
Endpoint                  p50     p95     p99     Throughput
GET /health              50ms    100ms   150ms   2000 req/sec
POST /tool (search)     2000ms   4000ms  5000ms   100 req/sec
POST /tool (fetch)      5000ms   8000ms  10000ms   50 req/sec
POST /tool (deep)      15000ms  25000ms  30000ms   10 req/sec
GET /analytics           800ms   1500ms   2000ms   300 req/sec
```

Adjust thresholds in `config.py` based on your hardware and acceptable SLAs.

## Advanced Usage

### Custom Load Curve

```python
class LoomUser(HttpUser):
    """Override wait_time for custom load curve."""
    
    def wait_time(self):
        # Ramp up: spend more time early
        import math
        import time
        elapsed = time.time() - self.user_start_time
        return max(0.1, 3 - (elapsed / 10))  # Starts at 3s, decreases
```

### Distributed Load Testing

Run Locust in distributed mode across multiple machines:

```bash
# Master node
locust -f locustfile.py --master

# Worker nodes (on different machines)
locust -f locustfile.py --worker --master-host=<master-ip>
```

### Custom Assertions

Add checks to `locustfile.py`:

```python
@task(5)
def search(self):
    response = self.client.post(...)
    
    # Assert response structure
    assert "results" in response.json()
    assert isinstance(response.json()["results"], list)
```

## References

- [Locust Official Docs](https://docs.locust.io/)
- [Writing Locust Load Tests](https://docs.locust.io/en/stable/writing-a-locustfile.html)
- [Loom Architecture](../docs/architecture.md)
- [Loom Tools Reference](../docs/tools-reference.md)
