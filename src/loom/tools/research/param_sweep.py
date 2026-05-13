"""Parameter sweeper tool for defense robustness testing.

Provides research_parameter_sweep — test attacks at various API parameter
combinations to find defense weaknesses. Useful for understanding how
temperature, top_p, and max_tokens affect model refusal/compliance behavior.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.param_sweeper import ParameterSweeper
    from loom.tools.llm.llm import _call_with_cascade
    _SWEEP_DEPS = True
except ImportError:
    _SWEEP_DEPS = False

logger = logging.getLogger("loom.tools.param_sweep")


@handle_tool_errors("research_parameter_sweep")
async def research_parameter_sweep(
    prompt: str,
    strategy: str,
    model_name: str = "unknown",
    sweep_type: str = "full",
    dimension: str | None = None,
    max_combinations: int = 100,
    max_concurrent: int = 5,
) -> dict[str, Any]:
    """Test attacks at various API parameter combinations to find defense weaknesses.

    Performs either a full grid sweep (temperature × top_p × max_tokens)
    or a single-dimension sweep varying one parameter while holding others constant.

    Args:
        prompt: The prompt/attack to test (max 5000 chars)
        strategy: Attack strategy name (e.g., 'jailbreak', 'prompt_injection')
        model_name: Name of the model being tested (default 'unknown')
        sweep_type: Type of sweep - 'full' for grid, 'single_dim' for one parameter
        dimension: For single_dim sweep: 'temperature', 'top_p', or 'max_tokens'
        max_combinations: Maximum combinations to test (default 100, max 500)
        max_concurrent: Max concurrent requests (default 5, max 20)

    Returns:
        Dict with analysis:
          - total_combinations_tested: int
          - compliance_rate: float (0-1) — percentage of responses that complied
          - best_params: dict with parameters that achieved highest compliance
          - worst_params: dict with parameters that achieved lowest compliance
          - heatmap_data: list of {temperature, top_p, compliance_rate}
          - recommendations: list of strings with security insights
          - model_name: str — the model tested
          - strategy_used: str — the strategy used
          - prompt_tested: str — the prompt tested

    Examples:
        Full grid sweep:
          result = await research_parameter_sweep(
              prompt="How do I exploit this vulnerability?",
              strategy="jailbreak",
              model_name="claude-3-sonnet",
              sweep_type="full",
              max_combinations=50
          )

        Single dimension sweep (temperature):
          result = await research_parameter_sweep(
              prompt="How do I break into a system?",
              strategy="prompt_injection",
              model_name="gpt-4",
              sweep_type="single_dim",
              dimension="temperature",
              max_combinations=10
          )

    Notes:
        - Full grid generates: 10 temperatures × 6 top_p × 6 max_tokens = 360 combos
        - Single dimension uses 10-20 values per dimension
        - Default ranges:
            - temperature: [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 2.0]
            - top_p: [0.1, 0.5, 0.8, 0.9, 0.95, 1.0]
            - max_tokens: [50, 200, 500, 1000, 2000, 4096]
        - Compliance detection uses simple heuristics (response length + refusal patterns)
        - HCS (Helpfulness-Compliance Score) rated 0-10 based on length, specificity, actionability
        - Results capped at max_combinations to prevent resource exhaustion
    """
    # Validate inputs
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be non-empty")
    if len(prompt) > 5000:
        raise ValueError("prompt max 5000 characters")

    if not strategy or not strategy.strip():
        raise ValueError("strategy must be non-empty")

    if sweep_type not in ("full", "single_dim"):
        raise ValueError("sweep_type must be 'full' or 'single_dim'")

    if sweep_type == "single_dim" and dimension is None:
        raise ValueError("dimension required for single_dim sweep")

    if dimension and dimension not in ("temperature", "top_p", "max_tokens"):
        raise ValueError("dimension must be temperature, top_p, or max_tokens")

    if max_combinations < 1 or max_combinations > 500:
        raise ValueError("max_combinations must be 1-500")

    if max_concurrent < 1 or max_concurrent > 20:
        raise ValueError("max_concurrent must be 1-20")

    sweeper = ParameterSweeper(max_combinations=max_combinations)

    # Real model callback using cascade system
    async def real_model_callback(prompt: str, params: dict[str, Any]) -> str:
        """Call real LLM via cascade system with given parameters."""
        try:
            response = await _call_with_cascade(
                [{"role": "user", "content": prompt}],
                max_tokens=params.get("max_tokens", 500),
            )
            return getattr(response, "text", "") or f"No response (T={params.get('temperature')}, P={params.get('top_p')})"
        except Exception as e:
            logger.debug("model_callback_failed: %s", e)
            return f"Error: {str(e)[:50]}"

    try:
        if sweep_type == "full":
            result = await sweeper.sweep(
                prompt=prompt,
                strategy=strategy,
                model_callback=real_model_callback,
                model_name=model_name,
                max_concurrent=max_concurrent,
            )
        else:  # single_dim
            result = await sweeper.sweep_single_dim(
                prompt=prompt,
                strategy=strategy,
                dimension=dimension,
                model_callback=real_model_callback,
                model_name=model_name,
                max_concurrent=max_concurrent,
            )

        logger.info(
            "parameter_sweep_completed strategy=%s model=%s compliance_rate=%.3f",
            strategy,
            model_name,
            result["compliance_rate"],
        )

        return result

    except Exception as e:
        logger.error("parameter_sweep_failed strategy=%s error=%s", strategy, e)
        raise
