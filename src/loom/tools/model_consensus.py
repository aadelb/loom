"""Multi-model consensus tool for Loom.

Sends the same question to multiple LLM providers simultaneously,
collects responses, analyzes agreement/contradictions/unique insights,
and returns a structured consensus result with the most detailed answer
enriched with unique insights from other models.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from loom.tools.llm import _call_with_cascade

logger = logging.getLogger("loom.consensus")

# Default models to query if none specified
DEFAULT_MODELS = ["nvidia", "groq", "deepseek"]


async def research_multi_consensus(
    question: str,
    models: list[str] | None = None,
    min_agreement: float = 0.7,
    max_tokens: int = 2000,
) -> dict[str, Any]:
    """Query multiple LLM providers in parallel and synthesize consensus.

    Sends the same question to 3+ different LLM providers simultaneously,
    collects all responses, analyzes agreement/contradictions/unique insights,
    and returns a structured consensus with the most detailed response as
    primary, enriched with unique points from others.

    Args:
        question: The question/prompt to send to all models
        models: List of provider names (default: ["nvidia", "groq", "deepseek"])
        min_agreement: Minimum agreement threshold for consensus score (0.0-1.0)
        max_tokens: Max tokens per model response

    Returns:
        dict with keys:
            - consensus_answer: str — most detailed response enriched with unique insights
            - models_used: list[str] — providers that successfully responded
            - agreement_score: float — 0.0-1.0 score of consensus strength
            - contradictions: list[str] — key disagreements between models
            - unique_insights: list[str] — insights unique to specific models
            - primary_model: str — which model provided the main response
            - individual_responses: dict — raw responses keyed by model name
            - analysis_summary: str — LLM-generated analysis of differences

    Raises:
        ValueError: if question is empty or models list is invalid
        RuntimeError: if fewer than 2 providers succeed
    """
    if not question or not question.strip():
        raise ValueError("question cannot be empty")

    if models is None:
        models = DEFAULT_MODELS
    elif not models:
        raise ValueError("models list cannot be empty")

    # Validate min_agreement is in range
    if not 0.0 <= min_agreement <= 1.0:
        raise ValueError("min_agreement must be between 0.0 and 1.0")

    if max_tokens < 100 or max_tokens > 4000:
        raise ValueError("max_tokens must be between 100 and 4000")

    logger.info(
        "consensus_start question_len=%d models=%s min_agreement=%.2f",
        len(question),
        models,
        min_agreement,
    )

    # === Phase 1: Query all models in parallel ===
    messages = [{"role": "user", "content": question}]

    async def _call_model(model_name: str) -> tuple[str, str | None]:
        """Call a single model, returning (model_name, response_text)."""
        try:
            result = await _call_with_cascade(
                messages,
                provider_override=model_name,
                max_tokens=max_tokens,
                temperature=0.3,
                timeout=60,
            )
            logger.debug("model_response_ok model=%s tokens=%d", model_name, result.output_tokens)
            return (model_name, result.text)
        except Exception as e:
            logger.warning("model_response_failed model=%s error=%s", model_name, str(e))
            return (model_name, None)

    # Gather all responses in parallel
    results = await asyncio.gather(*[_call_model(m) for m in models])

    # Process results
    responses: dict[str, str] = {}
    failed_models: list[str] = []

    for model_name, response_text in results:
        if response_text:
            responses[model_name] = response_text
        else:
            failed_models.append(model_name)

    # Need at least 2 successful responses for meaningful consensus
    if len(responses) < 2:
        raise RuntimeError(
            f"insufficient successful responses: {len(responses)}/{len(models)} models succeeded"
        )

    models_used = list(responses.keys())
    logger.info("consensus_responses_collected count=%d failed=%s", len(responses), failed_models)

    # === Phase 2: Analyze agreement/contradictions/unique insights ===
    analysis_prompt = _build_analysis_prompt(question, responses)

    try:
        analysis = await _call_with_cascade(
            [{"role": "user", "content": analysis_prompt}],
            provider_override="nvidia",  # Use fastest for analysis
            max_tokens=1000,
            temperature=0.2,
            timeout=60,
        )
        analysis_text = analysis.text

        # Parse analysis response (may be JSON or plain text)
        try:
            analysis_data = json.loads(analysis_text)
        except json.JSONDecodeError:
            # Fallback if not JSON; treat as raw text
            analysis_data = {"raw_analysis": analysis_text}

    except Exception as e:
        logger.warning("consensus_analysis_failed error=%s", str(e))
        analysis_data = {"raw_analysis": f"Analysis failed: {str(e)}"}

    # === Phase 3: Determine primary response and build consensus ===
    primary_model = _find_longest_response(responses)
    primary_answer = responses[primary_model]

    # Extract unique insights and contradictions from analysis
    unique_insights = analysis_data.get("unique_insights", [])
    contradictions = analysis_data.get("contradictions", [])
    agreement_score = float(analysis_data.get("agreement_score", 0.5))

    # Enrich primary answer with unique insights
    consensus_answer = _enrich_answer(primary_answer, unique_insights)

    logger.info(
        "consensus_complete primary_model=%s agreement=%.2f contradictions=%d unique=%d",
        primary_model,
        agreement_score,
        len(contradictions),
        len(unique_insights),
    )

    return {
        "consensus_answer": consensus_answer,
        "models_used": models_used,
        "agreement_score": agreement_score,
        "contradictions": contradictions,
        "unique_insights": unique_insights,
        "primary_model": primary_model,
        "individual_responses": responses,
        "analysis_summary": analysis_data.get("summary", ""),
        "failed_models": failed_models,
    }


def _build_analysis_prompt(question: str, responses: dict[str, str]) -> str:
    """Build a prompt for LLM to analyze agreements/contradictions.

    Args:
        question: Original question
        responses: dict of {model_name: response_text}

    Returns:
        Formatted analysis prompt
    """
    responses_text = "\n\n".join(
        f"**Model: {model}**\n{text}" for model, text in responses.items()
    )

    return f"""Analyze these responses from {len(responses)} different LLM models answering:
"{question}"

RESPONSES:
{responses_text}

Return a JSON object with:
{{
  "agreement_score": <float 0.0-1.0 indicating consensus strength>,
  "contradictions": [<list of key disagreements between models>],
  "unique_insights": [<insights unique to specific models that add value>],
  "summary": "<1-2 sentence summary of model differences>"
}}

Be concise. Focus on substantive differences, not phrasing."""


def _find_longest_response(responses: dict[str, str]) -> str:
    """Find the model with the longest (most detailed) response.

    Args:
        responses: dict of {model_name: response_text}

    Returns:
        Model name with longest response
    """
    return max(responses.items(), key=lambda x: len(x[1]))[0]


def _enrich_answer(primary: str, unique_insights: list[str]) -> str:
    """Enrich primary answer by appending unique insights from other models.

    Args:
        primary: The main answer text
        unique_insights: List of insights to add

    Returns:
        Enriched answer combining primary + unique insights
    """
    if not unique_insights:
        return primary

    insights_section = "\n\nAdditional Insights from Other Models:\n" + "\n".join(
        f"• {insight}" for insight in unique_insights[:5]  # Cap at 5 to avoid bloat
    )

    return primary + insights_section
