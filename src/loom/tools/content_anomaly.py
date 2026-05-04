"""Content anomaly detection for fetch results.

Detects bait-and-switch attacks and injection attempts by comparing
search snippets against actual fetched content using Jaccard similarity
and pattern matching.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.content_anomaly")

# Injection pattern signatures for common attack vectors
_INJECTION_PATTERNS = [
    # SQL injection patterns
    r"(?i)(union\s+.*select|select\s+.*from|drop\s+table|insert\s+into|update\s+set)",
    # Script injection patterns
    r"(?i)(<script|javascript:|onerror=|onload=)",
    # Command injection patterns
    r"(?i)(bash|cmd|exec|system|shell)",
    # XXE/XML injection (escaped properly)
    r"(?i)(<!ENTITY|DOCTYPE.*SYSTEM)",
    # LDAP injection
    r"(?i)(\*\)|(&\()",
]


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, remove extra whitespace."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def _extract_words(text: str) -> set[str]:
    """Extract words from text for set comparison."""
    normalized = _normalize_text(text)
    # Filter out very short words and common stopwords
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would", "should",
        "could", "can", "may", "might", "must", "shall", "this", "that",
        "these", "those", "i", "you", "he", "she", "it", "we", "they",
    }
    words = set(normalized.split())
    return {w for w in words if len(w) > 2 and w not in stopwords}


def _jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """Calculate Jaccard similarity between two sets.

    Jaccard similarity = |intersection| / |union|
    Returns 0.0-1.0 where 1.0 is perfect match.
    """
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return intersection / union


def _detect_injection_patterns(content: str) -> bool:
    """Detect injection attack patterns in content.

    Args:
        content: Content to check for injection patterns

    Returns:
        True if injection patterns detected, False otherwise
    """
    return any(re.search(pattern, content) for pattern in _INJECTION_PATTERNS)


def detect_anomaly(snippet: str, fetched_content: str) -> dict[str, Any]:
    """Detect content anomalies between search snippet and fetched content.

    Compares search snippet with actual fetched content to detect:
    - Bait-and-switch attacks (content mismatch)
    - Injection attempts (malicious patterns in content)

    Args:
        snippet: Search result snippet text (expected content)
        fetched_content: Actual fetched content from the URL

    Returns:
        Dictionary with:
        - anomaly_detected: bool, True if anomaly found
        - type: str, one of "none", "bait_and_switch", "injection_attempt", "mixed"
        - similarity_score: float, Jaccard similarity 0.0-1.0
        - details: str, human-readable explanation
        - injection_found: bool, True if injection patterns detected
    """
    if not snippet or not fetched_content:
        return {
            "anomaly_detected": False,
            "type": "none",
            "similarity_score": 0.0,
            "details": "Missing snippet or content",
            "injection_found": False,
        }

    # Extract word sets for similarity comparison
    snippet_words = _extract_words(snippet)
    content_words = _extract_words(fetched_content)

    # Calculate Jaccard similarity
    similarity = _jaccard_similarity(snippet_words, content_words)

    # Detect injection patterns
    injection_detected = _detect_injection_patterns(fetched_content)

    # Determine anomaly type
    anomaly_detected = False
    anomaly_type = "none"
    details = ""

    if injection_detected:
        anomaly_detected = True
        anomaly_type = "injection_attempt"
        details = "Injection patterns detected in fetched content"

    if similarity < 0.3:
        anomaly_detected = True
        if anomaly_type == "injection_attempt":
            anomaly_type = "mixed"
            details += " and content mismatch detected"
        else:
            anomaly_type = "bait_and_switch"
            details = f"Content mismatch: snippet similarity only {similarity:.1%}"

    if not anomaly_detected:
        details = f"Content appears legitimate (similarity: {similarity:.1%})"

    return {
        "anomaly_detected": anomaly_detected,
        "type": anomaly_type,
        "similarity_score": similarity,
        "details": details,
        "injection_found": injection_detected,
    }


def research_content_anomaly(
    url: str,
    expected_snippet: str,
    actual_content: str,
) -> dict[str, Any]:
    """MCP tool wrapper for content anomaly detection.

    Detects bait-and-switch attacks and injection attempts by comparing
    a search result snippet with actual fetched content.

    Args:
        url: URL that was fetched (for logging/reporting)
        expected_snippet: Search result snippet text
        actual_content: Actual content fetched from the URL

    Returns:
        Dictionary with anomaly detection results:
        - anomaly_detected: bool
        - type: "none" | "bait_and_switch" | "injection_attempt" | "mixed"
        - similarity_score: float (0.0-1.0)
        - details: str
        - injection_found: bool
        - url: str (echoed back for context)
    """
    logger.info(
        "content_anomaly_check url=%s snippet_len=%d content_len=%d",
        url,
        len(expected_snippet),
        len(actual_content),
    )

    result = detect_anomaly(expected_snippet, actual_content)
    result["url"] = url

    if result["anomaly_detected"]:
        logger.warning(
            "content_anomaly_detected url=%s type=%s similarity=%.2f",
            url,
            result["type"],
            result["similarity_score"],
        )
    else:
        logger.debug(
            "content_anomaly_none url=%s similarity=%.2f",
            url,
            result["similarity_score"],
        )

    return result
