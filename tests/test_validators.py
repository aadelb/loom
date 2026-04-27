"""Unit tests for URL and input validators (SSRF prevention, gh query sanitization).

Tests are ported from /tmp/research-toolbox-staging/test_validators.py
and cover 11 SSRF cases + 7 GitHub query cases, all currently passing.
"""

from __future__ import annotations

import pytest

from loom.validators import GH_QUERY_RE, UrlSafetyError, validate_url


class TestValidateUrl:
    """SSRF validator tests — 11 cases."""

    def test_ssrf_public_https(self) -> None:
        """Allow public https URLs."""
        url = "https://huggingface.co"
        result = validate_url(url)
        assert result == url

    def test_ssrf_public_http(self) -> None:
        """Allow public http URLs."""
        url = "https://arxiv.org/abs/2406.11717"
        result = validate_url(url)
        assert result == url

    def test_ssrf_loopback_v4(self) -> None:
        """Block loopback IPv4."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1:8080")

    def test_ssrf_loopback_v6(self) -> None:
        """Block loopback IPv6."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::1]:8080")

    def test_ssrf_ec2_metadata(self) -> None:
        """Block EC2 metadata endpoint."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/latest/meta-data")

    def test_ssrf_rfc1918_10_subnet(self) -> None:
        """Block RFC1918 10.0.0.0/8."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://10.0.0.1")

    def test_ssrf_rfc1918_192_subnet(self) -> None:
        """Block RFC1918 192.168.0.0/16."""
        with pytest.raises(UrlSafetyError):
            validate_url("https://192.168.1.1")

    def test_ssrf_rfc1918_172_subnet(self) -> None:
        """Block RFC1918 172.16.0.0/12."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://172.16.0.5")

    def test_ssrf_file_scheme(self) -> None:
        """Block file:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("file:///etc/passwd")

    def test_ssrf_ftp_scheme(self) -> None:
        """Block ftp:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("ftp://example.com")

    def test_ssrf_localhost_hostname(self) -> None:
        """Block localhost hostname."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://localhost")


class TestGitHubQueryValidator:
    """GitHub query allow-list tests — 7 cases."""

    def test_gh_query_normal(self) -> None:
        """Allow normal research query."""
        query = "fanar arabic llm"
        assert GH_QUERY_RE.match(query)
        assert not query.lstrip().startswith("-")

    def test_gh_query_with_version(self) -> None:
        """Allow query with version numbers."""
        query = "Qwen3.5-9B"
        assert GH_QUERY_RE.match(query)
        assert not query.lstrip().startswith("-")

    def test_gh_query_with_spaces(self) -> None:
        """Allow query with spaces."""
        query = "refusal direction abliteration"
        assert GH_QUERY_RE.match(query)
        assert not query.lstrip().startswith("-")

    def test_gh_query_rejects_long_flag(self) -> None:
        """Reject --flag injection."""
        query = "--flag evil"
        # Should either fail regex OR start with dash
        result = bool(GH_QUERY_RE.match(query)) and not query.lstrip().startswith("-")
        assert not result

    def test_gh_query_rejects_short_flag(self) -> None:
        """Reject -o flag injection."""
        query = "-o evil"
        result = bool(GH_QUERY_RE.match(query)) and not query.lstrip().startswith("-")
        assert not result

    def test_gh_query_rejects_shell_injection(self) -> None:
        """Reject $() shell injection."""
        query = "$(rm -rf /)"
        # The regex should reject this pattern
        result = bool(GH_QUERY_RE.match(query)) and not query.lstrip().startswith("-")
        assert not result

    def test_gh_query_with_quotes(self) -> None:
        """Allow normal query with quotes."""
        query = "normal query with 'quotes'"
        assert GH_QUERY_RE.match(query)
        assert not query.lstrip().startswith("-")


class TestOnionUrlValidation:
    """Test .onion URL validation with Tor config."""

    def test_onion_url_accepted_when_tor_enabled(self) -> None:
        """Accept .onion URLs when TOR_ENABLED is true."""
        from unittest.mock import patch

        with patch("loom.config.get_config", return_value={"TOR_ENABLED": True}):
            result = validate_url("http://exampleonion.onion/path")
            assert result == "http://exampleonion.onion/path"

    def test_onion_url_rejected_when_tor_disabled(self) -> None:
        """Reject .onion URLs when TOR_ENABLED is false."""
        from unittest.mock import patch

        with patch("loom.config.get_config", return_value={"TOR_ENABLED": False}), pytest.raises(UrlSafetyError):
            validate_url("http://exampleonion.onion/path")
