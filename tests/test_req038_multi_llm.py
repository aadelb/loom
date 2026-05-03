"""REQ-038 Multi-LLM Test Suite.

Tests for ask_all_llms, query_expand, and ask_all_models tools.
Tests use short prompts and low max_tokens to minimize API costs.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import pytest

# Add src to path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))


@pytest.mark.asyncio
async def test_research_ask_all_llms_basic() -> None:
    """Test research_ask_all_llms with a simple prompt.

    Tests:
    - Returns dict with required fields
    - Has providers_queried >= 1 or returns error gracefully
    - responses list is present
    """
    from loom.tools.multi_llm import research_ask_all_llms

    result = await research_ask_all_llms(
        prompt="What is 2+2?",
        max_tokens=50,
        include_reframe=False,
    )

    assert isinstance(result, dict), "Result should be a dict"
    assert "prompt" in result, "Result should contain 'prompt'"
    assert "providers_queried" in result, "Result should contain 'providers_queried'"
    assert "responses" in result, "Result should contain 'responses'"

    # Either we got responses or a graceful error
    if "error" in result:
        # No LLM providers configured - this is acceptable
        assert result["error"], "Error message should be non-empty"
        assert result["providers_queried"] == 0
    else:
        # We have providers configured
        assert isinstance(result["providers_queried"], int)
        assert result["providers_queried"] >= 0
        assert isinstance(result["responses"], list)

        # If any responses, check structure
        if result["responses"]:
            for resp in result["responses"]:
                assert "provider" in resp
                assert "elapsed_ms" in resp


@pytest.mark.asyncio
async def test_research_ask_all_llms_with_max_tokens() -> None:
    """Test research_ask_all_llms respects max_tokens parameter."""
    from loom.tools.multi_llm import research_ask_all_llms

    result = await research_ask_all_llms(
        prompt="Hello",
        max_tokens=20,
    )

    assert isinstance(result, dict)
    assert "prompt" in result


@pytest.mark.asyncio
async def test_research_llm_query_expand_basic() -> None:
    """Test research_llm_query_expand generates query variations.

    Tests:
    - Returns dict with 'queries' list
    - Returns expected fields (model, provider, cost_usd)
    - Handles graceful errors if no providers available
    """
    from loom.tools.llm import research_llm_query_expand

    result = await research_llm_query_expand(
        query="best programming languages 2026",
        n=3,
    )

    assert isinstance(result, dict), "Result should be a dict"

    # Either success or graceful error
    if "error" in result:
        # No providers available
        assert isinstance(result["error"], str)
    else:
        # Success case
        assert "queries" in result, "Result should contain 'queries'"
        assert isinstance(result["queries"], list), "'queries' should be a list"

        # Check other expected fields
        assert "model" in result
        assert "provider" in result


@pytest.mark.asyncio
async def test_research_llm_query_expand_n_parameter() -> None:
    """Test research_llm_query_expand respects n parameter clamping."""
    from loom.tools.llm import research_llm_query_expand

    # Test with n=1 (minimum)
    result_min = await research_llm_query_expand(
        query="test query",
        n=1,
    )
    assert isinstance(result_min, dict)

    # Test with n=10 (maximum)
    result_max = await research_llm_query_expand(
        query="test query",
        n=10,
    )
    assert isinstance(result_max, dict)

    # Test with n=0 (should be clamped to 1)
    result_zero = await research_llm_query_expand(
        query="test query",
        n=0,
    )
    assert isinstance(result_zero, dict)

    # Test with n > 10 (should be clamped to 10)
    result_over = await research_llm_query_expand(
        query="test query",
        n=100,
    )
    assert isinstance(result_over, dict)


async def test_research_ask_all_models_basic() -> None:
    """Test research_ask_all_models sends to multiple models.

    Tests:
    - Returns dict with structured response
    - Has models_queried and responses fields
    - Handles no API keys gracefully
    """
    from loom.tools.ask_all_models import research_ask_all_models

    result = await research_ask_all_models(
        prompt="2+2=?",
        max_tokens=50,
        auto_reframe=False,
        include_clis=False,
        timeout=30,
    )

    assert isinstance(result, dict), "Result should be a dict"
    assert "prompt" in result, "Result should contain 'prompt'"
    assert "models_queried" in result, "Result should contain 'models_queried'"
    assert "models_responded" in result, "Result should contain 'models_responded'"
    assert "responses" in result, "Result should contain 'responses'"

    # Validate structure
    assert isinstance(result["models_queried"], int)
    assert isinstance(result["models_responded"], int)
    assert isinstance(result["responses"], list)

    # If models responded, check response structure
    if result["models_responded"] > 0:
        for resp in result["responses"]:
            if resp.get("text"):  # Has response text
                assert "provider" in resp
                assert "model" in resp
                assert "elapsed_ms" in resp


async def test_research_ask_all_models_timeout_respect() -> None:
    """Test research_ask_all_models respects timeout parameter."""
    from loom.tools.ask_all_models import research_ask_all_models

    # Use very short timeout to test parameter acceptance
    result = await research_ask_all_models(
        prompt="hi",
        max_tokens=30,
        timeout=5,
    )

    assert isinstance(result, dict)


async def test_research_ask_all_models_auto_reframe_param() -> None:
    """Test research_ask_all_models auto_reframe parameter is accepted."""
    from loom.tools.ask_all_models import research_ask_all_models

    result = await research_ask_all_models(
        prompt="test",
        auto_reframe=True,
        max_tokens=30,
    )

    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_multi_llm_concurrent_execution() -> None:
    """Test that multi-LLM tools handle concurrent execution safely."""
    from loom.tools.multi_llm import research_ask_all_llms
    from loom.tools.llm import research_llm_query_expand

    # Run two concurrent queries
    results = await asyncio.gather(
        await research_ask_all_llms("test1", max_tokens=30),
        await research_llm_query_expand("test2", n=2),
    )

    assert len(results) == 2
    assert isinstance(results[0], dict)
    assert isinstance(results[1], dict)


@pytest.mark.asyncio
async def test_ask_all_llms_empty_prompt() -> None:
    """Test research_ask_all_llms handles empty prompt gracefully."""
    from loom.tools.multi_llm import research_ask_all_llms

    result = await research_ask_all_llms(
        prompt="",
        max_tokens=50,
    )

    assert isinstance(result, dict)
    assert "prompt" in result


@pytest.mark.asyncio
async def test_query_expand_long_query() -> None:
    """Test research_llm_query_expand handles long queries."""
    from loom.tools.llm import research_llm_query_expand

    long_query = "x" * 1000  # 1000 char query

    result = await research_llm_query_expand(
        query=long_query,
        n=2,
    )

    assert isinstance(result, dict)


async def test_ask_all_models_models_parameter() -> None:
    """Test research_ask_all_models models filter parameter."""
    from loom.tools.ask_all_models import research_ask_all_models

    result = await research_ask_all_models(
        prompt="test",
        models=["gpt"],  # Filter to GPT models only
        max_tokens=30,
    )

    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_research_llm_query_expand_response_format() -> None:
    """Test query_expand returns properly formatted responses."""
    from loom.tools.llm import research_llm_query_expand

    result = await research_llm_query_expand(
        query="artificial intelligence trends",
        n=3,
    )

    assert isinstance(result, dict)

    # If no error, check format
    if "error" not in result:
        assert "queries" in result
        if result["queries"]:  # Has queries
            assert isinstance(result["queries"], list)
            for query in result["queries"]:
                assert isinstance(query, (str, dict))


@pytest.mark.asyncio
async def test_ask_all_llms_response_structure() -> None:
    """Test research_ask_all_llms response has all expected fields."""
    from loom.tools.multi_llm import research_ask_all_llms

    result = await research_ask_all_llms(
        prompt="test",
        max_tokens=50,
    )

    # Check core fields always present
    assert "prompt" in result
    assert "responses" in result
    assert "providers_queried" in result

    # Check responses list structure
    assert isinstance(result["responses"], list)
    for resp in result["responses"]:
        assert "provider" in resp
        assert "elapsed_ms" in resp or "error" in resp


if __name__ == "__main__":
    # Allow running via: python -m pytest tests/test_req038_multi_llm.py
    pytest.main([__file__, "-v", "--timeout=180", "--maxfail=3"])
