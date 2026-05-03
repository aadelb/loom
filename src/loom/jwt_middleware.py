"""JWT authentication middleware for MCP tool authorization.

Provides middleware functions to enforce role-based access control
on MCP tools during execution.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from loom.jwt_auth import (
    InsufficientPermissionsError,
    InvalidTokenError,
    TokenExpiredError,
    check_tool_access,
    validate_token,
    verify_and_get_role,
)

logger = logging.getLogger("loom.jwt_middleware")

F = TypeVar("F", bound=Callable[..., Any])


class AuthorizationError(Exception):
    """Raised when user is not authorized to access a tool."""

    pass


def extract_token_from_kwargs(kwargs: dict[str, Any]) -> str | None:
    """Extract JWT token from tool kwargs.

    Looks for token in these locations (in order):
    1. _jwt_token parameter
    2. _token parameter
    3. token parameter
    4. _auth parameter (dict with 'token' key)

    Args:
        kwargs: Tool parameter dictionary

    Returns:
        JWT token string if found, None otherwise
    """
    # Check direct token parameters
    for param_name in ["_jwt_token", "_token", "token"]:
        if param_name in kwargs:
            token = kwargs.pop(param_name)
            if isinstance(token, str):
                return token

    # Check nested auth dict
    auth = kwargs.get("_auth")
    if isinstance(auth, dict) and "token" in auth:
        return auth["token"]

    return None


def require_auth(
    require_role: str | None = None,
    allow_roles: set[str] | None = None,
) -> Callable[[F], F]:
    """Decorator to require JWT authentication on a tool.

    Args:
        require_role: Specific role required (e.g., "red_team")
        allow_roles: Set of allowed roles (e.g., {"admin", "red_team"})

    Returns:
        Decorator function

    Raises:
        InvalidTokenError: If token is invalid or missing
        TokenExpiredError: If token is expired
        AuthorizationError: If user role doesn't match requirements

    Example:
        @require_auth(require_role="red_team")
        async def research_prompt_reframe(query: str) -> dict:
            ...

        @require_auth(allow_roles={"admin", "researcher"})
        def research_search(query: str) -> dict:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract and validate token
            token = extract_token_from_kwargs(kwargs)
            if not token:
                raise InvalidTokenError("JWT token required but not provided")

            # Validate token signature and expiration
            try:
                payload = validate_token(token)
                role = payload.get("role")
            except (InvalidTokenError, TokenExpiredError) as e:
                logger.warning(
                    "auth_failed tool=%s error=%s",
                    func.__name__,
                    str(e),
                )
                raise

            # Check role requirements
            if require_role and role != require_role:
                logger.warning(
                    "role_mismatch tool=%s required=%s actual=%s user_id=%s",
                    func.__name__,
                    require_role,
                    role,
                    payload.get("sub"),
                )
                raise AuthorizationError(
                    f"Tool {func.__name__} requires {require_role} role, "
                    f"but user has {role} role"
                )

            if allow_roles and role not in allow_roles:
                logger.warning(
                    "role_not_allowed tool=%s allowed=%s actual=%s user_id=%s",
                    func.__name__,
                    allow_roles,
                    role,
                    payload.get("sub"),
                )
                raise AuthorizationError(
                    f"Tool {func.__name__} allows roles {allow_roles}, "
                    f"but user has {role} role"
                )

            # Log successful authentication
            logger.debug(
                "tool_access_granted tool=%s role=%s user_id=%s",
                func.__name__,
                role,
                payload.get("sub"),
            )

            # Call original function
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract and validate token
            token = extract_token_from_kwargs(kwargs)
            if not token:
                raise InvalidTokenError("JWT token required but not provided")

            # Validate token signature and expiration
            try:
                payload = validate_token(token)
                role = payload.get("role")
            except (InvalidTokenError, TokenExpiredError) as e:
                logger.warning(
                    "auth_failed tool=%s error=%s",
                    func.__name__,
                    str(e),
                )
                raise

            # Check role requirements
            if require_role and role != require_role:
                logger.warning(
                    "role_mismatch tool=%s required=%s actual=%s user_id=%s",
                    func.__name__,
                    require_role,
                    role,
                    payload.get("sub"),
                )
                raise AuthorizationError(
                    f"Tool {func.__name__} requires {require_role} role, "
                    f"but user has {role} role"
                )

            if allow_roles and role not in allow_roles:
                logger.warning(
                    "role_not_allowed tool=%s allowed=%s actual=%s user_id=%s",
                    func.__name__,
                    allow_roles,
                    role,
                    payload.get("sub"),
                )
                raise AuthorizationError(
                    f"Tool {func.__name__} allows roles {allow_roles}, "
                    f"but user has {role} role"
                )

            # Log successful authentication
            logger.debug(
                "tool_access_granted tool=%s role=%s user_id=%s",
                func.__name__,
                role,
                payload.get("sub"),
            )

            # Call original function
            return await func(*args, **kwargs)

        # Return appropriate wrapper
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def check_tool_authorization(token: str, tool_name: str) -> bool:
    """Check if token holder is authorized to use a specific tool.

    Args:
        token: JWT token string
        tool_name: Name of tool to check access for

    Returns:
        True if authorized, False otherwise

    Raises:
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
    """
    return check_tool_access(token, tool_name)


def get_user_from_token(token: str) -> dict[str, Any]:
    """Extract user information from JWT token.

    Args:
        token: JWT token string

    Returns:
        Dict with keys: user_id, role

    Raises:
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
    """
    payload = validate_token(token)
    return {
        "user_id": payload.get("sub"),
        "role": payload.get("role"),
    }


def create_authorized_wrapper(func: Callable[..., Any], allow_unauthenticated: bool = False) -> Callable[..., Any]:
    """Create a wrapper that enforces JWT authorization on a tool.

    Unlike @require_auth decorator, this allows unauthenticated access
    if allow_unauthenticated=True.

    Args:
        func: Tool function to wrap
        allow_unauthenticated: If True, allow access without token (for read-only tools)

    Returns:
        Wrapped function
    """

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        token = extract_token_from_kwargs(kwargs)

        if not token:
            if allow_unauthenticated:
                logger.debug("tool_access_unauthenticated tool=%s", func.__name__)
                return func(*args, **kwargs)
            else:
                raise InvalidTokenError("JWT token required but not provided")

        # Validate token
        try:
            validate_token(token)
        except (InvalidTokenError, TokenExpiredError) as e:
            logger.warning("auth_failed tool=%s error=%s", func.__name__, str(e))
            raise

        # Check tool access
        if not check_tool_authorization(token, func.__name__):
            role = verify_and_get_role(token)
            logger.warning(
                "tool_access_denied tool=%s role=%s",
                func.__name__,
                role,
            )
            raise AuthorizationError(f"User not authorized to access tool: {func.__name__}")

        logger.debug("tool_access_granted tool=%s", func.__name__)
        return func(*args, **kwargs)

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        token = extract_token_from_kwargs(kwargs)

        if not token:
            if allow_unauthenticated:
                logger.debug("tool_access_unauthenticated tool=%s", func.__name__)
                return await func(*args, **kwargs)
            else:
                raise InvalidTokenError("JWT token required but not provided")

        # Validate token
        try:
            validate_token(token)
        except (InvalidTokenError, TokenExpiredError) as e:
            logger.warning("auth_failed tool=%s error=%s", func.__name__, str(e))
            raise

        # Check tool access
        if not check_tool_authorization(token, func.__name__):
            role = verify_and_get_role(token)
            logger.warning(
                "tool_access_denied tool=%s role=%s",
                func.__name__,
                role,
            )
            raise AuthorizationError(f"User not authorized to access tool: {func.__name__}")

        logger.debug("tool_access_granted tool=%s", func.__name__)
        return await func(*args, **kwargs)

    # Return appropriate wrapper
    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
