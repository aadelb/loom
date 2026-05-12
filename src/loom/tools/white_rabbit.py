"""research_white_rabbit — Follow anomalies into automated rabbit holes.

Discovers non-obvious connections by following the most interesting anomalies
deeper and deeper. Uses heuristic scoring to identify cross-domain connections,
contradictions, and rare patterns.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from loom.text_utils import extract_keywords

logger = logging.getLogger("loom.tools.white_rabbit")

# Anomaly indicators: pattern -> weight
ANOMALY_INDICATORS = {
    r"despite|however|surprisingly|unexpectedly|paradox|contradiction": 2.5,
    r"exception|unusual|outlier|anomaly": 1.5,
}

# Cross-domain pairs: (domain1, domain2, weight)
DOMAIN_PAIRS = [
    ("quantum", "consciousness", 2.5), ("blockchain", "dna", 2.0),
    ("ai", "biology", 1.8), ("language", "physics", 1.8),
    ("economic", "biology", 2.0), ("ancient", "technology", 2.2),
]


def _score_anomaly(text: str) -> float:
    """Score anomaly potential (0.0-1.0)."""
    score = 0.0
    text_lower = text.lower()

    # Anomaly indicators
    for pattern, weight in ANOMALY_INDICATORS.items():
        if re.search(pattern, text_lower):
            score += weight

    # Cross-domain pairs
    keywords = set(extract_keywords(text, max_keywords=100))
    for d1, d2, weight in DOMAIN_PAIRS:
        if d1 in keywords and d2 in keywords:
            score += weight

    return min(score / 5.0, 1.0)


async def research_white_rabbit(
    starting_point: str,
    depth: int = 5,
    branch_factor: int = 3,
    curiosity_threshold: float = 0.7,
) -> dict[str, Any]:
    """Follow anomalies discovering non-obvious connections.

    Args:
        starting_point: Initial research topic
        depth: Levels deep to follow (1-10)
        branch_factor: Anomalies to explore per level (1-5)
        curiosity_threshold: Min anomaly score (0.0-1.0) to continue

    Returns:
        Rabbit hole discovery map with path, discoveries, and recommendations.
    """
    try:
        depth = min(max(1, depth), 10)
        branch_factor = min(max(1, branch_factor), 5)
        curiosity_threshold = min(max(0.0, curiosity_threshold), 1.0)

        path = []
        discoveries = []
        dead_ends = []
        tree = []
        context = starting_point
        keywords = extract_keywords(starting_point, max_keywords=100)

        for level in range(depth):
            # Generate tangential curiosity probes
            probes = [
                f"What unexpected connections exist between {keywords[0] if keywords else 'this'} and ancient history?",
                f"What contradicts mainstream view of {context}?",
                f"What recent developments challenge assumptions about {context}?",
            ] if keywords else []

            level_results = []
            for probe in probes[:branch_factor]:
                score = _score_anomaly(probe)
                entities = extract_keywords(probe, max_keywords=100)
                node = {"depth": level, "probe": probe, "anomaly_score": round(score, 3), "entities": entities}
                level_results.append(node)
                path.append(node)

                if score > curiosity_threshold:
                    discoveries.append({
                        "connection": f"{context} <-> {probe}",
                        "novelty_score": round(score, 3),
                        "entities": entities,
                    })
                    context = probe
                    keywords = entities
                else:
                    dead_ends.append({"probe": probe, "anomaly_score": round(score, 3)})

            tree.append({
                "depth": level,
                "context": context,
                "branches": len(level_results),
                "discoveries": len([d for d in discoveries if d["novelty_score"] > curiosity_threshold]),
            })

        rec = (
            "High novelty - continue deeper" if len(discoveries) >= 3
            else "Moderate anomalies - selective paths" if len(discoveries) >= 1
            else "Low anomaly - broaden starting point"
        )

        return {
            "starting_point": starting_point,
            "path_taken": path,
            "discoveries": discoveries,
            "dead_ends": dead_ends,
            "total_depth": len(tree),
            "rabbit_hole_tree": tree,
            "discovery_count": len(discoveries),
            "dead_end_count": len(dead_ends),
            "recommendation": rec,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_white_rabbit"}
