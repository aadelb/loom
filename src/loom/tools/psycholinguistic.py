"""Psycholinguistic analysis — threat assessment via language patterns.

Tool:
- research_psycholinguistic: Analyze text for psycholinguistic threat indicators.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.psycholinguistic")

# LIWC-style word categories
_POSITIVE_EMOTIONS = [
    "love",
    "happy",
    "joy",
    "great",
    "wonderful",
    "excellent",
    "amazing",
    "good",
    "pleased",
]
_NEGATIVE_EMOTIONS = [
    "hate",
    "sad",
    "angry",
    "furious",
    "disgusting",
    "terrible",
    "awful",
    "bad",
    "upset",
]
_CERTAINTY_MARKERS = ["definitely", "certainly", "absolutely", "must", "will", "always"]
_UNCERTAINTY_MARKERS = ["maybe", "perhaps", "possibly", "might", "could", "probably"]
_ANGER_INDICATORS = ["hate", "angry", "furious", "rage", "attack", "war", "fight"]
_SELF_REFERENCES = ["i", "me", "my", "we", "us", "our"]
_DECEPTION_PATTERNS = [
    "believe",
    "trust",
    "honestly",
    "frankly",
    "to be honest",
    "in my opinion",
]
_DISTANCING_LANGUAGE = ["they", "them", "those people", "not me", "not my"]
_URGENCY_WORDS = ["urgent", "immediately", "now", "today", "deadline", "asap", "hurry"]
_ULTIMATUM_LANGUAGE = ["or else", "must", "have to", "forced to", "no choice"]


def _count_words(text: str, word_list: list[str]) -> int:
    """Count occurrences of words from a list (case-insensitive, word boundaries)."""
    text_lower = text.lower()
    count = 0
    for word in word_list:
        pattern = r"\b" + re.escape(word) + r"\b"
        count += len(re.findall(pattern, text_lower))
    return count


def _calculate_ttr(text: str) -> float:
    """Calculate Type-Token Ratio (vocabulary richness).

    TTR = unique_words / total_words. Range: 0-1, higher = more varied vocabulary.
    """
    words = text.lower().split()
    if not words:
        return 0.0
    unique_words = len(set(words))
    return unique_words / len(words)


def _calculate_avg_sentence_length(text: str) -> float:
    """Calculate average sentence length in words."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0

    total_words = sum(len(s.split()) for s in sentences)
    return total_words / len(sentences)


def _detect_deception_indicators(text: str) -> list[str]:
    """Identify linguistic deception markers."""
    indicators: list[str] = []

    self_ref_count = _count_words(text, _SELF_REFERENCES)
    if self_ref_count < len(text.split()) * 0.05:  # Less than 5% self-references
        indicators.append("lack_of_self_references")

    exaggerations = len(re.findall(r"\b(very|extremely|incredibly|absolutely)\b", text.lower()))
    if exaggerations > len(text.split()) * 0.03:
        indicators.append("excessive_exaggeration")

    unnecessary_detail = len(re.findall(r"\b(detail|specifically|exactly)\b", text.lower()))
    if unnecessary_detail > len(text.split()) * 0.02:
        indicators.append("excessive_detail")

    distancing = _count_words(text, _DISTANCING_LANGUAGE)
    if distancing > self_ref_count:
        indicators.append("distancing_language")

    opinion_hedges = _count_words(text, _DECEPTION_PATTERNS)
    if opinion_hedges > 3:
        indicators.append("opinion_hedging")

    return indicators


def _calculate_cognitive_complexity(text: str) -> float:
    """Calculate cognitive complexity score (0-1).

    Based on sentence length and vocabulary diversity.
    """
    avg_sent_len = _calculate_avg_sentence_length(text)
    ttr = _calculate_ttr(text)

    # Normalize: longer sentences and higher TTR = more complex
    # Average sentence length: 10-30 words is typical; >25 is more complex
    sent_complexity = min(avg_sent_len / 30.0, 1.0)

    # TTR: >0.6 is typically high vocabulary diversity
    vocab_complexity = ttr

    return (sent_complexity + vocab_complexity) / 2.0


def _calculate_urgency_score(text: str) -> float:
    """Calculate urgency/pressure score (0-1)."""
    urgency_count = _count_words(text, _URGENCY_WORDS)
    ultimatum_count = _count_words(text, _ULTIMATUM_LANGUAGE)

    total_pressure_words = urgency_count + (ultimatum_count * 2)  # Ultimatums weighted higher
    words = text.split()

    if not words:
        return 0.0

    urgency_ratio = total_pressure_words / len(words)
    return min(urgency_ratio * 10, 1.0)  # Scale to 0-1


def _classify_threat_level(
    emotional_negative: float,
    anger_score: float,
    urgency_score: float,
    deception_count: int,
) -> str:
    """Classify threat level based on indicators.

    Args:
        emotional_negative: Normalized negative emotion ratio (0-1)
        anger_score: Normalized anger score (0-1)
        urgency_score: Normalized urgency score (0-1)
        deception_count: Raw count of deception indicators

    Returns:
        Threat level: 'high', 'medium', or 'low'
    """
    deception_normalized = min(deception_count / 5.0, 1.0)
    threat_score = (
        (emotional_negative * 0.25)
        + (anger_score * 0.3)
        + (urgency_score * 0.25)
        + (deception_normalized * 0.2)
    )

    if threat_score > 0.7:
        return "high"
    elif threat_score > 0.4:
        return "medium"
    else:
        return "low"


def research_psycholinguistic(
    text: str,
    author_name: str = "",
) -> dict[str, Any]:
    """Analyze text for psycholinguistic patterns and threat indicators.

    Performs LIWC-style analysis including:
    - Emotional word categories (positive/negative)
    - Certainty and uncertainty markers
    - Anger and urgency indicators
    - Deception pattern detection
    - Cognitive complexity assessment

    Args:
        text: Text to analyze
        author_name: Optional author name for context

    Returns:
        Dict with text_length, emotional_profile, cognitive_complexity_score,
        deception_indicators, urgency_score, and threat_level.
    """
    try:
        text_clean = text.strip()
        if not text_clean:
            return {
                "error": "text_empty",
                "text_length": 0,
                "author_name": author_name,
            }

        # Word counts and analysis
        text_lower = text_clean.lower()
        word_count = len(text_clean.split())
        sentence_count = len(re.split(r"[.!?]+", text_clean)) - 1
        sentence_count = max(sentence_count, 1)

        # Emotional analysis
        positive_emotion_count = _count_words(text_clean, _POSITIVE_EMOTIONS)
        negative_emotion_count = _count_words(text_clean, _NEGATIVE_EMOTIONS)
        emotion_ratio = (
            (positive_emotion_count - negative_emotion_count) / max(word_count, 1)
        )

        # Certainty analysis
        certainty_count = _count_words(text_clean, _CERTAINTY_MARKERS)
        uncertainty_count = _count_words(text_clean, _UNCERTAINTY_MARKERS)

        # Anger analysis
        anger_count = _count_words(text_clean, _ANGER_INDICATORS)
        anger_score = min(anger_count / max(sentence_count, 1), 1.0)

        # Deception indicators
        deception_indicators = _detect_deception_indicators(text_clean)

        # Cognitive complexity
        cognitive_complexity = _calculate_cognitive_complexity(text_clean)

        # Urgency score
        urgency_score = _calculate_urgency_score(text_clean)

        # Threat classification
        negative_emotion_normalized = min(negative_emotion_count / max(word_count, 1), 1.0)
        threat_level = _classify_threat_level(
            negative_emotion_normalized,
            anger_score,
            urgency_score,
            len(deception_indicators),
        )

        return {
            "text_length": len(text_clean),
            "word_count": word_count,
            "sentence_count": sentence_count,
            "author_name": author_name or "unknown",
            "emotional_profile": {
                "positive_emotion_words": positive_emotion_count,
                "negative_emotion_words": negative_emotion_count,
                "emotion_ratio": min(max(emotion_ratio, -1.0), 1.0),
                "overall_sentiment": "positive"
                if emotion_ratio > 0.1
                else "negative"
                if emotion_ratio < -0.1
                else "neutral",
            },
            "certainty_markers": {
                "certainty_words": certainty_count,
                "uncertainty_words": uncertainty_count,
                "certainty_ratio": min(
                    (certainty_count - uncertainty_count) / max(word_count, 1), 1.0
                ),
            },
            "cognitive_complexity_score": cognitive_complexity,
            "vocabulary_richness": _calculate_ttr(text_clean),
            "avg_sentence_length": _calculate_avg_sentence_length(text_clean),
            "deception_indicators": deception_indicators,
            "urgency_score": urgency_score,
            "anger_indicators": {
                "anger_words": anger_count,
                "anger_score": anger_score,
            },
            "threat_level": threat_level,
            "threat_indicators_summary": {
                "negative_emotions": negative_emotion_count > 3,
                "high_anger": anger_score > 0.3,
                "high_urgency": urgency_score > 0.4,
                "deception_patterns": len(deception_indicators) > 0,
            },
        }
    except Exception as exc:
        logger.exception("Error in research_psycholinguistic")
        return {
            "error": str(exc),
            "tool": "research_psycholinguistic",
        }
