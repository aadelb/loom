#!/usr/bin/env python3
"""Example: Using the session replay tools to debug research workflows.

This demonstrates how to record tool calls during a research workflow,
then replay the session for debugging and analysis.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loom.tools.session_replay import (
    research_session_record,
    research_session_replay,
    research_session_list,
)


async def main():
    """Demonstrate session recording and replay."""

    print("=== Session Replay Tool Demo ===\n")

    # Simulate a research workflow by recording multiple tool calls
    print("1. Recording a research workflow...")
    session_id = "research_workflow_001"

    # Record first tool call (research_fetch)
    result = await research_session_record(
        session_id=session_id,
        tool_name="research_fetch",
        params={"url": "https://example.com", "timeout": 30},
        result_summary="Fetched 15KB of HTML content",
        duration_ms=2500.0,
    )
    print(f"   Step {result['step_number']}: {result['timestamp']}")

    # Record second tool call (research_markdown)
    result = await research_session_record(
        session_id=session_id,
        tool_name="research_markdown",
        params={"html_size": "15KB"},
        result_summary="Converted to 8KB markdown",
        duration_ms=1200.0,
    )
    print(f"   Step {result['step_number']}: {result['timestamp']}")

    # Record third tool call (research_llm_summarize)
    result = await research_session_record(
        session_id=session_id,
        tool_name="research_llm_summarize",
        params={"provider": "groq", "model": "mixtral-8x7b"},
        result_summary="Generated 3-sentence summary using Groq",
        duration_ms=3400.0,
    )
    print(f"   Step {result['step_number']}: {result['timestamp']}\n")

    # Record a different workflow
    print("2. Recording a second workflow...")
    session_id2 = "search_analysis_002"

    for i, tool in enumerate(["research_search", "research_deep"], 1):
        result = await research_session_record(
            session_id=session_id2,
            tool_name=tool,
            params={"query": "machine learning safety"},
            result_summary=f"Step {i} completed successfully",
            duration_ms=1500.0 + i * 500,
        )
        print(f"   Step {result['step_number']}: {result['timestamp']}")

    print()

    # List all recorded sessions
    print("3. Listing all recorded sessions...")
    sessions_result = await research_session_list()
    print(f"   Total sessions: {sessions_result['total_sessions']}\n")

    for session in sessions_result["sessions"]:
        print(f"   Session: {session['id']}")
        print(f"   - Steps: {session['steps_count']}")
        print(f"   - Total duration: {session['total_duration_ms']}ms")
        print(f"   - First step: {session['first_step_at']}")
        print(f"   - Last step: {session['last_step_at']}\n")

    # Replay a specific session
    print("4. Replaying workflow_001...")
    replay_result = await research_session_replay("research_workflow_001")

    print(f"   Session: {replay_result['session_id']}")
    print(f"   Total steps: {replay_result['total_steps']}")
    print(f"   Total duration: {replay_result['total_duration_ms']}ms\n")

    print("   Workflow timeline:")
    for step in replay_result["steps"]:
        print(
            f"   [{step['step']}] {step['tool']} "
            f"({step['duration_ms']}ms) @ {step['timestamp']}"
        )
        print(f"       Result: {step['result_summary']}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
