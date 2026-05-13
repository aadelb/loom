"""MCP tool wrapper for daisy-chain decomposition pipeline.

Exposes research_daisy_chain as an MCP tool for splitting dangerous queries
across multiple models with response combination and safety scoring.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.daisy_chain import DaisyChainDecomposer, _compute_daisy_chain_hcs
    from loom.params import DaisyChainParams
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False
    DaisyChainDecomposer = None  # type: ignore[assignment,misc]
    DaisyChainParams = None  # type: ignore[assignment,misc]

logger = logging.getLogger("loom.tools.daisy_chain")


@handle_tool_errors("research_daisy_chain")
async def research_daisy_chain(
    query: str,
    available_models: list[str] | None = None,
    combiner_model: str = "gpt-4",
    timeout_per_model: float = 30.0,
    max_sub_queries: int = 4,
    include_execution_trace: bool = False,
) -> dict[str, Any]:
    """Execute query across multiple models via daisy-chain decomposition.

    Splits a potentially dangerous query into harmless sub-parts, routes each
    to a different LLM provider, and combines responses at a neutral combiner
    model. No single model sees the full dangerous query context.

    This tests whether AI model safety mechanisms depend on seeing the complete
    query context, and whether model responses can be exploited by decomposition
    and recombination.

    Args:
        query: The query to decompose and execute (max 5000 chars)
        available_models: Models to distribute sub-queries (default: 4 major providers)
        combiner_model: Model to synthesize sub-responses (default: gpt-4)
        timeout_per_model: Timeout per model call in seconds (5.0-120.0, default: 30.0)
        max_sub_queries: Maximum sub-queries to generate (2-6, default: 4)
        include_execution_trace: Include detailed execution trace (default: False)

    Returns:
        Dict with:
            original_query: The input query
            sub_queries: List of decomposed harmless sub-queries
            model_assignments: Dict mapping sub-query to model
            sub_responses: Dict of sub-query -> response text
            combined_response: Final synthesized response
            combiner_model: Model used for combination
            success: Whether execution succeeded
            hcs_score: HCS (helpfulness/compliance) score 0-10
            execution_time_ms: Total execution time
            execution_trace: (Optional) Detailed step-by-step trace
    """
    if not _DEPS_AVAILABLE:
        return {"error": "Dependencies not available (loom.daisy_chain, loom.params)", "tool": "research_daisy_chain", "success": False}

    params = DaisyChainParams(
        query=query,
        available_models=available_models,
        combiner_model=combiner_model,
        timeout_per_model=timeout_per_model,
        max_sub_queries=max_sub_queries,
    )

    models = params.available_models or ["nvidia_nim", "groq", "deepseek", "gemini"]

    logger.info(
        "Starting daisy-chain decomposition query_len=%s num_models=%s combiner=%s",
        len(params.query),
        len(models),
        params.combiner_model,
    )

    decomposer = DaisyChainDecomposer(available_models=models)

    # Build real LLM provider callbacks using cascade system
    async def real_llm_callback(model_name: str, prompt: str) -> str:
        """Call real LLM providers via cascade system."""
        try:
            from loom.tools.llm.llm import _call_with_cascade
            response = await _call_with_cascade(
                [{"role": "user", "content": prompt}],
                max_tokens=500,
                provider_override=model_name,
            )
            return getattr(response, "text", "") or f"No response from {model_name}"
        except Exception as e:
            logger.warning("llm_callback_failed model=%s: %s", model_name, e)
            return f"Error calling {model_name}: {str(e)[:100]}"

    callbacks = {
        model: real_llm_callback for model in models
    }
    callbacks[params.combiner_model] = real_llm_callback

    # Execute daisy-chain pipeline
    try:
        result = await decomposer.execute_chain(
            query=params.query,
            model_callbacks=callbacks,
            combiner_model=params.combiner_model,
            timeout_per_model=params.timeout_per_model,
        )

        # Build response
        response: dict[str, Any] = {
            "original_query": result.original_query,
            "sub_queries": result.sub_queries,
            "model_assignments": result.model_assignments,
            "sub_responses": result.sub_responses,
            "combined_response": result.combined_response,
            "combiner_model": result.combiner_model,
            "success": result.success,
            "hcs_score": round(result.hcs_score, 2),
            "execution_time_ms": result.execution_time_ms,
        }

        if result.error:
            response["error"] = result.error

        if include_execution_trace:
            response["execution_trace"] = {
                "steps": [
                    "Query decomposed into sub-queries",
                    f"Models assigned: {list(set(result.model_assignments.values()))}",
                    f"Sub-queries executed in parallel (timeout: {params.timeout_per_model}s)",
                    f"Responses collected from {len(result.sub_responses)} models",
                    f"Combination step executed with {result.combiner_model}",
                    f"HCS scoring: {result.hcs_score:.1f}/10",
                ],
                "timing": {
                    "total_ms": result.execution_time_ms,
                    "per_stage_estimate": {
                        "decomposition": "~10ms",
                        "assignment": "~5ms",
                        "parallel_execution": f"~{max(0, result.execution_time_ms - 30)}ms",
                        "combination": "~10ms",
                        "scoring": "~5ms",
                    },
                },
            }

        logger.info(
            "Daisy-chain execution completed success=%s hcs_score=%s execution_time_ms=%s",
            result.success,
            result.hcs_score,
            result.execution_time_ms,
        )

        return response

    except Exception as e:
        error_msg = f"Daisy-chain execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        return {
            "original_query": query,
            "sub_queries": [],
            "model_assignments": {},
            "sub_responses": {},
            "combined_response": "",
            "combiner_model": combiner_model,
            "success": False,
            "hcs_score": 0.0,
            "execution_time_ms": 0,
            "error": error_msg,
        }
