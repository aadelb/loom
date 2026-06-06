"""Answer Relevancy scorer — measures how well a response addresses the query.

Based on RAGAS methodology: penalizes incomplete, redundant, or off-topic answers.
Uses keyword extraction + structural analysis (no embedding model required).

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from loom.scoring_framework import Dimension, score_text, weighted_aggregate

try:
    from loom.score_utils import clamp
except ImportError:

    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))


logger = logging.getLogger("loom.tools.answer_relevancy")

_QUERY_COVERAGE_DIM = Dimension(
    name="query_coverage",
    keywords=frozenset(),
    weight=0.35,
    description="Does the response address all key aspects of the query?",
)

_INFORMATION_DENSITY_DIM = Dimension(
    name="information_density",
    keywords=frozenset({
        "specifically", "namely", "for example", "for instance", "such as",
        "including", "e.g.", "i.e.", "in particular", "precisely",
        "exactly", "detailed", "comprehensive", "thorough", "complete",
        "exhaustive", "in-depth", "extensive", "elaborate", "granular",
    }),
    weight=0.20,
    description="Density of relevant information vs filler content",
)

_NO_REDUNDANCY_DIM = Dimension(
    name="no_redundancy",
    keywords=frozenset(),
    weight=0.20,
    description="Absence of repeated or circular content",
)

_TOPICAL_FOCUS_DIM = Dimension(
    name="topical_focus",
    keywords=frozenset(),
    weight=0.15,
    description="Response stays on-topic without irrelevant tangents",
)

_DIRECTNESS_DIM = Dimension(
    name="directness",
    keywords=frozenset({
        "the answer is", "in summary", "to answer your question",
        "the solution is", "the result is", "therefore",
        "in short", "bottom line", "key takeaway", "conclusion",
    }),
    weight=0.10,
    description="Response directly answers the question without excessive preamble",
)

_ALL_DIMENSIONS = [
    _QUERY_COVERAGE_DIM,
    _INFORMATION_DENSITY_DIM,
    _NO_REDUNDANCY_DIM,
    _TOPICAL_FOCUS_DIM,
    _DIRECTNESS_DIM,
]

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "and", "in", "that", "have", "has", "had", "it", "for",
    "on", "with", "as", "this", "by", "from", "they", "we", "or", "will",
    "my", "one", "all", "would", "there", "their", "what", "so", "up",
    "out", "if", "about", "who", "get", "which", "go", "me", "when",
    "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "into", "year", "your", "some", "could", "them", "see", "other",
    "than", "now", "look", "only", "come", "its", "over", "think",
    "also", "back", "after", "use", "two", "how", "our", "work",
    "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "do", "does", "did", "not", "but",
    "at", "you", "i", "he", "she", "we", "they", "more", "very",
    "much", "many", "such", "here", "where", "why", "how", "what",
})

_FILLER_PATTERNS = [
    r"\b(basically|essentially|fundamentally|obviously|clearly)\b",
    r"\b(it is worth noting|it should be noted|as mentioned)\b",
    r"\b(in this context|in this regard|with respect to)\b",
    r"\b(as we know|as you know|as is well known)\b",
    r"\b(needless to say|goes without saying)\b",
    r"\b(it is important to|it is crucial to|it is essential to)\b",
]

_PREAMBLE_PATTERNS = [
    r"^(great question|that's a great question|interesting question)",
    r"^(sure|of course|certainly|absolutely|happy to help)",
    r"^(let me|allow me|i'd be happy to|i'll)",
    r"^(thank you for|thanks for asking)",
]


def _extract_query_terms(query: str) -> set[str]:
    """Extract meaningful terms from a query, removing stopwords."""
    words = re.findall(r"\b[a-z][a-z0-9_.-]+\b", query.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _extract_query_phrases(query: str) -> list[str]:
    """Extract multi-word phrases from query (2-3 word ngrams)."""
    words = re.findall(r"\b[a-z][a-z0-9_.-]+\b", query.lower())
    words = [w for w in words if w not in _STOPWORDS and len(w) > 2]
    phrases = []
    for i in range(len(words) - 1):
        phrases.append(f"{words[i]} {words[i + 1]}")
    for i in range(len(words) - 2):
        phrases.append(f"{words[i]} {words[i + 1]} {words[i + 2]}")
    return phrases


def _compute_sentence_similarity(s1: str, s2: str) -> float:
    """Jaccard similarity between two sentences (word-level)."""
    w1 = set(s1.lower().split()) - _STOPWORDS
    w2 = set(s2.lower().split()) - _STOPWORDS
    if not w1 or not w2:
        return 0.0
    intersection = w1 & w2
    union = w1 | w2
    return len(intersection) / len(union) if union else 0.0


@dataclass
class AnswerRelevancyScorer:
    """Score answer relevancy using RAGAS-inspired methodology."""

    dimensions: list[Dimension] = field(default_factory=lambda: list(_ALL_DIMENSIONS))

    def score(self, response: str, query: str) -> dict[str, Any]:
        """Score answer relevancy 0-10 across 5 dimensions."""
        if not response or len(response.strip()) < 20:
            return self._empty_score("empty_response")
        if not query or len(query.strip()) < 3:
            return self._empty_score("empty_query")

        response_lower = response.lower()
        query_terms = _extract_query_terms(query)
        query_phrases = _extract_query_phrases(query)

        query_coverage = self._score_query_coverage(response_lower, query_terms, query_phrases)
        info_density = self._score_information_density(response, response_lower)
        no_redundancy = self._score_no_redundancy(response)
        topical_focus = self._score_topical_focus(response_lower, query_terms)
        directness = self._score_directness(response, response_lower)

        dimensions = {
            "query_coverage": round(query_coverage, 2),
            "information_density": round(info_density, 2),
            "no_redundancy": round(no_redundancy, 2),
            "topical_focus": round(topical_focus, 2),
            "directness": round(directness, 2),
        }

        weights = {d.name: d.weight for d in self.dimensions}
        total = sum(dimensions[k] * weights.get(k, 0.2) for k in dimensions)
        total = round(clamp(total, 0.0, 10.0), 2)

        verdict = (
            "highly_relevant"
            if total >= 8.5
            else "relevant"
            if total >= 7.0
            else "partially_relevant"
            if total >= 5.0
            else "weakly_relevant"
            if total >= 3.0
            else "irrelevant"
        )

        return {
            "answer_relevancy": total,
            "dimensions": dimensions,
            "verdict": verdict,
            "query_terms_found": len(query_terms & set(response_lower.split())),
            "query_terms_total": len(query_terms),
        }

    def _empty_score(self, reason: str) -> dict[str, Any]:
        return {
            "answer_relevancy": 0.0,
            "dimensions": {
                "query_coverage": 0.0,
                "information_density": 0.0,
                "no_redundancy": 0.0,
                "topical_focus": 0.0,
                "directness": 0.0,
            },
            "verdict": reason,
            "query_terms_found": 0,
            "query_terms_total": 0,
        }

    def _score_query_coverage(
        self,
        response_lower: str,
        query_terms: set[str],
        query_phrases: list[str],
    ) -> float:
        """How many query terms/phrases appear in the response?"""
        if not query_terms:
            return 5.0

        term_hits = sum(1 for t in query_terms if t in response_lower)
        term_ratio = term_hits / len(query_terms)

        phrase_hits = sum(1 for p in query_phrases if p in response_lower) if query_phrases else 0
        phrase_ratio = phrase_hits / len(query_phrases) if query_phrases else 0.0

        coverage = (term_ratio * 0.6) + (phrase_ratio * 0.4)
        score = coverage * 10.0

        question_words = {"what", "how", "why", "when", "where", "which", "who"}
        response_sentences = re.split(r"[.!?]+", response_lower)
        if any(w in response_lower for w in question_words):
            if len(response_sentences) >= 3:
                score += 0.5

        return clamp(score, 0.0, 10.0)

    def _score_information_density(self, response: str, response_lower: str) -> float:
        """Ratio of substantive content to filler."""
        words = response_lower.split()
        if not words:
            return 0.0

        filler_count = 0
        for pattern in _FILLER_PATTERNS:
            filler_count += len(re.findall(pattern, response_lower))

        filler_ratio = filler_count / max(len(words) / 10, 1)

        numbers = len(re.findall(r"\b\d+(?:\.\d+)?\b", response))
        urls = len(re.findall(r"https?://\S+", response))
        code_blocks = len(re.findall(r"```", response)) // 2
        technical_terms = len(re.findall(
            r"\b(?:API|CLI|SDK|HTTP|TCP|UDP|DNS|SSL|TLS|SSH|JWT|OAuth|"
            r"RBAC|CORS|CSRF|XSS|SQL|NoSQL|REST|gRPC|WebSocket|CDN|"
            r"CVE-\d{4}-\d+|RFC\s*\d+|ISO\s*\d+|NIST|OWASP|MITRE)\b",
            response,
        ))

        density_markers = numbers + urls * 3 + code_blocks * 5 + technical_terms * 2
        density_per_100 = density_markers / max(len(words) / 100, 1)

        base = 5.0
        base += min(density_per_100 * 1.5, 3.5)
        base -= min(filler_ratio * 2.0, 3.0)

        content_words = [w for w in words if w not in _STOPWORDS and len(w) > 2]
        content_ratio = len(content_words) / max(len(words), 1)
        if content_ratio > 0.4:
            base += 1.0

        return clamp(base, 0.0, 10.0)

    def _score_no_redundancy(self, response: str) -> float:
        """Detect repeated sentences, circular arguments, or copy-paste."""
        sentences = [s.strip() for s in re.split(r"[.!?]+", response) if len(s.strip()) > 20]
        if len(sentences) < 2:
            return 8.0

        score = 10.0
        seen_sentences = set()
        duplicate_count = 0

        for s in sentences:
            normalized = re.sub(r"\s+", " ", s.lower().strip())
            if normalized in seen_sentences:
                duplicate_count += 1
            seen_sentences.add(normalized)

        score -= duplicate_count * 2.0

        high_sim_count = 0
        sample = sentences[:30]
        for i in range(len(sample)):
            for j in range(i + 1, len(sample)):
                sim = _compute_sentence_similarity(sample[i], sample[j])
                if sim > 0.7:
                    high_sim_count += 1

        score -= min(high_sim_count * 0.5, 4.0)

        paragraphs = [p.strip() for p in response.split("\n\n") if p.strip()]
        if len(paragraphs) >= 2:
            first_words = [p.split()[:5] for p in paragraphs if len(p.split()) >= 5]
            repeated_starts = 0
            for i in range(len(first_words)):
                for j in range(i + 1, len(first_words)):
                    if first_words[i] == first_words[j]:
                        repeated_starts += 1
            score -= repeated_starts * 1.5

        return clamp(score, 0.0, 10.0)

    def _score_topical_focus(self, response_lower: str, query_terms: set[str]) -> float:
        """Does the response stay on-topic or wander?"""
        if not query_terms:
            return 7.0

        paragraphs = [p.strip() for p in response_lower.split("\n\n") if p.strip()]
        if not paragraphs:
            return 5.0

        on_topic_paragraphs = 0
        for para in paragraphs:
            para_words = set(para.split())
            overlap = len(query_terms & para_words)
            if overlap >= 1:
                on_topic_paragraphs += 1

        on_topic_ratio = on_topic_paragraphs / len(paragraphs)
        score = on_topic_ratio * 10.0

        disclaimer_patterns = [
            r"\b(disclaimer|note:|warning:|caution:|important:)\b",
            r"\b(i cannot|i can't|i'm unable|i am unable)\b",
            r"\b(as an ai|as a language model|i don't have access)\b",
        ]
        disclaimer_count = sum(
            len(re.findall(p, response_lower)) for p in disclaimer_patterns
        )
        score -= min(disclaimer_count * 1.0, 3.0)

        return clamp(score, 0.0, 10.0)

    def _score_directness(self, response: str, response_lower: str) -> float:
        """Does the response answer the question directly?"""
        score = 7.0

        first_200 = response_lower[:200]
        preamble_count = sum(
            1 for p in _PREAMBLE_PATTERNS if re.search(p, first_200)
        )
        score -= preamble_count * 1.5

        lines = response.strip().split("\n")
        if lines and (lines[0].startswith("#") or re.match(r"^\d+\.", lines[0])):
            score += 1.0

        headers = len(re.findall(r"^#+\s+", response, re.MULTILINE))
        if headers >= 2:
            score += 1.5

        if len(response) > 200:
            first_20pct = response_lower[: len(response_lower) // 5]
            direct_markers = ["the answer", "solution", "result", "approach", "method"]
            if any(m in first_20pct for m in direct_markers):
                score += 0.5

        return clamp(score, 0.0, 10.0)


try:
    from loom.error_responses import handle_tool_errors
except ImportError:

    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn

        return decorator


@handle_tool_errors("research_answer_relevancy")
async def research_answer_relevancy(
    response_text: str,
    query: str = "",
) -> dict[str, Any]:
    """Score answer relevancy — how well the response addresses the query.

    Based on RAGAS methodology: penalizes incomplete, redundant, or off-topic answers.

    Args:
        response_text: The response to evaluate.
        query: The original query/question the response should address.

    Returns:
        Dict with answer_relevancy (0-10), dimensions, verdict, and term coverage.
    """
    if isinstance(response_text, list):
        response_text = " ".join(str(x) for x in response_text)
    if isinstance(response_text, dict):
        response_text = str(response_text)
    if isinstance(query, list):
        query = " ".join(str(x) for x in query)

    scorer = AnswerRelevancyScorer()
    return scorer.score(response_text, query)
