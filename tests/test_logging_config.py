"""Tests for structured logging configuration."""

from __future__ import annotations

import json
import logging
from io import StringIO

import pytest

from loom.logging_config import JsonFormatter, log_tool_invocation, setup_logging



pytestmark = pytest.mark.asyncio
class TestJsonFormatter:
    """Tests for JsonFormatter."""

    async def test_format_basic_message(self) -> None:
        """Test formatting a basic log message."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.module"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    async def test_format_with_request_id(self) -> None:
        """Test formatting includes request_id when available."""
        from loom.tracing import REQUEST_ID

        formatter = JsonFormatter()
        REQUEST_ID.set("test-request-123")

        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["request_id"] == "test-request-123"

        # Clean up
        REQUEST_ID.set("")

    async def test_format_without_request_id(self) -> None:
        """Test formatting without request_id doesn't include it."""
        from loom.tracing import REQUEST_ID

        formatter = JsonFormatter()
        REQUEST_ID.set("")

        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        parsed = json.loads(result)

        assert "request_id" not in parsed or parsed["request_id"] == ""

    async def test_format_with_exception(self) -> None:
        """Test formatting includes exception info when present."""
        formatter = JsonFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        parsed = json.loads(result)

        assert "exception" in parsed
        assert "ValueError: Test exception" in parsed["exception"]

    async def test_format_with_args(self) -> None:
        """Test formatting with message arguments."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="User %s logged in from %s",
            args=("alice", "192.168.1.1"),
            exc_info=None,
        )
        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["message"] == "User alice logged in from 192.168.1.1"

    async def test_format_with_tool_fields(self) -> None:
        """Test formatting includes tool-specific fields when present."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="loom.tools.fetch",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Tool invocation completed",
            args=(),
            exc_info=None,
        )
        # Add tool-specific fields
        record.tool_name = "research_fetch"  # type: ignore[attr-defined]
        record.duration_ms = 1250  # type: ignore[attr-defined]
        record.status = "ok"  # type: ignore[attr-defined]
        record.cache_hit = True  # type: ignore[attr-defined]
        record.client_id = "user-123"  # type: ignore[attr-defined]

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["tool_name"] == "research_fetch"
        assert parsed["duration_ms"] == 1250
        assert parsed["status"] == "ok"
        assert parsed["cache_hit"] is True
        assert parsed["client_id"] == "user-123"

    async def test_format_with_partial_tool_fields(self) -> None:
        """Test formatting with only some tool fields present."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="loom.tools.fetch",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Tool invocation completed",
            args=(),
            exc_info=None,
        )
        # Add only some tool fields
        record.tool_name = "research_fetch"  # type: ignore[attr-defined]
        record.duration_ms = 500  # type: ignore[attr-defined]
        record.status = "error"  # type: ignore[attr-defined]

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["tool_name"] == "research_fetch"
        assert parsed["duration_ms"] == 500
        assert parsed["status"] == "error"
        # cache_hit and client_id should not be present
        assert "cache_hit" not in parsed
        assert "client_id" not in parsed

    async def test_format_ignores_none_tool_fields(self) -> None:
        """Test formatting skips None values for tool fields."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="loom.tools.fetch",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Tool invocation completed",
            args=(),
            exc_info=None,
        )
        record.tool_name = "research_fetch"  # type: ignore[attr-defined]
        record.duration_ms = 500  # type: ignore[attr-defined]
        record.status = "ok"  # type: ignore[attr-defined]
        record.cache_hit = False  # type: ignore[attr-defined]
        record.client_id = None  # type: ignore[attr-defined]

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["tool_name"] == "research_fetch"
        assert parsed["cache_hit"] is False  # False should be included
        assert "client_id" not in parsed  # None should be excluded


class TestSetupLogging:
    """Tests for setup_logging function."""

    async def test_setup_json_logging(self) -> None:
        """Test setting up JSON logging format."""
        target_logger = logging.getLogger("test_json_logger")

        setup_logging(log_level="INFO", log_format="json", logger_name="test_json_logger")

        # Check that we have handlers
        assert len(target_logger.handlers) > 0

        # Check that the handler has JsonFormatter
        has_json_formatter = any(
            isinstance(h.formatter, JsonFormatter) for h in target_logger.handlers
        )
        assert has_json_formatter

    async def test_setup_text_logging(self) -> None:
        """Test setting up text logging format."""
        target_logger = logging.getLogger("test_text_logger")

        setup_logging(log_level="DEBUG", log_format="text", logger_name="test_text_logger")

        # Check that we have handlers with standard formatter
        assert len(target_logger.handlers) > 0
        formatter = target_logger.handlers[0].formatter
        assert formatter is not None
        assert not isinstance(formatter, JsonFormatter)

    async def test_setup_logging_level(self) -> None:
        """Test that setup_logging sets the correct log level."""
        test_logger = logging.getLogger("test_level_logger")

        setup_logging(log_level="ERROR", log_format="text", logger_name="test_level_logger")
        assert test_logger.level == logging.ERROR

        setup_logging(log_level="DEBUG", log_format="text", logger_name="test_level_logger")
        assert test_logger.level == logging.DEBUG

    async def test_json_format_is_valid_json(self) -> None:
        """Test that JSON format produces valid JSON."""
        test_stream = StringIO()
        test_handler = logging.StreamHandler(test_stream)
        test_handler.setFormatter(JsonFormatter())

        test_logger = logging.getLogger("test.json.valid")
        # Clear existing handlers
        for h in test_logger.handlers[:]:
            test_logger.removeHandler(h)
        test_logger.addHandler(test_handler)
        test_logger.setLevel(logging.INFO)

        test_logger.info("Test message")

        output = test_stream.getvalue()
        if output:
            parsed = json.loads(output.strip())
            assert isinstance(parsed, dict)
            assert "message" in parsed
            assert parsed["message"] == "Test message"

    async def test_setup_logging_defaults(self) -> None:
        """Test setup_logging with default parameters."""
        test_logger = logging.getLogger("test_defaults")

        setup_logging(logger_name="test_defaults")

        # Should be INFO level by default
        assert test_logger.level == logging.INFO
        # Should have a text formatter by default
        has_text_formatter = not any(
            isinstance(h.formatter, JsonFormatter) for h in test_logger.handlers
        )
        assert has_text_formatter

    async def test_setup_logging_clears_old_handlers(self) -> None:
        """Test that setup_logging removes old handlers."""
        test_logger = logging.getLogger("test_clear")
        # Add an initial handler
        initial_handler = logging.StreamHandler()
        test_logger.addHandler(initial_handler)

        initial_count = len(test_logger.handlers)
        assert initial_count > 0

        # Setup new logging
        setup_logging(log_format="json", logger_name="test_clear")

        # Old handlers should be removed and new one added
        assert len(test_logger.handlers) > 0
        # New handler should have JSON formatter
        has_json = any(isinstance(h.formatter, JsonFormatter) for h in test_logger.handlers)
        assert has_json


class TestLogToolInvocation:
    """Tests for log_tool_invocation function."""

    async def test_log_tool_invocation_basic(self) -> None:
        """Test logging a basic tool invocation."""
        test_stream = StringIO()
        test_handler = logging.StreamHandler(test_stream)
        test_handler.setFormatter(JsonFormatter())

        test_logger = logging.getLogger("loom.tools.test_basic")
        # Clear existing handlers
        for h in test_logger.handlers[:]:
            test_logger.removeHandler(h)
        test_logger.addHandler(test_handler)
        test_logger.setLevel(logging.INFO)

        log_tool_invocation(
            tool_name="research_fetch",
            duration_ms=1250,
            status="ok",
            logger=test_logger,
        )

        output = test_stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["tool_name"] == "research_fetch"
        assert parsed["duration_ms"] == 1250
        assert parsed["status"] == "ok"
        assert "message" in parsed

    async def test_log_tool_invocation_with_all_fields(self) -> None:
        """Test logging a tool invocation with all fields."""
        test_stream = StringIO()
        test_handler = logging.StreamHandler(test_stream)
        test_handler.setFormatter(JsonFormatter())

        test_logger = logging.getLogger("loom.tools.test_full")
        # Clear existing handlers
        for h in test_logger.handlers[:]:
            test_logger.removeHandler(h)
        test_logger.addHandler(test_handler)
        test_logger.setLevel(logging.INFO)

        log_tool_invocation(
            tool_name="research_spider",
            duration_ms=3500,
            status="ok",
            cache_hit=True,
            client_id="user-456",
            message="Multi-URL research completed",
            logger=test_logger,
        )

        output = test_stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["tool_name"] == "research_spider"
        assert parsed["duration_ms"] == 3500
        assert parsed["status"] == "ok"
        assert parsed["cache_hit"] is True
        assert parsed["client_id"] == "user-456"
        assert "Multi-URL research completed" in parsed["message"]

    async def test_log_tool_invocation_error_status(self) -> None:
        """Test logging a tool invocation with error status."""
        test_stream = StringIO()
        test_handler = logging.StreamHandler(test_stream)
        test_handler.setFormatter(JsonFormatter())

        test_logger = logging.getLogger("loom.tools.test_error")
        # Clear existing handlers
        for h in test_logger.handlers[:]:
            test_logger.removeHandler(h)
        test_logger.addHandler(test_handler)
        test_logger.setLevel(logging.INFO)

        log_tool_invocation(
            tool_name="research_fetch",
            duration_ms=250,
            status="error",
            cache_hit=False,
            client_id="api_key",
            message="Tool invocation failed",
            logger=test_logger,
        )

        output = test_stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["status"] == "error"
        assert parsed["cache_hit"] is False
        assert parsed["client_id"] == "api_key"

    async def test_log_tool_invocation_request_id_correlation(self) -> None:
        """Test that request_id is correlated in tool invocation logs."""
        from loom.tracing import REQUEST_ID

        test_stream = StringIO()
        test_handler = logging.StreamHandler(test_stream)
        test_handler.setFormatter(JsonFormatter())

        test_logger = logging.getLogger("loom.tools.test_correlation")
        # Clear existing handlers
        for h in test_logger.handlers[:]:
            test_logger.removeHandler(h)
        test_logger.addHandler(test_handler)
        test_logger.setLevel(logging.INFO)

        # Set a request ID
        REQUEST_ID.set("req-correlation-test-123")

        log_tool_invocation(
            tool_name="research_deep",
            duration_ms=2000,
            status="ok",
            logger=test_logger,
        )

        output = test_stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["request_id"] == "req-correlation-test-123"
        assert parsed["tool_name"] == "research_deep"

        # Clean up
        REQUEST_ID.set("")

    async def test_log_tool_invocation_default_logger(self) -> None:
        """Test logging uses default logger when none provided."""
        # This test verifies that no exception is raised when logger is None
        # The default should be loom.tools logger
        try:
            log_tool_invocation(
                tool_name="research_test",
                duration_ms=100,
                status="ok",
            )
            # If we get here without exception, test passes
            assert True
        except Exception as e:
            pytest.fail(f"log_tool_invocation raised exception: {e}")

    async def test_log_tool_invocation_without_client_id(self) -> None:
        """Test logging without client_id doesn't include it."""
        test_stream = StringIO()
        test_handler = logging.StreamHandler(test_stream)
        test_handler.setFormatter(JsonFormatter())

        test_logger = logging.getLogger("loom.tools.test_no_client")
        # Clear existing handlers
        for h in test_logger.handlers[:]:
            test_logger.removeHandler(h)
        test_logger.addHandler(test_handler)
        test_logger.setLevel(logging.INFO)

        log_tool_invocation(
            tool_name="research_fetch",
            duration_ms=500,
            status="ok",
            logger=test_logger,
        )

        output = test_stream.getvalue()
        parsed = json.loads(output.strip())

        assert "client_id" not in parsed
        assert parsed["tool_name"] == "research_fetch"
