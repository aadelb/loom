"""MCP tools for prompt compression and token optimization.

Provides tools for compressing prompts using LLMLingua 2 with extractive fallback,
enabling cost-effective LLM usage through semantic-preserving text reduction.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.prompt_compressor import estimate_tokens, get_compressor

logger = logging.getLogger("loom.tools.prompt_compression")


async def research_compress_prompt(
    text: str,
    target_ratio: float = 0.5,
) -> dict[str, Any]:
    """Compress prompt text to reduce token consumption while preserving meaning.

    Uses LLMLingua 2 for ML-based compression if available, falls back to
    extractive sentence scoring. Ideal for:
    - Long context passages before LLM processing
    - Reducing API costs for large-document analysis
    - Improving latency on token-constrained models

    Examples:
        Compress a 5000-token document to ~2500 tokens (50%):
        {
            "text": "Alice was born in 1990. She studied physics...",
            "target_ratio": 0.5
        }

        Aggressive compression to 30% of original size:
        {
            "text": "Long technical specification...",
            "target_ratio": 0.3
        }

    Args:
        text: Input text to compress (must be non-empty)
        target_ratio: Target compression ratio between 0.1 and 0.9
            - 0.5 = keep 50% of text (compress to ~50% original size)
            - 0.3 = keep 30% of text (compress to ~30% original size)
            - 0.7 = keep 70% of text (minimal compression, high fidelity)

    Returns:
        Dict with keys:
            - original_tokens: Estimated token count of input
            - compressed_tokens: Estimated token count of compressed output
            - ratio: Actual compression ratio achieved (output/input)
            - compressed_text: The compressed text
            - method: "llmlingua" or "extractive"
            - reduction_percent: Percentage of tokens saved (e.g., 50 = 50% reduction)

    Raises:
        ValueError: If text is empty or target_ratio is invalid
    """
    try:
        if not text or not isinstance(text, str):
            raise ValueError("text must be a non-empty string")

        if not 0.1 <= target_ratio <= 0.9:
            raise ValueError("target_ratio must be between 0.1 and 0.9")

        # Get compressor instance
        compressor = get_compressor(use_llmlingua=True)

        # Estimate original token count
        original_tokens = estimate_tokens(text)

        # Perform compression
        compressed_text = compressor.compress(text, target_ratio=target_ratio)

        # Estimate compressed token count
        compressed_tokens = estimate_tokens(compressed_text)

        # Update compressor stats
        compressor.stats.total_input_tokens += original_tokens
        compressor.stats.total_output_tokens += compressed_tokens

        # Calculate actual compression ratio
        actual_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 0

        # Calculate reduction percentage
        reduction_percent = int((1.0 - actual_ratio) * 100)

        logger.info(
            "compress_prompt orig_tokens=%d comp_tokens=%d reduction=%d%% method=%s",
            original_tokens,
            compressed_tokens,
            reduction_percent,
            compressor.get_stats()["method"],
        )

        return {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "ratio": round(actual_ratio, 3),
            "compressed_text": compressed_text,
            "method": compressor.get_stats()["method"],
            "reduction_percent": reduction_percent,
        }
    except Exception as exc:
        logger.exception("Error in research_compress_prompt")
        return {
            "error": str(exc),
            "tool": "research_compress_prompt",
            "original_tokens": None,
            "compressed_tokens": None,
            "compressed_text": None,
            "ratio": None,
            "method": None,
            "reduction_percent": None,
        }


async def research_compression_stats() -> dict[str, Any]:
    """Get cumulative compression statistics and performance metrics.

    Returns statistics from all compression operations performed in the
    current session, useful for monitoring cost savings and method effectiveness.

    Returns:
        Dict with keys:
            - compressions_done: Number of compressions performed
            - avg_ratio: Average compression ratio (0-1)
            - tokens_saved: Estimated total tokens saved
            - total_input_tokens: Total input tokens processed
            - total_output_tokens: Total output tokens after compression
            - method: "llmlingua" or "extractive"
            - ratios: Last 10 compression ratios achieved
            - compression_cost_estimate: Estimated USD saved (rough estimate)

    Example:
        If 100,000 input tokens compressed to 50,000 output tokens with avg
        provider cost of $0.50/1M input tokens, estimated savings ~$0.025.
    """
    try:
        compressor = get_compressor()
        stats = compressor.get_stats()

        # Rough cost estimation (assuming average provider at $0.50/1M tokens)
        # and average output cost at $1.50/1M tokens
        tokens_input_cost = stats["total_input_tokens"] * (0.50 / 1_000_000)
        tokens_output_cost = stats["total_output_tokens"] * (1.50 / 1_000_000)
        total_input_cost = tokens_input_cost + tokens_output_cost

        saved_tokens_cost = stats["tokens_saved"] * (0.50 / 1_000_000)

        stats["compression_cost_estimate_usd"] = round(saved_tokens_cost, 6)
        stats["total_cost_estimate_usd"] = round(total_input_cost, 6)

        logger.info(
            "compression_stats compressions=%d avg_ratio=%.3f tokens_saved=%d method=%s",
            stats["compressions_done"],
            stats["avg_ratio"],
            stats["tokens_saved"],
            stats["method"],
        )

        return stats
    except Exception as exc:
        logger.exception("Error in research_compression_stats")
        return {
            "error": str(exc),
            "tool": "research_compression_stats",
        }


async def research_compression_reset() -> dict[str, str]:
    """Reset cumulative compression statistics.

    Clears all tracked compression history and metrics. Useful when starting
    a new analysis phase or for benchmarking specific operations.

    Returns:
        Dict confirming reset: {"status": "stats_reset", "message": "..."}
    """
    try:
        compressor = get_compressor()
        compressor.reset_stats()

        logger.info("compression_stats_reset")

        return {
            "status": "stats_reset",
            "message": "Compression statistics cleared",
        }
    except Exception as exc:
        logger.exception("Error in research_compression_reset")
        return {
            "error": str(exc),
            "tool": "research_compression_reset",
        }
