"""Tests for sanitization module."""

import pytest
from loom.sanitization import (
    mask_key,
    safe_repr,
    sanitize_headers,
    sanitize_text,
    sanitize_url,
)


class TestMaskKey:
    """Tests for mask_key function."""

    def test_mask_key_normal(self):
        """Normal key gets masked with first 4 and last 2 chars."""
        result = mask_key("sk-1234567890")
        assert result == "sk-1...90"

    def test_mask_key_short_key(self):
        """Short keys (4 chars or less) are fully masked."""
        assert mask_key("abc") == "***"
        assert mask_key("abcd") == "***"

    def test_mask_key_empty(self):
        """Empty string returns masked."""
        assert mask_key("") == "***"

    def test_mask_key_custom_visible(self):
        """Custom visible_chars parameter works."""
        result = mask_key("verylongkey123456", visible_chars=8)
        assert result == "verylong...56"

    def test_mask_key_one_char_visible(self):
        """One visible char minimum."""
        result = mask_key("password123", visible_chars=1)
        assert result == "p...23"


class TestSanitizeUrl:
    """Tests for sanitize_url function."""

    def test_sanitize_url_with_api_key(self):
        """API key in query params gets masked."""
        url = "https://api.example.com/search?q=test&api_key=sk-123456"
        result = sanitize_url(url)
        # URL encoding converts *** to %2A%2A%2A
        assert "%2A%2A%2A" in result or "api_key=***" in result
        assert "sk-123456" not in result
        assert "q=test" in result

    def test_sanitize_url_no_query(self):
        """URL without query params returned unchanged."""
        url = "https://example.com/path"
        assert sanitize_url(url) == url

    def test_sanitize_url_multiple_sensitive(self):
        """Multiple sensitive params all get masked."""
        url = "https://api.com/?token=abc&password=xyz&limit=10"
        result = sanitize_url(url)
        # Check that sensitive values are gone (either as *** or %2A%2A%2A)
        assert "abc" not in result
        assert "xyz" not in result
        assert "limit=10" in result

    def test_sanitize_url_case_insensitive(self):
        """Parameter name matching is case-insensitive."""
        url = "https://api.com/?API_KEY=secret123&AUTH=token456"
        result = sanitize_url(url)
        assert "secret123" not in result
        assert "token456" not in result

    def test_sanitize_url_invalid_url(self):
        """Invalid URLs are returned unchanged."""
        invalid = "not-a-real-url:::weird"
        result = sanitize_url(invalid)
        assert result == invalid

    def test_sanitize_url_preserves_safe_params(self):
        """Safe parameters pass through unchanged."""
        url = "https://api.com/?name=John&email=john@example.com&api_key=secret"
        result = sanitize_url(url)
        assert "John" in result
        assert "john" in result
        assert "secret" not in result


class TestSanitizeText:
    """Tests for sanitize_text function."""

    def test_sanitize_text_api_key(self):
        """API key in text gets masked."""
        text = "Using api_key=sk-123456789 for authentication"
        result = sanitize_text(text)
        assert "sk-123456789" not in result
        assert "api_key=sk-1...89" in result

    def test_sanitize_text_multiple_keys(self):
        """Multiple keys in text all get masked."""
        text = "token=abc123456 and secret=xyz987654"
        result = sanitize_text(text)
        assert "abc123456" not in result
        assert "xyz987654" not in result

    def test_sanitize_text_various_separators(self):
        """Works with = and : separators."""
        result1 = sanitize_text("password=secret123")
        assert "secret123" not in result1

        result2 = sanitize_text("api-key:secret456")
        assert "secret456" not in result2

    def test_sanitize_text_no_sensitive_data(self):
        """Text without sensitive data passes through."""
        text = "This is just normal text with model and parameters"
        assert sanitize_text(text) == text

    def test_sanitize_text_case_insensitive(self):
        """Key name matching is case-insensitive."""
        result = sanitize_text("API_KEY=secret123")
        assert "secret123" not in result


class TestSanitizeHeaders:
    """Tests for sanitize_headers function."""

    def test_sanitize_headers_authorization(self):
        """Authorization header gets masked."""
        headers = {"Authorization": "Bearer sk-123456"}
        result = sanitize_headers(headers)
        assert "sk-123456" not in result["Authorization"]
        assert result["Authorization"] == "Bear...56"

    def test_sanitize_headers_api_key(self):
        """X-API-Key header gets masked."""
        headers = {"X-API-Key": "sk-987654321"}
        result = sanitize_headers(headers)
        assert "sk-987654321" not in result["X-API-Key"]

    def test_sanitize_headers_safe_headers_pass(self):
        """Non-sensitive headers pass through unchanged."""
        headers = {
            "User-Agent": "curl/7.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        result = sanitize_headers(headers)
        assert result == headers

    def test_sanitize_headers_mixed(self):
        """Mix of sensitive and safe headers."""
        headers = {
            "Authorization": "Bearer secret123",
            "User-Agent": "browser",
            "X-API-Key": "key456",
        }
        result = sanitize_headers(headers)
        assert result["User-Agent"] == "browser"
        assert "secret123" not in result["Authorization"]
        assert "key456" not in result["X-API-Key"]

    def test_sanitize_headers_case_insensitive(self):
        """Header name matching is case-insensitive."""
        headers = {
            "authorization": "Bearer token789",
            "x-api-key": "key123",
        }
        result = sanitize_headers(headers)
        assert "token789" not in result["authorization"]
        assert "key123" not in result["x-api-key"]

    def test_sanitize_headers_empty(self):
        """Empty headers dict returns empty."""
        assert sanitize_headers({}) == {}


class TestSafeRepr:
    """Tests for safe_repr function."""

    def test_safe_repr_with_api_key(self):
        """API key in object repr gets masked."""
        obj = {"api_key": "sk-123456", "model": "gpt-4"}
        result = safe_repr(obj)
        assert "sk-123456" not in result
        assert "gpt-4" in result

    def test_safe_repr_length_cap(self):
        """Long repr gets capped."""
        long_str = "x" * 250
        result = safe_repr(long_str, max_length=100)
        assert len(result) <= 104  # 100 + "..."

    def test_safe_repr_default_length(self):
        """Default max_length is 200."""
        obj = {"key": "a" * 300}
        result = safe_repr(obj)
        assert len(result) <= 204  # 200 + "..."

    def test_safe_repr_no_truncation_needed(self):
        """Short repr not truncated."""
        obj = {"model": "gpt-4"}
        result = safe_repr(obj)
        assert "..." not in result

    def test_safe_repr_multiple_sensitive(self):
        """Multiple sensitive fields all masked."""
        obj = {
            "api_key": "sk-123456",
            "token": "abc789",
            "password": "secret",
        }
        result = safe_repr(obj)
        assert "sk-123456" not in result
        assert "abc789" not in result
        assert "secret" not in result

    def test_safe_repr_empty_object(self):
        """Empty dict repr works."""
        result = safe_repr({})
        assert result == "{}"


class TestIntegration:
    """Integration tests across functions."""

    def test_full_sanitization_flow(self):
        """Complete sanitization of mixed data."""
        url = "https://api.com/?api_key=secret123&q=test"
        headers = {"Authorization": "Bearer token456"}
        text = "Connecting to server with password=pass789"

        clean_url = sanitize_url(url)
        clean_headers = sanitize_headers(headers)
        clean_text = sanitize_text(text)

        assert "secret123" not in clean_url
        assert "token456" not in clean_headers["Authorization"]
        assert "pass789" not in clean_text
        assert "test" in clean_url

    def test_nested_sanitization(self):
        """Sanitization works on nested structures."""
        obj = {
            "config": {
                "api_key": "sk-nested123",
                "url": "https://api.com/?token=abc",
            }
        }
        result = safe_repr(obj)
        assert "sk-nested123" not in result
        assert "abc" not in result
