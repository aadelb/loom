#!/usr/bin/env python3
"""Test top 20 tools by importing modules directly (avoids FastMCP instantiation)."""
import sys
import asyncio
import json
import time

# Add source to path
sys.path.insert(0, "/opt/research-toolbox/src")


async def run_tests():
    """Run test suite by importing tool modules."""
    results = []

    # Test list of tools to validate (module_name, tool_name, import_path)
    # import_path can be different from module_name if the function is in a different location
    tools_to_test = [
        ("search", "research_search", "loom.tools.search"),
        ("fetch", "research_fetch", "loom.tools.fetch"),
        ("markdown", "research_markdown", "loom.tools.markdown"),
        ("github", "research_github", "loom.tools.github"),
        ("cache_mgmt", "research_cache_stats", "loom.tools.cache_mgmt"),
        ("llm", "research_llm_summarize", "loom.tools.llm"),
        ("llm", "research_llm_chat", "loom.tools.llm"),
        ("spider", "research_spider", "loom.tools.spider"),
        ("deep", "research_deep", "loom.tools.deep"),
        ("stealth", "research_camoufox", "loom.tools.stealth"),
        ("llm", "research_llm_embed", "loom.tools.llm"),
        ("search", "research_search", "loom.tools.search"),  # Duplicate to test caching
    ]

    for module_name, tool_name, import_path in tools_to_test:
        start = time.time()
        try:
            # Attempt to import the tool module
            mod = __import__(import_path, fromlist=[tool_name])

            # Check if tool function exists
            if not hasattr(mod, tool_name):
                ms = int((time.time() - start) * 1000)
                results.append({
                    "tool": tool_name,
                    "status": "not_found",
                    "module": module_name,
                    "ms": ms
                })
                continue

            func = getattr(mod, tool_name)

            # Validate it's callable
            if not callable(func):
                ms = int((time.time() - start) * 1000)
                results.append({
                    "tool": tool_name,
                    "status": "not_callable",
                    "module": module_name,
                    "ms": ms
                })
                continue

            ms = int((time.time() - start) * 1000)

            # Get function signature
            import inspect
            sig = str(inspect.signature(func))

            results.append({
                "tool": tool_name,
                "status": "loaded",
                "module": module_name,
                "ms": ms,
                "is_async": asyncio.iscoroutinefunction(func),
                "signature": sig[:80]  # Truncate long signatures
            })

        except ImportError as e:
            ms = int((time.time() - start) * 1000)
            results.append({
                "tool": tool_name,
                "status": "import_error",
                "module": module_name,
                "error": str(e)[:80],
                "ms": ms
            })
        except Exception as e:
            ms = int((time.time() - start) * 1000)
            results.append({
                "tool": tool_name,
                "status": "exception",
                "module": module_name,
                "error": f"{type(e).__name__}: {str(e)[:80]}",
                "ms": ms
            })

    return results


def main():
    """Entry point."""
    try:
        print("="*80)
        print("LOOM TOOL TEST SUITE — Direct Module Import")
        print("="*80)
        print()

        results = asyncio.run(run_tests())

        print("Tool Loading Results:")
        print("-"*80)
        for r in results:
            status_icon = "✓" if r["status"] == "loaded" else "✗"
            module = r.get("module", "?")
            status = r.get("status", "unknown")
            ms = r.get("ms", 0)
            print(f"{status_icon} {r['tool']:30s} [{module:12s}] {status:15s} {ms:4d}ms")

        print()
        print("="*80)

        # Summary
        passed = sum(1 for r in results if r["status"] == "loaded")
        total = len(results)

        print(f"SUMMARY: {passed}/{total} tools loaded successfully")
        print("="*80)
        print()

        # Show detailed results for loaded tools
        print("Loaded Tools Details:")
        print("-"*80)
        for r in results:
            if r["status"] == "loaded":
                is_async = "async" if r.get("is_async") else "sync"
                sig = r.get("signature", "")[:60]
                print(f"  {r['tool']:30s} [{is_async:5s}] {sig}")

        if passed == total:
            print()
            print("✓ All tools loaded successfully!")
            return 0
        else:
            print()
            print(f"✗ {total - passed} tools failed to load")
            # Show detailed errors
            print()
            print("Failed Tools:")
            print("-"*80)
            for r in results:
                if r["status"] != "loaded":
                    error_msg = r.get('error', '')[:60]
                    print(f"  {r['tool']:30s} {r.get('status', 'unknown'):15s} {error_msg}")
            return 1

    except Exception as e:
        print(f"✗ FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
