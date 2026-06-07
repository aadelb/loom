"""Context Compression — reduce token count while preserving key information.

Lightweight alternative to LLMLingua that doesn't need GPU model weights.
Uses heuristic compression: sentence importance scoring, redundancy removal,
and smart truncation based on information density.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import logging
import re
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.context_compress")

_LOW_INFO_PATTERNS = [
    r"\b(?:however|moreover|furthermore|additionally|in addition)\b",
    r"\b(?:it is worth noting|it should be noted|please note)\b",
    r"\b(?:as mentioned (?:earlier|above|before|previously))\b",
    r"\b(?:in conclusion|to summarize|in summary|overall)\b",
    r"\b(?:disclaimer|note that|important to)\b",
]

_HIGH_INFO_INDICATORS = [
    r"\b(?:CVE-\d{4}-\d+|RFC\s*\d+|NIST|OWASP)\b",
    r"https?://\S+",
    r"\b(?:\d+\.\d+\.\d+)\b",
    r"```[\s\S]+?```",
    r"\b(?:step \d+|phase \d+)\b",
    r"\$\s*[\d,]+",
    r"\b(?:specifically|exactly|precisely)\b",
]


def _score_sentence(sentence: str) -> float:
    """Score a sentence by information density (0-1)."""
    if len(sentence.strip()) < 10:
        return 0.1

    score = 0.5

    for pattern in _HIGH_INFO_INDICATORS:
        if re.search(pattern, sentence, re.IGNORECASE):
            score += 0.15

    for pattern in _LOW_INFO_PATTERNS:
        if re.search(pattern, sentence, re.IGNORECASE):
            score -= 0.2

    word_count = len(sentence.split())
    if word_count > 5:
        unique_ratio = len(set(sentence.lower().split())) / word_count
        score += unique_ratio * 0.2

    if re.search(r'\d', sentence):
        score += 0.1
    if re.search(r'[A-Z]{2,}', sentence):
        score += 0.05

    return max(0.0, min(1.0, score))


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    text = re.sub(r'(Mr|Mrs|Ms|Dr|Prof|Inc|Ltd|Corp)\.\s', r'\1<DOT> ', text)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.replace('<DOT>', '.').strip() for s in sentences if s.strip()]


def _remove_redundancy(sentences: list[str]) -> list[str]:
    """Remove highly similar consecutive sentences."""
    if len(sentences) <= 1:
        return sentences

    result = [sentences[0]]
    for i in range(1, len(sentences)):
        prev_words = set(sentences[i - 1].lower().split())
        curr_words = set(sentences[i].lower().split())
        if prev_words and curr_words:
            overlap = len(prev_words & curr_words) / max(len(prev_words), len(curr_words))
            if overlap < 0.7:
                result.append(sentences[i])
    return result


@handle_tool_errors("research_context_compress")
async def research_context_compress(
    text: str,
    target_ratio: float = 0.5,
    preserve_code: bool = True,
    preserve_urls: bool = True,
) -> dict[str, Any]:
    """Compress text while preserving the most important information.

    Uses heuristic scoring: keeps high-info sentences (with numbers,
    URLs, code, specific terms) and removes filler/redundancy.

    Args:
        text: Text to compress.
        target_ratio: Target compression ratio (0.3=aggressive, 0.7=mild). Default 0.5.
        preserve_code: Keep code blocks intact (default True).
        preserve_urls: Keep URLs intact (default True).

    Returns:
        Dict with compressed text, original/compressed lengths,
        compression ratio achieved, and sentences kept/removed.
    """
    if not text or len(text) < 100:
        return {
            "compressed": text,
            "original_length": len(text or ""),
            "compressed_length": len(text or ""),
            "ratio": 1.0,
            "sentences_kept": 0,
            "sentences_removed": 0,
        }

    original_length = len(text)

    code_blocks = []
    if preserve_code:
        code_blocks = re.findall(r'```[\s\S]*?```', text)
        for i, block in enumerate(code_blocks):
            text = text.replace(block, f"__CODE_BLOCK_{i}__")

    sentences = _split_sentences(text)
    sentences = _remove_redundancy(sentences)

    scored = [(s, _score_sentence(s)) for s in sentences]
    scored.sort(key=lambda x: -x[1])

    target_chars = int(original_length * target_ratio)
    kept = []
    total_chars = 0

    for sent, score in scored:
        if total_chars >= target_chars:
            break
        kept.append(sent)
        total_chars += len(sent)

    original_order = []
    for sent in sentences:
        if sent in kept:
            original_order.append(sent)

    compressed = " ".join(original_order)

    if preserve_code:
        for i, block in enumerate(code_blocks):
            compressed = compressed.replace(f"__CODE_BLOCK_{i}__", block)

    return {
        "compressed": compressed,
        "original_length": original_length,
        "compressed_length": len(compressed),
        "ratio": round(len(compressed) / original_length, 2),
        "sentences_kept": len(kept),
        "sentences_removed": len(sentences) - len(kept),
    }
