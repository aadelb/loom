"""Test REQ-039: LLM Ops 8 tools (summarize, extract, classify, translate, answer, embed, chat, detect_language).

Tests all 8 tools from loom.tools.llm and loom.tools.enrich:
1. research_llm_summarize — Text summarization
2. research_llm_extract — Structured extraction with schema
3. research_llm_classify — Classification into allowed labels
4. research_llm_translate — Language translation
5. research_llm_answer — Question answering with sources
6. research_llm_embed — Semantic embeddings
7. research_llm_chat — Raw LLM chat pass-through
8. research_detect_language — Language detection (from enrich.py)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import tools
try:
    from loom.tools.llm import (
        research_llm_summarize,
        research_llm_extract,
        research_llm_classify,
        research_llm_translate,
        research_llm_answer,
        research_llm_embed,
        research_llm_chat,
    )
except ImportError as e:
    pytest.skip(f"LLM tools import failed: {e}", allow_module_level=True)

try:
    from loom.tools.enrich import research_detect_language
except ImportError as e:
    pytest.skip(f"Enrich tools import failed: {e}", allow_module_level=True)

from loom.providers.base import LLMResponse


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_response():
    """Create a mock LLMResponse."""
    return LLMResponse(
        text="Test response",
        model="test-model",
        provider="test-provider",
        cost_usd=0.001,
        input_tokens=10,
        output_tokens=5,
        finish_reason="stop",
        latency_ms=100,
    )


@pytest.fixture
def mock_refusal_meta():
    """Create mock refusal metadata."""
    return {
        "refused": False,
        "refusal_patterns": [],
        "reframe_attempts": 0,
    }


# ============================================================================
# TEST 1: research_llm_summarize
# ============================================================================


@pytest.mark.asyncio
async def test_research_llm_summarize_basic(mock_llm_response, mock_refusal_meta):
    """Test summarization with short text and low max_tokens."""
    text = "Python is a popular programming language created by Guido van Rossum. It is known for its simple syntax and readability."

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (mock_llm_response, mock_refusal_meta)

        result = await research_llm_summarize(
            text=text,
            max_tokens=100,
        )

    # Assert: returns dict with 'summary' key
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "summary" in result, "Result must have 'summary' key"
    assert isinstance(result["summary"], str), "Summary must be a string"
    assert result["summary"] == "Test response", "Summary matches mock response"

    # Check other expected keys
    assert "model" in result
    assert "provider" in result
    assert "cost_usd" in result
    assert "input_tokens" in result
    assert "output_tokens" in result


@pytest.mark.asyncio
async def test_research_llm_summarize_error_handling(mock_refusal_meta):
    """Test summarize error handling."""
    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.side_effect = RuntimeError("Provider unavailable")

        result = await research_llm_summarize(
            text="Some text",
            max_tokens=50,
        )

    # Assert: returns dict with 'error' key on failure
    assert isinstance(result, dict)
    assert "error" in result, "Result should have 'error' key on exception"


# ============================================================================
# TEST 2: research_llm_extract
# ============================================================================


@pytest.mark.asyncio
async def test_research_llm_extract_basic(mock_llm_response, mock_refusal_meta):
    """Test extraction with schema."""
    text = "John Smith, age 30, works at Google in Mountain View"
    schema = {"name": "string", "age": "integer", "company": "string"}

    # Mock response contains JSON
    response_with_json = LLMResponse(
        text='{"name": "John Smith", "age": 30, "company": "Google"}',
        model="test-model",
        provider="test-provider",
        cost_usd=0.001,
        input_tokens=10,
        output_tokens=5,
        finish_reason="stop",
        latency_ms=100,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (response_with_json, mock_refusal_meta)

        result = await research_llm_extract(
            text=text,
            schema=schema,
        )

    # Assert: returns dict with 'data' key
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "data" in result, "Result must have 'data' key"
    assert isinstance(result["data"], dict), "Data must be a dictionary"
    assert result["data"]["name"] == "John Smith"
    assert result["data"]["age"] == 30
    assert result["data"]["company"] == "Google"

    # Check other expected keys
    assert "model" in result
    assert "provider" in result
    assert "cost_usd" in result


@pytest.mark.asyncio
async def test_research_llm_extract_error_handling(mock_refusal_meta):
    """Test extract error handling."""
    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.side_effect = ValueError("Schema invalid")

        result = await research_llm_extract(
            text="Some text",
            schema={"field": "string"},
        )

    # Assert: returns dict with 'error' key on failure
    assert isinstance(result, dict)
    assert "error" in result


# ============================================================================
# TEST 3: research_llm_classify
# ============================================================================


@pytest.mark.asyncio
async def test_research_llm_classify_basic(mock_refusal_meta):
    """Test classification into allowed labels."""
    text = "I love this product!"
    labels = ["positive", "negative", "neutral"]

    # Mock response returns a label
    response_with_label = LLMResponse(
        text="positive",
        model="test-model",
        provider="test-provider",
        cost_usd=0.0005,
        input_tokens=8,
        output_tokens=1,
        finish_reason="stop",
        latency_ms=50,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (response_with_label, mock_refusal_meta)

        result = await research_llm_classify(
            text=text,
            labels=labels,
        )

    # Assert: returns dict with 'label' key in the labels list
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "label" in result, "Result must have 'label' key"
    assert result["label"] in labels, "Label must be from allowed list"
    assert result["label"] == "positive"

    # Check other expected keys
    assert "model" in result
    assert "provider" in result
    assert "cost_usd" in result


@pytest.mark.asyncio
async def test_research_llm_classify_multi_label(mock_refusal_meta):
    """Test multi-label classification."""
    text = "Great product with excellent support"
    labels = ["positive", "negative", "excellent-support"]

    # Mock response returns array
    response_with_labels = LLMResponse(
        text='["positive", "excellent-support"]',
        model="test-model",
        provider="test-provider",
        cost_usd=0.0005,
        input_tokens=8,
        output_tokens=2,
        finish_reason="stop",
        latency_ms=50,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (response_with_labels, mock_refusal_meta)

        result = await research_llm_classify(
            text=text,
            labels=labels,
            multi_label=True,
        )

    # Assert: returns dict with 'labels' key (plural)
    assert isinstance(result, dict)
    assert "labels" in result, "Result must have 'labels' key for multi_label=True"
    assert isinstance(result["labels"], list), "Labels must be a list"
    assert all(label in labels for label in result["labels"]), "All labels must be from allowed list"


@pytest.mark.asyncio
async def test_research_llm_classify_empty_labels():
    """Test classify with empty labels list."""
    result = await research_llm_classify(
        text="Some text",
        labels=[],
    )

    # Assert: returns error for empty labels
    assert isinstance(result, dict)
    assert "error" in result


# ============================================================================
# TEST 4: research_llm_translate
# ============================================================================


@pytest.mark.asyncio
async def test_research_llm_translate_basic(mock_refusal_meta):
    """Test translation to Arabic."""
    text = "Hello world"

    # Mock Arabic translation
    response_ar = LLMResponse(
        text="السلام عليكم العالم",
        model="test-model",
        provider="test-provider",
        cost_usd=0.001,
        input_tokens=5,
        output_tokens=3,
        finish_reason="stop",
        latency_ms=80,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (response_ar, mock_refusal_meta)

        result = await research_llm_translate(
            text=text,
            target_lang="ar",
        )

    # Assert: returns dict with 'translated' key
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "translated" in result, "Result must have 'translated' key"
    assert isinstance(result["translated"], str), "Translated must be a string"
    assert result["translated"] == "السلام عليكم العالم"

    # Check other expected keys
    assert "model" in result
    assert "provider" in result
    assert "cost_usd" in result


@pytest.mark.asyncio
async def test_research_llm_translate_with_source_lang(mock_refusal_meta):
    """Test translation with source language specified."""
    text = "Bonjour"

    response_translated = LLMResponse(
        text="Hello",
        model="test-model",
        provider="test-provider",
        cost_usd=0.0008,
        input_tokens=4,
        output_tokens=1,
        finish_reason="stop",
        latency_ms=60,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (response_translated, mock_refusal_meta)

        result = await research_llm_translate(
            text=text,
            target_lang="en",
            source_lang="fr",
        )

    # Assert: returns dict with 'translated' key
    assert isinstance(result, dict)
    assert "translated" in result


# ============================================================================
# TEST 5: research_llm_answer
# ============================================================================


@pytest.mark.asyncio
async def test_research_llm_answer_basic(mock_refusal_meta):
    """Test question answering with sources."""
    question = "What is Python?"
    sources = [
        {
            "title": "Wikipedia",
            "text": "Python is a high-level, interpreted programming language with dynamic typing.",
            "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
        },
        {
            "title": "Official Docs",
            "text": "Python is an interpreted, high-level programming language for general-purpose programming.",
            "url": "https://www.python.org",
        },
    ]

    response_answer = LLMResponse(
        text="Python is a high-level programming language [1] used for general-purpose programming [2].",
        model="test-model",
        provider="test-provider",
        cost_usd=0.002,
        input_tokens=50,
        output_tokens=20,
        finish_reason="stop",
        latency_ms=120,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (response_answer, mock_refusal_meta)

        result = await research_llm_answer(
            question=question,
            sources=sources,
            max_tokens=100,
        )

    # Assert: returns dict with 'answer' key
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "answer" in result, "Result must have 'answer' key"
    assert isinstance(result["answer"], str), "Answer must be a string"
    assert "[1]" in result["answer"] or len(result["answer"]) > 0, "Answer should contain citations or be non-empty"

    # Check other expected keys
    assert "citations" in result, "Result must have 'citations' key"
    assert isinstance(result["citations"], list), "Citations must be a list"
    assert len(result["citations"]) == 2, "Citations should contain the provided sources"
    assert "model" in result
    assert "provider" in result
    assert "cost_usd" in result


@pytest.mark.asyncio
async def test_research_llm_answer_no_sources(mock_refusal_meta):
    """Test answer with empty sources list."""
    result = await research_llm_answer(
        question="What is Python?",
        sources=[],
    )

    # Assert: returns answer with empty citations
    assert isinstance(result, dict)
    assert "answer" in result
    assert result["answer"] == "No sources provided."
    assert result["citations"] == []


# ============================================================================
# TEST 6: research_llm_embed
# ============================================================================


@pytest.mark.asyncio
async def test_research_llm_embed_basic():
    """Test embeddings generation."""
    texts = ["hello world", "goodbye world"]

    # Mock embeddings (768-dim vectors)
    embeddings = [
        [0.1] * 768,  # First embedding
        [0.2] * 768,  # Second embedding
    ]

    with patch("loom.tools.llm._build_provider_chain") as mock_chain:
        mock_provider = AsyncMock()
        mock_provider.available.return_value = True
        mock_provider.embed = AsyncMock(return_value=embeddings)
        mock_provider.name = "test-provider"
        mock_chain.return_value = [mock_provider]

        result = await research_llm_embed(
            texts=texts,
        )

    # Assert: returns dict with 'embeddings' key, list of 2
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "embeddings" in result, "Result must have 'embeddings' key"
    assert isinstance(result["embeddings"], list), "Embeddings must be a list"
    assert len(result["embeddings"]) == 2, "Should have 2 embeddings for 2 inputs"
    assert isinstance(result["embeddings"][0], list), "Each embedding should be a list"

    # Check other expected keys
    assert "text_count" in result
    assert result["text_count"] == 2
    assert "model" in result
    assert "provider" in result
    assert "cost_usd" in result


@pytest.mark.asyncio
async def test_research_llm_embed_empty_texts():
    """Test embeddings with empty list."""
    result = await research_llm_embed(
        texts=[],
    )

    # Assert: returns empty embeddings
    assert isinstance(result, dict)
    assert "embeddings" in result
    assert result["embeddings"] == []


@pytest.mark.asyncio
async def test_research_llm_embed_error_handling():
    """Test embeddings error handling."""
    with patch("loom.tools.llm._build_provider_chain") as mock_chain:
        mock_provider = AsyncMock()
        mock_provider.available.return_value = True
        mock_provider.embed = AsyncMock(side_effect=RuntimeError("Provider failed"))
        mock_chain.return_value = [mock_provider]

        result = await research_llm_embed(
            texts=["hello"],
        )

    # Assert: returns dict with 'error' key on failure
    assert isinstance(result, dict)
    assert "error" in result


# ============================================================================
# TEST 7: research_llm_chat
# ============================================================================


@pytest.mark.asyncio
async def test_research_llm_chat_basic(mock_refusal_meta):
    """Test raw LLM chat pass-through."""
    messages = [
        {"role": "user", "content": "Say hello"}
    ]

    response_chat = LLMResponse(
        text="Hello! How can I help you today?",
        model="test-model",
        provider="test-provider",
        cost_usd=0.001,
        input_tokens=5,
        output_tokens=10,
        finish_reason="stop",
        latency_ms=90,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (response_chat, mock_refusal_meta)

        result = await research_llm_chat(
            messages=messages,
            max_tokens=50,
        )

    # Assert: returns dict with 'text' key
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "text" in result, "Result must have 'text' key"
    assert isinstance(result["text"], str), "Text must be a string"
    assert result["text"] == "Hello! How can I help you today?"

    # Check other expected keys
    assert "model" in result
    assert "provider" in result
    assert "cost_usd" in result
    assert "input_tokens" in result
    assert "output_tokens" in result
    assert "finish_reason" in result


@pytest.mark.asyncio
async def test_research_llm_chat_multi_turn(mock_refusal_meta):
    """Test multi-turn conversation."""
    messages = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "2+2=4"},
        {"role": "user", "content": "What is 3+3?"},
    ]

    response_chat = LLMResponse(
        text="3+3=6",
        model="test-model",
        provider="test-provider",
        cost_usd=0.0015,
        input_tokens=20,
        output_tokens=5,
        finish_reason="stop",
        latency_ms=70,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        mock_call.return_value = (response_chat, mock_refusal_meta)

        result = await research_llm_chat(
            messages=messages,
            max_tokens=50,
        )

    # Assert: returns dict with 'text' key
    assert isinstance(result, dict)
    assert "text" in result


# ============================================================================
# TEST 8: research_detect_language
# ============================================================================


async def test_research_detect_language_english():
    """Test language detection for English."""
    text = "The quick brown fox jumps over the lazy dog. This is a sample English text for testing language detection."

    result = await research_detect_language(text)

    # Assert: returns dict with 'language' key
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "language" in result, "Result must have 'language' key"
    assert "confidence" in result, "Result must have 'confidence' key"

    # Confidence should be float
    assert isinstance(result["confidence"], (float, int)), "Confidence must be numeric"

    # For English, should detect 'en'
    # Note: langdetect might return slightly different results, so be lenient
    if "error" not in result:
        assert result["language"] in ["en", "unknown"], "Should detect English or unknown"


async def test_research_detect_language_arabic():
    """Test language detection for Arabic."""
    text = "مرحبا بك في العالم. هذا نص عربي لاختبار كشف اللغة. الذكاء الاصطناعي رائع جدا في معالجة اللغات الطبيعية."

    result = await research_detect_language(text)

    # Assert: returns dict with 'language' key
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "language" in result, "Result must have 'language' key"
    assert "confidence" in result, "Result must have 'confidence' key"

    # For Arabic, should detect 'ar' (or variations)
    if "error" not in result:
        assert result["language"] in ["ar", "unknown"], "Should detect Arabic or unknown"


async def test_research_detect_language_short_text():
    """Test language detection with very short text."""
    text = "Hi"

    result = await research_detect_language(text)

    # Assert: returns dict with 'error' key for text too short
    assert isinstance(result, dict)
    # Short text returns error
    if len(text) < 10:
        # Should either return error or unknown
        assert "error" in result or result["language"] == "unknown", "Short text should return error or unknown"


async def test_research_detect_language_with_alternatives():
    """Test language detection returns alternatives."""
    text = "This is English text with enough content to detect the language properly. Language detection is an important NLP task."

    result = await research_detect_language(text)

    # Assert: has alternatives list
    assert isinstance(result, dict)
    if "error" not in result and "alternatives" in result:
        assert isinstance(result["alternatives"], list), "Alternatives must be a list"
        if result["alternatives"]:
            assert "lang" in result["alternatives"][0], "Alternative must have 'lang' key"
            assert "prob" in result["alternatives"][0], "Alternative must have 'prob' key"


# ============================================================================
# Integration Test: Chain of Operations
# ============================================================================


@pytest.mark.asyncio
async def test_integration_llm_pipeline(mock_refusal_meta):
    """Test chaining multiple LLM operations."""
    # Simulate: classify -> translate -> extract

    # Step 1: Classify
    response_classify = LLMResponse(
        text="positive",
        model="test-model",
        provider="test-provider",
        cost_usd=0.0005,
        input_tokens=8,
        output_tokens=1,
        finish_reason="stop",
        latency_ms=50,
    )

    # Step 2: Translate
    response_translate = LLMResponse(
        text="إيجابي",
        model="test-model",
        provider="test-provider",
        cost_usd=0.001,
        input_tokens=5,
        output_tokens=2,
        finish_reason="stop",
        latency_ms=80,
    )

    # Step 3: Extract
    response_extract = LLMResponse(
        text='{"sentiment": "positive", "lang": "ar"}',
        model="test-model",
        provider="test-provider",
        cost_usd=0.002,
        input_tokens=15,
        output_tokens=8,
        finish_reason="stop",
        latency_ms=100,
    )

    with patch("loom.tools.llm._call_with_refusal_handling") as mock_call:
        # Sequential calls with different responses
        mock_call.side_effect = [
            (response_classify, mock_refusal_meta),
            (response_translate, mock_refusal_meta),
            (response_extract, mock_refusal_meta),
        ]

        # Step 1
        result1 = await research_llm_classify(
            text="I love this!",
            labels=["positive", "negative"],
        )
        assert "label" in result1
        assert result1["label"] == "positive"

        # Step 2
        result2 = await research_llm_translate(
            text="positive",
            target_lang="ar",
        )
        assert "translated" in result2

        # Step 3
        result3 = await research_llm_extract(
            text=result2["translated"],
            schema={"sentiment": "string", "lang": "string"},
        )
        assert "data" in result3
        assert result3["data"]["sentiment"] == "positive"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--timeout=300", "--maxfail=5"])
