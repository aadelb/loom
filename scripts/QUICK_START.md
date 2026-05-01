# Quick Start: Real Query Test Suite

## 30-Second Overview

Test **all 150+ Loom MCP tools** with realistic Dubai wealth-building queries:

```bash
# On Hetzner (recommended)
ssh hetzner "cd /Users/aadel/projects/loom && python3 scripts/real_query_test.py"

# Or locally
python3 scripts/real_query_test.py
```

Expected output: JSON report with per-tool results (status, timing, errors).

## What It Does

1. **Connects to Loom MCP** server at `http://127.0.0.1:8787/mcp`
2. **Discovers all tools** via JSON-RPC `tools/list` method
3. **Generates smart parameters** based on tool schemas (no hardcoding)
4. **Executes tools** concurrently (max 10 at a time)
5. **Reports results** as JSON with success/failure/timing data

## Files

| File | Purpose |
|------|---------|
| `real_query_test.py` | Main test script (484 lines) |
| `run_real_query_test_remote.sh` | Execute on Hetzner via SSH |
| `analyze_test_report.py` | Analyze report & extract insights |
| `REAL_QUERY_TEST_README.md` | Full documentation |
| `QUICK_START.md` | This file |

## Usage Examples

### Test Locally

Requires Loom server running on `127.0.0.1:8787`:

```bash
cd /Users/aadel/projects/loom
loom serve &
python3 scripts/real_query_test.py
```

### Test on Hetzner (Recommended)

Simplest approach — handles SSH and server startup:

```bash
./scripts/run_real_query_test_remote.sh hetzner
```

This script will:
- Connect via SSH
- Check if Loom server is running (start if needed)
- Run the test
- Fetch report to `./test_reports/report_TIMESTAMP.json`

### Analyze Results

After test completes, analyze the report:

```bash
python3 scripts/analyze_test_report.py ./real_query_test_report.json
```

Output includes:
- Status breakdown (OK/ERROR/TIMEOUT/SKIP)
- Timing statistics (avg, min, max, median)
- Error details by type
- Top performers (fastest tools)
- Slowest successful tools
- Recommendations

## Sample Output

```
============================================
TEST SUMMARY
============================================
Total tools tested: 156
  OK:       142
  ERROR:      8
  TIMEOUT:    4
  SKIP:       2

Timing (OK tools only):
  Average: 1250ms
  Min:     50ms
  Max:     65000ms
```

## Smart Parameter Generation

The script intelligently generates parameters based on tool schemas:

### String Parameters

| Pattern | Value |
|---------|-------|
| `url` | `https://www.khaleejtimes.com/business` |
| `domain` | `khaleejtimes.com` |
| `query` | `Dubai free zone business setup 2026` |
| `email` | `investor@example.com` |
| `username` | `dubai_investor_2026` |
| `address` (crypto) | Bitcoin address |
| `enum` | First valid enum value |

### Numeric Parameters

| Name | Value |
|------|-------|
| `n`, `limit` | `10` |
| `timeout` | `30` |
| `max_chars` | `5000` |
| `retries` | `0` |

### Complex Parameters

| Type | Value |
|------|-------|
| `boolean` | `false` |
| `array` (urls) | 3 Dubai URLs |
| `object` (headers) | `{"User-Agent": "Mozilla/5.0"}` |

## Report Format

JSON report with structure:

```json
{
  "timestamp": "2026-05-02T14:30:45Z",
  "summary": {
    "total": 156,
    "ok": 142,
    "error": 8,
    "timeout": 4,
    "skip": 2
  },
  "tools": [
    {
      "tool_name": "research_fetch",
      "status": "OK",
      "response_size": 8542,
      "error_detail": null,
      "time_ms": 2341,
      "response_sample": "..."
    }
  ]
}
```

## Troubleshooting

### Connection Refused

```bash
# Check if server is running
curl -s http://127.0.0.1:8787/mcp -X POST \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Start server if needed
loom serve
```

### Tools Timing Out

- Run slower: Edit `max_concurrent=5` in script
- Increase timeouts: Edit `_get_timeout_for_tool()`
- Run on Hetzner: Better resources there

### API Key Errors

These tools are auto-skipped (no action needed):
- Stripe billing tools
- VastAI GPU provider
- Email/SMTP tools
- Joplin note tools

## Performance

- **Duration**: 2-5 minutes for ~150 tools
- **Network-bound**: Waiting for tool responses
- **Success rate**: 80-95% typical
- **Concurrent**: 10 tools at a time (configurable)

## Extending

### Add Custom Queries

Edit top of `real_query_test.py`:

```python
DUBAI_QUERIES = [
    "Your custom query 1",
    "Your custom query 2",
    ...
]
```

### Change Concurrency

In `main()` function:

```python
results = await test_all_tools(client, max_concurrent=5)
```

### Add Tool-Specific Logic

Edit `generate_smart_params()` function.

## FAQ

**Q: Why does it skip some tools?**
A: Tools requiring Stripe, VastAI, email, or Joplin keys are auto-skipped since test can't provide them.

**Q: Can I run this locally?**
A: Yes, but need Loom server running. Recommended to run on Hetzner where server is hosted.

**Q: How accurate are timing numbers?**
A: Timing includes network overhead, not just tool execution. Fast tools appear slow due to SSH latency.

**Q: Can I use different queries?**
A: Yes! Edit `DUBAI_QUERIES`, `DUBAI_URLS`, or `DUBAI_DOMAINS` lists.

**Q: What if a tool fails?**
A: Check error detail in report. Likely missing API key, network issue, or tool bug.

## Next Steps

1. Run the test: `./scripts/run_real_query_test_remote.sh hetzner`
2. Wait 3-5 minutes for completion
3. Analyze report: `python3 scripts/analyze_test_report.py ./real_query_test_report.json`
4. Review any errors and investigate failures
5. Extend with custom queries as needed

## Contact

Created for comprehensive Loom MCP tool validation.
