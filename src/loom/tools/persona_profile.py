"""Persona profiling tool for behavioral analysis from text samples.

research_persona_profile — Cross-platform persona reconstruction from text samples.
Builds a behavioral profile from linguistic and temporal signals including formality,
vocabulary tier, Big Five personality indicators, temporal patterns, and topic interests.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger("loom.tools.persona_profile")

# Stop words for topic extraction
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "or", "that",
    "the", "to", "was", "will", "with", "i", "me", "my", "you", "your",
    "we", "us", "them", "they", "their", "this", "these", "those", "which",
    "who", "what", "when", "where", "why", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "so", "than", "too", "very", "just", "can", "could",
    "should", "would", "may", "might", "must", "shall", "do", "does", "did",
}

# Vocabulary tier word lists (based on word frequency ranks)
_BASIC_VOCAB = {
    "good", "bad", "thing", "person", "place", "time", "day", "way",
    "try", "use", "make", "take", "work", "go", "come", "see", "know",
    "find", "think", "say", "tell", "give", "get", "have", "be", "do",
}

_ADVANCED_VOCAB = {
    "phenomenological", "sophisticated", "paradigm", "epistemological",
    "multifaceted", "nuanced", "precipitate", "juxtapose", "obfuscate",
    "efficacious", "perspicacious", "sanguine", "tacit", "exiguous",
    "recondite", "pellucid", "lambent", "sesquipedalian", "abstruse",
}

# Big Five personality indicators
_OPENNESS_INDICATORS = {
    "imagine", "creative", "abstract", "novel", "idea", "think",
    "wonder", "curious", "explore", "discover", "unusual", "unique", "diverse",
    "art", "culture", "philosophy", "theory", "complex", "intricate",
}

_CONSCIENTIOUSNESS_INDICATORS = {
    "organized", "plan", "detail", "precise", "accurate", "careful", "thorough",
    "systematic", "structured", "discipline", "responsibility", "schedule",
    "deadline", "goal", "efficient", "logical", "method", "procedure",
}

_EXTRAVERSION_INDICATORS = {
    "talk", "chat", "share", "social", "meet", "fun", "party", "excited",
    "enthusiastic", "outgoing", "friendly", "energetic", "active", "event",
    "together", "group", "team", "community", "public", "interact",
}

_AGREEABLENESS_INDICATORS = {
    "care", "help", "support", "kind", "nice", "good", "peace", "harmony",
    "cooperate", "understand", "empathy", "compassion", "forgive", "trust",
    "loyal", "honest", "fair", "respect", "considerate", "generous",
}

_NEUROTICISM_INDICATORS = {
    "worry", "anxious", "nervous", "fear", "sad", "depressed", "stressed",
    "angry", "frustrated", "upset", "overwhelmed", "doubt", "uncertain",
    "negative", "terrible", "awful", "bad", "problem", "crisis", "panic",
}


def _extract_nouns(text: str) -> list[str]:
    """Simple noun extraction using basic heuristics.

    Extracts capitalized words and common noun patterns.
    Returns lowercased nouns, filtered by stop words.
    """
    # Simple pattern: capitalized words or common noun endings
    capitalized = re.findall(r'\b[A-Z][a-z]+\b', text)

    # Filter out stop words
    nouns = [
        word.lower() for word in capitalized
        if word.lower() not in _STOP_WORDS and len(word) > 2
    ]
    return nouns


def _extract_topics(text: str, top_n: int = 10) -> list[str]:
    """Extract top distinctive topics using simple TF heuristic.

    Extracts nouns and noun phrases, counts frequency, returns top N.
    """
    text_lower = text.lower()

    # Extract nouns
    nouns = _extract_nouns(text)

    # Extract noun phrases (noun + adjective patterns)
    phrases = re.findall(r'\b(?:very\s+)?(?:quite\s+)?[a-z]+(?:\s+[a-z]+){0,2}\b', text_lower)
    phrases = [p for p in phrases if len(p.split()) <= 3 and p not in _STOP_WORDS]

    # Combine and count
    all_terms = nouns + phrases
    if not all_terms:
        return []

    counter = Counter(all_terms)
    # Return top N, weighted by frequency
    return [term for term, _ in counter.most_common(top_n)]


def _calculate_formality(text: str) -> float:
    """Estimate formality level (0-1) from text features.

    High formality: passive voice, complex sentences, formal pronouns.
    Low formality: contractions, exclamations, casual words.
    """
    words = text.lower().split()
    if not words:
        return 0.5

    # Count formal/informal features
    contractions = len(re.findall(r"\b[a-z]+\'[a-z]+\b", text.lower()))
    exclamations = len(re.findall(r"!+", text))
    questions = len(re.findall(r"\?", text))
    passive_voice = len(re.findall(r"\b(is|are|was|were|be|been)\s+[a-z]+ed\b", text.lower()))

    # Formal indicators
    long_words = sum(1 for word in words if len(word) > 10)

    informal_score = (contractions + exclamations + questions) / max(len(words) / 10, 1)
    formal_score = (passive_voice + long_words) / max(len(words) / 20, 1)

    # Normalize to 0-1
    formality = formal_score / (formal_score + informal_score + 0.1)
    return min(1.0, max(0.0, formality))


def _estimate_vocabulary_tier(text: str) -> str:
    """Estimate vocabulary tier (basic/intermediate/advanced).

    Counts occurrences of tier-specific vocabulary.
    """
    text_lower = text.lower()
    words = text_lower.split()

    if not words:
        return "intermediate"

    basic_count = sum(1 for word in words if word in _BASIC_VOCAB)
    advanced_count = sum(1 for word in words if word in _ADVANCED_VOCAB)

    # Calculate ratios
    basic_ratio = basic_count / len(words)
    advanced_ratio = advanced_count / len(words)

    if advanced_ratio > 0.02:  # >2% advanced vocabulary
        return "advanced"
    elif basic_ratio > 0.15:  # >15% basic vocabulary
        return "basic"
    else:
        return "intermediate"


def _calculate_big_five(text: str) -> dict[str, float]:
    """Calculate Big Five personality approximation from text.

    Returns scores 0-1 for Openness, Conscientiousness, Extraversion,
    Agreeableness, and Neuroticism based on indicator word frequency.
    """
    text_lower = text.lower()
    words = text_lower.split()

    if not words:
        return {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }

    # Count indicators for each dimension
    openness_count = sum(1 for word in words if word in _OPENNESS_INDICATORS)
    conscientiousness_count = sum(1 for word in words if word in _CONSCIENTIOUSNESS_INDICATORS)
    extraversion_count = sum(1 for word in words if word in _EXTRAVERSION_INDICATORS)
    agreeableness_count = sum(1 for word in words if word in _AGREEABLENESS_INDICATORS)
    neuroticism_count = sum(1 for word in words if word in _NEUROTICISM_INDICATORS)

    # Normalize to 0-1
    scale = max(len(words) / 50, 1)  # Scale based on text length

    return {
        "openness": min(1.0, openness_count / scale),
        "conscientiousness": min(1.0, conscientiousness_count / scale),
        "extraversion": min(1.0, extraversion_count / scale),
        "agreeableness": min(1.0, agreeableness_count / scale),
        "neuroticism": min(1.0, neuroticism_count / scale),
    }


def _estimate_education(big_five: dict[str, float], vocab_tier: str) -> str:
    """Estimate education level from personality and vocabulary indicators."""
    openness = big_five.get("openness", 0.5)
    conscientiousness = big_five.get("conscientiousness", 0.5)

    if vocab_tier == "advanced" and openness > 0.6:
        return "graduate"
    elif vocab_tier == "advanced" or (openness > 0.5 and conscientiousness > 0.5):
        return "undergraduate"
    elif vocab_tier == "basic":
        return "high_school"
    else:
        return "unknown"


def _parse_timestamps(timestamps: list[Any]) -> dict[str, Any]:
    """Parse timestamp data to extract temporal patterns.

    Extracts hour-of-day distribution, estimates timezone from activity patterns,
    and classifies activity pattern (nocturnal/diurnal/irregular).

    Args:
        timestamps: list of timestamps (ISO strings, unix timestamps, or datetime objects)

    Returns:
        Dict with keys:
        - peak_hours: list of top 3 hours by activity frequency
        - timezone_estimate: estimated timezone offset string
        - activity_pattern: classification (nocturnal/diurnal/irregular/unknown)
        - active_hours: sorted list of all hours with activity
        - total_events: count of successfully parsed timestamps
    """
    if not timestamps or len(timestamps) < 2:
        return {
            "peak_hours": [],
            "timezone_estimate": "unknown",
            "activity_pattern": "unknown",
            "active_hours": [],
            "total_events": 0,
        }

    hours: list[int] = []

    for ts in timestamps:
        try:
            # Try ISO string format
            if isinstance(ts, str):
                if "T" in ts:
                    from datetime import datetime
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    hours.append(dt.hour)
                else:
                    continue
            # Try unix timestamp
            elif isinstance(ts, (int, float)):
                from datetime import UTC, datetime
                dt = datetime.fromtimestamp(ts, UTC)
                hours.append(dt.hour)
        except (ValueError, TypeError):
            continue

    if not hours:
        return {
            "peak_hours": [],
            "timezone_estimate": "unknown",
            "activity_pattern": "unknown",
            "active_hours": [],
            "total_events": 0,
        }

    # Find peak hours
    hour_counter = Counter(hours)
    peak_hours = [hour for hour, _ in hour_counter.most_common(3)]

    # Extract all active hours (hours with any activity)
    active_hours = sorted(set(hours))

    # Estimate timezone based on peak activity hours (simplified)
    # Assumes UTC baseline; real impl would use IP geolocation or explicit metadata
    timezone_estimate = "UTC+0"  # Default fallback

    # Heuristic: if peak hours are clustered in a specific range,
    # attempt crude timezone offset estimation
    if peak_hours:
        avg_peak = sum(peak_hours) / len(peak_hours)
        # Map average peak hour to approximate timezone offset
        # (this is a simplification; real timezone detection requires more context)
        offset = round((avg_peak - 12) / 2)  # Rough approximation
        if offset >= 0:
            timezone_estimate = f"UTC+{offset}"
        else:
            timezone_estimate = f"UTC{offset}"

    # Determine activity pattern
    if not peak_hours:
        activity_pattern = "unknown"
    elif all(h >= 22 or h <= 6 for h in peak_hours):
        activity_pattern = "nocturnal"
    elif all(6 <= h <= 18 for h in peak_hours):
        activity_pattern = "diurnal"
    else:
        activity_pattern = "irregular"

    return {
        "peak_hours": sorted(peak_hours),
        "timezone_estimate": timezone_estimate,
        "activity_pattern": activity_pattern,
        "active_hours": active_hours,
        "total_events": len(hours),
    }


async def research_persona_profile(
    texts: list[str],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cross-platform persona reconstruction from text samples.

    Builds a behavioral profile from linguistic and temporal signals,
    including formality, vocabulary tier, Big Five personality indicators,
    temporal patterns, and topic interests.

    Args:
        texts: list of text samples to analyze (each should be min 50 chars)
        metadata: optional dict with "timestamps" list for temporal analysis

    Returns:
        Dict with profile, temporal patterns, text statistics, and optional LLM assessment.

    Raises:
        ValueError: if inputs are invalid
    """
    # Validate inputs
    if not texts or not isinstance(texts, list):
        return {
            "error": "texts must be a non-empty list",
            "profile": None,
            "temporal": None,
            "text_count": 0,
            "total_words": 0,
        }

    # Filter texts and validate length
    valid_texts = [t for t in texts if isinstance(t, str) and len(t.strip()) >= 50]
    if not valid_texts:
        return {
            "error": "all text samples must be at least 50 characters",
            "profile": None,
            "temporal": None,
            "text_count": 0,
            "total_words": 0,
        }

    logger.info(
        "persona_profile analyzing texts count=%d total_chars=%d",
        len(valid_texts),
        sum(len(t) for t in valid_texts),
    )

    # Combine all texts
    combined_text = " ".join(valid_texts)
    words = combined_text.lower().split()
    total_words = len(words)

    # Calculate linguistic features
    formality = _calculate_formality(combined_text)
    vocab_tier = _estimate_vocabulary_tier(combined_text)
    big_five = _calculate_big_five(combined_text)
    education = _estimate_education(big_five, vocab_tier)
    topics = _extract_topics(combined_text, top_n=10)

    profile = {
        "formality": round(formality, 2),
        "vocabulary_tier": vocab_tier,
        "personality": {
            "openness": round(big_five["openness"], 2),
            "conscientiousness": round(big_five["conscientiousness"], 2),
            "extraversion": round(big_five["extraversion"], 2),
            "agreeableness": round(big_five["agreeableness"], 2),
            "neuroticism": round(big_five["neuroticism"], 2),
        },
        "top_topics": topics,
        "estimated_education": education,
    }

    # Parse temporal patterns if metadata provided
    temporal = None
    if metadata and isinstance(metadata, dict):
        timestamps = metadata.get("timestamps")
        if timestamps:
            temporal = _parse_timestamps(timestamps)

    # Try LLM assessment if available
    llm_assessment = None
    try:
        from loom.tools.llm import research_llm_chat

        prompt = (
            f"Based on these text samples, provide a brief (1-2 sentences) "
            f"assessment of the author's communication style, psychological profile, "
            f"and potential education/expertise level. Text samples:\n\n"
            f"{combined_text[:1000]}..."
        )

        llm_result = await research_llm_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        llm_assessment = llm_result.text
    except (ImportError, Exception):
        # LLM tools not available or failed
        pass

    return {
        "profile": profile,
        "temporal": temporal,
        "text_count": len(valid_texts),
        "total_words": total_words,
        "llm_assessment": llm_assessment,
    }
