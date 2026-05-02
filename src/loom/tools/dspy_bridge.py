"""DSPy-to-LLM-cascade bridge — integrate DSPy with Loom's cost-tracked providers.

Enables DSPy to use Loom's LLM cascade instead of its own instances,
ensuring all costs are tracked and routed through the same provider fallback chain.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("loom.tools.dspy_bridge")

# Module-level tracking for DSPy calls
_dspy_stats: dict[str, Any] = {
    "total_calls": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost_usd": 0.0,
    "providers_used": {},
    "call_times": [],
}


class LoomDSPyLM:
    """DSPy LM class that routes through Loom's cost-tracked cascade.

    Implements the DSPy language model interface by wrapping
    _call_with_cascade and tracking usage statistics.
    """

    def __init__(
        self,
        model: str = "auto",
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ):
        """Initialize the Loom DSPy LM adapter.

        Args:
            model: model identifier or "auto" for config default
            max_tokens: max tokens per response
            temperature: sampling temperature (0.0-1.0)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.name = "LoomDSPyLM"

    async def __call__(
        self,
        prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> str:
        """Route a DSPy query through Loom's cascade.

        Args:
            prompt: single string prompt (legacy DSPy API)
            messages: chat-style message list (preferred)
            **kwargs: additional LLM parameters

        Returns:
            Response text from first successful provider
        """
        from loom.tools.llm import _call_with_cascade

        # Normalize to messages format
        if messages is None:
            if prompt is None:
                raise ValueError("either prompt or messages required")
            messages = [{"role": "user", "content": prompt}]

        # Merge kwargs with instance settings
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)
        model = kwargs.get("model", self.model)

        # Track call start time
        start_time = time.time()

        try:
            response = await _call_with_cascade(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=kwargs.get("timeout", 60),
            )

            # Update module-level stats
            elapsed_ms = int((time.time() - start_time) * 1000)
            _dspy_stats["total_calls"] += 1
            _dspy_stats["total_input_tokens"] += response.input_tokens
            _dspy_stats["total_output_tokens"] += response.output_tokens
            _dspy_stats["total_cost_usd"] += response.cost_usd
            _dspy_stats["call_times"].append(elapsed_ms)

            # Track provider usage
            if response.provider not in _dspy_stats["providers_used"]:
                _dspy_stats["providers_used"][response.provider] = 0
            _dspy_stats["providers_used"][response.provider] += 1

            logger.info(
                "dspy_call_ok provider=%s model=%s tokens=%d/%d cost=$%.5f latency=%dms",
                response.provider,
                response.model,
                response.input_tokens,
                response.output_tokens,
                response.cost_usd,
                elapsed_ms,
            )

            return response.text

        except Exception as e:
            logger.error(
                "dspy_call_failed model=%s error=%s latency=%dms",
                model,
                str(e)[:200],
                int((time.time() - start_time) * 1000),
            )
            raise


async def research_dspy_configure(
    model: str = "auto",
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """Configure DSPy to use Loom's LLM cascade for all calls.

    Integrates DSPy with Loom's cost-tracked provider cascade,
    ensuring all DSPy LLM calls route through the configured fallback
    chain and are properly metered.

    Args:
        model: model identifier or "auto" for config default
        max_tokens: maximum tokens per response
        temperature: sampling temperature (0.0-1.0)

    Returns:
        Configuration status dict with:
        - configured: True if DSPy integration succeeded
        - model: resolved model identifier
        - dspy_version: DSPy package version or None
        - lm_class: name of the LM adapter class
        - error: error message if failed
    """
    try:
        import importlib

        # Check if DSPy is installed
        try:
            dspy_module = importlib.import_module("dspy")
            dspy_version = getattr(dspy_module, "__version__", "unknown")
        except ImportError:
            return {
                "configured": False,
                "error": "DSPy not installed; run: pip install dspy-ai",
                "dspy_version": None,
                "lm_class": None,
            }

        # Create LoomDSPyLM instance
        loom_lm = LoomDSPyLM(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Configure DSPy to use our LM
        dspy_module.settings.configure(lm=loom_lm)

        logger.info(
            "dspy_configured model=%s max_tokens=%d temperature=%.2f version=%s",
            model,
            max_tokens,
            temperature,
            dspy_version,
        )

        return {
            "configured": True,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "dspy_version": dspy_version,
            "lm_class": "LoomDSPyLM",
        }

    except Exception as e:
        error_msg = f"DSPy configuration failed: {str(e)[:200]}"
        logger.error("dspy_configure_failed error=%s", error_msg)
        return {
            "configured": False,
            "error": error_msg,
            "dspy_version": None,
            "lm_class": None,
        }


async def research_dspy_cost_report() -> dict[str, Any]:
    """Report DSPy's cumulative LLM usage through Loom's cascade.

    Returns detailed metrics on all DSPy calls routed through Loom,
    including token usage, costs, and provider distribution.

    Returns:
        Usage statistics dict with:
        - total_calls: number of DSPy LLM calls
        - total_input_tokens: cumulative input tokens
        - total_output_tokens: cumulative output tokens
        - estimated_cost_usd: total cost in USD
        - providers_used: dict of provider → call count
        - avg_latency_ms: average latency across calls
        - call_times: list of individual call latencies (ms)
    """
    total_time = sum(_dspy_stats["call_times"]) if _dspy_stats["call_times"] else 0
    avg_latency = (
        total_time / len(_dspy_stats["call_times"])
        if _dspy_stats["call_times"]
        else 0
    )

    result = {
        "total_calls": _dspy_stats["total_calls"],
        "total_input_tokens": _dspy_stats["total_input_tokens"],
        "total_output_tokens": _dspy_stats["total_output_tokens"],
        "estimated_cost_usd": round(_dspy_stats["total_cost_usd"], 5),
        "providers_used": dict(_dspy_stats["providers_used"]),
        "avg_latency_ms": round(avg_latency, 1),
    }

    logger.info(
        "dspy_cost_report calls=%d tokens=%d/%d cost=$%.5f",
        result["total_calls"],
        result["total_input_tokens"],
        result["total_output_tokens"],
        result["estimated_cost_usd"],
    )

    return result
