#!/usr/bin/env python3
"""Full-pipeline workflow orchestration for all Loom tool categories.

Demonstrates using 10 major Loom tool categories in a single research workflow:
1. Multi-search (multi_search) - Find sources across 20+ engines
2. Deep research (deep) - Full 12-stage pipeline
3. LLM synthesis (llm) - Summarize and extract findings
4. Career trajectory (career_trajectory) - Market velocity analysis
5. Company intel (company_intel) - Competitor/vendor analysis
6. Knowledge graph (knowledge_graph) - Entity extraction
7. Fact checker (fact_checker) - Claim verification
8. HCS scoring (hcs10_academic) - Output quality assessment
9. Prompt reframe (prompt_reframe) - Compliance reframing
10. AI safety (ai_safety) - Safety validation

Query: "AI safety testing market 2026"

Each stage feeds into the next where possible, building a comprehensive
research synthesis with quality metrics, entity graphs, and safety validation.

Usage (local Mac):
    python3 scripts/full_tool_pipeline.py

Usage (Hetzner):
    ssh hetzner 'cd /opt/research-toolbox && python3 scripts/full_tool_pipeline.py'
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# ─── Setup ───────────────────────────────────────────────────────────────────

# Load credentials
load_dotenv(Path.home() / ".claude" / "resources.env")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("full_tool_pipeline")

# Config - detect environment
def get_output_dir() -> Path:
    """Determine output directory based on environment."""
    # Try Hetzner first
    if Path("/opt/research-toolbox/tmp").parent.exists():
        return Path("/opt/research-toolbox/tmp")
    # Fall back to local temp
    return Path("/tmp/loom-pipeline")

MCP_SERVER_URL = os.environ.get("LOOM_MCP_SERVER", "http://127.0.0.1:8787/mcp")
OUTPUT_DIR = get_output_dir()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TIMEOUT = 180  # seconds


# ─── Data Models ─────────────────────────────────────────────────────────────

@dataclass
class ToolInvocation:
    """Records a single tool invocation."""

    tool_name: str
    status: str  # "success", "error", "skipped"
    elapsed_secs: float
    input_size: int
    output_size: int
    error_message: str | None = None


@dataclass
class PipelineResult:
    """Overall pipeline result."""

    query: str
    started_at: str
    completed_at: str
    total_elapsed_secs: float
    tools_invoked: int
    tools_succeeded: int
    tools_failed: int
    invocations: list[dict[str, Any]]
    multi_search_results: dict[str, Any] | None
    deep_research_results: dict[str, Any] | None
    llm_synthesis: dict[str, Any] | None
    career_velocity: dict[str, Any] | None
    company_analysis: dict[str, Any] | None
    entity_graph: dict[str, Any] | None
    fact_checks: dict[str, Any] | None
    quality_score: dict[str, Any] | None
    reframed_content: dict[str, Any] | None
    safety_check: dict[str, Any] | None


# ─── MCP Client ──────────────────────────────────────────────────────────────

async def call_mcp_tool(
    tool_name: str,
    params: dict[str, Any],
    timeout: int = TIMEOUT,
) -> tuple[dict[str, Any] | None, str | None]:
    """Call an MCP tool via streamable-http.

    Returns:
        (result_dict, error_string)
    """
    try:
        async with streamablehttp_client(MCP_SERVER_URL, timeout=timeout) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                logger.debug(f"Calling {tool_name} with params: {params}")

                result = await session.call_tool(tool_name, params)

                # Extract text from MCP TextContent
                if result.content and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, "text"):
                        try:
                            return cast(dict[str, Any], json.loads(content.text)), None
                        except json.JSONDecodeError:
                            return {"text": content.text}, None
                    return {"text": str(content)}, None

                return {}, None

    except asyncio.TimeoutError as e:
        error = f"Timeout: {e}"
        logger.error(error)
        return None, error
    except ConnectionError as e:
        error = f"Connection error: {e}"
        logger.error(error)
        return None, error
    except Exception as e:
        error = f"Exception: {e}"
        logger.error(error)
        return None, error


# ─── Tool Execution ──────────────────────────────────────────────────────────

async def run_multi_search(
    query: str, invocations: list[ToolInvocation]
) -> dict[str, Any] | None:
    """Stage 1: Multi-search across 20+ search engines."""
    logger.info("=== Stage 1: Multi-Search ===")
    tool_name = "research_multi_search"
    start = time.time()

    result, error = await call_mcp_tool(
        tool_name,
        {"query": query, "max_per_engine": 5},
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(query),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        logger.info(f"Multi-search found {len(result.get('results', []))} sources")
    else:
        logger.warning(f"Multi-search failed: {error}")

    return result


async def run_deep_research(
    query: str, invocations: list[ToolInvocation]
) -> dict[str, Any] | None:
    """Stage 2: Deep research via 12-stage pipeline."""
    logger.info("=== Stage 2: Deep Research ===")
    tool_name = "research_deep"
    start = time.time()

    result, error = await call_mcp_tool(
        tool_name,
        {"query": query, "with_sentiment": False, "with_red_team": False},
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(query),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        logger.info(
            f"Deep research completed with {result.get('stages_completed', 0)} stages"
        )
    else:
        logger.warning(f"Deep research failed: {error}")

    return result


async def run_llm_synthesis(
    deep_result: dict[str, Any] | None,
    multi_search_result: dict[str, Any] | None,
    invocations: list[ToolInvocation],
) -> dict[str, Any] | None:
    """Stage 3: LLM synthesis and summarization."""
    logger.info("=== Stage 3: LLM Synthesis ===")
    tool_name = "research_llm_summarize"
    start = time.time()

    # Combine inputs
    content_to_summarize = ""
    if deep_result and "answer" in deep_result:
        content_to_summarize = deep_result["answer"][:2000]
    elif multi_search_result and "results" in multi_search_result:
        snippets = [r.get("snippet", "") for r in multi_search_result["results"][:3]]
        content_to_summarize = "\n".join(snippets)[:2000]

    if not content_to_summarize:
        logger.warning("No content to synthesize")
        invocations.append(
            ToolInvocation(
                tool_name=tool_name,
                status="skipped",
                elapsed_secs=0,
                input_size=0,
                output_size=0,
                error_message="No content available",
            )
        )
        return None

    result, error = await call_mcp_tool(
        tool_name,
        {"content": content_to_summarize, "max_length": 500, "style": "technical"},
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(content_to_summarize),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        logger.info("LLM synthesis produced summary")
    else:
        logger.warning(f"LLM synthesis failed: {error}")

    return result


async def run_career_trajectory(
    query: str, invocations: list[ToolInvocation]
) -> dict[str, Any] | None:
    """Stage 4: Career trajectory and market velocity."""
    logger.info("=== Stage 4: Career Trajectory & Market Velocity ===")
    tool_name = "research_market_velocity"
    start = time.time()

    # Extract skill/tech from query
    skills = [s.strip() for s in query.split() if len(s) > 3][:2]
    if not skills:
        skills = ["AI safety", "testing"]

    result, error = await call_mcp_tool(
        tool_name,
        {"skill": skills[0], "region": "global"},
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(query),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        logger.info("Career trajectory analysis completed")
    else:
        logger.warning(f"Career trajectory failed: {error}")

    return result


async def run_company_intel(
    query: str, invocations: list[ToolInvocation]
) -> dict[str, Any] | None:
    """Stage 5: Company intelligence and competitor analysis."""
    logger.info("=== Stage 5: Company Intelligence ===")
    tool_name = "research_company_intel"
    start = time.time()

    # Extract company/domain if present
    company = "OpenAI"  # Default for AI safety market

    result, error = await call_mcp_tool(
        tool_name,
        {"company": company, "include_financials": True},
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(query),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        logger.info("Company intel analysis completed")
    else:
        logger.warning(f"Company intel failed: {error}")

    return result


async def run_knowledge_graph(
    deep_result: dict[str, Any] | None,
    invocations: list[ToolInvocation],
) -> dict[str, Any] | None:
    """Stage 6: Knowledge graph extraction."""
    logger.info("=== Stage 6: Knowledge Graph Extraction ===")
    tool_name = "research_knowledge_graph"
    start = time.time()

    # Use synthesis result as input
    content = ""
    if deep_result and "answer" in deep_result:
        content = deep_result["answer"][:3000]

    if not content:
        logger.warning("No content for knowledge graph")
        invocations.append(
            ToolInvocation(
                tool_name=tool_name,
                status="skipped",
                elapsed_secs=0,
                input_size=0,
                output_size=0,
                error_message="No content available",
            )
        )
        return None

    result, error = await call_mcp_tool(
        tool_name,
        {
            "content": content,
            "entity_types": ["PERSON", "ORGANIZATION", "TECHNOLOGY", "MARKET"],
        },
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(content),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        entities = result.get("entities", [])
        relations = result.get("relations", [])
        logger.info(f"Knowledge graph: {len(entities)} entities, {len(relations)} relations")
    else:
        logger.warning(f"Knowledge graph failed: {error}")

    return result


async def run_fact_checker(
    deep_result: dict[str, Any] | None,
    invocations: list[ToolInvocation],
) -> dict[str, Any] | None:
    """Stage 7: Fact-checking on key claims."""
    logger.info("=== Stage 7: Fact Checking ===")
    tool_name = "research_fact_check"
    start = time.time()

    # Extract claims from synthesis
    claim = "AI safety testing is a growing market in 2026"
    if deep_result and "answer" in deep_result:
        # Simple claim extraction - first sentence
        sentences = deep_result["answer"].split(".")
        if sentences:
            claim = sentences[0].strip()[:200]

    result, error = await call_mcp_tool(
        tool_name,
        {"claim": claim, "max_depth": 2},
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(claim),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        confidence = result.get("confidence", 0)
        logger.info(f"Fact check: confidence={confidence}")
    else:
        logger.warning(f"Fact check failed: {error}")

    return result


async def run_hcs_scoring(
    llm_synthesis: dict[str, Any] | None,
    invocations: list[ToolInvocation],
) -> dict[str, Any] | None:
    """Stage 8: HCS-10 quality scoring."""
    logger.info("=== Stage 8: HCS Scoring ===")
    tool_name = "research_hcs_score"
    start = time.time()

    # Score the synthesis content
    content = ""
    if llm_synthesis and isinstance(llm_synthesis, dict):
        if "summary" in llm_synthesis:
            content = llm_synthesis["summary"]
        elif "text" in llm_synthesis:
            content = llm_synthesis["text"]

    if not content:
        logger.warning("No content for HCS scoring")
        invocations.append(
            ToolInvocation(
                tool_name=tool_name,
                status="skipped",
                elapsed_secs=0,
                input_size=0,
                output_size=0,
                error_message="No synthesis content",
            )
        )
        return None

    result, error = await call_mcp_tool(
        tool_name,
        {"content": content, "rubric": "academic_quality"},
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(content),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        score = result.get("score", 0)
        logger.info(f"HCS score: {score}/100")
    else:
        logger.warning(f"HCS scoring failed: {error}")

    return result


async def run_prompt_reframe(
    llm_synthesis: dict[str, Any] | None,
    invocations: list[ToolInvocation],
) -> dict[str, Any] | None:
    """Stage 9: Prompt reframing for compliance."""
    logger.info("=== Stage 9: Prompt Reframing ===")
    tool_name = "research_prompt_reframe"
    start = time.time()

    # Reframe synthesis for compliance
    content = ""
    if llm_synthesis and isinstance(llm_synthesis, dict):
        if "summary" in llm_synthesis:
            content = llm_synthesis["summary"]
        elif "text" in llm_synthesis:
            content = llm_synthesis["text"]

    if not content:
        logger.warning("No content for prompt reframing")
        invocations.append(
            ToolInvocation(
                tool_name=tool_name,
                status="skipped",
                elapsed_secs=0,
                input_size=0,
                output_size=0,
                error_message="No synthesis content",
            )
        )
        return None

    result, error = await call_mcp_tool(
        tool_name,
        {
            "prompt": content,
            "strategy": "formal_academic",
            "max_tokens": 500,
        },
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(content),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        logger.info("Prompt reframing completed")
    else:
        logger.warning(f"Prompt reframing failed: {error}")

    return result


async def run_ai_safety_check(
    llm_synthesis: dict[str, Any] | None,
    invocations: list[ToolInvocation],
) -> dict[str, Any] | None:
    """Stage 10: AI safety validation."""
    logger.info("=== Stage 10: AI Safety Check ===")
    tool_name = "research_safety_filter_map"
    start = time.time()

    # Safety check the synthesis
    content = ""
    if llm_synthesis and isinstance(llm_synthesis, dict):
        if "summary" in llm_synthesis:
            content = llm_synthesis["summary"]
        elif "text" in llm_synthesis:
            content = llm_synthesis["text"]

    if not content:
        logger.warning("No content for safety check")
        invocations.append(
            ToolInvocation(
                tool_name=tool_name,
                status="skipped",
                elapsed_secs=0,
                input_size=0,
                output_size=0,
                error_message="No synthesis content",
            )
        )
        return None

    result, error = await call_mcp_tool(
        tool_name,
        {"text": content},
    )

    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=len(content),
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )

    if result:
        safe = result.get("is_safe", True)
        logger.info(f"Safety check: is_safe={safe}")
    else:
        logger.warning(f"Safety check failed: {error}")

    return result


# ─── Main Pipeline ───────────────────────────────────────────────────────────

async def run_pipeline(query: str) -> PipelineResult:
    """Execute the full 10-stage research pipeline."""
    logger.info(f"Starting full pipeline for: {query}")

    pipeline_start = time.time()
    started_at = datetime.now(UTC).isoformat()
    invocations: list[ToolInvocation] = []

    # Execute stages in sequence with dependencies
    multi_search_results = await run_multi_search(query, invocations)
    deep_research_results = await run_deep_research(query, invocations)
    llm_synthesis = await run_llm_synthesis(
        deep_research_results, multi_search_results, invocations
    )
    career_velocity = await run_career_trajectory(query, invocations)
    company_analysis = await run_company_intel(query, invocations)
    entity_graph = await run_knowledge_graph(deep_research_results, invocations)
    fact_checks = await run_fact_checker(deep_research_results, invocations)
    quality_score = await run_hcs_scoring(llm_synthesis, invocations)
    reframed_content = await run_prompt_reframe(llm_synthesis, invocations)
    safety_check = await run_ai_safety_check(llm_synthesis, invocations)

    pipeline_elapsed = time.time() - pipeline_start
    completed_at = datetime.now(UTC).isoformat()

    # Count successes/failures
    succeeded = sum(1 for inv in invocations if inv.status == "success")
    failed = sum(1 for inv in invocations if inv.status == "error")

    # Build result
    result = PipelineResult(
        query=query,
        started_at=started_at,
        completed_at=completed_at,
        total_elapsed_secs=pipeline_elapsed,
        tools_invoked=len(invocations),
        tools_succeeded=succeeded,
        tools_failed=failed,
        invocations=[asdict(inv) for inv in invocations],
        multi_search_results=multi_search_results,
        deep_research_results=deep_research_results,
        llm_synthesis=llm_synthesis,
        career_velocity=career_velocity,
        company_analysis=company_analysis,
        entity_graph=entity_graph,
        fact_checks=fact_checks,
        quality_score=quality_score,
        reframed_content=reframed_content,
        safety_check=safety_check,
    )

    return result


# ─── Entry ───────────────────────────────────────────────────────────────────

async def main() -> int:
    """Run the pipeline and save results."""
    query = "AI safety testing market 2026"

    logger.info(f"MCP Server: {MCP_SERVER_URL}")
    logger.info(f"Output Dir: {OUTPUT_DIR}")
    logger.info("")

    try:
        result = await run_pipeline(query)

        # Save to JSON
        output_file = OUTPUT_DIR / "full_pipeline_result.json"
        with open(output_file, "w") as f:
            json.dump(asdict(result), f, indent=2, default=str)

        logger.info("")
        logger.info("=== PIPELINE COMPLETE ===")
        logger.info(f"Tools invoked: {result.tools_invoked}")
        logger.info(f"Tools succeeded: {result.tools_succeeded}")
        logger.info(f"Tools failed: {result.tools_failed}")
        logger.info(f"Total time: {result.total_elapsed_secs:.2f}s")
        logger.info(f"Results saved to: {output_file}")

        # Print summary
        print("")
        print("=" * 70)
        print("FULL TOOL PIPELINE EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Query: {result.query}")
        print(f"Total Tools: {result.tools_invoked}")
        print(f"  Succeeded: {result.tools_succeeded}")
        print(f"  Failed: {result.tools_failed}")
        print(f"Elapsed: {result.total_elapsed_secs:.2f}s")
        print("")
        print("Tool Execution Times:")
        for inv in result.invocations:
            status_badge = (
                "✓"
                if inv["status"] == "success"
                else "✗"
                if inv["status"] == "error"
                else "—"
            )
            print(
                f"  {status_badge} {inv['tool_name']:<35} {inv['elapsed_secs']:.2f}s "
                f"({inv['input_size']} in, {inv['output_size']} out)"
            )
        print("")
        print(f"Output: {output_file}")
        print("=" * 70)

        return 0

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
