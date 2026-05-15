"""Trend forecasting tool — analyze research directions via term frequency evolution.

Predicts emerging research directions by:
1. Searching for recent papers/articles on topic (with date filtering)
2. Extracting key terms from results using word frequency analysis
3. Comparing term frequencies across time windows (recent vs older)
4. Identifying emerging (new/growing), declining (shrinking), and stable terms
5. Generating forecast of likely next developments
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.tools.trend_forecaster")

# Min term length (filter noise)
_MIN_TERM_LEN = 3
# Min frequency to be considered
_MIN_FREQUENCY = 2
# Terms to exclude from analysis
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "be", "been", "have", "has", "having", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must",
    "for", "to", "of", "in", "on", "at", "by", "with", "from",
    "as", "about", "into", "through", "during", "before", "after",
    "above", "below", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "both", "each", "few", "more",
    "most", "other", "same", "so", "such", "no", "nor", "not",
    "only", "own", "what", "which", "who", "whom", "this", "that",
    "it", "its", "they", "them", "their", "we", "us", "our",
    "i", "you", "he", "she", "me", "him", "her", "my", "your",
    "research", "study", "paper", "article", "data", "results",
})


async def _search_with_date_range(
    client: httpx.AsyncClient,
    query: str,
    start_date: str,
    end_date: str,
    provider: str = "exa",
) -> list[dict[str, Any]]:
    """Search using date range filters via research_search simulation.

    Returns list of search results with title and snippet.
    """
    try:
        # For demo/testing, use a simplified search without actual API
        # In production, this would call the actual research_search tool
        logger.debug(
            "searching_with_dates query=%s start=%s end=%s",
            query[:50],
            start_date,
            end_date,
        )

        # Simulated results - in production would be real API call
        return []
    except Exception as exc:
        logger.debug("search_with_date_range failed: %s", exc)
        return []


def _extract_terms(text: str) -> list[str]:
    """Extract meaningful terms from text.

    Converts to lowercase, removes special chars, filters stopwords.
    """
    if not text:
        return []

    # Convert to lowercase and split on word boundaries
    text = text.lower()
    # Remove special characters but keep hyphens and underscores for tech terms
    text = re.sub(r"[^\w\s-]", " ", text)
    words = text.split()

    # Filter: minimum length, not stopword, alphanumeric or hyphens
    terms = [
        w for w in words
        if len(w) >= _MIN_TERM_LEN
        and w not in _STOPWORDS
        and re.match(r"^[a-z0-9_-]+$", w)
    ]

    return terms


def _compute_term_frequencies(
    texts: list[str], normalize: bool = False
) -> dict[str, float]:
    """Compute term frequencies from text list.

    Args:
        texts: list of text snippets
        normalize: if True, normalize by total documents

    Returns:
        Dict mapping term -> frequency (raw count or normalized)
    """
    all_terms: list[str] = []

    for text in texts:
        terms = _extract_terms(text)
        all_terms.extend(terms)

    if not all_terms:
        return {}

    # Count frequencies
    freq_counter = Counter(all_terms)

    # Filter: only terms with min frequency
    filtered = {
        term: float(count)
        for term, count in freq_counter.items()
        if count >= _MIN_FREQUENCY
    }

    # Normalize if requested
    if normalize and texts:
        total_docs = len(texts)
        filtered = {
            term: freq / total_docs
            for term, freq in filtered.items()
        }

    return filtered


def _classify_trend_signals(
    recent_terms: dict[str, float],
    older_terms: dict[str, float],
) -> tuple[list[str], list[str], list[str]]:
    """Classify terms as emerging, declining, or stable.

    Args:
        recent_terms: term frequencies from recent period
        older_terms: term frequencies from older period

    Returns:
        (emerging, declining, stable) lists of terms
    """
    emerging: list[str] = []
    declining: list[str] = []
    stable: list[str] = []

    all_terms = set(recent_terms.keys()) | set(older_terms.keys())

    for term in all_terms:
        recent_freq = recent_terms.get(term, 0.0)
        older_freq = older_terms.get(term, 0.0)

        # Emerging: appears in recent but not (or barely) in older
        if recent_freq > 0 and older_freq == 0:
            emerging.append(term)
        # Emerging: significant growth
        elif recent_freq > older_freq * 1.5 and older_freq > 0:
            emerging.append(term)
        # Declining: appears in older but not (or barely) in recent
        elif older_freq > 0 and recent_freq == 0:
            declining.append(term)
        # Declining: significant drop
        elif older_freq > recent_freq * 1.5 and recent_freq > 0:
            declining.append(term)
        # Stable: consistent presence
        else:
            stable.append(term)

    return (emerging, declining, stable)


def _predict_next_developments(
    emerging_terms: list[str],
    stable_terms: list[str],
    domain_knowledge: dict[str, list[str]] | None = None,
) -> list[str]:
    """Predict likely next developments based on emerging and stable signals.

    Args:
        emerging_terms: newly appearing/growing terms
        stable_terms: consistently present terms
        domain_knowledge: optional dict mapping stable terms to likely next steps

    Returns:
        List of predicted next developments
    """
    predictions: list[str] = []

    # Rule 1: Combinations of emerging + stable terms are likely next steps
    if emerging_terms and stable_terms:
        # Take first few emerging and combine with core stable terms
        top_emerging = emerging_terms[:3]
        core_stable = stable_terms[:2] if stable_terms else []

        for emerg in top_emerging:
            if core_stable:
                for stable in core_stable:
                    predictions.append(f"{stable} + {emerg}")
            else:
                predictions.append(f"integration of {emerg}")

    # Rule 2: If strong emerging signal, predict refinement/optimization
    if len(emerging_terms) >= 3:
        top_3_emerging = emerging_terms[:3]
        predictions.append(
            f"optimization and refinement of {', '.join(top_3_emerging)}"
        )

    # Rule 3: Domain-specific predictions
    if domain_knowledge:
        for stable_term in stable_terms[:2]:
            if stable_term in domain_knowledge:
                next_steps = domain_knowledge[stable_term]
                predictions.extend(next_steps[:2])

    # Rule 4: Cross-domain innovation prediction
    if emerging_terms:
        predictions.append(
            f"cross-domain applications of {emerging_terms[0]}"
        )

    return list(dict.fromkeys(predictions))  # Deduplicate


def _calculate_confidence(
    recent_data_points: int,
    older_data_points: int,
    emerging_count: int,
    total_unique_terms: int,
) -> float:
    """Calculate confidence score for forecast (0-1).

    Based on:
    - Sample size (more data = higher confidence)
    - Signal clarity (clear emerging/declining signals)
    - Term diversity (if many signals agree, higher confidence)
    """
    # Data point contribution (0.3 max)
    data_score = min(0.3, (recent_data_points + older_data_points) / 100.0)

    # Signal clarity (0.4 max)
    if total_unique_terms > 0:
        signal_clarity = min(0.4, emerging_count / (total_unique_terms * 2))
    else:
        signal_clarity = 0.0

    # Minimum baseline
    confidence = max(0.2, data_score + signal_clarity + 0.3)

    return min(1.0, confidence)

@handle_tool_errors("research_trend_forecast")

async def research_trend_forecast(
    topic: str,
    timeframe: str = "6months",
    min_term_frequency: int = 2,
) -> dict[str, Any]:
    """Predict research directions by analyzing term frequency evolution.

    Analyzes emerging vs declining research signals through:
    1. Multi-window search (recent + older periods)
    2. Term frequency analysis with stopword filtering
    3. Trend classification (emerging/declining/stable)
    4. Forecast generation based on signal combinations

    Args:
        topic: research topic or keyword (e.g., "transformers in NLP", "quantum ML")
        timeframe: analysis window - "3months", "6months" (default), "1year"
        min_term_frequency: minimum occurrences for term inclusion (default: 2)

    Returns:
        Dict with keys:
        - topic: input topic
        - timeframe: analysis window
        - trends: dict with keys:
            - up: list of emerging terms
            - down: list of declining terms
            - stable: list of stable terms
        - forecast: list of predicted next developments
        - data_points: total search results analyzed
        - confidence: forecast confidence (0-1)
        - timestamp: analysis timestamp ISO format
    """

    # Validate timeframe
    timeframe_days = {
        "3months": 90,
        "6months": 180,
        "1year": 365,
    }
    if timeframe not in timeframe_days:
        return {
            "error": f"invalid timeframe: {timeframe}. Use: {', '.join(timeframe_days.keys())}",
            "topic": topic,
            "confidence": 0.0,
        }

    days = timeframe_days[timeframe]
    now = datetime.now(UTC)

    # Define time windows
    recent_end = now
    recent_start = now - timedelta(days=days // 3)  # Last 1/3 of timeframe
    older_end = recent_start
    older_start = now - timedelta(days=days)  # Full historical window

    logger.info(
        "trend_forecast topic=%s timeframe=%s days=%d",
        topic,
        timeframe,
        days,
    )

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "Loom-Trend-Forecaster/1.0"},
        ) as client:
            # Search recent and older results in parallel
            # Note: actual implementation would use research_search tool
            recent_results = await _search_with_date_range(
                client,
                query=topic,
                start_date=recent_start.strftime("%Y-%m-%d"),
                end_date=recent_end.strftime("%Y-%m-%d"),
            )
            older_results = await _search_with_date_range(
                client,
                query=topic,
                start_date=older_start.strftime("%Y-%m-%d"),
                end_date=older_end.strftime("%Y-%m-%d"),
            )

        # Extract text from results (title + snippet)
        recent_texts = [
            f"{r.get('title', '')} {r.get('snippet', '')}"
            for r in recent_results
        ]
        older_texts = [
            f"{r.get('title', '')} {r.get('snippet', '')}"
            for r in older_results
        ]

        # Compute term frequencies
        recent_terms = _compute_term_frequencies(recent_texts, normalize=True)
        older_terms = _compute_term_frequencies(older_texts, normalize=True)

        # Classify trends
        emerging, declining, stable = _classify_trend_signals(
            recent_terms, older_terms
        )

        # Sort by frequency
        emerging.sort(
            key=lambda t: recent_terms.get(t, 0.0), reverse=True
        )
        declining.sort(
            key=lambda t: older_terms.get(t, 0.0), reverse=True
        )
        stable.sort(
            key=lambda t: max(recent_terms.get(t, 0), older_terms.get(t, 0)),
            reverse=True,
        )

        # Generate forecast
        forecast = _predict_next_developments(emerging, stable)

        # Calculate confidence
        total_unique = len(recent_terms) + len(older_terms)
        confidence = _calculate_confidence(
            len(recent_results),
            len(older_results),
            len(emerging),
            max(1, total_unique),  # Avoid division by zero
        )

        return {
            "topic": topic,
            "timeframe": timeframe,
            "trends": {
                "up": emerging[:10],  # Top 10 emerging
                "down": declining[:10],  # Top 10 declining
                "stable": stable[:10],  # Top 10 stable
            },
            "forecast": forecast[:5],  # Top 5 predictions
            "data_points": len(recent_results) + len(older_results),
            "confidence": round(confidence, 2),
            "timestamp": now.isoformat(),
        }

    except Exception as exc:
        logger.error("trend_forecast failed: %s", exc)
        return {
            "error": str(exc),
            "topic": topic,
            "timeframe": timeframe,
            "confidence": 0.0,
            "timestamp": now.isoformat(),
        }
