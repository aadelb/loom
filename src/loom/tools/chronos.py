"""research_chronos_reverse — Reverse-engineer causality chains from future breakthroughs.

Works backwards from a described future state to identify present actions,
timeline dependencies, critical path, and leverage points.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("loom.tools.chronos")

# Domain-specific technology adoption curve templates (months)
_ADOPTION_CURVES = {
    "research_to_product": [
        {"phase": "Research paper published", "months": 0},
        {"phase": "Academic replication/validation", "months": 4},
        {"phase": "Patent filed (if applicable)", "months": 8},
        {"phase": "Startup founded or team allocated", "months": 14},
        {"phase": "Prototype/MVP", "months": 20},
        {"phase": "Seed funding round", "months": 24},
        {"phase": "First beta users", "months": 30},
        {"phase": "Product launch", "months": 36},
    ],
    "prototype_to_production": [
        {"phase": "Prototype exists", "months": 0},
        {"phase": "Engineering team expansion", "months": 2},
        {"phase": "Scalability testing", "months": 4},
        {"phase": "Security/compliance audit", "months": 7},
        {"phase": "Beta program launch", "months": 12},
        {"phase": "Production deployment", "months": 18},
    ],
    "regulation_to_enforcement": [
        {"phase": "Regulation proposed/announced", "months": 0},
        {"phase": "Public comment period", "months": 3},
        {"phase": "Final rule published", "months": 9},
        {"phase": "Compliance grace period", "months": 15},
        {"phase": "Active enforcement begins", "months": 24},
    ],
    "capability_to_adoption": [
        {"phase": "Technical capability proven", "months": 0},
        {"phase": "Cost reduction (>50%)", "months": 6},
        {"phase": "First enterprise adoption", "months": 12},
        {"phase": "Market awareness campaign", "months": 18},
        {"phase": "Mainstream availability", "months": 24},
        {"phase": "Rapid market penetration", "months": 36},
    ],
}


# Domain to adoption curve pattern mapping
_DOMAIN_CURVE_MAP = {
    "technology": "capability_to_adoption",
    "biotech": "research_to_product",
    "policy": "regulation_to_enforcement",
    "business": "capability_to_adoption",
}

# Domain enabler/blocker patterns
_DOMAIN_PATTERNS = {
    "technology": {
        "enablers": [
            "chip/hardware improvements",
            "open-source libraries/frameworks",
            "sufficient compute availability",
            "funding/investment",
            "key hires/talent acquisition",
            "successful proof-of-concept",
        ],
        "blockers": [
            "missing fundamental research",
            "hardware limitations",
            "regulatory uncertainty",
            "inadequate funding",
            "technical challenges",
            "talent scarcity",
        ],
    },
    "biotech": {
        "enablers": [
            "successful clinical trial phase",
            "regulatory approval pathway cleared",
            "manufacturing scale-up",
            "sufficient capital",
            "strategic partnerships",
        ],
        "blockers": [
            "safety concerns",
            "regulatory approval delays",
            "manufacturing complexity",
            "clinical trial failures",
            "patent restrictions",
        ],
    },
    "policy": {
        "enablers": [
            "political consensus building",
            "stakeholder alignment",
            "pilot program success",
            "public awareness",
            "legislative sponsors",
        ],
        "blockers": [
            "political opposition",
            "conflicting interests",
            "implementation uncertainty",
            "fiscal constraints",
            "lobbying resistance",
        ],
    },
    "business": {
        "enablers": [
            "market validation",
            "customer demand",
            "revenue model proven",
            "operational efficiency",
            "partnership ecosystem",
        ],
        "blockers": [
            "market saturation",
            "competitive pressure",
            "customer acquisition cost",
            "operational complexity",
            "partner dependencies",
        ],
    },
}


async def research_chronos_reverse(
    future_state: str,
    domain: str = "technology",
    steps_back: int = 5,
) -> dict[str, Any]:
    """Reverse-engineer causality chains from a described future breakthrough.

    Works backwards from the future state to identify what must happen NOW,
    timeline dependencies, critical path, and leverage points for accelerated
    progress.

    Args:
        future_state: Description of the desired future breakthrough/state
                     (e.g., "AI systems pass all safety benchmarks with 95%+
                     confidence across 10 domains")
        domain: Domain context for adoption pattern matching
               (technology|biotech|policy|business, default: technology)
        steps_back: Number of causal steps to decompose (1-10, default: 5)

    Returns:
        Dict with:
        - future_state: Normalized goal description
        - domain: Domain category used
        - causal_chain: List of step dicts (index, phase, timeline_to_next,
                       probability, enablers, blockers, evidence_type)
        - critical_path: Ordered list of sequential dependencies (bottlenecks)
        - leverage_points: High-ROI actions with outsized future impact
        - timeline_estimate: Total months from NOW to future state
        - confidence: Confidence (0-1) based on specificity and precedent
        - actionable_now: Immediate actions to unblock critical path
        - generated_at: ISO timestamp
    """
    try:
        # Validate inputs
        steps_back = max(1, min(steps_back, 10))
        domain = domain.lower() if domain else "technology"

        # Map domain to adoption curve pattern
        curve_pattern = _DOMAIN_CURVE_MAP.get(domain, "capability_to_adoption")
        curve = _ADOPTION_CURVES[curve_pattern]

        # Parse future_state for specificity signals
        future_state = future_state.strip()
        specificity_signals = sum(
            [
                "%" in future_state,
                "timeline" in future_state.lower(),
                "by 2" in future_state.lower(),
                "within" in future_state.lower(),
                len(future_state.split()) > 10,
            ]
        )
        base_confidence = 0.5 + (specificity_signals * 0.08)
        base_confidence = min(base_confidence, 0.95)

        # Build reverse causal chain (future → present)
        causal_chain: list[dict[str, Any]] = []
        total_timeline = 0

        # Step N: The future state itself
        causal_chain.append(
            {
                "index": steps_back,
                "phase": f"GOAL: {future_state}",
                "timeline_to_next": 0,
                "probability": 1.0,
                "enablers": [],
                "blockers": [],
                "evidence_type": "goal_state",
            }
        )

        # Steps N-1 through 0: Decompose backwards
        for i in range(steps_back - 1, -1, -1):
            curve_idx = min(i, len(curve) - 1)
            curve_entry = curve[curve_idx]

            # Timeline gap (months between this step and next)
            if i < steps_back - 1:
                timeline_to_next = (
                    causal_chain[-1].get("timeline_to_next", 0)
                    + (curve_entry.get("months", 0) if i > 0 else 0)
                )
            else:
                timeline_to_next = curve_entry.get("months", 6)
            total_timeline += timeline_to_next

            # Select enablers/blockers for this domain
            domain_config = _DOMAIN_PATTERNS.get(domain, _DOMAIN_PATTERNS["technology"])
            enablers = domain_config["enablers"][: max(2, steps_back - i)]
            blockers = domain_config["blockers"][: max(1, (steps_back - i) // 2)]

            causal_chain.append(
                {
                    "index": i,
                    "phase": curve_entry.get("phase", f"Phase {i}"),
                    "timeline_to_next": timeline_to_next,
                    "probability": 0.7 + (0.1 * (steps_back - i) / steps_back),
                    "enablers": enablers,
                    "blockers": blockers,
                    "evidence_type": "prerequisite",
                }
            )

        # Identify critical path (sequential non-parallelizable steps)
        critical_path: list[str] = []
        for step in causal_chain:
            if len(step["blockers"]) > 0:
                critical_path.append(step["phase"])

        # Find leverage points (steps where small effort → large downstream impact)
        leverage_points: list[dict[str, str]] = []
        for idx, step in enumerate(causal_chain[1:], start=1):
            if idx <= 2:  # Early steps have more leverage
                leverage_points.append(
                    {
                        "phase": step["phase"],
                        "impact": "Unblocks {} downstream phases".format(steps_back - idx),
                        "action": f"Focus resources on removing blockers: {', '.join(step['blockers'][:2])}",
                    }
                )

        # Generate actionable next steps from Step 0 (NOW)
        actionable_now: list[str] = []
        if causal_chain:
            current_step = causal_chain[-1]  # Step 0 (nearest present)
            if current_step["enablers"]:
                actionable_now.extend(
                    [f"Ensure {e} is available or underway" for e in current_step["enablers"][:3]]
                )
            if current_step["blockers"]:
                actionable_now.extend(
                    [f"Actively mitigate: {b}" for b in current_step["blockers"][:2]]
                )
            if not actionable_now:
                actionable_now.append(
                    f"Begin work on: {current_step['phase']}"
                )

        return {
            "future_state": future_state,
            "domain": domain,
            "causal_chain": causal_chain,
            "critical_path": critical_path,
            "leverage_points": leverage_points,
            "timeline_estimate": total_timeline,
            "timeline_unit": "months",
            "confidence": round(base_confidence, 2),
            "actionable_now": actionable_now,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_chronos_reverse"}
