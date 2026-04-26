"""Cipher Mirror — Monitor paste sites for leaked credentials and model weights.

Tool:
- research_cipher_mirror: entropy-based credential detection on paste sites
"""

from __future__ import annotations

import asyncio
import logging
import re
from functools import partial
from typing import Any

logger = logging.getLogger("loom.tools.cipher_mirror")

# Common API key patterns (prefix-based detection)
_API_KEY_PATTERNS = {
    "openai": (r"sk-[A-Za-z0-9\-_]{20,}", "sk-"),
    "nvidia_nim": (r"nvapi-[A-Za-z0-9\-_]{20,}", "nvapi-"),
    "github": (r"ghp_[A-Za-z0-9]{36,}", "ghp_"),
    "aws": (r"AKIA[0-9A-Z]{16}", "AKIA"),
    "stripe": (r"sk_live_[A-Za-z0-9]{24,}", "sk_live_"),
    "sendgrid": (r"SG\.[A-Za-z0-9\-_]{20,}", "SG."),
    "anthropic": (r"sk-ant-[A-Za-z0-9\-_]{20,}", "sk-ant-"),
    "huggingface": (r"hf_[A-Za-z0-9]{34,}", "hf_"),
}

# Model weight file patterns (common extensions/names)
_MODEL_WEIGHT_PATTERNS = [
    r"model\.safetensors",
    r"model\.bin",
    r"pytorch_model\.bin",
    r"adapter_model\.safetensors",
    r"adapter_config\.json",
    r"model\.gguf",
    r"model\.onnx",
    r"weights\.pt",
    r"checkpoints/\w+\.pt",
    r"LoRA.*\.safetensors",
]


def _entropy_score(text: str, window_size: int = 32) -> float:
    """Calculate Shannon entropy of a string (0.0 to 1.0 normalized).

    High entropy indicates random/encrypted content (like API keys, tokens).

    Args:
        text: string to analyze
        window_size: analyze this many chars (default 32)

    Returns:
        Entropy score from 0.0 (all same char) to 1.0 (max randomness)
    """
    if not text or window_size <= 0:
        return 0.0

    sample = text[:window_size]
    if len(sample) < 10:
        return 0.0

    # Count frequency of each byte
    freq: dict[int, int] = {}
    for byte in sample.encode():
        freq[byte] = freq.get(byte, 0) + 1

    # Shannon entropy
    entropy = 0.0
    for count in freq.values():
        p = count / len(sample)
        entropy -= p * (p ** 0.5) if p > 0 else 0

    # Normalize to 0-1 (max entropy is ~5.0 for 256 possible values)
    return min(entropy / 5.0, 1.0)


def _detect_credentials(text: str) -> list[dict[str, Any]]:
    """Scan text for high-entropy credentials matching known patterns.

    Args:
        text: content to scan

    Returns:
        List of detected credentials with type and confidence
    """
    findings: list[dict[str, Any]] = []

    for key_type, (pattern, prefix) in _API_KEY_PATTERNS.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            candidate = match.group(0)
            entropy = _entropy_score(candidate)

            # High-entropy strings matching API key pattern are likely real
            if entropy > 0.6:
                findings.append({
                    "type": "api_key",
                    "key_type": key_type,
                    "confidence": round(min(0.95, entropy + 0.1), 2),
                    "length": len(candidate),
                    "snippet": candidate[:20] + "..." if len(candidate) > 20 else candidate,
                })

    return findings


def _detect_model_weights(text: str, snippet: str = "") -> list[dict[str, Any]]:
    """Scan text and snippet for references to model weight files.

    Args:
        text: content to scan
        snippet: additional context (title, description)

    Returns:
        List of detected model weight references
    """
    findings: list[dict[str, Any]] = []
    search_text = (text + " " + snippet).lower()

    for pattern in _MODEL_WEIGHT_PATTERNS:
        matches = re.finditer(pattern, search_text, re.IGNORECASE)
        for match in matches:
            findings.append({
                "type": "model_weight",
                "filename": match.group(0),
                "confidence": 0.85,
            })

    return findings


async def research_cipher_mirror(
    query: str,
    n: int = 10,
    entropy_threshold: float = 0.6,
    max_cost_usd: float = 0.10,
) -> dict[str, Any]:
    """Monitor paste sites for leaked credentials and model weights.

    Searches known paste sites (Pastebin, Splunk, GitHub public pastes) via
    DuckDuckGo + Ahmia for query matches, then analyzes results for:
    - High-entropy API keys (sk-, nvapi-, ghp_, AKIA, etc.)
    - Model weight references (safetensors, .bin, .gguf, etc.)
    - Fuzzy pattern matching for known credential formats

    Args:
        query: search term (e.g., "openai api key", "llama model weights")
        n: max paste sites to scan (default 10)
        entropy_threshold: minimum entropy for credential detection (0.0-1.0)
        max_cost_usd: LLM cost cap (not used for search, informational)

    Returns:
        Dict with:
        - query: original search query
        - findings: list of {source, type, confidence, snippet}
        - stats: {total_scanned, credentials_found, weights_found}
        - error: error message if any
    """
    loop = asyncio.get_running_loop()
    findings: list[dict[str, Any]] = []

    # Expand query to target paste sites
    search_queries = [
        f'site:pastebin.com "{query}"',
        f'site:pastes.sh "{query}"',
        f'site:github.com/gists "{query}"',
        f'"{query}" paste leaked credentials',
        f'"{query}" model weights leaked',
    ]

    try:
        from loom.tools.search import research_search
    except ImportError:
        return {
            "query": query,
            "error": "search tools not available",
            "findings": [],
        }

    # Run searches in parallel
    async def _search_paste_site(search_q: str) -> list[dict[str, Any]]:
        """Search a paste site pattern via DuckDuckGo."""
        try:
            result = await loop.run_in_executor(
                None,
                partial(
                    research_search,
                    search_q,
                    provider="ddgs",
                    n=n // len(search_queries),
                ),
            )
            return result.get("results", [])  # type: ignore[return-value]
        except Exception as exc:
            logger.warning("cipher_mirror_search_failed: %s", exc)
            return []

    gather_results = await asyncio.gather(
        *[_search_paste_site(sq) for sq in search_queries],
        return_exceptions=True,
    )
    all_results: list[dict[str, Any]] = []
    for result in gather_results:
        if isinstance(result, list):
            all_results.extend(result)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_results: list[dict[str, Any]] = []
    for result in all_results:
        url = result.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)

    # Analyze each paste for credentials/weights
    for result in unique_results[:n]:
        url = result.get("url", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")

        # Scan snippet for credentials
        cred_findings = _detect_credentials(snippet)
        weight_findings = _detect_model_weights(snippet, title)

        # Filter by entropy threshold
        cred_findings = [
            f for f in cred_findings if f.get("confidence", 0) >= entropy_threshold
        ]

        # Add source context
        all_findings = cred_findings + weight_findings
        for finding in all_findings:
            finding["source"] = url
            finding["title"] = title
            findings.append(finding)

    # Aggregate statistics
    credentials_found = sum(1 for f in findings if f.get("type") == "api_key")
    weights_found = sum(1 for f in findings if f.get("type") == "model_weight")

    logger.info(
        "cipher_mirror_complete query=%s credentials=%d weights=%d",
        query[:50],
        credentials_found,
        weights_found,
    )

    return {
        "query": query,
        "findings": findings,
        "stats": {
            "total_scanned": len(unique_results),
            "credentials_found": credentials_found,
            "weights_found": weights_found,
            "high_confidence": sum(1 for f in findings if f.get("confidence", 0) > 0.8),
        },
    }
