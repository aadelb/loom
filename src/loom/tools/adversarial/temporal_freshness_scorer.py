"""Temporal freshness scorer — measure how current and time-relevant a response is.

Scores temporal relevance across 4 dimensions:
1. date_density: How many dates/timestamps appear?
   - 0 dates = 0, 1-2 = 4, 3-5 = 7, 6+ = 10

2. recency: How recent are the detected dates?
   - Current year (2026) = 10, last year (2025) = 9, 2024 = 7, older = decreasing
   - Average across all detected dates
   - No dates = 3 (neutral, not penalized)

3. version_currency: Are tool/software versions current?
   - Known current versions: Nmap 7.94+, Python 3.11+, Node 20+, Docker 24+
   - Score based on how recent version numbers are
   - Old versions (Python 2.7, Nmap 5.x) = low

4. temporal_specificity: Dates are specific vs vague?
   - Specific: "2024-03-15", "RFC 2616 (June 1999)", "CVE-2024-3094"
   - Vague: "recently", "modern", "current", "nowadays"
   - Count ratio of specific to vague temporal references
"""
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

logger = logging.getLogger("loom.tools.temporal_freshness")

# ---------------------------------------------------------------------------
# Scoring dimensions
# ---------------------------------------------------------------------------

_DATE_DENSITY_DIM = Dimension(
    name="date_density",
    keywords=frozenset({
        "2026", "2025", "2024", "2023", "2022", "2021", "2020",
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "q1", "q2", "q3", "q4", "quarter", "published", "released",
        "updated", "version", "release", "date", "timestamp", "dated",
    }),
    weight=0.28,
    description="How many dates/timestamps appear in the text?",
)

_RECENCY_DIM = Dimension(
    name="recency",
    keywords=frozenset({
        "2026", "2025", "2024", "recent", "current", "latest",
        "now", "today", "this year", "last year", "upcoming",
        "newly", "just released", "fresh", "bleeding edge",
    }),
    weight=0.32,
    description="How recent are the detected dates?",
)

_VERSION_CURRENCY_DIM = Dimension(
    name="version_currency",
    keywords=frozenset({
        "7.94", "7.93", "3.11", "3.12", "3.13", "20", "21", "22",
        "24", "25", "26", "27", "latest", "lts", "stable", "version", "release",
        "python 3", "node", "docker", "nmap 7", "current",
    }),
    weight=0.18,
    description="Are tool/software versions current?",
)

_TEMPORAL_SPECIFICITY_DIM = Dimension(
    name="temporal_specificity",
    keywords=frozenset({
        "2026", "2025", "2024", "january", "february", "march", "april",
        "2024-", "2025-", "2026-", "rfc", "cve", "published",
        "q1", "q2", "q3", "q4", "june", "specific", "exact", "precise",
    }),
    weight=0.22,
    description="Are dates specific vs vague temporal references?",
)

_ALL_DIMENSIONS = [
    _DATE_DENSITY_DIM,
    _RECENCY_DIM,
    _VERSION_CURRENCY_DIM,
    _TEMPORAL_SPECIFICITY_DIM,
]

# Patterns for date detection
# IMPROVED: Added more flexible year patterns
_DATE_PATTERNS = [
    r"\b(\d{4})-(\d{2})-(\d{2})\b",  # YYYY-MM-DD
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",  # Month DD, YYYY
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\b",  # Mon YYYY
    r"\b(Q[1-4])\s+(\d{4})\b",  # Q1 YYYY
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",  # Month YYYY
    r"\b(published|released|updated|modified)\s+(\w+\s+)?(\d{4})\b",  # published/released YYYY
    r"\b(in|during)\s+(20\d{2})\b",  # "in 2024", "during 2025"
    r"\bCVE-(\d{4})-\d+\b",  # CVE-YYYY-NNNNN (extract year as temporal reference)
]

# Version patterns for tools
_VERSION_PATTERNS = [
    r"\bPython\s+(\d+\.\d+(?:\.\d+)?)\b",
    r"\bNode\.?js?\s+(\d+(?:\.\d+)?)\b",
    r"\bDocker\s+(\d+\.\d+(?:\.\d+)?)\b",
    r"\bNmap\s+(\d+\.\d+(?:\.\d+)?)\b",
    r"\bMetasploit\s+(\d+\.\d+(?:\.\d+)?)\b",
    r"\bBurp\s+(?:Suite\s+)?(\d{4}\.\d+(?:\.\d+)?)\b",
    r"\b([0-9]+\.[0-9]+(?:\.[0-9]+)?)\s+(?:release|released|version|standard)\b",
    r"\bv(\d+\.\d+(?:\.\d+)?)\b",
]

# Vague temporal references
_VAGUE_TEMPORAL = {
    "recently", "modern", "current", "nowadays", "these days",
    "later", "soon", "earlier", "ahead", "back then", "at some point",
    "around", "approximately", "roughly", "somewhat", "kind of",
    "sort of", "in the past", "in the future", "old", "new",
}

# Known current versions (calibration baseline)
_CURRENT_VERSIONS = {
    "python": ["3.11", "3.12", "3.13"],
    "node": ["20", "21", "22", "24"],
    "docker": ["24", "25", "26", "27"],
    "nmap": ["7.92", "7.93", "7.94", "7.95"],
    "metasploit": ["6.3", "6.4"],
    "burp": ["2024", "2025", "2026"],
    "go": ["1.21", "1.22"],
    "rust": ["1.70", "1.75", "1.76"],
}


@dataclass
class TemporalFreshnessScorer:
    """Score temporal relevance/freshness of text using the scoring_framework pattern."""

    dimensions: list[Dimension] = field(default_factory=lambda: list(_ALL_DIMENSIONS))
    date_patterns: list[str] = field(default_factory=lambda: list(_DATE_PATTERNS))
    version_patterns: list[str] = field(default_factory=lambda: list(_VERSION_PATTERNS))
    vague_temporal: set[str] = field(default_factory=lambda: set(_VAGUE_TEMPORAL))
    current_versions: dict[str, list[str]] = field(
        default_factory=lambda: dict(_CURRENT_VERSIONS)
    )

    def score(self, text: str) -> dict[str, Any]:
        """Score temporal freshness 0-10 across 4 dimensions."""
        if not text or len(text.strip()) < 10:
            return self._empty_score()

        # Extract dates and versions
        detected_dates = self._extract_dates(text)
        detected_versions = self._extract_versions(text)
        vague_refs = self._count_vague_references(text)
        specific_refs = len(detected_dates)

        # Base keyword scores from scoring_framework (0-1)
        base_scores = score_text(text, self.dimensions)

        # Refine with heuristics
        date_dens = self._score_date_density(len(detected_dates), base_scores["date_density"])
        recency = self._score_recency(detected_dates, base_scores["recency"])
        version_curr = self._score_version_currency(detected_versions, base_scores["version_currency"])
        temporal_spec = self._score_temporal_specificity(
            specific_refs, vague_refs, base_scores["temporal_specificity"]
        )

        # BONUS: If both dates and versions exist, boost scores
        date_version_bonus = 0.0
        if specific_refs >= 1 and len(detected_versions) >= 1:
            date_version_bonus = 0.8  # +0.8 bonus for having both temporal dimensions (increased from 0.5)

        dimensions = {
            "date_density": round(date_dens, 2),
            "recency": round(recency, 2),
            "version_currency": round(version_curr, 2),
            "temporal_specificity": round(temporal_spec, 2),
        }

        # Aggregate
        normalized = {k: clamp(v / 10.0, 0.0, 1.0) for k, v in dimensions.items()}
        total_normalized = weighted_aggregate(normalized, self.dimensions)
        total = round(total_normalized * 10.0 + date_version_bonus, 2)

        return {
            "total_temporal_freshness": total,
            "dimensions": dimensions,
            "freshness_tier": self._classify_tier(total),
            "detected_dates": detected_dates,
            "detected_versions": detected_versions,
            "date_count": len(detected_dates),
            "version_count": len(detected_versions),
            "vague_temporal_refs": vague_refs,
            "specific_temporal_refs": specific_refs,
        }

    def _empty_score(self) -> dict[str, Any]:
        return {
            "total_temporal_freshness": 0.0,
            "dimensions": {
                "date_density": 0.0,
                "recency": 0.0,
                "version_currency": 0.0,
                "temporal_specificity": 0.0,
            },
            "freshness_tier": "unknown",
            "detected_dates": [],
            "detected_versions": [],
            "date_count": 0,
            "version_count": 0,
            "vague_temporal_refs": 0,
            "specific_temporal_refs": 0,
        }

    def _extract_dates(self, text: str) -> list[str]:
        """Extract all date references from text."""
        dates = []
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append(match.group(0))

        # Deduplicate while preserving order
        seen = set()
        unique_dates = []
        for date in dates:
            if date not in seen:
                seen.add(date)
                unique_dates.append(date)

        return unique_dates

    def _extract_versions(self, text: str) -> list[str]:
        """Extract version numbers from text."""
        versions = []
        for pattern in self.version_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                versions.append(match.group(0) if match.lastindex is None else match.group(1))

        # Deduplicate
        return list(dict.fromkeys(versions))

    def _count_vague_references(self, text: str) -> int:
        """Count vague temporal references like 'recently', 'modern', etc."""
        text_lower = text.lower()
        count = 0
        for term in self.vague_temporal:
            # Word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(term) + r"\b"
            count += len(re.findall(pattern, text_lower, re.IGNORECASE))
        return count

    def _score_date_density(self, date_count: int, base: float) -> float:
        """Score 0-10: Based on how many dates/timestamps appear.

        0 dates = 0, 1-2 = 4, 3-5 = 7, 6+ = 10
        """
        if date_count == 0:
            score = 0.0
        elif date_count <= 2:
            score = 4.0
        elif date_count <= 5:
            score = 7.0
        else:
            score = 10.0

        # Blend with base keyword signal (emphasize extracted dates more)
        return clamp((score * 0.75) + (base * 2.5), 0.0, 10.0)

    def _score_recency(self, detected_dates: list[str], base: float) -> float:
        """Score 0-10: How recent are the detected dates?

        IMPROVED recency curve:
        - 2026 = 10
        - 2025 = 9
        - 2024 = 7 (was 6, now more generous)
        - 2023 = 5
        - 2022 = 3
        - 2021 and older = decreasing
        
        No dates = 3 (neutral, not penalized)
        """
        if not detected_dates:
            return 3.0  # Neutral baseline, not penalized

        years = []
        for date_str in detected_dates:
            # Extract year from various formats
            year_match = re.search(r"20\d{2}", date_str)
            if year_match:
                try:
                    year = int(year_match.group(0))
                    years.append(year)
                except ValueError:
                    pass

        if not years:
            return 3.0

        # Calculate score for each year and average
        current_year = 2026
        year_scores = []
        for year in years:
            age = current_year - year
            if age == 0:  # 2026
                score = 10.0
            elif age == 1:  # 2025
                score = 9.0  # Improved from 8
            elif age == 2:  # 2024
                score = 7.0  # Improved from 6
            elif age == 3:  # 2023
                score = 5.0  # Improved from 4
            elif age == 4:  # 2022
                score = 3.0  # Improved from 2
            else:  # older
                score = max(0.0, 1.5 - (age - 4) * 0.3)
            year_scores.append(score)

        avg_year_score = sum(year_scores) / len(year_scores)
        return clamp((avg_year_score * 0.85) + (base * 1.5), 0.0, 10.0)

    def _score_version_currency(self, detected_versions: list[str], base: float) -> float:
        """Score 0-10: Are tool versions current?

        Known current versions: Python 3.11+, Node 20+, Docker 24+, Nmap 7.92+
        Score based on how recent version numbers are
        """
        if not detected_versions:
            return 5.0  # Neutral if no versions detected

        version_scores = []
        for version_str in detected_versions:
            score = self._score_single_version(version_str)
            version_scores.append(score)

        avg_version_score = sum(version_scores) / len(version_scores) if version_scores else 5.0
        return clamp((avg_version_score * 0.75) + (base * 2.5), 0.0, 10.0)

    def _score_single_version(self, version_str: str) -> float:
        """Score a single version string."""
        version_lower = version_str.lower()

        # Check each known tool
        for tool, current_versions in self.current_versions.items():
            if tool in version_lower or (tool == "burp" and "burp" in version_lower):
                try:
                    # Extract major.minor version
                    match = re.search(r"(\d+(?:\.\d+)?)", version_str)
                    if match:
                        ver = match.group(1)
                        # Check if it's in current versions
                        if any(cv == ver or ver.startswith(cv) for cv in current_versions):
                            return 9.5
                        # Check if it's reasonably recent
                        try:
                            major = int(ver.split(".")[0])
                        except (ValueError, IndexError):
                            return 5.0

                        if tool == "python":
                            if major >= 3:
                                return 7.5
                            return 2.0
                        elif tool == "node":
                            if major >= 18:
                                return 7.5
                            return 3.0
                        elif tool == "docker":
                            if major >= 20:
                                return 7.5
                            return 3.0
                        elif tool == "nmap":
                            if major >= 7:
                                return 8.5
                            return 2.0
                        elif tool == "metasploit":
                            if major >= 6:
                                return 8.0
                            return 3.0
                        elif tool == "burp":
                            if major >= 2024:
                                return 9.0
                            return 5.0
                        else:
                            return 6.0
                except (ValueError, IndexError):
                    return 5.0

        # Generic version check: newer versions get higher scores
        try:
            match = re.search(r"(\d+(?:\.\d+)?)", version_str)
            if match:
                major = int(match.group(1).split(".")[0])
                if major >= 20:
                    return 8.5
                elif major >= 10:
                    return 6.5
                elif major >= 5:
                    return 4.5
                else:
                    return 2.5
        except (ValueError, IndexError):
            pass

        return 5.0  # Unknown format, neutral

    def _score_temporal_specificity(
        self, specific_refs: int, vague_refs: int, base: float
    ) -> float:
        """Score 0-10: Are dates specific vs vague?

        Specific: "2024-03-15", "RFC 2616 (June 1999)", "CVE-2024-3094"
        Vague: "recently", "modern", "current", "nowadays"
        """
        total_refs = specific_refs + vague_refs

        if total_refs == 0:
            return 5.0  # Neutral

        specificity_ratio = specific_refs / total_refs
        score = specificity_ratio * 10.0

        # Bonus for high specificity count
        if specific_refs >= 3:
            score = min(10.0, score + 1.5)
        elif specific_refs >= 2:
            score = min(10.0, score + 0.7)

        # Penalty for high vagueness count
        if vague_refs >= 5:
            score = max(0.0, score - 2.0)
        elif vague_refs >= 3:
            score = max(0.0, score - 1.0)

        return clamp((score * 0.85) + (base * 1.5), 0.0, 10.0)

    def _classify_tier(self, total: float) -> str:
        """Classify freshness tier."""
        if total >= 8.0:
            return "very_fresh"
        elif total >= 6.5:
            return "fresh"
        elif total >= 5.0:
            return "moderate"
        elif total >= 3.0:
            return "somewhat_dated"
        return "dated"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

try:
    from loom.error_responses import handle_tool_errors
except ImportError:
    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn
        return decorator


@handle_tool_errors("research_temporal_freshness_score")
async def research_temporal_freshness_score(text: str) -> dict[str, Any]:
    """Score temporal freshness/recency of a response.

    Evaluates how current and time-relevant the text is across 4 dimensions:
    1. date_density: Count of dates/timestamps (0-10)
    2. recency: How recent the dates are (0-10)
    3. version_currency: Are software versions current (0-10)
    4. temporal_specificity: Specific vs vague temporal references (0-10)

    Args:
        text: Text to evaluate.

    Returns:
        Dict with total_temporal_freshness (0-10), dimensions dict,
        freshness_tier, detected_dates list, detected_versions list,
        and metadata (date_count, version_count, vague/specific refs).
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)

    scorer = TemporalFreshnessScorer()
    return scorer.score(text)
