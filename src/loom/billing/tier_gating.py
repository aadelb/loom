"""Premium tool gating via tier-based decorator.

Provides @requires_tier(min_tier: str) decorator for gating premium tools
based on subscription tier. The decorator checks user tier from request context
or defaults to "free" tier (fail-open for development).

Example:
    @requires_tier("pro")
    async def research_dark_recon(target: str) -> dict:
        return {"dark_result": "..."}

    # Calling the tool:
    result = await research_dark_recon("example.com")
    # If user tier < pro: {"error": "upgrade_required", ...}
    # If user tier >= pro: {"dark_result": "..."}
"""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, TypeVar

from loom.billing.tiers import TIERS, get_tier

logger = logging.getLogger("loom.billing.tier_gating")

# Type variable for function signatures
F = TypeVar("F", bound=Callable[..., Any])

# Tier hierarchy for comparison
TIER_HIERARCHY = {
    "free": 0,
    "pro": 1,
    "team": 2,
    "enterprise": 3,
}


def _get_current_user_tier() -> str:
    """Get the current user's tier from request context.

    Returns "free" if no context is available (fail-open for development).
    In a production FastMCP/FastAPI context, this would extract tier from
    MCP auth token or HTTP request headers.

    Returns:
        Tier name: "free", "pro", "team", or "enterprise"
    """
    # TODO: In production, extract from:
    # - MCP ServerRequest context (auth token metadata)
    # - FastAPI request context (user principal)
    # - Environment variable for service-to-service calls
    try:
        from contextvars import ContextVar

        # If we had a context var, we'd check it here
        # user_context: ContextVar[dict] = ContextVar("user", default=None)
        # ctx = user_context.get()
        # if ctx and "tier" in ctx:
        #     return ctx["tier"]
        pass
    except Exception as e:
        logger.debug("Failed to get user context: %s", e)

    # Default to free tier (development/unauthenticated)
    return "free"


def _get_caller_name() -> str:
    """Get the name of the calling function.

    Returns:
        Function name or "unknown" if unavailable
    """
    try:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            return frame.f_back.f_code.co_name
    except Exception:
        pass
    return "unknown"


def _check_tier_access(
    required_tier: str, current_tier: str
) -> tuple[bool, dict[str, Any] | None]:
    """Check if current tier has access to required tier.

    Args:
        required_tier: Minimum tier required for the tool
        current_tier: Current user's subscription tier

    Returns:
        Tuple of (allowed: bool, error_response: dict | None)
        If allowed=True, error_response=None
        If allowed=False, error_response contains upgrade information
    """
    required_rank = TIER_HIERARCHY.get(required_tier.lower(), 0)
    current_rank = TIER_HIERARCHY.get(current_tier.lower(), 0)

    if current_rank >= required_rank:
        return (True, None)

    # User tier is insufficient; return upgrade error
    current_tier_obj = get_tier(current_tier)
    required_tier_obj = get_tier(required_tier)

    error = {
        "error": "upgrade_required",
        "current_tier": current_tier,
        "required_tier": required_tier,
        "current_tier_name": current_tier_obj.name,
        "required_tier_name": required_tier_obj.name,
        "upgrade_url": "https://loom.local/upgrade",
        "message": f"This tool requires {required_tier_obj.name} tier. You are on {current_tier_obj.name}.",
    }

    logger.warning(
        "tier_access_denied user_tier=%s required_tier=%s tool=%s",
        current_tier,
        required_tier,
        _get_caller_name(),
    )

    return (False, error)


def requires_tier(min_tier: str) -> Callable[[F], F]:
    """Decorator to gate premium tools by subscription tier.

    Checks the current user's tier (from request context or defaults to "free").
    If the user's tier is lower than min_tier, returns an error dict instead
    of executing the function.

    Works with both sync and async functions.

    Args:
        min_tier: Minimum tier required ("free", "pro", "team", "enterprise")

    Returns:
        Decorated function that enforces tier gating

    Example:
        @requires_tier("pro")
        async def research_dark_recon(target: str) -> dict:
            return {"result": "dark web data"}

        result = await research_dark_recon("example.com")
        # If user tier < pro: {"error": "upgrade_required", ...}
        # If user tier >= pro: {"result": "dark web data"}
    """
    # Validate min_tier
    if min_tier.lower() not in TIER_HIERARCHY:
        raise ValueError(
            f"Invalid min_tier: {min_tier}. Must be one of: {list(TIER_HIERARCHY.keys())}"
        )

    def decorator(func: F) -> F:
        # Check if function is async
        is_async = inspect.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                current_tier = _get_current_user_tier()
                allowed, error = _check_tier_access(min_tier, current_tier)

                if not allowed:
                    logger.info(
                        "tool_access_denied tier_required=%s user_tier=%s func=%s",
                        min_tier,
                        current_tier,
                        func.__name__,
                    )
                    return error

                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                current_tier = _get_current_user_tier()
                allowed, error = _check_tier_access(min_tier, current_tier)

                if not allowed:
                    logger.info(
                        "tool_access_denied tier_required=%s user_tier=%s func=%s",
                        min_tier,
                        current_tier,
                        func.__name__,
                    )
                    return error

                return func(*args, **kwargs)

            return sync_wrapper  # type: ignore

    return decorator
