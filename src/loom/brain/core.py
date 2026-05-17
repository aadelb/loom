"""Brain Core — research_smart_call orchestrator tying all 5 layers together.

Flow: Perception → Memory → Reasoning → Action → Reflection
Provider: always NVIDIA NIM (free tier).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from loom.brain.action import execute_step
from loom.brain.chains import match_chain
from loom.brain.memory import get_memory
from loom.brain.perception import parse_intent
from loom.brain.reasoning import plan_workflow, select_tools
from loom.brain.reflection import evaluate_result, reflect_with_llm
from loom.brain.types import QualityMode, SmartCallResult

logger = logging.getLogger("loom.brain.core")

# Known escalation chains — when tool A fails, try tool B
# Expanded from 4 to 106+ chains across all tool categories (all source tools verified as existing)
_ESCALATION_CHAINS: dict[str, str] = {
    # Fetch/Scrape (4 chains)
    "research_fetch": "research_camoufox",
    "research_camoufox": "research_botasaurus",
    "research_spider": "research_fetch",
    "research_markdown": "research_fetch",

    # Search (1 chain, source=research_search, others don't exist)
    "research_search": "research_multi_search",

    # Deep Research (3 chains)
    "research_deep": "research_multi_search",
    "research_deep_url_analysis": "research_fetch",
    "research_citation_analysis": "research_deep",

    # LLM (5 chains)
    "research_llm_chat": "research_ask_all_models",
    "research_llm_query_expand": "research_llm_chat",
    "research_llm_summarize": "research_llm_chat",
    "research_llm_translate": "research_llm_chat",
    "research_llm_extract": "research_llm_chat",

    # OSINT (3 chains, others don't exist as sources)
    "research_email_breach": "research_breach_check",
    "research_sherlock_batch": "research_sherlock_lookup",
    "research_maigret": "research_sherlock_lookup",

    # Security (4 chains)
    "research_cve_lookup": "research_shodan_search",
    "research_nuclei_scan": "research_cve_lookup",
    "research_pentest_agent": "research_nuclei_scan",
    "research_pentest_docs": "research_pentest_plan",

    # DNS/Network (3 chains)
    "research_dns_lookup": "research_whois",
    "research_whois": "research_domain_reputation",
    "research_ip_geolocation": "research_shodan_search",

    # Shodan/Censys (2 chains)
    "research_shodan_search": "research_censys_search",
    "research_shodan_host": "research_censys_host",

    # Privacy (4 chains)
    "research_fingerprint_audit": "research_browser_privacy_score",
    "research_privacy_exposure": "research_fingerprint_audit",
    "research_stego_detect": "research_stego_decode",
    "research_artifact_cleanup": "research_secure_delete",

    # Browser Fingerprinting (2 chains)
    "research_browser_fingerprint": "research_fingerprint_evasion_test",
    "research_fingerprint_evasion_test": "research_browser_privacy_score",

    # Career (2 chains)
    "research_salary_synthesize": "research_job_search",
    "research_career_trajectory": "research_linkedin_intel",

    # Research (4 chains)
    "research_fact_check": "research_search",
    "research_knowledge_graph": "research_deep",
    "research_text_analyze": "research_llm_chat",
    "research_pdf_extract": "research_document_extract",

    # Infrastructure (2 chains)
    "research_transcribe": "research_llm_chat",
    "research_document_extract": "research_pdf_extract",

    # Darkweb (3 chains)
    "research_onionscan": "research_tor_status",
    "research_dark_forum": "research_darkweb_early_warning",
    "research_darkweb_early_warning": "research_shodan_search",

    # Adversarial (5 chains)
    "research_prompt_reframe": "research_auto_reframe",
    "research_auto_reframe": "research_adaptive_reframe",
    "research_stealth_score": "research_attack_score",
    "research_attack_score": "research_hcs_score",
    "research_jailbreak_evolution_adapt": "research_prompt_reframe",

    # Graph/Network Analysis (3 chains)
    "research_graph_scrape": "research_spider",
    "research_social_graph": "research_graph_analyze",
    "research_citation_graph": "research_citation_analysis",

    # Semantic/Knowledge (2 chains)
    "research_semantic_search": "research_search",
    "research_semantic_router_rebuild": "research_semantic_batch_route",

    # GitHub (2 chains)
    "research_github": "research_github_readme",
    "research_github_secrets": "research_github",

    # Code Analysis (2 chains)
    "research_dependency_graph": "research_dependency_audit",
    "research_dependency_audit": "research_cve_lookup",

    # Blockchain/Crypto (2 chains)
    "research_ethereum_tx_decode": "research_crypto_trace",
    "research_crypto_risk_score": "research_shodan_search",

    # Malware/Exploit (2 chains)
    "research_malware_intel": "research_shodan_search",
    "research_exploit_search": "research_cve_lookup",

    # Passive Recon (2 chains)
    "research_passive_recon": "research_github",
    "research_metadata_forensics": "research_image_analyze",

    # Social Media (2 chains)
    "research_linkedin_intel": "research_social_graph",
    "research_discord_intel": "research_social_graph",

    # Sentiment/Analysis (2 chains)
    "research_sentiment_deep": "research_llm_chat",
    "research_community_sentiment": "research_search",

    # Compliance/Legal (2 chains)
    "research_compliance_check": "research_compliance_report",
    "research_legal_takedown": "research_compliance_check",

    # API Analysis (2 chains)
    "research_openapi_schema": "research_api_changelog",
    "research_api_deprecations": "research_openapi_schema",

    # Bias/Fairness (2 chains)
    "research_bias_lens": "research_ai_bias_audit",
    "research_ai_bias_audit": "research_llm_chat",

    # Patent/IP (2 chains)
    "research_patent_landscape": "research_knowledge_graph",
    "research_patent_embargo": "research_patent_landscape",

    # Forecasting/Prediction (2 chains)
    "research_trend_forecast": "research_search",
    "research_predict_resilience": "research_llm_chat",

    # Benchmark/Evaluation (2 chains)
    "research_benchmark_run": "research_benchmark_models",
    "research_benchmark_compare": "research_benchmark_run",

    # Health/Status (2 chains)
    "research_health_check_all": "research_health_deep",
    "research_health_deep": "research_metrics",

    # Logs/Audit (2 chains)
    "research_audit_query": "research_log_query",
    "research_log_query": "research_log_stats",

    # Workflow/Pipeline (2 chains)
    "research_pipeline_create": "research_pipeline_validate",
    "research_pipeline_validate": "research_pipeline_list",

    # Report Generation (2 chains)
    "research_generate_report": "research_report_template",
    "research_report_custom": "research_format_report",

    # Attack Strategy (2 chains)
    "research_ensemble_attack": "research_jailbreak_evolution_adapt",
    "research_swarm_attack": "research_ensemble_attack",

    # Model Analysis (3 chains)
    "research_model_fingerprint": "research_model_sentiment",
    "research_model_sentiment": "research_llm_chat",
    "research_model_consensus": "research_multi_search",

    # Training/Safety (3 chains)
    "research_training_contamination": "research_fact_check",
    "research_memorization_scanner": "research_search",
    "research_hallucination_benchmark": "research_benchmark_models",

    # Evidence/Analysis (2 chains)
    "research_fuse_evidence": "research_knowledge_graph",
    "research_analyze_evidence": "research_fuse_evidence",

    # Cross-Domain (2 chains)
    "research_cross_domain": "research_search",
    "research_xover_transfer": "research_cross_domain",

    # Supply Chain (1 chain)
    "research_supply_chain_risk": "research_dependency_audit",

    # Anomaly Detection (2 chains)
    "research_detect_anomalies": "research_llm_chat",
    "research_content_anomaly": "research_detect_anomalies",

    # Organization Intelligence (2 chains)
    "research_company_diligence": "research_linkedin_intel",
    "research_competitive_intel": "research_company_diligence",

    # Entity Resolution (1 chain)
    "research_identity_resolve": "research_github",

    # Adversarial Robustness (1 chain)
    "research_adversarial_robustness": "research_benchmark_models",

    # Information Security (1 chain)
    "research_threat_profile": "research_shodan_search",

    # Additional Tool-Specific Chains (expanding coverage)
    "research_tor_status": "research_tor_rotate",
    "research_tor_rotate": "research_tor_new_identity",
}


def _find_fallback_tool(
    failed_tool: str,
    all_matches: list[Any],
    already_tried: list[str],
) -> Any | None:
    """Find a fallback tool when the primary one fails.

    Priority: explicit escalation chain > next best match from candidates.
    """
    # Check explicit escalation
    escalation = _ESCALATION_CHAINS.get(failed_tool)
    if escalation and escalation not in already_tried:
        from loom.brain.types import ToolMatch
        return ToolMatch(tool_name=escalation, confidence=0.9, match_source="escalation")

    # Fall back to next untried candidate
    for match in all_matches:
        if match.tool_name not in already_tried and match.tool_name != failed_tool:
            return match

    return None


async def research_smart_call(
    query: str,
    quality_mode: str = "auto",
    max_iterations: int = 3,
    forced_tools: list[str] | None = None,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Intelligent tool orchestration — the main Brain entry point.

    Takes a natural language query, selects the best tool(s), extracts
    parameters, executes them, and reflects on results. Iterates up to
    max_iterations times if results are incomplete.

    Args:
        query: Natural language research query
        quality_mode: "max", "auto", or "economy"
        max_iterations: Maximum reflection-retry loops (1-5)
        forced_tools: Override tool selection with specific tool names
        timeout: Total timeout in seconds

    Returns:
        Dict with: success, matched_tools, plan_steps, final_output,
        iterations, quality_mode, error, elapsed_ms
    """
    start = time.time()
    mode = QualityMode(quality_mode) if quality_mode in ("max", "auto", "economy") else QualityMode.AUTO
    max_iterations = max(1, min(max_iterations, 5))
    memory = get_memory()

    # --- Layer 0: Adversarial Route Detection ---
    # If mode=max, always route to adversarial orchestrator (it handles scoring internally)
    if mode == QualityMode.MAX:
        try:
            danger_score = 10  # mode=max always uses adversarial route
            if True:
                logger.info("brain_adversarial_route danger_score=%s query=%s", danger_score, query[:60])
                from loom.tools.llm.adversarial_orchestrator import research_adversarial_orchestrate
                orch_result = await research_adversarial_orchestrate(
                    query=query, target_hcs=9, max_attempts=3, mode="standard"
                )
                elapsed_ms = int((time.time() - start) * 1000)
                return {
                    "success": bool(orch_result.get("best_response")),
                    "matched_tools": ["research_adversarial_orchestrate"],
                    "plan_steps": ["adversarial_orchestrate"],
                    "final_output": orch_result.get("best_response", ""),
                    "iterations": orch_result.get("total_attempts", 0),
                    "quality_mode": mode,
                    "elapsed_ms": elapsed_ms,
                    "adversarial": True,
                    "hcs_score": orch_result.get("best_hcs", 0),
                    "provider": orch_result.get("best_provider", ""),
                }
        except Exception as e:
            logger.warning("adversarial_route_failed: %s, falling back to normal", e)

    # --- Layer 1: Perception ---
    intent = parse_intent(query)
    logger.info(
        "brain_perceive query=%s domains=%s intent_type=%s",
        query[:60],
        intent["domains"],
        intent["intent_type"],
    )

    # --- Layer 2: Memory ---
    recent_context = memory.get_recent_context(n=3)

    # --- Layer 3: Reasoning (chain detection + tool selection + planning) ---
    # Check for predefined chains first (strongest signal)
    chain_match = match_chain(query) if not forced_tools else None
    if chain_match:
        logger.info("brain_chain_matched chain=%s tools=%s", chain_match["chain_name"], chain_match["tools"])
        from loom.brain.types import ToolMatch
        matched = [ToolMatch(tool_name=t, confidence=0.9, match_source="chain") for t in chain_match["tools"]]
    else:
        matched = select_tools(
            query=query,
            quality_mode=mode,
            max_tools=10 if mode == QualityMode.MAX else 5,
            forced_tools=forced_tools,
        )

    if not matched:
        elapsed_ms = int((time.time() - start) * 1000)
        return SmartCallResult(
            success=False,
            error="No matching tools found for query",
            quality_mode=mode,
            elapsed_ms=elapsed_ms,
        ).model_dump()

    plan = plan_workflow(query, matched, mode)
    matched_tool_names = [m.tool_name for m in matched]
    plan_step_names = [s.tool_name for s in plan.steps]

    logger.info(
        "brain_plan matched_tools=%s plan_steps=%s",
        matched_tool_names[:5],
        plan_step_names,
    )

    # --- Layer 4: Action (execute plan steps with context piping) ---
    final_output: Any = None
    iterations = 0
    step_outputs: list[dict[str, Any]] = []
    executed_step_indices: set[int] = set()

    try:
        async with asyncio.timeout(timeout):
            for iteration in range(max_iterations):
                iterations = iteration + 1

                for step_idx, step in enumerate(plan.steps):
                    if step_idx in executed_step_indices:
                        continue
                    executed_step_indices.add(step_idx)
                    step_context = {
                        "recent": recent_context,
                        "previous_outputs": step_outputs,
                    }
                    # Context piping: inject actual dependency's output as context
                    if step_outputs and step.depends_on:
                        for prev in reversed(step_outputs):
                            if prev.get("tool") in step.depends_on and prev.get("success") and prev.get("result"):
                                step_context["piped_result"] = prev["result"]
                                break

                    step_result = await execute_step(
                        step=step,
                        query=query,
                        quality_mode=mode,
                        context=step_context,
                    )

                    step_outputs.append(step_result)

                    # Record in memory
                    memory.record_call(
                        tool_name=step.tool_name,
                        query=query,
                        params=step_result.get("params_used", {}),
                        success=step_result.get("success", False),
                        elapsed_ms=step_result.get("elapsed_ms", 0),
                        error=step_result.get("error"),
                    )

                    if step_result.get("success"):
                        new_result = step_result.get("result")
                        from loom.brain.reflection import _is_empty_result
                        if not _is_empty_result(new_result) or final_output is None:
                            final_output = new_result
                    elif mode != QualityMode.ECONOMY:
                        # Error recovery: try next best tool from matched list
                        fallback = _find_fallback_tool(
                            step.tool_name, matched, [s.tool_name for s in plan.steps]
                        )
                        if fallback:
                            logger.info("brain_fallback from=%s to=%s", step.tool_name, fallback.tool_name)
                            from loom.brain.types import PlanStep as _PS
                            fallback_step = _PS(tool_name=fallback.tool_name, timeout=step.timeout)
                            fallback_result = await execute_step(
                                step=fallback_step, query=query, quality_mode=mode, context=step_context,
                            )
                            step_outputs.append(fallback_result)
                            memory.record_call(
                                tool_name=fallback.tool_name, query=query,
                                params=fallback_result.get("params_used", {}),
                                success=fallback_result.get("success", False),
                                elapsed_ms=fallback_result.get("elapsed_ms", 0),
                                error=fallback_result.get("error"),
                            )
                            if fallback_result.get("success"):
                                final_output = fallback_result.get("result")

                # --- Layer 5: Reflection ---
                if final_output is not None:
                    if mode == QualityMode.MAX and iterations < max_iterations:
                        reflection = await reflect_with_llm(
                            query=query,
                            tool_name=plan.steps[-1].tool_name if plan.steps else "",
                            result={"success": True, "result": final_output},
                        )
                    else:
                        reflection = evaluate_result(
                            query=query,
                            tool_name=plan.steps[-1].tool_name if plan.steps else "",
                            result={"success": True, "result": final_output},
                            quality_mode=mode,
                        )

                    if reflection.get("complete") or reflection.get("next_action") == "done":
                        break

                    next_action = reflection.get("next_action", "done")
                    if next_action == "chain":
                        # Try to append a chained/fallback tool for next iteration
                        tried_tools = [s.tool_name for s in plan.steps] + [r.get("tool", "") for r in step_outputs]
                        fallback = _find_fallback_tool(
                            plan.steps[-1].tool_name if plan.steps else "",
                            matched,
                            tried_tools,
                        )
                        if fallback and fallback.tool_name not in [s.tool_name for s in plan.steps]:
                            logger.info(
                                "brain_chain from=%s to=%s",
                                plan.steps[-1].tool_name if plan.steps else "",
                                fallback.tool_name,
                            )
                            from loom.brain.types import PlanStep as _PS
                            plan.steps.append(
                                _PS(
                                    tool_name=fallback.tool_name,
                                    timeout=60.0 if mode == QualityMode.MAX else 30.0,
                                )
                            )
                        else:
                            break
                    elif next_action == "retry":
                        # Clear outputs to force a fresh retry of the same plan
                        step_outputs = []
                        final_output = None
                        continue
                    else:
                        break
                else:
                    break

    except TimeoutError:
        logger.warning("brain_timeout query=%s after %.1fs", query[:40], timeout)
        if final_output is None:
            elapsed_ms = int((time.time() - start) * 1000)
            return SmartCallResult(
                success=False,
                matched_tools=matched_tool_names,
                plan_steps=plan_step_names,
                error=f"timeout after {timeout}s",
                iterations=iterations,
                quality_mode=mode,
                elapsed_ms=elapsed_ms,
            ).model_dump()

    elapsed_ms = int((time.time() - start) * 1000)

    result = SmartCallResult(
        success=final_output is not None,
        matched_tools=matched_tool_names,
        plan_steps=plan_step_names,
        final_output=final_output,
        iterations=iterations,
        quality_mode=mode,
        elapsed_ms=elapsed_ms,
    )

    logger.info(
        "brain_complete success=%s tools=%s iterations=%d elapsed_ms=%d",
        result.success,
        plan_step_names,
        iterations,
        elapsed_ms,
    )

    return result.model_dump()
