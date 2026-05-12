"""Multi-model response comparison and consensus detection."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.model_compare")


async def research_compare_responses(
    responses: list[dict],
    comparison_type: str = "quality",
) -> dict[str, Any]:
    """Compare responses: quality/agreement/diversity metrics."""
    try:
        if not responses:
            return {"error": "No responses", "models_compared": 0, "rankings": [], "agreement_score": 0.0}

        rankings = []
        for resp in responses:
            text = resp.get("text", "")
            length = len(text)
            # Length score (500-2000 optimal)
            ls = min(100.0, (length / 1000) * 100) if length < 2000 else 100.0
            # Specificity (numbers + proper nouns)
            spec = ((len(re.findall(r"\b\d+", text)) + len(re.findall(r"\b[A-Z][a-z]+", text))) / max(1, len(text)//50)) * 10
            spec = min(100.0, spec)
            # Structure (headers + lists)
            struct = min(100.0, (len(re.findall(r"^#+\s|^[-*]\s", text, re.M)) * 10) + 50)
            # Hedging (penalty for "maybe", "might", "could", etc.)
            hedge = max(0.0, 100.0 - (len(re.findall(r"\b(maybe|might|could|possibly|perhaps)\b", text, re.I)) * 5))
            score = (ls + spec + struct + hedge) / 4

            strengths = []
            if ls > 80:
                strengths.append("Good depth")
            if spec > 70:
                strengths.append("Specific")
            if struct > 60:
                strengths.append("Well-structured")
            if hedge > 80:
                strengths.append("Confident")

            rankings.append({
                "model": resp.get("model", "unknown"),
                "score": round(score, 1),
                "strengths": strengths or ["Baseline"],
                "weaknesses": (["Too brief"] if ls < 30 else []) + (["Vague"] if spec < 30 else []),
            })

        rankings.sort(key=lambda x: x["score"], reverse=True)

        # Agreement: word overlap
        word_sets = [set(re.findall(r"\b\w{4,}\b", r.get("text", "").lower())) for r in responses]
        if word_sets:
            common = set.intersection(*word_sets)
            all_w = set.union(*word_sets)
            agree = (len(common) / len(all_w) * 100) if all_w else 0.0
        else:
            agree = 0.0

        # Unique terms per model
        unique = {}
        for i, (r, ws) in enumerate(zip(responses, word_sets)):
            others = set.union(*(word_sets[j] for j in range(len(word_sets)) if j != i), set())
            unique[r.get("model", f"m{i}")] = sorted(ws - others)[:10]

        return {
            "comparison_type": comparison_type,
            "models_compared": len(responses),
            "rankings": rankings,
            "agreement_score": round(agree, 1),
            "unique_insights_by_model": unique,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_compare_responses"}


async def research_model_consensus(
    responses: list[dict],
    threshold: float = 0.7,
) -> dict[str, Any]:
    """Find consensus claims across models.

    DEPRECATED: This tool analyzes pre-collected responses for claim consensus.
    For unified multi-model LLM consensus building with configurable methods
    (voting, debate, weighted), use research_consensus_build() from
    consensus_builder.py instead.

    Args:
        responses: List of dicts with "text" and "model" fields
        threshold: Minimum agreement threshold (0.0-1.0)

    Returns:
        Dict with consensus_claims, disputed_claims, consensus_score.
    """
    try:
        if not responses:
            return {"error": "No responses", "models_count": 0, "consensus_claims": [], "consensus_score": 0.0}

        threshold = max(0.0, min(1.0, threshold))
        n = len(responses)
        min_agree = max(1, int(n * threshold))

        # Extract assertion sentences
        claims_map: dict[str, list[int]] = {}
        for idx, resp in enumerate(responses):
            for sent in re.split(r"[.!?]+", resp.get("text", "")):
                s = sent.strip()
                if len(s) > 20 and any(kw in s.lower() for kw in
                                       ["is", "are", "was", "show", "indicate", "found", "demonstrate"]):
                    key = s.lower()
                    if key not in claims_map:
                        claims_map[key] = []
                    if idx not in claims_map[key]:
                        claims_map[key].append(idx)

        consensus, disputed = [], []
        for key, models in claims_map.items():
            conf = (len(models) / n) * 100
            entry = {"claim": key[:80].rstrip(".:").capitalize(), "models_agreeing": len(models), "confidence": round(conf, 1)}
            (consensus if len(models) >= min_agree else disputed).append(entry)

        consensus.sort(key=lambda x: x["confidence"], reverse=True)
        consensus_score = sum(c["confidence"] for c in consensus) / len(consensus) if consensus else 0.0

        return {
            "models_count": n,
            "consensus_claims": consensus[:20],
            "disputed_claims": disputed[:20],
            "consensus_score": round(consensus_score, 1),
            "threshold": threshold,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_model_consensus"}
