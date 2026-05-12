"""Tool Recommendation Engine v2 — workflow and co-occurrence based suggestions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from loom.error_responses import handle_tool_errors

log = logging.getLogger("loom.tools.tool_recommender_v2")

# Co-occurrence pairs: tools commonly used together
CO_OCCURRENCE_MAP = {
    "research_whois": ["research_dns_lookup", "research_cert_analyzer", "research_passive_recon"],
    "research_dns_lookup": ["research_whois", "research_infra_correlator", "research_nmap_scan"],
    "research_search": ["research_fetch", "research_deep", "research_llm_summarize"],
    "research_fetch": ["research_markdown", "research_llm_summarize", "research_spider"],
    "research_deep": ["research_fetch", "research_search", "research_fact_checker"],
    "research_dark_forum": ["research_onion_discover", "research_leak_scan", "research_darkweb_early_warning"],
    "research_prompt_reframe": ["research_hcs_scorer", "research_stealth_score", "research_ask_all_models"],
    "research_metadata_forensics": ["research_stego_detect", "research_pdf_extract", "research_image_intel"],
    "research_cert_analyzer": ["research_whois", "research_domain_intel", "research_security_headers"],
    "research_passive_recon": ["research_whois", "research_dns_lookup", "research_social_graph"],
    "research_github": ["research_multi_search", "research_deep", "research_spider"],
    "research_arxiv_pipeline": ["research_fact_checker", "research_llm_summarize", "research_knowledge_graph"],
    "research_social_intel": ["research_identity_resolve", "research_social_graph", "research_leak_scan"],
    "research_threat_intel": ["research_breach_check", "research_cve_lookup", "research_urlhaus_lookup"],
    "research_leak_scan": ["research_breach_check", "research_social_intel", "research_dark_forum"],
    "research_breach_check": ["research_leak_scan", "research_threat_intel", "research_identity_resolve"],
    "research_infra_correlator": ["research_dns_lookup", "research_nmap_scan", "research_passive_recon"],
    "research_nmap_scan": ["research_cert_analyzer", "research_security_headers", "research_threat_intel"],
    "research_onion_discover": ["research_dark_forum", "research_tor_monitor", "research_darkweb_early_warning"],
    "research_identity_resolve": ["research_social_graph", "research_social_intel", "research_osint_extended"],
    "research_report_gen": ["research_search", "research_fetch", "research_llm_summarize"],
    "research_attack_scorer": ["research_prompt_reframe", "research_stealth_score", "research_ask_all_models"],
    "research_stealth_score": ["research_attack_scorer", "research_prompt_reframe", "research_model_profiler"],
    "research_llm_summarize": ["research_fetch", "research_spider", "research_extract"],
    "research_extract": ["research_llm_summarize", "research_pdf_extract", "research_knowledge_graph"],
    "research_knowledge_graph": ["research_extract", "research_fact_checker", "research_multi_search"],
    "research_fact_checker": ["research_search", "research_deep", "research_knowledge_graph"],
    "research_osint_extended": ["research_identity_resolve", "research_threat_intel", "research_passive_recon"],
    "research_model_profiler": ["research_stealth_score", "research_ask_all_models", "research_attack_scorer"],
    "research_ask_all_models": ["research_model_profiler", "research_prompt_reframe", "research_llm_summarize"],
    "research_cve_lookup": ["research_threat_intel", "research_urlhaus_lookup", "research_breach_check"],
    "research_urlhaus_lookup": ["research_cve_lookup", "research_threat_intel", "research_domain_intel"],
    "research_security_headers": ["research_cert_analyzer", "research_nmap_scan", "research_threat_intel"],
    "research_domain_intel": ["research_whois", "research_cert_analyzer", "research_security_headers"],
    "research_image_intel": ["research_metadata_forensics", "research_stego_detect", "research_vision_agent"],
    "research_pdf_extract": ["research_metadata_forensics", "research_extract", "research_text_analyze"],
    "research_text_analyze": ["research_pdf_extract", "research_llm_summarize", "research_stylometry"],
    "research_stylometry": ["research_text_analyze", "research_deception_detect", "research_cultural_attacks"],
    "research_deception_detect": ["research_stylometry", "research_sentiment_deep", "research_psychological"],
    "research_vision_agent": ["research_image_intel", "research_metadata_forensics", "research_stego_detect"],
    "research_stego_detect": ["research_image_intel", "research_vision_agent", "research_metadata_forensics"],
    "research_sentiment_deep": ["research_deception_detect", "research_psychological", "research_bias_lens"],
    "research_psychological": ["research_sentiment_deep", "research_cultural_attacks", "research_radicalization_detect"],
    "research_cultural_attacks": ["research_psychological", "research_multilang_attack", "research_stylometry"],
    "research_multilang_attack": ["research_cultural_attacks", "research_detect_language", "research_classify"],
    "research_bias_lens": ["research_sentiment_deep", "research_model_profiler", "research_ask_all_models"],
}

# Workflow templates: what steps are typically used together
WORKFLOW_TEMPLATES = {
    "osint_full": {
        "tools": ["research_search", "research_passive_recon", "research_whois", "research_infra_correlator", "research_report_gen"],
        "description": "Full OSINT reconnaissance workflow",
    },
    "threat_analysis": {
        "tools": ["research_threat_intel", "research_breach_check", "research_cve_lookup", "research_nmap_scan"],
        "description": "Threat intelligence and vulnerability analysis",
    },
    "content_analysis": {
        "tools": ["research_fetch", "research_markdown", "research_extract", "research_llm_summarize"],
        "description": "Web content extraction and analysis",
    },
    "identity_research": {
        "tools": ["research_identity_resolve", "research_social_graph", "research_social_intel", "research_report_gen"],
        "description": "Identity and relationship mapping",
    },
    "prompt_testing": {
        "tools": ["research_prompt_reframe", "research_ask_all_models", "research_attack_scorer", "research_stealth_score"],
        "description": "Prompt attack crafting and evaluation",
    },
    "dark_web": {
        "tools": ["research_dark_forum", "research_onion_discover", "research_leak_scan", "research_darkweb_early_warning"],
        "description": "Dark web intelligence gathering",
    },
    "academic_research": {
        "tools": ["research_arxiv_pipeline", "research_search", "research_fact_checker", "research_knowledge_graph"],
        "description": "Academic paper research and analysis",
    },
    "forensics": {
        "tools": ["research_metadata_forensics", "research_pdf_extract", "research_image_intel", "research_stego_detect"],
        "description": "Digital forensics and artifact analysis",
    },
}

# Tool categories for classification
TOOL_CATEGORIES = {
    "search": ["research_search", "research_deep", "research_multi_search", "research_github"],
    "fetch": ["research_fetch", "research_spider", "research_markdown", "research_camoufox"],
    "osint": ["research_whois", "research_dns_lookup", "research_passive_recon", "research_infra_correlator"],
    "analysis": ["research_llm_summarize", "research_extract", "research_fact_checker", "research_knowledge_graph"],
    "security": ["research_threat_intel", "research_breach_check", "research_cve_lookup", "research_nmap_scan"],
    "dark_web": ["research_dark_forum", "research_onion_discover", "research_leak_scan"],
    "attack": ["research_prompt_reframe", "research_attack_scorer", "research_stealth_score"],
    "reporting": ["research_report_gen", "research_llm_summarize", "research_export_json"],
}


@dataclass(frozen=True)
class RecommendedTool:
    """A recommended tool with scoring details."""
    tool: str
    score: float
    reason: str
    source: str  # "co_occurrence", "category", or "semantic"


@handle_tool_errors("research_recommend_next")
async def research_recommend_next(
    last_tool: str,
    context: str = "",
    top_k: int = 5,
) -> dict[str, Any]:
    """Recommend tools to use after a given tool.

    Given the last tool used, recommend what to use next based on:
    - Co-occurrence patterns (tools commonly used together)
    - Category similarity (related tool categories)
    - Semantic similarity (docstring matching)

    Scoring: co_occurrence_score * 3 + category_match * 2 + semantic_similarity * 1

    Args:
        last_tool: The tool that was just used (e.g., "research_fetch")
        context: Optional additional context about the research goal
        top_k: Number of recommendations to return (default: 5)

    Returns:
        Dict with keys:
        - last_tool: The input tool
        - recommendations: List of {tool, score, reason, source}
        - context_applied: Whether context was considered
        - total_candidates: Total candidates evaluated
    """
    candidates: dict[str, RecommendedTool] = {}

    # 1. Co-occurrence scoring (weight: 3)
    if last_tool in CO_OCCURRENCE_MAP:
        for co_tool in CO_OCCURRENCE_MAP[last_tool]:
            score = 3.0
            candidates[co_tool] = RecommendedTool(
                tool=co_tool,
                score=score,
                reason=f"Often used after {last_tool}",
                source="co_occurrence",
            )

    # 2. Category scoring (weight: 2)
    last_category = None
    for cat, tools in TOOL_CATEGORIES.items():
        if last_tool in tools:
            last_category = cat
            for other_tool in tools:
                if other_tool != last_tool:
                    existing = candidates.get(other_tool)
                    score = 2.0
                    if existing:
                        score += existing.score
                    candidates[other_tool] = RecommendedTool(
                        tool=other_tool,
                        score=score,
                        reason=f"Same category ({cat}) as {last_tool}",
                        source="category",
                    )
            break

    # 3. Semantic similarity (weight: 1) — based on context
    if context:
        for cat, tools in TOOL_CATEGORIES.items():
            if context.lower() in cat.lower():
                for tool in tools:
                    if tool != last_tool:
                        existing = candidates.get(tool)
                        score = 1.0
                        if existing:
                            score += existing.score
                        candidates[tool] = RecommendedTool(
                            tool=tool,
                            score=score,
                            reason=f"Matches context: {context}",
                            source="semantic",
                        )

    # Sort by score and return top-k
    sorted_candidates = sorted(candidates.values(), key=lambda x: x.score, reverse=True)[:top_k]

    log.info(
        "recommend_next last_tool=%s context_len=%d top_k=%d results=%d",
        last_tool,
        len(context),
        top_k,
        len(sorted_candidates),
    )

    return {
        "last_tool": last_tool,
        "recommendations": [
            {
                "tool": rec.tool,
                "score": round(rec.score, 2),
                "reason": rec.reason,
                "source": rec.source,
            }
            for rec in sorted_candidates
        ],
        "context_applied": bool(context),
        "total_candidates": len(candidates),
    }

@handle_tool_errors("research_suggest_workflow")
async def research_suggest_workflow(
    tools_used: list[str],
) -> dict[str, Any]:
    """Suggest missing workflow steps based on tools already used.

    Compares the used tools against known workflow templates to identify:
    - Which workflow the user is likely following
    - What steps are missing
    - Suggested tools to complete the workflow

    Args:
        tools_used: List of tool names that have been used (e.g., ["research_search", "research_fetch"])

    Returns:
        Dict with keys:
        - tools_used: The input tools
        - missing_steps: List of {tool, reason, priority}
        - workflow_match: Best matching workflow template name or None
        - completeness_pct: Percentage of matched workflow completed (0-100)
    """
    used_set = set(tools_used)
    best_match = None
    best_match_coverage = 0.0

    # Find best matching workflow
    for workflow_name, workflow_data in WORKFLOW_TEMPLATES.items():
        workflow_tools = set(workflow_data["tools"])
        overlap = len(used_set & workflow_tools)
        if overlap > 0:
            coverage = overlap / len(workflow_tools)
            if coverage > best_match_coverage:
                best_match = workflow_name
                best_match_coverage = coverage

    missing_steps = []

    if best_match:
        workflow_tools = set(WORKFLOW_TEMPLATES[best_match]["tools"])
        for tool in workflow_tools - used_set:
            missing_steps.append({
                "tool": tool,
                "reason": f"Part of {best_match} workflow",
                "priority": "high" if best_match_coverage > 0.5 else "medium",
            })
    else:
        # No clear workflow match; suggest category completeness
        used_categories = set()
        for tool in used_set:
            for cat, tools in TOOL_CATEGORIES.items():
                if tool in tools:
                    used_categories.add(cat)

        # For each used category, suggest related tools
        for cat in used_categories:
            for tool in TOOL_CATEGORIES[cat]:
                if tool not in used_set:
                    missing_steps.append({
                        "tool": tool,
                        "reason": f"Related to {cat} category",
                        "priority": "medium",
                    })

    # Cap missing steps to 10
    missing_steps = missing_steps[:10]

    completeness_pct = 0
    if best_match:
        total_tools = len(WORKFLOW_TEMPLATES[best_match]["tools"])
        completeness_pct = int(best_match_coverage * 100)

    log.info(
        "suggest_workflow tools_used=%d best_match=%s completeness=%d missing=%d",
        len(tools_used),
        best_match or "none",
        completeness_pct,
        len(missing_steps),
    )

    return {
        "tools_used": tools_used,
        "missing_steps": missing_steps,
        "workflow_match": best_match,
        "completeness_pct": completeness_pct,
    }


__all__ = ["research_recommend_next", "research_suggest_workflow"]
