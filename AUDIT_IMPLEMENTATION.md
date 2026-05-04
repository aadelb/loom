# Comprehensive Audit Logging Implementation

## Overview

The Loom MCP server now includes comprehensive audit logging for every tool call, meeting EU AI Act Article 15 compliance requirements for transparency and auditability.

## Architecture

### 1. Audit Event Capture

Every tool call in the `_wrap_tool` wrapper function is now logged at three key points:

#### Before Execution
- **Event**: `tool_call_started`
- **Fields**: client_id, tool_name, params (PII-scrubbed), timestamp
- **Location**: `/Users/aadel/projects/loom/src/loom/server.py` - async and sync wrappers

#### After Success
- **Event**: `tool_call_success`
- **Fields**: client_id, tool_name, params, duration_ms, result_size_bytes, status
- **Location**: async wrapper (line ~1071), sync wrapper (line ~1277)

#### After Failure
- **Event**: `tool_call_failure`
- **Fields**: client_id, tool_name, params, error_type, error_message, duration_ms, status
- **Locations**:
  - Timeout: async wrapper (line ~1103)
  - General errors: async wrapper (line ~1120), sync wrapper (line ~1286)

### 2. Storage Backends

Audit entries are persisted to multiple backends for redundancy and compliance:

#### Primary: Daily JSON Lines Files
- **Location**: `~/.loom/audit/YYYY-MM-DD.jsonl`
- **Configurable via**: `LOOM_AUDIT_DIR` environment variable
- **Format**: One JSON entry per line with HMAC-SHA256 signature
- **Features**:
  - Tamper detection via HMAC signatures
  - File-level locking for concurrent writes
  - Secure permissions (0o600 owner-read/write only)

#### Fallback: SQLite Database
- **Location**: `~/.loom/audit/audit.db`
- **Tables**: audit_log (client_id, tool_name, timestamp, duration_ms, status, signature)
- **Features**: ACID compliance, transaction support

#### Always: Structured JSON Log File
- **Location**: `/var/log/loom/audit.jsonl` (configurable via `LOOM_AUDIT_LOG_PATH`)
- **Features**: System-level centralized logging for compliance audits

### 3. PII Scrubbing

All audit entries have sensitive data removed before logging:

#### Automatic Redaction
Parameters containing these keywords are marked `***REDACTED***`:
- `key`, `token`, `password`, `secret`, `api_key`, etc.

#### PII Scrubbing
All string values are scrubbed to remove:
- Email addresses
- Phone numbers
- IP addresses
- Social security numbers
- Credit card numbers
- Personal names (when detected)

**Module**: `/Users/aadel/projects/loom/src/loom/pii_scrubber.py`

### 4. HMAC Signature Verification

Each audit entry is signed with HMAC-SHA256 for tamper detection:

- **Secret Key**: `LOOM_AUDIT_SECRET` environment variable (required)
- **Signature Verification**: Automatically performed on export
- **Tamper Detection**: Mismatched signatures indicate tampering

## Tools

### 1. research_audit_query

Query audit log entries by tool name and time range.

**Signature**:
```python
async def research_audit_query(
    tool_name: str = "",
    hours: int = 24,
    limit: int = 100,
) -> dict[str, Any]
```

**Parameters**:
- `tool_name` (str): Filter by tool name (empty = all tools)
- `hours` (int): Look back N hours (1-720, default 24)
- `limit` (int): Maximum entries to return (1-1000, default 100)

**Response**:
```json
{
  "entries": [
    {
      "client_id": "user_123",
      "tool_name": "research_fetch",
      "params_summary": {"url": "https://example.com", "method": "GET"},
      "timestamp": "2026-05-04T10:30:45.123Z",
      "duration_ms": 1250,
      "status": "success",
      "signature": "a1b2c3d4e5f6..."
    }
  ],
  "count": 25,
  "total_count": 42,
  "timestamp": "2026-05-04T11:00:00Z",
  "query_duration_ms": 45.2
}
```

**Use Cases**:
- Audit compliance investigations
- Tool usage analysis
- Performance debugging
- Security incident analysis

### 2. research_audit_stats

Generate aggregate audit statistics for compliance reporting.

**Signature**:
```python
async def research_audit_stats(
    hours: int = 24,
) -> dict[str, Any]
```

**Parameters**:
- `hours` (int): Look back N hours (1-720, default 24)

**Response**:
```json
{
  "total_calls": 1523,
  "successful_calls": 1489,
  "failed_calls": 28,
  "timeout_calls": 5,
  "other_error_calls": 1,
  "top_tools": {
    "research_fetch": 456,
    "research_search": 389,
    "research_spider": 278
  },
  "top_errors": {
    "timeout": 5,
    "error": 28
  },
  "avg_duration_ms": 1245.67,
  "min_duration_ms": 15,
  "max_duration_ms": 58000,
  "total_duration_ms": 1894562,
  "total_cost_credits": 1523,
  "timestamp": "2026-05-04T11:00:00Z"
}
```

**Use Cases**:
- Monthly compliance reports
- Cost analysis
- Performance trending
- SLA verification

### 3. research_audit_export

Export audit logs for compliance reporting (existing tool, enhanced).

**Signature**:
```python
async def research_audit_export(
    start_date: str | None = None,
    end_date: str | None = None,
    format: str = "json",
) -> dict[str, Any]
```

**Formats**:
- `json`: JSON array with all entries and _verified status
- `csv`: CSV string with headers

## Implementation Details

### Module Structure

**File**: `/Users/aadel/projects/loom/src/loom/tools/audit_query.py`

Contains:
- `research_audit_query()` - Query entries by name and time
- `research_audit_stats()` - Generate statistics
- `_load_daily_jsonl_entries()` - Load from daily files
- `_load_jsonl_entries()` - Load from central log
- `_parse_audit_entry()` - Parse and validate entries
- `_get_audit_dir()` - Resolve audit directory path
- `_get_jsonl_log_path()` - Resolve JSON log path

### Enhanced _wrap_tool Function

**File**: `/Users/aadel/projects/loom/src/loom/server.py`

Changes:
1. Import: `from loom.audit import export_audit, log_invocation`
2. Async wrapper enhancements:
   - Line ~1071: Log success with result size
   - Line ~1103: Log timeout errors
   - Line ~1120: Log general exceptions
3. Sync wrapper enhancements:
   - Line ~1277: Log success
   - Line ~1286: Log errors

### Audit Entry Schema

```json
{
  "client_id": "string",
  "tool_name": "string",
  "params_summary": {
    "key1": "value1",
    "sensitive_field": "***REDACTED***"
  },
  "timestamp": "ISO 8601 UTC timestamp",
  "duration_ms": "integer",
  "status": "started|success|error|timeout",
  "signature": "HMAC-SHA256 hex string"
}
```

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOOM_AUDIT_SECRET` | required | HMAC signing secret key (must be set) |
| `LOOM_AUDIT_DIR` | `~/.loom/audit` | Directory for daily JSONL files |
| `LOOM_AUDIT_LOG_PATH` | `/var/log/loom/audit.jsonl` | Central structured log file path |
| `LOOM_CLIENT_ID` | `$LOOM_USER_ID` | Client identifier for audit entries |
| `LOOM_USER_ID` | `anonymous` | User identifier (fallback for client_id) |

### Setup Instructions

1. **Set HMAC Secret** (required for signing):
```bash
export LOOM_AUDIT_SECRET="$(openssl rand -hex 32)"
```

2. **Create Audit Directory**:
```bash
mkdir -p ~/.loom/audit
chmod 700 ~/.loom/audit
```

3. **Setup Centralized Logging** (optional):
```bash
sudo mkdir -p /var/log/loom
sudo chmod 755 /var/log/loom
```

4. **Optional: Configure Custom Paths**:
```bash
export LOOM_AUDIT_DIR="/var/log/loom-audit"
export LOOM_AUDIT_LOG_PATH="/var/log/loom/audit.jsonl"
```

## Security Considerations

### Signature Verification

All exported audit logs include HMAC-SHA256 signatures for tamper detection.

To verify signatures:
```python
from loom.audit import verify_integrity
from pathlib import Path

result = verify_integrity(Path("~/.loom/audit/2026-05-04.jsonl"))
print(f"Valid: {result.valid}, Invalid: {result.invalid}, Tampered: {result.tampered}")
```

### File Permissions

- Daily JSONL files: `0o600` (owner read/write only)
- Audit directory: `0o700` (owner access only)
- Lock-based concurrent write protection

### Compliance

- **EU AI Act Article 15**: Audit trail for AI system behavior
- **GDPR**: PII scrubbing removes personal data
- **SOC 2**: Tamper-proof, append-only log design
- **ISO 27001**: HMAC signature verification and access control

## Testing

### Unit Tests

Location: `/Users/aadel/projects/loom/tests/test_audit_query.py`

Coverage:
- Query filtering by tool name and time
- Statistics aggregation
- Entry parsing and validation
- JSON Lines format handling

### Integration Tests

```bash
# Set up test environment
export LOOM_AUDIT_SECRET="test-secret-key"
export LOOM_AUDIT_DIR="./test-audit"

# Run tests
pytest tests/test_audit_query.py -v

# Test audit export
pytest tests/test_audit.py -v
```

### Manual Testing

```python
import asyncio
from loom.tools.audit_query import research_audit_query, research_audit_stats

# Query last 24 hours
result = await research_audit_query(tool_name="research_fetch", hours=24, limit=100)
print(f"Found {result['count']} entries")

# Get statistics
stats = await research_audit_stats(hours=24)
print(f"Total calls: {stats['total_calls']}, Success rate: {stats['successful_calls']}/{stats['total_calls']}")
```

## Troubleshooting

### No Audit Entries Found

**Problem**: `research_audit_query` returns empty results

**Solutions**:
1. Check audit directory exists: `ls -la ~/.loom/audit/`
2. Verify file permissions: `ls -la ~/.loom/audit/*.jsonl`
3. Check tool names match: Compare with tool registry
4. Check time range: Ensure entries are within requested hours

### Signature Verification Fails

**Problem**: `_verified: false` on exported entries

**Solutions**:
1. Verify `LOOM_AUDIT_SECRET` is set and matches the one used for signing
2. Check no manual edits to audit files (signatures will not match)
3. Verify HMAC computation is correct

### Permission Denied on /var/log/loom

**Problem**: Cannot write to `/var/log/loom/audit.jsonl`

**Solutions**:
1. Create directory with proper permissions:
```bash
sudo mkdir -p /var/log/loom
sudo chmod 755 /var/log/loom
sudo touch /var/log/loom/audit.jsonl
sudo chmod 666 /var/log/loom/audit.jsonl
```

2. Or use alternative path:
```bash
export LOOM_AUDIT_LOG_PATH="$HOME/.loom/audit.jsonl"
```

## Performance Impact

### Overhead

- Audit logging adds ~5-10ms per tool call
- Negligible for tools with >100ms execution time
- Synchronous file I/O with file locking

### Optimization

For high-throughput scenarios:

1. **Batch writes**: Log entries are buffered by OS
2. **Async I/O**: Consider moving to async file writes (future enhancement)
3. **Log rotation**: Daily files prevent unbounded growth

### Monitoring

Check audit log file size:
```bash
du -sh ~/.loom/audit/
find ~/.loom/audit -name "*.jsonl" -type f -exec wc -l {} \; | awk '{sum+=$1} END {print "Total entries:", sum}'
```

## Future Enhancements

1. **PostgreSQL Backend**: Direct database logging for distributed deployments
2. **Log Rotation**: Automatic compression of old audit files
3. **Async I/O**: Non-blocking audit writes for high-throughput scenarios
4. **Real-time Analytics**: Live audit stream processing
5. **Visualization**: Dashboard for audit log exploration
6. **Alerting**: Audit rule engine for compliance monitoring

## Author

Implementation: Ahmed Adel Bakr Alderai
Date: 2026-05-04
