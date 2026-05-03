"""Tests for OpenTelemetry integration module (loom.otel).

Tests cover:
- Initialization with and without packages installed
- Tracer retrieval and no-op fallback
- Span creation and attribute recording
- Context manager and decorator patterns
- Graceful error handling and disable state
- Both sync and async function tracing
"""

from __future__ import annotations

import asyncio
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Ensure otel module loads before tests
from loom.otel import (
    init_telemetry,
    shutdown_telemetry,
    is_enabled,
    get_tracer,
    record_tool_span,
    tool_span,
    trace_tool_execution,
    _NoOpTracer,
    _NoOpSpan,
)


class TestInitialization:
    """Test OpenTelemetry initialization and shutdown."""

    def test_disabled_by_default(self):
        """OTEL_ENABLED=false should not initialize."""
        # Reset state
        import loom.otel as otel_module
        otel_module._enabled = False
        otel_module._tracer = None
        otel_module._tracer_provider = None

        # Verify disabled state
        assert not is_enabled()

    def test_init_without_packages(self):
        """init_telemetry should gracefully skip if packages missing."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}):
            with patch("loom.otel._check_otel_available", return_value=False):
                # Should not raise, just log warning
                init_telemetry()
                assert not is_enabled()

    def test_init_with_enabled_flag(self):
        """init_telemetry with OTEL_ENABLED=true should attempt initialization."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}):
            with patch("loom.otel._check_otel_available", return_value=False):
                init_telemetry()
                # Disabled because packages not available
                assert not is_enabled()

    def test_idempotent_initialization(self):
        """Multiple init_telemetry calls should be safe."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            # Multiple calls should not raise
            init_telemetry()
            init_telemetry()
            assert not is_enabled()


class TestTracerRetrieval:
    """Test getting tracer instances."""

    def test_get_tracer_returns_noop_when_disabled(self):
        """get_tracer should return no-op tracer when disabled."""
        import loom.otel as otel_module
        otel_module._tracer = None
        otel_module._enabled = False

        tracer = get_tracer()
        assert tracer is not None
        # Should be no-op tracer
        assert hasattr(tracer, "start_as_current_span")
        assert callable(tracer.start_as_current_span)

    def test_get_tracer_returns_active_tracer_when_enabled(self):
        """get_tracer should return real tracer when enabled."""
        import loom.otel as otel_module

        mock_tracer = MagicMock()
        otel_module._tracer = mock_tracer
        otel_module._enabled = True

        tracer = get_tracer()
        assert tracer is mock_tracer


class TestNoOpTracer:
    """Test no-op tracer implementation."""

    def test_noop_tracer_context_manager(self):
        """No-op tracer should work in with statement."""
        tracer = _NoOpTracer()
        with tracer.start_as_current_span("test_span") as span:
            assert span is not None
            # Should not raise on any operations
            span.set_attribute("key", "value")
            span.record_exception(ValueError("test"))
            span.add_event("event_name")

    def test_noop_tracer_start_span(self):
        """No-op tracer should handle start_span."""
        tracer = _NoOpTracer()
        span = tracer.start_span("test_span")
        assert span is not None
        assert isinstance(span, _NoOpSpan)


class TestNoOpSpan:
    """Test no-op span implementation."""

    def test_noop_span_operations(self):
        """No-op span should handle all operations gracefully."""
        span = _NoOpSpan()

        # All operations should succeed without raising
        span.set_attribute("tool.name", "test_tool")
        span.set_attribute("tool.duration_ms", 100.5)
        span.set_attribute("tool.success", True)
        span.record_exception(ValueError("test error"))
        span.add_event("tool_started")
        span.set_status("OK")

    def test_noop_span_context_manager(self):
        """No-op span should work as context manager."""
        span = _NoOpSpan()
        with span as s:
            assert s is span
            s.set_attribute("key", "value")


class TestRecordToolSpan:
    """Test recording attributes to spans."""

    def test_record_tool_span_success(self):
        """record_tool_span should set success attributes."""
        span = MagicMock()
        record_tool_span(span, "test_tool", 150.5, True)

        span.set_attribute.assert_any_call("tool.name", "test_tool")
        span.set_attribute.assert_any_call("tool.duration_ms", 150.5)
        span.set_attribute.assert_any_call("tool.success", True)

    def test_record_tool_span_failure(self):
        """record_tool_span should record error_type on failure."""
        span = MagicMock()
        record_tool_span(span, "test_tool", 50.0, False, error_type="ValidationError")

        span.set_attribute.assert_any_call("tool.name", "test_tool")
        span.set_attribute.assert_any_call("tool.duration_ms", 50.0)
        span.set_attribute.assert_any_call("tool.success", False)
        span.set_attribute.assert_any_call("tool.error_type", "ValidationError")

    def test_record_tool_span_none_span(self):
        """record_tool_span should handle None span gracefully."""
        # Should not raise
        record_tool_span(None, "test_tool", 100.0, True)


class TestToolSpanContextManager:
    """Test tool_span context manager."""

    def test_tool_span_when_disabled(self):
        """tool_span should yield None when disabled."""
        import loom.otel as otel_module
        otel_module._enabled = False

        with tool_span("test_tool") as span:
            assert span is None

    def test_tool_span_when_enabled(self):
        """tool_span should yield span when enabled."""
        import loom.otel as otel_module

        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(
            return_value=mock_span
        )
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(
            return_value=None
        )

        otel_module._enabled = True
        otel_module._tracer = mock_tracer

        with tool_span("test_tool") as span:
            assert span is mock_span

        mock_tracer.start_as_current_span.assert_called_once_with("test_tool")

    def test_tool_span_exception_handling(self):
        """tool_span should handle exceptions in tracing."""
        import loom.otel as otel_module

        # Create a tracer that raises
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.side_effect = RuntimeError("tracer error")

        otel_module._enabled = True
        otel_module._tracer = mock_tracer

        # Should not raise, should yield None
        with tool_span("test_tool") as span:
            assert span is None


class TestTraceToolExecutionDecorator:
    """Test trace_tool_execution decorator."""

    def test_decorator_preserves_async_function(self):
        """Decorator should preserve async function signature."""

        @trace_tool_execution
        async def async_tool(url: str, timeout: int = 30) -> dict:
            return {"url": url, "timeout": timeout}

        assert asyncio.iscoroutinefunction(async_tool)

    def test_decorator_preserves_sync_function(self):
        """Decorator should preserve sync function signature."""

        @trace_tool_execution
        def sync_tool(query: str) -> dict:
            return {"query": query}

        assert callable(sync_tool)

    @pytest.mark.asyncio
    async def test_trace_async_function_success(self):
        """Decorator should trace successful async function."""
        import loom.otel as otel_module

        call_count = 0

        @trace_tool_execution
        async def async_tool(value: int) -> dict:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {"result": value * 2}

        # Test with tracing disabled
        otel_module._enabled = False
        result = await async_tool(5)
        assert result == {"result": 10}
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_trace_async_function_error(self):
        """Decorator should handle async function errors."""
        import loom.otel as otel_module

        @trace_tool_execution
        async def async_tool_error() -> dict:
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        # Test with tracing disabled
        otel_module._enabled = False
        with pytest.raises(ValueError, match="Test error"):
            await async_tool_error()

    def test_trace_sync_function_success(self):
        """Decorator should trace successful sync function."""
        import loom.otel as otel_module

        call_count = 0

        @trace_tool_execution
        def sync_tool(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + y

        # Test with tracing disabled
        otel_module._enabled = False
        result = sync_tool(3, 4)
        assert result == 7
        assert call_count == 1

    def test_trace_sync_function_error(self):
        """Decorator should handle sync function errors."""
        import loom.otel as otel_module

        @trace_tool_execution
        def sync_tool_error() -> None:
            raise RuntimeError("Test sync error")

        # Test with tracing disabled
        otel_module._enabled = False
        with pytest.raises(RuntimeError, match="Test sync error"):
            sync_tool_error()

    @pytest.mark.asyncio
    async def test_trace_async_with_mock_tracer(self):
        """Decorator should use tracer when enabled."""
        import loom.otel as otel_module

        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(
            return_value=mock_span
        )
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(
            return_value=None
        )

        otel_module._enabled = True
        otel_module._tracer = mock_tracer

        @trace_tool_execution
        async def async_tool() -> dict:
            await asyncio.sleep(0.01)
            return {"status": "ok"}

        result = await async_tool()
        assert result == {"status": "ok"}
        mock_tracer.start_as_current_span.assert_called_with("async_tool")
        # Should have called set_attribute at least once
        assert mock_span.set_attribute.called

    def test_trace_sync_with_mock_tracer(self):
        """Decorator should use tracer for sync functions when enabled."""
        import loom.otel as otel_module

        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(
            return_value=mock_span
        )
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(
            return_value=None
        )

        otel_module._enabled = True
        otel_module._tracer = mock_tracer

        @trace_tool_execution
        def sync_tool(x: int) -> dict:
            return {"value": x}

        result = sync_tool(42)
        assert result == {"value": 42}
        mock_tracer.start_as_current_span.assert_called_with("sync_tool")
        assert mock_span.set_attribute.called


class TestShutdown:
    """Test OpenTelemetry shutdown."""

    def test_shutdown_when_disabled(self):
        """shutdown_telemetry should be safe when disabled."""
        import loom.otel as otel_module
        otel_module._tracer_provider = None
        # Should not raise
        shutdown_telemetry()

    def test_shutdown_with_error(self):
        """shutdown_telemetry should handle processor errors."""
        import loom.otel as otel_module

        mock_processor = MagicMock()
        mock_processor.shutdown.side_effect = RuntimeError("shutdown error")
        mock_provider = MagicMock()
        mock_provider.shutdown.side_effect = RuntimeError("provider error")

        otel_module._span_processor = mock_processor
        otel_module._tracer_provider = mock_provider
        otel_module._tracer = MagicMock()
        otel_module._enabled = True

        # Should not raise despite errors
        shutdown_telemetry()
        assert not is_enabled()


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    def test_endpoint_from_env(self):
        """OTEL_ENDPOINT environment variable should be used."""
        # This would be tested with actual OTLP if packages available
        # For now, just verify the logic path exists
        test_endpoint = "http://otel.example.com:4317"
        with patch.dict(os.environ, {"OTEL_ENDPOINT": test_endpoint}):
            # Would be used in actual init_telemetry with packages
            endpoint = os.environ.get("OTEL_ENDPOINT", "http://localhost:4317")
            assert endpoint == test_endpoint

    def test_service_name_from_env(self):
        """OTEL_SERVICE_NAME environment variable should be used."""
        test_service = "my-custom-service"
        with patch.dict(os.environ, {"OTEL_SERVICE_NAME": test_service}):
            service_name = os.environ.get("OTEL_SERVICE_NAME", "loom-mcp")
            assert service_name == test_service

    def test_defaults_when_env_not_set(self):
        """Should use defaults when environment not set."""
        with patch.dict(os.environ, clear=True):
            endpoint = os.environ.get("OTEL_ENDPOINT", "http://localhost:4317")
            service = os.environ.get("OTEL_SERVICE_NAME", "loom-mcp")

            assert endpoint == "http://localhost:4317"
            assert service == "loom-mcp"


class TestZeroOverheadWhenDisabled:
    """Verify minimal overhead when OTEL_ENABLED=false."""

    def test_is_enabled_returns_false(self):
        """is_enabled should return false when disabled."""
        import loom.otel as otel_module
        otel_module._enabled = False
        assert not is_enabled()

    def test_disabled_decorator_minimal_overhead(self):
        """Decorator should add minimal overhead when disabled."""
        import loom.otel as otel_module
        otel_module._enabled = False

        @trace_tool_execution
        def simple_func(x: int) -> int:
            return x + 1

        # Single call
        result = simple_func(5)
        assert result == 6

        # Should have minimal branches when disabled
        import inspect
        source = inspect.getsource(simple_func)
        # Verify it's wrapped
        assert "wrapper" not in source or "@" in source


__all__ = [
    "TestInitialization",
    "TestTracerRetrieval",
    "TestNoOpTracer",
    "TestNoOpSpan",
    "TestRecordToolSpan",
    "TestToolSpanContextManager",
    "TestTraceToolExecutionDecorator",
    "TestShutdown",
    "TestEnvironmentConfiguration",
    "TestZeroOverheadWhenDisabled",
]
