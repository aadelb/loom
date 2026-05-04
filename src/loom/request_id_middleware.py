"""Request ID / Correlation ID middleware for ASGI applications.

Generates or accepts X-Request-ID headers and stores in contextvars
for request-scoped access during logging and processing.
"""

import uuid
from contextvars import ContextVar
from typing import Any, Callable

_request_id: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get current request ID from context.

    Returns:
        Request ID string or empty string if not set.
    """
    return _request_id.get()


class RequestIdMiddleware:
    """ASGI middleware for request ID correlation tracking.

    Generates UUID4 request ID for each HTTP request (or uses X-Request-ID
    header if provided). Stores in contextvars for logging access and
    adds to response headers for client correlation.
    """

    def __init__(self, app: Any) -> None:
        """Initialize middleware with wrapped application.

        Args:
            app: ASGI application to wrap.
        """
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Any],
        send: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Process ASGI request/response cycle.

        Args:
            scope: ASGI scope dict (connection metadata)
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract or generate request ID
        headers = dict(scope.get("headers", []))
        req_id = headers.get(b"x-request-id", b"").decode().strip() or str(
            uuid.uuid4()
        )

        # Store in context
        token = _request_id.set(req_id)

        try:

            async def send_with_id(message: dict[str, Any]) -> None:
                """Inject X-Request-ID into response headers.

                Args:
                    message: ASGI send message
                """
                if message["type"] == "http.response.start":
                    headers_list = list(message.get("headers", []))
                    headers_list.append((b"x-request-id", req_id.encode()))
                    message["headers"] = headers_list

                await send(message)

            await self.app(scope, receive, send_with_id)
        finally:
            # Clean up context
            _request_id.reset(token)
