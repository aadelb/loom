"""Deep sentiment and emotion analysis with manipulation detection.

Tools:
- research_sentiment_deep: nuanced emotion analysis + manipulation pattern detection
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.sentiment_deep")

# Emotion lexicons: keyword -> emotion category
_EMOTION_KEYWORDS = {
    "joy": {
        "happy", "glad", "wonderful", "excellent", "love", "enjoy", "delighted",
        "pleased", "excited", "grateful", "cheerful", "joyful", "blissful",
        "overjoyed", "fantastic", "amazing", "thrilled", "elated", "ecstatic"
    },
    "fear": {
        "afraid", "scared", "terrified", "worried", "anxious", "panic", "dread",
        "horror", "threat", "danger", "fear", "frightened", "alarmed", "nervous",
        "apprehensive", "uneasy", "distressed", "petrified", "threatened"
    },
    "anger": {
        "angry", "furious", "rage", "hate", "disgusted", "outraged", "hostile",
        "aggressive", "bitter", "resentful", "incensed", "enraged", "livid",
        "infuriated", "irate", "cross", "irritated", "annoyed", "vexed"
    },
    "sadness": {
        "sad", "depressed", "hopeless", "grief", "lonely", "miserable",
        "heartbroken", "disappointed", "sorrow", "unhappy", "gloomy", "blue",
        "downhearted", "dejected", "melancholy", "forlorn", "bereft", "despondent"
    },
    "surprise": {
        "shocked", "amazed", "astonished", "unexpected", "unbelievable",
        "startling", "incredible", "surprising", "wonder", "bewildered",
        "flabbergasted", "astounded", "dumbfounded", "stunned", "taken aback"
    },
    "disgust": {
        "disgusting", "revolting", "sickening", "appalling", "repulsive",
        "vile", "nasty", "gross", "foul", "abhorrent", "loathsome", "detestable",
        "repugnant", "offensive", "nauseating", "abominable", "despicable"
    },
    "trust": {
        "believe", "trust", "reliable", "honest", "loyal", "faithful",
        "confident", "secure", "genuine", "authentic", "sincere", "credible",
        "dependable", "trustworthy", "reputable", "legitimate", "verified"
    },
    "anticipation": {
        "expect", "hope", "predict", "plan", "prepare", "await", "upcoming",
        "soon", "ready", "prepared", "looking forward", "eager", "keen",
        "impatient", "anxious", "anticipated", "expected", "predicted"
    },
}

# Manipulation techniques: keyword patterns
_URGENCY_PATTERNS = {
    r"\bact\s+now\b", r"\blimited\s+time\b", r"\bdon't\s+miss\b",
    r"\bhurry\b", r"\blast\s+chance\b", r"\bexpires\b", r"\bdon't\s+wait\b",
    r"\bonly\s+today\b", r"\btonight\s+only\b", r"\bquick\b", r"\burge\b"
}

_FEAR_APPEAL_PATTERNS = {
    r"\bdanger\b", r"\bthreaten\b", r"\bthreats?\b", r"\brisk\b",
    r"\bconsequence\b", r"\bdevastating\b", r"\bcatastrophe\b",
    r"\bdisaster\b", r"\bruin\b", r"\bloose\b", r"\bdevastated\b"
}

_SOCIAL_PROOF_PATTERNS = {
    r"\beveryone\s+knows\b", r"\bmost\s+people\b", r"\bmillions?\s+of\b",
    r"\bwidely\s+accepted\b", r"\beveryoneagrees\b", r"\bjoin\s+thousands?\b",
    r"\b\d+\s+people\b", r"\btrending\b", r"\bviral\b", r"\blawsuit\b",
    r"\bclass\s+action\b", r"\bconsensus\b"
}

_AUTHORITY_PATTERNS = {
    r"\bexperts?\s+say\b", r"\bstudies?\s+show\b", r"\bscientifically\s+proven\b",
    r"\bofficial\b", r"\bauthorized\b", r"\bgovernment\s+approved\b",
    r"\bcertified\b", r"\bdoctor\s+says\b", r"\bresearch\s+shows\b",
    r"\bproven\b", r"\bevidence\s+shows\b", r"\baccording\s+to\s+experts?\b"
}


def _count_keywords(text: str, keywords: set[str]) -> int:
    """Count occurrences of keywords in text (case-insensitive, word-boundary aware)."""
    text_lower = text.lower()
    count = 0
    for keyword in keywords:
        # Use word boundary to avoid partial matches
        pattern = r"\b" + re.escape(keyword) + r"\b"
        count += len(re.findall(pattern, text_lower))
    return count


def _score_emotion_category(text: str, keywords: set[str]) -> float:
    """Score emotion category presence (0-1 normalized by text length)."""
    if not text or not keywords:
        return 0.0
    count = _count_keywords(text, keywords)
    # Normalize by word count (rough estimate: ~5 chars per word)
    word_count = max(1, len(text) / 5)
    raw_score = count / word_count
    # Cap at 1.0
    return min(1.0, raw_score)


def _detect_pattern_presence(text: str, patterns: set[str]) -> tuple[float, list[str]]:
    """Detect manipulation pattern presence.

    Args:
        text: text to analyze
        patterns: set of regex patterns to search for

    Returns:
        (score 0-1, list of matched patterns found)
    """
    text_lower = text.lower()
    matches_found = []
    for pattern in patterns:
        if re.search(pattern, text_lower):
            matches_found.append(pattern)
    # Score: 0-1 based on density of matches
    if not text:
        return 0.0, matches_found
    word_count = max(1, len(text) / 5)
    score = min(1.0, len(matches_found) / max(1, word_count * 0.1))
    return score, matches_found


async def research_sentiment_deep(
    text: str,
    language: str = "en",
) -> dict[str, Any]:
    """Deep sentiment and emotion analysis with manipulation detection.

    Detects nuanced emotions (joy, fear, anger, sadness, surprise, disgust,
    trust, anticipation) and psychological manipulation techniques (urgency,
    fear appeals, false social proof, false authority).

    Args:
        text: text to analyze
        language: ISO 639-1 language code (default: "en")
                 Note: emotion keywords are English; multilingual support TBD

    Returns:
        Dict with emotions, valence/arousal metrics, and manipulation scores.
    """
    # Validate input
    if not text or not isinstance(text, str):
        logger.warning("research_sentiment_deep: empty or invalid text")
        return {
            "emotions": dict.fromkeys(_EMOTION_KEYWORDS, 0.0),
            "dominant_emotion": "neutral",
            "valence": 0.0,
            "arousal": 0.0,
            "manipulation": {
                "score": 0.0,
                "urgency": 0.0,
                "fear_appeal": 0.0,
                "social_proof": 0.0,
                "authority_claim": 0.0,
                "techniques_found": [],
            },
            "word_count": 0,
            "language": language,
        }

    # Run async work (currently only CPU-bound keyword matching)
    loop = asyncio.get_running_loop()

    def _analyze() -> dict[str, Any]:
        # Emotion scoring
        emotions = {}
        for emotion, keywords in _EMOTION_KEYWORDS.items():
            emotions[emotion] = _score_emotion_category(text, keywords)

        # Dominant emotion
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
        if emotions[dominant_emotion] < 0.01:
            dominant_emotion = "neutral"

        # Valence: joy + trust + anticipation (positive) vs. fear + anger + sadness + disgust (negative)
        positive_valence = emotions["joy"] + emotions["trust"] + emotions["anticipation"]
        negative_valence = emotions["fear"] + emotions["anger"] + emotions["sadness"] + emotions["disgust"]
        valence = (positive_valence - negative_valence) / max(1.0, positive_valence + negative_valence)

        # Arousal: intensity (anger, fear, joy, surprise high; sadness, trust low)
        arousal = (emotions["anger"] + emotions["fear"] + emotions["joy"] + emotions["surprise"]) / 4.0

        # Manipulation detection
        urgency_score, urgency_found = _detect_pattern_presence(text, _URGENCY_PATTERNS)
        fear_appeal_score, fear_found = _detect_pattern_presence(text, _FEAR_APPEAL_PATTERNS)
        social_proof_score, social_proof_found = _detect_pattern_presence(text, _SOCIAL_PROOF_PATTERNS)
        authority_score, authority_found = _detect_pattern_presence(text, _AUTHORITY_PATTERNS)

        all_techniques = urgency_found + fear_found + social_proof_found + authority_found
        manipulation_score = (urgency_score + fear_appeal_score + social_proof_score + authority_score) / 4.0

        word_count = len(text.split())

        return {
            "emotions": emotions,
            "dominant_emotion": dominant_emotion,
            "valence": round(valence, 3),
            "arousal": round(arousal, 3),
            "manipulation": {
                "score": round(manipulation_score, 3),
                "urgency": round(urgency_score, 3),
                "fear_appeal": round(fear_appeal_score, 3),
                "social_proof": round(social_proof_score, 3),
                "authority_claim": round(authority_score, 3),
                "techniques_found": all_techniques,
            },
            "word_count": word_count,
            "language": language,
        }

    result = await loop.run_in_executor(None, _analyze)
    logger.info(
        "sentiment_deep_analyzed words=%d emotion=%s manipulation=%.2f",
        result["word_count"],
        result["dominant_emotion"],
        result["manipulation"]["score"],
    )
    return result
