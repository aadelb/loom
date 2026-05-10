"""Migrate a single tool file to A+ quality using an AI model.

Usage:
    python scripts/a_plus/migrate_tool.py --file src/loom/tools/fetch.py --model gemini
    python scripts/a_plus/migrate_tool.py --file src/loom/tools/fetch.py --model kimi --mode implement
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import call_model, read_prompt, run_async


def migrate(file_path: Path, model: str, mode: str, dry_run: bool) -> str:
    """Run migration on a single tool file."""
    content = file_path.read_text()
    system = read_prompt("migrate_system.txt")

    user_prompt = f"""## Mode: {mode}

## File: {file_path.name}

```python
{content}
```

## Instructions
{"Implement real logic for all stubs (NotImplementedError). Use httpx with timeout=30 for network calls." if mode == "implement" else "Wrap all returns in the standard ToolResponse envelope. Add type hints. Fix bare except clauses. Add timeout=30 to network calls."}

Return ONLY the complete migrated Python file, no explanations.
"""

    response = run_async(call_model(model, system, user_prompt, max_tokens=8000))

    # Extract code block if wrapped in markdown
    if "```python" in response:
        response = response.split("```python")[1].split("```")[0]
    elif "```" in response:
        response = response.split("```")[1].split("```")[0]

    if dry_run:
        print(f"[DRY RUN] Would write {len(response)} chars to {file_path}")
        print(response[:500] + "...")
    else:
        output_path = file_path.with_suffix(".py.migrated")
        output_path.write_text(response)
        print(f"Written: {output_path} ({len(response)} chars)")

    return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate a tool to A+ quality")
    parser.add_argument("--file", required=True, help="Tool file to migrate")
    parser.add_argument("--model", required=True, choices=["gemini", "kimi", "deepseek", "nvidia"])
    parser.add_argument("--mode", default="migrate", choices=["migrate", "implement"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    migrate(file_path, args.model, args.mode, args.dry_run)


if __name__ == "__main__":
    main()
