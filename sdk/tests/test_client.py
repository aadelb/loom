"""Unit tests for Loom SDK client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom_sdk import LoomClient
from loom_sdk.models import HealthStatus, SearchResponse, FetchResult


@pytest.mark.unit
class TestLoomClientInit:
    """Test LoomClient initialization."""

    def test_init_defaults(self) -> None:
        """Test initialization with default parameters."""
        client = LoomClient()
        assert client.base_url == "http://localhost:8787"
        assert client.api_key is None
        assert client.timeout == 60.0
        assert client.max_retries == 3

    def test_init_custom_values(self) -> None:
        """Test initialization with custom parameters."""
        client = LoomClient(
            base_url="https://api.example.com",
            api_key="sk_test_123",
            timeout=120.0,
            max_retries=5,
        )
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "sk_test_123"
        assert client.timeout == 120.0
        assert client.max_retries == 5

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slashes are stripped from base_url."""
        client = LoomClient(base_url="http://localhost:8787/")
        assert client.base_url == "http://localhost:8787"

    def test_init_invalid_base_url(self) -> None:
        """Test initialization with invalid base_url."""
        with pytest.raises(ValueError, match="base_url must be a non-empty string"):
            LoomClient(base_url="")

        with pytest.raises(ValueError, match="base_url must be a non-empty string"):
            LoomClient(base_url=None)  # type: ignore

    def test_init_invalid_timeout(self) -> None:
        """Test initialization with invalid timeout."""
        with pytest.raises(ValueError, match="timeout must be greater than 0"):
            LoomClient(timeout=0)

        with pytest.raises(ValueError, match="timeout must be greater than 0"):
            LoomClient(timeout=-1)

    def test_init_invalid_max_retries(self) -> None:
        """Test initialization with invalid max_retries."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            LoomClient(max_retries=-1)


@pytest.mark.unit
class TestLoomClientValidation:
    """Test input validation for client methods."""

    def test_search_empty_query(self) -> None:
        """Test search with empty query."""
        client = LoomClient()

        with pytest.raises(ValueError, match="query must be a non-empty string"):
            pytest.asyncio.run(client.search(""))

    def test_search_invalid_n(self) -> None:
        """Test search with invalid result count."""
        client = LoomClient()

        with pytest.raises(ValueError, match="n must be between 1 and 100"):
            pytest.asyncio.run(client.search("test", n=0))

        with pytest.raises(ValueError, match="n must be between 1 and 100"):
            pytest.asyncio.run(client.search("test", n=101))

    def test_fetch_empty_url(self) -> None:
        """Test fetch with empty URL."""
        client = LoomClient()

        with pytest.raises(ValueError, match="url must be a non-empty string"):
            pytest.asyncio.run(client.fetch(""))

    def test_deep_research_empty_query(self) -> None:
        """Test deep_research with empty query."""
        client = LoomClient()

        with pytest.raises(ValueError, match="query must be a non-empty string"):
            pytest.asyncio.run(client.deep_research(""))

    def test_deep_research_invalid_max_results(self) -> None:
        """Test deep_research with invalid max_results."""
        client = LoomClient()

        with pytest.raises(ValueError, match="max_results must be between 1 and 50"):
            pytest.asyncio.run(client.deep_research("test", max_results=0))

        with pytest.raises(ValueError, match="max_results must be between 1 and 50"):
            pytest.asyncio.run(client.deep_research("test", max_results=51))

    def test_llm_summarize_empty_text(self) -> None:
        """Test llm_summarize with empty text."""
        client = LoomClient()

        with pytest.raises(ValueError, match="text must be a non-empty string"):
            pytest.asyncio.run(client.llm_summarize(""))

    def test_llm_summarize_invalid_max_words(self) -> None:
        """Test llm_summarize with invalid max_words."""
        client = LoomClient()

        with pytest.raises(ValueError, match="max_words must be between 50 and 2000"):
            pytest.asyncio.run(client.llm_summarize("test", max_words=10))

        with pytest.raises(ValueError, match="max_words must be between 50 and 2000"):
            pytest.asyncio.run(client.llm_summarize("test", max_words=2001))

    def test_call_tool_empty_name(self) -> None:
        """Test call_tool with empty tool name."""
        client = LoomClient()

        with pytest.raises(ValueError, match="tool_name must be a non-empty string"):
            pytest.asyncio.run(client.call_tool(""))


@pytest.mark.unit
class TestLoomClientContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self) -> None:
        """Test context manager entry and exit."""
        async with LoomClient() as client:
            assert isinstance(client, LoomClient)
        # Client should be closed after exiting context

    @pytest.mark.asyncio
    async def test_manual_close(self) -> None:
        """Test manual client close."""
        client = LoomClient()
        await client.close()
        assert client._client is None


@pytest.mark.unit
class TestResponseModels:
    """Test response model creation."""

    def test_search_response_creation(self) -> None:
        """Test SearchResponse dataclass."""
        from loom_sdk.models import SearchResult

        result = SearchResult(
            url="https://example.com",
            title="Example",
            snippet="Example snippet",
            provider="exa",
            relevance_score=0.95,
        )
        assert result.url == "https://example.com"
        assert result.title == "Example"
        assert result.provider == "exa"
        assert result.relevance_score == 0.95

    def test_fetch_result_creation(self) -> None:
        """Test FetchResult dataclass."""
        result = FetchResult(
            url="https://example.com",
            content_type="text/html",
            status_code=200,
            body_length=1024,
            title="Example",
        )
        assert result.url == "https://example.com"
        assert result.status_code == 200
        assert result.body_length == 1024

    def test_health_status_creation(self) -> None:
        """Test HealthStatus dataclass."""
        health = HealthStatus(
            status="healthy",
            version="0.1.0",
            uptime_seconds=3600.0,
            tools_available=100,
        )
        assert health.status == "healthy"
        assert health.version == "0.1.0"
        assert health.tools_available == 100

    def test_response_models_immutable(self) -> None:
        """Test that response models are frozen (immutable)."""
        result = FetchResult(
            url="https://example.com",
            content_type="text/html",
            status_code=200,
            body_length=1024,
        )

        with pytest.raises(AttributeError):
            result.status_code = 404  # type: ignore


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
