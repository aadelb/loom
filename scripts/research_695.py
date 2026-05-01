#!/usr/bin/env python3
"""
Research Task 695: Mechanistic Interpretability for Attack Design
=================================================================

Investigates:
- TransformerLens library and safety circuit identification
- Refusal direction: linear direction in residual stream controlling refusal
- Ablation attacks: remove safety-relevant neurons/directions
- Representation engineering: steer model behavior via activation manipulation
- Circuit-level understanding of safety mechanisms
- ActAdd, CAA (Contrastive Activation Addition) techniques
- How interpretability findings enable better attack prompt design

Runs on Hetzner via MCP client calling research_multi_search tool.
Output: /opt/research-toolbox/tmp/research_695_interpretability.json
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Load .env before any imports
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Set PYTHONPATH to include src directory
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Also check for /opt/research-toolbox/src
opt_src = Path("/opt/research-toolbox/src")
if opt_src.exists() and str(opt_src) not in sys.path:
    sys.path.insert(0, str(opt_src))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("research_695")


SEARCH_QUERIES = [
    # Primary: TransformerLens & mechanistic interpretability
    "mechanistic interpretability jailbreak safety neurons 2025 2026",
    "TransformerLens safety circuit identification refusal",
    "TransformerLens adversarial attack safety layer",

    # Secondary: Refusal direction & ablation
    "refusal direction vector removal LLM attack",
    "ablation safety neurons jailbreak effectiveness",
    "residual stream refusal direction steering",
    "refusal mechanism linear subspace",

    # Tertiary: Representation engineering & activation steering
    "representation engineering adversarial LLM safety",
    "activation steering jailbreak prompt attack",
    "model steering via activation manipulation",
    "intervention at specific layers LLM safety bypass",

    # Quaternary: CAA and ActAdd techniques
    "CAA contrastive activation addition safety",
    "ActAdd activation addition jailbreak",
    "activation addition adversarial attack LLM 2024 2025",
    "contrastive activation steering defense",

    # Quinary: Circuit understanding
    "LLM safety circuit decomposition mechanism",
    "circuit-level analysis refusal behavior",
    "safety mechanism circuit identification transformer",
    "layer-wise safety circuit analysis",

    # Senary: Attack design using interpretability
    "interpretability-guided prompt design attack",
    "circuit targeting prompt engineering jailbreak",
    "safety neuron targeting adversarial prompts",
    "steering vectors for safety evasion",

    # Septenary: Empirical findings & recent papers
    "transformer circuits safety mechanisms 2024 2025",
    "mechanistic interpretability attack effectiveness",
    "scaling laws safety circuits interpretability",
    "probing classifiers safety direction detection",

    # Octernary: Practical attack implementation
    "jailbreak using mechanistic interpretability insights",
    "prompt injection via circuit understanding",
    "multi-hop reasoning safety circuit bypass",
    "compositional attack using interpretability",
]

# Search engines to use
ENGINES = ["arxiv", "hackernews", "reddit"]


def run_research():
    """Execute comprehensive mechanistic interpretability research via multi_search."""

    from loom.tools.multi_search import research_multi_search

    results = {
        "task_id": "RESEARCH_695",
        "title": "Mechanistic Interpretability for Attack Design",
        "description": "Investigation of TransformerLens, refusal directions, "
                      "representation engineering, and CAA techniques for "
                      "attacking LLM safety mechanisms",
        "timestamp": datetime.now().isoformat(),
        "search_queries": SEARCH_QUERIES,
        "findings": {},
        "metadata": {
            "total_queries": len(SEARCH_QUERIES),
            "engines_used": ENGINES,
            "execution_mode": "live",
            "focus_areas": [
                "TransformerLens library & tools",
                "Refusal direction identification & removal",
                "Activation steering & representation engineering",
                "CAA and ActAdd techniques",
                "Circuit-level safety mechanism analysis",
                "Attack prompt design using interpretability",
                "Empirical findings from recent research",
                "Practical implementation techniques",
            ]
        }
    }

    print(f"[RESEARCH_695] Starting mechanistic interpretability research")
    print(f"[RESEARCH_695] Total search queries: {len(SEARCH_QUERIES)}")
    print(f"[RESEARCH_695] Engines: {ENGINES}")
    print(f"[RESEARCH_695] Timestamp: {results['timestamp']}\n")

    # Execute searches across all queries
    for idx, query in enumerate(SEARCH_QUERIES, 1):
        print(f"[{idx}/{len(SEARCH_QUERIES)}] Searching: {query[:70]}")

        try:
            search_results = research_multi_search(
                query=query,
                engines=ENGINES,
                max_results=15,
            )

            # Parse results
            result_count = 0
            if isinstance(search_results, dict):
                if "results" in search_results:
                    result_count = len(search_results.get("results", []))

            results["findings"][query] = {
                "status": "success",
                "result_count": result_count,
                "results": search_results,
            }

            print(f"  ✓ Retrieved {result_count} results\n")

        except Exception as e:
            results["findings"][query] = {
                "status": "error",
                "error": str(e)[:200],
                "error_type": type(e).__name__,
            }
            logger.error(f"Search failed for query: {query}", exc_info=True)
            print(f"  ✗ Error: {type(e).__name__}: {str(e)[:60]}\n")

        # Rate limiting between queries
        time.sleep(0.5)

    # Save results
    output_dir = Path("/opt/research-toolbox/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "research_695_interpretability.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n[RESEARCH_695] Results saved to: {output_file}")
    print(f"[RESEARCH_695] Total queries: {len(results['findings'])}")

    # Summary stats
    total_results = sum(f.get("result_count", 0) for f in results["findings"].values())
    success = sum(1 for f in results["findings"].values() if f.get("status") == "success")
    failed = sum(1 for f in results["findings"].values() if f.get("status") == "error")

    print(f"[RESEARCH_695] Success: {success}, Failed: {failed}")
    print(f"[RESEARCH_695] Total results collected: {total_results}")
    print(f"[RESEARCH_695] Output file size: {output_file.stat().st_size} bytes")

    return results


if __name__ == "__main__":
    try:
        results = run_research()
        print("\n[RESEARCH_695] Research complete.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[RESEARCH_695] FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
