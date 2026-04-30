"""Tests for Loom structured error responses.

Tests verify that LoomError builder creates consistent error responses
with error_code, message, and suggestion fields as per REQ-069.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from loom.errors import LoomError


class TestToolError:
    """Test LoomError.tool_error for standard exception handling."""

    def test_tool_error_timeout_error(self) -> None:
        """TimeoutError maps to TIMEOUT code."""
        error = TimeoutError("Request took too long")
        result = LoomError.tool_error("research_fetch", error)

        assert isinstance(result, dict)
        assert result["error_code"] == "TIMEOUT"
        assert result["message"] == "Request took too long"
        assert result["tool_name"] == "research_fetch"
        assert result["error_type"] == "TimeoutError"
        assert "suggestion" in result
        assert isinstance(result["suggestion"], str)
        assert len(result["suggestion"]) > 0

    def test_tool_error_connection_error(self) -> None:
        """ConnectionError maps to CONNECTION_FAILED code."""
        error = ConnectionError("Failed to connect to provider")
        result = LoomError.tool_error("research_search", error)

        assert result["error_code"] == "CONNECTION_FAILED"
        assert result["message"] == "Failed to connect to provider"
        assert result["tool_name"] == "research_search"
        assert result["error_type"] == "ConnectionError"
        assert "suggestion" in result

    def test_tool_error_value_error(self) -> None:
        """ValueError maps to INVALID_INPUT code."""
        error = ValueError("Invalid URL format")
        result = LoomError.tool_error("research_spider", error)

        assert result["error_code"] == "INVALID_INPUT"
        assert result["message"] == "Invalid URL format"
        assert result["tool_name"] == "research_spider"
        assert result["error_type"] == "ValueError"

    def test_tool_error_key_error(self) -> None:
        """KeyError maps to MISSING_PARAM code."""
        error = KeyError("api_key")
        result = LoomError.tool_error("research_llm_summarize", error)

        assert result["error_code"] == "MISSING_PARAM"
        assert result["tool_name"] == "research_llm_summarize"
        assert result["error_type"] == "KeyError"

    def test_tool_error_permission_error(self) -> None:
        """PermissionError maps to AUTH_REQUIRED code."""
        error = PermissionError("Access denied")
        result = LoomError.tool_error("research_config_set", error)

        assert result["error_code"] == "AUTH_REQUIRED"
        assert result["message"] == "Access denied"
        assert result["tool_name"] == "research_config_set"
        assert result["error_type"] == "PermissionError"

    def test_tool_error_file_not_found(self) -> None:
        """FileNotFoundError maps to NOT_FOUND code."""
        error = FileNotFoundError("Config file not found")
        result = LoomError.tool_error("research_config_get", error)

        assert result["error_code"] == "NOT_FOUND"
        assert result["message"] == "Config file not found"
        assert result["tool_name"] == "research_config_get"
        assert result["error_type"] == "FileNotFoundError"

    def test_tool_error_type_error(self) -> None:
        """TypeError maps to INVALID_INPUT code."""
        error = TypeError("Expected str, got int")
        result = LoomError.tool_error("research_fetch", error)

        assert result["error_code"] == "INVALID_INPUT"
        assert result["message"] == "Expected str, got int"
        assert result["error_type"] == "TypeError"

    def test_tool_error_unknown_exception(self) -> None:
        """Unknown exception type maps to INTERNAL_ERROR."""
        error = RuntimeError("Something went wrong")
        result = LoomError.tool_error("research_pdf_extract", error)

        assert result["error_code"] == "INTERNAL_ERROR"
        assert result["message"] == "Something went wrong"
        assert result["tool_name"] == "research_pdf_extract"
        assert result["error_type"] == "RuntimeError"

    def test_tool_error_custom_suggestion(self) -> None:
        """Custom suggestion overrides default."""
        error = TimeoutError("Request timeout")
        custom_suggestion = "Use a VPN or try a different region"
        result = LoomError.tool_error(
            "research_fetch", error, suggestion=custom_suggestion
        )

        assert result["suggestion"] == custom_suggestion

    def test_tool_error_default_suggestion_applied(self) -> None:
        """Default suggestion is applied when not provided."""
        error = ConnectionError("Network unavailable")
        result = LoomError.tool_error("research_search", error)

        assert result["suggestion"] is not None
        assert "network" in result["suggestion"].lower()

    def test_tool_error_response_is_dict(self) -> None:
        """tool_error always returns a dict, never raises."""
        error = ValueError("Invalid input")
        result = LoomError.tool_error("test_tool", error)

        assert isinstance(result, dict)
        assert "error_code" in result
        assert "message" in result
        assert "suggestion" in result
        assert "tool_name" in result
        assert "error_type" in result

    def test_tool_error_preserves_exception_message(self) -> None:
        """Exception message is preserved in error response."""
        original_message = "This is the specific error that occurred"
        error = RuntimeError(original_message)
        result = LoomError.tool_error("test_tool", error)

        assert result["message"] == original_message


class TestRateLimited:
    """Test LoomError.rate_limited for rate limit errors."""

    def test_rate_limited_default_retry_after(self) -> None:
        """rate_limited returns default retry_after of 60 seconds."""
        result = LoomError.rate_limited("research_search")

        assert result["error_code"] == "RATE_LIMITED"
        assert "Rate limit exceeded for research_search" in result["message"]
        assert result["tool_name"] == "research_search"
        assert result["retry_after"] == 60
        assert "suggestion" in result

    def test_rate_limited_custom_retry_after(self) -> None:
        """rate_limited accepts custom retry_after value."""
        result = LoomError.rate_limited("research_fetch", retry_after=120)

        assert result["error_code"] == "RATE_LIMITED"
        assert result["retry_after"] == 120
        assert "120" in result["suggestion"]

    def test_rate_limited_small_retry_after(self) -> None:
        """rate_limited handles small retry_after values."""
        result = LoomError.rate_limited("research_spider", retry_after=5)

        assert result["retry_after"] == 5
        assert "5" in result["suggestion"]

    def test_rate_limited_response_is_dict(self) -> None:
        """rate_limited always returns a dict."""
        result = LoomError.rate_limited("test_tool")

        assert isinstance(result, dict)
        assert "error_code" in result
        assert "message" in result
        assert "suggestion" in result
        assert "tool_name" in result
        assert "retry_after" in result

    def test_rate_limited_suggestion_mentions_retry(self) -> None:
        """Suggestion clearly mentions how to handle rate limiting."""
        result = LoomError.rate_limited("research_search", retry_after=30)

        assert "retry" in result["suggestion"].lower() or "after" in result[
            "suggestion"
        ].lower()


class TestInsufficientCredits:
    """Test LoomError.insufficient_credits for credit errors."""

    def test_insufficient_credits_basic(self) -> None:
        """insufficient_credits includes required and available credits."""
        result = LoomError.insufficient_credits("research_fetch", required=100, available=50)

        assert result["error_code"] == "INSUFFICIENT_CREDITS"
        assert "100" in result["message"]
        assert "50" in result["message"]
        assert result["tool_name"] == "research_fetch"
        assert result["required"] == 100
        assert result["available"] == 50

    def test_insufficient_credits_suggestion(self) -> None:
        """Suggestion mentions billing."""
        result = LoomError.insufficient_credits("research_search", required=200, available=0)

        assert "billing" in result["suggestion"].lower() or "credits" in result[
            "suggestion"
        ].lower()

    def test_insufficient_credits_zero_available(self) -> None:
        """insufficient_credits handles zero available credits."""
        result = LoomError.insufficient_credits("test_tool", required=10, available=0)

        assert result["available"] == 0
        assert result["required"] == 10

    def test_insufficient_credits_response_is_dict(self) -> None:
        """insufficient_credits always returns a dict."""
        result = LoomError.insufficient_credits("test_tool", required=50, available=25)

        assert isinstance(result, dict)
        assert all(k in result for k in ["error_code", "message", "suggestion", "tool_name", "required", "available"])


class TestProviderUnavailable:
    """Test LoomError.provider_unavailable for provider errors."""

    def test_provider_unavailable_basic(self) -> None:
        """provider_unavailable includes provider name and error details."""
        error = ConnectionError("API returned 503")
        result = LoomError.provider_unavailable("groq", error)

        assert result["error_code"] == "PROVIDER_UNAVAILABLE"
        assert "groq" in result["message"]
        assert result["provider"] == "groq"
        assert result["error_type"] == "ConnectionError"
        assert "suggestion" in result

    def test_provider_unavailable_with_timeout(self) -> None:
        """provider_unavailable handles timeout errors."""
        error = TimeoutError("Request timed out")
        result = LoomError.provider_unavailable("openai", error)

        assert result["provider"] == "openai"
        assert result["error_type"] == "TimeoutError"
        assert "openai" in result["message"]

    def test_provider_unavailable_cascade_suggestion(self) -> None:
        """Suggestion mentions automatic provider cascade."""
        error = RuntimeError("Internal error")
        result = LoomError.provider_unavailable("anthropic", error)

        assert "cascade" in result["suggestion"].lower() or "next" in result[
            "suggestion"
        ].lower()

    def test_provider_unavailable_response_is_dict(self) -> None:
        """provider_unavailable always returns a dict."""
        error = ValueError("Invalid config")
        result = LoomError.provider_unavailable("deepseek", error)

        assert isinstance(result, dict)
        assert all(k in result for k in ["error_code", "message", "suggestion", "provider", "error_type"])


class TestValidationError:
    """Test LoomError.validation_error for input validation errors."""

    def test_validation_error_basic(self) -> None:
        """validation_error includes field name and reason."""
        result = LoomError.validation_error(
            "research_fetch", "url", "URL must be absolute"
        )

        assert result["error_code"] == "VALIDATION_ERROR"
        assert "url" in result["message"].lower()
        assert "URL must be absolute" in result["message"]
        assert result["tool_name"] == "research_fetch"
        assert result["field"] == "url"

    def test_validation_error_response_is_dict(self) -> None:
        """validation_error always returns a dict."""
        result = LoomError.validation_error(
            "test_tool", "api_key", "API key is required"
        )

        assert isinstance(result, dict)
        assert all(k in result for k in ["error_code", "message", "suggestion", "tool_name", "field"])

    def test_validation_error_multiple_fields(self) -> None:
        """validation_error can be called for different fields."""
        url_error = LoomError.validation_error(
            "research_fetch", "url", "Invalid format"
        )
        key_error = LoomError.validation_error(
            "research_fetch", "api_key", "Required"
        )

        assert url_error["field"] == "url"
        assert key_error["field"] == "api_key"
        assert url_error != key_error


class TestConfigurationError:
    """Test LoomError.configuration_error for config errors."""

    def test_configuration_error_basic(self) -> None:
        """configuration_error includes config key and reason."""
        result = LoomError.configuration_error(
            "GROQ_API_KEY", "Environment variable not set"
        )

        assert result["error_code"] == "CONFIGURATION_ERROR"
        assert "GROQ_API_KEY" in result["message"]
        assert "Environment variable not set" in result["message"]
        assert result["config_key"] == "GROQ_API_KEY"

    def test_configuration_error_response_is_dict(self) -> None:
        """configuration_error always returns a dict."""
        result = LoomError.configuration_error("LOOM_HOST", "Invalid value")

        assert isinstance(result, dict)
        assert all(k in result for k in ["error_code", "message", "suggestion", "config_key"])

    def test_configuration_error_suggestion(self) -> None:
        """Suggestion mentions checking config."""
        result = LoomError.configuration_error("API_KEY", "Missing")

        assert "config" in result["suggestion"].lower() or "environment" in result[
            "suggestion"
        ].lower()


class TestDependencyError:
    """Test LoomError.dependency_error for dependency errors."""

    def test_dependency_error_basic(self) -> None:
        """dependency_error includes dependency name and reason."""
        result = LoomError.dependency_error(
            "scrapling", "Package not installed"
        )

        assert result["error_code"] == "DEPENDENCY_ERROR"
        assert "scrapling" in result["message"]
        assert "Package not installed" in result["message"]
        assert result["dependency"] == "scrapling"

    def test_dependency_error_response_is_dict(self) -> None:
        """dependency_error always returns a dict."""
        result = LoomError.dependency_error("playwright", "Not found")

        assert isinstance(result, dict)
        assert all(k in result for k in ["error_code", "message", "suggestion", "dependency"])

    def test_dependency_error_suggestion(self) -> None:
        """Suggestion mentions installing dependencies."""
        result = LoomError.dependency_error("torch", "GPU not available")

        assert "install" in result["suggestion"].lower() or "dependencies" in result[
            "suggestion"
        ].lower()


class TestErrorConsistency:
    """Test consistency across all error types."""

    def test_all_errors_have_error_code(self) -> None:
        """All error responses include error_code."""
        errors = [
            LoomError.tool_error("test", ValueError("test")),
            LoomError.rate_limited("test"),
            LoomError.insufficient_credits("test", 10, 5),
            LoomError.provider_unavailable("test", ValueError("test")),
            LoomError.validation_error("test", "field", "reason"),
            LoomError.configuration_error("KEY", "reason"),
            LoomError.dependency_error("dep", "reason"),
        ]

        for error in errors:
            assert "error_code" in error
            assert isinstance(error["error_code"], str)
            assert len(error["error_code"]) > 0

    def test_all_errors_have_message(self) -> None:
        """All error responses include message."""
        errors = [
            LoomError.tool_error("test", ValueError("test error")),
            LoomError.rate_limited("test"),
            LoomError.insufficient_credits("test", 10, 5),
            LoomError.provider_unavailable("test", ValueError("test")),
            LoomError.validation_error("test", "field", "reason"),
            LoomError.configuration_error("KEY", "reason"),
            LoomError.dependency_error("dep", "reason"),
        ]

        for error in errors:
            assert "message" in error
            assert isinstance(error["message"], str)
            assert len(error["message"]) > 0

    def test_all_errors_have_suggestion(self) -> None:
        """All error responses include suggestion."""
        errors = [
            LoomError.tool_error("test", ValueError("test")),
            LoomError.rate_limited("test"),
            LoomError.insufficient_credits("test", 10, 5),
            LoomError.provider_unavailable("test", ValueError("test")),
            LoomError.validation_error("test", "field", "reason"),
            LoomError.configuration_error("KEY", "reason"),
            LoomError.dependency_error("dep", "reason"),
        ]

        for error in errors:
            assert "suggestion" in error
            assert isinstance(error["suggestion"], str)
            assert len(error["suggestion"]) > 0

    def test_all_errors_return_dicts(self) -> None:
        """All error methods return dicts, never raise."""
        errors = [
            LoomError.tool_error("test", ValueError("test")),
            LoomError.rate_limited("test"),
            LoomError.insufficient_credits("test", 10, 5),
            LoomError.provider_unavailable("test", ValueError("test")),
            LoomError.validation_error("test", "field", "reason"),
            LoomError.configuration_error("KEY", "reason"),
            LoomError.dependency_error("dep", "reason"),
        ]

        for error in errors:
            assert isinstance(error, dict)

    def test_error_codes_are_uppercase_with_underscores(self) -> None:
        """All error_code values follow naming convention."""
        errors = [
            LoomError.tool_error("test", ValueError("test")),
            LoomError.rate_limited("test"),
            LoomError.insufficient_credits("test", 10, 5),
            LoomError.provider_unavailable("test", ValueError("test")),
            LoomError.validation_error("test", "field", "reason"),
            LoomError.configuration_error("KEY", "reason"),
            LoomError.dependency_error("dep", "reason"),
        ]

        for error in errors:
            code = error["error_code"]
            assert code.isupper() or "_" in code
            assert not code.startswith("_")
            assert not code.endswith("_")


class TestAsyncioTimeout:
    """Test that asyncio.TimeoutError is properly handled."""

    def test_asyncio_timeout_error_mapping(self) -> None:
        """asyncio.TimeoutError maps to TIMEOUT code."""
        # Create an asyncio timeout error
        error = asyncio.TimeoutError("Async operation timed out")
        result = LoomError.tool_error("research_fetch", error)

        # asyncio.TimeoutError should map to TIMEOUT
        assert result["error_code"] == "TIMEOUT"
        assert result["message"] == "Async operation timed out"
        assert result["error_type"] == "TimeoutError"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_error_message(self) -> None:
        """Handles exceptions with empty messages gracefully."""
        error = ValueError()
        result = LoomError.tool_error("test_tool", error)

        assert result["error_code"] == "INVALID_INPUT"
        # Empty string is still valid
        assert "message" in result

    def test_very_long_error_message(self) -> None:
        """Handles very long error messages."""
        long_message = "x" * 10000
        error = RuntimeError(long_message)
        result = LoomError.tool_error("test_tool", error)

        assert result["message"] == long_message
        assert len(result["message"]) == 10000

    def test_special_characters_in_messages(self) -> None:
        """Handles special characters in error messages."""
        message = "Error with émojis 🔥 and spëcial çharacters"
        error = ValueError(message)
        result = LoomError.tool_error("test_tool", error)

        assert result["message"] == message

    def test_tool_name_with_special_characters(self) -> None:
        """Handles tool names with underscores and numbers."""
        result = LoomError.tool_error("research_fetch_v2_beta", ValueError("test"))

        assert result["tool_name"] == "research_fetch_v2_beta"
