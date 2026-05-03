# JWT Authentication Integration Guide

This guide explains how to integrate the JWT-based authentication system into Loom's MCP server.

## Overview

The JWT authentication module (`src/loom/jwt_auth.py`) provides:

- **Token Generation**: Create JWT tokens for users with specific roles
- **Token Validation**: Verify token signatures and expiration
- **Role-Based Access Control (RBAC)**: Restrict tool access based on user roles
- **Four Role Tiers**: admin, researcher, red_team, viewer

## Quick Start

### 1. Set Environment Variables

```bash
# Required: JWT secret key (use strong random value in production)
export LOOM_JWT_SECRET="your-super-secret-key-change-this"

# Optional: Generate a secure secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Create Tokens

```python
from loom.jwt_auth import create_token

# Create an admin token (24-hour expiry)
admin_token = create_token("user@example.com", "admin", expires_in_hours=24)

# Create a researcher token
researcher_token = create_token("researcher@example.com", "researcher", expires_in_hours=168)

# Create a red_team token
red_team_token = create_token("tester@example.com", "red_team", expires_in_hours=8)

# Create a viewer token (read-only)
viewer_token = create_token("observer@example.com", "viewer", expires_in_hours=720)
```

### 3. Validate Tokens in Your Application

```python
from loom.jwt_auth import validate_token, check_tool_access

# Validate token and get payload
try:
    payload = validate_token(token)
    user_id = payload["sub"]
    role = payload["role"]
except TokenExpiredError:
    # Handle expired token
    pass
except InvalidTokenError:
    # Handle invalid token
    pass

# Check if user can access a specific tool
if check_tool_access(token, "research_fetch"):
    # Proceed with tool execution
else:
    # Deny access
```

## Integration with server.py

### Option A: Authorization Middleware in _wrap_tool()

Modify `_wrap_tool()` to check tool access before execution:

```python
def _wrap_tool(func: Callable[..., Any], category: str | None = None) -> Callable[..., Any]:
    """Wrap tool with tracing, rate limiting, auth, and billing."""
    import inspect
    
    is_async = inspect.iscoroutinefunction(func)
    
    if is_async:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract JWT token from request context (if available)
            token = kwargs.pop("_jwt_token", None)
            
            # Check authorization if token provided
            if token:
                from loom.jwt_auth import check_tool_access, InvalidTokenError
                try:
                    if not check_tool_access(token, func.__name__):
                        return {
                            "error": "Unauthorized",
                            "message": f"User lacks permission for tool: {func.__name__}",
                            "tool": func.__name__,
                        }
                except InvalidTokenError as e:
                    return {
                        "error": "Invalid Token",
                        "message": str(e),
                        "tool": func.__name__,
                    }
            
            # ... rest of wrapper code (rate limiting, tracing, etc.)
            return await func(*args, **corrected_kwargs)
        
        return async_wrapper
    
    # Similar for sync_wrapper
```

### Option B: Custom HTTP Endpoint for Token Validation

Add an endpoint to create and validate tokens:

```python
from starlette.responses import JSONResponse
from starlette.requests import Request

@mcp.custom_route("/auth/token", methods=["POST"])
async def create_token_endpoint(request: Request) -> JSONResponse:
    """Create a JWT token for a user.
    
    Request body:
    {
        "user_id": "user@example.com",
        "role": "researcher",
        "expires_in_hours": 24
    }
    """
    from loom.jwt_auth import create_token, JWTAuthError
    
    try:
        data = await request.json()
        token = create_token(
            data["user_id"],
            data["role"],
            expires_in_hours=data.get("expires_in_hours", 24),
        )
        return JSONResponse({
            "token": token,
            "user_id": data["user_id"],
            "role": data["role"],
        })
    except JWTAuthError as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            {"error": "Token creation failed"},
            status_code=500,
        )


@mcp.custom_route("/auth/verify", methods=["POST"])
async def verify_token_endpoint(request: Request) -> JSONResponse:
    """Verify a JWT token.
    
    Request body:
    {
        "token": "eyJ0eXAi...",
        "tool_name": "research_fetch"  # Optional: check specific tool access
    }
    """
    from loom.jwt_auth import validate_token, check_tool_access, InvalidTokenError
    
    try:
        data = await request.json()
        token = data["token"]
        
        # Validate token
        payload = validate_token(token)
        
        # Optionally check specific tool access
        tool_access = None
        if "tool_name" in data:
            tool_access = check_tool_access(token, data["tool_name"])
        
        return JSONResponse({
            "valid": True,
            "user_id": payload["sub"],
            "role": payload["role"],
            "tool_access": tool_access,
        })
    except InvalidTokenError as e:
        return JSONResponse(
            {"valid": False, "error": str(e)},
            status_code=401,
        )
    except Exception as e:
        return JSONResponse(
            {"valid": False, "error": "Verification failed"},
            status_code=500,
        )
```

## Role Definitions

### Admin
- **Access**: All 581 tools unrestricted
- **Use Case**: System administrators, security researchers
- **Expiry**: Typically 24-168 hours

### Researcher
- **Access**: Safe tools only (search, fetch, LLM, creative, academic, career)
- **Denied**: Red team tools, prompt injection, jailbreaks, etc.
- **Use Case**: Legitimate researchers, content creators
- **Expiry**: Typically 168 hours (1 week)

### Red Team
- **Access**: All tools (same as admin)
- **Use Case**: Security testing, authorized penetration testing
- **Expiry**: Typically 1-8 hours (short-lived)

### Viewer
- **Access**: Read-only tools (search, help, health check)
- **Denied**: All write/modify operations
- **Use Case**: Monitoring, reporting, public dashboards
- **Expiry**: Typically 720 hours (30 days)

## Tool Categories

### Safe Tools (Researcher Tier)
```python
{
    "search", "fetch", "markdown", "deep",
    "llm", "enrich", "creative",
    "academic_integrity", "career_intel",
    "knowledge_graph", "fact_checker",
    "trend_predictor", "health_check", "help"
}
```

### Restricted Tools (Red Team/Admin Only)
```python
{
    "prompt_reframe", "adversarial_debate_tool",
    "context_poison", "daisy_chain",
    "jailbreak_evolution", "stealth_detect",
    "ai_safety", "reid_pipeline",
    "crescendo_loop", "swarm_attack", "xover_attack"
}
```

### Infrastructure Tools
```python
{
    "vastai", "billing", "email_report", "joplin",
    "tor", "transcribe", "document", "sessions", "config"
}
```

## API Usage Examples

### Create Token via cURL

```bash
curl -X POST http://localhost:8787/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "researcher@example.com",
    "role": "researcher",
    "expires_in_hours": 168
  }'
```

Response:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": "researcher@example.com",
  "role": "researcher"
}
```

### Verify Token Access

```bash
curl -X POST http://localhost:8787/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "tool_name": "research_fetch"
  }'
```

Response:
```json
{
  "valid": true,
  "user_id": "researcher@example.com",
  "role": "researcher",
  "tool_access": true
}
```

### Call Tool with Token

In MCP client, include token in tool parameters:

```json
{
  "tool_name": "research_fetch",
  "parameters": {
    "_jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "url": "https://example.com",
    "timeout": 30
  }
}
```

## Testing

Run JWT authentication tests:

```bash
# Run all JWT tests
pytest tests/test_jwt_auth.py -v

# Run specific test class
pytest tests/test_jwt_auth.py::TestTokenGeneration -v

# Run with coverage
pytest tests/test_jwt_auth.py --cov=src/loom/jwt_auth
```

## Security Considerations

### Secret Key Management
- Store `LOOM_JWT_SECRET` in a secure vault (AWS Secrets Manager, HashiCorp Vault, etc.)
- Rotate keys periodically
- Use strong random values (minimum 32 characters)
- Never commit secrets to version control

### Token Expiration
- Shorter expiry for high-risk tokens (red_team: 1-8 hours)
- Longer expiry for service tokens (viewer: 30 days)
- Implement refresh token mechanism for long-lived sessions

### Logging
- Log all token creation events with user ID and role
- Log all access denials with tool name and reason
- Never log full tokens in logs (only first 20 chars)

### HTTPS Enforcement
- Always use HTTPS in production
- Implement secure cookie settings
- Add CORS headers for API endpoints

## Troubleshooting

### "LOOM_JWT_SECRET environment variable not set"
**Solution**: Set the environment variable before running the server:
```bash
export LOOM_JWT_SECRET="your-secret-key"
```

### "Invalid token" when token was recently created
**Possible causes**:
1. Secret key changed between token creation and validation
2. Token expired (check `expires_in_hours`)
3. System clock skew between servers

**Solution**: Verify secret key is consistent and check system time.

### "Unauthorized" error for allowed tool
**Possible causes**:
1. User role doesn't include the tool
2. Tool name doesn't match (case-sensitive)
3. Token expired

**Solution**: Check role permissions with `get_token_info()` or verify token hasn't expired.

## Advanced Features

### Custom Role Definition

To add custom roles, modify `ROLE_PERMISSIONS` in `jwt_auth.py`:

```python
ROLE_PERMISSIONS["custom_role"] = {
    "search", "fetch", "markdown",
    # Add specific tools here
}
```

### Token Introspection

Get detailed token information:

```python
from loom.jwt_auth import get_token_info

info = get_token_info(token)
print(info)
# Output:
# {
#   "user_id": "user@example.com",
#   "role": "researcher",
#   "issued_at": "2024-01-15T10:30:00+00:00",
#   "expires_at": "2024-01-22T10:30:00+00:00",
#   "is_expired": False,
#   "allowed_tools_count": 15,
#   "allowed_tool_categories": ["safe", "research"]
# }
```

## Next Steps

1. **Install PyJWT**: `pip install PyJWT`
2. **Set LOOM_JWT_SECRET**: Export environment variable or use .env
3. **Add HTTP endpoints**: Integrate token creation/verification endpoints
4. **Update _wrap_tool()**: Add authorization checks to tool wrapper
5. **Test integration**: Run test suite to verify everything works
6. **Deploy**: Push to production with secure secret management
