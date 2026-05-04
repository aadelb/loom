#!/usr/bin/env python3
"""Verification script for tool_dependencies integration.

Tests:
1. Dependency graph exists and contains expected tools
2. get_execution_plan generates valid topological ordering
3. resolve_dependencies transitively resolves all prerequisites
4. validate_execution_order validates ordering correctness
5. Cycle detection (if any)

Run: python verify_tool_dependencies.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_dependency_graph():
    """Test 1: Verify dependency graph structure."""
    from loom.tools.tool_dependencies import DEPENDENCY_GRAPH

    print("Test 1: Dependency Graph Structure")
    print(f"  Total tools: {len(DEPENDENCY_GRAPH)}")
    print(f"  Sample tools: {list(DEPENDENCY_GRAPH.keys())[:5]}")

    # Verify leaf tools exist
    leaf_tools = [t for t, deps in DEPENDENCY_GRAPH.items() if not deps]
    print(f"  Leaf tools (no dependencies): {len(leaf_tools)}")
    assert len(leaf_tools) > 0, "Should have leaf tools"

    # Verify research_deep has dependencies
    assert DEPENDENCY_GRAPH["research_deep"], "research_deep should have dependencies"
    assert "research_search" in DEPENDENCY_GRAPH["research_deep"]
    assert "research_fetch" in DEPENDENCY_GRAPH["research_deep"]

    print("  ✓ Dependency graph structure is valid\n")


async def test_resolve_dependencies():
    """Test 2: Dependency resolution."""
    from loom.tools.tool_dependencies import resolve_dependencies

    print("Test 2: Dependency Resolution")

    # Test single tool
    deps = resolve_dependencies(["research_deep"])
    print(f"  Dependencies for research_deep: {sorted(deps)}")
    assert "research_search" in deps
    assert "research_fetch" in deps
    assert "research_deep" in deps
    print(f"  Total: {len(deps)} tools")

    # Test multiple tools
    deps2 = resolve_dependencies(["research_deep", "research_github"])
    assert len(deps2) > len(deps), "Multiple tools should have more deps"
    print(f"  Dependencies for [research_deep, research_github]: {len(deps2)} tools")

    print("  ✓ Dependency resolution works correctly\n")


async def test_execution_plan():
    """Test 3: Execution plan generation."""
    from loom.tools.tool_dependencies import get_execution_plan, validate_execution_order

    print("Test 3: Execution Plan Generation")

    plan = get_execution_plan(["research_deep"])
    print(f"  Execution groups for research_deep:")
    for i, group in enumerate(plan):
        print(f"    Group {i}: {group}")

    # Validate the plan
    validation = validate_execution_order(plan)
    assert validation["valid"], f"Plan should be valid: {validation}"
    print(f"  Plan is topologically sorted: {validation['valid']}")

    # Test multiple tools
    plan2 = get_execution_plan(["research_deep", "research_full_pipeline"])
    print(f"  Execution groups for [research_deep, research_full_pipeline]: {len(plan2)} groups")
    validation2 = validate_execution_order(plan2)
    assert validation2["valid"], "Plan should be valid"

    print("  ✓ Execution plans are valid and topologically sorted\n")


async def test_research_tool_dependencies():
    """Test 4: research_tool_dependencies function."""
    from loom.tools.tool_dependencies import research_tool_dependencies

    print("Test 4: research_tool_dependencies Function")

    result = await research_tool_dependencies("research_deep")
    print(f"  Tool: {result['tool']}")
    print(f"  Direct dependencies: {result['direct_deps']}")
    print(f"  Transitive dependencies: {len(result['transitive_deps'])} tools")
    print(f"  Execution order groups: {len(result['execution_order'])} groups")

    assert result["tool"] == "research_deep"
    assert len(result["transitive_deps"]) > 0
    assert len(result["execution_order"]) > 0
    assert not result["is_leaf_tool"]

    print("  ✓ Function returns correct structure\n")


async def test_get_execution_plan_function():
    """Test 5: research_get_execution_plan function."""
    from loom.tools.tool_dependencies import research_get_execution_plan

    print("Test 5: research_get_execution_plan Function")

    result = await research_get_execution_plan(["research_deep", "research_github"])
    print(f"  Requested tools: {result['requested_tools']}")
    print(f"  All tools needed: {len(result['all_tools_needed'])} tools")
    print(f"  Execution plan groups: {len(result['execution_plan'])} groups")
    print(f"  Estimated speedup: {result['estimated_speedup']:.2f}x")

    assert len(result["all_tools_needed"]) >= 2
    assert len(result["execution_plan"]) > 0

    print("  ✓ Execution plan function works correctly\n")


async def test_dependency_graph_stats():
    """Test 6: Graph statistics."""
    from loom.tools.tool_dependencies import research_dependency_graph_stats

    print("Test 6: Dependency Graph Statistics")

    stats = await research_dependency_graph_stats()
    print(f"  Total tools: {stats['total_tools']}")
    print(f"  Total dependencies: {stats['total_dependencies']}")
    print(f"  Leaf tools: {stats['leaf_tools_count']}")
    print(f"  Root tools: {stats['root_tools_count']}")
    print(f"  Max dependency depth: {stats['max_dependency_depth']}")
    print(f"  Avg dependency depth: {stats['avg_dependency_depth']}")
    print(f"  Graph density: {stats['graph_density']:.4f}")

    assert stats["total_tools"] > 0
    assert stats["max_dependency_depth"] >= 0

    print("  ✓ Statistics computed correctly\n")


async def test_pipeline_enhancer_functions():
    """Test 7: Pipeline enhancer new functions exist."""
    from loom.tools import pipeline_enhancer

    print("Test 7: Pipeline Enhancer Functions")

    # Check that new functions exist
    assert hasattr(pipeline_enhancer, "research_enhance_with_dependencies")
    assert hasattr(pipeline_enhancer, "research_compose_pipeline")
    assert callable(getattr(pipeline_enhancer, "research_enhance_with_dependencies"))
    assert callable(getattr(pipeline_enhancer, "research_compose_pipeline"))

    print("  ✓ New functions exist in pipeline_enhancer module\n")


async def test_prepare_tool_execution():
    """Test 8: prepare_tool_execution integration hook."""
    from loom.tools.tool_dependencies import prepare_tool_execution

    print("Test 8: prepare_tool_execution Integration Hook")

    result = await prepare_tool_execution(["research_deep"])
    print(f"  Requested tools: {result['requested_tools']}")
    print(f"  All tools to execute: {len(result['all_tools'])} tools")
    print(f"  First execution group: {result['first_group']}")
    print(f"  Remaining groups: {len(result['remaining_groups'])} groups")
    print(f"  Valid execution plan: {result['valid']}")

    assert result["requested_tools"] == ["research_deep"]
    assert len(result["all_tools"]) >= 1
    assert result["valid"]

    print("  ✓ prepare_tool_execution hook works correctly\n")


async def run_all_tests():
    """Run all verification tests."""
    print("=" * 70)
    print("Tool Dependencies Integration Verification")
    print("=" * 70)
    print()

    try:
        await test_dependency_graph()
        await test_resolve_dependencies()
        await test_execution_plan()
        await test_research_tool_dependencies()
        await test_get_execution_plan_function()
        await test_dependency_graph_stats()
        await test_pipeline_enhancer_functions()
        await test_prepare_tool_execution()

        print("=" * 70)
        print("✅ All tests passed!")
        print("=" * 70)
        return True

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Test failed: {e}")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
