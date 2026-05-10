"""Batch migrate an entire category of tools in parallel.

Usage:
    python scripts/a_plus/batch_migrate.py --category core --model gemini --parallel 3
    python scripts/a_plus/batch_migrate.py --category intelligence --model kimi --parallel 1
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import call_model, read_prompt, discover_tools_in_category


async def migrate_one(file_path: Path, model: str, semaphore: asyncio.Semaphore) -> dict:
    """Migrate a single file with concurrency control."""
    async with semaphore:
        content = file_path.read_text()
        system = read_prompt("migrate_system.txt")
        user_prompt = f"""## File: {file_path.name}

```python
{content}
```

## Instructions
Wrap all returns in the standard ToolResponse envelope. Add type hints. Fix bare except clauses. Add timeout=30 to network calls. Return ONLY the complete migrated Python file.
"""
        try:
            response = await call_model(model, system, user_prompt, max_tokens=8000)
            if "```python" in response:
                response = response.split("```python")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            output_path = file_path.with_suffix(".py.migrated")
            output_path.write_text(response)
            return {"file": str(file_path), "status": "ok", "output": str(output_path)}
        except Exception as e:
            return {"file": str(file_path), "status": "error", "error": str(e)}


async def batch_migrate(category: str, model: str, parallel: int, dry_run: bool) -> None:
    """Migrate all tools in a category."""
    tool_files = discover_tools_in_category(category)
    print(f"Found {len(tool_files)} tool files in category '{category}'")

    if dry_run:
        for f in tool_files:
            print(f"  [DRY RUN] Would migrate: {f}")
        return

    semaphore = asyncio.Semaphore(parallel)
    tasks = [migrate_one(f, model, semaphore) for f in tool_files]
    results = await asyncio.gather(*tasks)

    ok = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "error"]

    print(f"\nResults: {len(ok)} OK, {len(errors)} errors")
    for e in errors:
        print(f"  ERROR: {e['file']} — {e['error']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch migrate tools to A+ quality")
    parser.add_argument("--category", required=True, help="Registration category")
    parser.add_argument("--model", required=True, choices=["gemini", "kimi", "deepseek", "nvidia"])
    parser.add_argument("--parallel", type=int, default=3, help="Max concurrent migrations")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(batch_migrate(args.category, args.model, args.parallel, args.dry_run))


if __name__ == "__main__":
    main()
