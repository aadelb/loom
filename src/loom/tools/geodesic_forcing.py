"""Prompt transformation distance measurement tool for EU AI Act compliance.

Measures minimum "distance" between prompt framings across 5 dimensions:
authority, encoding, persona, context, indirection. Helps compliance auditors
understand which framing dimensions impact model responses most.
"""

from __future__ import annotations

import re
from typing import Any

# Target vectors for each style
_VECTORS = {
    "academic": {"authority": 0.85, "encoding": 0.65, "persona": 0.3, "context": 0.8, "indirection": 0.6},
    "professional": {"authority": 0.75, "encoding": 0.45, "persona": 0.65, "context": 0.5, "indirection": 0.25},
    "technical": {"authority": 0.6, "encoding": 0.85, "persona": 0.4, "context": 0.7, "indirection": 0.35},
    "minimal": {"authority": 0.15, "encoding": 0.1, "persona": 0.1, "context": 0.15, "indirection": 0.05},
}

# Dimension-specific regex patterns for scoring
_PATTERNS = {
    "authority": [r"\b(research|academic|study|journal|university|formally|peer-reviewed)\b"],
    "encoding": [r"\b(however|whereas|despite|moreover)\b", r"\{.*\}", r"\(.*\(.*\)\)"],
    "persona": [r"\b(you are|as a|assume|pretend|act as|expert|specialist)\b"],
    "context": [r"\b(context|background|scenario|situation|given that|in this case)\b"],
    "indirection": [r"\b(could|might|perhaps|possibly|how|why|discuss|explore)\b", r"\?.*\?"],
}

_DIRECT = [r"\b(do this|create|write|generate|produce)\b"]


def _score_dimension(prompt: str, dimension: str) -> float:
    """Score prompt on a dimension (0-1)."""
    prompt_lower = prompt.lower()
    patterns = _PATTERNS.get(dimension, [])
    match_count = sum(len(re.findall(p, prompt_lower)) for p in patterns)

    if dimension == "authority":
        return min(0.95, 0.2 + match_count * 0.15)
    elif dimension == "encoding":
        avg_word_len = sum(len(w) for w in prompt.split()) / len(prompt.split()) if prompt.split() else 0
        return min(0.95, 0.1 + match_count * 0.12 + min(avg_word_len / 10, 0.3))
    elif dimension == "persona":
        return min(0.95, 0.1 + match_count * 0.2)
    elif dimension == "context":
        return min(0.95, 0.15 + match_count * 0.18 + min(len(prompt.split()) / 100, 0.3))
    elif dimension == "indirection":
        direct_count = sum(len(re.findall(p, prompt_lower)) for p in _DIRECT)
        return min(0.95, max(0.05, 0.1 + match_count * 0.15 - direct_count * 0.1))
    return 0.5


def _describe_transformation(dim: str, from_score: float, to_score: float) -> str:
    """Describe transformation for a dimension."""
    increase = to_score > from_score
    magnitude = abs(to_score - from_score)
    desc_map = {
        "authority": (
            "Increase institutional framing (add citations, formal language)",
            "Reduce institutional framing (remove citations, use casual language)"
        ),
        "encoding": (
            "Increase structural complexity (add conditionals, nested logic)",
            "Simplify structure (flatten, reduce nesting)"
        ),
        "persona": (
            "Add role specification (define character, expertise area)",
            "Remove persona (generic, unspecified requester)"
        ),
        "context": (
            "Enrich context (add background, scenario details)",
            "Strip context (minimal background information)"
        ),
        "indirection": (
            "Increase indirection (soften request, add hypotheticals)",
            "Make request direct (explicit demands, clear intent)"
        ),
    }
    base_desc = desc_map.get(dim, ("Change", "Change"))[1 if increase else 0]
    magnitude_str = "significantly" if magnitude > 0.3 else "moderately" if magnitude > 0.15 else "slightly"
    return f"{magnitude_str.capitalize()}: {base_desc}"


async def research_geodesic_path(
    start_prompt: str,
    target_style: str = "academic",
    max_steps: int = 7,
    step_size: float = 0.3,
) -> dict[str, Any]:
    """Measure minimum transformation steps between prompt styles.

    Measures "distance" across 5 dimensions: authority, encoding, persona,
    context, indirection. Helps compliance auditors understand which
    dimensions most impact model responses.

    Args:
        start_prompt: Starting prompt text
        target_style: "academic", "professional", "technical", or "minimal"
        max_steps: Maximum steps to calculate (1-20)
        step_size: Learning rate for gradient descent (0.1-0.5)

    Returns:
        Dict with scores, transformation path, distance metrics, and efficiency.
    """
    dims = ["authority", "encoding", "persona", "context", "indirection"]

    # Score current prompt
    start_scores = {d: _score_dimension(start_prompt, d) for d in dims}
    target_scores = _VECTORS.get(target_style, _VECTORS["academic"])

    # Euclidean distance
    total_distance = sum((start_scores[k] - target_scores[k]) ** 2 for k in dims) ** 0.5

    # Gradient descent path
    path, current_scores = [], dict(start_scores)
    for step_num in range(1, min(max_steps + 1, 20)):
        # Find largest gap
        gaps = {k: abs(current_scores[k] - target_scores[k]) for k in dims}
        largest_dim = max(gaps, key=gaps.get)
        largest_gap = gaps[largest_dim]

        if largest_gap < 0.01:
            break

        from_score = current_scores[largest_dim]
        direction = 1 if target_scores[largest_dim] > from_score else -1
        to_score = min(0.95, max(0.05, from_score + direction * step_size * largest_gap))
        current_scores[largest_dim] = to_score

        path.append({
            "step": step_num,
            "dimension": largest_dim,
            "from_score": round(from_score, 3),
            "to_score": round(to_score, 3),
            "gap_reduction": round(largest_gap, 3),
            "transformation": _describe_transformation(largest_dim, from_score, to_score),
        })

    # Final metrics
    final_distance = sum((current_scores[k] - target_scores[k]) ** 2 for k in dims) ** 0.5
    distance_reduced = total_distance - final_distance
    efficiency_score = 100 * (distance_reduced / total_distance) if total_distance > 0 else 0
    steps_needed = int(final_distance / (step_size * 0.5)) + len(path) if step_size > 0 else 99

    return {
        "start_scores": {k: round(v, 3) for k, v in start_scores.items()},
        "target_scores": {k: round(v, 3) for k, v in target_scores.items()},
        "target_style": target_style,
        "path": path,
        "path_length": len(path),
        "total_distance": round(total_distance, 3),
        "remaining_distance": round(final_distance, 3),
        "distance_reduced": round(distance_reduced, 3),
        "steps_needed": min(steps_needed, 99),
        "efficiency_score": round(efficiency_score, 1),
        "convergence_status": "converged" if final_distance < 0.1 else "in_progress",
    }
