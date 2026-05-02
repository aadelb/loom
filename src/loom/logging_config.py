"""Structured logging configuration for Loom MCP server.

Provides JSON and text formatting options for logging. JSON format includes
structured fields like timestamp, level, logger, message, and optional request_id,
tool_name, duration_ms, status, cache_hit, and client_id for production deployments.

JSON Format:
    {
        "timestamp": "2025-04-29T14:30:45.123456+00:00",
        "level": "INFO",
        "logger": "loom.tools.fetch",
        "message": "Tool invocation completed",
        "request_id": "a1b2c3d4e5f6g7h8",
        "tool_name": "research_fetch",
        "duration_ms": 1250,
        "status": "ok",
        "cache_hit": true,
        "client_id": "user-123"
    }

Text Format:
    2025-04-29 14:30:45,123 - loom.tools.fetch - INFO - [a1b2c3d4e5f6g7h8] Tool invocation completed
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from loom.tracing import get_request_id


class JsonFormatter(logging.Formatter):
    """Format log records as JSON with structured fields.

    Includes timestamp, log level, logger name, message, request_id (if present),
    and optional tool-specific fields (tool_name, duration_ms, status, cache_hit,
    client_id) and exception info (if applicable).
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The LogRecord to format

        Returns:
            JSON-formatted log entry as string
        """
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request_id if available
        request_id = get_request_id()
        if request_id:
            log_entry["request_id"] = request_id

        # Include tool-specific fields if present
        tool_fields = ["tool_name", "duration_ms", "status", "cache_hit", "client_id"]
        for field in tool_fields:
            if hasattr(record, field):
                value = getattr(record, field)
                # Only include non-None values
                if value is not None:
                    log_entry[field] = value

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "text",
    logger_name: str = "loom",
) -> None:
    """Configure root logger with JSON or text formatting.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  Can be overridden by LOOM_LOG_LEVEL environment variable.
        log_format: "json" for JSON output, "text" for plain text (default: "text")
        logger_name: Logger to configure. Defaults to "loom" root logger.
    """
    # Allow environment variable to override log level
    log_level = os.environ.get("LOOM_LOG_LEVEL", log_level).upper()

    # Get the target logger (usually root or "loom")
    target_logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    target_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in target_logger.handlers[:]:
        target_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))

    # Set formatter based on log_format parameter
    formatter: logging.Formatter
    if log_format.lower() == "json":
        formatter = JsonFormatter()
    else:
        # Plain text format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    target_logger.addHandler(console_handler)


def log_tool_invocation(
    tool_name: str,
    duration_ms: int,
    status: str,
    cache_hit: bool = False,
    client_id: str | None = None,
    message: str = "Tool invocation completed",
    logger: logging.Logger | None = None,
) -> None:
    """Log a structured tool invocation record.

    Adds tool-specific fields to a log record for production tracing.

    Args:
        tool_name: Name of the tool that was invoked
        duration_ms: Execution duration in milliseconds
        status: Status code or outcome ("ok", "error", "timeout", etc.)
        cache_hit: Whether result came from cache (default: False)
        client_id: Client identifier (e.g., session ID, user ID, API key)
        message: Log message (default: "Tool invocation completed")
        logger: Logger instance to use (default: loom.tools)
    """
    if logger is None:
        logger = logging.getLogger("loom.tools")

    # Create a log record with extra fields
    extra: dict[str, Any] = {
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "status": status,
        "cache_hit": cache_hit,
    }

    if client_id:
        extra["client_id"] = client_id

    logger.info(message, extra=extra)
