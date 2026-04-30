"""Structured error responses for Loom tools.

All errors follow REQ-069: error responses include error_code, message,
and suggestion fields. Tools return error dicts instead of raising exceptions,
enabling callers to pass them directly to the MCP client.
"""

from __future__ import annotations

from typing import Any


class LoomError:
    """Standardized error response builder for Loom tools."""

    @staticmethod
    def tool_error(
        tool_name: str, error: Exception, suggestion: str = ""
    ) -> dict[str, Any]:
        """Build a standardized error response from an exception.

        Args:
            tool_name: Name of the tool that encountered the error
            error: The exception that was raised
            suggestion: Optional custom suggestion (uses default if not provided)

        Returns:
            Dict with error_code, message, suggestion, tool_name, and error_type
        """
        error_type = type(error).__name__
        code_map = {
            "TimeoutError": "TIMEOUT",
            "asyncio.TimeoutError": "TIMEOUT",
            "ConnectionError": "CONNECTION_FAILED",
            "ValueError": "INVALID_INPUT",
            "KeyError": "MISSING_PARAM",
            "PermissionError": "AUTH_REQUIRED",
            "FileNotFoundError": "NOT_FOUND",
            "TypeError": "INVALID_INPUT",
            "RuntimeError": "INTERNAL_ERROR",
            "OSError": "SYSTEM_ERROR",
        }
        return {
            "error_code": code_map.get(error_type, "INTERNAL_ERROR"),
            "message": str(error),
            "suggestion": suggestion or _default_suggestion(error_type),
            "tool_name": tool_name,
            "error_type": error_type,
        }

    @staticmethod
    def rate_limited(tool_name: str, retry_after: int = 60) -> dict[str, Any]:
        """Build a rate limit exceeded error response.

        Args:
            tool_name: Name of the tool that is rate limited
            retry_after: Number of seconds until retry is possible (default 60)

        Returns:
            Dict with error_code, message, suggestion, tool_name, and retry_after
        """
        return {
            "error_code": "RATE_LIMITED",
            "message": f"Rate limit exceeded for {tool_name}",
            "suggestion": f"Retry after {retry_after} seconds",
            "tool_name": tool_name,
            "retry_after": retry_after,
        }

    @staticmethod
    def insufficient_credits(
        tool_name: str, required: int, available: int
    ) -> dict[str, Any]:
        """Build an insufficient credits error response.

        Args:
            tool_name: Name of the tool requiring credits
            required: Number of credits required
            available: Number of credits currently available

        Returns:
            Dict with error_code, message, suggestion, tool_name, required, available
        """
        return {
            "error_code": "INSUFFICIENT_CREDITS",
            "message": f"Need {required} credits for {tool_name}, only {available} available",
            "suggestion": "Top up credits at /billing or upgrade tier",
            "tool_name": tool_name,
            "required": required,
            "available": available,
        }

    @staticmethod
    def provider_unavailable(provider: str, error: Exception) -> dict[str, Any]:
        """Build a provider unavailable error response.

        Args:
            provider: Name of the unavailable provider
            error: The exception that caused the unavailability

        Returns:
            Dict with error_code, message, suggestion, provider, and error_type
        """
        return {
            "error_code": "PROVIDER_UNAVAILABLE",
            "message": f"Provider {provider} is unavailable: {error}",
            "suggestion": "System will automatically try next provider in cascade",
            "provider": provider,
            "error_type": type(error).__name__,
        }

    @staticmethod
    def validation_error(
        tool_name: str, field: str, reason: str
    ) -> dict[str, Any]:
        """Build a validation error response.

        Args:
            tool_name: Name of the tool with validation error
            field: Name of the field that failed validation
            reason: Reason for validation failure

        Returns:
            Dict with error_code, message, suggestion, tool_name, and field
        """
        return {
            "error_code": "VALIDATION_ERROR",
            "message": f"Invalid {field}: {reason}",
            "suggestion": "Check input parameters match expected format",
            "tool_name": tool_name,
            "field": field,
        }

    @staticmethod
    def configuration_error(config_key: str, reason: str) -> dict[str, Any]:
        """Build a configuration error response.

        Args:
            config_key: The configuration key that is missing or invalid
            reason: Reason for the configuration error

        Returns:
            Dict with error_code, message, suggestion, and config_key
        """
        return {
            "error_code": "CONFIGURATION_ERROR",
            "message": f"Configuration error for {config_key}: {reason}",
            "suggestion": "Check environment variables and config file",
            "config_key": config_key,
        }

    @staticmethod
    def dependency_error(dependency: str, reason: str) -> dict[str, Any]:
        """Build a dependency error response.

        Args:
            dependency: Name of the missing or unavailable dependency
            reason: Reason for the dependency error

        Returns:
            Dict with error_code, message, suggestion, and dependency
        """
        return {
            "error_code": "DEPENDENCY_ERROR",
            "message": f"Dependency {dependency} unavailable: {reason}",
            "suggestion": "Install required dependencies or check system requirements",
            "dependency": dependency,
        }


def _default_suggestion(error_type: str) -> str:
    """Get default suggestion for an error type.

    Args:
        error_type: The Python exception type name

    Returns:
        A helpful default suggestion for the error type
    """
    suggestions = {
        "TimeoutError": "Try again or increase timeout in config",
        "asyncio.TimeoutError": "Try again or increase timeout in config",
        "ConnectionError": "Check network connectivity and provider status",
        "ValueError": "Check input parameters match expected format",
        "KeyError": "Ensure all required parameters are provided",
        "PermissionError": "Set LOOM_API_KEY environment variable",
        "FileNotFoundError": "Check that the required file exists",
        "TypeError": "Check input parameter types match expected types",
        "RuntimeError": "Check logs for detailed error information",
        "OSError": "Check system resources and permissions",
    }
    return suggestions.get(
        error_type, "Check logs for details or contact support"
    )
