# Secret Manager Guide

## Overview

The SecretManager provides centralized API key validation, rotation, and expiration tracking for all Loom providers (8 LLM providers + 6 search providers with API keys).

**Key features:**
- Format validation (prefix check, length, base64 validity)
- In-memory key rotation without server restart
- Last-used timestamp tracking
- Staleness detection (alerts on keys >7 days unused)
- Comprehensive health status reporting

## Architecture

### Singleton Pattern

The SecretManager is a singleton — only one instance exists per server:

```python
from loom.secret_manager import get_secret_manager

mgr = get_secret_manager()  # Same instance every time
```

### Key Configuration

All 14 providers have standardized configuration:

| Provider | Env Variable | Prefix | Min Length | Rotation Supported |
|----------|--------------|--------|------------|-------------------|
| **groq** | GROQ_API_KEY | `gsk_` | 20 | ✓ Yes |
| **nvidia_nim** | NVIDIA_NIM_API_KEY | `nvapi-` | 20 | ✓ Yes |
| **deepseek** | DEEPSEEK_API_KEY | `sk-` | 20 | ✓ Yes |
| **gemini** | GOOGLE_AI_KEY | `AIzaSy` | 30 | ✓ Yes |
| **moonshot** | MOONSHOT_API_KEY | `sk-` | 20 | ✓ Yes |
| **openai** | OPENAI_API_KEY | `sk-` | 20 | ✓ Yes |
| **anthropic** | ANTHROPIC_API_KEY | `sk-ant-` | 20 | ✓ Yes |
| **vllm** | VLLM_ENDPOINT | `http` | 10 | ✗ No |
| **exa** | EXA_API_KEY | `exa-` | 20 | ✓ Yes |
| **tavily** | TAVILY_API_KEY | `tvly-` | 20 | ✓ Yes |
| **firecrawl** | FIRECRAWL_API_KEY | `fc-` | 20 | ✓ Yes |
| **brave** | BRAVE_API_KEY | `BSA` | 10 | ✓ Yes |
| **newsapi** | NEWS_API_KEY | - | 20 | ✓ Yes |
| **coinmarketcap** | COINMARKETCAP_API_KEY | - | 20 | ✓ Yes |

**Always-available providers** (no key required): `ddgs`, `arxiv`, `wikipedia`, `hackernews`, `reddit`

## Server Startup

When the server starts, SecretManager is automatically initialized:

```
INFO: secret_manager_initialized status=degraded valid_keys=2 missing_keys=12
```

Logs include:
- Overall health status
- Count of valid vs missing keys
- Alerts for stale keys (>7 days unused)

## API Reference

### `get_secret_manager() -> SecretManager`

Get or create the singleton instance:

```python
from loom.secret_manager import get_secret_manager

mgr = get_secret_manager()
```

### `validate_all_keys() -> dict[str, dict]`

Validate all configured keys at once:

```python
validation_results = mgr.validate_all_keys()
# {
#   "groq": {"valid": True, "present": True, "error": None, ...},
#   "openai": {"valid": False, "present": False, "error": "Key not present", ...},
#   ...
# }
```

### `validate_key(provider: str) -> dict`

Validate a single key:

```python
result = mgr.validate_key("groq")
# {
#   "valid": True,
#   "present": True,
#   "error": None,
#   "format_check": True,
#   "length_check": True,
#   "prefix_check": True
# }
```

**Validation checks:**
- `present`: Key is present in environment
- `format_check`: Valid characters (alphanumeric + hyphens/underscores)
- `length_check`: Meets minimum length requirement
- `prefix_check`: Matches expected prefix (if configured)

### `get_key(provider: str) -> str | None`

Get current API key (updates last-used timestamp):

```python
key = mgr.get_key("groq")
if key:
    print(f"Using key: {key[:10]}...")
```

### `rotate_key(provider: str, new_key: str) -> bool`

Rotate API key without restart:

```python
success = mgr.rotate_key("groq", "gsk_newkeylongerthan20chars")
if success:
    print("Key rotated successfully")
```

**Requirements:**
- Provider must support rotation (see table above)
- New key must pass validation
- If validation fails, old key is preserved (atomic rollback)

### `get_last_used(provider: str) -> datetime | None`

Get last-used timestamp for a key:

```python
last_used = mgr.get_last_used("groq")
if last_used:
    print(f"Last used: {last_used.isoformat()}")
```

### `get_health() -> dict`

Get comprehensive health status:

```python
health = mgr.get_health()
# {
#   "overall_status": "degraded",
#   "valid_keys": 2,
#   "missing_keys": 12,
#   "stale_keys": ["exa"],
#   "stale_threshold_days": 7,
#   "total_providers": 14,
#   "providers": {
#     "groq": {
#       "status": "valid",
#       "present": True,
#       "valid": True,
#       "last_used": "2026-05-04T12:30:45.123456+00:00",
#       "error": ""
#     },
#     ...
#   },
#   "always_available": ["ddgs", "arxiv", "wikipedia", "hackernews", "reddit"],
#   "timestamp": "2026-05-04T12:30:45.123456+00:00"
# }
```

**Health status values:**
- `healthy`: All keys valid, none stale
- `degraded`: Some keys missing or stale
- `unhealthy`: No valid keys present

## MCP Tool: `research_secret_health()`

Check API key health via MCP protocol:

```python
result = await research_secret_health()
# Returns: health status dict (same as get_health())
```

**Example response:**
```json
{
  "overall_status": "degraded",
  "valid_keys": 2,
  "missing_keys": 12,
  "stale_keys": ["exa"],
  "stale_threshold_days": 7,
  "total_providers": 14,
  "providers": {
    "groq": {
      "status": "valid",
      "present": true,
      "valid": true,
      "last_used": "2026-05-04T12:30:45.123456+00:00",
      "error": ""
    }
  },
  "always_available": ["ddgs", "arxiv", "wikipedia", "hackernews", "reddit"],
  "timestamp": "2026-05-04T12:30:45.123456+00:00"
}
```

## Usage Examples

### Check Key Health

```python
from loom.secret_manager import get_secret_manager

mgr = get_secret_manager()
health = mgr.get_health()

if health["overall_status"] == "healthy":
    print("✓ All API keys configured and valid")
else:
    print(f"⚠ {health['missing_keys']} keys missing")
    if health["stale_keys"]:
        print(f"⚠ Stale keys: {health['stale_keys']}")
```

### Rotate a Key Programmatically

```python
from loom.secret_manager import get_secret_manager

mgr = get_secret_manager()

# Check current status
current_health = mgr.get_health()
print(f"Before: {current_health['providers']['groq']['status']}")

# Rotate the key
new_key = "gsk_new_key_from_admin_panel"
if mgr.rotate_key("groq", new_key):
    print("✓ Key rotated successfully (no restart needed)")
else:
    print("✗ Key rotation failed (validation error)")
```

### Monitor Staleness

```python
from loom.secret_manager import get_secret_manager
from datetime import UTC, datetime, timedelta

mgr = get_secret_manager()

# Check for keys not used in 7+ days
for provider in ["groq", "openai", "exa"]:
    last_used = mgr.get_last_used(provider)
    if last_used:
        days_unused = (datetime.now(UTC) - last_used).days
        if days_unused > 7:
            print(f"⚠ {provider}: unused for {days_unused} days")
```

## Validation Rules

### Format Validation

Each API key is checked for:

1. **Presence**: Key must be in environment variable
2. **Prefix**: Must start with provider-specific prefix (if configured)
3. **Length**: Must meet minimum length requirement
4. **Characters**: Only alphanumeric + hyphens/underscores allowed

### Example Validations

✓ **Valid Groq key:**
```
gsk_validkeylongerthan20characters
```

✗ **Invalid (wrong prefix):**
```
sk_groqkeylongerthan20characters  # Expected 'gsk_' prefix
```

✗ **Invalid (too short):**
```
gsk_short  # Only 9 chars, requires 20+
```

✗ **Invalid (bad characters):**
```
gsk_key!@#$invalid%  # Contains !@#$%
```

## Logging

### Startup Validation

```
INFO: secret_manager_initialized status=degraded valid_keys=2 missing_keys=12
INFO: validate_all_keys total_providers=14 valid=2 present=2
```

### Key Rotation

```
INFO: rotate_key_success provider=groq key_length=32
```

### Staleness Alerts

```
WARNING: stale_key_alert provider=exa days_since_use=8
```

### Initialization Errors

```
ERROR: secret_manager_init_failed error=ConnectionError
```

## Thread Safety

The SecretManager uses internal locking to ensure thread-safe operation:

```python
# Safe to call from multiple threads/async tasks
mgr.get_key("groq")
mgr.rotate_key("openai", "new_key")
mgr.get_health()
```

## Future Enhancements

Potential improvements for future releases:

1. **Expiration tracking**: Store and monitor actual key expiration dates
2. **Encryption**: Store keys encrypted at rest instead of plain text
3. **Audit log**: Track all key access and rotation events
4. **Key rotation policies**: Automatic rotation schedules
5. **Webhook alerts**: Notify external systems of key issues
6. **Rate limit headers**: Track and report API rate limit status per provider

## Troubleshooting

### "Key not present" error

**Cause**: Environment variable is not set

**Solution**: Set the required environment variable:
```bash
export GROQ_API_KEY="gsk_your_key_here"
```

### "Key too short" error

**Cause**: API key doesn't meet minimum length

**Solution**: Verify you copied the key correctly from the provider's dashboard

### "Invalid prefix" error

**Cause**: Key doesn't start with expected prefix

**Solution**: Verify you're using the correct API key (not a different service's key)

### "Invalid character" error

**Cause**: Key contains non-alphanumeric characters (except hyphens/underscores)

**Solution**: Verify key format from provider documentation

## Performance

- **Validation**: <1ms per key
- **Rotation**: <5ms per key (includes validation)
- **Health check**: <10ms for all 14 providers
- **Memory usage**: <1 MB singleton instance

## Security

- Keys are loaded from environment variables only (not hardcoded)
- Validation catches malformed keys early
- Atomic rotation prevents partial updates
- Thread-safe operations prevent race conditions
- No logging of actual key values (only length and status)
