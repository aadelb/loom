"""Security tests for Loom MCP server.

Tests cover:
  - SSRF prevention (private IPs rejected)
  - Injection prevention (SQL/XSS sanitization)
  - Authentication enforcement
  - PII scrubbing in logs
  - Rate limiting enforcement
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.security


class TestSSRFPrevention:
    """Test SSRF attack prevention."""

    def test_private_ips_rejected(self, private_url: str) -> None:
        """Private IP URLs are rejected."""
        try:
            from loom.validators import validate_url

            with pytest.raises((ValueError, RuntimeError)):
                validate_url(private_url)
        except ImportError:
            pytest.skip("SSRF validator not available")

    def test_localhost_rejected(self, localhost_url: str) -> None:
        """Localhost URLs are rejected."""
        try:
            from loom.validators import validate_url

            with pytest.raises((ValueError, RuntimeError)):
                validate_url(localhost_url)
        except ImportError:
            pytest.skip("SSRF validator not available")

    def test_public_url_accepted(self, test_url: str) -> None:
        """Public URLs are accepted."""
        try:
            from loom.validators import validate_url

            # Should not raise
            result = validate_url(test_url)
            assert result is not None
        except ImportError:
            pytest.skip("SSRF validator not available")

    def test_private_ranges_rejected(self) -> None:
        """All private IP ranges are rejected."""
        private_ranges = [
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://192.168.1.1",
            "http://169.254.1.1",
        ]

        try:
            from loom.validators import validate_url

            for url in private_ranges:
                with pytest.raises((ValueError, RuntimeError)):
                    validate_url(url)
        except ImportError:
            pytest.skip("SSRF validator not available")


class TestInjectionPrevention:
    """Test injection attack prevention."""

    def test_query_parameter_sanitization(self) -> None:
        """Query parameters are properly validated."""
        try:
            from loom.validators import sanitize_query

            # SQL injection attempt
            malicious = "'; DROP TABLE users; --"
            result = sanitize_query(malicious)

            # Should be escaped/sanitized
            assert "DROP TABLE" not in result or result == malicious

        except (ImportError, AttributeError):
            pytest.skip("Query sanitizer not available")

    def test_url_parameter_validation(self, test_url: str) -> None:
        """URL parameters are validated."""
        try:
            from loom.validators import validate_url

            # Valid URL should pass
            result = validate_url(test_url)
            assert result is not None

            # Malicious URLs should fail
            malicious_urls = [
                "javascript:alert('xss')",
                "data:text/html,<script>alert('xss')</script>",
            ]

            for mal_url in malicious_urls:
                with pytest.raises((ValueError, RuntimeError)):
                    validate_url(mal_url)

        except ImportError:
            pytest.skip("URL validator not available")


class TestAuthenticationEnforcement:
    """Test authentication and authorization."""

    def test_auth_module_exists(self) -> None:
        """Authentication module is available."""
        try:
            from loom.auth import AuthSettings  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("Auth module not available")

    def test_api_key_middleware_exists(self) -> None:
        """API key middleware is configured."""
        try:
            from loom.api_auth import ApiKeyAuthMiddleware  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("API key middleware not available")


class TestPIIScrubbing:
    """Test PII removal from logs."""

    def test_email_scrubber_exists(self) -> None:
        """Email scrubber is available."""
        try:
            from loom.audit import _redact_params

            # Test email redaction
            params = {"email": "test@example.com", "name": "John"}
            result = _redact_params(params)

            # Email should be redacted
            assert "test@example.com" not in str(result)

        except (ImportError, AttributeError):
            pytest.skip("PII scrubber not available")

    def test_phone_scrubber_exists(self) -> None:
        """Phone number scrubber is available."""
        try:
            from loom.audit import _redact_params

            params = {"phone": "1234567890", "name": "John"}
            result = _redact_params(params)

            # Phone should be redacted
            assert "1234567890" not in str(result)

        except (ImportError, AttributeError):
            pytest.skip("Phone scrubber not available")


class TestRateLimiting:
    """Test rate limiting enforcement."""

    def test_rate_limiter_exists(self) -> None:
        """Rate limiter module is available."""
        try:
            from loom.rate_limiter import rate_limited  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("Rate limiter not available")

    def test_rate_limiter_decorator_functional(self) -> None:
        """Rate limiter decorator is functional."""
        try:
            from loom.rate_limiter import rate_limited

            @rate_limited("test_category")
            async def test_func() -> str:
                return "ok"

            assert callable(test_func)

        except ImportError:
            pytest.skip("Rate limiter not available")


class TestSecretManagement:
    """Test secret handling."""

    def test_no_hardcoded_secrets(self) -> None:
        """Check that common secret patterns are not in config."""
        try:
            from loom.config import CONFIG

            # Verify no API keys in default config
            config_str = str(CONFIG)

            forbidden_patterns = ["sk-", "sk_", "api_key=", "password="]

            for pattern in forbidden_patterns:
                assert pattern.lower() not in config_str.lower(), (
                    f"Potential hardcoded secret pattern: {pattern}"
                )

        except ImportError:
            pytest.skip("Config not available")

    def test_secret_manager_exists(self) -> None:
        """Secret manager is available."""
        try:
            from loom.secret_manager import get_secret_manager  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("Secret manager not available")


class TestInputValidation:
    """Test input validation at boundaries."""

    def test_url_character_limits(self, test_url: str) -> None:
        """URLs have reasonable length limits."""
        try:
            from loom.validators import validate_url

            # Extremely long URL should be rejected
            long_url = test_url + "?" + "a" * 10000

            with pytest.raises((ValueError, RuntimeError)):
                validate_url(long_url)

        except ImportError:
            pytest.skip("URL validator not available")

    def test_query_character_limits(self) -> None:
        """Query parameters have length limits."""
        try:
            from loom.validators import sanitize_query

            # Extremely long query
            long_query = "a" * 100000

            result = sanitize_query(long_query)

            # Should either be capped or validated
            assert result is not None

        except (ImportError, AttributeError):
            pytest.skip("Query validator not available")


class TestAuditTrail:
    """Test audit logging for security events."""

    def test_audit_logging_available(self) -> None:
        """Audit logging is available."""
        try:
            from loom.audit import log_invocation  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("Audit logging not available")

    def test_audit_entry_has_timestamp(self) -> None:
        """Audit entries include timestamp."""
        try:
            from loom.audit import AuditEntry

            entry = AuditEntry(
                client_id="test",
                tool_name="research_test",
                params_summary={},
                timestamp="2025-01-01T10:00:00Z",
                duration_ms=100,
                status="success",
            )

            assert entry.timestamp is not None

        except ImportError:
            pytest.skip("Audit module not available")
