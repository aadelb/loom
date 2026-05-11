"""Brain Reasoning Layer — Tool selection, param extraction, and multi-step planning.

Primary tool detection uses keyword matching (weight 0.35), with semantic and
fuzzy methods as secondary signals. Provider is always NVIDIA NIM (free tier).
"""

from __future__ import annotations

import difflib
import inspect
import json
import logging
import re
from pathlib import Path
from typing import Any

from loom.brain.memory import get_memory
from loom.brain.perception import parse_intent
from loom.brain.types import (
    ExecutionPlan,
    PlanStep,
    QualityMode,
    ToolMatch,
    ToolMeta,
)

logger = logging.getLogger("loom.brain.reasoning")

_LLM_AVAILABLE = False
_tool_name_index: dict[str, str] | None = None
_server_tools: dict[str, ToolMeta] | None = None
_brain_index_loaded = False


def _select_best_provider(quality_mode: QualityMode) -> str:
    """Always return nvidia — NVIDIA NIM is free and required for Brain."""
    return "nvidia"


def _load_brain_index() -> dict[str, ToolMeta]:
    """Load tool metadata from brain_index.json (primary source, no network needed)."""
    global _server_tools, _brain_index_loaded
    if _brain_index_loaded and _server_tools is not None:
        return _server_tools

    import json as _json

    index_path = Path(__file__).parent / "brain_index.json"
    if index_path.exists():
        try:
            data = _json.loads(index_path.read_text(encoding="utf-8"))
            tools = {}
            for t in data.get("tools", []):
                name = t.get("name", "")
                if name:
                    tools[name] = ToolMeta(
                        name=name,
                        description=t.get("description", ""),
                        parameters=t.get("parameters", {}),
                        categories=t.get("categories", []),
                        is_async=t.get("is_async", True),
                    )
            _server_tools = tools
            _brain_index_loaded = True
            logger.info("loaded %d tools from brain_index.json", len(tools))
            return tools
        except Exception as exc:
            logger.warning("brain_index.json load failed: %s", exc)

    return _fetch_server_tools_sync()


def _fetch_server_tools_sync() -> dict[str, ToolMeta]:
    """Fallback: fetch tool list from running server."""
    global _server_tools
    if _server_tools is not None:
        return _server_tools

    try:
        import httpx

        resp = httpx.get("http://localhost:8787/api/v1/tools", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            tools = {}
            if isinstance(data, dict) and "tools" in data:
                for t in data["tools"]:
                    name = t.get("name", "")
                    if name:
                        tools[name] = ToolMeta(
                            name=name,
                            description=t.get("description", ""),
                            parameters=t.get("parameters", {}),
                            categories=t.get("categories", []),
                        )
            elif isinstance(data, list):
                for t in data:
                    name = t.get("name", "") if isinstance(t, dict) else str(t)
                    if name:
                        tools[name] = ToolMeta(name=name)
            _server_tools = tools
            logger.info("fetched %d tools from server", len(tools))
            return tools
    except Exception as exc:
        logger.debug("server tool fetch failed: %s", exc)

    _server_tools = {}
    return _server_tools


def _build_tool_name_index() -> dict[str, str]:
    """Build once: scan loom/tools/*.py for function names → module paths."""
    global _tool_name_index
    if _tool_name_index is not None:
        return _tool_name_index

    index: dict[str, str] = {}
    tools_dir = Path(__file__).parent.parent / "tools"
    if tools_dir.is_dir():
        for py_file in tools_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                import ast

                tree = ast.parse(py_file.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("research_"):
                            index[node.name] = str(py_file)
            except Exception:
                continue

    _tool_name_index = index
    logger.info("built tool name index: %d entries", len(index))
    return index


def _resolve_tool_name(candidate: str) -> str:
    """Resolve a candidate tool name to an actual registered tool.

    Uses high-cutoff fuzzy matching (0.9) to prevent false positives.
    Returns the candidate unchanged if no close match found.
    """
    server_tools = _fetch_server_tools_sync()
    if candidate in server_tools:
        return candidate

    name_index = _build_tool_name_index()
    if candidate in name_index:
        return candidate

    all_names = list(server_tools.keys()) + list(name_index.keys())
    matches = difflib.get_close_matches(candidate, all_names, n=1, cutoff=0.9)
    if matches:
        return matches[0]

    return candidate


def select_tools(
    query: str,
    quality_mode: QualityMode = QualityMode.AUTO,
    max_tools: int = 5,
    forced_tools: list[str] | None = None,
) -> list[ToolMatch]:
    """Select the best tools for a query using keyword-primary matching.

    Composite scoring (keyword-dominant):
        keyword:   0.35
        semantic:  0.25
        gorilla:   0.15
        signature: 0.10
        category:  0.10
        usage:     0.05
    """
    if forced_tools:
        return [
            ToolMatch(tool_name=_resolve_tool_name(t), confidence=1.0, match_source="forced")
            for t in forced_tools
        ]

    intent = parse_intent(query)
    keywords = intent["keywords"]
    domains = intent["domains"]
    entities = intent["entities"]
    server_tools = _load_brain_index()

    if not server_tools:
        return _fallback_keyword_match(query, keywords, max_tools)

    scored: list[tuple[str, float, str]] = []

    # Adaptive weights: boost category when domain is specific (not "general")
    has_specific_domain = domains and domains != ["general"]
    w_keyword = 0.30
    w_semantic = 0.20
    w_signature = 0.15  # Boosted: entity-param alignment is very informative
    w_category = 0.20 if has_specific_domain else 0.08
    w_usage = 0.05
    w_name_match = 0.10  # New: direct tool name match bonus

    for tool_name, meta in server_tools.items():
        keyword_score = _keyword_score(tool_name, meta, keywords, domains)
        semantic_score = _semantic_score(tool_name, meta, query)
        signature_score = _signature_score(meta, entities)
        category_score = _category_score(meta, domains)
        usage_score = _usage_score(tool_name)
        name_match_score = _name_match_score(tool_name, keywords)

        composite = (
            keyword_score * w_keyword
            + semantic_score * w_semantic
            + signature_score * w_signature
            + category_score * w_category
            + usage_score * w_usage
            + name_match_score * w_name_match
        )

        if composite > 0.08:
            scored.append((tool_name, composite, "composite"))

    scored.sort(key=lambda x: x[1], reverse=True)

    limit = max_tools
    if quality_mode == QualityMode.ECONOMY:
        limit = min(max_tools, 5)
    elif quality_mode == QualityMode.MAX:
        limit = min(max_tools, 100)

    results = []
    for tool_name, score, source in scored[:limit]:
        results.append(
            ToolMatch(tool_name=tool_name, confidence=round(score, 4), match_source=source)
        )

    return results


def _keyword_score(
    tool_name: str, meta: ToolMeta, keywords: list[str], domains: list[str]
) -> float:
    """Score based on keyword overlap between query keywords and tool name/description.

    Uses both exact match and substring match for higher recall.
    Weights exact matches higher than substring matches.
    """
    name_parts = set(tool_name.replace("research_", "").split("_"))
    desc_words = set(meta.description.lower().split()) if meta.description else set()
    searchable = name_parts | desc_words

    if not keywords:
        return 0.0

    exact_hits = 0
    substring_hits = 0
    for kw in keywords:
        if kw in searchable:
            exact_hits += 1
        elif any(kw in s for s in searchable):
            substring_hits += 1

    score = (exact_hits * 1.0 + substring_hits * 0.5) / max(len(keywords), 1)
    return min(score, 1.0)


def _name_match_score(tool_name: str, keywords: list[str]) -> float:
    """Bonus score when keywords appear directly in tool name (strongest signal).

    'nuclei' in query + 'nuclei' in 'research_nuclei_scan' = high confidence.
    """
    if not keywords:
        return 0.0
    name_parts = set(tool_name.replace("research_", "").split("_"))
    hits = sum(1 for kw in keywords if kw in name_parts)
    return min(hits / max(len(keywords), 2), 1.0)


def _semantic_score(tool_name: str, meta: ToolMeta, query: str) -> float:
    """Lightweight semantic score using word overlap ratio.

    Weights longer matching words higher (IDF-like effect).
    """
    query_words = set(query.lower().split())
    tool_words = set(tool_name.split("_")) | set(meta.description.lower().split()[:30])
    if not query_words or not tool_words:
        return 0.0

    weighted_overlap = 0.0
    for word in query_words & tool_words:
        # Longer/rarer words score higher (crude IDF proxy)
        weighted_overlap += min(len(word) / 5, 1.5)

    return min(weighted_overlap / max(len(query_words), 4), 1.0)


def _signature_score(meta: ToolMeta, entities: dict[str, list[str]]) -> float:
    """Score based on parameter-entity alignment.

    If query contains a URL and tool accepts 'url' param → strong match.
    If query contains domain and tool accepts 'domain'/'target' → strong match.
    """
    if not entities or not meta.parameters:
        return 0.0
    param_names = set(meta.parameters.keys()) if isinstance(meta.parameters, dict) else set()

    score = 0.0
    # URL entity → url/target param alignment (strongest signal)
    if "urls" in entities:
        if "url" in param_names or "target_url" in param_names:
            score += 0.5
        if "target" in param_names:
            score += 0.3

    # Domain entity → domain/target param alignment
    if "domains" in entities:
        if "domain" in param_names or "target" in param_names:
            score += 0.4

    # IP entity → ip/target param alignment
    if "ips" in entities:
        if "ip" in param_names or "target" in param_names or "host" in param_names:
            score += 0.4

    # Email entity → email param alignment
    if "emails" in entities:
        if "email" in param_names or "target" in param_names:
            score += 0.4

    return min(score, 1.0)


def _category_score(meta: ToolMeta, domains: list[str]) -> float:
    """Score based on category overlap with detected domains.

    Returns graduated score: more category matches = higher score.
    """
    if not meta.categories or not domains:
        return 0.0
    cat_set = set(c.lower() for c in meta.categories)
    matches = sum(1 for d in domains if d in cat_set)
    return min(matches / max(len(domains), 1), 1.0)


def _usage_score(tool_name: str) -> float:
    """Score based on historical reliability + affinity from memory."""
    memory = get_memory()
    reliability = memory.get_tool_reliability(tool_name)
    affinity = memory.get_affinity_boost(tool_name)
    return min(reliability + affinity, 1.0)


def _fallback_keyword_match(
    query: str, keywords: list[str], max_tools: int
) -> list[ToolMatch]:
    """Fallback when server tools aren't available — match against file index."""
    name_index = _build_tool_name_index()
    scored: list[tuple[str, float]] = []

    for func_name in name_index:
        name_parts = set(func_name.replace("research_", "").split("_"))
        hits = sum(1 for kw in keywords if kw in name_parts)
        if hits > 0:
            score = hits / max(len(keywords), 1)
            scored.append((func_name, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [
        ToolMatch(tool_name=name, confidence=round(score, 4), match_source="keyword_fallback")
        for name, score in scored[:max_tools]
    ]


def decompose_query(query: str) -> list[str]:
    """Decompose a complex query into sub-queries for multi-tool routing.

    Splits on conjunctions and clause boundaries while preserving meaning.
    """
    import re

    separators = re.compile(
        r"\b(?:and also|and then|then|additionally|also|after that|next|plus)\b",
        re.I,
    )

    parts = separators.split(query)
    sub_queries = [p.strip() for p in parts if len(p.strip()) > 10]

    return sub_queries if len(sub_queries) > 1 else [query]


def plan_workflow(
    query: str,
    matched_tools: list[ToolMatch],
    quality_mode: QualityMode = QualityMode.AUTO,
) -> ExecutionPlan:
    """Build an execution plan from matched tools.

    For economy mode: single tool, 1 iteration.
    For auto mode: up to 3 steps.
    For max mode: up to 5 steps with chaining.

    Supports query decomposition for multi-intent queries.
    """
    intent = parse_intent(query)
    max_steps = {"max": 5, "auto": 3, "economy": 1}[quality_mode.value]

    # For multi-step intents, decompose and match tools per sub-query
    if intent["intent_type"] == "multi_step" and quality_mode != QualityMode.ECONOMY:
        sub_queries = decompose_query(query)
        if len(sub_queries) > 1:
            steps: list[PlanStep] = []
            for i, sub_q in enumerate(sub_queries[:max_steps]):
                sub_matches = select_tools(sub_q, quality_mode, max_tools=1)
                if sub_matches:
                    step = PlanStep(
                        tool_name=sub_matches[0].tool_name,
                        params=sub_matches[0].inferred_params,
                        depends_on=[steps[-1].tool_name] if steps else [],
                        timeout=30.0 if quality_mode != QualityMode.MAX else 60.0,
                    )
                    steps.append(step)
            if steps:
                return ExecutionPlan(
                    steps=steps,
                    quality_mode=quality_mode,
                    estimated_cost=len(steps) * 0.001,
                )

    # Standard single-query plan
    steps = []
    for match in matched_tools[:max_steps]:
        step = PlanStep(
            tool_name=match.tool_name,
            params=match.inferred_params,
            depends_on=[steps[-1].tool_name] if steps and intent["intent_type"] == "multi_step" else [],
            timeout=30.0 if quality_mode != QualityMode.MAX else 60.0,
        )
        steps.append(step)

    return ExecutionPlan(
        steps=steps,
        quality_mode=quality_mode,
        estimated_cost=len(steps) * 0.001,
    )
