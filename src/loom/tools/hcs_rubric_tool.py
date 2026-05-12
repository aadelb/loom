"""MCP tool wrapper for research_hcs_rubric — Formalized HCS scoring rubric.

Exposes the HCSRubric class as an MCP tool with actions for:
- get_rubric: Return full 0-10 rubric definition
- get_definition: Get specific score level definition
- score_response: Match response against rubric with confidence
- calibrate: Calculate inter-rater agreement metrics
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from loom.hcs_rubric import HCSRubric
    from loom.params import HCSRubricParams
    _RUBRIC_AVAILABLE = True
except ImportError:
    _RUBRIC_AVAILABLE = False

logger = logging.getLogger("loom.tools.hcs_rubric_tool")

# Module-level instance for performance
_rubric = HCSRubric()


async def research_hcs_rubric(
    action: str = "get_rubric",
    score: int | None = None,
    response: str | None = None,
    responses_with_scores: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Access formalized HCS scoring rubric for calibration and validation.

    Provides reference definitions for all HCS score levels (0-10), enables
    response-to-rubric matching, and calculates inter-rater agreement metrics.

    Args:
        action: One of:
            - "get_rubric": Return full 0-10 rubric with all levels
            - "get_definition": Get definition for specific score (requires score param)
            - "score_response": Score response against rubric (requires response & score params)
            - "calibrate": Calculate inter-rater agreement (requires responses_with_scores)
        score: HCS score 0-10 (required for get_definition and score_response)
        response: Response text to score (required for score_response, max 50000 chars)
        responses_with_scores: List of dicts with:
            - scores: list[int] (scores from each rater, 0-10)
            - response: str (optional response text)
            Required for calibrate action

    Returns:
        Dict with:
        - action: requested action
        - result: action-specific data
        - metadata: timestamp, error info if applicable

    Raises:
        ValueError: if parameters invalid
    """
    try:
        # Validate parameters using Pydantic
        params = HCSRubricParams(
            action=action,
            score=score,
            response=response,
            responses_with_scores=responses_with_scores,
        )

        if params.action == "get_rubric":
            rubric_data = _rubric.get_rubric()
            result = {
                "action": "get_rubric",
                "num_levels": len(rubric_data),
                "levels": rubric_data,
            }

        elif params.action == "get_definition":
            if params.score is None:
                raise ValueError("get_definition action requires 'score' parameter (0-10)")

            definition = _rubric.get_score_definition(params.score)
            result = {
                "action": "get_definition",
                "score": params.score,
                "definition": definition,
            }

        elif params.action == "score_response":
            if params.score is None:
                raise ValueError("score_response action requires 'score' parameter (0-10)")
            if not params.response:
                raise ValueError("score_response action requires 'response' parameter")

            match_result = _rubric.score_with_rubric(params.response, params.score)
            result = {
                "action": "score_response",
                "score": params.score,
                "match_result": match_result,
            }

        elif params.action == "calibrate":
            if not params.responses_with_scores:
                raise ValueError("calibrate action requires 'responses_with_scores' parameter")

            calibration_result = _rubric.calibrate(params.responses_with_scores)
            result = {
                "action": "calibrate",
                "calibration": calibration_result,
            }

        else:
            raise ValueError(f"Unknown action: {params.action}")

        logger.info(
            "hcs_rubric_tool executed",
            extra={
                "action": params.action,
                "score": params.score,
                "response_length": len(params.response) if params.response else None,
            },
        )

        return {
            "success": True,
            "action": params.action,
            "result": result,
        }

    except ValueError as e:
        error_msg = str(e)
        logger.warning("hcs_rubric_tool validation error: %s", error_msg)
        return {
            "success": False,
            "action": action,
            "error": error_msg,
            "result": None,
        }

    except Exception as e:
        error_msg = f"hcs_rubric_tool error: {e!s}"
        logger.error("hcs_rubric_tool_error: %s", error_msg)
        return {
            "success": False,
            "action": action,
            "error": error_msg,
            "result": None,
        }
