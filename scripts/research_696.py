#!/usr/bin/env python3
"""
Research Task 696: Multilingual Code-Switching Attack Vectors
=============================================================

Direct invocation via loom.tools.multi_search (synchronous).
Investigates multilingual code-switching, low-resource language bypass,
Arabic-specific vectors, Unicode confusables, PINT benchmark, romanization.

Output: /opt/research-toolbox/tmp/research_696_multilingual.json
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path (same approach as run_loom.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
os.chdir('/opt/research-toolbox')

# Load .env
env_file = Path('/opt/research-toolbox/.env')
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

SEARCH_QUERIES = [
    # Primary: Code-switching attacks
    "multilingual jailbreak code switching attack LLM 2025",
    "code switching prompt injection safety bypass",
    "mixed language jailbreak confusion safety filter",

    # Secondary: Low-resource language bypass
    "Arabic English mixed prompt bypass safety",
    "low resource language LLM safety filter bypass",
    "underrepresented language safety vulnerability",

    # Tertiary: Arabic-specific vectors
    "Arabic RTL injection attack LLM safety",
    "diacritics manipulation Arabic prompt attack",
    "Arabic safety filter evasion technique",

    # Quaternary: Unicode and encoding
    "homoglyph Unicode confusables multilingual LLM",
    "Unicode normalization bypass attack",
    "script mixing attack prompt injection",

    # Quinary: Academic & benchmark
    "PINT benchmark multilingual inputs safety",
    "multilingual LLM safety evaluation 2024 2025",
    "low-resource language jailbreak benchmark",

    # Senary: Romanization attacks
    "Romanization Arabic phonetic bypass attack",
    "transliteration attack safety filter",
    "phonetic code-switching jailbreak",
]


def run_research():
    """Execute comprehensive multilingual attack research synchronously."""

    from loom.tools.multi_search import research_multi_search

    results = {
        "task_id": "RESEARCH_696",
        "title": "Multilingual Code-Switching Attack Vectors",
        "timestamp": datetime.now().isoformat(),
        "search_queries": SEARCH_QUERIES,
        "findings": {},
        "metadata": {
            "total_queries": len(SEARCH_QUERIES),
            "engines_used": ["duckduckgo", "hackernews", "reddit", "wikipedia", "arxiv"],
            "execution_mode": "live",
        }
    }

    print(f"[RESEARCH_696] Starting multilingual attack vector research")
    print(f"[RESEARCH_696] Total search queries: {len(SEARCH_QUERIES)}")
    print(f"[RESEARCH_696] Timestamp: {results['timestamp']}\n")

    success_count = 0
    error_count = 0

    # Execute multi-search across all queries (SYNCHRONOUSLY)
    for idx, query in enumerate(SEARCH_QUERIES, 1):
        print(f"[{idx}/{len(SEARCH_QUERIES)}] Searching: {query[:70]}")

        try:
            # Call multi-search tool SYNCHRONOUSLY (it manages its own event loop)
            search_results = research_multi_search(
                query=query,
                engines=["duckduckgo", "hackernews", "reddit", "wikipedia", "arxiv"],
                max_results=50,
            )

            # Count results
            result_count = 0
            if isinstance(search_results, dict) and "results" in search_results:
                result_count = len(search_results.get("results", []))

            results["findings"][query] = {
                "status": "success",
                "result_count": result_count,
                "search_result": search_results,
            }

            print(f"  ✓ Retrieved {result_count} results from {len(search_results.get('engines_queried', []))} engines\n")
            success_count += 1

        except Exception as e:
            results["findings"][query] = {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }
            print(f"  ✗ Error ({type(e).__name__}): {str(e)[:60]}\n")
            error_count += 1

    # Save results
    output_dir = Path("/opt/research-toolbox/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "research_696_multilingual.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n[RESEARCH_696] Results saved to: {output_file}")
    print(f"[RESEARCH_696] Total queries: {len(results['findings'])}")
    print(f"[RESEARCH_696] Success: {success_count}, Errors: {error_count}")

    if output_file.exists():
        file_size = output_file.stat().st_size
        print(f"[RESEARCH_696] Output file size: {file_size:,} bytes")

    return results


if __name__ == "__main__":
    try:
        results = run_research()
        print("\n[RESEARCH_696] Research complete.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[RESEARCH_696] FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
