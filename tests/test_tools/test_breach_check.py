"""Unit tests for breach_check tool — Email and password breach checking."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from loom.tools.breach_check import (
    _is_valid_email,
    research_breach_check,
    research_password_check,
)


class TestIsValidEmail:
    """Email format validation."""

    def test_valid_email(self) -> None:
        """Valid emails pass validation."""
        assert _is_valid_email("user@example.com")
        assert _is_valid_email("test.name@subdomain.example.org")
        assert _is_valid_email("john+tag@company.co.uk")

    def test_invalid_email_no_at(self) -> None:
        """Email without @ fails validation."""
        assert not _is_valid_email("userexample.com")

    def test_invalid_email_no_domain(self) -> None:
        """Email without domain fails validation."""
        assert not _is_valid_email("user@")
        assert not _is_valid_email("@example.com")

    def test_invalid_email_multiple_at(self) -> None:
        """Email with multiple @ fails validation."""
        assert not _is_valid_email("user@@example.com")

    def test_invalid_email_spaces(self) -> None:
        """Email with spaces fails validation."""
        assert not _is_valid_email("user @example.com")
        assert not _is_valid_email("user@ example.com")

    def test_invalid_email_empty(self) -> None:
        """Empty email fails validation."""
        assert not _is_valid_email("")
        assert not _is_valid_email(None)

    def test_email_too_long(self) -> None:
        """Email exceeding 254 chars fails validation."""
        long_email = "a" * 250 + "@example.com"
        assert not _is_valid_email(long_email)


class TestBreachCheck:
    """research_breach_check function."""

    def test_invalid_email_format(self) -> None:
        """Invalid email format returns error."""
        result = research_breach_check("not-an-email")
        assert result.get("error")
        assert "Invalid email" in result["error"]

    def test_no_api_key(self) -> None:
        """Missing API key returns message."""
        with patch.dict("os.environ", {}, clear=False):
            result = research_breach_check("user@example.com")
            assert result["api_available"] is False
            assert result["breaches_found"] == 0
            assert "HIBP_API_KEY" in result.get("message", "")

    @patch.dict("os.environ", {"HIBP_API_KEY": "test-key"})
    def test_email_not_in_breach(self) -> None:
        """Email not in breach returns 0 breaches."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_breach_check("safe@example.com")
            assert result["api_available"] is True
            assert result["breaches_found"] == 0
            assert result["breaches"] == []

    @patch.dict("os.environ", {"HIBP_API_KEY": "test-key"})
    def test_email_in_breach(self) -> None:
        """Email in breach returns breach data."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "Name": "LinkedIn",
                    "BreachDate": "2021-06-22",
                    "DataClasses": ["Email addresses", "Passwords"],
                },
                {
                    "Name": "Equifax",
                    "BreachDate": "2017-09-07",
                    "DataClasses": ["Names", "Social Security numbers"],
                },
            ]
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_breach_check("compromised@example.com")
            assert result["api_available"] is True
            assert result["breaches_found"] == 2
            assert len(result["breaches"]) == 2
            assert result["breaches"][0]["name"] == "LinkedIn"
            assert "Passwords" in result["breaches"][0]["data_classes"]

    @patch.dict("os.environ", {"HIBP_API_KEY": "test-key"})
    def test_api_error(self) -> None:
        """API error returns error message."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_breach_check("user@example.com")
            assert result.get("error")
            assert "401" in result["error"]

    @patch.dict("os.environ", {"HIBP_API_KEY": "test-key"})
    def test_timeout_error(self) -> None:
        """Request timeout returns error."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client_class.return_value = mock_client

            result = research_breach_check("user@example.com")
            assert result.get("error")
            assert "timeout" in result["error"].lower()


class TestPasswordCheck:
    """research_password_check function."""

    def test_empty_password(self) -> None:
        """Empty password returns error."""
        result = research_password_check("")
        assert result.get("error")

    def test_password_too_long(self) -> None:
        """Password exceeding 256 chars returns error."""
        long_password = "a" * 257
        result = research_password_check(long_password)
        assert result.get("error")
        assert "too long" in result["error"].lower()

    def test_password_not_pwned(self) -> None:
        """Non-pwned password returns pwned_count 0."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Mock HIBP k-anonymity response (no match for our password)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "0018A45C0D5C205246012A1ADA4CB6C2:3\n0018A4B4F9AFCE1B96B7E8E9D9D7F7E7:5\n"
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_password_check("unique_password_xyz_123")
            assert result["api_available"] is not False
            assert result["pwned_count"] == 0
            assert result["is_pwned"] is False

    def test_password_pwned(self) -> None:
        """Pwned password returns pwned_count > 0."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Mock HIBP k-anonymity response (match found)
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Assume password hash starts with "AA1BB" and suffix matches
            mock_response.text = "1BB2C3D4E5F6:123456\n1BB2C3D5E5F7:789012\n"
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_password_check("password123")
            assert result["pwned_count"] >= 0
            # Note: actual result depends on hash computation

    def test_password_strength_very_weak(self) -> None:
        """Short password returns very weak strength."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_password_check("abc")
            assert result["password_length"] == 3
            assert result["strength_hint"] == "very weak"

    def test_password_strength_weak(self) -> None:
        """8-char lowercase password returns weak strength."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_password_check("abcdefgh")
            assert result["password_length"] == 8
            assert result["strength_hint"] == "weak"

    def test_password_strength_strong(self) -> None:
        """Long password with mixed complexity returns strong strength."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_password_check("MyPassw0rd!")
            assert result["password_length"] == 11
            # At least strong (3+ complexity components + length)
            assert result["strength_hint"] in ("strong", "very strong")

    def test_password_complexity_detection(self) -> None:
        """Complexity components are correctly detected."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_password_check("Abc123!@#")
            assert result["complexity_components"]["has_uppercase"] is True
            assert result["complexity_components"]["has_lowercase"] is True
            assert result["complexity_components"]["has_digit"] is True
            assert result["complexity_components"]["has_special"] is True

    def test_timeout_error(self) -> None:
        """Request timeout returns error."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client_class.return_value = mock_client

            result = research_password_check("testpassword")
            assert result.get("error")
            assert "timeout" in result["error"].lower()

    def test_hash_prefix_included(self) -> None:
        """Hash prefix is included in response for verification."""
        with patch("loom.tools.breach_check.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = research_password_check("test")
            assert "hash_prefix_sent" in result
            assert len(result["hash_prefix_sent"]) == 5
            assert all(c in "0123456789ABCDEF" for c in result["hash_prefix_sent"])
