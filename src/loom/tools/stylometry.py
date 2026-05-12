"""research_stylometry — Author fingerprinting via writing style analysis."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from collections import Counter
from typing import Any

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

logger = logging.getLogger("loom.tools.stylometry")

# Top 20 English function words for frequency analysis
FUNCTION_WORDS = {
    "the",
    "is",
    "at",
    "which",
    "on",
    "and",
    "to",
    "a",
    "of",
    "in",
    "for",
    "that",
    "be",
    "it",
    "as",
    "with",
    "by",
    "from",
    "or",
    "are",
}


def _tokenize_sentences(text: str) -> list[str]:
    """Split text into sentences using basic regex."""
    # Split on period, question mark, exclamation mark
    sentences = re.split(r"[.!?]+", text)
    # Filter out empty strings and strip whitespace
    return [s.strip() for s in sentences if s.strip()]


def _tokenize_words(text: str) -> list[str]:
    """Split text into words using basic regex."""
    # Convert to lowercase and split on non-word characters
    words = re.findall(r"\b\w+\b", text.lower())
    return words


def _extract_features(text: str) -> dict[str, Any]:
    """Extract linguistic features from text (CPU-bound).

    Returns dict with:
    - avg_word_length, avg_sentence_length
    - vocabulary_richness (type-token ratio)
    - hapax_ratio (words appearing once)
    - yules_k (vocabulary richness measure)
    - punctuation_profile
    - function_word_profile
    - word_count, sentence_count

    This is a pure sync function suitable for CPU executor.
    """
    if not text or len(text) < 100:
        return {
            "avg_word_length": 0.0,
            "avg_sentence_length": 0.0,
            "vocabulary_richness": 0.0,
            "hapax_ratio": 0.0,
            "yules_k": 0.0,
            "punctuation_profile": {},
            "function_word_profile": {},
            "word_count": len(_tokenize_words(text)) if text else 0,
            "sentence_count": len(_tokenize_sentences(text)) if text else 0,
        }

    sentences = _tokenize_sentences(text)
    words = _tokenize_words(text)

    if not words or not sentences:
        return {
            "avg_word_length": 0.0,
            "avg_sentence_length": 0.0,
            "vocabulary_richness": 0.0,
            "hapax_ratio": 0.0,
            "yules_k": 0.0,
            "punctuation_profile": {},
            "function_word_profile": {},
            "word_count": len(words),
            "sentence_count": len(sentences),
        }

    word_count = len(words)
    sentence_count = len(sentences)

    # Average word length
    total_char_length = sum(len(w) for w in words)
    avg_word_length = total_char_length / word_count if word_count > 0 else 0.0

    # Average sentence length
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0.0

    # Vocabulary richness (type-token ratio)
    unique_words = len(set(words))
    vocabulary_richness = unique_words / word_count if word_count > 0 else 0.0

    # Hapax legomena ratio (words appearing exactly once)
    word_freq = Counter(words)
    hapax_count = sum(1 for count in word_freq.values() if count == 1)
    hapax_ratio = hapax_count / word_count if word_count > 0 else 0.0

    # Yule's K measure of vocabulary richness
    # K = 10000 * (M1 - N) / (N^2)
    # where M1 = sum of frequency^2 for each unique word frequency
    # and N = total number of words
    # Simplified calculation: sum of (frequency * frequency) for each word
    m1 = sum(freq * freq for freq in word_freq.values())
    yules_k = (10000 * (m1 - word_count)) / (word_count * word_count) if word_count > 0 else 0.0
    yules_k = max(0.0, yules_k)  # Ensure non-negative

    # Punctuation frequency distribution
    punctuation_counts = {
        "comma": text.count(","),
        "period": text.count("."),
        "question": text.count("?"),
        "exclamation": text.count("!"),
        "semicolon": text.count(";"),
        "colon": text.count(":"),
        "apostrophe": text.count("'"),
        "quotation": text.count('"'),
        "dash": text.count("-"),
        "parenthesis": text.count("(") + text.count(")"),
    }

    # Normalize punctuation by sentence count
    punctuation_profile = {}
    for punc_type, count in punctuation_counts.items():
        punctuation_profile[punc_type] = count / sentence_count if sentence_count > 0 else 0.0

    # Function word frequency profile
    function_word_counts = {fw: words.count(fw) for fw in FUNCTION_WORDS}
    function_word_profile = {}
    for fw, count in function_word_counts.items():
        function_word_profile[fw] = count / word_count if word_count > 0 else 0.0

    return {
        "avg_word_length": round(avg_word_length, 3),
        "avg_sentence_length": round(avg_sentence_length, 3),
        "vocabulary_richness": round(vocabulary_richness, 3),
        "hapax_ratio": round(hapax_ratio, 3),
        "yules_k": round(yules_k, 3),
        "punctuation_profile": {k: round(v, 4) for k, v in punctuation_profile.items()},
        "function_word_profile": {k: round(v, 4) for k, v in function_word_profile.items()},
        "word_count": word_count,
        "sentence_count": sentence_count,
    }


def _cosine_similarity(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    """Compute cosine similarity between two feature vectors."""
    # Get all keys
    all_keys = set(vec1.keys()) | set(vec2.keys())

    # Compute dot product
    dot_product = 0.0
    for key in all_keys:
        dot_product += vec1.get(key, 0.0) * vec2.get(key, 0.0)

    # Compute magnitudes
    mag1 = math.sqrt(sum(v**2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v**2 for v in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


def _flatten_features(features: dict[str, Any]) -> dict[str, float]:
    """Flatten nested feature dict into single-level float dict for similarity."""
    flat: dict[str, float] = {}

    for key, value in features.items():
        if isinstance(value, dict):
            # Flatten nested dicts with prefix
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (int, float)):
                    flat[f"{key}_{sub_key}"] = float(sub_value)
        elif isinstance(value, (int, float)):
            flat[key] = float(value)

    return flat


async def research_stylometry(
    text: str, compare_texts: list[str] | None = None
) -> dict[str, Any]:
    """Analyze text for stylometric fingerprinting (async with CPU executor).

    Extracts linguistic features to identify author writing style.
    Optionally compares against reference texts. Feature extraction
    runs in the CPU executor to avoid blocking the event loop.

    Args:
        text: Text to analyze (minimum 100 characters)
        compare_texts: Optional list of reference texts for comparison

    Returns:
        Dict with features, optional comparisons, and metadata
    """
    if not text or len(text) < 100:
        logger.warning("stylometry: text too short (min 100 chars)")
        return {
            "error": "Text must be at least 100 characters",
            "word_count": len(_tokenize_words(text)) if text else 0,
            "sentence_count": len(_tokenize_sentences(text)) if text else 0,
        }

    # Run CPU-intensive feature extraction in executor
    try:
        from loom.cpu_executor import run_cpu_bound

        features = await run_cpu_bound(_extract_features, text)
    except Exception as exc:
        logger.error("stylometry cpu_executor failed: %s", exc)
        return {
            "error": f"Feature extraction failed: {str(exc)[:100]}",
            "text_length": len(text),
        }

    words = _tokenize_words(text)
    sentences = _tokenize_sentences(text)

    result: dict[str, Any] = {
        "features": features,
        "word_count": len(words),
        "sentence_count": len(sentences),
    }

    # Optional: compare against reference texts
    if compare_texts:
        main_features_flat = _flatten_features(features)
        comparisons = []

        for idx, compare_text in enumerate(compare_texts):
            if not compare_text or len(compare_text) < 100:
                comparisons.append(
                    {
                        "index": idx,
                        "similarity": 0.0,
                        "verdict": "insufficient_data",
                    }
                )
                continue

            # Run each comparison's feature extraction in executor
            try:
                compare_features = await run_cpu_bound(_extract_features, compare_text)
            except Exception as exc:
                logger.warning("stylometry comparison %d failed: %s", idx, exc)
                comparisons.append(
                    {
                        "index": idx,
                        "similarity": 0.0,
                        "verdict": "extraction_error",
                        "error": str(exc)[:50],
                    }
                )
                continue

            compare_features_flat = _flatten_features(compare_features)
            similarity = _cosine_similarity(main_features_flat, compare_features_flat)

            # Determine verdict based on thresholds
            if similarity > 0.85:
                verdict = "likely_same_author"
            elif similarity >= 0.6:
                verdict = "possible_match"
            else:
                verdict = "different_author"

            comparisons.append(
                {
                    "index": idx,
                    "similarity": round(similarity, 3),
                    "verdict": verdict,
                }
            )

        result["comparisons"] = comparisons

    return result


async def tool_stylometry(
    text: str, compare_texts: list[str] | None = None
) -> list[TextContent]:
    """MCP wrapper for research_stylometry.

    Async wrapper that properly awaits the async research function.
    """
    result = await research_stylometry(text, compare_texts)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
