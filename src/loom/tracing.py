"""Request-scoped tracing via contextvars.

Each MCP tool call gets a unique request_id. Downstream loggers pick it up
automatically through the ``RequestIdFilter`` installed on the root loom
logger.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")


def new_request_id() -> str:
    """Generate and set a fresh request ID in the current context."""
    rid = uuid.uuid4().hex[:16]
    REQUEST_ID.set(rid)
    return rid


def get_request_id() -> str:
    return REQUEST_ID.get("")


class RequestIdFilter(logging.Filter):
    """Inject ``request_id`` into every log record under the ``loom`` logger."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID.get("")  # type: ignore[attr-defined]
        return True


def install_tracing() -> None:
    """Install the RequestIdFilter on all root logger handlers."""
    root_logger = logging.getLogger()
    filter_instance = RequestIdFilter()
    # Add to all existing handlers
    for handler in root_logger.handlers:
        handler.addFilter(filter_instance)
    # Also add to root logger so any new handlers might get it (if they use the same formatter)
    root_logger.addFilter(filter_instance)
