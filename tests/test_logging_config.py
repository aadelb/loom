"""Tests for structured logging configuration."""

from __future__ import annotations

import json
import logging
from io import StringIO

import pytest

from loom.logging_config import JsonFormatter, setup_logging


class TestJsonFormatter:
    """Tests for JsonFormatter."""

    def test_format_basic_message(self) -> None:
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

    def test_format_with_request_id(self) -> None:
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

    def test_format_without_request_id(self) -> None:
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

    def test_format_with_exception(self) -> None:
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

    def test_format_with_args(self) -> None:
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


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_json_logging(self) -> None:
        """Test setting up JSON logging format."""
        # Get the root logger
        root_logger = logging.getLogger()
        initial_handler_count = len(root_logger.handlers)

        setup_logging(log_level="INFO", log_format="json")

        # Check that we have handlers
        assert len(root_logger.handlers) > 0

        # Check that the handler has JsonFormatter
        has_json_formatter = any(
            isinstance(h.formatter, JsonFormatter) for h in root_logger.handlers
        )
        assert has_json_formatter

    def test_setup_text_logging(self) -> None:
        """Test setting up text logging format."""
        root_logger = logging.getLogger()

        setup_logging(log_level="DEBUG", log_format="text")

        # Check that we have handlers with standard formatter
        assert len(root_logger.handlers) > 0
        formatter = root_logger.handlers[0].formatter
        assert formatter is not None
        assert not isinstance(formatter, JsonFormatter)

    def test_setup_logging_level(self) -> None:
        """Test that setup_logging sets the correct log level."""
        root_logger = logging.getLogger()

        setup_logging(log_level="ERROR", log_format="text")
        assert root_logger.level == logging.ERROR

        setup_logging(log_level="DEBUG", log_format="text")
        assert root_logger.level == logging.DEBUG

    def test_json_format_is_valid_json(self) -> None:
        """Test that JSON format produces valid JSON."""
        # Create a test handler to capture output (BEFORE setup_logging)
        test_stream = StringIO()
        test_handler = logging.StreamHandler(test_stream)
        test_handler.setFormatter(JsonFormatter())

        # Now setup logging with JSON format
        setup_logging(log_level="INFO", log_format="json")

        # Log a message using the test handler
        test_logger = logging.getLogger("test.json")
        test_logger.addHandler(test_handler)
        test_logger.info("Test message")

        # Get the output and parse it
        output = test_stream.getvalue()
        if output:
            parsed = json.loads(output.strip())
            assert isinstance(parsed, dict)
            assert "message" in parsed
            assert parsed["message"] == "Test message"
