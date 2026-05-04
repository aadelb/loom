# API Authentication Middleware

This document explains how to configure and use the X-API-Key authentication middleware for the Loom MCP server.

## Overview

The Loom MCP server includes optional X-API-Key header-based authentication to protect your research tools and data. Authentication is **disabled by default** (opt-in) to maintain backward compatibility.

## Configuration

### Environment Variables

Two environment variables control authentication behavior:

| Variable | Type | Default | Purpose |
|----------|------|---------|---------|
| `LOOM_AUTH_REQUIRED` | bool | `false` | Enable/disable authentication enforcement |
| `LOOM_API_KEYS` | string | (empty) | Comma-separated list of valid API keys |

### Enabling Authentication

Authentication is controlled by the `LOOM_AUTH_REQUIRED` environment variable:

```bash
# Disable authentication (default)
export LOOM_AUTH_REQUIRED=false

# Enable authentication
export LOOM_AUTH_REQUIRED=true
```

The value is case-insensitive (`true`, `True`, `TRUE` all work).

### Configuring API Keys

When authentication is enabled, provide one or more valid API keys via `LOOM_API_KEYS`:

```bash
# Single key
export LOOM_API_KEYS="your-secret-api-key"

# Multiple keys (comma-separated)
export LOOM_API_KEYS="key-1,key-2,key-3"

# Whitespace is automatically trimmed
export LOOM_API_KEYS="key-1, key-2 , key-3"
```

### Quick Start Example

```bash
# Set environment variables
export LOOM_AUTH_REQUIRED=true
export LOOM_API_KEYS="prod-key-abc123,dev-key-xyz789"

# Start the server
loom serve
```

## Using the API

### Including the X-API-Key Header

Send the `X-API-Key` header with your API key in all requests:

```bash
# curl example
curl -H "X-API-Key: your-secret-api-key" \
  http://localhost:8787/api/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

```python
# Python requests example
import requests

headers = {
    "X-API-Key": "your-secret-api-key",
    "Content-Type": "application/json"
}

response = requests.get(
    "http://localhost:8787/v1/health",
    headers=headers
)
print(response.json())
```

```javascript
// JavaScript fetch example
const response = await fetch(
  'http://localhost:8787/api/research/fetch',
  {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-secret-api-key',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      url: 'https://example.com',
      mode: 'stealthy'
    })
  }
);

const data = await response.json();
console.log(data);
```

### Response on Authentication Failure

When a request lacks a valid API key, the server returns HTTP 401:

```json
{
  "error": "unauthorized",
  "message": "Missing or invalid X-API-Key header",
  "status": 401
}
```

### Case-Sensitivity

The `X-API-Key` header name is **case-insensitive**:

- `X-API-Key` ✓
- `x-api-key` ✓
- `X-Api-Key` ✓
- `X-API-KEY` ✓

However, the **API key value itself is case-sensitive**. Use the exact key you configured.

## Exempt Endpoints

The following endpoints **bypass authentication** and are always accessible without an API key:

- `/health` — Legacy health check
- `/v1/health` — Versioned health check
- `/v1/health/deep` — Deep diagnostics health check
- `/versions` — API versions information
- `/v1/versions` — Versioned versions endpoint
- `/metrics` — Prometheus metrics (if enabled)
- `/v1/metrics` — Versioned metrics endpoint
- `/mcp` — MCP protocol endpoint

These endpoints are useful for load balancers, monitoring systems, and health checks.

### Example: Health Check Without Authentication

```bash
# This works without X-API-Key header
curl http://localhost:8787/v1/health

# Returns
{
  "api_version": "v1",
  "status": "healthy",
  "uptime_seconds": 12345,
  "tool_count": 346,
  "strategy_count": 957,
  "prometheus_enabled": true,
  "timestamp": "2026-05-04T10:30:00+00:00"
}
```

## Behavior Matrix

| Scenario | Auth Enabled | Auth Disabled | Exempt Path |
|----------|--------------|---------------|-------------|
| Valid API key | ✓ Allowed | ✓ Allowed | ✓ Allowed |
| Invalid API key | ✗ 401 | ✓ Allowed | ✓ Allowed |
| Missing API key | ✗ 401 | ✓ Allowed | ✓ Allowed |

## Best Practices

### 1. Use Strong API Keys

Generate cryptographically secure API keys:

```bash
# Generate a 32-character random key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Or use openssl
openssl rand -hex 32
```

### 2. Rotate Keys Regularly

Periodically update `LOOM_API_KEYS` to remove old keys:

```bash
# Old key: export LOOM_API_KEYS="old-key,temporary-key"
# New key: export LOOM_API_KEYS="new-key,another-key"
```

### 3. Use Environment Variables or Secrets Manager

Never hardcode API keys in your code:

```bash
# Good: Load from .env file (not committed to Git)
source ~/.loom_env
export LOOM_AUTH_REQUIRED
export LOOM_API_KEYS

# Better: Use a secrets manager
export LOOM_API_KEYS=$(aws secretsmanager get-secret-value --secret-id loom/api-keys --query SecretString --output text)
```

### 4. Monitor Authentication Logs

The middleware logs all authentication events (successes and failures):

```bash
# View logs with grep
loom serve 2>&1 | grep "auth_middleware"

# Example output:
# 2026-05-04 10:30:15 DEBUG loom.api_auth auth_middleware_accepted path=/api/fetch method=POST
# 2026-05-04 10:30:20 WARNING loom.api_auth auth_middleware_rejected path=/api/search method=GET remote_addr=192.168.1.100
```

### 5. Implement Rate Limiting

Consider adding rate limiting on top of API key authentication to prevent abuse:

```bash
# Example: Limit to 1000 requests per hour per key
export LOOM_RATE_LIMIT_PER_KEY="1000/hour"
```

## Troubleshooting

### Problem: "401 unauthorized" on all requests

**Cause**: Authentication is enabled but no valid API key is provided.

**Solution**: 
1. Check that `LOOM_AUTH_REQUIRED=true`
2. Include valid `X-API-Key` header from `LOOM_API_KEYS`
3. Verify header name spelling (case-insensitive, but must be "X-API-Key")

### Problem: "Missing or invalid X-API-Key header" error

**Cause**: The API key doesn't match any configured key in `LOOM_API_KEYS`.

**Solution**:
1. Check the API key value for typos (case-sensitive)
2. Ensure the key exists in `LOOM_API_KEYS` (comma-separated)
3. Verify the header is present in the request

### Problem: Health check returns 401

**Cause**: This shouldn't happen! Health checks are exempt from authentication.

**Solution**:
1. Verify you're using a correct health endpoint (`/v1/health`, not custom paths)
2. Check if your reverse proxy is adding authentication

### Problem: Unable to access health check for monitoring

**Solution**: Use exempt health endpoints which don't require authentication:

```bash
# Monitoring system can use this without API key
curl http://localhost:8787/v1/health

# Or deeper checks
curl http://localhost:8787/v1/health/deep
```

## Server Startup

When the Loom server starts, it logs authentication configuration:

```
INFO: api_auth_middleware_registered auth_required=true
```

If auth is enabled but no keys are configured:

```
WARNING: auth_middleware_misconfigured LOOM_AUTH_REQUIRED=true but LOOM_API_KEYS is empty; all requests will be rejected
```

This warning helps prevent accidental lock-outs.

## Implementation Details

### Architecture

The middleware is implemented as an ASGI layer that:

1. **Intercepts** all HTTP requests before they reach the FastMCP application
2. **Extracts** the `X-API-Key` header (if present)
3. **Validates** the key against configured `LOOM_API_KEYS`
4. **Allows** exempt paths to pass through without validation
5. **Returns** 401 JSON response for invalid/missing keys
6. **Logs** all authentication events for audit trails

### Request Flow

```
Request
  ↓
[ApiKeyAuthMiddleware]
  ├─ Is it HTTP? → No: Pass through
  └─ Is path exempt? → Yes: Pass through
  └─ Is auth required? → No: Pass through
  └─ Valid API key? → Yes: Pass through
  └─ Valid API key? → No: Return 401 JSON
  ↓
FastMCP Application
  ↓
Response
```

### Code Location

- **Middleware**: `src/loom/api_auth.py`
- **Tests**: `tests/test_api_auth.py`
- **Integration**: `src/loom/server.py` (lines ~1859-1861)

## See Also

- [Loom API Documentation](./tools-reference.md)
- [Configuration Guide](./api-keys.md)
- [Server Architecture](./architecture.md)
