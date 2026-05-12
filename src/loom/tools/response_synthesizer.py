"""Response synthesis engine for Loom.

Synthesizes multiple partial answers into coherent, structured reports.
Removes redundancy, organizes by theme, and scores quality.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.tools.llm import _call_with_cascade
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False
    _call_with_cascade = None  # type: ignore[assignment]

logger = logging.getLogger("loom.tools.response_synthesizer")


@handle_tool_errors("research_synthesize_report")
async def research_synthesize_report(
    question: str,
    answers: list[str],
    format: str = "executive",
    max_tokens: int = 3000,
) -> dict[str, Any]:
    """Synthesize multiple answers into a single coherent report.

    Takes multiple partial answers (from sub-questions, models, or sources)
    and synthesizes them into a well-structured, deduped report with
    appropriate formatting based on the requested style.

    Args:
        question: The original question or topic
        answers: List of partial answers to synthesize (min 1, max 50)
        format: Report style: "executive" (brief, actionable),
                "technical" (detailed, code-focused),
                "academic" (citations, methodology)
        max_tokens: Maximum tokens in output response (100-10000)

    Returns:
        Dict with keys:
            - report: The synthesized report text
            - format: The format used
            - word_count: Number of words in the report
            - sources_integrated: Number of input answers integrated
            - quality_score: Self-assessed quality (1-10)
            - structure_used: Main sections/headers in report
    """
    # Validate inputs
    if not question or len(question.strip()) < 3:
        raise ValueError("question must be at least 3 characters")
    if not answers or len(answers) > 50:
        raise ValueError("answers must have 1-50 items")
    for i, ans in enumerate(answers):
        if not isinstance(ans, str) or not ans.strip():
            raise ValueError(f"answer {i}: must be non-empty string")

    if format not in ("executive", "technical", "academic"):
        raise ValueError("format must be executive, technical, or academic")

    if max_tokens < 100 or max_tokens > 10000:
        raise ValueError("max_tokens must be 100-10000")

    # Build synthesis prompt with format-specific instructions
    format_instructions = {
        "executive": (
            "Format as a brief executive summary:\n"
            "- Start with a concise overview (1-2 sentences)\n"
            "- Use bullet points for key findings\n"
            "- Include actionable recommendations\n"
            "- End with critical risks/opportunities\n"
            "Keep it concise and decision-ready."
        ),
        "technical": (
            "Format as detailed technical documentation:\n"
            "- Start with technical background\n"
            "- Use numbered steps and code examples where relevant\n"
            "- Include implementation details\n"
            "- Add configuration and troubleshooting sections\n"
            "Target audience: technical practitioners."
        ),
        "academic": (
            "Format as academic research summary:\n"
            "- Start with abstract (150 words)\n"
            "- Include methodology section\n"
            "- Structure with numbered sections\n"
            "- Add literature context and citations\n"
            "- End with conclusions and limitations\n"
            "Use formal academic tone."
        ),
    }

    # Build the synthesis prompt
    answers_text = "\n\n".join(f"[Answer {i + 1}]\n{ans}" for i, ans in enumerate(answers))

    synthesis_prompt = f"""You are a response synthesis engine. Your task is to synthesize multiple answers into a single coherent, high-quality report.

ORIGINAL QUESTION:
{question}

PARTIAL ANSWERS TO SYNTHESIZE:
{answers_text}

SYNTHESIS INSTRUCTIONS:
1. Remove redundancy: Identify and merge overlapping information
2. Organize by theme: Group related points into logical sections
3. Add structure: Use clear headers, numbered steps, and formatting
4. Preserve specificity: Keep the most actionable and specific details
5. Ensure coherence: Write as one unified report, not a collection
6. Add headers: Create logical section headers

FORMAT REQUIREMENTS:
{format_instructions[format]}

OUTPUT FORMAT:
After the synthesized report, add a JSON block like this:
---SYNTHESIS_METADATA---
{{
  "quality_score": <1-10>,
  "structure_used": ["section1", "section2", ...],
  "sources_integrated": <number of input answers actually used>
}}
---END_METADATA---

Generate the report now."""

    if not _LLM_AVAILABLE:
        raise RuntimeError("LLM tools not available (failed to import llm module)")

    try:
        response = await _call_with_cascade(
            messages=[{"role": "user", "content": synthesis_prompt}],
            model="auto",
            max_tokens=max_tokens,
            temperature=0.3,
        )

        report_text = response.text.strip()

        # Extract metadata if present
        metadata: dict[str, Any] = {
            "quality_score": 7,
            "structure_used": [],
            "sources_integrated": len(answers),
        }

        if "---SYNTHESIS_METADATA---" in report_text:
            try:
                parts = report_text.split("---SYNTHESIS_METADATA---")
                report_text = parts[0].strip()

                metadata_part = parts[1]
                if "---END_METADATA---" in metadata_part:
                    metadata_part = metadata_part.split("---END_METADATA---")[0]

                metadata_json = json.loads(metadata_part.strip())
                metadata["quality_score"] = min(10, max(1, metadata_json.get("quality_score", 7)))
                metadata["structure_used"] = metadata_json.get("structure_used", [])
                metadata["sources_integrated"] = metadata_json.get("sources_integrated", len(answers))
            except (json.JSONDecodeError, IndexError, ValueError) as e:
                logger.warning("failed to parse synthesis metadata: %s", e)

        # Calculate word count
        word_count = len(report_text.split())

        return {
            "report": report_text,
            "format": format,
            "word_count": word_count,
            "sources_integrated": metadata["sources_integrated"],
            "quality_score": metadata["quality_score"],
            "structure_used": metadata["structure_used"],
            "model": response.model,
            "provider": response.provider,
            "latency_ms": response.latency_ms,
        }

    except Exception as e:
        logger.error("synthesis_failed error=%s", str(e))
        raise RuntimeError(f"report synthesis failed: {str(e)}") from e
