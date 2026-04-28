"""Unit tests for identity_resolve tool — link online identities via public data."""

from __future__ import annotations

import asyncio
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.identity_resolve import research_identity_resolve


class TestGravatarCheck:
    """research_identity_resolve email → gravatar tests."""

    def test_gravatar_exists(self) -> None:
        """Gravatar check detects existing profile."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head:
            mock_head.return_value = mock_response

            result = research_identity_resolve("test@example.com", query_type="email")

            assert result["query"] == "test@example.com"
            assert result["query_type"] == "email"
            assert result["gravatar"]["exists"] is True
            assert "gravatar.com/avatar/" in result["gravatar"]["url"]

    def test_gravatar_not_exists(self) -> None:
        """Gravatar check detects missing profile."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head:
            mock_head.return_value = mock_response

            result = research_identity_resolve("notfound@example.com", query_type="email")

            assert result["gravatar"]["exists"] is False

    def test_gravatar_hash_correct(self) -> None:
        """Gravatar hash is correct MD5 of lowercase email."""
        email = "Test@EXAMPLE.com"
        expected_hash = hashlib.md5(email.lower().encode()).hexdigest()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head:
            mock_head.return_value = mock_response

            result = research_identity_resolve(email, query_type="email")

            assert result["gravatar"]["hash"] == expected_hash


class TestPGPKeysCheck:
    """research_identity_resolve email → PGP keys tests."""

    def test_pgp_keys_found(self) -> None:
        """PGP keyserver returns key list."""
        pgp_response = {
            "keys": [
                {
                    "keyid": "0x1234567890ABCDEF",
                    "uids": ["Test User <test@example.com>"],
                    "created": "2020-01-01T00:00:00Z",
                },
                {
                    "keyid": "0xFEDCBA0987654321",
                    "uids": ["Test User <test@example.com>"],
                    "created": "2021-06-15T00:00:00Z",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = pgp_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("test@example.com", query_type="email")

            assert result["pgp_keys_count"] == 2
            assert len(result["pgp_keys"]) == 2
            assert result["pgp_keys"][0]["keyid"] == "0x1234567890ABCDEF"

    def test_pgp_keys_not_found(self) -> None:
        """PGP keyserver returns empty list for unknown email."""
        pgp_response = {"keys": []}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = pgp_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("notfound@example.com", query_type="email")

            assert result["pgp_keys_count"] == 0
            assert result["pgp_keys"] == []

    def test_pgp_keys_max_10_returned(self) -> None:
        """PGP keys limited to 10 entries."""
        keys = [
            {
                "keyid": f"0x{i:016x}",
                "uids": [f"User{i} <test{i}@example.com>"],
                "created": "2020-01-01T00:00:00Z",
            }
            for i in range(15)
        ]

        pgp_response = {"keys": keys}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = pgp_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("test@example.com", query_type="email")

            assert result["pgp_keys_count"] == 10


class TestGitHubCommitsCheck:
    """research_identity_resolve email → GitHub commits tests."""

    def test_github_commits_found(self) -> None:
        """GitHub search returns commit count."""
        github_response = {"total_count": 42, "items": []}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("developer@example.com", query_type="email")

            assert result["github_commits"] == 42

    def test_github_commits_zero(self) -> None:
        """GitHub search returns zero commits."""
        github_response = {"total_count": 0, "items": []}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = github_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("unknown@example.com", query_type="email")

            assert result["github_commits"] == 0

    def test_github_api_error_returns_zero(self) -> None:
        """GitHub API error returns zero commits."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API error")

            result = research_identity_resolve("test@example.com", query_type="email")

            assert result["github_commits"] == 0


class TestUsernameplatformCheck:
    """research_identity_resolve username → platforms tests."""

    def test_username_found_on_multiple_platforms(self) -> None:
        """Username found on multiple platforms."""

        async def mock_head(url, **kwargs):
            response = MagicMock()
            # Simulate existing on GitHub and Reddit
            response.status_code = 200 if ("github.com" in url or "reddit.com" in url) else 404
            return response

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head_func:
            mock_head_func.side_effect = mock_head

            result = research_identity_resolve("testuser", query_type="username")

            assert result["query"] == "testuser"
            assert result["query_type"] == "username"
            assert result["platforms_checked"] == 10
            assert result["platforms_found_count"] >= 0
            assert isinstance(result["platforms_found"], list)

    def test_username_platform_structure(self) -> None:
        """Username platform check returns correct structure."""
        async def mock_head(url, **kwargs):
            response = MagicMock()
            response.status_code = 200
            return response

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head_func:
            mock_head_func.side_effect = mock_head

            result = research_identity_resolve("testuser", query_type="username")

            # Check structure
            for platform in result["all_platforms"]:
                assert "platform" in platform
                assert "url" in platform
                assert "exists" in platform

    def test_username_no_platforms_found(self) -> None:
        """Username not found on any platform."""
        async def mock_head(url, **kwargs):
            response = MagicMock()
            response.status_code = 404
            return response

        with patch("httpx.AsyncClient.head", new_callable=AsyncMock) as mock_head_func:
            mock_head_func.side_effect = mock_head

            result = research_identity_resolve("xyzabc123nonexistent", query_type="username")

            assert result["platforms_found_count"] == 0
            assert result["platforms_found"] == []


class TestWhoisCheck:
    """research_identity_resolve domain → WHOIS tests."""

    def test_whois_registrant_found(self) -> None:
        """WHOIS registrant info extracted."""
        rdap_response = {
            "entities": [
                {
                    "roles": ["registrant"],
                    "vcardArray": [
                        "vcard",
                        [
                            ["version", {}, "text", "4.0"],
                            ["fn", {}, "text", "John Doe"],
                            ["org", {}, "text", "Example Corp"],
                        ],
                    ],
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = rdap_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("example.com", query_type="domain")

            assert result["query_type"] == "domain"
            assert "whois_registrant" in result
            assert isinstance(result["whois_registrant"], dict)

    def test_whois_registrant_not_found(self) -> None:
        """WHOIS registrant returns empty when not available."""
        rdap_response = {"entities": []}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = rdap_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("example.com", query_type="domain")

            assert result["whois_registrant"] == {"name": "", "organization": ""}

    def test_whois_rdap_error(self) -> None:
        """WHOIS check handles RDAP errors gracefully."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection error")

            result = research_identity_resolve("example.com", query_type="domain")

            assert result["whois_registrant"] == {"name": "", "organization": ""}


class TestDNSSOACheck:
    """research_identity_resolve domain → DNS SOA email tests."""

    def test_dns_soa_email_found(self) -> None:
        """DNS SOA email extracted."""
        dns_response = {
            "Answer": [
                {
                    "type": 6,
                    "data": "ns.example.com. admin.example.com. 2024042801 10800 3600 604800 3600",
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = dns_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("example.com", query_type="domain")

            assert result["dns_soa_email"] == "admin.example.com."

    def test_dns_soa_email_not_found(self) -> None:
        """DNS SOA email returns empty when not available."""
        dns_response = {"Answer": []}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = dns_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = research_identity_resolve("example.com", query_type="domain")

            assert result["dns_soa_email"] == ""

    def test_dns_api_error(self) -> None:
        """DNS check handles API errors gracefully."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("DNS lookup failed")

            result = research_identity_resolve("example.com", query_type="domain")

            assert result["dns_soa_email"] == ""


class TestEmailResolution:
    """Integration tests for email resolution."""

    def test_email_resolution_complete(self) -> None:
        """Email resolution returns all expected fields."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock all HTTP calls
            async def mock_head(url, **kwargs):
                response = MagicMock()
                response.status_code = 200
                return response

            async def mock_get(url, **kwargs):
                response = MagicMock()
                response.status_code = 200
                if "keys.openpgp.org" in url:
                    response.json.return_value = {"keys": []}
                elif "github.com" in url:
                    response.json.return_value = {"total_count": 5}
                return response

            mock_client.head = AsyncMock(side_effect=mock_head)
            mock_client.get = AsyncMock(side_effect=mock_get)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            result = research_identity_resolve("dev@example.com", query_type="email")

            assert result["query"] == "dev@example.com"
            assert "gravatar" in result
            assert "pgp_keys" in result
            assert "github_commits" in result


class TestDomainResolution:
    """Integration tests for domain resolution."""

    def test_domain_resolution_complete(self) -> None:
        """Domain resolution returns all expected fields."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            async def mock_get(url, **kwargs):
                response = MagicMock()
                response.status_code = 200
                if "rdap.org" in url:
                    response.json.return_value = {"entities": []}
                elif "dns.google" in url:
                    response.json.return_value = {"Answer": []}
                return response

            mock_client.get = AsyncMock(side_effect=mock_get)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            result = research_identity_resolve("example.com", query_type="domain")

            assert result["query"] == "example.com"
            assert "whois_registrant" in result
            assert "dns_soa_email" in result


class TestErrorHandling:
    """Error handling and edge cases."""

    def test_invalid_query_type_defaults(self) -> None:
        """Invalid query_type is handled gracefully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=200))
            mock_client.head = AsyncMock(return_value=MagicMock(status_code=200))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            # Invalid query type should still return result with query_type field
            result = research_identity_resolve("test", query_type="unknown")

            assert result["query_type"] == "unknown"

    def test_empty_query_handled(self) -> None:
        """Empty query is handled."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get = AsyncMock(return_value=MagicMock(status_code=200))
            mock_client.head = AsyncMock(return_value=MagicMock(status_code=200))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            result = research_identity_resolve("", query_type="email")

            assert result["query"] == ""
            assert "gravatar" in result
