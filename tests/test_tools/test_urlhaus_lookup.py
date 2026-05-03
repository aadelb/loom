"""Unit tests for research_urlhaus_lookup — URLhaus threat database lookup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import Response

from loom.tools.urlhaus_lookup import research_urlhaus_check, research_urlhaus_search


class TestURLhausCheck:
    """research_urlhaus_check queries URLhaus for URL threats."""

    def test_urlhaus_check_invalid_url_format(self) -> None:
        """Rejects non-HTTP URLs."""
        result = research_urlhaus_check(url="not-a-url")

        assert result["error"] is not None
        assert "Invalid URL" in result["error"]
        assert result["threat"] is None
        assert result["status"] is None

    def test_urlhaus_check_missing_protocol(self) -> None:
        """Rejects URLs without http:// or https://."""
        result = research_urlhaus_check(url="example.com")

        assert "Invalid URL" in result["error"]

    def test_urlhaus_check_empty_url(self) -> None:
        """Rejects empty URL."""
        result = research_urlhaus_check(url="")

        assert "Invalid URL" in result["error"]

    def test_urlhaus_check_not_listed(self) -> None:
        """Returns not_listed when URL is clean."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={"query_status": "ok", "result": []}
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_check(url="https://example.com")

            assert result["threat"] is None
            assert result["status"] == "not_listed"
            assert result["tags"] == []
            assert result["date_added"] is None

    def test_urlhaus_check_url_listed(self) -> None:
        """Returns threat details when URL is listed."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "query_status": "ok",
                    "result": [
                        {
                            "threat": "malware",
                            "tags": ["trojan", "banking"],
                            "date_added": "2026-04-20",
                        }
                    ],
                }
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_check(url="https://malware-site.com")

            assert result["status"] == "listed"
            assert result["threat"] == "malware"
            assert "trojan" in result["tags"]
            assert result["date_added"] == "2026-04-20"

    def test_urlhaus_check_query_failed(self) -> None:
        """Handles API query failures."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={"query_status": "invalid_url"}
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_check(url="https://test.com")

            assert "error" in result
            assert result["status"] is None

    def test_urlhaus_check_network_error(self) -> None:
        """Handles network errors gracefully."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post = MagicMock(side_effect=Exception("Network error"))
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_check(url="https://test.com")

            assert "error" in result
            assert "Network error" in result["error"]

    def test_urlhaus_check_http_protocol(self) -> None:
        """Accepts http:// protocol."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={"query_status": "ok", "result": []}
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_check(url="http://example.com")

            assert result["url"] == "http://example.com"
            assert "error" not in result
            assert result["status"] == "not_listed"


class TestURLhausSearch:
    """research_urlhaus_search queries URLhaus by tag, signature, or hash."""

    def test_urlhaus_search_empty_query(self) -> None:
        """Rejects empty query."""
        result = research_urlhaus_search(query="")

        assert result["error"] == "query required"
        assert result["results"] == []
        assert result["total"] == 0

    def test_urlhaus_search_by_tag(self) -> None:
        """Searches URLhaus by tag."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "query_status": "ok",
                    "result": [
                        {
                            "url": "http://malware1.com",
                            "url_status": "online",
                            "threat": "trojan",
                            "tags": ["banking"],
                            "date_added": "2026-04-20",
                        },
                        {
                            "url": "http://malware2.com",
                            "url_status": "offline",
                            "threat": "ransomware",
                            "tags": ["banking"],
                            "date_added": "2026-04-21",
                        },
                    ],
                }
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_search(query="banking", search_type="tag")

            assert result["type"] == "tag"
            assert result["total"] == 2
            assert len(result["results"]) == 2
            assert result["results"][0]["threat"] == "trojan"
            assert result["results"][1]["threat"] == "ransomware"

    def test_urlhaus_search_by_hash(self) -> None:
        """Searches URLhaus by payload hash."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "query_status": "ok",
                    "result": [
                        {
                            "url": "http://malware-hash.com",
                            "url_status": "online",
                            "threat": "malware",
                            "tags": ["exploit"],
                            "date_added": "2026-04-19",
                        }
                    ],
                }
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_search(
                query="abc123def456", search_type="hash"
            )

            assert result["type"] == "hash"
            assert result["total"] == 1

    def test_urlhaus_search_by_signature(self) -> None:
        """Searches URLhaus by signature."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "query_status": "ok",
                    "result": [
                        {
                            "url": "http://sig-match.com",
                            "url_status": "online",
                            "threat": "phishing",
                            "tags": [],
                            "date_added": "2026-04-18",
                        }
                    ],
                }
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_search(
                query="suspicious_signature", search_type="signature"
            )

            assert result["type"] == "signature"
            assert result["results"][0]["threat"] == "phishing"

    def test_urlhaus_search_invalid_type_defaults_to_tag(self) -> None:
        """Defaults to tag search for invalid type."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={"query_status": "ok", "result": []}
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_search(
                query="test", search_type="invalid"  # type: ignore
            )

            assert result["type"] == "tag"

    def test_urlhaus_search_no_results(self) -> None:
        """Returns empty results when no matches found."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={"query_status": "ok", "result": []}
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_search(query="nonexistent_tag")

            assert result["total"] == 0
            assert result["results"] == []

    def test_urlhaus_search_query_failed(self) -> None:
        """Handles API query failures."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={"query_status": "invalid_query"}
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_search(query="test")

            assert "error" in result
            assert result["total"] == 0

    def test_urlhaus_search_network_error(self) -> None:
        """Handles network errors gracefully."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post = MagicMock(side_effect=Exception("Network error"))
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_search(query="test")

            assert "error" in result
            assert result["total"] == 0

    def test_urlhaus_search_results_capped_at_50(self) -> None:
        """Results are capped at 50 entries."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            # Create 100 results
            results_list = [
                {
                    "url": f"http://malware{i}.com",
                    "url_status": "online",
                    "threat": "malware",
                    "tags": [],
                    "date_added": "2026-04-20",
                }
                for i in range(100)
            ]

            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={"query_status": "ok", "result": results_list}
            )
            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = research_urlhaus_search(query="test")

            assert result["total"] == 50
            assert len(result["results"]) == 50
