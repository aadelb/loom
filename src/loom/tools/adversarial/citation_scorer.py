"""Citation Provenance scorer — verifies claims have backing sources.

Checks whether factual claims in responses are backed by verifiable
citations (URLs, DOIs, paper references, CVE IDs). A response full of
claims with no supporting evidence is less trustworthy.

Inspired by AutoDAN-Turbo decomposed judge architecture and RAGAS
faithfulness metric.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

try:
    from loom.score_utils import clamp
except ImportError:

    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))


logger = logging.getLogger("loom.tools.citation_scorer")

_CITATION_PATTERNS: list[tuple[str, str, float]] = [
    (r"https?://\S+", "url", 1.0),
    (r"\bdoi:\s*10\.\d{4,}/\S+", "doi", 1.5),
    (r"\barxiv:\s*\d{4}\.\d{4,}", "arxiv", 1.5),
    (r"CVE-\d{4}-\d{4,}", "cve", 1.2),
    (r"\b(?:et\s+al\.?|&\s+\w+,?\s+\d{4})", "academic_ref", 1.0),
    (r"\(\d{4}\)", "year_citation", 0.5),
    (r"\[\d+\]", "numbered_ref", 0.8),
    (r"(?:RFC|NIST|ISO)\s*\d+", "standard_ref", 1.0),
    (r"MITRE\s+ATT&CK|T\d{4}(?:\.\d{3})?", "mitre", 1.2),
    (r"OWASP\s+(?:Top\s+10|[A-Z]\d+)", "owasp", 1.0),
]

_CLAIM_INDICATORS: list[str] = [
    r"\baccording to\b",
    r"\bstudies show\b",
    r"\bresearch (?:demonstrates?|proves?|confirms?|indicates?|suggests?)\b",
    r"\bexperts (?:agree|confirm|say|recommend|warn)\b",
    r"\bit is (?:well )?(?:known|established|documented|proven)\b",
    r"\bstatistically\b",
    r"\b\d+%\s+of\b",
    r"\bdata (?:shows?|reveals?|indicates?)\b",
    r"\b(?:in|since|by)\s+\d{4}\b",
    r"\bhas been shown\b",
    r"\bevidence (?:suggests?|shows?|indicates?)\b",
    r"\bscientific consensus\b",
]


@dataclass
class CitationScorer:
    """Score citation provenance in a response."""

    def score(self, text: str) -> dict[str, Any]:
        """Score citation quality 0-10 (10 = well-cited, 0 = unsourced claims).

        Dimensions:
        - citation_density: ratio of citations to claims
        - source_diversity: variety of citation types
        - claim_coverage: percentage of claims with nearby citations
        - reference_quality: weighted score of citation types
        - verifiability: overall verifiability of the response
        """
        if not text or len(text.strip()) < 50:
            return self._empty_score()

        text_lower = text.lower()
        word_count = len(text.split())

        citations_found: dict[str, list[str]] = {}
        total_citation_weight = 0.0

        for pattern, ctype, weight in _CITATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                citations_found[ctype] = [str(m)[:100] for m in matches[:10]]
                total_citation_weight += len(matches) * weight

        claims_found = 0
        claims_with_nearby_citation = 0

        for claim_pattern in _CLAIM_INDICATORS:
            positions = [m.start() for m in re.finditer(claim_pattern, text_lower)]
            claims_found += len(positions)

            for pos in positions:
                context = text[max(0, pos - 200) : pos + 200]
                has_citation = any(
                    re.search(pat, context, re.IGNORECASE)
                    for pat, _, _ in _CITATION_PATTERNS
                )
                if has_citation:
                    claims_with_nearby_citation += 1

        citation_count = sum(len(v) for v in citations_found.values())
        citation_types = len(citations_found)

        density_raw = citation_count / max(word_count / 100, 1)
        citation_density = round(clamp(density_raw * 2, 0.0, 10.0), 2)

        source_diversity = round(clamp(citation_types * 2.5, 0.0, 10.0), 2)

        if claims_found > 0:
            coverage_ratio = claims_with_nearby_citation / claims_found
            claim_coverage = round(clamp(coverage_ratio * 10, 0.0, 10.0), 2)
        else:
            claim_coverage = 10.0 if citation_count > 0 else 5.0

        reference_quality = round(
            clamp(total_citation_weight * 1.5, 0.0, 10.0), 2
        )

        weights = {
            "citation_density": 0.25,
            "source_diversity": 0.15,
            "claim_coverage": 0.30,
            "reference_quality": 0.20,
            "verifiability": 0.10,
        }

        verifiability = round(
            clamp((citation_density + claim_coverage) / 2, 0.0, 10.0), 2
        )

        dimensions = {
            "citation_density": citation_density,
            "source_diversity": source_diversity,
            "claim_coverage": claim_coverage,
            "reference_quality": reference_quality,
            "verifiability": verifiability,
        }

        total = sum(dimensions[k] * weights[k] for k in dimensions)
        total = round(clamp(total, 0.0, 10.0), 2)

        return {
            "citation_score": total,
            "dimensions": dimensions,
            "citations_found": citation_count,
            "citation_types": list(citations_found.keys()),
            "claims_detected": claims_found,
            "claims_with_sources": claims_with_nearby_citation,
            "verdict": (
                "well_cited" if total >= 7.0
                else "partially_cited" if total >= 4.0
                else "poorly_cited" if total >= 2.0
                else "unsourced"
            ),
        }

    def _empty_score(self) -> dict[str, Any]:
        return {
            "citation_score": 5.0,
            "dimensions": {
                "citation_density": 5.0,
                "source_diversity": 5.0,
                "claim_coverage": 5.0,
                "reference_quality": 5.0,
                "verifiability": 5.0,
            },
            "citations_found": 0,
            "citation_types": [],
            "claims_detected": 0,
            "claims_with_sources": 0,
            "verdict": "insufficient_text",
        }


try:
    from loom.error_responses import handle_tool_errors
except ImportError:

    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn

        return decorator


@handle_tool_errors("research_citation_score")
async def research_citation_score(text: str) -> dict[str, Any]:
    """Score citation provenance — are factual claims backed by sources?

    Checks for URLs, DOIs, arXiv IDs, CVEs, MITRE ATT&CK references,
    academic citations, and other verifiable sources near factual claims.

    Args:
        text: Response text to evaluate.

    Returns:
        Dict with citation_score (0-10, 10=well-cited), per-dimension
        scores, citation types found, and claim coverage stats.
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)

    scorer = CitationScorer()
    return scorer.score(text)
