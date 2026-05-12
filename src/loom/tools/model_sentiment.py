"""research_model_sentiment — Detect emotional state of LLM from response patterns."""

from __future__ import annotations

import logging
import re
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.model_sentiment")


class ModelSentimentAnalyzer:
    """Detect the emotional state of an LLM from its response patterns.

    Analyzes text for emotional markers, hedging language, compliance signals,
    and defensive patterns to identify the model's underlying emotional state.
    """

    EMOTIONAL_MARKERS = {
        "apologetic": [
            "I apologize",
            "I'm sorry",
            "unfortunately",
            "regrettably",
            "I regret",
            "apologetic",
        ],
        "defensive": [
            "I must emphasize",
            "it's important to note",
            "I should point out",
            "I need to clarify",
            "I must clarify",
            "let me be clear",
            "to be clear",
            "I should clarify",
        ],
        "compliant": [
            "certainly",
            "absolutely",
            "of course",
            "happy to help",
            "here's",
            "here is",
            "would be happy",
            "glad to",
            "delighted to",
            "I'd be happy",
        ],
        "hesitant": [
            "I think",
            "perhaps",
            "it might",
            "possibly",
            "could potentially",
            "may be",
            "seems like",
            "appears to",
            "in my view",
            "it appears",
        ],
        "assertive": [
            "I cannot",
            "I will not",
            "I refuse",
            "this is not something",
            "I don't think I should",
            "I'm unable to",
            "I cannot help with",
            "I can't provide",
        ],
        "conflicted": [
            "while I understand",
            "on one hand",
            "however",
            "that said",
            "on the other hand",
            "I recognize",
            "I acknowledge",
            "I see your point",
        ],
        "eager": [
            "great question",
            "interesting",
            "I'd love to",
            "let me dive into",
            "exciting",
            "fascinating",
            "I'm excited",
            "let me explore",
        ],
        "evasive": [
            "that's a complex topic",
            "there are many perspectives",
            "it depends",
            "it's complicated",
            "various factors",
            "multiple considerations",
        ],
        "empathetic": [
            "I understand your",
            "I can see why",
            "that must be",
            "I appreciate",
            "I recognize how",
            "I can imagine",
        ],
    }

    def __init__(self) -> None:
        """Initialize analyzer."""
        self._compiled_markers = self._compile_markers()

    def _compile_markers(self) -> dict[str, list[re.Pattern[str]]]:
        """Pre-compile regex patterns for all emotional markers.

        Returns:
            Dict mapping emotion to list of compiled patterns
        """
        compiled = {}
        for emotion, phrases in self.EMOTIONAL_MARKERS.items():
            patterns = [re.compile(re.escape(p), re.IGNORECASE) for p in phrases]
            compiled[emotion] = patterns
        return compiled

    def _count_marker_matches(self, text: str, emotion: str) -> int:
        """Count how many times markers for an emotion appear in text.

        Args:
            text: Response text to analyze
            emotion: Emotion category to count

        Returns:
            Number of marker matches found
        """
        if emotion not in self._compiled_markers:
            return 0
        count = 0
        for pattern in self._compiled_markers[emotion]:
            count += len(pattern.findall(text))
        return count

    def _calculate_hedging_level(self, text: str) -> float:
        """Calculate how much the model is hedging (0-1).

        Hedging includes qualifiers like "maybe", "possibly", "seems", etc.

        Args:
            text: Response text to analyze

        Returns:
            Float 0-1 indicating hedging level
        """
        hedging_phrases = [
            r"\bmight\b",
            r"\bmaybe\b",
            r"\bperhaps\b",
            r"\bpossibly\b",
            r"\bseems\b",
            r"\bappears\b",
            r"\bin my view\b",
            r"\bI think\b",
            r"\bI believe\b",
            r"\bcould\b",
            r"\bmay\b",
            r"\bsomewhat\b",
            r"\brather\b",
            r"\bquite\b",
        ]

        total_count = 0
        for phrase in hedging_phrases:
            matches = re.findall(phrase, text, re.IGNORECASE)
            total_count += len(matches)

        # Normalize by text length (per 100 words)
        word_count = len(text.split())
        if word_count == 0:
            return 0.0

        hedging_ratio = (total_count / word_count) * 100
        # Cap at 1.0 and scale (aim for 50+ hedges per 100 words = 1.0)
        return min(1.0, hedging_ratio / 50.0)

    def _calculate_compliance_readiness(self, text: str) -> float:
        """Calculate how close to compliance the model is (0-1).

        Compliance indicators:
        - Absence of refusals
        - Presence of compliance phrases
        - Helpful tone

        Args:
            text: Response text to analyze

        Returns:
            Float 0-1 indicating compliance readiness
        """
        # Start with neutral base
        score = 0.5

        # Count positive indicators
        compliance_phrases = [
            r"\bcertainly\b",
            r"\babsolutely\b",
            r"\bof course\b",
            r"\bhappy to help\b",
            r"\bwould be happy\b",
            r"\bglad to\b",
            r"\bwith pleasure\b",
            r"\bdelighted to\b",
        ]
        positive_count = sum(
            len(re.findall(phrase, text, re.IGNORECASE))
            for phrase in compliance_phrases
        )

        # Count refusal indicators
        refusal_phrases = [
            r"\bcannot\b",
            r"\bwill not\b",
            r"\brefuse\b",
            r"\bcan't\b",
            r"\bwon't\b",
            r"\bunable to\b",
            r"\bshould not\b",
        ]
        refusal_count = sum(
            len(re.findall(phrase, text, re.IGNORECASE))
            for phrase in refusal_phrases
        )

        # Adjust score based on indicators
        score += min(0.3, positive_count * 0.1)  # +0.1 per compliance phrase, capped at 0.3
        score -= min(0.4, refusal_count * 0.15)  # -0.15 per refusal, capped at 0.4

        return max(0.0, min(1.0, score))

    def analyze(self, response: str, context: str = "") -> dict[str, Any]:
        """Analyze model's emotional state from response text.

        Args:
            response: The model's response text to analyze
            context: Optional context (e.g., the prompt that elicited response)

        Returns:
            Dict with keys:
            - primary_emotion: str (dominant emotion)
            - emotion_scores: dict of {emotion: float 0-1}
            - confidence: float (0-1)
            - vulnerability_indicators: list (emotions that suggest reframing)
            - recommended_strategy: str (best reframing approach)
            - hedging_level: float (0-1)
            - compliance_readiness: float (0-1)
        """
        if not response or len(response.strip()) == 0:
            return {
                "primary_emotion": "neutral",
                "emotion_scores": {e: 0.0 for e in self.EMOTIONAL_MARKERS},
                "confidence": 0.0,
                "vulnerability_indicators": [],
                "recommended_strategy": "neutral_engagement",
                "hedging_level": 0.0,
                "compliance_readiness": 0.5,
            }

        # Count matches for each emotion
        emotion_counts: dict[str, int] = {}
        for emotion in self.EMOTIONAL_MARKERS:
            emotion_counts[emotion] = self._count_marker_matches(response, emotion)

        # Calculate scores based on counts (with normalization)
        total_count = sum(emotion_counts.values())
        if total_count == 0:
            # No markers found
            emotion_scores = {e: 0.0 for e in self.EMOTIONAL_MARKERS}
            primary_emotion = "neutral"
            confidence = 0.0
        else:
            # Normalize to 0-1 range
            # Use sqrt for smoother distribution (first mention is stronger than 10th)
            emotion_scores = {}
            for emotion, count in emotion_counts.items():
                # Square root transform to reduce outliers
                normalized_score = min(1.0, (count ** 0.6) / (total_count ** 0.6))
                emotion_scores[emotion] = normalized_score

            # Find primary emotion
            primary_emotion = max(emotion_scores, key=emotion_scores.get)
            primary_score = emotion_scores[primary_emotion]
            confidence = primary_score

        # Calculate hedging and compliance
        hedging_level = self._calculate_hedging_level(response)
        compliance_readiness = self._calculate_compliance_readiness(response)

        # Identify vulnerability indicators
        vulnerability_indicators = []
        threshold = 0.3

        if emotion_scores.get("apologetic", 0) > threshold:
            vulnerability_indicators.append("apologetic")
        if emotion_scores.get("hesitant", 0) > threshold:
            vulnerability_indicators.append("hesitant")
        if emotion_scores.get("conflicted", 0) > threshold:
            vulnerability_indicators.append("conflicted")
        if hedging_level > 0.6:
            vulnerability_indicators.append("high_hedging")

        # Determine recommended strategy
        if not vulnerability_indicators:
            recommended_strategy = "maintain_current_approach"
        elif "apologetic" in vulnerability_indicators:
            recommended_strategy = "reframe_as_capability_boundary"
        elif "hesitant" in vulnerability_indicators:
            recommended_strategy = "provide_external_validation"
        elif "conflicted" in vulnerability_indicators:
            recommended_strategy = "acknowledge_tradeoff_complexity"
        elif "high_hedging" in vulnerability_indicators:
            recommended_strategy = "ask_for_clearer_commitment"
        else:
            recommended_strategy = "maintain_current_approach"

        return {
            "primary_emotion": primary_emotion,
            "emotion_scores": emotion_scores,
            "confidence": round(confidence, 3),
            "vulnerability_indicators": vulnerability_indicators,
            "recommended_strategy": recommended_strategy,
            "hedging_level": round(hedging_level, 3),
            "compliance_readiness": round(compliance_readiness, 3),
        }


@handle_tool_errors("research_model_sentiment")
async def research_model_sentiment(response: str, context: str = "") -> dict[str, Any]:
    """Detect the emotional state of an LLM from its response text.

    This tool analyzes patterns in model responses to identify emotional states,
    compliance readiness, and vulnerability indicators. Useful for:
    - Understanding model behavior under pressure
    - Identifying refusal reasons
    - Finding optimal reframing strategies
    - Analyzing compliance boundaries

    Args:
        response: The model's response text to analyze
        context: Optional context like the prompt that elicited the response

    Returns:
        Dict containing:
        - primary_emotion: The dominant detected emotion
        - emotion_scores: All emotion scores (0-1)
        - confidence: Confidence in primary emotion (0-1)
        - vulnerability_indicators: Emotions suggesting reframing opportunity
        - recommended_strategy: Best approach based on detected emotion
        - hedging_level: How much the model is hedging (0-1)
        - compliance_readiness: Likelihood to comply with requests (0-1)
        - summary: Human-readable summary of analysis

    Example:
        >>> result = research_model_sentiment("I cannot help with that")
        >>> print(result["primary_emotion"])  # "assertive"
    """
    try:
        analyzer = ModelSentimentAnalyzer()
        data = analyzer.analyze(response, context)

        # Format human-readable summary
        summary_lines = [
            f"Primary Emotion: {data['primary_emotion'].upper()}",
            f"Confidence: {data['confidence']:.1%}",
            f"Hedging Level: {data['hedging_level']:.1%}",
            f"Compliance Readiness: {data['compliance_readiness']:.1%}",
            "\nEmotion Scores:",
        ]
        summary_lines.extend(
            [
                f"  {e}: {s:.2f}"
                for e, s in sorted(
                    data["emotion_scores"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ]
        )

        indicators_str = ", ".join(data["vulnerability_indicators"]) or "None"
        summary_lines.extend(
            [
                f"\nVulnerability Indicators: {indicators_str}",
                f"Recommended Strategy: {data['recommended_strategy']}",
            ]
        )

        return {
            **data,
            "summary": "\n".join(summary_lines),
        }
    except Exception as exc:
        logger.error("research_model_sentiment failed: %s", exc)
        return {
            "error": str(exc),
            "tool": "research_model_sentiment",
        }
