"""Examples of using the Tool Composition DSL (Composer).

This file demonstrates practical usage patterns for the research_compose
and research_compose_validate functions.
"""

import asyncio
from loom.tools.composer import research_compose, research_compose_validate


# ──────────────────────────────────────────────────────────────────────────
# Example 1: Simple Sequential Pipeline
# ──────────────────────────────────────────────────────────────────────────


async def example_simple_search():
    """Search for content and fetch the first result."""
    result = await research_compose(
        pipeline="search(python vulnerabilities) | fetch($.urls[0]) | markdown($)",
        initial_input="",
    )

    print("Example 1: Simple Search Pipeline")
    print(f"Success: {result['success']}")
    print(f"Execution time: {result['execution_time_ms']:.2f}ms")
    print(f"Steps executed: {len(result['steps'])}")
    if not result["success"]:
        print(f"Errors: {result['errors']}")


# ──────────────────────────────────────────────────────────────────────────
# Example 2: Parallel OSINT Sweep
# ──────────────────────────────────────────────────────────────────────────


async def example_parallel_osint():
    """Execute parallel OSINT tools."""
    result = await research_compose(
        pipeline="search(target.com) & github(target.com) | merge($)",
        initial_input="",
    )

    print("\nExample 2: Parallel OSINT")
    print(f"Success: {result['success']}")
    print(f"Steps: {[step['tool'] for step in result['steps']]}")
    if result["success"]:
        merged_data = result["output"]
        print(f"Merged sources: {merged_data.get('sources', [])}")


# ──────────────────────────────────────────────────────────────────────────
# Example 3: Using Pipeline Aliases
# ──────────────────────────────────────────────────────────────────────────


async def example_deep_research():
    """Use a built-in pipeline alias."""
    result = await research_compose(
        pipeline="deep_research",
        initial_input="AI safety research",
    )

    print("\nExample 3: Deep Research Alias")
    print(f"Success: {result['success']}")
    print(f"Expanded pipeline: {result.get('expanded_pipeline', 'N/A')}")


# ──────────────────────────────────────────────────────────────────────────
# Example 4: Validate Before Executing
# ──────────────────────────────────────────────────────────────────────────


def example_validate_pipeline():
    """Validate a pipeline before execution."""
    pipeline = "search(query) | fetch($.urls[0]) | markdown($) | llm_summarize($)"

    validation = research_compose_validate(pipeline)

    print("\nExample 4: Pipeline Validation")
    print(f"Valid: {validation['valid']}")
    print(f"Steps: {len(validation['steps'])}")
    print(f"Step names: {[step['tool_name'] for step in validation['steps']]}")

    if not validation["valid"]:
        print(f"Errors: {validation['errors']}")


# ──────────────────────────────────────────────────────────────────────────
# Example 5: Complex Field References
# ──────────────────────────────────────────────────────────────────────────


async def example_field_references():
    """Use field references to access nested results."""
    result = await research_compose(
        pipeline="search(query) | spider($.urls[:5]) | markdown($)",
        initial_input="cybersecurity threats",
    )

    print("\nExample 5: Field References")
    print(f"Success: {result['success']}")
    print(f"Final output type: {type(result['output']).__name__}")
    print(f"Step results count: {len(result['step_results'])}")


# ──────────────────────────────────────────────────────────────────────────
# Example 6: Continue on Error
# ──────────────────────────────────────────────────────────────────────────


async def example_continue_on_error():
    """Execute pipeline and continue despite errors."""
    result = await research_compose(
        pipeline="fetch(bad_url) | markdown($) | llm_summarize($)",
        continue_on_error=True,
    )

    print("\nExample 6: Continue on Error")
    print(f"Success: {result['success']}")
    print(f"Errors encountered: {len(result['errors'])}")
    for error in result["errors"]:
        print(f"  - {error}")
    print(f"Partial results available: {len([r for r in result['step_results'] if r is not None])}")


# ──────────────────────────────────────────────────────────────────────────
# Example 7: With Timeout
# ──────────────────────────────────────────────────────────────────────────


async def example_with_timeout():
    """Execute pipeline with a timeout."""
    result = await research_compose(
        pipeline="search(query) | fetch($.urls[0]) | markdown($)",
        timeout_ms=30000,  # 30 second timeout
    )

    print("\nExample 7: With Timeout")
    print(f"Execution time: {result['execution_time_ms']:.2f}ms")
    print(f"Completed within timeout: {result['execution_time_ms'] < 30000}")


# ──────────────────────────────────────────────────────────────────────────
# Example 8: Multi-step Chain
# ──────────────────────────────────────────────────────────────────────────


async def example_multi_step():
    """Execute a complex multi-step pipeline."""
    result = await research_compose(
        pipeline="search(python) & github(python) | merge($) | llm_summarize($)",
    )

    print("\nExample 8: Multi-step Chain")
    print(f"Total steps: {len(result['steps'])}")
    for i, step in enumerate(result["steps"]):
        print(f"  Step {i}: {step['tool']} - {step['status']}")


# ──────────────────────────────────────────────────────────────────────────
# Example 9: Error Handling Pattern
# ──────────────────────────────────────────────────────────────────────────


async def example_error_handling():
    """Proper error handling pattern."""
    pipeline = "search(query) | fetch($.urls[0]) | markdown($)"

    # Step 1: Validate
    validation = research_compose_validate(pipeline)
    if not validation["valid"]:
        print("\nExample 9: Error Handling")
        print(f"Validation failed: {validation['errors']}")
        return

    # Step 2: Execute
    result = await research_compose(pipeline, continue_on_error=False)

    if result["success"]:
        print("\nExample 9: Error Handling")
        print(f"Pipeline succeeded!")
        print(f"Final result type: {type(result['output']).__name__}")
    else:
        print("\nExample 9: Error Handling")
        print(f"Pipeline failed: {result['errors']}")
        print(f"Failed at step(s): {[s for s in result['steps'] if s['status'] == 'error']}")


# ──────────────────────────────────────────────────────────────────────────
# Example 10: Composite Pipeline with Merge
# ──────────────────────────────────────────────────────────────────────────


async def example_composite_pipeline():
    """Combine search, GitHub, and social graph analysis."""
    result = await research_compose(
        pipeline="search(target) & github(target) & social_graph(target) | merge($)",
    )

    print("\nExample 10: Composite Pipeline with Merge")
    print(f"Success: {result['success']}")

    if result["success"] and isinstance(result["output"], dict):
        merged = result["output"]
        print(f"Merged data sources: {merged.get('sources', [])}")
        print(f"Data keys: {list(merged.get('data', {}).keys())}")


# ──────────────────────────────────────────────────────────────────────────
# Main: Run Examples
# ──────────────────────────────────────────────────────────────────────────


async def main():
    """Run all examples."""
    print("=" * 70)
    print("Tool Composition DSL (Composer) — Usage Examples")
    print("=" * 70)

    # Synchronous examples
    example_validate_pipeline()

    # Asynchronous examples
    # Note: These may fail if tools are not available,
    # but demonstrate the correct usage patterns

    try:
        await example_simple_search()
    except Exception as e:
        print(f"Example 1 skipped (tools not available): {type(e).__name__}")

    try:
        await example_parallel_osint()
    except Exception as e:
        print(f"Example 2 skipped (tools not available): {type(e).__name__}")

    try:
        await example_deep_research()
    except Exception as e:
        print(f"Example 3 skipped (tools not available): {type(e).__name__}")

    try:
        await example_field_references()
    except Exception as e:
        print(f"Example 5 skipped (tools not available): {type(e).__name__}")

    try:
        await example_continue_on_error()
    except Exception as e:
        print(f"Example 6 skipped (tools not available): {type(e).__name__}")

    try:
        await example_with_timeout()
    except Exception as e:
        print(f"Example 7 skipped (tools not available): {type(e).__name__}")

    try:
        await example_error_handling()
    except Exception as e:
        print(f"Example 9 skipped (tools not available): {type(e).__name__}")

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
