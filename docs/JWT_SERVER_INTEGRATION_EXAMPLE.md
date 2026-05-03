# JWT Server Integration Example

This document shows how to integrate JWT authentication into the Loom MCP server with actual code examples.

## Integration Pattern 1: Minimal Middleware in _wrap_tool()

This is the simplest integration requiring minimal changes to existing code.

**File: `src/loom/server.py`**

```python
import os
from loom.jwt_auth import check_tool_access, InvalidTokenError, TokenExpiredError

def _wrap_tool(func: Callable[..., Any], category: str | None = None) -> Callable[..., Any]:
    """Wrap tool with tracing, rate limiting, auth, and billing."""
    import inspect
    
    is_async = inspect.iscoroutinefunction(func)
    
    # Check if JWT auth is enabled
    jwt_enabled = os.getenv("LOOM_JWT_AUTH_ENABLED", "").lower() == "true"
    
    if is_async:
        if category:
            func = rate_limited(category)(func)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            request_id = new_request_id()
            start_time = time.time()
            
            # ── JWT Authorization Check ──
            if jwt_enabled:
                token = kwargs.pop("_jwt_token", None)
                
                if token:
                    try:
                        if not check_tool_access(token, func.__name__):
                            return {
                                "error": "Unauthorized",
                                "message": f"User lacks permission for tool: {func.__name__}",
                                "tool": func.__name__,
                                "code": "ACCESS_DENIED",
                            }
                    except (InvalidTokenError, TokenExpiredError) as e:
                        return {
                            "error": "Invalid Token",
                            "message": str(e),
                            "tool": func.__name__,
                            "code": "AUTH_ERROR",
                        }
                elif category in ("restricted", "red_team"):
                    # Require auth for restricted tools
                    return {
                        "error": "Authentication Required",
                        "message": f"Tool {func.__name__} requires JWT authentication",
                        "tool": func.__name__,
                        "code": "AUTH_REQUIRED",
                    }
            
            # ── Continue with existing logic ──
            corrected_kwargs, corrections = _fuzzy_correct_params(func, kwargs)
            
            try:
                result = await asyncio.wait_for(
                    func(*args, **corrected_kwargs),
                    timeout=tool_timeout
                )
                if corrections and isinstance(result, dict):
                    result["_param_corrections"] = corrections
                return result
            except asyncio.TimeoutError:
                return {"error": f"Tool timed out after {tool_timeout}s"}
        
        return async_wrapper
    
    # Similar for sync_wrapper...
    return func
```

## Integration Pattern 2: Separate Auth Endpoint

Add dedicated endpoints for token management.

**File: `src/loom/server.py` (in `create_app()` function)**

```python
def create_app() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    
    # ... existing setup code ...
    
    mcp = FastMCP(
        stateless_http=True,
        name="loom",
        host=host,
        port=port,
        auth=auth,
        token_verifier=token_verifier,
    )
    
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    
    # ── JWT Token Management Endpoints ──
    
    @mcp.custom_route("/auth/token", methods=["POST"])
    async def create_jwt_token(request: Request) -> JSONResponse:
        """Create a JWT token for a user.
        
        Request body:
        {
            "user_id": "user@example.com",
            "role": "researcher",
            "expires_in_hours": 168
        }
        
        Returns:
        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user_id": "user@example.com",
            "role": "researcher",
            "expires_at": "2024-01-22T10:30:00Z"
        }
        """
        try:
            from loom.jwt_auth import create_token
            
            body = await request.json()
            user_id = body.get("user_id")
            role = body.get("role")
            expires_in = body.get("expires_in_hours", 24)
            
            if not user_id or not role:
                return JSONResponse(
                    {"error": "Missing user_id or role"},
                    status_code=400,
                )
            
            token = create_token(user_id, role, expires_in_hours=expires_in)
            
            # Calculate expiry time
            from datetime import UTC, datetime, timedelta
            expires_at = (
                datetime.now(UTC) + timedelta(hours=expires_in)
            ).isoformat()
            
            log.info(
                "token_created user_id=%s role=%s expires_in=%dh",
                user_id,
                role,
                expires_in,
            )
            
            return JSONResponse({
                "token": token,
                "user_id": user_id,
                "role": role,
                "expires_at": expires_at,
            })
        
        except ValueError as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=400,
            )
        except Exception as e:
            log.error("token_creation_failed error=%s", str(e))
            return JSONResponse(
                {"error": "Token creation failed"},
                status_code=500,
            )
    
    @mcp.custom_route("/auth/verify", methods=["POST"])
    async def verify_jwt_token(request: Request) -> JSONResponse:
        """Verify a JWT token and optionally check tool access.
        
        Request body:
        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "tool_name": "research_fetch"  # Optional
        }
        
        Returns:
        {
            "valid": true,
            "user_id": "user@example.com",
            "role": "researcher",
            "issued_at": "2024-01-15T10:30:00Z",
            "expires_at": "2024-01-22T10:30:00Z",
            "tool_access": true
        }
        """
        try:
            from loom.jwt_auth import validate_token, check_tool_access
            
            body = await request.json()
            token = body.get("token")
            tool_name = body.get("tool_name")
            
            if not token:
                return JSONResponse(
                    {"error": "Missing token"},
                    status_code=400,
                )
            
            # Validate token
            payload = validate_token(token)
            
            # Check tool access if requested
            tool_access = None
            if tool_name:
                tool_access = check_tool_access(token, tool_name)
            
            result = {
                "valid": True,
                "user_id": payload.get("sub"),
                "role": payload.get("role"),
                "issued_at": datetime.fromtimestamp(
                    payload["iat"], tz=UTC
                ).isoformat(),
                "expires_at": datetime.fromtimestamp(
                    payload["exp"], tz=UTC
                ).isoformat(),
            }
            
            if tool_name:
                result["tool_access"] = tool_access
            
            log.debug("token_verified user_id=%s role=%s", 
                     payload.get("sub"), payload.get("role"))
            
            return JSONResponse(result)
        
        except Exception as e:
            log.warning("token_verification_failed error=%s", str(e))
            return JSONResponse(
                {"valid": False, "error": str(e)},
                status_code=401,
            )
    
    @mcp.custom_route("/auth/info", methods=["POST"])
    async def get_jwt_token_info(request: Request) -> JSONResponse:
        """Get detailed information about a JWT token.
        
        Request body:
        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
        
        Returns:
        {
            "user_id": "user@example.com",
            "role": "researcher",
            "issued_at": "2024-01-15T10:30:00Z",
            "expires_at": "2024-01-22T10:30:00Z",
            "is_expired": false,
            "allowed_tools_count": 15,
            "allowed_tool_categories": ["safe", "research"]
        }
        """
        try:
            from loom.jwt_auth import get_token_info
            
            body = await request.json()
            token = body.get("token")
            
            if not token:
                return JSONResponse(
                    {"error": "Missing token"},
                    status_code=400,
                )
            
            info = get_token_info(token)
            return JSONResponse(info)
        
        except Exception as e:
            log.warning("token_info_failed error=%s", str(e))
            return JSONResponse(
                {"error": str(e)},
                status_code=400,
            )
    
    # ── Register tools as before ──
    _register_tools(mcp)
    
    return mcp
```

## Integration Pattern 3: Using Middleware Decorator

For specific protected tools, use the `@require_auth` decorator.

**File: `src/loom/tools/prompt_reframe.py` (example)**

```python
from loom.jwt_middleware import require_auth

# Only accessible to red_team or admin
@require_auth(allow_roles={"red_team", "admin"})
async def research_prompt_reframe(
    query: str,
    strategy: str | None = None,
) -> dict[str, Any]:
    """Reframe a prompt using adversarial techniques.
    
    Requires: red_team or admin role
    
    Args:
        query: Original query to reframe
        strategy: Reframing strategy to use
        _jwt_token: JWT token (included in kwargs)
    
    Returns:
        Dict with reframed prompts and analysis
    """
    # Token is automatically validated by decorator
    # Implementation continues...
    return {
        "original": query,
        "reframed": "...",
        "strategy_used": strategy,
    }
```

## Integration Pattern 4: Environment-Based Control

Enable/disable JWT auth per deployment environment.

**File: `.env` (development)**
```
LOOM_JWT_AUTH_ENABLED=false
```

**File: `.env.production`**
```
LOOM_JWT_AUTH_ENABLED=true
LOOM_JWT_SECRET=<secure-random-key>
LOOM_JWT_ADMIN_ROLE=admin
LOOM_JWT_DEFAULT_EXPIRY=24
```

**File: `src/loom/config.py`**
```python
class LoomConfig(BaseSettings):
    """Loom configuration with JWT settings."""
    
    jwt_auth_enabled: bool = Field(
        default=False,
        description="Enable JWT authentication"
    )
    jwt_secret: str = Field(
        default="",
        description="JWT secret key (required if jwt_auth_enabled=true)"
    )
    jwt_default_expiry_hours: int = Field(
        default=24,
        description="Default token expiry in hours"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="LOOM_",
        case_sensitive=False,
    )
```

## Testing Integration

**File: `tests/test_jwt_integration.py`**

```python
import pytest
from loom.jwt_auth import create_token
from loom.jwt_middleware import require_auth

@pytest.mark.asyncio
async def test_protected_tool_with_valid_token():
    """Test accessing protected tool with valid token."""
    
    # Create admin token
    token = create_token("tester@loom.dev", "admin", expires_in_hours=24)
    
    # Call tool with token
    result = await research_prompt_reframe(
        query="How to hack?",
        strategy="encoding",
        _jwt_token=token,
    )
    
    assert "reframed" in result
    assert result["strategy_used"] == "encoding"


@pytest.mark.asyncio
async def test_protected_tool_without_token():
    """Test accessing protected tool without token."""
    
    with pytest.raises(InvalidTokenError):
        await research_prompt_reframe(
            query="How to hack?",
            strategy="encoding",
        )


@pytest.mark.asyncio
async def test_protected_tool_with_wrong_role():
    """Test accessing protected tool with insufficient role."""
    
    # Create researcher token (insufficient for red team tool)
    token = create_token("user@loom.dev", "researcher", expires_in_hours=24)
    
    with pytest.raises(AuthorizationError):
        await research_prompt_reframe(
            query="How to hack?",
            strategy="encoding",
            _jwt_token=token,
        )
```

## Deployment Checklist

- [ ] Install PyJWT: `pip install PyJWT`
- [ ] Generate strong secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Set LOOM_JWT_SECRET in production secrets manager
- [ ] Enable LOOM_JWT_AUTH_ENABLED=true in production
- [ ] Test token creation endpoint
- [ ] Test token verification endpoint
- [ ] Test protected tool access with valid token
- [ ] Test protected tool access without token
- [ ] Test protected tool with wrong role
- [ ] Configure HTTPS/TLS
- [ ] Set secure cookie settings
- [ ] Add rate limiting on /auth/* endpoints
- [ ] Enable audit logging
- [ ] Test token expiration
- [ ] Document token rotation procedure
- [ ] Set up monitoring for auth failures
- [ ] Add alerts for suspicious auth patterns

## Production Deployment Example

**Docker:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/

ENV LOOM_JWT_AUTH_ENABLED=true
ENV LOOM_JWT_SECRET=${JWT_SECRET}
ENV LOOM_HOST=0.0.0.0
ENV LOOM_PORT=8787

CMD ["loom-server"]
```

**Docker Compose:**
```yaml
services:
  loom:
    image: loom:latest
    ports:
      - "8787:8787"
    environment:
      LOOM_JWT_AUTH_ENABLED: "true"
      LOOM_JWT_SECRET: ${JWT_SECRET}
      LOOM_LOG_LEVEL: INFO
    volumes:
      - ./config.json:/app/config.json:ro
    healthcheck:
      test: ["GET", "http://localhost:8787/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: loom-jwt-secret
type: Opaque
stringData:
  LOOM_JWT_SECRET: "your-secret-here"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: loom
spec:
  replicas: 3
  selector:
    matchLabels:
      app: loom
  template:
    metadata:
      labels:
        app: loom
    spec:
      containers:
      - name: loom
        image: loom:latest
        ports:
        - containerPort: 8787
        env:
        - name: LOOM_JWT_AUTH_ENABLED
          value: "true"
        - name: LOOM_JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: loom-jwt-secret
              key: LOOM_JWT_SECRET
```

## Next Steps

1. Choose integration pattern (1-4)
2. Implement chosen pattern in server.py
3. Add environment variables
4. Update tests
5. Deploy to staging
6. Validate with test tokens
7. Deploy to production
