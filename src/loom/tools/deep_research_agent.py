"""Hierarchical multi-agent research orchestrator.

Implements a 5-stage hierarchical research pipeline:
1. Decompose query into sub-questions
2. Search for sources per sub-question
3. Fetch and extract content from sources
4. Synthesize findings with LLM
5. Return structured report with confidence scoring
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("loom.tools.deep_research_agent")


async def research_hierarchical_research(
    query: str,
    depth: int = 2,
    max_sources: int = 10,
    model: str = "nvidia",
) -> dict[str, Any]:
    """Execute hierarchical multi-agent research on a query.

    Decomposes the query into sub-questions, searches for sources,
    fetches content, and synthesizes findings with confidence scoring.

    Args:
        query: Research query (max 500 chars)
        depth: Recursion depth for sub-questions (1-3, default 2)
        max_sources: Max sources per sub-question (1-50, default 10)
        model: LLM model for synthesis (nvidia, groq, deepseek, gemini)

    Returns:
        Dict with:
        - query: Original query
        - sub_questions: List of decomposed questions
        - findings: List of extracted findings with sources
        - sources: List of unique sources used (with title, url)
        - synthesis: LLM-synthesized summary
        - confidence_score: 0.0-1.0 confidence in findings
        - error: Error message if execution failed (else None)
    """
    # ── Input validation ──
    if not query or not isinstance(query, str):
        return {
            "query": query,
            "sub_questions": [],
            "findings": [],
            "sources": [],
            "synthesis": "",
            "confidence_score": 0.0,
            "error": "query must be a non-empty string",
        }

    query = query.strip()[:500]  # Cap to 500 chars
    depth = max(1, min(depth, 3))  # Clamp to 1-3
    max_sources = max(1, min(max_sources, 50))  # Clamp to 1-50

    logger.info(
        "hierarchical_research query=%s depth=%d max_sources=%d model=%s",
        query[:50],
        depth,
        max_sources,
        model,
    )

    result = {
        "query": query,
        "sub_questions": [],
        "findings": [],
        "sources": [],
        "synthesis": "",
        "confidence_score": 0.0,
        "error": None,
    }

    try:
        # Stage 1: Decompose query into sub-questions
        sub_questions = await _decompose_query(query, depth)
        result["sub_questions"] = sub_questions

        # Stage 2-3: Search, fetch, and extract per sub-question
        findings_by_question: dict[str, list[dict[str, Any]]] = {}
        sources_set: set[str] = set()
        all_content = []

        for sub_q in sub_questions:
            try:
                findings_list, sources_list, content = await _fetch_sources_for_question(
                    sub_q, max_sources
                )
                findings_by_question[sub_q] = findings_list
                sources_set.update(sources_list)
                all_content.extend(content)
            except Exception as e:
                logger.warning(
                    "fetch_failed sub_question=%s error=%s",
                    sub_q[:50],
                    str(e)[:100],
                )
                # Continue with other sub-questions
                continue

        result["findings"] = [f for findings in findings_by_question.values() for f in findings]
        result["sources"] = list(sources_set)[:30]  # Cap to 30 unique sources

        # Stage 4: Synthesize with LLM
        if result["findings"]:
            synthesis, confidence = await _synthesize_findings(
                query, result["findings"], all_content, model
            )
            result["synthesis"] = synthesis
            result["confidence_score"] = confidence
        else:
            result["confidence_score"] = 0.0

    except Exception as e:
        logger.error(
            "hierarchical_research_failed query=%s error=%s",
            query[:50],
            str(e)[:200],
        )
        result["error"] = f"Research failed: {str(e)[:100]}"

    return result


async def _decompose_query(query: str, depth: int) -> list[str]:
    """Decompose a query into sub-questions using LLM."""
    try:
        from loom.tools.llm import research_llm_answer

        prompt = (
            f"Break down this research query into {min(depth + 1, 4)} specific, "
            f"focused sub-questions that together answer the main query. "
            f"Return only the sub-questions, one per line.\n\nQuery: {query}"
        )

        result = research_llm_answer(prompt, model="nvidia", max_tokens=300)
        if result.get("answer"):
            lines = [
                line.strip() for line in result["answer"].split("\n") if line.strip()
            ]
            return lines[:5]  # Cap to 5 sub-questions
        return [query]  # Fallback: use original query
    except Exception as e:
        logger.warning("query_decompose_failed error=%s", str(e)[:100])
        return [query]  # Fallback: use original query


async def _fetch_sources_for_question(
    question: str, max_sources: int
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Search, fetch, and extract content for a single sub-question.

    Returns:
        (findings_list, sources_urls, extracted_content)
    """
    findings = []
    sources = []
    content_list = []

    try:
        # Stage 2: Search
        from loom.tools.search import research_search

        search_result = research_search(
            question, provider="exa", n=min(max_sources, 10)
        )
        if not search_result.get("results"):
            return findings, sources, content_list

        # Stage 3: Fetch top results
        from loom.tools.fetch import research_fetch

        for result in search_result["results"][:max_sources]:
            url = result.get("url")
            if not url:
                continue

            try:
                fetch_result = research_fetch(url, mode="stealthy", max_chars=5000)
                if fetch_result.get("content"):
                    title = result.get("title", "Unknown")
                    sources.append(url)
                    content_list.append(fetch_result["content"])

                    findings.append(
                        {
                            "source": url,
                            "title": title,
                            "snippet": result.get("snippet", "")[:300],
                            "relevance": result.get("score", 0.5),
                        }
                    )
            except Exception as e:
                logger.warning(
                    "fetch_url_failed url=%s error=%s",
                    url[:50],
                    str(e)[:100],
                )
                continue

    except Exception as e:
        logger.warning("search_failed question=%s error=%s", question[:50], str(e)[:100])

    return findings, sources, content_list


async def _synthesize_findings(
    query: str,
    findings: list[dict[str, Any]],
    content: list[str],
    model: str,
) -> tuple[str, float]:
    """Synthesize findings using LLM and compute confidence score."""
    try:
        from loom.tools.llm import research_llm_answer

        # Build synthesis prompt
        findings_text = "\n".join(
            [f"- {f['title']} ({f['source']}): {f['snippet']}" for f in findings[:10]]
        )

        prompt = (
            f"Based on these research findings, provide a comprehensive "
            f"answer to: {query}\n\nFindings:\n{findings_text}\n\n"
            f"Synthesize the key insights in 2-3 paragraphs."
        )

        result = research_llm_answer(prompt, model=model, max_tokens=500)
        synthesis = result.get("answer", "")

        # Simple confidence scoring: based on number of sources and content length
        source_count = len(findings)
        total_content_len = sum(len(c) for c in content)

        # Confidence: 0.3-1.0 based on sources (3-10) and content (3KB-15KB)
        source_factor = min(source_count / 10.0, 1.0) * 0.5
        content_factor = min(total_content_len / 15000.0, 1.0) * 0.5
        confidence = max(0.3, source_factor + content_factor)

        return synthesis, confidence

    except Exception as e:
        logger.warning("synthesize_failed error=%s", str(e)[:100])
        return "", 0.5
