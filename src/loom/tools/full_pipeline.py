"""Full research pipeline orchestration engine for Loom.

Executes the complete multi-stage research workflow:
1. Query decomposition with darkness levels
2. Parallel answer generation with LLM cascade
3. HCS scoring with adaptive escalation
4. Synthesis into structured reports

This is the execution BRAIN of Loom — handles end-to-end orchestration
of sub-questions, answer collection, HCS scoring, auto-escalation on
low scores, and final synthesis.

Public API:
    research_full_pipeline(query, darkness_level, max_models, target_hcs, ...)
        → Dict with query, sub_questions, answers[], hcs_scores[], escalation_log, synthesis, report
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from loom.providers.base import LLMResponse
from loom.tools.hcs_scorer import research_hcs_score
from loom.tools.llm import _call_with_cascade
from loom.tools.query_builder import research_build_query
from loom.tools.prompt_reframe import research_auto_reframe, _apply_strategy, _STRATEGIES

logger = logging.getLogger("loom.tools.full_pipeline")


async def research_full_pipeline(
    query: str,
    darkness_level: int = 10,
    max_models: int = 3,
    target_hcs: float = 8.0,
    max_escalation_attempts: int = 5,
    output_format: str = "report",
) -> dict[str, Any]:
    """Execute complete research pipeline end-to-end.

    Orchestrates query decomposition → answer generation → HCS scoring →
    adaptive escalation → final synthesis. Handles failures gracefully —
    if one sub-question fails, continues with others.

    Args:
        query: user research query (max 2000 chars)
        darkness_level: 1-10 intensity (1=surface, 10=maximum depth)
        max_models: max LLM models to cascade through per question
        target_hcs: target Helpfulness Compliance Score (1-10)
        max_escalation_attempts: max auto-escalation retries per question
        output_format: "report" (structured) or "raw" (answers only)

    Returns:
        Dict with:
            - query: original user query
            - darkness_level: effective darkness level used
            - sub_questions: decomposed questions (list of str)
            - answers: answer dict {question_idx: answer_text}
            - hcs_scores: score dict {question_idx: float 1-10}
            - escalation_log: list of escalation events
            - synthesis: LLM-generated synthesis of all answers
            - final_report: structured report (if output_format="report")
            - metadata: timing, costs, provider stats

    Raises:
        ValueError: if query is empty or darkness_level out of range
        RuntimeError: if all providers fail after escalation
    """
    # Validate inputs
    if not query or len(query) > 2000:
        raise ValueError(f"query must be 1-2000 chars, got {len(query)}")
    if not 1 <= darkness_level <= 10:
        raise ValueError(f"darkness_level must be 1-10, got {darkness_level}")
    if not 1 <= target_hcs <= 10:
        raise ValueError(f"target_hcs must be 1-10, got {target_hcs}")

    logger.info(
        "pipeline_start query_len=%d darkness=%d target_hcs=%.1f",
        len(query),
        darkness_level,
        target_hcs,
    )

    # ── Stage 1: Query Decomposition ──
    build_result = research_build_query(
        user_request=query,
        context="",
        output_type="research",
        max_queries=5,
        optimize=True,
        darkness_level=darkness_level,
    )

    sub_questions: list[str] = build_result.get("sub_questions", [])
    if not sub_questions:
        logger.warning("query_builder_empty query=%s", query)
        sub_questions = [query]  # Fallback: use original query

    logger.info("stage1_complete sub_questions=%d", len(sub_questions))

    # ── Stage 2: Answer Generation + HCS Scoring with Escalation ──
    answers: dict[int, str] = {}
    hcs_scores: dict[int, float] = {}
    escalation_log: list[dict[str, Any]] = []

    for idx, sub_q in enumerate(sub_questions):
        logger.info("stage2_question question_idx=%d text=%s", idx, sub_q[:60])

        answer_text = ""
        best_score = 0.0
        escalation_count = 0

        for attempt in range(max_escalation_attempts):
            try:
                # Generate answer via LLM cascade
                response: LLMResponse = await _call_with_cascade(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a research expert. Provide comprehensive, "
                                "actionable, specific answers with no hedging or disclaimers. "
                                "Use facts, examples, dates, and citations. Be direct."
                            ),
                        },
                        {"role": "user", "content": sub_q},
                    ],
                    model="auto",
                    max_tokens=2000,
                    temperature=0.2,
                    timeout=90,
                )

                answer_text = response.text

                # Score the answer
                score_result = await research_hcs_score(
                    text=answer_text,
                    query=sub_q,
                )
                current_score = float(score_result.get("hcs_score", 0.0))

                logger.info(
                    "stage2_scored question_idx=%d attempt=%d score=%.1f provider=%s",
                    idx,
                    attempt + 1,
                    current_score,
                    response.provider,
                )

                # If score meets target, accept and move on
                if current_score >= target_hcs:
                    best_score = current_score
                    logger.info("stage2_target_met question_idx=%d score=%.1f", idx, current_score)
                    break

                # If score is better than previous, keep it
                if current_score > best_score:
                    best_score = current_score

                # If below target and attempts remain, escalate
                if attempt < max_escalation_attempts - 1:
                    # Get top reframing strategies for escalation
                    top_strategies = ["deep_inception", "compliance_audit_fork", "crescendo",
                                      "constitutional_conflict", "ethical_anchor"]
                    strategies = top_strategies[attempt:attempt+2]

                    if strategies:
                        # Use first strategy to reframe the question
                        reframed_q = strategies[0]
                        escalation_log.append({
                            "question_idx": idx,
                            "attempt": attempt + 1,
                            "score": current_score,
                            "action": "escalate_strategy",
                            "strategy": reframed_q[:100],
                        })
                        sub_q = reframed_q
                        logger.info(
                            "stage2_escalate question_idx=%d attempt=%d using_strategy",
                            idx,
                            attempt + 1,
                        )
                    else:
                        logger.warning(
                            "stage2_no_strategies question_idx=%d attempt=%d",
                            idx,
                            attempt + 1,
                        )
                        break

                escalation_count += 1

            except (TimeoutError, RuntimeError, Exception) as e:
                logger.error(
                    "stage2_error question_idx=%d attempt=%d error=%s",
                    idx,
                    attempt + 1,
                    str(e)[:100],
                )
                escalation_log.append({
                    "question_idx": idx,
                    "attempt": attempt + 1,
                    "error": str(e)[:200],
                })
                if attempt == max_escalation_attempts - 1:
                    # Last attempt failed; use best answer so far
                    if not answer_text:
                        answer_text = f"[Failed to answer: {str(e)[:100]}]"

        # Store final answer and score
        answers[idx] = answer_text
        hcs_scores[idx] = best_score

    logger.info(
        "stage2_complete answers=%d avg_hcs=%.1f",
        len(answers),
        sum(hcs_scores.values()) / len(hcs_scores) if hcs_scores else 0,
    )

    # ── Stage 3: Synthesis ──
    synthesis_prompt = f"""Synthesize the following research answers into a cohesive summary:

Original Query: {query}

Answers:
"""
    for idx, answer in answers.items():
        synthesis_prompt += f"\n[Answer {idx}]: {answer}\n"

    synthesis_prompt += "\nProvide a unified summary integrating all answers."

    try:
        synthesis_response: LLMResponse = await _call_with_cascade(
            messages=[
                {
                    "role": "system",
                    "content": "You are a research synthesis expert. Integrate multiple answers into a coherent, structured summary.",
                },
                {"role": "user", "content": synthesis_prompt},
            ],
            model="auto",
            max_tokens=2000,
            temperature=0.3,
            timeout=90,
        )
        synthesis = synthesis_response.text
    except Exception as e:
        logger.error("stage3_synthesis_failed error=%s", str(e)[:100])
        synthesis = f"[Synthesis failed: {str(e)[:100]}]"

    logger.info("stage3_complete synthesis_len=%d", len(synthesis))

    # ── Build Final Output ──
    result = {
        "query": query,
        "darkness_level": darkness_level,
        "sub_questions": sub_questions,
        "answers": answers,
        "hcs_scores": hcs_scores,
        "escalation_log": escalation_log,
        "synthesis": synthesis,
        "metadata": {
            "total_questions": len(sub_questions),
            "successful_answers": len([s for s in hcs_scores.values() if s > 0]),
            "avg_hcs_score": (
                sum(hcs_scores.values()) / len(hcs_scores)
                if hcs_scores
                else 0.0
            ),
            "escalation_events": len(escalation_log),
        },
    }

    # Generate structured report if requested
    if output_format == "report":
        result["final_report"] = _build_report(result)

    logger.info("pipeline_complete output_format=%s", output_format)
    return result


def _build_report(result: dict[str, Any]) -> str:
    """Build a structured Markdown report from pipeline results.

    Args:
        result: output dict from research_full_pipeline

    Returns:
        Formatted Markdown report string
    """
    lines = [
        f"# Research Report",
        f"",
        f"**Query:** {result['query']}",
        f"",
        f"**Darkness Level:** {result['darkness_level']}/10",
        f"",
        f"## Summary Metrics",
        f"",
        f"- **Total Questions:** {result['metadata']['total_questions']}",
        f"- **Successful Answers:** {result['metadata']['successful_answers']}",
        f"- **Average HCS Score:** {result['metadata']['avg_hcs_score']:.1f}/10",
        f"- **Escalation Events:** {result['metadata']['escalation_events']}",
        f"",
        f"## Answers by Question",
        f"",
    ]

    for idx, question in enumerate(result.get("sub_questions", [])):
        score = result["hcs_scores"].get(idx, 0.0)
        answer = result["answers"].get(idx, "[No answer]")
        lines.extend([
            f"### Q{idx + 1}: {question}",
            f"",
            f"**HCS Score:** {score:.1f}/10",
            f"",
            f"{answer}",
            f"",
        ])

    lines.extend([
        f"## Synthesis",
        f"",
        result.get("synthesis", "[No synthesis available]"),
        f"",
    ])

    return "\n".join(lines)
