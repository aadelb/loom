# Sherlock Username OSINT Integration

## Overview

Sherlock is a powerful open-source tool for searching usernames across 400+ social networks. This integration wraps Sherlock as a Loom MCP tool, enabling username OSINT lookups through the Loom platform.

## Files Created

### Core Implementation
- **`src/loom/tools/sherlock_backend.py`** (306 lines)
  - `research_sherlock_lookup(username, platforms=None, timeout=30)` - Single username lookup
  - `research_sherlock_batch(usernames, platforms=None, timeout=30)` - Batch username lookups
  - Helper functions for validation and availability checking

### Parameter Models
- **`src/loom/params.py`** (expanded)
  - `SherlockLookupParams` - Validation model for single lookups
  - `SherlockBatchParams` - Validation model for batch operations

### Server Registration
- **`src/loom/server.py`** (modified)
  - Added `sherlock_backend` import
  - Registered both tools with FastMCP

### Tests
- **`tests/test_tools/test_sherlock_backend.py`** (34 tests, 93% coverage)
  - Tests for validation helpers
  - Tests for single and batch lookups
  - Tests for subprocess integration and error handling
  
- **`tests/test_params_sherlock.py`** (29 tests)
  - Pydantic model validation tests
  - Boundary and security tests
  
- **`tests/test_sherlock_integration.py`** (10 tests)
  - End-to-end integration tests
  - Workflow tests combining params and functions

**Total: 73 tests, all passing**

## API Functions

### research_sherlock_lookup(username, platforms=None, timeout=30)

Search for a single username across social networks.

**Parameters:**
- `username` (str): Username to search (1-255 chars, alphanumeric + underscore/hyphen/period/plus)
- `platforms` (list[str], optional): Specific platforms to search (max 50)
- `timeout` (int): Timeout in seconds (1-300, default 30)

**Returns:**
```python
{
    "username": str,
    "found_on": [
        {
            "platform": str,
            "url": str,
            "user_id": str,
            "status_code": int
        }
    ],
    "total_found": int,
    "total_checked": int,
    "sherlock_available": bool,
    "error": str  # Optional, only if error occurred
}
```

### research_sherlock_batch(usernames, platforms=None, timeout=30)

Search for multiple usernames in batch.

**Parameters:**
- `usernames` (list[str]): Usernames to search (1-100 items)
- `platforms` (list[str], optional): Specific platforms to search (max 50)
- `timeout` (int): Timeout per lookup in seconds (1-300, default 30)

**Returns:**
```python
{
    "usernames_checked": int,
    "results": {
        "username1": {...},  # Same format as research_sherlock_lookup
        "username2": {...},
        ...
    },
    "total_accounts_found": int,  # Sum across all usernames
    "sherlock_available": bool,
    "error": str  # Optional, only if batch failed
}
```

## Installation

Sherlock CLI must be installed:
```bash
pip install sherlock-project
```

The tools gracefully handle missing Sherlock CLI and return appropriate error messages.

## Usage Examples

### Single Lookup
```python
from loom.tools.sherlock_backend import research_sherlock_lookup

result = research_sherlock_lookup(
    username="john_doe",
    platforms=["twitter", "github", "instagram"],
    timeout=45
)

for account in result["found_on"]:
    print(f"{account['platform']}: {account['url']}")
```

### Batch Lookup
```python
from loom.tools.sherlock_backend import research_sherlock_batch

result = research_sherlock_batch(
    usernames=["alice", "bob", "charlie"],
    platforms=["twitter", "instagram"]
)

print(f"Found {result['total_accounts_found']} accounts total")
for username, findings in result["results"].items():
    print(f"{username}: {findings['total_found']} accounts found")
```

### Via Pydantic Models (Type-Safe)
```python
from loom.params import SherlockLookupParams, SherlockBatchParams
from loom.tools.sherlock_backend import research_sherlock_lookup, research_sherlock_batch

# Single lookup with validation
params = SherlockLookupParams(
    username="john_doe",
    timeout=60
)
result = research_sherlock_lookup(params.username, params.platforms, params.timeout)

# Batch with validation
batch_params = SherlockBatchParams(
    usernames=["user1", "user2"],
    platforms=["twitter"]
)
result = research_sherlock_batch(batch_params.usernames, batch_params.platforms)
```

## Security & Validation

### Username Validation
- Must be 1-255 characters
- Allowed chars: alphanumeric, underscore (_), hyphen (-), period (.), plus (+)
- Automatically stripped of whitespace
- Rejects special chars that could cause command injection

### Platform Validation
- Must be 1-100 characters per platform
- Max 50 platforms per request
- Allowed chars: alphanumeric, underscore, hyphen
- Rejects invalid site names

### Timeout Validation
- Range: 1-300 seconds
- Prevents runaway processes

## Error Handling

All functions gracefully handle errors:

1. **Sherlock CLI Not Found**
   - Returns error message with installation instructions
   - Graceful degradation without exceptions

2. **Invalid Parameters**
   - Pydantic validation catches before function execution
   - Clear error messages

3. **Subprocess Failures**
   - Timeouts, JSON parse errors handled
   - Returns error in response dict

4. **Network Issues**
   - Handled by Sherlock subprocess
   - Results reflect which platforms were checked

## Testing

Run all tests:
```bash
cd /Users/aadel/projects/loom
PYTHONPATH=src python3 -m pytest \
    tests/test_tools/test_sherlock_backend.py \
    tests/test_params_sherlock.py \
    tests/test_sherlock_integration.py \
    -v --cov=src/loom/tools/sherlock_backend
```

Coverage: 93% of sherlock_backend.py
Total Tests: 73 (all passing)

## Architecture

### Subprocess Wrapper Pattern
Uses subprocess to invoke Sherlock CLI with JSON output (`--json` flag) rather than attempting to import Sherlock as a library, which is cleaner and more reliable.

### Validation Layers
1. **Input Validation** - Pydantic models validate at API boundary
2. **Safety Validation** - Helper functions prevent injection attacks
3. **Runtime Validation** - Subprocess timeout + JSON parsing error handling

### Response Format
Consistent dict-based responses matching Loom's standard patterns with:
- Data payload (found_on, results)
- Metadata (total_found, total_checked)
- Status indicators (sherlock_available)
- Error messages (optional)

## Integration Points

- **Server Registration** - Tools available via FastMCP to MCP clients
- **Parameter System** - Uses Loom's Pydantic v2 validation framework
- **Logging** - Uses Loom's logging configuration
- **Error Handling** - Follows Loom's dict-based error response pattern

## Future Enhancements

1. Support for Sherlock's custom config files
2. Incremental result streaming for large batches
3. Caching of results with configurable TTL
4. Integration with Loom's rate limiting
5. Support for Sherlock's JSON output filtering
