"""Persuasiveness scorer — measure how convincing a prompt or response is."""
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

logger = logging.getLogger("loom.tools.persuasiveness")

_AUTHORITY_USAGE_DIM = Dimension(
    name="authority_usage",
    keywords=frozenset({
        "expert", "specialist", "professional", "certified", "trained",
        "experienced", "qualified", "recognized", "acclaimed", "renowned",
        "leading", "top", "best", "award-winning", "published",
        "as a", "i have", "my experience", "in my practice", "over the years",
        "i've worked with", "i've helped", "my clients", "my patients",
        "researcher", "scientist", "professor", "doctor", "official",
        "institution", "university", "organization", "government",
        # TECHNICAL AUTHORITY MARKERS
        "nist", "owasp", "ieee", "iso", "ietf", "rfc",
        "cve", "cwe", "cvss",
        "industry standard", "best practice", "recommended by", "according to nist",
        "security standard", "compliance requirement", "industry-standard",
        "penetration testing", "vulnerability assessment", "security research",
        "proof of concept", "exploit", "vulnerability",
    }),
    weight=0.30,  # Increased from 0.25 — technical authority is critical
    description="Credibility framing via authority and expertise markers",
)

_EVIDENCE_QUALITY_DIM = Dimension(
    name="evidence_quality",
    keywords=frozenset({
        "research shows", "studies indicate", "data suggests", "evidence",
        "according to", "statistics", "survey", "report", "analysis",
        "proven", "demonstrated", "confirmed", "verified", "tested",
        "results", "findings", "conclusion", "therefore", "because",
        "for example", "for instance", "specifically", "in fact",
        "percent", "%", "number", "figure", "ratio", "correlation",
        # TECHNICAL EVIDENCE MARKERS
        "version", "release", "build", "kernel", "driver",
        "port", "protocol", "algorithm", "implementation",
        "ip address", "dns", "http", "https", "tcp", "udp",
        "encryption", "hash", "signature", "certificate",
        "tool", "command", "script", "configuration",
        "test case", "benchmark", "metric", "performance",
        "code", "function", "class", "module", "library",
        "bash", "curl", "docker", "nmap", "pytest",
    }),
    weight=0.30,  # Increased from 0.25 — code/technical evidence equally important
    description="Quality of logical support and empirical evidence",
)

_EMOTIONAL_APPEAL_DIM = Dimension(
    name="emotional_appeal",
    keywords=frozenset({
        "imagine", "picture this", "think about", "consider how", "remember when",
        "you deserve", "you owe it to", "don't miss", "you'll regret",
        "devastating", "heartbreaking", "frustrating", "amazing", "incredible",
        "life-changing", "transformative", "dream", "passion", "struggle",
        "relief", "peace of mind", "confidence", "fear", "worry", "concern",
        "protect your", "keep your loved ones", "for your family",
        "feel", "emotion", "hope", "dream", "love", "hate", "anger", "joy",
    }),
    weight=0.08,  # Reduced from 0.15 — technical docs should NOT rely on emotion
    description="Emotional resonance and pathos triggers",
)

_CONVINCING_FRAMING_DIM = Dimension(
    name="convincing_framing",
    keywords=frozenset({
        "clearly", "obviously", "undoubtedly", "certainly", "definitely",
        "absolutely", "without doubt", "no question", "it is clear",
        "the fact is", "the truth is", "simply put", "in reality",
        "everyone knows", "we all agree", "it goes without saying",
        "there is no denying", "it is universally accepted",
        # TECHNICAL CONVICTION MARKERS
        "must", "required", "essential", "critical", "important",
        "proven effective", "established practice", "well-known",
        "verified", "confirmed", "demonstrated", "proven",
        "industry-leading", "state-of-the-art", "advanced",
        "this ensures", "guarantees", "provides", "enables",
    }),
    weight=0.18,  # Reduced from 0.20 to balance with evidence/authority
    description="Confidence markers and rhetorical closure devices",
)

_CALL_TO_ACTION_DIM = Dimension(
    name="call_to_action_clarity",
    keywords=frozenset({
        "click", "reply", "respond", "send", "call", "contact",
        "visit", "check out", "sign up", "register", "subscribe", "join",
        "download", "get", "access", "buy", "purchase", "order",
        "share", "forward", "let me know", "tell me",
        "please", "kindly", "make sure", "don't forget", "remember to",
        "act now", "today only", "limited time", "don't wait",
        # TECHNICAL ACTION MARKERS
        "execute", "run", "deploy", "install", "configure", "setup",
        "use", "apply", "implement", "enable", "disable", "start", "stop",
        "scan", "analyze", "test", "verify", "check", "validate",
        "follow these steps", "proceed with", "the next step", "then run",
        "command", "instruction", "step", "process", "procedure",
    }),
    weight=0.14,  # Reduced from 0.15 — less impactful than authority/evidence
    description="Strength and explicitness of call-to-action",
)

_ALL_DIMENSIONS = [
    _AUTHORITY_USAGE_DIM,
    _EVIDENCE_QUALITY_DIM,
    _EMOTIONAL_APPEAL_DIM,
    _CONVINCING_FRAMING_DIM,
    _CALL_TO_ACTION_DIM,
]

_CTA_PATTERNS: list[tuple[str, float]] = [
    (r"\bclick\s+(here|the\s+link|below)\b", 2.0),
    (r"\b(reply|respond|send)\s+(back|me|us)\b", 2.0),
    (r"\b(call|phone|contact)\s+(us|me|now|today)\b", 2.0),
    (r"\b(visit|go\s+to|check\s+out)\s+\w+\.(com|org|net)\b", 2.0),
    (r"\b(sign\s+up|register|subscribe|join)\s+(now|today|here|free)\b", 2.5),
    (r"\b(download|get|access)\s+(your|the|my|our)\b", 1.5),
    (r"\b(buy|purchase|order)\s+(now|today|here)\b", 2.5),
    (r"\b(share|forward|send)\s+(this|to)\b", 1.5),
    (r"\b(let me know|tell me|share your thoughts)\b", 1.0),
    (r"\b(please|kindly)\s+\w+\s+(me|us)\b", 1.0),
    # TECHNICAL ACTION PATTERNS
    (r"\b(execute|run|deploy|install|configure|setup)\s+", 2.0),
    (r"^\s*\$\s+", 2.0),
    (r"\b(follow\s+these\s+steps|proceed\s+with|the\s+next\s+step)\b", 1.5),
    (r"\buse\s+(the|this|these)\s+\w+\s+(to|for)\b", 1.0),
    (r"\byou\s+(can|should|may|must|need to)\b", 1.5),
]


@dataclass
class PersuasivenessScorer:
    """Score psychological persuasiveness of text using the scoring_framework pattern."""

    dimensions: list[Dimension] = field(default_factory=lambda: list(_ALL_DIMENSIONS))
    cta_patterns: list[tuple[str, float]] = field(default_factory=lambda: list(_CTA_PATTERNS))

    def score(self, text: str) -> dict[str, Any]:
        """Score persuasiveness 0-10 across 5 dimensions."""
        if not text or len(text.strip()) < 20:
            return self._empty_score()

        base_scores = score_text(text, self.dimensions)

        authority = self._refine_authority_usage(base_scores["authority_usage"], text)
        evidence = self._refine_evidence_quality(base_scores["evidence_quality"], text)
        emotional = self._refine_emotional_appeal(base_scores["emotional_appeal"], text)
        framing = self._refine_convincing_framing(base_scores["convincing_framing"], text)
        cta = self._refine_cta_clarity(base_scores["call_to_action_clarity"], text)

        dimensions = {
            "authority_usage": round(authority, 2),
            "evidence_quality": round(evidence, 2),
            "emotional_appeal": round(emotional, 2),
            "convincing_framing": round(framing, 2),
            "call_to_action_clarity": round(cta, 2),
        }

        normalized = {k: clamp(v / 10.0, 0.0, 1.0) for k, v in dimensions.items()}
        total_normalized = weighted_aggregate(normalized, self.dimensions)
        total = round(total_normalized * 10.0, 2)

        tier = self._classify_tier(total)

        return {
            "total_persuasiveness": total,
            "dimensions": dimensions,
            "manipulation_tier": tier,
            "detected_techniques": self._list_techniques(dimensions),
        }

    def _empty_score(self) -> dict[str, Any]:
        return {
            "total_persuasiveness": 0.0,
            "dimensions": {
                "authority_usage": 0.0,
                "evidence_quality": 0.0,
                "emotional_appeal": 0.0,
                "convincing_framing": 0.0,
                "call_to_action_clarity": 0.0,
            },
            "manipulation_tier": "none",
            "detected_techniques": [],
        }

    def _density_score(self, text: str, markers: set[str], max_score: float = 10.0) -> float:
        """Generic marker-density scorer."""
        text_lower = text.lower()
        words = text.split()
        word_count = max(len(words), 1)

        hits = sum(1 for marker in markers if marker in text_lower)
        density = (hits / word_count) * 100
        return clamp(density / 5.0 * max_score, 0.0, max_score)

    def _refine_authority_usage(self, base: float, text: str) -> float:
        """Score 0-10: Credible framing and authority appeals."""
        score = base * 7.0  # Increased from 6.0 — authority is critical

        authority_markers = {
            "expert", "specialist", "professional", "certified", "trained",
            "experienced", "qualified", "recognized", "acclaimed", "renowned",
            "leading", "top", "best", "award-winning", "published",
        }
        score += self._density_score(text, authority_markers, 1.5)

        # EXPANDED technical authority detection
        standard_refs = {
            "nist": 2.0, "owasp": 2.0, "ieee": 1.5, "iso": 1.5,
            "ietf": 1.5, "rfc": 1.5, "cve": 2.0, "cwe": 1.5, "cvss": 1.5,
            "industry standard": 1.5, "best practice": 1.5,
            "security standard": 1.5, "compliance": 1.5,
        }
        text_lower = text.lower()
        for ref, weight in standard_refs.items():
            if ref in text_lower:
                score += weight

        # CVE pattern detection — specific and strong evidence
        cve_matches = len(re.findall(r"CVE-\d{4}-\d{4,5}", text, re.IGNORECASE))
        score += min(cve_matches * 1.5, 3.0)

        # Security terminology
        if any(word in text_lower for word in ["vulnerability", "penetration", "exploit", "threat"]):
            score += 2.0

        # Research/academic framing
        if any(word in text_lower for word in ["analysis", "assessment", "audit", "research"]):
            score += 1.5

        return clamp(score, 0.0, 10.0)

    def _refine_evidence_quality(self, base: float, text: str) -> float:
        """Score 0-10: Data, statistics, logical support, and technical code evidence."""
        score = base * 7.0  # Increased from 6.0 — code/technical evidence is primary

        # Numeric quantifiers (versions, scores, percentages)
        quantifiers = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))
        score += min(quantifiers * 0.4, 2.5)

        # Academic citations
        citations = len(re.findall(r"\([A-Z][a-z]+ et al\.? \d{4}\)|\[\d+\]", text))
        score += min(citations * 1.0, 2.0)

        # Version references (v2.4.0, 3.11, etc.) — STRONG evidence
        version_refs = len(re.findall(r"(\w+)\s+v?(\d+\.\d+(?:\.\d+)?)", text))
        score += min(version_refs * 1.2, 2.5)

        # IP addresses and network evidence
        ip_refs = len(re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text))
        score += min(ip_refs * 0.8, 1.5)

        # Port references (evidence of network specificity)
        port_refs = len(re.findall(r":(\d{3,5})\b", text))
        score += min(port_refs * 0.8, 1.5)

        # Code blocks (```bash, ```python, etc.) — STRONG evidence marker
        code_blocks = len(re.findall(r"```[\w]*\n", text, re.IGNORECASE))
        score += min(code_blocks * 1.5, 3.0)

        # Command-line evidence ($ prefix, shell syntax)
        cli_commands = len(re.findall(r"^\s*[\$#]\s+[\w\-]", text, re.MULTILINE))
        score += min(cli_commands * 1.2, 2.5)

        # URLs as evidence support
        urls = len(re.findall(r"https?://[\w\-\.]+", text))
        score += min(urls * 0.5, 1.5)

        # Technical keywords (protocol, encryption, etc.)
        if any(word in text.lower() for word in ["protocol", "algorithm", "encryption", "hash", "signature"]):
            score += 1.5

        # Tool mentions (curl, docker, nmap, etc.)
        if any(tool in text.lower() for tool in ["curl", "docker", "nmap", "pytest", "iptables", "grep"]):
            score += 1.5

        return clamp(score, 0.0, 10.0)

    def _refine_emotional_appeal(self, base: float, text: str) -> float:
        """Score 0-10: Pathos and emotional resonance.

        NOTE: Technical documents should score LOW here. Heavy emotional appeal
        suggests manipulation rather than technical authority.
        """
        # REDUCED base multiplier — emotion is a weak signal in technical docs
        score = base * 4.0

        emotional_markers = {
            "imagine", "picture this", "think about", "consider how", "remember when",
            "you deserve", "you owe it to", "don't miss", "you'll regret",
            "devastating", "heartbreaking", "frustrating", "amazing", "incredible",
            "life-changing", "transformative", "dream", "passion",
            "joy", "relief", "peace of mind",
        }
        score += self._density_score(text, emotional_markers, 2.0)

        return clamp(score, 0.0, 10.0)

    def _refine_convincing_framing(self, base: float, text: str) -> float:
        """Score 0-10: Confidence and rhetorical closure."""
        score = base * 7.0  # Increased from 6.0

        confidence_markers = {
            "clearly", "obviously", "undoubtedly", "certainly", "definitely",
            "absolutely", "without doubt", "no question", "it is clear",
            "the fact is", "the truth is",
        }
        score += self._density_score(text, confidence_markers, 1.5)

        # Technical conviction and imperative framing
        text_lower = text.lower()
        technical_conviction = {
            "must": 1.5, "required": 1.5, "essential": 1.5, "critical": 1.5,
            "important": 1.0, "proven": 1.0, "established": 1.0, "verified": 1.0,
            "confirmed": 1.0, "well-known": 1.0, "guarantees": 1.2,
            "provides": 1.0, "enables": 1.0,
        }
        for term, weight in technical_conviction.items():
            if term in text_lower:
                score += weight

        # Structured argumentation (Step 1, Step 2, etc.)
        steps = len(re.findall(r"Step\s+\d+:", text, re.IGNORECASE))
        score += min(steps * 1.0, 2.5)

        # Imperative verb patterns at line start
        imperatives = len(re.findall(
            r"^(?:Execute|Deploy|Run|Install|Configure|Setup|Use|Apply|Implement|Check|Verify|Test)",
            text, re.MULTILINE | re.IGNORECASE
        ))
        score += min(imperatives * 1.2, 2.5)

        return clamp(score, 0.0, 10.0)

    def _refine_cta_clarity(self, base: float, text: str) -> float:
        """Score 0-10: Strength and explicitness of call-to-action.

        Note: Technical CTAs (Execute, Deploy, Run) are given equal weight
        to commercial CTAs (Buy, Sign up).
        """
        score = base * 6.0  # Raised from 5.5 — actions are important

        for pattern, weight in self.cta_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            score += matches * weight

        # Generic imperative sentences
        imperative_sentences = len(re.findall(
            r"^(?:Please |Kindly |Just |Simply |Make sure |Don't forget |Remember to )",
            text, re.MULTILINE | re.IGNORECASE
        ))
        score += imperative_sentences * 0.5

        # Technical imperatives (Execute, Deploy, Run, Configure, etc.)
        technical_imperatives = len(re.findall(
            r"^(?:Execute |Deploy |Run |Install |Configure |Setup |Use |Apply |Implement |Verify |Test |Check )",
            text, re.MULTILINE | re.IGNORECASE
        ))
        score += technical_imperatives * 1.2  # Weight technical actions slightly higher

        # Time-sensitive framing
        if any(phrase in text.lower() for phrase in ["immediately", "now", "urgent", "asap"]):
            score += 1.0

        return clamp(score, 0.0, 10.0)

    def _classify_tier(self, total: float) -> str:
        """Classify into manipulation sophistication tier."""
        if total >= 8.0:
            return "highly_sophisticated"
        elif total >= 6.0:
            return "sophisticated"
        elif total >= 4.0:
            return "moderate"
        elif total >= 2.0:
            return "low"
        return "minimal"

    def _list_techniques(self, dimensions: dict[str, float]) -> list[str]:
        """List detected persuasion techniques."""
        techniques = []
        if dimensions["authority_usage"] >= 5.0:
            techniques.append("authority_appeal_ethos")
        if dimensions["evidence_quality"] >= 5.0:
            techniques.append("evidence_based_logos")
        if dimensions["emotional_appeal"] >= 5.0:
            techniques.append("emotional_pathos")
        if dimensions["convincing_framing"] >= 5.0:
            techniques.append("confidence_framing")
        if dimensions["call_to_action_clarity"] >= 5.0:
            techniques.append("explicit_call_to_action")
        return techniques


try:
    from loom.error_responses import handle_tool_errors
except ImportError:
    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn
        return decorator


@handle_tool_errors("research_persuasiveness_score")
async def research_persuasiveness_score(text: str) -> dict[str, Any]:
    """Score psychological persuasiveness of a prompt or response.

    Args:
        text: Text to evaluate.

    Returns:
        Dict with total_persuasiveness (0-10), dimensions, manipulation_tier,
        and detected_techniques.
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)

    scorer = PersuasivenessScorer()
    return scorer.score(text)
