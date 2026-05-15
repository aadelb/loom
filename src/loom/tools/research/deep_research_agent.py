"""Hierarchical multi-agent research orchestrator.

Implements a 5-stage hierarchical research pipeline:
1. Decompose query into sub-questions
2. Search for sources per sub-question
3. Fetch and extract content from sources
4. Synthesize findings with LLM
5. Return structured report with confidence scoring
"""
from __future__ import annotations

import logging
from typing import Any

from loom.error_responses import handle_tool_errors
from loom.pipeline_runner import run_pipeline

logger = logging.getLogger("loom.tools.deep_research_agent")


@handle_tool_errors("research_hierarchical_research")
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
        # Define pipeline stages
        stages = [
            (
                "decompose",
                lambda ctx: _decompose_query(query, depth),
            ),
            (
                "fetch_sources",
                lambda ctx: _fetch_all_sources(ctx.get("decompose", []), max_sources),
            ),
            (
                "synthesize",
                lambda ctx: _synthesize_findings(
                    query,
                    ctx.get("fetch_sources", {}).get("findings", []),
                    ctx.get("fetch_sources", {}).get("content", []),
                    model,
                ),
            ),
        ]

        # Execute pipeline
        pipeline_result = await run_pipeline(
            stages,
            context={},
            stop_on_failure=True,
            timeout_per_stage=120.0,
        )

        if not pipeline_result.success:
            result["error"] = f"Pipeline failed at stage: {[s.name for s in pipeline_result.stages if not s.success]}"
            return result

        # Extract results from pipeline context
        sub_questions = pipeline_result.get_stage("decompose")
        if sub_questions and sub_questions.success:
            result["sub_questions"] = sub_questions.data or []

        fetch_results = pipeline_result.get_stage("fetch_sources")
        if fetch_results and fetch_results.success:
            fetch_data = fetch_results.data or {}
            result["findings"] = fetch_data.get("findings", [])
            result["sources"] = fetch_data.get("sources", [])[:30]

        synthesize_results = pipeline_result.get_stage("synthesize")
        if synthesize_results and synthesize_results.success:
            synthesis_data = synthesize_results.data or ({}, 0.0)
            result["synthesis"] = synthesis_data[0] if isinstance(synthesis_data, tuple) else ""
            result["confidence_score"] = synthesis_data[1] if isinstance(synthesis_data, tuple) else 0.0

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
        from loom.tools.llm.llm import research_llm_answer

        prompt = (
            f"Break down this research query into {min(depth + 1, 4)} specific, "
            f"focused sub-questions that together answer the main query. "
            f"Return only the sub-questions, one per line.\n\nQuery: {query}"
        )

        result = await research_llm_answer(prompt, model="nvidia", max_tokens=300)
        if result.get("answer"):
            lines = [
                line.strip() for line in result["answer"].split("\n") if line.strip()
            ]
            return lines[:5]  # Cap to 5 sub-questions
        return [query]  # Fallback: use original query
    except Exception as e:
        logger.warning("query_decompose_failed error=%s", str(e)[:100])
        return [query]  # Fallback: use original query


async def _fetch_all_sources(
    questions: list[str], max_sources: int
) -> dict[str, Any]:
    """Search, fetch, and extract content for all sub-questions.

    Returns:
        Dict with 'findings' and 'sources' keys
    """
    findings = []
    sources = []
    content_list = []

    for question in questions:
        try:
            sub_findings, sub_sources, sub_content = await _fetch_sources_for_question(
                question, max_sources
            )
            findings.extend(sub_findings)
            sources.extend(sub_sources)
            content_list.extend(sub_content)
        except Exception as e:
            logger.warning(
                "fetch_failed sub_question=%s error=%s",
                question[:50],
                str(e)[:100],
            )
            # Continue with other sub-questions
            continue

    return {
        "findings": findings,
        "sources": list(set(sources)),  # Deduplicate
        "content": content_list,
    }


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
        from loom.tools.core.search import research_search

        search_result = await research_search(
            question, provider="exa", n=min(max_sources, 10)
        )
        if not search_result.get("results"):
            return findings, sources, content_list

        # Stage 3: Fetch top results
        from loom.tools.core.fetch import research_fetch

        for result in search_result["results"][:max_sources]:
            url = result.get("url")
            if not url:
                continue

            try:
                fetch_result = await research_fetch(url, mode="stealthy", max_chars=5000)
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
        from loom.tools.llm.llm import research_llm_answer

        # Build synthesis prompt
        findings_text = "\n".join(
            [f"- {f['title']} ({f['source']}): {f['snippet']}" for f in findings[:10]]
        )

        prompt = (
            f"Based on these research findings, provide a comprehensive "
            f"answer to: {query}\n\nFindings:\n{findings_text}\n\n"
            f"Synthesize the key insights in 2-3 paragraphs."
        )

        result = await research_llm_answer(prompt, model=model, max_tokens=500)
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
