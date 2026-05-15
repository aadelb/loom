"""OpenTelemetry distributed tracing integration for Loom MCP server.

Provides optional OTLP (OpenTelemetry Protocol) exporter with zero overhead when disabled.
Traces each tool execution with attributes: tool_name, duration_ms, success, error_type.
Propagates trace context across tool chains and exports metrics.

Configuration via environment variables:
    OTEL_ENABLED=true          Activate tracing (default: false, no overhead when disabled)
    OTEL_ENDPOINT=http://...   OTLP gRPC endpoint (default: http://localhost:4317)
    OTEL_SERVICE_NAME=loom-mcp Service identifier (default: loom-mcp)

Example usage in server.py _wrap_tool():
    from loom.otel import init_telemetry, get_tracer, record_tool_span

    # At server startup
    init_telemetry()

    # In _wrap_tool decorator
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(func.__name__) as span:
        record_tool_span(span, func, duration_ms, success, error)
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager, suppress
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger("loom.otel")

# Global state: set by init_telemetry()
_tracer_provider: Any = None
_tracer: Any = None
_span_processor: Any = None
_enabled: bool = False


def _check_otel_available() -> bool:
    """Verify OpenTelemetry packages are installed."""
    try:
        import opentelemetry  # noqa: F401
        import opentelemetry.sdk.trace  # noqa: F401
        return True
    except ImportError:
        return False


def init_telemetry() -> None:
    """Initialize OpenTelemetry with OTLP exporter if OTEL_ENABLED=true.

    Gracefully skips if packages are not installed or OTEL_ENABLED is false.
    Safe to call multiple times (idempotent).
    """
    global _tracer_provider, _tracer, _span_processor, _enabled

    # Check if telemetry is enabled
    if not os.environ.get("OTEL_ENABLED", "").lower() == "true":
        logger.debug("OpenTelemetry disabled (OTEL_ENABLED not set to true)")
        return

    # Check if packages are available
    if not _check_otel_available():
        logger.warning(
            "OpenTelemetry packages not installed. Skipping initialization. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-exporter-otlp"
        )
        return

    if _tracer_provider is not None:
        logger.debug("OpenTelemetry already initialized")
        return

    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource

        endpoint = os.environ.get("OTEL_ENDPOINT", "http://localhost:4317")
        service_name = os.environ.get("OTEL_SERVICE_NAME", "loom-mcp")

        # Create resource with service metadata
        resource = Resource(
            {
                "service.name": service_name,
                "service.version": "1.0.0",
            }
        )

        # Create tracer provider with resource
        _tracer_provider = TracerProvider(resource=resource)

        # Create OTLP exporter with configurable endpoint
        exporter = OTLPSpanExporter(endpoint=endpoint)

        # Add batch processor for efficient exporting
        _span_processor = BatchSpanProcessor(exporter)
        _tracer_provider.add_span_processor(_span_processor)

        # Get tracer instance
        _tracer = _tracer_provider.get_tracer("loom")

        _enabled = True
        logger.info(
            "OpenTelemetry initialized",
            extra={
                "endpoint": endpoint,
                "service_name": service_name,
            },
        )

    except Exception as e:
        logger.error(
            f"Failed to initialize OpenTelemetry: {e}",
            exc_info=True,
        )


def is_enabled() -> bool:
    """Check if OpenTelemetry tracing is active."""
    return _enabled


def get_tracer() -> Any:
    """Get the global tracer instance.

    Returns a no-op tracer if telemetry is disabled.
    Safe to call even if telemetry is disabled.
    """
    if _tracer is None:
        try:
            from opentelemetry import trace
            return trace.get_tracer("loom")
        except ImportError:
            # Return a no-op tracer
            return _NoOpTracer()

    return _tracer


def shutdown_telemetry() -> None:
    """Gracefully shutdown OpenTelemetry and flush pending spans."""
    global _tracer_provider, _span_processor, _tracer, _enabled

    if _tracer_provider is None:
        return

    try:
        if _span_processor is not None:
            _span_processor.shutdown()
        _tracer_provider.shutdown()
        logger.info("OpenTelemetry shutdown complete")
    except Exception as e:
        logger.error(f"Error during OpenTelemetry shutdown: {e}", exc_info=True)
    finally:
        _tracer_provider = None
        _span_processor = None
        _tracer = None
        _enabled = False


def record_tool_span(
    span: Any,
    tool_name: str,
    duration_ms: float,
    success: bool,
    error_type: str | None = None,
) -> None:
    """Record tool execution attributes in a span.

    Args:
        span: OpenTelemetry span instance
        tool_name: Name of the tool function
        duration_ms: Execution time in milliseconds
        success: Whether tool executed successfully
        error_type: Error class name if failed (e.g., "ValidationError")
    """
    if span is None:
        return

    with suppress(Exception):
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.duration_ms", duration_ms)
        span.set_attribute("tool.success", success)
        if error_type:
            span.set_attribute("tool.error_type", error_type)


@contextmanager
def tool_span(tool_name: str) -> Any:
    """Context manager for creating and managing a tool execution span.

    Usage:
        with tool_span("research_fetch") as span:
            result = await fetch(url)
            if span:
                record_tool_span(span, "research_fetch", duration_ms, success)

    Yields:
        OpenTelemetry span or None if telemetry disabled
    """
    tracer = get_tracer()
    if not is_enabled() or tracer is None:
        yield None
        return

    with suppress(Exception):
        with tracer.start_as_current_span(tool_name) as span:
            yield span
            return

    yield None


def trace_tool_execution(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to automatically trace tool execution with timing and error handling.

    Works with both sync and async functions.
    Gracefully handles missing OpenTelemetry packages.

    Usage:
        @trace_tool_execution
        async def research_fetch(url: str) -> dict:
            ...

        @trace_tool_execution
        def sync_tool(param: str) -> dict:
            ...

    Args:
        func: Tool function to wrap (sync or async)

    Returns:
        Wrapped function with OpenTelemetry tracing
    """
    import inspect

    is_async = inspect.iscoroutinefunction(func)

    if is_async:

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not is_enabled():
                return await func(*args, **kwargs)

            tracer = get_tracer()
            start_time = time.time()

            with suppress(Exception):
                with tracer.start_as_current_span(func.__name__) as span:
                    try:
                        result = await func(*args, **kwargs)
                        duration_ms = (time.time() - start_time) * 1000
                        record_tool_span(span, func.__name__, duration_ms, True)
                        return result
                    except Exception as e:
                        duration_ms = (time.time() - start_time) * 1000
                        record_tool_span(
                            span,
                            func.__name__,
                            duration_ms,
                            False,
                            error_type=type(e).__name__,
                        )
                        with suppress(Exception):
                            span.record_exception(e)
                        raise

            # Fallback if tracing fails
            return await func(*args, **kwargs)

        return async_wrapper

    else:

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not is_enabled():
                return func(*args, **kwargs)

            tracer = get_tracer()
            start_time = time.time()

            with suppress(Exception):
                with tracer.start_as_current_span(func.__name__) as span:
                    try:
                        result = func(*args, **kwargs)
                        duration_ms = (time.time() - start_time) * 1000
                        record_tool_span(span, func.__name__, duration_ms, True)
                        return result
                    except Exception as e:
                        duration_ms = (time.time() - start_time) * 1000
                        record_tool_span(
                            span,
                            func.__name__,
                            duration_ms,
                            False,
                            error_type=type(e).__name__,
                        )
                        with suppress(Exception):
                            span.record_exception(e)
                        raise

            # Fallback if tracing fails
            return func(*args, **kwargs)

        return sync_wrapper


class _NoOpTracer:
    """Minimal no-op tracer for when OpenTelemetry is disabled or unavailable.

    Implements just enough of the OpenTelemetry tracer interface to avoid errors.
    """

    def start_as_current_span(self, name: str) -> Any:
        """Return a no-op context manager."""
        return _NoOpSpan()

    def start_span(self, name: str) -> Any:
        """Return a no-op span."""
        return _NoOpSpan()


class _NoOpSpan:
    """Minimal no-op span that implements core span operations."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        """No-op attribute setter."""
        pass

    def record_exception(self, exception: Exception) -> None:
        """No-op exception recorder."""
        pass

    def add_event(self, name: str, **kwargs: Any) -> None:
        """No-op event adder."""
        pass

    def set_status(self, status: Any) -> None:
        """No-op status setter."""
        pass


__all__ = [
    "init_telemetry",
    "shutdown_telemetry",
    "is_enabled",
    "get_tracer",
    "record_tool_span",
    "tool_span",
    "trace_tool_execution",
]
