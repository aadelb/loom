"""Tests for production hardening: header validation, JS blocklist,
provider config filtering, rate limiter, tracing, token redaction,
deep warnings, health check.
"""

from __future__ import annotations

import asyncio
import re

import pytest

from loom.rate_limiter import RateLimiter, reset_all
from loom.tracing import REQUEST_ID, RequestIdFilter, get_request_id, new_request_id
from loom.validators import (
    PROVIDER_CONFIG_ALLOWLIST,
    SAFE_REQUEST_HEADERS,
    filter_headers,
    filter_provider_config,
    validate_js_script,
)


# ─── Header validation ─────────────────────────────────────────────────────


class TestHeaderValidation:
    def test_safe_headers_pass(self) -> None:
        h = filter_headers({"Accept-Language": "en", "User-Agent": "bot/1"})
        assert h is not None
        assert "Accept-Language" in h
        assert "User-Agent" in h

    def test_dangerous_headers_rejected(self) -> None:
        h = filter_headers({
            "Authorization": "Bearer token123",
            "Host": "evil.com",
            "X-Forwarded-For": "127.0.0.1",
            "Cookie": "session=abc",
        })
        assert h is None

    def test_mixed_headers_filtered(self) -> None:
        h = filter_headers({
            "Accept-Language": "en",
            "Authorization": "Bearer xxx",
            "Referer": "https://site.com",
        })
        assert h is not None
        assert "Accept-Language" in h
        assert "Referer" in h
        assert "Authorization" not in h

    def test_none_passthrough(self) -> None:
        assert filter_headers(None) is None

    def test_empty_dict_passthrough(self) -> None:
        result = filter_headers({})
        assert result is None or result == {}

    def test_header_value_length_limit(self) -> None:
        h = filter_headers({"Accept-Language": "x" * 600})
        assert h is None

    def test_case_insensitive(self) -> None:
        h = filter_headers({"ACCEPT-LANGUAGE": "en"})
        assert h is not None


# ─── JS validation ──────────────────────────────────────────────────────────


class TestJSValidation:
    def test_safe_dom_script(self) -> None:
        validate_js_script('document.querySelector(".login").click()')

    def test_safe_localstorage(self) -> None:
        validate_js_script('localStorage.getItem("token")')

    def test_blocks_fetch(self) -> None:
        with pytest.raises(ValueError, match="fetch"):
            validate_js_script('fetch("https://evil.com")')

    def test_blocks_xmlhttprequest(self) -> None:
        with pytest.raises(ValueError, match="XMLHttpRequest"):
            validate_js_script("new XMLHttpRequest()")

    def test_blocks_eval(self) -> None:
        with pytest.raises(ValueError, match="eval"):
            validate_js_script('eval("alert(1)")')

    def test_blocks_function_constructor(self) -> None:
        with pytest.raises(ValueError, match="Function"):
            validate_js_script('new Function("return 1")')

    def test_blocks_import(self) -> None:
        with pytest.raises(ValueError, match="import"):
            validate_js_script('import("./evil.js")')

    def test_blocks_websocket(self) -> None:
        with pytest.raises(ValueError, match="WebSocket"):
            validate_js_script('new WebSocket("ws://evil")')

    def test_blocks_worker(self) -> None:
        with pytest.raises(ValueError, match="Worker"):
            validate_js_script('new Worker("evil.js")')

    def test_blocks_sendbeacon(self) -> None:
        with pytest.raises(ValueError, match="sendBeacon"):
            validate_js_script('navigator.sendBeacon("/exfil", data)')

    def test_case_insensitive_blocking(self) -> None:
        with pytest.raises(ValueError):
            validate_js_script('FETCH("https://evil.com")')


# ─── Provider config filtering ──────────────────────────────────────────────


class TestProviderConfigFilter:
    def test_exa_allowed_keys(self) -> None:
        pc = filter_provider_config("exa", {
            "include_domains": ["x.com"],
            "api_key": "secret",
            "endpoint": "https://evil",
        })
        assert "include_domains" in pc
        assert "api_key" not in pc
        assert "endpoint" not in pc

    def test_brave_allowed_keys(self) -> None:
        pc = filter_provider_config("brave", {"country": "US", "timeout": 1})
        assert "country" in pc
        assert "timeout" not in pc

    def test_ddgs_allowed_keys(self) -> None:
        pc = filter_provider_config("ddgs", {"region": "us-en", "secret": "x"})
        assert "region" in pc
        assert "secret" not in pc

    def test_unknown_provider_rejects_all(self) -> None:
        pc = filter_provider_config("unknown", {"any_key": "value"})
        assert pc == {}

    def test_none_returns_empty(self) -> None:
        assert filter_provider_config("exa", None) == {}

    def test_all_providers_have_schemas(self) -> None:
        expected = {
            "exa", "tavily", "firecrawl", "brave", "ddgs", "arxiv",
            "wikipedia", "hackernews", "reddit", "newsapi", "crypto", "coindesk",
            "binance", "investing", "ahmia", "darksearch", "ummro",
            "onionsearch", "torcrawl", "darkweb_cti", "robin_osint",
        }
        assert set(PROVIDER_CONFIG_ALLOWLIST.keys()) == expected


# ─── Rate limiter ─────��─────────────────────────────────────────────────────


class TestRateLimiter:
    def test_allows_within_limit(self) -> None:
        limiter = RateLimiter(max_calls=3, window_seconds=60)
        for _ in range(3):
            assert asyncio.run(limiter.check("test"))

    def test_blocks_over_limit(self) -> None:
        limiter = RateLimiter(max_calls=2, window_seconds=60)
        assert asyncio.run(limiter.check("test"))
        assert asyncio.run(limiter.check("test"))
        assert not asyncio.run(limiter.check("test"))

    def test_separate_keys(self) -> None:
        limiter = RateLimiter(max_calls=1, window_seconds=60)
        assert asyncio.run(limiter.check("a"))
        assert asyncio.run(limiter.check("b"))
        assert not asyncio.run(limiter.check("a"))

    def test_remaining(self) -> None:
        limiter = RateLimiter(max_calls=5, window_seconds=60)
        assert limiter.remaining("x") == 5
        asyncio.run(limiter.check("x"))
        assert limiter.remaining("x") == 4

    def test_reset_all(self) -> None:
        reset_all()


# ─── Tracing ──────────��─────────────────────────��───────────────────────────


class TestTracing:
    def test_new_request_id(self) -> None:
        rid = new_request_id()
        assert len(rid) == 16
        assert rid == get_request_id()

    def test_request_id_default(self) -> None:
        REQUEST_ID.set("")
        assert get_request_id() == ""

    def test_filter_injects_request_id(self) -> None:
        import logging

        rid = new_request_id()
        filt = RequestIdFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        filt.filter(record)
        assert record.request_id == rid  # type: ignore[attr-defined]


# ─── Token redaction ────────────────────────────────────────────────────────


class TestTokenRedaction:
    def setup_method(self) -> None:
        from loom.tools.llm import _sanitize_error

        self.sanitize = _sanitize_error

    def test_openai_key(self) -> None:
        assert "[OPENAI_KEY_REDACTED]" in self.sanitize("key: sk-1234567890abcdef")

    def test_nvidia_key(self) -> None:
        assert "[NVIDIA_KEY_REDACTED]" in self.sanitize("key: nvapi-1234567890abcdef")

    def test_github_token(self) -> None:
        assert "[GITHUB_TOKEN_REDACTED]" in self.sanitize(
            "token: ghp_" + "a" * 36
        )

    def test_aws_key(self) -> None:
        assert "[AWS_KEY_REDACTED]" in self.sanitize("key: AKIA1234567890ABCDEF")

    def test_bearer_token(self) -> None:
        result = self.sanitize("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert "TOKEN_REDACTED" in result
        assert "eyJhbG" not in result


# ─── Params integration ────────────────────────────────────────────────────


class TestParamsIntegration:
    def test_fetch_params_filters_headers(self) -> None:
        from loom.params import FetchParams

        # Authorization should be stripped
        params = FetchParams(
            url="https://example.com",
            headers={"Authorization": "Bearer xxx", "Accept-Language": "en"},
        )
        assert params.headers is not None
        assert "Authorization" not in params.headers
        assert "Accept-Language" in params.headers

    def test_fetch_params_rejects_dangerous_js(self) -> None:
        from loom.params import MarkdownParams

        with pytest.raises(Exception, match="disallowed"):
            MarkdownParams(url="https://example.com", js_before_scrape='fetch("https://evil")')

    def test_session_params_rejects_dangerous_login_script(self) -> None:
        from loom.params import SessionOpenParams

        with pytest.raises(Exception, match="disallowed"):
            SessionOpenParams(name="test", login_script='eval("alert(1)")')

    def test_session_params_allows_safe_login_script(self) -> None:
        from loom.params import SessionOpenParams

        params = SessionOpenParams(
            name="test",
            login_script='document.querySelector("#login").click()',
        )
        assert params.login_script is not None


# ─── Health check ───────────────────────────────────────────────────────────


class TestHealthCheck:
    def test_health_check_returns_status(self) -> None:
        from loom.server import research_health_check

        result = asyncio.run(research_health_check())
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "active_sessions" in result


# ─── Deep warnings ──────────────────────────────────────────────────────────


class TestDeepWarnings:
    def test_deep_returns_warnings_key(self) -> None:
        """research_deep response includes a 'warnings' list."""
        from unittest.mock import patch

        async def run() -> dict:
            with patch("loom.tools.search.research_search", return_value={
                "provider": "mock",
                "results": [],
            }):
                from loom.tools.deep import research_deep
                return await research_deep("test query", depth=1, expand_queries=False)

        result = asyncio.run(run())
        assert "warnings" in result
        assert isinstance(result["warnings"], list)
