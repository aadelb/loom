# Quick Start: Loom Load Testing

## One-Minute Setup

```bash
# 1. Install Locust
pip install locust

# 2. Start Loom server (in terminal 1)
loom serve

# 3. Run load test (in terminal 2)
cd /Users/aadel/projects/loom
./tests/load/run_load_test.sh headless
```

## Common Commands

```bash
# Quick test: 10 users × 30 seconds
./tests/load/run_load_test.sh headless --quick

# Normal test: 50 users × 60 seconds
./tests/load/run_load_test.sh headless

# Sustained test: 50 users × 5 minutes
./tests/load/run_load_test.sh headless --sustained

# Stress test: 200 users × 2 minutes
./tests/load/run_load_test.sh headless --stress

# Interactive web UI (http://localhost:8089)
./tests/load/run_load_test.sh ui
```

## What Gets Tested

- **Health checks** (48%): Fast endpoint (expect <100ms)
- **Search** (24%): Multi-provider search (expect <5s)
- **Fetch** (14%): URL fetching (expect <10s)
- **Deep research** (9%): Heavy analysis (expect <30s)
- **Analytics** (5%): Dashboard queries (expect <2s)

## View Results

After test completes, check CSV outputs:

```bash
ls -lh tests/load/results/
# load_test_stats.csv          ← Main results
# load_test_stats_history.csv  ← Time series
# load_test_failures.csv       ← Errors only
```

Open in spreadsheet or parse with Python:

```python
import csv

with open('tests/load/results/load_test_stats.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['Name']
        fails = row['# fails']
        p95 = row['95%ile']
        print(f"{name:30} Failures: {fails:5} p95: {p95:8}ms")
```

## Performance Baseline

Expected on mid-range hardware:

| Endpoint | p50 | p95 | p99 | Target |
|----------|-----|-----|-----|--------|
| Health | 50ms | 100ms | 150ms | <100ms |
| Search | 2s | 4s | 5s | <5s |
| Fetch | 5s | 8s | 10s | <10s |
| Deep | 15s | 25s | 30s | <30s |
| Analytics | 800ms | 1.5s | 2s | <2s |

## Troubleshooting

**Server not running?**
```bash
curl http://localhost:8787/health
# Should return 200 OK
```

**Port already in use?**
```bash
lsof -i :8787
kill -9 <PID>
```

**Low throughput?**
- Check server logs: `tail -f ~/.loom/logs/server.log`
- Reduce users: `--quick` test mode
- Check CPU/memory: `top` or `htop`

## Full Documentation

See `README.md` for comprehensive guide including:
- Configuration details
- Understanding metrics
- Custom load profiles
- CI/CD integration
- Advanced usage
