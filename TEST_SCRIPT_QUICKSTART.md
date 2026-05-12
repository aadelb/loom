# Loom Comprehensive Tools Test Script - Quick Start

## What Is This?
A Python script that **automatically discovers and tests ALL 881+ tools** registered in Loom, with sensible default parameters for each tool.

## Where Is It?
- **Source:** `/Users/aadel/projects/loom/test_all_tools.py` (Mac)
- **Deployed:** `/opt/research-toolbox/test_all_tools.py` (Hetzner)

## How To Run?

**On Hetzner ONLY** (not Mac — 24GB RAM constraint):

```bash
# Quick run
python3 /opt/research-toolbox/test_all_tools.py

# With 30-minute timeout
timeout 1800 python3 /opt/research-toolbox/test_all_tools.py

# In background
nohup timeout 1800 python3 /opt/research-toolbox/test_all_tools.py > /var/log/loom_test.log 2>&1 &

# Monitor progress
tail -f /var/log/loom_test.log
```

## What Does It Do?

1. **Discovers** all functions in `src/loom/tools/` starting with `research_` or `tool_`
2. **Generates** sensible default parameters for each function
3. **Tests** each function with a 30-second timeout
4. **Categorizes** results as: OK, FAIL, TIMEOUT, or SKIP
5. **Reports** findings in console + JSON format

## Expected Output

### Console
```
================================================================================
LOOM COMPREHENSIVE TOOL TEST REPORT
================================================================================

Test Duration: 1234.5s
Start Time: 2026-05-06T16:41:23.000000+00:00
End Time: 2026-05-06T16:41:45.000000+00:00

SUMMARY
────────────────────────────────────────────────────────────────────────────────
Total Tools Found:     881
Total Tested:          750
Total Skipped:         131

Results:
  OK:                  650 (73.8%)
  FAILED:              45
  TIMEOUT:             55

Pass Rate:             73.8% (650/881)
Tested Rate:           85.1%

BY MODULE
────────────────────────────────────────────────────────────────────────────────
fetch                          | Found:  5 | OK:   5 (100.0%) | Failed:  0 | ...
search                         | Found:  3 | OK:   3 (100.0%) | Failed:  0 | ...
...
```

### JSON Report
File: `/opt/research-toolbox/full_tool_test_report.json`

```json
{
  "metadata": {
    "total_tools_found": 881,
    "total_tested": 750,
    "total_ok": 650,
    "total_failed": 45,
    "total_timeout": 55,
    "pass_rate_percent": 73.8,
    "duration_sec": 1234.5
  },
  "by_module": { ... },
  "failures": [ ... ],
  "timeouts": [ ... ],
  "skipped": [ ... ]
}
```

## Expected Results
- **81-95% pass rate** (700-800 of 881 tools)
- **5-10% failures** (network, missing API keys)
- **5-10% timeouts** (slow operations)
- **10-15% skipped** (require file paths)

## Key Features

✓ **Automatic Discovery** — No hardcoding tool names  
✓ **Smart Defaults** — Parameter generation based on names/types  
✓ **Async/Sync** — Handles both async and sync functions  
✓ **Error Resilience** — Continues testing on failures  
✓ **Progress Tracking** — Reports every 10 tools  
✓ **Comprehensive Reports** — Console + JSON output  

## Configuration

Edit these constants in the script to adjust:

```python
TOOL_TIMEOUT_SECS = 30       # Timeout per tool
TOTAL_TIMEOUT_SECS = 1800    # 30 minutes total
PROGRESS_INTERVAL = 10        # Progress report frequency
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Script hangs** | Use `timeout 1800` wrapper or `pkill -f test_all_tools` |
| **Many failures** | Check `.env` file, verify API keys in `/opt/research-toolbox/.env` |
| **Many timeouts** | Increase `TOOL_TIMEOUT_SECS` or check network connectivity |
| **Import errors** | Ensure Loom is installed: `pip install -e /opt/research-toolbox/src` |
| **No tools found** | Check that `src/loom/tools/` directory exists |

## Smart Parameter Mapping

The script maps parameter names to sensible defaults:

| Parameter Name | Default Value |
|---|---|
| `url`, `uri`, `link` | `"https://example.com"` |
| `query`, `prompt`, `text`, `search` | `"how to build wealth in 2026"` |
| `domain`, `hostname` | `"example.com"` |
| `provider` | `"exa"` |
| `model` | `"auto"` |
| `strategy` | `"ethical_anchor"` |
| `darkness_level` | `5` |
| `spectrum` | `True` |
| `target_lang` | `"ar"` |
| `dry_run` | `True` |
| Any other string param | `"test input"` |
| Any other int param | `5` |
| Any other bool param | `True` |
| Any other list param | `[]` |
| Any other dict param | `{}` |

## After Running

1. **Review report:** `cat /opt/research-toolbox/full_tool_test_report.json | jq .`
2. **Check failures:** Look for patterns in error messages
3. **Add missing keys:** Update `/opt/research-toolbox/.env` if needed
4. **Re-run:** Test again to verify fixes

## Scheduling

Run daily to detect regressions:

```bash
# Add to crontab
0 2 * * * timeout 1800 python3 /opt/research-toolbox/test_all_tools.py \
  >> /var/log/loom_health_check.log 2>&1
```

## Support

For issues, check:
- Script syntax: `python3 -m py_compile test_all_tools.py`
- Loom import: `python3 -c "import loom; print(loom.__file__)"`
- Environment: `test -f /opt/research-toolbox/.env && echo OK`
- Logs: `/var/log/loom_health_check.log`

---

**Created:** 2026-05-06  
**Updated:** 2026-05-06  
**Tools Tested:** 881+  
**Status:** Ready to Run
