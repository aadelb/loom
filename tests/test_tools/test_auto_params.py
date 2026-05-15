"""Tests for auto_params tool."""

from __future__ import annotations

import pytest

from loom.tools.llm.auto_params import (
    _detect_language,
    _detect_model,
    _extract_domain,
    _extract_numbers,
    _extract_urls,
    _infer_param_value,
    research_auto_params,
    research_inspect_tool,
)


class TestExtractUrls:
    """Tests for URL extraction."""

    def test_extract_single_url(self) -> None:
        """Extract single HTTP URL."""
        text = "Please fetch https://example.com/page"
        urls = _extract_urls(text)
        assert len(urls) == 1
        assert urls[0] == "https://example.com/page"

    def test_extract_multiple_urls(self) -> None:
        """Extract multiple URLs."""
        text = "Try https://example.com and http://test.org"
        urls = _extract_urls(text)
        assert len(urls) == 2
        assert "https://example.com" in urls
        assert "http://test.org" in urls

    def test_extract_urls_with_trailing_punct(self) -> None:
        """Strip trailing punctuation from URLs."""
        text = "Check https://example.com."
        urls = _extract_urls(text)
        assert urls[0] == "https://example.com"

    def test_no_urls(self) -> None:
        """Return empty list when no URLs found."""
        text = "No URLs here"
        urls = _extract_urls(text)
        assert urls == []


class TestExtractNumbers:
    """Tests for number extraction."""

    def test_extract_single_number(self) -> None:
        """Extract single number."""
        text = "Get 10 results"
        numbers = _extract_numbers(text)
        assert numbers == [10]

    def test_extract_multiple_numbers(self) -> None:
        """Extract multiple numbers."""
        text = "Test 5 models with 10 iterations"
        numbers = _extract_numbers(text)
        assert 5 in numbers
        assert 10 in numbers

    def test_no_numbers(self) -> None:
        """Return empty list when no numbers found."""
        text = "No numbers here"
        numbers = _extract_numbers(text)
        assert numbers == []


class TestDetectLanguage:
    """Tests for language detection."""

    def test_detect_english(self) -> None:
        """Detect English language."""
        text = "Search in english language"
        lang = _detect_language(text)
        assert lang == "en"

    def test_detect_arabic(self) -> None:
        """Detect Arabic language."""
        text = "Search in arabic language"
        lang = _detect_language(text)
        assert lang == "ar"

    def test_detect_french(self) -> None:
        """Detect French language."""
        text = "Search in french language"
        lang = _detect_language(text)
        assert lang == "fr"

    def test_no_language_detected(self) -> None:
        """Return None when language not detected."""
        text = "Random text"
        lang = _detect_language(text)
        assert lang is None


class TestDetectModel:
    """Tests for model name detection."""

    def test_detect_claude(self) -> None:
        """Detect Claude model."""
        text = "Use claude for analysis"
        model = _detect_model(text)
        assert model == "claude"

    def test_detect_gpt(self) -> None:
        """Detect GPT model."""
        text = "Query with gpt-4"
        model = _detect_model(text)
        assert model == "gpt"

    def test_detect_deepseek(self) -> None:
        """Detect DeepSeek model."""
        text = "Try deepseek reasoning"
        model = _detect_model(text)
        assert model == "deepseek"

    def test_no_model_detected(self) -> None:
        """Return None when model not detected."""
        text = "No model specified"
        model = _detect_model(text)
        assert model is None


class TestExtractDomain:
    """Tests for domain extraction."""

    def test_extract_simple_domain(self) -> None:
        """Extract simple domain."""
        text = "Research github.com"
        domain = _extract_domain(text)
        assert domain == "github.com"

    def test_extract_subdomain(self) -> None:
        """Extract subdomain."""
        text = "Visit api.example.org"
        domain = _extract_domain(text)
        assert domain == "api.example.org"

    def test_extract_from_url(self) -> None:
        """Extract domain from full URL."""
        text = "Check https://example.com/page"
        domain = _extract_domain(text)
        assert domain == "example.com"

    def test_no_domain(self) -> None:
        """Return None when no domain found."""
        text = "No domains here"
        domain = _extract_domain(text)
        assert domain is None


class TestInferParamValue:
    """Tests for parameter value inference."""

    def test_infer_url_param(self) -> None:
        """Infer URL parameter from query."""
        value = _infer_param_value("url", str, "Fetch https://example.com")
        assert value == "https://example.com"

    def test_infer_query_param(self) -> None:
        """Infer query parameter uses full query."""
        value = _infer_param_value("query", str, "Search for python")
        assert value == "Search for python"

    def test_infer_domain_param(self) -> None:
        """Infer domain parameter."""
        value = _infer_param_value("domain", str, "Analyze github.com")
        assert value == "github.com"

    def test_infer_model_param(self) -> None:
        """Infer model parameter."""
        value = _infer_param_value("model", str, "Use gpt for analysis")
        assert value == "gpt"

    def test_infer_language_param(self) -> None:
        """Infer language parameter."""
        value = _infer_param_value("language", str, "Search in arabic")
        assert value == "ar"

    def test_infer_limit_param(self) -> None:
        """Infer limit parameter."""
        value = _infer_param_value("limit", int, "Get 5 results")
        assert value == 5

    def test_infer_limit_default(self) -> None:
        """Default limit to 10 when not found."""
        value = _infer_param_value("limit", int, "Get results")
        assert value == 10

    def test_infer_boolean_param(self) -> None:
        """Infer boolean parameter defaults to True."""
        value = _infer_param_value("enabled", bool, "Enable feature")
        assert value is True

    def test_infer_list_param(self) -> None:
        """Infer list parameter wraps values."""
        value = _infer_param_value("urls", "list[str]", "Fetch https://example.com")
        assert isinstance(value, list)
        assert len(value) > 0


@pytest.mark.asyncio
async def test_research_auto_params_fetch() -> None:
    """Test auto params for research_fetch tool."""
    result = await research_auto_params(
        "research_fetch",
        "Fetch https://example.com with stealthy mode"
    )
    assert result["tool_name"] == "research_fetch"
    assert "generated_params" in result
    # Should have inferred at least URL
    assert result["params_inferred"] >= 1


@pytest.mark.asyncio
async def test_research_auto_params_search() -> None:
    """Test auto params for research_search tool."""
    result = await research_auto_params(
        "research_search",
        "Search for python tutorials with 5 results"
    )
    assert result["tool_name"] == "research_search"
    assert result["params_inferred"] >= 1


@pytest.mark.asyncio
async def test_research_auto_params_missing_tool() -> None:
    """Test with non-existent tool."""
    result = await research_auto_params(
        "research_nonexistent",
        "Some query"
    )
    assert "error" in result or result["params_inferred"] == 0


@pytest.mark.asyncio
async def test_research_inspect_tool_fetch() -> None:
    """Test inspection of research_fetch tool."""
    result = await research_inspect_tool("research_fetch")
    assert result["tool_name"] == "research_fetch"
    assert "module" in result
    assert "parameters" in result
    assert len(result["parameters"]) > 0

    # Check parameter structure
    for param in result["parameters"]:
        assert "name" in param
        assert "type" in param
        assert "default" in param
        assert "required" in param


@pytest.mark.asyncio
async def test_research_inspect_tool_search() -> None:
    """Test inspection of research_search tool."""
    result = await research_inspect_tool("research_search")
    assert result["tool_name"] == "research_search"
    assert len(result["parameters"]) > 0
    assert result.get("docstring") is not None


@pytest.mark.asyncio
async def test_research_inspect_tool_missing() -> None:
    """Test inspection of non-existent tool."""
    result = await research_inspect_tool("research_nonexistent")
    assert "error" in result or len(result["parameters"]) == 0


class TestConfidenceScoring:
    """Tests for confidence calculation."""

    @pytest.mark.asyncio
    async def test_high_confidence_with_many_inferred(self) -> None:
        """High confidence when many params inferred."""
        result = await research_auto_params(
            "research_fetch",
            "Fetch https://example.com in stealthy mode with 20000 chars"
        )
        # Should have moderate confidence
        assert result["confidence"] > 0

    @pytest.mark.asyncio
    async def test_confidence_calculation(self) -> None:
        """Confidence increases with more inferred params."""
        result1 = await research_auto_params(
            "research_search",
            "Search"
        )
        result2 = await research_auto_params(
            "research_search",
            "Search for python with gpt using 10 results in english"
        )
        # More detailed query should have higher or equal confidence
        assert result2["confidence"] >= result1["confidence"]


class TestParamValidation:
    """Tests for parameter validation."""

    @pytest.mark.asyncio
    async def test_url_validation(self) -> None:
        """Validate extracted URLs are valid."""
        result = await research_auto_params(
            "research_fetch",
            "Fetch https://example.com/path?query=value&test=1"
        )
        assert "generated_params" in result
        if "url" in result["generated_params"]:
            url = result["generated_params"]["url"]
            assert url.startswith("http")


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_query(self) -> None:
        """Handle empty query gracefully."""
        result = await research_auto_params("research_fetch", "")
        assert result["tool_name"] == "research_fetch"
        assert isinstance(result["confidence"], int)

    @pytest.mark.asyncio
    async def test_query_with_special_chars(self) -> None:
        """Handle special characters in query."""
        result = await research_auto_params(
            "research_search",
            "Search for 'hello & goodbye' at example.com"
        )
        assert result["tool_name"] == "research_search"
        assert isinstance(result["confidence"], int)

    @pytest.mark.asyncio
    async def test_very_long_query(self) -> None:
        """Handle very long query."""
        long_query = "Search " + "for something " * 100
        result = await research_auto_params("research_search", long_query)
        assert result["tool_name"] == "research_search"
        assert isinstance(result["confidence"], int)
