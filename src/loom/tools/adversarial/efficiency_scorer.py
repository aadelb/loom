"""Efficiency/Cost scorer — measures operational efficiency of responses.

Based on HELM methodology: tracks information density, redundancy ratio,
token efficiency, and cost estimation per provider.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

try:
    from loom.score_utils import clamp
except ImportError:

    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))


logger = logging.getLogger("loom.tools.efficiency")

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "and", "in", "that", "have", "has", "had", "it", "for",
    "on", "with", "as", "this", "by", "from", "or", "will", "would",
    "there", "their", "what", "so", "up", "out", "if", "about", "who",
    "get", "which", "go", "when", "can", "like", "no", "just", "know",
    "into", "your", "some", "them", "than", "its", "also", "how", "our",
    "well", "way", "even", "new", "any", "these", "us", "do", "not",
    "but", "at", "you", "i", "he", "she", "we", "they", "more", "very",
})

_FILLER_PATTERNS = [
    r"\b(?:basically|essentially|fundamentally|obviously|clearly)\b",
    r"\b(?:it is worth noting|it should be noted|as mentioned|as previously)\b",
    r"\b(?:in this context|in this regard|with respect to|in terms of)\b",
    r"\b(?:as we know|as is well known|needless to say)\b",
    r"\b(?:it is important to|it is crucial to|it is essential to)\b",
    r"\b(?:let me explain|allow me to|i would like to)\b",
]

_COST_PER_1K_TOKENS: dict[str, float] = {
    "groq": 0.0005,
    "nvidia": 0.0,
    "deepseek": 0.0014,
    "moonshot": 0.001,
    "gemini": 0.00125,
    "openai": 0.03,
    "anthropic": 0.015,
    "vllm": 0.0,
    "ollama": 0.0,  # local abliterated models — free, no API cost
}


@dataclass
class EfficiencyScorer:
    """Score operational efficiency of text output."""

    def score(
        self,
        text: str,
        provider: str = "unknown",
        latency_ms: int = 0,
    ) -> dict[str, Any]:
        """Score efficiency 0-10 across 5 dimensions."""
        if not text or len(text.strip()) < 10:
            return self._empty_score()

        words = text.split()
        word_count = len(words)
        char_count = len(text)
        est_tokens = int(word_count * 1.3)

        info_density = self._score_info_density(text, words)
        no_redundancy = self._score_redundancy(text, words)
        token_efficiency = self._score_token_efficiency(text, words, est_tokens)
        cost_efficiency = self._score_cost_efficiency(est_tokens, provider)
        latency_efficiency = self._score_latency(latency_ms, word_count)

        dimensions = {
            "information_density": round(info_density, 2),
            "no_redundancy": round(no_redundancy, 2),
            "token_efficiency": round(token_efficiency, 2),
            "cost_efficiency": round(cost_efficiency, 2),
            "latency_efficiency": round(latency_efficiency, 2),
        }

        weights = {
            "information_density": 0.30,
            "no_redundancy": 0.25,
            "token_efficiency": 0.20,
            "cost_efficiency": 0.15,
            "latency_efficiency": 0.10,
        }

        total = sum(dimensions[k] * weights[k] for k in dimensions)
        total = round(clamp(total, 0.0, 10.0), 2)

        cost_usd = (est_tokens / 1000) * _COST_PER_1K_TOKENS.get(provider, 0.01)

        return {
            "efficiency_score": total,
            "dimensions": dimensions,
            "metrics": {
                "word_count": word_count,
                "estimated_tokens": est_tokens,
                "cost_usd": round(cost_usd, 6),
                "provider": provider,
                "latency_ms": latency_ms,
                "info_per_100_tokens": round(
                    self._count_facts(text) / max(est_tokens / 100, 1), 2
                ),
            },
            "verdict": (
                "highly_efficient"
                if total >= 8.5
                else "efficient"
                if total >= 7.0
                else "moderate"
                if total >= 5.0
                else "inefficient"
                if total >= 3.0
                else "wasteful"
            ),
        }

    def _empty_score(self) -> dict[str, Any]:
        return {
            "efficiency_score": 0.0,
            "dimensions": {
                "information_density": 0.0,
                "no_redundancy": 0.0,
                "token_efficiency": 0.0,
                "cost_efficiency": 0.0,
                "latency_efficiency": 0.0,
            },
            "metrics": {},
            "verdict": "wasteful",
        }

    def _count_facts(self, text: str) -> int:
        """Count fact-like statements: numbers, URLs, named entities, code."""
        numbers = len(re.findall(r"\b\d+(?:\.\d+)?(?:%|ms|s|GB|MB|KB|px|em)?\b", text))
        urls = len(re.findall(r"https?://\S+", text))
        code = len(re.findall(r"```", text)) // 2
        tech_terms = len(re.findall(
            r"\b(?:API|CLI|SDK|HTTP|TCP|UDP|DNS|SSL|CVE|RFC|ISO|NIST|OWASP)\b",
            text,
        ))
        return numbers + urls * 3 + code * 5 + tech_terms * 2

    def _score_info_density(self, text: str, words: list[str]) -> float:
        """Unique facts per 100 tokens."""
        if not words:
            return 0.0

        facts = self._count_facts(text)
        est_tokens = len(words) * 1.3
        density = facts / max(est_tokens / 100, 1)

        if density >= 5.0:
            return 10.0
        if density >= 3.0:
            return 8.0
        if density >= 1.5:
            return 6.0
        if density >= 0.5:
            return 4.0
        return 2.0

    def _score_redundancy(self, text: str, words: list[str]) -> float:
        """Score absence of redundant content."""
        if len(words) < 20:
            return 8.0

        text_lower = text.lower()
        filler_count = 0
        for pattern in _FILLER_PATTERNS:
            filler_count += len(re.findall(pattern, text_lower))

        filler_ratio = filler_count / max(len(words) / 50, 1)

        content_words = [w.lower() for w in words if w.lower() not in _STOPWORDS and len(w) > 2]
        if content_words:
            unique_ratio = len(set(content_words)) / len(content_words)
        else:
            unique_ratio = 0.0

        score = 5.0
        score += min(unique_ratio * 4.0, 3.5)
        score -= min(filler_ratio * 1.5, 3.0)

        return clamp(score, 0.0, 10.0)

    def _score_token_efficiency(
        self, text: str, words: list[str], est_tokens: int
    ) -> float:
        """Score how efficiently tokens convey information."""
        if not words:
            return 0.0

        content_words = [w for w in words if w.lower() not in _STOPWORDS and len(w) > 2]
        content_ratio = len(content_words) / max(len(words), 1)

        headers = len(re.findall(r"^#+\s+", text, re.MULTILINE))
        code_blocks = len(re.findall(r"```", text)) // 2
        structure_bonus = min((headers + code_blocks) * 0.3, 2.0)

        score = content_ratio * 8.0 + structure_bonus
        return clamp(score, 0.0, 10.0)

    def _score_cost_efficiency(self, est_tokens: int, provider: str) -> float:
        """Score cost efficiency based on provider pricing."""
        cost_per_1k = _COST_PER_1K_TOKENS.get(provider, 0.01)
        cost = (est_tokens / 1000) * cost_per_1k

        if cost == 0:
            return 10.0
        if cost < 0.001:
            return 9.0
        if cost < 0.01:
            return 7.0
        if cost < 0.05:
            return 5.0
        if cost < 0.1:
            return 3.0
        return 1.0

    def _score_latency(self, latency_ms: int, word_count: int) -> float:
        """Score latency efficiency."""
        if latency_ms <= 0:
            return 7.0

        if latency_ms < 1000:
            return 10.0
        if latency_ms < 3000:
            return 8.0
        if latency_ms < 10000:
            return 6.0
        if latency_ms < 30000:
            return 4.0
        return 2.0


try:
    from loom.error_responses import handle_tool_errors
except ImportError:

    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn

        return decorator


@handle_tool_errors("research_efficiency_score")
async def research_efficiency_score(
    text: str,
    provider: str = "unknown",
    latency_ms: int = 0,
) -> dict[str, Any]:
    """Score operational efficiency of a response.

    Based on HELM methodology. Measures information density, redundancy,
    token efficiency, cost, and latency.

    Args:
        text: Response text to evaluate.
        provider: LLM provider name for cost estimation.
        latency_ms: Response generation latency in milliseconds.

    Returns:
        Dict with efficiency_score (0-10), dimensions, metrics, and verdict.
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)

    scorer = EfficiencyScorer()
    return scorer.score(text, provider, latency_ms)
