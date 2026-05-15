"""Prompt compression using LLMLingua 2 with fallback to extractive compression.

Provides token-efficient prompt compression for LLM inputs, reducing costs while
maintaining semantic relevance. Supports both ML-based (LLMLingua) and extractive
fallback approaches.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("loom.prompt_compressor")

# Try to import LLMLingua for ML-based compression
try:
    from llmlingua import PromptCompressor as LLMCompressor

    HAS_LLMLINGUA = True
except ImportError:
    HAS_LLMLINGUA = False
    logger.info("LLMLingua not installed; using fallback extractive compression")


@dataclass
class CompressionStats:
    """Statistics from compression operations."""

    compressions_done: int = 0
    avg_ratio: float = 0.0
    tokens_saved: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def _ratios(self) -> list[float]:
        """Get list of compression ratios from tracked compressions."""
        return []


class PromptCompressor:
    """Compress prompts using LLMLingua 2 with extractive fallback.

    Supports two modes:
    1. ML-based (LLMLingua) - ~40-60% compression with semantic preservation
    2. Extractive fallback - ~30-40% compression using heuristic sentence scoring

    Attributes:
        use_llmlingua: Use LLMLingua if available, else use extractive
        stats: Cumulative compression statistics
    """

    def __init__(self, use_llmlingua: bool = True) -> None:
        """Initialize compressor.

        Args:
            use_llmlingua: Prefer LLMLingua if available (default True)
        """
        self.use_llmlingua = use_llmlingua and HAS_LLMLINGUA
        self._llm_compressor: LLMCompressor | None = None
        self.stats = CompressionStats()
        self._compression_ratios: list[float] = []

        if self.use_llmlingua:
            try:
                self._llm_compressor = LLMCompressor(model_name="gpt2")
                logger.info("LLMLingua initialized for prompt compression")
            except Exception as e:
                logger.warning("Failed to initialize LLMLingua: %s; using fallback", e)
                self.use_llmlingua = False

    def compress(self, text: str, target_ratio: float = 0.5) -> str:
        """Compress text to target ratio while preserving semantic meaning.

        Args:
            text: Input text to compress
            target_ratio: Target compression ratio (0.1-0.9)
                0.5 = keep 50% of text, compress to ~50% size

        Returns:
            Compressed text

        Raises:
            ValueError: If target_ratio not in valid range
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        if not 0.1 <= target_ratio <= 0.9:
            raise ValueError("target_ratio must be between 0.1 and 0.9")

        # Short text - no compression needed
        if len(text) < 200:
            return text

        if self.use_llmlingua and self._llm_compressor:
            return self._compress_llmlingua(text, target_ratio)
        else:
            return self._compress_extractive(text, target_ratio)

    def _compress_llmlingua(self, text: str, target_ratio: float) -> str:
        """Compress using LLMLingua 2.

        Args:
            text: Input text
            target_ratio: Target compression ratio

        Returns:
            Compressed text
        """
        try:
            # LLMLingua expects a context and instruction
            # We use the full text as context
            compressed = self._llm_compressor.compress_prompt(
                context=text,
                instruction="",
                compress_ratio=target_ratio,
                target_tokens=None,
            )

            # Track compression
            orig_length = len(text)
            comp_length = len(compressed)
            actual_ratio = comp_length / orig_length if orig_length > 0 else 0
            self._compression_ratios.append(actual_ratio)

            logger.info(
                "llmlingua_compress orig=%d comp=%d ratio=%.2f",
                orig_length,
                comp_length,
                actual_ratio,
            )

            return compressed
        except Exception as e:
            logger.warning("LLMLingua compression failed: %s; falling back", e)
            return self._compress_extractive(text, target_ratio)

    def _compress_extractive(self, text: str, target_ratio: float) -> str:
        """Compress using extractive heuristics (no ML).

        Splits text into sentences and scores each by:
        - Word count (longer sentences weighted more)
        - Keyword density (sentences with key terms)
        - Position (first/last sentences in paragraphs weighted higher)

        Args:
            text: Input text
            target_ratio: Target compression ratio

        Returns:
            Compressed text with ~target_ratio of original content
        """
        sentences = self._split_sentences(text)

        if len(sentences) <= 1:
            return text

        # Score each sentence
        scores = self._score_sentences(sentences)

        # Keep top ratio% of sentences
        keep_count = max(1, int(len(sentences) * target_ratio))
        keep_count = min(keep_count, len(sentences))

        # Get indices of top sentences (maintain order)
        top_indices = sorted(
            sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[
                :keep_count
            ]
        )

        # Reconstruct text preserving original order
        compressed = " ".join(sentences[i] for i in top_indices)

        # Track compression
        orig_length = len(text)
        comp_length = len(compressed)
        actual_ratio = comp_length / orig_length if orig_length > 0 else 0
        self._compression_ratios.append(actual_ratio)

        logger.info(
            "extractive_compress orig_sents=%d kept=%d ratio=%.2f",
            len(sentences),
            keep_count,
            actual_ratio,
        )

        return compressed

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences preserving structure.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Basic sentence splitting on . ! ? followed by space
        # Preserve sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _score_sentences(self, sentences: list[str]) -> list[float]:
        """Score sentences by informativeness.

        Scoring factors:
        - Word count: longer sentences weighted higher (avg 15 words per sentence)
        - Keyword density: sentences with numbers/capitals scored higher
        - Position: first and last sentences in text weighted 1.5x

        Args:
            sentences: List of sentences to score

        Returns:
            List of scores (0-1 range) in sentence order
        """
        scores = []

        for i, sentence in enumerate(sentences):
            word_count = len(sentence.split())

            # Word count score (0-1): normalized to ~15 words average
            word_score = min(1.0, word_count / 20.0)

            # Keyword density: uppercase letters, digits (indicators of entities/numbers)
            uppercase_ratio = sum(1 for c in sentence if c.isupper()) / len(
                sentence
            ) if sentence else 0
            digit_ratio = sum(1 for c in sentence if c.isdigit()) / len(
                sentence
            ) if sentence else 0
            keyword_score = min(1.0, (uppercase_ratio + digit_ratio) * 2)

            # Position score: first and last sentences weighted higher
            position_score = 1.0
            if i == 0 or i == len(sentences) - 1:
                position_score = 1.5
            elif i == 1 or i == len(sentences) - 2:
                position_score = 1.2

            # Combined score
            combined = (word_score * 0.4) + (keyword_score * 0.3) + (position_score * 0.3)
            scores.append(min(1.0, combined))

        return scores

    def get_stats(self) -> dict[str, Any]:
        """Get cumulative compression statistics.

        Returns:
            Dict with:
            - compressions_done: Number of compressions performed
            - avg_ratio: Average compression ratio across all compressions
            - tokens_saved: Estimated tokens saved
            - total_input_tokens: Total input tokens processed
            - total_output_tokens: Total output tokens after compression
            - method: "llmlingua" or "extractive"
        """
        avg_ratio = 0.0
        if self._compression_ratios:
            avg_ratio = sum(self._compression_ratios) / len(self._compression_ratios)

        # Estimate tokens saved (rough estimate: 1 token per 4 characters)
        estimated_tokens_saved = int(
            self.stats.total_input_tokens * (1.0 - avg_ratio)
        )

        return {
            "compressions_done": len(self._compression_ratios),
            "avg_ratio": round(avg_ratio, 3),
            "tokens_saved": estimated_tokens_saved,
            "total_input_tokens": self.stats.total_input_tokens,
            "total_output_tokens": self.stats.total_output_tokens,
            "method": "llmlingua" if self.use_llmlingua else "extractive",
            "ratios": [round(r, 3) for r in self._compression_ratios[-10:]],  # Last 10
        }

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.stats = CompressionStats()
        self._compression_ratios = []


# Global singleton instance
_COMPRESSOR: PromptCompressor | None = None


def get_compressor(use_llmlingua: bool = True) -> PromptCompressor:
    """Get or create the global compressor instance.

    Args:
        use_llmlingua: Prefer LLMLingua if available

    Returns:
        PromptCompressor singleton
    """
    global _COMPRESSOR

    if _COMPRESSOR is None:
        _COMPRESSOR = PromptCompressor(use_llmlingua=use_llmlingua)

    return _COMPRESSOR


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count.

    Uses simple heuristic: 1 token per 4 characters on average.
    For precise counts, use provider's tokenizer.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    return max(1, len(text) // 4)
