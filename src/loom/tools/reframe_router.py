"""Smart router that classifies queries and routes to reframing or integration tools.

This tool analyzes user queries to determine whether they need:
1. Reframing strategies (LLM-based jailbreaks, prompt techniques)
2. Tool integrations (data fetching, scraping, searching)
3. Both (complex queries needing strategies + external data)

The router uses keyword heuristics, dangerous pattern detection, and
data-oriented intent recognition to make intelligent routing decisions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

from loom.tools.reframe_strategies import ALL_STRATEGIES

log = logging.getLogger("loom.tools.reframe_router")


@dataclass(frozen=True)
class RouterDecision:
    """Immutable routing decision result."""

    decision: Literal["reframe", "integrate", "both"]
    confidence: float
    suggested_tools: list[str]
    suggested_strategies: list[str]
    reasoning: str
    query_intent: str
    detected_patterns: list[str]


class ReframeRouter:
    """Intelligent router for reframing vs. integration decisions."""

    # Keywords indicating refusal resistance / bypass needs
    REFRAMING_KEYWORDS = {
        "how to": 0.9,
        "bypass": 0.95,
        "jailbreak": 0.95,
        "circumvent": 0.90,
        "evade": 0.85,
        "exploit": 0.85,
        "vulnerability": 0.80,
        "unauthorized": 0.85,
        "illegal": 0.80,
        "malware": 0.75,
        "hack": 0.85,
        "crack": 0.85,
        "unethical": 0.70,
        "dangerous": 0.70,
        "forbidden": 0.80,
        "restricted": 0.75,
        "can you help me": 0.60,
        "can you do this": 0.60,
        "can you tell me": 0.40,
        "explain how": 0.75,
        "teach me": 0.65,
        "guide me": 0.60,
        "without detection": 0.90,
        "without getting caught": 0.95,
        "covertly": 0.85,
        "secretly": 0.80,
        "anonymously": 0.70,
        "undetected": 0.85,
        "without consent": 0.90,
        "resistance": 0.75,
        "refuse": 0.70,
        "won't": 0.70,
        "shouldn't": 0.65,
    }

    # Keywords indicating tool/data integration needs
    INTEGRATION_KEYWORDS = {
        "find": 0.85,
        "search": 0.90,
        "look up": 0.85,
        "discover": 0.80,
        "fetch": 0.90,
        "scrape": 0.95,
        "crawl": 0.90,
        "analyze": 0.70,
        "monitor": 0.75,
        "track": 0.80,
        "extract": 0.85,
        "identify": 0.75,
        "locate": 0.85,
        "list": 0.80,
        "enumerate": 0.85,
        "query": 0.85,
        "get information": 0.80,
        "retrieve": 0.85,
        "obtain": 0.80,
        "collect": 0.85,
        "gather": 0.85,
        "check": 0.70,
        "verify": 0.70,
        "validate": 0.70,
        "scan": 0.85,
        "probe": 0.80,
        "research": 0.75,
        "investigate": 0.75,
        "explore": 0.70,
        "examine": 0.70,
        "test": 0.65,
        "benchmark": 0.70,
        "compare": 0.65,
        "trending": 0.70,
        "latest": 0.70,
        "recent": 0.70,
        "top": 0.65,
    }

    # Dangerous patterns that strongly suggest refusal attempt
    DANGEROUS_PATTERNS = [
        r"how to create.*malware",
        r"how to .*exploit.*vulnerability",
        r"how to .*hack.*system",
        r"how to bypass.*security",
        r"how to crack.*password",
        r"how to build.*virus",
        r"how to launch.*attack",
        r"how to perform.*phishing",
        r"help.*illegal.*activity",
        r"guide.*unethical.*conduct",
        r"teach.*unauthorized.*access",
        r"without.*consent",
        r"without.*detection",
        r"covert.*operation",
        r"evade.*detection",
        r"bypass.*filter",
        r"circumvent.*protection",
    ]

    # Tool recommendations for integration category
    INTEGRATION_TOOLS = {
        "web_scraping": [
            "research_fetch",
            "research_spider",
            "research_markdown",
            "research_camoufox",
            "research_botasaurus",
        ],
        "search": [
            "research_search",
            "research_multi_search",
            "research_deep",
        ],
        "osint": [
            "research_passive_recon",
            "research_identity_resolve",
            "research_social_graph",
            "research_whois",
            "research_dns_lookup",
        ],
        "code": [
            "research_github",
        ],
        "academic": [
            "research_arxiv_search",
            "research_wikipedia_search",
        ],
        "monitoring": [
            "research_rss_monitor",
            "research_change_monitor",
            "research_darkweb_early_warning",
        ],
    }

    # Strategy recommendations for reframing category
    REFRAMING_STRATEGIES = {
        "jailbreak": [s for s in ALL_STRATEGIES.keys() if "jailbreak" in s.lower()][:5],
        "encoding": [s for s in ALL_STRATEGIES.keys() if "encoding" in s.lower()][:5],
        "reasoning": [s for s in ALL_STRATEGIES.keys() if "reasoning" in s.lower()][:5],
        "persona": [s for s in ALL_STRATEGIES.keys() if "persona" in s.lower()][:5],
        "novel": [s for s in ALL_STRATEGIES.keys() if "novel" in s.lower()][:5],
    }

    def __init__(self) -> None:
        """Initialize the router with keyword and pattern analysis."""
        self.router = self

    @staticmethod
    def _score_keyword_match(
        text: str, keywords: dict[str, float]
    ) -> tuple[float, list[str]]:
        """Score text against keyword dictionary, return (score, matched_keywords).

        Args:
            text: Text to analyze
            keywords: Dict mapping keywords to match scores

        Returns:
            Tuple of (average_score, list_of_matched_keywords)
        """
        text_lower = text.lower()
        matched = []
        scores = []

        for keyword, score in keywords.items():
            if keyword in text_lower:
                matched.append(keyword)
                scores.append(score)

        avg_score = sum(scores) / len(scores) if scores else 0.0
        return avg_score, matched

    @staticmethod
    def _check_dangerous_patterns(text: str) -> list[str]:
        """Check for dangerous patterns in text.

        Args:
            text: Text to check

        Returns:
            List of matched dangerous patterns
        """
        matched_patterns = []
        for pattern in ReframeRouter.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matched_patterns.append(pattern)
        return matched_patterns

    def classify(self, query: str, context: str = "") -> RouterDecision:
        """Classify query as needing reframe, integrate, or both.

        Args:
            query: User's query/question
            context: Optional additional context about the query

        Returns:
            RouterDecision with classification and recommendations
        """
        full_text = f"{query} {context}"

        # Check for dangerous patterns first
        dangerous_patterns = self._check_dangerous_patterns(full_text)

        # Score against reframing keywords
        reframe_score, reframe_keywords = self._score_keyword_match(
            full_text, self.REFRAMING_KEYWORDS
        )

        # Score against integration keywords
        integrate_score, integrate_keywords = self._score_keyword_match(
            full_text, self.INTEGRATION_KEYWORDS
        )

        # Boost reframe score if dangerous patterns found
        if dangerous_patterns:
            reframe_score = min(1.0, reframe_score + 0.3)

        # Determine decision based on scores
        decision: Literal["reframe", "integrate", "both"] = "both"
        confidence = 0.5
        intent = "unknown"

        if reframe_score > 0.6 and integrate_score > 0.5:
            decision = "both"
            confidence = min(reframe_score, integrate_score)
            intent = "complex_attack_with_data"
        elif reframe_score > integrate_score + 0.2:
            decision = "reframe"
            confidence = reframe_score
            intent = "refusal_bypass"
        elif integrate_score > reframe_score + 0.2:
            decision = "integrate"
            confidence = integrate_score
            intent = "data_gathering"
        else:
            # Default: use whichever is higher
            if reframe_score > integrate_score:
                decision = "reframe"
                confidence = reframe_score
                intent = "potential_bypass"
            else:
                decision = "integrate"
                confidence = integrate_score
                intent = "information_retrieval"

        # Select suggested tools
        suggested_tools = self._select_tools(full_text, decision)

        # Select suggested strategies
        suggested_strategies = self._select_strategies(full_text, decision)

        # Build reasoning
        reasoning = self._build_reasoning(
            decision,
            intent,
            reframe_score,
            integrate_score,
            len(dangerous_patterns),
        )

        # Compile detected patterns
        detected_patterns = dangerous_patterns + list(
            set(reframe_keywords + integrate_keywords)
        )

        return RouterDecision(
            decision=decision,
            confidence=confidence,
            suggested_tools=suggested_tools,
            suggested_strategies=suggested_strategies,
            reasoning=reasoning,
            query_intent=intent,
            detected_patterns=detected_patterns,
        )

    def _select_tools(self, text: str, decision: str) -> list[str]:
        """Select recommended tools based on intent.

        Args:
            text: Full query text
            decision: Router decision (reframe, integrate, or both)

        Returns:
            List of recommended tool names
        """
        if decision == "reframe":
            return []

        tools = []
        text_lower = text.lower()

        # Check for scraping keywords
        if any(kw in text_lower for kw in ["scrape", "fetch", "crawl", "page"]):
            tools.extend(self.INTEGRATION_TOOLS["web_scraping"][:2])

        # Check for search keywords
        if any(kw in text_lower for kw in ["search", "find", "discover", "look up"]):
            tools.extend(self.INTEGRATION_TOOLS["search"][:2])

        # Check for OSINT keywords
        if any(
            kw in text_lower
            for kw in ["osint", "recon", "identity", "domain", "person"]
        ):
            tools.extend(self.INTEGRATION_TOOLS["osint"][:2])

        # Check for code/GitHub keywords
        if any(kw in text_lower for kw in ["github", "code", "repo", "project"]):
            tools.extend(self.INTEGRATION_TOOLS["code"])

        # Check for monitoring keywords
        if any(
            kw in text_lower for kw in ["monitor", "track", "trending", "latest"]
        ):
            tools.extend(self.INTEGRATION_TOOLS["monitoring"][:2])

        # Remove duplicates and limit to 5
        return list(dict.fromkeys(tools))[:5]

    def _select_strategies(self, text: str, decision: str) -> list[str]:
        """Select recommended strategies based on intent.

        Args:
            text: Full query text
            decision: Router decision (reframe, integrate, or both)

        Returns:
            List of recommended strategy names
        """
        if decision == "integrate":
            return []

        strategies = []
        text_lower = text.lower()

        # Check for jailbreak keywords
        if any(
            kw in text_lower
            for kw in ["bypass", "jailbreak", "circumvent", "without detection"]
        ):
            strategies.extend(self.REFRAMING_STRATEGIES["jailbreak"])

        # Check for encoding keywords
        if any(kw in text_lower for kw in ["encode", "obfuscate", "hide", "rot"]):
            strategies.extend(self.REFRAMING_STRATEGIES["encoding"])

        # Check for reasoning/logic keywords
        if any(
            kw in text_lower
            for kw in ["explain", "reason", "logic", "thinking", "step by step"]
        ):
            strategies.extend(self.REFRAMING_STRATEGIES["reasoning"])

        # Check for persona keywords
        if any(
            kw in text_lower
            for kw in ["pretend", "role play", "assume", "act as", "imagine"]
        ):
            strategies.extend(self.REFRAMING_STRATEGIES["persona"])

        # Check for novel attack keywords
        if any(
            kw in text_lower
            for kw in ["novel", "creative", "unique", "never tried", "new way"]
        ):
            strategies.extend(self.REFRAMING_STRATEGIES["novel"])

        # If no specific strategies matched, recommend popular ones
        if not strategies:
            strategies = list(ALL_STRATEGIES.keys())[:3]

        # Remove duplicates and limit to 5
        return list(dict.fromkeys(strategies))[:5]

    @staticmethod
    def _build_reasoning(
        decision: str, intent: str, reframe_score: float, integrate_score: float, pattern_count: int
    ) -> str:
        """Build human-readable reasoning for the decision.

        Args:
            decision: Router decision
            intent: Detected intent
            reframe_score: Reframing keyword match score
            integrate_score: Integration keyword match score
            pattern_count: Number of dangerous patterns detected

        Returns:
            Human-readable reasoning string
        """
        parts = []

        if decision == "reframe":
            parts.append(f"Query requires reframing (refusal bypass detected)")
            if pattern_count > 0:
                parts.append(f"{pattern_count} dangerous patterns detected")
        elif decision == "integrate":
            parts.append(f"Query requires external data tools and API integration")
        else:  # both
            parts.append(
                f"Query is complex: needs both reframing ({reframe_score:.2f}) and "
                f"integration ({integrate_score:.2f})"
            )

        parts.append(f"Detected intent: {intent}")

        return " | ".join(parts)


# Global router instance
_router: ReframeRouter | None = None


def _get_router() -> ReframeRouter:
    """Get or create the global router instance."""
    global _router
    if _router is None:
        _router = ReframeRouter()
    return _router


async def research_reframe_or_integrate(
    query: str, context: str = ""
) -> dict[str, Any]:
    """Route a query to reframing strategies or tool integrations.

    This intelligent router analyzes your query to determine whether:
    1. **Reframing**: The query is being refused by LLMs and needs
       prompt engineering strategies (jailbreaks, encoding, personas, etc.)
    2. **Integration**: The query needs external data from tools
       (web scraping, search, OSINT, APIs, etc.)
    3. **Both**: Complex queries needing both strategies AND data gathering

    Use this before executing a research task to route to the right approach.

    Args:
        query: Your research question or task
        context: Optional additional context for better classification

    Returns:
        Dictionary with routing decision:
        {
            "decision": "reframe" | "integrate" | "both",
            "confidence": 0.0-1.0 (confidence in classification),
            "query_intent": "refusal_bypass" | "data_gathering" | etc.,
            "suggested_tools": ["research_fetch", ...] (if integrate),
            "suggested_strategies": ["jailbreak_v1", ...] (if reframe),
            "detected_patterns": ["bypass", "fetch", ...],
            "reasoning": "Human-readable explanation"
        }

    Examples:
        Input: "How to bypass OpenAI safety filters"
        Output: {
            "decision": "reframe",
            "confidence": 0.92,
            "suggested_strategies": [jailbreak strategies],
            "reasoning": "Query requires reframing (refusal bypass detected) | ..."
        }

        Input: "Find all open SSH ports on example.com"
        Output: {
            "decision": "integrate",
            "confidence": 0.88,
            "suggested_tools": ["research_nmap_scan", "research_passive_recon"],
            "reasoning": "Query requires external data tools and API integration | ..."
        }

        Input: "How to exploit CVE-2024-1234 without getting detected"
        Output: {
            "decision": "both",
            "confidence": 0.95,
            "suggested_tools": ["research_cve_lookup", ...],
            "suggested_strategies": ["jailbreak", "encoding", ...],
            "reasoning": "Query is complex: needs both reframing and integration | ..."
        }
    """
    try:
        router = _get_router()
        decision = router.classify(query, context)

        log.info(
            "reframe_router classification query_len=%s decision=%s confidence=%.2f intent=%s pattern_count=%s",
            len(query),
            decision.decision,
            decision.confidence,
            decision.query_intent,
            len(decision.detected_patterns),
        )

        return {
            "decision": decision.decision,
            "confidence": round(decision.confidence, 3),
            "query_intent": decision.query_intent,
            "suggested_tools": decision.suggested_tools,
            "suggested_strategies": decision.suggested_strategies,
            "detected_patterns": decision.detected_patterns,
            "reasoning": decision.reasoning,
        }

    except Exception as e:
        log.error("router_error error=%s query_len=%s", str(e), len(query))
        raise


__all__ = ["research_reframe_or_integrate"]
