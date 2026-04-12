"""Extended tests for LLM tools — extract, classify, translate, expand, answer.

Uses AsyncMock on _call_with_cascade to test tool-specific logic and response parsing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("loom.tools.llm")


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


async def test_llm_extract_returns_parsed_json() -> None:
    """research_llm_extract returns parsed JSON dict from cascade response."""
    from loom.tools.llm import research_llm_extract

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response('{"name": "Alice", "age": 30}')),
    ):
        result = await research_llm_extract(
            text="Alice is 30 years old",
            schema={"name": "string", "age": "integer"},
        )

    assert isinstance(result, dict)
    assert "data" in result
    assert result["data"]["name"] == "Alice"
    assert result["data"]["age"] == 30


async def test_llm_classify_returns_label() -> None:
    """research_llm_classify enforces allow-list and returns single label."""
    from loom.tools.llm import research_llm_classify

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response("positive")),
    ):
        result = await research_llm_classify(
            text="This is wonderful!",
            labels=["positive", "negative", "neutral"],
        )

    assert isinstance(result, dict)
    assert "label" in result
    assert result["label"] in ["positive", "negative", "neutral"]


async def test_llm_translate_returns_translated_text() -> None:
    """research_llm_translate returns translated text in target language."""
    from loom.tools.llm import research_llm_translate

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response("Good morning")),
    ):
        result = await research_llm_translate(
            text="مرحبا صباح الخير",
            source_lang="ar",
            target_lang="en",
        )

    assert isinstance(result, dict)
    assert "translated" in result
    assert result["translated"] == "Good morning"


async def test_llm_query_expand_returns_list() -> None:
    """research_llm_query_expand returns list of expanded query strings."""
    from loom.tools.llm import research_llm_query_expand

    mock_queries = '["query1", "query2", "query3", "query4", "query5"]'

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response(mock_queries)),
    ):
        result = await research_llm_query_expand(query="llm safety", n=5)

    assert isinstance(result, dict)
    assert "queries" in result
    assert isinstance(result["queries"], list)
    assert len(result["queries"]) == 5


async def test_llm_answer_returns_cited_text() -> None:
    """research_llm_answer returns answer with citations list."""
    from loom.tools.llm import research_llm_answer

    sources = [
        {"title": "Paper A", "text": "Content A", "url": "http://a.com"},
        {"title": "Paper B", "text": "Content B", "url": "http://b.com"},
    ]

    with patch(
        "loom.tools.llm._call_with_cascade",
        new=AsyncMock(return_value=_mock_response("Answer from [1] and [2]")),
    ):
        result = await research_llm_answer(
            question="What is this?",
            sources=sources,
        )

    assert isinstance(result, dict)
    assert "answer" in result
    assert "citations" in result
    assert result["answer"] == "Answer from [1] and [2]"
    assert len(result["citations"]) == 2
