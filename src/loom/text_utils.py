"""Text processing utilities shared across tools.

Consolidates duplicated text operations: keyword extraction, truncation,
word counting, text chunking, similarity metrics, and text cleaning.
Eliminates redundant implementations across 154 tool modules.
"""

from __future__ import annotations

import re
from collections import Counter

# Common English stopwords for filtering
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "can", "could",
    "did", "do", "does", "for", "from", "had", "has", "have", "he", "her",
    "his", "how", "i", "if", "in", "into", "is", "it", "its", "just", "may",
    "me", "might", "my", "no", "not", "of", "on", "or", "our", "out", "over",
    "she", "should", "so", "some", "such", "than", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "to", "too", "under",
    "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "would", "you", "your",
}


def extract_keywords(
    text: str,
    *,
    max_keywords: int = 10,
    min_length: int = 3,
) -> list[str]:
    """Extract top keywords from text by frequency, filtering stopwords.

    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to return
        min_length: Minimum word length to consider (characters)

    Returns:
        List of top keywords sorted by frequency (descending)
    """
    words = re.findall(r"\b[a-z]+\b", text.lower())
    filtered = [
        w for w in words if len(w) >= min_length and w not in _STOPWORDS
    ]
    return [word for word, _ in Counter(filtered).most_common(max_keywords)]


def truncate(
    text: str,
    max_chars: int = 500,
    *,
    suffix: str = "...",
) -> str:
    """Truncate text to max_chars, appending suffix if truncated.

    Args:
        text: Text to truncate
        max_chars: Maximum characters to keep (including suffix)
        suffix: String to append if text is truncated

    Returns:
        Truncated text (original if under max_chars, truncated + suffix otherwise)
    """
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def count_words(text: str) -> int:
    """Count words in text.

    Args:
        text: Text to count words in

    Returns:
        Number of words (whitespace-separated tokens)
    """
    return len(text.split())


def estimate_tokens(text: str) -> int:
    """Rough token estimate (approximately 4 characters per token for English).

    Args:
        text: Text to estimate token count for

    Returns:
        Approximate token count (minimum 1)
    """
    return max(1, len(text) // 4)


def split_into_chunks(
    text: str,
    *,
    chunk_size: int = 4000,
    overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks for LLM processing.

    Chunks are created with specified overlap to preserve context at boundaries.

    Args:
        text: Text to split
        chunk_size: Target size of each chunk (characters)
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks (non-empty), or [text] if text <= chunk_size
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():  # Skip empty chunks
            chunks.append(chunk)
        start = end - overlap

    return chunks


def jaccard_similarity(
    a: str | set[str],
    b: str | set[str],
) -> float:
    """Jaccard similarity between two texts or sets of tokens.

    If strings are passed, they're tokenized into word sets first.
    Returns 1.0 if both are empty, 0.0 if one is empty and the other isn't.

    Args:
        a: First text/set (string or set of tokens)
        b: Second text/set (string or set of tokens)

    Returns:
        Jaccard similarity in range [0.0, 1.0], where 1.0 is perfect match
    """
    if isinstance(a, str):
        a = set(a.lower().split())
    if isinstance(b, str):
        b = set(b.lower().split())

    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    intersection = len(a & b)
    union = len(a | b)

    return intersection / union if union > 0 else 0.0


def clean_text(text: str) -> str:
    """Remove extra whitespace, control chars, normalize newlines.

    Removes control characters, normalizes line endings, condenses spaces
    and multiple newlines to single newlines.

    Args:
        text: Text to clean

    Returns:
        Cleaned text (whitespace trimmed, normalized)
    """
    # Remove control characters except newline, tab
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize line endings (CRLF -> LF)
    text = re.sub(r"\r\n", "\n", text)
    # Condense multiple spaces/tabs to single space
    text = re.sub(r"[ \t]+", " ", text)
    # Condense multiple newlines (3+) to double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
