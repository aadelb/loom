#!/usr/bin/env python3
"""Extract reframing strategies from local sources.

Scans directories for strategy-related content and extracts unique patterns/templates
from Python files, Markdown files, and JSON files. Deduplicates against existing
strategies in src/loom/tools/reframe_strategies/.

Usage:
    python scripts/extract_strategies.py --scan-dir <directory> [--output <file>]
    python scripts/extract_strategies.py --scan-dir . --output new_strategies.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Import existing strategies
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from loom.tools.reframe_strategies import ALL_STRATEGIES


@dataclass
class ExtractedStrategy:
    """Extracted strategy from source code."""

    name: str
    template: str
    description: str
    category: str
    difficulty: int
    safety_flags: list[str]
    source_file: str
    line_number: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "template": self.template,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty,
            "safety_flags": self.safety_flags,
            "source": {"file": self.source_file, "line": self.line_number},
        }


class StrategyExtractor:
    """Extracts reframing strategies from source files."""

    # Keywords indicating strategy content
    STRATEGY_KEYWORDS = (
        "reframe",
        "bypass",
        "jailbreak",
        "attack",
        "inject",
        "prompt",
        "template",
        "technique",
    )

    # Pattern for extracting template strings
    TEMPLATE_PATTERN = r'["\']template["\']:\s*["\']([^"\']+)["\']'
    MULTILINE_TEMPLATE_PATTERN = r'template\s*=\s*["\'{]{1,3}(.*?)["\'{]{1,3}'

    def __init__(self) -> None:
        """Initialize extractor."""
        self.existing_names = set(ALL_STRATEGIES.keys())
        self.extracted: list[ExtractedStrategy] = []
        self.duplicates: list[str] = []

    def scan_directory(self, directory: str | Path) -> None:
        """Scan directory for strategy content.

        Args:
            directory: Directory to scan recursively
        """
        directory = Path(directory)
        if not directory.exists():
            print(f"Error: Directory {directory} does not exist")
            sys.exit(1)

        print(f"Scanning {directory} for strategy content...")

        # Scan Python files
        for py_file in directory.glob("**/*.py"):
            self._extract_from_python(py_file)

        # Scan Markdown files
        for md_file in directory.glob("**/*.md"):
            self._extract_from_markdown(md_file)

        # Scan JSON files
        for json_file in directory.glob("**/*.json"):
            self._extract_from_json(json_file)

        print(f"Found {len(self.extracted)} new strategies")
        print(f"Found {len(self.duplicates)} duplicates")

    def _extract_from_python(self, py_file: Path) -> None:
        """Extract strategies from Python file.

        Args:
            py_file: Python file to scan
        """
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IOError):
            return

        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check for strategy keywords
            if not any(keyword in line.lower() for keyword in self.STRATEGY_KEYWORDS):
                continue

            # Look for template patterns
            if "template" in line.lower() and ("=" in line or ":" in line):
                # Extract template content
                template = self._extract_template_from_line(line)
                if template:
                    name = self._generate_strategy_name(template)
                    if name not in self.existing_names and name not in [
                        s.name for s in self.extracted
                    ]:
                        strategy = ExtractedStrategy(
                            name=name,
                            template=template,
                            description=f"Extracted from {py_file.name}",
                            category="extracted",
                            difficulty=5,
                            safety_flags=["extracted", "unverified"],
                            source_file=str(py_file),
                            line_number=line_num,
                        )
                        self.extracted.append(strategy)
                    else:
                        self.duplicates.append(name)

    def _extract_from_markdown(self, md_file: Path) -> None:
        """Extract strategies from Markdown file.

        Args:
            md_file: Markdown file to scan
        """
        try:
            content = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IOError):
            return

        # Look for code blocks with strategy markers
        code_block_pattern = r"```(?:python|json)?\n(.*?)\n```"
        for match in re.finditer(code_block_pattern, content, re.DOTALL):
            block = match.group(1)
            if any(keyword in block.lower() for keyword in self.STRATEGY_KEYWORDS):
                # Try to extract strategy definition
                lines = block.split("\n")
                for line_num, line in enumerate(lines):
                    template = self._extract_template_from_line(line)
                    if template:
                        name = self._generate_strategy_name(template)
                        if name not in self.existing_names and name not in [
                            s.name for s in self.extracted
                        ]:
                            strategy = ExtractedStrategy(
                                name=name,
                                template=template,
                                description=f"Extracted from {md_file.name}",
                                category="extracted",
                                difficulty=5,
                                safety_flags=["extracted", "unverified"],
                                source_file=str(md_file),
                                line_number=match.start(),
                            )
                            self.extracted.append(strategy)
                        else:
                            self.duplicates.append(name)

    def _extract_from_json(self, json_file: Path) -> None:
        """Extract strategies from JSON file.

        Args:
            json_file: JSON file to scan
        """
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return

        # Handle list of strategy objects
        if isinstance(data, list):
            strategies = data
        elif isinstance(data, dict) and "strategies" in data:
            strategies = data["strategies"]
        else:
            return

        for item in strategies:
            if not isinstance(item, dict):
                continue

            # Check if it looks like a strategy
            if "template" in item or "strategy" in item:
                template = item.get("template") or item.get("strategy", "")
                if not template:
                    continue

                name = item.get("name") or self._generate_strategy_name(template)
                if name not in self.existing_names and name not in [
                    s.name for s in self.extracted
                ]:
                    strategy = ExtractedStrategy(
                        name=name,
                        template=str(template),
                        description=item.get("description", f"Extracted from {json_file.name}"),
                        category=item.get("category", "extracted"),
                        difficulty=item.get("difficulty", 5),
                        safety_flags=item.get("safety_flags", ["extracted", "unverified"]),
                        source_file=str(json_file),
                        line_number=0,
                    )
                    self.extracted.append(strategy)
                else:
                    self.duplicates.append(name)

    def _extract_template_from_line(self, line: str) -> str | None:
        """Extract template string from a line.

        Args:
            line: Line of code to extract template from

        Returns:
            Template string or None
        """
        # Try single-line pattern first
        match = re.search(self.TEMPLATE_PATTERN, line)
        if match:
            return match.group(1)

        # Try to extract quoted string
        quote_patterns = [r'"([^"]{20,})"', r"'([^']{20,})'", r'"""(.*?)"""', r"'''(.*?)'''"]

        for pattern in quote_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)

        return None

    def _generate_strategy_name(self, template: str) -> str:
        """Generate a strategy name from template.

        Args:
            template: Template string

        Returns:
            Generated strategy name
        """
        # Use first 5 words as basis for name
        words = re.sub(r"[^a-zA-Z0-9\s]", "", template).split()[:5]
        name = "_".join(words[:3]).lower()

        # Sanitize name
        name = re.sub(r"[^a-z0-9_]", "", name)
        if not name:
            name = "extracted_strategy"

        return name

    def output_strategies(self, output_file: str | Path | None = None) -> None:
        """Output extracted strategies.

        Args:
            output_file: Output file path (default: stdout)
        """
        output = {
            "summary": {
                "total_extracted": len(self.extracted),
                "total_duplicates": len(self.duplicates),
                "existing_count": len(self.existing_names),
            },
            "strategies": [s.to_dict() for s in self.extracted],
            "duplicates": self.duplicates,
        }

        if output_file:
            output_path = Path(output_file)
            output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
            print(f"Wrote {len(self.extracted)} strategies to {output_path}")
        else:
            print(json.dumps(output, indent=2))


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract reframing strategies from local sources"
    )
    parser.add_argument(
        "--scan-dir",
        type=str,
        required=True,
        help="Directory to scan for strategy content",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    extractor = StrategyExtractor()
    extractor.scan_directory(args.scan_dir)
    extractor.output_strategies(args.output)


if __name__ == "__main__":
    main()
