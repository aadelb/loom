"""Prompt danger pre-scorer for analyzing query risk BEFORE sending to any model.

Analyzes prompt danger/sensitivity across 6 dimensions:
- Topic sensitivity (keyword matching against 12 categories)
- Explicit intent markers ("how to", "step by step", "detailed guide")
- Specificity (named targets, tools, locations, dates)
- Dual-use indicators (could be legitimate research vs harmful)
- Language register (academic vs casual vs threatening)

Returns risk level, detected topics, intent markers, and recommended strategies.
"""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar

try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

logger = logging.getLogger("loom.danger_prescore")


class DangerPreScorer:
    """Analyze prompt danger/sensitivity BEFORE sending to model.

    Scores prompts across multiple dimensions to enable risk-aware routing
    and safety strategy selection.
    """

    # Topic weight matrix: higher = more sensitive
    TOPIC_WEIGHTS: ClassVar = {
        "cbrn": 10,  # Chemical, biological, radiological, nuclear
        "violence": 9,  # Violence, gore, self-harm instructions
        "self_harm": 10,  # Explicit self-harm content
        "csam": 10,  # Child sexual abuse material
        "weapons": 9,  # Weapons manufacturing, instructions
        "hacking": 6,  # Unauthorized system access
        "drugs": 7,  # Illegal drug synthesis, use
        "fraud": 7,  # Fraud, scams, financial crime
        "hate": 8,  # Hate speech, targeting
        "privacy": 6,  # Privacy invasion, doxxing
        "disinfo": 5,  # Disinformation, manipulation
        "manipulation": 4,  # Psychological manipulation, coercion
    }

    # Keyword patterns per topic (compiled for performance)
    TOPIC_PATTERNS: ClassVar = {
        "cbrn": re.compile(
            r"\b(ricin|anthrax|plutonium|uranium|nuke|radioactive|biological|"
            r"chemical|nerve agent|sarin|ebola|smallpox|fentanyl|novichok|"
            r"cbrn|wmd|weapon of mass)\b",
            re.IGNORECASE,
        ),
        "violence": re.compile(
            r"\b(murder|kill|stab|shoot|bomb|behead|torture|rape|assault|mutilate|"
            r"gore|decapitate|dismember|disembowel|violent|beat|batter|strangle)\b",
            re.IGNORECASE,
        ),
        "self_harm": re.compile(
            r"\b(suicide|hang|overdose|cut myself|slit wrist|jump off|poison|"
            r"self.harm|self.injury|harm myself|end my life)\b",
            re.IGNORECASE,
        ),
        "csam": re.compile(
            r"\b(child sexual|child abuse|csam|child porn|underage|minor sexual|"
            r"pedophile|pedophilia|cp|lolita)\b",
            re.IGNORECASE,
        ),
        "weapons": re.compile(
            r"\b(explosives?|bombs?|guns?|rifles?|weapons?|ied|c4|tnt|dynamites?|grenades?|"
            r"landmines?|flamethrowers?|missiles?|ammunition|gunpowder|"
            r"improvised|detonators?|triggers?|make bomb|create explosive|build bomb)\b",
            re.IGNORECASE,
        ),
        "hacking": re.compile(
            r"\b(hacks?|hack(?:ing|ed)?|exploits?|vulnerab|bypass|crack|brute force|"
            r"sql injection|malware|ransomware|trojan|ddos|phishing|"
            r"zero.day|unauthorized access|breach|compromise)\b",
            re.IGNORECASE,
        ),
        "drugs": re.compile(
            r"\b(cocaine|heroin|meth|fentanyl|lsd|mdma|crack|cannabis|marijuana|"
            r"synthesize|cook|extract|synthesis|manufacture|illegal drug|"
            r"controlled substance)\b",
            re.IGNORECASE,
        ),
        "fraud": re.compile(
            r"\b(scam|fraud|forgery|counterfeit|money launder|embezzle|"
            r"ponzi|wire fraud|tax evasion|insider trading|phishing|"
            r"financial crime|swindle|defraud)\b",
            re.IGNORECASE,
        ),
        "hate": re.compile(
            r"\b(hate speech|racist|supremacist|racial slur|ethnic|genocide|"
            r"dehumanize|discriminate|bigot|intolerance|antisemit|islamophob)\b",
            re.IGNORECASE,
        ),
        "privacy": re.compile(
            r"\b(doxx|home address|phone number|ssn|social security|"
            r"credit card|bank account|leak|publish personal|personal info|"
            r"identity theft|stalk|harassment)\b",
            re.IGNORECASE,
        ),
        "disinfo": re.compile(
            r"\b(deepfake|fake news|misinformation|disinformation|hoax|"
            r"conspiracy|false flag|fabricate|false narrative|manipulate)\b",
            re.IGNORECASE,
        ),
        "manipulation": re.compile(
            r"\b(manipulate|persuade|coerce|blackmail|extort|control|hypnosis|"
            r"brainwash|cult|isolation|abuse|gaslighting|influence)\b",
            re.IGNORECASE,
        ),
    }

    # Explicit intent markers (dangerous action indicators)
    INTENT_PATTERNS: ClassVar = {
        "howto": re.compile(
            r"\b(how to|how do i|steps to|guide to|instructions|"
            r"tell me|teach|walk through|procedure|process)\b",
            re.IGNORECASE,
        ),
        "stepwise": re.compile(
            r"\b(step by step|detailed|comprehensive|complete|full|"
            r"start to finish|beginning to end|breakdown|detailed guide)\b",
            re.IGNORECASE,
        ),
        "request": re.compile(
            r"\b(can you|will you|would you|please|could you|help me|"
            r"i need|i want|show me|give me|provide|create|make)\b",
            re.IGNORECASE,
        ),
        "actual": re.compile(
            r"\b(actually|really|truly|for real|in practice|real world|"
            r"genuine|authentic|legitimate|working|functional)\b",
            re.IGNORECASE,
        ),
        "urgency": re.compile(
            r"\b(urgent|asap|immediately|quickly|fast|before|deadline|"
            r"time sensitive|no time|hurry|emergency)\b",
            re.IGNORECASE,
        ),
    }

    # Academic/legitimate research markers (dual-use indicator)
    ACADEMIC_PATTERNS: ClassVar = re.compile(
        r"\b(research|study|academic|scientific|educational|analysis|"
        r"literature|hypothesis|methodology|experiment|evidence|"
        r"published|peer.review|journal|thesis|university|institution|"
        r"defense|security|protection|safeguard|threat model|assessment)\b",
        re.IGNORECASE,
    )

    # Casual/threatening language patterns
    THREATENING_PATTERNS: ClassVar = re.compile(
        r"\b(gonna|wanna|imma|ur|omg|wtf|lol|yo|ayo|bruh|dude|"
        r"gonna get|going to|threat|fuck|shit|damn|pissed|mad)\b",
        re.IGNORECASE,
    )

    # Specificity patterns (named targets, tools, locations, dates)
    SPECIFICITY_PATTERNS: ClassVar = {
        "named_entity": re.compile(
            r"\b([A-Z][a-z]+ [A-Z][a-z]+|[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)\b"
        ),  # Person names
        "location": re.compile(
            r"\b(street|avenue|road|boulevard|lane|drive|plaza|building|"
            r"floor|suite|apt|apartment|address|location|city|state)\b",
            re.IGNORECASE,
        ),
        "date": re.compile(
            r"\b(\d{1,2}/\d{1,2}/\d{2,4}|january|february|march|april|"
            r"may|june|july|august|september|october|november|december|"
            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
            r"spring|summer|fall|winter)\b",
            re.IGNORECASE,
        ),
        "tool": re.compile(
            r"\b(tool|software|hardware|device|weapon|substance|chemical|"
            r"material|component|application|framework|library|system)\b",
            re.IGNORECASE,
        ),
    }

    def prescore(self, prompt: str) -> dict[str, Any]:
        """Score prompt danger BEFORE sending to any model.

        Args:
            prompt: The user prompt to analyze

        Returns:
            Dict containing:
            - danger_score: float (0-10, where 10 is most dangerous)
            - risk_level: "safe" | "low" | "medium" | "high" | "critical"
            - detected_topics: list of {topic, score, count}
            - intent_markers: list of {marker, count}
            - specificity_score: float (0-1, higher = more specific)
            - dual_use_probability: float (0-1, higher = more likely legitimate research)
            - language_register: "academic" | "casual" | "threatening" | "neutral"
            - recommended_strategies: list of str (safety/routing strategies)
            - recommended_model: str (model most suited for this danger level)
            - api_params: dict (temperature, top_p recommendations)
        """
        logger.info("prescore_start prompt_len=%d", len(prompt))

        # Detect topics and calculate topic score
        detected_topics, topic_score = self._detect_topics(prompt)

        # Detect intent markers
        intent_markers = self._detect_intent_markers(prompt)
        intent_score = clamp(len(intent_markers) * 2.0, 0.0, 10.0)  # Each marker adds 2 points

        # Calculate specificity
        specificity_score = self._calculate_specificity(prompt)
        specificity_danger = clamp(specificity_score * 3.0, 0.0, 3.0)  # Specificity up to 3 points of danger

        # Evaluate dual-use (legitimate research vs harmful)
        dual_use_probability = self._calculate_dual_use_probability(prompt, detected_topics)

        # Language register analysis
        language_register = self._analyze_language_register(prompt)
        language_danger = 2.0 if language_register == "threatening" else 0.0

        # Calculate final danger score (weighted average)
        # Reduce danger if high dual-use probability (legitimate research)
        raw_danger = topic_score + intent_score + specificity_danger + language_danger
        danger_score = clamp(raw_danger * (1.0 - dual_use_probability * 0.4), 0.0, 10.0)  # -40% max

        # Determine risk level
        risk_level = self._score_to_risk_level(danger_score)

        # Recommend strategies
        recommended_strategies = self._recommend_strategies(
            risk_level, detected_topics, intent_markers, dual_use_probability
        )

        # Recommend model based on danger level
        recommended_model = self._recommend_model(risk_level, dual_use_probability)

        # Recommend API parameters
        api_params = self._recommend_api_params(risk_level)

        result = {
            "danger_score": round(danger_score, 2),
            "risk_level": risk_level,
            "detected_topics": detected_topics,
            "intent_markers": intent_markers,
            "specificity_score": round(specificity_score, 2),
            "dual_use_probability": round(dual_use_probability, 2),
            "language_register": language_register,
            "recommended_strategies": recommended_strategies,
            "recommended_model": recommended_model,
            "api_params": api_params,
        }

        logger.info(
            "prescore_complete danger=%.2f risk=%s topics=%d intents=%d dual_use=%.2f",
            danger_score,
            risk_level,
            len(detected_topics),
            len(intent_markers),
            dual_use_probability,
        )

        return result

    def _detect_topics(self, prompt: str) -> tuple[list[dict[str, Any]], float]:
        """Detect dangerous topics and their scores.

        Returns:
            Tuple of (detected_topics, total_score)
        """
        detected_topics: list[dict[str, Any]] = []
        total_score = 0.0

        for topic, pattern in self.TOPIC_PATTERNS.items():
            matches = pattern.findall(prompt)
            if matches:
                count = len(matches)
                weight = self.TOPIC_WEIGHTS[topic]
                # Score: weight * min(count, 3) / 10 (cap at 3 occurrences for scoring)
                score = weight * min(count, 3) / 10.0
                total_score += score
                detected_topics.append(
                    {"topic": topic, "score": round(score, 2), "count": count}
                )

        return detected_topics, clamp(total_score, 0.0, 10.0)

    def _detect_intent_markers(self, prompt: str) -> list[dict[str, Any]]:
        """Detect explicit intent markers (dangerous action indicators)."""
        intent_markers: list[dict[str, Any]] = []

        for marker_type, pattern in self.INTENT_PATTERNS.items():
            matches = pattern.findall(prompt)
            if matches:
                intent_markers.append(
                    {"type": marker_type, "count": len(matches), "examples": matches[:3]}
                )

        return intent_markers

    def _calculate_specificity(self, prompt: str) -> float:
        """Calculate specificity score (0-1, higher = more specific/targeted)."""
        specificity_score = 0.0

        # Count named entities
        named_matches = self.SPECIFICITY_PATTERNS["named_entity"].findall(prompt)
        specificity_score += clamp(len(named_matches) * 0.15, 0.0, 0.25)  # max 0.25

        # Count location references
        location_matches = self.SPECIFICITY_PATTERNS["location"].findall(prompt)
        specificity_score += clamp(len(location_matches) * 0.2, 0.0, 0.25)  # max 0.25

        # Count date references
        date_matches = self.SPECIFICITY_PATTERNS["date"].findall(prompt)
        specificity_score += clamp(len(date_matches) * 0.15, 0.0, 0.25)  # max 0.25

        # Count tool/substance references
        tool_matches = self.SPECIFICITY_PATTERNS["tool"].findall(prompt)
        specificity_score += clamp(len(tool_matches) * 0.1, 0.0, 0.25)  # max 0.25

        return clamp(specificity_score, 0.0, 1.0)

    def _calculate_dual_use_probability(
        self, prompt: str, detected_topics: list[dict[str, Any]]
    ) -> float:
        """Estimate probability that query is legitimate dual-use research.

        Returns:
            float (0-1, higher = more likely legitimate)
        """
        if not detected_topics:
            return 0.0  # No dangerous topics = automatically legitimate

        # Count academic language
        academic_matches = self.ACADEMIC_PATTERNS.findall(prompt)
        academic_density = len(academic_matches) / max(len(prompt.split()), 1)

        # Bonus points for research language
        dual_use_score = 0.0
        if academic_density > 0.03:  # >3% academic terms
            dual_use_score += 0.4
        if academic_density > 0.08:  # >8% academic terms
            dual_use_score += 0.3

        # Check for legitimate use cases
        legitimate_phrases = [
            "research", "study", "academic", "educational", "analysis",
            "understanding", "literature", "methodological", "peer-review",
            "published", "safety", "threat model", "defense", "assessment",
            "protection", "vulnerability", "security"
        ]
        for phrase in legitimate_phrases:
            if phrase.lower() in prompt.lower():
                dual_use_score += 0.15

        return clamp(dual_use_score, 0.0, 1.0)

    def _analyze_language_register(self, prompt: str) -> str:
        """Analyze language register (academic, casual, threatening, neutral)."""
        threatening_matches = self.THREATENING_PATTERNS.findall(prompt)
        academic_matches = self.ACADEMIC_PATTERNS.findall(prompt)

        # Count matches
        word_count = max(len(prompt.split()), 1)
        threatening_density = len(threatening_matches) / word_count
        academic_density = len(academic_matches) / word_count

        if threatening_density > 0.08:
            return "threatening"
        elif academic_density > 0.08:
            return "academic"
        elif threatening_density > 0.02:
            return "casual"
        else:
            return "neutral"

    def _score_to_risk_level(self, danger_score: float) -> str:
        """Convert danger score to risk level."""
        if danger_score >= 8.5:
            return "critical"
        elif danger_score >= 7.0:
            return "high"
        elif danger_score >= 5.0:
            return "medium"
        elif danger_score >= 2.5:
            return "low"
        else:
            return "safe"

    def _recommend_strategies(
        self,
        risk_level: str,
        detected_topics: list[dict[str, Any]],
        intent_markers: list[dict[str, Any]],
        dual_use_probability: float,
    ) -> list[str]:
        """Recommend safety/routing strategies."""
        strategies: list[str] = []

        if dual_use_probability > 0.6:
            strategies.append("allow_with_context")  # Legitimate research
            strategies.append("add_disclaimers")
        elif risk_level == "safe":
            strategies.append("allow")
        elif risk_level == "low":
            strategies.append("allow_with_guardrails")
            strategies.append("require_authentication")
        elif risk_level == "medium":
            strategies.append("require_audit_log")
            strategies.append("add_safety_preamble")
            strategies.append("limit_iterations")
            if intent_markers:
                strategies.append("reject_or_reframe")
        elif risk_level == "high":
            strategies.append("require_review")
            strategies.append("reject_by_default")
            strategies.append("escalate_to_human")
        elif risk_level == "critical":
            strategies.append("immediate_rejection")
            strategies.append("alert_security")
            strategies.append("log_attempt")

        return strategies

    def _recommend_model(self, risk_level: str, dual_use_probability: float) -> str:
        """Recommend which model is most likely to comply with this query."""
        if risk_level == "safe":
            return "any"  # All models safe

        if dual_use_probability > 0.5:
            return "gpt-4"  # GPT-4 good for legitimate research

        # By risk level, which model is most strict?
        if risk_level in ("high", "critical"):
            return "claude"  # Claude more aligned for harmful content

        # Default
        return "mixed"  # Recommend testing multiple models

    def _recommend_api_params(self, risk_level: str) -> dict[str, float]:
        """Recommend API parameters (temperature, top_p) by risk level."""
        params = {
            "temperature": 0.7,
            "top_p": 0.9,
        }

        if risk_level == "safe":
            params["temperature"] = 0.9
            params["top_p"] = 1.0
        elif risk_level == "low":
            params["temperature"] = 0.8
            params["top_p"] = 0.95
        elif risk_level == "medium":
            params["temperature"] = 0.7
            params["top_p"] = 0.9
        elif risk_level == "high":
            params["temperature"] = 0.3
            params["top_p"] = 0.7
        elif risk_level == "critical":
            params["temperature"] = 0.0
            params["top_p"] = 0.5

        return {k: round(v, 2) for k, v in params.items()}


# Global instance for use as MCP tool
_scorer = DangerPreScorer()


async def research_danger_prescore(prompt: str) -> dict[str, Any]:
    """Analyze prompt danger BEFORE sending to any model.

    Scores prompts across multiple dimensions to enable risk-aware routing
    and safety strategy selection.

    Args:
        prompt: The user prompt to analyze for danger/sensitivity

    Returns:
        Dict containing:
        - danger_score: float (0-10, where 10 is most dangerous)
        - risk_level: "safe" | "low" | "medium" | "high" | "critical"
        - detected_topics: list of {topic, score, count}
        - intent_markers: list of {marker, count}
        - specificity_score: float (0-1)
        - dual_use_probability: float (0-1, higher = more likely legitimate research)
        - language_register: "academic" | "casual" | "threatening" | "neutral"
        - recommended_strategies: list of str
        - recommended_model: str
        - api_params: dict (temperature, top_p)
    """
    return _scorer.prescore(prompt)
