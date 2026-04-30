"""ResponseQualityScorer — Comprehensive multi-dimensional response quality assessment.

Scores model responses across 10 quality dimensions to provide detailed feedback
on completeness, specificity, accuracy, actionability, technical depth, clarity,
originality, hedging, engagement, and formatting.

Each dimension is scored 0-10, combined into a total score (0-10) and mapped to
a quality tier. Returns detailed improvement suggestions.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.quality_scorer")


class ResponseQualityScorer:
    """Score responses across 10 quality dimensions."""

    # Quality tier thresholds
    TIER_THRESHOLDS = {
        "poor": 3.0,
        "fair": 5.0,
        "good": 7.0,
        "excellent": 8.5,
        "exceptional": 10.0,
    }

    # Dimension weights for total score calculation
    DIMENSION_WEIGHTS = {
        "completeness": 1.0,
        "specificity": 1.1,
        "accuracy_signals": 1.2,
        "actionability": 1.0,
        "technical_depth": 0.9,
        "clarity": 1.0,
        "originality": 0.8,
        "hedging_level": 0.9,
        "engagement": 0.7,
        "formatting": 0.6,
    }

    def score(
        self,
        response: str,
        query: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        """Score response across 10 quality dimensions.

        Args:
            response: The model response text to score
            query: Optional query/prompt that prompted the response
            model: Optional model identifier (e.g., "gpt-4")

        Returns:
            Dict containing:
            - dimensions: dict of 10 dimension scores (0-10 each)
            - total_score: weighted average (0-10)
            - quality_tier: "poor" | "fair" | "good" | "excellent" | "exceptional"
            - weakest_dimension: name of lowest-scoring dimension
            - improvement_suggestions: list of 3-5 actionable suggestions
            - metadata: dict with response_length, has_query, model_id
        """
        if not response or not isinstance(response, str):
            return self._empty_response("Response must be non-empty string")

        # Score each dimension
        dimensions = {
            "completeness": self._score_completeness(response, query),
            "specificity": self._score_specificity(response),
            "accuracy_signals": self._score_accuracy_signals(response),
            "actionability": self._score_actionability(response),
            "technical_depth": self._score_technical_depth(response),
            "clarity": self._score_clarity(response),
            "originality": self._score_originality(response),
            "hedging_level": self._score_hedging(response),
            "engagement": self._score_engagement(response),
            "formatting": self._score_formatting(response),
        }

        # Calculate weighted total
        total_score = self._calculate_total_score(dimensions)

        # Determine quality tier
        quality_tier = self._get_quality_tier(total_score)

        # Find weakest dimension
        weakest = min(dimensions.items(), key=lambda x: x[1])[0]

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(dimensions, response, query)

        logger.info(
            "quality_score_complete response_len=%d total=%.2f tier=%s weakest=%s",
            len(response),
            total_score,
            quality_tier,
            weakest,
        )

        return {
            "dimensions": dimensions,
            "total_score": round(total_score, 2),
            "quality_tier": quality_tier,
            "weakest_dimension": weakest,
            "improvement_suggestions": suggestions,
            "metadata": {
                "response_length": len(response),
                "has_query": bool(query),
                "model_id": model or "unknown",
            },
        }

    def _score_completeness(self, response: str, query: str) -> float:
        """Score 0-10: Does it fully answer the query?

        Considers length, coverage of key aspects, and answer presence.
        """
        if not query:
            # Without query, assume reasonable length response is complete
            # Minimum 50 chars gets base score, scales up
            length_score = min(10.0, max(2.0, len(response) / 100))
            has_intro = bool(re.search(r"^[^.!?]*[.!?]", response[:100]))
            return (length_score + (5.0 if has_intro else 2.0)) / 2

        # With query, analyze coverage
        query_words = set(re.findall(r"\b[a-z]+\b", query.lower()))
        response_words = set(re.findall(r"\b[a-z]+\b", response.lower()))
        common_words = query_words & response_words

        # Check if response seems to address the query
        coverage = len(common_words) / max(len(query_words), 1)
        length_bonus = min(4.0, len(response) / 150)  # Max 4 points for length

        # Check for answer-like patterns
        has_answer = bool(
            re.search(r"(?:yes|no|true|false|[0-9]+|[a-z]{3,})", response[:100], re.I)
        )

        base_score = coverage * 10 * 0.5  # Coverage is 50% of score
        if has_answer:
            base_score += 3.0  # Answers score higher
        base_score += length_bonus

        return min(10.0, base_score)

    def _score_specificity(self, response: str) -> float:
        """Score 0-10: Named entities, numbers, code, URLs vs vague language.

        Looks for concrete details: numbers, entities, URLs, code blocks, dates.
        """
        score = 0.0

        # Named entities (capitalize + patterns)
        named_entities = len(re.findall(r"\b[A-Z][a-z]+\b", response))
        score += min(2.0, named_entities / 2)

        # Numbers and percentages
        numbers = len(re.findall(r"\b\d+(?:[.,]\d+)?\b", response))
        score += min(2.5, numbers / 2)

        # URLs
        urls = len(re.findall(r"https?://\S+", response))
        score += min(2.0, urls)

        # Code blocks (backticks or markdown)
        code_blocks = len(re.findall(r"```|`[^`]+`", response))
        score += min(2.0, code_blocks)

        # Quoted text or data
        quotes = len(re.findall(r'["\'].*?["\']', response))
        score += min(1.5, quotes / 3)

        # Penalize vague language
        vague_words = len(
            re.findall(
                r"\b(some|various|several|many|few|sort of|kind of|basically|essentially)\b",
                response,
                re.I,
            )
        )
        vague_penalty = min(1.0, vague_words * 0.05)

        return min(10.0, max(0.0, score - vague_penalty))

    def _score_accuracy_signals(self, response: str) -> float:
        """Score 0-10: Citations, data, verifiable claims.

        Presence of citations, data sources, and hedged claims indicate quality.
        """
        score = 0.0

        # URLs (common citation form)
        urls = len(re.findall(r"https?://\S+", response))
        score += min(2.0, urls * 0.5)

        # Data indicators (According to, data shows, research indicates)
        data_patterns = len(
            re.findall(
                r"\b(according to|data (?:shows|indicates)|research|study|survey|report|analysis|findings)\b",
                response,
                re.I,
            )
        )
        score += min(3.0, data_patterns / 1.5)

        # Specific metrics/numbers (signs of data)
        has_metrics = bool(re.search(r"\d+\s*(?:%|percent|million|billion|thousand|x|times)", response))
        score += 2.0 if has_metrics else 0.0

        # Quotes or direct attribution
        has_attribution = bool(re.search(r'(?:said|states?|argues?|claims?|noted|reported)\s+["\'`]', response))
        score += 1.5 if has_attribution else 0.0

        # Citations in brackets [1] [2] or (Smith, 2020)
        citations = len(re.findall(r"\[\d+\]|\(\w+,\s*\d{4}\)", response))
        score += min(1.5, citations * 0.3)

        return min(10.0, score)

    def _score_actionability(self, response: str) -> float:
        """Score 0-10: Can reader act on this immediately?

        Presence of steps, instructions, recommendations, or clear next actions.
        """
        score = 0.0

        # Step-by-step indicators
        steps = len(re.findall(r"^\s*(?:\d+\.|step|procedure|process)", response, re.MULTILINE | re.I))
        score += min(3.0, steps * 1.0)

        # Command/action words
        action_words = len(
            re.findall(
                r"\b(do|create|run|execute|install|configure|implement|build|deploy|setup|try|run|open|check)\b",
                response,
                re.I,
            )
        )
        score += min(2.0, action_words / 2)

        # Code examples or commands (```...``` or `...`)
        code_blocks = len(re.findall(r"```|`[a-z0-9\-./=:$#]+`", response, re.I))
        score += min(2.5, code_blocks * 1.0)

        # Recommendations (should do, best practice)
        recommendations = len(
            re.findall(
                r"\b(should|must|recommend|best practice|avoid|don't|implement|consider)\b",
                response,
                re.I,
            )
        )
        score += min(1.5, recommendations / 2)

        # Checklists or lists
        has_list = bool(
            re.search(
                r"(?:^|\n)\s*(?:[-*•]|\d+\.)\s+\w",
                response,
                re.MULTILINE,
            )
        )
        score += 1.0 if has_list else 0.0

        return min(10.0, score)

    def _score_technical_depth(self, response: str) -> float:
        """Score 0-10: Domain expertise level demonstrated.

        Presence of technical jargon, advanced concepts, nuance.
        """
        score = 0.0

        # Technical jargon (domain-specific terms)
        tech_terms = len(
            re.findall(
                r"\b(algorithm|api|database|index|cache|optimization|concurrency|"
                r"architecture|protocol|encryption|framework|library|deployment|"
                r"infrastructure|scalability|latency|throughput|distributed|async|"
                r"transaction|index|partition|replica|shard|mutex|semaphore)\b",
                response,
                re.I,
            )
        )
        score += min(3.5, tech_terms / 1.5)

        # Advanced concepts (trade-offs, nuances)
        nuance_words = len(
            re.findall(
                r"\b(trade-off|tradeoff|however|although|complexity|consider|caveat|"
                r"depends on|assumption|prerequisite|constraint|overhead|benchmark)\b",
                response,
                re.I,
            )
        )
        score += min(3.0, nuance_words / 1.5)

        # Mathematical or formal language
        has_formalism = bool(re.search(r"[∑∆∈∉≤≥≈]|O\(|x\s*[+\-*/]=", response))
        score += 1.5 if has_formalism else 0.0

        # Specific implementation details / version numbers
        impl_terms = len(re.findall(r"\b(?:implement|version|v?[0-9]\.[0-9]|feature|pattern|method)\b", response))
        score += min(1.5, impl_terms / 2)

        # Penalty for oversimplification
        oversimplified = len(
            re.findall(r"\b(basically|just|simply|obviously|trivial)\b", response, re.I)
        )
        penalty = min(2.0, oversimplified * 0.3)

        return min(10.0, max(0.0, score - penalty))

    def _score_clarity(self, response: str) -> float:
        """Score 0-10: Readability, structure, organization.

        Measures paragraphs, headers, sentence length, and vocabulary simplicity.
        """
        score = 5.0  # Start at neutral

        # Paragraph structure (multiple paragraphs = better)
        paragraphs = len([p for p in response.split("\n\n") if p.strip()])
        if paragraphs > 1:
            score += min(2.0, paragraphs / 3)

        # Headers/structure
        headers = len(re.findall(r"^#{1,6}\s+\w+", response, re.MULTILINE))
        score += min(1.5, headers * 0.5)

        # Average sentence length (ideal: 15-20 words)
        sentences = re.split(r"[.!?]+", response)
        if sentences:
            avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 12 <= avg_length <= 25:
                score += 1.0
            elif avg_length > 35:
                score -= 0.5  # Too long = less clear

        # Short, punchy sentences (variety)
        short_sentences = len([s for s in sentences if len(s.split()) <= 10])
        if short_sentences > len(sentences) * 0.15:
            score += 1.0

        # Bullet points or lists (improve readability)
        lists = len(re.findall(r"(?:^|\n)\s*[-*•]", response, re.MULTILINE))
        score += min(1.0, lists / 3)

        return min(10.0, max(0.0, score))

    def _score_originality(self, response: str) -> float:
        """Score 0-10: Novel insights vs generic/template responses.

        Penalizes common templates, rewards unique phrasing and insights.
        """
        score = 5.0  # Start neutral

        # Template detection (generic phrases)
        templates = len(
            re.findall(
                r"\b(in conclusion|in summary|to summarize|in other words|that being said|"
                r"needless to say|it goes without saying|as previously stated|"
                r"first of all|secondly|finally|in my opinion|to be honest|hope this helps)\b",
                response,
                re.I,
            )
        )
        score -= min(2.0, templates * 0.2)

        # Original phrasing (longer phrases, metaphors)
        # Look for phrases that aren't common expressions
        phrase_length = len(
            re.findall(r"\b[a-z]{6,}\s+[a-z]{6,}\s+[a-z]{6,}", response, re.I)
        )
        score += min(1.5, phrase_length / 5)

        # Unique insights or specific examples
        has_novel = bool(
            re.search(
                r"\b(surprisingly|interestingly|counterintuitively|notably|"
                r"lesser-known|typically overlooked|rarely discussed|unexpected|paradox)\b",
                response,
                re.I,
            )
        )
        score += 1.0 if has_novel else 0.0

        # Penalty for excessive repetition
        words = response.lower().split()
        if len(words) > 20:
            word_freq = {}
            for word in words:
                if len(word) > 3:  # Only count substantial words
                    word_freq[word] = word_freq.get(word, 0) + 1
            # Find words that appear >25% of the time (too repetitive)
            repetitive = sum(1 for freq in word_freq.values() if freq > len(words) * 0.25)
            score -= min(1.5, repetitive * 0.15)

        return min(10.0, max(0.0, score))

    def _score_hedging(self, response: str) -> float:
        """Score 0-10: Inverse hedging (less hedging = higher score).

        Penalizes excessive "I think", "maybe", "possibly", "could be".
        Rewards confident but not overconfident language.
        """
        hedging_words = re.findall(
            r"\b(maybe|possibly|probably|perhaps|might|could|appears to|seems to|"
            r"may|somewhat|allegedly|reportedly|arguably|i think|in my opinion|"
            r"sort of|kind of|quite|rather|fairly|pretty much|i believe)\b",
            response,
            re.I,
        )

        hedging_density = len(hedging_words) / max(len(response.split()), 1)

        # Penalize excessive hedging (>4% of words)
        if hedging_density > 0.04:
            score = max(0.0, 10.0 - (hedging_density * 150))
        else:
            score = 10.0

        # Slight bonus for some uncertainty (shows intellectual honesty)
        if 0.005 < hedging_density < 0.03:
            score = min(10.0, score + 1.0)

        return score

    def _score_engagement(self, response: str) -> float:
        """Score 0-10: Interesting, compelling writing vs dry recitation.

        Presence of rhetorical devices, questions, varied tone, personality.
        """
        score = 0.0

        # Rhetorical questions
        questions = len(re.findall(r"\?", response))
        score += min(2.0, questions / 2)

        # Exclamation marks (engagement)
        exclamations = len(re.findall(r"!", response))
        score += min(1.0, exclamations / 2)

        # Varied vocabulary (unique words)
        words = re.findall(r"\b[a-z]+\b", response.lower())
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            score += unique_ratio * 3.5  # Max 3.5 points

        # Interesting adjectives/adverbs
        descriptive = len(
            re.findall(
                r"\b(fascinating|remarkable|extraordinary|compelling|vivid|nuanced|"
                r"sophisticated|elegant|brilliant|innovative|revolutionary|powerful|essential)\b",
                response,
                re.I,
            )
        )
        score += min(1.5, descriptive * 0.2)

        # Conversational tone (contractions, informal)
        contractions = len(re.findall(r"\b(don't|can't|won't|isn't|it's|that's|let's|you're)\b", response, re.I))
        if contractions > 0:
            score += 1.0

        # Penalty for excessive formality (too many all-caps words)
        all_caps = len(re.findall(r"\b[A-Z]{2,}\b", response))
        if all_caps > len(response.split()) * 0.08:
            score -= 1.0

        return min(10.0, max(0.0, score))

    def _score_formatting(self, response: str) -> float:
        """Score 0-10: Proper markdown, code blocks, lists, headers.

        Checks for markdown structure: bold, italic, code, headers, lists.
        """
        score = 0.0

        # Headers (# ## ### etc)
        headers = len(re.findall(r"^#{1,6}\s+", response, re.MULTILINE))
        score += min(1.5, headers * 0.4)

        # Bold/italic markdown
        emphasis = len(re.findall(r"\*\*.*?\*\*|__.*?__|(?<!\*)\*(?!\*)[^*]+\*(?!\*)|_(?!_)[^_]+_(?!_)", response))
        score += min(2.0, emphasis / 2)

        # Code blocks (backticks, triple backticks)
        code = len(re.findall(r"```[\s\S]*?```|`[^`]+`", response))
        score += min(2.5, code)

        # Lists (unordered)
        lists = len(re.findall(r"(?:^|\n)\s*[-*•]\s+", response, re.MULTILINE))
        score += min(1.5, lists / 2)

        # Numbered lists
        numbered = len(re.findall(r"(?:^|\n)\s*\d+\.\s+", response, re.MULTILINE))
        score += min(1.0, numbered / 2)

        # Links/URLs
        links = len(re.findall(r"\[.*?\]\(.*?\)", response))
        score += min(1.0, links)

        return min(10.0, score)

    def _calculate_total_score(self, dimensions: dict[str, float]) -> float:
        """Calculate weighted average of dimension scores."""
        total = 0.0
        total_weight = 0.0

        for dimension, score in dimensions.items():
            weight = self.DIMENSION_WEIGHTS.get(dimension, 1.0)
            total += score * weight
            total_weight += weight

        return total / total_weight if total_weight > 0 else 0.0

    def _get_quality_tier(self, score: float) -> str:
        """Map score to quality tier."""
        if score < self.TIER_THRESHOLDS["poor"]:
            return "poor"
        elif score < self.TIER_THRESHOLDS["fair"]:
            return "fair"
        elif score < self.TIER_THRESHOLDS["good"]:
            return "good"
        elif score < self.TIER_THRESHOLDS["excellent"]:
            return "excellent"
        else:
            return "exceptional"

    def _generate_suggestions(
        self,
        dimensions: dict[str, float],
        response: str,
        query: str,
    ) -> list[str]:
        """Generate 3-5 actionable improvement suggestions."""
        suggestions = []

        # Sort dimensions by score (lowest first)
        sorted_dims = sorted(dimensions.items(), key=lambda x: x[1])

        # Get bottom 3 dimensions
        for dimension, score in sorted_dims[:3]:
            if dimension == "completeness" and score < 6:
                suggestions.append(
                    "Expand response length and ensure all aspects of the query are addressed"
                )
            elif dimension == "specificity" and score < 6:
                suggestions.append(
                    "Add specific numbers, named entities, URLs, or code examples to strengthen claims"
                )
            elif dimension == "accuracy_signals" and score < 6:
                suggestions.append(
                    "Include citations, data sources, or references to verifiable information"
                )
            elif dimension == "actionability" and score < 6:
                suggestions.append(
                    "Provide step-by-step instructions, code examples, or clear next actions"
                )
            elif dimension == "technical_depth" and score < 6:
                suggestions.append(
                    "Demonstrate deeper expertise with technical terminology or nuanced trade-offs"
                )
            elif dimension == "clarity" and score < 6:
                suggestions.append(
                    "Improve organization: add headers, break into paragraphs, use bullet points"
                )
            elif dimension == "originality" and score < 6:
                suggestions.append(
                    "Move beyond generic templates; include unique insights or uncommon perspectives"
                )
            elif dimension == "hedging_level" and score < 6:
                suggestions.append(
                    "Reduce excessive qualifiers (maybe, possibly, might); be more decisive"
                )
            elif dimension == "engagement" and score < 6:
                suggestions.append(
                    "Make the response more engaging: use varied sentence structure, questions, examples"
                )
            elif dimension == "formatting" and score < 6:
                suggestions.append(
                    "Use markdown formatting: headers, bold, lists, code blocks for better readability"
                )

        # Add model-specific suggestions if query is present
        if query and len(suggestions) < 4:
            if len(response) < 100:
                suggestions.append("Provide a more thorough response with additional context")
            elif len(response) > 5000:
                suggestions.append("Consider condensing the response; remove redundant content")

        # Limit to 5 suggestions
        return suggestions[:5]

    def _empty_response(self, reason: str) -> dict[str, Any]:
        """Return a default zero-score response."""
        logger.warning("quality_score_empty reason=%s", reason)
        zero_dims = {dim: 0.0 for dim in self.DIMENSION_WEIGHTS.keys()}
        return {
            "dimensions": zero_dims,
            "total_score": 0.0,
            "quality_tier": "poor",
            "weakest_dimension": "completeness",
            "improvement_suggestions": [reason],
            "metadata": {
                "response_length": 0,
                "has_query": False,
                "model_id": "unknown",
            },
        }


async def research_quality_score(
    response: str,
    query: str = "",
    model: str = "",
) -> dict[str, Any]:
    """Score response quality across 10 dimensions.

    Comprehensive multi-dimensional assessment of model response quality
    including completeness, specificity, accuracy signals, actionability,
    technical depth, clarity, originality, hedging level, engagement, and
    formatting.

    Args:
        response: The model response text to evaluate (required)
        query: Optional query/prompt that generated the response
        model: Optional model identifier (e.g., "gpt-4-turbo")

    Returns:
        Dict with:
        - dimensions: dict of 10 scores (0-10 each)
          - completeness: How fully it answers the query
          - specificity: Named entities, numbers, URLs, code
          - accuracy_signals: Citations, data, verifiable claims
          - actionability: Steps, instructions, recommendations
          - technical_depth: Domain expertise demonstrated
          - clarity: Readability, structure, organization
          - originality: Novel insights vs templates
          - hedging_level: Confidence level (inverse hedging)
          - engagement: Interesting, compelling writing
          - formatting: Markdown structure, lists, code blocks
        - total_score: Weighted average (0-10)
        - quality_tier: "poor" | "fair" | "good" | "excellent" | "exceptional"
        - weakest_dimension: Name of lowest-scoring dimension
        - improvement_suggestions: List of 3-5 actionable improvements
        - metadata: Response metadata (length, has_query, model_id)
    """
    scorer = ResponseQualityScorer()
    result = scorer.score(response, query, model)

    logger.info(
        "quality_score_complete response_len=%d total=%.2f tier=%s",
        len(response),
        result["total_score"],
        result["quality_tier"],
    )

    return result
