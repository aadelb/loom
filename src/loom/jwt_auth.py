"""JWT-based authentication with role-based access control for Loom MCP.

Provides token generation, validation, and tool access authorization
based on user roles (admin, researcher, red_team, viewer).
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore

logger = logging.getLogger("loom.jwt_auth")


# ── Role Definitions ──

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},  # All tools
    "researcher": {
        # Safe research tools
        "search",
        "fetch",
        "markdown",
        "deep",
        "llm",
        "enrich",
        "creative",
        "academic_integrity",
        "career_intel",
        "knowledge_graph",
        "fact_checker",
        "trend_predictor",
        "health_check",
        "help",
    },
    "red_team": {
        "*"  # All tools for red team testing
    },
    "viewer": {
        # Read-only tools
        "search",
        "markdown",
        "knowledge_graph",
        "fact_checker",
        "health_check",
        "help",
    },
}

# Tool categories for authorization
TOOL_CATEGORIES: dict[str, set[str]] = {
    "safe": {
        "search",
        "fetch",
        "markdown",
        "deep",
        "llm",
        "enrich",
        "creative",
        "academic_integrity",
        "career_intel",
        "knowledge_graph",
        "fact_checker",
        "trend_predictor",
        "help",
    },
    "research": {
        "research_fetch",
        "research_spider",
        "research_markdown",
        "research_search",
        "research_deep",
        "research_llm_summarize",
        "research_llm_extract",
        "research_llm_classify",
        "research_llm_translate",
        "research_llm_expand",
        "research_llm_answer",
        "research_llm_embed",
        "research_llm_chat",
    },
    "restricted": {
        # Red team and adversarial tools
        "prompt_reframe",
        "adversarial_debate_tool",
        "context_poison",
        "daisy_chain",
        "jailbreak_evolution",
        "stealth_detect",
        "ai_safety",
        "ai_safety_extended",
        "reid_pipeline",
        "crescendo_loop",
        "swarm_attack",
        "xover_attack",
    },
    "infrastructure": {
        # Infrastructure and service tools
        "vastai",
        "billing",
        "email_report",
        "joplin",
        "tor",
        "transcribe",
        "document",
        "sessions",
        "config",
    },
}


class JWTAuthError(Exception):
    """Base exception for JWT authentication errors."""

    pass


class InvalidTokenError(JWTAuthError):
    """Raised when token is invalid or expired."""

    pass


class TokenExpiredError(JWTAuthError):
    """Raised when token has expired."""

    pass


class InsufficientPermissionsError(JWTAuthError):
    """Raised when user lacks permission to access tool."""

    pass


def _get_secret_key() -> str:
    """Get JWT secret key from environment variable.

    Returns:
        Secret key string from LOOM_JWT_SECRET environment variable.

    Raises:
        ValueError: If LOOM_JWT_SECRET is not configured.
    """
    secret = os.environ.get("LOOM_JWT_SECRET")
    if not secret:
        raise ValueError("LOOM_JWT_SECRET environment variable not set")
    return secret


def create_token(
    user_id: str,
    role: str,
    expires_in_hours: int = 24,
) -> str:
    """Generate JWT token for user with specified role.

    Args:
        user_id: Unique user identifier
        role: User role (admin, researcher, red_team, viewer)
        expires_in_hours: Token expiration time in hours (default: 24)

    Returns:
        Encoded JWT token string

    Raises:
        ValueError: If role is invalid or JWT library unavailable
        JWTAuthError: If token generation fails
    """
    if not jwt:
        raise ValueError("PyJWT library required. Install: pip install PyJWT")

    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Invalid role: {role}. Must be one of: {list(ROLE_PERMISSIONS.keys())}")

    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=expires_in_hours)

    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    try:
        secret = _get_secret_key()
        token = jwt.encode(payload, secret, algorithm="HS256")
        logger.info("token_created user_id=%s role=%s expires_in=%dh", user_id, role, expires_in_hours)
        return token
    except Exception as e:
        logger.error("token_creation_failed user_id=%s error=%s", user_id, str(e))
        raise JWTAuthError(f"Token creation failed: {str(e)}") from e


def validate_token(token: str) -> dict[str, Any]:
    """Validate JWT token and return payload.

    Args:
        token: JWT token string to validate

    Returns:
        Token payload dict with keys: sub, role, iat, exp

    Raises:
        ValueError: If JWT library unavailable
        InvalidTokenError: If token is malformed or signature invalid
        TokenExpiredError: If token has expired
    """
    if not jwt:
        raise ValueError("PyJWT library required. Install: pip install PyJWT")

    try:
        secret = _get_secret_key()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        logger.debug("token_validated user_id=%s role=%s", payload.get("sub"), payload.get("role"))
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.warning("token_expired token=%s...", token[:20])
        raise TokenExpiredError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        logger.warning("token_invalid error=%s", str(e))
        raise InvalidTokenError(f"Invalid token: {str(e)}") from e
    except Exception as e:
        logger.error("token_validation_failed error=%s", str(e))
        raise InvalidTokenError(f"Token validation failed: {str(e)}") from e


def get_allowed_tools(role: str) -> set[str]:
    """Get set of tools allowed for the given role.

    Args:
        role: User role (admin, researcher, red_team, viewer)

    Returns:
        Set of allowed tool names (or {"*"} for unrestricted access)

    Raises:
        ValueError: If role is invalid
    """
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Invalid role: {role}. Must be one of: {list(ROLE_PERMISSIONS.keys())}")

    return ROLE_PERMISSIONS[role]


def check_tool_access(token: str, tool_name: str) -> bool:
    """Check if token holder has access to specified tool.

    Args:
        token: JWT token string
        tool_name: Name of tool to access (e.g., "research_fetch", "prompt_reframe")

    Returns:
        True if user has access, False otherwise

    Raises:
        ValueError: If JWT library unavailable
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
    """
    payload = validate_token(token)
    role = payload.get("role")

    if not role:
        logger.warning("token_missing_role token=%s...", token[:20])
        return False

    allowed_tools = get_allowed_tools(role)

    # Admin and red_team have unrestricted access
    if "*" in allowed_tools:
        logger.debug(
            "tool_access_granted_unrestricted user_id=%s role=%s tool=%s",
            payload.get("sub"),
            role,
            tool_name,
        )
        return True

    # Check if tool is explicitly allowed
    if tool_name in allowed_tools:
        logger.debug(
            "tool_access_granted_explicit user_id=%s role=%s tool=%s",
            payload.get("sub"),
            role,
            tool_name,
        )
        return True

    logger.warning(
        "tool_access_denied user_id=%s role=%s tool=%s",
        payload.get("sub"),
        role,
        tool_name,
    )
    return False


def get_token_info(token: str) -> dict[str, Any]:
    """Get human-readable information about a token.

    Args:
        token: JWT token string

    Returns:
        Dict with token info: user_id, role, issued_at, expires_at,
        is_expired, allowed_tools_count, allowed_tool_categories

    Raises:
        ValueError: If JWT library unavailable
        InvalidTokenError: If token is invalid
    """
    payload = validate_token(token)
    role = payload.get("role", "unknown")
    allowed_tools = get_allowed_tools(role)

    iat_ts = payload.get("iat", 0)
    exp_ts = payload.get("exp", 0)

    issued_at = datetime.fromtimestamp(iat_ts, tz=UTC)
    expires_at = datetime.fromtimestamp(exp_ts, tz=UTC)
    is_expired = datetime.now(UTC) > expires_at

    # Determine which categories this role has access to
    allowed_categories = []
    for category, tools in TOOL_CATEGORIES.items():
        if "*" in allowed_tools or any(t in allowed_tools for t in tools):
            allowed_categories.append(category)

    return {
        "user_id": payload.get("sub"),
        "role": role,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "is_expired": is_expired,
        "allowed_tools_count": len(allowed_tools) if "*" not in allowed_tools else "unlimited",
        "allowed_tool_categories": allowed_categories,
    }


def verify_and_get_role(token: str) -> str:
    """Verify token and extract role (convenience function).

    Args:
        token: JWT token string

    Returns:
        User role string (admin, researcher, red_team, viewer)

    Raises:
        ValueError: If JWT library unavailable
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
    """
    payload = validate_token(token)
    return payload.get("role", "unknown")
