# Loom API Authentication — Quick Start

## Enable Authentication

```bash
export LOOM_AUTH_REQUIRED=true
export LOOM_API_KEYS="your-secret-key"
loom serve
```

## Make Authenticated Requests

### cURL
```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8787/v1/health
```

### Python
```python
import requests

headers = {"X-API-Key": "your-secret-key"}
response = requests.get(
    "http://localhost:8787/v1/health",
    headers=headers
)
print(response.json())
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8787/v1/health', {
  headers: { 'X-API-Key': 'your-secret-key' }
});
const data = await response.json();
console.log(data);
```

## Multiple Keys

```bash
export LOOM_API_KEYS="prod-key,dev-key,test-key"
```

## Exempt Endpoints (No Auth Required)

- `/health`, `/v1/health`, `/v1/health/deep`
- `/versions`, `/v1/versions`
- `/metrics`, `/v1/metrics`
- `/mcp`

Use these for monitoring and health checks:

```bash
# Works without X-API-Key
curl http://localhost:8787/v1/health
```

## Disable Authentication (Default)

```bash
# Auth is disabled by default
export LOOM_AUTH_REQUIRED=false
# OR don't set it
loom serve
```

## Error Response

Authentication failure returns 401 JSON:

```json
{
  "error": "unauthorized",
  "message": "Missing or invalid X-API-Key header",
  "status": 401
}
```

## See Full Documentation

See `docs/api_authentication.md` for detailed configuration, troubleshooting, and best practices.
