"""research_fact_verify and research_batch_verify — Cross-source fact verification.

Performs multi-source fact verification on claims by:
1. Searching for the claim across multiple sources via research_search
2. Extracting supporting/contradicting evidence from top results
3. Scoring confidence based on source agreement
4. Returning structured verdict with evidence

Batch verification processes multiple claims in parallel.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text: str, max_chars: int = 500, *, suffix: str = "...") -> str:
        """Fallback truncate if text_utils unavailable."""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - len(suffix)] + suffix

try:
    from loom.retry import with_retry
except ImportError:
    def with_retry(*args, **kwargs):  # type: ignore[misc]
        def decorator(func):  # type: ignore[no-untyped-def]
            return func
        return decorator

logger = logging.getLogger("loom.tools.fact_verifier")

# Constants
MIN_CLAIM_CHARS = 5
MAX_CLAIM_CHARS = 500
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
DEFAULT_SOURCES = 3
MAX_SOURCES = 20
DEFAULT_MIN_CONFIDENCE = 0.6
MAX_BATCH_CLAIMS = 50


def _extract_evidence(
    search_result: dict[str, Any],
) -> tuple[str, str]:
    """Extract snippet from search result for evidence analysis.

    Args:
        search_result: single search result dict from research_search

    Returns:
        (url, snippet) tuple
    """
    url = search_result.get("url", "")
    snippet = search_result.get("snippet", "")
    title = search_result.get("title", "")

    # Combine title and snippet for better evidence context
    evidence_text = f"{title}. {snippet}".strip()
    return url, truncate(evidence_text, 500)


def _score_agreement(
    results_list: list[list[dict[str, Any]]],
) -> tuple[str, float, list[dict[str, Any]], list[dict[str, Any]]]:
    """Score agreement across multiple sources.

    Analyzes search results from multiple providers and determines
    if sources agree, disagree, or provide mixed/ambiguous evidence.

    WARNING: This uses simple keyword matching, which has limitations:
    - Cannot handle negations ("X does NOT cause Y" contains "cause")
    - May misclassify conflicting statements in same snippet
    - Relies on English keywords

    Args:
        results_list: list of search result lists (one per provider attempt)

    Returns:
        (verdict, confidence, supporting_sources, contradicting_sources)
        where verdict is one of: "supported", "contradicted", "mixed", "unverified"
    """
    # Flatten all results
    all_results = []
    for results in results_list:
        if results and isinstance(results, list):
            all_results.extend(results)

    if not all_results:
        return "unverified", 0.1, [], []

    # Extract evidence snippets
    evidence_snippets = []
    urls_seen = set()

    for result in all_results:
        url, evidence = _extract_evidence(result)
        if url and url not in urls_seen:
            urls_seen.add(url)
            evidence_snippets.append({
                "url": url,
                "evidence": evidence,
                "title": result.get("title", ""),
                "source": result.get("source", "unknown"),
            })

    if not evidence_snippets:
        return "unverified", 0.1, [], []

    # Classify evidence as supporting, contradicting, or neutral
    # This is a simplified heuristic based on keywords
    # NOTE: This is naive and produces false positives on negations
    supporting_keywords = [
        "confirm", "support", "verify", "prove", "evidence", "true", "yes",
        "agree", "right", "correct", "valid", "authentic", "real"
    ]
    contradicting_keywords = [
        "contradict", "deny", "refute", "disprove", "false", "no", "wrong",
        "disagree", "incorrect", "invalid", "fake", "hoax", "misleading"
    ]

    supporting = []
    contradicting = []
    mixed = []

    for snippet_info in evidence_snippets:
        evidence = snippet_info["evidence"].lower()

        has_supporting = any(kw in evidence for kw in supporting_keywords)
        has_contradicting = any(kw in evidence for kw in contradicting_keywords)

        if has_supporting and not has_contradicting:
            supporting.append(snippet_info)
        elif has_contradicting and not has_supporting:
            contradicting.append(snippet_info)
        elif has_supporting and has_contradicting:
            # Both keywords found — likely conflicting statement or negation
            mixed.append(snippet_info)

    # Determine verdict based on source agreement
    total_classified = len(supporting) + len(contradicting)

    if total_classified == 0:
        # No strong signals found
        verdict = "unverified"
        confidence = 0.3
    elif len(supporting) >= 3:
        # 3+ sources support
        verdict = "supported"
        confidence = min(1.0, 0.85 + (len(supporting) - 3) * 0.05)
    elif len(supporting) == 2:
        # 2 sources support
        verdict = "supported"
        confidence = 0.7
    elif len(supporting) == 1:
        # Only 1 source supports
        if len(contradicting) > 0:
            verdict = "mixed"
            confidence = 0.5
        else:
            verdict = "unverified"
            confidence = 0.4
    elif len(contradicting) >= 3:
        # 3+ sources contradict
        verdict = "contradicted"
        confidence = min(1.0, 0.85 + (len(contradicting) - 3) * 0.05)
    elif len(contradicting) == 2:
        # 2 sources contradict
        verdict = "contradicted"
        confidence = 0.7
    elif len(contradicting) == 1:
        # Only 1 source contradicts
        if len(supporting) > 0:
            verdict = "mixed"
            confidence = 0.5
        else:
            verdict = "unverified"
            confidence = 0.4
    else:
        # Mixed evidence
        verdict = "mixed"
        confidence = 0.5

    return verdict, round(confidence, 2), supporting, contradicting


@with_retry(max_attempts=2, backoff_base=1.0)
@handle_tool_errors("research_fact_verify")
async def research_fact_verify(
    claim: str,
    sources: int = DEFAULT_SOURCES,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> dict[str, Any]:
    """Verify a claim across multiple sources via cross-source agreement analysis.

    Performs fact verification by:
    1. Searching for the claim across multiple search providers
    2. Extracting evidence snippets from top results
    3. Analyzing source agreement patterns
    4. Computing confidence based on agreement levels

    Confidence scoring:
    - 3+ sources agree: confidence 0.9+ (supported/contradicted)
    - 2 sources agree: confidence 0.7 (supported/contradicted)
    - Mixed/conflicting: confidence 0.3-0.5
    - No sources found: confidence 0.1 (unverified)

    Args:
        claim: the claim to verify (5-500 chars)
        sources: number of search results to analyze per provider (1-20, default 3)
        min_confidence: minimum confidence threshold to filter results (0.0-1.0, default 0.6)

    Returns:
        Dict with keys:
        - claim: original claim
        - verdict: one of "supported", "contradicted", "unverified", "mixed"
        - confidence: 0-1 confidence score
        - supporting_sources: list of {url, evidence, title, source}
        - contradicting_sources: list of {url, evidence, title, source}
        - evidence_summary: concise summary of findings
        - total_sources_analyzed: count of unique sources consulted
        - error: error message if verification failed
    """
    # Validate inputs
    if not claim or len(claim) < MIN_CLAIM_CHARS:
        error_msg = f"claim must be at least {MIN_CLAIM_CHARS} characters"
        logger.warning("fact_verify_invalid_claim length=%d", len(claim) if claim else 0)
        return {
            "claim": claim,
            "verdict": "unverified",
            "confidence": 0.0,
            "supporting_sources": [],
            "contradicting_sources": [],
            "evidence_summary": error_msg,
            "total_sources_analyzed": 0,
            "error": error_msg,
        }

    if len(claim) > MAX_CLAIM_CHARS:
        error_msg = f"claim exceeds {MAX_CLAIM_CHARS} character limit"
        logger.warning("fact_verify_claim_too_long length=%d", len(claim))
        return {
            "claim": claim,
            "verdict": "unverified",
            "confidence": 0.0,
            "supporting_sources": [],
            "contradicting_sources": [],
            "evidence_summary": error_msg,
            "total_sources_analyzed": 0,
            "error": error_msg,
        }

    # Validate sources parameter
    sources = max(1, min(sources, MAX_SOURCES))

    # Validate min_confidence
    if min_confidence < MIN_CONFIDENCE or min_confidence > MAX_CONFIDENCE:
        min_confidence = DEFAULT_MIN_CONFIDENCE

    logger.info(
        "fact_verify_start claim=%s sources=%d min_confidence=%.2f",
        claim[:50],
        sources,
        min_confidence,
    )

    try:
        from loom.tools.core.search import research_search

        # Search using multiple providers in parallel
        # Try different providers for better coverage
        search_tasks = [
            research_search(claim, provider="exa", n=sources),
            research_search(claim, provider="tavily", n=sources),
            research_search(claim, provider="brave", n=sources),
        ]

        # Execute searches in parallel
        results_list = []
        try:
            raw_results = await asyncio.gather(
                *search_tasks,
                return_exceptions=True,  # Don't fail if one provider fails
            )

            # Extract results, handling exceptions
            for result in raw_results:
                if isinstance(result, Exception):
                    logger.warning("search_provider_failed: %s", result)
                    continue
                if isinstance(result, dict):
                    source_results = result.get("results", [])
                    if source_results:
                        results_list.append(source_results)

        except Exception as e:
            logger.error("fact_verify_search_error: %s", e)
            return {
                "claim": claim,
                "verdict": "unverified",
                "confidence": 0.0,
                "supporting_sources": [],
                "contradicting_sources": [],
                "evidence_summary": f"Search failed: {str(e)}",
                "total_sources_analyzed": 0,
                "error": str(e),
            }

        # Score agreement across sources
        verdict, confidence, supporting, contradicting = _score_agreement(results_list)

        # Filter by minimum confidence threshold
        if confidence < min_confidence:
            verdict = "unverified"
            # Note: confidence is NOT changed here. Low confidence + "unverified" verdict
            # creates an intentional contract: "unverified" means we don't trust the result

        # Generate evidence summary
        summary_parts = []
        if supporting:
            summary_parts.append(
                f"{len(supporting)} supporting source(s) found"
            )
        if contradicting:
            summary_parts.append(
                f"{len(contradicting)} contradicting source(s) found"
            )
        # Note: mixed evidence is counted but not separately reported in summary
        # It contributes to the verdict but is not distinguished in the text
        if not summary_parts:
            summary_parts.append("Insufficient evidence to verify claim")

        evidence_summary = "; ".join(summary_parts)

        total_sources = len(supporting) + len(contradicting)

        logger.info(
            "fact_verify_complete claim=%s verdict=%s confidence=%.2f sources=%d",
            claim[:50],
            verdict,
            confidence,
            total_sources,
        )

        return {
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "supporting_sources": supporting,
            "contradicting_sources": contradicting,
            "evidence_summary": evidence_summary,
            "total_sources_analyzed": total_sources,
        }

    except ImportError as e:
        error_msg = f"research_search not available: {e}"
        logger.error("fact_verify_import_error: %s", e)
        return {
            "claim": claim,
            "verdict": "unverified",
            "confidence": 0.0,
            "supporting_sources": [],
            "contradicting_sources": [],
            "evidence_summary": error_msg,
            "total_sources_analyzed": 0,
            "error": error_msg,
        }
    except Exception as e:
        error_msg = f"fact verification failed: {str(e)}"
        logger.error("fact_verify_error: %s", e)
        return {
            "claim": claim,
            "verdict": "unverified",
            "confidence": 0.0,
            "supporting_sources": [],
            "contradicting_sources": [],
            "evidence_summary": error_msg,
            "total_sources_analyzed": 0,
            "error": error_msg,
        }


@handle_tool_errors("research_batch_verify")
async def research_batch_verify(
    claims: list[str],
    sources: int = DEFAULT_SOURCES,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> list[dict[str, Any]]:
    """Verify multiple claims in parallel via cross-source fact checking.

    Verifies a batch of claims concurrently, returning results for each claim.
    Useful for bulk fact-checking operations.

    Args:
        claims: list of claims to verify (1-50 claims, each 5-500 chars)
        sources: number of search results per provider (1-20, default 3)
        min_confidence: minimum confidence threshold (0.0-1.0, default 0.6)

    Returns:
        List of dicts, one per claim, with keys:
        - claim: original claim
        - verdict: one of "supported", "contradicted", "unverified", "mixed"
        - confidence: 0-1 confidence score
        - supporting_sources: list of {url, evidence, title, source}
        - contradicting_sources: list of {url, evidence, title, source}
        - evidence_summary: concise summary of findings
        - total_sources_analyzed: count of unique sources
        - error: error message if applicable
    """
    # Validate inputs
    if not claims or not isinstance(claims, list):
        error_msg = "claims must be a non-empty list"
        logger.warning("batch_verify_invalid_input")
        return [{
            "claim": "",
            "verdict": "unverified",
            "confidence": 0.0,
            "supporting_sources": [],
            "contradicting_sources": [],
            "evidence_summary": error_msg,
            "total_sources_analyzed": 0,
            "error": error_msg,
        }]

    if len(claims) > MAX_BATCH_CLAIMS:
        logger.warning(
            "batch_verify_too_many_claims count=%d max=%d",
            len(claims),
            MAX_BATCH_CLAIMS,
        )
        claims = claims[:MAX_BATCH_CLAIMS]

    logger.info("batch_verify_start count=%d", len(claims))

    try:
        # Verify all claims in parallel
        verify_tasks = [
            research_fact_verify(claim, sources=sources, min_confidence=min_confidence)
            for claim in claims
        ]

        results = await asyncio.gather(*verify_tasks, return_exceptions=True)

        # Handle exceptions in results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("batch_verify_claim_failed index=%d error=%s", i, result)
                final_results.append({
                    "claim": claims[i] if i < len(claims) else "",
                    "verdict": "unverified",
                    "confidence": 0.0,
                    "supporting_sources": [],
                    "contradicting_sources": [],
                    "evidence_summary": f"Verification failed: {str(result)}",
                    "total_sources_analyzed": 0,
                    "error": str(result),
                })
            else:
                final_results.append(result)

        logger.info("batch_verify_complete count=%d", len(final_results))
        return final_results

    except Exception as e:
        error_msg = f"batch verification failed: {str(e)}"
        logger.error("batch_verify_error: %s", e)
        return [{
            "claim": claim,
            "verdict": "unverified",
            "confidence": 0.0,
            "supporting_sources": [],
            "contradicting_sources": [],
            "evidence_summary": error_msg,
            "total_sources_analyzed": 0,
            "error": error_msg,
        } for claim in claims]
