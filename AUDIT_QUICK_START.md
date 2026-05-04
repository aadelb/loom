# Audit Logging - Quick Start Guide

## Enable Audit Logging

### 1. Set Required Environment Variables

```bash
# Generate a secure HMAC signing key
export LOOM_AUDIT_SECRET="$(openssl rand -hex 32)"

# Set client/user identifier (optional, defaults to LOOM_USER_ID)
export LOOM_CLIENT_ID="user_123"

# Optional: Configure custom audit directory
export LOOM_AUDIT_DIR="$HOME/.loom/audit"

# Optional: Configure centralized JSON log
export LOOM_AUDIT_LOG_PATH="/var/log/loom/audit.jsonl"
```

### 2. Verify Audit Directory

```bash
# Create and secure audit directory
mkdir -p ~/.loom/audit
chmod 700 ~/.loom/audit

# For centralized logging
sudo mkdir -p /var/log/loom
sudo chmod 755 /var/log/loom
```

### 3. Start the Loom Server

```bash
# With audit logging enabled
LOOM_AUDIT_SECRET="$(openssl rand -hex 32)" loom serve
```

## Query Audit Logs

### Via MCP Client

```python
import asyncio
from loom.tools.audit_query import research_audit_query, research_audit_stats

async def demo():
    # Query last 24 hours of fetch tool calls
    result = await research_audit_query(
        tool_name="research_fetch",
        hours=24,
        limit=100
    )
    print(f"Found {result['count']} audit entries")
    for entry in result['entries']:
        print(f"  {entry['timestamp']}: {entry['tool_name']} - {entry['status']}")

    # Get statistics
    stats = await research_audit_stats(hours=24)
    print(f"\nStatistics for last 24 hours:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Successful: {stats['successful_calls']}")
    print(f"  Failed: {stats['failed_calls']}")
    print(f"  Avg duration: {stats['avg_duration_ms']:.0f}ms")
    print(f"  Top tools: {stats['top_tools']}")

asyncio.run(demo())
```

### Via Loom CLI

```bash
# Query audit entries
loom audit-query --tool research_fetch --hours 24 --limit 100

# Get audit statistics
loom audit-stats --hours 24
```

### Via REST API

```bash
# Query entries
curl -X POST http://localhost:8787/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "research_audit_query",
    "params": {
      "tool_name": "research_fetch",
      "hours": 24,
      "limit": 100
    }
  }'

# Get statistics
curl -X POST http://localhost:8787/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "research_audit_stats",
    "params": {"hours": 24}
  }'
```

## Audit Entry Format

Each audit entry contains:

```json
{
  "client_id": "user_123",
  "tool_name": "research_fetch",
  "params_summary": {
    "url": "https://example.com",
    "timeout": 30
  },
  "timestamp": "2026-05-04T10:30:45.123Z",
  "duration_ms": 1250,
  "status": "success",
  "signature": "a1b2c3d4e5f6..."
}
```

### Status Values
- `started`: Tool call initiated
- `success`: Completed successfully
- `error`: Generic error occurred
- `timeout`: Execution timeout

### PII Handling
Parameters are automatically scrubbed to remove:
- Email addresses
- Phone numbers
- IP addresses
- Credit card numbers
- API keys (marked `***REDACTED***`)

## Verify Audit Integrity

```python
from loom.audit import verify_integrity
from pathlib import Path

# Check a specific audit file
result = verify_integrity(Path("~/.loom/audit/2026-05-04.jsonl"))
print(f"Valid signatures: {result.valid}")
print(f"Invalid signatures: {result.invalid}")
print(f"Tampered: {result.tampered}")
```

## Export Audit Logs

```python
from loom.audit import export_audit
from pathlib import Path

# Export as JSON
export_result = export_audit(
    start_date="2026-05-01",
    end_date="2026-05-04",
    format="json"
)
print(f"Exported {export_result['count']} entries")

# Export as CSV
export_result = export_audit(
    start_date="2026-05-01",
    end_date="2026-05-04",
    format="csv"
)
# Write to file
with open("audit_export.csv", "w") as f:
    f.write(export_result['data'])
```

## Compliance Reporting

### Monthly Report

```python
import asyncio
from datetime import datetime, timedelta
from loom.tools.audit_query import research_audit_stats

async def monthly_report():
    # Get stats for last 30 days
    stats = await research_audit_stats(hours=24*30)
    
    print("=== Monthly Compliance Report ===")
    print(f"Period: Last 30 days (as of {stats['timestamp']})")
    print(f"\nCall Summary:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Successful: {stats['successful_calls']}")
    print(f"  Failed: {stats['failed_calls']}")
    print(f"  Error rate: {stats['failed_calls'] / max(1, stats['total_calls']) * 100:.1f}%")
    print(f"\nPerformance Metrics:")
    print(f"  Avg duration: {stats['avg_duration_ms']:.0f}ms")
    print(f"  Min duration: {stats['min_duration_ms']}ms")
    print(f"  Max duration: {stats['max_duration_ms']}ms")
    print(f"\nCost Summary:")
    print(f"  Total credits used: {stats['total_cost_credits']}")
    print(f"\nTop Tools (by usage):")
    for tool, count in list(stats['top_tools'].items())[:5]:
        print(f"  {tool}: {count} calls")

asyncio.run(monthly_report())
```

## Troubleshooting

### No audit entries appear

1. Check LOOM_AUDIT_SECRET is set:
```bash
echo $LOOM_AUDIT_SECRET
```

2. Verify audit directory exists and is writable:
```bash
ls -la ~/.loom/audit/
# Should show owner rwx (700) permissions
```

3. Check recent audit files:
```bash
ls -la ~/.loom/audit/*.jsonl
# Should show files from today with content
```

### "Insufficient permissions" error

For centralized logging to `/var/log/loom/`:

```bash
sudo mkdir -p /var/log/loom
sudo chmod 755 /var/log/loom
sudo touch /var/log/loom/audit.jsonl
sudo chmod 666 /var/log/loom/audit.jsonl
```

Or use home directory instead:
```bash
export LOOM_AUDIT_LOG_PATH="$HOME/.loom/audit.jsonl"
```

### Audit files are empty

Check if tool calls are actually being made:

```bash
# Monitor real-time audit entries
tail -f ~/.loom/audit/$(date +%Y-%m-%d).jsonl
```

## Performance Notes

- Audit logging adds ~5-10ms overhead per tool call
- Minimal impact for tools with >100ms execution time
- File I/O is synchronous but batched by OS
- Daily files prevent unbounded growth

## Storage Requirements

Typical storage usage:
- ~1KB per audit entry
- ~500MB per million entries
- ~15GB per 30 days (high-volume deployment)

Example cleanup:
```bash
# Delete audit files older than 90 days
find ~/.loom/audit -name "*.jsonl" -mtime +90 -delete
```

## Security Best Practices

1. **Rotate LOOM_AUDIT_SECRET regularly**:
```bash
# Generate new secret
NEW_SECRET=$(openssl rand -hex 32)
export LOOM_AUDIT_SECRET="$NEW_SECRET"
```

2. **Restrict audit directory permissions**:
```bash
chmod 700 ~/.loom/audit
```

3. **Monitor audit file modifications**:
```bash
# Watch for tampering
watch -n 5 'ls -la ~/.loom/audit/*.jsonl | tail -5'
```

4. **Verify signatures before compliance review**:
```bash
from loom.audit import verify_integrity
result = verify_integrity(Path("~/.loom/audit/2026-05-04.jsonl"))
assert not result.tampered, "Audit log tampering detected!"
```

## For More Information

See `/Users/aadel/projects/loom/AUDIT_IMPLEMENTATION.md` for:
- Architecture details
- Configuration options
- Security considerations
- Testing procedures
- Troubleshooting guide
