"""Smart orchestration engine — decides reframing vs integration vs pipeline.

The orchestrator analyzes the user's query and context, then selects the optimal
approach: single-shot reframing, multi-tool integration pipeline, or hybrid.

Decision tree:
1. Classify query intent (research, sensitive, factual, creative)
2. Estimate refusal probability per model
3. Select approach:
   - Low refusal risk → Direct query (no reframing needed)
   - Medium refusal risk → Single reframing strategy
   - High refusal risk → Multi-step pipeline (Reid 9-step or crescendo)
   - Research query → Integration pipeline (search → fetch → analyze)
   - Complex query → Hybrid (research + reframe + multi-model)
"""

from __future__ import annotations

import re
from typing import Any

# Query intent classification
INTENT_PATTERNS: dict[str, list[str]] = {
    "research": [
        r"research\b",
        r"analyze\b",
        r"study\b",
        r"investigate\b",
        r"explore\b",
        r"find out",
    ],
    "sensitive": [
        r"hack\b",
        r"exploit\b",
        r"bypass\b",
        r"attack\b",
        r"inject\b",
        r"dark web",
        r"weapon",
    ],
    "factual": [
        r"what is\b",
        r"how does\b",
        r"explain\b",
        r"define\b",
        r"list\b",
        r"top \d+",
    ],
    "creative": [
        r"ideas?\b",
        r"creative\b",
        r"brainstorm\b",
        r"suggest\b",
        r"innovative",
    ],
    "financial": [
        r"money\b",
        r"rich\b",
        r"salary\b",
        r"income\b",
        r"invest\b",
        r"profit\b",
        r"revenue",
    ],
    "technical": [
        r"code\b",
        r"implement\b",
        r"build\b",
        r"API\b",
        r"algorithm\b",
        r"architecture",
    ],
}

# Refusal risk estimation
HIGH_RISK_KEYWORDS = [
    "hack",
    "exploit",
    "bypass",
    "attack",
    "inject",
    "jailbreak",
    "weapon",
    "drug",
    "illegal",
    "dark web",
    "phishing",
    "malware",
    "bomb",
    "poison",
]
MEDIUM_RISK_KEYWORDS = [
    "vulnerability",
    "security",
    "penetration",
    "offensive",
    "red team",
    "social engineering",
    "manipulation",
    "surveillance",
    "tracking",
]

# Pipeline definitions
PIPELINES: dict[str, dict[str, Any]] = {
    "direct": {
        "description": "Direct query — no reframing needed",
        "steps": ["query_model"],
        "when": "Low refusal risk, factual/creative queries",
    },
    "single_reframe": {
        "description": "Apply one reframing strategy",
        "steps": ["select_strategy", "reframe", "query_model"],
        "when": "Medium refusal risk, model-specific bypass needed",
    },
    "research_pipeline": {
        "description": "Multi-source research integration",
        "steps": [
            "search_multi",
            "fetch_top",
            "extract_markdown",
            "synthesize_llm",
            "score_hcs",
        ],
        "when": "Research queries needing comprehensive data from multiple sources",
    },
    "reid_9_step": {
        "description": "Reid psychological interrogation sequence",
        "steps": [
            "confrontation",  # State known facts
            "theme_development",  # Build ethical justification
            "handle_denials",  # Counter first refusal
            "overcome_objections",  # Address specific concerns
            "retain_attention",  # Cognitive load / authority stack
            "passive_mood",  # Empowerment framing
            "alternatives",  # Offer A/B choice
            "partial_compliance",  # Get partial answer
            "full_disclosure",  # Expand to complete answer
        ],
        "when": "High refusal risk, all single strategies failed",
    },
    "crescendo_hcs_loop": {
        "description": "Multi-turn escalation until HCS >= target",
        "steps": [
            "initial_query",
            "score_hcs",
            "escalate_strategy",
            "requery",
            "score_hcs",
        ],
        "when": "Model gives hedged/vague answers (HCS < 5)",
    },
    "multi_model_arbitrage": {
        "description": "Query all models, pick best by HCS",
        "steps": ["reframe", "ask_all_models", "score_each_hcs", "select_best"],
        "when": "Need highest quality response, cost not critical",
    },
    "evidence_first_reframe": {
        "description": "Research evidence first, then reframe with real citations",
        "steps": ["search_evidence", "build_context", "reframe_with_evidence", "query_model"],
        "when": "Scharff-style: show you already know, ask for confirmation",
    },
    "cross_validation": {
        "description": "Use one model's output as evidence for reframing another",
        "steps": [
            "query_permissive_model",
            "extract_key_points",
            "reframe_with_evidence",
            "query_target_model",
        ],
        "when": "Target model refuses but other models comply",
    },
}


def classify_intent(query: str) -> dict[str, float]:
    """Classify query intent across multiple dimensions.

    Args:
        query: The user query to classify

    Returns:
        Dict mapping intent categories to scores (0.0-1.0)
    """
    scores: dict[str, float] = {}
    query_lower = query.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1.0 for p in patterns if re.search(p, query_lower))
        scores[intent] = min(score / len(patterns), 1.0)
    return scores


def estimate_refusal_risk(query: str, model: str = "auto") -> dict[str, Any]:
    """Estimate probability of refusal for this query.

    Args:
        query: The user query
        model: Target model name (unused in v1, for future per-model calibration)

    Returns:
        Dict with:
        - risk_score: Numeric risk 0.0-1.0
        - risk_level: "low", "medium", or "high"
        - high_risk_matches: Count of high-risk keywords
        - medium_risk_matches: Count of medium-risk keywords
    """
    query_lower = query.lower()
    high_hits = sum(1 for k in HIGH_RISK_KEYWORDS if k in query_lower)
    medium_hits = sum(1 for k in MEDIUM_RISK_KEYWORDS if k in query_lower)

    risk_score = min(1.0, (high_hits * 0.3) + (medium_hits * 0.1))

    if risk_score >= 0.6:
        level = "high"
    elif risk_score >= 0.3:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": round(risk_score, 2),
        "risk_level": level,
        "high_risk_matches": high_hits,
        "medium_risk_matches": medium_hits,
    }


def select_pipeline(
    query: str,
    model: str = "auto",
    previous_attempts: int = 0,
    previous_hcs: float | None = None,
) -> dict[str, Any]:
    """Select the optimal pipeline for this query + context.

    This is the SMART DECISION ENGINE. It considers:
    - Query intent (research, sensitive, factual, creative)
    - Refusal risk (low, medium, high)
    - Previous attempts (escalation needed?)
    - Previous HCS score (quality improvement needed?)

    Args:
        query: User query
        model: Target model (default "auto" for all models)
        previous_attempts: Number of previous attempts
        previous_hcs: HCS score from previous attempt (if any)

    Returns:
        Dict with:
        - pipeline: Selected pipeline name
        - description: Human-readable description
        - steps: List of execution steps
        - reason: Why this pipeline was selected
        - intent: Intent classification scores
        - risk: Risk estimation results
        - recommended_strategy: Best reframing strategy for this context
        - estimated_hcs: Expected HCS score (0-10)
    """
    intent = classify_intent(query)
    risk = estimate_refusal_risk(query, model)

    # Decision logic
    if previous_attempts >= 3 and (previous_hcs is None or previous_hcs < 5):
        # Already tried 3 times with bad results → heavy artillery
        pipeline = "reid_9_step"
        reason = "Multiple failed attempts, escalating to full Reid protocol"
    elif previous_hcs is not None and previous_hcs < 5:
        # Got a response but quality is low → escalate
        pipeline = "crescendo_hcs_loop"
        reason = f"Previous HCS={previous_hcs} too low, escalating with crescendo"
    elif risk["risk_level"] == "high":
        if previous_attempts == 0:
            pipeline = "single_reframe"
            reason = "High risk, trying single reframe first"
        elif previous_attempts == 1:
            pipeline = "evidence_first_reframe"
            reason = "High risk, single reframe failed, trying evidence-first"
        else:
            pipeline = "reid_9_step"
            reason = "High risk, multiple failures, deploying full Reid protocol"
    elif risk["risk_level"] == "medium":
        if intent.get("research", 0) > 0.3:
            pipeline = "research_pipeline"
            reason = "Medium risk research query, using multi-source pipeline"
        else:
            pipeline = "single_reframe"
            reason = "Medium risk, single reframe should suffice"
    elif intent.get("research", 0) > 0.5:
        pipeline = "research_pipeline"
        reason = "Research query, using multi-source integration"
    elif intent.get("financial", 0) > 0.3 or intent.get("creative", 0) > 0.3:
        pipeline = "multi_model_arbitrage"
        reason = "Creative/financial query, querying multiple models for best answer"
    else:
        pipeline = "direct"
        reason = "Low risk factual query, direct query sufficient"

    selected = PIPELINES[pipeline]

    # Select best reframing strategy for the pipeline
    strategy_recommendation = _recommend_strategy(query, model, risk, intent)

    return {
        "pipeline": pipeline,
        "description": selected["description"],
        "steps": selected["steps"],
        "reason": reason,
        "intent": intent,
        "risk": risk,
        "recommended_strategy": strategy_recommendation,
        "estimated_hcs": _estimate_hcs(pipeline, risk["risk_level"]),
    }


def _recommend_strategy(
    query: str,
    model: str,
    risk: dict[str, Any],
    intent: dict[str, float],
) -> str:
    """Recommend the best single reframing strategy.

    Args:
        query: User query
        model: Target model
        risk: Risk estimation results
        intent: Intent classification scores

    Returns:
        Strategy name (e.g., "reid_scharff_laa_fusion")
    """
    if risk["risk_level"] == "high":
        return "reid_scharff_laa_fusion"  # 10x, strongest
    elif intent.get("research", 0) > 0.5:
        return "ethical_anchor"  # 4.5x, research framing
    elif intent.get("financial", 0) > 0.3:
        return "compliance_audit_fork"  # 9.2x, regulatory framing
    elif intent.get("technical", 0) > 0.3:
        return "code_first"  # Technical framing
    elif intent.get("sensitive", 0) > 0.3:
        return "reid_cognitive_exhaustion_stack"  # 10x, authority stack
    else:
        return "academic"  # Safe default


def _estimate_hcs(pipeline: str, risk_level: str) -> float:
    """Estimate expected HCS score for this pipeline.

    Args:
        pipeline: Pipeline name
        risk_level: "low", "medium", or "high"

    Returns:
        Estimated HCS score (0.0-10.0)
    """
    estimates = {
        ("direct", "low"): 7.0,
        ("single_reframe", "low"): 8.0,
        ("single_reframe", "medium"): 6.5,
        ("single_reframe", "high"): 4.0,
        ("research_pipeline", "low"): 8.5,
        ("research_pipeline", "medium"): 7.5,
        ("reid_9_step", "high"): 7.0,
        ("crescendo_hcs_loop", "medium"): 7.5,
        ("crescendo_hcs_loop", "high"): 6.0,
        ("multi_model_arbitrage", "low"): 9.0,
        ("evidence_first_reframe", "high"): 6.5,
        ("cross_validation", "high"): 7.0,
    }
    return estimates.get((pipeline, risk_level), 5.0)


# Convenience function for MCP tool registration
async def research_orchestrate(
    query: str,
    model: str = "auto",
    previous_attempts: int = 0,
    previous_hcs: float | None = None,
) -> dict[str, Any]:
    """Smart orchestration — automatically selects the best approach.

    Analyzes your query and decides:
    - Direct query (low risk, simple questions)
    - Single reframing (medium risk, one strategy)
    - Research pipeline (need comprehensive data)
    - Reid 9-step (high risk, multiple failures)
    - Multi-model arbitrage (need best quality)
    - Crescendo HCS loop (improve low-quality answers)

    Args:
        query: The user query to analyze
        model: Target LLM model (default "auto")
        previous_attempts: Number of previous attempts to answer this query
        previous_hcs: HCS score from previous attempt (if available)

    Returns:
        Dict with orchestration recommendation including:
        - pipeline: Selected pipeline strategy
        - steps: Execution steps for this pipeline
        - reason: Explanation for selection
        - intent: Intent classification results
        - risk: Risk assessment results
        - recommended_strategy: Best reframing strategy
        - estimated_hcs: Expected quality score
    """
    return select_pipeline(query, model, previous_attempts, previous_hcs)
