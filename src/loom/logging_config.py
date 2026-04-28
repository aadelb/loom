"""Structured logging configuration for Loom MCP server.

Provides JSON and text formatting options for logging. JSON format includes
structured fields like timestamp, level, logger, message, and optional request_id.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from loom.tracing import get_request_id


class JsonFormatter(logging.Formatter):
    """Format log records as JSON with structured fields.

    Includes timestamp, log level, logger name, message, request_id (if present),
    and exception info (if applicable).
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

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO", log_format: str = "text") -> None:
    """Configure root logger with JSON or text formatting.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: "json" for JSON output, "text" for plain text (default)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))

    # Set formatter based on log_format
    if log_format.lower() == "json":
        formatter = JsonFormatter()
    else:
        # Plain text format with request_id support
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
