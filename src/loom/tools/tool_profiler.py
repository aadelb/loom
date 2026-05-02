"""Tool performance profiler — Identify execution bottlenecks in Loom tools."""
from __future__ import annotations
import gc, importlib.util, logging, psutil, sys, time
from pathlib import Path
from typing import Any
logger = logging.getLogger("loom.tools.tool_profiler")

async def research_profile_tool(tool_name: str, iterations: int = 5) -> dict[str, Any]:
    try:
        if not isinstance(tool_name, str) or not tool_name.strip() or not (1 <= iterations <= 20):
            return {"error": "invalid params"}
        tool_func = tool_module = None
        import_ms = 0.0
        for mf in (Path(__file__).parent).glob("*.py"):
            if mf.name in ("__init__.py", "tool_profiler.py"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(mf.stem, mf)
                if not (spec and spec.loader): continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[mf.stem] = module
                start = time.perf_counter_ns()
                spec.loader.exec_module(module)
                import_ms = (time.perf_counter_ns() - start) / 1_000_000
                if hasattr(module, tool_name):
                    tool_func, tool_module = getattr(module, tool_name), mf.stem
                    break
            except: pass
        if not tool_func:
            return {"error": f"tool {tool_name} not found"}
        gc.collect()
        mem_before = psutil.Process().memory_info().rss / 1024
        timings_ms = []
        for _ in range(iterations):
            try:
                start = time.perf_counter_ns()
                await tool_func()
                timings_ms.append((time.perf_counter_ns() - start) / 1_000_000)
            except:
                try: await tool_func()
                except: pass
                timings_ms.append(0.0)
        gc.collect()
        mem_after = psutil.Process().memory_info().rss / 1024
        timings_ms = timings_ms or [0.0]
        avg_call_ms = sum(timings_ms) / len(timings_ms)
        bottleneck = "import" if import_ms > avg_call_ms * 2 else "execution" if max(timings_ms) > avg_call_ms * 3 else "none"
        return {"tool": tool_name, "module": tool_module, "iterations": iterations, "import_ms": round(import_ms, 3), "avg_call_ms": round(avg_call_ms, 3), "min_call_ms": round(min(timings_ms), 3), "max_call_ms": round(max(timings_ms), 3), "memory_delta_kb": round(mem_after - mem_before, 2), "bottleneck": bottleneck}
    except Exception as e:
        return {"error": str(e)}

async def research_profile_hotspots(top_n: int = 10) -> dict[str, Any]:
    try:
        if not (1 <= top_n <= 50): return {"error": "top_n 1-50"}
        tools_dir = Path(__file__).parent
        hotspots = []
        for mf in sorted(tools_dir.glob("*.py")):
            if mf.name in ("__init__.py", "tool_profiler.py"): continue
            try:
                spec = importlib.util.spec_from_file_location(mf.stem, mf)
                if not (spec and spec.loader): continue
                module = importlib.util.module_from_spec(spec)
                gc.collect()
                start = time.perf_counter_ns()
                spec.loader.exec_module(module)
                hotspots.append({"module": mf.stem, "import_ms": round((time.perf_counter_ns() - start) / 1_000_000, 3)})
                if mf.stem in sys.modules: del sys.modules[mf.stem]
            except: pass
        hotspots.sort(key=lambda x: x["import_ms"], reverse=True)
        hotspots = hotspots[:top_n]
        total_modules = len([f for f in tools_dir.glob("*.py") if f.name not in ("__init__.py", "tool_profiler.py")])
        times = [h["import_ms"] for h in hotspots]
        return {"hotspots": hotspots, "total_modules": total_modules, "avg_import_ms": round(sum(times) / len(times) if times else 0.0, 3), "total_import_ms": round(sum(times), 3), "top_n": top_n}
    except Exception as e:
        return {"error": str(e)}
