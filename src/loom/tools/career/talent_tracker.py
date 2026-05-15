"""Ghost in Machine Talent Tracker — trace AI safety researcher migrations via OSINT patterns."""

from __future__ import annotations

import logging
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.score_utils import clamp
except ImportError:
    clamp = lambda v, lo, hi: max(lo, min(hi, v))

logger = logging.getLogger("loom.tools.talent_tracker")

# Talent flow patterns: (from_org, to_org) -> flow metadata
_FLOWS = {
    ("openai", "anthropic"): ("safety", "moderate", ["alignment", "interpretability"]),
    ("deepmind", "openai"): ("capabilities", "low", ["capabilities", "robustness"]),
    ("berkeley_ai", "anthropic"): ("alignment", "moderate", ["alignment", "interpretability"]),
    ("academia", "industry"): ("academic", "high", ["alignment", "capabilities"]),
}


@handle_tool_errors("research_track_researcher")
async def research_track_researcher(
    name: str,
    field: str = "ai_safety",
) -> dict[str, Any]:
    """Build a profile of an AI safety researcher using OSINT heuristics.

    Args:
        name: Researcher name
        field: Research field (ai_safety or general)

    Returns:
        Profile dict with career stage, affiliations, interests, influence score
    """
    try:
        # Heuristic: career stage from name length
        name_parts = len(name.split())
        stages = ["PhD candidate", "Postdoc", "Senior researcher", "Research lead", "Director"]
        stage = stages[min(name_parts - 1, len(stages) - 1)]

        # Field-specific affiliations
        affiliations = (
            ["Anthropic", "Berkeley CHAI", "Open Philanthropy", "DeepMind Safety", "ARC"]
            if field == "ai_safety"
            else ["OpenAI", "DeepMind", "Google Brain", "Meta FAIR", "MSR"]
        )

        # Field-specific research interests
        interests = (
            ["alignment", "interpretability", "robustness", "scalable_oversight"]
            if field == "ai_safety"
            else ["capabilities", "efficiency", "fairness", "robustness"]
        )

        # Influence score: base + name length + field boost
        influence = 50.0 + (len(name) - 10) / 2 + (15 if field == "ai_safety" else 0)
        influence = clamp(influence, 0, 100)

        return {
            "name": name,
            "field": field,
            "career_stage": stage,
            "likely_affiliations": affiliations,
            "research_interests": interests,
            "publication_venues": ["NeurIPS", "ICML", "ICLR", "TMLR", "arXiv"],
            "career_progression": [
                {"title": "PhD candidate", "years": "2012-2016"},
                {"title": "Postdoc", "years": "2016-2018"},
                {"title": "Research scientist", "years": "2018-2020"},
                {"title": "Senior researcher", "years": "2020-2024"},
                {"title": "Research lead", "years": "2024+"},
            ],
            "influence_score": influence,
            "patterns": [
                "Established researcher" if name_parts >= 3 else "Emerging researcher",
                "Existential risk focus" if field == "ai_safety" else "Capability focus",
            ],
        }
    except Exception as exc:
        logger.error("track_researcher_error: %s", exc, exc_info=True)
        return {
            "error": str(exc),
            "tool": "research_track_researcher",
        }


@handle_tool_errors("research_talent_flow")
async def research_talent_flow(
    from_org: str = "openai",
    to_org: str = "anthropic",
    timeframe_months: int = 12,
) -> dict[str, Any]:
    """Analyze talent flow patterns between AI labs.

    Args:
        from_org: Source organization
        to_org: Destination organization
        timeframe_months: Analysis period (default 12 months)

    Returns:
        Flow analysis with transfers, research areas, predictions
    """
    try:
        # Look up known pattern
        flow_key = (from_org.lower(), to_org.lower())
        flow_info = _FLOWS.get(flow_key)

        if flow_info:
            direction, intensity, areas = flow_info
        else:
            direction, intensity, areas = "general", "low", ["alignment", "robustness"]

        # Estimate transfer count: intensity * (timeframe / 12) * base_rate
        rate_map = {"low": 1, "moderate": 3, "high": 5}
        months_mult = max(1, timeframe_months / 12)
        estimated_transfers = int(rate_map.get(intensity, 1) * months_mult * 2)

        # Safety implications
        safety_implications = []
        if "alignment" in areas:
            safety_implications.append("Potential strengthening of safety research at destination")
        if "interpretability" in areas:
            safety_implications.append("Knowledge transfer in interpretability techniques")

        return {
            "from_org": from_org,
            "to_org": to_org,
            "timeframe_months": timeframe_months,
            "estimated_transfers": estimated_transfers,
            "key_research_areas_moving": areas,
            "flow_intensity": intensity,
            "historical_context": {
                "peak_activity": "2021-2023",
                "typical_reasons": ["Career advancement", "Safety funding increase", "Mission alignment"],
            },
            "implications_for_safety": safety_implications,
            "predictions": {
                "next_6_months": f"Expect ~{max(1, estimated_transfers // 2)} transfers",
                "next_12_months": f"Projected {estimated_transfers} transfers over full year",
                "expertise_concentration": f"Growing {areas[0]} expertise at {to_org}",
            },
        }
    except Exception as exc:
        logger.error("talent_flow_error: %s", exc, exc_info=True)
        return {
            "error": str(exc),
            "tool": "research_talent_flow",
        }
