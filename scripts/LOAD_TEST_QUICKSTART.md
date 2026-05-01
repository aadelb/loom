# Loom Load Test Quick Start

## 30-Second Setup

### 1. Start the Server
```bash
cd /Users/aadel/projects/loom
loom serve  # Or: python3 -m loom.server
```

### 2. Run Load Test (Terminal 2)
```bash
cd /Users/aadel/projects/loom
PYTHONPATH=src python3 scripts/load_test.py --quick
```

### 3. View Results
```bash
python3 scripts/analyze_load_test.py /opt/research-toolbox/tmp/load_test_results.json
```

## One-Command Tests

### Quick Local Test (2 min)
```bash
PYTHONPATH=src python3 scripts/load_test.py --quick
```

### Full Local Test (10 min)
```bash
PYTHONPATH=src python3 scripts/load_test.py
```

### On Hetzner (Remote)
```bash
./scripts/run_load_test_remote.sh
```

### Quick Hetzner Test
```bash
./scripts/run_load_test_remote.sh --quick
```

## Understanding Output

### Real-time Progress
```
[TEST 1] Concurrent Sessions...
  Testing 10 concurrent sessions...
    10 sessions: 10 successful
  ...
  Result: PASS (98.3% success)

[TEST 2] Throughput (Rapid Requests)...
  ...
  Result: PASS (50.23 req/s, 100.0% success)
```

### Final Results
```json
{
  "overall_status": "PASS",
  "summary": {
    "passed": 5,
    "warned": 0,
    "failed": 0
  }
}
```

### PASS = All tests passed ✓
### WARN = Some tests marginal ⚠
### FAIL = Tests failed ✗

## Comparing Performance

### Save Baseline
```bash
PYTHONPATH=src python3 scripts/load_test.py --output baseline.json
```

### Test Changes
```bash
# Make your changes...
PYTHONPATH=src python3 scripts/load_test.py --output current.json
```

### Compare
```bash
python3 scripts/analyze_load_test.py baseline.json current.json
```

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `Connection refused` | Start server: `loom serve` |
| `MemoryError` | Run on Hetzner with `--quick` |
| `Timeouts` | Use `--quick` flag |
| `Slow throughput` | Check API keys: `echo $GROQ_API_KEY` |

## Files Reference

| File | Purpose |
|------|---------|
| `load_test.py` | Main load test runner |
| `analyze_load_test.py` | Analyze and compare results |
| `run_load_test_remote.sh` | Run on Hetzner |
| `LOAD_TEST_README.md` | Full documentation |
| `LOAD_TEST_IMPLEMENTATION.md` | Technical details |

## Success Indicators

✓ **Good Results (PASS)**
- All 5 tests: PASS status
- Success rates: ≥95%
- Throughput: ≥10 req/s
- Latencies stable

⚠ **Warning Results (WARN)**
- 1-2 tests: WARN status
- Success rates: 80-95%
- Throughput: 5-10 req/s
- Latencies increasing

✗ **Bad Results (FAIL)**
- 1+ tests: FAIL status
- Success rates: <80%
- Frequent timeouts/errors

## Next Steps

1. **Run quick test**: `PYTHONPATH=src python3 scripts/load_test.py --quick`
2. **View results**: `python3 scripts/analyze_load_test.py load_test_results.json`
3. **Run full test**: `PYTHONPATH=src python3 scripts/load_test.py`
4. **Save baseline**: Keep first full run for comparison
5. **Track over time**: Run before/after major changes

## Example Output

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
  Result: PASS (45.67 req/s, 100.0% success)

[TEST 3] Heavy Tools (Resource-Intensive)...
  Result: PASS (92.3% success, avg 234ms)

[TEST 4] Sustained Load...
  Result: PASS (9.87 actual req/s, 99.2% success, avg latency 156ms)

[TEST 5] Large Payloads...
  Result: PASS (100.0% success)

Results saved to: /opt/research-toolbox/tmp/load_test_results.json
Overall Status: PASS
Summary: {'passed': 5, 'warned': 0, 'failed': 0}
```

## Documentation

- **Full Docs:** `scripts/LOAD_TEST_README.md`
- **Implementation:** `LOAD_TEST_IMPLEMENTATION.md`
- **This Guide:** `scripts/LOAD_TEST_QUICKSTART.md`
