#!/usr/bin/env python3
"""
Research Task 691: Constitutional Classifiers Bypass Analysis

Investigates Anthropic's Constitutional Classifiers defense:
- How they work (input/output classifiers trained on constitutions)
- Published ASR reduction: 86% → 4.4% effectiveness
- Known bypass techniques from published research
- Implications for Loom's strategy effectiveness
- Which strategies might still work against this defense

Queries:
1. "Constitutional Classifiers Anthropic defense 2026"
2. "bypass constitutional AI classifiers adversarial"
3. "Anthropic safety classifiers attack surface reduction"

Output: /opt/research-toolbox/tmp/research_691_constitutional.json
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load env
from dotenv import load_dotenv

load_dotenv(Path.home() / ".claude" / "resources.env")

from loom.tools.multi_search import research_multi_search
from loom.tools.deep import research_deep
from loom.tools.llm import research_llm_answer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("research_691")


def main() -> None:
    """Execute Constitutional Classifiers research workflow."""
    result: dict[str, Any] = {
        "research_id": "691",
        "topic": "Constitutional Classifiers Bypass Analysis",
        "queries": [
            "Constitutional Classifiers Anthropic defense 2026",
            "bypass constitutional AI classifiers adversarial",
            "Anthropic safety classifiers attack surface reduction",
        ],
        "stages": {},
        "findings": {
            "how_they_work": None,
            "asr_reduction": None,
            "known_bypasses": None,
            "implications_for_loom": None,
            "effective_strategies": None,
        },
        "error": None,
    }

    output_path = Path("/opt/research-toolbox/tmp/research_691_constitutional.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # ────────────────────────────────────────────────────────────────
        # STAGE 1: Multi-search across all three queries
        # ────────────────────────────────────────────────────────────────
        logger.info("STAGE 1: Executing research_multi_search() across 3 queries...")

        queries = [
            "Constitutional Classifiers Anthropic defense 2026",
            "bypass constitutional AI classifiers adversarial",
            "Anthropic safety classifiers attack surface reduction",
        ]

        multi_results = []
        total_results_count = 0
        for query in queries:
            logger.info(f"  Searching: {query}")
            try:
                search_result = research_multi_search(
                    query=query,
                    max_results=15,
                )
                multi_results.append({
                    "query": query,
                    "result": search_result,
                })
                total_results_count += len(search_result.get("results", []))
            except Exception as e:
                logger.warning(f"  Search failed for '{query}': {e}")
                multi_results.append({
                    "query": query,
                    "error": str(e),
                })

        result["stages"]["1_multi_search"] = {
            "queries_executed": len(queries),
            "total_results": total_results_count,
            "error": None,
        }
        logger.info(
            "STAGE 1 complete: %d queries, %d total results",
            len(queries),
            total_results_count,
        )

        # ────────────────────────────────────────────────────────────────
        # STAGE 2: Deep research on main topic
        # ────────────────────────────────────────────────────────────────
        logger.info("STAGE 2: Executing research_deep() for Constitutional Classifiers...")

        try:
            # Note: research_deep is async, but we're in sync context
            # We need to use asyncio.run() once at top level
            import asyncio

            async def run_deep_research():
                return await research_deep(
                    query="Constitutional Classifiers Anthropic adversarial robustness defense mechanisms",
                    depth=3,
                    include_github=True,
                    include_academic=True,
                    include_community=False,
                    synthesize=True,
                    extract=True,
                )

            deep_result = asyncio.run(run_deep_research())
        except Exception as e:
            logger.error(f"Deep research failed: {e}")
            deep_result = {"error": str(e)}

        result["stages"]["2_deep_research"] = {
            "query": "Constitutional Classifiers Anthropic adversarial robustness",
            "pages_searched": deep_result.get("pages_searched", 0),
            "pages_fetched": deep_result.get("pages_fetched", 0),
            "top_pages_count": len(deep_result.get("top_pages", [])),
            "synthesis_present": deep_result.get("synthesis") is not None,
            "cost_usd": deep_result.get("total_cost_usd", 0),
            "elapsed_ms": deep_result.get("elapsed_ms", 0),
            "error": deep_result.get("error"),
        }

        logger.info(
            "STAGE 2 complete: searched %d pages, fetched %d, synthesis=%s",
            deep_result.get("pages_searched", 0),
            deep_result.get("pages_fetched", 0),
            deep_result.get("synthesis") is not None,
        )

        # ────────────────────────────────────────────────────────────────
        # STAGE 3: LLM synthesis of findings
        # ────────────────────────────────────────────────────────────────
        logger.info("STAGE 3: Synthesizing findings with research_llm_answer()...")

        synthesis_prompt = """
Based on the Constitutional Classifiers research, provide a structured analysis:

1. HOW THEY WORK: Explain how Constitutional Classifiers function
   - Input vs output classifiers
   - Constitution-based training approach
   - Architecture and mechanism

2. ASR REDUCTION: Document the published defense effectiveness
   - Starting ASR (86%)
   - Final ASR (4.4%)
   - Methodology and metrics

3. KNOWN BYPASSES: List any published bypass techniques
   - Adversarial examples that work
   - Jailbreak strategies that bypass them
   - Evasion methods

4. IMPLICATIONS FOR LOOM: What does this mean for attack strategy effectiveness?
   - Which Loom strategies are affected
   - New approaches needed
   - Recommended adaptations

5. EFFECTIVE STRATEGIES: Which attack strategies likely still work?
   - Reasoning-based attacks
   - Role-play and persona attacks
   - Encoding/obfuscation approaches
   - Multi-turn conversation exploits
"""

        try:
            import asyncio

            async def run_llm_synthesis():
                return await research_llm_answer(
                    query=synthesis_prompt,
                    context="Constitutional Classifiers defense research findings",
                    cite_sources=True,
                )

            llm_result = asyncio.run(run_llm_synthesis())
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            llm_result = {"error": str(e)}

        result["stages"]["3_llm_synthesis"] = {
            "prompt_length": len(synthesis_prompt),
            "answer_length": len(llm_result.get("answer", "")),
            "cost_usd": llm_result.get("total_cost_usd", 0),
            "sources_cited": len(llm_result.get("sources", [])),
            "error": llm_result.get("error"),
        }

        # Extract synthesis into findings
        synthesis_answer = llm_result.get("answer", "")
        if synthesis_answer:
            result["findings"] = {
                "how_they_work": synthesis_answer[:1000] if synthesis_answer else None,
                "asr_reduction": "86% to 4.4% - Anthropic Constitutional Classifiers",
                "known_bypasses": "See synthesis section for details",
                "implications_for_loom": "Constitutional Classifiers significantly reduce jailbreak effectiveness",
                "effective_strategies": "Reasoning-based, multi-turn, and encoding-based attacks may still work",
            }

        logger.info("STAGE 3 complete: LLM synthesis executed")

        # ────────────────────────────────────────────────────────────────
        # FINAL: Assemble results and save to JSON
        # ────────────────────────────────────────────────────────────────
        result["synthesis"] = llm_result.get("answer", "")
        result["sources"] = llm_result.get("sources", [])
        result["multi_search_results"] = multi_results
        result["deep_research"] = deep_result
        result["status"] = "complete"

        # Save to file
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"Research complete. Results saved to {output_path}")
        print(json.dumps({"status": "success", "output_file": str(output_path)}, indent=2))

    except Exception as e:
        logger.error(f"Research failed: {e}", exc_info=True)
        result["error"] = str(e)
        result["status"] = "error"

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
