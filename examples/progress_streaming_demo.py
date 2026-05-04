#!/usr/bin/env python3
"""Demo script showing SSE progress streaming with research_deep_with_progress.

This example demonstrates:
1. Starting a long-running research task
2. Subscribing to progress updates via HTTP
3. Parsing SSE events
4. Displaying progress in real-time

Run:
    python3 examples/progress_streaming_demo.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

try:
    import httpx
except ImportError:
    print("Error: httpx required. Install with: pip install httpx")
    sys.exit(1)


async def stream_progress(base_url: str, job_id: str) -> None:
    """Stream progress events for a job via SSE.

    Args:
        base_url: Base URL of Loom server (e.g., "http://localhost:8787")
        job_id: Job ID to stream progress for
    """
    url = f"{base_url}/progress/{job_id}"
    print(f"Streaming progress from: {url}\n")

    try:
        with httpx.stream("GET", url) as response:
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return

            for line in response.iter_lines():
                if not line:
                    continue

                if line.startswith("data: "):
                    try:
                        data_json = line[6:]  # Remove "data: " prefix
                        event = json.loads(data_json)

                        # Display progress
                        stage = event.get("stage", "unknown")
                        percent = event.get("percent", 0)
                        message = event.get("message", "")
                        timestamp = event.get("timestamp", "")

                        # Simple progress bar
                        bar_length = 30
                        filled = int(bar_length * percent / 100)
                        bar = "█" * filled + "░" * (bar_length - filled)

                        print(
                            f"[{percent:3d}%] {bar} | {stage:12s} | {message}"
                        )

                        # Stop on complete or error
                        if stage in ("complete", "error"):
                            print(f"\nPipeline finished at {timestamp}")
                            break

                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON: {e}")
                        print(f"Raw line: {line}")

    except httpx.ConnectError:
        print(f"Error: Could not connect to {base_url}")
        print("Make sure the Loom server is running:")
        print("  loom serve")
    except KeyboardInterrupt:
        print("\n\nStream interrupted by user")


async def start_research_task(base_url: str, query: str) -> str:
    """Start a research task via MCP tool.

    Note: This is a placeholder showing how to integrate with the MCP client.
    In practice, you would call research_deep_with_progress() directly if you're
    in the same process, or use an MCP client to invoke it.

    Args:
        base_url: Base URL of Loom server
        query: Research query

    Returns:
        Job ID from the response
    """
    print(f"Starting research task: {query}")
    print("(Note: In this demo, we'll use a hardcoded job_id)")
    print("In production, the research tool would return the job_id\n")

    # For demonstration, we'll use a fixed job_id
    # In production, this would come from the research tool response
    job_id = "demo-job-550e8400-e29b-41d4-a716-446655440000"
    return job_id


async def demo_direct_progress() -> None:
    """Demonstrate progress tracking directly (without HTTP)."""
    from loom.progress import get_progress_tracker, create_job_id

    print("\n" + "=" * 60)
    print("DEMO 2: Direct Progress Tracking (In-Process)")
    print("=" * 60 + "\n")

    tracker = get_progress_tracker()
    job_id = create_job_id()

    print(f"Job ID: {job_id}\n")

    # Simulate a pipeline
    stages = [
        ("initialize", 0, "Starting pipeline"),
        ("search", 20, "Searching across 3 providers"),
        ("fetch", 50, "Fetching and processing results"),
        ("extract", 75, "Extracting with LLM"),
        ("complete", 100, "Done!"),
    ]

    # Report progress
    print("Reporting progress...")
    for stage, percent, message in stages:
        await tracker.report_progress(
            job_id=job_id,
            stage=stage,
            percent=percent,
            message=message,
        )
        print(f"  [{percent:3d}%] {stage:12s} | {message}")
        await asyncio.sleep(0.5)

    # Collect events
    print("\nCollecting events from queue...")
    events = []

    async def collect() -> None:
        count = 0
        async for event in tracker.get_events(job_id):
            events.append(event)
            count += 1
            print(f"  Received event {count}: {event.stage}")
            if count >= len(stages):
                break

    await asyncio.wait_for(collect(), timeout=5)

    print(f"\nTotal events: {len(events)}")
    print("Events collected successfully!\n")

    # Cleanup
    await tracker.cleanup(job_id)


async def main() -> None:
    """Run the demo."""
    print("=" * 60)
    print("Loom SSE Progress Streaming Demo")
    print("=" * 60 + "\n")

    print("DEMO 1: HTTP SSE Streaming (requires running server)")
    print("-" * 60)
    base_url = "http://localhost:8787"

    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}/health", timeout=2)
            if resp.status_code == 200:
                print("Loom server is running!\n")

                # Start a research task
                # job_id = await start_research_task(base_url, "Python async patterns")

                # For now, show a demo with a synthetic job_id
                job_id = "demo-job-550e8400-e29b-41d4-a716-446655440000"
                print(f"Demo job_id: {job_id}")
                print("\nTo test streaming, in another terminal:")
                print(f"  curl -N {base_url}/progress/{job_id}")
                print()

                # Stream progress (won't show anything if no real task)
                # await stream_progress(base_url, job_id)

            else:
                print(f"Unexpected response: {resp.status_code}")
    except (httpx.ConnectError, httpx.TimeoutException):
        print("Loom server not running.")
        print("To start the server:")
        print("  loom serve")
        print()

    # Demo 2: Direct in-process progress tracking
    await demo_direct_progress()

    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
