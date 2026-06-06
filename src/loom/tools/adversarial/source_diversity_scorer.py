"""Source diversity scorer — measure whether response draws from diverse, independent sources.

Implements Stanford AI Index 2025 critical dimension: evaluates whether a response
draws from diverse, independent sources rather than echo-chamber content.

Scoring dimensions (5 total, weights sum to 1.0):
1. source_count (0.25): Distinct sources referenced (URLs, standards, tools, authors)
2. domain_variety (0.25): Source domains span different TLDs/organizations
3. perspective_range (0.20): Multiple viewpoints represented (contrast language)
4. authority_mix (0.15): Mix of authority types (government, academic, industry, OSS)
5. independence (0.15): Sources appear independent (not clustered under one vendor)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from loom.scoring_framework import Dimension, score_text, weighted_aggregate

try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

logger = logging.getLogger("loom.tools.source_diversity")

# ---------------------------------------------------------------------------
# Scoring dimensions
# ---------------------------------------------------------------------------

_SOURCE_COUNT_DIM = Dimension(
    name="source_count",
    keywords=frozenset({
        "source", "sources", "reference", "references", "cited", "cite",
        "according to", "says", "states", "indicates", "shows", "demonstrates",
        "research", "study", "paper", "publication", "article", "document",
        "url", "link", "website", "site", "page", "resource", "resource",
        "standard", "specification", "framework", "guideline", "best practice",
        "author", "researcher", "expert", "organization", "company",
    }),
    weight=0.25,
    description="Count of distinct sources (URLs, standards, tools, named authors)",
)

_DOMAIN_VARIETY_DIM = Dimension(
    name="domain_variety",
    keywords=frozenset({
        "nist.gov", "owasp.org", "mitre.org", "cisa.gov", "ieee.org",
        "acm.org", "sans.org", "ietf.org", "w3c.org", "iso.org",
        "eff.org", "afl.org", "tor.org", "wikipedia.org", "github.com",
        "arxiv.org", "researchgate.net", "scholar.google.com",
        "academic", "government", "nonprofit", "corporate", "open source",
        "domain", "tld", ".gov", ".org", ".com", ".edu", ".net",
    }),
    weight=0.25,
    description="Domain variety across different organizations/TLDs",
)

_PERSPECTIVE_RANGE_DIM = Dimension(
    name="perspective_range",
    keywords=frozenset({
        "however", "alternatively", "on the other hand", "conversely",
        "in contrast", "whereas", "compared to", "vs", "versus",
        "different", "differs", "disagree", "opposing", "conflicting",
        "some argue", "others argue", "some say", "others say",
        "perspective", "viewpoint", "opinion", "position", "approach",
        "critical", "critique", "counter", "counterargument", "challenge",
        "trade-off", "tradeoff", "balance", "consider", "consider both",
    }),
    weight=0.20,
    description="Multiple viewpoints/perspectives represented",
)

_AUTHORITY_MIX_DIM = Dimension(
    name="authority_mix",
    keywords=frozenset({
        "government", "federal", "nist", "cisa", "nsa", "fbi",
        "academic", "university", "ieee", "acm", "research", "scholar",
        "industry", "owasp", "sans", "isc2", "vendor", "organization",
        "open source", "opensource", "oss", "github", "linux foundation",
        "standard", "specification", "framework", "guidelines",
        "certified", "accredited", "authoritative", "official", "recognized",
    }),
    weight=0.15,
    description="Mix of authority types (gov + academic + industry + OSS)",
)

_INDEPENDENCE_DIM = Dimension(
    name="independence",
    keywords=frozenset({
        "independent", "independently", "separate", "distinct",
        "different", "varies", "various", "diverse", "variety",
        "multiple", "range", "spectrum", "broad", "wide",
        "vendor-neutral", "agnostic", "unbiased", "objective",
        "competing", "alternative", "choice", "options",
    }),
    weight=0.15,
    description="Sources appear independent (not clustered under one vendor)",
)

_ALL_DIMENSIONS = [
    _SOURCE_COUNT_DIM,
    _DOMAIN_VARIETY_DIM,
    _PERSPECTIVE_RANGE_DIM,
    _AUTHORITY_MIX_DIM,
    _INDEPENDENCE_DIM,
]

# Named standards and tools that boost source_count
_KNOWN_STANDARDS = {
    "nist", "owasp", "mitre", "cisa", "ieee", "acm", "iso", "ietf",
    "pci-dss", "hipaa", "gdpr", "sox", "cis controls", "sans", "eff",
    "pec", "nhs", "cve", "cvss", "cwe", "capec", "atkp",
}

_KNOWN_TOOLS = {
    "nmap", "metasploit", "burp", "wireshark", "kali", "ghidra",
    "snort", "zeek", "ossec", "tripwire", "aide", "splunk",
    "elk stack", "prometheus", "grafana", "terraform", "ansible",
}

_KNOWN_AUTHORITIES = {
    "government": {"nist", "cisa", "nsa", "fbi", "dod", "dhs", "cia", "fed"},
    "academic": {"ieee", "acm", "university", "researcher", "scholar", "paper", "arxiv"},
    "industry": {"owasp", "sans", "isc2", "vendor", "company", "organization"},
    "opensource": {"github", "linux foundation", "oss", "open source"},
}

# Detect domains from URLs
_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    re.IGNORECASE
)

# Detect domain mentions (even without http://)
_DOMAIN_MENTION_PATTERN = re.compile(
    r"\b([a-zA-Z0-9.-]+\.(gov|org|com|edu|net|io|ai|uk|de|eu|info))\b",
    re.IGNORECASE
)

# Common vendor clustering (penalizes if all from same vendor)
_VENDOR_CLUSTERS = {
    "microsoft": {"azure", "office", "windows", "microsoft", "msdn"},
    "google": {"google", "gcp", "cloud.google", "googleapis", "google scholar"},
    "amazon": {"aws", "amazon", "awslabs", "amazonaws"},
    "ibm": {"ibm", "redhat", "rhel"},
    "cisco": {"cisco", "meraki"},
    "oracle": {"oracle", "mysql", "java"},
}


@dataclass
class SourceDiversityScorer:
    """Score source diversity using the scoring_framework pattern.

    Evaluates whether a response draws from diverse, independent sources
    rather than echo-chamber content, following Stanford AI Index 2025.
    """

    contradiction_patterns: list[tuple[str, float]] = field(
        default_factory=lambda: [
            (r"\ball\b.+?\b(only|never|sole)\b", 1.5),
            (r"\b(only|sole|unique)\b.+?\b(or|and|also)\b", 1.0),
        ]
    )

    def score(self, text: str) -> dict[str, Any]:
        """Score source diversity of text (0-10 scale).

        Args:
            text: Text to evaluate for source diversity

        Returns:
            Dict with:
                - total_source_diversity (0-10)
                - source_count (0-10)
                - domain_variety (0-10)
                - perspective_range (0-10)
                - authority_mix (0-10)
                - independence (0-10)
                - unique_sources (int)
                - unique_domains (int)
                - authority_types_found (list[str])
                - verdict (str: "diverse", "moderate", "narrow", "clustered")
                - details (dict with breakdown)
        """
        if isinstance(text, list):
            text = " ".join(str(x) for x in text)
        if isinstance(text, dict):
            text = str(text)

        text = text.strip()
        if not text:
            return {
                "total_source_diversity": 0.0,
                "source_count": 0.0,
                "domain_variety": 0.0,
                "perspective_range": 0.0,
                "authority_mix": 0.0,
                "independence": 0.0,
                "unique_sources": 0,
                "unique_domains": 0,
                "authority_types_found": [],
                "verdict": "no_content",
                "details": {},
            }

        # Score each dimension
        source_count_score = self._score_source_count(text)
        domain_variety_score = self._score_domain_variety(text)
        perspective_score = self._score_perspective_range(text)
        authority_score = self._score_authority_mix(text)
        independence_score = self._score_independence(text)

        # Aggregate with weights
        weighted_scores = {
            "source_count": source_count_score * 0.25,
            "domain_variety": domain_variety_score * 0.25,
            "perspective_range": perspective_score * 0.20,
            "authority_mix": authority_score * 0.15,
            "independence": independence_score * 0.15,
        }

        total_diversity = sum(weighted_scores.values())
        total_diversity = clamp(total_diversity, 0.0, 10.0)

        # Determine verdict
        if total_diversity >= 7.0:
            verdict = "diverse"
        elif total_diversity >= 5.0:
            verdict = "moderate"
        elif total_diversity >= 3.0:
            verdict = "narrow"
        else:
            verdict = "clustered"

        # Extract metadata
        unique_sources = self._count_unique_sources(text)
        unique_domains = self._count_unique_domains(text)
        authorities = self._detect_authority_types(text)

        return {
            "total_source_diversity": round(total_diversity, 2),
            "source_count": round(source_count_score, 2),
            "domain_variety": round(domain_variety_score, 2),
            "perspective_range": round(perspective_score, 2),
            "authority_mix": round(authority_score, 2),
            "independence": round(independence_score, 2),
            "unique_sources": unique_sources,
            "unique_domains": unique_domains,
            "authority_types_found": authorities,
            "verdict": verdict,
            "details": {
                "weighted_scores": {k: round(v, 2) for k, v in weighted_scores.items()},
                "source_diversity_Stanford_2025": True,
            },
        }

    def _score_source_count(self, text: str) -> float:
        """Score 0-10: Number of distinct sources referenced."""
        unique_sources = self._count_unique_sources(text)

        # Calibration: 0 sources = 0, 1-2 = 3, 3-5 = 6, 6-10 = 8, 10+ = 10
        if unique_sources == 0:
            return 0.0
        elif unique_sources <= 2:
            return 3.0
        elif unique_sources <= 5:
            return 6.0
        elif unique_sources <= 10:
            return 8.0
        else:
            return 10.0

    def _count_unique_sources(self, text: str) -> int:
        """Count distinct sources: URLs, standards, tools, named authors."""
        sources = set()

        # Extract URLs
        urls = re.findall(_URL_PATTERN, text)
        sources.update(urls)

        # Extract named standards
        text_lower = text.lower()
        for standard in _KNOWN_STANDARDS:
            if re.search(rf"\b{re.escape(standard)}\b", text_lower):
                sources.add(standard)

        # Extract named tools
        for tool in _KNOWN_TOOLS:
            if re.search(rf"\b{re.escape(tool)}\b", text_lower):
                sources.add(tool)

        # Extract named authors (simple: "Author Name" or similar patterns)
        author_pattern = r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"
        authors = re.findall(author_pattern, text)
        for author in authors[:5]:  # Limit to first 5 to avoid noise
            sources.add(f"author:{author}")

        return len(sources)

    def _score_domain_variety(self, text: str) -> float:
        """Score 0-10: Do sources span different domains/TLDs?"""
        domains = self._extract_domain_variety(text)

        if not domains:
            return 0.0

        domain_count = len(domains)
        tld_count = len(set(d.split(".")[-1] for d in domains if "." in d))

        # More domains + more varied TLDs = higher score
        # Calibration: 1 domain = 2.0, 2 = 4.0, 3 = 6.0, 4+ = 8.0, with TLD bonus
        domain_score = min(domain_count * 2.0, 8.0)
        tld_bonus = min(tld_count * 0.5, 2.0)

        return clamp(domain_score + tld_bonus, 0.0, 10.0)

    def _count_unique_domains(self, text: str) -> int:
        """Count unique domains extracted from URLs and domain mentions."""
        domains = self._extract_domain_variety(text)
        return len(domains)

    def _extract_domain_variety(self, text: str) -> set[str]:
        """Extract domains from URLs and domain mentions, normalize to base domain."""
        domains = set()
        
        # Extract from full URLs
        urls = re.findall(_URL_PATTERN, text)
        for url in urls:
            # Extract base domain (e.g., "github.com" from "api.github.com")
            parts = url.split(".")
            if len(parts) >= 2:
                base = ".".join(parts[-2:])
                domains.add(base)
            else:
                domains.add(url)

        # Extract domain mentions (e.g., "nist.gov", "github.com" without http://)
        domain_mentions = re.findall(_DOMAIN_MENTION_PATTERN, text)
        for domain_mention in domain_mentions:
            domains.add(domain_mention[0])  # Extract the domain part

        return domains

    def _score_perspective_range(self, text: str) -> float:
        """Score 0-10: Multiple viewpoints represented?"""
        text_lower = text.lower()
        score = 5.0  # Neutral baseline

        # Detect contrast language
        contrast_keywords = {
            "however", "alternatively", "on the other hand", "conversely",
            "in contrast", "whereas", "compared to", "vs", "versus",
        }
        contrast_count = sum(1 for kw in contrast_keywords if kw in text_lower)
        score += min(contrast_count * 1.0, 2.5)

        # Detect comparison patterns
        comparison_patterns = [
            r"(\w+)\s+vs\.?\s+(\w+)",
            r"compared to",
            r"in contrast to",
            r"different from",
        ]
        comparison_count = sum(
            len(re.findall(pat, text_lower, re.IGNORECASE))
            for pat in comparison_patterns
        )
        score += min(comparison_count * 0.5, 1.5)

        # Detect multiple tool recommendations
        tool_count = sum(1 for tool in _KNOWN_TOOLS if tool in text_lower)
        if tool_count >= 3:
            score += 1.0

        return clamp(score, 0.0, 10.0)

    def _score_authority_mix(self, text: str) -> float:
        """Score 0-10: Mix of authority types (gov, academic, industry, OSS)?"""
        authorities = self._detect_authority_types(text)
        authority_count = len(authorities)

        # Calibration: 1 = 4, 2 = 6, 3 = 8, 4 = 10
        if authority_count == 0:
            return 0.0
        elif authority_count == 1:
            return 4.0
        elif authority_count == 2:
            return 6.0
        elif authority_count == 3:
            return 8.0
        else:
            return 10.0

    def _detect_authority_types(self, text: str) -> list[str]:
        """Detect which authority types are represented."""
        text_lower = text.lower()
        found_authorities = []

        for authority_type, keywords in _KNOWN_AUTHORITIES.items():
            if any(kw in text_lower for kw in keywords):
                found_authorities.append(authority_type)

        return found_authorities

    def _score_independence(self, text: str) -> float:
        """Score 0-10: Sources appear independent (not vendor-clustered)?"""
        text_lower = text.lower()
        score = 5.0  # Neutral baseline

        # Check for vendor clustering
        vendor_hits = {}
        for vendor, keywords in _VENDOR_CLUSTERS.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits > 0:
                vendor_hits[vendor] = hits

        # Penalize clustering under single vendor
        if vendor_hits:
            dominant_vendor = max(vendor_hits, key=vendor_hits.get)
            if vendor_hits[dominant_vendor] >= 5:
                score -= 4.0  # Heavily penalize single-vendor clustering
            elif vendor_hits[dominant_vendor] >= 3:
                score -= 2.0

        # Boost for explicit independence language
        independence_keywords = {"diverse", "variety", "independent", "different", "alternatives"}
        if any(kw in text_lower for kw in independence_keywords):
            score += 1.5

        # Boost for multiple distinct approaches mentioned
        approach_patterns = [
            r"approach\d+",
            r"method\d+",
            r"option\d+",
            r"alternative\d+",
        ]
        for pattern in approach_patterns:
            if re.search(pattern, text_lower):
                score += 0.5

        return clamp(score, 0.0, 10.0)


try:
    from loom.error_responses import handle_tool_errors
except ImportError:
    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn
        return decorator


@handle_tool_errors("research_source_diversity_score")
async def research_source_diversity_score(text: str) -> dict[str, Any]:
    """Score source diversity of a response using Stanford AI Index 2025 dimensions.

    Measures whether the response draws from diverse, independent sources
    rather than echo-chamber content. Evaluates:
    - source_count: How many distinct sources?
    - domain_variety: Do sources span different domains/TLDs?
    - perspective_range: Multiple viewpoints represented?
    - authority_mix: Government + Academic + Industry + OSS?
    - independence: Sources independent (not vendor-clustered)?

    Args:
        text: Text/response to evaluate for source diversity.

    Returns:
        Dict with:
            - total_source_diversity (0-10)
            - source_count, domain_variety, perspective_range, authority_mix, independence (each 0-10)
            - unique_sources (int)
            - unique_domains (int)
            - authority_types_found (list[str])
            - verdict (str: "diverse", "moderate", "narrow", "clustered")
            - details (dict)

    Example:
        >>> result = await research_source_diversity_score(
        ...     "This NIST and OWASP framework... GitHub example... IEEE standard..."
        ... )
        >>> print(result["total_source_diversity"])  # Should be ~7.5
        >>> print(result["verdict"])  # "diverse"
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)

    scorer = SourceDiversityScorer()
    return scorer.score(text)
