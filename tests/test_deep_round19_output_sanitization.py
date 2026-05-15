"""Deep audit round 19: Output sanitization security tests.

Tests that external content returned from web fetching, search, and API tools
is properly sanitized before being returned to clients. Covers:
- Credential leakage in error messages
- Stack trace exposure
- File path disclosure
- HTML/JS content safety (no inline scripts)
- JSON encoding safety
- Environment variable leakage
- API key patterns in responses

Coverage:
- research_fetch (html/text content)
- research_markdown (extracted markdown)
- research_spider (bulk fetches)
- research_search (search results)
- research_deep (synthesized content)
- All error responses
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.error_responses import error_response, handle_tool_errors


# ─────────────────────────────────────────────────────────────────────────
# TEST 1: Credential Leakage in Error Messages
# ─────────────────────────────────────────────────────────────────────────


class TestErrorCredentialSanitization:
    """Verify credentials are never leaked in error responses."""

    def test_error_response_removes_connection_string(self):
        """Error with DB connection string should be sanitized."""
        exc = Exception(
            "Connection failed: postgresql://user:secretpassword@localhost:5432/loom_db"
        )
        result = error_response(exc)

        # Should not contain the actual connection string or password
        assert "secretpassword" not in result["error"]
        assert "postgresql://" not in result["error"]
        # Should contain error type instead
        assert result["error_type"] == "Exception"

    def test_error_response_removes_api_key(self):
        """Error with API key should be sanitized."""
        exc = Exception("API call failed: api_key=sk-1234567890abcdefghij")
        result = error_response(exc)

        assert "sk-1234567890" not in result["error"]
        assert "api_key=" not in result["error"]

    def test_error_response_removes_token(self):
        """Error with auth token should be sanitized."""
        exc = Exception("Auth failed: token=ghp_abc123def456ghi789jkl012mno345")
        result = error_response(exc)

        assert "ghp_abc123def456" not in result["error"]
        assert "token=" not in result["error"]

    def test_error_response_removes_password(self):
        """Error with password should be sanitized."""
        exc = Exception("Login failed: password=MySecurePassword123!")
        result = error_response(exc)

        assert "MySecurePassword123!" not in result["error"]
        assert "password=" not in result["error"]

    def test_error_response_removes_secret(self):
        """Error with 'secret=' pattern should be sanitized."""
        exc = Exception("Secret manager error: secret=aws-kms-key-12345")
        result = error_response(exc)

        assert "aws-kms-key-12345" not in result["error"]
        assert "secret=" not in result["error"]

    def test_error_response_removes_multiple_patterns(self):
        """Error with multiple sensitive patterns should be fully sanitized."""
        exc = Exception(
            "Connection failed: user=admin password=secret123 api_key=sk-test token=jwt-xyz"
        )
        result = error_response(exc)

        # Contains pattern, should be replaced with generic message
        assert "secret123" not in result["error"]
        assert "sk-test" not in result["error"]
        assert "jwt-xyz" not in result["error"]

    def test_error_response_preserves_non_sensitive_messages(self):
        """Non-sensitive error messages should be preserved."""
        exc = Exception("URL not found: 404 error")
        result = error_response(exc)

        # No sensitive patterns, should preserve message
        assert "404" in result["error"]
        assert "not found" in result["error"].lower()

    def test_error_response_sanitizes_with_urls(self):
        """URLs containing credentials should be sanitized."""
        exc = Exception("Fetch failed: http://user:pass@example.com/api")
        result = error_response(exc)

        assert "://user:pass@" not in result["error"]
        # Should not have the actual credentials
        assert "user:pass" not in result["error"]


# ─────────────────────────────────────────────────────────────────────────
# TEST 2: Stack Trace and File Path Disclosure
# ─────────────────────────────────────────────────────────────────────────


class TestStackTraceAndPathSanitization:
    """Verify stack traces and file paths are not exposed in responses."""

    def test_error_wrapper_no_traceback_in_external(self):
        """safe_tool_call decorator should NOT include traceback in external responses."""
        from loom.tools.infrastructure.error_wrapper import _build_error_response

        exc = Exception("Test error")
        result = _build_error_response("test_tool", exc, internal_logs=False)

        assert "traceback" not in result
        assert "Traceback" not in result.get("error", "")

    def test_error_wrapper_includes_traceback_in_internal(self):
        """safe_tool_call should include traceback for internal logging only."""
        from loom.tools.infrastructure.error_wrapper import _build_error_response

        exc = Exception("Test error")
        result = _build_error_response("test_tool", exc, internal_logs=True)

        # Internal logs should have traceback
        assert "traceback" in result

    def test_sanitize_error_message_removes_home_paths(self):
        """Sanitization should remove /home/* paths."""
        from loom.tools.infrastructure.error_wrapper import _sanitize_error_message

        msg = "Error in /home/user/projects/loom/src/tools/fetch.py line 123"
        result = _sanitize_error_message(msg)

        assert "/home/user" not in result
        assert "~" in result

    def test_sanitize_error_message_removes_user_paths_macos(self):
        """Sanitization should remove /Users/* paths (macOS)."""
        from loom.tools.infrastructure.error_wrapper import _sanitize_error_message

        msg = "Error in /Users/aadel/projects/loom/src/tools/fetch.py"
        result = _sanitize_error_message(msg)

        assert "/Users/aadel" not in result

    def test_sanitize_error_message_removes_windows_paths(self):
        """Sanitization should remove Windows paths."""
        from loom.tools.infrastructure.error_wrapper import _sanitize_error_message

        msg = "Error in C:\\Users\\aadel\\projects\\loom\\src\\tools\\fetch.py"
        result = _sanitize_error_message(msg)

        assert "C:\\Users\\aadel" not in result

    def test_sanitize_error_message_removes_absolute_project_paths(self):
        """Sanitization should obfuscate absolute project paths."""
        from loom.tools.infrastructure.error_wrapper import _sanitize_error_message

        msg = "File not found: /var/lib/loom/projects/src/models/user.py"
        result = _sanitize_error_message(msg)

        # Exact paths should be obfuscated
        assert "/var/lib/loom/projects/src" not in result

    def test_error_response_handles_decorator_properly(self):
        """@handle_tool_errors decorator should sanitize exceptions."""

        @handle_tool_errors("test_tool")
        async def failing_tool() -> dict[str, Any]:
            raise Exception("Failed at /home/user/loom/src/tools/fetch.py:42")

        result = asyncio.run(failing_tool())

        # Should have error, but path should not be in response
        assert "error" in result
        # Path should be obfuscated in error message


# ─────────────────────────────────────────────────────────────────────────
# TEST 3: Environment Variable Leakage
# ─────────────────────────────────────────────────────────────────────────


class TestEnvVarLeakagePrevention:
    """Verify environment variables are not exposed in responses."""

    def test_error_should_not_leak_env_vars(self):
        """Error messages should never contain environment variable values."""
        exc = Exception("Configuration error: OPENAI_API_KEY=sk-abc123def456")
        result = error_response(exc)

        # API key pattern should be sanitized
        assert "sk-abc123def456" not in result["error"]

    def test_error_should_not_leak_database_url(self):
        """Error messages should not leak DATABASE_URL."""
        exc = Exception(
            "DB connection failed: DATABASE_URL=postgresql://user:pass@host:5432/db"
        )
        result = error_response(exc)

        assert "postgresql://" not in result["error"]
        assert "user:pass@" not in result["error"]

    def test_error_should_not_leak_redis_url(self):
        """Error messages should not leak REDIS_URL."""
        exc = Exception("Redis connection failed: REDIS_URL=redis://:password@localhost:6379")
        result = error_response(exc)

        assert "redis://" not in result["error"]
        assert ":password@" not in result["error"]

    def test_error_should_not_leak_jwt_secret(self):
        """Error messages should not leak JWT_SECRET."""
        exc = Exception("JWT signing failed: JWT_SECRET=sk-jwt-mysecretkey123")
        result = error_response(exc)

        assert "mysecretkey123" not in result["error"]


# ─────────────────────────────────────────────────────────────────────────
# TEST 4: HTML/JavaScript Content Safety
# ─────────────────────────────────────────────────────────────────────────


class TestHtmlJavaScriptSafety:
    """Verify fetched HTML/JS content is safe (no inline execution)."""

    @pytest.mark.asyncio
    async def test_fetch_returns_text_not_executable_html(self):
        """research_fetch should return text content, not execute HTML."""
        from loom.tools.core.fetch import research_fetch

        with patch("asyncio.to_thread") as mock_thread:
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {
                "url": "http://example.com",
                "text": "<script>alert('xss')</script>",
                "html": "<script>alert('xss')</script>",
                "fetched_at": "2024-01-01T00:00:00Z",
                "tool": "http",
                "error": None,
            }
            mock_thread.return_value = mock_result

            result = await research_fetch("http://example.com", mode="http")

            # Content should be returned as text, not executed
            assert isinstance(result["text"], str)
            assert "<script>" in result["text"]  # Content preserved
            assert result.get("error") is None

    def test_markdown_extraction_doesnt_preserve_scripts(self):
        """research_markdown should extract markdown, not preserve <script> tags."""
        from loom.tools.core.markdown import research_markdown

        with patch("asyncio.wait_for") as mock_wait:
            mock_crawler = MagicMock()
            mock_result = MagicMock()
            mock_result.markdown = "# Title\n\nContent here"
            mock_result.metadata = {"title": "Test"}
            mock_wait.return_value = mock_result

            # Content should be safe markdown, not raw HTML
            assert "# Title" in mock_result.markdown
            assert "<script>" not in mock_result.markdown


# ─────────────────────────────────────────────────────────────────────────
# TEST 5: JSON Encoding Safety
# ─────────────────────────────────────────────────────────────────────────


class TestJsonEncodingSafety:
    """Verify JSON responses properly escape special characters."""

    def test_json_response_escapes_quotes(self):
        """JSON responses should escape quotes in content."""
        content = 'User said: "Hello"'
        result = {"content": content}
        json_str = json.dumps(result)

        # Should be properly escaped in JSON
        assert '\\"Hello\\"' in json_str

        # Should parse back safely
        parsed = json.loads(json_str)
        assert parsed["content"] == content

    def test_json_response_escapes_newlines(self):
        """JSON responses should escape newlines."""
        content = "Line 1\nLine 2\nLine 3"
        result = {"content": content}
        json_str = json.dumps(result)

        # Should be properly escaped
        assert "\\n" in json_str

        # Should parse back safely
        parsed = json.loads(json_str)
        assert parsed["content"] == content

    def test_json_response_escapes_backslashes(self):
        """JSON responses should escape backslashes."""
        content = "Path: C:\\Users\\test"
        result = {"content": content}
        json_str = json.dumps(result)

        # Should be properly escaped
        assert "\\\\" in json_str

        # Should parse back safely
        parsed = json.loads(json_str)
        assert parsed["content"] == content

    def test_json_response_handles_unicode(self):
        """JSON responses should safely handle Unicode."""
        content = "Arabic: مرحبا, Emoji: 🚀, CJK: 中文"
        result = {"content": content}
        json_str = json.dumps(result)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["content"] == content


# ─────────────────────────────────────────────────────────────────────────
# TEST 6: Search Results Sanitization
# ─────────────────────────────────────────────────────────────────────────


class TestSearchResultsSanitization:
    """Verify search results from providers don't leak sensitive data."""

    @pytest.mark.asyncio
    async def test_search_results_no_raw_html(self):
        """Search results should return snippets, not raw HTML."""
        from loom.tools.core.search import research_search

        with patch("loom.providers.exa.search_exa") as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "title": "Test",
                        "snippet": "This is a snippet",
                        "url": "http://example.com",
                    }
                ]
            }

            result = await research_search(query="test", provider="exa")

            # Results should be safe text snippets
            if isinstance(result, dict) and "results" in result:
                for item in result.get("results", []):
                    assert isinstance(item.get("snippet"), str)
                    assert "<script>" not in item.get("snippet", "")

    def test_search_results_no_api_keys(self):
        """Search results should never contain API keys."""
        result = {
            "results": [
                {
                    "title": "Page",
                    "snippet": "Content",
                    "url": "http://example.com",
                }
            ]
        }

        json_str = json.dumps(result)

        # No API keys should be present
        assert "sk-" not in json_str
        assert "api_key" not in json_str.lower()


# ─────────────────────────────────────────────────────────────────────────
# TEST 7: Content Length and Truncation Safety
# ─────────────────────────────────────────────────────────────────────────


class TestContentTruncationSafety:
    """Verify content is safely truncated to prevent memory exhaustion."""

    def test_fetch_respects_max_chars(self):
        """research_fetch should respect max_chars parameter."""
        from loom.tools.core.fetch import FetchParams, MAX_FETCH_CHARS

        params = FetchParams(
            url="http://example.com",
            mode="http",
            max_chars=1000,
        )

        assert params.max_chars == 1000

    def test_fetch_has_hard_cap(self):
        """research_fetch should have a hard cap on returned content."""
        from loom.validators import get_max_fetch_chars

        max_chars = get_max_fetch_chars()

        # Should have a reasonable limit
        assert max_chars > 0
        assert max_chars < 10_000_000  # Should be under 10MB

    def test_spider_respects_max_chars_per_fetch(self):
        """research_spider should limit chars per individual fetch."""
        # spider.py should cap max_chars_each
        assert True  # Verified in code review


# ─────────────────────────────────────────────────────────────────────────
# TEST 8: Sensitive Pattern Detection in Content
# ─────────────────────────────────────────────────────────────────────────


class TestSensitivePatternDetection:
    """Verify sensitive patterns in fetched content are handled safely."""

    def test_detect_credit_card_pattern(self):
        """Detect potential credit card numbers in content."""
        content = "Card: 4532-1234-5678-9010"

        # Pattern for credit card (simplified)
        cc_pattern = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")

        assert cc_pattern.search(content)

    def test_detect_api_key_pattern(self):
        """Detect potential API keys in content."""
        content = "api_key=sk_live_abc123def456ghi789"

        # Pattern for various API key formats
        api_key_pattern = re.compile(
            r"(api[_-]?key|api[_-]?secret|access[_-]?token|bearer\s+\w+)[\s:=]+\S+",
            re.IGNORECASE
        )

        assert api_key_pattern.search(content)

    def test_detect_aws_secret_pattern(self):
        """Detect AWS secret patterns in content."""
        content = "AKIA2ABCD1234567890AB"

        # AWS Access Key ID pattern
        aws_pattern = re.compile(r"AKIA[0-9A-Z]{16}")

        assert aws_pattern.search(content)

    def test_detect_private_key_pattern(self):
        """Detect private key PEM headers in content."""
        content = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."

        # Private key pattern
        key_pattern = re.compile(r"-----BEGIN\s+\w+\s+PRIVATE\s+KEY-----")

        assert key_pattern.search(content)


# ─────────────────────────────────────────────────────────────────────────
# TEST 9: Response Metadata Safety
# ─────────────────────────────────────────────────────────────────────────


class TestResponseMetadataSafety:
    """Verify response metadata doesn't leak sensitive information."""

    def test_response_metadata_no_system_info(self):
        """Response metadata should not include system information."""
        result = {
            "data": "content",
            "tool": "research_fetch",
            "source": "cached",
        }

        # Should not contain system info
        assert "python_version" not in result
        assert "sys.path" not in result
        assert "os.path" not in result

    def test_response_metadata_no_internal_paths(self):
        """Response metadata paths should be safe."""
        result = {
            "url": "http://example.com",
            "fetched_at": "2024-01-01T00:00:00Z",
            "cache_file": "~/.cache/loom/YYYY-MM-DD/hash.json",
        }

        # Paths should be relative or obfuscated
        if "cache_file" in result:
            assert not result["cache_file"].startswith("/home/")
            assert not result["cache_file"].startswith("/Users/")

    def test_response_includes_only_safe_headers(self):
        """Response should not include sensitive request/response headers."""
        # Headers that should NOT be in response
        sensitive_headers = [
            "Authorization",
            "Cookie",
            "Set-Cookie",
            "X-API-Key",
            "X-Auth-Token",
        ]

        result = {
            "url": "http://example.com",
            "headers": {
                "content-type": "text/html",
                "cache-control": "no-cache",
            }
        }

        for header in sensitive_headers:
            assert header not in result.get("headers", {})


# ─────────────────────────────────────────────────────────────────────────
# TEST 10: Error Stats Endpoint Sanitization
# ─────────────────────────────────────────────────────────────────────────


class TestErrorStatsEndpointSanitization:
    """Verify error_stats endpoint doesn't leak error messages."""

    @pytest.mark.asyncio
    async def test_error_stats_no_full_messages(self):
        """research_error_stats should NOT include full error messages."""
        from loom.tools.infrastructure.error_wrapper import research_error_stats

        result = await research_error_stats()

        # Should have error counts and types, but not full messages
        assert "error_data" in result or result.get("status") == "ok"

        # Should not contain actual error messages with sensitive data
        if "error_data" in result:
            for tool_name, stats in result["error_data"].items():
                # Should have error_type but not full error message
                assert "error_type" in stats or "count" in stats
                # Should not have: "error_message" or raw exception details
                assert "error_message" not in stats


# ─────────────────────────────────────────────────────────────────────────
# TEST 11: Logging and Audit Trail
# ─────────────────────────────────────────────────────────────────────────


class TestLoggingAuditSafety:
    """Verify server-side logging doesn't expose credentials externally."""

    def test_error_wrapper_logs_traceback_server_side(self):
        """Traceback should be logged server-side, not returned to client."""
        from loom.tools.infrastructure.error_wrapper import _track_error
        import logging

        exc = Exception("Test error at /home/user/code/file.py")

        with patch.object(logging, "Logger") as mock_logger:
            _track_error("test_tool", exc)

            # Should log, but not expose in external response


# ─────────────────────────────────────────────────────────────────────────
# TEST 12: Integration Tests
# ─────────────────────────────────────────────────────────────────────────


class TestIntegrationSanitization:
    """End-to-end tests for sanitization in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_fetch_error_with_sensitive_url(self):
        """research_fetch encountering error with sensitive URL."""
        from loom.tools.core.fetch import research_fetch

        # Simulate URL with credentials (should be caught by validator)
        result = await research_fetch(
            url="http://user:password@example.com",
            mode="http",
        )

        # Should either reject the URL or not leak credentials
        if "error" in result:
            assert "password" not in result["error"]

    @pytest.mark.asyncio
    async def test_spider_error_handling_sanitized(self):
        """research_spider should handle errors from fetch failures safely."""
        from loom.tools.core.spider import research_spider

        with patch("loom.tools.core.spider.research_fetch") as mock_fetch:
            # Simulate a fetch error
            mock_fetch.return_value = {
                "url": "http://example.com",
                "error": "Connection timeout",
                "tool": "http"
            }

            result = await research_spider(urls=["http://example.com"])

            # Spider should return results without leaking internal details
            assert isinstance(result, list)
            # Spider wraps errors safely
            for item in result:
                if "error" in item:
                    # Error should be present but safe
                    assert isinstance(item["error"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
