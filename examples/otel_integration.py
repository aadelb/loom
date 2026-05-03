"""Integration examples for OpenTelemetry distributed tracing in Loom.

These examples show how to integrate OpenTelemetry tracing with:
1. Tool execution in server.py
2. Async tools with proper span management
3. Error handling and exception recording
4. Custom attributes beyond standard tool attributes
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from loom.otel import (
    init_telemetry,
    shutdown_telemetry,
    get_tracer,
    record_tool_span,
    tool_span,
    trace_tool_execution,
)


# ═════════════════════════════════════════════════════════════════════════════
# Example 1: Simple Decorator Usage
# ═════════════════════════════════════════════════════════════════════════════


@trace_tool_execution
async def research_fetch(url: str) -> dict:
    """Fetch URL with automatic OpenTelemetry tracing.

    The decorator automatically:
    - Creates a span named "research_fetch"
    - Records duration in milliseconds
    - Captures exceptions with error type
    - Sets success/failure status

    No additional code needed for tracing.
    """
    await asyncio.sleep(0.1)  # Simulate fetch
    return {"url": url, "status": 200, "content_length": 1024}


@trace_tool_execution
def sync_search_tool(query: str) -> dict:
    """Synchronous tool with automatic tracing.

    Works the same for sync functions.
    """
    time.sleep(0.05)  # Simulate search
    return {"query": query, "results": 42}


# ═════════════════════════════════════════════════════════════════════════════
# Example 2: Context Manager with Fine-Grained Control
# ═════════════════════════════════════════════════════════════════════════════


async def research_spider(urls: list[str]) -> dict:
    """Fetch multiple URLs with detailed span management.

    The context manager pattern gives you:
    - Direct span access for custom attributes
    - Manual timing control
    - Exception handling with span recording
    """
    start = time.time()

    with tool_span("research_spider") as span:
        try:
            fetched = []
            for url in urls:
                result = await research_fetch(url)
                fetched.append(result)

            # Record success with duration
            duration_ms = (time.time() - start) * 1000
            record_tool_span(span, "research_spider", duration_ms, True)

            # Add custom attributes to span
            if span:
                span.set_attribute("spider.urls_fetched", len(fetched))
                span.set_attribute("spider.total_size", sum(r.get("content_length", 0) for r in fetched))

            return {
                "urls": len(fetched),
                "results": fetched,
            }

        except Exception as e:
            # Record failure with error type
            duration_ms = (time.time() - start) * 1000
            record_tool_span(
                span,
                "research_spider",
                duration_ms,
                False,
                error_type=type(e).__name__,
            )
            raise


# ═════════════════════════════════════════════════════════════════════════════
# Example 3: Integration with server.py _wrap_tool
# ═════════════════════════════════════════════════════════════════════════════


def create_traced_wrapper(func: callable) -> callable:
    """Factory to create a traced wrapper for any tool function.

    This pattern can be used in server.py's _wrap_tool() to add
    OpenTelemetry tracing to all tools automatically.

    Usage in server.py:

        def _wrap_tool(func, category=None):
            # ... existing code ...
            func = create_traced_wrapper(func)
            # ... rest of wrapping ...
    """
    import functools
    import inspect

    is_async = inspect.iscoroutinefunction(func)

    if is_async:

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            with tool_span(func.__name__) as span:
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start) * 1000
                    record_tool_span(span, func.__name__, duration_ms, True)
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start) * 1000
                    record_tool_span(
                        span,
                        func.__name__,
                        duration_ms,
                        False,
                        error_type=type(e).__name__,
                    )
                    raise

        return async_wrapper

    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            with tool_span(func.__name__) as span:
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start) * 1000
                    record_tool_span(span, func.__name__, duration_ms, True)
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start) * 1000
                    record_tool_span(
                        span,
                        func.__name__,
                        duration_ms,
                        False,
                        error_type=type(e).__name__,
                    )
                    raise

        return sync_wrapper


# ═════════════════════════════════════════════════════════════════════════════
# Example 4: Tool with Custom Span Attributes
# ═════════════════════════════════════════════════════════════════════════════


async def research_deep(query: str, include_analysis: bool = True) -> dict:
    """Deep research with custom span attributes beyond tool.* namespace.

    Demonstrates adding domain-specific attributes to traces for better
    observability and debugging.
    """
    start = time.time()

    with tool_span("research_deep") as span:
        try:
            # Simulate deep research stages
            search_results = await research_fetch(f"https://search.example.com?q={query}")

            # Add custom attributes during execution
            if span:
                span.set_attribute("research.query", query)
                span.set_attribute("research.stage", "search_completed")
                span.add_event("search_completed", {"results": len(search_results)})

            # Fetch top results
            urls = [search_results["url"]]  # Simplified
            fetched = await research_spider(urls)

            if span:
                span.set_attribute("research.stage", "fetch_completed")
                span.set_attribute("research.fetched_urls", len(fetched))
                span.add_event("fetch_completed")

            # Optional analysis
            if include_analysis:
                if span:
                    span.set_attribute("research.analysis", "enabled")
                analysis = {"quality_score": 0.95}
            else:
                if span:
                    span.set_attribute("research.analysis", "disabled")
                analysis = {}

            duration_ms = (time.time() - start) * 1000
            record_tool_span(span, "research_deep", duration_ms, True)

            return {
                "query": query,
                "results": fetched,
                "analysis": analysis,
            }

        except Exception as e:
            if span:
                span.set_attribute("research.stage", "error")
            duration_ms = (time.time() - start) * 1000
            record_tool_span(
                span, "research_deep", duration_ms, False, error_type=type(e).__name__
            )
            raise


# ═════════════════════════════════════════════════════════════════════════════
# Example 5: Server Startup and Shutdown
# ═════════════════════════════════════════════════════════════════════════════


async def main_with_tracing() -> None:
    """Complete example: Initialize tracing, run tools, shutdown gracefully."""

    # Initialize OpenTelemetry (safe if disabled or packages missing)
    init_telemetry()

    try:
        # Run tools
        print("Fetching URL...")
        result1 = await research_fetch("https://example.com")
        print(f"  Result: {result1}")

        print("\nSearching...")
        result2 = sync_search_tool("python opentelemetry")
        print(f"  Result: {result2}")

        print("\nSpidering URLs...")
        result3 = await research_spider(
            [
                "https://example.com/1",
                "https://example.com/2",
            ]
        )
        print(f"  Result: {result3}")

        print("\nDeep research...")
        result4 = await research_deep("distributed tracing")
        print(f"  Result: {result4}")

    finally:
        # Always shutdown telemetry to flush pending spans
        shutdown_telemetry()
        print("\nOpenTelemetry shutdown complete")


# ═════════════════════════════════════════════════════════════════════════════
# Example 6: Error Handling with Tracing
# ═════════════════════════════════════════════════════════════════════════════


@trace_tool_execution
async def research_fetch_with_errors(url: str) -> dict:
    """Tool that demonstrates error handling and exception tracing."""
    if "invalid" in url.lower():
        raise ValueError(f"Invalid URL: {url}")
    if url.startswith("http://forbidden"):
        raise PermissionError("Access forbidden")

    await asyncio.sleep(0.05)
    return {"url": url, "status": 200}


async def example_error_handling() -> None:
    """Show how exceptions are captured in traces."""
    init_telemetry()

    try:
        # This will be traced as a failure with error_type="ValueError"
        await research_fetch_with_errors("https://invalid.example.com")
    except ValueError:
        print("ValueError caught and traced")

    try:
        # This will be traced as a failure with error_type="PermissionError"
        await research_fetch_with_errors("http://forbidden.example.com")
    except PermissionError:
        print("PermissionError caught and traced")

    shutdown_telemetry()


# ═════════════════════════════════════════════════════════════════════════════
# Example 7: Conditional Tracing (Production vs Development)
# ═════════════════════════════════════════════════════════════════════════════


async def main_production_aware() -> None:
    """Initialize tracing only in production environments."""

    # Typically set via environment
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    if is_production:
        # Enable tracing in production
        os.environ["OTEL_ENABLED"] = "true"
        init_telemetry()
        print("Production mode: OpenTelemetry enabled")
    else:
        print("Development mode: OpenTelemetry disabled (zero overhead)")

    try:
        # Same code works regardless of tracing state
        result = await research_fetch("https://example.com")
        print(f"Result: {result}")
    finally:
        shutdown_telemetry()


# ═════════════════════════════════════════════════════════════════════════════
# Running Examples
# ═════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    # To run these examples with actual tracing:
    #
    # 1. Start Jaeger collector:
    #    docker run -d -p 4317:4317 -p 16686:16686 jaegertracing/all-in-one
    #
    # 2. Enable tracing:
    #    export OTEL_ENABLED=true
    #    export OTEL_ENDPOINT=http://localhost:4317
    #
    # 3. Run this script:
    #    python examples/otel_integration.py
    #
    # 4. View traces at http://localhost:16686

    print("Example 1: Decorator Usage")
    print("-" * 60)
    asyncio.run(main_with_tracing())

    print("\n\nExample 2: Error Handling")
    print("-" * 60)
    asyncio.run(example_error_handling())

    print("\n\nExample 3: Production-Aware Setup")
    print("-" * 60)
    asyncio.run(main_production_aware())
