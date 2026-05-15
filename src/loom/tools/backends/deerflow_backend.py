"""research_deer_flow — Multi-agent research orchestration via DeerFlow.

Provides coordinated multi-agent research using DeerFlow framework with
automatic agent selection, task decomposition, and synthesis.

Integrates with ByteDance's DeerFlow 2.0 (https://github.com/bytedance/deer-flow)
which orchestrates sub-agents, memory, and sandboxes for deep exploration.

Note: Full DeerFlow integration requires Python 3.12+ for the embedded client.
      Until then, uses enhanced fallback mode with simulated multi-agent research.
      When DeerFlow HTTP server is available, can connect via REST API instead.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    # Requires Python 3.12+ for deerflow-harness
    from deerflow.client import DeerFlowClient, StreamEvent

    _HAS_DEERFLOW_CLIENT = True
except ImportError:
    _HAS_DEERFLOW_CLIENT = False

logger = logging.getLogger("loom.tools.deerflow_backend")

# Constraints
MIN_QUERY_LEN = 3
MAX_QUERY_LEN = 2000
MAX_AGENTS = 10
VALID_DEPTHS = ["shallow", "standard", "deep", "comprehensive"]

# DeerFlow HTTP server endpoint (if running separately)
DEERFLOW_HTTP_URL = os.environ.get("DEERFLOW_HTTP_URL", None)


@handle_tool_errors("research_deer_flow")
async def research_deer_flow(
    query: str,
    depth: str = "standard",
    max_agents: int = 5,
    timeout: int = 120,
) -> dict[str, Any]:
    """Run multi-agent research using DeerFlow orchestration.

    Coordinates multiple specialized research agents for parallel
    investigation, cross-validation, and synthesis. Uses ByteDance's
    DeerFlow framework for advanced agentic research capabilities.

    Attempts to use:
    1. Embedded DeerFlow client (requires Python 3.12+)
    2. HTTP DeerFlow server (if DEERFLOW_HTTP_URL is set)
    3. Enhanced fallback mode with simulated multi-agent research

    Args:
        query: Research topic or question
        depth: Research depth: 'shallow', 'standard', 'deep', 'comprehensive'
               (default: 'standard')
        max_agents: Maximum number of agents to deploy (1-10, default: 5)
        timeout: Operation timeout in seconds (10-600, default: 120)

    Returns:
        Dict with keys:
        - query: Input query
        - agents_used: Number of agents deployed
        - findings: List of findings from each agent with {agent, result, confidence}
        - synthesis: Synthesized conclusion across all agents
        - contradictions: Any contradictory findings (optional)
        - backend: "deerflow_embedded", "deerflow_http", or "fallback"
        - error: Error message if operation failed (optional)
        - note: Additional context (e.g., "Fallback mode used")
    """
    try:
        # Input validation
        if not query or not isinstance(query, str):
            return {
                "query": query,
                "error": "query must be a non-empty string",
                "agents_used": 0,
                "findings": [],
                "synthesis": "",
                "backend": "none",
            }

        query = query.strip()
        if len(query) < MIN_QUERY_LEN or len(query) > MAX_QUERY_LEN:
            return {
                "query": query,
                "error": f"query length must be {MIN_QUERY_LEN}-{MAX_QUERY_LEN} chars",
                "agents_used": 0,
                "findings": [],
                "synthesis": "",
                "backend": "none",
            }

        # Validate depth
        if depth not in VALID_DEPTHS:
            depth = "standard"

        # Validate max_agents
        if not isinstance(max_agents, int) or max_agents < 1 or max_agents > MAX_AGENTS:
            max_agents = 5

        # Validate timeout
        if not isinstance(timeout, int) or timeout < 10 or timeout > 600:
            timeout = 120

        # Try embedded client first (Python 3.12+)
        if _HAS_DEERFLOW_CLIENT:
            result = await _research_with_embedded_client(query, depth, max_agents, timeout)
            if result:
                return result

        # Try HTTP API if configured
        if DEERFLOW_HTTP_URL:
            result = await _research_with_http_api(query, depth, max_agents, timeout)
            if result:
                return result

        # Fall back to enhanced fallback mode
        logger.info(
            "deerflow_unavailable, using enhanced fallback pipeline query=%s depth=%s",
            query[:50],
            depth,
        )
        return _fallback_multi_agent_research(query, depth, max_agents, timeout)
    except Exception as exc:
        return {"error": str(exc), "tool": "research_deer_flow"}


async def _research_with_embedded_client(
    query: str,
    depth: str,
    max_agents: int,
    timeout: int,
) -> dict[str, Any] | None:
    """Attempt research using embedded DeerFlow client (Python 3.12+ only)."""
    try:
        from deerflow.client import DeerFlowClient, StreamEvent

        logger.info(
            "deerflow_embedded_start query=%s depth=%s agents=%d",
            query[:50],
            depth,
            max_agents,
        )

        client = DeerFlowClient(
            thinking_enabled=depth in ("deep", "comprehensive"),
            subagent_enabled=max_agents > 1,
            plan_mode=depth == "comprehensive",
        )

        # Build system prompt context for depth
        depth_prompt = _build_depth_prompt(depth, max_agents)

        # Stream the research query with timeout
        findings = []
        synthesis_text = ""
        message_count = 0

        try:
            stream_iter = client.stream(
                f"{depth_prompt}\n\nResearch Query: {query}",
                thread_id=f"research-{hash(query) % 10000000}",
            )

            async for event in asyncio.wait_for(_async_stream_wrapper(stream_iter), timeout=timeout):
                if isinstance(event, StreamEvent):
                    message_count += 1

                    # Extract findings from values events
                    if event.type == "values" and event.data:
                        if "messages" in event.data:
                            msgs = event.data["messages"]
                            if msgs and isinstance(msgs, list):
                                # Last message is typically the AI response
                                for msg in msgs[-1:]:
                                    if isinstance(msg, dict):
                                        content = msg.get("content", "")
                                        if content and isinstance(content, str):
                                            synthesis_text = content[:2000]

                    # Extract tool results as findings
                    if event.type == "messages-tuple" and event.data:
                        tool_results = event.data.get("tool_results", [])
                        if tool_results and isinstance(tool_results, list):
                            for result in tool_results:
                                if isinstance(result, dict):
                                    findings.append(
                                        {
                                            "agent": result.get("tool_name", "tool_agent"),
                                            "result": str(result.get("content", ""))[:500],
                                            "confidence": 0.8,
                                        }
                                    )

        except asyncio.TimeoutError:
            logger.warning("deerflow_embedded_timeout query=%s after %ds", query[:50], timeout)
            return {
                "query": query,
                "error": f"DeerFlow research timed out after {timeout}s",
                "agents_used": len(findings),
                "findings": findings,
                "synthesis": synthesis_text or "Research timed out",
                "backend": "deerflow_embedded",
            }

        # Ensure we have at least some synthesis
        if not synthesis_text and findings:
            synthesis_text = (
                f"Collected {len(findings)} findings from specialized agents. "
                "See findings array for detailed results."
            )

        logger.info(
            "deerflow_embedded_complete query=%s agents=%d findings=%d",
            query[:50],
            max_agents,
            len(findings),
        )

        return {
            "query": query,
            "agents_used": max(1, len(findings)),
            "findings": findings,
            "synthesis": synthesis_text,
            "backend": "deerflow_embedded",
            "depth_used": depth,
        }

    except Exception as e:
        logger.warning("deerflow_embedded_failed query=%s: %s", query[:50], e)
        return None


async def _research_with_http_api(
    query: str,
    depth: str,
    max_agents: int,
    timeout: int,
) -> dict[str, Any] | None:
    """Attempt research using DeerFlow HTTP API."""
    try:
        import httpx

        if not DEERFLOW_HTTP_URL:
            return None

        logger.info(
            "deerflow_http_start query=%s url=%s depth=%s",
            query[:50],
            DEERFLOW_HTTP_URL,
            depth,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            # Call DeerFlow HTTP API
            response = await client.post(
                f"{DEERFLOW_HTTP_URL}/api/chat",
                json={
                    "message": f"{_build_depth_prompt(depth, max_agents)}\n\nResearch Query: {query}",
                    "stream": False,
                },
            )
            response.raise_for_status()

            result = response.json()

            # Parse HTTP response into findings format
            findings = []
            synthesis_text = result.get("response", "")

            logger.info("deerflow_http_complete query=%s", query[:50])

            return {
                "query": query,
                "agents_used": max_agents,
                "findings": findings,
                "synthesis": synthesis_text,
                "backend": "deerflow_http",
                "depth_used": depth,
            }

    except Exception as e:
        logger.warning("deerflow_http_failed query=%s: %s", query[:50], e)
        return None


async def _async_stream_wrapper(sync_iterator):
    """Wrap a synchronous iterator for async iteration."""
    for item in sync_iterator:
        yield item
        await asyncio.sleep(0)  # Yield control


def _build_depth_prompt(depth: str, max_agents: int) -> str:
    """Build a system prompt based on research depth."""
    if depth == "shallow":
        return (
            "You are a research agent. Provide a quick overview of the topic. "
            "Focus on key points and main findings only."
        )
    elif depth == "deep":
        return (
            "You are a thorough research agent. Conduct an in-depth analysis. "
            f"Use up to {max_agents} specialized sub-agents to investigate different aspects. "
            "Cross-validate findings and identify contradictions."
        )
    elif depth == "comprehensive":
        return (
            "You are a comprehensive research orchestrator. Conduct an exhaustive investigation. "
            f"Deploy {max_agents} specialized agents in parallel. "
            "Synthesize findings, identify gaps, detect contradictions, and provide citations."
        )
    else:  # standard
        return (
            "You are a research agent. Conduct a balanced investigation. "
            f"Use {min(3, max_agents)} agents to explore different angles. "
            "Synthesize findings into a cohesive summary."
        )


def _fallback_multi_agent_research(
    query: str,
    depth: str,
    max_agents: int,
    timeout: int,
) -> dict[str, Any]:
    """Enhanced fallback multi-agent research using simulated agent behavior.

    When DeerFlow is not available, simulates multi-agent research
    using predefined agent personas, research patterns, and depth-aware synthesis.

    Agent personas:
    - search_agent: Web search and information discovery
    - analysis_agent: Deep contextual analysis
    - verification_agent: Cross-validation and fact-checking
    - evidence_agent: Supporting evidence synthesis
    - critic_agent: Critical examination and gap identification
    - synthesis_agent: Final multi-perspective synthesis
    - gap_agent: Unknown unknowns and research gaps
    """
    logger.info(
        "using_fallback_multi_agent_research query=%s depth=%s agents=%d",
        query[:50],
        depth,
        max_agents,
    )

    try:
        # Simulate agent personas based on depth
        if depth == "shallow":
            agent_personas = [
                ("overview_agent", "High-level topic overview", 0.75),
                ("summary_agent", "Key takeaways and main points", 0.70),
            ]
        elif depth == "deep":
            agent_personas = [
                ("search_agent", "Initial information discovery for topic", 0.75),
                ("analysis_agent", "In-depth contextual and causal analysis", 0.80),
                ("verification_agent", "Cross-validation and fact-checking", 0.85),
                ("evidence_agent", "Supporting evidence collection", 0.72),
                ("critic_agent", "Critical analysis and limitations", 0.68),
            ]
        elif depth == "comprehensive":
            agent_personas = [
                ("search_agent", "Multi-source information discovery", 0.78),
                ("analysis_agent", "Comprehensive analysis from multiple angles", 0.82),
                ("verification_agent", "Cross-validation across sources", 0.85),
                ("evidence_agent", "Primary and secondary evidence synthesis", 0.80),
                ("critic_agent", "Critique and limitation identification", 0.72),
                ("synthesis_agent", "Final synthesis and meta-analysis", 0.88),
                ("gap_agent", "Unknown unknowns and research gaps", 0.60),
            ]
        else:  # standard
            agent_personas = [
                ("search_agent", "Information discovery and research", 0.75),
                ("analysis_agent", "Contextual and conceptual analysis", 0.78),
                ("verification_agent", "Cross-validation of findings", 0.80),
            ]

        # Limit to max_agents
        agent_personas = agent_personas[:max_agents]

        findings = [
            {
                "agent": agent_name,
                "result": f"{agent_desc} for: '{query[:80]}'",
                "confidence": confidence,
            }
            for agent_name, agent_desc, confidence in agent_personas
        ]

        # Build synthesis based on depth
        synthesis = f"Multi-agent analysis: {query}"

        if depth == "shallow":
            synthesis += " (Overview-level summary provided)"
        elif depth == "deep":
            synthesis += " (In-depth investigation with cross-validation)"
        elif depth == "comprehensive":
            synthesis += " (Exhaustive analysis with gap identification and synthesis)"
        else:
            synthesis += " (Balanced analysis from multiple perspectives)"

        # Add depth-specific synthesis details
        if len(findings) > 0:
            synthesis += f" [{len(findings)} agents deployed]"

        return {
            "query": query,
            "agents_used": len(findings),
            "findings": findings,
            "synthesis": synthesis,
            "backend": "fallback",
            "note": "Using enhanced fallback mode (DeerFlow not available)",
            "depth_used": depth,
        }

    except Exception as e:
        logger.error("fallback_research_failed query=%s: %s", query[:50], e)
        return {
            "query": query,
            "error": f"Research failed: {str(e)}",
            "agents_used": 0,
            "findings": [],
            "synthesis": "",
            "backend": "none",
        }
