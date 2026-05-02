# Loom MCP Load Test Suite - Complete Index

## Overview

A comprehensive load testing suite for the Loom MCP server with 5 test categories, async HTTP client, detailed metrics, and JSON reporting.

## Start Here

**First time?** Read: [Quick Start Guide](scripts/LOAD_TEST_QUICKSTART.md) (5 minutes)

**Need details?** Read: [Full Reference](scripts/LOAD_TEST_README.md) (15 minutes)

**Want examples?** See: [Example Output](LOAD_TEST_EXAMPLE_OUTPUT.md) (10 minutes)

## Files Overview

### Executable Scripts

1. **`scripts/load_test.py`** (751 lines)
   - Main load test runner
   - 5 concurrent test categories
   - Async HTTP client for MCP
   - JSON report generation
   - Usage: `PYTHONPATH=src python3 scripts/load_test.py`

2. **`scripts/analyze_load_test.py`** (269 lines)
   - Analyze load test results
   - Single report analysis with recommendations
   - Comparison mode for baseline vs current
   - Regression detection
   - Usage: `python3 scripts/analyze_load_test.py report.json`

3. **`scripts/run_load_test_remote.sh`**
   - Remote Hetzner execution helper
   - Automatic result retrieval
   - SSH tunneling support
   - Usage: `./scripts/run_load_test_remote.sh`

### Documentation

1. **`scripts/LOAD_TEST_QUICKSTART.md`**
   - 30-second setup guide
   - Common one-command examples
   - Issue troubleshooting table
   - **Read this first!**

2. **`scripts/LOAD_TEST_README.md`**
   - Comprehensive reference documentation
   - Detailed test descriptions
   - Success criteria and thresholds
   - Performance benchmarks
   - Troubleshooting guide
   - CI/CD integration examples

3. **`LOAD_TEST_IMPLEMENTATION.md`**
   - Technical implementation details
   - Architecture and design decisions
   - Code organization
   - Performance tuning recommendations

4. **`LOAD_TEST_EXAMPLE_OUTPUT.md`**
   - Real-world example outputs
   - PASS/WARN/FAIL scenarios
   - JSON report examples
   - Analysis tool output samples

5. **`LOAD_TEST_INDEX.md`** (this file)
   - Navigation guide for all documentation
   - Quick reference to all files and their purpose

## Quick Commands

### Run Tests

```bash
# Quick test (2 min)
PYTHONPATH=src python3 scripts/load_test.py --quick

# Full test (10 min)
PYTHONPATH=src python3 scripts/load_test.py

# Remote on Hetzner
./scripts/run_load_test_remote.sh
```

### Analyze Results

```bash
# Single report analysis
python3 scripts/analyze_load_test.py /opt/research-toolbox/tmp/load_test_results.json

# Compare baseline vs current
python3 scripts/analyze_load_test.py baseline.json current.json
```

## Test Categories

| Test | Purpose | Target | Good |
|------|---------|--------|------|
| Concurrent Sessions | Handle 10-100 simultaneous connections | ≥95% | ≥99% |
| Throughput | Maximum request rate on single session | ≥10 req/s | ≥20 req/s |
| Heavy Tools | Concurrent fetch, search, analyze | ≥90% | ≥98% |
| Sustained Load | 10 req/sec for 60 seconds | ≥95% | <200ms avg |
| Large Payloads | 100KB+ request/response handling | ≥90% | ≥95% |

## Key Metrics

- **Success Rate**: % of requests that completed successfully
- **Throughput**: Requests per second (RPS)
- **Latency**: Response time percentiles (P50, P95, P99)
- **Status**: PASS (≥95% success), WARN (80-95%), FAIL (<80%)

## Documentation Map

```
START HERE
    |
    +-- LOAD_TEST_QUICKSTART.md (quick start, 5 min)
    |
    +-- LOAD_TEST_README.md (full reference, 15 min)
    |   |
    |   +-- Test categories (detailed)
    |   +-- Success criteria
    |   +-- Performance benchmarks
    |   +-- Troubleshooting
    |   +-- CI/CD integration
    |
    +-- LOAD_TEST_EXAMPLE_OUTPUT.md (examples, 10 min)
    |   |
    |   +-- Console output examples
    |   +-- JSON report examples
    |   +-- Analysis output samples
    |   +-- PASS/WARN/FAIL scenarios
    |
    +-- LOAD_TEST_IMPLEMENTATION.md (technical, 15 min)
        |
        +-- Architecture
        +-- Code structure
        +-- Performance tuning
        +-- Integration points

EXECUTABLE SCRIPTS
    |
    +-- load_test.py (main runner)
    |   +-- 5 test categories
    |   +-- MCP HTTP client
    |   +-- JSON reporting
    |
    +-- analyze_load_test.py (analysis)
    |   +-- Single report analysis
    |   +-- Comparison mode
    |   +-- Recommendations
    |
    +-- run_load_test_remote.sh (remote helper)
        +-- Hetzner SSH execution
        +-- Result retrieval
```

## Usage Workflows

### Workflow 1: Quick Local Test

```bash
# Start server
loom serve

# Run quick test (2 min)
PYTHONPATH=src python3 scripts/load_test.py --quick

# View results
python3 scripts/analyze_load_test.py /opt/research-toolbox/tmp/load_test_results.json
```

### Workflow 2: Baseline & Comparison

```bash
# Save baseline
PYTHONPATH=src python3 scripts/load_test.py --output baseline.json

# Make changes...

# Test changes
PYTHONPATH=src python3 scripts/load_test.py --output current.json

# Compare
python3 scripts/analyze_load_test.py baseline.json current.json
```

### Workflow 3: Remote Testing (Hetzner)

```bash
# Run on Hetzner with automatic retrieval
./scripts/run_load_test_remote.sh

# Quick remote test
./scripts/run_load_test_remote.sh --quick
```

### Workflow 4: CI/CD Integration

```bash
# In GitHub Actions or pre-push hook
PYTHONPATH=src python3 scripts/load_test.py --quick

# Check result
STATUS=$(jq -r '.overall_status' /opt/research-toolbox/tmp/load_test_results.json)
if [ "$STATUS" != "PASS" ]; then exit 1; fi
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused | Start server: `loom serve` |
| Timeouts | Use `--quick` flag |
| OOM on Mac | Run on Hetzner (128GB) |
| Slow throughput | Check API keys, server logs |

See [LOAD_TEST_README.md](scripts/LOAD_TEST_README.md) for full troubleshooting guide.

## Expected Output

**Console:**
```
[TEST 1] Concurrent Sessions... Result: PASS (100.0% success)
[TEST 2] Throughput... Result: PASS (47.82 req/s, 100.0% success)
[TEST 3] Heavy Tools... Result: PASS (94.6% success, avg 312ms)
[TEST 4] Sustained Load... Result: PASS (9.95 actual req/s, 99.2% success)
[TEST 5] Large Payloads... Result: PASS (95.2% success)

Overall Status: PASS
Summary: {'passed': 5, 'warned': 0, 'failed': 0}
```

**JSON Report:**
Located at `/opt/research-toolbox/tmp/load_test_results.json`

Includes:
- Timestamp
- Overall status
- Per-test metrics (success rate, throughput, latencies)
- Summary counts (PASS/WARN/FAIL)

## File Locations

**Scripts:**
- `/Users/aadel/projects/loom/scripts/load_test.py`
- `/Users/aadel/projects/loom/scripts/analyze_load_test.py`
- `/Users/aadel/projects/loom/scripts/run_load_test_remote.sh`

**Documentation:**
- `/Users/aadel/projects/loom/scripts/LOAD_TEST_README.md`
- `/Users/aadel/projects/loom/scripts/LOAD_TEST_QUICKSTART.md`
- `/Users/aadel/projects/loom/LOAD_TEST_IMPLEMENTATION.md`
- `/Users/aadel/projects/loom/LOAD_TEST_EXAMPLE_OUTPUT.md`
- `/Users/aadel/projects/loom/LOAD_TEST_INDEX.md` (this file)

**Output:**
- `/opt/research-toolbox/tmp/load_test_results.json` (default)

## Next Steps

1. **Read:** [Quick Start Guide](scripts/LOAD_TEST_QUICKSTART.md)
2. **Run:** `PYTHONPATH=src python3 scripts/load_test.py --quick`
3. **Analyze:** `python3 scripts/analyze_load_test.py load_test_results.json`
4. **Learn:** [Full Reference](scripts/LOAD_TEST_README.md)
5. **Integrate:** Add to CI/CD pipeline

## Support

- **Quick issues?** See [Troubleshooting](scripts/LOAD_TEST_README.md#troubleshooting)
- **Need examples?** See [Example Output](LOAD_TEST_EXAMPLE_OUTPUT.md)
- **Technical details?** See [Implementation](LOAD_TEST_IMPLEMENTATION.md)

## Summary

A production-ready load testing suite with:
- 5 comprehensive test categories
- Async HTTP client with proper error handling
- Detailed metrics collection and analysis
- JSON reporting for automation
- Full documentation with examples
- No additional external dependencies

Ready to stress-test the Loom MCP server!
