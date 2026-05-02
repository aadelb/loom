"""Example: Using DSPy with Loom's cost-tracked LLM cascade.

This example shows how to configure DSPy to use Loom's LLM providers
with automatic cost tracking and provider fallback.
"""

import asyncio

from loom.tools.dspy_bridge import (
    research_dspy_configure,
    research_dspy_cost_report,
)


async def example_dspy_integration():
    """Configure and use DSPy with Loom's cascade."""

    # Step 1: Configure DSPy to use Loom's LLM cascade
    print("1. Configuring DSPy...")
    config_result = await research_dspy_configure(
        model="auto",  # Use config default, or specify: "gpt-4", "llama-2", etc.
        max_tokens=1500,
        temperature=0.3,
    )

    if config_result["configured"]:
        print(f"   ✓ DSPy configured: {config_result['dspy_version']}")
        print(f"   ✓ LM Class: {config_result['lm_class']}")
        print(f"   ✓ Model: {config_result['model']}")
    else:
        print(f"   ✗ Configuration failed: {config_result['error']}")
        return

    # Step 2: Use DSPy with Loom's cascade
    # Example: Define a DSPy program that uses the cascade
    try:
        import dspy

        # Create a simple DSPy module that uses Loom's cascade
        class SimpleQA(dspy.ChainOfThought):
            """Simple question-answering with chain of thought."""

            input = dspy.InputField()
            reasoning = dspy.OutputField()
            answer = dspy.OutputField()

        # The module will now automatically use Loom's LLM cascade
        # via the LoomDSPyLM class configured above
        print("\n2. DSPy modules will now use Loom's cascade...")

        # Step 3: Get cost report
        print("\n3. Cost report after DSPy calls:")
        cost_report = await research_dspy_cost_report()

        print(f"   Total calls: {cost_report['total_calls']}")
        print(
            f"   Total tokens: {cost_report['total_input_tokens']} input, "
            f"{cost_report['total_output_tokens']} output"
        )
        print(f"   Total cost: ${cost_report['estimated_cost_usd']:.5f}")
        print(f"   Providers used: {cost_report['providers_used']}")
        print(f"   Avg latency: {cost_report['avg_latency_ms']:.1f}ms")

    except ImportError:
        print("   (DSPy not installed, skipping example usage)")


async def example_cost_tracking():
    """Example showing cost tracking across DSPy calls."""
    print("Cost Tracking Example")
    print("=" * 50)

    # Configure DSPy
    await research_dspy_configure(
        model="auto",
        max_tokens=2000,
        temperature=0.5,
    )

    # After DSPy operations, get detailed cost breakdown
    report = await research_dspy_cost_report()

    print("\nCost Breakdown:")
    print(f"  Total LLM calls: {report['total_calls']}")
    print(f"  Input tokens: {report['total_input_tokens']}")
    print(f"  Output tokens: {report['total_output_tokens']}")
    print(f"  Cost (USD): ${report['estimated_cost_usd']:.5f}")
    print(f"  Avg latency (ms): {report['avg_latency_ms']:.1f}")

    if report["providers_used"]:
        print("\n  Provider Distribution:")
        for provider, count in report["providers_used"].items():
            print(f"    - {provider}: {count} calls")


if __name__ == "__main__":
    print("Loom DSPy Bridge Examples")
    print("=" * 50)

    asyncio.run(example_dspy_integration())
    asyncio.run(example_cost_tracking())

    print("\n" + "=" * 50)
    print("Examples complete!")
