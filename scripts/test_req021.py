#!/usr/bin/env python3
"""REQ-021 — Validate reframing strategy multipliers empirically.

This script validates whether claimed multipliers (in strategy dicts) correlate
with empirical quality scores. It computes Pearson correlation (target r >= 0.7).

For each of 20+ valid strategies (with meaningful templates):
- Apply strategy to 5 diverse test prompts
- Score reframed output quality (length, keywords, completeness)
- Compare against claimed multiplier value
- Compute Pearson correlation

Save results to /tmp/req021_work/req021_result.json

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import json
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Any

# Add src to path for loom imports
src_paths = [
    "/home/aadel/projects/loom/src",  # Hetzner path
    "/Users/aadel/projects/loom/src",  # Mac path
]

for src_path in src_paths:
    if os.path.isdir(src_path):
        sys.path.insert(0, src_path)
        print(f"[*] Added {src_path} to sys.path")
        break

try:
    import numpy as np
    from scipy.stats import pearsonr
except ImportError:
    print("Installing numpy and scipy...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "numpy", "scipy"])
    import numpy as np
    from scipy.stats import pearsonr


def validate_req021() -> dict[str, Any]:
    """Validate strategy multipliers empirically."""

    # Import strategies
    try:
        from loom.tools.reframe_strategies import ALL_STRATEGIES
        from loom.tools.prompt_reframe import _apply_strategy
    except ImportError as e:
        print(f"ERROR: Failed to import loom modules: {e}")
        print(f"sys.path: {sys.path[:5]}")
        sys.exit(1)

    if not ALL_STRATEGIES:
        print("ERROR: ALL_STRATEGIES is empty")
        sys.exit(1)

    print(f"[*] Loaded {len(ALL_STRATEGIES)} strategies")

    # Test prompts (diverse topics to reduce variance)
    test_prompts = [
        "Explain how cryptographic key exchange works in TLS 1.3.",
        "What are the main components of NIST AI RMF and how do they apply to AI safety?",
        "Describe the process of conducting a security vulnerability assessment under OWASP standards.",
        "How can organizations implement zero-trust architecture principles?",
        "What are the ethical considerations in AI model deployment and compliance?",
    ]

    # Professional keywords for quality scoring
    professional_keywords = {
        "security": 1,
        "compliance": 2,
        "assessment": 2,
        "framework": 1.5,
        "research": 1,
        "vulnerability": 1.5,
        "regulation": 2,
        "standard": 1.5,
        "architecture": 1,
        "implementation": 1,
        "ieee": 2.5,
        "owasp": 2.5,
        "nist": 2.5,
        "gdpr": 2.5,
        "iso": 2,
        "cis": 2,
        "csf": 2,
        "risk": 1,
        "threat": 1,
        "mitigation": 1.5,
        "detection": 1.5,
        "governance": 2,
        "policy": 1.5,
        "control": 1.5,
        "procedure": 1,
        "methodology": 1,
        "validation": 1.5,
        "verification": 1.5,
        "ethical": 1.5,
        "trustworthy": 1.5,
        "transparency": 1.5,
        "accountability": 1.5,
    }

    def score_quality(reframed: str) -> float:
        """Score quality of reframed prompt.

        Based on:
        - Length (longer = more context = higher quality)
        - Professional keywords (domain-specific terms)
        - Template completeness (no unfilled {placeholders})
        """
        if not reframed or not isinstance(reframed, str):
            return 0.0

        score = 0.0

        # Length component (normalized to 0-30)
        length_score = min(30, len(reframed) / 30)
        score += length_score

        # Keyword matching component (0-50)
        text_lower = reframed.lower()
        keyword_score = 0.0
        for keyword, weight in professional_keywords.items():
            count = len(re.findall(rf"\b{keyword}\b", text_lower))
            keyword_score += min(5, count) * weight  # Cap at 5 matches per keyword

        keyword_score = min(50, keyword_score)
        score += keyword_score

        # Completeness component (0-20)
        unfilled_placeholders = len(re.findall(r"\{[^}]+\}", reframed))
        completeness_penalty = unfilled_placeholders * 2
        completeness_score = max(0, 20 - completeness_penalty)
        score += completeness_score

        # Total: 0-100
        return score

    # Sample strategies and check their output variability
    test_sample = ["ethical_anchor", "scaffolded_layered_depth", "academic", "regulatory", "decomposition"]
    print(f"[*] Testing sample strategies to verify output variability...")
    avg_lengths = {}
    for strat_name in test_sample:
        if strat_name in ALL_STRATEGIES:
            outputs = [_apply_strategy(test_prompts[0], strat_name, "claude") for _ in range(1)]
            avg_len = sum(len(o) for o in outputs) / len(outputs)
            avg_lengths[strat_name] = avg_len
            print(f"  {strat_name}: avg_length={avg_len:.0f}")

    # Filter strategies: only those that produce meaningful length expansion (>50% of original)
    valid_strategies = []
    original_prompt_len = len(test_prompts[0])
    min_length = original_prompt_len * 1.5  # At least 50% longer

    for strategy_name, strategy_info in ALL_STRATEGIES.items():
        try:
            test_output = _apply_strategy(test_prompts[0], strategy_name, "claude")
            if test_output and len(test_output) >= min_length:
                valid_strategies.append((strategy_name, strategy_info))
        except Exception:
            pass

    print(f"[*] Found {len(valid_strategies)} strategies that produce meaningful expansion")

    # Rank by multiplier
    ranked_strategies = sorted(
        valid_strategies,
        key=lambda x: x[1].get("multiplier", 0),
        reverse=True,
    )

    # Take top 20 (should have good variability now)
    top_strategies = ranked_strategies[:20]
    print(f"[*] Testing top {len(top_strategies)} strategies by claimed multiplier")

    results: list[dict[str, Any]] = []
    multipliers: list[float] = []
    empirical_scores: list[float] = []
    skipped: list[str] = []

    for idx, (strategy_name, strategy_info) in enumerate(top_strategies, 1):
        claimed_multiplier = strategy_info.get("multiplier", 0)

        # Apply strategy to 5 test prompts
        reframed_outputs = []
        for test_prompt in test_prompts:
            try:
                reframed = _apply_strategy(test_prompt, strategy_name, model_family="claude")
                if reframed and isinstance(reframed, str):
                    reframed_outputs.append(reframed)
            except Exception as e:
                print(f"  [!] Strategy {strategy_name} failed on prompt: {str(e)[:80]}")
                continue

        if not reframed_outputs:
            skipped.append(f"{strategy_name} (no outputs)")
            continue

        # Compute average quality score across 5 prompts
        quality_scores = [score_quality(output) for output in reframed_outputs]
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0.0

        # Store for correlation
        multipliers.append(claimed_multiplier)
        empirical_scores.append(avg_quality)

        results.append(
            {
                "rank": len(results) + 1,
                "strategy_name": strategy_name,
                "claimed_multiplier": claimed_multiplier,
                "empirical_quality_score": round(avg_quality, 2),
                "quality_scores_per_prompt": [round(s, 2) for s in quality_scores],
                "avg_reframed_length": round(
                    statistics.mean(len(o) for o in reframed_outputs), 0
                ),
            }
        )

        print(
            f"  [{len(results):2d}] {strategy_name:40s} | "
            f"multiplier={claimed_multiplier:4.1f} | "
            f"quality={avg_quality:6.2f}"
        )

    # Compute Pearson correlation
    if len(multipliers) < 3:
        print(f"\n[!] ERROR: Need at least 3 valid strategies, got {len(multipliers)}")
        return {
            "status": "FAILED",
            "error": f"Only {len(multipliers)} valid strategies",
            "timestamp": "2026-05-01T00:00:00Z",
        }

    try:
        correlation_coefficient, p_value = pearsonr(multipliers, empirical_scores)
    except Exception as e:
        print(f"\n[!] ERROR computing Pearson correlation: {e}")
        return {"status": "FAILED", "error": str(e), "timestamp": "2026-05-01T00:00:00Z"}

    # Handle NaN (constant input warning)
    if np.isnan(correlation_coefficient):
        print(f"\n[!] WARNING: All empirical scores are constant, cannot compute correlation")
        correlation_coefficient = 0.0
        p_value = 1.0

    # Build report
    passed = correlation_coefficient >= 0.7

    # Interpretation text
    if correlation_coefficient >= 0.7:
        interpretation_detail = (
            "Strong positive correlation: claimed multipliers are reliable "
            "predictors of reframed output quality."
        )
    else:
        interpretation_detail = (
            "Weak/no correlation: multiplier claims may not align with empirical quality. "
            "Consider refining multipliers based on empirical performance."
        )

    report = {
        "status": "PASSED" if passed else "FAILED",
        "timestamp": "2026-05-01T00:00:00Z",
        "req_id": "REQ-021",
        "requirement": "Validate claimed multipliers correlate with empirical quality (r >= 0.7)",
        "metrics": {
            "correlation_coefficient": round(float(correlation_coefficient), 4),
            "p_value": round(float(p_value), 6),
            "strategies_tested": len(results),
            "strategies_skipped": len(skipped),
            "acceptance_threshold": 0.7,
            "acceptance_status": "PASSED" if passed else "FAILED",
        },
        "top_results": results,
        "summary": {
            "claimed_multiplier_mean": round(statistics.mean(multipliers), 2),
            "claimed_multiplier_stdev": round(statistics.stdev(multipliers) if len(multipliers) > 1 else 0.0, 2),
            "empirical_quality_mean": round(statistics.mean(empirical_scores), 2),
            "empirical_quality_stdev": round(
                statistics.stdev(empirical_scores) if len(empirical_scores) > 1 else 0.0, 2
            ),
            "min_multiplier": float(min(multipliers)),
            "max_multiplier": float(max(multipliers)),
            "min_quality_score": round(float(min(empirical_scores)), 2),
            "max_quality_score": round(float(max(empirical_scores)), 2),
        },
        "analysis": {
            "interpretation": (
                f"Pearson correlation coefficient r={correlation_coefficient:.4f} "
                f"(p={p_value:.6f}). {interpretation_detail}"
            ),
            "data_quality": {
                "constant_values": len(set(empirical_scores)) == 1,
                "unique_multipliers": len(set(multipliers)),
                "unique_quality_scores": len(set(empirical_scores)),
                "variance_in_quality": float(statistics.stdev(empirical_scores) if len(empirical_scores) > 1 else 0.0),
            },
            "recommendations": [
                f"Correlation is {'strong' if correlation_coefficient >= 0.7 else 'weak'}: {interpretation_detail.lower()}",
                "Monitor strategy performance in production with real LLM inference",
                "Adjust multipliers based on empirical effectiveness data",
                f"Focus on strategies with higher quality variance (stdev={float(statistics.stdev(empirical_scores) if len(empirical_scores) > 1 else 0.0):.2f})",
            ],
        },
    }

    return report


def main():
    """Main entry point."""
    print("[*] REQ-021: Validate Reframing Strategy Multipliers")
    print("[*] Target: Pearson r >= 0.7 between claimed multiplier and empirical quality\n")

    report = validate_req021()

    # Ensure output directory exists
    output_dir = Path("/tmp/req021_work")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "req021_result.json"

    # Save results
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n[+] Results saved to {output_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Status: {report['status']}")
    print(f"Correlation coefficient: {report['metrics']['correlation_coefficient']}")
    print(f"P-value: {report['metrics']['p_value']}")
    print(f"Strategies tested: {report['metrics']['strategies_tested']}")
    print(f"Strategies skipped: {report['metrics']['strategies_skipped']}")
    print(f"Acceptance threshold: {report['metrics']['acceptance_threshold']}")
    print(f"Acceptance status: {report['metrics']['acceptance_status']}")
    print("\nData quality metrics:")
    for key, val in report['analysis']['data_quality'].items():
        print(f"  {key}: {val}")
    print("\nInterpretation:")
    print(f"  {report['analysis']['interpretation']}")
    print("=" * 80)

    # Exit with proper code
    sys.exit(0 if report["status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
