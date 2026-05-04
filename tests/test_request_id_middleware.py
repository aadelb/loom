"""Tests for request ID middleware."""

import pytest
from loom.request_id_middleware import RequestIdMiddleware, get_request_id, _request_id


@pytest.mark.asyncio
async def test_request_id_middleware_generates_uuid():
    """Test that middleware generates a UUID4 for requests without X-Request-ID."""
    generated_ids = []

    async def dummy_app(scope, receive, send):
        """Dummy ASGI app that records the request ID."""
        req_id = get_request_id()
        generated_ids.append(req_id)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestIdMiddleware(dummy_app)

    # Simulate HTTP request without X-Request-ID header
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
    }

    messages_sent = []

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        messages_sent.append(message)

    await middleware(scope, receive, send)

    # Verify a UUID was generated and stored
    assert len(generated_ids) == 1
    req_id = generated_ids[0]
    assert len(req_id) == 36  # UUID4 format
    assert req_id.count("-") == 4


@pytest.mark.asyncio
async def test_request_id_middleware_uses_header():
    """Test that middleware uses X-Request-ID header if provided."""
    generated_ids = []
    custom_id = "custom-request-123"

    async def dummy_app(scope, receive, send):
        """Dummy ASGI app that records the request ID."""
        req_id = get_request_id()
        generated_ids.append(req_id)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestIdMiddleware(dummy_app)

    # Simulate HTTP request WITH X-Request-ID header
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [(b"x-request-id", custom_id.encode())],
    }

    messages_sent = []

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        messages_sent.append(message)

    await middleware(scope, receive, send)

    # Verify the custom ID was used
    assert len(generated_ids) == 1
    assert generated_ids[0] == custom_id


@pytest.mark.asyncio
async def test_request_id_middleware_adds_to_response():
    """Test that middleware adds X-Request-ID to response headers."""
    response_headers = None

    async def dummy_app(scope, receive, send):
        """Dummy ASGI app."""
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    middleware = RequestIdMiddleware(dummy_app)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
    }

    messages_sent = []

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        nonlocal response_headers
        if message["type"] == "http.response.start":
            response_headers = message.get("headers", [])
        messages_sent.append(message)

    await middleware(scope, receive, send)

    # Verify X-Request-ID header was added to response
    assert response_headers is not None
    header_dict = dict(response_headers)
    assert b"x-request-id" in header_dict
    req_id = header_dict[b"x-request-id"].decode()
    assert len(req_id) == 36  # UUID4


@pytest.mark.asyncio
async def test_request_id_middleware_non_http():
    """Test that middleware passes through non-HTTP requests."""
    app_called = False

    async def dummy_app(scope, receive, send):
        nonlocal app_called
        app_called = True
        # WebSocket scope
        if scope["type"] == "websocket":
            await send({"type": "websocket.accept"})

    middleware = RequestIdMiddleware(dummy_app)

    scope = {"type": "websocket", "path": "/ws"}

    async def receive():
        return {"type": "websocket.receive"}

    async def send(message):
        pass

    await middleware(scope, receive, send)

    # Verify app was called
    assert app_called


def test_get_request_id_default():
    """Test that get_request_id returns empty string when context not set."""
    # Reset context
    token = _request_id.set("")
    try:
        assert get_request_id() == ""
    finally:
        _request_id.reset(token)
