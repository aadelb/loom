# Real Query Test Script

Comprehensive test suite for all Loom MCP tools using realistic Dubai wealth-building queries.

## Overview

This script (`real_query_test.py`) tests ALL Loom MCP tools by:

1. **Connecting to MCP Server**: Connects via streamable-http to `http://127.0.0.1:8787/mcp`
2. **Discovering Tools**: Lists all available tools and their parameter schemas
3. **Generating Smart Parameters**: For each tool, generates realistic Dubai-related parameters based on its schema:
   - URLs → Dubai business sites (khaleejtimes.com, gulfnews.com, invest.dubai.ae)
   - Queries → Dubai wealth queries ("free zone business setup", "golden visa investment", etc.)
   - Domains → Dubai domains (dubaichamber.ae, dubailand.gov.ae, etc.)
   - Integers → Appropriate values per param purpose
   - Enums → First valid value from enum constraint
4. **Running Tests**: Executes tools with 10 concurrent operations
5. **Reporting**: Generates JSON report with success/failure/timing data

## Prerequisites

- Loom MCP server running at `http://127.0.0.1:8787`
- Python 3.11+ with httpx installed

## Usage

### Basic Run

```bash
# On Hetzner (remote)
cd /Users/aadel/projects/loom
python3 scripts/real_query_test.py
```

### Output

The script produces:

1. **Console Output**: Real-time progress with tool status, timing, and response size
2. **JSON Report**: `./real_query_test_report.json` containing:
   - Timestamp
   - Summary (total, OK, ERROR, TIMEOUT, SKIP counts)
   - Per-tool results with:
     - Tool name
     - Status (OK/ERROR/TIMEOUT/SKIP)
     - Response size in bytes
     - Timing in milliseconds
     - Error details (if any)
     - Response sample (first 500 chars)

## Parameter Generation Strategy

The script intelligently generates parameters without hardcoding tool-specific logic:

### By Parameter Type

| Type | Generated Value |
|------|-----------------|
| `string` (url) | `https://www.khaleejtimes.com/business` |
| `string` (domain) | `khaleejtimes.com` |
| `string` (query) | `Dubai free zone business setup 2026` |
| `string` (email) | `investor@example.com` |
| `string` (username) | `dubai_investor_2026` |
| `string` (enum) | First enum value |
| `integer` (n/limit) | `10` |
| `integer` (timeout) | `30` |
| `integer` (max_chars) | `5000` |
| `boolean` | `false` |
| `array` (urls) | `["https://khaleejtimes.com", "https://gulfnews.com"]` |
| `array` (domains) | `["khaleejtimes.com", "gulfnews.com"]` |
| `object` (headers) | `{"User-Agent": "Mozilla/5.0"}` |

### Smart Heuristics

- Examines parameter name and description
- Uses enum constraints when available
- Picks appropriate defaults for each tool type
- Skips tools requiring unavailable API keys (Stripe, VastAI, email, etc.)

## Timeouts

Tools are categorized by type:

- **Long-running** (deep research, benchmarks, spiders, markdown, dynamic): 120s
- **Medium** (search, fetch, scrape): 60s
- **Fast** (default): 30s

Network overhead adds 5s to all timeouts.

## Example Report

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
      "response_sample": "{\"url\": \"https://www.khaleejtimes.com/business\", \"status_code\": 200, ...}"
    },
    {
      "tool_name": "research_search",
      "status": "OK",
      "response_size": 4231,
      "error_detail": null,
      "time_ms": 1250,
      "response_sample": "{\"provider\": \"exa\", \"query\": \"Dubai free zone business setup 2026\", \"results\": [...]}"
    },
    ...
  ]
}
```

## Troubleshooting

### Connection Refused

Ensure Loom MCP server is running:
```bash
# On Hetzner
loom serve
# or
python3 -m loom.server
```

### Tools Are Timing Out

- Increase timeout values in the script (edit `_get_timeout_for_tool()`)
- Check server resource usage
- Run with fewer concurrent tasks (reduce `max_concurrent` parameter)

### API Key Errors

Some tools require external API keys. The script automatically skips these:
- Stripe (billing tools)
- VastAI (GPU provider)
- Email/SMTP credentials
- Joplin token

### Memory Issues

If running on constrained system:
- Reduce `max_concurrent` parameter (default 10)
- Run on Hetzner with `ssh hetzner "cd /path && python3 scripts/real_query_test.py"`

## Extending the Script

### Add Custom Queries

Edit the `DUBAI_QUERIES` list at the top of the script:

```python
DUBAI_QUERIES = [
    "Your custom query 1",
    "Your custom query 2",
    ...
]
```

### Add Custom URLs

Edit the `DUBAI_URLS` list:

```python
DUBAI_URLS = [
    "https://your-domain.com",
    ...
]
```

### Modify Parameter Generation

Edit the `generate_smart_params()` function to add tool-specific heuristics:

```python
elif param_name == "my_custom_param":
    params[param_name] = "custom_value"
```

## Performance Notes

- Typical run: 2-5 minutes for ~150 tools
- Network-bound: Most time spent waiting for tool responses
- CPU-light: Script only generates parameters and aggregates results

## Integration with CI/CD

The script exits with:
- `0` if all tools succeeded or timed out is acceptable
- `1` if any tool errored or too many timeouts

Use in pipelines:
```bash
python3 scripts/real_query_test.py && echo "All tests passed"
```

## Author

Created for Loom MCP comprehensive tool validation.
