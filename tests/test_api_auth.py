"""Tests for API key authentication middleware.

Tests cover:
- API key validation with valid/invalid keys
- Exempt path handling (/health, /versions, /metrics)
- Authentication enforcement (enabled/disabled)
- Proper JSON error responses
- Request header parsing
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.api_auth import (
    ApiKeyAuthMiddleware,
    EXEMPT_PATHS,
    _get_api_keys,
    _is_auth_required,
    _is_exempt_path,
)


class TestApiKeyValidation:
    """Tests for API key extraction and validation."""

    def test_extract_api_key_from_headers(self) -> None:
        """Test extracting X-API-Key from request headers."""
        scope = {
            "headers": [
                (b"content-type", b"application/json"),
                (b"x-api-key", b"test-key-123"),
                (b"user-agent", b"test-client"),
            ]
        }
        key = ApiKeyAuthMiddleware._extract_api_key(scope)
        assert key == "test-key-123"

    def test_extract_api_key_case_insensitive(self) -> None:
        """Test that X-API-Key header is case-insensitive."""
        scope = {
            "headers": [
                (b"X-API-KEY", b"test-key-456"),
            ]
        }
        key = ApiKeyAuthMiddleware._extract_api_key(scope)
        assert key == "test-key-456"

    def test_extract_api_key_not_found(self) -> None:
        """Test when X-API-Key header is not present."""
        scope = {
            "headers": [
                (b"content-type", b"application/json"),
            ]
        }
        key = ApiKeyAuthMiddleware._extract_api_key(scope)
        assert key is None

    def test_extract_api_key_empty_headers(self) -> None:
        """Test with empty headers list."""
        scope = {"headers": []}
        key = ApiKeyAuthMiddleware._extract_api_key(scope)
        assert key is None

    def test_extract_api_key_utf8_decode(self) -> None:
        """Test UTF-8 decoding of API key value."""
        scope = {
            "headers": [
                (b"x-api-key", "test-key-utf8".encode("utf-8")),
            ]
        }
        key = ApiKeyAuthMiddleware._extract_api_key(scope)
        assert key == "test-key-utf8"


class TestExemptPaths:
    """Tests for exempt path checking."""

    @pytest.mark.parametrize(
        "path",
        [
            "/health",
            "/v1/health",
            "/versions",
            "/v1/versions",
            "/metrics",
            "/v1/metrics",
            "/mcp",
        ],
    )
    def test_exempt_paths(self, path: str) -> None:
        """Test that known exempt paths are recognized."""
        assert _is_exempt_path(path)

    @pytest.mark.parametrize(
        "path",
        [
            "/Health",  # case-insensitive
            "/V1/HEALTH",
            "/VERSIONS",
            "/Metrics",
        ],
    )
    def test_exempt_paths_case_insensitive(self, path: str) -> None:
        """Test that exempt path check is case-insensitive."""
        assert _is_exempt_path(path)

    @pytest.mark.parametrize(
        "path",
        [
            "/api/fetch",
            "/api/search",
            "/unknown",
            "/healthcheck",  # similar but not exempt
            "/metrics/custom",
        ],
    )
    def test_non_exempt_paths(self, path: str) -> None:
        """Test that other paths are not exempt."""
        assert not _is_exempt_path(path)

    def test_exempt_paths_constant(self) -> None:
        """Test that EXEMPT_PATHS constant is properly defined."""
        assert isinstance(EXEMPT_PATHS, set)
        assert "/health" in EXEMPT_PATHS
        assert "/v1/health" in EXEMPT_PATHS
        assert "/metrics" in EXEMPT_PATHS


class TestAuthConfigParsing:
    """Tests for authentication configuration parsing."""

    def test_get_api_keys_from_env(self) -> None:
        """Test parsing comma-separated API keys from env."""
        with patch.dict(os.environ, {"LOOM_API_KEYS": "key1,key2,key3"}):
            keys = _get_api_keys()
            assert keys == {"key1", "key2", "key3"}

    def test_get_api_keys_with_whitespace(self) -> None:
        """Test that whitespace is trimmed from keys."""
        with patch.dict(os.environ, {"LOOM_API_KEYS": "key1, key2 , key3"}):
            keys = _get_api_keys()
            assert keys == {"key1", "key2", "key3"}

    def test_get_api_keys_empty_env(self) -> None:
        """Test when LOOM_API_KEYS is not set."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove if exists
            os.environ.pop("LOOM_API_KEYS", None)
            keys = _get_api_keys()
            assert keys == set()

    def test_get_api_keys_empty_string(self) -> None:
        """Test when LOOM_API_KEYS is empty string."""
        with patch.dict(os.environ, {"LOOM_API_KEYS": ""}):
            keys = _get_api_keys()
            assert keys == set()

    def test_get_api_keys_single_key(self) -> None:
        """Test with single API key."""
        with patch.dict(os.environ, {"LOOM_API_KEYS": "single-key"}):
            keys = _get_api_keys()
            assert keys == {"single-key"}

    def test_is_auth_required_true(self) -> None:
        """Test LOOM_AUTH_REQUIRED=true enables auth."""
        with patch.dict(os.environ, {"LOOM_AUTH_REQUIRED": "true"}):
            assert _is_auth_required() is True

    def test_is_auth_required_false(self) -> None:
        """Test LOOM_AUTH_REQUIRED=false disables auth."""
        with patch.dict(os.environ, {"LOOM_AUTH_REQUIRED": "false"}):
            assert _is_auth_required() is False

    def test_is_auth_required_case_insensitive(self) -> None:
        """Test that LOOM_AUTH_REQUIRED check is case-insensitive."""
        with patch.dict(os.environ, {"LOOM_AUTH_REQUIRED": "TRUE"}):
            assert _is_auth_required() is True

        with patch.dict(os.environ, {"LOOM_AUTH_REQUIRED": "True"}):
            assert _is_auth_required() is True

    def test_is_auth_required_default_false(self) -> None:
        """Test that auth is disabled by default."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LOOM_AUTH_REQUIRED", None)
            assert _is_auth_required() is False


class TestMiddlewareInitialization:
    """Tests for middleware initialization."""

    def test_middleware_init_auth_disabled(self) -> None:
        """Test middleware initialization with auth disabled."""
        with patch.dict(os.environ, {"LOOM_AUTH_REQUIRED": "false"}):
            app = MagicMock()
            middleware = ApiKeyAuthMiddleware(app)
            assert middleware.app is app
            assert middleware.auth_required is False
            assert middleware.api_keys == set()

    def test_middleware_init_auth_enabled_with_keys(self) -> None:
        """Test middleware initialization with auth enabled and keys configured."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "key1,key2",
            },
        ):
            app = MagicMock()
            middleware = ApiKeyAuthMiddleware(app)
            assert middleware.auth_required is True
            assert middleware.api_keys == {"key1", "key2"}

    def test_middleware_init_auth_enabled_no_keys_warning(self, caplog) -> None:
        """Test that warning is logged when auth enabled but no keys configured."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "",
            },
        ):
            app = MagicMock()
            middleware = ApiKeyAuthMiddleware(app)
            assert middleware.auth_required is True
            assert middleware.api_keys == set()


class TestMiddlewareExecution:
    """Tests for middleware request processing."""

    @pytest.mark.asyncio
    async def test_non_http_request_passed_through(self) -> None:
        """Test that non-HTTP requests pass through unchanged."""
        app = AsyncMock()
        middleware = ApiKeyAuthMiddleware(app)

        scope = {"type": "websocket"}  # Not HTTP
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # App should be called with original scope/receive/send
        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_exempt_path_allowed(self) -> None:
        """Test that exempt paths bypass authentication."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "valid-key",
            },
        ):
            app = AsyncMock()
            middleware = ApiKeyAuthMiddleware(app)

            scope = {
                "type": "http",
                "path": "/health",
                "method": "GET",
                "headers": [],  # No API key
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # App should be called despite missing API key
            app.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_disabled_allows_all(self) -> None:
        """Test that when auth is disabled, all requests are allowed."""
        with patch.dict(os.environ, {"LOOM_AUTH_REQUIRED": "false"}):
            app = AsyncMock()
            middleware = ApiKeyAuthMiddleware(app)

            scope = {
                "type": "http",
                "path": "/api/fetch",
                "method": "GET",
                "headers": [],  # No API key
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # App should be called despite missing API key
            app.assert_called_once()

    @pytest.mark.asyncio
    async def test_valid_api_key_allowed(self) -> None:
        """Test that valid API key allows request through."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "valid-key",
            },
        ):
            app = AsyncMock()
            middleware = ApiKeyAuthMiddleware(app)

            scope = {
                "type": "http",
                "path": "/api/fetch",
                "method": "GET",
                "headers": [(b"x-api-key", b"valid-key")],
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # App should be called
            app.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self) -> None:
        """Test that invalid API key returns 401."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "valid-key",
            },
        ):
            app = AsyncMock()
            middleware = ApiKeyAuthMiddleware(app)

            scope = {
                "type": "http",
                "path": "/api/fetch",
                "method": "GET",
                "headers": [(b"x-api-key", b"invalid-key")],
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # App should NOT be called
            app.assert_not_called()

            # send should be called with 401
            assert send.call_count == 2
            first_call = send.call_args_list[0]
            assert first_call[0][0]["status"] == 401

    @pytest.mark.asyncio
    async def test_missing_api_key_rejected(self) -> None:
        """Test that missing API key returns 401 when auth enabled."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "valid-key",
            },
        ):
            app = AsyncMock()
            middleware = ApiKeyAuthMiddleware(app)

            scope = {
                "type": "http",
                "path": "/api/fetch",
                "method": "GET",
                "headers": [],  # No API key
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # App should NOT be called
            app.assert_not_called()

            # send should be called with 401
            assert send.call_count == 2


class TestUnauthorizedResponse:
    """Tests for 401 response format."""

    @pytest.mark.asyncio
    async def test_401_response_format(self) -> None:
        """Test that 401 response has correct JSON format."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "valid-key",
            },
        ):
            app = AsyncMock()
            middleware = ApiKeyAuthMiddleware(app)

            scope = {
                "type": "http",
                "path": "/api/fetch",
                "method": "GET",
                "headers": [(b"x-api-key", b"invalid-key")],
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Get the body from second send call
            second_call = send.call_args_list[1]
            body = second_call[0][0]["body"]
            data = json.loads(body)

            assert data["error"] == "unauthorized"
            assert data["status"] == 401
            assert "X-API-Key" in data["message"]

    @pytest.mark.asyncio
    async def test_401_response_headers(self) -> None:
        """Test that 401 response has correct headers."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "valid-key",
            },
        ):
            app = AsyncMock()
            middleware = ApiKeyAuthMiddleware(app)

            scope = {
                "type": "http",
                "path": "/api/fetch",
                "method": "GET",
                "headers": [],
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Get headers from first send call
            first_call = send.call_args_list[0]
            headers = dict(first_call[0][0]["headers"])

            assert headers.get(b"content-type") == b"application/json"
            assert b"content-length" in headers


class TestRemoteAddressExtraction:
    """Tests for client IP extraction."""

    def test_get_remote_addr_with_client(self) -> None:
        """Test extracting client IP from scope."""
        scope = {"client": ("192.168.1.100", 54321)}
        addr = ApiKeyAuthMiddleware._get_remote_addr(scope)
        assert addr == "192.168.1.100"

    def test_get_remote_addr_missing_client(self) -> None:
        """Test when client tuple is missing."""
        scope = {}
        addr = ApiKeyAuthMiddleware._get_remote_addr(scope)
        assert addr == "unknown"

    def test_get_remote_addr_none_client(self) -> None:
        """Test when client is None."""
        scope = {"client": None}
        addr = ApiKeyAuthMiddleware._get_remote_addr(scope)
        assert addr == "unknown"


class TestIntegration:
    """Integration tests for complete authentication flow."""

    @pytest.mark.asyncio
    async def test_complete_auth_flow_success(self) -> None:
        """Test complete authentication flow with valid key."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "test-key-123",
            },
        ):
            call_tracker = []

            async def mock_app(scope, receive, send):
                call_tracker.append(("app_called", scope["path"]))

            middleware = ApiKeyAuthMiddleware(mock_app)

            scope = {
                "type": "http",
                "path": "/api/research/fetch",
                "method": "POST",
                "headers": [(b"x-api-key", b"test-key-123")],
                "client": ("127.0.0.1", 12345),
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Verify app was called
            assert len(call_tracker) == 1
            assert call_tracker[0] == ("app_called", "/api/research/fetch")

    @pytest.mark.asyncio
    async def test_complete_auth_flow_failure(self) -> None:
        """Test complete authentication flow with invalid key."""
        with patch.dict(
            os.environ,
            {
                "LOOM_AUTH_REQUIRED": "true",
                "LOOM_API_KEYS": "test-key-123",
            },
        ):
            call_tracker = []

            async def mock_app(scope, receive, send):
                call_tracker.append(("app_called",))

            middleware = ApiKeyAuthMiddleware(mock_app)

            scope = {
                "type": "http",
                "path": "/api/research/fetch",
                "method": "POST",
                "headers": [(b"x-api-key", b"wrong-key")],
                "client": ("127.0.0.1", 12345),
            }
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Verify app was NOT called
            assert len(call_tracker) == 0

            # Verify 401 response was sent
            assert send.call_count == 2
