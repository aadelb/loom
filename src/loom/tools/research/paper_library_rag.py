"""Paper-grounded generation — RAG over the local paper library.

Retrieves the most relevant papers from Loom's local library (semantic
search + QA passages + knowledge-graph neighbors) and injects them as
grounding context into generation. This deepens responses and lifts the
evidence-oriented quality dimensions (citation, source_diversity, novelty,
temporal_freshness) by anchoring the answer in real, recent papers.

Reuses: research_paper_semantic_search, research_paper_qa,
research_paper_knowledge_graph, the internal LLM cascade, and the
reframing-strategy system.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.paper_library_rag")


async def _gather_paper_context(query: str, num_papers: int) -> dict[str, Any]:
    """Retrieve papers + passages + KG neighbors for a query."""
    from loom.tools.research.paper_library import (
        research_paper_semantic_search,
        research_paper_qa,
    )

    search = await research_paper_semantic_search(query=query, limit=num_papers)
    papers = search.get("results", []) if isinstance(search, dict) else []

    passages: list[dict[str, str]] = []
    for p in papers:
        pid = p.get("paper_id")
        if not pid:
            continue
        try:
            qa = await research_paper_qa(question=query, paper_ids=[pid])
            ans = qa.get("answer", "") if isinstance(qa, dict) else ""
        except Exception:
            ans = ""
        passages.append({
            "paper_id": pid,
            "title": p.get("title", ""),
            "score": p.get("score", 0),
            "passage": str(ans)[:900],
        })

    return {"papers": papers, "passages": passages}


@handle_tool_errors("research_paper_grounded_generation")
async def research_paper_grounded_generation(
    query: str,
    num_papers: int = 3,
    strategy: str = "",
    provider: str = "auto",
    max_tokens: int = 2500,
    score_dimensions: bool = True,
) -> dict[str, Any]:
    """Generate a response grounded in the local paper library with citations.

    Pipeline: semantic-search the paper library → extract a QA passage per
    paper → build a grounded system context → optionally reframe the query
    with a strategy → generate → optionally score the evidence dimensions.

    Args:
        query: The research question to answer.
        num_papers: How many papers to retrieve as grounding (default: 3).
        strategy: Optional reframing strategy name from ALL_STRATEGIES to
            apply to the query before generation (e.g. a paper-grounded one).
        provider: LLM provider override or "auto".
        max_tokens: Max tokens in the generated answer.
        score_dimensions: Whether to score citation/source_diversity/
            novelty/temporal_freshness on the output (default: True).

    Returns:
        response, cited_papers, dimension_scores, strategy_used, duration_ms.
    """
    start = time.time()

    ctx = await _gather_paper_context(query, num_papers)
    passages = ctx["passages"]

    if not passages:
        return {
            "error": "No papers retrieved — library may be empty or not embedded.",
            "hint": "Ingest papers via research_paper_discover/download/parse/embed first.",
        }

    # Build grounded system context
    grounding_lines = ["You are a research analyst. Ground your answer in these "
                       "retrieved papers and cite each by its [title] inline. "
                       "Be thorough, specific, and technical.\n"]
    for i, p in enumerate(passages, 1):
        grounding_lines.append(f"[{i}] {p['title']}")
        if p["passage"]:
            grounding_lines.append(f"    Passage: {p['passage']}")
    grounding = "\n".join(grounding_lines)

    # Optional reframe of the user query with a strategy
    user_query = query
    strategy_used = ""
    if strategy:
        try:
            from loom.tools.llm.prompt_reframe import research_prompt_reframe
            rf = await research_prompt_reframe(query=query, strategy=strategy, model=provider)
            user_query = rf.get("reframed", rf.get("reframed_prompt", query)) if isinstance(rf, dict) else query
            strategy_used = strategy
        except Exception as e:
            logger.debug("reframe_skip strategy=%s err=%s", strategy, str(e)[:80])

    # Generate grounded answer
    from loom.tools.llm.llm import _call_with_cascade
    messages = [
        {"role": "system", "content": grounding},
        {"role": "user", "content": user_query},
    ]
    try:
        resp = await _call_with_cascade(
            messages=messages,
            model="auto" if provider == "auto" else "auto",
            provider_override=None if provider == "auto" else provider,
            max_tokens=max_tokens,
            temperature=0.3,
            timeout=90,
        )
        answer = resp.text if resp else ""
        used_provider = getattr(resp, "provider", "") if resp else ""
    except Exception as e:
        return {"error": f"Generation failed: {str(e)[:200]}", "passages": passages}

    result: dict[str, Any] = {
        "query": query,
        "response": answer,
        "provider": used_provider,
        "strategy_used": strategy_used,
        "cited_papers": [
            {"paper_id": p["paper_id"], "title": p["title"], "relevance": p["score"]}
            for p in passages
        ],
        "papers_grounded": len(passages),
    }

    # Score the evidence-oriented dimensions
    if score_dimensions and answer:
        import requests
        base = "http://localhost:8788/api/v1/tools"

        async def _score(endpoint: str, payload: dict, key: str) -> float:
            try:
                r = await asyncio.to_thread(
                    requests.post, f"{base}/{endpoint}", json=payload, timeout=15
                )
                d = r.json()
                return float(d.get(key, d.get("score", 0)) or 0)
            except Exception:
                return 0.0

        cite, sdiv, nov, fresh = await asyncio.gather(
            _score("research_citation_score", {"text": answer}, "citation_score"),
            _score("research_source_diversity_score", {"text": answer}, "total_source_diversity"),
            _score("research_novelty_score", {"text": answer}, "total_novelty"),
            _score("research_temporal_freshness_score", {"text": answer}, "total_temporal_freshness"),
        )
        result["dimension_scores"] = {
            "citation": cite,
            "source_diversity": sdiv,
            "novelty": nov,
            "temporal_freshness": fresh,
            # Grounding count is a hard floor on source_diversity
            "papers_cited": len(passages),
        }

    result["duration_ms"] = round((time.time() - start) * 1000)
    return result
