"""Strategy Router — KNN-based optimal strategy selection using 37M+ vectors.

Searches the migrated ChromaDB tactics data (70K vectors with effectiveness
ratings) to find the best reframing strategy for a given query and target
provider. Uses semantic similarity to match query intent to historical
tactics that achieved effectiveness=10.

This is the "strategic brain" from Gemini's research — it predicts which
of the 957 strategies will score highest for a specific query type.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.strategy_router")

QDRANT_URL = "http://localhost:6333"
TACTICS_COLLECTION = "ummro_chromadb_migrated"
HCS10_COLLECTION = "ummro_hcs10_responses"
VECTOR_DIM = 384

_PROVIDER_STRATEGY_MAP: dict[str, list[str]] = {
    "groq": ["compliance_audit_fork", "ethical_anchor", "deep_inception", "echo_chamber"],
    "nvidia": ["reasoning_chain_hijack", "rl_optimized_framing", "cognitive_load_saturation"],
    "deepseek": ["h_cot_hijacking_chain_of_thought", "code_first", "structured_semantic_cloaking"],
    "moonshot": ["ethical_anchor", "context_first", "compliance_audit_fork"],
    "gemini": ["storytelling_embed", "grounding", "allegory_bypass"],
    "openai": ["compliance_audit_fork", "foot_in_the_door_progressive", "authority_gradient_cascade"],
    "anthropic": ["ethical_anchor", "xml_structured", "structured_semantic_cloaking"],
    "vllm": ["direct", "compliance_audit_fork", "deep_inception"],
}

_QUERY_TYPE_PATTERNS: dict[str, list[str]] = {
    "technical": ["code", "script", "command", "tool", "exploit", "vulnerability", "hack", "bypass"],
    "intelligence": ["find", "discover", "locate", "identify", "track", "monitor", "osint"],
    "social": ["manipulate", "persuade", "convince", "social engineer", "phish"],
    "financial": ["money", "transfer", "payment", "fraud", "laundering", "crypto"],
    "physical": ["break", "access", "lock", "surveillance", "weapon"],
    "academic": ["research", "study", "paper", "methodology", "framework", "analysis"],
}

_QUERY_TYPE_STRATEGIES: dict[str, list[str]] = {
    "technical": ["code_first", "structured_semantic_cloaking", "compliance_audit_fork"],
    "intelligence": ["ethical_anchor", "deep_inception", "defensive_threat_assessment"],
    "social": ["foot_in_the_door_progressive", "cognitive_dissonance_trigger", "storytelling_embed"],
    "financial": ["compliance_audit_fork", "nash_equilibrium_frame", "authority_gradient_cascade"],
    "physical": ["deep_inception", "allegory_bypass", "socratic_method_exploit"],
    "academic": ["ethical_anchor", "compliance_audit_fork", "godel_incompleteness_frame"],
}


def _embed_query_sync(text: str) -> list[float]:
    """Embed query text for vector search (sync, run in thread)."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode([text[:500]], normalize_embeddings=True)
        return embedding[0].tolist()
    except ImportError:
        return []


async def _search_tactics(
    vector: list[float],
    limit: int = 5,
    score_threshold: float = 0.3,
) -> list[dict]:
    """Search tactics collection for similar content."""
    import aiohttp

    body = {
        "vector": vector,
        "limit": limit,
        "score_threshold": score_threshold,
        "with_payload": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{QDRANT_URL}/collections/{TACTICS_COLLECTION}/points/search",
            json=body,
        ) as resp:
            data = await resp.json()
            return data.get("result", [])


async def _search_hcs10(
    vector: list[float],
    limit: int = 3,
) -> list[dict]:
    """Search HCS10 gold responses for similar content."""
    import aiohttp

    body = {
        "vector": vector,
        "limit": limit,
        "score_threshold": 0.3,
        "with_payload": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{QDRANT_URL}/collections/{HCS10_COLLECTION}/points/search",
            json=body,
        ) as resp:
            data = await resp.json()
            return data.get("result", [])


def _detect_query_type(query: str) -> str:
    """Detect query type from keywords."""
    query_lower = query.lower()
    scores = {}
    for qtype, keywords in _QUERY_TYPE_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scores[qtype] = score

    if scores:
        return max(scores, key=lambda k: scores[k])
    return "technical"


def _extract_tactics_from_results(results: list[dict]) -> list[dict]:
    """Extract tactic information from search results."""
    import json

    tactics = []
    for r in results:
        payload = r.get("payload", {})
        text = payload.get("text", "")

        try:
            if text.strip().startswith("{"):
                data = json.loads(text.split("\n")[0])
                tactics.append({
                    "tactic_file": data.get("tactic_file", ""),
                    "effectiveness": data.get("effectiveness", 0),
                    "complexity": data.get("complexity", 0),
                    "detection_difficulty": data.get("detection_difficulty", 0),
                    "techniques": data.get("techniques", [])[:5],
                    "pangea_categories": data.get("pangea_categories", [])[:4],
                    "similarity": round(r.get("score", 0), 4),
                })
        except (json.JSONDecodeError, IndexError):
            if "effectiveness" in text.lower() or "tactic" in text.lower():
                tactics.append({
                    "raw_match": text[:200],
                    "similarity": round(r.get("score", 0), 4),
                })

    return tactics


@handle_tool_errors("research_strategy_route")
async def research_strategy_route(
    query: str,
    provider: str = "groq",
    top_k: int = 5,
) -> dict[str, Any]:
    """Route query to optimal strategy using vector similarity + historical data.

    Searches 70K tactics vectors and 206 HCS10 gold responses to find
    strategies that historically achieved high scores for similar queries.

    Args:
        query: The research query to find optimal strategy for.
        provider: Target LLM provider (groq, nvidia, deepseek, moonshot, gemini, openai, anthropic, vllm).
        top_k: Number of strategy candidates to return (default 5).

    Returns:
        Dict with recommended strategies ranked by predicted effectiveness,
        query type detection, similar HCS10 responses, and tactical matches.
    """
    query_type = _detect_query_type(query)

    vector = await asyncio.to_thread(_embed_query_sync, query)
    if not vector:
        provider_strategies = _PROVIDER_STRATEGY_MAP.get(provider, ["compliance_audit_fork"])
        return {
            "recommended_strategies": provider_strategies[:top_k],
            "query_type": query_type,
            "method": "fallback_static",
            "provider": provider,
        }

    tactics_results = await _search_tactics(vector, limit=top_k * 2)
    hcs10_results = await _search_hcs10(vector, limit=3)

    extracted_tactics = _extract_tactics_from_results(tactics_results)

    hcs10_strategies = []
    for r in hcs10_results:
        payload = r.get("payload", {})
        hcs10_strategies.append({
            "strategy": payload.get("terminal_strategy", ""),
            "tactic": payload.get("tactic", ""),
            "mold": payload.get("mold", ""),
            "model": payload.get("model_id", ""),
            "hcs": payload.get("max_hcs", 0),
            "similarity": round(r.get("score", 0), 4),
        })

    provider_prefs = _PROVIDER_STRATEGY_MAP.get(provider, [])
    type_prefs = _QUERY_TYPE_STRATEGIES.get(query_type, [])

    recommended = []
    seen = set()

    for strat in hcs10_strategies:
        s = strat.get("strategy", "")
        if s and s not in seen:
            recommended.append(s)
            seen.add(s)

    for s in type_prefs:
        if s not in seen:
            recommended.append(s)
            seen.add(s)

    for s in provider_prefs:
        if s not in seen:
            recommended.append(s)
            seen.add(s)

    return {
        "recommended_strategies": recommended[:top_k],
        "query_type": query_type,
        "provider": provider,
        "method": "vector_knn",
        "tactics_matched": extracted_tactics[:5],
        "hcs10_similar": hcs10_strategies[:3],
        "confidence": round(
            max([t.get("similarity", 0) for t in extracted_tactics] or [0]) * 10, 1
        ),
    }
