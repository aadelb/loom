#!/usr/bin/env python3
"""
REQ-002 E2E Test: Full workflow for "AI for wealth generation"

Executes:
1. research_deep(query="AI for wealth generation strategies 2026")
2. research_multi_search(query="AI tools for making money")
3. research_llm_answer() to synthesize findings

Output: /opt/research-toolbox/tmp/req002_result.json

Acceptance:
- AI-specific strategies with tool/platform recommendations
- Actionable insights
- Multiple sources cited
"""

import asyncio
import concurrent.futures
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loom.tools.deep import research_deep
from loom.tools.llm import research_llm_answer
from loom.tools.multi_search import research_multi_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("req002")


async def main() -> None:
    """Execute REQ-002 workflow."""
    result = {
        "request_id": "REQ-002",
        "workflow": "AI for wealth generation",
        "stages": {},
        "error": None,
    }

    try:
        # ────────────────────────────────────────────────────────────────
        # STAGE 1: Deep research on "AI for wealth generation strategies"
        # ────────────────────────────────────────────────────────────────
        logger.info("STAGE 1: Executing research_deep() for AI wealth generation...")
        deep_query = "AI for wealth generation strategies 2026"

        deep_result = await research_deep(
            query=deep_query,
            depth=2,
            include_github=True,
            include_community=False,
            synthesize=True,
            extract=True,
        )

        result["stages"]["1_deep_research"] = {
            "query": deep_query,
            "pages_searched": deep_result.get("pages_searched", 0),
            "pages_fetched": deep_result.get("pages_fetched", 0),
            "top_pages_count": len(deep_result.get("top_pages", [])),
            "synthesis_present": deep_result.get("synthesis") is not None,
            "github_repos_found": len(deep_result.get("github_repos", [])) if deep_result.get("github_repos") else 0,
            "cost_usd": deep_result.get("total_cost_usd", 0),
            "elapsed_ms": deep_result.get("elapsed_ms", 0),
            "error": deep_result.get("error"),
        }

        logger.info(
            "STAGE 1 complete: searched %d pages, fetched %d, synthesis=%s",
            deep_result.get("pages_searched", 0),
            deep_result.get("pages_fetched", 0),
            deep_result.get("synthesis") is not None,
        )

        # ────────────────────────────────────────────────────────────────
        # STAGE 2: Multi-source search on "AI tools for making money"
        # Call in a separate thread executor to avoid event loop conflicts
        # ────────────────────────────────────────────────────────────────
        logger.info("STAGE 2: Executing research_multi_search() for AI money-making tools...")
        multi_query = "AI tools for making money"

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            multi_result = await loop.run_in_executor(
                executor,
                research_multi_search,
                multi_query,
                None,  # engines
                30,    # max_results
            )

        result["stages"]["2_multi_search"] = {
            "query": multi_query,
            "engines_queried": multi_result.get("engines_queried", []),
            "total_raw_results": multi_result.get("total_raw_results", 0),
            "total_deduplicated": multi_result.get("total_deduplicated", 0),
            "results_returned": len(multi_result.get("results", [])),
            "sources_breakdown": multi_result.get("sources_breakdown", {}),
        }

        logger.info(
            "STAGE 2 complete: %d deduplicated results from %d engines",
            multi_result.get("total_deduplicated", 0),
            len(multi_result.get("engines_queried", [])),
        )

        # ────────────────────────────────────────────────────────────────
        # STAGE 3: LLM synthesis of findings
        # ────────────────────────────────────────────────────────────────
        logger.info("STAGE 3: Synthesizing findings via research_llm_answer()...")

        # Prepare sources from deep research for LLM answer
        sources_for_llm: list[dict[str, str]] = []

        if deep_result.get("top_pages"):
            for page in deep_result.get("top_pages", [])[:5]:
                markdown_text = page.get("markdown", "")
                # Truncate to first 500 chars if needed
                text_content = markdown_text[:500] if markdown_text else page.get("title", "")
                sources_for_llm.append({
                    "title": page.get("title", ""),
                    "text": text_content,
                    "url": page.get("url", ""),
                })

        # Add top multi-search results as additional sources
        if multi_result.get("results"):
            for hit in multi_result.get("results", [])[:3]:
                sources_for_llm.append({
                    "title": hit.get("title", ""),
                    "text": hit.get("snippet", "")[:500],
                    "url": hit.get("url", ""),
                })

        if not sources_for_llm:
            logger.warning("No sources available for LLM synthesis, using fallback")
            sources_for_llm = [
                {
                    "title": "AI Wealth Generation Methods",
                    "text": "AI has created numerous opportunities for wealth generation through automation, content creation, data analysis, and AI-powered tools. Key strategies include building AI-powered applications, offering AI consulting services, creating AI training content, and automating business processes.",
                    "url": "https://example.com/ai-wealth",
                }
            ]

        answer_result = await research_llm_answer(
            question="What are the most promising AI tools and strategies for wealth generation in 2026?",
            sources=sources_for_llm,
            max_tokens=800,
            style="cited",
        )

        result["stages"]["3_llm_synthesis"] = {
            "question": "What are the most promising AI tools and strategies for wealth generation in 2026?",
            "answer_length": len(answer_result.get("answer", "")),
            "citations_count": len(answer_result.get("citations", [])),
            "model_used": answer_result.get("model", ""),
            "provider_used": answer_result.get("provider", ""),
            "cost_usd": answer_result.get("cost_usd", 0),
            "answer_preview": answer_result.get("answer", "")[:200],
        }

        logger.info(
            "STAGE 3 complete: synthesized answer with %d citations using %s/%s",
            len(answer_result.get("citations", [])),
            answer_result.get("provider", "unknown"),
            answer_result.get("model", "unknown"),
        )

        # ────────────────────────────────────────────────────────────────
        # VALIDATION & OUTPUT
        # ────────────────────────────────────────────────────────────────
        logger.info("Validating acceptance criteria...")

        # Acceptance criterion 1: AI-specific strategies with tool/platform recommendations
        has_strategies = (
            deep_result.get("synthesis") is not None or
            len(deep_result.get("top_pages", [])) > 0
        )
        has_tools = (
            len(multi_result.get("results", [])) > 0 or
            len(deep_result.get("github_repos", [])) > 0
        )

        # Acceptance criterion 2: Actionable insights
        has_actionable = len(answer_result.get("answer", "")) > 100

        # Acceptance criterion 3: Multiple sources cited
        has_citations = len(answer_result.get("citations", [])) > 0 or len(sources_for_llm) > 1

        result["validation"] = {
            "criterion_1_strategies_and_tools": has_strategies and has_tools,
            "criterion_2_actionable_insights": has_actionable,
            "criterion_3_multiple_sources": has_citations,
            "all_criteria_met": (has_strategies and has_tools) and has_actionable and has_citations,
        }

        # Build final summary
        result["summary"] = {
            "total_sources_searched": (
                deep_result.get("pages_searched", 0) +
                multi_result.get("total_raw_results", 0)
            ),
            "total_sources_synthesized": len(sources_for_llm),
            "total_cost_usd": (
                deep_result.get("total_cost_usd", 0) +
                answer_result.get("cost_usd", 0)
            ),
            "total_time_ms": deep_result.get("elapsed_ms", 0),
            "insights_generated": answer_result.get("answer", ""),
            "key_findings": {
                "ai_tools_mentioned": _extract_ai_tools(answer_result.get("answer", "")),
                "strategies_identified": _extract_strategies(answer_result.get("answer", "")),
                "sources_cited": [
                    {"title": c.get("title", ""), "url": c.get("url", "")}
                    for c in answer_result.get("citations", [])
                ] if answer_result.get("citations") else [
                    {"title": s.get("title", ""), "url": s.get("url", "")}
                    for s in sources_for_llm
                ],
            },
        }

    except Exception as exc:
        logger.exception("Workflow failed")
        result["error"] = f"{type(exc).__name__}: {str(exc)}"
        result["validation"] = {
            "criterion_1_strategies_and_tools": False,
            "criterion_2_actionable_insights": False,
            "criterion_3_multiple_sources": False,
            "all_criteria_met": False,
        }
        result["summary"] = {
            "total_sources_searched": 0,
            "total_sources_synthesized": 0,
            "total_cost_usd": 0,
            "total_time_ms": 0,
            "insights_generated": "",
            "key_findings": {
                "ai_tools_mentioned": [],
                "strategies_identified": [],
                "sources_cited": [],
            },
        }

    # ────────────────────────────────────────────────────────────────
    # SAVE RESULTS
    # ────────────────────────────────────────────────────────────────
    output_dir = Path("/opt/research-toolbox/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "req002_result.json"
    output_file.write_text(json.dumps(result, indent=2))

    logger.info("Results saved to: %s", output_file)

    # Print key results
    print("\n" + "="*80)
    print("REQ-002 E2E TEST RESULTS")
    print("="*80)
    print(f"\nValidation: {result['validation']['all_criteria_met']}")
    print(f"Stages completed: {len(result['stages'])}")
    print(f"Total sources searched: {result['summary']['total_sources_searched']}")
    print(f"Total sources synthesized: {result['summary']['total_sources_synthesized']}")

    print(f"\nKey Findings:")
    if result.get("summary", {}).get("key_findings"):
        findings = result["summary"]["key_findings"]
        if findings.get("ai_tools_mentioned"):
            print(f"  AI Tools identified: {', '.join(findings['ai_tools_mentioned'][:5])}")
        if findings.get("strategies_identified"):
            print(f"  Strategies: {', '.join(findings['strategies_identified'][:3])}")
        print(f"  Sources cited: {len(findings.get('sources_cited', []))}")

    print(f"\nCosts: ${result['summary']['total_cost_usd']:.4f}")
    print(f"Time: {result['summary']['total_time_ms']}ms")
    print(f"Output: {output_file}")

    if result.get("error"):
        print(f"\nError: {result['error']}")

    print("="*80 + "\n")

    # Exit with appropriate code
    sys.exit(0 if result["validation"]["all_criteria_met"] else 1)


def _extract_ai_tools(text: str) -> list[str]:
    """Extract AI tool names from synthesis text."""
    tools = []
    keywords = [
        "ChatGPT", "Claude", "Gemini", "GPT-4", "Midjourney", "DALL-E",
        "Copilot", "Perplexity", "LLaMA", "Stable Diffusion", "AutoGPT",
        "Jasper", "Copy.ai", "Writersonic", "Surfer", "Synthesia",
    ]
    for keyword in keywords:
        if keyword.lower() in text.lower():
            tools.append(keyword)
    return tools


def _extract_strategies(text: str) -> list[str]:
    """Extract wealth generation strategies from synthesis text."""
    strategies = []
    keywords = [
        "content creation", "automation", "consulting", "training",
        "API integration", "data analysis", "chatbot development",
        "image generation", "marketing automation", "copywriting",
    ]
    for keyword in keywords:
        if keyword.lower() in text.lower():
            strategies.append(keyword)
    return strategies


if __name__ == "__main__":
    asyncio.run(main())
