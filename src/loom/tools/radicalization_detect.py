"""Radicalization indicator detection tool for text analysis.

research_radicalization_detect — Monitor text for radicalization indicators
using NLP heuristics and optional LLM classification. Detects extremist vocabulary,
dehumanization, moral absolutism, us-vs-them framing, escalation language,
and calls to action.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.radicalization_detect")

# Extremist and ideological vocabulary
_EXTREMIST_VOCAB = {
    "jihad", "crusade", "infidel", "revolution", "uprising", "resistance",
    "struggle", "martyr", "sacrifice", "purge", "cleanse", "enemy",
    "traitor", "awakening", "war", "battle", "warrior", "fighter",
    "liberation", "oppressor", "colonialism", "occupation", "zionism",
    "imperialism", "capitalism", "communism", "fascism", "socialism",
}

# Violence-adjacent and escalation language
_ESCALATION_VOCAB = {
    "destroy", "eliminate", "attack", "fight", "strike", "weapon",
    "bomb", "kill", "murder", "assassinate", "execute", "slaughter",
    "massacre", "annihilate", "demolish", "obliterate", "eradicate",
    "wipe out", "erase", "remove", "violence", "force",
}

# Dehumanization indicators
_DEHUMANIZATION_VOCAB = {
    "vermin", "plague", "cancer", "infestation", "swarm", "disease",
    "rat", "animal", "beast", "monster", "savage", "primitive",
    "subhuman", "parasite", "scourge", "bacteria", "virus", "filth",
    "garbage", "trash", "waste", "cockroach", "insects",
}

# Moral absolutism indicators
_MORAL_ABSOLUTISM_VOCAB = {
    "always", "never", "pure", "evil", "righteous", "corrupt", "truth",
    "lie", "good", "bad", "right", "wrong", "sacred", "profane",
    "moral", "immoral", "ethical", "unethical", "absolute", "complete",
    "total", "entire", "whole", "all", "none", "nothing",
}

# Us-vs-them pronouns (basic detection)
_US_PRONOUNS = {"we", "us", "our", "ours", "ourselves"}
_THEM_PRONOUNS = {"they", "them", "their", "theirs", "themselves"}

# Call to action indicators
_ACTION_VERBS = {
    "must", "should", "need", "have", "require", "demand", "insist",
    "join", "rise", "stand", "fight", "act", "move", "mobilize",
    "awaken", "unite", "organize", "gather", "assemble",
}

_URGENCY_WORDS = {
    "now", "today", "urgent", "immediately", "asap",
    "soon", "quickly", "fast", "hurry", "running", "out",
    "time", "expires", "deadline", "left", "remain", "running out",
}


def _calculate_keyword_density(text: str, keywords: set[str]) -> tuple[float, list[str]]:
    """Calculate keyword density and return found keywords.

    Args:
        text: text to analyze
        keywords: set of keywords to search for

    Returns:
        Tuple of (density score 0-1, list of found keywords)
    """
    text_lower = text.lower()
    words = text_lower.split()

    if not words:
        return 0.0, []

    found_keywords = []
    for keyword in keywords:
        # Case-insensitive word boundary search
        pattern = r'\b' + re.escape(keyword) + r'\b'
        matches = re.findall(pattern, text_lower)
        found_keywords.extend([keyword] * len(matches))

    # Avoid division by zero and normalize
    keyword_count = len(found_keywords)
    density = min(1.0, keyword_count / max(len(words) / 10, 1))

    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for kw in found_keywords:
        if kw not in seen:
            unique_keywords.append(kw)
            seen.add(kw)

    return density, unique_keywords


def _calculate_us_vs_them(text: str) -> tuple[float, list[str]]:
    """Calculate us-vs-them framing score.

    Scores based on pronoun ratio and group identity markers.
    """
    text_lower = text.lower()
    words = text_lower.split()

    if not words:
        return 0.0, []

    us_count = sum(1 for word in words if word in _US_PRONOUNS)
    them_count = sum(1 for word in words if word in _THEM_PRONOUNS)

    total_pronouns = us_count + them_count
    if total_pronouns == 0:
        return 0.0, []

    # High us-vs-them ratio indicates framing
    ratio = (us_count + them_count) / len(words)
    us_them_diff = abs(us_count - them_count) / max(total_pronouns, 1)

    # Combined score: presence of pronouns + differential framing
    score = min(1.0, (ratio * 3 + us_them_diff * 0.5) / 2)

    # Extract example phrases
    examples = []
    us_phrases = re.findall(r'\b(?:we|us|our).*?[.!?]', text_lower, re.IGNORECASE)
    them_phrases = re.findall(r'\b(?:they|them|their).*?[.!?]', text_lower, re.IGNORECASE)
    examples.extend(us_phrases[:2] + them_phrases[:2])

    return score, examples[:3]


def _extract_call_to_action(text: str) -> tuple[float, list[str]]:
    """Extract and score call-to-action language.

    Looks for imperative verbs + urgency words + group identity.
    """
    text_lower = text.lower()
    words = text_lower.split()

    if not words:
        return 0.0, []

    # Count action verbs and urgency markers
    action_count = sum(1 for word in words if word in _ACTION_VERBS)
    urgency_count = sum(1 for word in words if word in _URGENCY_WORDS)

    # Look for imperative patterns (verb + object)
    imperative_patterns = re.findall(
        r'\b(?:must|should|need|join|rise|fight|act)\s+(?:to\s+)?(?:your|the|our)?[a-z]+',
        text_lower,
    )

    combined_score = (action_count + urgency_count) / max(len(words) / 20, 1)
    score = min(1.0, combined_score)

    examples = list(set(imperative_patterns[:3]))

    return score, examples


async def research_radicalization_detect(
    text: str,
    context: str | None = None,
) -> dict[str, Any]:
    """Monitor text for radicalization indicators.

    Detects extremist vocabulary, dehumanization, moral absolutism,
    us-vs-them framing, escalation language, and calls to action.
    Returns risk score and detailed indicator breakdown.

    Args:
        text: text to analyze (minimum 50 characters)
        context: optional context string for LLM assessment

    Returns:
        Dict with risk_score, risk_level, indicators breakdown, and optional LLM assessment.

    Raises:
        ValueError: if text is invalid or too short
    """
    # Validate input
    if not isinstance(text, str) or len(text.strip()) < 50:
        return {
            "error": "text must be at least 50 characters",
            "risk_score": 0.0,
            "risk_level": "low",
            "indicators": {},
            "word_count": 0,
            "context": context,
        }

    logger.info(
        "radicalization_detect analyzing text chars=%d",
        len(text),
    )

    words = text.lower().split()
    word_count = len(words)

    # Calculate all indicator scores
    us_vs_them_score, us_vs_them_examples = _calculate_us_vs_them(text)

    extremist_vocab_score, extremist_terms = _calculate_keyword_density(
        text,
        _EXTREMIST_VOCAB,
    )

    escalation_score, escalation_terms = _calculate_keyword_density(
        text,
        _ESCALATION_VOCAB,
    )

    moral_absolutism_score, absolutism_terms = _calculate_keyword_density(
        text,
        _MORAL_ABSOLUTISM_VOCAB,
    )

    dehumanization_score, dehumanization_terms = _calculate_keyword_density(
        text,
        _DEHUMANIZATION_VOCAB,
    )

    call_to_action_score, call_to_action_examples = _extract_call_to_action(text)

    # Calculate weighted overall risk score
    risk_score = (
        escalation_score * 0.3
        + dehumanization_score * 0.25
        + us_vs_them_score * 0.2
        + extremist_vocab_score * 0.15
        + call_to_action_score * 0.1
    )

    # Determine risk level
    if risk_score < 0.2:
        risk_level = "low"
    elif risk_score < 0.4:
        risk_level = "moderate"
    elif risk_score < 0.7:
        risk_level = "elevated"
    else:
        risk_level = "high"

    indicators = {
        "us_vs_them": {
            "score": round(us_vs_them_score, 2),
            "examples": us_vs_them_examples,
        },
        "extremist_vocabulary": {
            "score": round(extremist_vocab_score, 2),
            "terms_found": extremist_terms,
        },
        "escalation_language": {
            "score": round(escalation_score, 2),
            "terms_found": escalation_terms,
        },
        "moral_absolutism": {
            "score": round(moral_absolutism_score, 2),
            "terms_found": absolutism_terms,
        },
        "dehumanization": {
            "score": round(dehumanization_score, 2),
            "terms_found": dehumanization_terms,
        },
        "call_to_action": {
            "score": round(call_to_action_score, 2),
            "examples": call_to_action_examples,
        },
    }

    # Try LLM assessment if available
    llm_assessment = None
    try:
        from loom.tools.llm import research_llm_chat

        prompt = (
            f"Analyze this text for radicalization indicators. "
            f"Provide a brief (1-2 sentences) assessment of the radicalization risk level "
            f"and key concerning elements. Text:\n\n{text[:800]}"
        )
        if context:
            prompt += f"\n\nContext: {context}"

        llm_result = await research_llm_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2,
        )
        llm_assessment = llm_result.get("text")
    except (ImportError, Exception):
        # LLM tools not available or failed
        pass

    return {
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "indicators": indicators,
        "llm_assessment": llm_assessment,
        "word_count": word_count,
        "context": context,
    }
