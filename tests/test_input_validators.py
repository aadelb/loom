"""Tests for shared input_validators module."""
from __future__ import annotations

import pytest

from loom.input_validators import (
    ValidationError,
    validate_domain,
    validate_email,
    validate_ip,
    validate_query,
    validate_timeout,
    validate_username,
)


class TestValidateDomain:
    def test_valid_domain(self):
        assert validate_domain("example.com") == "example.com"

    def test_valid_subdomain(self):
        assert validate_domain("sub.example.com") == "sub.example.com"

    def test_strips_whitespace(self):
        assert validate_domain("  example.com  ") == "example.com"

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("")

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("a" * 254)

    def test_leading_dot_raises(self):
        with pytest.raises(ValidationError):
            validate_domain(".example.com")

    def test_trailing_dot_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("example.com.")

    def test_special_chars_raises(self):
        with pytest.raises(ValidationError):
            validate_domain("example.com; rm -rf /")

    def test_non_string_raises(self):
        with pytest.raises(ValidationError):
            validate_domain(123)


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_email("")

    def test_no_at_sign_raises(self):
        with pytest.raises(ValidationError):
            validate_email("userexample.com")

    def test_non_string_raises(self):
        with pytest.raises(ValidationError):
            validate_email(None)


class TestValidateIp:
    def test_valid_ipv4(self):
        assert validate_ip("192.168.1.1") == "192.168.1.1"

    def test_valid_ipv6(self):
        result = validate_ip("::1")
        assert result == "::1"

    def test_invalid_ip_raises(self):
        with pytest.raises(ValidationError):
            validate_ip("not-an-ip")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_ip("")


class TestValidateQuery:
    def test_valid_query(self):
        assert validate_query("search term") == "search term"

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_query("")

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_query("a" * 10001)


class TestValidateTimeout:
    def test_valid_timeout(self):
        assert validate_timeout(30) == 30

    def test_valid_float(self):
        assert validate_timeout(10.5) == 10.5

    def test_negative_clamps_to_min(self):
        result = validate_timeout(-1)
        assert result >= 1.0

    def test_zero_clamps_to_min(self):
        result = validate_timeout(0)
        assert result >= 1.0


class TestValidateUsername:
    def test_valid_username(self):
        assert validate_username("john_doe") == "john_doe"

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_username("")
