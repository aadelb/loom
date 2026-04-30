"""Example: Integrating structured logging into Loom tool wrappers.

This example shows how to add comprehensive logging to tool invocations
using the structured logging system defined in logging_config.py.

REQ-075: Every tool call logged with: tool_name, duration_ms, status,
         cache_hit, client_id. JSON format. Request ID correlation.
"""

import asyncio
import functools
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any

from loom.logging_config import log_tool_invocation
from loom.tracing import get_request_id

logger = logging.getLogger("loom.tools")


def wrap_tool_with_logging(
    func: Callable[..., Any],
    tool_name: str | None = None,
) -> Callable[..., Any]:
    """Wrap a tool function with structured logging.

    Logs every tool invocation with:
    - tool_name: Name of the tool
    - duration_ms: Execution time in milliseconds
    - status: "ok", "error", "timeout", or other status code
    - cache_hit: Whether result came from cache (if applicable)
    - client_id: Current request ID (client identifier)

    Args:
        func: Tool function to wrap
        tool_name: Name of tool (default: function name)

    Returns:
        Wrapped function with structured logging
    """
    actual_tool_name = tool_name or func.__name__

    is_async = inspect.iscoroutinefunction(func)

    if is_async:

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            status = "ok"
            cache_hit = False

            try:
                result = await func(*args, **kwargs)

                # Check if result came from cache (if result has _from_cache attr)
                if isinstance(result, dict) and "_from_cache" in result:
                    cache_hit = result.pop("_from_cache")
                elif hasattr(result, "_from_cache"):
                    cache_hit = result._from_cache

                return result

            except TimeoutError:
                status = "timeout"
                raise
            except Exception as e:
                status = "error"
                logger.error(
                    f"Tool {actual_tool_name} raised {type(e).__name__}",
                    exc_info=True,
                )
                raise

            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                client_id = get_request_id()

                log_tool_invocation(
                    tool_name=actual_tool_name,
                    duration_ms=duration_ms,
                    status=status,
                    cache_hit=cache_hit,
                    client_id=client_id if client_id else None,
                    logger=logger,
                )

        return async_wrapper

    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            status = "ok"
            cache_hit = False

            try:
                result = func(*args, **kwargs)

                # Check if result came from cache
                if isinstance(result, dict) and "_from_cache" in result:
                    cache_hit = result.pop("_from_cache")
                elif hasattr(result, "_from_cache"):
                    cache_hit = result._from_cache

                return result

            except TimeoutError:
                status = "timeout"
                raise
            except Exception as e:
                status = "error"
                logger.error(
                    f"Tool {actual_tool_name} raised {type(e).__name__}",
                    exc_info=True,
                )
                raise

            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                client_id = get_request_id()

                log_tool_invocation(
                    tool_name=actual_tool_name,
                    duration_ms=duration_ms,
                    status=status,
                    cache_hit=cache_hit,
                    client_id=client_id if client_id else None,
                    logger=logger,
                )

        return sync_wrapper


# ============================================================================
# Example Usage
# ============================================================================


async def example_async_tool(query: str) -> dict[str, Any]:
    """Example async tool that fetches research."""
    await asyncio.sleep(0.5)  # Simulate network call
    return {
        "query": query,
        "results": ["result1", "result2"],
        "count": 2,
    }


def example_sync_tool(query: str) -> dict[str, Any]:
    """Example sync tool that processes data."""
    time.sleep(0.3)  # Simulate work
    return {
        "query": query,
        "processed": True,
    }


async def example_cached_tool(query: str) -> dict[str, Any]:
    """Example tool that returns cached result."""
    await asyncio.sleep(0.1)
    return {
        "query": query,
        "results": ["cached"],
        "_from_cache": True,  # Indicate cache hit
    }


async def example_failing_tool(query: str) -> None:
    """Example tool that raises an error."""
    await asyncio.sleep(0.2)
    raise ValueError(f"Invalid query: {query}")


# ============================================================================
# Integration with Server
# ============================================================================


def create_wrapped_tool_registry() -> dict[str, Callable[..., Any]]:
    """Create a registry of wrapped tools with logging.

    This shows how to apply logging to tools during registration.
    """
    tools = {
        "example_async": wrap_tool_with_logging(
            example_async_tool, tool_name="example_async"
        ),
        "example_sync": wrap_tool_with_logging(
            example_sync_tool, tool_name="example_sync"
        ),
        "example_cached": wrap_tool_with_logging(
            example_cached_tool, tool_name="example_cached"
        ),
        "example_failing": wrap_tool_with_logging(
            example_failing_tool, tool_name="example_failing"
        ),
    }
    return tools


# ============================================================================
# Running Examples
# ============================================================================


async def main() -> None:
    """Demonstrate structured logging of tool invocations."""
    # Setup logging in JSON format for this example
    from loom.logging_config import setup_logging
    from loom.tracing import install_tracing, new_request_id

    setup_logging(log_level="INFO", log_format="json")
    install_tracing()

    # Create request ID for this batch
    new_request_id()

    # Get wrapped tools
    tools = create_wrapped_tool_registry()

    print("=" * 70)
    print("Example 1: Async tool (success)")
    print("=" * 70)
    try:
        result = await tools["example_async"]("test query")
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    print("=" * 70)
    print("Example 2: Sync tool (success)")
    print("=" * 70)
    try:
        result = tools["example_sync"]("another query")
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    print("=" * 70)
    print("Example 3: Cached result")
    print("=" * 70)
    try:
        result = await tools["example_cached"]("cached query")
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    print("=" * 70)
    print("Example 4: Tool that fails")
    print("=" * 70)
    try:
        result = await tools["example_failing"]("invalid")
        print(f"Result: {result}\n")
    except ValueError as e:
        print(f"Expected error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
