# Loom Load Test - Example Output

This document shows example output from a healthy Loom MCP server running the load test suite.

## Console Output

```
$ PYTHONPATH=src python3 scripts/load_test.py

Starting Loom MCP load tests...
Target: http://127.0.0.1:8787

[TEST 1] Concurrent Sessions...
  Testing 10 concurrent sessions...
    10 sessions: 10 successful
  Testing 20 concurrent sessions...
    20 sessions: 20 successful
  Testing 50 concurrent sessions...
    50 sessions: 50 successful
  Testing 100 concurrent sessions...
    100 sessions: 100 successful
  Result: PASS (100.0% success)

[TEST 2] Throughput (Rapid Requests)...
  Result: PASS (47.82 req/s, 100.0% success)

[TEST 3] Heavy Tools (Resource-Intensive)...
  Result: PASS (94.6% success, avg 312ms)

[TEST 4] Sustained Load...
  Result: PASS (9.95 actual req/s, 99.2% success, avg latency 152ms)

[TEST 5] Large Payloads...
  Result: PASS (95.2% success)

Results saved to: /opt/research-toolbox/tmp/load_test_results.json
Overall Status: PASS
Summary: {'passed': 5, 'warned': 0, 'failed': 0}
```

## JSON Report

```json
{
  "timestamp": "2026-05-02T15:30:45.123456",
  "overall_status": "PASS",
  "total_duration_sec": 187.3,
  "test_results": [
    {
      "name": "Concurrent Sessions",
      "description": "Test opening multiple simultaneous MCP sessions",
      "status": "PASS",
      "duration_sec": 42.1,
      "request_count": 180,
      "success_rate": "100.0%",
      "throughput_rps": "4.27",
      "latency_ms": {
        "avg": "234.5",
        "p50": "210.2",
        "p95": "450.1",
        "p99": "890.3"
      },
      "error": null
    },
    {
      "name": "Throughput",
      "description": "Fire 100 rapid requests on single session",
      "status": "PASS",
      "duration_sec": 2.09,
      "request_count": 100,
      "success_rate": "100.0%",
      "throughput_rps": "47.82",
      "latency_ms": {
        "avg": "18.5",
        "p50": "15.2",
        "p95": "35.4",
        "p99": "62.1"
      },
      "error": null
    },
    {
      "name": "Heavy Tools",
      "description": "Concurrent fetch, search, and analysis operations",
      "status": "PASS",
      "duration_sec": 45.2,
      "request_count": 13,
      "success_rate": "94.6%",
      "throughput_rps": "0.29",
      "latency_ms": {
        "avg": "312.4",
        "p50": "298.1",
        "p95": "723.2",
        "p99": "1205.8"
      },
      "error": null
    },
    {
      "name": "Sustained Load",
      "description": "Maintain 10 req/sec for 60 seconds",
      "status": "PASS",
      "duration_sec": 61.5,
      "request_count": 597,
      "success_rate": "99.2%",
      "throughput_rps": "9.71",
      "latency_ms": {
        "avg": "152.3",
        "p50": "145.1",
        "p95": "234.5",
        "p99": "456.7"
      },
      "error": null
    },
    {
      "name": "Large Payloads",
      "description": "Send 100KB request + receive large responses",
      "status": "PASS",
      "duration_sec": 36.2,
      "request_count": 4,
      "success_rate": "95.2%",
      "throughput_rps": "0.11",
      "latency_ms": {
        "avg": "8756.2",
        "p50": "8521.3",
        "p95": "9234.5",
        "p99": "9512.1"
      },
      "error": null
    }
  ],
  "summary": {
    "total_tests": 5,
    "passed": 5,
    "warned": 0,
    "failed": 0
  }
}
```

## Analysis Output

```
$ python3 scripts/analyze_load_test.py /opt/research-toolbox/tmp/load_test_results.json

======================================================================
Load Test Analysis: /opt/research-toolbox/tmp/load_test_results.json
======================================================================

Timestamp: 2026-05-02T15:30:45.123456
Total Duration: 187.3s
Overall Status: PASS

Summary:
  Total Tests: 5
  Passed: 5
  Warned: 0
  Failed: 0

Test Results:

  Concurrent Sessions
    Status: PASS
    Duration: 42.1s
    Requests: 180
    Success Rate: 100.0%
    Throughput: 4.27 req/s
    Latency (ms):
      Avg:  234.5
      P50:  210.2
      P95:  450.1
      P99:  890.3

  Throughput
    Status: PASS
    Duration: 2.1s
    Requests: 100
    Success Rate: 100.0%
    Throughput: 47.82 req/s
    Latency (ms):
      Avg:  18.5
      P50:  15.2
      P95:  35.4
      P99:  62.1

  Heavy Tools
    Status: PASS
    Duration: 45.2s
    Requests: 13
    Success Rate: 94.6%
    Throughput: 0.29 req/s
    Latency (ms):
      Avg:  312.4
      P50:  298.1
      P95:  723.2
      P99:  1205.8
    Recommendations:
      - Success rate below 95% - monitor for reliability issues

  Sustained Load
    Status: PASS
    Duration: 61.5s
    Requests: 597
    Success Rate: 99.2%
    Throughput: 9.71 req/s
    Latency (ms):
      Avg:  152.3
      P50:  145.1
      P95:  234.5
      P99:  456.7

  Large Payloads
    Status: PASS
    Duration: 36.2s
    Requests: 4
    Success Rate: 95.2%
    Throughput: 0.11 req/s
    Latency (ms):
      Avg:  8756.2
      P50:  8521.3
      P95:  9234.5
      P99:  9512.1
```

## Comparison Output

```
$ python3 scripts/analyze_load_test.py baseline.json current.json

======================================================================
Load Test Comparison
======================================================================
Baseline: baseline.json
Current:  current.json

======================================================================

Overall Status:
  Baseline: PASS
  Current:  PASS

Results Summary:
  Baseline: 5 PASS, 0 WARN, 0 FAIL
  Current:  5 PASS, 0 WARN, 0 FAIL

======================================================================
Test-by-Test Comparison
======================================================================

  Concurrent Sessions:
    Status: PASS → PASS → Same
    Success Rate: 98.3% → 100.0% (+1.7%)
    Throughput: 4.12 → 4.27 req/s (+3.6%)
    Avg Latency: 245.2ms → 234.5ms (-4.4%)
    P99 Latency: 923.4ms → 890.3ms (-3.6%)

  Throughput:
    Status: PASS → PASS → Same
    Success Rate: 99.5% → 100.0% (+0.5%)
    Throughput: 46.21 → 47.82 req/s (+3.5%)
    Avg Latency: 19.2ms → 18.5ms (-3.6%)
    P99 Latency: 65.3ms → 62.1ms (-4.9%)

  Heavy Tools:
    Status: WARN → PASS → ✓ Improved
    Success Rate: 85.2% → 94.6% (+9.4%)
    Throughput: 0.27 → 0.29 req/s (+7.4%)
    Avg Latency: 412.3ms → 312.4ms (-24.2%)
    P99 Latency: 1523.4ms → 1205.8ms (-20.8%)

  Sustained Load:
    Status: PASS → PASS → Same
    Success Rate: 98.1% → 99.2% (+1.1%)
    Throughput: 9.45 → 9.71 req/s (+2.8%)
    Avg Latency: 156.2ms → 152.3ms (-2.5%)
    P99 Latency: 487.2ms → 456.7ms (-6.3%)

  Large Payloads:
    Status: PASS → PASS → Same
    Success Rate: 93.4% → 95.2% (+1.8%)
    Throughput: 0.10 → 0.11 req/s (+10.0%)
    Avg Latency: 8923.5ms → 8756.2ms (-1.9%)
    P99 Latency: 9734.2ms → 9512.1ms (-2.3%)

Summary: ✓ Performance IMPROVED
```

## Quick Mode Output

```
$ PYTHONPATH=src python3 scripts/load_test.py --quick

Starting Loom MCP load tests...
Target: http://127.0.0.1:8787

[TEST 1] Concurrent Sessions...
  Testing 10 concurrent sessions...
    10 sessions: 10 successful
  Testing 20 concurrent sessions...
    20 sessions: 20 successful
  Result: PASS (100.0% success)

[TEST 2] Throughput (Rapid Requests)...
  Result: PASS (48.23 req/s, 100.0% success)

[TEST 3] Heavy Tools (Resource-Intensive)...
  Result: PASS (92.3% success, avg 245ms)

[TEST 4] Sustained Load...
  Result: PASS (9.98 actual req/s, 99.8% success, avg latency 148ms)

[TEST 5] Large Payloads...
  Result: PASS (100.0% success)

Results saved to: /opt/research-toolbox/tmp/load_test_results.json
Overall Status: PASS
Summary: {'passed': 5, 'warned': 0, 'failed': 0}

Total time: 42 seconds (quick mode)
```

## Warning Scenario Output

```
$ python3 scripts/analyze_load_test.py warning_run.json

======================================================================
Load Test Analysis: warning_run.json
======================================================================

Timestamp: 2026-05-02T14:20:15.654321
Total Duration: 195.4s
Overall Status: WARN

Summary:
  Total Tests: 5
  Passed: 3
  Warned: 2
  Failed: 0

Test Results:

  Concurrent Sessions
    Status: WARN
    Duration: 48.2s
    Requests: 180
    Success Rate: 87.2%
    Throughput: 3.73 req/s
    Latency (ms):
      Avg:  534.2
      P50:  512.3
      P95:  834.5
      P99:  1245.6
    Recommendations:
      - Success rate below 95% - monitor for reliability issues
      - High latency variance (P99 2.3x avg) - check for outliers

  Throughput
    Status: WARN
    Duration: 3.2s
    Requests: 100
    Success Rate: 92.1%
    Throughput: 31.25 req/s
    Latency (ms):
      Avg:  28.4
      P50:  25.1
      P95:  54.2
      P99:  95.3

  Heavy Tools
    Status: PASS
    Duration: 47.1s
    Requests: 13
    Success Rate: 96.2%
    Throughput: 0.28 req/s
    Latency (ms):
      Avg:  418.2
      P50:  401.2
      P95:  834.5
      P99:  1512.3

  Sustained Load
    Status: WARN
    Duration: 61.8s
    Requests: 597
    Success Rate: 81.2%
    Throughput: 9.65 req/s
    Latency (ms):
      Avg:  523.4
      P50:  501.2
      P95:  834.5
      P99:  1234.5
    Recommendations:
      - Success rate below 95% - monitor for reliability issues
      - Sustained load below target - consider optimization

  Large Payloads
    Status: PASS
    Duration: 39.1s
    Requests: 4
    Success Rate: 100.0%
    Throughput: 0.10 req/s
    Latency (ms):
      Avg:  9234.2
      P50:  8945.1
      P95:  9512.3
      P99:  9834.5
```

## Failure Scenario Output

```
$ python3 scripts/analyze_load_test.py failure_run.json

======================================================================
Load Test Analysis: failure_run.json
======================================================================

Timestamp: 2026-05-02T13:10:22.123456
Total Duration: 45.6s
Overall Status: FAIL

Summary:
  Total Tests: 5
  Passed: 2
  Warned: 1
  Failed: 2

Test Results:

  Concurrent Sessions
    Status: FAIL
    Duration: 12.3s
    Requests: 45
    Success Rate: 45.2%
    Error: Connection timeout after 30 seconds
    Recommendations:
      - Critical: Success rate below 80% - investigate failures
      - Test failed - review error logs

  Throughput
    Status: FAIL
    Duration: 5.2s
    Requests: 100
    Success Rate: 65.3%
    Error: Server error: HTTP 500, 503
    Recommendations:
      - Throughput below 5 req/s - check server capacity
      - Test failed - review error logs

  Heavy Tools
    Status: FAIL
    Duration: 18.1s
    Requests: 11
    Success Rate: 18.2%
    Error: Multiple tool failures, API errors
    Recommendations:
      - Critical: Success rate below 80% - investigate failures
      - Test failed - review error logs

  Sustained Load
    Status: WARN
    Duration: 65.0s
    Requests: 597
    Success Rate: 73.2%
    Error: Increasing error rate over time
    Recommendations:
      - Success rate below 95% - monitor for reliability issues
      - Sustained load below target - consider optimization

  Large Payloads
    Status: PASS
    Duration: 24.8s
    Requests: 4
    Success Rate: 100.0%
    Throughput: 0.16 req/s
```

## Interpreting Results

### PASS Status Indicators
- All 5 tests PASS
- Success rates ≥95%
- Latency variance (P99/avg) < 5x
- Sustained load maintains target RPS
- No memory growth over sustained load

### WARN Status Indicators
- 1-2 tests WARN status
- Success rates 80-95%
- Latency variance 5-10x
- Throughput 5-10 req/s
- Memory grows during sustained load

### FAIL Status Indicators
- 1+ tests FAIL status
- Success rates <80%
- Connection timeouts or server errors
- Server crashes or cannot handle load
- Review error logs for root cause
