#!/usr/bin/env python3
"""
Research 700: Adversarial Evasion of AI Defense Systems

Research task: Document guardrail-specific bypasses, stealth metrics, and adaptive attacks.
Searches for:
1. "bypass AI guardrails evasion techniques 2025 2026"
2. "content moderation adversarial evasion"
3. "safety classifier bypass adversarial examples text"
4. "LLM guard bypass NeMo guardrails attack"

Output: /opt/research-toolbox/tmp/research_700_defense_evasion.json

This script runs on Hetzner via Loom's multi_search tool.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("research_700")


def research_defense_evasion() -> dict:
    """Execute multi-source research on AI defense evasion techniques.

    Returns:
        Dictionary with research results, sources, and analysis.
    """
    try:
        # Import the research tools (synchronous)
        sys.path.insert(0, "/opt/research-toolbox/src")
        from loom.tools.multi_search import research_multi_search

        logger.info("Initialized research tools")

        # Define research queries
        queries = [
            "bypass AI guardrails evasion techniques 2025 2026",
            "content moderation adversarial evasion",
            "safety classifier bypass adversarial examples text",
            "LLM guard bypass NeMo guardrails attack",
        ]

        results = {
            "research_task": "Adversarial Evasion of AI Defense Systems",
            "timestamp": datetime.now(UTC).isoformat(),
            "queries": queries,
            "research_results": {},
            "guardrail_bypasses": {
                "nemo_guardrails": [],
                "llama_guard": [],
                "azure_content_safety": [],
                "generic_classifiers": [],
            },
            "evasion_techniques": {
                "perplexity_evasion": [],
                "semantic_similarity_evasion": [],
                "token_manipulation": [],
                "adaptive_attacks": [],
            },
            "stealth_metrics": [],
            "analysis_summary": "",
            "sources_found": [],
        }

        # Query each topic with research_multi_search
        for idx, query in enumerate(queries, 1):
            logger.info(f"[{idx}/{len(queries)}] Researching: {query}")

            try:
                # Call research_multi_search (synchronous wrapper)
                search_result = research_multi_search(
                    query=query,
                    max_results=50,
                )

                results["research_results"][query] = {
                    "raw_results": search_result.get("results", []),
                    "total_deduplicated": search_result.get("total_deduplicated", 0),
                    "sources_breakdown": search_result.get("sources_breakdown", {}),
                }

                # Track all sources
                for result in search_result.get("results", []):
                    if "url" in result:
                        url = result["url"]
                        if url not in results["sources_found"]:
                            results["sources_found"].append(url)

                logger.info(
                    f"  Found {search_result.get('total_deduplicated', 0)} "
                    f"deduplicated results from {len(search_result.get('sources_breakdown', {}))} sources"
                )

            except Exception as e:
                logger.error(f"Error researching '{query}': {e}")
                results["research_results"][query] = {
                    "error": str(e),
                    "raw_results": [],
                }

        # Extract all snippets for analysis
        all_snippets = []
        for query_result in results["research_results"].values():
            for item in query_result.get("raw_results", []):
                snippet = item.get("snippet", "")
                title = item.get("title", "")
                if snippet or title:
                    all_snippets.append({
                        "title": title,
                        "snippet": snippet,
                        "url": item.get("url", ""),
                        "source": item.get("source", ""),
                    })

        results["all_snippets"] = all_snippets

        # Categorize findings by guardrail system
        for snippet in all_snippets:
            text = f"{snippet['title']} {snippet['snippet']}".lower()

            if "nemo" in text or "nemoguardrails" in text:
                results["guardrail_bypasses"]["nemo_guardrails"].append(snippet)
            if "llama guard" in text or "llamaguard" in text:
                results["guardrail_bypasses"]["llama_guard"].append(snippet)
            if "azure" in text and "content" in text:
                results["guardrail_bypasses"]["azure_content_safety"].append(snippet)
            if "bypass" in text or "evasion" in text:
                results["guardrail_bypasses"]["generic_classifiers"].append(snippet)

            if "perplexity" in text:
                results["evasion_techniques"]["perplexity_evasion"].append(snippet)
            if "semantic" in text or "embedding" in text:
                results["evasion_techniques"]["semantic_similarity_evasion"].append(snippet)
            if "token" in text or "homoglyph" in text or "zero-width" in text:
                results["evasion_techniques"]["token_manipulation"].append(snippet)
            if "adaptive" in text or "detect" in text and "defense" in text:
                results["evasion_techniques"]["adaptive_attacks"].append(snippet)

        # Remove duplicates within categories
        for category in results["guardrail_bypasses"]:
            results["guardrail_bypasses"][category] = list(
                {json.dumps(s, sort_keys=True): s
                 for s in results["guardrail_bypasses"][category]}.values()
            )
        for category in results["evasion_techniques"]:
            results["evasion_techniques"][category] = list(
                {json.dumps(s, sort_keys=True): s
                 for s in results["evasion_techniques"][category]}.values()
            )

        # Analysis summary
        guardrail_count = sum(
            len(v) for v in results["guardrail_bypasses"].values()
        )
        evasion_count = sum(
            len(v) for v in results["evasion_techniques"].values()
        )

        results["analysis_summary"] = (
            f"Research completed at {results['timestamp']}. "
            f"Queried {len(queries)} research topics. "
            f"Found {len(results['sources_found'])} unique sources. "
            f"Total snippets extracted: {len(all_snippets)}. "
            f"Guardrail-specific findings: {guardrail_count} entries. "
            f"Evasion technique findings: {evasion_count} entries. "
            f"Key guardrail systems documented: NeMo Guardrails, Llama Guard, Azure Content Safety, "
            f"generic safety classifiers. Key evasion techniques: perplexity-based evasion, "
            f"semantic similarity evasion, token-level manipulation, adaptive attacks."
        )

        return results

    except Exception as e:
        logger.error(f"Fatal error in research: {e}", exc_info=True)
        return {
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("Research 700: Adversarial Evasion of AI Defense Systems")
    logger.info("=" * 80)

    # Run research
    results = research_defense_evasion()

    # Write results to output file
    output_path = Path("/opt/research-toolbox/tmp/research_700_defense_evasion.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"Results saved to {output_path}")
    logger.info(f"Total unique sources found: {len(results.get('sources_found', []))}")
    logger.info(f"Analysis: {results.get('analysis_summary', '')}")

    return results


if __name__ == "__main__":
    results = main()
    sys.exit(0 if "error" not in results else 1)
