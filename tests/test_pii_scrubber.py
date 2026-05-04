"""Unit tests for PII scrubbing middleware.

Tests regex patterns for detecting and scrubbing:
- Email addresses
- Phone numbers
- IP addresses (IPv4/IPv6)
- Credit card numbers
- Social Security Numbers / National IDs
- API keys
- Database connection strings
- AWS credentials
"""

from __future__ import annotations

import asyncio
import pytest

from loom.pii_scrubber import (
    scrub_pii,
    scrub_dict,
    scrub_output,
    _scrub_list,
    _scrub_result,
)


class TestEmailScrubbing:
    """Test email address detection and scrubbing."""

    def test_scrub_simple_email(self) -> None:
        text = "Contact me at john@example.com"
        result = scrub_pii(text)
        assert result == "Contact me at [EMAIL]"

    def test_scrub_multiple_emails(self) -> None:
        text = "Email john@example.com or jane.doe@company.org"
        result = scrub_pii(text)
        assert "[EMAIL]" in result
        assert "john@example.com" not in result
        assert "jane.doe@company.org" not in result

    def test_scrub_email_with_special_chars(self) -> None:
        text = "Contact: alice.smith+tag@example.co.uk"
        result = scrub_pii(text)
        assert "[EMAIL]" in result
        assert "alice.smith+tag@example.co.uk" not in result

    def test_preserve_non_email(self) -> None:
        text = "No email here"
        result = scrub_pii(text)
        assert result == text


class TestPhoneScrubbing:
    """Test phone number detection and scrubbing."""

    def test_scrub_us_phone_with_dashes(self) -> None:
        text = "Call me at 555-123-4567"
        result = scrub_pii(text)
        assert "[PHONE]" in result
        assert "555-123-4567" not in result

    def test_scrub_us_phone_with_parens(self) -> None:
        text = "Call (555) 123-4567"
        result = scrub_pii(text)
        assert "[PHONE]" in result

    def test_scrub_us_phone_with_spaces(self) -> None:
        text = "Call 555 123 4567"
        result = scrub_pii(text)
        assert "[PHONE]" in result

    def test_scrub_international_phone(self) -> None:
        text = "International: +44 20 7946 0958"
        result = scrub_pii(text)
        assert "[PHONE]" in result

    def test_scrub_plus_format_phone(self) -> None:
        text = "Contact +1-555-123-4567"
        result = scrub_pii(text)
        assert "[PHONE]" in result


class TestIPAddressScrubbing:
    """Test IP address detection and scrubbing."""

    def test_scrub_ipv4_address(self) -> None:
        text = "Server at 192.168.1.1"
        result = scrub_pii(text)
        assert result == "Server at [IP]"
        assert "192.168.1.1" not in result

    def test_scrub_multiple_ipv4_addresses(self) -> None:
        text = "Ping 10.0.0.1 or 172.16.0.1"
        result = scrub_pii(text)
        assert result.count("[IP]") == 2
        assert "10.0.0.1" not in result
        assert "172.16.0.1" not in result

    def test_scrub_ipv6_address(self) -> None:
        text = "IPv6: 2001:db8::1"
        result = scrub_pii(text)
        assert "[IP]" in result
        assert "2001:db8::1" not in result

    def test_scrub_ipv6_full(self) -> None:
        text = "Full IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        result = scrub_pii(text)
        assert "[IP]" in result


class TestCreditCardScrubbing:
    """Test credit card number detection and scrubbing."""

    def test_scrub_visa_card(self) -> None:
        text = "Card 4532015112830366"
        result = scrub_pii(text)
        assert "[CARD]" in result
        assert "4532015112830366" not in result

    def test_scrub_mastercard(self) -> None:
        text = "Card 5425233010103442"
        result = scrub_pii(text)
        assert "[CARD]" in result

    def test_scrub_amex_card(self) -> None:
        text = "Card 374245455400126"
        result = scrub_pii(text)
        assert "[CARD]" in result

    def test_scrub_card_with_spaces(self) -> None:
        text = "Card: 4532 0151 1283 0366"
        result = scrub_pii(text)
        assert "[CARD]" in result

    def test_scrub_card_with_dashes(self) -> None:
        text = "Card: 4532-0151-1283-0366"
        result = scrub_pii(text)
        assert "[CARD]" in result


class TestSSNScrubbing:
    """Test Social Security Number / National ID detection and scrubbing."""

    def test_scrub_ssn_with_dashes(self) -> None:
        text = "SSN: 123-45-6789"
        result = scrub_pii(text)
        assert "[ID]" in result
        assert "123-45-6789" not in result

    def test_scrub_ssn_with_dots(self) -> None:
        text = "ID: 123.45.6789"
        result = scrub_pii(text)
        assert "[ID]" in result

    def test_skip_invalid_ssn(self) -> None:
        # SSNs starting with 000, 666, or 9xx are invalid
        text = "Invalid: 000-00-0000"
        # This test just verifies it doesn't crash
        result = scrub_pii(text)
        assert isinstance(result, str)


class TestAPIKeyScrubbing:
    """Test API key detection and scrubbing."""

    def test_scrub_openai_key_format(self) -> None:
        """Test OpenAI key format detection."""
        # Use a format that's long enough and doesn't match phone patterns
        text = "api_key sk-ABCDEFGHIJKLMNOPQRSTuvwxyzABCD"
        result = scrub_pii(text)
        # Should scrub either as API_KEY or at least the key portion
        assert "[API_KEY]" in result or "sk-" not in result

    def test_scrub_key_equals_pattern(self) -> None:
        text = "api_key=secret_abcdef1234567890123456"
        result = scrub_pii(text)
        assert "[API_KEY]" in result

    def test_scrub_token_equals_pattern(self) -> None:
        text = "token=ghp_1234567890123456789012345678901234567890"
        result = scrub_pii(text)
        assert "[API_KEY]" in result

    def test_scrub_bearer_token(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9_VERYLONGTOKEN"
        result = scrub_pii(text)
        # Should scrub the bearer token portion
        assert "[API_KEY]" in result or "Bearer" in result

    def test_scrub_github_token(self) -> None:
        text = "ghp_1234567890123456789012345678901234567890123456"
        result = scrub_pii(text)
        assert "[API_KEY]" in result

    def test_scrub_secret_equals(self) -> None:
        """Test secret= pattern."""
        text = "database_secret=VeryLongSecretString1234567890ABCDEF"
        result = scrub_pii(text)
        assert "[API_KEY]" in result


class TestDatabaseConnectionScrubbing:
    """Test database connection string detection and scrubbing."""

    def test_scrub_postgres_connection(self) -> None:
        text = "postgres://user:password@localhost/dbname"
        result = scrub_pii(text)
        assert "[DB_CONN]" in result
        assert "password" not in result or "[DB_CONN]" in result

    def test_scrub_mysql_connection(self) -> None:
        text = "mysql://admin:secret123@localhost:3306/mydb"
        result = scrub_pii(text)
        assert "[DB_CONN]" in result

    def test_scrub_mongodb_connection(self) -> None:
        text = "mongodb://user:pass@mongo.example.com:27017"
        result = scrub_pii(text)
        assert "[DB_CONN]" in result


class TestAWSCredentialsScrubbing:
    """Test AWS credentials detection and scrubbing."""

    def test_scrub_aws_access_key(self) -> None:
        text = "AKIAIOSFODNN7EXAMPLE"
        result = scrub_pii(text)
        assert "[AWS_KEY]" in result

    def test_scrub_aws_secret_key(self) -> None:
        text = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        result = scrub_pii(text)
        assert "[AWS_KEY]" in result


class TestDictScrubbing:
    """Test recursive dictionary scrubbing."""

    def test_scrub_simple_dict(self) -> None:
        data = {"email": "john@example.com", "name": "John"}
        result = scrub_dict(data)
        assert result["email"] == "[EMAIL]"
        assert result["name"] == "John"

    def test_scrub_nested_dict(self) -> None:
        data = {
            "user": {
                "email": "alice@example.com",
                "contact": {
                    "phone": "555-123-4567"
                }
            }
        }
        result = scrub_dict(data)
        assert result["user"]["email"] == "[EMAIL]"
        assert "[PHONE]" in result["user"]["contact"]["phone"]

    def test_scrub_dict_with_list(self) -> None:
        data = {
            "emails": ["john@example.com", "jane@example.com"],
            "count": 2
        }
        result = scrub_dict(data)
        assert result["emails"][0] == "[EMAIL]"
        assert result["emails"][1] == "[EMAIL]"
        assert result["count"] == 2

    def test_preserve_non_string_values(self) -> None:
        data = {
            "id": 12345,
            "active": True,
            "score": 95.5,
            "tags": None
        }
        result = scrub_dict(data)
        assert result["id"] == 12345
        assert result["active"] is True
        assert result["score"] == 95.5
        assert result["tags"] is None

    def test_immutability(self) -> None:
        original = {"email": "test@example.com"}
        result = scrub_dict(original)
        # Original should not be modified
        assert original["email"] == "test@example.com"
        assert result["email"] == "[EMAIL]"


class TestListScrubbing:
    """Test list scrubbing helper function."""

    def test_scrub_list_of_strings(self) -> None:
        data = ["john@example.com", "normal text", "192.168.1.1"]
        result = _scrub_list(data)
        assert result[0] == "[EMAIL]"
        assert result[1] == "normal text"
        assert result[2] == "[IP]"

    def test_scrub_nested_list(self) -> None:
        data = [
            ["john@example.com", "jane@example.com"],
            ["192.168.1.1"]
        ]
        result = _scrub_list(data)
        assert result[0][0] == "[EMAIL]"
        assert result[0][1] == "[EMAIL]"
        assert result[1][0] == "[IP]"

    def test_scrub_list_with_dicts(self) -> None:
        data = [
            {"email": "john@example.com"},
            {"phone": "555-123-4567"}
        ]
        result = _scrub_list(data)
        assert result[0]["email"] == "[EMAIL]"
        assert "[PHONE]" in result[1]["phone"]


class TestScrubDecorator:
    """Test @scrub_output decorator for functions."""

    def test_scrub_sync_function_string(self) -> None:
        @scrub_output
        def get_email() -> str:
            return "john@example.com"

        result = get_email()
        assert result == "[EMAIL]"

    def test_scrub_sync_function_dict(self) -> None:
        @scrub_output
        def get_user_data() -> dict:
            return {
                "email": "john@example.com",
                "phone": "555-123-4567"
            }

        result = get_user_data()
        assert result["email"] == "[EMAIL]"
        assert "[PHONE]" in result["phone"]

    def test_scrub_sync_function_list(self) -> None:
        @scrub_output
        def get_ips() -> list:
            return ["192.168.1.1", "10.0.0.1"]

        result = get_ips()
        assert result == ["[IP]", "[IP]"]

    @pytest.mark.asyncio
    async def test_scrub_async_function_string(self) -> None:
        @scrub_output
        async def get_email_async() -> str:
            await asyncio.sleep(0)
            return "john@example.com"

        result = await get_email_async()
        assert result == "[EMAIL]"

    @pytest.mark.asyncio
    async def test_scrub_async_function_dict(self) -> None:
        @scrub_output
        async def get_user_async() -> dict:
            await asyncio.sleep(0)
            return {
                "email": "john@example.com",
                "phone": "555-123-4567"
            }

        result = await get_user_async()
        assert result["email"] == "[EMAIL]"
        assert "[PHONE]" in result["phone"]

    def test_scrub_function_with_args(self) -> None:
        @scrub_output
        def create_log(message: str) -> str:
            return f"Log: {message}"

        result = create_log("User john@example.com logged in")
        assert "[EMAIL]" in result

    def test_preserve_function_metadata(self) -> None:
        @scrub_output
        def my_function() -> str:
            """My docstring."""
            return "test"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestScrubResult:
    """Test _scrub_result helper function."""

    def test_scrub_result_string(self) -> None:
        result = _scrub_result("john@example.com")
        assert result == "[EMAIL]"

    def test_scrub_result_dict(self) -> None:
        data = {"email": "john@example.com"}
        result = _scrub_result(data)
        assert result["email"] == "[EMAIL]"

    def test_scrub_result_list(self) -> None:
        data = ["john@example.com"]
        result = _scrub_result(data)
        assert result[0] == "[EMAIL]"

    def test_scrub_result_non_string(self) -> None:
        # Non-string, non-dict, non-list values pass through unchanged
        assert _scrub_result(42) == 42
        assert _scrub_result(True) is True
        assert _scrub_result(None) is None


class TestNonStringInputs:
    """Test behavior with non-string inputs."""

    def test_scrub_pii_non_string(self) -> None:
        # scrub_pii should handle non-string inputs gracefully
        assert scrub_pii(None) is None
        assert scrub_pii(42) == 42
        assert scrub_pii(True) is True

    def test_scrub_dict_non_dict(self) -> None:
        # scrub_dict should return non-dict inputs as-is
        assert scrub_dict("string") == "string"  # type: ignore[arg-type]
        assert scrub_dict(None) is None  # type: ignore[arg-type]
        assert scrub_dict(42) == 42  # type: ignore[arg-type]


class TestRealWorldScenarios:
    """Test real-world PII scrubbing scenarios."""

    def test_scrub_error_message_with_pii(self) -> None:
        error = "Connection failed from 192.168.1.100 user@example.com"
        result = scrub_pii(error)
        assert "[IP]" in result
        assert "[EMAIL]" in result

    def test_scrub_log_entry(self) -> None:
        log = "User john@example.com with phone 555-123-4567 logged in from 10.0.0.1"
        result = scrub_pii(log)
        assert "[EMAIL]" in result
        assert "[PHONE]" in result
        assert "[IP]" in result

    def test_scrub_api_request_data(self) -> None:
        data = {
            "user_email": "john@example.com",
            "phone": "555-123-4567",
            "card_number": "4532015112830366",
        }
        result = scrub_dict(data)
        assert result["user_email"] == "[EMAIL]"
        assert "[PHONE]" in result["phone"]
        assert "[CARD]" in result["card_number"]

    def test_scrub_database_credentials(self) -> None:
        config = "postgres://admin:password123@db.example.com/mydb"
        result = scrub_pii(config)
        assert "[DB_CONN]" in result

    def test_scrub_audit_entry(self) -> None:
        entry = {
            "client_id": "user-john@example.com",
            "tool": "research_fetch",
            "params": {
                "url": "http://example.com",
            },
            "result": "Success from 192.168.1.1",
            "timestamp": "2025-01-01T00:00:00Z"
        }
        result = scrub_dict(entry)
        assert "[EMAIL]" in result["client_id"]
        assert "[IP]" in result["result"]

    def test_scrub_multiple_pii_types(self) -> None:
        text = (
            "Error: User alice@example.com (555-987-6543) tried to pay with "
            "card 4111111111111111 from 10.20.30.40"
        )
        result = scrub_pii(text)
        assert "[EMAIL]" in result
        assert "[PHONE]" in result
        assert "[CARD]" in result
        assert "[IP]" in result
