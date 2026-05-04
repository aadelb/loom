#!/usr/bin/env python3
"""Loom performance benchmark suite."""
import time, sys, importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def bench_imports():
    """Benchmark module import times."""
    results = []
    tools_dir = Path(__file__).parent.parent / "src" / "loom" / "tools"
    for f in sorted(tools_dir.glob("*.py"))[:30]:
        if f.name.startswith("_"):
            continue
        start = time.perf_counter()
        try:
            importlib.import_module(f"loom.tools.{f.stem}")
            elapsed = (time.perf_counter() - start) * 1000
            results.append((f.stem, elapsed, "ok"))
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            results.append((f.stem, elapsed, str(type(e).__name__)))
    return results


def bench_cache():
    """Benchmark cache put/get (100 iterations)."""
    from loom.cache import get_cache
    cache = get_cache()
    start = time.perf_counter()
    for i in range(100):
        cache.put(f"bench_key_{i}", f"value_{i}" * 100)
    write_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    for i in range(100):
        cache.get(f"bench_key_{i}")
    read_ms = (time.perf_counter() - start) * 1000
    return {"write_100": f"{write_ms:.1f}ms", "read_100": f"{read_ms:.1f}ms"}


def bench_pii():
    """Benchmark PII scrubber throughput."""
    from loom.pii_scrubber import scrub_pii
    text = "Contact john@example.com or call 555-123-4567. IP: 192.168.1.1" * 50
    start = time.perf_counter()
    for _ in range(1000):
        scrub_pii(text)
    elapsed = (time.perf_counter() - start) * 1000
    return {"1000_iterations_ms": f"{elapsed:.1f}", "texts_per_sec": f"{1000000/elapsed:.0f}"}


if __name__ == "__main__":
    print("=== Loom Benchmark Suite ===\n")
    print("## Import Benchmarks (top 30 modules)")
    for name, ms, status in sorted(bench_imports(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {name:40s} {ms:8.1f}ms  {status}")
    print(f"\n## Cache Benchmarks")
    for k, v in bench_cache().items():
        print(f"  {k:20s} {v}")
    print(f"\n## PII Scrubber Benchmarks")
    for k, v in bench_pii().items():
        print(f"  {k:20s} {v}")
    print("\nDone.")
