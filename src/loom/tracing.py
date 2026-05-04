"""Request-scoped tracing via contextvars.

Each MCP tool call gets a unique request_id. Downstream loggers pick it up
automatically through the ``RequestIdFilter`` installed on the root loom
logger.

All span attributes are scrubbed of PII before export.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from loom.pii_scrubber import scrub_dict, scrub_pii

REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")


def new_request_id() -> str:
    """Generate and set a fresh request ID in the current context."""
    rid = uuid.uuid4().hex[:16]
    REQUEST_ID.set(rid)
    return rid


def get_request_id() -> str:
    return REQUEST_ID.get("")


class RequestIdFilter(logging.Filter):
    """Inject ``request_id`` into every log record under the ``loom`` logger.

    Also scrubs PII from log messages before filtering.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID.get("")  # type: ignore[attr-defined]

        # Scrub PII from log message
        if isinstance(record.msg, str):
            record.msg = scrub_pii(record.msg)

        # Scrub PII from log args if they are strings
        if record.args:
            if isinstance(record.args, dict):
                record.args = scrub_dict(record.args)
            elif isinstance(record.args, (tuple, list)):
                scrubbed_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        scrubbed_args.append(scrub_pii(arg))
                    else:
                        scrubbed_args.append(arg)
                record.args = tuple(scrubbed_args)

        return True


def install_tracing() -> None:
    """Install the RequestIdFilter on all root logger handlers.

    The filter injects request_id into all log records and scrubs PII.
    """
    root_logger = logging.getLogger()
    filter_instance = RequestIdFilter()
    # Add to all existing handlers
    for handler in root_logger.handlers:
        handler.addFilter(filter_instance)
    # Also add to root logger so any new handlers might get it (if they use the same formatter)
    root_logger.addFilter(filter_instance)
