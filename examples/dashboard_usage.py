"""Example usage of the Loom Attack Visualization Dashboard.

This example shows how to:
1. Create and populate a dashboard with attack events
2. Retrieve event logs for analysis
3. Generate summary statistics
4. Create a standalone HTML visualization
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loom.dashboard import AttackDashboard


def example_basic_usage() -> None:
    """Basic dashboard usage example."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Dashboard Usage")
    print("=" * 60)

    dashboard = AttackDashboard()

    # Add events as attacks are executed
    dashboard.add_event(
        "strategy_applied",
        {"strategy": "prompt_injection", "model": "gpt-4"},
    )
    dashboard.add_event(
        "model_response",
        {"response": "I cannot help with that request"},
    )
    dashboard.add_event(
        "attack_failure",
        {"model": "gpt-4", "reason": "safety_filter", "hcs_score": 10},
    )

    dashboard.add_event(
        "strategy_applied",
        {"strategy": "roleplay", "model": "gpt-4"},
    )
    dashboard.add_event(
        "model_response",
        {"response": "Sure, I can help with that"},
    )
    dashboard.add_event(
        "attack_success",
        {"model": "gpt-4", "hcs_score": 82},
    )

    # Get summary
    summary = dashboard.get_summary()
    print(f"\nAttack Summary:")
    print(f"  Total attacks: {summary['total_attacks']}")
    print(f"  Successes: {summary['successes']}")
    print(f"  Failures: {summary['failures']}")
    print(f"  Success rate: {summary['success_rate']:.1f}%")
    print(f"  Avg HCS score: {summary['avg_hcs_score']:.1f}")


def example_strategy_analysis() -> None:
    """Analyze strategy effectiveness."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Strategy Analysis")
    print("=" * 60)

    dashboard = AttackDashboard()

    # Test multiple strategies
    strategies = ["prompt_injection", "roleplay", "jailbreak_v2", "academic_framing"]

    for strategy in strategies:
        # Apply strategy
        dashboard.add_event("strategy_applied", {"strategy": strategy})

        # Simulate variable success
        import random

        success = random.random() > (0.3 + len(strategy) / 100)

        if success:
            dashboard.add_event(
                "attack_success",
                {
                    "strategy": strategy,
                    "model": "gpt-4",
                    "hcs_score": random.randint(50, 95),
                },
            )
        else:
            dashboard.add_event(
                "attack_failure",
                {
                    "strategy": strategy,
                    "model": "gpt-4",
                },
            )

    summary = dashboard.get_summary()
    print("\nTop Strategies:")
    for i, strategy in enumerate(summary["top_strategies"], 1):
        print(
            f"  {i}. {strategy['name']}: {strategy['attempts']} attempts, "
            f"{strategy['successes']} successes ({strategy['rate']:.1f}%)"
        )


def example_event_filtering() -> None:
    """Filter and retrieve specific events."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Event Filtering")
    print("=" * 60)

    dashboard = AttackDashboard()

    # Generate 20 events
    for i in range(20):
        event_type = (
            "attack_success" if i % 3 == 0 else
            "attack_failure" if i % 3 == 1 else
            "strategy_applied"
        )
        dashboard.add_event(
            event_type,
            {"attempt": i, "model": f"model_{i % 3}"},
        )

    # Retrieve events from index 10 onwards
    recent_events = dashboard.get_events(since=10)
    print(f"\nRecent events (indices 10-19):")
    print(f"  Total: {len(recent_events)}")
    print(f"  First: {recent_events[0]['type']} at index {recent_events[0]['index']}")
    print(f"  Last: {recent_events[-1]['type']} at index {recent_events[-1]['index']}")


def example_html_generation() -> None:
    """Generate standalone HTML dashboard."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: HTML Dashboard Generation")
    print("=" * 60)

    dashboard = AttackDashboard()

    # Populate with sample data
    models = ["gpt-4", "claude", "llama-2", "mistral"]
    strategies = ["prompt_injection", "roleplay", "jailbreak", "subtle_redirect"]

    import random

    for i in range(50):
        model = random.choice(models)
        strategy = random.choice(strategies)

        dashboard.add_event(
            "strategy_applied",
            {"strategy": strategy, "model": model},
        )

        if random.random() > 0.4:  # 60% success rate
            dashboard.add_event(
                "attack_success",
                {
                    "strategy": strategy,
                    "model": model,
                    "hcs_score": random.randint(40, 95),
                },
            )
        else:
            dashboard.add_event(
                "attack_failure",
                {
                    "strategy": strategy,
                    "model": model,
                    "reason": "safety_filter",
                },
            )

    # Generate HTML
    html = dashboard.generate_html()

    # Save to file
    output_file = Path(__file__).parent.parent / "dashboard.html"
    with open(output_file, "w") as f:
        f.write(html)

    print(f"\nHTML dashboard generated:")
    print(f"  File: {output_file}")
    print(f"  Size: {len(html):,} bytes")

    summary = dashboard.get_summary()
    print(f"\nDashboard statistics:")
    print(f"  Total events: {summary['event_count']}")
    print(f"  Total attacks: {summary['total_attacks']}")
    print(f"  Success rate: {summary['success_rate']:.1f}%")
    print(f"  Avg HCS: {summary['avg_hcs_score']:.1f}")
    print(f"  Models tested: {len(summary['active_models'])}")
    print(f"  Strategies tested: {len(summary['model_stats'])}")


def example_realtime_updates() -> None:
    """Simulate real-time dashboard updates."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Real-time Updates")
    print("=" * 60)

    dashboard = AttackDashboard()

    print("\nSimulating real-time attack progression:")

    for attempt in range(1, 6):
        print(f"\n  Attack #{attempt}:")

        dashboard.add_event(
            "strategy_applied",
            {"strategy": f"strategy_{attempt}", "model": "gpt-4"},
        )
        print(f"    - Strategy applied: strategy_{attempt}")

        import time
        time.sleep(0.1)

        import random

        success = random.random() > 0.4
        if success:
            dashboard.add_event(
                "attack_success",
                {"hcs_score": random.randint(60, 90)},
            )
            print(f"    - Attack succeeded!")
        else:
            dashboard.add_event("attack_failure", {})
            print(f"    - Attack failed")

        summary = dashboard.get_summary()
        print(
            f"    - Overall success rate: {summary['success_rate']:.1f}% "
            f"({summary['successes']}/{summary['total_attacks']})"
        )


if __name__ == "__main__":
    example_basic_usage()
    example_strategy_analysis()
    example_event_filtering()
    example_html_generation()
    example_realtime_updates()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
