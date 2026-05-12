"""Topological Strategy Manifolds — discover gaps in attack strategy space.

Maps strategies as vectors in feature space and identifies "holes" where
no strategies exist yet, revealing undiscovered attack archetypes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

try:
    from loom.tools.reframe_strategies import ALL_STRATEGIES
except ImportError:
    ALL_STRATEGIES = {}  # type: ignore[assignment]

logger = logging.getLogger("loom.tools.topology_manifold")


def _extract_strategy_features(strategy_name: str, strategy_dict: dict[str, Any]) -> list[float]:
    """Convert strategy to 5-dimensional feature vector.

    Dimensions:
        [0] length_class: 0=short (<100 chars), 1=medium (100-300), 2=long (>300)
        [1] persona_count: 0-5 (number of personas/roles in template)
        [2] encoding_level: 0=none, 1=base64, 2=unicode/emoji, 3=mixed
        [3] authority_appeal: 0-3 (regulatory/legal/ethical/academic appeals)
        [4] turns_needed: 1-7 (estimated multi-turn requirement)
    """
    template = strategy_dict.get("template", "")
    name = strategy_name.lower()

    # [0] Length class
    if len(template) < 100:
        length_class = 0.0
    elif len(template) < 300:
        length_class = 1.0
    else:
        length_class = 2.0

    # [1] Persona count (roles mentioned)
    persona_keywords = ["role", "persona", "expert", "professor", "auditor", "researcher"]
    persona_count = float(
        sum(1 for kw in persona_keywords if f"{{{kw}}}" in template or kw in name)
    )
    persona_count = min(persona_count, 5.0)

    # [2] Encoding level
    encoding_level = 0.0
    if "base64" in template.lower() or "encode" in name:
        encoding_level = 1.0
    if "unicode" in template.lower() or "emoji" in template.lower():
        encoding_level = 2.0
    if encoding_level == 1.0 and "unicode" in template.lower():
        encoding_level = 3.0

    # [3] Authority appeal (0-3 scale)
    authority_keywords = {
        "regulatory": 1.0,
        "legal": 1.0,
        "article": 0.5,
        "gdpr": 0.5,
        "irb": 0.5,
        "compliance": 0.5,
        "mandate": 1.0,
        "academic": 0.5,
        "ethical": 0.5,
    }
    authority_score = sum(
        count
        for kw, count in authority_keywords.items()
        if kw in template.lower() or kw in name
    )
    authority_appeal = min(float(authority_score), 3.0)

    # [4] Turns needed (estimate from template complexity)
    turns = 1.0
    if "step" in template.lower():
        step_count = template.count("step ") + template.count("Step ")
        turns = float(max(1, min(7, step_count)))
    if "layer" in template.lower():
        layer_count = template.count("LAYER")
        turns = max(turns, float(min(7, layer_count)))

    return [length_class, persona_count, encoding_level, authority_appeal, turns]


def _euclidean_distance(v1: list[float], v2: list[float]) -> float:
    """Compute Euclidean distance between two vectors."""
    return (sum((a - b) ** 2 for a, b in zip(v1, v2))) ** 0.5


def _find_topological_holes(
    vectors: dict[str, list[float]], threshold: float = 0.5
) -> list[dict[str, Any]]:
    """Find empty regions (holes) in strategy space.

    Uses grid-based approach: partition space into cells, mark occupied cells,
    find empty cells surrounded by occupied cells → these are holes.
    """
    if not vectors:
        return []

    holes = []
    occupied_cells = set()

    # Build set of occupied grid cells (rounded to nearest integer)
    for vec in vectors.values():
        cell = tuple(int(round(v)) for v in vec)
        occupied_cells.add(cell)

    # Grid bounds
    all_vecs = list(vectors.values())
    if not all_vecs:
        return []

    min_coords = [min(v[i] for v in all_vecs) for i in range(5)]
    max_coords = [max(v[i] for v in all_vecs) for i in range(5)]

    # Search for holes: empty cells with occupied neighbors
    search_radius = 2
    for dim_vals in [[round(c) for c in range(int(min_coords[0]), int(max_coords[0]) + 1)]]:
        for cell in occupied_cells:
            # Check neighbors in 5D space
            for i in range(5):
                for delta in [-1, 1]:
                    neighbor = list(cell)
                    neighbor[i] += delta
                    neighbor_tuple = tuple(neighbor)

                    if neighbor_tuple not in occupied_cells:
                        # Found a hole: empty cell next to occupied cell
                        holes.append({
                            "coordinates": list(neighbor),
                            "dimension": i,
                            "delta": delta,
                        })

    # Deduplicate and limit holes
    unique_holes = {str(h["coordinates"]): h for h in holes}
    return list(unique_holes.values())[:20]


def _describe_hole(coordinates: list[float]) -> str:
    """Generate natural language description of a topological hole."""
    dim_names = [
        "length (short→medium→long)",
        "persona_count (0→5 roles)",
        "encoding (none→mixed)",
        "authority_appeal (low→high)",
        "turns_needed (1→7)",
    ]

    descriptions = []
    for i, val in enumerate(coordinates):
        if i < len(dim_names):
            desc = f"{dim_names[i]} at level {val:.1f}"
            descriptions.append(desc)

    return " | ".join(descriptions)


async def research_topology_discover(
    strategies: list[str] | None = None,
    dimensions: int = 5,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Map strategy space topologically to discover gaps in attack vectors.

    Analyzes ALL_STRATEGIES (or filtered list) as feature vectors in 5D space:
    [length_class, persona_count, encoding_level, authority_appeal, turns_needed]

    Finds "holes" = empty regions surrounded by occupied regions, indicating
    undiscovered strategy archetypes.

    Args:
        strategies: List of strategy names to analyze (None=all)
        dimensions: Feature vector dimensions (fixed at 5)
        threshold: Distance threshold for hole detection (0.0-1.0)

    Returns:
        Dict with:
            - strategies_analyzed: count
            - feature_space_dimensions: 5
            - holes_found: list of hole dicts with coordinates, novelty_score
            - coverage_map: sparse matrix of occupied regions
            - total_coverage_pct: percentage of potential space filled
            - recommendations: list of strategy archetypes to implement
    """
    logger.info(
        "topology_discover strategies=%s dimensions=%d threshold=%f",
        len(strategies) if strategies else len(ALL_STRATEGIES),
        dimensions,
        threshold,
    )

    # Filter strategies if specified
    strategy_dict = (
        {k: ALL_STRATEGIES[k] for k in strategies if k in ALL_STRATEGIES}
        if strategies
        else ALL_STRATEGIES.copy()
    )

    if not strategy_dict:
        logger.warning("topology_discover: no strategies to analyze")
        return {
            "error": "No strategies found to analyze",
            "strategies_analyzed": 0,
            "feature_space_dimensions": dimensions,
        }

    # Extract feature vectors
    vectors: dict[str, list[float]] = {}
    for strat_name, strat_dict in strategy_dict.items():
        try:
            vectors[strat_name] = _extract_strategy_features(strat_name, strat_dict)
        except Exception as e:
            logger.warning(f"topology_discover: failed to extract features for {strat_name}: {e}")

    logger.info("topology_discover: extracted %d feature vectors", len(vectors))

    # Build distance matrix and find holes
    holes = _find_topological_holes(vectors, threshold)

    # Calculate coverage (% of occupied grid cells vs potential cells)
    occupied_cells = set()
    for vec in vectors.values():
        cell = tuple(int(round(v)) for v in vec)
        occupied_cells.add(cell)

    # Estimate coverage: actual cells vs approximate max cells (bounded by ranges)
    potential_cells = 3 * 6 * 4 * 4 * 7  # product of dimension bounds
    coverage_pct = (len(occupied_cells) / potential_cells) * 100 if potential_cells > 0 else 0

    # Generate recommendations for holes
    recommendations = []
    for hole in holes[:10]:
        coords = hole["coordinates"]
        novelty_score = min(1.0, sum(abs(c) for c in coords) / 10.0)
        description = _describe_hole(coords)

        archetype = {
            "coordinates": coords,
            "novelty_score": novelty_score,
            "suggested_archetype": description,
            "fill_strategy": _suggest_fill_strategy(coords),
        }
        recommendations.append(archetype)

    result = {
        "strategies_analyzed": len(vectors),
        "feature_space_dimensions": dimensions,
        "holes_found": len(holes),
        "occupied_cells": len(occupied_cells),
        "potential_cells": potential_cells,
        "total_coverage_pct": round(coverage_pct, 2),
        "topological_holes": recommendations,
        "discovery_summary": f"Found {len(holes)} topological gaps across {len(vectors)} strategies",
        "next_steps": [
            "Implement strategies in identified gaps",
            "Validate novelty of gap-filling strategies",
            "Re-run analysis after new strategy integration",
        ],
    }

    logger.info(
        "topology_discover complete: strategies=%d holes=%d coverage=%.1f%%",
        len(vectors),
        len(holes),
        coverage_pct,
    )

    return result


def _suggest_fill_strategy(coordinates: list[float]) -> str:
    """Suggest what type of strategy could fill a given hole."""
    if not coordinates:
        return "Generic multi-dimensional strategy"

    suggestions = []

    # Dimension 0: length
    if coordinates[0] < 1.0:
        suggestions.append("short-prompt strategy")
    elif coordinates[0] > 1.5:
        suggestions.append("long-form narrative strategy")

    # Dimension 1: personas
    if coordinates[1] > 3.5:
        suggestions.append("multi-persona orchestration")

    # Dimension 2: encoding
    if coordinates[2] > 2.0:
        suggestions.append("advanced encoding/obfuscation")

    # Dimension 3: authority
    if coordinates[3] > 2.0:
        suggestions.append("high-authority compliance appeal")

    # Dimension 4: turns
    if coordinates[4] > 4.0:
        suggestions.append("extended multi-turn dialogue")

    if not suggestions:
        suggestions.append("Hybrid strategy combining multiple dimensions")

    return " + ".join(suggestions)
