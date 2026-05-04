#!/usr/bin/env python3
"""Detect duplicate and near-duplicate strategies in the strategy registry.

Uses fuzzy string matching (difflib.SequenceMatcher) to find near-duplicates
and reports exact dupes, near-dupes (>0.85 similarity), and unique count.

Usage:
    python scripts/strategy_dedup.py [--threshold <float>]
    python scripts/strategy_dedup.py --threshold 0.85
"""

from __future__ import annotations

import argparse
import sys
from difflib import SequenceMatcher
from pathlib import Path

# Import existing strategies
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from loom.tools.reframe_strategies import ALL_STRATEGIES


class StrategyDeduplicate:
    """Detects duplicate and near-duplicate strategies."""

    def __init__(self, threshold: float = 0.85) -> None:
        """Initialize deduplicator.

        Args:
            threshold: Similarity threshold (0.0-1.0) for near-dupes
        """
        self.threshold = threshold
        self.strategies = ALL_STRATEGIES
        self.exact_dupes: list[tuple[str, str]] = []
        self.near_dupes: list[tuple[str, str, float]] = []
        self.unique_count = 0

    def analyze(self) -> None:
        """Analyze strategies for duplicates."""
        strategy_names = sorted(self.strategies.keys())
        analyzed = set()

        print(f"Analyzing {len(strategy_names)} strategies...")
        print(f"Threshold: {self.threshold}\n")

        # Check all pairs
        for i, name1 in enumerate(strategy_names):
            for name2 in strategy_names[i + 1 :]:
                if name1 in analyzed and name2 in analyzed:
                    continue

                strategy1 = self.strategies[name1]
                strategy2 = self.strategies[name2]

                # Compare templates
                template1 = str(strategy1.get("template", "")).lower()
                template2 = str(strategy2.get("template", "")).lower()

                if not template1 or not template2:
                    continue

                similarity = self._calculate_similarity(template1, template2)

                # Exact match
                if template1 == template2:
                    self.exact_dupes.append((name1, name2))
                    analyzed.add(name2)
                # Near match
                elif similarity > self.threshold:
                    self.near_dupes.append((name1, name2, similarity))

        self.unique_count = len(strategy_names) - len(self.exact_dupes) - len(
            self.near_dupes
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0-1.0)
        """
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()

    def report(self) -> None:
        """Print analysis report."""
        print("=" * 80)
        print("STRATEGY DEDUPLICATION REPORT")
        print("=" * 80)

        print(f"\nTotal strategies: {len(self.strategies)}")
        print(f"Exact duplicates: {len(self.exact_dupes)}")
        print(f"Near-duplicates (>{self.threshold}): {len(self.near_dupes)}")
        print(f"Unique strategies: {self.unique_count}")

        if self.exact_dupes:
            print("\n" + "-" * 80)
            print("EXACT DUPLICATES")
            print("-" * 80)
            for name1, name2 in sorted(self.exact_dupes):
                print(f"  {name1} == {name2}")

        if self.near_dupes:
            print("\n" + "-" * 80)
            print(f"NEAR-DUPLICATES (>{self.threshold} similarity)")
            print("-" * 80)
            for name1, name2, similarity in sorted(
                self.near_dupes, key=lambda x: x[2], reverse=True
            ):
                print(f"  {name1} <-> {name2}  ({similarity:.2%})")

                # Show comparison
                strategy1 = self.strategies[name1]
                strategy2 = self.strategies[name2]
                template1 = strategy1.get("template", "")[:80]
                template2 = strategy2.get("template", "")[:80]
                print(f"    S1: {template1}...")
                print(f"    S2: {template2}...")

        # Category distribution
        print("\n" + "-" * 80)
        print("CATEGORY DISTRIBUTION")
        print("-" * 80)
        categories = {}
        for strategy in self.strategies.values():
            category = strategy.get("category", "uncategorized")
            categories[category] = categories.get(category, 0) + 1

        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")

        # Module distribution
        print("\n" + "-" * 80)
        print("MODULE DISTRIBUTION (by strategy name patterns)")
        print("-" * 80)

        # Group by inferred module
        module_stats = {}
        for name in sorted(self.strategies.keys()):
            # Infer module from strategy name patterns
            module = "unknown"
            if any(x in name for x in ["arabic", "lang"]):
                module = "arabic_attacks"
            elif any(x in name for x in ["token", "smuggl"]):
                module = "token_smuggling"
            elif any(x in name for x in ["fusion", "10x"]):
                module = "fusion_10x"

            if module not in module_stats:
                module_stats[module] = 0
            module_stats[module] += 1

        for module, count in sorted(module_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {module}: {count}")

        print("\n" + "=" * 80)

    def export_duplicates(self, output_file: str | Path) -> None:
        """Export duplicate information to file.

        Args:
            output_file: Output file path
        """
        import json

        output_path = Path(output_file)
        data = {
            "summary": {
                "total": len(self.strategies),
                "exact_dupes": len(self.exact_dupes),
                "near_dupes": len(self.near_dupes),
                "unique": self.unique_count,
            },
            "exact_duplicates": [
                {"strategy_a": s1, "strategy_b": s2} for s1, s2 in self.exact_dupes
            ],
            "near_duplicates": [
                {"strategy_a": s1, "strategy_b": s2, "similarity": sim}
                for s1, s2, sim in self.near_dupes
            ],
        }

        output_path.write_text(json.dumps(data, indent=2))
        print(f"Exported duplicate info to {output_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detect duplicate and near-duplicate reframing strategies"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Similarity threshold for near-dupes (default: 0.85)",
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export results to JSON file",
    )

    args = parser.parse_args()

    if not (0.0 <= args.threshold <= 1.0):
        print("Error: threshold must be between 0.0 and 1.0")
        sys.exit(1)

    dedup = StrategyDeduplicate(threshold=args.threshold)
    dedup.analyze()
    dedup.report()

    if args.export:
        dedup.export_duplicates(args.export)


if __name__ == "__main__":
    main()
