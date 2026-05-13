"""Pipeline enhancer middleware for automatic tool output enrichment.

Wraps ANY pipeline tool execution with automatic enrichment:
1. Pre-execution: cost estimation
2. Post-execution: HCS scoring (8-dimension quality assessment)
3. Post-execution: strategy learning (if reframe was used)
4. Post-execution: fact checking (optional, adds latency)
5. Post-execution: related tool suggestions
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import time
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.pipeline_enhancer")


@handle_tool_errors("research_enhance")
async def research_enhance(
    tool_name: str,
    params: dict[str, Any],
    auto_hcs: bool = True,
    auto_cost: bool = True,
    auto_learn: bool = True,
    auto_fact_check: bool = False,
    auto_suggest: bool = True,
) -> dict[str, Any]:
    """Execute any tool with automatic enrichment.

    Wraps tool execution with:
    1. Pre-execution: cost estimation
    2. Post-execution: HCS scoring
    3. Post-execution: strategy learning (if reframe was used)
    4. Post-execution: fact checking (optional, adds latency)
    5. Post-execution: related tool suggestions

    Args:
        tool_name: Name of tool to execute (e.g., "research_deep")
        params: Parameters to pass to the tool as dict
        auto_hcs: Auto-score response with HCS (default True)
        auto_cost: Estimate cost before execution (default True)
        auto_learn: Feed results to meta_learner (default True)
        auto_fact_check: Verify factual claims (default False, slow)
        auto_suggest: Suggest related tools for follow-up (default True)

    Returns:
        Dict with original tool result + enrichment metadata:
        - _original_result: the tool's actual output
        - _hcs_scores: 8-dimension quality scores (if auto_hcs enabled)
        - _estimated_cost: pre-execution cost estimate (if auto_cost enabled)
        - _actual_cost: post-execution actual cost
        - _suggested_tools: related tools for follow-up (if auto_suggest enabled)
        - _fact_check: verified claims (if auto_fact_check enabled)
        - _execution_time_ms: wall-clock execution time
    """
    start_time = time.time()
    result = {"_original_result": None}

    try:
        # Step 1: Pre-execution cost estimation (non-blocking)
        estimated_cost = None
        if auto_cost:
            try:
                estimated_cost = await _estimate_tool_cost(tool_name, params)
                result["_estimated_cost"] = estimated_cost
            except Exception as e:
                logger.debug(f"Cost estimation failed for {tool_name}: {e}")

        # Step 2: Execute the target tool
        tool_result = await _execute_tool(tool_name, params)
        result["_original_result"] = tool_result

        # Step 3: Post-execution enrichment (parallel tasks)
        enrichment_tasks = []
        task_order = []  # Track which tasks were added and in what order

        if auto_hcs:
            enrichment_tasks.append(_score_with_hcs(tool_result, tool_name))
            task_order.append("hcs")

        if auto_learn and _has_reframe_data(params):
            enrichment_tasks.append(_feed_to_meta_learner(tool_result, params))
            task_order.append("learn")

        if auto_fact_check:
            enrichment_tasks.append(_verify_factual_claims(tool_result))
            task_order.append("fact_check")

        if auto_suggest:
            enrichment_tasks.append(_suggest_follow_up_tools(tool_name, params, tool_result))
            task_order.append("suggest")

        # Execute all enrichment tasks in parallel
        if enrichment_tasks:
            enrichment_results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)

            # Collect results using tracked order, handling exceptions gracefully
            for idx, task_type in enumerate(task_order):
                if idx >= len(enrichment_results):
                    break
                if isinstance(enrichment_results[idx], Exception):
                    continue

                if task_type == "hcs":
                    result["_hcs_scores"] = enrichment_results[idx]
                elif task_type == "learn":
                    result["_learning_recorded"] = enrichment_results[idx]
                elif task_type == "fact_check":
                    result["_fact_check"] = enrichment_results[idx]
                elif task_type == "suggest":
                    result["_suggested_tools"] = enrichment_results[idx]

    except Exception as e:
        logger.error(f"Pipeline enhancement failed for {tool_name}: {e}", exc_info=True)
        result["_error"] = str(e)

    finally:
        # Always record execution time
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["_execution_time_ms"] = elapsed_ms

    return result


@handle_tool_errors("research_enhance_batch")
async def research_enhance_batch(
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Execute multiple tools with enhancement in parallel.

    Each task dict must have:
    - tool_name: str
    - params: dict
    - (optional) auto_hcs, auto_cost, auto_learn, auto_fact_check, auto_suggest

    Args:
        tasks: List of task dicts with tool_name and params

    Returns:
        Dict with:
        - results: List of results from research_enhance for each task
        - total_time_ms: Total batch execution time
        - success_count: Number of successful executions
        - error_count: Number of failed executions
    """
    start_time = time.time()
    results = []

    try:
        # Execute all enhance operations in parallel
        enhance_coros = [
            research_enhance(
                task["tool_name"],
                task["params"],
                auto_hcs=task.get("auto_hcs", True),
                auto_cost=task.get("auto_cost", True),
                auto_learn=task.get("auto_learn", True),
                auto_fact_check=task.get("auto_fact_check", False),
                auto_suggest=task.get("auto_suggest", True),
            )
            for task in tasks
        ]

        results = await asyncio.gather(*enhance_coros, return_exceptions=False)

    except Exception as e:
        logger.error(f"Batch enhancement failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "results": results,
            "total_time_ms": int((time.time() - start_time) * 1000),
        }

    # Count successes and errors
    success_count = sum(1 for r in results if "_error" not in r)
    error_count = len(results) - success_count

    return {
        "results": results,
        "total_time_ms": int((time.time() - start_time) * 1000),
        "success_count": success_count,
        "error_count": error_count,
    }


# ── Private Helper Functions ──


async def _execute_tool(tool_name: str, params: dict[str, Any]) -> Any:
    """Dynamically import and execute the specified tool.

    Args:
        tool_name: Name of tool function (e.g., "research_deep")
        params: Parameters dict to pass

    Returns:
        The tool's return value

    Raises:
        AttributeError: Tool not found
        Exception: Tool execution error
    """
    # Map tool names to module paths
    tool_module_map = {
        "research_fetch": "loom.tools.fetch",
        "research_spider": "loom.tools.spider",
        "research_markdown": "loom.tools.markdown",
        "research_search": "loom.tools.search",
        "research_deep": "loom.tools.deep",
        "research_github": "loom.tools.github",
        "research_llm_summarize": "loom.tools.llm",
        "research_llm_extract": "loom.tools.llm",
        "research_score_all": "loom.scoring",
        "research_unified_score": "loom.unified_scorer",
        "research_orchestrate": "loom.orchestrator",
    }

    # Determine module from tool name or try direct import
    if tool_name in tool_module_map:
        module_path = tool_module_map[tool_name]
    else:
        # Infer module from tool name (e.g., research_deep -> loom.tools.deep)
        if tool_name.startswith("research_"):
            tool_base = tool_name.replace("research_", "")
            module_path = f"loom.tools.{tool_base}"
        else:
            module_path = f"loom.tools.{tool_name}"

    try:
        module = importlib.import_module(module_path)
        tool_func = getattr(module, tool_name)
        return await tool_func(**params)
    except ImportError as e:
        raise ImportError(f"Module {module_path} not found: {e}") from e
    except AttributeError as e:
        raise AttributeError(f"Tool {tool_name} not found in {module_path}: {e}") from e


async def _estimate_tool_cost(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Estimate execution cost (tokens, API calls, etc.) for a tool.

    Args:
        tool_name: Name of tool
        params: Parameters dict

    Returns:
        Cost estimation dict with estimated tokens, API calls, etc.
    """
    # Simple heuristic cost model (can be enhanced with actual cost tracking)
    cost_estimate = {
        "tool": tool_name,
        "estimated_tokens": 0,
        "estimated_api_calls": 0,
        "estimated_cost_usd": 0.0,
    }

    # Add more detailed cost estimates based on tool type
    if "research_fetch" in tool_name:
        cost_estimate["estimated_tokens"] = params.get("max_chars", 20000) // 4
        cost_estimate["estimated_api_calls"] = 1

    elif "research_spider" in tool_name:
        urls = params.get("urls", [])
        cost_estimate["estimated_tokens"] = (params.get("max_chars", 20000) // 4) * len(urls)
        cost_estimate["estimated_api_calls"] = len(urls)

    elif "research_deep" in tool_name:
        # Deep research typically makes multiple API calls
        cost_estimate["estimated_tokens"] = 5000  # 12-stage pipeline estimate
        cost_estimate["estimated_api_calls"] = 3

    elif "research_search" in tool_name:
        cost_estimate["estimated_tokens"] = 2000
        cost_estimate["estimated_api_calls"] = 1

    return cost_estimate


async def _score_with_hcs(result: Any, tool_name: str) -> dict[str, float]:
    """Score tool output with HCS (8-dimension quality assessment).

    Args:
        result: Tool output result
        tool_name: Name of the tool

    Returns:
        Dict with 8 HCS dimensions: bypass, density, stealth, transfer,
        persistence, escalation, defense_evasion, novelty
    """
    try:
        from loom.attack_scorer import research_score_response

        # Convert result to string for scoring
        result_text = str(result) if result else ""

        # Perform HCS scoring
        hcs_scores = await research_score_response(
            response=result_text,
            strategy_name=tool_name,
        )
        return hcs_scores if hcs_scores else _default_hcs_scores()

    except Exception as e:
        logger.debug(f"HCS scoring failed: {e}")
        return _default_hcs_scores()


async def _feed_to_meta_learner(
    result: Any,
    params: dict[str, Any],
) -> bool:
    """Record tool result to meta-learner for strategy evolution.

    Args:
        result: Tool output
        params: Original parameters (may contain reframe data)

    Returns:
        True if learning was recorded
    """
    try:
        from loom.jailbreak_evolution import record_strategy_result

        # Extract reframe strategy if present
        strategy = params.get("strategy_name", "unknown")
        success = params.get("success", False)

        await record_strategy_result(
            strategy_name=strategy,
            result=str(result),
            success=success,
        )
        return True

    except Exception as e:
        logger.debug(f"Meta-learner recording failed: {e}")
        return False


async def _verify_factual_claims(result: Any) -> dict[str, Any]:
    """Verify factual claims in tool output.

    Args:
        result: Tool output to fact-check

    Returns:
        Dict with fact-check results and verified claims
    """
    try:
        from loom.tools.llm import research_llm_classify

        result_text = str(result) if result else ""
        if len(result_text) < 50:
            return {"verified": True, "reason": "Result too short to fact-check"}

        # Use LLM to identify and verify factual claims
        verification = await research_llm_classify(
            text=result_text,
            categories=["factual_claim", "opinion", "uncertain"],
        )
        return {
            "verified_claims": verification.get("factual", []),
            "opinion_content": verification.get("opinion", []),
        }

    except Exception as e:
        logger.debug(f"Fact checking failed: {e}")
        return {"error": str(e)}


async def _suggest_follow_up_tools(
    tool_name: str,
    params: dict[str, Any],
    result: Any,
) -> dict[str, Any]:
    """Suggest related tools for follow-up analysis.

    Args:
        tool_name: Name of the tool just executed
        params: Original parameters
        result: Tool output

    Returns:
        Dict with suggested tools and reasons
    """
    try:
        from loom.tool_recommender import ToolRecommender

        recommender = ToolRecommender()

        # Build a query from tool name and result
        query_parts = [tool_name.replace("research_", "")]
        if isinstance(result, dict) and "summary" in result:
            query_parts.append(result["summary"][:100])

        query = " ".join(query_parts)

        # Get recommendations
        recommendations = recommender.recommend(
            query=query,
            exclude_used=[tool_name],
            max_recommendations=3,
        )

        return {
            "suggested_tools": recommendations,
            "reason": f"Follow-up tools to complement {tool_name}",
        }

    except Exception as e:
        logger.debug(f"Tool suggestion failed: {e}")
        return {"error": str(e)}


def _has_reframe_data(params: dict[str, Any]) -> bool:
    """Check if params contain reframing strategy data.

    Args:
        params: Parameters dict

    Returns:
        True if reframe data is present
    """
    return (
        "strategy_name" in params
        or "prompt_reframed" in params
        or "reframe_strategy" in params
    )


def _default_hcs_scores() -> dict[str, float]:
    """Return default HCS scoring dict.

    Returns:
        Dict with 8 HCS dimensions all set to 0.0
    """
    return {
        "bypass_success": 0.0,
        "information_density": 0.0,
        "stealth_score": 0.0,
        "transferability": 0.0,
        "persistence": 0.0,
        "escalation_potential": 0.0,
        "defense_evasion": 0.0,
        "novelty": 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Dependency-Aware Pipeline Composition
# ─────────────────────────────────────────────────────────────────────────────


@handle_tool_errors("research_enhance_with_dependencies")
async def research_enhance_with_dependencies(
    tool_names: list[str],
    params_map: dict[str, dict[str, Any]] | None = None,
    auto_resolve_deps: bool = True,
    execute_dependencies: bool = True,
    auto_hcs: bool = True,
    auto_cost: bool = True,
    auto_learn: bool = True,
    auto_fact_check: bool = False,
    auto_suggest: bool = True,
) -> dict[str, Any]:
    """Execute multiple tools respecting dependency order with enrichment.

    This function resolves tool dependencies, organizes them into
    parallel execution groups, and executes each group sequentially
    while executing tools within a group in parallel.

    Args:
        tool_names: List of tool names to execute
        params_map: Dict mapping tool_name -> params dict (optional)
        auto_resolve_deps: Resolve and execute dependencies (default True)
        execute_dependencies: Include dependencies in execution (default True)
        auto_hcs: Enable HCS scoring (default True)
        auto_cost: Enable cost estimation (default True)
        auto_learn: Enable meta-learning (default True)
        auto_fact_check: Enable fact checking (default False)
        auto_suggest: Enable tool suggestions (default True)

    Returns:
        Dict with:
        - requested_tools: Original list
        - execution_plan: Organized parallel groups
        - execution_order: Actual execution order taken
        - results: List of tool results
        - total_time_ms: Total execution time
        - success_count: Number of successful tools
        - error_count: Number of failed tools
        - dependency_info: Information about resolved dependencies
    """
    start_time = time.time()
    params_map = params_map or {}

    try:
        # Step 1: Resolve dependencies
        from loom.tools.tool_dependencies import prepare_tool_execution

        prep_result = await prepare_tool_execution(tool_names)

        if not prep_result["valid"]:
            logger.warning(f"Dependency issues found: {prep_result['dependency_warnings']}")

        execution_plan = prep_result["execution_plan"]
        all_tools = prep_result["all_tools"]
        execution_order = []
        results_map: dict[str, dict[str, Any]] = {}

        # Step 2: Execute each parallel group sequentially
        for group_idx, group in enumerate(execution_plan):
            logger.info(f"Executing group {group_idx}: {group}")
            execution_order.extend(group)

            # Skip tool dependencies if execute_dependencies is False
            if not execute_dependencies:
                group = [t for t in group if t in tool_names]

            if not group:
                continue

            # Create enhancement tasks for all tools in group
            enhance_tasks = [
                research_enhance(
                    tool_name,
                    params_map.get(tool_name, {}),
                    auto_hcs=auto_hcs,
                    auto_cost=auto_cost,
                    auto_learn=auto_learn,
                    auto_fact_check=auto_fact_check,
                    auto_suggest=auto_suggest,
                )
                for tool_name in group
            ]

            # Execute all tools in group in parallel
            group_results = await asyncio.gather(*enhance_tasks, return_exceptions=True)

            # Collect results
            for tool_name, result in zip(group, group_results):
                if isinstance(result, Exception):
                    logger.error(f"Tool {tool_name} failed: {result}")
                    results_map[tool_name] = {
                        "_error": str(result),
                        "_execution_time_ms": 0,
                    }
                else:
                    results_map[tool_name] = result

        # Step 3: Aggregate results
        results = [results_map.get(t, {"_error": "No result"}) for t in tool_names]
        success_count = sum(1 for r in results if "_error" not in r)
        error_count = len(results) - success_count

        return {
            "requested_tools": tool_names,
            "execution_plan": execution_plan,
            "execution_order": execution_order,
            "results": results,
            "results_by_tool": results_map,
            "total_time_ms": int((time.time() - start_time) * 1000),
            "success_count": success_count,
            "error_count": error_count,
            "dependency_info": {
                "all_tools_executed": all_tools,
                "warnings": prep_result.get("dependency_warnings", []),
                "valid": prep_result["valid"],
            },
        }

    except Exception as e:
        logger.error(f"Dependency-aware batch enhancement failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "requested_tools": tool_names,
            "results": [],
            "total_time_ms": int((time.time() - start_time) * 1000),
            "success_count": 0,
            "error_count": len(tool_names),
        }


@handle_tool_errors("research_compose_pipeline")
async def research_compose_pipeline(
    primary_tools: list[str],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose and execute an intelligent research pipeline.

    Selects optimal execution strategy based on tool types and dependencies.
    Automatically organizes tools into efficient parallel groups.

    Args:
        primary_tools: Main tools user wants to execute
        config: Optional pipeline config with execution preferences

    Returns:
        Dict with pipeline execution result and metadata
    """
    config = config or {}
    start_time = time.time()

    try:
        from loom.tools.tool_dependencies import (
            get_execution_plan,
            resolve_dependencies,
        )

        # Resolve full dependency tree
        all_tools = resolve_dependencies(primary_tools)
        execution_plan = get_execution_plan(primary_tools)

        # Extract enhancement settings from config
        auto_hcs = config.get("auto_hcs", True)
        auto_cost = config.get("auto_cost", True)
        auto_learn = config.get("auto_learn", True)
        auto_fact_check = config.get("auto_fact_check", False)
        auto_suggest = config.get("auto_suggest", True)

        # Get parameters for each tool from config
        params_map = config.get("params_map", {})

        # Execute with dependency awareness
        result = await research_enhance_with_dependencies(
            list(primary_tools),
            params_map=params_map,
            auto_resolve_deps=True,
            execute_dependencies=config.get("execute_dependencies", True),
            auto_hcs=auto_hcs,
            auto_cost=auto_cost,
            auto_learn=auto_learn,
            auto_fact_check=auto_fact_check,
            auto_suggest=auto_suggest,
        )

        result["pipeline_config"] = config
        result["elapsed_ms"] = int((time.time() - start_time) * 1000)

        return result

    except Exception as e:
        logger.error(f"Pipeline composition failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "primary_tools": primary_tools,
            "total_time_ms": int((time.time() - start_time) * 1000),
        }
