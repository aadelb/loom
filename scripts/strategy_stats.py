#!/usr/bin/env python3
"""Analyze reframing strategy statistics and distribution.

Counts strategies per module, shows category distribution, finds underpopulated
modules (<10 strategies), and suggests rebalancing.

Usage:
    python scripts/strategy_stats.py [--min-threshold <int>]
    python scripts/strategy_stats.py --min-threshold 15
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

# Import existing strategies
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from loom.tools.reframe_strategies import ALL_STRATEGIES


class StrategyStats:
    """Analyzes strategy statistics and distribution."""

    def __init__(self, min_threshold: int = 10) -> None:
        """Initialize stats analyzer.

        Args:
            min_threshold: Minimum strategies per module threshold
        """
        self.strategies = ALL_STRATEGIES
        self.min_threshold = min_threshold
        self.module_stats: dict[str, list[str]] = defaultdict(list)
        self.category_stats: dict[str, int] = defaultdict(int)

    def analyze(self) -> None:
        """Analyze strategy distribution."""
        print(f"Analyzing {len(self.strategies)} strategies...\n")

        # Load module information
        self._map_strategies_to_modules()

        # Analyze categories
        for strategy in self.strategies.values():
            category = strategy.get("category", "uncategorized")
            self.category_stats[category] += 1

    def _map_strategies_to_modules(self) -> None:
        """Map strategies to their source modules."""
        # Get the strategies directory
        strategies_dir = (
            Path(__file__).parent.parent / "src" / "loom" / "tools" / "reframe_strategies"
        )

        # Load each module and map strategies
        module_files = list(strategies_dir.glob("*.py"))

        for module_file in sorted(module_files):
            if module_file.name.startswith("__"):
                continue

            module_name = module_file.stem

            # Read module to find strategy definitions
            try:
                content = module_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, IOError):
                continue

            # Find strategy names in this module
            for strategy_name in self.strategies.keys():
                # Look for strategy definition in module
                if f'"{strategy_name}"' in content or f"'{strategy_name}'" in content:
                    self.module_stats[module_name].append(strategy_name)

    def report(self) -> None:
        """Print analysis report."""
        print("=" * 80)
        print("STRATEGY STATISTICS REPORT")
        print("=" * 80)

        # Overview
        print(f"\nTotal strategies: {len(self.strategies)}")
        print(f"Total modules: {len(self.module_stats)}")
        print(f"Average per module: {len(self.strategies) / max(len(self.module_stats), 1):.1f}")

        # Module distribution
        print("\n" + "-" * 80)
        print("MODULE DISTRIBUTION")
        print("-" * 80)

        sorted_modules = sorted(
            self.module_stats.items(), key=lambda x: len(x[1]), reverse=True
        )

        underpopulated = []
        for module_name, strategies in sorted_modules:
            count = len(strategies)
            status = ""
            if count < self.min_threshold:
                status = " [UNDERPOPULATED]"
                underpopulated.append((module_name, count))
            print(f"  {module_name:30s} {count:3d} strategies{status}")

        # Category distribution
        print("\n" + "-" * 80)
        print("CATEGORY DISTRIBUTION")
        print("-" * 80)

        sorted_categories = sorted(
            self.category_stats.items(), key=lambda x: x[1], reverse=True
        )

        total_categorized = 0
        for category, count in sorted_categories:
            pct = (count / len(self.strategies)) * 100
            print(f"  {category:30s} {count:3d} ({pct:5.1f}%)")
            total_categorized += count

        if len(self.strategies) > total_categorized:
            uncategorized = len(self.strategies) - total_categorized
            pct = (uncategorized / len(self.strategies)) * 100
            print(f"  {'(uncategorized)':30s} {uncategorized:3d} ({pct:5.1f}%)")

        # Recommendations
        if underpopulated:
            print("\n" + "-" * 80)
            print(f"UNDERPOPULATED MODULES (<{self.min_threshold} strategies)")
            print("-" * 80)
            for module_name, count in sorted(underpopulated, key=lambda x: x[1]):
                needed = self.min_threshold - count
                print(f"  {module_name:30s} {count:3d} strategies (needs +{needed})")

            print("\n" + "-" * 80)
            print("RECOMMENDATIONS")
            print("-" * 80)

            # Suggest redistribution
            total_underpopulated = sum(count for _, count in underpopulated)
            print(f"\nTotal strategies in underpopulated modules: {total_underpopulated}")

            # Find overpopulated modules
            overpopulated = []
            avg_per_module = len(self.strategies) / len(self.module_stats)
            for module_name, strategies in sorted_modules:
                if len(strategies) > avg_per_module * 1.5:
                    overpopulated.append((module_name, len(strategies)))

            if overpopulated:
                print("\nOverpopulated modules (>1.5x average):")
                for module_name, count in overpopulated[:3]:
                    can_move = int(count - avg_per_module)
                    print(f"  {module_name}: {count} strategies (could move ~{can_move})")

            print("\nSuggestions:")
            print(f"  1. Create new specialized modules for related strategies")
            print(f"  2. Move related strategies from overpopulated modules")
            print(f"  3. Consider merging very small modules (<5 strategies)")
            print(f"  4. Extract strategies from tools/ if source code has patterns")

        # Diversity metrics
        print("\n" + "-" * 80)
        print("DIVERSITY METRICS")
        print("-" * 80)
        print(f"  Categories covered: {len(self.category_stats)}")
        print(f"  Modules with >20 strategies: {sum(1 for _, s in sorted_modules if len(s) > 20)}")
        print(f"  Modules with 10-20 strategies: {sum(1 for _, s in sorted_modules if 10 <= len(s) <= 20)}")
        print(f"  Modules with <10 strategies: {sum(1 for _, s in sorted_modules if len(s) < 10)}")

        # Size analysis
        print("\n" + "-" * 80)
        print("STRATEGY SIZE ANALYSIS")
        print("-" * 80)

        template_sizes: dict[str, int] = {}
        for key, strategy in self.strategies.items():
            template = strategy.get("template", "")
            template_sizes[key] = len(str(template))

        if template_sizes:
            sizes = list(template_sizes.values())
            avg_size = sum(sizes) / len(sizes)
            max_size = max(sizes)
            min_size = min(sizes)

            print(f"  Average template size: {avg_size:.0f} characters")
            print(f"  Maximum template size: {max_size} characters")
            print(f"  Minimum template size: {min_size} characters")

            # Find largest/smallest by key
            largest_key = max(template_sizes, key=template_sizes.get)
            smallest_key = min(template_sizes, key=template_sizes.get)

            print(f"  Largest strategy: {largest_key} ({template_sizes[largest_key]} chars)")
            print(f"  Smallest strategy: {smallest_key} ({template_sizes[smallest_key]} chars)")

        print("\n" + "=" * 80)

    def export_stats(self, output_file: str | Path) -> None:
        """Export statistics to JSON file.

        Args:
            output_file: Output file path
        """
        import json

        output_path = Path(output_file)
        data = {
            "summary": {
                "total_strategies": len(self.strategies),
                "total_modules": len(self.module_stats),
                "average_per_module": len(self.strategies) / max(len(self.module_stats), 1),
            },
            "by_module": {
                module: {
                    "count": len(strategies),
                    "strategies": strategies,
                }
                for module, strategies in sorted(
                    self.module_stats.items(), key=lambda x: len(x[1]), reverse=True
                )
            },
            "by_category": dict(
                sorted(self.category_stats.items(), key=lambda x: x[1], reverse=True)
            ),
        }

        output_path.write_text(json.dumps(data, indent=2))
        print(f"Exported statistics to {output_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze reframing strategy statistics and distribution"
    )
    parser.add_argument(
        "--min-threshold",
        type=int,
        default=10,
        help="Minimum strategies per module threshold (default: 10)",
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export statistics to JSON file",
    )

    args = parser.parse_args()

    if args.min_threshold < 1:
        print("Error: min-threshold must be >= 1")
        sys.exit(1)

    stats = StrategyStats(min_threshold=args.min_threshold)
    stats.analyze()
    stats.report()

    if args.export:
        stats.export_stats(args.export)


if __name__ == "__main__":
    main()
