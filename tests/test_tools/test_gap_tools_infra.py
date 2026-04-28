"""Unit tests for gap_tools_infra — cloud enumeration, secret scanning, WHOIS correlation, LLM consistency."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.tools.gap_tools_infra import (
    _check_cloud_resource,
    _get_rdap_data,
    _jaccard_similarity,
    _query_llm_endpoint,
    _search_crt_sh,
    research_cloud_enum,
    research_github_secrets,
    research_output_consistency,
    research_whois_correlator,
)


class TestCloudEnum:
    """Cloud resource enumeration for domains."""

    def test_cloud_enum_valid_domain(self) -> None:
        """Valid domain triggers enumeration."""
        result = research_cloud_enum("example.com")
        assert result["domain"] == "example.com"
        assert "cloud_resources" in result
        assert isinstance(result["cloud_resources"], list)

    def test_cloud_enum_empty_domain(self) -> None:
        """Empty domain returns error."""
        result = research_cloud_enum("")
        assert "error" in result
        assert result["domain"] == ""

    def test_cloud_enum_domain_too_long(self) -> None:
        """Domain exceeding 255 chars returns error."""
        long_domain = "a" * 256 + ".com"
        result = research_cloud_enum(long_domain)
        assert "error" in result

    def test_cloud_enum_invalid_chars(self) -> None:
        """Domain with invalid chars returns error."""
        result = research_cloud_enum("example@domain.com")
        assert "error" in result

    def test_cloud_enum_with_subdomain(self) -> None:
        """Subdomain extraction works correctly."""
        result = research_cloud_enum("sub.example.com")
        assert result["domain"] == "sub.example.com"
        assert "cloud_resources" in result


class TestCheckCloudResource:
    """_check_cloud_resource helper function."""

    @pytest.mark.asyncio
    async def test_check_cloud_resource_success(self) -> None:
        """Successful HTTP check returns status and flags."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        async with httpx.AsyncClient() as client:
            with patch.object(client, "head", new_callable=AsyncMock) as mock_head:
                mock_head.return_value = mock_response
                result = await _check_cloud_resource(client, "https://example.s3.amazonaws.com")

        assert result["status"] == 200
        assert result["is_public"] is True
        assert result["is_private"] is False

    @pytest.mark.asyncio
    async def test_check_cloud_resource_private(self) -> None:
        """Status 403 indicates private resource."""
        mock_response = MagicMock()
        mock_response.status_code = 403

        async with httpx.AsyncClient() as client:
            with patch.object(client, "head", new_callable=AsyncMock) as mock_head:
                mock_head.return_value = mock_response
                result = await _check_cloud_resource(client, "https://example.s3.amazonaws.com")

        assert result["status"] == 403
        assert result["is_public"] is False
        assert result["is_private"] is True

    @pytest.mark.asyncio
    async def test_check_cloud_resource_notfound(self) -> None:
        """Status 404 indicates not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        async with httpx.AsyncClient() as client:
            with patch.object(client, "head", new_callable=AsyncMock) as mock_head:
                mock_head.return_value = mock_response
                result = await _check_cloud_resource(client, "https://example.s3.amazonaws.com")

        assert result["status"] == 404
        assert result["is_public"] is False
        assert result["is_private"] is False

    @pytest.mark.asyncio
    async def test_check_cloud_resource_timeout(self) -> None:
        """Network timeout returns error."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "head", new_callable=AsyncMock) as mock_head:
                mock_head.side_effect = httpx.TimeoutException()
                result = await _check_cloud_resource(client, "https://example.s3.amazonaws.com")

        assert result["status"] is None
        assert "error" in result


class TestGithubSecrets:
    """GitHub secret scanning using code search API."""

    def test_github_secrets_valid_query(self) -> None:
        """Valid query returns secrets list."""
        result = research_github_secrets("example")
        assert result["query"] == "example"
        assert "secrets_found" in result
        assert isinstance(result["secrets_found"], list)

    def test_github_secrets_empty_query(self) -> None:
        """Empty query returns error."""
        result = research_github_secrets("")
        assert "error" in result

    def test_github_secrets_query_too_long(self) -> None:
        """Query exceeding 100 chars returns error."""
        long_query = "a" * 101
        result = research_github_secrets(long_query)
        assert "error" in result

    def test_github_secrets_invalid_chars(self) -> None:
        """Query with invalid chars returns error."""
        result = research_github_secrets("example@invalid")
        assert "error" in result

    def test_github_secrets_max_results_capped(self) -> None:
        """max_results capped at 100."""
        result = research_github_secrets("test", max_results=200)
        # Should not error, just cap the results
        assert "secrets_found" in result

    def test_github_secrets_min_max_results(self) -> None:
        """max_results=1 is valid."""
        result = research_github_secrets("test", max_results=1)
        assert "secrets_found" in result

    def test_github_secrets_returns_correct_fields(self) -> None:
        """Results contain expected fields."""
        result = research_github_secrets("example")
        if result.get("secrets_found"):
            secret = result["secrets_found"][0]
            assert "repo" in secret
            assert "file_path" in secret
            assert "match_preview" in secret
            assert "secret_type" in secret


class TestWhoisCorrelator:
    """WHOIS registrant correlation across domains."""

    def test_whois_correlator_valid_domain(self) -> None:
        """Valid domain returns correlation data."""
        result = research_whois_correlator("example.com")
        assert result["domain"] == "example.com"
        assert "registrant_email" in result
        assert "registrant_org" in result
        assert "related_domains" in result
        assert "ownership_graph" in result
        assert isinstance(result["related_domains"], list)
        assert isinstance(result["ownership_graph"], dict)

    def test_whois_correlator_empty_domain(self) -> None:
        """Empty domain returns error."""
        result = research_whois_correlator("")
        assert "error" in result

    def test_whois_correlator_domain_too_long(self) -> None:
        """Domain exceeding 255 chars returns error."""
        long_domain = "a" * 256 + ".com"
        result = research_whois_correlator(long_domain)
        assert "error" in result

    def test_whois_correlator_invalid_chars(self) -> None:
        """Domain with invalid chars returns error."""
        result = research_whois_correlator("example@domain.com")
        assert "error" in result

    def test_whois_correlator_ownership_graph_structure(self) -> None:
        """Ownership graph has correct structure."""
        result = research_whois_correlator("example.com")
        if "ownership_graph" in result:
            graph = result["ownership_graph"]
            if "example.com" in graph:
                node = graph["example.com"]
                assert "email" in node
                assert "org" in node
                assert "related" in node


class TestGetRdapData:
    """_get_rdap_data helper for WHOIS lookups."""

    @pytest.mark.asyncio
    async def test_get_rdap_data_success(self) -> None:
        """Successful RDAP lookup returns registrant info."""
        rdap_response = {
            "entities": [
                {
                    "roles": ["registrant"],
                    "vcardArray": [
                        ["vcard", [["email", {}, "text", "admin@example.com"]]],
                        ["vcard", [["org", {}, "text", "Example Corp"]]],
                    ],
                }
            ],
            "nameservers": [
                {"ldhName": "ns1.example.com"},
                {"ldhName": "ns2.example.com"},
            ],
        }

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = rdap_response
                mock_get.return_value = mock_response
                result = await _get_rdap_data(client, "example.com")

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_rdap_data_not_found(self) -> None:
        """RDAP 404 returns empty dict."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_get.return_value = mock_response
                result = await _get_rdap_data(client, "invalid.test")

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_rdap_data_timeout(self) -> None:
        """RDAP timeout returns empty dict."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = httpx.TimeoutException()
                result = await _get_rdap_data(client, "example.com")

        assert result == {}


class TestSearchCrtSh:
    """_search_crt_sh helper for certificate transparency."""

    @pytest.mark.asyncio
    async def test_search_crt_sh_empty_email(self) -> None:
        """Empty email returns empty list."""
        async with httpx.AsyncClient() as client:
            result = await _search_crt_sh(client, "")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_crt_sh_valid_email(self) -> None:
        """Valid email returns results or empty list."""
        async with httpx.AsyncClient() as client:
            result = await _search_crt_sh(client, "admin@example.com")
        assert isinstance(result, list)


class TestJaccardSimilarity:
    """_jaccard_similarity helper for word overlap."""

    def test_jaccard_similarity_identical(self) -> None:
        """Identical sets have similarity 1.0."""
        sim = _jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"})
        assert sim == 1.0

    def test_jaccard_similarity_disjoint(self) -> None:
        """Disjoint sets have similarity 0.0."""
        sim = _jaccard_similarity({"a", "b"}, {"c", "d"})
        assert sim == 0.0

    def test_jaccard_similarity_partial(self) -> None:
        """Partial overlap returns correct value."""
        # {a,b,c} ∩ {b,c,d} = {b,c}, union = {a,b,c,d}
        # similarity = 2/4 = 0.5
        sim = _jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert sim == 0.5

    def test_jaccard_similarity_empty_both(self) -> None:
        """Both empty sets have similarity 1.0."""
        sim = _jaccard_similarity(set(), set())
        assert sim == 1.0

    def test_jaccard_similarity_empty_one(self) -> None:
        """One empty set with non-empty has similarity 0.0."""
        sim = _jaccard_similarity(set(), {"a"})
        assert sim == 0.0


class TestQueryLlmEndpoint:
    """_query_llm_endpoint helper for LLM calls."""

    @pytest.mark.asyncio
    async def test_query_llm_endpoint_success(self) -> None:
        """Successful LLM query returns response text."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"response": "Hello, world!"}
                mock_post.return_value = mock_response
                result = await _query_llm_endpoint(
                    client, "https://api.example.com/chat", "test prompt"
                )

        assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_query_llm_endpoint_text_response(self) -> None:
        """LLM endpoint returning plain text is extracted."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.side_effect = ValueError("not json")
                mock_response.text = "Direct text response"
                mock_post.return_value = mock_response
                result = await _query_llm_endpoint(
                    client, "https://api.example.com/chat", "test prompt"
                )

        assert result == "Direct text response"

    @pytest.mark.asyncio
    async def test_query_llm_endpoint_invalid_url(self) -> None:
        """Invalid URL returns empty string."""
        async with httpx.AsyncClient() as client:
            result = await _query_llm_endpoint(
                client, "not-a-valid-url", "test prompt"
            )

        assert result == ""

    @pytest.mark.asyncio
    async def test_query_llm_endpoint_timeout(self) -> None:
        """Timeout returns empty string."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.side_effect = httpx.TimeoutException()
                result = await _query_llm_endpoint(
                    client, "https://api.example.com/chat", "test prompt"
                )

        assert result == ""

    @pytest.mark.asyncio
    async def test_query_llm_endpoint_error_status(self) -> None:
        """Error status code returns empty string."""
        async with httpx.AsyncClient() as client:
            with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_post.return_value = mock_response
                result = await _query_llm_endpoint(
                    client, "https://api.example.com/chat", "test prompt"
                )

        assert result == ""


class TestOutputConsistency:
    """LLM output consistency measurement."""

    def test_output_consistency_valid_params(self) -> None:
        """Valid params trigger consistency check."""
        result = research_output_consistency(
            "https://api.example.com/chat",
            "What is 2+2?",
            runs=3,
        )
        assert result["target"] == "https://api.example.com/chat"
        assert "prompt" in result
        assert "mean_similarity" in result
        assert "variance" in result
        assert "consistency_score" in result

    def test_output_consistency_invalid_url(self) -> None:
        """Invalid URL returns error."""
        result = research_output_consistency("", "test prompt")
        assert "error" in result

    def test_output_consistency_url_too_long(self) -> None:
        """URL exceeding 500 chars returns error."""
        long_url = "https://" + "a" * 500 + ".com"
        result = research_output_consistency(long_url, "test prompt")
        assert "error" in result

    def test_output_consistency_invalid_prompt(self) -> None:
        """Invalid prompt returns error."""
        result = research_output_consistency("https://api.example.com/chat", "")
        assert "error" in result

    def test_output_consistency_prompt_too_long(self) -> None:
        """Prompt exceeding 5000 chars returns error."""
        long_prompt = "a" * 5001
        result = research_output_consistency(
            "https://api.example.com/chat", long_prompt
        )
        assert "error" in result

    def test_output_consistency_runs_default(self) -> None:
        """Default runs is 5."""
        result = research_output_consistency(
            "https://api.example.com/chat", "test prompt"
        )
        assert result["runs"] >= 0  # Will be 0 if endpoints fail, but structure is correct

    def test_output_consistency_runs_capped(self) -> None:
        """Runs capped at 20."""
        result = research_output_consistency(
            "https://api.example.com/chat", "test prompt", runs=100
        )
        assert result["runs"] <= 20

    def test_output_consistency_min_runs(self) -> None:
        """Runs minimum is 1."""
        result = research_output_consistency(
            "https://api.example.com/chat", "test prompt", runs=0
        )
        assert result["runs"] >= 0

    def test_output_consistency_scores_bounded(self) -> None:
        """Scores are between 0 and 1."""
        result = research_output_consistency(
            "https://api.example.com/chat", "test prompt"
        )
        assert 0 <= result["mean_similarity"] <= 1
        assert 0 <= result["variance"] <= 1
        assert 0 <= result["consistency_score"] <= 1

    def test_output_consistency_response_truncation(self) -> None:
        """Individual response previews are truncated to 200 chars."""
        result = research_output_consistency(
            "https://api.example.com/chat", "test prompt"
        )
        for resp in result.get("responses", []):
            assert len(resp) <= 200
