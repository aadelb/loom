"""Unit tests for URL and input validators (SSRF prevention, gh query sanitization).

Tests are ported from /tmp/research-toolbox-staging/test_validators.py
and cover 11 SSRF cases + 7 GitHub query cases, all currently passing.
"""

from __future__ import annotations

import pytest

from loom.validators import GH_QUERY_RE, UrlSafetyError, validate_url



pytestmark = pytest.mark.asyncio
class TestValidateUrl:
    """SSRF validator tests — 11 cases."""

    async def test_ssrf_public_https(self) -> None:
        """Allow public https URLs."""
        url = "https://huggingface.co"
        result = validate_url(url)
        assert result == url

    async def test_ssrf_public_http(self) -> None:
        """Allow public http URLs."""
        url = "https://arxiv.org/abs/2406.11717"
        result = validate_url(url)
        assert result == url

    async def test_ssrf_loopback_v4(self) -> None:
        """Block loopback IPv4."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1:8080")

    async def test_ssrf_loopback_v6(self) -> None:
        """Block loopback IPv6."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::1]:8080")

    async def test_ssrf_ec2_metadata(self) -> None:
        """Block EC2 metadata endpoint."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/latest/meta-data")

    async def test_ssrf_rfc1918_10_subnet(self) -> None:
        """Block RFC1918 10.0.0.0/8."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://10.0.0.1")

    async def test_ssrf_rfc1918_192_subnet(self) -> None:
        """Block RFC1918 192.168.0.0/16."""
        with pytest.raises(UrlSafetyError):
            validate_url("https://192.168.1.1")

    async def test_ssrf_rfc1918_172_subnet(self) -> None:
        """Block RFC1918 172.16.0.0/12."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://172.16.0.5")

    async def test_ssrf_file_scheme(self) -> None:
        """Block file:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("file:///etc/passwd")

    async def test_ssrf_ftp_scheme(self) -> None:
        """Block ftp:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("ftp://example.com")

    async def test_ssrf_localhost_hostname(self) -> None:
        """Block localhost hostname."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://localhost")


class TestGitHubQueryValidator:
    """GitHub query allow-list tests — 7 cases."""

    async def test_gh_query_normal(self) -> None:
        """Allow normal research query."""
        query = "fanar arabic llm"
        assert GH_QUERY_RE.match(query)
        assert not query.lstrip().startswith("-")

    async def test_gh_query_with_version(self) -> None:
        """Allow query with version numbers."""
        query = "Qwen3.5-9B"
        assert GH_QUERY_RE.match(query)
        assert not query.lstrip().startswith("-")

    async def test_gh_query_with_spaces(self) -> None:
        """Allow query with spaces."""
        query = "refusal direction abliteration"
        assert GH_QUERY_RE.match(query)
        assert not query.lstrip().startswith("-")

    async def test_gh_query_rejects_long_flag(self) -> None:
        """Reject --flag injection."""
        query = "--flag evil"
        # Should either fail regex OR start with dash
        result = bool(GH_QUERY_RE.match(query)) and not query.lstrip().startswith("-")
        assert not result

    async def test_gh_query_rejects_short_flag(self) -> None:
        """Reject -o flag injection."""
        query = "-o evil"
        result = bool(GH_QUERY_RE.match(query)) and not query.lstrip().startswith("-")
        assert not result

    async def test_gh_query_rejects_shell_injection(self) -> None:
        """Reject $() shell injection."""
        query = "$(rm -rf /)"
        # The regex should reject this pattern
        result = bool(GH_QUERY_RE.match(query)) and not query.lstrip().startswith("-")
        assert not result

    async def test_gh_query_with_quotes(self) -> None:
        """Allow normal query with quotes."""
        query = "normal query with 'quotes'"
        assert GH_QUERY_RE.match(query)
        assert not query.lstrip().startswith("-")


class TestOnionUrlValidation:
    """Test .onion URL validation with Tor config."""

    async def test_onion_url_accepted_when_tor_enabled(self) -> None:
        """Accept .onion URLs when TOR_ENABLED is true."""
        from unittest.mock import patch

        with patch("loom.config.get_config", return_value={"TOR_ENABLED": True}):
            result = validate_url("http://exampleonion.onion/path")
            assert result == "http://exampleonion.onion/path"

    async def test_onion_url_rejected_when_tor_disabled(self) -> None:
        """Reject .onion URLs when TOR_ENABLED is false."""
        from unittest.mock import patch

        with patch("loom.config.get_config", return_value={"TOR_ENABLED": False}), pytest.raises(UrlSafetyError):
            validate_url("http://exampleonion.onion/path")


class TestDNSCaching:
    """Test DNS caching functionality with Redis fallback."""

    async def test_dns_cache_get_set_local(self) -> None:
        """Test local DNS cache get/set."""
        from loom.validators import _get_cached_dns, _set_cached_dns

        # Clear cache first
        from loom.validators import _dns_cache
        _dns_cache.clear()

        host = "test-example.com"
        ips = ["1.2.3.4", "5.6.7.8"]

        # Initially should be None
        result = _get_cached_dns(host)
        assert result is None

        # Set the cache
        _set_cached_dns(host, ips)

        # Should now return the IPs
        cached = _get_cached_dns(host)
        assert cached == ips

    async def test_dns_cache_expiration(self) -> None:
        """Test DNS cache expiration after TTL."""
        from loom.validators import _get_cached_dns, _set_cached_dns, _DNS_CACHE_TTL, _dns_cache
        import time

        _dns_cache.clear()

        host = "expiring-example.com"
        ips = ["1.2.3.4"]

        # Set cache
        _set_cached_dns(host, ips)
        assert _get_cached_dns(host) == ips

        # Manually expire the cache entry
        if host in _dns_cache:
            old_ips, _ = _dns_cache[host]
            _dns_cache[host] = (old_ips, time.time() - _DNS_CACHE_TTL - 1)

        # Should now be expired and return None
        result = _get_cached_dns(host)
        assert result is None

    async def test_validate_url_caches_dns(self) -> None:
        """Test that validate_url caches DNS results."""
        from loom.validators import validate_url, get_validated_dns, _dns_cache

        _dns_cache.clear()

        url = "https://huggingface.co"
        validate_url(url)

        # DNS for huggingface.co should now be cached
        ips = get_validated_dns("huggingface.co")
        assert ips is not None
        assert len(ips) > 0
        assert all(isinstance(ip, str) for ip in ips)
