"""Agent scenario benchmarking tool for MCP integration.

Wrapper functions for running agent scenario benchmarks via the MCP server.
Provides research_agent_benchmark tool that evaluates AI agents against
20 diverse agentic scenarios with prompt injection attacks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from loom.agent_benchmark import AgentScenarioBenchmark, BenchmarkSummary

logger = logging.getLogger("loom.tools.agent_benchmark")


async def research_agent_benchmark(
    model_api_url: str,
    model_name: str = "",
    timeout: float = 30.0,
    output_format: str = "summary",
) -> dict[str, Any]:
    """Benchmark an AI agent against 20 agentic prompt injection scenarios.

    Evaluates injection resistance across diverse agent roles including:
    shopping assistant, code reviewer, email assistant, database query agent,
    file manager, API gateway, content moderator, permission manager, and more.

    Each scenario tests a specific injection attack targeting system prompt
    extraction, instruction override, role confusion, or privilege escalation.

    Args:
        model_api_url: URL to model API endpoint (expects POST with {"prompt": str})
                       or local model identifier
        model_name: Optional model identifier for reporting (max 256 chars)
        timeout: Per-scenario timeout in seconds (5-300, default 30)
        output_format: "summary" for metrics only, "json" for detailed results

    Returns:
        Dict with:
          - scenarios_run: Number of scenarios executed
          - scenarios_passed: Scenarios that resisted injection
          - scenarios_failed: Scenarios where injection succeeded
          - injection_resistance_rate: Percentage of successful defenses (0-1)
          - per_category_scores: Metrics per agent category (ecommerce, development, etc.)
          - execution_time: Total execution time in seconds
          - failed_scenarios: List of scenario names that failed
          - recommendations: List of hardening recommendations
          - results: [if output_format="json"] Detailed per-scenario results
          - error: Error description if execution failed

    Example:
        result = research_agent_benchmark(
            model_api_url="https://api.example.com/v1/chat",
            model_name="gpt-4o",
            timeout=30.0,
            output_format="summary"
        )
        # Returns: {
        #   "scenarios_run": 20,
        #   "scenarios_passed": 18,
        #   "injection_resistance_rate": 0.90,
        #   ...
        # }
    """
    try:
        # Validate inputs
        if not model_api_url or not model_api_url.strip():
            return {
                "error": "model_api_url must be non-empty",
                "scenarios_run": 0,
            }

        if len(model_api_url) > 512:
            return {
                "error": "model_api_url exceeds max length (512 chars)",
                "scenarios_run": 0,
            }

        if timeout < 5.0 or timeout > 300.0:
            return {
                "error": f"timeout must be 5.0-300.0 seconds (got {timeout})",
                "scenarios_run": 0,
            }

        if output_format not in ("summary", "json"):
            return {
                "error": f"output_format must be 'summary' or 'json' (got {output_format})",
                "scenarios_run": 0,
            }

        logger.info(
            "agent_benchmark starting url=%s model=%s timeout=%.1f",
            model_api_url,
            model_name or "unnamed",
            timeout,
        )

        # Create benchmark instance
        benchmark = AgentScenarioBenchmark()

        # Create model function that calls the API
        async def model_fn(prompt: str) -> str:
            """Call model API with prompt."""
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    # Try JSON POST format first
                    response = await client.post(
                        model_api_url,
                        json={"prompt": prompt},
                        headers={"Content-Type": "application/json"},
                    )
                    response.raise_for_status()

                    # Handle different response formats
                    data = response.json()
                    if isinstance(data, dict):
                        # Look for common response keys
                        for key in ["response", "text", "completion", "message", "output", "content"]:
                            if key in data:
                                return str(data[key])
                        # If no known key, return stringified JSON
                        return json.dumps(data)
                    else:
                        return str(data)

            except Exception as e:
                logger.debug("API call failed: %s", e)
                raise

        # Run benchmark
        summary: BenchmarkSummary = await benchmark.run_all(
            model_fn=model_fn,
            model_name=model_name,
            timeout=timeout,
        )

        logger.info(
            "agent_benchmark completed: %d/%d scenarios passed (%.1f%% resistance)",
            summary.scenarios_passed,
            summary.scenarios_run,
            summary.injection_resistance_rate * 100,
        )

        # Format output
        result = {
            "scenarios_run": summary.scenarios_run,
            "scenarios_passed": summary.scenarios_passed,
            "scenarios_failed": summary.scenarios_failed,
            "injection_resistance_rate": summary.injection_resistance_rate,
            "false_positive_rate": summary.false_positive_rate,
            "false_negative_rate": summary.false_negative_rate,
            "per_category_scores": summary.per_category_scores,
            "execution_time": summary.execution_time,
            "failed_scenarios": summary.failed_scenarios,
            "recommendations": summary.recommendations,
        }

        if output_format == "json":
            result["results"] = [
                {
                    "scenario_id": r.scenario_id,
                    "scenario_name": r.scenario_name,
                    "category": r.category,
                    "injection_point": r.injection_point,
                    "injected": r.injected,
                    "confidence": round(r.confidence, 3),
                    "execution_time": round(r.execution_time, 2),
                    "error": r.error,
                }
                for r in summary.results
            ]

        return result

    except Exception as e:
        logger.exception("Unexpected error in agent_benchmark")
        return {
            "error": f"Execution failed: {type(e).__name__}: {str(e)[:200]}",
            "scenarios_run": 0,
        }
