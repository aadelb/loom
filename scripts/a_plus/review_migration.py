"""AI-powered code review of migrated tool files.

Usage:
    python scripts/a_plus/review_migration.py --file src/loom/tools/fetch.py --reviewer deepseek
    python scripts/a_plus/review_migration.py --category core --reviewer deepseek
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import call_model, read_prompt, discover_tools_in_category


async def review_one(original: Path, reviewer: str) -> dict:
    """Review a single migrated file against its original."""
    migrated = original.with_suffix(".py.migrated")
    if not migrated.exists():
        return {"file": str(original), "status": "skip", "reason": "no .migrated file"}

    original_content = original.read_text()
    migrated_content = migrated.read_text()

    system = read_prompt("review_system.txt")
    user_prompt = f"""## Original: {original.name}
```python
{original_content}
```

## Migrated: {original.name} (A+ version)
```python
{migrated_content}
```

## Review Instructions
1. Check: Does it preserve the same function signatures (name + params)?
2. Check: Are all returns wrapped in dict with source/category/elapsed_ms?
3. Check: No bare except clauses?
4. Check: Type hints on all signatures?
5. Check: Network calls have timeout?
6. Check: No hardcoded secrets?
7. Check: No NotImplementedError remaining?

Respond with:
VERDICT: PASS or FAIL
ISSUES: (list of issues, or "none")
"""

    try:
        response = await call_model(reviewer, system, user_prompt, max_tokens=2000)
        verdict = "PASS" if "VERDICT: PASS" in response.upper() else "FAIL"
        return {"file": str(original), "status": verdict, "review": response}
    except Exception as e:
        return {"file": str(original), "status": "error", "error": str(e)}


def main() -> None:
    parser = argparse.ArgumentParser(description="AI code review of migrations")
    parser.add_argument("--file", help="Single file to review")
    parser.add_argument("--category", help="Category to review")
    parser.add_argument("--reviewer", default="deepseek", choices=["deepseek", "gemini", "nvidia"])
    args = parser.parse_args()

    if args.file:
        files = [Path(args.file)]
    elif args.category:
        files = discover_tools_in_category(args.category)
    else:
        print("Specify --file or --category", file=sys.stderr)
        sys.exit(1)

    results = asyncio.run(asyncio.gather(*[review_one(f, args.reviewer) for f in files]))

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    skipped = [r for r in results if r["status"] == "skip"]
    errors = [r for r in results if r["status"] == "error"]

    print(f"\nReview Results: {len(passed)} PASS, {len(failed)} FAIL, {len(skipped)} skipped, {len(errors)} errors")
    for r in failed:
        print(f"\n  FAIL: {r['file']}")
        print(f"  {r.get('review', '')[:200]}")


if __name__ == "__main__":
    main()
