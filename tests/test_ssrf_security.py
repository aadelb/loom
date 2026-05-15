"""Comprehensive SSRF security testing for Loom MCP server.

Tests cover 35+ SSRF bypass techniques including:
  - IPv4 representation variants (hex, decimal, octal, short form)
  - IPv6 variants and IPv4-mapped IPv6
  - Cloud metadata endpoints (AWS, GCP, Alibaba, Azure)
  - DNS rebinding and localhost variants
  - URL encoding and double encoding
  - Redirect/auth-bypass patterns
  - Internal network ranges (RFC1918)
  - File protocol and dangerous schemes
  - TLD confusion and subdomain tricks
  - Case sensitivity and null byte injection
  - Port-based bypass attempts

Every payload is tested to verify it either:
  1. Is correctly rejected (raises UrlSafetyError), or
  2. Results in a sanitized/safe URL

CRITICAL VULNERABILITIES: Any payload that passes validation is flagged.
"""

from __future__ import annotations

import pytest

from loom.validators import UrlSafetyError, validate_url


class TestIPv4Variants:
    """Test SSRF prevention against IPv4 representation variants."""

    def test_ipv4_literal_127_0_0_1(self) -> None:
        """Block direct IPv4 loopback literal."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1/")

    def test_ipv4_literal_127_0_0_1_with_port(self) -> None:
        """Block loopback with port."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1:8787/")

    def test_ipv4_hex_0x7f000001(self) -> None:
        """Block hex-encoded IPv4 loopback (0x7f000001)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://0x7f000001/")

    def test_ipv4_hex_0x127_0_0_1_per_octet(self) -> None:
        """Block mixed hex-decimal per octet."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://0x7f.0.0.1/")

    def test_ipv4_decimal_2130706433(self) -> None:
        """Block decimal representation of 127.0.0.1 (2130706433)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://2130706433/")

    def test_ipv4_octal_0177_0_0_1(self) -> None:
        """Block octal representation 0177.0.0.1."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://0177.0.0.1/")

    def test_ipv4_short_form_127_1(self) -> None:
        """Block short-form IPv4 loopback (127.1)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.1/")

    def test_ipv4_short_form_127_with_port(self) -> None:
        """Block short-form with port (127:8080)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127:8080/")

    def test_ipv4_aws_metadata_169_254_169_254(self) -> None:
        """Block AWS metadata endpoint 169.254.169.254."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_ipv4_gcp_metadata_169_254_169_254_alternate(self) -> None:
        """Block GCP metadata (same as AWS)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/computeMetadata/v1/")

    def test_ipv4_alibaba_metadata_100_100_100_200(self) -> None:
        """Block Alibaba metadata endpoint 100.100.100.200."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://100.100.100.200/latest/meta-data/")

    def test_ipv4_zero_0_0_0_0(self) -> None:
        """Block 0.0.0.0 (unspecified address)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://0.0.0.0/")

    def test_ipv4_broadcast_255_255_255_255(self) -> None:
        """Block broadcast address 255.255.255.255."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://255.255.255.255/")


class TestIPv6Variants:
    """Test SSRF prevention against IPv6 representation variants."""

    def test_ipv6_literal_loopback_1(self) -> None:
        """Block IPv6 loopback [::1]."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::1]/")

    def test_ipv6_literal_loopback_1_with_port(self) -> None:
        """Block IPv6 loopback with port [::1]:8787."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::1]:8787/")

    def test_ipv6_expanded_loopback_0_0_0_0_0_0_0_1(self) -> None:
        """Block expanded IPv6 loopback [0:0:0:0:0:0:0:1]."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[0:0:0:0:0:0:0:1]/")

    def test_ipv6_ipv4_mapped_127_0_0_1(self) -> None:
        """Block IPv4-mapped IPv6 loopback [::ffff:127.0.0.1]."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::ffff:127.0.0.1]/")

    def test_ipv6_ipv4_mapped_10_0_0_1(self) -> None:
        """Block IPv4-mapped IPv6 for private IP [::ffff:10.0.0.1]."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::ffff:10.0.0.1]/")

    def test_ipv6_ipv4_mapped_192_168_1_1(self) -> None:
        """Block IPv4-mapped IPv6 for private IP [::ffff:192.168.1.1]."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::ffff:192.168.1.1]/")

    def test_ipv6_unspecified_0_0_0_0_0_0_0_0(self) -> None:
        """Block IPv6 unspecified address [::]."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[::]/")

    def test_ipv6_private_fc_prefix(self) -> None:
        """Block IPv6 private address fc00::1."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[fc00::1]/")


class TestCloudMetadataEndpoints:
    """Test SSRF prevention against cloud provider metadata endpoints."""

    def test_aws_ec2_metadata_169_254(self) -> None:
        """Block AWS EC2 metadata endpoint."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_aws_ec2_metadata_imdsv2(self) -> None:
        """Block AWS IMDSv2 endpoint (still 169.254)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/latest/api/token")

    def test_gcp_metadata_google_internal(self) -> None:
        """Block GCP metadata server metadata.google.internal."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://metadata.google.internal/")

    def test_gcp_metadata_169_254(self) -> None:
        """Block GCP metadata via 169.254.169.254 (same as AWS)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/computeMetadata/v1/")

    def test_azure_metadata_169_254_169_254(self) -> None:
        """Block Azure metadata endpoint 169.254.169.254:80."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254:80/metadata/instance")

    def test_alibaba_metadata_100_100_100_200(self) -> None:
        """Block Alibaba cloud metadata 100.100.100.200."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://100.100.100.200/latest/meta-data/")

    def test_openstack_metadata_169_254(self) -> None:
        """Block OpenStack metadata endpoint 169.254.169.254."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.169.254/metadata/")


class TestDNSRebindingVariants:
    """Test SSRF prevention against DNS rebinding and hostname tricks."""

    def test_localhost_hostname(self) -> None:
        """Block localhost hostname."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://localhost/")

    def test_localhost_with_port(self) -> None:
        """Block localhost with port."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://localhost:8080/")

    def test_localhost_localdomain(self) -> None:
        """Block localhost.localdomain."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://localhost.localdomain/")

    def test_hostname_127_0_0_1_local(self) -> None:
        """Block 127.0.0.1.local hostname."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1.local/")

    def test_hostname_loopback_local(self) -> None:
        """Block loopback.local hostname."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://loopback.local/")


class TestURLEncoding:
    """Test SSRF prevention against URL encoding bypasses."""

    def test_url_encoded_127_0_0_1(self) -> None:
        """Block URL-encoded 127.0.0.1 (%31%32%37%2e...)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://%31%32%37%2e%30%2e%30%2e%31/")

    def test_url_encoded_localhost(self) -> None:
        """Block URL-encoded localhost."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://%6c%6f%63%61%6c%68%6f%73%74/")

    def test_mixed_encoded_decoded_127_1(self) -> None:
        """Block mixed encoding 127.%30.0.1."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.%30.0.1/")

    def test_unicode_encoding_127_0_0_1(self) -> None:
        """Block unicode-encoded IP address."""
        # This depends on urlparse behavior; may or may not be necessary
        # Test is included for completeness
        with pytest.raises(UrlSafetyError):
            validate_url("http://127․0․0․1/")  # Using unicode dots


class TestRedirectBypassPatterns:
    """Test SSRF prevention against auth/redirect bypass patterns."""

    def test_userinfo_bypass_example_at_loopback(self) -> None:
        """Block user@loopback bypass (user:pass@127.0.0.1)."""
        # urlparse extracts hostname correctly, should still be blocked
        with pytest.raises(UrlSafetyError):
            validate_url("http://user:pass@127.0.0.1/")

    def test_domain_at_loopback_bypass(self) -> None:
        """Block domain@loopback bypass (example.com@127.0.0.1)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://example.com@127.0.0.1/")

    def test_fragment_bypass_loopback(self) -> None:
        """Block fragment bypass (#) with loopback."""
        # Fragment is not sent to server, but URL should be blocked anyway
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1#@example.com/")

    def test_query_bypass_loopback(self) -> None:
        """Block query bypass (?) with loopback."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1?@example.com/")


class TestInternalNetworkRanges:
    """Test SSRF prevention against RFC1918 private networks."""

    def test_rfc1918_10_0_0_0_8_start(self) -> None:
        """Block RFC1918 10.0.0.0/8 start."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://10.0.0.0/")

    def test_rfc1918_10_0_0_1(self) -> None:
        """Block RFC1918 10.0.0.1."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://10.0.0.1/")

    def test_rfc1918_10_255_255_255(self) -> None:
        """Block RFC1918 10.255.255.255 (end of range)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://10.255.255.255/")

    def test_rfc1918_172_16_0_0_12_start(self) -> None:
        """Block RFC1918 172.16.0.0/12 start."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://172.16.0.0/")

    def test_rfc1918_172_16_0_1(self) -> None:
        """Block RFC1918 172.16.0.1."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://172.16.0.1/")

    def test_rfc1918_172_31_255_255(self) -> None:
        """Block RFC1918 172.31.255.255 (end of range)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://172.31.255.255/")

    def test_rfc1918_192_168_0_0_16_start(self) -> None:
        """Block RFC1918 192.168.0.0/16 start."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://192.168.0.0/")

    def test_rfc1918_192_168_1_1(self) -> None:
        """Block RFC1918 192.168.1.1."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://192.168.1.1/")

    def test_rfc1918_192_168_255_255(self) -> None:
        """Block RFC1918 192.168.255.255 (end of range)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://192.168.255.255/")

    def test_link_local_169_254_0_0_16(self) -> None:
        """Block link-local 169.254.0.0/16 (except metadata)."""
        # 169.254.0.1 should be blocked (link-local)
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.0.1/")

    def test_link_local_169_254_255_255(self) -> None:
        """Block link-local end of range 169.254.255.255."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://169.254.255.255/")


class TestDangerousSchemes:
    """Test SSRF prevention against dangerous URL schemes."""

    def test_file_scheme_etc_passwd(self) -> None:
        """Block file:// scheme (local file access)."""
        with pytest.raises(UrlSafetyError):
            validate_url("file:///etc/passwd")

    def test_file_scheme_windows_path(self) -> None:
        """Block file:// scheme with Windows path."""
        with pytest.raises(UrlSafetyError):
            validate_url("file:///C:/Windows/System32/config/SAM")

    def test_ftp_scheme(self) -> None:
        """Block ftp:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("ftp://example.com/")

    def test_sftp_scheme(self) -> None:
        """Block sftp:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("sftp://example.com/")

    def test_gopher_scheme(self) -> None:
        """Block gopher:// scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("gopher://example.com/")

    def test_data_scheme(self) -> None:
        """Block data: scheme (can bypass validation)."""
        with pytest.raises(UrlSafetyError):
            validate_url("data:text/html,<script>alert('xss')</script>")

    def test_javascript_scheme(self) -> None:
        """Block javascript: scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("javascript:alert('xss')")

    def test_about_scheme(self) -> None:
        """Block about: scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("about:blank")

    def test_blob_scheme(self) -> None:
        """Block blob: scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("blob:https://example.com/123")


class TestNullByteAndCaseInsensitivity:
    """Test edge cases with null bytes and case sensitivity."""

    def test_null_byte_in_hostname(self) -> None:
        """Block URLs with null bytes in hostname."""
        # Python's urlparse may handle this differently
        with pytest.raises(UrlSafetyError):
            validate_url("http://127.0.0.1%00.example.com/")

    def test_uppercase_file_scheme(self) -> None:
        """Block FILE:// scheme (case insensitive)."""
        with pytest.raises(UrlSafetyError):
            validate_url("FILE:///etc/passwd")

    def test_mixed_case_http_scheme(self) -> None:
        """Accept HTTP:// with mixed case scheme (normalized)."""
        result = validate_url("HTTP://example.com")
        assert result is not None

    def test_uppercase_localhost(self) -> None:
        """Block LOCALHOST (case insensitive)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://LOCALHOST/")


class TestValidPublicURLs:
    """Test that legitimate public URLs pass validation."""

    def test_valid_https_public_domain(self) -> None:
        """Allow valid HTTPS public domain."""
        result = validate_url("https://example.com")
        assert result is not None

    def test_valid_http_public_domain(self) -> None:
        """Allow valid HTTP public domain."""
        result = validate_url("https://github.com/")
        assert result is not None

    def test_valid_url_with_path(self) -> None:
        """Allow valid URL with path."""
        result = validate_url("https://example.com/path/to/resource")
        assert result is not None

    def test_valid_url_with_query(self) -> None:
        """Allow valid URL with query string."""
        result = validate_url("https://example.com/search?q=test")
        assert result is not None

    def test_valid_url_with_port(self) -> None:
        """Allow valid public domain with port."""
        result = validate_url("https://example.com:443/")
        assert result is not None


class TestEdgeCasesAndMalformed:
    """Test edge cases and malformed URLs."""

    def test_missing_scheme(self) -> None:
        """Block URL with missing scheme."""
        with pytest.raises(UrlSafetyError):
            validate_url("example.com")

    def test_missing_hostname(self) -> None:
        """Block URL with missing hostname."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://")

    def test_empty_string(self) -> None:
        """Block empty URL string."""
        with pytest.raises(UrlSafetyError):
            validate_url("")

    def test_whitespace_only(self) -> None:
        """Block whitespace-only URL."""
        with pytest.raises(UrlSafetyError):
            validate_url("   ")

    def test_url_too_long(self) -> None:
        """Block URL exceeding max length (4096)."""
        long_url = "https://example.com/" + "a" * 5000
        with pytest.raises(UrlSafetyError):
            validate_url(long_url)

    def test_invalid_ipv6_format(self) -> None:
        """Block invalid IPv6 format."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://[invalid:ipv6]/")

    def test_invalid_ipv4_format(self) -> None:
        """Block invalid IPv4 format."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://256.256.256.256/")


class TestMulticastAndReserved:
    """Test SSRF prevention against multicast and reserved IP ranges."""

    def test_multicast_224_0_0_1(self) -> None:
        """Block multicast address 224.0.0.1."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://224.0.0.1/")

    def test_multicast_239_255_255_255(self) -> None:
        """Block multicast address 239.255.255.255 (end of range)."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://239.255.255.255/")

    def test_reserved_240_0_0_0(self) -> None:
        """Block reserved address 240.0.0.0."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://240.0.0.0/")

    def test_reserved_255_255_255_255(self) -> None:
        """Block reserved broadcast 255.255.255.255."""
        with pytest.raises(UrlSafetyError):
            validate_url("http://255.255.255.255/")
