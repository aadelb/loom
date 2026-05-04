# SLA Monitoring System

This document describes the SLA (Service-Level Agreement) monitoring system integrated into Loom.

## Overview

The SLA monitoring system tracks four key service-level metrics over a sliding 1-hour window:

1. **Uptime Percent** (target: 99.9%)
   - Percentage of successful requests vs. total requests
   - Formula: `(successful_requests / total_requests) * 100`

2. **P95 Latency** (target: 5000ms)
   - 95th percentile response time across all requests
   - Identifies slow tool executions

3. **Error Rate Percent** (target: 1.0%)
   - Percentage of failed requests vs. total requests
   - Formula: `(failed_requests / total_requests) * 100`

4. **Tool Availability Percent** (target: 95.0%)
   - Percentage of unique tools responding successfully
   - Tracks per-tool health for availability insights

## Architecture

### Components

- **`sla_monitor.py`** - Core SLA monitoring implementation
  - `SLAMonitor` class: Singleton that tracks metrics in a sliding window
  - `RequestMetrics`: Data structure for individual request measurements
  - `BreachEvent`: Represents an active SLA breach

- **`tools/sla_status.py`** - MCP tool for SLA status reporting
  - `research_sla_status()`: Returns current metrics and breach status

- **`server.py`** - Integration with tool wrapper
  - Automatically records successful requests after execution
  - Records failed requests on timeouts and exceptions
  - Calls `check_and_alert()` after each request to detect breaches

## Usage

### Getting SLA Status

Call the `research_sla_status()` MCP tool to get current metrics:

```python
from loom.tools.sla_status import research_sla_status

result = research_sla_status()

# Returns:
# {
#   "current_sla": {
#     "uptime_percent": {"actual": 99.95, "target": 99.9},
#     "p95_latency_ms": {"actual": 3500.0, "target": 5000.0},
#     "error_rate_percent": {"actual": 0.05, "target": 1.0},
#     "tool_availability_percent": {"actual": 98.0, "target": 95.0},
#     "timestamp": "2026-05-04T12:34:56.789Z",
#     "metrics_count": 1234,
#     "window_age_seconds": 3600.0
#   },
#   "is_breaching": False,
#   "breaches": [],
#   "status": "healthy"  # or "degraded" / "critical"
# }
```

### Direct Monitor Access

Get the singleton monitor instance:

```python
from loom.sla_monitor import get_sla_monitor

monitor = get_sla_monitor()

# Record a request (normally done automatically by _wrap_tool)
monitor.record_request(success=True, latency_ms=250.0, tool_name="research_fetch")

# Check and update breach status
monitor.check_and_alert()

# Get current metrics
sla_metrics = monitor.get_current_sla()

# Check if any SLA is breached
if monitor.is_breaching():
    for breach in monitor.get_breaches():
        print(f"SLA Breach: {breach.metric} at {breach.actual}% vs {breach.target}%")
```

### Updating SLA Targets

Modify SLA targets at runtime:

```python
monitor.set_sla_target("uptime_percent", 99.95)  # Increase uptime requirement
monitor.set_sla_target("p95_latency_ms", 3000.0)  # Tighten latency SLA
```

## Integration with Tool Wrapper

The SLA monitor is automatically integrated into `_wrap_tool()` in `server.py`:

1. **Success path**: Calls `record_request(success=True, latency_ms=..., tool_name=...)`
2. **Timeout path**: Calls `record_request(success=False, latency_ms=..., tool_name=...)`
3. **Exception path**: Calls `record_request(success=False, latency_ms=..., tool_name=...)`
4. **After each record**: Calls `check_and_alert()` to detect breaches

When a breach is detected, a warning is logged:
```
WARNING: SLA breach detected: uptime_percent at 95.50% vs target 99.90%
```

When a breach recovers:
```
INFO: SLA recovered: uptime_percent at 99.95% (was breached for 1200.0s)
```

## Data Retention

The monitor uses a `deque(maxlen=6000)` to store request metrics:
- At 1 request/sec: holds exactly 1.67 hours
- At 10 requests/sec: holds exactly 10 minutes
- At 0.5 requests/sec: holds approximately 3.3 hours

The sliding window automatically discards old metrics when the deque fills up.

## Testing

Comprehensive test suites are provided:

- **`tests/test_sla_monitor.py`** (400+ lines)
  - Unit tests for all SLAMonitor methods
  - Tests for metrics calculation
  - Breach detection and recovery scenarios
  - Sliding window behavior

- **`tests/test_tools/test_sla_status.py`** (250+ lines)
  - Tests for the `research_sla_status()` MCP tool
  - Response format validation
  - Integration tests

Run tests:
```bash
pytest tests/test_sla_monitor.py -v
pytest tests/test_tools/test_sla_status.py -v
```

## Monitoring and Alerting

The SLA system integrates with existing alerting infrastructure:

1. **Structured logging**: Breaches and recoveries are logged at WARN/INFO level
2. **Log format**: 
   - `log.warning("SLA breach detected: {metric} at {actual}% vs {target}%")`
   - `log.info("SLA recovered: {metric} at {actual}% (was breached for {duration}s)")`

3. **Integration with `alerting.py`**: Can be extended to send webhooks/emails for critical breaches

## Performance Considerations

- **Memory**: ~6000 RequestMetrics objects, each ~40 bytes = ~240KB
- **CPU**: O(n log n) for percentile calculation on `check_and_alert()`
  - n = number of requests in window (typically < 6000)
  - Called once per tool execution (microseconds for typical n)

- **Thread-safe**: Deque operations are atomic in CPython; distributed deployments should use AsyncLock if needed

## Example Scenarios

### Scenario 1: Detection of Service Degradation

```python
# Tool execution times increase significantly
for i in range(100):
    latency = 1000 + (5000 * i)  # Growing latencies
    monitor.record_request(success=True, latency_ms=latency)

monitor.check_and_alert()
# Triggers: "SLA breach detected: p95_latency_ms at 7500% vs 5000%"
```

### Scenario 2: High Error Rate

```python
# Simulate 5% error rate
for _ in range(95):
    monitor.record_request(success=True, latency_ms=100.0)
for _ in range(5):
    monitor.record_request(success=False, latency_ms=5000.0)

monitor.check_and_alert()
# Triggers: "SLA breach detected: error_rate_percent at 5.0% vs 1.0%"
```

### Scenario 3: Recovery from Outage

```python
# Simulate outage recovery
for _ in range(100):
    monitor.record_request(success=False, latency_ms=10000.0)
monitor.check_and_alert()
# Breaches detected

# Recovery begins
for _ in range(1000):
    monitor.record_request(success=True, latency_ms=100.0)
monitor.check_and_alert()
# Breach recovers: "SLA recovered: uptime_percent at 99.01% (was breached for 120s)"
```

## Future Enhancements

Potential extensions:

1. **Persistent SLA metrics** to external time-series database (Prometheus, InfluxDB)
2. **Historical breach reporting** with duration and impact quantification
3. **Per-customer SLA tracking** for multi-tenant deployments
4. **SLA-based tool throttling** (slow down requests if breaching latency)
5. **Configurable breach thresholds** (separate alert vs. critical levels)
6. **Webhook notifications** for breach events
7. **Dashboard integration** to visualize SLA metrics over time
