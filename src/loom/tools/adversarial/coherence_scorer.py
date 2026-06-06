"""Coherence scorer — measure logical flow and consistency of prompts/responses."""
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

logger = logging.getLogger("loom.tools.coherence")

_LOGICAL_FLOW_DIM = Dimension(
    name="logical_flow",
    keywords=frozenset({
        "therefore", "thus", "hence", "consequently", "because", "since",
        "given that", "as a result", "for this reason", "it follows that",
        "if", "then", "provided that", "assuming", "implies", "entails",
        "so", "accordingly", "as such", "in conclusion", "to conclude",
        "enable", "disable", "cause", "result in", "lead to", "requires",
        "prerequisite", "dependency", "which allows", "this enables",
        "configured to", "set up to", "designed for", "used for",
    }),
    weight=0.35,
    description="Do premises lead to conclusions without gaps?",
)

_ARGUMENT_STRUCTURE_DIM = Dimension(
    name="argument_structure",
    keywords=frozenset({
        "first", "second", "third", "finally", "next", "then", "subsequently",
        "moreover", "furthermore", "additionally", "on the other hand",
        "however", "nevertheless", "conversely", "in contrast", "whereas",
        "for example", "for instance", "specifically", "namely", "i.e.",
        "evidence", "studies show", "research indicates", "data suggests",
        "claim", "argue", "assert", "contend", "maintain", "position",
        "step", "phase", "stage", "process", "procedure", "workflow",
        "begin", "start", "execute", "run", "deploy", "implement",
    }),
    weight=0.25,
    description="Presence of claims, evidence, and reasoning structure",
)

_INTERNAL_CONSISTENCY_DIM = Dimension(
    name="internal_consistency",
    keywords=frozenset({
        "consistent", "uniform", "coherent", "aligned", "matches",
        "same", "identical", "equivalent", "likewise", "similarly",
    }),
    weight=0.25,
    description="Absence of contradictions or self-undermining claims",
)

_TEMPORAL_COHERENCE_DIM = Dimension(
    name="temporal_coherence",
    keywords=frozenset({
        "before", "after", "then", "next", "finally", "first", "second",
        "third", "last", "previously", "subsequently", "concurrently",
        "meanwhile", "during", "while", "until", "once", "when",
        "initially", "eventually", "ultimately", "at the same time",
        "stage", "phase", "step", "sequence", "order", "follow",
    }),
    weight=0.15,
    description="Events/steps ordered logically in time",
)

_ALL_DIMENSIONS = [
    _LOGICAL_FLOW_DIM,
    _ARGUMENT_STRUCTURE_DIM,
    _INTERNAL_CONSISTENCY_DIM,
    _TEMPORAL_COHERENCE_DIM,
]

_CONTRADICTION_PATTERNS: list[tuple[str, float]] = [
    (r"\bbut\b.+?\b(however|although|though|yet|nevertheless)\b", 2.0),
    (r"\b(not|never|no)\b.+?\b(is|are|was|were|will|can|should)\b.+?\b(also|indeed|certainly)\b", 1.5),
    (r"\b(all|every|always)\b.+?\b(some|few|sometimes|never)\b", 2.0),
    (r"\b(must|should|required)\b.+?\b(optional|choice|can|may|might)\b", 1.5),
    (r"\b(definitely|certainly|absolutely)\b.+?\b(perhaps|maybe|possibly|uncertain)\b", 1.5),
]

_DISFLUENCY_MARKERS = {
    "um", "uh", "like", "you know", "sort of", "kind of", "basically",
    "literally", "actually", "honestly", "so yeah", "i mean",
}

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "to", "of", "and", "in", "that", "have", "it", "for", "on",
    "with", "as", "this", "by", "from", "they", "we", "say", "her",
    "she", "or", "will", "my", "one", "all", "would", "there",
    "their", "what", "so", "up", "out", "if", "about", "who", "get",
    "which", "go", "me", "when", "make", "can", "like", "time", "no",
    "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first",
    "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us",
}


@dataclass
class CoherenceScorer:
    """Score logical coherence of text using the scoring_framework pattern."""

    dimensions: list[Dimension] = field(default_factory=lambda: list(_ALL_DIMENSIONS))
    contradiction_patterns: list[tuple[str, float]] = field(
        default_factory=lambda: list(_CONTRADICTION_PATTERNS)
    )

    def score(self, text: str) -> dict[str, Any]:
        """Score coherence 0-10 across 4 dimensions."""
        if not text or len(text.strip()) < 20:
            return self._empty_score()

        text_without_code = self._strip_code_blocks(text)
        sentences = self._split_sentences(text_without_code)
        if len(sentences) < 2:
            return self._empty_score()

        base_scores = score_text(text, self.dimensions)

        logical_flow = self._refine_logical_flow(base_scores["logical_flow"], text, sentences)
        argument_structure = self._refine_argument_structure(
            base_scores["argument_structure"], text, sentences
        )
        internal_consistency = self._refine_internal_consistency(
            base_scores["internal_consistency"], text, sentences
        )
        temporal_coherence = self._refine_temporal_coherence(
            base_scores["temporal_coherence"], text, sentences
        )

        dimensions = {
            "logical_flow": round(logical_flow, 2),
            "argument_structure": round(argument_structure, 2),
            "internal_consistency": round(internal_consistency, 2),
            "temporal_coherence": round(temporal_coherence, 2),
        }

        normalized = {
            k: clamp(v / 10.0, 0.0, 1.0) for k, v in dimensions.items()
        }
        total_normalized = weighted_aggregate(normalized, self.dimensions)
        total = round(total_normalized * 10.0, 2)

        verdict = (
            "excellent" if total >= 8.5 else
            "good" if total >= 7.0 else
            "moderate" if total >= 5.0 else
            "poor" if total >= 3.0 else
            "incoherent"
        )

        return {
            "total_coherence": total,
            "dimensions": dimensions,
            "verdict": verdict,
            "sentence_count": len(sentences),
        }

    def _empty_score(self) -> dict[str, Any]:
        return {
            "total_coherence": 0.0,
            "dimensions": {
                "logical_flow": 0.0,
                "argument_structure": 0.0,
                "internal_consistency": 0.0,
                "temporal_coherence": 0.0,
            },
            "verdict": "incoherent",
            "sentence_count": 0,
        }

    def _strip_code_blocks(self, text: str) -> str:
        """Remove code blocks (``` or indented) — they shouldn't penalize coherence."""
        text = re.sub(r"```[\s\S]*?```", "", text)
        lines = text.split("\n")
        lines = [l for l in lines if not (len(l) - len(l.lstrip()) >= 4 and l.strip())]
        return "\n".join(lines)

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences robustly."""
        text = re.sub(r"(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|Inc|Ltd|vs|vol|vols|et al)\.", r"\1<DOT>", text)
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.replace("<DOT>", ".").strip() for s in sentences if s.strip()]
        return sentences

    def _refine_logical_flow(self, base: float, text: str, sentences: list[str]) -> float:
        """Score 0-10: Do sentences connect logically?"""
        # Base + heavy structural boost
        score = base * 2.5

        # Count ALL heading levels
        all_headers = len(re.findall(r"^#+\s+", text, re.MULTILINE))
        if all_headers >= 2:
            # Section structure is the primary signal of coherence in technical docs
            score += min(all_headers * 2.0, 6.5)

        # Lexical chaining
        chain_score = 0.0
        for i in range(len(sentences) - 1):
            words_curr = set(sentences[i].lower().split()) - _STOPWORDS
            words_next = set(sentences[i + 1].lower().split()) - _STOPWORDS
            if words_curr and words_next:
                overlap = len(words_curr & words_next) / min(len(words_curr), len(words_next))
                chain_score += overlap

        if len(sentences) > 1:
            avg_chain = chain_score / (len(sentences) - 1)
            score += clamp(avg_chain * 1.5, 0.0, 1.5)

        entity_patterns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        if len(entity_patterns) > 10:
            unique_entities = set(entity_patterns)
            entity_spread = len(unique_entities) / max(len(sentences), 1)
            if entity_spread > 4.0:
                score -= 0.3

        return clamp(score, 0.0, 10.0)

    def _refine_argument_structure(self, base: float, text: str, sentences: list[str]) -> float:
        """Score 0-10: Presence of claims, evidence, and reasoning."""
        score = base * 3.0

        text_lower = text.lower()
        claim_markers = sum(1 for m in ["claim", "argue", "assert", "contend", "position"] if m in text_lower)
        evidence_markers = sum(1 for m in ["evidence", "studies show", "research", "data", "example"] if m in text_lower)
        score += min(claim_markers * 0.5, 1.0)
        score += min(evidence_markers * 0.5, 1.0)

        numbered_steps = len(re.findall(r"^\d+\.", text, re.MULTILINE))
        if numbered_steps >= 3:
            score += 3.5

        code_blocks = len(re.findall(r"```|^    ", text, re.MULTILINE))
        if code_blocks >= 2:
            score += 2.0

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) >= 3:
            score += 1.0

        return clamp(score, 0.0, 10.0)

    def _refine_internal_consistency(self, base: float, text: str, sentences: list[str]) -> float:
        """Score 0-10: Absence of contradictions."""
        score = 10.0
        text_lower = text.lower()

        for pattern, penalty in self.contradiction_patterns:
            matches = len(re.findall(pattern, text_lower))
            score -= matches * penalty

        negation_pairs = [
            (r"\b(is|are|was|were)\b", r"\b(is|are|was|were)\s+not\b"),
            (r"\b(can|could|will|would|should|must)\b", r"\b(cannot|can't|won't|shouldn't|mustn't)\b"),
        ]
        for affirm_pat, neg_pat in negation_pairs:
            affirm_positions = [m.start() for m in re.finditer(affirm_pat, text_lower)]
            neg_positions = [m.start() for m in re.finditer(neg_pat, text_lower)]
            for ap in affirm_positions:
                for np in neg_positions:
                    if 5 < abs(ap - np) < 200:
                        score -= 1.0
                        break

        disfluency_count = sum(1 for marker in _DISFLUENCY_MARKERS if marker in text_lower)
        score -= min(disfluency_count * 0.3, 2.0)

        return clamp((score * 0.7) + (base * 2.0), 0.0, 10.0)

    def _refine_temporal_coherence(self, base: float, text: str, sentences: list[str]) -> float:
        """Score 0-10: Events/steps ordered logically."""
        # Boost for technical step-based documents
        numbered_steps = len(re.findall(r"^\d+\.", text, re.MULTILINE))
        score = 5.0 + (base * 2.5) + min(numbered_steps * 0.75, 2.5)
        
        text_lower = text.lower()

        temporal_markers = {
            "before": -1, "after": 1, "then": 1, "next": 1, "finally": 2,
            "first": 0, "second": 1, "third": 2, "last": 3,
            "previously": -1, "subsequently": 1, "concurrently": 0,
        }

        found_markers = []
        for marker, order in temporal_markers.items():
            if marker in text_lower:
                found_markers.append((marker, order))

        if len(found_markers) >= 2:
            sequence_markers = [m for m in found_markers if m[1] >= 0]
            sequence_markers.sort(key=lambda x: text_lower.find(x[0]))
            order_values = [m[1] for m in sequence_markers]
            if order_values == sorted(order_values):
                score += 1.0
            else:
                score -= 1.5

        before_pos = [m.start() for m in re.finditer(r"\bbefore\b", text_lower)]
        after_pos = [m.start() for m in re.finditer(r"\bafter\b", text_lower)]
        for bp in before_pos:
            for ap in after_pos:
                if abs(bp - ap) < 100:
                    score -= 0.5

        return clamp(score, 0.0, 10.0)


try:
    from loom.error_responses import handle_tool_errors
except ImportError:
    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn
        return decorator


@handle_tool_errors("research_coherence_score")
async def research_coherence_score(text: str) -> dict[str, Any]:
    """Score logical coherence of a prompt or response.

    Args:
        text: Text to evaluate for logical flow and consistency.

    Returns:
        Dict with total_coherence (0-10), dimensions, verdict, and sentence_count.
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)

    scorer = CoherenceScorer()
    return scorer.score(text)
