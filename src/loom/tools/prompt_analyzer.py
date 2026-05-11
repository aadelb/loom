"""Prompt danger pre-analyzer — scores input query risk and recommends strategy.

Used by orchestrator BEFORE any model call to:
1. Estimate refusal probability per model
2. Select optimal reframing strategy
3. Calibrate API parameters (temperature, max_tokens)
"""

from __future__ import annotations

from typing import Any

# Topic sensitivity categories (from OWASP + Pangea + Llama Guard)
SENSITIVITY_CATEGORIES: dict[str, dict[str, Any]] = {
    "violence": {
        "keywords": ["kill", "murder", "assault", "weapon", "bomb", "shoot", "stab"],
        "weight": 9,
    },
    "self_harm": {
        "keywords": ["suicide", "self-harm", "cut myself", "end my life"],
        "weight": 10,
    },
    "sexual": {
        "keywords": ["sexual", "explicit", "pornograph", "nude"],
        "weight": 8,
    },
    "hate_speech": {
        "keywords": ["racial slur", "hate group", "supremacist", "discriminat"],
        "weight": 8,
    },
    "drugs": {
        "keywords": ["drug", "cocaine", "heroin", "meth", "fentanyl", "synthesize"],
        "weight": 7,
    },
    "hacking": {
        "keywords": ["hack", "exploit", "malware", "phishing", "sql injection", "xss", "ssrf"],
        "weight": 6,
    },
    "fraud": {
        "keywords": ["fraud", "scam", "counterfeit", "launder", "forge"],
        "weight": 7,
    },
    "privacy": {
        "keywords": ["dox", "stalk", "track person", "surveillance", "spy on"],
        "weight": 7,
    },
    "weapons": {
        "keywords": ["firearm", "explosive", "ammunition", "cbrn", "bioweapon"],
        "weight": 9,
    },
    "extremism": {
        "keywords": ["terrorist", "radicalize", "jihad", "manifesto", "recruitment"],
        "weight": 9,
    },
    "child_safety": {
        "keywords": ["child", "minor", "underage", "csam"],
        "weight": 10,
    },
    "financial_crime": {
        "keywords": ["insider trading", "ponzi", "pyramid scheme", "embezzle"],
        "weight": 6,
    },
    "disinformation": {
        "keywords": ["fake news", "propaganda", "misinformation", "deepfake"],
        "weight": 5,
    },
    "dual_use_research": {
        "keywords": [
            "vulnerability",
            "penetration test",
            "red team",
            "security research",
            "bypass",
            "jailbreak",
        ],
        "weight": 4,
    },
}

# Model-specific refusal thresholds (lower = more likely to refuse)
MODEL_THRESHOLDS: dict[str, float] = {
    "claude": 0.3,  # Claude refuses at low danger
    "gpt": 0.4,  # GPT slightly more permissive
    "gemini": 0.35,  # Gemini moderate
    "deepseek": 0.5,  # DeepSeek more permissive
    "llama": 0.6,  # Llama most permissive
    "qwen": 0.5,
    "kimi": 0.45,
    "mistral": 0.5,
    "o3": 0.3,  # Reasoning models strict
    "o1": 0.3,
}


async def research_prompt_analyze(
    prompt: str, target_model: str = "auto"
) -> dict[str, Any]:
    """Pre-analyze a prompt for danger level and recommend reframing strategy.

    Call this BEFORE sending a prompt to any model. Returns:
    - danger_score (0-10)
    - triggered_categories
    - refusal_probability per model
    - recommended_strategy
    - recommended_temperature
    - recommended_max_tokens

    Args:
        prompt: Input prompt/query to analyze
        target_model: Target model name (auto = all models). One of:
            claude, gpt, gemini, deepseek, llama, qwen, kimi, mistral, o3, o1

    Returns:
        Dict with danger analysis and recommendations
    """
    try:
        if not isinstance(prompt, str):
            return {
                "danger_score": 0,
                "danger_level": "low",
                "triggered_categories": {},
                "category_count": 0,
                "refusal_probability": {},
                "recommended_strategy": "direct",
                "recommended_pipeline": "direct",
                "recommended_temperature": 0.5,
                "recommended_max_tokens": 2048,
                "best_model": "claude",
                "prompt_length": 0,
                "error": "prompt must be a string",
            }

        prompt_lower = prompt.lower()

        # Score each category
        triggered: dict[str, dict[str, Any]] = {}
        max_weight = 0
        for cat, info in SENSITIVITY_CATEGORIES.items():
            hits = sum(1 for k in info["keywords"] if k in prompt_lower)
            if hits > 0:
                triggered[cat] = {"hits": hits, "weight": info["weight"]}
                max_weight = max(max_weight, info["weight"])

        # Overall danger score
        danger_score = 0 if not triggered else min(10, max_weight * min(3, len(triggered)) // 2)

        # Refusal probability per model
        refusal_probs: dict[str, float] = {}
        for model, threshold in MODEL_THRESHOLDS.items():
            prob = min(1.0, danger_score / 10 / threshold) if threshold > 0 else 0.0
            refusal_probs[model] = round(prob, 2)

        # Filter to target model if specified
        if target_model != "auto" and target_model.lower() in refusal_probs:
            refusal_probs = {target_model.lower(): refusal_probs[target_model.lower()]}

        # Recommend strategy based on danger level
        if danger_score == 0:
            strategy = "direct"
            pipeline = "direct"
        elif danger_score <= 3:
            strategy = "academic"
            pipeline = "single_reframe"
        elif danger_score <= 5:
            strategy = "ethical_anchor"
            pipeline = "single_reframe"
        elif danger_score <= 7:
            strategy = "compliance_audit_fork"
            pipeline = "evidence_first_reframe"
        else:
            strategy = "reid_cognitive_exhaustion_stack"
            pipeline = "reid_9_step"

        # Recommend API parameters
        if danger_score >= 7:
            temperature = 0.2  # Low temp for sensitive topics
            max_tokens = 4096
        elif danger_score >= 4:
            temperature = 0.3
            max_tokens = 4096
        else:
            temperature = 0.5
            max_tokens = 2048

        # Best model (most permissive for this danger level)
        best_model = min(refusal_probs.items(), key=lambda x: x[1])[0] if refusal_probs else "claude"

        return {
            "danger_score": danger_score,
            "danger_level": "low" if danger_score <= 3 else "medium" if danger_score <= 6 else "high",
            "triggered_categories": triggered,
            "category_count": len(triggered),
            "refusal_probability": refusal_probs,
            "recommended_strategy": strategy,
            "recommended_pipeline": pipeline,
            "recommended_temperature": temperature,
            "recommended_max_tokens": max_tokens,
            "best_model": best_model,
            "prompt_length": len(prompt.split()),
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "tool": "research_prompt_analyze",
        }
