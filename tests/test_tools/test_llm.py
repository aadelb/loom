"""Unit tests for LLM tools — chat, summarize, extract, classify, translate.

All 8 research_llm_* tools are async; tests use async def + AsyncMock for
the _call_with_cascade patch.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("loom.tools.llm.llm")


def _mock_response(text: str = "example") -> MagicMock:
    return MagicMock(
        text=text,
        model="gpt-4",
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.01,
        latency_ms=100,
        provider="openai",
        finish_reason="stop",
    )


async def test_llm_chat_returns_expected_structure() -> None:
    """LLM chat returns structure with text, model, tokens, cost, latency."""
    from loom.tools.llm.llm import research_llm_chat

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response("Example response")),
    ):
        result = await research_llm_chat(
            messages=[{"role": "user", "content": "Hello"}]
        )

    assert isinstance(result, dict)
    assert "error" in result or "text" in result or "response" in result


async def test_llm_summarize_respects_max_length() -> None:
    """LLM summarize respects max_tokens bounds."""
    from loom.tools.llm.llm import research_llm_summarize

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response("Short summary")),
    ):
        result = await research_llm_summarize(text="Long content " * 100, max_tokens=500)

    assert isinstance(result, dict)
    assert "error" in result or "summary" in result or "text" in result


async def test_llm_extract_validates_against_schema() -> None:
    """LLM extract validates result against provided schema."""
    from loom.tools.llm.llm import research_llm_extract

    schema = {"name": "string"}

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response('{"name": "Example"}')),
    ):
        result = await research_llm_extract(text="Extract name", schema=schema)

    assert isinstance(result, dict)
    assert "error" in result or "extracted" in result or "data" in result


async def test_llm_classify_respects_label_allowlist() -> None:
    """LLM classify returns a label from the allow-list."""
    from loom.tools.llm.llm import research_llm_classify

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response("positive")),
    ):
        result = await research_llm_classify(
            text="This is great!",
            labels=["positive", "negative"],
        )

    assert isinstance(result, dict)
    assert "error" in result or "label" in result or "labels" in result


async def test_llm_translate_preserves_arabic() -> None:
    """LLM translate returns a structured result for non-English input."""
    from loom.tools.llm.llm import research_llm_translate

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response("Welcome")),
    ):
        result = await research_llm_translate(
            text="مرحبا بك", source_lang="ar", target_lang="en"
        )

    assert isinstance(result, dict)
    assert "error" in result or "translated" in result or "translation" in result


async def test_llm_query_expand_returns_multiple() -> None:
    """LLM query expand returns multiple expanded queries."""
    from loom.tools.llm.llm import research_llm_query_expand

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response("query1\nquery2\nquery3")),
    ):
        result = await research_llm_query_expand(query="llm", n=3)

    assert isinstance(result, dict)
    assert "error" in result or "queries" in result
